"""/questionnaire, /onboarding and /questionnaire/submit: server-side scoring and ownership."""
import json

import pytest

from app.models import OnboardingProgress, PsychologicalProfile
from app.questionnaire_catalog import QUESTIONNAIRE_VERSION, QUESTIONS, REQUIRED_QUESTION_IDS
from conftest import API
from unit.test_questionnaire_processor import FIXTURE, FIXTURE_EXPECTED

QUESTIONNAIRE = f"{API}/questionnaire"
ONBOARDING = f"{API}/onboarding"
SUBMIT = f"{API}/questionnaire/submit"
PSYCH = f"{API}/users/me/psychological-profile"
ME = f"{API}/auth/me"


@pytest.fixture()
def user_headers(make_user, auth_headers):
    return auth_headers(make_user())


def _ids(response):
    return {e["question_id"] for e in response.json()["detail"]}


# --- auth required -----------------------------------------------------------------

@pytest.mark.parametrize("method,url", [
    ("get", QUESTIONNAIRE), ("get", ONBOARDING), ("put", ONBOARDING), ("post", SUBMIT),
])
def test_requires_auth(client, method, url):
    r = client.request(method.upper(), url, json=None if method == "get" else {"answers": {}})
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


# --- catalog -----------------------------------------------------------------------

def test_questionnaire_definition(client, user_headers):
    r = client.get(QUESTIONNAIRE, headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == QUESTIONNAIRE_VERSION
    ids = [q["id"] for s in body["sections"] for q in s["questions"]]
    assert set(ids) == set(QUESTIONS)
    text = json.dumps(body)
    for leaked in ("reverse", "trait", "ipip", "role"):
        assert f'"{leaked}' not in text


# --- drafts ------------------------------------------------------------------------

def test_onboarding_default_state(client, user_headers):
    r = client.get(ONBOARDING, headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_started"
    assert body["answers"] == {}
    assert body["completed_at"] is None


def test_draft_merge_and_resume(client, user_headers):
    r1 = client.put(ONBOARDING, headers=user_headers,
                    json={"current_section": "personality", "answers": {"bf_1": 4}})
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "in_progress"
    r2 = client.put(ONBOARDING, headers=user_headers,
                    json={"current_section": "values", "answers": {"val_1": 5, "bf_1": 2}})
    assert r2.status_code == 200
    state = client.get(ONBOARDING, headers=user_headers).json()
    assert state["answers"] == {"bf_1": 2, "val_1": 5}
    assert state["current_section"] == "values"
    assert state["questionnaire_version"] == QUESTIONNAIRE_VERSION
    me = client.get(ME, headers=user_headers).json()
    assert me["onboarding_status"] == "in_progress"


def test_draft_null_removes_answer(client, user_headers):
    client.put(ONBOARDING, headers=user_headers, json={"answers": {"bf_1": 4, "bf_2": 3}})
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": {"bf_1": None}})
    assert r.status_code == 200
    assert r.json()["answers"] == {"bf_2": 3}


def test_draft_null_for_unknown_id_rejected(client, user_headers):
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": {"zz_999": None}})
    assert r.status_code == 422
    assert _ids(r) == {"zz_999"}


@pytest.mark.parametrize("answers,bad", [
    ({"zz_999": 3}, {"zz_999"}),
    ({"bf_1": 6}, {"bf_1"}),
    ({"bf_1": 0}, {"bf_1"}),
    ({"bf_1": "x"}, {"bf_1"}),
    ({"bf_1": True}, {"bf_1"}),
    ({"bf_1": 3.5}, {"bf_1"}),
    ({"comm_1": "Not an option"}, {"comm_1"}),
    ({"verify_1": "x" * 1001}, {"verify_1"}),
    ({"bf_1": 9, "bf_2": 3, "comm_1": "nope"}, {"bf_1", "comm_1"}),
])
def test_draft_invalid_answers(client, user_headers, answers, bad):
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": answers})
    assert r.status_code == 422
    assert _ids(r) == bad
    # Nothing was persisted.
    assert client.get(ONBOARDING, headers=user_headers).json()["status"] == "not_started"


def test_draft_unknown_section_rejected(client, user_headers):
    r = client.put(ONBOARDING, headers=user_headers, json={"current_section": "nope", "answers": {}})
    assert r.status_code == 422


@pytest.mark.parametrize("extra", [{"status": "completed"}, {"completed_at": "2026-01-01T00:00:00Z"}])
def test_draft_server_fields_forbidden(client, user_headers, extra):
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": {}, **extra})
    assert r.status_code == 422
    assert client.get(ONBOARDING, headers=user_headers).json()["status"] == "not_started"


def test_draft_oversized_payload(client, user_headers):
    answers = {f"k{i}": 1 for i in range(10_000)}
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": answers})
    assert r.status_code == 422
    assert _ids(r) == {"__all__"}


def test_draft_isolation(client, make_user, auth_headers):
    a, b = make_user(), make_user()
    client.put(ONBOARDING, headers=auth_headers(a), json={"answers": {"bf_1": 5}})
    state_b = client.get(ONBOARDING, headers=auth_headers(b)).json()
    assert state_b["status"] == "not_started" and state_b["answers"] == {}


# --- submit ------------------------------------------------------------------------

def test_submit_scores_server_side(client, db, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)
    r = client.post(SUBMIT, headers=headers, json={"answers": FIXTURE})
    assert r.status_code == 201, r.text
    body = r.json()
    for key, expected in FIXTURE_EXPECTED.items():
        assert body[key] == expected, key
    assert body["questionnaire_version"] == QUESTIONNAIRE_VERSION
    assert "questionnaire_responses" not in body and "ai_insights" not in body

    # Persisted and readable; onboarding completed.
    assert client.get(PSYCH, headers=headers).json()["openness"] == FIXTURE_EXPECTED["openness"]
    state = client.get(ONBOARDING, headers=headers).json()
    assert state["status"] == "completed" and state["completed_at"] is not None
    assert client.get(ME, headers=headers).json()["onboarding_status"] == "completed"
    stored = db.query(PsychologicalProfile).filter_by(user_id=user.id).one()
    assert stored.questionnaire_responses["bf_1"] == FIXTURE["bf_1"]


def test_submit_merges_saved_draft(client, user_headers):
    half = dict(list(FIXTURE.items())[:40])
    rest = dict(list(FIXTURE.items())[40:])
    assert client.put(ONBOARDING, headers=user_headers, json={"answers": half}).status_code == 200
    r = client.post(SUBMIT, headers=user_headers, json={"answers": rest})
    assert r.status_code == 201, r.text
    assert r.json()["extraversion"] == FIXTURE_EXPECTED["extraversion"]


def test_submit_missing_required_lists_ids(client, user_headers):
    answers = dict(FIXTURE)
    for qid in ("bf_3", "val_2", "verify_1"):
        answers.pop(qid)
    r = client.post(SUBMIT, headers=user_headers, json={"answers": answers})
    assert r.status_code == 422
    assert _ids(r) == {"bf_3", "val_2", "verify_1"}
    assert client.get(PSYCH, headers=user_headers).status_code == 404


def test_submit_empty_lists_every_required_id(client, user_headers):
    r = client.post(SUBMIT, headers=user_headers, json={"answers": {}})
    assert r.status_code == 422
    assert _ids(r) == set(REQUIRED_QUESTION_IDS)


def test_submit_blank_text_counts_as_missing(client, user_headers):
    r = client.post(SUBMIT, headers=user_headers, json={"answers": {**FIXTURE, "verify_2": "   "}})
    assert r.status_code == 422
    assert "verify_2" in _ids(r)


def test_submit_unknown_id_rejected(client, user_headers):
    r = client.post(SUBMIT, headers=user_headers, json={"answers": {**FIXTURE, "zz_1": 3}})
    assert r.status_code == 422
    assert _ids(r) == {"zz_1"}


@pytest.mark.parametrize("extra", [
    {"openness": 99},
    {"attachment_style": "secure"},
    {"questionnaire_version": "hacked"},
])
def test_submit_client_scores_rejected_at_top_level(client, user_headers, extra):
    r = client.post(SUBMIT, headers=user_headers, json={"answers": FIXTURE, **extra})
    assert r.status_code == 422
    assert client.get(PSYCH, headers=user_headers).status_code == 404


def test_submit_client_scores_rejected_inside_answers(client, user_headers):
    r = client.post(SUBMIT, headers=user_headers, json={"answers": {**FIXTURE, "openness": 99}})
    assert r.status_code == 422
    assert _ids(r) == {"openness"}


def test_submit_twice_conflict_and_draft_locked(client, user_headers):
    assert client.post(SUBMIT, headers=user_headers, json={"answers": FIXTURE}).status_code == 201
    assert client.post(SUBMIT, headers=user_headers, json={"answers": FIXTURE}).status_code == 409
    r = client.put(ONBOARDING, headers=user_headers, json={"answers": {"bf_1": 1}})
    assert r.status_code == 409


def test_submit_reproducible_across_users(client, make_user, auth_headers):
    a = client.post(SUBMIT, headers=auth_headers(make_user()), json={"answers": FIXTURE}).json()
    b = client.post(SUBMIT, headers=auth_headers(make_user()), json={"answers": FIXTURE}).json()
    strip = lambda d: {k: v for k, v in d.items() if k not in ("created_at", "updated_at")}
    assert strip(a) == strip(b)


def test_psych_profile_isolation(client, make_user, auth_headers):
    a, b = make_user(), make_user()
    assert client.post(SUBMIT, headers=auth_headers(a), json={"answers": FIXTURE}).status_code == 201
    assert client.get(PSYCH, headers=auth_headers(b)).status_code == 404


def test_progress_row_deleted_with_user(client, db, make_user, auth_headers):
    user = make_user()
    client.put(ONBOARDING, headers=auth_headers(user), json={"answers": {"bf_1": 4}})
    db.delete(user)
    db.commit()
    assert db.query(OnboardingProgress).count() == 0
