"""/users/me/psychological-profile: GET only; client-computed scores cannot be posted."""
from app.models import PsychologicalProfile
from conftest import API

PSYCH = f"{API}/users/me/psychological-profile"

CONTRACT_FIELDS = {
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "family_orientation", "career_ambition", "adventure_seeking", "social_consciousness",
    "spiritual_religious", "communication_style", "conflict_resolution",
    "love_language_words", "love_language_acts", "love_language_gifts",
    "love_language_time", "love_language_touch", "attachment_style",
    "questionnaire_version", "created_at", "updated_at",
}


def test_get_psych_profile_404_when_missing(client, make_user, auth_headers):
    user = make_user()
    assert client.get(PSYCH, headers=auth_headers(user)).status_code == 404


def test_get_psych_profile_returns_contract_fields_only(client, db, make_user, auth_headers):
    user = make_user()
    db.add(PsychologicalProfile(
        user_id=user.id, openness=70, conscientiousness=60, extraversion=50,
        agreeableness=40, neuroticism=30, communication_style="direct",
        attachment_style="secure", questionnaire_version="2026.1",
        questionnaire_responses={"bf_1": 5}, ai_insights="secret insight text",
    ))
    db.commit()
    r = client.get(PSYCH, headers=auth_headers(user))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == CONTRACT_FIELDS
    assert body["openness"] == 70 and body["questionnaire_version"] == "2026.1"
    assert "secret insight text" not in r.text
    assert "questionnaire_responses" not in body and "ai_insights" not in body


def test_post_psych_profile_route_removed(client, db, make_user, auth_headers):
    user = make_user()
    payload = {k: 50 for k in ("openness", "conscientiousness", "extraversion",
                               "agreeableness", "neuroticism")}
    r = client.post(PSYCH, json=payload, headers=auth_headers(user))
    assert r.status_code == 405
    assert db.query(PsychologicalProfile).count() == 0
