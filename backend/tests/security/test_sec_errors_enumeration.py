"""
Error bodies never leak internals (including on database errors); login does not enumerate accounts;
email normalisation; bcrypt input limits; request-size limits on answers; CORS and debug defaults.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

import app.auth as auth_module
from app import questionnaire
from app.config import Settings, settings
from app.main import app
from app.models import OnboardingAnswer, PsychologicalProfile, User
from helpers import API, DEFAULT_PASSWORD, assert_error, auth, create_profile, login, register

LEAK_MARKERS = (
    "Traceback", "File \"", "SELECT", "INSERT", "UPDATE ", "psycopg2", "sqlalchemy", "OperationalError",
    "DataError", "IntegrityError", "hashed_password", "s3cr3t", "datenow_test", "line ",
)
GENERIC_500 = {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}


def _db_error(kind):
    stmt = "SELECT users.hashed_password FROM users WHERE users.email = %(email)s"
    params = {"email": "victim@example.com", "password": "s3cr3t"}
    return kind(stmt, params, Exception("could not connect to server: datenow_test"))


@pytest.fixture
def raw_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# (dotted target to patch, method, path, body, needs_token)
DB_FAILURE_POINTS = [
    ("app.routes.users.onboarding_status", "GET", "/users/me", None, True),
    ("app.routes.users._get_own_profile", "GET", "/users/me/profile", None, True),
    ("app.services.questionnaire.save_answers", "PUT", "/users/me/questionnaire/answers", {"answers": {"bf_1": 3}},
     True),
    ("app.services.questionnaire.questionnaire_state", "GET", "/users/me/questionnaire", None, True),
    ("app.services.questionnaire.submit", "POST", "/users/me/questionnaire/submit", None, True),
    ("app.routes.auth.authenticate_user", "POST", "/auth/login", {"email": "a@b.com", "password": "x"}, False),
    ("app.routes.auth.get_user_by_email", "POST", "/auth/register",
     {"email": "a@b.com", "password": DEFAULT_PASSWORD}, False),
]


@pytest.mark.parametrize("kind", [OperationalError, DataError, IntegrityError])
@pytest.mark.parametrize("target,method,path,body,needs_token", DB_FAILURE_POINTS, ids=[p[2] for p in DB_FAILURE_POINTS])
def test_database_errors_return_generic_500(raw_client, monkeypatch, kind, target, method, path, body, needs_token):
    headers = auth(register(raw_client, "owner@example.com")["access_token"]) if needs_token else {}

    def boom(*args, **kwargs):
        raise _db_error(kind)

    monkeypatch.setattr(target, boom)
    resp = raw_client.request(method, f"{API}{path}", json=body, headers=headers)
    assert resp.status_code == 500, resp.text
    assert resp.json() == GENERIC_500
    for marker in LEAK_MARKERS:
        assert marker not in resp.text, marker


def test_real_database_error_on_legacy_route_is_generic(raw_client, db):
    """A genuine PostgreSQL error (negative LIMIT on the legacy suggestions route) must not leak SQL."""
    token = register(raw_client, "owner@example.com")["access_token"]
    assert create_profile(raw_client, token).status_code == 201
    db.add(PsychologicalProfile(user_id=1, openness=50.0))
    db.commit()
    resp = raw_client.get(f"{API}/matches/suggestions?limit=-5", headers=auth(token))
    assert resp.status_code in (422, 500), resp.text  # 500 today (see SECURITY_REVIEW_SPRINT1.md); 422 once fixed
    if resp.status_code == 500:
        assert resp.json() == GENERIC_500
    for marker in LEAK_MARKERS:
        assert marker not in resp.text, marker


def test_validation_errors_do_not_echo_password(client):
    resp = client.post(f"{API}/auth/register", json={"email": "not-an-email", "password": "s3cr3t"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert "s3cr3t" not in resp.text
    assert set(err["fields"]) == {"email", "password"}


def test_malformed_json_is_4xx_without_internals(client):
    resp = client.put(f"{API}/users/me/questionnaire/answers", content=b'{"answers": {"bf_1": ',
                      headers={**auth(register(client)["access_token"]), "Content-Type": "application/json"})
    assert 400 <= resp.status_code < 500
    for marker in LEAK_MARKERS:
        assert marker not in resp.text


# --------------------------------------------------------------------------- account enumeration

def _normalised(resp):
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("date", "content-length")}
    return resp.status_code, resp.json(), headers


def test_login_unknown_email_and_bad_password_are_indistinguishable(client):
    register(client)
    unknown = login(client, "nobody@example.com", DEFAULT_PASSWORD)
    bad_pw = login(client, "user@example.com", "wrong-password")
    assert _normalised(unknown) == _normalised(bad_pw)
    assert_error(unknown, 401, "INVALID_CREDENTIALS")


def test_login_runs_bcrypt_for_unknown_email(client, monkeypatch):
    """Timing proxy: both failure paths perform exactly one bcrypt verification."""
    register(client)
    calls = []
    real = auth_module.verify_password
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    login(client, "nobody@example.com", DEFAULT_PASSWORD)
    login(client, "user@example.com", "wrong-password")
    assert len(calls) == 2
    assert calls[0] == auth_module._DUMMY_HASH and calls[1] != auth_module._DUMMY_HASH
    # The dummy hash uses the same cost factor as real hashes, so the work is comparable.
    assert calls[0].split("$")[2] == calls[1].split("$")[2]


# --------------------------------------------------------------------------- email normalisation

@pytest.mark.parametrize("variant", [
    "USER@EXAMPLE.COM", "User@Example.Com", "  user@example.com", "user@example.com\t", "user@EXAMPLE.com",
])
def test_email_variants_cannot_create_duplicate_accounts(client, db, variant):
    register(client, "user@example.com")
    resp = client.post(f"{API}/auth/register", json={"email": variant, "password": DEFAULT_PASSWORD})
    assert_error(resp, 409, "EMAIL_TAKEN")
    assert db.query(User).count() == 1
    assert login(client, variant, DEFAULT_PASSWORD).status_code == 200


@pytest.mark.parametrize("email", ["user​@example.com", "user@example.com.", "user @example.com"])
def test_invisible_or_malformed_email_rejected(client, email):
    assert_error(client.post(f"{API}/auth/register", json={"email": email, "password": DEFAULT_PASSWORD}), 422,
                 "VALIDATION_ERROR")


def test_stored_email_is_normalised(client, db):
    register(client, "  Mixed.Case@Example.COM ")
    assert db.query(User).one().email == "mixed.case@example.com"


# --------------------------------------------------------------------------- password limits (bcrypt)

def test_password_longer_than_128_chars_rejected(client):
    resp = client.post(f"{API}/auth/register", json={"email": "a@example.com", "password": "x" * 129})
    assert_error(resp, 422, "VALIDATION_ERROR")
    resp = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "x" * 10_000})
    assert_error(resp, 422, "VALIDATION_ERROR")


@pytest.mark.xfail(strict=True, reason="KNOWN (open): bcrypt only uses the first 72 bytes of the password")
def test_password_bytes_after_72_are_significant(client):
    prefix = "x" * 72
    register(client, "long@example.com", prefix + "-first-suffix")
    assert login(client, "long@example.com", prefix + "-other-suffix").status_code == 401


# --------------------------------------------------------------------------- request-size limits

def test_answers_batch_limit(client, db):
    token = register(client)["access_token"]
    ids = questionnaire.question_ids()
    too_many = {f"x{i}": 1 for i in range(101)}
    assert_error(client.put(f"{API}/users/me/questionnaire/answers", headers=auth(token), json={"answers": too_many}),
                 422, "VALIDATION_ERROR")
    ok = {qid: 3 for qid in ids[:5]}
    assert client.put(f"{API}/users/me/questionnaire/answers", headers=auth(token), json={"answers": ok}).status_code \
        == 200
    assert db.query(OnboardingAnswer).count() == 5


@pytest.mark.parametrize("value", [True, 3.0, "3", None, [3], {"v": 3}, 10**30, -1])
def test_scale_answer_type_confusion_rejected(client, db, value):
    token = register(client)["access_token"]
    resp = client.put(f"{API}/users/me/questionnaire/answers", headers=auth(token), json={"answers": {"bf_1": value}})
    assert_error(resp, 422, "VALIDATION_ERROR")
    assert db.query(OnboardingAnswer).count() == 0


# --------------------------------------------------------------------------- CORS / debug defaults

def test_cors_rejects_unknown_origin(client):
    resp = client.options(f"{API}/users/me", headers={"Origin": "https://evil.example",
                                                      "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in resp.headers
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in resp.headers


def test_cors_origins_are_explicit():
    assert "*" not in settings.BACKEND_CORS_ORIGINS


def test_debug_and_sql_echo_off_by_default():
    assert Settings.model_fields["DEBUG"].default is False
    assert app.debug is False
    from app.database import engine
    assert engine.echo is False
