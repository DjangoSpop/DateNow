"""CORS: only configured origins are reflected."""
from app.config import settings
from conftest import API


def test_disallowed_origin_not_reflected(client):
    r = client.options(f"{API}/auth/login", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_allowed_origin_reflected(client):
    origin = settings.BACKEND_CORS_ORIGINS[0]
    r = client.options(f"{API}/auth/login", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("access-control-allow-origin") == origin
