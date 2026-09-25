"""
Pydantic schemas for request/response validation
"""
import re
from datetime import date, datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from pydantic import (
    BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator,
)

from app.models import (
    Gender, RelationshipGoal, MatchStatus,
    AISessionStatus, MessageType
)


def _reject_nul(v: Any) -> Any:
    """NUL characters are rejected by bcrypt and by PostgreSQL text columns (they would surface as a 500)."""
    if isinstance(v, str) and "\x00" in v:
        raise ValueError("must not contain NUL characters")
    return v


# Authentication Schemas
class UserRegister(BaseModel):
    """Extra fields (e.g. legacy first_name/last_name) are ignored."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("password")
    @classmethod
    def no_nul(cls, v: str) -> str:
        return _reject_nul(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("password")
    @classmethod
    def no_nul(cls, v: str) -> str:
        return _reject_nul(v)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class Token(BaseModel):
    """TokenPair in the API contract."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[int] = None


# Current user
class OnboardingStatus(BaseModel):
    profile_complete: bool
    questionnaire_complete: bool
    questionnaire_answered: int
    questionnaire_total: int
    questionnaire_version: Optional[str]
    complete: bool


class UserMeResponse(BaseModel):
    id: int
    email: str
    is_verified: bool
    created_at: Optional[datetime]
    onboarding: OnboardingStatus


# User Profile Schemas
MIN_USER_AGE = 18
MAX_USER_AGE = 120
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FirstName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
LastName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
Bio = Annotated[str, StringConstraints(max_length=500)]
Place = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
AgePref = Annotated[int, Field(ge=18, le=100)]
GenderList = Annotated[List[Gender], Field(min_length=1, max_length=4)]


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class _ProfileFields(BaseModel):
    """Shared validation for ProfileCreate / ProfileUpdate. Unknown fields are rejected."""
    model_config = ConfigDict(extra="forbid")

    @field_validator("date_of_birth", mode="before", check_fields=False)
    @classmethod
    def date_format(cls, v: Any) -> Any:
        if v is None or isinstance(v, date) and not isinstance(v, datetime):
            return v
        if not isinstance(v, str) or not _DATE_RE.match(v):
            raise ValueError("must be a date in YYYY-MM-DD format")
        return v

    @field_validator("date_of_birth", check_fields=False)
    @classmethod
    def date_rules(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = utc_today()
        if v > today:
            raise ValueError("must not be in the future")
        age = age_on(v, today)
        if age < MIN_USER_AGE:
            raise ValueError(f"you must be at least {MIN_USER_AGE} years old")
        if age > MAX_USER_AGE:
            raise ValueError(f"age must be at most {MAX_USER_AGE}")
        return v

    @field_validator("looking_for_gender", check_fields=False)
    @classmethod
    def unique_genders(cls, v: Optional[List[Gender]]) -> Optional[List[Gender]]:
        if v is not None and len(set(v)) != len(v):
            raise ValueError("values must be unique")
        return v


class ProfileCreate(_ProfileFields):
    first_name: FirstName
    last_name: Optional[LastName] = None
    date_of_birth: date
    gender: Gender
    looking_for_gender: GenderList
    age_preference_min: AgePref
    age_preference_max: AgePref
    relationship_goal: RelationshipGoal
    bio: Optional[Bio] = None
    city: Optional[Place] = None
    country: Optional[Place] = None


# Fields that may not be explicitly set to null in a PATCH.
PROFILE_REQUIRED_FIELDS = (
    "first_name", "date_of_birth", "gender", "looking_for_gender",
    "age_preference_min", "age_preference_max", "relationship_goal",
)


class ProfileUpdate(_ProfileFields):
    first_name: Optional[FirstName] = None
    last_name: Optional[LastName] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    looking_for_gender: Optional[GenderList] = None
    age_preference_min: Optional[AgePref] = None
    age_preference_max: Optional[AgePref] = None
    relationship_goal: Optional[RelationshipGoal] = None
    bio: Optional[Bio] = None
    city: Optional[Place] = None
    country: Optional[Place] = None

    @field_validator(*PROFILE_REQUIRED_FIELDS)
    @classmethod
    def not_null(cls, v: Any) -> Any:
        # Only runs for values actually supplied (defaults are not validated).
        if v is None:
            raise ValueError("may not be null")
        return v


class ProfileResponse(BaseModel):
    first_name: str
    last_name: Optional[str]
    date_of_birth: date
    age: int
    gender: Gender
    looking_for_gender: List[Gender]
    age_preference_min: int
    age_preference_max: int
    relationship_goal: RelationshipGoal
    bio: Optional[str]
    city: Optional[str]
    country: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# Psychological Profile Schemas (read-only; scores are computed server-side)
class BigFiveScores(BaseModel):
    openness: Optional[float]
    conscientiousness: Optional[float]
    extraversion: Optional[float]
    agreeableness: Optional[float]
    neuroticism: Optional[float]


class ValuesScores(BaseModel):
    family_orientation: Optional[float]
    career_ambition: Optional[float]
    adventure_seeking: Optional[float]
    social_consciousness: Optional[float]
    spiritual_religious: Optional[float]


class LoveLanguageScores(BaseModel):
    words: Optional[float]
    acts: Optional[float]
    gifts: Optional[float]
    time: Optional[float]
    touch: Optional[float]


class PsychologicalProfileResponse(BaseModel):
    questionnaire_version: Optional[str]
    scored_at: Optional[datetime]
    big_five: BigFiveScores
    values: ValuesScores
    love_languages: LoveLanguageScores
    communication_style: Optional[str]
    conflict_resolution: Optional[str]
    attachment_style: Optional[str]

    @classmethod
    def from_model(cls, p: Any) -> "PsychologicalProfileResponse":
        return cls(
            questionnaire_version=p.questionnaire_version,
            scored_at=p.scored_at,
            big_five=BigFiveScores(
                openness=p.openness, conscientiousness=p.conscientiousness, extraversion=p.extraversion,
                agreeableness=p.agreeableness, neuroticism=p.neuroticism,
            ),
            values=ValuesScores(
                family_orientation=p.family_orientation, career_ambition=p.career_ambition,
                adventure_seeking=p.adventure_seeking, social_consciousness=p.social_consciousness,
                spiritual_religious=p.spiritual_religious,
            ),
            love_languages=LoveLanguageScores(
                words=p.love_language_words, acts=p.love_language_acts, gifts=p.love_language_gifts,
                time=p.love_language_time, touch=p.love_language_touch,
            ),
            communication_style=p.communication_style,
            conflict_resolution=p.conflict_resolution,
            attachment_style=p.attachment_style,
        )


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
    # ORM attribute is Message.message_metadata (DB column "metadata"); serialised as "metadata".
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="message_metadata")
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
