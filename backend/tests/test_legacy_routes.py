"""Smoke tests: out-of-scope routes keep importing and working after the Sprint 1 changes."""
from app.models import Interest
from helpers import API, assert_error, auth, create_profile, register


def test_matches_list(client):
    token = register(client)["access_token"]
    resp = client.get(f"{API}/matches/", headers=auth(token))
    assert resp.status_code == 200 and resp.json() == []


def test_matches_suggestions_requires_onboarding(client):
    token = register(client)["access_token"]
    resp = client.get(f"{API}/matches/suggestions", headers=auth(token))
    assert_error(resp, 400, "BAD_REQUEST")


def test_interests_flow(client, db):
    db.add_all([Interest(name="music", category="arts"), Interest(name="hiking", category="sports")])
    db.commit()
    token = register(client)["access_token"]
    assert len(client.get(f"{API}/users/interests").json()) == 2
    assert_error(client.get(f"{API}/users/me/interests", headers=auth(token)), 404, "PROFILE_NOT_FOUND")
    create_profile(client, token)
    resp = client.post(f"{API}/users/me/interests", json=[1], headers=auth(token))
    assert resp.status_code == 201, resp.text
    got = client.get(f"{API}/users/me/interests", headers=auth(token))
    assert got.status_code == 200 and [i["name"] for i in got.json()] == ["music"]
