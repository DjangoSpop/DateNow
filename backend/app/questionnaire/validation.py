"""Definition export and answer validation (pure, stdlib only)."""
from __future__ import annotations

from typing import Any, Dict, List

from .bank import QUESTIONNAIRE_VERSION, QUESTIONS, QUESTIONS_BY_ID, SCALE, SECTIONS, Question


class AnswerValidationError(ValueError):
    """Raised when answers are invalid or incomplete.

    ``errors`` maps question id -> human readable message, listing every
    offending id (not just the first). Missing required answers use the
    message ``"required"`` (matches the contract's QUESTIONNAIRE_INCOMPLETE).
    """

    def __init__(self, errors: Dict[str, str]):
        self.errors: Dict[str, str] = dict(errors)
        super().__init__(f"invalid questionnaire answers: {sorted(self.errors)}")


def _question_json(q: Question) -> Dict[str, Any]:
    out: Dict[str, Any] = {"id": q.id, "text": q.text, "type": q.type, "required": q.required}
    if q.type == SCALE:
        out["scale"] = {"min": q.scale_min, "max": q.scale_max, "labels": dict(q.labels)}
    else:
        out["options"] = [{"value": o.value, "label": o.label} for o in q.options]
    return out


def get_definition() -> Dict[str, Any]:
    """JSON-serializable questionnaire definition (GET /questionnaire shape).

    A fresh structure is built on every call so callers may mutate it freely.
    """
    return {
        "version": QUESTIONNAIRE_VERSION,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "estimated_minutes": s.estimated_minutes,
                "questions": [_question_json(q) for q in s.questions],
            }
            for s in SECTIONS
        ],
    }


def question_ids() -> List[str]:
    """All question ids in presentation order."""
    return [q.id for q in QUESTIONS]


def total_required() -> int:
    return sum(1 for q in QUESTIONS if q.required)


def _check(q: Question, value: Any) -> str | None:
    """Return an error message for ``value`` or None if valid."""
    if q.type == SCALE:
        if isinstance(value, bool):
            return "must be an integer, not a boolean"
        if not isinstance(value, int):
            return f"must be an integer between {q.scale_min} and {q.scale_max}"
        if not q.scale_min <= value <= q.scale_max:
            return f"must be between {q.scale_min} and {q.scale_max}"
        return None
    if not isinstance(value, str):
        return "must be one of the option values"
    if value not in q.option_values:
        return "invalid option; expected one of: " + ", ".join(q.option_values)
    return None


def validate_answers(answers: dict) -> dict:
    """Validate a (possibly partial) answers mapping.

    Returns a normalized copy: keys in presentation order, scale values as
    plain ``int``, choice values as plain ``str``. Raises
    ``AnswerValidationError`` listing every bad id (unknown ids, wrong types,
    out-of-range scale values, booleans, floats, unknown option values).
    """
    if not isinstance(answers, dict):
        raise AnswerValidationError({"answers": "must be an object mapping question id to answer"})

    errors: Dict[str, str] = {}
    for key, value in answers.items():
        q = QUESTIONS_BY_ID.get(key) if isinstance(key, str) else None
        if q is None:
            errors[str(key)] = "unknown question id"
            continue
        msg = _check(q, value)
        if msg is not None:
            errors[key] = msg
    if errors:
        raise AnswerValidationError(errors)

    normalized: Dict[str, Any] = {}
    for q in QUESTIONS:
        if q.id in answers:
            v = answers[q.id]
            normalized[q.id] = int(v) if q.type == SCALE else str(v)
    return normalized


def missing_required(answers: dict) -> List[str]:
    """Required question ids that are absent (or None) in ``answers``, in presentation order.

    Does not validate values; call ``validate_answers`` for that.
    """
    answers = answers or {}
    return [q.id for q in QUESTIONS if q.required and answers.get(q.id) is None]
