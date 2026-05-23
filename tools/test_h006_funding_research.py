#!/usr/bin/env python3
"""Network-free unit tests for tools/h006_funding_research.py.

Covers the signal math (rolling_z, build_signal_records, basis gate,
no-look-ahead entry), the synthetic-record shape, the purged-CV summary, and
the harness wiring (records actually flow through edge_stability_harness and
produce the same verdict shape).

    python tools/test_h006_funding_research.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
ROOT = TOOLS.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import edge_stability_harness as harness  # noqa: E402
import h006_funding_research as h6  # noqa: E402

_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
# rolling_z
# ---------------------------------------------------------------------------
def test_rolling_z():
    # strictly-past: idx < roll -> None
    check("rolling_z short-history None", h6.rolling_z([1, 2, 3], 1, 5) is None)
    # constant past window -> sd==0 -> None
    check("rolling_z degenerate-window None",
          h6.rolling_z([5.0] * 10 + [9.0], 10, 10) is None)
    # known z: past = 0..9 (mean 4.5, pstdev ~2.872), value 13.372 -> z ~ 3.087
    series = list(range(10)) + [13.372281323]
    z = h6.rolling_z([float(x) for x in series], 10, 10)
    check("rolling_z known value", z is not None and abs(z - 3.087) < 0.01,
          f"got {z}")
    # rolling_z must compute the window from STRICTLY-PAST observations:
    # series[idx] must NOT enter the window mean/sd. Two series identical up to
    # idx-1 but differing at idx must use the SAME window stats, so the z's
    # differ ONLY through the numerator (series[idx] - mu).
    past = [1.0, 3.0, 2.0, 5.0, 4.0, 6.0]   # 6 non-degenerate past obs
    za = h6.rolling_z(past + [10.0], 6, 6)
    zb = h6.rolling_z(past + [20.0], 6, 6)
    mu = sum(past) / 6
    sd = (sum((x - mu) ** 2 for x in past) / 6) ** 0.5
    check("rolling_z window is strictly-past (current obs excluded from stats)",
          abs(za - (10.0 - mu) / sd) < 1e-9 and abs(zb - (20.0 - mu) / sd) < 1e-9,
          f"za={za} zb={zb} — current obs leaked into window stats")


# ---------------------------------------------------------------------------
# build_signal_records — signal math, basis gate, no-look-ahead
# ---------------------------------------------------------------------------
def _dates(n: int, start="2024-01-01"):
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def _noisy_funding(dts, spike_idx, spike_val):
    """Funding dict with a small-amplitude noise floor (so the rolling window
    is non-degenerate, pstdev>0) plus one large spike at spike_idx."""
    funding = {}
    for i, d in enumerate(dts):
        # deterministic small oscillation around zero — gives the past window
        # a real (tiny) standard deviation so rolling_z is not None.
        funding[d] = 0.0001 * (1 if i % 2 == 0 else -1) + 0.00003 * (i % 5)
    funding[dts[spike_idx]] = spike_val
    return funding


def test_no_lookahead_entry():
    """Entry must be the first price date STRICTLY AFTER the signal date."""
    dts = _dates(60)
    funding = _noisy_funding(dts, spike_idx=40, spike_val=0.05)
    prices = {d: 100.0 + i for i, d in enumerate(dts)}
    recs = h6.build_signal_records(funding, {}, prices, "TESTUSDT",
                                   z_roll=30, z_threshold=1.0, fwd_days=3)
    check("no-lookahead: at least one signal fires", len(recs) >= 1,
          f"recs={[r['entry_date'] for r in recs]}")
    # the spike at idx 40 -> signal date dts[40] -> entry must be strictly after
    spike_recs = [r for r in recs if r["signal_date"] == dts[40]]
    check("no-lookahead: entry strictly after signal date",
          all(r["entry_date"] > dts[40] for r in spike_recs)
          and len(spike_recs) >= 1,
          f"spike entries={[r['entry_date'] for r in spike_recs]}")


def test_contrarian_direction():
    """Positive funding z -> SHORT (-1); negative -> LONG (+1)."""
    dts = _dates(50)
    prices = {d: 100.0 + (i % 3) for i, d in enumerate(dts)}
    # positive spike at idx 35
    fpos = _noisy_funding(dts, spike_idx=35, spike_val=0.10)
    recs = h6.build_signal_records(fpos, {}, prices, "T",
                                   z_roll=30, z_threshold=1.0, fwd_days=2)
    pos = [r for r in recs if r["signal_date"] == dts[35]]
    check("contrarian: positive funding z -> SHORT",
          len(pos) >= 1 and all(r["direction"] == -1 for r in pos),
          f"directions={[r['direction'] for r in pos]}")
    # negative spike at idx 35
    fneg = _noisy_funding(dts, spike_idx=35, spike_val=-0.10)
    recs2 = h6.build_signal_records(fneg, {}, prices, "T",
                                    z_roll=30, z_threshold=1.0, fwd_days=2)
    neg = [r for r in recs2 if r["signal_date"] == dts[35]]
    check("contrarian: negative funding z -> LONG",
          len(neg) >= 1 and all(r["direction"] == 1 for r in neg),
          f"directions={[r['direction'] for r in neg]}")


def test_basis_gate():
    """Basis disagreeing with the faded crowd suppresses the trade."""
    dts = _dates(50)
    funding = _noisy_funding(dts, spike_idx=35, spike_val=0.10)  # crowded long
    prices = {d: 100.0 + (i % 3) for i, d in enumerate(dts)}
    # basis NEGATIVE on signal date -> disagrees with crowded-long -> suppressed
    recs_blocked = h6.build_signal_records(funding, {dts[35]: -0.002}, prices,
                                           "T", z_roll=30, z_threshold=1.0,
                                           fwd_days=2)
    fired_blocked = [r for r in recs_blocked if r["signal_date"] == dts[35]]
    # basis POSITIVE -> agrees -> trade passes
    recs_pass = h6.build_signal_records(funding, {dts[35]: 0.002}, prices, "T",
                                        z_roll=30, z_threshold=1.0, fwd_days=2)
    fired_pass = [r for r in recs_pass if r["signal_date"] == dts[35]]
    check("basis gate: disagreeing basis suppresses the trade",
          len(fired_blocked) == 0, f"got {len(fired_blocked)} (expected 0)")
    check("basis gate: agreeing basis lets the trade through",
          len(fired_pass) >= 1, f"got {len(fired_pass)} (expected >=1)")


def test_record_shape():
    rec = h6.make_record("2024-02-01", "2024-02-04", z=-2.5, fwd_ret=-0.03,
                          direction=1, symbol="BTCUSDT")
    # direction +1 LONG, fwd_ret -0.03 -> signed -0.03 -> LOST
    check("record status from signed return (LOST)", rec["status"] == "LOST")
    rec2 = h6.make_record("2024-02-01", "2024-02-04", z=2.0, fwd_ret=-0.03,
                           direction=-1, symbol="BTCUSDT")
    # SHORT a -3% move -> +3% -> WON
    check("record status from signed return (WON)", rec2["status"] == "WON")
    check("record carries abs(z) as signal_z",
          rec[h6.HARNESS_FIELD] == 2.5)
    check("record has harness date fields",
          "resolved_at" in rec and "entry_date" in rec and "timestamp" in rec)


# ---------------------------------------------------------------------------
# purged-CV + harness wiring
# ---------------------------------------------------------------------------
def _synthetic_records(n_per_window: int, n_windows: int, edge: bool):
    """Build records spanning n_windows 14-day blocks.

    edge=True: winners carry HIGH signal_z, losers LOW (a real, stable edge).
    edge=False: signal_z is independent of outcome (pure noise).
    """
    import random
    rng = random.Random(42)
    recs = []
    d0 = date.fromisoformat("2024-01-01")
    for w in range(n_windows):
        for i in range(n_per_window):
            day = d0 + timedelta(days=w * 14 + (i % 14))
            won = i % 2 == 0
            if edge:
                z = rng.uniform(2.5, 4.0) if won else rng.uniform(0.5, 1.5)
            else:
                z = rng.uniform(0.5, 4.0)
            recs.append({
                "status": "WON" if won else "LOST",
                "resolved_at": day.isoformat(),
                "entry_date": day.isoformat(),
                "timestamp": day.isoformat(),
                h6.HARNESS_FIELD: z,
            })
    return recs


def test_harness_wiring_edge():
    """A clean separating signal must come back ADMISSIBLE through our wiring."""
    recs = _synthetic_records(n_per_window=90, n_windows=4, edge=True)
    v = h6.harness_verdict(recs, h6.WINDOW_DAYS)
    check("harness wiring: clean edge -> admissible", v.get("admissible") is True,
          f"verdict={v.get('reason')}")
    check("harness wiring: edge eff sign positive", v.get("sign") == "+",
          f"sign={v.get('sign')}")


def test_harness_wiring_noise():
    """Pure noise must NOT come back admissible."""
    recs = _synthetic_records(n_per_window=90, n_windows=4, edge=False)
    v = h6.harness_verdict(recs, h6.WINDOW_DAYS)
    check("harness wiring: noise -> not admissible",
          v.get("admissible") is False, f"verdict={v.get('reason')}")


def test_harness_loader_restored():
    """harness._load must be restored after harness_verdict (no global leak)."""
    orig = harness._load
    h6.harness_verdict(_synthetic_records(90, 3, True), 14)
    check("harness loader restored after call", harness._load is orig)


def test_purge_embargo_summary():
    recs = _synthetic_records(n_per_window=20, n_windows=3, edge=True)
    cv = h6.purge_embargo(recs)
    check("purge_embargo: oos_n counts all records",
          cv["oos_n"] == len(recs), f"{cv['oos_n']} != {len(recs)}")
    check("purge_embargo: pooled WR ~0.5 for even WON/LOST split",
          abs(cv["oos_wr"] - 0.5) < 0.05, f"wr={cv['oos_wr']}")
    check("purge_embargo: blocks non-empty", len(cv["blocks"]) >= 1)


def test_collapse_funding_daily():
    # two funding events same UTC day -> averaged
    # 2024-03-01 00:00 and 08:00 UTC
    ts1 = 1709251200000   # 2024-03-01 00:00:00 UTC
    ts2 = ts1 + 8 * 3600 * 1000
    ts3 = ts1 + 24 * 3600 * 1000   # next day
    daily = h6.collapse_funding_daily([(ts1, 0.01), (ts2, 0.03), (ts3, 0.05)])
    check("collapse_funding_daily averages same-day events",
          abs(daily["2024-03-01"] - 0.02) < 1e-9, f"{daily}")
    check("collapse_funding_daily keeps distinct days",
          "2024-03-02" in daily and abs(daily["2024-03-02"] - 0.05) < 1e-9)


def test_offline_pipeline_end_to_end():
    """research_h006 must run fully offline from a cache blob."""
    dts = _dates(120)
    funding = {d: 0.0001 for d in dts}
    for i in (40, 70, 100):
        funding[dts[i]] = 0.08
    prices = {d: 100.0 + (i % 7) for i, d in enumerate(dts)}
    cache = {"BTCUSDT": {"funding": [], "prices": prices, "basis": {}}}
    # funding list is (ts, rate) — convert ISO dates to ms timestamps
    from datetime import datetime as _dt, timezone as _tz
    flist = []
    for d, r in funding.items():
        ms = int(_dt.fromisoformat(d).replace(tzinfo=_tz.utc).timestamp() * 1000)
        flist.append([ms, r])
    cache["BTCUSDT"]["funding"] = flist
    res = h6.research_h006(quick=True, offline=cache)
    check("offline pipeline: produces a result dict",
          res.get("hypothesis") == "H-006" and "records" in res)
    res = h6.evaluate(res)
    check("offline pipeline: evaluate attaches a harness verdict",
          "harness" in res and "admissible" in res["harness"])


def main() -> int:
    print("# H-006 funding-research unit tests (network-free)\n")
    for fn in (test_rolling_z, test_no_lookahead_entry, test_contrarian_direction,
               test_basis_gate, test_record_shape, test_harness_wiring_edge,
               test_harness_wiring_noise, test_harness_loader_restored,
               test_purge_embargo_summary, test_collapse_funding_daily,
               test_offline_pipeline_end_to_end):
        print(f"{fn.__name__}:")
        fn()
    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
