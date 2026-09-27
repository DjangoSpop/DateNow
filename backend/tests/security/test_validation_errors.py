"""422 responses must not echo submitted values (e.g. passwords) back."""
from conftest import API


def test_validation_error_does_not_echo_password(client):
    secret = "p" * 200  # too long -> 422
    r = client.post(f"{API}/auth/register", json={
        "email": "x@example.com", "password": secret, "first_name": "X",
    })
    assert r.status_code == 422
    assert secret not in r.text
    errors = r.json()["detail"]
    assert errors and all(set(e) <= {"loc", "msg", "type"} for e in errors)
    assert any(e["loc"][-1] == "password" for e in errors)
