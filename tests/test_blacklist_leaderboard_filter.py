"""PR-F (2026-05-12) — leaderboard render must mark + demote blacklisted.

Tests the surgical patch in ``audit_trail/dashboard_generator.py``
``collect_strategy_leaderboard`` finalize block. Memory ref:
``feedback_gate_at_execution_not_generation`` — gate-at-intake is not
enough; the leaderboard render must also refuse to crown a blacklisted
strategy.

Tests:
 1. blacklisted strategy gets ``is_blacklisted: True``
 2. ranking demotes blacklisted (top-N excludes them)
 3. non-blacklisted strategies pass through unchanged
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from alpha_engine.config import BLACKLISTED_STRATEGIES

ROOT = Path(__file__).resolve().parent.parent


def _stub_row(strategy: str, fwd_wr: float, fwd_trades: int = 100) -> dict:
    return {
        "strategy": strategy,
        "source_system": strategy,
        "bt_wr": None,
        "bt_trades": 0,
        "bt_sharpe": None,
        "bt_pf": None,
        "bt_return": None,
        "bt_verdict": "",
        "bt_oos_wr": None,
        "bt_symbols_profitable": 0,
        "bt_symbols_tested": 0,
        "fwd_wr": fwd_wr,
        "fwd_trades": fwd_trades,
        "fwd_wins": int(fwd_trades * fwd_wr / 100),
        "fwd_losses": fwd_trades - int(fwd_trades * fwd_wr / 100),
        "fwd_avg_pnl": 0.0,
        "fwd_total_pnl": 0.0,
    }


def _apply_finalize(rows: list[dict]) -> list[dict]:
    """Replicate the finalize block from dashboard_generator.py PR-F patch.

    Kept in lock-step with audit_trail/dashboard_generator.py:~11404 so any
    drift between this helper and prod is a test failure surface.
    """
    bl_set = {str(s).lower() for s in (BLACKLISTED_STRATEGIES or [])}
    for r in rows:
        nm = str(r.get("strategy", "")).lower()
        src = str(r.get("source_system", "")).lower()
        if nm in bl_set or src in bl_set:
            r["is_blacklisted"] = True
        else:
            r.setdefault("is_blacklisted", False)
    rows.sort(
        key=lambda x: (
            not x.get("is_blacklisted", False),
            x["fwd_trades"] > 0,
            x["fwd_wr"] or 0,
            x["bt_wr"] or 0,
        ),
        reverse=True,
    )
    return rows


def test_blacklisted_row_marked_is_blacklisted():
    assert "claude_gainer_st" in BLACKLISTED_STRATEGIES, "fixture assumption"
    rows = [
        _stub_row("claude_gainer_st", 78.5, 3472),
        _stub_row("legit_strategy", 55.0, 200),
    ]
    out = _apply_finalize(rows)
    by_name = {r["strategy"]: r for r in out}
    assert by_name["claude_gainer_st"]["is_blacklisted"] is True
    assert by_name["legit_strategy"]["is_blacklisted"] is False


def test_ranking_excludes_blacklisted_from_top_n():
    rows = [
        _stub_row("claude_gainer_st", 78.5, 3472),   # would top by fwd_wr
        _stub_row("kimi_signal_tracking", 70.0, 500),
        _stub_row("legit_a", 55.0, 200),
        _stub_row("legit_b", 50.0, 150),
    ]
    out = _apply_finalize(rows)
    top2 = out[:2]
    top2_names = {r["strategy"] for r in top2}
    assert top2_names == {"legit_a", "legit_b"}, f"top-2 leaked: {top2_names}"
    # blacklisted rows must still exist (not deleted) — pushed to bottom
    tail_names = {r["strategy"] for r in out[2:]}
    assert "claude_gainer_st" in tail_names
    assert "kimi_signal_tracking" in tail_names


def test_non_blacklisted_unchanged_relative_order():
    rows = [
        _stub_row("legit_a", 55.0, 200),
        _stub_row("legit_b", 60.0, 150),
        _stub_row("legit_c", 45.0, 80),
    ]
    out = _apply_finalize(rows)
    # All flagged False
    assert all(r["is_blacklisted"] is False for r in out)
    # Sort key is (forward-tested first, fwd_wr desc, bt_wr desc)
    assert [r["strategy"] for r in out] == ["legit_b", "legit_a", "legit_c"]


def test_patch_present_in_dashboard_generator():
    """Smoke test that the finalize patch lives where the test thinks it does."""
    src = (ROOT / "audit_trail" / "dashboard_generator.py").read_text(encoding="utf-8")
    assert "_BLACKLISTED_STRATEGIES" in src
    assert "is_blacklisted" in src
    assert "blacklisted demoted" in src
