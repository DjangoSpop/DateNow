"""Pure unit tests for app.questionnaire_processor (no DB, no settings)."""
import pytest

from app import questionnaire_processor as qp
from app.questionnaire_catalog import QUESTIONS, score_questionnaire

BIG_FIVE = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


def base_answers(scale_value=3):
    out = {}
    for q in QUESTIONS.values():
        if q.type == "scale":
            out[q.id] = scale_value
        elif q.type == "text":
            out[q.id] = "I would like to meet someone kind and fun."
        else:
            out[q.id] = q.options[0]
    return out


def trait_items(trait):
    return qp.BIG_FIVE_KEYS[trait]


# Hand-computed fixture ---------------------------------------------------------
# E  bf_1..8   [5,1,4,2,5,1,4,2] rev 2,4,6,8 -> [5,5,4,4,5,5,4,4] = 36/8 = 4.5  -> 87.5
# A  bf_9..18  [2,4,1,5,2,4,1,5,3,3] rev 9,11,13,15 -> 42/10 = 4.2       -> 80.0
# C  bf_19..28 [1,5,1,5,1,5,1,5,1,1] rev 20,22,24,26 -> all 1            -> 0.0
# N  bf_29..36 [4,2,3,3,5,4,2,1] rev 30,32 -> [4,4,3,3,5,4,2,1] = 26/8 = 3.25 -> 56.25 -> 56.3
# O  bf_37..44 [5,1,5,1,5,1,5,5] rev 38,40,42 -> all 5                    -> 100.0
# family = mean(val_1=5 -> 100, val_6 'Probably not' -> 25) = 62.5
# career = val_2=2 -> 25.0 ; social = val_4=3 -> 50.0 ; spiritual = val_5=1 -> 0.0
# adventure = .75 * (val_3=4 -> 75) + .25 * ('Relaxing at home' -> 0) = 56.25 -> 56.3
# love ll_1..5 = 1..5 -> 0, 25, 50, 75, 100
# attachment: anxiety mean(att_2=2, att_4=3) = 2.5 (low);
#             avoidance mean(6-2, 6-1, independence=3) = 4 (high) -> avoidant
FIXTURE_BF = {
    **dict(zip([f"bf_{i}" for i in range(1, 9)], [5, 1, 4, 2, 5, 1, 4, 2])),
    **dict(zip([f"bf_{i}" for i in range(9, 19)], [2, 4, 1, 5, 2, 4, 1, 5, 3, 3])),
    **dict(zip([f"bf_{i}" for i in range(19, 29)], [1, 5, 1, 5, 1, 5, 1, 5, 1, 1])),
    **dict(zip([f"bf_{i}" for i in range(29, 37)], [4, 2, 3, 3, 5, 4, 2, 1])),
    **dict(zip([f"bf_{i}" for i in range(37, 45)], [5, 1, 5, 1, 5, 1, 5, 5])),
}
FIXTURE = {
    **base_answers(),
    **FIXTURE_BF,
    "val_1": 5, "val_2": 2, "val_3": 4, "val_4": 3, "val_5": 1,
    "val_6": "Probably not", "val_7": "Relaxing at home with loved ones",
    "ll_1": 1, "ll_2": 2, "ll_3": 3, "ll_4": 4, "ll_5": 5,
    "comm_1": "Logical and analytical", "comm_2": "Take time to cool down first",
    "att_1": 2, "att_2": 2, "att_3": 1, "att_4": 3, "att_5": "Maintain some independence",
}
FIXTURE_EXPECTED = {
    "extraversion": 87.5, "agreeableness": 80.0, "conscientiousness": 0.0,
    "neuroticism": 56.3, "openness": 100.0,
    "family_orientation": 62.5, "career_ambition": 25.0, "adventure_seeking": 56.3,
    "social_consciousness": 50.0, "spiritual_religious": 0.0,
    "communication_style": "logical", "conflict_resolution": "reflective",
    "love_language_words": 0.0, "love_language_acts": 25.0, "love_language_gifts": 50.0,
    "love_language_time": 75.0, "love_language_touch": 100.0,
    "attachment_style": "avoidant",
}


def test_hand_computed_fixture():
    profile = score_questionnaire(FIXTURE)
    for key, expected in FIXTURE_EXPECTED.items():
        assert profile[key] == expected, key


def test_reproducible():
    first = qp.process_questionnaire(FIXTURE)
    for _ in range(50):
        assert qp.process_questionnaire(dict(FIXTURE)) == first


def test_keys_derived_from_catalog():
    for trait in BIG_FIVE:
        for qid, rev in trait_items(trait).items():
            assert QUESTIONS[qid].trait == trait and QUESTIONS[qid].reverse is rev
    assert sum(len(trait_items(t)) for t in BIG_FIVE) == 44


# Scaling / keying ---------------------------------------------------------------

@pytest.mark.parametrize("trait", BIG_FIVE)
def test_min_and_max_consistent_answers(trait):
    items = trait_items(trait)
    low = {qid: (5 if rev else 1) for qid, rev in items.items()}
    high = {qid: (1 if rev else 5) for qid, rev in items.items()}
    mid = {qid: 3 for qid in items}
    assert qp.calculate_big_five_score(low, trait) == 0.0
    assert qp.calculate_big_five_score(high, trait) == 100.0
    assert qp.calculate_big_five_score(mid, trait) == 50.0


@pytest.mark.parametrize("trait", BIG_FIVE)
def test_all_fives_vs_all_ones_mixed_keying(trait):
    items = trait_items(trait)
    n, n_rev = len(items), sum(items.values())
    # all 5s: forward items score 5, reverse items score 1
    expected_5 = round(((5 * (n - n_rev) + 1 * n_rev) / n - 1) / 4 * 100 + 1e-9, 1)
    expected_1 = round(((1 * (n - n_rev) + 5 * n_rev) / n - 1) / 4 * 100 + 1e-9, 1)
    assert qp.calculate_big_five_score({q: 5 for q in items}, trait) == expected_5
    assert qp.calculate_big_five_score({q: 1 for q in items}, trait) == expected_1


def test_all_fives_explicit_numbers():
    fives = {f"bf_{i}": 5 for i in range(1, 45)}
    # E 4 fwd/4 rev -> 50 ; A 6/4 -> (26/10-1)/4 = 40 -> 60 ; C 6/4 -> 60
    # N 6 fwd/2 rev -> (32/8-1)/4 -> 75 ; O 5 fwd/3 rev -> (28/8-1)/4 -> 62.5
    assert {t: qp.calculate_big_five_score(fives, t) for t in BIG_FIVE} == {
        "extraversion": 50.0, "agreeableness": 60.0, "conscientiousness": 60.0,
        "neuroticism": 75.0, "openness": 62.5}


@pytest.mark.parametrize("qid", [f"bf_{i}" for i in range(1, 45)])
def test_each_item_direction(qid):
    q = QUESTIONS[qid]
    items = trait_items(q.trait)
    answers = {i: 3 for i in items}
    answers[qid] = 5
    score = qp.calculate_big_five_score(answers, q.trait)
    delta = 2 / len(items) / 4 * 100
    expected = 50 - delta if q.reverse else 50 + delta
    assert score == pytest.approx(expected, abs=0.051)
    assert (score < 50) is q.reverse


def test_rounding_half_up():
    # 8-item trait, one item +1 over neutral: 50 + 3.125 = 53.125 -> 53.1
    e = {i: 3 for i in trait_items("extraversion")}
    e["bf_1"] = 4
    assert qp.calculate_big_five_score(e, "extraversion") == 53.1
    # keyed [5,1,1,3,3,3,3,3] -> mean 2.75 -> 43.75 -> 43.8
    e["bf_1"] = 5
    e["bf_3"] = 1  # net 0
    e["bf_2"] = 5  # reverse item -> keyed 1: mean 2.75 -> 43.75
    assert qp.calculate_big_five_score(e, "extraversion") == 43.8
    n = {i: 3 for i in trait_items("neuroticism")}
    n["bf_29"] = 5  # 50 + 6.25 = 56.25 -> 56.3 (half-up; round() would give 56.2)
    assert qp.calculate_big_five_score(n, "neuroticism") == 56.3


# Missing / robustness ------------------------------------------------------------

def test_missing_returns_none_not_zero():
    profile = qp.process_questionnaire({})
    for k, v in profile.items():
        if k == "questionnaire_responses":
            assert v == {}
        else:
            assert v is None, k


def test_wrong_types_never_crash():
    junk = {"bf_1": "3", "bf_2": True, "bf_3": 100, "bf_4": -2, "bf_5": None, "bf_6": [1],
            "comm_1": 5, "comm_2": None, "att_1": "high", "att_2": {"x": 1},
            "att_5": 7, "val_6": 3, "val_7": ["x"], "ll_1": 2.5, "verify_1": 12}
    profile = qp.process_questionnaire(junk)
    assert profile["extraversion"] is None
    assert profile["communication_style"] is None
    assert profile["attachment_style"] is None
    assert profile["love_language_words"] is None
    for bad in (None, [], "x", 3):
        qp.process_questionnaire(bad)
        assert qp.verify_authenticity(bad)[0] is False


def test_partial_trait_uses_answered_items():
    assert qp.calculate_big_five_score({"bf_1": 5}, "extraversion") == 100.0
    assert qp.calculate_big_five_score({"bf_2": 5}, "extraversion") == 0.0


def test_unknown_dimension_raises():
    with pytest.raises(ValueError):
        qp.calculate_big_five_score({}, "honesty")
    with pytest.raises(ValueError):
        qp.calculate_value_score({}, "wealth")
    with pytest.raises(ValueError):
        qp.calculate_love_language_score({}, "service")


# Choice mappings ----------------------------------------------------------------

def test_choice_maps_cover_exact_catalog_options():
    assert set(qp.COMM_1_STYLES) == set(QUESTIONS["comm_1"].options)
    assert set(qp.COMM_1_STYLES.values()) == set(qp.COMMUNICATION_STYLES)
    assert set(qp.COMM_2_CONFLICT) == set(QUESTIONS["comm_2"].options)
    assert set(qp.COMM_2_CONFLICT.values()) == set(qp.CONFLICT_STYLES)
    assert set(qp.ATT_5_AVOIDANCE) == set(QUESTIONS["att_5"].options)
    assert set(qp.VAL_6_SCORES) == set(QUESTIONS["val_6"].options)
    assert set(qp.VAL_7_ADVENTURE_SCORES) == set(QUESTIONS["val_7"].options)


def test_choice_near_misses_not_matched():
    assert qp.determine_communication_style({"comm_1": "direct"}) is None
    assert qp.determine_communication_style({"comm_1": "Direct and straightforward"}) == "direct"
    assert qp.determine_conflict_resolution({"comm_2": "I avoid it"}) is None


def test_values_partial_and_mapping():
    assert qp.calculate_value_score({"val_1": 1}, "family_orientation") == 0.0
    assert qp.calculate_value_score({"val_6": "Definitely"}, "family_orientation") == 100.0
    assert qp.calculate_value_score({"val_3": 5}, "adventure_seeking") == 100.0
    assert qp.calculate_value_score(
        {"val_7": "Outdoor adventures and activities"}, "adventure_seeking") == 100.0
    assert qp.calculate_value_score(
        {"val_3": 1, "val_7": "Outdoor adventures and activities"}, "adventure_seeking") == 25.0


# Attachment ---------------------------------------------------------------------

@pytest.mark.parametrize("att, expected", [
    # (att_1 close, att_2 abandon, att_3 depend, att_4 undervalued, att_5)
    ((5, 1, 5, 1, "Be very close and connected"), "secure"),
    ((3, 3, 3, 3, "It depends on the situation"), "secure"),  # neutral is not fearful
    ((5, 5, 4, 4, "Be very close and connected"), "anxious"),
    ((1, 1, 2, 2, "Keep emotional distance"), "avoidant"),
    ((1, 5, 1, 5, "Keep emotional distance"), "fearful-avoidant"),
    ((4, 2, 4, 2, "Maintain some independence"), "secure"),  # independence != avoidance
    ((2, 2, 2, 2, "It depends on the situation"), "avoidant"),  # 'depends' excluded
])
def test_attachment_rule(att, expected):
    answers = dict(zip(["att_1", "att_2", "att_3", "att_4", "att_5"], att))
    assert qp.determine_attachment_style(answers) == expected


def test_attachment_uses_scale_items_not_only_att_5():
    # Previously att_5 short-circuited everything: 'very close' => secure always.
    answers = {"att_1": 5, "att_2": 5, "att_3": 5, "att_4": 5, "att_5": "Be very close and connected"}
    assert qp.determine_attachment_style(answers) == "anxious"


def test_attachment_needs_both_dimensions():
    assert qp.determine_attachment_style({"att_2": 5, "att_4": 5}) is None
    assert qp.determine_attachment_style({"att_1": 5, "att_5": "Keep emotional distance"}) is None


# Authenticity heuristic (unchanged behaviour, type-safe) ---------------------------

def test_verify_authenticity():
    ok = {"verify_1": "I want to find a partner to share my life with",
          "verify_2": "A walk in the park and coffee with a good chat"}
    assert qp.verify_authenticity(ok) == (True, "Verification successful")
    assert qp.verify_authenticity({"verify_1": "short", "verify_2": ok["verify_2"]})[0] is False
    assert qp.verify_authenticity({})[0] is False
