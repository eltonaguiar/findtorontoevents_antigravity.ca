#!/usr/bin/env python3
"""Network-free unit tests for tools/h008_bond_research.py.

Covers the pure signal math (slope, momentum, rolling-z no-look-ahead) and the
continuous-position backtest + harness wiring on a synthetic deterministic
fixture. No HTTP, no FRED, no yfinance.

    python tools/test_h008_bond_research.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h008_bond_research as h  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
# compute_slope
# ---------------------------------------------------------------------------
def test_compute_slope():
    dgs2 = {"2020-01-01": 1.5, "2020-01-02": 1.6, "2020-01-03": 1.4}
    dgs10 = {"2020-01-01": 2.0, "2020-01-02": 2.1, "2020-01-03": 1.9}
    dates, slope = h.compute_slope(dgs2, dgs10)
    check("compute_slope dates sorted",
          dates == ["2020-01-01", "2020-01-02", "2020-01-03"], str(dates))
    check("compute_slope = DGS10 - DGS2",
          slope == [0.5, 0.5, 0.5], str(slope))
    # only common dates retained
    dgs10b = dict(dgs10); dgs10b["2020-01-09"] = 2.2
    d2, _ = h.compute_slope(dgs2, dgs10b)
    check("compute_slope intersects dates", "2020-01-09" not in d2, str(d2))


# ---------------------------------------------------------------------------
# slope_momentum
# ---------------------------------------------------------------------------
def test_slope_momentum():
    slope = [1.0, 1.1, 1.2, 1.5, 1.4]
    mom = h.slope_momentum(slope, lookback=2)
    # i<2 -> 0.0 ; i=2 -> 1.2-1.0=0.2 ; i=3 -> 1.5-1.1=0.4 ; i=4 -> 1.4-1.2=0.2
    check("slope_momentum pre-lookback zeros", mom[0] == 0.0 and mom[1] == 0.0,
          str(mom))
    check("slope_momentum i=2", abs(mom[2] - 0.2) < 1e-9, str(mom[2]))
    check("slope_momentum i=3", abs(mom[3] - 0.4) < 1e-9, str(mom[3]))
    check("slope_momentum length preserved", len(mom) == len(slope))


# ---------------------------------------------------------------------------
# rolling_z — the no-look-ahead guarantee
# ---------------------------------------------------------------------------
def test_rolling_z():
    series = [0.0] * 5 + [10.0]   # constant past, spike at idx 5
    z = h.rolling_z(series, idx=5, roll=5)
    # past window [0:5] all zero -> sd 0 -> None
    check("rolling_z zero-dispersion -> None", z is None, str(z))
    series2 = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]
    z2 = h.rolling_z(series2, idx=5, roll=5)
    check("rolling_z big positive spike -> large +z", z2 is not None and z2 > 3,
          str(z2))
    # idx < roll -> None
    check("rolling_z insufficient history -> None",
          h.rolling_z(series2, idx=2, roll=5) is None)
    # NO LOOK-AHEAD: appending a future value must not change z at idx 5
    z_before = h.rolling_z(series2, idx=5, roll=5)
    series3 = series2 + [999.0, -999.0]
    z_after = h.rolling_z(series3, idx=5, roll=5)
    check("rolling_z is look-ahead free", z_before == z_after,
          f"{z_before} vs {z_after}")


# ---------------------------------------------------------------------------
# build_signal_z_by_date + latest_signal_on_or_before
# ---------------------------------------------------------------------------
def test_signal_by_date_and_lookup():
    # 200 trading-ish days of a slowly drifting curve
    dates = [f"2020-{(m%12)+1:02d}-{(d%28)+1:02d}-{i}" for i, (m, d)
             in enumerate([(i // 28, i) for i in range(200)])]
    # use simple incrementing ISO dates to keep sort order trivial
    iso = [f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(200)]
    dgs2 = {iso[i]: 1.0 for i in range(200)}
    dgs10 = {iso[i]: 2.0 + 0.01 * i for i in range(200)}   # steadily steepening
    z_by_date = h.build_signal_z_by_date(dgs2, dgs10)
    check("build_signal_z_by_date returns dict", isinstance(z_by_date, dict))
    check("build_signal_z_by_date skips early dates (insufficient history)",
          len(z_by_date) < 200 and len(z_by_date) > 0, str(len(z_by_date)))

    sorted_z = sorted(z_by_date)
    # lookup must be STRICTLY before the position date
    pos = sorted_z[len(sorted_z) // 2]
    sig = h.latest_signal_on_or_before(z_by_date, sorted_z, pos)
    check("latest_signal returns a value mid-series", sig is not None)
    # position date == first signal date -> nothing strictly before -> None
    first = sorted_z[0]
    check("latest_signal strictly-before (no same-day leak)",
          h.latest_signal_on_or_before(z_by_date, sorted_z, first) is None,
          "same-day signal leaked")
    # a position date before all signal dates -> None
    check("latest_signal before all data -> None",
          h.latest_signal_on_or_before(z_by_date, sorted_z, "1999-01-01") is None)


# ---------------------------------------------------------------------------
# backtest_continuous — record shape + density
# ---------------------------------------------------------------------------
def _synthetic_inputs(n_days: int = 400, n_inst: int = 6):
    iso = [f"20{20 + i // 250:02d}-{1 + (i // 21) % 12:02d}-{1 + i % 21:02d}"
           for i in range(n_days)]
    iso = sorted(set(iso))
    dgs2 = {d: 1.5 for d in iso}
    # an oscillating 10y so the slope-momentum z swings sign repeatedly
    import math
    dgs10 = {d: 2.5 + 0.4 * math.sin(i / 12.0) for i, d in enumerate(iso)}
    price_by_inst = {}
    for k in range(n_inst):
        prices = {}
        for i, d in enumerate(iso):
            prices[d] = 100.0 + 5.0 * math.sin((i + k * 7) / 9.0)
        price_by_inst[f"INST{k}"] = prices
    return dgs2, dgs10, price_by_inst


def test_backtest_continuous():
    dgs2, dgs10, price_by_inst = _synthetic_inputs()
    bt = h.backtest_continuous(dgs2, dgs10, price_by_inst)
    recs = bt["records"]
    check("backtest produces records", len(recs) > 0, str(len(recs)))
    # density: with 6 instruments x ~400 days, far past the harness floor
    check("backtest record density >> harness floor",
          len(recs) >= 80, str(len(recs)))
    sample = recs[0]
    for fld in ("status", "resolved_at", "entry_date", h.HARNESS_FIELD,
                "signed_ret", "direction", "instrument"):
        check(f"record carries '{fld}'", fld in sample, str(sample.keys()))
    check("record status in {WON,LOST}",
          all(r["status"] in ("WON", "LOST") for r in recs))
    check("signal_z is non-negative magnitude",
          all(r[h.HARNESS_FIELD] >= 0 for r in recs))
    # status must agree with sign of signed_ret
    check("status matches signed_ret sign",
          all((r["status"] == "WON") == (r["signed_ret"] > 0) for r in recs))
    # resolved_at strictly after entry_date (no zero-hold)
    check("resolved_at after entry_date",
          all(r["resolved_at"] > r["entry_date"] for r in recs))


# ---------------------------------------------------------------------------
# harness wiring — runs and restores the loader
# ---------------------------------------------------------------------------
def test_harness_wiring():
    import edge_stability_harness as harness
    orig = harness._load
    dgs2, dgs10, price_by_inst = _synthetic_inputs(n_days=500, n_inst=8)
    bt = h.backtest_continuous(dgs2, dgs10, price_by_inst)
    recs = bt["records"]
    if len(recs) < harness.MIN_WINDOW_N:
        check("harness fixture has enough records", False,
              f"only {len(recs)}")
        return
    verdict = h.harness_verdict(recs)
    check("harness_verdict returns a dict with 'admissible'",
          isinstance(verdict, dict) and "admissible" in verdict)
    check("harness_verdict exposes per_window_eff",
          "per_window_eff" in verdict)
    check("harness loader restored after call", harness._load is orig)
    check("is_admissible cross-check present",
          "admissible_via_is_admissible" in verdict)
    # synthetic random-ish data must NOT be admissible (sanity: no fake pass)
    check("synthetic noise is not admissible (no false positive)",
          verdict["admissible"] is False, str(verdict.get("reason")))


# ---------------------------------------------------------------------------
# in_sample_sharpe
# ---------------------------------------------------------------------------
def test_in_sample_sharpe():
    check("sharpe None on tiny sample",
          h.in_sample_sharpe([0.01, 0.02]) is None)
    flat = [0.0] * 100
    check("sharpe None on zero-dispersion", h.in_sample_sharpe(flat) is None)
    pos = [0.001] * 100
    s = h.in_sample_sharpe(pos)
    check("sharpe None when sd==0 even if mean>0", s is None)
    mixed = [0.01, -0.005] * 60
    s2 = h.in_sample_sharpe(mixed)
    check("sharpe computed on mixed returns", s2 is not None and s2 > 0,
          str(s2))


def main() -> int:
    print("# H-008 bond research — unit tests (network-free)\n")
    for fn in (test_compute_slope, test_slope_momentum, test_rolling_z,
               test_signal_by_date_and_lookup, test_backtest_continuous,
               test_harness_wiring, test_in_sample_sharpe):
        print(f"{fn.__name__}:")
        fn()
    print(f"\n# {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
