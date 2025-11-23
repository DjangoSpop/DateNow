"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models import (
    Gender, RelationshipGoal, MatchStatus,
    AISessionStatus, MessageType
)


# Authentication Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# User Profile Schemas
class UserProfileCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: datetime
    gender: Gender
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    height_cm: Optional[int] = None
    looking_for_gender: List[Gender]
    age_preference_min: int = Field(..., ge=18, le=100)
    age_preference_max: int = Field(..., ge=18, le=100)
    distance_preference_km: int = Field(50, ge=1, le=500)
    relationship_goal: RelationshipGoal


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    height_cm: Optional[int] = None
    looking_for_gender: Optional[List[Gender]] = None
    age_preference_min: Optional[int] = None
    age_preference_max: Optional[int] = None
    distance_preference_km: Optional[int] = None
    relationship_goal: Optional[RelationshipGoal] = None


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: Optional[str]
    date_of_birth: datetime
    gender: Gender
    bio: Optional[str]
    city: Optional[str]
    country: Optional[str]
    height_cm: Optional[int]
    looking_for_gender: List[Gender]
    age_preference_min: int
    age_preference_max: int
    distance_preference_km: int
    relationship_goal: RelationshipGoal
    profile_photo_url: Optional[str]
    photos: Optional[List[str]]
    is_profile_complete: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Psychological Profile Schemas
class PsychologicalProfileCreate(BaseModel):
    # Big Five
    openness: float = Field(..., ge=0, le=100)
    conscientiousness: float = Field(..., ge=0, le=100)
    extraversion: float = Field(..., ge=0, le=100)
    agreeableness: float = Field(..., ge=0, le=100)
    neuroticism: float = Field(..., ge=0, le=100)

    # Values
    family_orientation: float = Field(..., ge=0, le=100)
    career_ambition: float = Field(..., ge=0, le=100)
    adventure_seeking: float = Field(..., ge=0, le=100)
    social_consciousness: float = Field(..., ge=0, le=100)
    spiritual_religious: float = Field(..., ge=0, le=100)

    # Communication
    communication_style: str
    conflict_resolution: str

    # Love Languages
    love_language_words: float = Field(..., ge=0, le=100)
    love_language_acts: float = Field(..., ge=0, le=100)
    love_language_gifts: float = Field(..., ge=0, le=100)
    love_language_time: float = Field(..., ge=0, le=100)
    love_language_touch: float = Field(..., ge=0, le=100)

    # Attachment
    attachment_style: str

    questionnaire_responses: Optional[Dict[str, Any]] = None


class PsychologicalProfileResponse(BaseModel):
    id: int
    user_id: int
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float
    family_orientation: float
    career_ambition: float
    adventure_seeking: float
    social_consciousness: float
    spiritual_religious: float
    communication_style: str
    conflict_resolution: str
    love_language_words: float
    love_language_acts: float
    love_language_gifts: float
    love_language_time: float
    love_language_touch: float
    attachment_style: str
    ai_insights: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Interest Schemas
class InterestCreate(BaseModel):
    name: str
    category: Optional[str] = None


class InterestResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]

    class Config:
        from_attributes = True


# Match Schemas
class MatchResponse(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    status: MatchStatus
    overall_compatibility: float
    personality_compatibility: float
    values_compatibility: float
    interests_compatibility: float
    lifestyle_compatibility: float
    compatibility_report: Optional[str]
    ai_recommendation: Optional[str]
    matched_at: datetime
    ai_mediation_started_at: Optional[datetime]
    direct_chat_started_at: Optional[datetime]

    class Config:
        from_attributes = True


class MatchCreate(BaseModel):
    user2_id: int


class MatchActionRequest(BaseModel):
    action: str  # "accept", "reject", "start_ai_mediation"


# AI Session Schemas
class AISessionResponse(BaseModel):
    id: int
    match_id: int
    user_id: int
    status: AISessionStatus
    questions_asked: int
    responses_collected: int
    user_insights: Optional[str]
    started_at: datetime
    last_activity_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AIQuestionRequest(BaseModel):
    context: Optional[Dict[str, Any]] = None


class AIQuestionResponse(BaseModel):
    session_id: int
    question: str
    question_number: int
    total_questions: int


class AIResponseSubmit(BaseModel):
    session_id: int
    question: str
    answer: str


# Message Schemas
class MessageCreate(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: Optional[int]
    message_type: MessageType
    content: str
    metadata: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationResponse(BaseModel):
    id: int
    match_id: int
    is_ai_mediated: bool
    is_active: bool
    created_at: datetime
    last_message_at: Optional[datetime]
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


# WebSocket Message Schemas
class WSMessage(BaseModel):
    type: str  # "question", "answer", "insight", "message", "notification"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Analytics Schemas
class CompatibilityAnalysis(BaseModel):
    overall_score: float
    personality_score: float
    values_score: float
    interests_score: float
    lifestyle_score: float
    strengths: List[str]
    potential_challenges: List[str]
    recommendation: str


# Questionnaire Schemas
class QuestionnaireQuestion(BaseModel):
    id: str
    question: str
    type: str  # "scale", "multiple_choice", "text"
    options: Optional[List[str]] = None
    category: str


class QuestionnaireResponse(BaseModel):
    question_id: str
    answer: Any


class QuestionnaireSubmit(BaseModel):
    responses: List[QuestionnaireResponse]
