#!/usr/bin/env python3
"""Tests for the Questrade cost model in alpha_engine/backtest/costs.py.

Context: the model charged forex_fee_pct (1.75%) on EVERY trade, and because
compute_exit_cost() reused compute_entry_cost(), a round trip paid it twice -
350 bp of FX against a measured round-trip spread of ~5 bp. It also charged
$0.0035/share ECN on every trade and omitted the SEC fee entirely.

These tests pin BOTH directions:
  * the Questrade path now matches the verified tariff and the measurement
  * the Interactive Brokers path is byte-identical to before (it must not move)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.backtest.costs import CostModel  # noqa: E402

PRICE = 100.0
SHARES = 200            # $20,000 notional
NOTIONAL = PRICE * SHARES


# --------------------------------------------------------------- IB parity
def test_ib_entry_cost_matches_original_formula():
    """IB entry = max(sh*0.005,1) + slip5 + spread3 + sh*0.003. Must not move."""
    m = CostModel.interactive_brokers()
    expected = 1.00 + NOTIONAL * 5 / 10_000 + NOTIONAL * 3 / 10_000 + SHARES * 0.003
    assert m.compute_entry_cost(PRICE, SHARES) == pytest.approx(expected)


def test_ib_exit_cost_matches_original_formula():
    """IB exit = same legs, no SEC fee, plus borrow only when short."""
    m = CostModel.interactive_brokers()
    expected = 1.00 + NOTIONAL * 5 / 10_000 + NOTIONAL * 3 / 10_000 + SHARES * 0.003
    assert m.compute_exit_cost(PRICE, SHARES) == pytest.approx(expected)


def test_ib_round_trip_unchanged():
    m = CostModel.interactive_brokers()
    per_side = 1.00 + NOTIONAL * 5 / 10_000 + NOTIONAL * 3 / 10_000 + SHARES * 0.003
    assert m.compute_round_trip_cost(PRICE, PRICE, SHARES) == pytest.approx(per_side * 2)


# --------------------------------------------------------- Questrade tariff
def test_questrade_charges_no_commission():
    m = CostModel.questrade_canada()
    assert m.commission_per_share == 0.0
    # with zero spread and slippage, a buy must cost nothing at all
    m_flat = CostModel.questrade_canada()
    m_flat.spread_bps = 0.0
    m_flat.slippage_bps = 0.0
    assert m_flat.compute_entry_cost(PRICE, SHARES) == 0.0


def test_questrade_charges_no_ecn():
    m = CostModel.questrade_canada()
    assert m.ecn_fee == 0.0


def test_questrade_does_not_charge_fx_per_trade():
    """The old model put 175 bp on entry AND exit. FX is a conversion event."""
    m = CostModel.questrade_canada()
    assert m.forex_fee_pct == 0.0
    # with spread/slippage zeroed, neither side may carry any FX
    m.spread_bps = 0.0
    m.slippage_bps = 0.0
    rt = m.compute_round_trip_cost(PRICE, PRICE, SHARES)
    assert rt == pytest.approx(NOTIONAL * 0.0000206)   # SEC fee only


def test_old_fx_bug_would_have_been_350bp():
    """Pin the removed behaviour so it cannot silently return."""
    old_round_trip_bp = 2 * 0.0175 * 10_000          # entry + exit
    assert old_round_trip_bp == pytest.approx(350.0)
    new_bp = CostModel.questrade_canada().compute_round_trip_cost(
        PRICE, PRICE, SHARES) / NOTIONAL * 10_000
    assert new_bp < 10.0, "Questrade round trip must be single-digit bp"


def test_questrade_sec_fee_on_sale_only_long():
    """A long SELLS on exit -> SEC fee lands on the exit leg."""
    m = CostModel.questrade_canada()
    m.spread_bps = 0.0
    m.slippage_bps = 0.0
    assert m.compute_entry_cost(PRICE, SHARES, is_short=False) == 0.0
    assert m.compute_exit_cost(PRICE, SHARES, is_short=False) == pytest.approx(
        NOTIONAL * 0.0000206)


def test_questrade_sec_fee_on_sale_only_short():
    """A short SELLS on entry -> SEC fee lands on the entry leg."""
    m = CostModel.questrade_canada()
    m.spread_bps = 0.0
    m.slippage_bps = 0.0
    m.borrow_cost_annual_bps = 0.0
    assert m.compute_entry_cost(PRICE, SHARES, is_short=True) == pytest.approx(
        NOTIONAL * 0.0000206)
    assert m.compute_exit_cost(PRICE, SHARES, is_short=True, holding_days=0) == 0.0


def test_questrade_round_trip_matches_measurement():
    """Must land on the measured ~4.98 bp, not the old 350 bp."""
    m = CostModel.questrade_canada()
    bp = m.compute_round_trip_cost(PRICE, PRICE, SHARES) / NOTIONAL * 10_000
    assert bp == pytest.approx(4.976, abs=0.01)


def test_currency_conversion_is_one_off_and_separate():
    m = CostModel.questrade_canada()
    m.forex_fee_pct = 0.015
    assert m.currency_conversion_cost(NOTIONAL) == pytest.approx(NOTIONAL * 0.015)
    # and it must NOT leak into the trade costs
    m.spread_bps = 0.0
    m.slippage_bps = 0.0
    assert m.compute_entry_cost(PRICE, SHARES) == 0.0


def test_max_commission_cap_applies():
    m = CostModel.interactive_brokers()
    m.commission_per_share = 1.0
    m.max_commission = 9.95
    # 200 shares * $1 = $200, capped at $9.95
    m.slippage_bps = 0.0
    m.spread_bps = 0.0
    m.exchange_fee_per_share = 0.0
    assert m.compute_entry_cost(PRICE, SHARES) == pytest.approx(9.95)


def test_zero_cost_model_is_still_all_zero():
    m = CostModel.zero_cost()
    assert m.compute_round_trip_cost(PRICE, PRICE, SHARES) == 0.0
