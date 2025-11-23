"""
WebSocket routes for real-time AI-moderated conversations
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json
import asyncio
from datetime import datetime

from app.database import get_db
from app.models import User, Match, UserProfile, PsychologicalProfile, MatchStatus
from app.websocket_manager import manager
from app.ai_moderator import moderator
from app.conversation_session import (
    session_manager,
    SessionStage,
    MessageType,
    ConversationSession
)
from app.auth import decode_token


router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Get user from JWT token"""
    try:
        token_data = decode_token(token)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user
    except:
        return None


@router.websocket("/conversation/{match_id}")
async def conversation_websocket(
    websocket: WebSocket,
    match_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for AI-moderated conversations

    Flow:
    1. User connects with token
    2. Join or create conversation session
    3. When both users ready, AI moderator starts
    4. AI asks questions alternately to each user
    5. Users respond in real-time
    6. After 10 questions, users decide yes/no
    7. Session ends
    """

    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify match exists and user is part of it
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if user.id not in [match.user1_id, match.user2_id]:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Get user profiles
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
    other_user = db.query(User).filter(User.id == other_user_id).first()
    other_profile = db.query(UserProfile).filter(UserProfile.user_id == other_user_id).first()

    # Get or create session
    session = session_manager.get_user_session(user.id)
    if not session:
        session = session_manager.create_session(
            match_id=match.id,
            user1_id=match.user1_id,
            user2_id=match.user2_id,
            user1_name=user_profile.first_name if user.id == match.user1_id else other_profile.first_name,
            user2_name=other_profile.first_name if user.id == match.user1_id else user_profile.first_name,
            compatibility_score=match.overall_compatibility
        )

    session_id = session.session_id

    # Connect to WebSocket
    await manager.connect(websocket, user.id, session_id)

    # Mark user as connected
    if user.id == session.user1_id:
        session.user1_connected = True
    else:
        session.user2_connected = True

    # Notify session
    await manager.broadcast_to_session({
        'type': 'user_connected',
        'user_id': user.id,
        'user_name': user_profile.first_name,
        'session': session.to_dict()
    }, session_id)

    try:
        # Send initial state to connected user
        await manager.send_personal_message({
            'type': 'session_state',
            'session': session.to_dict(),
            'messages': session.get_messages_for_user(user.id),
            'your_user_id': user.id
        }, user.id)

        # Main message loop
        while True:
            # Receive message from user
            data = await websocket.receive_json()
            message_type = data.get('type')

            # Handle different message types
            if message_type == 'ready':
                # User is ready to start
                if user.id == session.user1_id:
                    session.user1_ready = True
                else:
                    session.user2_ready = True

                await manager.broadcast_to_session({
                    'type': 'user_ready',
                    'user_id': user.id,
                    'user_name': user_profile.first_name
                }, session_id)

                # Start session if both ready
                if session.can_start():
                    await start_conversation_session(session, match, user, other_user, user_profile, other_profile, db)

            elif message_type == 'message':
                # User response to AI question
                content = data.get('content', '').strip()
                if not content:
                    continue

                # Add user message to session
                message = session.add_message(
                    MessageType.USER_RESPONSE,
                    content,
                    sender_id=user.id,
                    sender_name=user_profile.first_name
                )

                # Broadcast to session
                await manager.broadcast_to_session({
                    'type': 'message',
                    'message': message.to_dict()
                }, session_id)

                # Get AI moderator response
                await process_ai_response(session, user, other_user, user_profile, other_profile, db)

            elif message_type == 'typing':
                # Typing indicator
                await manager.send_to_session({
                    'type': 'typing',
                    'user_id': user.id,
                    'user_name': user_profile.first_name
                }, session_id, exclude_user=user.id)

            elif message_type == 'decision':
                # Final yes/no decision
                decision = data.get('decision')  # True or False
                session.mark_decision(user.id, decision)

                await manager.send_personal_message({
                    'type': 'decision_recorded',
                    'your_decision': decision
                }, user.id)

                # If both decided, end session
                if session.both_decided():
                    await end_conversation_session(session, match, db)

    except WebSocketDisconnect:
        manager.disconnect(user.id)

        # Mark as disconnected
        if user.id == session.user1_id:
            session.user1_connected = False
        else:
            session.user2_connected = False

        await manager.broadcast_to_session({
            'type': 'user_disconnected',
            'user_id': user.id,
            'user_name': user_profile.first_name
        }, session_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user.id)


async def start_conversation_session(
    session: ConversationSession,
    match: Match,
    user1: User,
    user2: User,
    user1_profile: UserProfile,
    user2_profile: UserProfile,
    db: Session
):
    """Start the AI-moderated conversation"""
    session.stage = SessionStage.OPENING
    session.started_at = datetime.utcnow()

    # Generate AI opening
    opening = await moderator.start_conversation(
        match, user1, user2, user1_profile, user2_profile, db
    )

    # Add opening message
    message = session.add_message(
        MessageType.MODERATOR_GREETING,
        opening,
        sender_name="AI Moderator"
    )

    # Broadcast opening
    await manager.broadcast_to_session({
        'type': 'conversation_started',
        'message': message.to_dict(),
        'session': session.to_dict()
    }, session.session_id)

    # Move to active stage
    session.stage = SessionStage.ACTIVE
    session.questions_asked += 1


async def process_ai_response(
    session: ConversationSession,
    responding_user: User,
    other_user: User,
    responding_profile: UserProfile,
    other_profile: UserProfile,
    db: Session
):
    """Process user response and generate AI moderator response"""

    # Get conversation history
    history = [
        {
            'role': 'moderator' if m.sender_id is None else 'user',
            'content': m.content,
            'user_name': m.sender_name
        }
        for m in session.messages
    ]

    # Get last user response
    last_response = session.messages[-1].content

    # Check if should wrap up
    if session.should_wrap_up():
        session.stage = SessionStage.WRAPPING_UP
        await wrap_up_conversation(session, db)
        return

    # Generate AI response
    ai_response = await moderator.process_user_response(
        last_response,
        responding_profile.first_name,
        other_profile.first_name,
        history,
        {'questions_count': session.questions_asked, 'stage': session.stage.value},
        db
    )

    # Add AI message
    message = session.add_message(
        MessageType.MODERATOR_QUESTION,
        ai_response,
        sender_name="AI Moderator"
    )

    # Broadcast AI response
    await manager.broadcast_to_session({
        'type': 'message',
        'message': message.to_dict()
    }, session.session_id)

    session.questions_asked += 1


async def wrap_up_conversation(session: ConversationSession, db: Session):
    """Wrap up conversation and request decisions"""

    # Generate summary
    history = [
        {
            'content': m.content,
            'user_name': m.sender_name
        }
        for m in session.messages
    ]

    summary = await moderator.generate_conversation_summary(
        history,
        session.user1_name,
        session.user2_name,
        session.compatibility_score,
        db
    )

    # Add summary message
    summary_text = f"""Thank you both for this wonderful conversation!

Based on our discussion, I've observed:

✨ Key Connections:
{chr(10).join(f'• {conn}' for conn in summary['key_connections'])}

💭 Things to Consider:
{chr(10).join(f'• {chal}' for chal in summary['potential_challenges'])}

🎯 My Recommendation: {summary['recommendation'].title()}

Now it's time for you both to decide if you'd like to continue getting to know each other. Take a moment to reflect, then let me know your decision."""

    message = session.add_message(
        MessageType.MODERATOR_OBSERVATION,
        summary_text,
        sender_name="AI Moderator",
        metadata={'summary': summary}
    )

    # Broadcast wrap-up
    await manager.broadcast_to_session({
        'type': 'conversation_wrapping_up',
        'message': message.to_dict(),
        'summary': summary,
        'request_decision': True
    }, session.session_id)

    session.stage = SessionStage.WRAPPING_UP


async def end_conversation_session(session: ConversationSession, match: Match, db: Session):
    """End conversation and reveal results"""

    is_mutual = session.is_mutual_match()

    # Update match status
    if is_mutual:
        match.status = MatchStatus.DIRECT_CHAT
        match.direct_chat_started_at = datetime.utcnow()
    else:
        match.status = MatchStatus.REJECTED

    db.commit()

    # Send results to both users
    result_message = {
        'type': 'conversation_ended',
        'is_mutual_match': is_mutual,
        'user1_decision': session.user1_decision,
        'user2_decision': session.user2_decision,
    }

    if is_mutual:
        result_message['message'] = "🎉 It's a match! You can now chat directly."
        result_message['can_chat_directly'] = True
    else:
        result_message['message'] = "Thank you for participating. We'll find the right match for you!"
        result_message['can_chat_directly'] = False

    await manager.broadcast_to_session(result_message, session.session_id)

    # Clean up session
    session_manager.end_session(session.session_id)


# Background task to cleanup expired sessions
@router.on_event("startup")
async def cleanup_task():
    """Periodic cleanup of expired sessions"""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        session_manager.cleanup_expired_sessions()
