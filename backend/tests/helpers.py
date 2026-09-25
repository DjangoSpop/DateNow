"""Shared test helpers (fixtures live in conftest.py)."""
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

API = "/api/v1"
DEFAULT_PASSWORD = "correct-horse-battery"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, email: str = "user@example.com", password: str = DEFAULT_PASSWORD) -> dict:
    resp = client.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def login(client: TestClient, email: str = "user@example.com", password: str = DEFAULT_PASSWORD):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def years_ago(years: int, days_offset: int = 0) -> date:
    today = datetime.now(timezone.utc).date()
    try:
        d = today.replace(year=today.year - years)
    except ValueError:  # Feb 29
        d = today.replace(year=today.year - years, day=28)
    return d + timedelta(days=days_offset)


def profile_payload(**overrides) -> dict:
    body = {
        "first_name": "Sam",
        "last_name": None,
        "date_of_birth": "1995-04-02",
        "gender": "female",
        "looking_for_gender": ["male"],
        "age_preference_min": 27,
        "age_preference_max": 38,
        "relationship_goal": "serious",
        "bio": None,
        "city": "Cairo",
        "country": "Egypt",
    }
    body.update(overrides)
    return body


def create_profile(client: TestClient, token: str, **overrides):
    return client.post(f"{API}/users/me/profile", json=profile_payload(**overrides), headers=auth(token))


def assert_error(resp, status: int, code: str) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert set(body.keys()) == {"error"}, body
    assert body["error"]["code"] == code, body
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    return body["error"]
