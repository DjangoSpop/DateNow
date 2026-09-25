import pytest

from qn_helpers import build_answers

from app.questionnaire import (
    AnswerValidationError,
    missing_required,
    question_ids,
    score,
    validate_answers,
)


def _errors(answers):
    with pytest.raises(AnswerValidationError) as exc:
        validate_answers(answers)
    assert isinstance(exc.value, ValueError)
    return exc.value.errors


def test_valid_partial_answers_are_normalized_in_presentation_order():
    out = validate_answers({"comm_1": "direct", "bf_2": 2, "bf_1": 5})
    assert out == {"bf_1": 5, "bf_2": 2, "comm_1": "direct"}
    assert list(out) == ["bf_1", "bf_2", "comm_1"]


def test_validate_returns_copy():
    src = {"bf_1": 4}
    out = validate_answers(src)
    out["bf_1"] = 1
    assert src == {"bf_1": 4}


def test_empty_is_valid():
    assert validate_answers({}) == {}


def test_full_valid_set(complete_answers):
    assert validate_answers(complete_answers) == complete_answers


@pytest.mark.parametrize("bad", [0, 6, -1, 100])
def test_scale_out_of_range(bad):
    assert set(_errors({"bf_1": bad})) == {"bf_1"}


@pytest.mark.parametrize("bad", [True, False])
def test_scale_bool_rejected(bad):
    assert "boolean" in _errors({"bf_1": bad})["bf_1"]


@pytest.mark.parametrize("bad", [4.0, 3.5, "4", None, [4], {"v": 4}])
def test_scale_wrong_type(bad):
    assert set(_errors({"val_1": bad})) == {"val_1"}


@pytest.mark.parametrize("bad", ["Direct and straightforward", "DIRECT", "", 1, True, None, "nope"])
def test_choice_invalid_value(bad):
    assert set(_errors({"comm_1": bad})) == {"comm_1"}


def test_unknown_ids_including_verify_and_non_string_keys():
    errs = _errors({"verify_1": "hello there", "bf_99": 3, 7: 3})
    assert errs == {"verify_1": "unknown question id", "bf_99": "unknown question id", "7": "unknown question id"}


def test_every_bad_id_is_listed():
    errs = _errors({
        "bf_1": 9, "bf_2": True, "bf_3": 2.0, "comm_1": "Direct and straightforward",
        "zzz": 1, "bf_4": 4,  # bf_4 valid
    })
    assert set(errs) == {"bf_1", "bf_2", "bf_3", "comm_1", "zzz"}


@pytest.mark.parametrize("bad", [None, [], "bf_1", 3])
def test_non_dict_rejected(bad):
    with pytest.raises(AnswerValidationError):
        validate_answers(bad)


def test_missing_required_order():
    ids = question_ids()
    assert missing_required({}) == ids
    assert missing_required(build_answers()) == []
    partial = build_answers()
    del partial["pref_5"], partial["bf_1"], partial["comm_2"]
    partial["att_1"] = None
    assert missing_required(partial) == ["bf_1", "comm_2", "att_1", "pref_5"]


def test_score_raises_on_incomplete():
    answers = build_answers()
    del answers["bf_10"], answers["rg_1"]
    with pytest.raises(AnswerValidationError) as exc:
        score(answers)
    assert exc.value.errors == {"bf_10": "required", "rg_1": "required"}


def test_score_raises_on_empty_with_all_ids():
    with pytest.raises(AnswerValidationError) as exc:
        score({})
    assert list(exc.value.errors) == question_ids()
    assert set(exc.value.errors.values()) == {"required"}


def test_score_raises_on_invalid_and_reports_both():
    answers = build_answers(bf_1=7, extra_q=1)
    del answers["ll_3"]
    with pytest.raises(AnswerValidationError) as exc:
        score(answers)
    assert set(exc.value.errors) == {"bf_1", "extra_q", "ll_3"}
    assert exc.value.errors["ll_3"] == "required"


def test_score_rejects_non_dict():
    with pytest.raises(AnswerValidationError):
        score(None)
