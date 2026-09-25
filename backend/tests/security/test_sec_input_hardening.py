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
