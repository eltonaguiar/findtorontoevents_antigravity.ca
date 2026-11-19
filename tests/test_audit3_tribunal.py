"""Deterministic tests for audit3's statistical gates and verdict logic."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    apply_harm_gate,
    apply_selection_alpha_gate,
    benjamini_hochberg,
    binom_sf,
    bootstrap_mean_ci,
    build_report,
    deflated_sharpe,
    evaluate_cell,
    global_trial_count,
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


# ─────────────────────────────────────────────── G8 selection-alpha scope ──
def _proven_cell(**kw):
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "verdict": "PROVEN_T2", "reasons": []}
    cell.update(kw)
    return cell


def test_selection_alpha_gate_rejects_a_class_proxy_for_a_strategy_cell():
    """A positive class alpha does not prove the strategy beat buy-and-hold."""
    cell = _proven_cell()
    alpha = {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [0.5, 1.0]}},
             "by_strategy": {}}
    summary = apply_selection_alpha_gate([cell], alpha)
    assert summary["applied"] is True and summary["demoted"] == 1
    assert cell["verdict"] == "CANDIDATE"
    assert cell["alpha_gate"]["alpha_ci_lo"] == 0.5
    assert cell["alpha_gate"]["scope"] == "class_proxy"
    assert cell["alpha_gate"]["passed"] is False
    assert cell["beta_dominant"] is True


def test_selection_alpha_gate_accepts_strategy_level_proof():
    cell = _proven_cell()
    alpha = {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-1.0, 1.0]}},
             "by_strategy": {"CRYPTO/s1/LONG": {"n": 120, "alpha_ci": [0.2, 0.9]}}}
    summary = apply_selection_alpha_gate([cell], alpha)
    assert summary["demoted"] == 0
    assert cell["verdict"] == "PROVEN_T2"
    assert cell["alpha_gate"]["alpha_ci_lo"] == 0.2
    assert cell["alpha_gate"]["scope"] == "strategy"
    assert cell["alpha_gate"]["alpha_n"] == 120
    assert cell["alpha_gate"]["passed"] is True
    assert "beta_dominant" not in cell


def test_selection_alpha_gate_keeps_candidate_but_flags_it():
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "verdict": "CANDIDATE", "reasons": []}
    apply_selection_alpha_gate(
        [cell], {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-0.2, 0.1]}}})
    assert cell["verdict"] == "CANDIDATE"
    assert cell["beta_dominant"] is True


def test_selection_alpha_gate_reports_when_it_did_not_run():
    assert apply_selection_alpha_gate([], None)["applied"] is False
    assert apply_selection_alpha_gate([], {})["applied"] is False


def test_build_report_records_that_the_alpha_gate_ran():
    rows = _rows(160, 1.2)
    for i, r in enumerate(rows):  # keep the symbol share under 60%
        r["symbol"] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"][i % 4]
    report = build_report(rows, "synthetic", None,
                          alpha={"by_class": {"CRYPTO": {"n": 160,
                                                         "alpha_ci": [0.4, 1.1]}}})
    gate = report["selection_alpha"]["gate"]
    assert gate["applied"] is True
    assert gate["scopes"].get("class_proxy", 0) >= 1


# ───────────────────────────────────────────── DSR multiplicity floor ──
def test_dsr_trial_count_never_below_the_registry_space():
    assert global_trial_count(3) == 658
    assert global_trial_count(0) == 658
    assert global_trial_count(2000) == 2000


# ───────────────────────────────────────────── source families ──
def test_source_families_pass_the_multiplicity_gates():
    """They are verdict-bearing rows, so they cannot skip BH/DSR."""
    rows = _rows(160, 1.2)
    for i, r in enumerate(rows):
        r["symbol"] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"][i % 4]
    report = build_report(rows, "synthetic", None)
    fam = next(f for f in report["source_families"] if f["n"] == 160)
    assert fam["q_value"] is not None
    assert fam["verdict"] != "PROVEN_T2"  # discovery cannot be sizing-eligible


def test_proven_tier_pays_the_global_dsr_correction():
    from alpha_engine.audit3_tribunal import _promote
    cell = {"verdict": "PROVEN_T2", "n": 120, "q_value": 0.01, "dsr": 0.40,
            "dsr_local": 0.99, "reasons": [], "namespace": "confirmatory"}
    _promote(cell)
    assert cell["verdict"] == "CANDIDATE"


def test_candidate_tier_uses_local_breadth_not_the_global_registry():
    from alpha_engine.audit3_tribunal import _promote
    # Single-cell bucket: no within-family multiplicity, so the CANDIDATE floor
    # must not be applied against the 658-trial registry.
    cell = {"verdict": "CANDIDATE", "n": 120, "q_value": 0.01, "dsr": 0.10,
            "dsr_local": None, "reasons": []}
    _promote(cell)
    assert cell["verdict"] == "CANDIDATE"
    # A real local breadth with a poor local DSR still demotes.
    cell2 = {"verdict": "CANDIDATE", "n": 120, "q_value": 0.01, "dsr": 0.90,
             "dsr_local": 0.30, "reasons": []}
    _promote(cell2)
    assert cell2["verdict"] == "WEAK"


def test_require_alpha_demotes_proven_when_the_sidecar_is_missing():
    from alpha_engine.audit3_tribunal import demote_proven_without_alpha
    cell = _proven_cell()
    # Library callers keep fail-open...
    assert apply_selection_alpha_gate([cell], None)["applied"] is False
    assert cell["verdict"] == "PROVEN_T2"
    # ...but the published path must not call an unmeasured alpha "proven".
    assert demote_proven_without_alpha(([cell],)) == 1
    assert cell["verdict"] == "CANDIDATE"
    assert cell["beta_dominant"] is True


def test_alpha_must_cover_enough_of_the_cell_to_prove_it():
    cell = _proven_cell(n=500)
    alpha = {"by_class": {"CRYPTO": {"n": 500, "alpha_ci": [0.4, 1.0]}},
             "by_strategy": {"CRYPTO/s1/LONG": {"n": 20, "alpha_ci": [0.3, 0.9]}}}
    summary = apply_selection_alpha_gate([cell], alpha)
    assert summary["demoted"] == 1
    assert cell["alpha_gate"]["scope"] == "strategy"
    assert cell["alpha_gate"]["alpha_coverage_ok"] is False
    assert cell["verdict"] == "CANDIDATE"
    assert "covers 20/500" in " ".join(cell["reasons"])
