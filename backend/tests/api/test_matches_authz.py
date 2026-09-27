"""Matches: non-participants cannot read or act on someone else's match (IDOR)."""
import pytest

from app.models import AISession, AISessionStatus, Match, MatchStatus
from conftest import API


@pytest.fixture()
def match_setup(db, make_user, auth_headers):
    a, b, outsider = make_user(), make_user(), make_user()
    match = Match(user1_id=a.id, user2_id=b.id, status=MatchStatus.PENDING,
                  overall_compatibility=0.8, personality_compatibility=0.8,
                  values_compatibility=0.8, interests_compatibility=0.8,
                  lifestyle_compatibility=0.8)
    db.add(match)
    db.commit()
    db.add(AISession(match_id=match.id, user_id=a.id, status=AISessionStatus.ACTIVE,
                     session_data={"qa_pairs": []}))
    db.commit()
    return {"a": a, "b": b, "outsider": outsider, "match_id": match.id,
            "ha": auth_headers(a), "ho": auth_headers(outsider)}


def test_participant_can_view_match(client, match_setup):
    r = client.get(f"{API}/matches/{match_setup['match_id']}", headers=match_setup["ha"])
    assert r.status_code == 200


def test_outsider_cannot_view_match(client, match_setup):
    r = client.get(f"{API}/matches/{match_setup['match_id']}", headers=match_setup["ho"])
    assert r.status_code == 404


def test_outsider_cannot_act_on_match(client, db, match_setup):
    mid = match_setup["match_id"]
    r = client.post(f"{API}/matches/{mid}/action", json={"action": "reject"}, headers=match_setup["ho"])
    assert r.status_code == 404
    db.expire_all()
    assert db.get(Match, mid).status == MatchStatus.PENDING


def test_outsider_cannot_access_ai_session(client, match_setup):
    mid = match_setup["match_id"]
    ho = match_setup["ho"]
    assert client.get(f"{API}/matches/{mid}/ai-session", headers=ho).status_code == 404
    assert client.post(f"{API}/matches/{mid}/ai-session/question", headers=ho).status_code == 404
    r = client.post(f"{API}/matches/{mid}/ai-session/response", headers=ho,
                    json={"session_id": 1, "question": "q", "answer": "a"})
    assert r.status_code == 404


def test_outsider_match_list_is_empty(client, match_setup):
    r = client.get(f"{API}/matches/", headers=match_setup["ho"])
    assert r.status_code == 200 and r.json() == []


def test_repeated_accept_does_not_duplicate_ai_sessions(client, db, make_user, auth_headers):
    a, b = make_user(), make_user()
    m = Match(user1_id=a.id, user2_id=b.id, status=MatchStatus.PENDING,
              overall_compatibility=0.9, personality_compatibility=0.9,
              values_compatibility=0.9, interests_compatibility=0.9,
              lifestyle_compatibility=0.9)
    db.add(m)
    db.commit()
    for user in (a, b, a, b):
        r = client.post(f"{API}/matches/{m.id}/action", json={"action": "accept"},
                        headers=auth_headers(user))
        assert r.status_code == 200, r.text
    assert db.query(AISession).filter(AISession.match_id == m.id).count() == 2


def test_suggestions_query_runs_without_ai_key(client, db, make_user, auth_headers, profile_payload):
    """Smoke test: enum-valued gender filter works on this backend; no Gemini key needed."""
    from app.models import PsychologicalProfile

    a, b = make_user(), make_user()
    client.post(f"{API}/users/me/profile", headers=auth_headers(a),
                json=profile_payload(gender="female", looking_for_gender=["male"]))
    client.post(f"{API}/users/me/profile", headers=auth_headers(b),
                json=profile_payload(first_name="Bob", gender="male", looking_for_gender=["female"]))
    traits = dict(openness=50, conscientiousness=50, extraversion=50, agreeableness=50,
                  neuroticism=50, family_orientation=50, career_ambition=50,
                  adventure_seeking=50, social_consciousness=50, spiritual_religious=50)
    db.add_all([PsychologicalProfile(user_id=a.id, **traits),
                PsychologicalProfile(user_id=b.id, **traits)])
    db.commit()
    r = client.get(f"{API}/matches/suggestions", headers=auth_headers(a))
    assert r.status_code == 200, r.text
    assert all(m["user2_id"] == b.id for m in r.json())
