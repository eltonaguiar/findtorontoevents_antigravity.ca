"""Tests for baby_strategies/daily_breakout_volume_confirm.py."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from baby_strategies.daily_breakout_volume_confirm import (
    DailyBreakoutVolumeConfirmStrategy,
    SUPPORTED_SYMBOLS,
)


def _quiet_tape(n=60, seed=0):
    """Range-bound daily tape with no breakout — close stays inside 20-day high."""
    rng = np.random.RandomState(seed)
    # Mean-revert around 100 inside a +/-2 band
    close = pd.Series(100 + np.sin(np.linspace(0, 6 * np.pi, n)) * 2 + rng.normal(0, 0.2, n))
    high = close + 0.3
    low = close - 0.3
    volume = pd.Series([1000.0] * n)
    return pd.DataFrame({"close": close, "high": high, "low": low,
                         "open": close - 0.05, "volume": volume})


def _breakout_tape(n=60, seed=1, with_volume_spike=True):
    """Range-bound for n-1 bars, then a clean upside breakout on the final bar
    with a volume spike."""
    rng = np.random.RandomState(seed)
    base = pd.Series(100 + rng.normal(0, 0.4, n - 1))
    base_high = base + 0.3
    base_low = base - 0.3

    # Last bar: close > max(base_high)
    breakout_close = float(base_high.max()) + 2.5
    close = pd.concat([base, pd.Series([breakout_close])], ignore_index=True)
    high = pd.concat([base_high, pd.Series([breakout_close + 0.5])], ignore_index=True)
    low = pd.concat([base_low, pd.Series([float(base.iloc[-1]) - 0.2])], ignore_index=True)

    base_vol = [1000.0] * (n - 1)
    final_vol = 3000.0 if with_volume_spike else 800.0  # 3x median vs 0.8x
    volume = pd.Series(base_vol + [final_vol])

    return pd.DataFrame({"close": close, "high": high, "low": low,
                         "open": close - 0.05, "volume": volume})


def _btc_d_falling(n=30):
    """BTC dominance falling steadily — alt-season tailwind."""
    return pd.Series(np.linspace(58.0, 52.0, n))


def _btc_d_rising(n=30):
    """BTC dominance rising — alt-season headwind."""
    return pd.Series(np.linspace(52.0, 58.0, n))


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_unsupported_symbol_rejected():
    strat = DailyBreakoutVolumeConfirmStrategy()
    assert strat.generate_signals(_breakout_tape(), "AAPL") == []
    assert strat.generate_signals(_breakout_tape(), "PEPEUSDT") == []


def test_insufficient_data_rejected():
    strat = DailyBreakoutVolumeConfirmStrategy()
    short = _breakout_tape(n=15)  # < donchian_len + 2
    assert strat.generate_signals(short, "BTCUSDT") == []


def test_no_signal_on_quiet_tape():
    """Range-bound tape with no breakout should produce no signals."""
    strat = DailyBreakoutVolumeConfirmStrategy()
    assert strat.generate_signals(_quiet_tape(), "BTCUSDT") == []


def test_signal_on_breakout_with_volume_spike():
    """Clean breakout + volume spike should fire a LONG signal."""
    strat = DailyBreakoutVolumeConfirmStrategy()
    sigs = strat.generate_signals(_breakout_tape(with_volume_spike=True), "BTCUSDT")
    assert len(sigs) == 1
    assert sigs[0].symbol == "BTCUSDT"
    assert sigs[0].direction == "LONG"


def test_breakout_without_volume_rejected():
    """Breakout without volume confirmation should NOT signal."""
    strat = DailyBreakoutVolumeConfirmStrategy()
    sigs = strat.generate_signals(_breakout_tape(with_volume_spike=False), "BTCUSDT")
    assert sigs == []


def test_long_tp_above_entry_above_sl():
    """LONG signal must have TP > entry > SL."""
    strat = DailyBreakoutVolumeConfirmStrategy()
    sigs = strat.generate_signals(_breakout_tape(), "BTCUSDT")
    assert len(sigs) == 1
    s = sigs[0]
    assert s.take_profit > s.entry_price > s.stop_loss


def test_btc_dominance_gate_blocks_alt_when_rising():
    """When BTC.D is rising, alt-coin breakout (e.g. ETHUSDT) should be blocked."""
    strat = DailyBreakoutVolumeConfirmStrategy()
    tape = _breakout_tape()

    # Alt with rising BTC.D — blocked
    sigs_blocked = strat.generate_signals(tape, "ETHUSDT",
                                           btc_dominance_series=_btc_d_rising())
    assert sigs_blocked == []

    # Alt with falling BTC.D — allowed
    sigs_allowed = strat.generate_signals(tape, "ETHUSDT",
                                           btc_dominance_series=_btc_d_falling())
    assert len(sigs_allowed) == 1
    assert sigs_allowed[0].symbol == "ETHUSDT"

    # BTC itself ignores the gate even when BTC.D is rising
    sigs_btc = strat.generate_signals(tape, "BTCUSDT",
                                       btc_dominance_series=_btc_d_rising())
    assert len(sigs_btc) == 1
    assert sigs_btc[0].symbol == "BTCUSDT"


def test_supported_symbols_match_leap_universe():
    expected = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"}
    assert set(SUPPORTED_SYMBOLS) == expected
