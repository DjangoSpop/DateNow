"""Questionnaire endpoints: bank, autosave, server-side scoring, ownership."""
from app import questionnaire
from app.models import OnboardingAnswer, PsychologicalProfile
from helpers import API, assert_error, auth, create_profile, register


def full_answers(scale_value: int = 4) -> dict:
    answers = {}
    for section in questionnaire.get_definition()["sections"]:
        for q in section["questions"]:
            answers[q["id"]] = scale_value if q["type"] == "scale" else q["options"][0]["value"]
    return answers


def put_answers(client, token, answers):
    return client.put(f"{API}/users/me/questionnaire/answers", headers=auth(token), json={"answers": answers})


def test_definition_requires_auth_and_matches_package(client):
    assert_error(client.get(f"{API}/questionnaire"), 401, "NOT_AUTHENTICATED")
    token = register(client)["access_token"]
    resp = client.get(f"{API}/questionnaire", headers=auth(token))
    assert resp.status_code == 200
    assert resp.json() == questionnaire.get_definition()
    assert resp.json()["version"] == questionnaire.QUESTIONNAIRE_VERSION


def test_initial_state(client):
    token = register(client)["access_token"]
    body = client.get(f"{API}/users/me/questionnaire", headers=auth(token)).json()
    assert body["answers"] == {} and body["answered"] == 0 and body["complete"] is False
    assert body["total_required"] == questionnaire.total_required()
    assert body["missing"] == questionnaire.question_ids()
    assert body["scored_at"] is None


def test_autosave_merges_and_replaces(client):
    token = register(client)["access_token"]
    assert put_answers(client, token, {"bf_1": 2, "bf_2": 3}).status_code == 200
    body = put_answers(client, token, {"bf_2": 5, "comm_1": "direct"}).json()
    assert body["answers"] == {"bf_1": 2, "bf_2": 5, "comm_1": "direct"}
    assert body["answered"] == 3
    assert "bf_1" not in body["missing"]


def test_invalid_batch_saves_nothing(client, db):
    token = register(client)["access_token"]
    resp = put_answers(client, token, {"bf_1": 3, "bf_2": 9, "nope": 1, "comm_1": "Direct and straightforward"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert set(err["fields"]) == {"bf_2", "nope", "comm_1"}
    assert db.query(OnboardingAnswer).count() == 0


def test_rejects_empty_and_extra_body(client):
    token = register(client)["access_token"]
    assert_error(put_answers(client, token, {}), 422, "VALIDATION_ERROR")
    resp = client.put(
        f"{API}/users/me/questionnaire/answers", headers=auth(token), json={"answers": {"bf_1": 3}, "scores": {}}
    )
    assert_error(resp, 422, "VALIDATION_ERROR")


def test_submit_incomplete_lists_missing(client):
    token = register(client)["access_token"]
    put_answers(client, token, {"bf_1": 3})
    err = assert_error(client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token)), 422,
                       "QUESTIONNAIRE_INCOMPLETE")
    assert "bf_1" not in err["fields"]
    assert len(err["fields"]) == questionnaire.total_required() - 1
    assert set(err["fields"].values()) == {"required"}


def test_submit_scores_server_side_and_is_idempotent(client, db):
    token = register(client)["access_token"]
    answers = full_answers(4)
    put_answers(client, token, answers)
    resp = client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected = questionnaire.score(answers)
    assert body["big_five"]["openness"] == expected["openness"]
    assert body["values"]["family_orientation"] == expected["family_orientation"]
    assert body["love_languages"]["time"] == expected["love_language_time"]
    assert body["attachment_style"] == expected["attachment_style"]
    assert body["questionnaire_version"] == questionnaire.QUESTIONNAIRE_VERSION and body["scored_at"]

    # Changing answers and resubmitting recomputes in place (one row per user).
    put_answers(client, token, {"bf_37": 1})
    body2 = client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token)).json()
    assert body2["big_five"]["openness"] != body["big_five"]["openness"]
    assert db.query(PsychologicalProfile).count() == 1

    assert client.get(f"{API}/users/me/psychological-profile", headers=auth(token)).json() == body2
    state = client.get(f"{API}/users/me/questionnaire", headers=auth(token)).json()
    assert state["complete"] is True and state["missing"] == []


def test_client_cannot_write_scores(client):
    token = register(client)["access_token"]
    resp = client.post(f"{API}/users/me/psychological-profile", headers=auth(token), json={"openness": 100})
    assert resp.status_code == 405
    resp = client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token), json={"openness": 100})
    assert_error(resp, 422, "QUESTIONNAIRE_INCOMPLETE")  # body ignored; scores only come from stored answers


def test_answers_and_scores_are_per_user(client):
    a = register(client, "a@example.com")["access_token"]
    b = register(client, "b@example.com")["access_token"]
    put_answers(client, a, full_answers(5))
    client.post(f"{API}/users/me/questionnaire/submit", headers=auth(a))
    put_answers(client, b, {"bf_1": 1})

    state_b = client.get(f"{API}/users/me/questionnaire", headers=auth(b)).json()
    assert state_b["answers"] == {"bf_1": 1} and state_b["complete"] is False
    assert_error(client.get(f"{API}/users/me/psychological-profile", headers=auth(b)), 404, "PSYCH_PROFILE_NOT_FOUND")
    state_a = client.get(f"{API}/users/me/questionnaire", headers=auth(a)).json()
    assert state_a["answers"]["bf_1"] == 5


def test_onboarding_flags_follow_the_flow(client):
    token = register(client)["access_token"]
    me = lambda: client.get(f"{API}/users/me", headers=auth(token)).json()["onboarding"]  # noqa: E731
    create_profile(client, token)
    put_answers(client, token, {"bf_1": 3, "bf_2": 3})
    assert me()["questionnaire_answered"] == 2 and me()["complete"] is False
    put_answers(client, token, full_answers())
    client.post(f"{API}/users/me/questionnaire/submit", headers=auth(token))
    status = me()
    assert status["profile_complete"] and status["questionnaire_complete"] and status["complete"]
    assert status["questionnaire_answered"] == questionnaire.total_required()


def test_answers_from_another_version_are_ignored(client, db):
    token = register(client)["access_token"]
    put_answers(client, token, {"bf_1": 3})
    db.query(OnboardingAnswer).update({"questionnaire_version": "old-v0"})
    db.commit()
    body = client.get(f"{API}/users/me/questionnaire", headers=auth(token)).json()
    assert body["answers"] == {}
    assert client.get(f"{API}/users/me", headers=auth(token)).json()["onboarding"]["questionnaire_answered"] == 0
