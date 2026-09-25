from datetime import datetime, timezone

import app.routes.users as users_routes
from app.models import OnboardingAnswer, PsychologicalProfile
from app.services.onboarding import questionnaire_meta
from helpers import API, assert_error, auth, create_profile, register


def onboarding(client, token):
    resp = client.get(f"{API}/users/me", headers=auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_me_shape(client):
    token = register(client, "me@example.com")["access_token"]
    body = onboarding(client, token)
    assert set(body) == {"id", "email", "is_verified", "created_at", "onboarding"}
    assert body["id"] == 1 and body["email"] == "me@example.com" and body["is_verified"] is False
    created = datetime.fromisoformat(body["created_at"])
    assert created.utcoffset().total_seconds() == 0  # UTC with offset
    version, total = questionnaire_meta()
    assert body["onboarding"] == {
        "profile_complete": False,
        "questionnaire_complete": False,
        "questionnaire_answered": 0,
        "questionnaire_total": total,
        "questionnaire_version": version,
        "complete": False,
    }


def test_onboarding_flags_progress(client, db):
    token = register(client)["access_token"]
    assert create_profile(client, token).status_code == 201
    ob = onboarding(client, token)["onboarding"]
    assert ob["profile_complete"] is True and ob["complete"] is False

    db.add_all([
        OnboardingAnswer(user_id=1, question_id="bf_1", value=4, questionnaire_version="ipip-v1"),
        OnboardingAnswer(user_id=1, question_id="comm_1", value="direct", questionnaire_version="ipip-v1"),
    ])
    db.commit()
    ob = onboarding(client, token)["onboarding"]
    assert ob["questionnaire_answered"] == 2 and ob["questionnaire_complete"] is False

    db.add(PsychologicalProfile(user_id=1, openness=50.0, questionnaire_version="ipip-v1",
                                scored_at=datetime.now(timezone.utc)))
    db.commit()
    ob = onboarding(client, token)["onboarding"]
    assert ob["questionnaire_complete"] is True and ob["complete"] is True


def test_other_users_answers_not_counted(client, db):
    token_a = register(client, "a@example.com")["access_token"]
    register(client, "b@example.com")
    db.add(OnboardingAnswer(user_id=2, question_id="bf_1", value=3, questionnaire_version="ipip-v1"))
    db.add(PsychologicalProfile(user_id=2))
    db.commit()
    ob = onboarding(client, token_a)["onboarding"]
    assert ob["questionnaire_answered"] == 0 and ob["questionnaire_complete"] is False


def test_psych_profile_not_found(client):
    token = register(client)["access_token"]
    assert_error(client.get(f"{API}/users/me/psychological-profile", headers=auth(token)),
                 404, "PSYCH_PROFILE_NOT_FOUND")


def test_psych_profile_nested_shape(client, db):
    token = register(client)["access_token"]
    db.add(PsychologicalProfile(
        user_id=1, openness=62.5, conscientiousness=71.9, extraversion=40.6, agreeableness=80.0, neuroticism=31.3,
        family_orientation=75.0, career_ambition=50.0, adventure_seeking=75.0, social_consciousness=50.0,
        spiritual_religious=25.0, love_language_words=75.0, love_language_acts=50.0, love_language_gifts=25.0,
        love_language_time=100.0, love_language_touch=50.0, communication_style="direct",
        conflict_resolution="collaborative", attachment_style="secure", questionnaire_version="ipip-v1",
        scored_at=datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc), ai_insights="private",
    ))
    db.commit()
    resp = client.get(f"{API}/users/me/psychological-profile", headers=auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "questionnaire_version": "ipip-v1",
        "scored_at": "2026-09-25T10:00:00Z",
        "big_five": {"openness": 62.5, "conscientiousness": 71.9, "extraversion": 40.6,
                     "agreeableness": 80.0, "neuroticism": 31.3},
        "values": {"family_orientation": 75.0, "career_ambition": 50.0, "adventure_seeking": 75.0,
                   "social_consciousness": 50.0, "spiritual_religious": 25.0},
        "love_languages": {"words": 75.0, "acts": 50.0, "gifts": 25.0, "time": 100.0, "touch": 50.0},
        "communication_style": "direct", "conflict_resolution": "collaborative", "attachment_style": "secure",
    }


def test_post_psych_profile_removed(client):
    token = register(client)["access_token"]
    resp = client.post(f"{API}/users/me/psychological-profile", json={"openness": 100}, headers=auth(token))
    assert_error(resp, 405, "METHOD_NOT_ALLOWED")


def test_profile_routes_do_not_use_ai():
    assert not hasattr(users_routes, "ai_service")
