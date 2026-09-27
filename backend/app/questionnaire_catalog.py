"""
Server-side questionnaire catalog, answer validation and the scoring entry point.

This module is the single source of truth for the onboarding questionnaire
(version ``QUESTIONNAIRE_VERSION``). It is pure Python (standard library only):
it must never import ``app.config``, ``app.database`` or ``app.models`` so it can
be imported and unit-tested without environment variables or a database.

Public interface
----------------
- ``QUESTIONNAIRE_VERSION``
- ``get_questionnaire_definition() -> dict``  (public JSON shape, see API contract)
- ``QuestionnaireValidationError`` (``.errors: list[{"question_id", "message"}]``)
- ``validate_partial_answers(answers) -> dict``  (draft save, ``PUT /onboarding``)
- ``validate_complete_answers(answers) -> dict`` (submit)
- ``score_questionnaire(answers) -> dict``       (submit: validate + score)

Provenance
----------
Question ids, texts, types, options and sections are ported verbatim from
``frontend/src/data/questionnaireData.ts`` (73 questions in 8 sections; there
are no ``multiple_choice`` questions in the UI today, but the validator supports
the type).

The ``bf_*`` items are the IPIP 50-item Big-Five factor markers (Goldberg, 1992;
ipip.ori.org), *not* the BFI-44 as the frontend comment claims. The UI keeps 44
of the 50 items, grouped by trait and renumbered ``bf_1..bf_44``. Omitted
IPIP-50 items: #41 "Don't mind being the center of attention" (E+),
#46 "Am quiet around strangers" (E-), #44 "Get irritated easily" (N+),
#49 "Often feel blue" (N+), #40 "Use difficult words" (O+),
#50 "Am full of ideas" (O+). E, N and O therefore use 8 items, A and C use 10.
The published IPIP item number of every retained item is kept in the internal
``ipip_item`` field. Reverse keys match both the UI ``reverse`` flags and the
published IPIP keying (Neuroticism is keyed as the reverse of IPIP Emotional
Stability).

Required-question policy (version 2026.1)
-----------------------------------------
Every question is required. Rationale:
- scale / single_choice: the web UI blocks "Next" until an answer exists, and
  the scoring model needs every scored item; unscored choice items (goals,
  preferences) feed matching/deal-breakers later and each sensitive one has an
  opt-out option (e.g. "Prefer not to say", "Not sure yet").
- text (``verify_1``, ``verify_2``): required because they are the anti-bot
  verification step and ``verify_authenticity`` depends on them. A draft may
  hold an empty string, but a whitespace-only answer counts as *missing* on
  submit. The UI's "minimum 20 characters" hint is advisory and is NOT enforced
  by validation (the contract's question shape has no ``min_length``);
  ``questionnaire_processor.verify_authenticity`` applies that heuristic
  separately.

Internal metadata (trait, reverse keying, IPIP item number, scoring role) lives
on ``Question`` but is never emitted by ``get_questionnaire_definition``.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

QUESTIONNAIRE_VERSION = "2026.1"

SCALE_MIN = 1
SCALE_MAX = 5
TEXT_MAX_LENGTH = 1000
MAX_ANSWER_KEYS = 200
_MAX_ID_ECHO = 64  # truncate unknown ids echoed back in error messages
ROOT_ERROR_ID = "__all__"

QUESTION_TYPES = ("scale", "single_choice", "multiple_choice", "text")

# Scoring roles (internal): how the processor uses an item.
ROLE_BIG_FIVE = "big_five"
ROLE_VALUE = "value"
ROLE_LOVE_LANGUAGE = "love_language"
ROLE_COMMUNICATION = "communication_style"
ROLE_CONFLICT = "conflict_resolution"
ROLE_ATTACHMENT = "attachment"
ROLE_UNSCORED = "unscored"  # collected and stored, not part of the profile scores

AGREE_LABELS = ("Strongly disagree", "Strongly agree")
IMPORTANCE_LABELS = ("Not at all important", "Extremely important")
AMOUNT_LABELS = ("Not at all", "Very much")


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: str
    section: str
    options: Optional[Tuple[str, ...]] = None
    required: bool = True
    scale_labels: Optional[Tuple[str, str]] = None
    max_length: Optional[int] = None
    max_selections: Optional[int] = None
    # ---- internal-only metadata (never exposed) ----
    trait: Optional[str] = None
    reverse: bool = False
    role: str = ROLE_UNSCORED
    ipip_item: Optional[int] = None


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    description: str
    question_ids: Tuple[str, ...]


def _bf(qid: str, text: str, trait: str, ipip: int, reverse: bool = False) -> Question:
    return Question(
        id=qid, text=text, type="scale", section="personality",
        scale_labels=AGREE_LABELS, trait=trait, reverse=reverse,
        role=ROLE_BIG_FIVE, ipip_item=ipip,
    )


def _scale(qid: str, text: str, section: str, trait: str, role: str,
           labels: Tuple[str, str] = AGREE_LABELS) -> Question:
    return Question(id=qid, text=text, type="scale", section=section,
                    scale_labels=labels, trait=trait, role=role)


def _choice(qid: str, text: str, section: str, trait: str, role: str,
            options: Tuple[str, ...]) -> Question:
    return Question(id=qid, text=text, type="single_choice", section=section,
                    options=options, trait=trait, role=role)


def _text(qid: str, text: str, section: str) -> Question:
    return Question(id=qid, text=text, type="text", section=section,
                    max_length=TEXT_MAX_LENGTH, trait="authenticity")


E, A, C, N, O = "extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"

_QUESTIONS: Tuple[Question, ...] = (
    # --- Personality: IPIP-50 markers (44 retained) ---
    _bf("bf_1", "I am the life of the party", E, 1),
    _bf("bf_2", "I don't talk a lot", E, 6, reverse=True),
    _bf("bf_3", "I feel comfortable around people", E, 11),
    _bf("bf_4", "I keep in the background", E, 16, reverse=True),
    _bf("bf_5", "I start conversations", E, 21),
    _bf("bf_6", "I have little to say", E, 26, reverse=True),
    _bf("bf_7", "I talk to a lot of different people at parties", E, 31),
    _bf("bf_8", "I don't like to draw attention to myself", E, 36, reverse=True),
    _bf("bf_9", "I feel little concern for others", A, 2, reverse=True),
    _bf("bf_10", "I am interested in people", A, 7),
    _bf("bf_11", "I insult people", A, 12, reverse=True),
    _bf("bf_12", "I sympathize with others' feelings", A, 17),
    _bf("bf_13", "I am not interested in other people's problems", A, 22, reverse=True),
    _bf("bf_14", "I have a soft heart", A, 27),
    _bf("bf_15", "I am not really interested in others", A, 32, reverse=True),
    _bf("bf_16", "I take time out for others", A, 37),
    _bf("bf_17", "I feel others' emotions", A, 42),
    _bf("bf_18", "I make people feel at ease", A, 47),
    _bf("bf_19", "I am always prepared", C, 3),
    _bf("bf_20", "I leave my belongings around", C, 8, reverse=True),
    _bf("bf_21", "I pay attention to details", C, 13),
    _bf("bf_22", "I make a mess of things", C, 18, reverse=True),
    _bf("bf_23", "I get chores done right away", C, 23),
    _bf("bf_24", "I often forget to put things back in their proper place", C, 28, reverse=True),
    _bf("bf_25", "I like order", C, 33),
    _bf("bf_26", "I shirk my duties", C, 38, reverse=True),
    _bf("bf_27", "I follow a schedule", C, 43),
    _bf("bf_28", "I am exacting in my work", C, 48),
    _bf("bf_29", "I get stressed out easily", N, 4),
    _bf("bf_30", "I am relaxed most of the time", N, 9, reverse=True),
    _bf("bf_31", "I worry about things", N, 14),
    _bf("bf_32", "I seldom feel blue", N, 19, reverse=True),
    _bf("bf_33", "I am easily disturbed", N, 24),
    _bf("bf_34", "I get upset easily", N, 29),
    _bf("bf_35", "I change my mood a lot", N, 34),
    _bf("bf_36", "I have frequent mood swings", N, 39),
    _bf("bf_37", "I have a rich vocabulary", O, 5),
    _bf("bf_38", "I have difficulty understanding abstract ideas", O, 10, reverse=True),
    _bf("bf_39", "I have a vivid imagination", O, 15),
    _bf("bf_40", "I am not interested in abstract ideas", O, 20, reverse=True),
    _bf("bf_41", "I have excellent ideas", O, 25),
    _bf("bf_42", "I do not have a good imagination", O, 30, reverse=True),
    _bf("bf_43", "I am quick to understand things", O, 35),
    _bf("bf_44", "I spend time reflecting on things", O, 45),
    # --- Values ---
    _scale("val_1", "How important is having a family in your future?", "values",
           "family_orientation", ROLE_VALUE, IMPORTANCE_LABELS),
    _scale("val_2", "How important is career success and professional achievement to you?",
           "values", "career_ambition", ROLE_VALUE, IMPORTANCE_LABELS),
    _scale("val_3", "How much do you value adventure and new experiences?", "values",
           "adventure_seeking", ROLE_VALUE, AMOUNT_LABELS),
    _scale("val_4", "How important is making a positive impact on society?", "values",
           "social_consciousness", ROLE_VALUE, IMPORTANCE_LABELS),
    _scale("val_5", "How important is spirituality or religion in your life?", "values",
           "spiritual_religious", ROLE_VALUE, IMPORTANCE_LABELS),
    _choice("val_6", "I prefer to have children:", "values", "family_orientation", ROLE_VALUE,
            ("Definitely", "Probably", "Not sure", "Probably not", "Definitely not")),
    _choice("val_7", "My ideal weekend involves:", "values", "adventure_seeking", ROLE_VALUE,
            ("Outdoor adventures and activities",
             "Cultural events and entertainment",
             "Relaxing at home with loved ones",
             "Social gatherings with friends",
             "Working on personal projects")),
    # --- Love languages ---
    _scale("ll_1", "I feel most loved when my partner tells me they appreciate me", "love",
           "love_language_words", ROLE_LOVE_LANGUAGE),
    _scale("ll_2", "I feel most loved when my partner does thoughtful things for me", "love",
           "love_language_acts", ROLE_LOVE_LANGUAGE),
    _scale("ll_3", "I feel most loved when my partner gives me meaningful gifts", "love",
           "love_language_gifts", ROLE_LOVE_LANGUAGE),
    _scale("ll_4", "I feel most loved when my partner spends quality time with me", "love",
           "love_language_time", ROLE_LOVE_LANGUAGE),
    _scale("ll_5", "I feel most loved through physical touch and affection", "love",
           "love_language_touch", ROLE_LOVE_LANGUAGE),
    # --- Communication ---
    _choice("comm_1", "How do you prefer to communicate?", "communication",
            "communication_style", ROLE_COMMUNICATION,
            ("Direct and straightforward", "Diplomatic and tactful",
             "Emotional and expressive", "Logical and analytical")),
    _choice("comm_2", "When there is conflict, I tend to:", "communication",
            "conflict_resolution", ROLE_CONFLICT,
            ("Address it directly and immediately", "Take time to cool down first",
             "Seek compromise and middle ground", "Avoid confrontation when possible")),
    _choice("comm_3", "I prefer to resolve disagreements by:", "communication",
            "conflict_repair", ROLE_UNSCORED,
            ("Working together to find solutions", "Taking turns getting our way",
             "Having deep discussions about feelings",
             "Giving each other space then reconnecting")),
    # --- Attachment ---
    _scale("att_1", "I find it easy to get emotionally close to others", "attachment",
           "attachment_avoidance", ROLE_ATTACHMENT),
    _scale("att_2", "I worry about being abandoned in relationships", "attachment",
           "attachment_anxiety", ROLE_ATTACHMENT),
    _scale("att_3", "I am comfortable depending on others", "attachment",
           "attachment_avoidance", ROLE_ATTACHMENT),
    _scale("att_4", "I worry that others will not value me as much as I value them",
           "attachment", "attachment_anxiety", ROLE_ATTACHMENT),
    _choice("att_5", "In relationships, I prefer to:", "attachment", "attachment_avoidance",
            ROLE_ATTACHMENT,
            ("Be very close and connected", "Maintain some independence",
             "Keep emotional distance", "It depends on the situation")),
    # --- Relationship goals (unscored; used for matching later) ---
    _choice("rg_1", "What are you looking for?", "goals", "relationship_goal", ROLE_UNSCORED,
            ("A serious, long-term relationship", "Dating to see where it goes",
             "Casual dating", "New friends and connections")),
    _choice("rg_2", "How soon do you see yourself settling down?", "goals", "timeline",
            ROLE_UNSCORED,
            ("Ready now", "Within the next year", "In a few years", "Not sure yet",
             "Not looking to settle down")),
    # --- Preferences / deal-breakers (unscored; used for matching later) ---
    _scale("pref_1", "How important is physical attraction to you?", "preferences",
           "physical_importance", ROLE_UNSCORED, IMPORTANCE_LABELS),
    _scale("pref_2",
           "How important is it that your partner shares your religious/spiritual beliefs?",
           "preferences", "spiritual_match", ROLE_UNSCORED, IMPORTANCE_LABELS),
    _scale("pref_3", "How important is intellectual compatibility?", "preferences",
           "intellectual_match", ROLE_UNSCORED, IMPORTANCE_LABELS),
    _choice("pref_4", "Your partner smoking is:", "preferences", "smoking", ROLE_UNSCORED,
            ("A deal breaker", "A concern", "Not ideal but okay", "Not an issue")),
    _choice("pref_5", "How often do you drink alcohol?", "preferences", "drinking",
            ROLE_UNSCORED,
            ("Never", "Rarely", "Socially", "Regularly", "Prefer not to say")),
    # --- Verification (anti-bot free text) ---
    _text("verify_1", "What brings you to DateNow? (Genuine answer required)", "verification"),
    _text("verify_2", "Describe your ideal first date in your own words", "verification"),
)

_SECTION_META: Tuple[Tuple[str, str, str], ...] = (
    ("personality", "Your Personality", "Help us understand who you are"),
    ("values", "Your Values", "What matters most to you in life"),
    ("love", "Love & Connection", "How you give and receive love"),
    ("communication", "Communication Style", "How you express yourself"),
    ("attachment", "Attachment & Bonding", "Your relationship patterns"),
    ("goals", "Relationship Goals", "What you are looking for"),
    ("preferences", "Preferences & Deal-Breakers", "What is important to you"),
    ("verification", "Verification", "Prove you are a real person"),
)

QUESTIONS: Mapping[str, Question] = MappingProxyType({q.id: q for q in _QUESTIONS})
SECTIONS: Tuple[Section, ...] = tuple(
    Section(sid, title, desc, tuple(q.id for q in _QUESTIONS if q.section == sid))
    for sid, title, desc in _SECTION_META
)
REQUIRED_QUESTION_IDS: Tuple[str, ...] = tuple(q.id for q in _QUESTIONS if q.required)


def _check_catalog_integrity() -> None:
    assert len(QUESTIONS) == len(_QUESTIONS), "duplicate question id"
    section_ids = {s.id for s in SECTIONS}
    for q in _QUESTIONS:
        assert q.type in QUESTION_TYPES, q.id
        assert q.section in section_ids, q.id
        if q.type in ("single_choice", "multiple_choice"):
            assert q.options and len(set(q.options)) == len(q.options), q.id
        else:
            assert q.options is None, q.id
        assert (q.type == "scale") == (q.scale_labels is not None), q.id
        assert (q.type == "text") == (q.max_length is not None), q.id


_check_catalog_integrity()


def get_question(question_id: str) -> Optional[Question]:
    return QUESTIONS.get(question_id)


def _public_question(q: Question) -> Dict[str, Any]:
    scale = None
    if q.type == "scale":
        assert q.scale_labels is not None
        scale = {"min": SCALE_MIN, "max": SCALE_MAX,
                 "min_label": q.scale_labels[0], "max_label": q.scale_labels[1]}
    return {
        "id": q.id,
        "text": q.text,
        "type": q.type,
        "required": q.required,
        "options": list(q.options) if q.options is not None else None,
        "scale": scale,
        "max_length": q.max_length,
    }


def get_questionnaire_definition() -> Dict[str, Any]:
    """Public questionnaire definition (fresh dict each call; safe to mutate).

    Exposes only presentation fields; trait, reverse keying, IPIP numbers and
    scoring roles are deliberately omitted.
    """
    return {
        "version": QUESTIONNAIRE_VERSION,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "questions": [_public_question(QUESTIONS[qid]) for qid in s.question_ids],
            }
            for s in SECTIONS
        ],
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class QuestionnaireValidationError(Exception):
    """Raised with every problem found; ``errors`` is a list of
    ``{"question_id": str, "message": str}`` in deterministic order."""

    def __init__(self, errors: List[Dict[str, str]]):
        self.errors = errors
        ids = ", ".join(e["question_id"] for e in errors[:10])
        more = "" if len(errors) <= 10 else f" (+{len(errors) - 10} more)"
        super().__init__(f"Invalid questionnaire answers: {ids}{more}")


def _echo_id(key: str) -> str:
    return key if len(key) <= _MAX_ID_ECHO else key[:_MAX_ID_ECHO] + "..."


def _is_int_value(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _normalize_text(value: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (normalized, error_message)."""
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    for ch in text:
        if ch == "\n":
            continue
        cat = unicodedata.category(ch)
        if cat == "Cc":
            return None, "must not contain control characters"
        if cat == "Cs":
            return None, "contains invalid characters"
    return text, None


def _validate_value(q: Question, value: Any) -> Tuple[Any, Optional[str]]:
    """Validate one answer against its question. Returns (normalized, error)."""
    if q.type == "scale":
        if isinstance(value, float) and not isinstance(value, bool) and value.is_integer():
            value = int(value)
        if not _is_int_value(value):
            return None, f"must be an integer from {SCALE_MIN} to {SCALE_MAX}"
        if not SCALE_MIN <= value <= SCALE_MAX:
            return None, f"must be an integer from {SCALE_MIN} to {SCALE_MAX}"
        return value, None

    if q.type == "single_choice":
        assert q.options is not None
        if not isinstance(value, str) or value not in q.options:
            return None, "must be one of the listed options"
        return value, None

    if q.type == "multiple_choice":
        assert q.options is not None
        if not isinstance(value, list):
            return None, "must be a list of options"
        if not all(isinstance(v, str) for v in value):
            return None, "must be a list of options"
        if any(v not in q.options for v in value):
            return None, "contains an option that is not listed"
        if len(set(value)) != len(value):
            return None, "must not contain duplicate options"
        if q.max_selections is not None and len(value) > q.max_selections:
            return None, f"select at most {q.max_selections} options"
        # canonical order = catalog order (deterministic storage)
        return [o for o in q.options if o in value], None

    if q.type == "text":
        if not isinstance(value, str):
            return None, "must be a string"
        text, err = _normalize_text(value)
        if err:
            return None, err
        limit = q.max_length or TEXT_MAX_LENGTH
        if len(text) > limit:  # type: ignore[arg-type]
            return None, f"must be at most {limit} characters"
        return text, None

    return None, "unsupported question type"  # pragma: no cover


def _validate_against(answers: Any, questions: Mapping[str, Question]
                      ) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Returns (normalized, errors). Structural problems (not a dict, too many
    keys) raise immediately since nothing else can be meaningfully checked."""
    if not isinstance(answers, dict):
        raise QuestionnaireValidationError(
            [{"question_id": ROOT_ERROR_ID, "message": "answers must be an object"}])
    if len(answers) > MAX_ANSWER_KEYS:
        raise QuestionnaireValidationError(
            [{"question_id": ROOT_ERROR_ID,
              "message": f"too many answers (max {MAX_ANSWER_KEYS})"}])
    errors: List[Dict[str, str]] = []
    normalized: Dict[str, Any] = {}
    for key, value in answers.items():
        if not isinstance(key, str):
            errors.append({"question_id": ROOT_ERROR_ID,
                           "message": "question ids must be strings"})
            continue
        q = questions.get(key)
        if q is None:
            errors.append({"question_id": _echo_id(key), "message": "unknown question id"})
            continue
        norm, err = _validate_value(q, value)
        if err:
            errors.append({"question_id": key, "message": err})
        else:
            normalized[key] = norm
    return normalized, errors


def validate_partial_answers(answers: Any) -> Dict[str, Any]:
    """Validate a (possibly partial) answer set, e.g. an onboarding draft.

    Returns a normalized copy (ints for scale items, stripped text, canonical
    order for multi-select). Raises ``QuestionnaireValidationError`` listing
    ALL problems. Empty text is allowed in a draft.
    """
    normalized, errors = _validate_against(answers, QUESTIONS)
    if errors:
        raise QuestionnaireValidationError(errors)
    return normalized


def _is_answered(q: Question, value: Any) -> bool:
    if value is None:
        return False
    if q.type == "text" and value == "":
        return False
    if q.type == "multiple_choice" and value == []:
        return False
    return True


def validate_complete_answers(answers: Any) -> Dict[str, Any]:
    """Validate a full submission: partial validation + every required question
    answered. Errors for invalid answers come first (in input order), then one
    ``"answer is required"`` error per missing id (in catalog order)."""
    normalized, errors = _validate_against(answers, QUESTIONS)
    invalid_ids = {e["question_id"] for e in errors}
    for qid in REQUIRED_QUESTION_IDS:
        if qid in invalid_ids:
            continue
        if not _is_answered(QUESTIONS[qid], normalized.get(qid)):
            errors.append({"question_id": qid, "message": "answer is required"})
    if errors:
        raise QuestionnaireValidationError(errors)
    return normalized


def score_questionnaire(answers: Any) -> Dict[str, Any]:
    """Validate a complete submission and compute the psychological profile.

    Returns the ``PsychologicalProfile`` score fields (see API contract) plus
    ``questionnaire_version`` and the normalized raw answers under
    ``questionnaire_responses``. Raises ``QuestionnaireValidationError``.
    This is the single function the API layer should call on submit.
    """
    from app.questionnaire_processor import process_questionnaire  # avoid import cycle

    normalized = validate_complete_answers(answers)
    profile = process_questionnaire(normalized)
    missing = [k for k, v in profile.items() if v is None]
    if missing:  # unreachable for a validated complete answer set; guards drift
        raise RuntimeError(f"scoring produced no value for {missing}")
    profile["questionnaire_version"] = QUESTIONNAIRE_VERSION
    return profile
