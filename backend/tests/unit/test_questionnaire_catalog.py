"""Pure unit tests for app.questionnaire_catalog (no DB, no settings)."""
import json
import re
from pathlib import Path

import pytest

from app import questionnaire_catalog as cat
from app.questionnaire_catalog import (
    QUESTIONNAIRE_VERSION,
    QUESTIONS,
    REQUIRED_QUESTION_IDS,
    Question,
    QuestionnaireValidationError,
    get_questionnaire_definition,
    score_questionnaire,
    validate_complete_answers,
    validate_partial_answers,
)

# Hard-coded from frontend/src/data/questionnaireData.ts (`reverse: true`).
UI_REVERSE_IDS = {
    "bf_2", "bf_4", "bf_6", "bf_8",
    "bf_9", "bf_11", "bf_13", "bf_15",
    "bf_20", "bf_22", "bf_24", "bf_26",
    "bf_30", "bf_32",
    "bf_38", "bf_40", "bf_42",
}
# Hard-coded from the same file (`trait:` on bf_* items).
UI_TRAIT_RANGES = {
    "extraversion": range(1, 9),
    "agreeableness": range(9, 19),
    "conscientiousness": range(19, 29),
    "neuroticism": range(29, 37),
    "openness": range(37, 45),
}
# Published IPIP-50 Big-Five marker keying: item number -> (factor, +/-).
# Factor 4 is Emotional Stability in IPIP; our trait is Neuroticism, so its sign flips.
IPIP50_KEYING = {
    1: ("E", "+"), 6: ("E", "-"), 11: ("E", "+"), 16: ("E", "-"), 21: ("E", "+"),
    26: ("E", "-"), 31: ("E", "+"), 36: ("E", "-"), 41: ("E", "+"), 46: ("E", "-"),
    2: ("A", "-"), 7: ("A", "+"), 12: ("A", "-"), 17: ("A", "+"), 22: ("A", "-"),
    27: ("A", "+"), 32: ("A", "-"), 37: ("A", "+"), 42: ("A", "+"), 47: ("A", "+"),
    3: ("C", "+"), 8: ("C", "-"), 13: ("C", "+"), 18: ("C", "-"), 23: ("C", "+"),
    28: ("C", "-"), 33: ("C", "+"), 38: ("C", "-"), 43: ("C", "+"), 48: ("C", "+"),
    4: ("ES", "-"), 9: ("ES", "+"), 14: ("ES", "-"), 19: ("ES", "+"), 24: ("ES", "-"),
    29: ("ES", "-"), 34: ("ES", "-"), 39: ("ES", "-"), 44: ("ES", "-"), 49: ("ES", "-"),
    5: ("O", "+"), 10: ("O", "-"), 15: ("O", "+"), 20: ("O", "-"), 25: ("O", "+"),
    30: ("O", "-"), 35: ("O", "+"), 40: ("O", "+"), 45: ("O", "+"), 50: ("O", "+"),
}
FACTOR_TO_TRAIT = {"E": "extraversion", "A": "agreeableness", "C": "conscientiousness",
                   "ES": "neuroticism", "O": "openness"}
IPIP_OMITTED = {40, 41, 44, 46, 49, 50}

UI_FILE = Path(__file__).resolve().parents[3] / "frontend" / "src" / "data" / "questionnaireData.ts"


def full_answers():
    """A complete, valid answer set."""
    out = {}
    for q in QUESTIONS.values():
        if q.type == "scale":
            out[q.id] = 3
        elif q.type == "text":
            out[q.id] = "I would like to meet someone kind and fun."
        else:
            out[q.id] = q.options[0]
    return out


def errors_of(fn, answers):
    with pytest.raises(QuestionnaireValidationError) as exc:
        fn(answers)
    return exc.value.errors


# --------------------------------------------------------------------- catalog

def test_catalog_counts_and_sections():
    assert len(QUESTIONS) == 73
    d = get_questionnaire_definition()
    assert [s["id"] for s in d["sections"]] == [
        "personality", "values", "love", "communication", "attachment",
        "goals", "preferences", "verification"]
    assert [len(s["questions"]) for s in d["sections"]] == [44, 7, 5, 3, 5, 2, 5, 2]


def test_reverse_keys_match_ui_flags():
    catalog_reverse = {q.id for q in QUESTIONS.values() if q.reverse}
    assert catalog_reverse == UI_REVERSE_IDS


def test_traits_match_ui():
    for trait, rng in UI_TRAIT_RANGES.items():
        ids = {q.id for q in QUESTIONS.values() if q.role == cat.ROLE_BIG_FIVE and q.trait == trait}
        assert ids == {f"bf_{i}" for i in rng}


def test_keying_matches_published_ipip50():
    seen = set()
    for q in QUESTIONS.values():
        if q.role != cat.ROLE_BIG_FIVE:
            continue
        factor, sign = IPIP50_KEYING[q.ipip_item]
        assert FACTOR_TO_TRAIT[factor] == q.trait, q.id
        expected_reverse = (sign == "-") if factor != "ES" else (sign == "+")
        assert q.reverse == expected_reverse, q.id
        seen.add(q.ipip_item)
    assert len(seen) == 44
    assert set(IPIP50_KEYING) - seen == IPIP_OMITTED


@pytest.mark.skipif(not UI_FILE.exists(), reason="frontend source not available")
def test_ids_texts_options_match_frontend_file():
    src = UI_FILE.read_text(encoding="utf-8")
    ui_ids = set(re.findall(r"id: '((?:bf|val|ll|comm|att|rg|pref|verify)_\d+)'", src))
    assert ui_ids == set(QUESTIONS)
    for q in QUESTIONS.values():
        variants = {f"'{q.text}'", f'"{q.text}"', "'" + q.text.replace("'", "\\'") + "'"}
        assert any(v in src for v in variants), q.id
        for opt in q.options or ():
            assert f"'{opt}'" in src, (q.id, opt)


# ------------------------------------------------------------------ definition

def test_definition_shape_matches_contract():
    d = get_questionnaire_definition()
    assert set(d) == {"version", "sections"}
    assert d["version"] == QUESTIONNAIRE_VERSION == "2026.1"
    for s in d["sections"]:
        assert set(s) == {"id", "title", "description", "questions"}
        assert all(isinstance(s[k], str) and s[k] for k in ("id", "title", "description"))
        for q in s["questions"]:
            assert set(q) == {"id", "text", "type", "required", "options", "scale", "max_length"}
            assert q["type"] in {"scale", "single_choice", "multiple_choice", "text"}
            assert isinstance(q["required"], bool)
            if q["type"] == "scale":
                assert q["options"] is None and q["max_length"] is None
                assert set(q["scale"]) == {"min", "max", "min_label", "max_label"}
                assert (q["scale"]["min"], q["scale"]["max"]) == (1, 5)
            elif q["type"] in ("single_choice", "multiple_choice"):
                assert isinstance(q["options"], list) and q["options"]
                assert q["scale"] is None and q["max_length"] is None
            else:
                assert q["options"] is None and q["scale"] is None
                assert q["max_length"] == 1000
    json.dumps(d)  # serialisable


def test_definition_hides_internal_metadata():
    blob = json.dumps(get_questionnaire_definition()).lower()
    for word in ("reverse", "trait", "ipip", "role", "neuroticism", "extraversion"):
        assert word not in blob, word


def test_definition_is_a_fresh_copy():
    d = get_questionnaire_definition()
    d["sections"][0]["questions"][0]["text"] = "hacked"
    assert get_questionnaire_definition()["sections"][0]["questions"][0]["text"] != "hacked"


def test_all_questions_required():
    assert set(REQUIRED_QUESTION_IDS) == set(QUESTIONS)


# ------------------------------------------------------------------ validation

def test_partial_valid_and_normalized():
    out = validate_partial_answers({
        "bf_1": 4, "bf_2": 5.0, "comm_1": "Direct and straightforward",
        "verify_1": "  hello\r\nworld  ", "verify_2": "",
    })
    assert out == {"bf_1": 4, "bf_2": 5, "comm_1": "Direct and straightforward",
                   "verify_1": "hello\nworld", "verify_2": ""}
    assert type(out["bf_2"]) is int


def test_partial_empty_ok():
    assert validate_partial_answers({}) == {}


@pytest.mark.parametrize("value", [0, 6, -1, 3.5, "3", True, False, None, [3], {"v": 3}])
def test_scale_rejects_bad_values(value):
    errs = errors_of(validate_partial_answers, {"bf_1": value})
    assert [e["question_id"] for e in errs] == ["bf_1"]


@pytest.mark.parametrize("value", ["direct", "direct and straightforward",
                                   "Direct and straightforward ", 1, None, ["Direct and straightforward"]])
def test_single_choice_rejects_bad_values(value):
    errs = errors_of(validate_partial_answers, {"comm_1": value})
    assert [e["question_id"] for e in errs] == ["comm_1"]


def test_text_rules():
    assert errors_of(validate_partial_answers, {"verify_1": "x" * 1001})[0]["question_id"] == "verify_1"
    assert validate_partial_answers({"verify_1": "x" * 1000})["verify_1"] == "x" * 1000
    assert validate_partial_answers({"verify_1": "  " + "x" * 1000 + "  "})["verify_1"] == "x" * 1000
    for bad in ("a\x00b", "a\x07b", "a\tb", "a\x1bb", "a\ud800b", 123, None, ["x"]):
        errs = errors_of(validate_partial_answers, {"verify_1": bad})
        assert errs[0]["question_id"] == "verify_1", repr(bad)
    assert validate_partial_answers({"verify_1": "line1\nline2 é\U0001F600"})["verify_1"] \
        == "line1\nline2 é\U0001F600"


def test_multiple_choice_rules():
    q = Question(id="mc", text="t", type="multiple_choice", section="values",
                 options=("A", "B", "C"), max_selections=2)
    assert cat._validate_value(q, ["C", "A"]) == (["A", "C"], None)
    assert cat._validate_value(q, [])[1] is None
    for bad in (["A", "A"], ["D"], ["A", "B", "C"], "A", [1], None):
        assert cat._validate_value(q, bad)[1] is not None, bad


def test_all_errors_collected_with_ids():
    errs = errors_of(validate_partial_answers, {
        "nope": 1, "bf_1": 0, "bf_2": 6, "bf_3": 3.5, "bf_4": "3", "bf_5": True,
        "bf_6": None, "comm_1": "wrong", "verify_1": "x" * 5000, "openness": 99,
    })
    assert [e["question_id"] for e in errs] == [
        "nope", "bf_1", "bf_2", "bf_3", "bf_4", "bf_5", "bf_6", "comm_1", "verify_1", "openness"]
    assert all(set(e) == {"question_id", "message"} for e in errs)
    assert all(isinstance(e["message"], str) and e["message"] for e in errs)


@pytest.mark.parametrize("payload", [None, [], "bf_1", 3, [("bf_1", 3)]])
def test_non_dict_rejected(payload):
    errs = errors_of(validate_partial_answers, payload)
    assert errs == [{"question_id": cat.ROOT_ERROR_ID, "message": "answers must be an object"}]
    errs = errors_of(validate_complete_answers, payload)
    assert len(errs) == 1


def test_non_string_keys_and_size_bound():
    errs = errors_of(validate_partial_answers, {1: 3, "bf_1": 3})
    assert errs[0]["question_id"] == cat.ROOT_ERROR_ID
    big = {f"x{i}": 1 for i in range(cat.MAX_ANSWER_KEYS + 1)}
    errs = errors_of(validate_partial_answers, big)
    assert len(errs) == 1 and "too many" in errs[0]["message"]


def test_unknown_long_id_is_truncated_in_error():
    errs = errors_of(validate_partial_answers, {"z" * 5000: 1})
    assert len(errs[0]["question_id"]) < 100


def test_complete_missing_lists_every_id():
    errs = errors_of(validate_complete_answers, {})
    assert [e["question_id"] for e in errs] == list(REQUIRED_QUESTION_IDS)
    assert all(e["message"] == "answer is required" for e in errs)

    answers = full_answers()
    for qid in ("bf_17", "val_7", "pref_5"):
        del answers[qid]
    errs = errors_of(validate_complete_answers, answers)
    assert [e["question_id"] for e in errs] == ["bf_17", "val_7", "pref_5"]


def test_complete_invalid_and_missing_combined():
    answers = full_answers()
    answers["bf_1"] = 9
    del answers["bf_2"]
    answers["verify_2"] = "   "
    errs = errors_of(validate_complete_answers, answers)
    assert [(e["question_id"], e["message"] == "answer is required") for e in errs] == [
        ("bf_1", False), ("bf_2", True), ("verify_2", True)]


def test_complete_valid_passes():
    answers = full_answers()
    assert validate_complete_answers(answers) == answers


# --------------------------------------------------------------------- scoring

PROFILE_KEYS = {
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
    "family_orientation", "career_ambition", "adventure_seeking", "social_consciousness",
    "spiritual_religious", "communication_style", "conflict_resolution",
    "love_language_words", "love_language_acts", "love_language_gifts",
    "love_language_time", "love_language_touch", "attachment_style",
    "questionnaire_version", "questionnaire_responses",
}


def test_score_questionnaire_shape():
    answers = full_answers()
    profile = score_questionnaire(answers)
    assert set(profile) == PROFILE_KEYS
    assert profile["questionnaire_version"] == "2026.1"
    assert profile["questionnaire_responses"] == answers
    assert profile["questionnaire_responses"] is not answers
    for k in PROFILE_KEYS - {"communication_style", "conflict_resolution", "attachment_style",
                             "questionnaire_version", "questionnaire_responses"}:
        assert isinstance(profile[k], float) and 0.0 <= profile[k] <= 100.0, k
    json.dumps(profile)


def test_score_questionnaire_validates_first():
    answers = full_answers()
    answers["openness"] = 99  # client-computed field is rejected
    errs = errors_of(score_questionnaire, answers)
    assert [e["question_id"] for e in errs] == ["openness"]
    errs = errors_of(score_questionnaire, {"bf_1": 3})
    assert len(errs) == len(REQUIRED_QUESTION_IDS) - 1


def test_score_questionnaire_deterministic():
    answers = full_answers()
    first = score_questionnaire(answers)
    for _ in range(20):
        assert score_questionnaire(dict(answers)) == first
    reordered = dict(reversed(list(answers.items())))
    got = score_questionnaire(reordered)
    got.pop("questionnaire_responses")
    exp = dict(first)
    exp.pop("questionnaire_responses")
    assert got == exp
    assert json.dumps(got, sort_keys=True) == json.dumps(exp, sort_keys=True)
