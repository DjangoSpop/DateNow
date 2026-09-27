"""
Database models for the DateNow application

The schema is managed by Alembic (``backend/alembic/versions``). Any change
here must be accompanied by a new migration.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Float, Text,
    ForeignKey, JSON, Enum as _SAEnum, Table, CheckConstraint, TypeDecorator,
)
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.sql import func, true, false
import enum
from app.database import Base


def SQLEnum(enum_cls, **kwargs):
    """Enum column type that stores the enum *values* (e.g. ``"male"``), not names.

    On PostgreSQL this is a native ENUM type named after the class
    (lower-cased); on SQLite a VARCHAR + CHECK constraint.
    """
    kwargs.setdefault("name", enum_cls.__name__.lower())
    kwargs.setdefault("values_callable", lambda e: [m.value for m in e])
    kwargs.setdefault("validate_strings", True)
    return _SAEnum(enum_cls, **kwargs)


class StrEnumString(TypeDecorator):
    """Stores a ``str`` enum as a plain VARCHAR value and returns the enum member.

    Accepts the enum member or its string value on write; anything else raises
    ``ValueError`` before reaching the database.
    """
    impl = String
    cache_ok = True

    def __init__(self, enum_cls, length=20, **kwargs):
        self._enum_cls = enum_cls
        super().__init__(length, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self._enum_cls(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self._enum_cls(value)


# Enums
class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    OTHER = "other"


class RelationshipGoal(str, enum.Enum):
    SERIOUS = "serious"
    CASUAL = "casual"
    FRIENDSHIP = "friendship"
    UNSURE = "unsure"


class MatchStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AI_MEDIATION = "ai_mediation"
    DIRECT_CHAT = "direct_chat"
    ENDED = "ended"


class AISessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MessageType(str, enum.Enum):
    AI_QUESTION = "ai_question"
    USER_RESPONSE = "user_response"
    AI_INSIGHT = "ai_insight"
    SYSTEM = "system"
    DIRECT_MESSAGE = "direct_message"


class OnboardingStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# Association table for user interests (keyed by users.id)
user_interests = Table(
    'user_interests',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('interest_id', Integer, ForeignKey('interests.id', ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User model for authentication and basic info"""
    __tablename__ = "users"
    __table_args__ = (
        # Emails are normalised to lower case by the application; enforce it.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    is_verified = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    psychological_profile = relationship(
        "PsychologicalProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    onboarding_progress = relationship(
        "OnboardingProgress", back_populates="user", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    matches_initiated = relationship(
        "Match", foreign_keys="Match.user1_id", back_populates="user1", passive_deletes=True
    )
    matches_received = relationship(
        "Match", foreign_keys="Match.user2_id", back_populates="user2", passive_deletes=True
    )
    ai_sessions = relationship("AISession", back_populates="user", passive_deletes=True)
    messages_sent = relationship(
        "Message", foreign_keys="Message.sender_id", back_populates="sender", passive_deletes=True
    )


class UserProfile(Base):
    """Extended user profile information"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Basic Info
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50))
    date_of_birth = Column(Date)
    gender = Column(SQLEnum(Gender))
    bio = Column(Text)

    # Location
    city = Column(String(100))
    country = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)

    # Physical attributes
    height_cm = Column(Integer)

    # Preferences
    looking_for_gender = Column(JSON)  # List of genders
    age_preference_min = Column(Integer)
    age_preference_max = Column(Integer)
    distance_preference_km = Column(Integer, default=50)
    relationship_goal = Column(SQLEnum(RelationshipGoal))

    # Photos
    photos = Column(JSON)  # List of photo URLs
    profile_photo_url = Column(String)

    # Verification
    is_profile_complete = Column(Boolean, nullable=False, default=False, server_default=false())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")
    # user_interests is keyed by users.id (not user_profiles.id), so the join
    # goes through UserProfile.user_id explicitly.
    interests = relationship(
        "Interest",
        secondary=user_interests,
        primaryjoin=lambda: UserProfile.user_id == foreign(user_interests.c.user_id),
        secondaryjoin=lambda: Interest.id == foreign(user_interests.c.interest_id),
        back_populates="users",
    )


class Interest(Base):
    """User interests and hobbies"""
    __tablename__ = "interests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))  # sports, arts, music, etc.

    # Relationships
    users = relationship(
        "UserProfile",
        secondary=user_interests,
        primaryjoin=lambda: Interest.id == foreign(user_interests.c.interest_id),
        secondaryjoin=lambda: UserProfile.user_id == foreign(user_interests.c.user_id),
        back_populates="interests",
    )


class PsychologicalProfile(Base):
    """Psychological profile from onboarding questionnaire"""
    __tablename__ = "psychological_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Big Five Personality Traits (0-100 scale)
    openness = Column(Float)
    conscientiousness = Column(Float)
    extraversion = Column(Float)
    agreeableness = Column(Float)
    neuroticism = Column(Float)

    # Values (0-100 scale)
    family_orientation = Column(Float)
    career_ambition = Column(Float)
    adventure_seeking = Column(Float)
    social_consciousness = Column(Float)
    spiritual_religious = Column(Float)

    # Communication Style
    communication_style = Column(String(50))  # direct, diplomatic, emotional, logical
    conflict_resolution = Column(String(50))  # avoidant, collaborative, competitive

    # Love Languages (0-100 scale for each)
    love_language_words = Column(Float)
    love_language_acts = Column(Float)
    love_language_gifts = Column(Float)
    love_language_time = Column(Float)
    love_language_touch = Column(Float)

    # Attachment Style
    attachment_style = Column(String(50))  # secure, anxious, avoidant, fearful-avoidant

    # Additional psychological data from questionnaire
    questionnaire_responses = Column(JSON)

    # AI-generated insights
    ai_insights = Column(Text)

    # Version of the server-side questionnaire catalog that produced this profile
    questionnaire_version = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="psychological_profile")


class OnboardingProgress(Base):
    """Server-side onboarding / questionnaire draft state (one row per user)"""
    __tablename__ = "onboarding_progress"
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="status_valid",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Stored as VARCHAR(20) + CHECK constraint; Python side is OnboardingStatus.
    status = Column(
        StrEnumString(OnboardingStatus, 20),
        nullable=False,
        default=OnboardingStatus.NOT_STARTED,
        server_default=OnboardingStatus.NOT_STARTED.value,
    )
    current_section = Column(String(50), nullable=True)
    answers = Column(JSON, nullable=False, default=dict)
    questionnaire_version = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="onboarding_progress")


class Match(Base):
    """Matching between two users"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user2_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = Column(SQLEnum(MatchStatus), default=MatchStatus.PENDING)

    # Compatibility scores
    overall_compatibility = Column(Float)  # 0-1 scale
    personality_compatibility = Column(Float)
    values_compatibility = Column(Float)
    interests_compatibility = Column(Float)
    lifestyle_compatibility = Column(Float)

    # AI analysis
    compatibility_report = Column(Text)
    ai_recommendation = Column(Text)

    # Timestamps
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
    ai_mediation_started_at = Column(DateTime(timezone=True))
    direct_chat_started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    # User actions
    user1_interested = Column(Boolean, default=False)
    user2_interested = Column(Boolean, default=False)

    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="matches_initiated")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="matches_received")
    ai_sessions = relationship("AISession", back_populates="match", passive_deletes=True)
    conversation = relationship(
        "Conversation", back_populates="match", uselist=False, passive_deletes=True
    )


class AISession(Base):
    """AI mediation session for a match"""
    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which user this session is for
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = Column(SQLEnum(AISessionStatus), default=AISessionStatus.ACTIVE)

    # Session data
    questions_asked = Column(Integer, default=0)
    responses_collected = Column(Integer, default=0)
    session_data = Column(JSON)  # Store Q&A pairs

    # AI analysis
    user_insights = Column(Text)  # AI insights about this user's responses
    compatibility_notes = Column(Text)  # Notes on compatibility with the other user

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    match = relationship("Match", back_populates="ai_sessions")
    user = relationship("User", back_populates="ai_sessions")
    messages = relationship("Message", back_populates="ai_session", passive_deletes=True)


class Conversation(Base):
    """Conversation between matched users"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    is_ai_mediated = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    match = relationship("Match", back_populates="conversation")
    messages = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at",
        passive_deletes=True,
    )


class Message(Base):
    """Messages in conversations"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    ai_session_id = Column(
        Integer, ForeignKey("ai_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Null for AI messages (and for messages whose sender account was deleted)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message_type = Column(SQLEnum(MessageType))

    content = Column(Text, nullable=False)
    # DB column is still named "metadata"; the Python attribute cannot be,
    # because `metadata` is reserved by SQLAlchemy's Declarative API.
    message_metadata = Column("metadata", JSON)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    ai_session = relationship("AISession", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")


class AIPromptTemplate(Base):
    """Templates for AI prompts and questions"""
    __tablename__ = "ai_prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    category = Column(String(50))  # onboarding, mediation, analysis, etc.

    template = Column(Text, nullable=False)
    variables = Column(JSON)  # List of variables used in template

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AIConversationLog(Base):
    """Log of all AI interactions for analytics and improvement"""
    __tablename__ = "ai_conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    prompt = Column(Text)
    response = Column(Text)
    model_used = Column(String(50))
    tokens_used = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
