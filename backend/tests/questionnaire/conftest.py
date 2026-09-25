"""Fixtures for the pure questionnaire unit tests (no DB, no app startup)."""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from qn_helpers import build_answers  # noqa: E402


@pytest.fixture
def complete_answers():
    return build_answers()
