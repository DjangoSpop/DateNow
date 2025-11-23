"""
Conversation Session Manager
Manages AI-moderated conversation sessions with privacy controls
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid


class SessionStage(str, Enum):
    """Conversation stages"""
    WAITING = "waiting"  # Waiting for both users to join
    OPENING = "opening"  # AI opening greeting
    ACTIVE = "active"  # Active conversation
    WRAPPING_UP = "wrapping_up"  # Final questions
    COMPLETED = "completed"  # Conversation ended
    CANCELLED = "cancelled"  # Session cancelled


class MessageType(str, Enum):
    """Message types in conversation"""
    MODERATOR_GREETING = "moderator_greeting"
    MODERATOR_QUESTION = "moderator_question"
    MODERATOR_OBSERVATION = "moderator_observation"
    USER_RESPONSE = "user_response"
    SYSTEM_NOTIFICATION = "system_notification"
    TYPING_INDICATOR = "typing_indicator"


@dataclass
class ConversationMessage:
    """Individual message in conversation"""
    id: str
    type: MessageType
    content: str
    sender_id: Optional[int]
    sender_name: Optional[str]
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type.value,
            'content': self.content,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class ConversationSession:
    """Manages a single AI-moderated conversation session"""
    session_id: str
    match_id: int
    user1_id: int
    user2_id: int
    user1_name: str
    user2_name: str
    compatibility_score: float

    # Session state
    stage: SessionStage = SessionStage.WAITING
    messages: List[ConversationMessage] = field(default_factory=list)
    questions_asked: int = 0
    max_questions: int = 10

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=2))

    # User state
    user1_connected: bool = False
    user2_connected: bool = False
    user1_ready: bool = False
    user2_ready: bool = False

    # Privacy & Control
    user1_can_see_name: bool = False  # Can see user2's name
    user2_can_see_name: bool = False  # Can see user1's name
    messages_visible_to_both: bool = True  # Both see all messages

    # Decisions
    user1_decision: Optional[bool] = None  # True = yes, False = no, None = pending
    user2_decision: Optional[bool] = None

    # Metadata
    context: Dict = field(default_factory=dict)

    def add_message(
        self,
        message_type: MessageType,
        content: str,
        sender_id: Optional[int] = None,
        sender_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ConversationMessage:
        """Add message to conversation"""
        message = ConversationMessage(
            id=str(uuid.uuid4()),
            type=message_type,
            content=content,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        return message

    def get_messages_for_user(self, user_id: int) -> List[Dict]:
        """Get messages visible to a specific user (privacy filtering)"""
        messages = []
        for msg in self.messages:
            msg_dict = msg.to_dict()

            # Privacy: Hide other user's name if not revealed yet
            if not self.messages_visible_to_both:
                if msg.sender_id and msg.sender_id != user_id:
                    can_see_name = (
                        (user_id == self.user1_id and self.user1_can_see_name) or
                        (user_id == self.user2_id and self.user2_can_see_name)
                    )
                    if not can_see_name:
                        msg_dict['sender_name'] = "Your Match"

            messages.append(msg_dict)

        return messages

    def both_users_connected(self) -> bool:
        """Check if both users are connected"""
        return self.user1_connected and self.user2_connected

    def both_users_ready(self) -> bool:
        """Check if both users are ready to start"""
        return self.user1_ready and self.user2_ready

    def can_start(self) -> bool:
        """Check if session can start"""
        return (
            self.stage == SessionStage.WAITING and
            self.both_users_connected() and
            self.both_users_ready()
        )

    def should_wrap_up(self) -> bool:
        """Check if conversation should wrap up"""
        return self.questions_asked >= self.max_questions

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at

    def get_next_responder(self) -> int:
        """Get which user should respond next (alternating)"""
        # Alternate based on number of user responses
        user_responses = [m for m in self.messages if m.type == MessageType.USER_RESPONSE]
        user1_responses = sum(1 for m in user_responses if m.sender_id == self.user1_id)
        user2_responses = sum(1 for m in user_responses if m.sender_id == self.user2_id)

        # Whoever has fewer responses goes next
        if user1_responses <= user2_responses:
            return self.user1_id
        else:
            return self.user2_id

    def mark_decision(self, user_id: int, decision: bool):
        """Record user's yes/no decision"""
        if user_id == self.user1_id:
            self.user1_decision = decision
        elif user_id == self.user2_id:
            self.user2_decision = decision

    def both_decided(self) -> bool:
        """Check if both users have made decisions"""
        return self.user1_decision is not None and self.user2_decision is not None

    def is_mutual_match(self) -> bool:
        """Check if both users said yes"""
        return self.user1_decision is True and self.user2_decision is True

    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'match_id': self.match_id,
            'stage': self.stage.value,
            'questions_asked': self.questions_asked,
            'max_questions': self.max_questions,
            'user1_connected': self.user1_connected,
            'user2_connected': self.user2_connected,
            'user1_ready': self.user1_ready,
            'user2_ready': self.user2_ready,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'expires_at': self.expires_at.isoformat(),
        }


class SessionManager:
    """Manages all active conversation sessions"""

    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.user_to_session: Dict[int, str] = {}  # {user_id: session_id}

    def create_session(
        self,
        match_id: int,
        user1_id: int,
        user2_id: int,
        user1_name: str,
        user2_name: str,
        compatibility_score: float
    ) -> ConversationSession:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())

        session = ConversationSession(
            session_id=session_id,
            match_id=match_id,
            user1_id=user1_id,
            user2_id=user2_id,
            user1_name=user1_name,
            user2_name=user2_name,
            compatibility_score=compatibility_score
        )

        self.sessions[session_id] = session
        self.user_to_session[user1_id] = session_id
        self.user_to_session[user2_id] = session_id

        print(f"✅ Created session {session_id} for match {match_id}")
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_user_session(self, user_id: int) -> Optional[ConversationSession]:
        """Get session for a user"""
        session_id = self.user_to_session.get(user_id)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def end_session(self, session_id: str):
        """End and clean up a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.stage = SessionStage.COMPLETED
            session.ended_at = datetime.utcnow()

            # Remove user mappings
            if session.user1_id in self.user_to_session:
                del self.user_to_session[session.user1_id]
            if session.user2_id in self.user_to_session:
                del self.user_to_session[session.user2_id]

            print(f"🏁 Ended session {session_id}")

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired() and session.stage != SessionStage.COMPLETED
        ]

        for sid in expired:
            self.end_session(sid)
            del self.sessions[sid]

        if expired:
            print(f"🧹 Cleaned up {len(expired)} expired sessions")


# Global session manager
session_manager = SessionManager()
