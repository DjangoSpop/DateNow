"""
Pydantic schemas for request/response validation
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator,
)

from app.models import (
    Gender, RelationshipGoal, MatchStatus,
    AISessionStatus, MessageType, OnboardingStatus,
)


MIN_USER_AGE = 18
MAX_USER_AGE = 120


def age_on(dob: date, today: Optional[date] = None) -> int:
    """Full years between ``dob`` and ``today``."""
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_adult_dob(dob: date) -> date:
    if dob > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    age = age_on(dob)
    if age < MIN_USER_AGE:
        raise ValueError(f"You must be at least {MIN_USER_AGE} years old")
    if age > MAX_USER_AGE:
        raise ValueError("date_of_birth is not plausible")
    return dob


class _StrictInput(BaseModel):
    """Base for request bodies: unknown / server-controlled fields -> 422."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Authentication Schemas
class UserRegister(_StrictInput):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()


class UserLogin(_StrictInput):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(_StrictInput):
    refresh_token: str = Field(..., min_length=1, max_length=4096)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class MeResponse(BaseModel):
    """`GET /auth/me` - never includes hashed_password."""
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    has_profile: bool
    onboarding_status: OnboardingStatus


# User Profile Schemas
_NON_NULLABLE_PROFILE_FIELDS = (
    "first_name", "date_of_birth", "gender", "looking_for_gender",
    "age_preference_min", "age_preference_max", "distance_preference_km",
    "relationship_goal",
)


class _ProfileFields(_StrictInput):
    """Field definitions shared by create/update; every field optional here."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    height_cm: Optional[int] = Field(None, ge=50, le=300)
    looking_for_gender: Optional[List[Gender]] = Field(None, min_length=1, max_length=4)
    age_preference_min: Optional[int] = Field(None, ge=18, le=100)
    age_preference_max: Optional[int] = Field(None, ge=18, le=100)
    distance_preference_km: Optional[int] = Field(None, ge=1, le=500)
    relationship_goal: Optional[RelationshipGoal] = None

    @field_validator("date_of_birth")
    @classmethod
    def adult(cls, v: Optional[date]) -> Optional[date]:
        return validate_adult_dob(v) if v is not None else v

    @field_validator("looking_for_gender")
    @classmethod
    def dedupe_genders(cls, v: Optional[List[Gender]]) -> Optional[List[Gender]]:
        if v is None:
            return v
        return list(dict.fromkeys(v))

    @model_validator(mode="after")
    def age_range(self):
        lo, hi = self.age_preference_min, self.age_preference_max
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("age_preference_min must be <= age_preference_max")
        return self


class UserProfileCreate(_ProfileFields):
    first_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    gender: Gender
    looking_for_gender: List[Gender] = Field(..., min_length=1, max_length=4)
    age_preference_min: int = Field(..., ge=18, le=100)
    age_preference_max: int = Field(..., ge=18, le=100)
    distance_preference_km: int = Field(50, ge=1, le=500)
    relationship_goal: RelationshipGoal


class UserProfileUpdate(_ProfileFields):
    """PATCH body: only sent fields are applied. Fields that are required on
    create may not be explicitly set to null."""

    @model_validator(mode="before")
    @classmethod
    def no_null_for_required(cls, data: Any) -> Any:
        if isinstance(data, dict):
            nulls = [f for f in _NON_NULLABLE_PROFILE_FIELDS if f in data and data[f] is None]
            if nulls:
                raise ValueError(f"These fields cannot be null: {', '.join(nulls)}")
        return data


class UserProfileResponse(BaseModel):
    """Owner view of the profile. Latitude/longitude are deliberately omitted."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    height_cm: Optional[int] = None
    looking_for_gender: Optional[List[Gender]] = None
    age_preference_min: Optional[int] = None
    age_preference_max: Optional[int] = None
    distance_preference_km: Optional[int] = None
    relationship_goal: Optional[RelationshipGoal] = None
    profile_photo_url: Optional[str] = None
    photos: Optional[List[str]] = None
    is_profile_complete: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Psychological Profile Schemas
# (Scores are computed server-side only; there is intentionally no create schema.)
class PsychologicalProfileResponse(BaseModel):
    """Raw questionnaire answers and AI insight text are not exposed."""
    model_config = ConfigDict(from_attributes=True)

    openness: Optional[float] = None
    conscientiousness: Optional[float] = None
    extraversion: Optional[float] = None
    agreeableness: Optional[float] = None
    neuroticism: Optional[float] = None
    family_orientation: Optional[float] = None
    career_ambition: Optional[float] = None
    adventure_seeking: Optional[float] = None
    social_consciousness: Optional[float] = None
    spiritual_religious: Optional[float] = None
    communication_style: Optional[str] = None
    conflict_resolution: Optional[str] = None
    love_language_words: Optional[float] = None
    love_language_acts: Optional[float] = None
    love_language_gifts: Optional[float] = None
    love_language_time: Optional[float] = None
    love_language_touch: Optional[float] = None
    attachment_style: Optional[str] = None
    questionnaire_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Interest Schemas
class InterestCreate(BaseModel):
    name: str
    category: Optional[str] = None


class InterestResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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
    # ORM attribute is Message.message_metadata (DB column "metadata")
    metadata: Optional[Dict[str, Any]] = Field(
        None, validation_alias=AliasChoices("message_metadata", "metadata")
    )
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Conversation Schemas
class ConversationResponse(BaseModel):
    id: int
    match_id: int
    is_ai_mediated: bool
    is_active: bool
    created_at: datetime
    last_message_at: Optional[datetime]
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


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


# Onboarding / Questionnaire Schemas
# Answers are validated against the server-side catalog in the route layer
# (app.questionnaire_catalog); these schemas only fix the envelope shape.
class OnboardingDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_section: Optional[str] = Field(None, max_length=50)
    # A null value removes a previously saved answer.
    answers: Dict[str, Any] = Field(default_factory=dict)


class OnboardingStateResponse(BaseModel):
    status: OnboardingStatus
    current_section: Optional[str] = None
    answers: Dict[str, Any] = Field(default_factory=dict)
    questionnaire_version: Optional[str] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QuestionnaireSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Dict[str, Any] = Field(default_factory=dict)
