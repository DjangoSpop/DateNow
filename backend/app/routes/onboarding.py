"""
Onboarding and questionnaire routes.

The server owns the question catalog and all scoring: clients only ever send raw
answers, which are validated against app.questionnaire_catalog and scored by
app.questionnaire_processor. Every route operates on the current user only.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import OnboardingProgress, OnboardingStatus, PsychologicalProfile, User
from app.questionnaire_catalog import (
    QUESTIONNAIRE_VERSION,
    QUESTIONS,
    SECTIONS,
    QuestionnaireValidationError,
    get_questionnaire_definition,
    score_questionnaire,
    validate_partial_answers,
)
from app.schemas import (
    OnboardingDraftUpdate,
    OnboardingStateResponse,
    PsychologicalProfileResponse,
    QuestionnaireSubmitRequest,
)

router = APIRouter(tags=["Onboarding"])

_SECTION_IDS = frozenset(s.id for s in SECTIONS)

# Fields produced by score_questionnaire that are persisted on PsychologicalProfile.
_PROFILE_FIELDS = (
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "family_orientation", "career_ambition", "adventure_seeking",
    "social_consciousness", "spiritual_religious",
    "communication_style", "conflict_resolution",
    "love_language_words", "love_language_acts", "love_language_gifts",
    "love_language_time", "love_language_touch",
    "attachment_style", "questionnaire_version", "questionnaire_responses",
)


def _validation_response(exc: QuestionnaireValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors},
    )


def _get_progress(db: Session, user: User) -> Optional[OnboardingProgress]:
    return db.query(OnboardingProgress).filter(OnboardingProgress.user_id == user.id).first()


def _state(progress: Optional[OnboardingProgress]) -> OnboardingStateResponse:
    if progress is None:
        return OnboardingStateResponse(
            status=OnboardingStatus.NOT_STARTED, questionnaire_version=QUESTIONNAIRE_VERSION
        )
    return OnboardingStateResponse(
        status=progress.status,
        current_section=progress.current_section,
        answers=dict(progress.answers or {}),
        questionnaire_version=progress.questionnaire_version,
        updated_at=progress.updated_at,
        completed_at=progress.completed_at,
    )


def _merge_answers(saved: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate `incoming` and merge it over `saved`.

    A null value for a known question removes the saved answer; everything else is
    validated against the catalog (unknown ids, wrong types and out-of-range values
    raise QuestionnaireValidationError listing every problem).
    """
    removals = {k for k, v in incoming.items() if v is None and k in QUESTIONS}
    to_validate = {k: v for k, v in incoming.items() if k not in removals}
    normalized = validate_partial_answers(to_validate)
    merged = {k: v for k, v in saved.items() if k not in removals}
    merged.update(normalized)
    return merged


@router.get("/questionnaire")
def get_questionnaire(current_user: User = Depends(get_current_user)):
    """Question catalog (no scoring keys are exposed)."""
    return get_questionnaire_definition()


@router.get("/onboarding", response_model=OnboardingStateResponse)
def get_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current onboarding draft; `not_started` with empty answers if none saved."""
    return _state(_get_progress(db, current_user))


@router.put("/onboarding", response_model=OnboardingStateResponse)
def save_onboarding_draft(
    body: OnboardingDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a partial draft so onboarding can be resumed."""
    if body.current_section is not None and body.current_section not in _SECTION_IDS:
        return _validation_response(QuestionnaireValidationError(
            [{"question_id": "__all__", "message": "unknown current_section"}]
        ))

    progress = _get_progress(db, current_user)
    if progress is not None and progress.status == OnboardingStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already completed")

    try:
        merged = _merge_answers(dict(progress.answers or {}) if progress else {}, body.answers)
    except QuestionnaireValidationError as exc:
        return _validation_response(exc)

    if progress is None:
        progress = OnboardingProgress(user_id=current_user.id)
        db.add(progress)
    # JSON column is not mutation-tracked: always assign a new dict.
    progress.answers = merged
    progress.status = OnboardingStatus.IN_PROGRESS
    progress.questionnaire_version = QUESTIONNAIRE_VERSION
    if body.current_section is not None:
        progress.current_section = body.current_section
    progress.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except IntegrityError:
        # Concurrent first save for the same user; the other request won.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent onboarding update, retry")
    db.refresh(progress)
    return _state(progress)


@router.post(
    "/questionnaire/submit",
    response_model=PsychologicalProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_questionnaire(
    body: QuestionnaireSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Complete onboarding: merge with the saved draft, require every question,
    score server-side and persist the psychological profile.
    """
    progress = _get_progress(db, current_user)
    existing_profile = db.query(PsychologicalProfile).filter(
        PsychologicalProfile.user_id == current_user.id
    ).first()
    if existing_profile is not None or (
        progress is not None and progress.status == OnboardingStatus.COMPLETED
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already completed")

    try:
        merged = _merge_answers(dict(progress.answers or {}) if progress else {}, body.answers)
        scored = score_questionnaire(merged)
    except QuestionnaireValidationError as exc:
        return _validation_response(exc)

    profile = PsychologicalProfile(
        user_id=current_user.id,
        **{field: scored.get(field) for field in _PROFILE_FIELDS},
    )
    db.add(profile)

    now = datetime.now(timezone.utc)
    if progress is None:
        progress = OnboardingProgress(user_id=current_user.id)
        db.add(progress)
    progress.answers = dict(scored["questionnaire_responses"])
    progress.status = OnboardingStatus.COMPLETED
    progress.questionnaire_version = scored["questionnaire_version"]
    progress.completed_at = now
    progress.updated_at = now

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already completed")
    db.refresh(profile)
    return profile
