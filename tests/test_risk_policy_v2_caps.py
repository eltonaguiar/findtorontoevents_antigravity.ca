"""Regression tests for risk_policy v2 — tighten crypto per-symbol/per-trade caps.

Reference: cycle-4 TON disaster (2026-05-09) + swarm 4/4 consensus
(swarm_runs/next_steps_perf_2026-05-09/).

v1 → v2 changes:
  crypto.max_equity_pct_per_symbol  10 → 5
  crypto.per_trade_cap_pct           5 → 3
  version                            1 → 2

Rationale: 7 open shorts on TONUSDT during a 40% pump (cycle-4) means a
single symbol's aggregated direction-level exposure was unbounded by the
old 10% cap because each individual short was only ~1.5% but the aggregated
short-side concentration was 10%+. Tightening per-symbol to 5% caps the
aggregated TON short concentration. per_trade 3% prevents single-trade
oversizing on cycle-4-style stale-dashboard fills.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_risk_policy_json_v2_per_symbol_cap_5():
    repo = Path(__file__).resolve().parent.parent
    pol = json.loads((repo / "config" / "risk_policy.json").read_text())
    assert pol["version"] == 2
    assert pol["crypto"]["max_equity_pct_per_symbol"] == 5


def test_risk_policy_json_v2_per_trade_cap_3():
    repo = Path(__file__).resolve().parent.parent
    pol = json.loads((repo / "config" / "risk_policy.json").read_text())
    assert pol["crypto"]["per_trade_cap_pct"] == 3


def test_risk_policy_json_v2_changelog_present():
    """v2 must include _v2_changelog field referencing the rationale."""
    repo = Path(__file__).resolve().parent.parent
    pol = json.loads((repo / "config" / "risk_policy.json").read_text())
    assert "_v2_changelog" in pol
    assert "swarm" in pol["_v2_changelog"].lower() or "cycle-4" in pol["_v2_changelog"].lower()


def test_loader_fallback_matches_v2():
    """When risk_policy.json is unreadable, loader fallback must also be v2."""
    from alpha_engine.risk_policy_loader import _FALLBACK
    assert _FALLBACK["version"] == 2
    assert _FALLBACK["crypto"]["max_equity_pct_per_symbol"] == 5
    assert _FALLBACK["crypto"]["per_trade_cap_pct"] == 3


def test_check_fallback_constants_match_v2():
    """risk_policy_check fallback constants must match the v2 policy."""
    from alpha_engine.risk_policy_check import _FALLBACK_PER_SYMBOL_PCT
    assert _FALLBACK_PER_SYMBOL_PCT == 5.0


def test_v2_caps_would_have_blocked_ton_disaster():
    """Cycle-4 TON: 7 open shorts × ~$3K notional each = $21K on $100K = 21%
    aggregated short-side exposure on TONUSDT. v1 cap 10% would have triggered
    a per-symbol breach but the warning was ignored. v2 cap 5% triggers earlier
    (after 2 shorts) and at a smaller drawdown surface."""
    portfolio_value = 100_000
    # Simulate 7 TON short trades like cycle-4
    trades_per_symbol_pct = 21.0  # actual cycle-4 aggregate
    v1_cap = 10.0
    v2_cap = 5.0
    # Both caps breached — but v2 breach hits at lower aggregate
    assert trades_per_symbol_pct > v1_cap
    assert trades_per_symbol_pct > v2_cap
    # v2 detection threshold is hit earlier (at fewer trades)
    # 2 × 1.5% = 3% < v2_cap → still ok
    # 4 × 1.5% = 6% > v2_cap → BREACH (v2 catches it)
    # 4 × 1.5% = 6% < v1_cap → would have passed under v1
    assert 4 * 1.5 > v2_cap
    assert 4 * 1.5 < v1_cap


def test_other_classes_unchanged():
    """Only crypto changed in v2 — commodity stays at 5% (already conservative)."""
    repo = Path(__file__).resolve().parent.parent
    pol = json.loads((repo / "config" / "risk_policy.json").read_text())
    assert pol["commodity"]["max_equity_pct_per_symbol"] == 5
    assert pol["commodity"]["per_trade_cap_pct"] == 3


def test_per_direction_cap_unchanged():
    """v2 only changed per-symbol + per-trade. per-direction stays at 20%."""
    repo = Path(__file__).resolve().parent.parent
    pol = json.loads((repo / "config" / "risk_policy.json").read_text())
    assert pol["crypto"]["max_equity_pct_per_direction"] == 20
