"""
Authorization / data-isolation regressions: IDOR via parameter smuggling, mass assignment, client-written
psychological scores, and sensitive fields in responses.
"""
import json

import pytest

from app import questionnaire
from app.main import app
from app.models import OnboardingAnswer, PsychologicalProfile, User, UserProfile
from helpers import API, assert_error, auth, create_profile, register

SCORE_FIELDS = {
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "family_orientation", "career_ambition", "adventure_seeking", "social_consciousness", "spiritual_religious",
    "love_language_words", "love_language_acts", "love_language_gifts", "love_language_time", "love_language_touch",
    "communication_style", "conflict_resolution", "attachment_style", "big_five", "values", "love_languages",
    "scores", "scored_at", "questionnaire_version", "ai_insights", "questionnaire_responses",
}
# Keys that must never appear anywhere in a response body or response schema.
FORBIDDEN_RESPONSE_KEYS = {
    "hashed_password", "password", "latitude", "longitude", "questionnaire_responses", "ai_insights",
}
SERVER_OWNED_PROFILE_FIELDS = {
    "id": 999, "user_id": 2, "is_profile_complete": False, "latitude": 1.5, "longitude": 2.5,
    "photos": ["x"], "profile_photo_url": "http://evil", "height_cm": 180, "distance_preference_km": 5,
    "created_at": "2000-01-01T00:00:00Z", "updated_at": "2000-01-01T00:00:00Z", "age": 99,
}


def full_answers(scale_value: int = 4) -> dict:
    answers = {}
    for section in questionnaire.get_definition()["sections"]:
        for q in section["questions"]:
            answers[q["id"]] = scale_value if q["type"] == "scale" else q["options"][0]["value"]
    return answers


def onboard(client, email: str, first_name: str, scale_value: int) -> tuple[str, int]:
    token = register(client, email)["access_token"]
    assert create_profile(client, token, first_name=first_name, city=f"{first_name}-city").status_code == 201
    resp = client.put(f"{API}/users/me/questionnaire/answers", headers=auth(token),
                      json={"answers": full_answers(scale_value)})
    assert resp.status_code == 200, resp.text
    assert client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token)).status_code == 200
    user_id = client.get(f"{API}/users/me", headers=auth(token)).json()["id"]
    return token, user_id


@pytest.fixture
def victim(client):
    """User B: fully onboarded. Returns (token, id, snapshot of B's readable state)."""
    token, uid = onboard(client, "victim@example.com", "Victim", scale_value=5)
    snapshot = {
        "profile": client.get(f"{API}/users/me/profile", headers=auth(token)).json(),
        "questionnaire": client.get(f"{API}/users/me/questionnaire", headers=auth(token)).json(),
        "psych": client.get(f"{API}/users/me/psychological-profile", headers=auth(token)).json(),
    }
    return token, uid, snapshot


@pytest.fixture
def attacker(client):
    return register(client, "attacker@example.com")["access_token"]


def assert_victim_unchanged(client, victim):
    token, _, snapshot = victim
    assert client.get(f"{API}/users/me/profile", headers=auth(token)).json() == snapshot["profile"]
    assert client.get(f"{API}/users/me/questionnaire", headers=auth(token)).json() == snapshot["questionnaire"]
    assert client.get(f"{API}/users/me/psychological-profile", headers=auth(token)).json() == snapshot["psych"]


def _leaks_victim(resp) -> bool:
    return "Victim" in resp.text or "victim@example.com" in resp.text


# --------------------------------------------------------------------------- IDOR: reads

@pytest.mark.parametrize("path", [
    "/users/me", "/users/me/profile", "/users/me/questionnaire", "/users/me/psychological-profile",
])
@pytest.mark.parametrize("smuggle", [
    "?user_id={id}", "?id={id}", "?uid={id}", "?user={id}", "?sub={id}", "?user_id={id}&user_id={id}",
])
def test_read_endpoints_ignore_user_id_query(client, victim, attacker, path, smuggle):
    _, vid, _ = victim
    resp = client.get(f"{API}{path}{smuggle.format(id=vid)}", headers=auth(attacker))
    assert resp.status_code in (200, 404), resp.text
    assert not _leaks_victim(resp)
    if path == "/users/me":
        assert resp.json()["id"] != vid


@pytest.mark.parametrize("header", ["X-User-Id", "X-Forwarded-User", "X-Original-User"])
def test_read_endpoints_ignore_identity_headers(client, victim, attacker, header):
    _, vid, _ = victim
    for path in ("/users/me", "/users/me/profile", "/users/me/psychological-profile"):
        resp = client.get(f"{API}{path}", headers={**auth(attacker), header: str(vid)})
        assert not _leaks_victim(resp), path


@pytest.mark.parametrize("path", [
    "/users/{id}", "/users/{id}/profile", "/users/{id}/questionnaire", "/users/{id}/psychological-profile",
    "/profiles/{id}", "/users/me/profile/{id}", "/psychological-profile/{id}",
])
def test_no_path_that_reads_another_user(client, victim, attacker, path):
    _, vid, _ = victim
    resp = client.get(f"{API}{path.format(id=vid)}", headers=auth(attacker))
    assert resp.status_code in (404, 405), resp.text
    assert not _leaks_victim(resp)


# --------------------------------------------------------------------------- IDOR: writes / mass assignment

@pytest.mark.parametrize("field,value", sorted(SERVER_OWNED_PROFILE_FIELDS.items()))
def test_profile_patch_rejects_server_owned_fields(client, victim, field, value):
    token, vid, _ = victim
    resp = client.patch(f"{API}/users/me/profile", headers=auth(token), json={field: value, "first_name": "Changed"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert field in err["fields"]
    assert_victim_unchanged(client, victim)


@pytest.mark.parametrize("field,value", sorted(SERVER_OWNED_PROFILE_FIELDS.items()))
def test_profile_create_rejects_server_owned_fields(client, attacker, field, value):
    from helpers import profile_payload
    resp = client.post(f"{API}/users/me/profile", headers=auth(attacker), json={**profile_payload(), field: value})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert field in err["fields"]


def test_attacker_patch_with_victim_user_id_does_not_touch_victim(client, victim, attacker, db):
    _, vid, _ = victim
    assert create_profile(client, attacker, first_name="Mallory").status_code == 201
    for body in ({"user_id": vid, "first_name": "Pwned"}, {"id": vid, "first_name": "Pwned"}):
        assert_error(client.patch(f"{API}/users/me/profile", headers=auth(attacker), json=body), 422,
                     "VALIDATION_ERROR")
    # Query-string smuggling: accepted, but applies to the caller only.
    resp = client.patch(f"{API}/users/me/profile?user_id={vid}", headers=auth(attacker), json={"first_name": "Pwned"})
    assert resp.status_code == 200 and resp.json()["first_name"] == "Pwned"
    assert_victim_unchanged(client, victim)
    assert db.query(UserProfile).filter(UserProfile.first_name == "Pwned").one().user_id != vid


def test_attacker_answers_cannot_target_victim(client, victim, attacker, db):
    _, vid, _ = victim
    before = {(r.question_id, json.dumps(r.value)) for r in db.query(OnboardingAnswer).filter_by(user_id=vid)}
    url = f"{API}/users/me/questionnaire/answers"
    assert_error(client.put(url, headers=auth(attacker), json={"answers": {"bf_1": 1}, "user_id": vid}), 422,
                 "VALIDATION_ERROR")
    resp = client.put(f"{url}?user_id={vid}", headers=auth(attacker), json={"answers": {"bf_1": 1}})
    assert resp.status_code == 200 and resp.json()["answers"] == {"bf_1": 1}
    # An answer id that looks like a scoped key is just an unknown question id.
    assert_error(client.put(url, headers=auth(attacker), json={"answers": {f"{vid}.bf_1": 1}}), 422,
                 "VALIDATION_ERROR")
    db.expire_all()
    after = {(r.question_id, json.dumps(r.value)) for r in db.query(OnboardingAnswer).filter_by(user_id=vid)}
    assert before == after
    assert_victim_unchanged(client, victim)


def test_attacker_submit_does_not_rescore_victim(client, victim, attacker):
    _, vid, _ = victim
    resp = client.post(f"{API}/users/me/questionnaire/submit?user_id={vid}", headers=auth(attacker),
                       json={"user_id": vid})
    assert_error(resp, 422, "QUESTIONNAIRE_INCOMPLETE")
    assert_victim_unchanged(client, victim)


def test_register_ignores_privileged_fields(client, db):
    resp = client.post(f"{API}/auth/register", json={
        "email": "new@example.com", "password": "correct-horse-battery",
        "id": 777, "is_active": False, "is_verified": True, "is_admin": True, "hashed_password": "x",
        "openness": 100, "created_at": "2000-01-01T00:00:00Z",
    })
    assert resp.status_code == 201
    user = db.query(User).filter_by(email="new@example.com").one()
    assert user.id != 777 and user.is_active is True and user.is_verified is False
    assert user.hashed_password != "x"
    assert db.query(PsychologicalProfile).count() == 0


# --------------------------------------------------------------------------- psych scores are server-only

@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_psych_profile_has_no_write_route(client, attacker, method):
    body = {"big_five": {"openness": 100}, "openness": 100}
    resp = client.request(method, f"{API}/users/me/psychological-profile", headers=auth(attacker), json=body)
    assert_error(resp, 405, "METHOD_NOT_ALLOWED")


@pytest.mark.parametrize("field", sorted(SCORE_FIELDS))
def test_scores_cannot_be_smuggled_into_writes(client, attacker, db, field):
    assert_error(client.put(f"{API}/users/me/questionnaire/answers", headers=auth(attacker),
                            json={"answers": {"bf_1": 3}, field: 100}), 422, "VALIDATION_ERROR")
    assert_error(client.put(f"{API}/users/me/questionnaire/answers", headers=auth(attacker),
                            json={"answers": {field: 100}}), 422, "VALIDATION_ERROR")
    assert_error(client.patch(f"{API}/users/me/profile", headers=auth(attacker), json={field: 100}), 422,
                 "VALIDATION_ERROR")
    assert db.query(PsychologicalProfile).count() == 0


def test_submit_ignores_client_supplied_scores(client, attacker):
    ok = client.put(f"{API}/users/me/questionnaire/answers", headers=auth(attacker), json={"answers": full_answers(3)})
    assert ok.status_code == 200
    resp = client.post(f"{API}/users/me/questionnaire/submit", headers=auth(attacker),
                       json={"big_five": {"openness": 100.0}, "openness": 100.0, "attachment_style": "evil"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["big_five"]["openness"] == 50.0  # all-neutral answers score the midpoint
    assert body["attachment_style"] != "evil"


def test_no_request_schema_accepts_score_fields():
    """No request body in the OpenAPI document declares a score / server-owned psych field."""
    spec = app.openapi()
    schemas = spec["components"]["schemas"]
    offenders = []
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            ref = (op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
                   .get("$ref"))
            if not ref:
                continue
            props = set(schemas[ref.rsplit("/", 1)[1]].get("properties", {}))
            if props & SCORE_FIELDS:
                offenders.append((method.upper(), path, sorted(props & SCORE_FIELDS)))
    assert offenders == []


# --------------------------------------------------------------------------- sensitive data in responses

def _keys(obj) -> set:
    if isinstance(obj, dict):
        out = set(obj)
        for v in obj.values():
            out |= _keys(v)
        return out
    if isinstance(obj, list):
        out = set()
        for v in obj:
            out |= _keys(v)
        return out
    return set()


def test_no_response_schema_declares_sensitive_fields():
    spec = app.openapi()
    offenders = {
        name: sorted(set(schema.get("properties", {})) & FORBIDDEN_RESPONSE_KEYS)
        for name, schema in spec["components"]["schemas"].items()
        if set(schema.get("properties", {})) & FORBIDDEN_RESPONSE_KEYS
    }
    # Request-only schemas legitimately carry a password.
    offenders.pop("UserRegister", None)
    offenders.pop("UserLogin", None)
    assert offenders == {}


def test_live_responses_never_contain_sensitive_fields(client, victim, db):
    token, vid, _ = victim
    # Populate the server-owned columns that must never be returned.
    db.query(UserProfile).filter_by(user_id=vid).update({"latitude": 30.0444, "longitude": 31.2357})
    db.query(PsychologicalProfile).filter_by(user_id=vid).update(
        {"ai_insights": "PRIVATE-INSIGHT", "questionnaire_responses": {"secret": "PRIVATE-RESPONSE"}}
    )
    db.commit()
    hashed = db.get(User, vid).hashed_password
    calls = [
        ("GET", "/users/me", None), ("GET", "/users/me/profile", None),
        ("PATCH", "/users/me/profile", {"bio": "hello"}), ("GET", "/questionnaire", None),
        ("GET", "/users/me/questionnaire", None), ("PUT", "/users/me/questionnaire/answers", {"answers": {"bf_1": 5}}),
        ("GET", "/users/me/psychological-profile", None), ("GET", "/users/me/interests", None),
        ("GET", "/matches/", None),
    ]
    for method, path, body in calls:
        resp = client.request(method, f"{API}{path}", headers=auth(token), json=body)
        assert resp.status_code == 200, (path, resp.text)
        assert not (_keys(resp.json()) & FORBIDDEN_RESPONSE_KEYS), path
        for needle in (hashed, "30.0444", "31.2357", "PRIVATE-INSIGHT", "PRIVATE-RESPONSE"):
            assert needle not in resp.text, (path, needle)
    for path in ("/auth/login", "/auth/register"):
        resp = client.post(f"{API}{path}", json={"email": "victim@example.com", "password": "correct-horse-battery"})
        assert hashed not in resp.text and "hashed_password" not in resp.text


def test_submit_response_has_no_ai_insights(client, attacker):
    client.put(f"{API}/users/me/questionnaire/answers", headers=auth(attacker), json={"answers": full_answers(2)})
    resp = client.post(f"{API}/users/me/questionnaire/submit", headers=auth(attacker))
    assert resp.status_code == 200
    assert not (_keys(resp.json()) & FORBIDDEN_RESPONSE_KEYS)
