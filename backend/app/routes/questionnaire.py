"""
Questionnaire routes: the server-owned question bank, answer autosave, and server-side scoring.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import questionnaire
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import PsychologicalProfileResponse
from app.services import questionnaire as questionnaire_service

router = APIRouter(tags=["Questionnaire"])


class AnswersUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Dict[str, Any] = Field(..., min_length=1, max_length=100)


class QuestionnaireState(BaseModel):
    version: str
    answers: Dict[str, Any]
    answered: int
    total_required: int
    missing: List[str]
    complete: bool
    scored_at: Optional[datetime]


@router.get("/questionnaire")
def get_questionnaire(current_user: User = Depends(get_current_user)) -> dict:
    """The question bank, in presentation order."""
    return questionnaire.get_definition()


@router.get("/users/me/questionnaire", response_model=QuestionnaireState)
def get_my_questionnaire(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return questionnaire_service.questionnaire_state(db, current_user)


@router.put("/users/me/questionnaire/answers", response_model=QuestionnaireState)
def save_my_answers(
    body: AnswersUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    questionnaire_service.save_answers(db, current_user, body.answers)
    return questionnaire_service.questionnaire_state(db, current_user)


@router.post("/users/me/questionnaire/submit", response_model=PsychologicalProfileResponse)
def submit_my_questionnaire(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = questionnaire_service.submit(db, current_user)
    return PsychologicalProfileResponse.from_model(profile)
