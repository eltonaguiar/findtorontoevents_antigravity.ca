"""Deterministic tests for tools/exit_ab_paper.py — synthetic bars, no database."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.exit_ab_paper import (  # noqa: E402
    DEFAULT_COST_PCT, _close_before, _ms, ab_report, time_exit_pnl,
)

H = 86400_000
T0 = 1_700_000_000_000  # fixed epoch, no wall-clock dependence


def _bars(series, klass="CRYPTO", symbol="SOLUSDT"):
    return {f"{klass}:{symbol}": series}


def _row(pnl, entry=T0, closed=T0 + 2 * H, klass="CRYPTO", symbol="SOLUSDT",
         direction="LONG"):
    return {"class": klass, "symbol": symbol, "dir": direction, "pnl": pnl,
            "entry_time": _iso(entry), "closed_at": _iso(closed)}


def _iso(ms):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def test_close_before_never_uses_a_future_bar():
    series = [(T0, 100.0), (T0 + H, 101.0), (T0 + 2 * H, 102.0)]
    assert _close_before(series, T0 + H) == 101.0        # exactly on the bar
    assert _close_before(series, T0 + H + 3600_000) == 101.0  # between bars


def test_close_before_returns_none_before_the_first_bar():
    series = [(T0, 100.0), (T0 + H, 101.0)]
    assert _close_before(series, T0 - 1) is None


def test_time_exit_beats_a_tp_capped_long():
    # Actual exits at +2%, but holding 3 days would have made +10% gross.
    series = [(T0, 100.0), (T0 + H, 100.0), (T0 + 2 * H, 102.0),
              (T0 + 3 * H, 110.0), (T0 + 4 * H, 111.0)]
    alt = time_exit_pnl(series, T0, 3.0, dir_sign=1, cost=DEFAULT_COST_PCT,
                        tol_ms=3 * 3600_000)
    assert alt == pytest.approx(10.0 - DEFAULT_COST_PCT)
    res = ab_report([_row(pnl=2.0)], _bars(series), horizons=(3.0,))
    o = res["horizons"][0]["overall"]
    assert o["n"] == 1
    assert o["mean_delta_pct"] == pytest.approx(10.0 - DEFAULT_COST_PCT - 2.0)
    assert o["mean_actual_pct"] == pytest.approx(2.0)


def test_short_direction_is_signed_and_paid_once_for_cost():
    # Price falls 10%: a SHORT's time exit gains, a LONG's loses the same 10.
    series = [(T0, 100.0), (T0 + H, 90.0)]
    short_alt = time_exit_pnl(series, T0, 1.0, dir_sign=-1)
    long_alt = time_exit_pnl(series, T0, 1.0, dir_sign=1)
    assert short_alt == pytest.approx(10.0 - DEFAULT_COST_PCT)
    assert long_alt == pytest.approx(-10.0 - DEFAULT_COST_PCT)
    assert short_alt - long_alt == pytest.approx(20.0)  # cost cancels: paid once each


def test_degenerate_zero_hold_row_is_skipped_not_dropped():
    series = [(T0, 100.0), (T0 + H, 101.0), (T0 + 2 * H, 102.0)]
    res = ab_report([_row(pnl=-1.65, entry=T0, closed=T0)], _bars(series), horizons=(1.0,))
    assert res["horizons"][0]["overall"]["n"] == 0
    assert res["skipped"]["degenerate_zero_hold"] == 1
    # accounting closes: with one horizon every input row is paired or skipped
    paired = sum(h["overall"]["n"] for h in res["horizons"])
    assert paired + sum(res["skipped"].values()) == res["rows_in"]


def test_missing_series_and_entry_bar_are_counted():
    series = [(T0 + 5 * H, 100.0)]  # first bar is after the entry signal
    res = ab_report([_row(pnl=1.0), {**_row(pnl=1.0), "symbol": "NOPE"}],
                    _bars(series), horizons=(1.0,))
    assert res["horizons"][0]["overall"]["n"] == 0
    assert res["skipped"]["no_price_series"] == 1
    assert res["skipped"]["no_entry_bar"] == 1


def test_report_is_paired_over_the_same_picks():
    # Two picks, same horizon: the report's n must equal the paired picks, not rows.
    rising = [(T0, 100.0), (T0 + H, 105.0)]
    falling = [(T0, 100.0), (T0 + H, 95.0)]
    bars = {"CRYPTO:SOLUSDT": rising, "CRYPTO:BTCUSDT": falling}
    rows = [_row(pnl=1.0, symbol="SOLUSDT"),
            _row(pnl=-1.0, symbol="BTCUSDT", direction="SHORT")]
    res = ab_report(rows, bars, horizons=(1.0,))
    o = res["horizons"][0]["overall"]
    assert o["n"] == 2
    # long made 5 gross, short made 5 gross: both beat their actual legs
    assert o["mean_alt_pct"] == pytest.approx(2 * (5.0 - DEFAULT_COST_PCT) / 2, abs=1e-6)
    assert o["better_share"] == 1.0


def test_cli_fails_closed_without_rows(tmp_path):
    # An empty rows file must exit 2, not print an empty "no edge" report.
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "exit_ab_paper.py"),
                           "--rows", str(empty)], capture_output=True, text=True)
    assert proc.returncode == 2, proc.stderr


def test_schema_and_cost_are_reported(tmp_path):
    series = [(T0, 100.0), (T0 + H, 110.0)]
    res = ab_report([_row(pnl=1.0)], _bars(series), horizons=(1.0,), cost=0.25)
    assert res["schema"] == "audit3.exit_ab_paper.v1"
    assert res["mode"] == "paper"
    assert res["cost_pct"] == 0.25
    assert res["horizons"][0]["overall"]["mean_alt_pct"] == pytest.approx(10.0 - 0.25)
