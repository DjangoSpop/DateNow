"""
Onboarding status for GET /users/me.

The questionnaire bank lives in `app.questionnaire` (built separately). Until it exists this module
falls back to version=None / total=0 so /users/me keeps working.
"""
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OnboardingAnswer, PsychologicalProfile, User, UserProfile


def questionnaire_meta() -> Tuple[Optional[str], int]:
    """(QUESTIONNAIRE_VERSION, total required questions) from app.questionnaire, or (None, 0)."""
    try:
        from app.questionnaire import QUESTIONNAIRE_VERSION, total_required
    except ModuleNotFoundError as exc:
        if exc.name != "app.questionnaire":
            raise  # the package exists but is broken: surface it
        return None, 0
    total = total_required() if callable(total_required) else total_required
    return QUESTIONNAIRE_VERSION, int(total)


def onboarding_status(db: Session, user: User) -> dict:
    """The `onboarding` object of GET /users/me (see docs/API_CONTRACT.md)."""
    profile_complete = db.scalar(
        select(func.count()).select_from(UserProfile).where(UserProfile.user_id == user.id)
    ) > 0
    questionnaire_complete = db.scalar(
        select(func.count()).select_from(PsychologicalProfile).where(PsychologicalProfile.user_id == user.id)
    ) > 0
    answered = db.scalar(
        select(func.count()).select_from(OnboardingAnswer).where(OnboardingAnswer.user_id == user.id)
    )
    version, total = questionnaire_meta()
    return {
        "profile_complete": profile_complete,
        "questionnaire_complete": questionnaire_complete,
        "questionnaire_answered": int(answered or 0),
        "questionnaire_total": total,
        "questionnaire_version": version,
        "complete": profile_complete and questionnaire_complete,
    }
