"""Deterministic tests for audit3's statistical gates and verdict logic."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    apply_harm_gate,
    benjamini_hochberg,
    binom_sf,
    bootstrap_mean_ci,
    build_report,
    deflated_sharpe,
    evaluate_cell,
    load_rows,
    split_half_ok,
    wilson_interval,
)


def _rows(n, pnl, ac="CRYPTO", strategy="s1", direction="LONG", symbol="BTCUSDT"):
    return [{
        "id": f"{strategy}-{i}",
        "asset_class": ac,
        "strategy": strategy,
        "direction": direction,
        "symbol": symbol,
        "source_system": "alpha_engine",
        "status": "WON" if pnl > 0 else "LOST",
        "pnl_pct": pnl,
        "closed_at": f"2026-11-{1 + i % 18:02d}T00:00:00+00:00",
    } for i in range(n)]


# ─────────────────────────────────────────────────────────────── statistics ──
def test_wilson_never_claims_certainty_on_tiny_samples():
    lo, hi = wilson_interval(2, 2)
    assert lo < 0.35
    assert hi == 1.0
    assert wilson_interval(0, 0) == (0.0, 1.0)
    # Symmetry around 0.5 for 50/100.
    lo2, hi2 = wilson_interval(50, 100)
    assert abs((1 - lo2) - hi2) < 1e-9


def test_binom_sf_matches_known_values():
    assert binom_sf(0, 10) == 1.0
    assert abs(binom_sf(10, 10) - 1 / 1024) < 1e-12
    assert abs(binom_sf(8, 10) - (1 + 10 + 45) / 1024) < 1e-12
    # Above 50% wins the one-sided p must shrink toward 0.
    assert binom_sf(60, 100) < 0.03
    assert binom_sf(40, 100) > 0.9


def test_bootstrap_is_deterministic_and_directional():
    vals = [1.0, 1.2, -0.4, 0.8, 0.9, 1.1, -0.2, 0.7]
    a = bootstrap_mean_ci(vals)
    b = bootstrap_mean_ci(vals)
    assert a["ci_lo"] == b["ci_lo"] and a["ci_hi"] == b["ci_hi"]
    assert a["ci_lo"] > 0
    neg = bootstrap_mean_ci([-1.0] * 20)
    assert neg["ci_hi"] < 0
    assert neg["frac_positive"] == 0.0


def test_bh_is_monotone_and_matches_worked_example():
    q = benjamini_hochberg([0.01, 0.02, 0.03, 0.04])
    assert all(abs(x - 0.04) < 1e-12 for x in q)
    q2 = benjamini_hochberg([0.001, 0.5, 0.9])
    assert q2[0] < 0.01 and abs(q2[1] - 0.75) < 1e-12 and q2[2] == 0.9
    assert benjamini_hochberg([]) == []


def test_deflated_sharpe_penalises_more_trials():
    # Moderate, noisy edge so DSR does not saturate at 1.0 and the trial-count
    # penalty is observable in both sr0 and DSR.
    moderate = [1.0, -0.6, 0.8, -0.5, 0.9, -0.4, 0.7, -0.6, 1.1, -0.5] * 6
    few = deflated_sharpe(moderate, 2)
    many = deflated_sharpe(moderate, 500)
    assert few and many
    assert deflated_sharpe(moderate, 1) is None  # no multiplicity -> undefined
    assert many["sr0"] > few["sr0"]
    assert many["dsr"] < few["dsr"]
    assert 0.0 <= many["dsr"] <= 1.0
    assert deflated_sharpe([1.0] * 30, 10) is None  # zero variance


def test_split_half_requires_both_halves_positive():
    ok, detail = split_half_ok([1.0] * 5 + [1.0] * 5)
    assert ok and detail["first_half_mean"] > 0 and detail["second_half_mean"] > 0
    ok2, _ = split_half_ok([1.0] * 5 + [-1.0] * 5)
    assert not ok2
    assert split_half_ok([1.0])[0] is False


# ────────────────────────────────────────────────────────────────── verdicts ──
def test_small_sample_is_never_promoted():
    cell = evaluate_cell(_rows(10, 1.0), 20, {"asset_class": "CRYPTO"})
    assert cell["n"] == 10
    assert cell["verdict"] == "INSUFFICIENT_N"


def test_clear_loser_is_killed():
    cell = evaluate_cell(_rows(60, -1.0), 20, {"asset_class": "CRYPTO"})
    assert cell["verdict"] == "KILL"
    assert any("CI" in r or "profit factor" in r for r in cell["reasons"])


def test_strong_large_sample_reaches_proven_then_fdr_can_demote():
    rows = _rows(150, 1.2)
    # Spread across symbols so the single-name concentration gate is not what
    # blocks promotion; 145 wins / 5 losers keeps mean positive.
    for i, r in enumerate(rows):
        r["symbol"] = f"SYM{i % 5}"
    for r in rows[:5]:
        r["pnl_pct"] = -0.8
    # Strategy-level cells opt out of the source-diversification gate: one
    # strategy is normally emitted by one source system.
    cell = evaluate_cell(rows, 1, {"asset_class": "CRYPTO"}, apply_source_gate=False)
    assert cell["verdict"] == "PROVEN_T2", cell
    cell["q_value"] = 0.5  # simulate multiplicity failure
    from alpha_engine.audit3_tribunal import _promote
    _promote(cell)
    assert cell["verdict"] == "CANDIDATE"


def test_low_pf_without_significant_harm_is_not_killed():
    """Innocent until proven guilty: PF < 0.80 alone must not kill a cell.

    20 winners at +3.15% gross and 40 losers at -2.00% gross gives PF ~0.70,
    but the sampled net mean has a CI that still contains zero -- the cell is
    unproven, not proven harmful, so it must stay in the ledger as WEAK.
    """
    rows = _rows(60, -2.0)
    for r in rows[:20]:
        r["pnl_pct"] = 3.15
        r["status"] = "WON"
    cell = evaluate_cell(rows, 10, {"asset_class": "CRYPTO"})
    assert cell["pf"] is not None and cell["pf"] < 0.80, cell
    assert cell["net_ci_pct"][1] is not None and cell["net_ci_pct"][1] > 0, cell
    assert cell["verdict"] == "WEAK", cell
    assert any("watch only" in x for x in cell["reasons"])


def test_harm_gate_requires_multiplicity_survival():
    noisy = {"verdict": "KILL", "p_harm": 0.9, "reasons": []}
    apply_harm_gate([noisy])
    assert noisy["verdict"] == "WEAK"
    assert noisy["harm_q"] == 0.9
    real = {"verdict": "KILL", "p_harm": 0.001, "reasons": []}
    apply_harm_gate([real])
    assert real["verdict"] == "KILL"
    assert real["harm_q"] < 0.01


def test_net_expectancy_deducts_slippage():
    rows = _rows(30, 0.10)  # 0.10% gross < 0.15% CRYPTO round trip
    cell = evaluate_cell(rows, 5, {"asset_class": "CRYPTO"})
    assert cell["gross_expectancy_pct"] == 0.1
    assert cell["net_expectancy_pct"] < 0
    assert cell["verdict"] in ("WEAK", "KILL")


def test_single_symbol_concentration_blocks_promotion():
    rows = _rows(120, 1.0)
    for r in rows:
        r["symbol"] = "BTCUSDT"
    rows += _rows(5, 1.0, symbol="ETHUSDT")
    cell = evaluate_cell(rows, 1, {"asset_class": "CRYPTO"})
    assert cell["top_symbol_share"] > 0.9
    assert cell["verdict"] != "PROVEN_T2"


# ─────────────────────────────────────────────────────────────────── report ──
def test_build_report_shapes_and_hypothesis_join(tmp_path, monkeypatch):
    rows = _rows(150, 1.0) + _rows(40, -1.0, strategy="loser", symbol="ADAUSDT")
    report = build_report(rows, "synthetic", None)
    assert report["schema"] == "audit3.v1"
    assert report["summary"]["n_rows"] == 190
    assert report["summary"]["n_cells_total"] == 2
    assert report["summary"]["n_kill"] >= 1
    assert len(report["kill_tribunal"]["kills"]) >= 1
    assert report["classes"][0]["asset_class"] == "CRYPTO"
    assert "conventions" in report and report["conventions"]["fdr_q"] == 0.10
    json.dumps(report, allow_nan=False)  # must be valid strict JSON


def test_report_has_section_by_class_matrix():
    good = _rows(60, 1.5, strategy="s1")
    for r in good:
        r.update({"trust_tier": "PROVEN", "score": 70, "rr_ratio": 2.0,
                  "paper_trade": False, "is_ac_survivor": False,
                  "strat_fwd_trades": 25})
    bad = _rows(40, -1.5, strategy="s2", symbol="ETHUSDT")
    for r in bad:
        r.update({"trust_tier": "WATCH", "score": 40, "rr_ratio": 1.0,
                  "paper_trade": False, "is_ac_survivor": False,
                  "strat_fwd_trades": 5})
    report = build_report(good + bad, "synthetic", None)
    assert report["doctrine"]["name"] == "innocent-until-proven-guilty"
    assert report["segments"], "expected reconstructed segment cells"
    seg = report["segments"][0]
    assert seg["reconstructed"] is True
    assert "segment" in seg and "asset_class" in seg
    assert report["summary"]["n_segment_cells"] == len(report["segments"])
    json.dumps(report, allow_nan=False)


def test_load_rows_dedupes_and_drops_open(tmp_path):
    payload = {
        "generated_at": "2026-11-19T00:00:00Z",
        "picks": {"recent_closed": [
            {"id": "a", "pnl_pct": 1.0, "status": "WON", "asset_class": "CRYPTO"},
            {"id": "a", "pnl_pct": 1.0, "status": "WON", "asset_class": "CRYPTO"},
            {"id": "b", "pnl_pct": None, "status": "LOST", "asset_class": "CRYPTO"},
            {"id": "c", "pnl_pct": 0.5, "status": "OPEN", "asset_class": "CRYPTO"},
        ]},
    }
    p = tmp_path / "picks.json"
    p.write_text(json.dumps(payload))
    rows, generated = load_rows(str(p))
    assert generated == "2026-11-19T00:00:00Z"
    assert len(rows) == 1 and rows[0]["id"] == "a"


def test_cell_reports_required_n_and_mde():
    rows = _rows(60, 1.0) + _rows(60, -0.5)
    cell = evaluate_cell(rows, 1, {"asset_class": "CRYPTO", "strategy": "s1",
                                   "direction": "LONG"})
    assert cell["required_n"] is not None and cell["required_n"] > 0
    assert cell["mde_pct"] is not None and cell["mde_pct"] > 0
    # no dispersion (all rows identical) -> no computable power/MDE
    flat = evaluate_cell(_rows(20, 1.0), 1, {"asset_class": "CRYPTO",
                                             "strategy": "s2", "direction": "LONG"})
    assert flat["required_n"] is None
    assert flat["mde_pct"] is None
