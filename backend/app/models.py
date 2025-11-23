"""
Database models for the DateNow application
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    ForeignKey, JSON, Enum as SQLEnum, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


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


# Association table for user interests
user_interests = Table(
    'user_interests',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('interest_id', Integer, ForeignKey('interests.id'))
)


class User(Base):
    """User model for authentication and basic info"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    psychological_profile = relationship("PsychologicalProfile", back_populates="user", uselist=False)
    matches_initiated = relationship("Match", foreign_keys="Match.user1_id", back_populates="user1")
    matches_received = relationship("Match", foreign_keys="Match.user2_id", back_populates="user2")
    ai_sessions = relationship("AISession", back_populates="user")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")


class UserProfile(Base):
    """Extended user profile information"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # Basic Info
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50))
    date_of_birth = Column(DateTime)
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
    is_profile_complete = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")
    interests = relationship("Interest", secondary=user_interests, back_populates="users")


class Interest(Base):
    """User interests and hobbies"""
    __tablename__ = "interests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))  # sports, arts, music, etc.

    # Relationships
    users = relationship("UserProfile", secondary=user_interests, back_populates="interests")


class PsychologicalProfile(Base):
    """Psychological profile from onboarding questionnaire"""
    __tablename__ = "psychological_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

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

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="psychological_profile")


class Match(Base):
    """Matching between two users"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"))
    user2_id = Column(Integer, ForeignKey("users.id"))

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
    ai_sessions = relationship("AISession", back_populates="match")
    conversation = relationship("Conversation", back_populates="match", uselist=False)


class AISession(Base):
    """AI mediation session for a match"""
    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # Which user this session is for

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
    messages = relationship("Message", back_populates="ai_session")


class Conversation(Base):
    """Conversation between matched users"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True)

    is_ai_mediated = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    match = relationship("Match", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    """Messages in conversations"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    ai_session_id = Column(Integer, ForeignKey("ai_sessions.id"), nullable=True)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for AI messages
    message_type = Column(SQLEnum(MessageType))

    content = Column(Text, nullable=False)
    metadata = Column(JSON)  # Additional message metadata

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
    user_id = Column(Integer, ForeignKey("users.id"))

    prompt = Column(Text)
    response = Column(Text)
    model_used = Column(String(50))
    tokens_used = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
