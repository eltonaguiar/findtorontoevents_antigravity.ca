"""Tests for M-019: Portfolio MDD hard-cap per Charter §7 (Tier 2 MDD ≤ 20%).

Verifies that gate4_profit_lock():
1. Blocks new picks when avg_unrealized_pnl_pct < -20% across all account positions
2. Approves when avg_unrealized is above the threshold
3. Respects kill-switch PORTFOLIO_MDD_GATE_ENABLED=0 (disables the gate)
4. Is fail-open when no account positions exist
5. Existing profit-lock logic is unaffected by M-019
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from audit_trail.portfolio_gates import gate4_profit_lock, GATE4_MDD_LIMIT_PCT


def _pick(account="ACC1"):
    return {"account": account, "symbol": "BTCUSDT", "asset_class": "CRYPTO"}


def _pos(account="ACC1", unrealized_pnl_pct=0.0, symbol="BTCUSDT", locked=True):
    return {
        "account": account,
        "symbol": symbol,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "sl_at_breakeven": locked,
        "partial_close_done": False,
        "trailing_stop_armed": False,
    }


def test_mdd_limit_constant():
    """GATE4_MDD_LIMIT_PCT must be 20.0 per Charter §7."""
    assert GATE4_MDD_LIMIT_PCT == 20.0


def test_mdd_blocks_when_avg_below_threshold(monkeypatch):
    """Avg unrealized PnL < -20% must return REJECT with gate 4_mdd_hard_cap."""
    monkeypatch.delenv("PORTFOLIO_MDD_GATE_ENABLED", raising=False)
    positions = [
        _pos(unrealized_pnl_pct=-25.0),
        _pos(unrealized_pnl_pct=-30.0),
    ]
    result = gate4_profit_lock(_pick(), positions)
    assert result["verdict"] == "REJECT"
    assert result["gate"] == "4_mdd_hard_cap"
    assert "M-019" in result["reason"]
    assert "-20" in result["reason"]


def test_mdd_approves_when_avg_above_threshold(monkeypatch):
    """Avg unrealized PnL ≥ -20% must pass through to normal profit-lock logic."""
    monkeypatch.delenv("PORTFOLIO_MDD_GATE_ENABLED", raising=False)
    positions = [
        _pos(unrealized_pnl_pct=-15.0),
        _pos(unrealized_pnl_pct=-10.0),
    ]
    result = gate4_profit_lock(_pick(), positions)
    assert result["verdict"] == "APPROVE"
    assert result["gate"] == "4_profit_lock"


def test_mdd_exactly_at_threshold_is_approved(monkeypatch):
    """Avg unrealized == -20.0% is NOT below threshold (strict <), must APPROVE."""
    monkeypatch.delenv("PORTFOLIO_MDD_GATE_ENABLED", raising=False)
    positions = [_pos(unrealized_pnl_pct=-20.0)]
    result = gate4_profit_lock(_pick(), positions)
    assert result["verdict"] == "APPROVE"


def test_kill_switch_disables_mdd_gate(monkeypatch):
    """PORTFOLIO_MDD_GATE_ENABLED=0 must disable MDD block even with severe drawdown."""
    monkeypatch.setenv("PORTFOLIO_MDD_GATE_ENABLED", "0")
    positions = [
        _pos(unrealized_pnl_pct=-50.0),
        _pos(unrealized_pnl_pct=-60.0),
    ]
    result = gate4_profit_lock(_pick(), positions)
    assert result["gate"] != "4_mdd_hard_cap", "Kill-switch must prevent MDD block"


def test_empty_positions_is_fail_open(monkeypatch):
    """No positions → gate must not block (fail-open, avoid blocking when no data)."""
    monkeypatch.delenv("PORTFOLIO_MDD_GATE_ENABLED", raising=False)
    result = gate4_profit_lock(_pick(), [])
    assert result["verdict"] == "APPROVE"


def test_mdd_gate_only_considers_matching_account(monkeypatch):
    """MDD computation must only use positions matching pick's account."""
    monkeypatch.delenv("PORTFOLIO_MDD_GATE_ENABLED", raising=False)
    positions = [
        _pos(account="ACC1", unrealized_pnl_pct=-5.0),   # pick's account — above threshold
        _pos(account="ACC2", unrealized_pnl_pct=-99.0),  # different account — must be ignored
    ]
    result = gate4_profit_lock(_pick(account="ACC1"), positions)
    assert result["gate"] != "4_mdd_hard_cap"
