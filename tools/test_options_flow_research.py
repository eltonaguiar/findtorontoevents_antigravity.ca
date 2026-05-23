#!/usr/bin/env python3
"""Unit tests for tools/options_flow_research.py — NETWORK-FREE.

Tests the pure signal math, leakage controls, cost gate, and harness wiring
on synthetic fixture records (the FIXTURES are test scaffolding only — the
research module itself never generates synthetic market data; these fixtures
exercise the math, they are not fed anywhere near a verdict).

    python tools/test_options_flow_research.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import options_flow_research as ofr  # noqa: E402

_fails = []


def check(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        _fails.append(msg)


def test_rolling_z_strictly_past():
    flat = [1.0] * 60 + [9.0]
    # idx 60 uses [0:60] all 1.0 -> sd 0 -> None
    check(ofr._rolling_z(flat, 60, 60) is None,
          "rolling_z None when past window has sd=0")
    rising = list(range(80))
    z = ofr._rolling_z(rising, 70, 60)
    check(z is not None and z > 0, "rolling_z positive for a rising series")
    check(ofr._rolling_z(rising, 10, 60) is None,
          "rolling_z None when idx < roll (no look-ahead into the future)")


def test_make_record_status_and_field():
    win = ofr._make_record("2026-01-01", "2026-01-08", z=2.5,
                           fwd_ret_net=0.02, direction=1)
    check(win["status"] == "WON", "LONG + positive net fwd_ret -> WON")
    loss = ofr._make_record("2026-01-01", "2026-01-08", z=2.5,
                            fwd_ret_net=0.02, direction=-1)
    check(loss["status"] == "LOST", "SHORT + positive net fwd_ret -> LOST")
    check(win[ofr.ZED_HARNESS_FIELD] == 2.5,
          "signal_z field stores conviction magnitude |z|")
    neg_z = ofr._make_record("2026-01-01", "2026-01-08", z=-3.0,
                             fwd_ret_net=0.01, direction=1)
    check(neg_z[ofr.ZED_HARNESS_FIELD] == 3.0, "signal_z stores abs(z)")


def test_build_records_continuous_book_full_series():
    """H3: continuous book — every signal-day x every ETF becomes a record,
    no |z| threshold, no self-selection of liked trades."""
    sdates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
              for i in range(200)]
    # 3-ETF basket, each drifting differently
    etfs = {
        "AAA": {(date(2026, 1, 1) + timedelta(days=i)).isoformat(): 100.0 + (i % 7)
                for i in range(210)},
        "BBB": {(date(2026, 1, 1) + timedelta(days=i)).isoformat(): 50.0 + (i % 5)
                for i in range(210)},
        "CCC": {(date(2026, 1, 1) + timedelta(days=i)).isoformat(): 200.0 - (i % 3)
                for i in range(210)},
    }
    svals = [10.0 + (i % 11) for i in range(200)]
    recs, gross = ofr._build_signal_records(sdates, svals, etfs, roll=60,
                                            contrarian=True)
    # count signal days with a valid strictly-past rolling z
    zdays = sum(1 for i in range(60, len(sdates) - 1)
                if ofr._rolling_z(svals, i, 60) is not None)
    check(len(recs) <= zdays * len(etfs),
          "record count <= signal-days x basket size (continuous book)")
    check(len(recs) >= len(etfs),
          "continuous book emits records across the whole basket")
    check(gross["n"] == len(recs),
          "gross summary counts the full record series, not a subset")
    # every record carries no-threshold z (records exist even for |z|<1)
    check(any(r[ofr.ZED_HARNESS_FIELD] < 1.0 for r in recs),
          "continuous book keeps |z|<1 records — no |z| threshold (H3)")


def test_cost_gate_subtracts_roundtrip_cost():
    """H4: net edge must be strictly below gross edge by the round-trip cost."""
    # all winners gross; cost should erode the net edge
    recs = []
    for i in range(120):
        d = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        recs.append(ofr._make_record(d, d, z=2.0,
                                     fwd_ret_net=0.01 - ofr.ROUNDTRIP_COST_BPS / 1e4,
                                     direction=1))
    gross = {"n": 120, "gross_wr": 1.0, "gross_mean_signed": 0.01}
    cg = ofr._cost_gate(recs, gross)
    check(cg["net_edge"] < cg["gross_edge"],
          "cost gate: net edge is below gross edge")
    expected_net = 0.01 - ofr.ROUNDTRIP_COST_BPS / 1e4
    check(abs(cg["net_edge"] - expected_net) < 1e-6,
          "cost gate: net edge = gross minus the round-trip cost")
    check(cg["roundtrip_cost_bps"] == ofr.ROUNDTRIP_COST_BPS,
          "cost gate reports the round-trip cost used")


def test_cost_gate_rejects_non_positive_gross():
    recs = [ofr._make_record("2026-01-01", "2026-01-08", z=1.0,
                             fwd_ret_net=-0.01, direction=1)]
    cg = ofr._cost_gate(recs, {"n": 1, "gross_wr": 0.0,
                               "gross_mean_signed": -0.01})
    check(not cg["passed"], "cost gate fails when gross edge is non-positive")


def test_cost_gate_60pct_threshold():
    """A signal keeping >=60% of gross passes; <60% fails."""
    # gross 0.0100, cost erodes to 0.0070 -> survival 70% -> PASS
    recs = [ofr._make_record(f"2026-01-{(i % 27)+1:02d}", "2026-02-01",
                             z=2.0, fwd_ret_net=0.0070, direction=1)
            for i in range(100)]
    cg_pass = ofr._cost_gate(recs, {"n": 100, "gross_wr": 1.0,
                                    "gross_mean_signed": 0.0100})
    check(cg_pass["passed"] and cg_pass["survival"] >= 0.60,
          "cost gate PASSES at 70% survival")
    # gross 0.0100, net 0.0040 -> survival 40% -> FAIL
    recs2 = [ofr._make_record(f"2026-01-{(i % 27)+1:02d}", "2026-02-01",
                              z=2.0, fwd_ret_net=0.0040, direction=1)
             for i in range(100)]
    cg_fail = ofr._cost_gate(recs2, {"n": 100, "gross_wr": 1.0,
                                     "gross_mean_signed": 0.0100})
    check(not cg_fail["passed"] and cg_fail["survival"] < 0.60,
          "cost gate FAILS at 40% survival")


def test_harness_imported_unmodified():
    """H5: is_admissible must be the genuine harness function, not a wrapper."""
    from edge_stability_harness import is_admissible, evaluate, EFF_MIN
    check(ofr.harness.is_admissible is is_admissible,
          "harness.is_admissible is the genuine unmodified function")
    check(ofr.harness.evaluate is evaluate,
          "harness.evaluate is the genuine unmodified function")
    check(EFF_MIN == 0.30, "harness EFF_MIN threshold is unmodified at 0.30")
    check(ofr.WINDOW_DAYS == 14, "module uses the harness's 14-day window")


def test_harness_rejects_noise_signal():
    """A signal_z unrelated to outcome must NOT be admissible."""
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(900):
        d = (d0 + timedelta(days=i // 8)).isoformat()  # dense windows
        z = 1.0 + (i % 5) * 0.1            # z independent of win/loss
        won = (i % 2 == 0)
        recs.append({"status": "WON" if won else "LOST", "resolved_at": d,
                     "entry_date": d, "timestamp": d, ofr.ZED_HARNESS_FIELD: z})
    v = ofr._harness_verdict(recs)
    check(not v["admissible"],
          "harness REJECTS a noise signal_z (no winner/loser separation)")


def test_evaluate_insufficient_data_is_untested_not_pass():
    """H1: too-thin data -> UNTESTED, explicitly NOT a pass."""
    res = {"sub_signal": "X", "name": "thin", "description": "", "data_source": "",
           "input_days": 10, "records": [{}] * 12,
           "gross": {"n": 12, "gross_wr": 0.5, "gross_mean_signed": 0.0}}
    out = ofr._evaluate(res)
    check(out["verdict"] == "UNTESTED",
          "insufficient data -> verdict UNTESTED (not a pass)")
    check(not out["harness"]["admissible"],
          "insufficient-data result is never admissible")
    check("data-insufficient" in out["classification"],
          "insufficient-data classification is labelled honestly")


def test_purge_embargo_tiles_full_series():
    recs = []
    d0 = date(2026, 1, 1)
    for i in range(120):
        d = (d0 + timedelta(days=i)).isoformat()
        recs.append(ofr._make_record(d, d, z=1.5,
                                     fwd_ret_net=0.01 if i % 2 else -0.01,
                                     direction=1))
    cv = ofr._purge_embargo(recs)
    check(cv["oos_n"] == 120, "purged-CV counts every signal event (full series)")
    check(len(cv["blocks"]) >= 5, "purged-CV tiles into multiple 14-day blocks")
    check(cv["embargo_days"] == ofr.EMBARGO_DAYS, "embargo days reported")


def test_dealer_gamma_excluded_from_verdict():
    """The gamma proxy is documentation-only — no verdict path consumes it."""
    summary = ofr._summarise_chain({"data": {"options": []}})
    check(summary.get("available") is False,
          "empty chain snapshot -> gamma proxy unavailable, no crash")
    chain = {"data": {"current_price": 500.0, "options": [
        {"option": "SPY260620C00500000", "open_interest": 1000},
        {"option": "SPY260620P00480000", "open_interest": 800},
    ]}}
    g = ofr._summarise_chain(chain)
    check(g.get("available") is True, "gamma proxy computes from a valid chain")
    check("NOT harness-tested" in g.get("note", ""),
          "gamma proxy note states it is NOT harness-tested (H2 boundary)")


def test_no_synthetic_generator_in_module():
    """The research module must contain no synthetic-data generator."""
    src = (ROOT / "tools" / "options_flow_research.py").read_text(encoding="utf-8")
    lower = src.lower()
    for banned in ("random.", "np.random", "numpy.random", "randn", "gauss(",
                   "random_walk", "synthetic data generator"):
        check(banned not in lower,
              f"module contains no '{banned}' (no synthetic data)")


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        print(f"# {name}")
        globals()[name]()
    if _fails:
        print(f"\n{len(_fails)} FAILURE(S)")
        raise SystemExit(1)
    print("\nALL TESTS PASSED")
