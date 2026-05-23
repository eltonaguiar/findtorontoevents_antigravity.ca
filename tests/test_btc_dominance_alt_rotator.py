"""Tests for baby_strategies/btc_dominance_alt_rotator.py."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from baby_strategies.btc_dominance_alt_rotator import (
    BtcDominanceAltRotatorStrategy,
    SUPPORTED_SYMBOLS,
)


# ----------------------------------------------------------------------
# Fixtures (plain helpers — no pytest decoration needed)
# ----------------------------------------------------------------------
def _alt_uptrend_tape(n=90, drift=0.5, vol=0.7, start=50.0, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(start + np.cumsum(rng.normal(drift, vol, n)))
    return pd.DataFrame({
        "close": close,
        "high": close + 0.5,
        "low": close - 0.5,
        "open": close - 0.1,
        "volume": [1000] * n,
    })


def _alt_flat_tape(n=90, start=50.0, seed=2):
    """Flat, slightly negative tape — fails momentum > 0 gate."""
    rng = np.random.RandomState(seed)
    close = pd.Series(start + np.cumsum(rng.normal(-0.05, 0.1, n)))
    return pd.DataFrame({
        "close": close,
        "high": close + 0.3,
        "low": close - 0.3,
        "open": close - 0.05,
        "volume": [1000] * n,
    })


def _btc_daily_uptrend(n=120, start=40000.0):
    close = pd.Series(start + np.arange(n) * 50.0)
    return pd.DataFrame({
        "close": close,
        "high": close + 100,
        "low": close - 100,
        "open": close,
        "volume": [10000] * n,
    })


def _btc_daily_downtrend(n=120, start=80000.0):
    close = pd.Series(start - np.arange(n) * 100.0)
    return pd.DataFrame({
        "close": close,
        "high": close + 100,
        "low": close - 100,
        "open": close,
        "volume": [10000] * n,
    })


def _btc_dom_falling(n=30, start=60.0, end=55.0):
    """BTC.D falling linearly from start to end over n days."""
    return pd.Series(np.linspace(start, end, n))


def _btc_dom_rising(n=30, start=52.0, end=58.0):
    """BTC.D rising linearly — kills alt-season trigger."""
    return pd.Series(np.linspace(start, end, n))


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_unsupported_symbol_rejected():
    """BTC and ETH excluded by design — only SOL/DOGE/XRP are supported."""
    strat = BtcDominanceAltRotatorStrategy()
    assert strat.generate_signals(
        _alt_uptrend_tape(),
        "BTCUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
    ) == []
    assert strat.generate_signals(
        _alt_uptrend_tape(),
        "AAPL",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
    ) == []


def test_insufficient_data_rejected():
    strat = BtcDominanceAltRotatorStrategy()
    short = _alt_uptrend_tape(n=5)
    assert strat.generate_signals(
        short,
        "SOLUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
    ) == []


def test_no_signal_when_btc_dominance_rising():
    """BTC.D rising = no alt-season; strategy must stay flat."""
    strat = BtcDominanceAltRotatorStrategy()
    sigs = strat.generate_signals(
        _alt_uptrend_tape(),
        "SOLUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_rising(),
    )
    assert sigs == []


def test_no_signal_when_btc_below_ema50():
    """Even with BTC.D falling, if BTC is in downtrend the trade is killed."""
    strat = BtcDominanceAltRotatorStrategy()
    sigs = strat.generate_signals(
        _alt_uptrend_tape(),
        "SOLUSDT",
        btc_daily=_btc_daily_downtrend(),
        btc_dominance_series=_btc_dom_falling(),
    )
    assert sigs == []


def test_signal_fires_on_falling_dom_plus_btc_uptrend_plus_alt_momentum():
    """All gates pass: BTC.D falling + BTC > EMA-50 + alt 7d momentum > 0."""
    strat = BtcDominanceAltRotatorStrategy()
    sigs = strat.generate_signals(
        _alt_uptrend_tape(),
        "SOLUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
    )
    assert len(sigs) == 1
    s = sigs[0]
    assert s.symbol == "SOLUSDT"
    assert s.direction == "LONG"
    assert s.momentum_7d > 0
    assert "btc-dominance alt-rotator" in s.reason.lower()


def test_long_signal_tp_above_entry_above_sl():
    """LONG geometry: TP > entry > SL with 3 ATR vs 2 ATR multipliers."""
    strat = BtcDominanceAltRotatorStrategy()
    sigs = strat.generate_signals(
        _alt_uptrend_tape(),
        "DOGEUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
    )
    assert len(sigs) == 1
    s = sigs[0]
    assert s.take_profit > s.entry_price > s.stop_loss
    # TP distance should be ~1.5x stop distance (3 ATR vs 2 ATR)
    up = s.take_profit - s.entry_price
    down = s.entry_price - s.stop_loss
    assert up > 0 and down > 0
    assert 1.4 < (up / down) < 1.6  # 3/2 = 1.5


def test_supported_symbols_sanity():
    """Universe is exactly the 3 Leap alts — BTC and ETH excluded by spec."""
    assert set(SUPPORTED_SYMBOLS) == {"SOLUSDT", "DOGEUSDT", "XRPUSDT"}
    assert "BTCUSDT" not in SUPPORTED_SYMBOLS
    assert "ETHUSDT" not in SUPPORTED_SYMBOLS


def test_peer_data_picks_top_momentum_alt():
    """When peer data is supplied, only the top-momentum alt emits a signal."""
    strat = BtcDominanceAltRotatorStrategy()
    # SOL has strongest drift, DOGE flat, XRP weak
    sol = _alt_uptrend_tape(drift=0.8, seed=1)
    doge = _alt_uptrend_tape(drift=0.1, seed=2)
    xrp = _alt_flat_tape(seed=3)

    # SOL should fire (top momentum)
    sigs_sol = strat.generate_signals(
        sol, "SOLUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
        peer_data_daily={"DOGEUSDT": doge, "XRPUSDT": xrp},
    )
    # DOGE should NOT fire (SOL has stronger momentum)
    sigs_doge = strat.generate_signals(
        doge, "DOGEUSDT",
        btc_daily=_btc_daily_uptrend(),
        btc_dominance_series=_btc_dom_falling(),
        peer_data_daily={"SOLUSDT": sol, "XRPUSDT": xrp},
    )
    assert len(sigs_sol) == 1
    assert sigs_sol[0].symbol == "SOLUSDT"
    assert sigs_doge == []


def test_should_rotate_threshold():
    """Rotation only triggers when peer beats current by > 5pp."""
    strat = BtcDominanceAltRotatorStrategy()
    # Current SOL at 10%, DOGE at 12% (only 2pp better) — no rotation
    assert strat.should_rotate(
        "SOLUSDT", 0.10, {"DOGEUSDT": 0.12, "XRPUSDT": 0.05}
    ) is None
    # DOGE at 17% (7pp better) — rotate to DOGE
    assert strat.should_rotate(
        "SOLUSDT", 0.10, {"DOGEUSDT": 0.17, "XRPUSDT": 0.05}
    ) == "DOGEUSDT"
