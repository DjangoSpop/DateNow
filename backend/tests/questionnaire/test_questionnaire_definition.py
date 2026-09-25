import json

from qn_helpers import build_answers  # noqa: F401  (ensures backend on sys.path)

from app.questionnaire import (
    QUESTIONNAIRE_VERSION,
    get_definition,
    question_ids,
    total_required,
)
from app.questionnaire.bank import QUESTIONS

EXPECTED_SECTIONS = ["personality", "values", "love", "communication", "attachment", "goals", "preferences"]


def test_version():
    assert QUESTIONNAIRE_VERSION == "ipip-v1"
    assert get_definition()["version"] == "ipip-v1"


def test_top_level_shape_and_json_roundtrip():
    d = get_definition()
    assert set(d) == {"version", "sections"}
    assert json.loads(json.dumps(d)) == d


def test_sections_shape_and_order():
    d = get_definition()
    assert [s["id"] for s in d["sections"]] == EXPECTED_SECTIONS
    for s in d["sections"]:
        assert set(s) == {"id", "title", "description", "estimated_minutes", "questions"}
        assert isinstance(s["title"], str) and s["title"]
        assert isinstance(s["description"], str) and s["description"]
        assert isinstance(s["estimated_minutes"], int) and s["estimated_minutes"] > 0
        assert s["questions"]


def test_every_question_shape():
    for s in get_definition()["sections"]:
        for q in s["questions"]:
            assert isinstance(q["id"], str) and q["id"]
            assert isinstance(q["text"], str) and q["text"]
            assert q["required"] is True
            assert q["type"] in ("scale", "single_choice")
            if q["type"] == "scale":
                assert set(q) == {"id", "text", "type", "required", "scale"}
                sc = q["scale"]
                assert sc["min"] == 1 and sc["max"] == 5
                assert set(sc["labels"]) == {"1", "2", "3", "4", "5"}
                assert all(isinstance(v, str) and v for v in sc["labels"].values())
            else:
                assert set(q) == {"id", "text", "type", "required", "options"}
                assert len(q["options"]) >= 2
                values = [o["value"] for o in q["options"]]
                assert len(values) == len(set(values))
                for o in q["options"]:
                    assert set(o) == {"value", "label"}
                    assert o["value"].replace("_", "").isalpha() and o["value"] == o["value"].lower()
                    assert o["label"]


def test_ids_unique_and_presentation_order():
    ids = [q["id"] for s in get_definition()["sections"] for q in s["questions"]]
    assert len(ids) == len(set(ids))
    assert ids == question_ids()


def test_counts():
    ids = question_ids()
    assert total_required() == 71 == len(ids)
    assert sum(i.startswith("bf_") for i in ids) == 44
    assert not any(i.startswith("verify_") for i in ids)


def test_no_scoring_metadata_leaks():
    blob = json.dumps(get_definition())
    assert "reverse" not in blob
    assert "trait" not in blob


def test_definition_is_fresh_copy():
    d = get_definition()
    d["sections"][0]["questions"][0]["text"] = "hacked"
    d["sections"][0]["questions"][0]["scale"]["labels"]["1"] = "hacked"
    d2 = get_definition()
    assert d2["sections"][0]["questions"][0]["text"] == "I am the life of the party"
    assert d2["sections"][0]["questions"][0]["scale"]["labels"]["1"] == "Strongly Disagree"


def test_contract_example_values():
    qs = {q.id: q for q in QUESTIONS}
    assert qs["bf_1"].text == "I am the life of the party"
    assert ("direct", "Direct and straightforward") in [(o.value, o.label) for o in qs["comm_1"].options]
