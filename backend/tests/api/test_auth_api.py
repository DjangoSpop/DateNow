"""Auth endpoints: register / login / refresh / me."""
from app.models import OnboardingProgress, OnboardingStatus, User
from conftest import API, DEFAULT_PASSWORD

REGISTER = f"{API}/auth/register"
LOGIN = f"{API}/auth/login"
REFRESH = f"{API}/auth/refresh"
ME = f"{API}/auth/me"


def _register(client, email="ada@example.com", password="s3cure-password", **extra):
    body = {"email": email, "password": password, "first_name": "Ada", "last_name": "L"}
    body.update(extra)
    return client.post(REGISTER, json=body)


def _assert_token_pair(body):
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]


# --- register ---------------------------------------------------------------

def test_register_returns_tokens_and_persists_names(client, db):
    r = _register(client, email="Ada@Example.COM")
    assert r.status_code == 201, r.text
    _assert_token_pair(r.json())

    user = db.query(User).one()
    assert user.email == "ada@example.com"  # stored lower-cased
    assert user.first_name == "Ada" and user.last_name == "L"
    assert user.hashed_password != "s3cure-password"


def test_register_duplicate_email_409(client):
    assert _register(client).status_code == 201
    r = _register(client)
    assert r.status_code == 409
    assert r.json() == {"detail": "Email already registered"}


def test_register_duplicate_email_different_case_409(client):
    assert _register(client, email="ada@example.com").status_code == 201
    r = _register(client, email="ADA@EXAMPLE.com")
    assert r.status_code == 409


def test_register_invalid_email_422(client):
    assert _register(client, email="not-an-email").status_code == 422


def test_register_short_password_422(client):
    assert _register(client, password="short").status_code == 422


def test_register_too_long_password_422(client):
    assert _register(client, password="x" * 129).status_code == 422


def test_register_missing_first_name_422(client):
    r = client.post(REGISTER, json={"email": "a@b.com", "password": "longenough"})
    assert r.status_code == 422


def test_register_rejects_server_controlled_fields(client, db):
    for field, value in [("is_verified", True), ("is_active", True), ("id", 99),
                         ("hashed_password", "x")]:
        r = _register(client, email=f"{field}@example.com", **{field: value})
        assert r.status_code == 422, (field, r.text)
    assert db.query(User).count() == 0


# --- login ------------------------------------------------------------------

def test_login_success(client, make_user):
    make_user(email="bob@example.com")
    r = client.post(LOGIN, json={"email": "bob@example.com", "password": DEFAULT_PASSWORD})
    assert r.status_code == 200, r.text
    _assert_token_pair(r.json())


def test_login_is_case_insensitive_on_email(client, make_user):
    make_user(email="bob@example.com")
    r = client.post(LOGIN, json={"email": "BOB@example.com", "password": DEFAULT_PASSWORD})
    assert r.status_code == 200


def test_login_bad_password_401(client, make_user):
    make_user(email="bob@example.com")
    r = client.post(LOGIN, json={"email": "bob@example.com", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Incorrect email or password"}
    assert r.headers.get("www-authenticate") == "Bearer"


def test_login_unknown_email_same_401(client):
    r = client.post(LOGIN, json={"email": "nobody@example.com", "password": "whatever-pw"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Incorrect email or password"}


def test_login_unknown_email_still_runs_bcrypt(client, monkeypatch):
    """Timing-oracle mitigation: a hash verification happens for unknown emails."""
    from app import auth

    calls = []
    real_verify = auth.pwd_context.verify
    monkeypatch.setattr(
        auth.pwd_context, "verify", lambda *a, **k: calls.append(1) or real_verify(*a, **k)
    )
    r = client.post(LOGIN, json={"email": "nobody@example.com", "password": "whatever-pw"})
    assert r.status_code == 401
    assert calls, "bcrypt verify was not called for an unknown email"


def test_login_inactive_user_403(client, make_user):
    make_user(email="off@example.com", is_active=False)
    r = client.post(LOGIN, json={"email": "off@example.com", "password": DEFAULT_PASSWORD})
    assert r.status_code == 403
    assert r.json() == {"detail": "Inactive user"}


# --- refresh ----------------------------------------------------------------

def test_refresh_returns_new_working_pair(client):
    tokens = _register(client).json()
    r = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text
    new = r.json()
    _assert_token_pair(new)
    me = client.get(ME, headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 200


def test_refresh_rejects_access_token(client):
    tokens = _register(client).json()
    r = client.post(REFRESH, json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


def test_refresh_rejects_garbage(client):
    r = client.post(REFRESH, json={"refresh_token": "garbage"})
    assert r.status_code == 401


def test_refresh_requires_json_body(client):
    tokens = _register(client).json()
    # Old implementation took ?refresh_token= as a query parameter.
    r = client.post(REFRESH, params={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 422


def test_refresh_expired_token_401(client, make_user, make_token):
    from datetime import timedelta

    user = make_user()
    token = make_token(sub=str(user.id), token_type="refresh", expires_in=timedelta(seconds=-10))
    assert client.post(REFRESH, json={"refresh_token": token}).status_code == 401


def test_refresh_for_deleted_user_401(client, db, make_user, make_token):
    user = make_user()
    token = make_token(sub=str(user.id), token_type="refresh")
    db.delete(user)
    db.commit()
    assert client.post(REFRESH, json={"refresh_token": token}).status_code == 401


# --- me ---------------------------------------------------------------------

def test_me_returns_contract_shape(client):
    tokens = _register(client, email="me@example.com").json()
    r = client.get(ME, headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "id", "email", "first_name", "last_name", "is_active", "is_verified",
        "created_at", "has_profile", "onboarding_status",
    }
    assert body["email"] == "me@example.com"
    assert body["first_name"] == "Ada" and body["last_name"] == "L"
    assert body["is_active"] is True and body["is_verified"] is False
    assert body["has_profile"] is False
    assert body["onboarding_status"] == "not_started"
    assert "hashed_password" not in r.text


def test_me_reflects_profile_and_onboarding(client, db, make_user, auth_headers, profile_payload):
    user = make_user()
    headers = auth_headers(user)
    assert client.post(f"{API}/users/me/profile", json=profile_payload(), headers=headers).status_code == 201
    db.add(OnboardingProgress(user_id=user.id, status=OnboardingStatus.IN_PROGRESS, answers={"bf_1": 3}))
    db.commit()

    body = client.get(ME, headers=headers).json()
    assert body["has_profile"] is True
    assert body["onboarding_status"] == "in_progress"


def test_me_unauthenticated_401(client):
    r = client.get(ME)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_health_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "healthy"
