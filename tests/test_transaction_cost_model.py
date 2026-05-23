"""Unit tests for audit_trail.transaction_cost_model.

Per the hedge-fund-uplift roadmap (reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md),
this module is the highest-leverage starting point: 4-reviewer consensus +
real-backtest empirical finding that transaction-cost overlay flips every class
except CRYPTO from gross-positive to net-negative at literature-prior slippage.

Module extracted from PR #621 (`audit_trail/transaction_cost_model.py`); the
algorithm code passes 4-reviewer praise but PR #621 shipped it as an orphan
with 0 tests. This PR fixes both gaps: tests + dashboard_generator wire-in.
"""
from __future__ import annotations

import pytest

from audit_trail.transaction_cost_model import (
    CostAssumption,
    COST_ASSUMPTIONS,
    _classify_cost_bucket,
    apply_costs_to_pick,
    compute_net_pnl,
    get_cost_assumption,
)


# ─────────────────────────────────────────────────────────────────
# Bucket classification — covers the symbol/asset_class routing
# ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ac, sym, expected_bucket", [
    # Crypto majors / spot
    ("CRYPTO", "BTCUSDT", "CRYPTO_PERP"),  # USDT suffix → perp per current logic
    ("CRYPTO", "BTC-USD", "CRYPTO_SPOT"),
    ("CRYPTO", "ETHUSD", "CRYPTO_SPOT"),
    # Crypto memes
    ("CRYPTO", "DOGEUSDT", "CRYPTO_MEME"),
    ("CRYPTO", "SHIBUSDT", "CRYPTO_MEME"),
    ("CRYPTO", "PEPEUSDT", "CRYPTO_MEME"),
    ("MEMECOIN", "RANDOMTOKEN", "CRYPTO_MEME"),
    # Forex majors vs crosses
    ("FOREX", "EURUSD=X", "FOREX_MAJOR"),
    ("FOREX", "GBPUSD=X", "FOREX_MAJOR"),
    ("FOREX", "USDJPY=X", "FOREX_MAJOR"),
    ("FOREX", "EURGBP=X", "FOREX_CROSS"),
    ("FOREX", "AUDJPY=X", "FOREX_CROSS"),
    # Equity / bond / etf / commodity / futures
    ("EQUITY", "AAPL", "EQUITY"),
    ("STOCK", "MSFT", "EQUITY"),
    ("BOND", "TLT", "BOND_ETF"),
    ("ETF", "SPY", "ETF"),
    ("COMMODITY", "GC=F", "COMMODITY"),
    ("FUTURES", "ES=F", "FUTURES"),
    ("PENNY", "RANDOMPENNY", "PENNY"),
    # Default fallback for unknown asset class
    ("UNKNOWN_CLASS", "FOO", "EQUITY"),
])
def test_classify_cost_bucket(ac, sym, expected_bucket):
    assert _classify_cost_bucket(ac, sym) == expected_bucket


# ─────────────────────────────────────────────────────────────────
# Cost assumption sanity checks — every bucket must have non-negative costs
# ─────────────────────────────────────────────────────────────────

def test_all_cost_assumptions_have_non_negative_components():
    for bucket, c in COST_ASSUMPTIONS.items():
        assert c.fee_pct >= 0, f"{bucket}: fee_pct must be >= 0"
        assert c.slippage_pct >= 0, f"{bucket}: slippage_pct must be >= 0"
        assert c.spread_pct >= 0, f"{bucket}: spread_pct must be >= 0"
        assert c.total_cost_pct > 0, f"{bucket}: total round-trip cost must be > 0"
        assert c.label, f"{bucket}: label must be non-empty"


def test_meme_cost_higher_than_spot():
    """Meme/micro-cap costs must exceed spot crypto — wide spread + slippage."""
    spot = COST_ASSUMPTIONS["CRYPTO_SPOT"].total_cost_pct
    meme = COST_ASSUMPTIONS["CRYPTO_MEME"].total_cost_pct
    assert meme > spot, f"Meme {meme}bp must exceed spot {spot}bp"


def test_penny_cost_highest_for_equities():
    """Penny stocks are the most expensive equity-like bucket."""
    eq = COST_ASSUMPTIONS["EQUITY"].total_cost_pct
    etf = COST_ASSUMPTIONS["ETF"].total_cost_pct
    penny = COST_ASSUMPTIONS["PENNY"].total_cost_pct
    assert penny > eq > etf or penny > eq, f"PENNY must be costliest equity-like"
    assert penny > etf


# ─────────────────────────────────────────────────────────────────
# compute_net_pnl — gross → net subtraction
# ─────────────────────────────────────────────────────────────────

def test_compute_net_pnl_subtracts_total_cost_for_taker():
    # CRYPTO_SPOT: fee 0.20 + slip 0.10 + spread 0.06 = 0.36% RT
    gross = 1.50
    net = compute_net_pnl(gross, "CRYPTO", "BTC-USD", is_maker=False)
    assert abs(net - (gross - 0.36)) < 1e-9


def test_compute_net_pnl_maker_halves_fee():
    """is_maker=True applies 50% fee (rebate-equivalent)."""
    # CRYPTO_SPOT: fee 0.20 → maker 0.10; total cost = 0.10 + 0.10 + 0.06 = 0.26
    gross = 1.50
    net = compute_net_pnl(gross, "CRYPTO", "BTC-USD", is_maker=True)
    assert abs(net - (gross - 0.26)) < 1e-9


def test_compute_net_pnl_negative_pick_more_negative_after_costs():
    """A losing pick gets MORE negative after costs (we pay both ways)."""
    gross = -0.50
    net = compute_net_pnl(gross, "CRYPTO", "BTC-USD", is_maker=False)
    assert net < gross
    assert abs(net - (-0.50 - 0.36)) < 1e-9


def test_compute_net_pnl_thin_alpha_can_flip_to_negative():
    """The empirical finding: thin alpha can flip from gross-positive to net-negative."""
    # CRYPTO_MEME total cost = 0.20 + 0.30 + 0.20 = 0.70%
    gross = 0.50  # thin positive
    net = compute_net_pnl(gross, "CRYPTO", "DOGEUSDT", is_maker=False)
    assert net < 0, f"Thin meme alpha {gross}% should flip to negative net; got {net}"


# ─────────────────────────────────────────────────────────────────
# apply_costs_to_pick — dict enrichment
# ─────────────────────────────────────────────────────────────────

def test_apply_costs_to_pick_adds_required_fields():
    pick = {"symbol": "BTC-USD", "asset_class": "CRYPTO", "pnl_pct": 1.5}
    out = apply_costs_to_pick(pick)
    assert "_cost_assumption" in out or "_total_cost_pct" in out or "net_of_cost_pnl_pct" in out
    # At minimum the net-of-cost field should exist for a pick with pnl_pct
    assert "net_of_cost_pnl_pct" in out, \
        "apply_costs_to_pick must add net_of_cost_pnl_pct"


def test_apply_costs_to_pick_does_not_mutate_input():
    """Function returns a new dict; original is unchanged."""
    pick = {"symbol": "BTC-USD", "asset_class": "CRYPTO", "pnl_pct": 1.5}
    original_keys = set(pick.keys())
    apply_costs_to_pick(pick)
    assert set(pick.keys()) == original_keys, "Input dict must not be mutated"


def test_apply_costs_to_pick_handles_non_dict():
    """Non-dict input passes through unchanged."""
    assert apply_costs_to_pick(None) is None
    assert apply_costs_to_pick("notdict") == "notdict"
    assert apply_costs_to_pick(42) == 42


def test_apply_costs_to_pick_meme_flips_thin_alpha():
    """Empirical finding: thin meme alpha flips net-negative."""
    pick = {"symbol": "DOGEUSDT", "asset_class": "CRYPTO", "pnl_pct": 0.40}
    out = apply_costs_to_pick(pick)
    assert out.get("net_of_cost_pnl_pct", 0) < 0, \
        f"Thin meme alpha should flip negative; got {out.get('net_of_cost_pnl_pct')}"


# ─────────────────────────────────────────────────────────────────
# get_cost_assumption — public API contract
# ─────────────────────────────────────────────────────────────────

def test_get_cost_assumption_returns_cost_assumption():
    c = get_cost_assumption("CRYPTO", "BTC-USD")
    assert isinstance(c, CostAssumption)
    assert c.total_cost_pct > 0


def test_get_cost_assumption_unknown_falls_back_to_equity():
    c = get_cost_assumption("MARTIAN_DERIVATIVES", "FOOBAR")
    assert c == COST_ASSUMPTIONS["EQUITY"]
