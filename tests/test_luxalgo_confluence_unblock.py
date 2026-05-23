"""Regression guards for the luxalgo_confluence unblock (2026-04-29).

Per Near-Miss Deep-Dive panel (reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md),
luxalgo_confluence was unblocked from BOTH:
  - alpha_engine/strategy_blocklist.py: _PAPER_ONLY_STRATEGIES (Fix A)
  - alpha_engine/data/core_whitelist.json: kill_list (Fix B)

These tests pin the unblock so future kill-list/blocklist refreshes
don't silently re-add it. They also serve as the regression guard for
the broader paper-only / kill_list scaffolding (other entries must be
preserved).

Standalone metrics that justify the unblock:
  n=205, WR 52.2%, PF 1.66 (past Tier 2 PF>=1.5; past PROVEN n>=200)
  Symmetric LONG/SHORT (52.4%/52.0%); 73 TP / 73 SL split
  Win/loss magnitude asymmetry: 2.21% / 1.45% = 1.52x
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_WHITELIST_PATH = REPO_ROOT / "alpha_engine" / "data" / "core_whitelist.json"


# ── Fix A: _PAPER_ONLY_STRATEGIES ───────────────────────────────────────────


def test_luxalgo_confluence_not_in_paper_only_strategies():
    """luxalgo_confluence must be removed from _PAPER_ONLY_STRATEGIES."""
    from alpha_engine.strategy_blocklist import _PAPER_ONLY_STRATEGIES

    assert "luxalgo_confluence" not in _PAPER_ONLY_STRATEGIES, (
        "luxalgo_confluence is back in _PAPER_ONLY_STRATEGIES — this regresses "
        "the 2026-04-29 Near-Miss Deep-Dive unblock. If consensus-combo "
        "toxicity returned, re-add it as a composite-pair entry in "
        "_BLOCKED_SOURCE_STRATEGY_PAIRS, NOT a strategy-wide kill."
    )


def test_luxalgo_confluence_not_blocked_by_helpers():
    """is_blocked_strategy() and block_reason() must not block luxalgo_confluence."""
    from alpha_engine.strategy_blocklist import (
        block_reason,
        is_blocked_pick,
        is_blocked_strategy,
    )

    assert is_blocked_strategy("luxalgo_confluence") is False
    assert block_reason("luxalgo_confluence") == ""
    assert (
        is_blocked_pick(
            {"strategy": "luxalgo_confluence", "source_system": "luxalgo_filters"}
        )
        is False
    )


def test_other_paper_only_strategies_preserved():
    """Regression guard: other _PAPER_ONLY_STRATEGIES entries must remain."""
    from alpha_engine.strategy_blocklist import _PAPER_ONLY_STRATEGIES

    # Sample entries that MUST stay paper-flagged (per their own gate ladders)
    must_remain_paper = {
        "ARE_LONG",
        "RC_LONG",
        "SWEEP_SHORT",
        "bollinger_squeeze_stochastic_breakout",
        "macd_obv_momentum",
        "fibonacci_rsi_mean_reversion",
        "intermarket-flow-scout",
        "copy_hl_whale",
        "crypto_mtf_ema_slope_alignment_v1",
        "golden_combo_crypto_quan_rsi",
    }
    missing = must_remain_paper - _PAPER_ONLY_STRATEGIES
    assert not missing, (
        f"_PAPER_ONLY_STRATEGIES is missing entries that must remain paper-only: "
        f"{sorted(missing)}. Did the luxalgo unblock accidentally remove "
        f"unrelated entries?"
    )


# ── Fix B: core_whitelist.json kill_list ────────────────────────────────────


@pytest.fixture(scope="module")
def core_whitelist_data():
    assert CORE_WHITELIST_PATH.exists(), f"Missing: {CORE_WHITELIST_PATH}"
    return json.loads(CORE_WHITELIST_PATH.read_text(encoding="utf-8"))


def test_luxalgo_confluence_not_in_kill_list(core_whitelist_data):
    """Bare-name entry must be removed from kill_list."""
    kl = core_whitelist_data.get("kill_list", [])
    assert "luxalgo_confluence" not in kl, (
        "luxalgo_confluence is back in core_whitelist.json kill_list — this "
        "regresses the 2026-04-29 unblock. Note PR #519 added a 21d "
        "auto-expiry, but several non-dashboard kill_list readers "
        "(forward_validator.py, isolated_signal_integrator.py, the "
        "dashboard_generator.py:7707 ad-hoc loader) do NOT honor auto-expiry "
        "— so the static entry must stay removed."
    )


def test_luxalgo_filters_qualified_not_in_kill_list(core_whitelist_data):
    """source-qualified entry must also be removed from kill_list."""
    kl = core_whitelist_data.get("kill_list", [])
    assert "luxalgo_filters::luxalgo_confluence" not in kl


def test_kill_list_unblocks_audit_entry_present(core_whitelist_data):
    """Audit log must record the 2026-04-29 luxalgo unblock."""
    md = core_whitelist_data.get("metadata", {})
    unblocks = md.get("kill_list_unblocks", [])
    luxalgo_entries = [
        u
        for u in unblocks
        if "luxalgo_confluence"
        in (u.get("strategies_unblocked", []) + u.get("removed_entries", []))
    ]
    assert luxalgo_entries, (
        "metadata.kill_list_unblocks audit log missing the luxalgo_confluence "
        "entry. Future kill-list refreshes need this paper trail to know "
        "why these entries were removed without a corresponding kill_run."
    )


def test_other_kill_list_entries_preserved(core_whitelist_data):
    """Regression guard: removing luxalgo entries must not remove others."""
    kl = core_whitelist_data.get("kill_list", [])
    # Sample of unrelated kill_list entries that must remain
    must_remain_killed = {
        "ml_crypto_pred",
        "stocks_competition",
        "fast_stocks_competition",
        "multi_asset_scanner",
    }
    missing = must_remain_killed - set(kl)
    assert not missing, (
        f"kill_list lost unrelated entries during the luxalgo unblock: "
        f"{sorted(missing)}"
    )
    # Also ensure list is still substantial — luxalgo unblock removes 2; if
    # the file was truncated we'd see this number drop dramatically.
    assert len(kl) >= 500, (
        f"kill_list size dropped to {len(kl)} — expected ~540 (2 removed by "
        f"this PR). Suggests bulk truncation, not surgical edit."
    )


# ── Integration: the unblock must actually let a luxalgo pick through ───────


def test_passes_active_gate_accepts_luxalgo_confluence_pick():
    """A well-formed luxalgo_confluence pick must not be killed by the gate.

    This pick is constructed to clear the structural checks that
    passes_active_gate enforces independently of the strategy-name gate
    (positive expected return, finite numbers, etc.). Anything beyond the
    strategy-name gate is the responsibility of other tests; this one only
    pins that the strategy-name path no longer rejects luxalgo_confluence.
    """
    from alpha_engine.strategy_blocklist import is_blocked_pick

    pick = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "strategy": "luxalgo_confluence",
        "source_system": "luxalgo_filters",
        "score": 75.0,
        "confidence": 0.62,
        "rr_ratio": 1.8,
        "expected_pct": 2.1,
        "stop_pct": 1.45,
        "tp_pct": 2.21,
        "asset_class": "CRYPTO",
        "ml_score": 0.66,
    }
    # The strategy-name gate (the layer this PR fixes) must let this pick
    # through. Other gates (fresh data, R:R, etc.) live in quality_gates.py
    # and are out-of-scope for this regression.
    assert is_blocked_pick(pick) is False, (
        "luxalgo_confluence pick is still being blocked by the strategy-name "
        "blocklist after the 2026-04-29 unblock — Fix A regressed."
    )
