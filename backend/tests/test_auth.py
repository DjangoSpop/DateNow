from datetime import timedelta

from jose import jwt

from app.auth import create_access_token, create_refresh_token
from app.config import settings
from app.models import User
from helpers import API, DEFAULT_PASSWORD, assert_error, auth, login, register


def me(client, token):
    return client.get(f"{API}/users/me", headers=auth(token))


# ------------------------------------------------------------------ register / login

def test_register_returns_token_pair(client, db):
    resp = client.post(
        f"{API}/auth/register",
        json={"email": "  New.User@Example.COM ", "password": DEFAULT_PASSWORD, "first_name": "ignored"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert db.query(User).one().email == "new.user@example.com"  # trimmed + lower-cased


def test_jwt_claims(client):
    tokens = register(client)
    for token, typ in ((tokens["access_token"], "access"), (tokens["refresh_token"], "refresh")):
        claims = jwt.get_unverified_claims(token)
        assert claims["sub"] == "1" and isinstance(claims["sub"], str)
        assert claims["type"] == typ
        assert isinstance(claims["iat"], int) and claims["exp"] > claims["iat"]


def test_register_duplicate_email_case_insensitive(client):
    register(client, "Foo@Example.com")
    resp = client.post(f"{API}/auth/register", json={"email": " foo@EXAMPLE.com", "password": DEFAULT_PASSWORD})
    err = assert_error(resp, 409, "EMAIL_TAKEN")
    assert "email" in err["fields"]


def test_register_validation(client):
    resp = client.post(f"{API}/auth/register", json={"email": "not-an-email", "password": "short"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert set(err["fields"]) == {"email", "password"}
    resp = client.post(f"{API}/auth/register", json={"email": "a@b.com", "password": "x" * 129})
    assert assert_error(resp, 422, "VALIDATION_ERROR")["fields"].keys() == {"password"}


def test_login_ok_case_insensitive(client):
    register(client, "user@example.com")
    resp = login(client, "USER@example.com ")
    assert resp.status_code == 200, resp.text
    assert me(client, resp.json()["access_token"]).status_code == 200


def test_login_bad_password(client):
    register(client)
    assert_error(login(client, password="wrong-password"), 401, "INVALID_CREDENTIALS")


def test_login_unknown_email_same_error(client):
    register(client)
    resp_unknown = login(client, email="nobody@example.com")
    resp_bad = login(client, password="wrong-password")
    assert_error(resp_unknown, 401, "INVALID_CREDENTIALS")
    assert resp_unknown.json() == resp_bad.json()


def test_login_disabled_user(client, db):
    register(client)
    db.query(User).update({"is_active": False})
    db.commit()
    assert_error(login(client), 403, "ACCOUNT_DISABLED")


# ------------------------------------------------------------------ token validation on /users/me

def test_valid_token_on_me(client):
    tokens = register(client)
    resp = me(client, tokens["access_token"])
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


def test_missing_header(client):
    assert_error(client.get(f"{API}/users/me"), 401, "NOT_AUTHENTICATED")
    assert_error(client.get(f"{API}/users/me", headers={"Authorization": "Basic abc"}), 401, "NOT_AUTHENTICATED")


def test_expired_token(client):
    register(client)
    token = create_access_token(1, expires_delta=timedelta(seconds=-10))
    assert_error(me(client, token), 401, "TOKEN_EXPIRED")


def test_malformed_token(client):
    register(client)
    assert_error(me(client, "not.a.jwt"), 401, "INVALID_TOKEN")
    assert_error(me(client, "garbage"), 401, "INVALID_TOKEN")


def test_bad_signature(client):
    register(client)
    forged = jwt.encode({"sub": "1", "type": "access", "iat": 0, "exp": 9999999999}, "another-key", algorithm="HS256")
    assert_error(me(client, forged), 401, "INVALID_TOKEN")


def test_non_string_or_bad_sub(client):
    register(client)
    for sub in (1, "abc", None):
        token = jwt.encode({"sub": sub, "type": "access", "exp": 9999999999}, settings.JWT_SECRET_KEY, algorithm="HS256")
        assert_error(me(client, token), 401, "INVALID_TOKEN")


def test_refresh_token_used_as_access(client):
    tokens = register(client)
    assert_error(me(client, tokens["refresh_token"]), 401, "INVALID_TOKEN")


def test_access_token_used_for_refresh(client):
    tokens = register(client)
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert_error(resp, 401, "INVALID_TOKEN")


def test_token_for_deleted_user(client, db):
    tokens = register(client)
    db.query(User).delete()
    db.commit()
    assert_error(me(client, tokens["access_token"]), 401, "INVALID_TOKEN")
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(resp, 401, "INVALID_TOKEN")


def test_disabled_user_token(client, db):
    tokens = register(client)
    db.query(User).update({"is_active": False})
    db.commit()
    assert_error(me(client, tokens["access_token"]), 403, "ACCOUNT_DISABLED")


# ------------------------------------------------------------------ refresh

def test_refresh_returns_new_working_pair(client):
    tokens = register(client)
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200, resp.text
    pair = resp.json()
    assert set(pair) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert me(client, pair["access_token"]).status_code == 200
    again = client.post(f"{API}/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert again.status_code == 200, again.text


def test_refresh_expired(client):
    register(client)
    token = create_refresh_token(1, expires_delta=timedelta(seconds=-10))
    assert_error(client.post(f"{API}/auth/refresh", json={"refresh_token": token}), 401, "TOKEN_EXPIRED")


def test_refresh_requires_body(client):
    err = assert_error(client.post(f"{API}/auth/refresh", json={}), 422, "VALIDATION_ERROR")
    assert "refresh_token" in err["fields"]
