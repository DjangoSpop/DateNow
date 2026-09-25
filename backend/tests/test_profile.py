import pytest

from app.models import UserProfile
from helpers import API, assert_error, auth, create_profile, profile_payload, register, years_ago

PROFILE_KEYS = {
    "first_name", "last_name", "date_of_birth", "age", "gender", "looking_for_gender",
    "age_preference_min", "age_preference_max", "relationship_goal", "bio", "city", "country",
    "created_at", "updated_at",
}


@pytest.fixture
def token(client):
    return register(client)["access_token"]


def test_create_get_patch(client, token):
    resp = create_profile(client, token, first_name="  Sam  ")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body) == PROFILE_KEYS  # never latitude/longitude/ids
    assert body["first_name"] == "Sam"
    assert body["date_of_birth"] == "1995-04-02"
    assert isinstance(body["age"], int) and body["age"] >= 31
    assert body["looking_for_gender"] == ["male"]

    got = client.get(f"{API}/users/me/profile", headers=auth(token))
    assert got.status_code == 200
    assert got.json() == body

    patched = client.patch(f"{API}/users/me/profile", json={"bio": "Hello", "city": "Giza"}, headers=auth(token))
    assert patched.status_code == 200, patched.text
    p = patched.json()
    assert p["bio"] == "Hello" and p["city"] == "Giza"
    for key in ("first_name", "date_of_birth", "gender", "age_preference_min", "country"):
        assert p[key] == body[key]  # untouched


def test_get_and_patch_without_profile(client, token):
    assert_error(client.get(f"{API}/users/me/profile", headers=auth(token)), 404, "PROFILE_NOT_FOUND")
    assert_error(client.patch(f"{API}/users/me/profile", json={"bio": "x"}, headers=auth(token)),
                 404, "PROFILE_NOT_FOUND")


def test_create_twice(client, token):
    assert create_profile(client, token).status_code == 201
    assert_error(create_profile(client, token), 409, "PROFILE_EXISTS")


def test_profile_requires_auth(client):
    assert_error(client.get(f"{API}/users/me/profile"), 401, "NOT_AUTHENTICATED")


def test_under_18_rejected(client, token):
    dob = years_ago(18, days_offset=1).isoformat()  # turns 18 tomorrow
    err = assert_error(create_profile(client, token, date_of_birth=dob), 422, "VALIDATION_ERROR")
    assert "date_of_birth" in err["fields"]


def test_exactly_18_accepted(client, token):
    resp = create_profile(client, token, date_of_birth=years_ago(18).isoformat())
    assert resp.status_code == 201, resp.text
    assert resp.json()["age"] == 18


def test_under_18_rejected_on_patch(client, token):
    create_profile(client, token)
    resp = client.patch(f"{API}/users/me/profile", json={"date_of_birth": years_ago(17).isoformat()},
                        headers=auth(token))
    assert "date_of_birth" in assert_error(resp, 422, "VALIDATION_ERROR")["fields"]


@pytest.mark.parametrize("dob", ["2999-01-01", years_ago(121).isoformat(), "1995/04/02",
                                 "1995-04-02T00:00:00", "02-04-1995", 799372800])
def test_invalid_dates(client, token, dob):
    err = assert_error(create_profile(client, token, date_of_birth=dob), 422, "VALIDATION_ERROR")
    assert "date_of_birth" in err["fields"]


def test_min_greater_than_max_rejected(client, token):
    err = assert_error(create_profile(client, token, age_preference_min=40, age_preference_max=30),
                       422, "VALIDATION_ERROR")
    assert "age_preference_max" in err["fields"]


def test_min_max_checked_against_resulting_values_on_patch(client, token):
    create_profile(client, token)  # 27..38
    resp = client.patch(f"{API}/users/me/profile", json={"age_preference_min": 40}, headers=auth(token))
    assert "age_preference_max" in assert_error(resp, 422, "VALIDATION_ERROR")["fields"]
    ok = client.patch(f"{API}/users/me/profile", json={"age_preference_min": 40, "age_preference_max": 50},
                      headers=auth(token))
    assert ok.status_code == 200 and ok.json()["age_preference_min"] == 40


@pytest.mark.parametrize("field,value", [
    ("age_preference_min", 17), ("age_preference_max", 101), ("first_name", ""), ("first_name", "x" * 51),
    ("bio", "x" * 501), ("city", "x" * 101), ("gender", "robot"), ("relationship_goal", "forever"),
    ("looking_for_gender", []), ("looking_for_gender", ["male", "male"]),
    ("looking_for_gender", ["male", "female", "non_binary", "other", "male"]),
])
def test_field_rules(client, token, field, value):
    err = assert_error(create_profile(client, token, **{field: value}), 422, "VALIDATION_ERROR")
    assert field in err["fields"]


def test_missing_required_field(client, token):
    body = profile_payload()
    del body["gender"]
    resp = client.post(f"{API}/users/me/profile", json=body, headers=auth(token))
    assert "gender" in assert_error(resp, 422, "VALIDATION_ERROR")["fields"]


@pytest.mark.parametrize("extra", [{"user_id": 999}, {"is_profile_complete": False}, {"latitude": 1.0},
                                   {"photos": []}, {"id": 5}])
def test_extra_fields_rejected(client, token, extra):
    err = assert_error(create_profile(client, token, **extra), 422, "VALIDATION_ERROR")
    assert next(iter(extra)) in err["fields"]


@pytest.mark.parametrize("extra", [{"user_id": 999}, {"is_profile_complete": False}, {"longitude": 2.0}])
def test_extra_fields_rejected_on_patch(client, token, db, extra):
    create_profile(client, token)
    resp = client.patch(f"{API}/users/me/profile", json=extra, headers=auth(token))
    assert_error(resp, 422, "VALIDATION_ERROR")
    profile = db.query(UserProfile).one()
    assert profile.user_id == 1 and profile.is_profile_complete is True and profile.longitude is None


def test_patch_null_on_required_field_rejected(client, token):
    create_profile(client, token)
    resp = client.patch(f"{API}/users/me/profile", json={"first_name": None}, headers=auth(token))
    assert "first_name" in assert_error(resp, 422, "VALIDATION_ERROR")["fields"]
    # optional fields may be cleared
    ok = client.patch(f"{API}/users/me/profile", json={"city": None}, headers=auth(token))
    assert ok.status_code == 200 and ok.json()["city"] is None


def test_users_are_isolated(client, db):
    token_a = register(client, "a@example.com")["access_token"]
    token_b = register(client, "b@example.com")["access_token"]
    assert create_profile(client, token_a, first_name="Alice").status_code == 201
    assert create_profile(client, token_b, first_name="Bob", gender="male",
                          looking_for_gender=["female"]).status_code == 201

    assert client.get(f"{API}/users/me/profile", headers=auth(token_a)).json()["first_name"] == "Alice"
    assert client.get(f"{API}/users/me/profile", headers=auth(token_b)).json()["first_name"] == "Bob"

    resp = client.patch(f"{API}/users/me/profile", json={"first_name": "Mallory"}, headers=auth(token_a))
    assert resp.status_code == 200 and resp.json()["first_name"] == "Mallory"
    assert client.get(f"{API}/users/me/profile", headers=auth(token_b)).json()["first_name"] == "Bob"

    # Attempting to target B through the body is rejected (no mass assignment of user_id).
    resp = client.patch(f"{API}/users/me/profile", json={"user_id": 2, "first_name": "Eve"}, headers=auth(token_a))
    assert_error(resp, 422, "VALIDATION_ERROR")
    names = {p.user_id: p.first_name for p in db.query(UserProfile).all()}
    assert names == {1: "Mallory", 2: "Bob"}

    # There is no id-based profile route.
    for path in (f"{API}/users/2/profile", f"{API}/users/2"):
        assert_error(client.get(path, headers=auth(token_a)), 404, "NOT_FOUND")
