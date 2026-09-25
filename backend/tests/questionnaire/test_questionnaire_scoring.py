import copy
import itertools
import random

import pytest

from qn_helpers import build_answers, items_for

from app.questionnaire import (
    ATTACHMENT_STYLES,
    COMMUNICATION_STYLES,
    CONFLICT_RESOLUTION_STYLES,
    score,
)
from app.questionnaire.bank import QUESTIONS_BY_ID

PROFILE_COLUMNS = {
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "family_orientation", "career_ambition", "adventure_seeking", "social_consciousness",
    "spiritual_religious", "communication_style", "conflict_resolution", "love_language_words",
    "love_language_acts", "love_language_gifts", "love_language_time", "love_language_touch",
    "attachment_style", "questionnaire_responses",
}
BIG_FIVE = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NUMERIC = [
    *BIG_FIVE, "family_orientation", "career_ambition", "adventure_seeking", "social_consciousness",
    "spiritual_religious", "love_language_words", "love_language_acts", "love_language_gifts",
    "love_language_time", "love_language_touch",
]

# Published IPIP 50-item Big-Five marker keys for the 44 items used (minus-keyed items).
EXPECTED_REVERSE = {
    "bf_2", "bf_4", "bf_6", "bf_8", "bf_9", "bf_11", "bf_13", "bf_15",
    "bf_20", "bf_22", "bf_24", "bf_26", "bf_30", "bf_32", "bf_38", "bf_40", "bf_42",
}
EXPECTED_TRAIT_ITEMS = {
    "extraversion": range(1, 9),
    "agreeableness": range(9, 19),
    "conscientiousness": range(19, 29),
    "neuroticism": range(29, 37),
    "openness": range(37, 45),
}


def test_output_keys_exact(complete_answers):
    assert set(score(complete_answers)) == PROFILE_COLUMNS


def test_reverse_keys_match_ipip():
    for trait, rng in EXPECTED_TRAIT_ITEMS.items():
        ids = [q.id for q in items_for(trait)]
        assert ids == [f"bf_{i}" for i in rng]
    actual = {q.id for t in EXPECTED_TRAIT_ITEMS for q in items_for(t) if q.reverse}
    assert actual == EXPECTED_REVERSE


@pytest.mark.parametrize("trait,expected", [
    # all-5 answers: forward -> 5, reverse -> 1; value = (mean-1)/4*100
    ("extraversion", 50.0),       # 4 fwd, 4 rev -> mean 3
    ("agreeableness", 60.0),      # 6 fwd, 4 rev -> mean 3.4
    ("conscientiousness", 60.0),  # 6 fwd, 4 rev -> mean 3.4
    ("neuroticism", 75.0),        # 6 fwd, 2 rev -> mean 4
    ("openness", 62.5),           # 5 fwd, 3 rev -> mean 3.5
])
def test_all_fives_per_trait(trait, expected):
    assert score(build_answers(5))[trait] == expected


@pytest.mark.parametrize("trait,expected", [
    ("extraversion", 50.0), ("agreeableness", 40.0), ("conscientiousness", 40.0),
    ("neuroticism", 25.0), ("openness", 37.5),
])
def test_all_ones_per_trait(trait, expected):
    assert score(build_answers(1))[trait] == expected


def _trait_answers(trait, forward_value, reverse_value):
    overrides = {q.id: (reverse_value if q.reverse else forward_value) for q in items_for(trait)}
    return build_answers(3, **overrides)


@pytest.mark.parametrize("trait", BIG_FIVE)
def test_pure_forward_and_reverse_bounds(trait):
    assert score(_trait_answers(trait, 5, 1))[trait] == 100.0
    assert score(_trait_answers(trait, 1, 5))[trait] == 0.0
    # only reverse items endorsed at max, forward at neutral
    n_fwd = sum(not q.reverse for q in items_for(trait))
    n_rev = sum(q.reverse for q in items_for(trait))
    expected = round(((n_fwd * 3 + n_rev * 1) / (n_fwd + n_rev) - 1) / 4 * 100, 6)
    assert score(_trait_answers(trait, 3, 5))[trait] == pytest.approx(expected, abs=0.051)


def test_forward_only_scales_all_ones_and_fives():
    lo, hi = score(build_answers(1)), score(build_answers(5))
    for col in ["career_ambition", "adventure_seeking", "social_consciousness", "spiritual_religious",
                "love_language_words", "love_language_acts", "love_language_gifts",
                "love_language_time", "love_language_touch"]:
        assert lo[col] == 0.0
        assert hi[col] == 100.0


def test_neutral_is_fifty(complete_answers):
    r = score(complete_answers)
    for col in BIG_FIVE:
        assert r[col] == 50.0


def test_numeric_range_and_rounding_random():
    rnd = random.Random(1234)
    for _ in range(200):
        answers = {}
        for qid, q in QUESTIONS_BY_ID.items():
            answers[qid] = rnd.randint(1, 5) if q.type == "scale" else rnd.choice(q.option_values)
        r = score(answers)
        for col in NUMERIC:
            v = r[col]
            assert isinstance(v, float)
            assert 0.0 <= v <= 100.0
            assert round(v, 1) == v


def test_round_half_up():
    # extraversion keyed values summing to 18 over 8 items -> mean 2.25 -> 31.25 -> 31.3
    def ext(keyed):
        items = items_for("extraversion")
        return build_answers(3, **{q.id: (6 - k if q.reverse else k) for q, k in zip(items, keyed)})
    assert score(ext([3, 3, 2, 2, 2, 2, 2, 2]))["extraversion"] == 31.3
    assert score(ext([3, 3, 3, 3, 3, 2, 2, 2]))["extraversion"] == 40.6  # 40.625


@pytest.mark.parametrize("val_1,val_6,expected", [
    (5, "definitely", 100.0), (1, "definitely_not", 0.0), (5, "definitely_not", 50.0),
    (4, "probably", 75.0), (3, "not_sure", 50.0), (2, "probably_not", 25.0), (1, "definitely", 50.0),
])
def test_family_orientation(val_1, val_6, expected):
    assert score(build_answers(3, val_1=val_1, val_6=val_6))["family_orientation"] == expected


def test_unscored_questions_do_not_affect_scores(complete_answers):
    base = score(complete_answers)
    for qid in ["val_7", "comm_3", "rg_1", "rg_2", "pref_1", "pref_2", "pref_3", "pref_4", "pref_5"]:
        q = QUESTIONS_BY_ID[qid]
        for v in (q.option_values or (1, 5)):
            r = score({**complete_answers, qid: v})
            r.pop("questionnaire_responses")
            b = dict(base)
            b.pop("questionnaire_responses")
            assert r == b


def test_communication_style_exhaustive(complete_answers):
    seen = set()
    for v in QUESTIONS_BY_ID["comm_1"].option_values:
        style = score({**complete_answers, "comm_1": v})["communication_style"]
        assert style in COMMUNICATION_STYLES
        seen.add(style)
    assert seen == set(COMMUNICATION_STYLES)


def test_conflict_resolution_exhaustive(complete_answers):
    seen = set()
    for c2, c3 in itertools.product(QUESTIONS_BY_ID["comm_2"].option_values,
                                    QUESTIONS_BY_ID["comm_3"].option_values):
        style = score({**complete_answers, "comm_2": c2, "comm_3": c3})["conflict_resolution"]
        assert style in CONFLICT_RESOLUTION_STYLES
        seen.add(style)
    assert seen == set(CONFLICT_RESOLUTION_STYLES)


def test_attachment_exhaustive_within_vocabulary(complete_answers):
    seen = set()
    att5 = QUESTIONS_BY_ID["att_5"].option_values
    for a1, a2, a3, a4, a5 in itertools.product(range(1, 6), range(1, 6), range(1, 6), range(1, 6), att5):
        style = score({**complete_answers, "att_1": a1, "att_2": a2, "att_3": a3, "att_4": a4,
                       "att_5": a5})["attachment_style"]
        assert style in ATTACHMENT_STYLES
        seen.add(style)
    assert seen == set(ATTACHMENT_STYLES)


@pytest.mark.parametrize("a1,a2,a3,a4,a5,expected", [
    (5, 1, 5, 1, "very_close", "secure"),
    (5, 5, 5, 5, "very_close", "anxious"),
    (1, 1, 1, 1, "keep_distance", "avoidant"),
    (1, 5, 1, 5, "depends", "fearful_avoidant"),
    (3, 3, 3, 3, "very_close", "secure"),          # midpoint -> not high
    (3, 3, 3, 3, "keep_distance", "avoidant"),     # att_5 breaks avoidance tie
    (3, 4, 3, 4, "keep_distance", "fearful_avoidant"),
    (1, 1, 1, 1, "very_close", "avoidant"),        # att_5 does not override scale items
    (4, 3, 3, 4, "some_independence", "anxious"),  # anxiety mean 3.5 > 3
])
def test_attachment_cases(complete_answers, a1, a2, a3, a4, a5, expected):
    r = score({**complete_answers, "att_1": a1, "att_2": a2, "att_3": a3, "att_4": a4, "att_5": a5})
    assert r["attachment_style"] == expected


def test_reproducible_and_order_independent():
    rnd = random.Random(99)
    answers = {qid: (rnd.randint(1, 5) if q.type == "scale" else rnd.choice(q.option_values))
               for qid, q in QUESTIONS_BY_ID.items()}
    items = list(answers.items())
    rnd.shuffle(items)
    shuffled = dict(items)
    r1, r2, r3 = score(answers), score(answers), score(shuffled)
    assert r1 == r2 == r3
    assert list(r1["questionnaire_responses"]) == list(r3["questionnaire_responses"])


def test_questionnaire_responses_is_copy():
    answers = build_answers(4)
    snapshot = copy.deepcopy(answers)
    r = score(answers)
    assert r["questionnaire_responses"] == snapshot
    assert r["questionnaire_responses"] is not answers
    answers["bf_1"] = 1
    del answers["bf_2"]
    assert r["questionnaire_responses"] == snapshot
    r["questionnaire_responses"]["bf_3"] = 1
    assert answers["bf_3"] == 4


def test_input_not_mutated():
    answers = build_answers(2)
    snapshot = copy.deepcopy(answers)
    score(answers)
    assert answers == snapshot


def test_legacy_shim_points_to_new_scorer(complete_answers):
    from app import questionnaire_processor
    assert questionnaire_processor.process_questionnaire is score
    assert not hasattr(questionnaire_processor, "verify_authenticity")
