"""Deprecated backward-compatibility shim.

The questionnaire bank, validation and scoring now live in
``app.questionnaire``. This module only re-exports that API under the old
entry point name. The legacy scorer (20-100 score range, raw label text as
categorical values, substring matching) and the ``verify_authenticity``
free-text heuristic were removed; see ``docs/QUESTIONNAIRE.md``.

New code should import from ``app.questionnaire`` directly.
"""
from app.questionnaire import (  # noqa: F401
    QUESTIONNAIRE_VERSION,
    AnswerValidationError,
    get_definition,
    missing_required,
    question_ids,
    score,
    total_required,
    validate_answers,
)

# Old name. Unlike the legacy function it requires complete, valid answers
# (option *values*, not label text) and raises AnswerValidationError otherwise.
process_questionnaire = score
