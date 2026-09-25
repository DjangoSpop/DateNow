"""Server-owned question bank for questionnaire version ``ipip-v1``.

This module is the single source of truth for question ids, texts, types,
answer options and scoring keys. It was ported from the legacy
``frontend/src/data/questionnaireData.ts``; ids and texts are unchanged.

Scoring metadata (``trait`` / ``reverse``) lives here but is never exposed by
``get_definition()``: clients only see what they need to render the form.

The legacy ``verify_*`` free-text section is intentionally NOT ported; see
``docs/QUESTIONNAIRE.md`` ("Excluded: verify_*").

Pure data, stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

QUESTIONNAIRE_VERSION = "ipip-v1"

SCALE = "scale"
SINGLE_CHOICE = "single_choice"

AGREE_LABELS: Mapping[str, str] = {
    "1": "Strongly Disagree",
    "2": "Disagree",
    "3": "Neutral",
    "4": "Agree",
    "5": "Strongly Agree",
}

IMPORTANCE_LABELS: Mapping[str, str] = {
    "1": "Not at all important",
    "2": "Slightly important",
    "3": "Moderately important",
    "4": "Very important",
    "5": "Extremely important",
}

AMOUNT_LABELS: Mapping[str, str] = {
    "1": "Not at all",
    "2": "A little",
    "3": "Somewhat",
    "4": "Quite a lot",
    "5": "Very much",
}


@dataclass(frozen=True)
class Option:
    value: str
    label: str


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: str
    # Scoring metadata (server-only).
    trait: Optional[str] = None
    reverse: bool = False
    # scale questions
    scale_min: int = 1
    scale_max: int = 5
    labels: Mapping[str, str] = field(default_factory=lambda: AGREE_LABELS)
    # single_choice questions
    options: Tuple[Option, ...] = ()
    required: bool = True

    @property
    def option_values(self) -> Tuple[str, ...]:
        return tuple(o.value for o in self.options)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    description: str
    estimated_minutes: int
    questions: Tuple[Question, ...]


def _s(qid: str, text: str, trait: Optional[str], reverse: bool = False,
       labels: Mapping[str, str] = AGREE_LABELS) -> Question:
    return Question(id=qid, text=text, type=SCALE, trait=trait, reverse=reverse, labels=labels)


def _c(qid: str, text: str, trait: Optional[str], options: Tuple[Tuple[str, str], ...]) -> Question:
    return Question(
        id=qid, text=text, type=SINGLE_CHOICE, trait=trait,
        options=tuple(Option(value=v, label=l) for v, l in options),
    )


E, A, C, N, O = "extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"

# IPIP 50-item Big-Five Factor Markers (Goldberg, 1992), 44 of the 50 items.
# reverse=True means the item is minus-keyed for the trait named in ``trait``.
# Every key below was checked against the published IPIP key (see docs).
PERSONALITY = (
    _s("bf_1", "I am the life of the party", E),
    _s("bf_2", "I don't talk a lot", E, reverse=True),
    _s("bf_3", "I feel comfortable around people", E),
    _s("bf_4", "I keep in the background", E, reverse=True),
    _s("bf_5", "I start conversations", E),
    _s("bf_6", "I have little to say", E, reverse=True),
    _s("bf_7", "I talk to a lot of different people at parties", E),
    _s("bf_8", "I don't like to draw attention to myself", E, reverse=True),

    _s("bf_9", "I feel little concern for others", A, reverse=True),
    _s("bf_10", "I am interested in people", A),
    _s("bf_11", "I insult people", A, reverse=True),
    _s("bf_12", "I sympathize with others' feelings", A),
    _s("bf_13", "I am not interested in other people's problems", A, reverse=True),
    _s("bf_14", "I have a soft heart", A),
    _s("bf_15", "I am not really interested in others", A, reverse=True),
    _s("bf_16", "I take time out for others", A),
    _s("bf_17", "I feel others' emotions", A),
    _s("bf_18", "I make people feel at ease", A),

    _s("bf_19", "I am always prepared", C),
    _s("bf_20", "I leave my belongings around", C, reverse=True),
    _s("bf_21", "I pay attention to details", C),
    _s("bf_22", "I make a mess of things", C, reverse=True),
    _s("bf_23", "I get chores done right away", C),
    _s("bf_24", "I often forget to put things back in their proper place", C, reverse=True),
    _s("bf_25", "I like order", C),
    _s("bf_26", "I shirk my duties", C, reverse=True),
    _s("bf_27", "I follow a schedule", C),
    _s("bf_28", "I am exacting in my work", C),

    # Scored in the neuroticism direction (high = more negative emotionality).
    _s("bf_29", "I get stressed out easily", N),
    _s("bf_30", "I am relaxed most of the time", N, reverse=True),
    _s("bf_31", "I worry about things", N),
    _s("bf_32", "I seldom feel blue", N, reverse=True),
    _s("bf_33", "I am easily disturbed", N),
    _s("bf_34", "I get upset easily", N),
    _s("bf_35", "I change my mood a lot", N),
    _s("bf_36", "I have frequent mood swings", N),

    # IPIP factor V "Intellect/Imagination", stored in the ``openness`` column.
    _s("bf_37", "I have a rich vocabulary", O),
    _s("bf_38", "I have difficulty understanding abstract ideas", O, reverse=True),
    _s("bf_39", "I have a vivid imagination", O),
    _s("bf_40", "I am not interested in abstract ideas", O, reverse=True),
    _s("bf_41", "I have excellent ideas", O),
    _s("bf_42", "I do not have a good imagination", O, reverse=True),
    _s("bf_43", "I am quick to understand things", O),
    _s("bf_44", "I spend time reflecting on things", O),
)

VALUES = (
    _s("val_1", "How important is having a family in your future?", "family_orientation",
       labels=IMPORTANCE_LABELS),
    _s("val_2", "How important is career success and professional achievement to you?",
       "career_ambition", labels=IMPORTANCE_LABELS),
    _s("val_3", "How much do you value adventure and new experiences?", "adventure_seeking",
       labels=AMOUNT_LABELS),
    _s("val_4", "How important is making a positive impact on society?", "social_consciousness",
       labels=IMPORTANCE_LABELS),
    _s("val_5", "How important is spirituality or religion in your life?", "spiritual_religious",
       labels=IMPORTANCE_LABELS),
    _c("val_6", "I prefer to have children:", "family_orientation", (
        ("definitely", "Definitely"),
        ("probably", "Probably"),
        ("not_sure", "Not sure"),
        ("probably_not", "Probably not"),
        ("definitely_not", "Definitely not"),
    )),
    _c("val_7", "My ideal weekend involves:", None, (
        ("outdoor_adventures", "Outdoor adventures and activities"),
        ("cultural_events", "Cultural events and entertainment"),
        ("relaxing_at_home", "Relaxing at home with loved ones"),
        ("social_gatherings", "Social gatherings with friends"),
        ("personal_projects", "Working on personal projects"),
    )),
)

LOVE = (
    _s("ll_1", "I feel most loved when my partner tells me they appreciate me", "love_language_words"),
    _s("ll_2", "I feel most loved when my partner does thoughtful things for me", "love_language_acts"),
    _s("ll_3", "I feel most loved when my partner gives me meaningful gifts", "love_language_gifts"),
    _s("ll_4", "I feel most loved when my partner spends quality time with me", "love_language_time"),
    _s("ll_5", "I feel most loved through physical touch and affection", "love_language_touch"),
)

COMMUNICATION = (
    _c("comm_1", "How do you prefer to communicate?", "communication_style", (
        ("direct", "Direct and straightforward"),
        ("diplomatic", "Diplomatic and tactful"),
        ("emotional", "Emotional and expressive"),
        ("logical", "Logical and analytical"),
    )),
    _c("comm_2", "When there is conflict, I tend to:", "conflict_resolution", (
        ("address_directly", "Address it directly and immediately"),
        ("cool_down_first", "Take time to cool down first"),
        ("seek_compromise", "Seek compromise and middle ground"),
        ("avoid_confrontation", "Avoid confrontation when possible"),
    )),
    _c("comm_3", "I prefer to resolve disagreements by:", None, (
        ("work_together", "Working together to find solutions"),
        ("take_turns", "Taking turns getting our way"),
        ("discuss_feelings", "Having deep discussions about feelings"),
        ("space_then_reconnect", "Giving each other space then reconnecting"),
    )),
)

ATTACHMENT = (
    _s("att_1", "I find it easy to get emotionally close to others", "attachment_avoidance", reverse=True),
    _s("att_2", "I worry about being abandoned in relationships", "attachment_anxiety"),
    _s("att_3", "I am comfortable depending on others", "attachment_avoidance", reverse=True),
    _s("att_4", "I worry that others will not value me as much as I value them", "attachment_anxiety"),
    _c("att_5", "In relationships, I prefer to:", "attachment_style", (
        ("very_close", "Be very close and connected"),
        ("some_independence", "Maintain some independence"),
        ("keep_distance", "Keep emotional distance"),
        ("depends", "It depends on the situation"),
    )),
)

# Collected but not scored in Sprint 1 (Sprint 2 normalizes them).
GOALS = (
    _c("rg_1", "What are you looking for?", None, (
        ("serious", "A serious, long-term relationship"),
        ("see_where_it_goes", "Dating to see where it goes"),
        ("casual", "Casual dating"),
        ("friendship", "New friends and connections"),
    )),
    _c("rg_2", "How soon do you see yourself settling down?", None, (
        ("ready_now", "Ready now"),
        ("within_a_year", "Within the next year"),
        ("in_a_few_years", "In a few years"),
        ("not_sure", "Not sure yet"),
        ("not_settling_down", "Not looking to settle down"),
    )),
)

PREFERENCES = (
    _s("pref_1", "How important is physical attraction to you?", None, labels=IMPORTANCE_LABELS),
    _s("pref_2", "How important is it that your partner shares your religious/spiritual beliefs?", None,
       labels=IMPORTANCE_LABELS),
    _s("pref_3", "How important is intellectual compatibility?", None, labels=IMPORTANCE_LABELS),
    _c("pref_4", "Your partner smoking is:", None, (
        ("deal_breaker", "A deal breaker"),
        ("concern", "A concern"),
        ("not_ideal_but_okay", "Not ideal but okay"),
        ("not_an_issue", "Not an issue"),
    )),
    _c("pref_5", "How often do you drink alcohol?", None, (
        ("never", "Never"),
        ("rarely", "Rarely"),
        ("socially", "Socially"),
        ("regularly", "Regularly"),
        ("prefer_not_to_say", "Prefer not to say"),
    )),
)

SECTIONS: Tuple[Section, ...] = (
    Section("personality", "Your Personality", "Help us understand who you are", 6, PERSONALITY),
    Section("values", "Your Values", "What matters most to you in life", 3, VALUES),
    Section("love", "Love & Connection", "How you give and receive love", 2, LOVE),
    Section("communication", "Communication Style", "How you express yourself", 2, COMMUNICATION),
    Section("attachment", "Attachment & Bonding", "Your relationship patterns", 2, ATTACHMENT),
    Section("goals", "Relationship Goals", "What you are looking for", 1, GOALS),
    Section("preferences", "Preferences & Deal-Breakers", "What is important to you", 2, PREFERENCES),
)

QUESTIONS: Tuple[Question, ...] = tuple(q for s in SECTIONS for q in s.questions)
QUESTIONS_BY_ID: Mapping[str, Question] = {q.id: q for q in QUESTIONS}

if len(QUESTIONS_BY_ID) != len(QUESTIONS):  # pragma: no cover - guards future edits
    raise RuntimeError("duplicate question id in questionnaire bank")
