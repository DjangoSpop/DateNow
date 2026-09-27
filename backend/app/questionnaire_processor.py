"""
Process questionnaire responses and calculate psychological scores.

Pure, deterministic, standard-library only (no app config / DB imports). Item
keying (trait + reverse flag) comes from ``app.questionnaire_catalog`` - the
single source of truth. The API layer should call
``questionnaire_catalog.score_questionnaire`` (validate + score); the helpers
here are tolerant of bad input (never raise on wrong answer types - a bad
answer is treated as missing) and return ``None`` when a dimension has no
usable answer, so "missing" is never confused with a genuine low score.

Scoring rules (questionnaire version 2026.1)
--------------------------------------------
Scale items are 1..5. A 1..5 item mean ``m`` is mapped to 0..100 as
``(m - 1) / 4 * 100`` (1 -> 0, 3 -> 50, 5 -> 100), computed exactly and rounded
half-up to 1 decimal.

- Big Five (``bf_*``, IPIP-50 markers, 44 items): reverse-keyed items are
  scored ``6 - answer``; trait score = scaled mean of the answered items.
- Values (0..100):
    family_orientation   = mean(val_1 scaled, val_6 mapped)
                           val_6: Definitely 100, Probably 75, Not sure 50,
                           Probably not 25, Definitely not 0
    career_ambition      = val_2 scaled
    adventure_seeking    = 0.75 * val_3 scaled + 0.25 * val_7 mapped
                           (val_7 "ideal weekend" as a novelty-seeking hint:
                           Outdoor adventures 100, Cultural events 75, Social
                           gatherings 50, Personal projects 25, Relaxing at
                           home 0). If one part is missing the other is used.
    social_consciousness = val_4 scaled
    spiritual_religious  = val_5 scaled
- Love languages: ll_1..ll_5 scaled individually (words, acts, gifts, time,
  touch).
- communication_style (comm_1) in {direct, diplomatic, emotional, logical}.
- conflict_resolution (comm_2) in {direct, reflective, collaborative, avoidant}.
  comm_3 (repair preference) is collected and stored but not scored in 2026.1.
- attachment_style in {secure, anxious, avoidant, fearful-avoidant}, from the
  two ECR-style dimensions on the 1..5 scale:
    anxiety   = mean(att_2, att_4)
    avoidance = mean(6 - att_1, 6 - att_3, att_5 mapped)
                att_5: "Be very close and connected" 1, "Maintain some
                independence" 3 (independence is not avoidance), "Keep
                emotional distance" 5, "It depends on the situation" -> no
                information (excluded)
  high = strictly above the scale midpoint 3 (a neutral 3 counts as low).
    low anxiety  + low avoidance  -> secure
    high anxiety + low avoidance  -> anxious
    low anxiety  + high avoidance -> avoidant
    high anxiety + high avoidance -> fearful-avoidant
  Requires at least one anxiety item and one avoidance item, else ``None``.
- Unscored but stored: val_7 (beyond the adventure weight), comm_3, rg_*,
  pref_*, verify_* (used only by ``verify_authenticity``).

Audit of the previous implementation (fixed here)
-------------------------------------------------
- Scaling ``(avg/5)*100`` mapped 1..5 to 20..100 (all-1s scored 20, not 0).
- Missing answers returned 0.0 - indistinguishable from a real minimum.
- Scale answers were not range/type checked: ``True`` counted as 1, 100 gave
  a score of 2000 (or negative after reverse keying).
- comm_1 was stored verbatim (e.g. "Direct and straightforward", or any
  client-sent string) instead of a fixed vocabulary; default "diplomatic"
  masked missing data.
- comm_2 / att_5 used substring heuristics and ``.lower()`` (crash on
  non-strings). att_5 was always answered in the UI, so att_1..att_4 were never
  used; "Maintain some independence" and "It depends..." both mapped to
  "secure", making "anxious"/"fearful-avoidant" unreachable. The att_1/att_2
  fallback labelled a neutral 3/3 respondent "fearful-avoidant", ignored
  att_3/att_4, and could raise TypeError on string answers.
- val_7, comm_3, att_3, att_4 were ignored; value scale items used the same
  20..100 scaling.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from app.questionnaire_catalog import QUESTIONS, ROLE_BIG_FIVE, SCALE_MAX, SCALE_MIN

BIG_FIVE_TRAITS: Tuple[str, ...] = (
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
)


def _build_big_five_keys() -> Dict[str, Dict[str, bool]]:
    keys: Dict[str, Dict[str, bool]] = {t: {} for t in BIG_FIVE_TRAITS}
    for q in QUESTIONS.values():
        if q.role == ROLE_BIG_FIVE:
            keys[q.trait][q.id] = q.reverse  # type: ignore[index]
    return keys


# trait -> {question_id: is_reverse}; derived from the catalog.
BIG_FIVE_KEYS: Dict[str, Dict[str, bool]] = _build_big_five_keys()

VALUE_DIMENSIONS: Tuple[str, ...] = (
    "family_orientation", "career_ambition", "adventure_seeking",
    "social_consciousness", "spiritual_religious",
)

LOVE_LANGUAGE_ITEMS: Dict[str, str] = {
    "words": "ll_1", "acts": "ll_2", "gifts": "ll_3", "time": "ll_4", "touch": "ll_5",
}

VAL_6_SCORES: Dict[str, int] = {
    "Definitely": 100, "Probably": 75, "Not sure": 50,
    "Probably not": 25, "Definitely not": 0,
}

VAL_7_ADVENTURE_SCORES: Dict[str, int] = {
    "Outdoor adventures and activities": 100,
    "Cultural events and entertainment": 75,
    "Social gatherings with friends": 50,
    "Working on personal projects": 25,
    "Relaxing at home with loved ones": 0,
}

COMMUNICATION_STYLES: Tuple[str, ...] = ("direct", "diplomatic", "emotional", "logical")
COMM_1_STYLES: Dict[str, str] = {
    "Direct and straightforward": "direct",
    "Diplomatic and tactful": "diplomatic",
    "Emotional and expressive": "emotional",
    "Logical and analytical": "logical",
}

CONFLICT_STYLES: Tuple[str, ...] = ("direct", "reflective", "collaborative", "avoidant")
COMM_2_CONFLICT: Dict[str, str] = {
    "Address it directly and immediately": "direct",
    "Take time to cool down first": "reflective",
    "Seek compromise and middle ground": "collaborative",
    "Avoid confrontation when possible": "avoidant",
}

ATTACHMENT_STYLES: Tuple[str, ...] = ("secure", "anxious", "avoidant", "fearful-avoidant")
ATT_5_AVOIDANCE: Dict[str, Optional[int]] = {
    "Be very close and connected": 1,
    "Maintain some independence": 3,
    "Keep emotional distance": 5,
    "It depends on the situation": None,
}
ATTACHMENT_ANXIETY_ITEMS: Tuple[str, ...] = ("att_2", "att_4")
ATTACHMENT_AVOIDANCE_REVERSED_ITEMS: Tuple[str, ...] = ("att_1", "att_3")
ATTACHMENT_MIDPOINT = Fraction(3)

_MIDPOINT_SHIFT = SCALE_MIN
_SPAN = SCALE_MAX - SCALE_MIN


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _round1(value: Fraction) -> float:
    """Exact half-up rounding to one decimal."""
    d = Decimal(value.numerator) / Decimal(value.denominator)
    return float(d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _scale_answer(responses: Mapping[str, Any], qid: str) -> Optional[int]:
    """A valid 1..5 integer answer, or None (missing / wrong type / out of range)."""
    value = responses.get(qid)
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and SCALE_MIN <= value <= SCALE_MAX:
        return value
    return None


def _choice_answer(responses: Mapping[str, Any], qid: str, mapping: Mapping[str, Any]) -> Any:
    value = responses.get(qid)
    if isinstance(value, str):
        return mapping.get(value)
    return None


def _to_percent(mean: Fraction) -> Fraction:
    return (mean - _MIDPOINT_SHIFT) / _SPAN * 100


def _mean(values: Sequence[Fraction]) -> Optional[Fraction]:
    return sum(values, Fraction(0)) / len(values) if values else None


def _safe_mapping(responses: Any) -> Mapping[str, Any]:
    return responses if isinstance(responses, Mapping) else {}


def _scaled_item(responses: Mapping[str, Any], qid: str) -> Optional[Fraction]:
    v = _scale_answer(responses, qid)
    return None if v is None else _to_percent(Fraction(v))


# ---------------------------------------------------------------------------
# public scoring functions
# ---------------------------------------------------------------------------

def calculate_big_five_score(responses: Dict[str, Any], trait: str) -> Optional[float]:
    """Big Five trait score 0..100 (1 decimal), or None if no valid item answers.

    Raises ValueError for an unknown trait name (programming error).
    """
    if trait not in BIG_FIVE_KEYS:
        raise ValueError(f"unknown Big Five trait: {trait!r}")
    responses = _safe_mapping(responses)
    keyed: List[Fraction] = []
    for qid, is_reverse in BIG_FIVE_KEYS[trait].items():
        v = _scale_answer(responses, qid)
        if v is not None:
            keyed.append(Fraction((SCALE_MIN + SCALE_MAX) - v if is_reverse else v))
    mean = _mean(keyed)
    return None if mean is None else _round1(_to_percent(mean))


def _value_fraction(responses: Mapping[str, Any], value: str) -> Optional[Fraction]:
    if value == "family_orientation":
        parts = [_scaled_item(responses, "val_1")]
        v6 = _choice_answer(responses, "val_6", VAL_6_SCORES)
        parts.append(None if v6 is None else Fraction(v6))
        return _mean([p for p in parts if p is not None])
    if value == "adventure_seeking":
        v3 = _scaled_item(responses, "val_3")
        v7raw = _choice_answer(responses, "val_7", VAL_7_ADVENTURE_SCORES)
        v7 = None if v7raw is None else Fraction(v7raw)
        if v3 is not None and v7 is not None:
            return Fraction(3, 4) * v3 + Fraction(1, 4) * v7
        return v3 if v3 is not None else v7
    single = {
        "career_ambition": "val_2",
        "social_consciousness": "val_4",
        "spiritual_religious": "val_5",
    }
    return _scaled_item(responses, single[value])


def calculate_value_score(responses: Dict[str, Any], value: str) -> Optional[float]:
    """Value dimension score 0..100 (1 decimal), or None if unanswered."""
    if value not in VALUE_DIMENSIONS:
        raise ValueError(f"unknown value dimension: {value!r}")
    result = _value_fraction(_safe_mapping(responses), value)
    return None if result is None else _round1(result)


def calculate_love_language_score(responses: Dict[str, Any], language: str) -> Optional[float]:
    """Love language score 0..100 (1 decimal), or None if unanswered."""
    if language not in LOVE_LANGUAGE_ITEMS:
        raise ValueError(f"unknown love language: {language!r}")
    result = _scaled_item(_safe_mapping(responses), LOVE_LANGUAGE_ITEMS[language])
    return None if result is None else _round1(result)


def determine_communication_style(responses: Dict[str, Any]) -> Optional[str]:
    """One of COMMUNICATION_STYLES, or None if comm_1 is missing/unrecognized."""
    return _choice_answer(_safe_mapping(responses), "comm_1", COMM_1_STYLES)


def determine_conflict_resolution(responses: Dict[str, Any]) -> Optional[str]:
    """One of CONFLICT_STYLES, or None if comm_2 is missing/unrecognized."""
    return _choice_answer(_safe_mapping(responses), "comm_2", COMM_2_CONFLICT)


def attachment_dimensions(responses: Dict[str, Any]) -> Tuple[Optional[Fraction], Optional[Fraction]]:
    """(anxiety, avoidance) means on the 1..5 scale, each None if no items."""
    responses = _safe_mapping(responses)
    anxiety_items = [Fraction(v) for v in
                     (_scale_answer(responses, q) for q in ATTACHMENT_ANXIETY_ITEMS)
                     if v is not None]
    avoidance_items = [Fraction((SCALE_MIN + SCALE_MAX) - v) for v in
                       (_scale_answer(responses, q) for q in ATTACHMENT_AVOIDANCE_REVERSED_ITEMS)
                       if v is not None]
    a5 = _choice_answer(responses, "att_5", ATT_5_AVOIDANCE)
    if a5 is not None:
        avoidance_items.append(Fraction(a5))
    return _mean(anxiety_items), _mean(avoidance_items)


def determine_attachment_style(responses: Dict[str, Any]) -> Optional[str]:
    """One of ATTACHMENT_STYLES (rule in the module docstring), or None."""
    anxiety, avoidance = attachment_dimensions(responses)
    if anxiety is None or avoidance is None:
        return None
    high_anx = anxiety > ATTACHMENT_MIDPOINT
    high_avoid = avoidance > ATTACHMENT_MIDPOINT
    if high_anx and high_avoid:
        return "fearful-avoidant"
    if high_anx:
        return "anxious"
    if high_avoid:
        return "avoidant"
    return "secure"


def process_questionnaire(responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the psychological profile from (ideally validated) responses.

    Score fields are None where the relevant answers are missing/invalid.
    Raw responses are returned (shallow copy) under ``questionnaire_responses``.
    """
    safe = _safe_mapping(responses)
    return {
        # Big Five
        "openness": calculate_big_five_score(safe, "openness"),
        "conscientiousness": calculate_big_five_score(safe, "conscientiousness"),
        "extraversion": calculate_big_five_score(safe, "extraversion"),
        "agreeableness": calculate_big_five_score(safe, "agreeableness"),
        "neuroticism": calculate_big_five_score(safe, "neuroticism"),
        # Values
        "family_orientation": calculate_value_score(safe, "family_orientation"),
        "career_ambition": calculate_value_score(safe, "career_ambition"),
        "adventure_seeking": calculate_value_score(safe, "adventure_seeking"),
        "social_consciousness": calculate_value_score(safe, "social_consciousness"),
        "spiritual_religious": calculate_value_score(safe, "spiritual_religious"),
        # Communication
        "communication_style": determine_communication_style(safe),
        "conflict_resolution": determine_conflict_resolution(safe),
        # Love languages
        "love_language_words": calculate_love_language_score(safe, "words"),
        "love_language_acts": calculate_love_language_score(safe, "acts"),
        "love_language_gifts": calculate_love_language_score(safe, "gifts"),
        "love_language_time": calculate_love_language_score(safe, "time"),
        "love_language_touch": calculate_love_language_score(safe, "touch"),
        # Attachment
        "attachment_style": determine_attachment_style(safe),
        # Raw responses
        "questionnaire_responses": dict(safe),
    }


def verify_authenticity(responses: Dict[str, Any]) -> tuple[bool, str]:
    """
    Heuristic anti-bot check on the verification free-text answers.
    Advisory only; not part of answer validation.

    Returns:
        (is_authentic, reason)
    """
    responses = _safe_mapping(responses)
    verify_1 = responses.get("verify_1")
    verify_2 = responses.get("verify_2")
    if not isinstance(verify_1, str) or not isinstance(verify_2, str):
        return (False, "Verification questions not answered")

    verify_1 = verify_1.strip()
    verify_2 = verify_2.strip()

    if len(verify_1) < 20:
        return (False, "First verification answer too short")
    if len(verify_2) < 20:
        return (False, "Second verification answer too short")

    if verify_1.isupper() or verify_2.isupper():
        return (False, "Suspicious formatting detected")

    common_words = {"i", "to", "the", "a", "and", "for", "with", "my", "me", "we"}
    has_common_1 = any(word in common_words for word in verify_1.lower().split())
    has_common_2 = any(word in common_words for word in verify_2.lower().split())
    if not has_common_1 or not has_common_2:
        return (False, "Answers do not appear natural")

    return (True, "Verification successful")
