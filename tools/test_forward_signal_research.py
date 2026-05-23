#!/usr/bin/env python3
"""Network-free leakage + density tests for tools/forward_signal_research.py.

These tests exercise the PURE transforms (z-score, cross-sectional rank,
forward-return measurement, inventory-surprise series, record construction,
harness wiring) with synthetic data — NO network. They prove the
non-negotiable property: no look-ahead anywhere. Run:

    python tools/test_forward_signal_research.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import forward_signal_research as fsr  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
# 1. _rolling_z — strictly-past, never includes index idx
# ---------------------------------------------------------------------------
def test_rolling_z_strictly_past() -> None:
    print("test_rolling_z_strictly_past")
    series = [float(i) for i in range(20)]
    # window for idx=10, roll=5 is series[5:10] = [5,6,7,8,9]; series[10]=10
    z = fsr._rolling_z(series, 10, 5)
    mu = statistics.fmean([5, 6, 7, 8, 9])
    sd = statistics.pstdev([5, 6, 7, 8, 9])
    expected = (10 - mu) / sd
    check("z matches strictly-past window", abs(z - expected) < 1e-9,
          f"{z} vs {expected}")
    # if the window erroneously included idx the mean would shift up
    bad_mu = statistics.fmean([5, 6, 7, 8, 9, 10])
    check("z does NOT use index idx in its own window",
          abs(z - (10 - bad_mu) / sd) > 1e-6)
    # too-short window returns None
    check("None when idx < roll", fsr._rolling_z(series, 3, 5) is None)
    # mutating a FUTURE value must not change a past z (no look-ahead)
    s2 = list(series)
    z_before = fsr._rolling_z(s2, 10, 5)
    s2[15] = 9999.0
    z_after = fsr._rolling_z(s2, 10, 5)
    check("future-value mutation does not change a past z",
          z_before == z_after)


# ---------------------------------------------------------------------------
# 2. _cross_sectional_z — single point in time, no time leakage
# ---------------------------------------------------------------------------
def test_cross_sectional_z() -> None:
    print("test_cross_sectional_z")
    vals = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
    csz = fsr._cross_sectional_z(vals)
    check("cross-sectional z has zero mean",
          abs(statistics.fmean(csz.values())) < 1e-9)
    check("highest input -> highest z", csz["D"] == max(csz.values()))
    check("lowest input -> lowest z", csz["A"] == min(csz.values()))
    check("empty on <3 inputs", fsr._cross_sectional_z({"A": 1.0}) == {})
    check("empty on zero variance",
          fsr._cross_sectional_z({"A": 5.0, "B": 5.0, "C": 5.0}) == {})


# ---------------------------------------------------------------------------
# 3. _fwd_return — measured FORWARD only, entry/exit both after signal
# ---------------------------------------------------------------------------
def test_fwd_return_forward_only() -> None:
    print("test_fwd_return_forward_only")
    pdates = [f"2024-01-{d:02d}" for d in range(1, 21)]
    prices = {d: 100.0 + i for i, d in enumerate(pdates)}
    fr = fsr._fwd_return(prices, pdates, "2024-01-05", 5)
    check("forward return computed", fr is not None)
    fwd, resolved = fr
    # entry idx 4 (px 104), exit idx 9 (px 109): 109/104 - 1
    check("return is exit/entry - 1 measured forward",
          abs(fwd - (109 / 104 - 1)) < 1e-9, str(fwd))
    check("resolved date is AFTER entry", resolved > "2024-01-05")
    check("resolved date is exactly hold bars later", resolved == "2024-01-10")
    # not enough forward bars -> None (no fabricated return)
    check("None when not enough forward bars",
          fsr._fwd_return(prices, pdates, "2024-01-19", 5) is None)
    # mutating a price BEFORE entry must not change the forward return
    p2 = dict(prices)
    p2["2024-01-02"] = 1.0
    fr2 = fsr._fwd_return(p2, pdates, "2024-01-05", 5)
    check("pre-entry price mutation does not change forward return",
          abs(fr2[0] - fwd) < 1e-12)


# ---------------------------------------------------------------------------
# 4. _make_record — status from direction-signed return, score = abs(z)
# ---------------------------------------------------------------------------
def test_make_record() -> None:
    print("test_make_record")
    # LONG with positive forward return -> WON
    r = fsr._make_record("2024-01-05", "2024-01-10", -2.3, 0.04, 1)
    check("LONG + positive return -> WON", r["status"] == "WON")
    check("score field is abs(z)", r[fsr.ZED_HARNESS_FIELD] == 2.3)
    # SHORT with positive forward return -> LOST (signed return negative)
    r2 = fsr._make_record("2024-01-05", "2024-01-10", 2.3, 0.04, -1)
    check("SHORT + positive return -> LOST", r2["status"] == "LOST")
    # SHORT with negative forward return -> WON
    r3 = fsr._make_record("2024-01-05", "2024-01-10", 1.0, -0.02, -1)
    check("SHORT + negative return -> WON", r3["status"] == "WON")
    check("entry_date carried", r["entry_date"] == "2024-01-05")
    check("resolved_at carried", r["resolved_at"] == "2024-01-10")


# ---------------------------------------------------------------------------
# 5. _inventory_surprise_series — surprise z is strictly-past
# ---------------------------------------------------------------------------
def test_inventory_surprise_strictly_past() -> None:
    print("test_inventory_surprise_strictly_past")
    # build a 40-week stocks level series with VARIED weekly changes (so the
    # rolling std of prior changes is non-zero), then a clear spike at week 30.
    dates = [f"2024-{((i // 4) + 1):02d}-{((i % 4) * 7 + 1):02d}"
             for i in range(40)]
    levels = {}
    lvl = 1000.0
    # small alternating changes give a non-degenerate prior-change std
    for i, d in enumerate(dates):
        if i == 30:
            lvl += 300.0                    # one big surprise change at i=30
        else:
            lvl += 8.0 if i % 2 == 0 else 12.0
        levels[d] = lvl
    surprises = fsr._inventory_surprise_series(levels, roll=12)
    check("surprise series produced", len(surprises) > 0)
    # the surprise at the spike date should be a large positive z. The change
    # at level-index i is dated dates[i] in cdates, so the spike is at dates[30].
    spike_date = dates[30]
    spike_z = dict(surprises).get(spike_date)
    check("spike change produces a large positive surprise z",
          spike_z is not None and spike_z > 3.0,
          str(spike_z))
    # mutating a FUTURE level must not change an EARLIER surprise z
    if len(surprises) >= 2:
        early_date, early_z = surprises[0]
        lv2 = dict(levels)
        lv2[dates[-1]] = 999999.0
        s2 = dict(fsr._inventory_surprise_series(lv2, roll=12))
        check("future level mutation does not change an earlier surprise z",
              abs(s2.get(early_date, -123) - early_z) < 1e-9)


# ---------------------------------------------------------------------------
# 6. harness wiring — synthetic records flow through evaluate() unmodified
# ---------------------------------------------------------------------------
def test_harness_wiring() -> None:
    print("test_harness_wiring")
    # synthetic: a CLEAN edge (winners always carry higher signal_z). The
    # harness buckets by 14-day windows, so each window's 100 picks must fall
    # inside ONE 14-day span. We pack 100 picks per window into days 1..10 of
    # consecutive months (a <=14-day footprint), 6 windows = 6 months.
    recs = []
    for w in range(6):                       # 6 windows, 1 per month
        for k in range(100):                 # 100 picks/window -> >= MIN_WINDOW_N
            iso = f"2024-{(w+1):02d}-{((k % 10)+1):02d}"   # days 1..10 only
            won = k % 2 == 0
            z = 3.0 if won else 0.2          # winners high z, losers low z
            recs.append({
                "status": "WON" if won else "LOST",
                "resolved_at": iso, "entry_date": iso, "timestamp": iso,
                fsr.ZED_HARNESS_FIELD: z,
            })
    verdict = fsr._harness_verdict(recs)
    check("clean-edge synthetic is harness-admissible",
          verdict.get("admissible") is True,
          str(verdict.get("reason")))
    # a NOISE signal (z identical for winners and losers) must NOT pass
    noise = []
    for r in recs:
        n = dict(r)
        n[fsr.ZED_HARNESS_FIELD] = 1.0
        noise.append(n)
    nv = fsr._harness_verdict(noise)
    check("noise synthetic is harness-REJECTED", nv.get("admissible") is False)
    # harness loader is restored after the patched call
    check("harness._load restored after verdict",
          fsr.harness._load.__name__ != "<lambda>")


# ---------------------------------------------------------------------------
# 7. _evaluate_signal density gate + classification
# ---------------------------------------------------------------------------
def test_evaluate_density_gate() -> None:
    print("test_evaluate_density_gate")
    # below MIN_WINDOW_N total -> INSUFFICIENT DATA, not admissible
    thin = {"hypothesis": "H-XXX", "asset_class": "TEST",
            "signal": "x", "data_source": "x",
            "records": [fsr._make_record("2024-01-01", "2024-01-05",
                                         1.0, 0.01, 1)
                        for _ in range(10)],
            "n": 10}
    res = fsr._evaluate_signal(thin)
    check("thin sample -> not admissible", res["harness"]["admissible"] is False)
    check("thin sample classified UNTESTED",
          fsr._classification(res["harness"]) == "UNTESTED")
    # classification helper maps the three states
    check("_classification ADMISSIBLE", fsr._classification(
        {"admissible": True, "windows_scored": 5}) == "ADMISSIBLE")
    check("_classification REJECTED", fsr._classification(
        {"admissible": False, "windows_scored": 5}) == "REJECTED")
    check("_classification UNTESTED", fsr._classification(
        {"admissible": False, "windows_scored": 1}) == "UNTESTED")


# ---------------------------------------------------------------------------
# 8. report renders without network and never crashes on empty results
# ---------------------------------------------------------------------------
def test_report_renders() -> None:
    print("test_report_renders")
    empty = [fsr._evaluate_signal({
        "hypothesis": "H-002", "asset_class": "EQUITY",
        "signal": "x", "data_source": "x", "records": [], "n": 0})]
    md = fsr.render_report(empty)
    check("report renders for an empty result", "Honest conclusion" in md)
    check("sidecar disclaimer present", "OPT-IN RESEARCH SIDECAR" in md)
    check("UNTESTED counted in conclusion", "UNTESTED" in md)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("=" * 64)
    print("forward_signal_research — network-free leakage/density tests")
    print("=" * 64)
    for fn in (test_rolling_z_strictly_past, test_cross_sectional_z,
               test_fwd_return_forward_only, test_make_record,
               test_inventory_surprise_strictly_past, test_harness_wiring,
               test_evaluate_density_gate, test_report_renders):
        fn()
    print("=" * 64)
    print(f"  {_PASS} passed, {_FAIL} failed")
    print("=" * 64)
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
