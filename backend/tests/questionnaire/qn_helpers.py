"""Shared helpers for questionnaire tests (unique module name to avoid clashing with other conftests)."""
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.questionnaire.bank import QUESTIONS, SCALE  # noqa: E402


def build_answers(scale_value=3, choice_index=0, **overrides):
    """Complete valid answers: every scale item = scale_value, every choice = option[choice_index]."""
    answers = {}
    for q in QUESTIONS:
        if q.type == SCALE:
            answers[q.id] = scale_value
        else:
            answers[q.id] = q.options[min(choice_index, len(q.options) - 1)].value
    answers.update(overrides)
    return answers


def items_for(trait):
    return [q for q in QUESTIONS if q.type == SCALE and q.trait == trait]
