#!/usr/bin/env python3
"""Unit tests for tools/new_signal_research.py — leakage controls + harness wiring.

Network-free: tests the pure logic (rolling z, purged-CV, harness verdict,
record construction). Run: python tools/test_new_signal_research.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import new_signal_research as nsr  # noqa: E402

_fails = []


def check(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        _fails.append(msg)


def test_rolling_z_strictly_past():
    series = [1.0] * 30 + [5.0]
    # idx 30 uses [0:30] = all 1.0 -> sd 0 -> None
    check(nsr._rolling_z(series, 30, 30) is None, "rolling_z returns None when past sd=0")
    series2 = list(range(40))
    z = nsr._rolling_z(series2, 35, 30)
    check(z is not None and z > 0, "rolling_z positive for rising series")
    # short index -> None
    check(nsr._rolling_z(series2, 5, 30) is None, "rolling_z None when idx < roll")


def test_make_record_status():
    r_win = nsr._make_record("2026-01-01", "2026-01-04", z=2.0, fwd_ret=0.05, direction=1)
    check(r_win["status"] == "WON", "LONG + positive fwd_ret -> WON")
    r_loss = nsr._make_record("2026-01-01", "2026-01-04", z=2.0, fwd_ret=0.05, direction=-1)
    check(r_loss["status"] == "LOST", "SHORT + positive fwd_ret -> LOST")
    check(r_win[nsr.ZED_HARNESS_FIELD] == 2.0, "signal_z stores conviction magnitude")


def test_purge_embargo_blocks():
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(100):
        d = (d0 + timedelta(days=i)).isoformat()
        recs.append(nsr._make_record(d, d, z=1.5, fwd_ret=0.01 if i % 2 else -0.01,
                                     direction=1))
    cv = nsr._purge_embargo(recs)
    check(cv["oos_n"] == 100, "purged-CV counts all events")
    check(len(cv["blocks"]) >= 5, "purged-CV tiles into multiple 14-day blocks")
    check(cv["embargo_days"] == nsr.EMBARGO_DAYS, "embargo days reported")


def test_harness_verdict_noise_rejected():
    """A signal_z unrelated to outcome must NOT be admissible."""
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(600):
        d = (d0 + timedelta(days=i // 6)).isoformat()  # ~6 picks/day -> dense windows
        # z alternates independently of win/loss -> pure noise
        z = 1.0 + (i % 5) * 0.1
        won = (i % 3 == 0)
        rec = {"status": "WON" if won else "LOST", "resolved_at": d,
               "entry_date": d, "timestamp": d, nsr.ZED_HARNESS_FIELD: z}
        recs.append(rec)
    v = nsr._harness_verdict(recs)
    check(not v["admissible"], "harness REJECTS a noise signal_z (no winner/loser sep)")


def test_evaluate_insufficient_data():
    res = {"hypothesis": "H-X", "asset_class": "TEST", "records": [{}] * 10}
    out = nsr._evaluate_signal(res)
    check(not out["harness"]["admissible"], "insufficient-data result is not admissible")
    check("INSUFFICIENT" in out["harness"]["reason"], "insufficient-data reason flagged")


# ---------------------------------------------------------------------------
# H-008 continuous-position variant — leakage controls + density
# ---------------------------------------------------------------------------
def test_bond_continuous_z_strictly_past():
    """The slope-momentum z is truncation-invariant: appending FUTURE yield
    observations must NOT change a z already computed for an earlier date."""
    d0 = date(2024, 1, 1)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(200)]
    # rising slope so momentum + rolling-z are well-defined
    dgs2 = {dates[i]: 1.0 + 0.001 * i for i in range(200)}
    dgs10 = {dates[i]: 2.0 + 0.01 * i for i in range(200)}
    full = nsr._bond_slope_momentum_z_from(dgs2, dgs10)
    # truncate to the first 120 days — z for those days must be identical
    cut = 120
    dgs2_t = {d: dgs2[d] for d in dates[:cut]}
    dgs10_t = {d: dgs10[d] for d in dates[:cut]}
    trunc = nsr._bond_slope_momentum_z_from(dgs2_t, dgs10_t)
    common = [d for d in dates[:cut] if d in full and d in trunc]
    check(len(common) >= 30, "continuous-z produced enough early-date z values")
    invariant = all(abs(full[d] - trunc[d]) < 1e-9 for d in common)
    check(invariant, "continuous-z is truncation-invariant (strictly past, no look-ahead)")


def test_latest_past_z_no_lookahead():
    """_latest_past_z must NEVER return a z dated after the entry date."""
    zrec = {"2024-01-05": 1.0, "2024-01-10": 2.0, "2024-01-20": 3.0}
    # entry between two z dates -> returns the latest one <= entry
    check(nsr._latest_past_z(zrec, "2024-01-12") == 2.0,
          "latest_past_z returns most recent z <= entry")
    # entry exactly on a z date -> that z is allowed (<= is inclusive)
    check(nsr._latest_past_z(zrec, "2024-01-10") == 2.0,
          "latest_past_z allows a z dated exactly on entry")
    # entry before any z -> None (no future z leaked)
    check(nsr._latest_past_z(zrec, "2024-01-01") is None,
          "latest_past_z returns None rather than a future-dated z")
    # entry after the last z -> last z, never a future one
    check(nsr._latest_past_z(zrec, "2024-02-01") == 3.0,
          "latest_past_z never returns a z dated after entry")


def test_bond_continuous_records_no_lookahead():
    """Records resolve strictly after entry, AND density clears MIN_WINDOW_N=80
    for >= 3 fourteen-day windows."""
    d0 = date(2024, 1, 1)
    # 250 trading-day price series (skip weekends for realism not required)
    pdates = [(d0 + timedelta(days=i)).isoformat() for i in range(250)]
    px = {pdates[i]: 100.0 + i * 0.1 for i in range(250)}
    # a z value available from early on, dated before the price window starts
    zrec = {(d0 - timedelta(days=5)).isoformat(): 1.5}
    recs = nsr._bond_continuous_records(zrec, px, horizons=(1, 2, 3))
    # (a) every record resolves strictly AFTER its entry
    forward_ok = all(r["resolved_at"] > r["entry_date"] for r in recs)
    check(forward_ok, "continuous records resolve strictly after entry (no look-ahead)")
    # (b) ~3 records per entry day (one per horizon)
    n_entries = len({r["entry_date"] for r in recs})
    check(len(recs) >= n_entries * 3 - 3,
          "continuous book emits ~3 records (1/horizon) per entry day")
    # (c) density: tile into 14-day windows, >= 3 windows clear MIN_WINDOW_N=80.
    #     Four instruments share the same z book, so model 4x the per-instrument
    #     record count (the harness sees the pooled book).
    pooled = recs * len(nsr.BOND_CONT_INSTRUMENTS)
    cv = nsr._purge_embargo(pooled)
    big_windows = [b for b in cv["blocks"] if b["n"] >= nsr.harness.MIN_WINDOW_N]
    check(len(big_windows) >= 3,
          f"continuous-book density clears MIN_WINDOW_N={nsr.harness.MIN_WINDOW_N} "
          f"for >= 3 windows (got {len(big_windows)})")


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        print(f"# {name}")
        globals()[name]()
    if _fails:
        print(f"\n{len(_fails)} FAILURE(S)")
        raise SystemExit(1)
    print("\nALL TESTS PASSED")
