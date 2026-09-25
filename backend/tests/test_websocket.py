"""WebSocket consent hot-fix: live sessions only open for matches in `ai_mediation`."""
import pytest
from starlette.websockets import WebSocketDisconnect

from app.ai_moderator import moderator
from app.models import Match, MatchStatus
from helpers import create_profile, register


@pytest.fixture(autouse=True)
def no_real_ai(monkeypatch):
    async def fail(*args, **kwargs):
        raise AssertionError("AI moderator must not be called in these tests")

    for name in ("start_conversation", "process_user_response", "generate_conversation_summary"):
        monkeypatch.setattr(moderator, name, fail)


@pytest.fixture
def pair(client):
    token_a = register(client, "a@example.com")["access_token"]
    token_b = register(client, "b@example.com")["access_token"]
    create_profile(client, token_a, first_name="Alice")
    create_profile(client, token_b, first_name="Bob", gender="male", looking_for_gender=["female"])
    return token_a, token_b


def make_match(db, status):
    match = Match(user1_id=1, user2_id=2, status=status, overall_compatibility=0.8)
    db.add(match)
    db.commit()
    return match.id


def assert_refused(client, match_id, token):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/conversation/{match_id}?token={token}") as ws:
            ws.receive_json()
    assert exc.value.code == 1008


@pytest.mark.parametrize("status", [MatchStatus.PENDING, MatchStatus.ACCEPTED, MatchStatus.REJECTED,
                                    MatchStatus.DIRECT_CHAT, MatchStatus.ENDED])
def test_refused_unless_ai_mediation(client, db, pair, status):
    match_id = make_match(db, status)
    assert_refused(client, match_id, pair[0])


def test_accepted_on_ai_mediation(client, db, pair):
    match_id = make_match(db, MatchStatus.AI_MEDIATION)
    with client.websocket_connect(f"/ws/conversation/{match_id}?token={pair[0]}") as ws:
        first = ws.receive_json()
        assert first["type"] == "user_connected" and first["user_id"] == 1
        state = ws.receive_json()
        assert state["type"] == "session_state" and state["your_user_id"] == 1


def test_refused_for_non_participant(client, db, pair):
    match_id = make_match(db, MatchStatus.AI_MEDIATION)
    token_c = register(client, "c@example.com")["access_token"]
    assert_refused(client, match_id, token_c)


def test_refused_with_refresh_or_bad_token(client, db, pair):
    match_id = make_match(db, MatchStatus.AI_MEDIATION)
    refresh = register(client, "d@example.com")["refresh_token"]
    assert_refused(client, match_id, refresh)
    assert_refused(client, match_id, "garbage")
