"""Tests for M-033: claude_gainer_st blocked-aggregator reconcile.

Verifies that systems whose source name appears in PERMANENTLY_KILLED_STRATEGIES
are marked is_stale=True, is_blocked_aggregator=True, active_picks=0, status=BLOCKED
in the systems payload — even if their source files have fresh picks.
"""
import json
import os
import sys
from unittest.mock import patch

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _make_pick(source_system, strategy, status="OPEN"):
    import datetime
    return {
        "source_system": source_system,
        "strategy": strategy,
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "status": status,
        "pnl_pct": 0.0,
        "confidence": 0.8,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


def _run_collect(active, closed=None):
    from audit_trail.dashboard_generator import collect_system_stats
    result = collect_system_stats(active, closed or [])
    # collect_system_stats returns (result, sys_strategies) or just result depending on version
    if isinstance(result, tuple):
        return result[0], result[1]
    return result, {}


def test_blocked_aggregator_marked_stale():
    """claude_gainer_st system must be is_stale=True even with fresh picks."""
    active = [_make_pick("claude_gainer_st", "st_fear_greed_contrarian")]
    result, _ = _run_collect(active)
    entry = next((r for r in result if r["name"] == "claude_gainer_st"), None)
    assert entry is not None, "claude_gainer_st must appear in systems payload"
    assert entry["is_stale"] is True, "claude_gainer_st must be stale (killed aggregator)"


def test_blocked_aggregator_flag_set():
    """claude_gainer_st must have is_blocked_aggregator=True."""
    active = [_make_pick("claude_gainer_st", "st_fear_greed_contrarian")]
    result, _ = _run_collect(active)
    entry = next(r for r in result if r["name"] == "claude_gainer_st")
    assert entry.get("is_blocked_aggregator") is True


def test_blocked_aggregator_active_picks_zero():
    """claude_gainer_st active_picks must be 0 in payload (no gate-passing picks)."""
    active = [_make_pick("claude_gainer_st", "st_fear_greed_contrarian")]
    result, _ = _run_collect(active)
    entry = next(r for r in result if r["name"] == "claude_gainer_st")
    assert entry["active_picks"] == 0, "blocked aggregator must show 0 active picks"


def test_blocked_aggregator_status_blocked():
    """claude_gainer_st status must be BLOCKED in payload."""
    active = [_make_pick("claude_gainer_st", "st_fear_greed_contrarian")]
    result, _ = _run_collect(active)
    entry = next(r for r in result if r["name"] == "claude_gainer_st")
    assert entry["status"] == "BLOCKED", f"expected BLOCKED, got {entry['status']}"


def test_blocked_aggregator_last_signal_at_null():
    """claude_gainer_st last_signal_at must be None in payload."""
    active = [_make_pick("claude_gainer_st", "st_fear_greed_contrarian")]
    result, _ = _run_collect(active)
    entry = next(r for r in result if r["name"] == "claude_gainer_st")
    assert entry["last_signal_at"] is None, "blocked aggregator last_signal_at must be None"


def test_non_killed_system_unaffected():
    """A healthy system must not be marked as blocked aggregator."""
    active = [_make_pick("alpha_engine", "some_good_strategy")]
    result, _ = _run_collect(active)
    entry = next((r for r in result if r["name"] == "alpha_engine"), None)
    if entry:
        assert entry.get("is_blocked_aggregator") is not True, \
            "alpha_engine must not be marked as blocked aggregator"
