"""Tests for M-010 Phase 2: get_eligible_picks.py tier gate filter.

Verifies that filter_picks() correctly splits swarm_picks.json records
into eligible/blocked based on passes_tier_gate().
"""
import os
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.swarm.get_eligible_picks import filter_picks


def _pick(tier, outcome=None):
    return {"consensus_tier": tier, "outcome": outcome}


# --- Basic eligibility ---

def test_strong_tier_eligible_at_strong_gate():
    eligible, blocked = filter_picks([_pick("strong")], min_tier="strong")
    assert len(eligible) == 1
    assert len(blocked) == 0


def test_unanimous_eligible_at_strong_gate():
    eligible, blocked = filter_picks([_pick("unanimous")], min_tier="strong")
    assert len(eligible) == 1
    assert len(blocked) == 0


def test_moderate_blocked_at_strong_gate():
    eligible, blocked = filter_picks([_pick("moderate")], min_tier="strong")
    assert len(eligible) == 0
    assert len(blocked) == 1


def test_single_blocked_at_strong_gate():
    eligible, blocked = filter_picks([_pick("single")], min_tier="strong")
    assert len(eligible) == 0
    assert len(blocked) == 1


def test_control_blocked_at_strong_gate():
    eligible, blocked = filter_picks([_pick("control")], min_tier="strong")
    assert len(eligible) == 0
    assert len(blocked) == 1


def test_moderate_eligible_at_moderate_gate():
    eligible, blocked = filter_picks([_pick("moderate")], min_tier="moderate")
    assert len(eligible) == 1
    assert len(blocked) == 0


# --- Mixed batch ---

def test_mixed_batch_correct_split():
    picks = [
        _pick("unanimous"),
        _pick("strong"),
        _pick("moderate"),
        _pick("single"),
        _pick("control"),
    ]
    eligible, blocked = filter_picks(picks, min_tier="strong")
    assert len(eligible) == 2   # unanimous + strong
    assert len(blocked) == 3    # moderate + single + control


# --- open_only mode ---

def test_open_only_excludes_resolved_picks():
    picks = [
        _pick("unanimous", outcome={"exit_reason": "TP_HIT"}),
        _pick("strong", outcome=None),
    ]
    eligible, blocked = filter_picks(picks, min_tier="strong", open_only=True)
    # unanimous has outcome → excluded from scope (not in either list)
    assert len(eligible) == 1
    assert eligible[0]["consensus_tier"] == "strong"


def test_open_only_all_resolved_returns_empty():
    picks = [
        _pick("unanimous", outcome={"exit_reason": "TP_HIT"}),
        _pick("strong", outcome={"exit_reason": "SL_HIT"}),
    ]
    eligible, blocked = filter_picks(picks, min_tier="strong", open_only=True)
    assert len(eligible) == 0
    assert len(blocked) == 0


def test_open_only_false_includes_resolved():
    picks = [
        _pick("strong", outcome={"exit_reason": "TP_HIT"}),
    ]
    eligible, blocked = filter_picks(picks, min_tier="strong", open_only=False)
    assert len(eligible) == 1


# --- Kill-switch ---

def test_kill_switch_all_picks_pass():
    picks = [_pick("control"), _pick("single"), _pick("moderate")]
    with patch.dict(os.environ, {"SWARM_TIER_GATE_ENABLED": "0"}):
        eligible, blocked = filter_picks(picks, min_tier="unanimous")
    assert len(eligible) == 3
    assert len(blocked) == 0


# --- Empty input ---

def test_empty_picks_returns_empty():
    eligible, blocked = filter_picks([], min_tier="strong")
    assert eligible == []
    assert blocked == []
