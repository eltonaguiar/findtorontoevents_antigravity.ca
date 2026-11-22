"""Minimal contract tests for tools/crypto_meanrev_intraday.py.

Two invariants that, if broken, would invalidate every number the backtest reports:

  1. ONE-BAR LAG: a signal observed at bar t's close must enter at bar t+1's OPEN -
     never at bar t's close (look-ahead).
  2. STOP FIRST: on a bar that hits the intrabar stop AND would also satisfy the
     reversion exit at its close, the STOP must win.

Both use synthetic series crafted so the wrong convention gives a different, detectable
answer.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.crypto_meanrev_intraday import (  # noqa: E402
    Z_LOOKBACK, generate_trades, walk_position)


def test_stop_checked_before_reversion_on_same_bar():
    """Bar 0 hits the stop intrabar AND closes in reversion territory (z >= 0 for a long).

    STOP-FIRST -> exit on bar 0 at the stop price.
    EXIT-FIRST (the bug) -> exit at bar 1's open via the reversion branch.
    """
    z = np.array([0.5, 0.2, 0.1])          # bar 0 close is already z>=0 -> reversion-true
    o = np.array([100.0, 120.0, 121.0])    # bar 1 open is far from the stop: distinguishable
    h = np.array([101.0, 122.0, 123.0])
    l = np.array([94.0, 118.0, 119.0])     # bar 0 low pierces the 95 stop
    c = np.array([100.0, 121.0, 122.0])
    res = walk_position(direction=1, entry_price=100.0, stop_price=95.0, start_bar=0,
                        z=z, open_=o, high=h, low=l, close=c, signal_bar=-1)
    assert res["reason"] == "stop", res
    assert res["exit_bar"] == 0, res
    assert res["exit_price"] == 95.0, res   # NOT 120.0 (bar 1 open) which exit-first would give


def test_gap_through_stop_fills_at_open_not_stop():
    """If the bar opens already beyond the stop, the fill is the open (worse), not the stop."""
    z = np.array([0.5, 0.2])
    o = np.array([90.0, 91.0])              # opens below the 95 stop -> gap
    h = np.array([92.0, 93.0])
    l = np.array([88.0, 89.0])
    c = np.array([91.0, 92.0])
    res = walk_position(direction=1, entry_price=100.0, stop_price=95.0, start_bar=0,
                        z=z, open_=o, high=h, low=l, close=c, signal_bar=-1)
    assert res["reason"] == "stop_gap", res
    assert res["exit_price"] == 90.0, res   # the open, not 95.0


def _synthetic_signal_series():
    """60 bars: flat ~100, then a sharp drop at bar 50 so z <= -2 with std > 0.

    open[51] is deliberately set far from close[50] so the fill price reveals which bar
    and which price the entry used.
    """
    rng = np.random.default_rng(7)
    close = 100.0 + rng.normal(0, 0.05, 60)
    close[50] = 90.0                        # sharp drop -> very negative z
    close[51:] = 91.0
    op = close.copy()
    op[1:] = close[:-1]                    # open = previous close, by default
    op[51] = 77.0                          # <-- distinctive next-open after the signal
    hi = np.maximum(op, close) + 0.1
    lo = np.minimum(op, close) - 0.1
    open_time = np.arange(60) * 4 * 3600 * 1000
    df = pd.DataFrame({"open_time": open_time,
                       "open": op, "high": hi, "low": lo, "close": close,
                       "volume": 1.0})
    df["dt"] = pd.to_datetime(open_time, unit="ms", utc=True)
    return df


def test_entry_is_next_bar_open_not_signal_close():
    df = _synthetic_signal_series()
    trades = generate_trades(df, "SYN")
    assert trades, "expected at least one trade from the synthetic drop"
    for tr in trades:
        # invariant: enter one bar AFTER the signal bar (never on it)
        assert tr["entry_bar"] == tr["signal_bar"] + 1, tr
        # invariant: the fill price is that bar's OPEN ...
        assert tr["entry_price"] == df["open"].iloc[tr["entry_bar"]], tr
    # ... and on the bar where open and close were made to differ, the fill is provably
    # the NEXT open (77.0), not the signal bar's close (90.0). Elsewhere open[t+1] equals
    # close[t] by construction, so only this bar can discriminate the two conventions.
    first = trades[0]
    assert first["signal_bar"] >= Z_LOOKBACK
    assert first["entry_bar"] == 51, first
    assert first["entry_price"] == 77.0, first                 # the crafted next open
    assert df["close"].iloc[first["signal_bar"]] == 90.0       # signal close, a different price
