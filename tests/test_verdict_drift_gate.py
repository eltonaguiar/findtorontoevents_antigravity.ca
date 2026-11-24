import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.verdict_drift_gate import compare  # noqa: E402


def test_no_change_passes():
    ok, msg = compare({"A": "KILL"}, {"A": "KILL"})
    assert ok and msg == "no drift"


def test_silent_change_fails_and_names_the_class():
    ok, msg = compare({"A": "KILL"}, {"A": "CANDIDATE"})
    assert not ok
    assert "A" in msg and "KILL" in msg and "CANDIDATE" in msg


def test_new_class_is_a_note_not_a_failure():
    ok, msg = compare({"A": "KILL"}, {"A": "KILL", "B": "WEAK"})
    assert ok
    assert "B" in msg


def test_vanished_class_is_a_note_not_a_failure():
    ok, msg = compare({"A": "KILL", "B": "WEAK"}, {"A": "KILL"})
    assert ok
    assert "B" in msg
