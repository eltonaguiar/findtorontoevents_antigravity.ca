"""Tests for tools/blacklist_reconciler.py."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pytest

from tools.blacklist_reconciler import (
    classify, parse_blacklist, MUTATE_PF, RESURRECT_PF, RESURRECT_WR, RESURRECT_N,
)


def test_classify_resurrection_candidate():
    live = {"profit_factor": 2.53, "win_rate": 55.6, "closed_picks": 123}
    assert classify(live, 0.55) == "RESURRECTION_CANDIDATE"


def test_classify_kill_confirmed_low_pf():
    live = {"profit_factor": 0.4, "win_rate": 30, "closed_picks": 50}
    assert classify(live, 0.5) == "KILL_CONFIRMED"


def test_classify_mutate_first_high_pf_low_wr():
    live = {"profit_factor": 1.31, "win_rate": 48.8, "closed_picks": 1891}
    assert classify(live, None) == "MUTATE_FIRST"


def test_classify_no_live_data():
    assert classify({}, 0.5) == "NO_LIVE_DATA"


def test_classify_low_n_falls_to_kill():
    """High PF but n<30 not enough to resurrect — needs corroborating sample."""
    live = {"profit_factor": 5.0, "win_rate": 80, "closed_picks": 15}
    assert classify(live, 0.5) == "KILL_CONFIRMED"


def test_parse_blacklist_returns_entries():
    entries = parse_blacklist()
    assert len(entries) > 0
    # Each entry must have at least a name
    for e in entries:
        assert "name" in e
        assert e["name"]


def test_parse_blacklist_extracts_pf_from_comment():
    """At least one entry should have parsed PF from the comment string."""
    entries = parse_blacklist()
    with_pf = [e for e in entries if e.get("blacklist_pf") is not None]
    assert len(with_pf) > 0, "expected at least one entry with parseable PF comment"


def test_thresholds_sane():
    assert RESURRECT_PF == 1.5
    assert RESURRECT_WR == 50.0
    assert RESURRECT_N == 30
    assert MUTATE_PF < RESURRECT_PF
