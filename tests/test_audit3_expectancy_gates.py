"""Tests for the audit3 v2 gates: expectancy-primary, cost stress, hash provenance.

The arena.ai review (AUDIT3_FEEDBACK_2026-11-19.md) is right that a win-rate gate
makes a trend/premia cell unpromotable by construction. These tests pin the rule
that replaced it, plus the trial-accounting and provenance fixes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_tribunal import build_report  # noqa: E402


def _rows(n_wins: int, n_losses: int, win: float, loss: float,
          *, klass: str = "CRYPTO", symbols=("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT"),
          sources=("src_a", "src_b"), tag: str | None = None) -> list[dict]:
    """Build a deterministic row set: wins and losses interleaved so both
    chronological halves carry the same edge (split-half stability)."""
    cycle = [win] + [loss, loss]
    rows, i = [], 0
    while len(rows) < n_wins + n_losses:
        v = cycle[i % 3]
        if v == win and sum(1 for r in rows if r["pnl_pct"] > 0) >= n_wins:
            v = loss
        if v == loss and sum(1 for r in rows if r["pnl_pct"] <= 0) >= n_losses:
            v = win
        rows.append({
            "id": f"r{i}", "asset_class": klass, "strategy": "cellA",
            "symbol": symbols[i % len(symbols)], "direction": "LONG",
            "source_system": sources[i % len(sources)],
            "pnl_pct": v, "status": "WON" if v > 0 else "LOST",
            "closed_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
            **({"trust_tier": tag} if tag else {}),
        })
        i += 1
    return rows[:n_wins + n_losses]


def test_expectancy_primary_promotes_low_win_rate_cell():
    # 33% win rate, 4.0/-0.6 payoff: positive expectancy that a WR>50% gate
    # could never certify. n=210 because PROVEN now pays the global 658-trial
    # DSR correction: the same cell at n=120 scores DSR 0.83 and caps at
    # CANDIDATE, which is the intended tightening, not a test failure.
    rows = _rows(70, 140, 4.0, -0.6)
    pod = {"path": "m.json", "available": True,
           "pods": [{"id": "POD-A", "status": "pre_registered",
                     "strategies": ["cellA"], "asset_classes": ["CRYPTO"]}]}
    rep = build_report(rows, "x.json", None, confirmatory=pod)
    cell = rep["cells"][0]
    assert cell["wr"] < 0.40
    assert cell["net_expectancy_pct"] > 0
    assert cell["p_wr"] > 0.9      # WR descriptor still says "not better than coin flip"
    assert cell["p_value"] < 0.01  # expectancy test says "yes, edge"
    # A 2,000-resample bootstrap cannot report p = 0; the +1 correction keeps the
    # top-ranked cell from getting a BH q of exactly zero.
    # strictly positive (never 0) and small; this synthetic cell still has a few
    # non-positive resamples, so the floor is the bound, not the value.
    assert 0 < cell["p_value"] < 0.01
    # Full gate stack: block bootstrap (F1) keeps the 2x-cost CI positive, so G9
    # stress passes and the cell reaches PROVEN_T2 (expectancy-primary intent).
    assert cell["verdict"] == "PROVEN_T2"
    assert cell["stress_2x_ok"] is True
    # Same evidence without a pre-registered pod: forward paper, not sizing.
    bare = build_report(rows, "x.json", None, confirmatory={"pods": []})
    assert bare["cells"][0]["verdict"] == "CANDIDATE"
    assert bare["summary"]["n_proven"] == 0


def test_high_win_rate_negative_expectancy_is_not_promoted():
    rows = _rows(90, 30, 0.2, -1.2)
    rep = build_report(rows, "x.json", None)
    cell = rep["cells"][0]
    assert cell["wr"] > 0.70
    assert cell["net_expectancy_pct"] < 0
    assert cell["verdict"] != "PROVEN_T2"


def test_dsr_is_only_scored_inside_the_tested_family():
    rows = _rows(40, 80, 3.0, -0.6)
    # 40 extra rows split into three sub-floor strategies.
    for i in range(36):
        rows.append({"id": f"small{i}", "asset_class": "CRYPTO",
                     "strategy": f"small{i % 3}", "symbol": "AAAUSDT",
                     "direction": "LONG", "pnl_pct": 0.5, "status": "WON",
                     "closed_at": "2026-02-01T00:00:00Z"})
    rep = build_report(rows, "x.json", None)
    assert all(c["dsr"] is None for c in rep["cells"]
               if c["n"] < 20), "sub-floor cells must not publish a DSR"
    assert rep["summary"]["n_cells_dsr_scored"] <= rep["summary"]["n_cells_tested"]


def test_reconstructed_segment_cannot_be_proven():
    rows = _rows(40, 80, 3.0, -0.6, tag="S")
    rep = build_report(rows, "x.json", None)
    segs = [c for c in rep["segments"] if c["segment"] == "trust_tier"]
    assert segs, "expected a trust_tier segment cell"
    for c in segs:
        # Section membership is rebuilt from row fields, so a segment cell is
        # never a registered pod and must never be sizing-eligible.
        assert c["verdict"] != "PROVEN_T2"
        assert c["namespace"] == "discovery"


def test_cost_stress_2x_is_reported_and_stricter():
    rows = _rows(40, 80, 3.0, -0.6)
    cell = build_report(rows, "x.json", None)["cells"][0]
    assert cell["net_ci_pct_2x"][0] is not None
    assert cell["net_ci_pct_2x"][0] < cell["net_ci_pct"][0]
    assert cell["stress_2x_ok"] == (cell["net_ci_pct_2x"][0] > 0)


def test_cost_stress_2x_is_a_required_gate():
    # 3.0/-0.6: positive expectancy, but the edge dies at 2x slippage -> the
    # cell must be demoted to WEAK with the stress clause named in its reasons.
    # 3.0/-1.0: net positive (+0.18%) but the 2x-cost CI lower bound is <= 0,
    # so the edge is a cost assumption and must be demoted.
    rows = _rows(40, 80, 3.0, -1.0)
    cell = build_report(rows, "x.json", None)["cells"][0]
    assert cell["net_expectancy_pct"] > 0
    assert cell["stress_2x_ok"] is False
    assert cell["verdict"] == "WEAK"
    assert any("2x-cost" in r for r in cell["reasons"])

    # A payoff that survives 2x cost still promotes inside a pre-registered pod.
    robust = build_report(
        _rows(70, 140, 4.0, -0.6), "x.json", None,
        confirmatory={"path": "m.json", "available": True,
                      "pods": [{"id": "POD-A", "status": "pre_registered",
                                "strategies": ["cellA"], "asset_classes": ["CRYPTO"]}]})
    assert robust["cells"][0]["stress_2x_ok"] is True
    assert robust["cells"][0]["verdict"] == "PROVEN_T2"


def test_observe_pod_does_not_confer_confirmatory():
    # A pod registered as observe (below the forward floor) must not launder
    # rows into a promotion; only pre_registered confers confirmatory status.
    rows = _rows(40, 80, 4.0, -0.6)
    rep = build_report(
        rows, "x.json", None,
        confirmatory={"path": "m.json", "available": True,
                      "pods": [{"id": "POD-OBS", "status": "observe",
                                "strategies": ["cellA"], "asset_classes": ["CRYPTO"]}]})
    assert rep["cells"][0]["verdict"] != "PROVEN_T2"


def test_provenance_carries_hash_and_version():
    rep = build_report(_rows(10, 10, 1.0, -1.0), "x.json", None, input_sha256="deadbeef")
    prov = rep["provenance"]
    assert prov["input_sha256"] == "deadbeef"
    assert prov["generator_version"].startswith("audit3.v")
    assert "DSR uses the global trial count" in prov["registry_note"]
    assert prov["n_trials_dsr"] >= 1
    json.dumps(rep, allow_nan=False)
