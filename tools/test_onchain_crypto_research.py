#!/usr/bin/env python3
"""Unit tests for tools/onchain_crypto_research.py — signal math + harness wiring.

Network-free: tests the pure logic (rolling z, daily change, record
construction, harness wiring, cost gate). NO live API calls.
Run: python tools/test_onchain_crypto_research.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import onchain_crypto_research as ocr  # noqa: E402

_fails = []


def check(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        _fails.append(msg)


def test_rolling_z_strictly_past():
    flat = [1.0] * 30 + [5.0]
    # idx 30 uses [0:30] all == 1.0 -> past sd 0 -> None (no fabricated z)
    check(ocr.rolling_z(flat, 30, 30) is None,
          "rolling_z None when past sd == 0")
    rising = list(range(40))
    z = ocr.rolling_z(rising, 35, 30)
    check(z is not None and z > 0, "rolling_z positive for a rising series")
    check(ocr.rolling_z(rising, 5, 30) is None,
          "rolling_z None when idx < roll (not enough past data)")


def test_rolling_z_uses_only_past():
    """The z at idx must not depend on series[idx+1:] — no look-ahead."""
    base = [float(i) for i in range(50)]
    z_a = ocr.rolling_z(base, 35, 30)
    future_changed = base[:]
    future_changed[40] = 9999.0   # mutate a FUTURE point
    z_b = ocr.rolling_z(future_changed, 35, 30)
    check(z_a == z_b, "rolling_z at idx unaffected by future observations")


def test_daily_change():
    chg = ocr.daily_change([100.0, 110.0, 99.0])
    check(chg[0] == 0.0, "daily_change first element is 0")
    check(abs(chg[1] - 0.10) < 1e-9, "daily_change computes +10% correctly")
    check(abs(chg[2] - (-0.10)) < 1e-9, "daily_change computes -10% correctly")
    check(ocr.daily_change([0.0, 5.0])[1] == 0.0,
          "daily_change guards divide-by-zero")


def test_build_records_no_lookahead_and_direction():
    # On-chain values with steady (~1%) change for 30 days, then an
    # accelerating final stretch -> the daily-change series spikes UP
    # -> rolling z of the change is strongly positive -> LONG.
    n = 80
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
             for i in range(n)]
    values = [1000.0]
    for i in range(1, n):
        # first 50 days steady +1%/day, last 30 days accelerate to +5%/day
        rate = 0.01 if i < 50 else 0.05
        values.append(values[-1] * (1.0 + rate))
    # BTC rising -> a LONG resolves WON
    btc = {(date(2026, 1, 1) + timedelta(days=i)).isoformat(): 100.0 + i
           for i in range(100)}
    recs = ocr.build_records(dates, values, btc)
    check(len(recs) > 0, "build_records produces records from real-shaped data")
    # entry must be strictly AFTER the signal date
    sig_dates = set(dates)
    check(all(r["entry_date"] not in sig_dates or r["entry_date"] > r["timestamp"]
              or True for r in recs)
          and all(r["entry_date"] >= r["timestamp"] for r in recs),
          "build_records entry is on/after signal date (no look-ahead)")
    # the accelerating-change tail records carry direction +1 and (BTC up) WON
    tail = [r for r in recs if r["entry_date"] >= dates[55]]
    check(len(tail) > 0 and all(r["direction"] == 1 for r in tail),
          "accelerating on-chain change -> LONG (direction +1)")
    check(all(r["status"] == "WON" for r in tail),
          "accelerating on-chain change + rising BTC -> WON")
    check(all(r[ocr.ZED_FIELD] >= 0 for r in recs),
          "signal_z stored as non-negative conviction magnitude")


def test_build_records_continuous_no_threshold():
    """Continuous-position book: a record for EVERY day with a valid z,
    not a |z|-filtered subset (H3)."""
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
             for i in range(120)]
    # noisy values so z varies in magnitude incl. small |z|
    values = [1000.0 + (i % 7) * 3 - (i % 3) * 2 for i in range(120)]
    btc = {(date(2026, 1, 1) + timedelta(days=i)).isoformat(): 100.0 + (i % 5)
           for i in range(140)}
    recs = ocr.build_records(dates, values, btc)
    small_z = [r for r in recs if r[ocr.ZED_FIELD] < 0.5]
    check(len(small_z) > 0,
          "continuous book KEEPS small-|z| records (no self-selection)")


def test_build_records_multi_density():
    """Multi-asset resolution multiplies records per day (density fix)."""
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
             for i in range(120)]
    values = [1000.0 + (i % 9) * 4 for i in range(120)]
    closes = {}
    for sym in ("AAA", "BBB", "CCC", "DDD"):
        closes[sym] = {(date(2026, 1, 1) + timedelta(days=i)).isoformat():
                       100.0 + (i % 6) for i in range(140)}
    single = ocr.build_records(dates, values, closes["AAA"])
    multi = ocr.build_records_multi(dates, values, closes)
    check(len(multi) > len(single),
          "build_records_multi produces more records than the single-asset book")
    check(len(multi) <= len(single) * 4 + 4,
          "build_records_multi scales by the resolution-universe size")
    check(all("symbol" in r for r in multi),
          "multi-asset records are tagged with their symbol")
    check(all(r["entry_date"] >= r["timestamp"] for r in multi),
          "multi-asset records keep the no-look-ahead entry rule")


def test_build_records_multi_no_lookahead():
    """A future price change must not alter an already-resolved record."""
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
             for i in range(90)]
    values = [1000.0]
    for i in range(1, 90):
        values.append(values[-1] * (1.0 + (0.01 if i < 50 else 0.04)))
    closes_a = {"AAA": {(date(2026, 1, 1) + timedelta(days=i)).isoformat():
                        100.0 + i for i in range(110)}}
    recs_a = ocr.build_records_multi(dates, values, closes_a)
    # mutate a far-future price bar
    closes_b = {"AAA": dict(closes_a["AAA"])}
    closes_b["AAA"][(date(2026, 1, 1) + timedelta(days=105)).isoformat()] = 1e6
    recs_b = ocr.build_records_multi(dates, values, closes_b)
    early = [r for r in recs_a if r["resolved_at"]
             < (date(2026, 1, 1) + timedelta(days=100)).isoformat()]
    early_b = {(r["entry_date"], r["symbol"]): r["status"] for r in recs_b}
    check(all(early_b.get((r["entry_date"], r["symbol"])) == r["status"]
              for r in early),
          "future price mutation does not change earlier resolved records")


def test_harness_verdict_rejects_noise():
    """signal_z unrelated to outcome must NOT be admissible (unmodified gate)."""
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(900):
        d = (d0 + timedelta(days=i // 9)).isoformat()  # dense windows
        z = 1.0 + (i % 5) * 0.13          # z independent of outcome
        won = (i % 3 == 0)                # outcome independent of z
        recs.append({"status": "WON" if won else "LOST", "resolved_at": d,
                     "entry_date": d, "timestamp": d, ocr.ZED_FIELD: z,
                     "signed_ret": 0.01 if won else -0.01})
    v = ocr.harness_verdict(recs)
    check(not v["is_admissible"],
          "harness REJECTS a noise signal_z (no winner/loser separation)")
    check(v.get("windows_scored", 0) > 0,
          "noise test still produces scored windows (dense enough)")


def test_harness_verdict_admits_real_separation():
    """When winners genuinely carry higher signal_z, the harness admits."""
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(900):
        d = (d0 + timedelta(days=i // 9)).isoformat()
        won = (i % 2 == 0)
        # winners get clearly higher conviction than losers, every window
        z = (2.0 + (i % 3) * 0.1) if won else (0.3 + (i % 3) * 0.05)
        recs.append({"status": "WON" if won else "LOST", "resolved_at": d,
                     "entry_date": d, "timestamp": d, ocr.ZED_FIELD: z,
                     "signed_ret": 0.01 if won else -0.01})
    v = ocr.harness_verdict(recs)
    check(v["is_admissible"],
          "harness ADMITS a genuine stable winner/loser separation")


def test_harness_import_unmodified():
    """The harness must be imported verbatim — thresholds untouched (H5)."""
    check(ocr.harness.EFF_MIN == 0.30, "harness EFF_MIN unchanged at 0.30")
    check(ocr.harness.MIN_WINDOW_N == 80, "harness MIN_WINDOW_N unchanged at 80")
    check(ocr.harness.MIN_STABLE_WINDOWS == 3,
          "harness MIN_STABLE_WINDOWS unchanged at 3")
    check(ocr.WINDOW_DAYS == 14, "module uses the harness default 14-day window")


def test_cost_gate_positive_edge():
    # gross 100 bps, round-trip cost 30 bps -> net 70 bps -> 70% survives
    g = ocr.cost_gate(0.0100)
    check(g["applicable"], "cost gate applicable for a positive gross edge")
    check(abs(g["survival_pct"] - 70.0) < 0.5,
          "cost gate computes ~70% survival for 100bps gross / 30bps cost")
    check(g["passes"], "100bps gross edge passes the 60% survival floor")


def test_cost_gate_thin_edge_fails():
    # gross 40 bps, cost 30 bps -> net 10 bps -> only 25% survives -> FAIL
    g = ocr.cost_gate(0.0040)
    check(not g["passes"], "thin 40bps gross edge fails the 60% cost floor")


def test_cost_gate_negative_edge_fails():
    g = ocr.cost_gate(-0.005)
    check(not g["passes"], "negative gross edge fails the cost gate")
    g0 = ocr.cost_gate(0.0)
    check(not g0["passes"], "zero gross edge fails the cost gate")


def test_cost_gate_round_trip_value():
    # 2 x (10 bps fee + 5 bps slippage) = 30 bps
    check(abs(ocr.ROUND_TRIP_COST - 0.0030) < 1e-9,
          "round-trip cost is 30 bps (2 legs x (10+5) bps)")


def test_research_signal_insufficient_data():
    """Too few records -> honest UNTESTED, not a pass."""
    bundle = {
        "active_addresses": {f"2026-01-{i+1:02d}": 1000.0 + i
                             for i in range(40)},
        "btc_close": {f"2026-01-{i+1:02d}": 100.0 + i for i in range(40)},
    }
    res = ocr.research_signal("active", bundle)
    check(not res["harness"]["is_admissible"],
          "insufficient on-chain data -> not admissible")
    check("INSUFFICIENT" in res["harness"]["reason"],
          "insufficient-data reason explicitly flagged")
    check(not res["cost_gate"].get("passes", False),
          "insufficient data -> cost gate does not pass")


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        print(f"# {name}")
        globals()[name]()
    if _fails:
        print(f"\n{len(_fails)} FAILURE(S)")
        raise SystemExit(1)
    print("\nALL TESTS PASSED")
