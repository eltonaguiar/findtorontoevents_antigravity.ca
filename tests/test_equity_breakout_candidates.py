import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.equity_breakout_candidates import daily_bars, donchian_signal, scan  # noqa: E402


def _day(i):
    return int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000) + i * 86_400_000


def test_daily_bars_aggregate_one_row_per_utc_day():
    rows = [{"timestamp": _day(0), "open": 10, "high": 12, "low": 9, "close": 11, "volume": 5},
            {"timestamp": _day(0) + 3_600_000, "open": 11, "high": 15, "low": 10,
             "close": 14, "volume": 7}]
    bars = daily_bars(rows)
    assert len(bars) == 1
    assert bars[0]["high"] == 15 and bars[0]["low"] == 9 and bars[0]["close"] == 14
    assert bars[0]["volume"] == 12


def _series(close_last, n=25, base=100.0):
    bars = []
    for i in range(n - 1):
        bars.append({"date": f"d{i}", "open": base, "high": base + 1, "low": base - 2,
                     "close": base, "volume": 1})
    bars.append({"date": "last", "open": base, "high": close_last, "low": base - 1,
                 "close": close_last, "volume": 1})
    return bars


def test_breakout_above_prior_high_emits_a_long_with_stop_below_entry():
    sig = donchian_signal(_series(110.0))
    assert sig is not None
    assert sig["entry"] == 110.0 and sig["stop"] < 110.0
    assert sig["target"] > sig["entry"]


def test_no_breakout_returns_none():
    assert donchian_signal(_series(100.5)) is None      # inside the 101 channel high


def test_too_few_bars_returns_none():
    assert donchian_signal(_series(110.0, n=10)) is None


def test_scan_assigns_etf_class_for_the_default_universe():
    rows = {s: [_day(0)] for s in ()}                    # unused
    picks = scan(["SPY"], {"SPY": []})
    assert picks == []                                   # no bars -> no candidate
