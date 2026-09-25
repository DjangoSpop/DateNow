"""
Authentication regression matrix for every protected (🔒) endpoint.

`PROTECTED_ENDPOINTS` is the single table to extend when an endpoint is added. `test_endpoint_table_is_complete`
fails if the app exposes an HTTP route that depends on `get_current_user` and is not listed here (or vice versa).
"""
import base64
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute
from jose import jwt

from app.auth import create_refresh_token, get_current_user
from app.config import settings
from app.main import app
from app.models import Match, MatchStatus
from helpers import API, assert_error, auth, create_profile, register
from starlette.websockets import WebSocketDisconnect

# (method, path, json body). Bodies are valid so that only authentication can fail.
PROTECTED_ENDPOINTS = [
    # Sprint 1 contract
    ("GET", "/users/me", None),
    ("GET", "/users/me/profile", None),
    ("POST", "/users/me/profile", {"first_name": "Sam"}),
    ("PATCH", "/users/me/profile", {"first_name": "Sam"}),
    ("GET", "/questionnaire", None),
    ("GET", "/users/me/questionnaire", None),
    ("PUT", "/users/me/questionnaire/answers", {"answers": {"bf_1": 3}}),
    ("POST", "/users/me/questionnaire/submit", None),
    ("GET", "/users/me/psychological-profile", None),
    # Legacy (out of Sprint 1 scope, still exposed)
    ("GET", "/users/me/interests", None),
    ("POST", "/users/me/interests", [1]),
    ("GET", "/matches/", None),
    ("GET", "/matches/suggestions", None),
    ("GET", "/matches/1", None),
    ("POST", "/matches/1/action", {"action": "accept"}),
    ("GET", "/matches/1/ai-session", None),
    ("POST", "/matches/1/ai-session/question", None),
    ("POST", "/matches/1/ai-session/response", {"session_id": 1, "question": "q", "answer": "a"}),
]

# Deliberately public HTTP endpoints.
PUBLIC_ENDPOINTS = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("GET", "/users/interests"),
}

_IDS = [f"{m} {p}" for m, p, _ in PROTECTED_ENDPOINTS]


def _b64(obj) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _claims(sub: str = "1", **extra) -> dict:
    now = int(time.time())
    claims = {"sub": sub, "type": "access", "iat": now, "exp": now + 600}
    claims.update(extra)
    return claims


def _unsigned(alg: str) -> str:
    return f"{_b64({'alg': alg, 'typ': 'JWT'})}.{_b64(_claims())}."


def _rs256_token() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return jwt.encode(_claims(), pem, algorithm="RS256")


def _signed(claims: dict, alg: str = "HS256", key: str | None = None) -> str:
    return jwt.encode(claims, key or settings.JWT_SECRET_KEY, algorithm=alg)


_no_type = _claims()
del _no_type["type"]

# name -> zero-arg factory (built lazily so every test gets a fresh token).
INVALID_TOKENS = {
    "garbage": lambda: "garbage",
    "three-garbage-segments": lambda: "aaa.bbb.ccc",
    "alg-none": lambda: _unsigned("none"),
    "alg-None-mixed-case": lambda: _unsigned("None"),
    "alg-HS256-empty-signature": lambda: _signed(_claims()).rsplit(".", 1)[0] + ".",
    "wrong-key": lambda: _signed(_claims(), key="some-other-secret-key-0123456789abcdef"),
    "HS512-with-server-key": lambda: _signed(_claims(), alg="HS512"),
    "RS256-foreign-key": _rs256_token,
    "refresh-as-access": lambda: create_refresh_token(1),
    "missing-type": lambda: _signed(_no_type),
    "unknown-type": lambda: _signed(_claims(type="admin")),
    "nonexistent-user": lambda: _signed(_claims(sub="999999")),
    "negative-sub": lambda: _signed(_claims(sub="-1")),
    "non-numeric-sub": lambda: _signed(_claims(sub="admin")),
    "integer-sub": lambda: _signed(_claims(sub=1)),
    "non-ascii-digit-sub": lambda: _signed(_claims(sub="١")),
    "no-exp": lambda: _signed({k: v for k, v in _claims().items() if k != "exp"}),
    "huge-token": lambda: "a." + "A" * 100_000 + ".b",
}


def _call(client, method: str, path: str, body, headers=None):
    kwargs = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return client.request(method, f"{API}{path}", **kwargs)


def _protected_routes() -> set:
    """(method, path) of every HTTP route whose dependency tree contains get_current_user."""

    def uses_auth(dependant) -> bool:
        return any(d.call is get_current_user or uses_auth(d) for d in dependant.dependencies)

    found = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and uses_auth(route.dependant):
            for method in route.methods:
                found.add((method, route.path.removeprefix(API)))
    return found


def test_endpoint_table_is_complete():
    table = {(m, p) for m, p, _ in PROTECTED_ENDPOINTS}
    table = {(m, p.replace("/matches/1", "/matches/{match_id}")) for m, p in table}
    assert _protected_routes() == table


def test_every_other_api_route_is_deliberately_public():
    protected = _protected_routes()
    public = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(API):
            for method in route.methods:
                key = (method, route.path.removeprefix(API))
                if key not in protected:
                    public.add(key)
    assert public == PUBLIC_ENDPOINTS


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS, ids=_IDS)
def test_missing_token_is_not_authenticated(client, method, path, body):
    err = assert_error(_call(client, method, path, body), 401, "NOT_AUTHENTICATED")
    assert "fields" not in err


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS, ids=_IDS)
@pytest.mark.parametrize("scheme", ["Basic dXNlcjpwYXNz", "Bearer", "Bearer ", "Token abc"])
def test_wrong_scheme_or_empty_bearer_is_not_authenticated(client, method, path, body, scheme):
    assert_error(_call(client, method, path, body, {"Authorization": scheme}), 401, "NOT_AUTHENTICATED")


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS, ids=_IDS)
@pytest.mark.parametrize("token_name", list(INVALID_TOKENS))
def test_invalid_token_rejected(client, method, path, body, token_name):
    resp = _call(client, method, path, body, auth(INVALID_TOKENS[token_name]()))
    assert_error(resp, 401, "INVALID_TOKEN")
    assert resp.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize("token_name", [n for n in INVALID_TOKENS if n != "refresh-as-access"])
def test_refresh_endpoint_rejects_invalid_tokens(client, token_name):
    token = INVALID_TOKENS[token_name]()
    if token_name not in ("garbage", "three-garbage-segments", "huge-token", "alg-none", "alg-None-mixed-case",
                          "alg-HS256-empty-signature", "wrong-key", "HS512-with-server-key", "RS256-foreign-key"):
        # Claim-level cases: re-issue as a refresh token so the type check is not what rejects it.
        claims = jwt.get_unverified_claims(token)
        if claims.get("type") == "access":
            claims["type"] = "refresh"
        token = _signed(claims)
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": token})
    assert_error(resp, 401, "INVALID_TOKEN")


@pytest.fixture
def mediated_match(client, db):
    """Users 1 and 2 with profiles and a match in ai_mediation (the only status the WS accepts)."""
    token_a = register(client, "a@example.com")["access_token"]
    token_b = register(client, "b@example.com")["access_token"]
    create_profile(client, token_a, first_name="Alice")
    create_profile(client, token_b, first_name="Bob", gender="male", looking_for_gender=["female"])
    match = Match(user1_id=1, user2_id=2, status=MatchStatus.AI_MEDIATION, overall_compatibility=0.8)
    db.add(match)
    db.commit()
    return match.id


def _assert_ws_refused(client, url):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


# huge-token is excluded: the test client itself refuses URLs that long.
@pytest.mark.parametrize("token_name", [n for n in INVALID_TOKENS if n != "huge-token"])
def test_websocket_rejects_invalid_tokens(client, mediated_match, token_name):
    _assert_ws_refused(client, f"/ws/conversation/{mediated_match}?token={INVALID_TOKENS[token_name]()}")


def test_websocket_rejects_missing_token(client, mediated_match):
    _assert_ws_refused(client, f"/ws/conversation/{mediated_match}")
