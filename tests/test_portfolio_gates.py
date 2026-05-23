"""Tests for audit_trail/portfolio_gates.py (PCG-5)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pytest

from audit_trail.portfolio_gates import (
    canonical,
    evaluate_pick,
    gate1_regime,
    gate2_cross_account,
    gate3_concentration,
    gate4_profit_lock,
    gate5_correlation_demote,
)


def test_canonical_collapses_btc_variants():
    assert canonical("BTC-USD") == "BTC"
    assert canonical("BINANCE:BTCUSDT") == "BTC"
    assert canonical("COINBASE:BTCUSDC.P") == "BTC"


def test_canonical_strips_exchange_prefix_default():
    assert canonical("NASDAQ:NVDA") == "NVDA"
    assert canonical("FX:USDJPY") == "USDJPY"


# Gate 1
def test_gate1_blocks_bull_equity_short_no_catalyst():
    r = gate1_regime({"asset_class": "EQUITY", "direction": "SHORT"}, regime="BULL")
    assert r["verdict"] == "REJECT"


def test_gate1_allows_bull_equity_short_with_catalyst():
    r = gate1_regime({"asset_class": "EQUITY", "direction": "SHORT",
                       "thesis_catalyst": "earnings_miss"}, regime="BULL")
    assert r["verdict"] == "APPROVE"


def test_gate1_allows_bull_equity_long():
    r = gate1_regime({"asset_class": "EQUITY", "direction": "LONG"}, regime="BULL")
    assert r["verdict"] == "APPROVE"


def test_gate1_blocks_bear_equity_long_no_catalyst():
    r = gate1_regime({"asset_class": "EQUITY", "direction": "LONG"}, regime="BEAR")
    assert r["verdict"] == "REJECT"


def test_gate1_passes_through_non_equity():
    r = gate1_regime({"asset_class": "CRYPTO", "direction": "SHORT"}, regime="BULL")
    assert r["verdict"] == "APPROVE"


# Gate 2
def test_gate2_blocks_duplicate_same_account():
    pick = {"account": "theswarm", "symbol": "BINANCE:BTCUSDT", "direction": "LONG"}
    pos = [{"account": "theswarm", "symbol": "BTC-USD", "direction": "LONG"}]
    r = gate2_cross_account(pick, pos)
    assert r["verdict"] == "REJECT"
    assert "duplicate" in r["reason"]


def test_gate2_nets_opposite_across_accounts():
    pick = {"account": "Leap", "symbol": "BTCUSDC.P", "direction": "LONG"}
    pos = [{"account": "theswarm", "symbol": "BINANCE:BTCUSDT", "direction": "SHORT"}]
    r = gate2_cross_account(pick, pos)
    assert r["verdict"] == "NET"


def test_gate2_approves_unique_symbol():
    pick = {"account": "theswarm", "symbol": "BINANCE:LINKUSDT", "direction": "LONG"}
    pos = [{"account": "theswarm", "symbol": "BINANCE:BTCUSDT", "direction": "LONG"}]
    r = gate2_cross_account(pick, pos)
    assert r["verdict"] == "APPROVE"


# Gate 3
def test_gate3_rejects_at_75_pct():
    conc = {"COMMODITY": {"top_symbol": "CT=F", "top_share_pct": 75.57}}
    pick = {"asset_class": "COMMODITY", "symbol": "CT=F"}
    r = gate3_concentration(pick, conc)
    assert r["verdict"] == "REJECT"


def test_gate3_approves_non_top_symbol():
    conc = {"COMMODITY": {"top_symbol": "CT=F", "top_share_pct": 75.57}}
    pick = {"asset_class": "COMMODITY", "symbol": "NYMEX:MCL1!"}
    r = gate3_concentration(pick, conc)
    assert r["verdict"] == "APPROVE"


def test_gate3_warn_zone_50_to_70():
    conc = {"EQUITY": {"top_symbol": "NVDA", "top_share_pct": 55.0}}
    pick = {"asset_class": "EQUITY", "symbol": "NASDAQ:NVDA"}
    r = gate3_concentration(pick, conc)
    assert r["verdict"] == "REJECT"  # WARN tier still rejects


# Gate 4
def test_gate4_blocks_account_with_unlocked_winners():
    pick = {"account": "theswarm"}
    pos = [{"account": "theswarm", "symbol": "AAA",
            "unrealized_pnl_pct": 5.0,
            "sl_at_breakeven": False,
            "partial_close_done": False,
            "trailing_stop_armed": False}]
    r = gate4_profit_lock(pick, pos)
    assert r["verdict"] == "REJECT"


def test_gate4_approves_when_winner_has_be_sl():
    pick = {"account": "theswarm"}
    pos = [{"account": "theswarm", "symbol": "AAA",
            "unrealized_pnl_pct": 5.0,
            "sl_at_breakeven": True}]
    r = gate4_profit_lock(pick, pos)
    assert r["verdict"] == "APPROVE"


def test_gate4_approves_when_other_account_unlocked():
    pick = {"account": "theswarm"}
    pos = [{"account": "Leap", "symbol": "AAA", "unrealized_pnl_pct": 5.0,
            "sl_at_breakeven": False}]
    r = gate4_profit_lock(pick, pos)
    assert r["verdict"] == "APPROVE"  # different account


# Gate 5
def test_gate5_demotes_correlated_class():
    corr = {
        "classes_resolved": ["EQUITY", "COMMODITY_GOLD"],
        "current_correlation_matrix": [[1.0, 0.77], [0.77, 1.0]],
    }
    pick = {"asset_class": "COMMODITY"}
    r = gate5_correlation_demote(pick, corr)
    assert r["verdict"] == "DEMOTE"
    assert r.get("sizing_adjustment") == 0.5


def test_gate5_approves_independent_class():
    corr = {
        "classes_resolved": ["EQUITY", "FUTURES_COT"],
        "current_correlation_matrix": [[1.0, 0.04], [0.04, 1.0]],
    }
    pick = {"asset_class": "FUTURES"}
    r = gate5_correlation_demote(pick, corr)
    assert r["verdict"] == "APPROVE"


# Integration
def test_evaluate_pick_returns_action_field():
    pick = {"pick_id": "t1", "account": "theswarm", "symbol": "BINANCE:LINKUSDT",
            "direction": "LONG", "asset_class": "CRYPTO"}
    v = evaluate_pick(pick, all_positions=[])
    assert "action" in v
    assert v["action"] in {"APPROVE", "APPROVE_HALF", "REJECT", "NET"}
    assert len(v["gate_results"]) == 5
