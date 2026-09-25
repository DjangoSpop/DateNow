"""
JWT claim validation for correctly *signed* tokens (defense in depth: these require the server key, e.g. a
future bug that signs attacker-influenced claims, or a leaked-but-rotated key window).
"""
import time

import pytest
from jose import jwt

from app.config import settings
from helpers import API, assert_error, auth, register


def signed(**claims) -> str:
    now = int(time.time())
    base = {"sub": "1", "type": "access", "iat": now, "exp": now + 600}
    base.update(claims)
    return jwt.encode({k: v for k, v in base.items() if v is not None}, settings.JWT_SECRET_KEY, algorithm="HS256")


def me(client, token):
    return client.get(f"{API}/users/me", headers=auth(token))


@pytest.mark.parametrize("sub", [
    "²",          # superscript two: str.isdigit() is True but int() raises
    "١",          # Arabic-Indic digit one: int() == 1 -> would resolve to user 1
    "１",          # fullwidth digit one
    "1 ", " 1", "+1", "01", "1.0", "0x1", "", "9" * 40,
])
def test_non_canonical_sub_is_invalid_token(client, sub):
    register(client)  # user id 1 exists
    assert_error(me(client, signed(sub=sub)), 401, "INVALID_TOKEN")


def test_canonical_sub_still_works(client):
    register(client)
    assert me(client, signed(sub="1")).status_code == 200


def test_token_without_exp_is_rejected(client):
    """A token with no expiry would be valid forever; the server never issues one."""
    register(client)
    assert_error(me(client, signed(exp=None)), 401, "INVALID_TOKEN")


def test_refresh_without_exp_is_rejected(client):
    register(client)
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": signed(type="refresh", exp=None)})
    assert_error(resp, 401, "INVALID_TOKEN")
