"""Deterministic tests for the audit3 edge-hunt module (beta vs alpha, PIT gates)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_edge_hunt import (  # noqa: E402
    beta_accounting,
    bootstrap_diff,
    build_report,
    gate_provenance,
    mirror_test,
    net_pnl,
    pit_replay,
    required_n,
    battery,
)


def _row(strategy="s1", pnl=1.0, ac="CRYPTO", direction="LONG", symbol="BTC-USD",
         issued="2026-01-01T00:00:00+00:00", closed="2026-01-01T06:00:00+00:00",
         wf=None, **extra):
    r = {
        "strategy": strategy, "pnl_pct": pnl, "asset_class": ac,
        "direction": direction, "symbol": symbol,
        "timestamp": issued, "closed_at": closed,
        "status": "WON" if isinstance(pnl, (int, float)) and pnl > 0 else "LOST",
    }
    if wf:
        r["wf_verdict"] = wf
    r.update(extra)
    return r


# ────────────────────────────────────────────────────────────── net / power ──
def test_net_pnl_applies_per_class_slippage():
    assert abs(net_pnl(_row(pnl=1.0)) - (1.0 - 0.15)) < 1e-9
    assert abs(net_pnl(_row(pnl=1.0, ac="EQUITY")) - 0.90) < 1e-9
    assert net_pnl(_row(pnl=None)) is None


def test_required_n_shrinks_with_bigger_effect():
    small = required_n(1.0, 4.0)
    big = required_n(2.0, 4.0)
    assert small > big > 0
    assert required_n(0.0, 4.0) is None


def test_bootstrap_diff_detects_separation_and_is_seeded():
    a = [2.0] * 40
    b = [0.0] * 40
    d1 = bootstrap_diff(a, b)
    d2 = bootstrap_diff(a, b)
    assert d1 == d2
    assert d1["diff"] == 2.0
    assert d1["ci_lo"] > 0
    assert bootstrap_diff([1.0], [0.0])["diff"] is None


# ────────────────────────────────────────────────────── beta accounting (§A) ──
def test_symmetric_long_short_is_pure_beta():
    # A -1% drift per window with 0.15% cost each way: long -1.15, short +0.85.
    rows = [_row(direction="LONG", pnl=-1.0) for _ in range(60)]
    rows += [_row(direction="SHORT", pnl=1.0) for _ in range(60)]
    b = beta_accounting(rows, "CRYPTO")
    assert b["available"] is True
    # residual alpha must sit inside one cost: this is one market move, twice
    assert abs(b["residual_selection_alpha_pct"]) < 0.20
    assert "beta" in b["verdict"]


def test_one_sided_skill_shows_residual_alpha():
    # Longs and shorts BOTH make money: that cannot be beta.
    rows = [_row(direction="LONG", pnl=2.0) for _ in range(60)]
    rows += [_row(direction="SHORT", pnl=2.0) for _ in range(60)]
    b = beta_accounting(rows, "CRYPTO")
    assert b["residual_selection_alpha_pct"] > 1.0
    assert "residual" in b["verdict"]


def test_beta_needs_both_sides():
    b = beta_accounting([_row(direction="LONG", pnl=1.0) for _ in range(30)], "CRYPTO")
    assert b["available"] is False


# ───────────────────────────────────────────────────────── mirror test (§B) ──
def test_mirror_pairs_need_both_directions_same_day():
    rows = []
    for i in range(30):
        rows.append(_row(direction="LONG", pnl=-1.0, symbol=f"S{i}"))
        rows.append(_row(direction="SHORT", pnl=1.0, symbol=f"S{i}"))
    m = mirror_test(rows, "CRYPTO")
    assert m["available"] is True
    assert m["n_pairs"] == 30
    # perfect mirror: the pair sums to ~0 gross, so net sum is -2c
    assert abs(m["mean_pair_sum_pct"] - (-0.30)) < 0.01


# ──────────────────────────────────────────── point-in-time replay (§C) ──
def test_pit_replay_cannot_see_the_future():
    """The first picks of a losing streak must never be scored by its outcome."""
    rows = []
    # 20 early losses, then 20 late wins, chronologically separated.
    for i in range(20):
        rows.append(_row(pnl=-1.0, issued=f"2026-01-{i+1:02d}T00:00:00+00:00",
                         closed=f"2026-01-{i+1:02d}T06:00:00+00:00"))
    for i in range(20):
        rows.append(_row(pnl=1.0, issued=f"2026-02-{i+1:02d}T00:00:00+00:00",
                         closed=f"2026-02-{i+1:02d}T06:00:00+00:00"))
    pit = pit_replay(rows, min_prior=10)
    buckets = {b["prior_wr_bucket"]: b for b in pit["buckets"]}
    # The first 10 picks have no history at all.
    assert buckets["insufficient"]["n"] == 10
    # Once 10 losses are on record the gate must see a LOW prior WR, not the
    # later wins -- so a "<35%" bucket must exist and contain those picks.
    assert "<35%" in buckets and buckets["<35%"]["n"] >= 10
    # The late picks climb as wins accumulate, but 20 opening losses put a
    # ceiling on the ratio: 20 wins of 40 prior is 50%, so the book tops out in
    # the 45-55% band rather than reaching >=65%. The bucket maths must show
    # that ascent instead of jumping to the top.
    assert {"insufficient", "<35%", "35-45%", "45-55%"} <= set(buckets)
    assert ">=65%" not in buckets


def test_pit_replay_history_is_released_only_at_close():
    """A pick issued before another closes cannot use that outcome."""
    rows = [
        _row(strategy="s1", pnl=1.0, issued="2026-01-01T00:00:00+00:00",
             closed="2026-01-05T00:00:00+00:00"),
        # issued while the first is still open -> prior must be empty
        _row(strategy="s1", pnl=-1.0, issued="2026-01-02T00:00:00+00:00",
             closed="2026-01-03T00:00:00+00:00"),
    ]
    pit = pit_replay(rows, min_prior=1)
    assert pit["n_without_history"] == 2


def test_pit_replay_empty_book_is_safe():
    pit = pit_replay([], min_prior=10)
    assert pit["available"] is False


# ───────────────────────────────────────────────────── battery / provenance ──
def test_battery_applies_bh_and_flags_harm():
    # Vary the outcomes: a constant series has sd 0, so required_n is correctly None.
    rows = [_row(direction="SHORT", pnl=(2.0 if i % 2 else 3.0)) for i in range(80)]
    rows += [_row(direction="LONG", pnl=(-2.0 if i % 2 else -3.0)) for i in range(80)]
    res = {r["test"]: r for r in battery(rows)}
    assert res["T1 CRYPTO short"]["verdict"] == "PROVEN_EDGE"
    assert res["T2 CRYPTO long"]["verdict"] == "PROVEN_HARM"
    assert res["T1 CRYPTO short"]["q_edge"] <= 0.10
    assert res["T1 CRYPTO short"]["n_needed"] is not None


def test_battery_marks_small_samples_insufficient():
    res = battery([_row(pnl=1.0) for _ in range(5)])
    assert all(r["verdict"] == "INSUFFICIENT_N" for r in res)


def test_gate_provenance_flags_a_backfilled_flag():
    rows = [_row(pnl=1.0, at_issue_strat_fwd_wr=0.0, strat_fwd_wr=90.0) for _ in range(50)]
    prov = gate_provenance(rows)
    assert prov["contaminated"] is True
    assert "UNPROVEN" in prov["note"]


def test_gate_provenance_accepts_a_real_snapshot():
    rows = [_row(pnl=1.0, at_issue_strat_fwd_wr=62.0, strat_fwd_wr=60.0) for _ in range(50)]
    prov = gate_provenance(rows)
    assert prov["contaminated"] is False


def test_report_is_serialisable_and_states_its_limits():
    import json
    rows = [_row(direction="LONG", pnl=-1.0) for _ in range(40)]
    rows += [_row(direction="SHORT", pnl=1.0) for _ in range(40)]
    rep = build_report(rows, "synthetic")
    json.dumps(rep, allow_nan=False)  # must not raise
    assert rep["schema"] == "audit3.edge_hunt.v1"
    assert rep["headline"]
    assert any("regime" in x for x in rep["limitations"])
