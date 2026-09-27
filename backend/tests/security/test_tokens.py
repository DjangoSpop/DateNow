"""JWT handling: every malformed/forged/wrong-type token must yield 401."""
from datetime import timedelta

import pytest
from jose import jwt

from app.auth import create_access_token, create_refresh_token
from conftest import API, TEST_JWT_SECRET

ME = f"{API}/auth/me"


def _me(client, token):
    return client.get(ME, headers={"Authorization": f"Bearer {token}"})


def _assert_401(r):
    assert r.status_code == 401, r.text
    assert r.headers.get("www-authenticate") == "Bearer"


def test_issued_tokens_have_contract_claims(make_user):
    user = make_user()
    access = jwt.decode(create_access_token({"sub": user.id}), TEST_JWT_SECRET, algorithms=["HS256"])
    refresh = jwt.decode(create_refresh_token({"sub": user.id}), TEST_JWT_SECRET, algorithms=["HS256"])
    for claims, typ in ((access, "access"), (refresh, "refresh")):
        assert claims["sub"] == str(user.id)  # string subject
        assert claims["type"] == typ
        assert isinstance(claims["iat"], int) and isinstance(claims["exp"], int)
        assert claims["exp"] > claims["iat"]
    assert jwt.get_unverified_header(create_access_token({"sub": 1}))["alg"] == "HS256"


def test_valid_token_accepted(client, make_user, make_token):
    user = make_user()
    r = _me(client, make_token(sub=str(user.id)))
    assert r.status_code == 200 and r.json()["id"] == user.id


def test_missing_authorization_header_401(client):
    _assert_401(client.get(ME))


@pytest.mark.parametrize("header", [
    "", "Bearer", "Bearer ", "Basic dXNlcjpwYXNz", "Token abc", "bearer",
])
def test_bad_authorization_header_401(client, header):
    _assert_401(client.get(ME, headers={"Authorization": header}))


def test_expired_token_401(client, make_user, make_token):
    user = make_user()
    _assert_401(_me(client, make_token(sub=str(user.id), expires_in=timedelta(seconds=-5))))


@pytest.mark.parametrize("token", [
    "not-a-jwt", "a.b.c", "....", "eyJhbGciOiJIUzI1NiJ9.e30.", "x" * 5000,
])
def test_malformed_token_401(client, token):
    _assert_401(_me(client, token))


def test_tampered_signature_401(client, make_user, make_token):
    user = make_user()
    token = make_token(sub=str(user.id))
    head, payload, sig = token.split(".")
    tampered_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    _assert_401(_me(client, f"{head}.{payload}.{tampered_sig}"))


def test_tampered_payload_401(client, make_user, make_token):
    """Swap in another user's payload but keep the original signature."""
    a, b = make_user(), make_user()
    ta = make_token(sub=str(a.id))
    tb = make_token(sub=str(b.id))
    forged = ".".join([ta.split(".")[0], tb.split(".")[1], ta.split(".")[2]])
    _assert_401(_me(client, forged))


def test_token_signed_with_other_secret_401(client, make_user, make_token):
    user = make_user()
    _assert_401(_me(client, make_token(sub=str(user.id), secret="some-other-secret-value-xxxxxxxx")))


def test_alg_none_token_401(client, make_user, make_token):
    user = make_user()
    _assert_401(_me(client, make_token(sub=str(user.id), alg="none")))


def test_other_hmac_alg_rejected(client, make_user, make_token):
    user = make_user()
    _assert_401(_me(client, make_token(sub=str(user.id), alg="HS512")))


def test_refresh_token_rejected_as_access(client, make_user):
    user = make_user()
    _assert_401(_me(client, create_refresh_token({"sub": user.id})))


def test_access_token_rejected_at_refresh(client, make_user):
    user = make_user()
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": create_access_token({"sub": user.id})})
    _assert_401(r)


@pytest.mark.parametrize("claims", [
    {"omit": ("type",)},
    {"token_type": "id"},
    {"token_type": None},
    {"omit": ("sub",)},
    {"omit": ("exp",)},
    {"omit": ("iat",)},
    {"sub": "abc"},
    {"sub": "1.5"},
    {"sub": "-1"},
    {"sub": "0"},
    {"sub": " 1"},
    {"sub": "１"},  # full-width digit
    {"sub": "9" * 40},
    {"sub": ""},
])
def test_invalid_claims_401(client, make_user, make_token, claims):
    user = make_user()
    claims = dict(claims)
    if "sub" not in claims:
        claims["sub"] = str(user.id)  # so the only defect is the one under test
    _assert_401(_me(client, make_token(**claims)))


def test_integer_sub_rejected(client, make_user, make_token):
    """Legacy tokens with an integer sub are invalid per RFC 7519 / contract."""
    user = make_user()
    _assert_401(_me(client, make_token(sub=user.id)))


def test_token_for_deleted_user_401(client, db, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)
    db.delete(user)
    db.commit()
    _assert_401(client.get(ME, headers=headers))


def test_token_for_unknown_user_401(client, make_token):
    _assert_401(_me(client, make_token(sub="424242")))


def test_inactive_user_403(client, make_user, auth_headers):
    user = make_user(is_active=False)
    r = client.get(ME, headers=auth_headers(user))
    assert r.status_code == 403
    assert r.json() == {"detail": "Inactive user"}


def test_inactive_user_refresh_403(client, make_user):
    user = make_user(is_active=False)
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": create_refresh_token({"sub": user.id})})
    assert r.status_code == 403


def test_get_current_active_user_inactive_403():
    from fastapi import HTTPException
    from app.auth import get_current_active_user
    from app.models import User

    with pytest.raises(HTTPException) as exc:
        get_current_active_user(User(id=1, email="x@y.z", is_active=False))
    assert exc.value.status_code == 403


def test_websocket_decode_token_rejects_refresh(make_user):
    """app.routes.websocket uses decode_token(); it must only accept access tokens."""
    from fastapi import HTTPException
    from app.auth import decode_token

    user = make_user()
    assert decode_token(create_access_token({"sub": user.id})).user_id == user.id
    with pytest.raises(HTTPException):
        decode_token(create_refresh_token({"sub": user.id}))
