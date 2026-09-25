"""Deterministic scorer for questionnaire version ``ipip-v1``.

All numeric outputs are on a 0-100 scale, rounded half-up to one decimal.
Arithmetic is done with exact fractions so results never depend on float
summation order. See ``docs/QUESTIONNAIRE.md`` for the rules.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any, Dict, Iterable, List

from .bank import QUESTIONS, QUESTIONS_BY_ID, SCALE
from .validation import AnswerValidationError, missing_required, validate_answers

BIG_FIVE = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

# Numeric value columns and the scale items feeding them.
VALUE_TRAITS = (
    "family_orientation", "career_ambition", "adventure_seeking",
    "social_consciousness", "spiritual_religious",
)
LOVE_LANGUAGE_COLUMNS = (
    "love_language_words", "love_language_acts", "love_language_gifts",
    "love_language_time", "love_language_touch",
)

# Single-choice value items -> 0-100 score.
CHOICE_SCORES: Dict[str, Dict[str, int]] = {
    "val_6": {
        "definitely": 100,
        "probably": 75,
        "not_sure": 50,
        "probably_not": 25,
        "definitely_not": 0,
    },
}

# Categorical vocabularies.
COMMUNICATION_STYLES = ("direct", "diplomatic", "emotional", "logical")
CONFLICT_RESOLUTION_STYLES = ("direct", "reflective", "collaborative", "avoidant")
ATTACHMENT_STYLES = ("secure", "anxious", "avoidant", "fearful_avoidant")

COMM_1_TO_STYLE = {v: v for v in COMMUNICATION_STYLES}
COMM_2_TO_CONFLICT = {
    "address_directly": "direct",
    "cool_down_first": "reflective",
    "seek_compromise": "collaborative",
    "avoid_confrontation": "avoidant",
}
# Attachment dimension means above this (on the 1-5 scale) count as "high".
ATTACHMENT_HIGH_THRESHOLD = Fraction(3)

PROFILE_KEYS = (
    *BIG_FIVE, *VALUE_TRAITS, "communication_style", "conflict_resolution",
    *LOVE_LANGUAGE_COLUMNS, "attachment_style", "questionnaire_responses",
)


def _round1(x: Fraction) -> float:
    d = Decimal(x.numerator) / Decimal(x.denominator)
    return float(d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _keyed(q_id: str, answers: Dict[str, Any]) -> Fraction:
    """Answer on its trait's direction (reverse items flipped: 6 - x on 1-5)."""
    q = QUESTIONS_BY_ID[q_id]
    v = answers[q_id]
    if q.reverse:
        v = q.scale_min + q.scale_max - v
    return Fraction(v)


def _scale_to_100(mean: Fraction, lo: int = 1, hi: int = 5) -> Fraction:
    """Map a mean on [lo, hi] to [0, 100]: (mean - lo) / (hi - lo) * 100."""
    return (mean - lo) / (hi - lo) * 100


def _mean(xs: Iterable[Fraction]) -> Fraction:
    xs = list(xs)
    return sum(xs, Fraction(0)) / len(xs)


def _items(trait: str) -> List[str]:
    return [q.id for q in QUESTIONS if q.type == SCALE and q.trait == trait]


def _scale_trait_score(trait: str, answers: Dict[str, Any]) -> Fraction:
    return _scale_to_100(_mean(_keyed(i, answers) for i in _items(trait)))


def _value_score(trait: str, answers: Dict[str, Any]) -> Fraction:
    parts = [_scale_to_100(_keyed(i, answers)) for i in _items(trait)]
    for q_id, table in CHOICE_SCORES.items():
        if QUESTIONS_BY_ID[q_id].trait == trait:
            parts.append(Fraction(table[answers[q_id]]))
    return _mean(parts)


def attachment_dimensions(answers: Dict[str, Any]) -> Dict[str, Fraction]:
    """Mean anxiety (att_2, att_4) and avoidance (reverse att_1, reverse att_3) on 1-5."""
    return {
        "anxiety": _mean(_keyed(i, answers) for i in _items("attachment_anxiety")),
        "avoidance": _mean(_keyed(i, answers) for i in _items("attachment_avoidance")),
    }


def classify_attachment(answers: Dict[str, Any]) -> str:
    """Coarse heuristic, NOT a clinical assessment.

    anxiety high   := mean(att_2, att_4) > 3
    avoidance high := mean(6-att_1, 6-att_3) > 3, or exactly 3 with att_5 == "keep_distance"
    (low, low) secure; (high, low) anxious; (low, high) avoidant; (high, high) fearful_avoidant.
    """
    dims = attachment_dimensions(answers)
    anxious = dims["anxiety"] > ATTACHMENT_HIGH_THRESHOLD
    avoidant = dims["avoidance"] > ATTACHMENT_HIGH_THRESHOLD or (
        dims["avoidance"] == ATTACHMENT_HIGH_THRESHOLD and answers["att_5"] == "keep_distance"
    )
    if anxious and avoidant:
        return "fearful_avoidant"
    if anxious:
        return "anxious"
    if avoidant:
        return "avoidant"
    return "secure"


def score(answers: dict) -> dict:
    """Score a complete, valid answer set.

    Raises ``AnswerValidationError`` (errors keyed by question id) if any
    answer is invalid or any required answer is missing ("required").
    Returns keys exactly matching the PsychologicalProfile columns listed in
    ``PROFILE_KEYS``; ``questionnaire_responses`` is a new dict (normalized copy).
    """
    errors: Dict[str, str] = {}
    try:
        normalized = validate_answers(answers)
    except AnswerValidationError as exc:
        errors.update(exc.errors)
        normalized = {}
    if isinstance(answers, dict):
        for q_id in missing_required(answers):
            errors.setdefault(q_id, "required")
    if errors:
        raise AnswerValidationError(errors)

    a = normalized
    result: Dict[str, Any] = {}
    for trait in BIG_FIVE:
        result[trait] = _round1(_scale_trait_score(trait, a))
    for trait in VALUE_TRAITS:
        result[trait] = _round1(_value_score(trait, a))
    result["communication_style"] = COMM_1_TO_STYLE[a["comm_1"]]
    result["conflict_resolution"] = COMM_2_TO_CONFLICT[a["comm_2"]]
    for col in LOVE_LANGUAGE_COLUMNS:
        result[col] = _round1(_scale_trait_score(col, a))
    result["attachment_style"] = classify_attachment(a)
    result["questionnaire_responses"] = dict(a)
    return {k: result[k] for k in PROFILE_KEYS}
