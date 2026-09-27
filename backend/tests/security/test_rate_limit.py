"""In-process auth rate limiting (per IP, and per email for login)."""
import pytest

from app import auth
from app.config import settings
from conftest import API, DEFAULT_PASSWORD


@pytest.fixture()
def limit_3(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_PER_MINUTE", 3)
    auth.auth_rate_limiter.reset()
    yield 3
    auth.auth_rate_limiter.reset()


def test_login_rate_limited_after_n_attempts(client, make_user, limit_3):
    make_user(email="rl@example.com")
    body = {"email": "rl@example.com", "password": "wrong-password"}
    codes = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    r = client.post(f"{API}/auth/login", json={"email": "rl@example.com", "password": DEFAULT_PASSWORD})
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


def test_login_rate_limited_per_email_across_ips(client, make_user, limit_3):
    """Per-email bucket: a distributed attack against one account is still capped."""
    make_user(email="target@example.com")
    body = {"email": "target@example.com", "password": "wrong-password"}
    for _ in range(3):
        assert client.post(f"{API}/auth/login", json=body).status_code == 401
        auth.auth_rate_limiter._hits.pop(f"{API}/auth/login:ip:testclient", None)  # simulate new IP
    assert client.post(f"{API}/auth/login", json=body).status_code == 429


def test_register_rate_limited(client, limit_3):
    codes = [
        client.post(f"{API}/auth/register", json={
            "email": f"u{i}@example.com", "password": "longenough1", "first_name": "U"
        }).status_code
        for i in range(4)
    ]
    assert codes == [201, 201, 201, 429]


def test_rate_limit_disabled_with_zero(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_PER_MINUTE", 0)
    make_user(email="nolimit@example.com")
    body = {"email": "nolimit@example.com", "password": "wrong-password"}
    assert all(client.post(f"{API}/auth/login", json=body).status_code == 401 for _ in range(15))


def test_limiter_window_expiry(monkeypatch):
    limiter = auth.SlidingWindowRateLimiter(window_seconds=60)
    clock = {"t": 1000.0}
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock["t"])
    assert limiter.hit("k", 2) is None
    assert limiter.hit("k", 2) is None
    assert limiter.hit("k", 2) is not None
    clock["t"] += 61
    assert limiter.hit("k", 2) is None
    limiter.reset()
    assert limiter._hits == {}
