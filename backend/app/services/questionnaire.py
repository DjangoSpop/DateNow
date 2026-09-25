"""
Questionnaire persistence and server-side scoring (docs/API_CONTRACT.md, "Questionnaire").

Raw answers live in `onboarding_answers` (one row per user + question, tagged with the questionnaire
version). Scores are only ever produced here, by `app.questionnaire.score`, never accepted from clients.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import questionnaire
from app.errors import AppError
from app.models import OnboardingAnswer, PsychologicalProfile, User


def load_answers(db: Session, user: User) -> Dict[str, Any]:
    """The user's answers for the current questionnaire version, in presentation order."""
    rows = db.execute(
        select(OnboardingAnswer.question_id, OnboardingAnswer.value).where(
            OnboardingAnswer.user_id == user.id,
            OnboardingAnswer.questionnaire_version == questionnaire.QUESTIONNAIRE_VERSION,
        )
    ).all()
    stored = {qid: value for qid, value in rows}
    return {qid: stored[qid] for qid in questionnaire.question_ids() if qid in stored}


def _current_profile(db: Session, user: User) -> Optional[PsychologicalProfile]:
    return db.scalar(select(PsychologicalProfile).where(PsychologicalProfile.user_id == user.id))


def questionnaire_state(db: Session, user: User) -> dict:
    answers = load_answers(db, user)
    profile = _current_profile(db, user)
    scored = profile is not None and profile.questionnaire_version == questionnaire.QUESTIONNAIRE_VERSION
    return {
        "version": questionnaire.QUESTIONNAIRE_VERSION,
        "answers": answers,
        "answered": len(answers),
        "total_required": questionnaire.total_required(),
        "missing": questionnaire.missing_required(answers),
        "complete": scored,
        "scored_at": profile.scored_at if scored else None,
    }


def save_answers(db: Session, user: User, answers: Dict[str, Any]) -> None:
    """Validate the whole batch, then upsert atomically. Nothing is written if any answer is invalid."""
    try:
        normalized = questionnaire.validate_answers(answers)
    except questionnaire.AnswerValidationError as exc:
        raise AppError(422, "VALIDATION_ERROR", "Invalid questionnaire answers", fields=exc.errors)

    now = datetime.now(timezone.utc)
    stmt = insert(OnboardingAnswer).values(
        [
            {
                "user_id": user.id,
                "question_id": qid,
                "value": value,
                "questionnaire_version": questionnaire.QUESTIONNAIRE_VERSION,
                "created_at": now,
                "updated_at": now,
            }
            for qid, value in normalized.items()
        ]
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_onboarding_answers_user_question",
        set_={
            "value": stmt.excluded.value,
            "questionnaire_version": stmt.excluded.questionnaire_version,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    db.commit()


def submit(db: Session, user: User) -> PsychologicalProfile:
    """Score the stored answers and create or replace the user's psychological profile."""
    answers = load_answers(db, user)
    try:
        scores = questionnaire.score(answers)
    except questionnaire.AnswerValidationError as exc:
        raise AppError(
            422, "QUESTIONNAIRE_INCOMPLETE", "Some required questions are unanswered", fields=exc.errors
        )

    profile = _current_profile(db, user)
    if profile is None:
        profile = PsychologicalProfile(user_id=user.id)
        db.add(profile)
    for column, value in scores.items():
        setattr(profile, column, value)
    profile.questionnaire_version = questionnaire.QUESTIONNAIRE_VERSION
    profile.scored_at = datetime.now(timezone.utc)
    profile.ai_insights = None  # AI narrative is out of Sprint 1 scope; never keep one from stale scores
    db.commit()
    db.refresh(profile)
    return profile
