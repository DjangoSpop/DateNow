"""/users/me/profile CRUD, validation, mass assignment and ownership."""
from datetime import date, timedelta

import pytest

from app.models import UserProfile
from conftest import API

PROFILE = f"{API}/users/me/profile"

RESPONSE_FIELDS = {
    "id", "user_id", "first_name", "last_name", "date_of_birth", "gender", "bio", "city",
    "country", "height_cm", "looking_for_gender", "age_preference_min", "age_preference_max",
    "distance_preference_km", "relationship_goal", "is_profile_complete", "photos",
    "profile_photo_url", "created_at", "updated_at",
}


def _years_ago(years: int, days: int = 0) -> str:
    today = date.today()
    try:
        d = today.replace(year=today.year - years)
    except ValueError:  # Feb 29
        d = today.replace(year=today.year - years, day=28)
    return (d + timedelta(days=days)).isoformat()


@pytest.fixture()
def user_headers(make_user, auth_headers):
    user = make_user()
    return user, auth_headers(user)


# --- CRUD -------------------------------------------------------------------

def test_get_profile_404_before_creation(client, user_headers):
    _, headers = user_headers
    r = client.get(PROFILE, headers=headers)
    assert r.status_code == 404


def test_create_get_patch_profile(client, user_headers, profile_payload):
    user, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(), headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == RESPONSE_FIELDS
    assert body["user_id"] == user.id
    assert body["date_of_birth"] == "1995-04-12"
    assert body["is_profile_complete"] is True
    assert body["looking_for_gender"] == ["male"]
    assert "latitude" not in body and "longitude" not in body

    r = client.get(PROFILE, headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == body["id"]

    r = client.patch(PROFILE, json={"bio": "Updated", "age_preference_max": 40}, headers=headers)
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["bio"] == "Updated"
    assert patched["age_preference_max"] == 40
    assert patched["first_name"] == "Ada"  # untouched fields preserved


def test_patch_date_of_birth_as_date_string(client, user_headers, profile_payload):
    _, headers = user_headers
    client.post(PROFILE, json=profile_payload(), headers=headers)
    r = client.patch(PROFILE, json={"date_of_birth": "1990-01-31"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["date_of_birth"] == "1990-01-31"


def test_patch_without_profile_404(client, user_headers):
    _, headers = user_headers
    assert client.patch(PROFILE, json={"bio": "x"}, headers=headers).status_code == 404


def test_create_profile_twice_400(client, user_headers, profile_payload):
    _, headers = user_headers
    assert client.post(PROFILE, json=profile_payload(), headers=headers).status_code == 201
    r = client.post(PROFILE, json=profile_payload(), headers=headers)
    assert r.status_code == 400
    assert r.json() == {"detail": "Profile already exists"}


def test_profile_requires_auth(client, profile_payload):
    assert client.get(PROFILE).status_code == 401
    assert client.post(PROFILE, json=profile_payload()).status_code == 401
    assert client.patch(PROFILE, json={"bio": "x"}).status_code == 401


# --- validation -------------------------------------------------------------

def test_under_18_rejected_422(client, user_headers, profile_payload):
    _, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(date_of_birth=_years_ago(18, days=1)), headers=headers)
    assert r.status_code == 422
    assert any("date_of_birth" in e["loc"] for e in r.json()["detail"])


def test_exactly_18_accepted(client, user_headers, profile_payload):
    _, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(date_of_birth=_years_ago(18)), headers=headers)
    assert r.status_code == 201, r.text


def test_future_dob_rejected(client, user_headers, profile_payload):
    _, headers = user_headers
    future = (date.today() + timedelta(days=10)).isoformat()
    assert client.post(PROFILE, json=profile_payload(date_of_birth=future), headers=headers).status_code == 422


def test_patch_under_18_rejected(client, user_headers, profile_payload):
    _, headers = user_headers
    client.post(PROFILE, json=profile_payload(), headers=headers)
    r = client.patch(PROFILE, json={"date_of_birth": _years_ago(10)}, headers=headers)
    assert r.status_code == 422


def test_age_min_greater_than_max_422(client, user_headers, profile_payload):
    _, headers = user_headers
    r = client.post(
        PROFILE, json=profile_payload(age_preference_min=40, age_preference_max=30), headers=headers
    )
    assert r.status_code == 422


@pytest.mark.parametrize("field,value", [
    ("age_preference_min", 17), ("age_preference_max", 101),
    ("distance_preference_km", 0), ("gender", "robot"), ("relationship_goal", "fling"),
    ("looking_for_gender", []), ("height_cm", 5), ("first_name", ""),
])
def test_field_level_validation_422(client, user_headers, profile_payload, field, value):
    _, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(**{field: value}), headers=headers)
    assert r.status_code == 422, (field, value, r.text)


def test_patch_merged_age_range_validated(client, user_headers, profile_payload):
    """min=25,max=35 stored; PATCH only min=40 -> merged min>max -> 422."""
    _, headers = user_headers
    client.post(PROFILE, json=profile_payload(), headers=headers)
    r = client.patch(PROFILE, json={"age_preference_min": 40}, headers=headers)
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "age_preference_min"]
    r = client.patch(PROFILE, json={"age_preference_max": 20}, headers=headers)
    assert r.status_code == 422
    # still unchanged
    body = client.get(PROFILE, headers=headers).json()
    assert (body["age_preference_min"], body["age_preference_max"]) == (25, 35)


def test_patch_cannot_null_required_fields(client, user_headers, profile_payload):
    _, headers = user_headers
    client.post(PROFILE, json=profile_payload(), headers=headers)
    for field in ("first_name", "date_of_birth", "gender", "age_preference_min"):
        r = client.patch(PROFILE, json={field: None}, headers=headers)
        assert r.status_code == 422, field


def test_patch_can_clear_optional_field(client, user_headers, profile_payload):
    _, headers = user_headers
    client.post(PROFILE, json=profile_payload(), headers=headers)
    r = client.patch(PROFILE, json={"bio": None}, headers=headers)
    assert r.status_code == 200 and r.json()["bio"] is None


# --- mass assignment --------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("user_id", 999), ("id", 999), ("is_profile_complete", False), ("photos", ["x"]),
    ("profile_photo_url", "http://evil"), ("latitude", 1.0), ("longitude", 2.0),
    ("created_at", "2020-01-01T00:00:00Z"), ("updated_at", "2020-01-01T00:00:00Z"),
])
def test_create_mass_assignment_rejected(client, db, user_headers, profile_payload, field, value):
    _, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(**{field: value}), headers=headers)
    assert r.status_code == 422, (field, r.text)
    assert db.query(UserProfile).count() == 0


@pytest.mark.parametrize("field,value", [
    ("user_id", 999), ("id", 999), ("is_profile_complete", False), ("latitude", 1.0),
])
def test_patch_mass_assignment_rejected(client, user_headers, profile_payload, field, value):
    user, headers = user_headers
    created = client.post(PROFILE, json=profile_payload(), headers=headers).json()
    r = client.patch(PROFILE, json={field: value}, headers=headers)
    assert r.status_code == 422
    after = client.get(PROFILE, headers=headers).json()
    assert after["user_id"] == user.id and after["id"] == created["id"]
    assert after["is_profile_complete"] is True


# --- ownership --------------------------------------------------------------

def test_users_only_see_and_modify_their_own_profile(client, make_user, auth_headers, profile_payload):
    a, b = make_user(), make_user()
    ha, hb = auth_headers(a), auth_headers(b)
    pa = client.post(PROFILE, json=profile_payload(first_name="Alice"), headers=ha).json()
    pb = client.post(PROFILE, json=profile_payload(first_name="Bob"), headers=hb).json()

    ga = client.get(PROFILE, headers=ha).json()
    assert ga["id"] == pa["id"] and ga["user_id"] == a.id and ga["first_name"] == "Alice"

    client.patch(PROFILE, json={"bio": "A's bio"}, headers=ha)
    gb = client.get(PROFILE, headers=hb).json()
    assert gb["id"] == pb["id"] and gb["bio"] == "Hello"

    # No route exposes another user's profile by id.
    for path in (f"{API}/users/{b.id}/profile", f"{API}/users/{b.id}", f"{API}/users/profile/{pb['id']}"):
        for method in ("get", "patch", "put", "delete"):
            r = getattr(client, method)(path, headers=ha)
            assert r.status_code in (404, 405), (method, path, r.status_code)


def test_profile_response_never_leaks_credentials(client, user_headers, profile_payload):
    _, headers = user_headers
    r = client.post(PROFILE, json=profile_payload(), headers=headers)
    assert "hashed_password" not in r.text and "email" not in r.json()
