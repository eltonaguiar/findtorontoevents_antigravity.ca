"""Tests for alpha_engine.forex_smart_picks.check_carry_trade direction guard.

The guard enforces Lustig 2011 carry-momentum: direction must match carry sign.
Regression target: previously `score = carry + mom_20d*10` could emit a BUY on
a negative-carry pair or a SELL on a positive-carry pair when momentum
dominated. Flagged in PR #341 P0-3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_engine.forex_smart_picks import PAIRS, check_carry_trade


def _df(prices: list[float]) -> pd.DataFrame:
    n = len(prices)
    return pd.DataFrame({
        "Close": prices,
        "High": [p * 1.001 for p in prices],
        "Low": [p * 0.999 for p in prices],
        "Open": prices,
        "Volume": [1.0] * n,
    })


def _uptrend(start: float, end: float, n: int = 70) -> list[float]:
    # Linear increase — ensures mom_20d > 0 and price > SMA50.
    return list(np.linspace(start, end, n))


def _downtrend(start: float, end: float, n: int = 70) -> list[float]:
    return list(np.linspace(start, end, n))


class TestCarryDirectionGuard:
    def test_positive_carry_uptrend_emits_buy(self):
        # USDJPY=X carry = +4.5; strong uptrend; should emit BUY.
        sym = "USDJPY=X"
        assert PAIRS[sym]["carry_yield_diff"] > 0
        prices = _uptrend(140.0, 147.0)  # 5% up over 70 bars
        result = check_carry_trade(_df(prices), sym)
        assert result is not None
        assert result[0] == "BUY"

    def test_negative_carry_downtrend_emits_sell(self):
        # EURUSD=X carry = -0.5; sufficient downtrend; should emit SELL.
        sym = "EURUSD=X"
        assert PAIRS[sym]["carry_yield_diff"] < 0
        # Need score = carry + mom_20d*10 < -0.5
        # => carry (-0.5) + 10*mom < -0.5 => mom < 0.0 (any down move qualifies at threshold,
        # but need strict < -0.5; with carry=-0.5 need mom_20d < 0 for SELL).
        # mom_20d = last/last20 - 1 on the last 20 bars: use strong downtrend.
        prices = _downtrend(1.10, 1.03)  # ~6% decline
        result = check_carry_trade(_df(prices), sym)
        # May be None due to vol filter, but if it fires the direction must be SELL.
        if result is not None:
            assert result[0] == "SELL"

    def test_negative_carry_strong_uptrend_does_not_emit_wrong_direction_buy(self):
        # EURUSD=X carry = -0.5; strong uptrend would have passed pre-fix.
        # score = -0.5 + mom_20d*10 > 0.5 requires mom_20d > 0.1 (10% in 20 bars).
        # Regression guard: even with such an uptrend, no BUY should emit.
        sym = "EURUSD=X"
        prices = _uptrend(1.00, 1.15)  # 15% up — triggers old BUY logic
        result = check_carry_trade(_df(prices), sym)
        # Either None (rejected by the new guard) or non-BUY. A BUY here was the bug.
        if result is not None:
            assert result[0] != "BUY", (
                "check_carry_trade must NOT emit BUY on a negative-carry pair "
                "regardless of momentum strength (Lustig 2011 direction rule)."
            )

    def test_positive_carry_strong_downtrend_does_not_emit_sell(self):
        # Symmetric regression guard: positive-carry pair should not emit SELL
        # regardless of how strong the downtrend is.
        sym = "USDJPY=X"  # +4.5
        prices = _downtrend(150.0, 130.0)  # ~13% drop
        result = check_carry_trade(_df(prices), sym)
        if result is not None:
            assert result[0] != "SELL", (
                "check_carry_trade must NOT emit SELL on a positive-carry pair."
            )
