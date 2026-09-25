"""Server-owned questionnaire: question bank, validation and scoring.

Pure Python (stdlib only): no database, web framework or I/O, so it can be
unit-tested in isolation. See ``docs/QUESTIONNAIRE.md``.

Public interface::

    QUESTIONNAIRE_VERSION
    AnswerValidationError          # ValueError with .errors: dict[question_id, message]
    get_definition() -> dict       # GET /questionnaire body
    question_ids() -> list[str]    # presentation order
    total_required() -> int
    validate_answers(answers) -> dict
    missing_required(answers) -> list[str]
    score(answers) -> dict         # PsychologicalProfile column values
"""
from .bank import QUESTIONNAIRE_VERSION
from .scoring import (
    ATTACHMENT_STYLES,
    COMMUNICATION_STYLES,
    CONFLICT_RESOLUTION_STYLES,
    PROFILE_KEYS,
    score,
)
from .validation import (
    AnswerValidationError,
    get_definition,
    missing_required,
    question_ids,
    total_required,
    validate_answers,
)

__all__ = [
    "QUESTIONNAIRE_VERSION",
    "AnswerValidationError",
    "get_definition",
    "question_ids",
    "total_required",
    "validate_answers",
    "missing_required",
    "score",
    "COMMUNICATION_STYLES",
    "CONFLICT_RESOLUTION_STYLES",
    "ATTACHMENT_STYLES",
    "PROFILE_KEYS",
]
