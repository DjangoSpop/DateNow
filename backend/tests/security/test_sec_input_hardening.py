"""
Input-hardening regressions: user input must produce 4xx, never an unhandled 500.
"""
import pytest

from helpers import API, assert_error, auth, create_profile, register


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
def test_nul_byte_in_password_is_a_validation_error(client, path):
    register(client)  # so login reaches the password check for a known email
    for email in ("user@example.com", "other@example.com"):
        resp = client.post(f"{API}{path}", json={"email": email, "password": "correct\u0000horse-battery"})
        err = assert_error(resp, 422, "VALIDATION_ERROR")
        assert "password" in err["fields"]


PROFILE_TEXT_FIELDS = ["first_name", "last_name", "bio", "city", "country"]


@pytest.mark.parametrize("field", PROFILE_TEXT_FIELDS)
def test_nul_byte_in_profile_create_is_a_validation_error(client, field):
    token = register(client)["access_token"]
    err = assert_error(create_profile(client, token, **{field: "Sa\u0000m"}), 422, "VALIDATION_ERROR")
    assert field in err["fields"]


@pytest.mark.parametrize("field", PROFILE_TEXT_FIELDS)
def test_nul_byte_in_profile_patch_is_a_validation_error(client, field):
    token = register(client)["access_token"]
    assert create_profile(client, token).status_code == 201
    resp = client.patch(f"{API}/users/me/profile", headers=auth(token), json={field: "x\u0000"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert field in err["fields"]
