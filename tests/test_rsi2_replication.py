"""Deterministic tests for tools/rsi2_replication.py (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.rsi2_replication import (  # noqa: E402
    MAX_HOLD,
    simulate,
    sma,
    summarize,
    wilder_rsi,
)


def _bars(closes, opens=None, start="2020-01-01"):
    from datetime import date, timedelta

    d0 = date.fromisoformat(start)
    opens = opens or closes
    return [
        {"date": str(d0 + timedelta(days=i)), "open": o, "close": c}
        for i, (o, c) in enumerate(zip(opens, closes))
    ]


def test_rsi_all_up_is_100_and_all_down_is_0():
    up = wilder_rsi([1, 2, 3, 4, 5, 6])
    down = wilder_rsi([6, 5, 4, 3, 2, 1])
    # Zero average loss is 100 by definition; zero average gain is 0.
    assert up[-1] == 100.0
    assert down[-1] == 0.0


def test_rsi_is_none_until_enough_history():
    # The seed consumes `period` deltas, so the first defined value is at index
    # `period` — one fewer price than a naive reading would suggest.
    r = wilder_rsi([1, 2, 3, 4])
    assert r[0] is None and r[1] is None
    assert r[2] is not None


def test_rsi_stays_in_range_on_noise():
    import random

    rng = random.Random(3)
    px = [100.0]
    for _ in range(200):
        px.append(max(1.0, px[-1] * (1 + rng.uniform(-0.03, 0.03))))
    vals = [v for v in wilder_rsi(px) if v is not None]
    assert vals and all(0.0 <= v <= 100.0 for v in vals)


def test_sma_window_and_padding():
    m = sma([1, 2, 3, 4, 5], 3)
    assert m[0] is None and m[1] is None
    assert m[2] == 2.0
    assert m[4] == 4.0


def test_no_entry_when_rsi_never_drops_below_threshold():
    bars = _bars([100 + i for i in range(30)])  # monotone up: RSI stays high
    assert simulate(bars, "SPY", "ETF") == []


def test_entry_is_next_open_not_signal_close():
    # Invariant rather than a guessed index: entry must be some bar's OPEN, and
    # never the close of the bar that triggered the signal.
    closes = [100, 99, 98, 97, 96, 95, 92, 105, 106, 107, 108, 110]
    opens = [100, 99, 98, 97, 96, 95, 50.0, 105, 106, 107, 108, 110]
    rows = simulate(_bars(closes, opens), "SPY", "ETF")
    assert rows, "expected at least one trade"
    assert rows[0]["entry_price"] in opens
    assert rows[0]["entry_price"] != closes[6]


def test_hold_is_capped_at_max_hold():
    closes = [100] * 3 + [50] + [50] * 40  # deep drop, then flat forever
    rows = simulate(_bars(closes), "SPY", "ETF")
    assert rows
    assert rows[0]["hold_days"] <= MAX_HOLD


def test_selection_alpha_subtracts_buy_and_hold():
    # A trade that rises but less than the index is negative alpha.
    closes = [100, 99, 98, 97, 96, 95, 96, 97, 98, 99, 100, 101, 102]
    rows = simulate(_bars(closes), "SPY", "ETF")
    for r in rows:
        assert abs(r["selection_alpha_pct"] - (r["pnl_pct"] - r["buy_hold_pct"])) < 1e-9


def test_summarize_empty_is_inconclusive_not_zero():
    s = summarize([])
    assert s["n"] == 0
    assert "INCONCLUSIVE" in s["verdict"]


def test_summarize_counts_wins_on_net():
    rows = [
        {"pnl_pct": 1.0, "selection_alpha_pct": 0.5, "hold_days": 2, "buy_hold_pct": 0.5},
        {"pnl_pct": -1.0, "selection_alpha_pct": -0.5, "hold_days": 4, "buy_hold_pct": -0.5},
    ]
    s = summarize(rows)
    assert s["n"] == 2
    assert s["win_rate"] == 0.5
    assert s["mean_net_pct"] == 0.0
    assert s["mean_hold_days"] == 3.0
