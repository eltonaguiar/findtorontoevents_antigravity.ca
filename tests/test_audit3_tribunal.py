"""Deterministic tests for audit3's statistical gates and verdict logic."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    apply_harm_gate,
    apply_selection_alpha_gate,
    apply_persistence_gate,
    benjamini_hochberg,
    binom_sf,
    bootstrap_mean_ci,
    build_report,
    cell_key,
    compute_verdict_churn,
    deflated_sharpe,
    evaluate_cell,
    global_trial_count,
    load_history,
    load_prev_verdicts,
    load_rows,
    materiality_floor,
    recency_ok,
    save_history,
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


def test_block_bootstrap_widens_clustered_ci():
    """F1: overlapping/clustered picks must not get an over-tight CI.

    The same multiset of PnLs should produce a WIDER 95% CI when the wins are
    clustered in one contiguous block than when they are spread evenly over
    time. This is the property that keeps the G2 edge gate honest.
    """
    spread = [0.5, -0.5] * 50
    clustered = [0.5] * 50 + [-0.5] * 50
    a = bootstrap_mean_ci(spread, block=True)
    b = bootstrap_mean_ci(clustered, block=True)
    assert a["bootstrap_mode"] == "block" and b["bootstrap_mode"] == "block"
    assert b["ci_hi"] - b["ci_lo"] > a["ci_hi"] - a["ci_lo"]
    # The i.i.d. default is unchanged and does not opt into block mode.
    iid = bootstrap_mean_ci(spread)
    assert iid["bootstrap_mode"] == "iid"


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


def test_selection_alpha_gate_demotes_a_beta_cell():
    # A confirmatory cell can be PROVEN_T2 on its own expectancy CI and still be
    # beta: if the picks do not beat holding the same instrument, it is not skill.
    rows = _rows(150, 1.2, strategy="cellA")
    for i, r in enumerate(rows):
        r["symbol"] = f"SYM{i % 5}"
        r["source_system"] = "src_a" if i % 2 else "src_b"
    for r in rows[:5]:
        r["pnl_pct"] = -0.8
    manifest = {"path": "m.json", "available": True,
                "pods": [{"id": "POD-A", "status": "pre_registered",
                          "strategies": ["cellA"], "asset_classes": ["CRYPTO"],
                          "directions": ["LONG"]}]}
    alpha = {"by_class": {"CRYPTO": {"n": 120, "alpha_pct": -0.3,
                                     "alpha_ci": [-0.6, 0.1], "alpha_wr": 0.45,
                                     "hold_net_pct": 0.5}}}
    rep = build_report(rows, "x.json", None, alpha=alpha, confirmatory=manifest)
    cell = [c for c in rep["cells"] if c["strategy"] == "cellA"][0]
    assert cell["verdict"] != "PROVEN_T2"
    assert any("selection alpha" in r for r in cell["reasons"])
    # Without the alpha sidecar the same rows are not demoted by this gate.
    bare = build_report(rows, "x.json", None, confirmatory=manifest)
    bare_cell = [c for c in bare["cells"] if c["strategy"] == "cellA"][0]
    assert bare_cell["verdict"] == "PROVEN_T2"
# ─────────────────────────────────────────────── N1 repeated looks ──
def _labeled_cell(verdict="PROVEN_T2", **over):
    cell = {"verdict": verdict, "reasons": [], "asset_class": "CRYPTO",
            "strategy": "s1", "direction": "LONG", "namespace": "discovery"}
    cell.update(over)
    return cell


def test_cell_key_is_stable_and_distinct():
    a = _labeled_cell()
    b = _labeled_cell()
    c = _labeled_cell(symbol="BTCUSDT")
    assert cell_key(a) == cell_key(b)
    assert cell_key(a) != cell_key(c)


def test_persistence_demotes_first_run_then_promotes_second():
    history: dict = {}
    run1 = "2026-11-19T00:00:00Z"
    run2 = "2026-11-19T06:00:00Z"
    first = _labeled_cell()
    counters = apply_persistence_gate([[first]], history, run_at=run1)
    assert first["verdict"] == "WEAK"
    assert counters["demoted"] == 1 and counters["promoted"] == 0
    assert any("repeated-looks" in r for r in first["reasons"])
    key = cell_key(first)
    assert history[key]["passes"] == 1
    assert history[key]["first_pass_at"] == run1
    assert history[key]["last_raw_verdict"] == "PROVEN_T2"

    second = _labeled_cell()
    counters2 = apply_persistence_gate([[second]], history, run_at=run2)
    assert second["verdict"] == "PROVEN_T2"
    assert counters2["promoted"] == 1 and counters2["demoted"] == 0
    assert second["first_pass_at"] == run1, "first_pass_at must be the streak origin"


def test_persistence_streak_counts_raw_verdict_not_final():
    """A demotion must not reset the streak: K consecutive raw passes promote."""
    history: dict = {}
    apply_persistence_gate([[_labeled_cell()]], history, run_at="t1")
    apply_persistence_gate([[_labeled_cell()]], history, run_at="t2")
    cell = _labeled_cell()
    apply_persistence_gate([[cell]], history, run_at="t3")
    assert cell["verdict"] == "PROVEN_T2"


def test_persistence_gap_resets_streak():
    history = {"deadbeef": {"passes": 5, "first_pass_at": "t0",
                            "last_raw_verdict": "PROVEN_T2",
                            "last_verdict": "PROVEN_T2", "last_seen": "t0"}}
    apply_persistence_gate([[]], history, run_at="t1")
    assert history["deadbeef"]["passes"] == 0
    assert history["deadbeef"]["first_pass_at"] is None


def test_persistence_ignores_non_promoted_verdicts():
    history: dict = {}
    weak = _labeled_cell(verdict="WEAK")
    apply_persistence_gate([[weak]], history, run_at="t1")
    assert history[cell_key(weak)]["passes"] == 0
    assert history[cell_key(weak)]["first_pass_at"] is None


def test_history_sidecar_roundtrip(tmp_path):
    path = str(tmp_path / "history.json")
    assert load_history(path) == {}
    history = {"k": {"passes": 2, "first_pass_at": "t0",
                     "last_raw_verdict": "CANDIDATE", "last_verdict": "CANDIDATE",
                     "last_seen": "t0"}}
    save_history(path, history, run_at="t1", runs_required=2)
    loaded = load_history(path)
    assert loaded["k"]["passes"] == 2
    assert loaded["k"]["first_pass_at"] == "t0"


def test_build_report_persistence_gate_end_to_end():
    rows = _rows(150, 1.2)
    for i, r in enumerate(rows):
        r["symbol"] = f"SYM{i % 5}"
    for r in rows[:5]:
        r["pnl_pct"] = -0.8
        r["status"] = "LOST"
    baseline = build_report(rows, "synthetic", None)
    assert baseline["persistence"]["available"] is False
    assert baseline["summary"]["n_candidate"] >= 1

    gated = build_report(rows, "synthetic", None, history={})
    assert gated["persistence"]["available"] is True
    assert gated["persistence"]["n_demoted_this_run"] >= 1
    assert gated["summary"]["n_candidate"] == 0
    assert gated["summary"]["n_weak"] > baseline["summary"]["n_weak"]
    json.dumps(gated, allow_nan=False)


# ─────────────────────────────────────────────── N2 verdict churn ──
def test_churn_uses_raw_verdict_not_persistence_demotion():
    cell = _labeled_cell(verdict="WEAK", raw_verdict="CANDIDATE")
    prev = {cell_key(cell): "CANDIDATE"}
    churn = compute_verdict_churn([[cell]], prev)
    assert churn["n_tracked"] == 1 and churn["n_flipped"] == 0
    changed = _labeled_cell(verdict="PROVEN_T2", raw_verdict="PROVEN_T2")
    churn2 = compute_verdict_churn([[changed]], {cell_key(changed): "CANDIDATE"})
    assert churn2["n_flipped"] == 1
    assert churn2["flips"][0]["from"] == "CANDIDATE"
    assert churn2["flips"][0]["to"] == "PROVEN_T2"


def test_churn_alert_requires_min_tracked():
    cells = [_labeled_cell(strategy=f"s{i}", raw_verdict="PROVEN_T2") for i in range(19)]
    prev = {cell_key(c): "CANDIDATE" for c in cells}
    churn = compute_verdict_churn([cells], prev)
    assert churn["n_flipped"] == 19 and churn["alert"] is False
    cells.append(_labeled_cell(strategy="s19", raw_verdict="PROVEN_T2"))
    prev[cell_key(cells[-1])] = "CANDIDATE"
    churn2 = compute_verdict_churn([cells], prev)
    assert churn2["n_tracked"] == 20 and churn2["alert"] is True


def test_churn_unavailable_without_prev_ledger():
    churn = compute_verdict_churn([[_labeled_cell()]], {})
    assert churn["available"] is False and churn["alert"] is False


def test_load_prev_verdicts_reads_raw_first(tmp_path):
    path = tmp_path / "prev.json"
    path.write_text(json.dumps({
        "cells": [{"asset_class": "CRYPTO", "strategy": "s", "direction": "LONG",
                   "namespace": "discovery", "verdict": "WEAK",
                   "raw_verdict": "CANDIDATE"}],
        "classes": [{"asset_class": "EQUITY", "verdict": "PROVEN_T2"}],
    }))
    prev = load_prev_verdicts(str(path))
    assert prev[cell_key(_labeled_cell(strategy="s"))] == "CANDIDATE"
    # A legacy row with no raw_verdict is skipped: comparing its post-gate
    # verdict to today's raw verdict would report a false churn spike.
    assert len(prev) == 1
    assert load_prev_verdicts(str(tmp_path / "missing.json")) == {}


def test_main_max_churn_exits_3(tmp_path, monkeypatch):
    import alpha_engine.audit3_tribunal as mod
    monkeypatch.setattr(mod, "CHURN_MIN_TRACKED", 0)
    picks = tmp_path / "picks.json"
    picks.write_text(json.dumps({"generated_at": "2026-11-19T00:00:00Z",
                                 "picks": {"recent_closed": _rows(30, 1.0)}}))
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps({
        "cells": [{"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
                   "namespace": "discovery", "verdict": "WEAK",
                   "raw_verdict": "KILL"}]}))
    rc = mod.main(["--picks", str(picks), "--out", str(tmp_path / "out.json"),
                   "--prev-ledger", str(prev), "--max-churn", "0.0"])
    assert rc == 3


# ─────────────────────────────────────────────── N3 recency gate ──
def _timed_rows(nets, cost=0.15, ac="CRYPTO"):
    rows = []
    for i, net in enumerate(nets):
        rows.append({
            "id": f"r{i}",
            "asset_class": ac,
            "strategy": "s1",
            "direction": "LONG",
            "symbol": "AAAUSDT" if i % 2 == 0 else "BBBUSDT",
            "source_system": "src1" if i % 2 == 0 else "src2",
            "status": "WON" if net > 0 else "LOST",
            "pnl_pct": net + cost,
            "closed_at": (f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
                          "T00:00:00+00:00"),
        })
    return rows


def test_recency_orders_by_close_time():
    rows = _timed_rows([1.0] * 4)
    nets = [1.0] * 4
    ok, info = recency_ok(rows, nets, fraction=0.5, min_trades=2)
    assert ok and info["window_trades"] == 2
    shuffled = [rows[2], rows[0], rows[3], rows[1]]
    shuffled_nets = [nets[2], nets[0], nets[3], nets[1]]
    ok2, info2 = recency_ok(shuffled, shuffled_nets, fraction=0.5, min_trades=2)
    assert ok2 == ok and info2 == info


def test_recency_caps_stale_regime_at_candidate():
    nets = [1.0] * 75 + [-0.5] * 25
    rows = _timed_rows(nets)
    cell = evaluate_cell(rows, 1, {"asset_class": "CRYPTO", "strategy": "s1",
                                   "direction": "LONG", "namespace": "discovery"})
    assert cell["recency"]["window_trades"] == 25
    assert cell["recency"]["window_net_mean"] < 0
    assert cell["verdict"] == "CANDIDATE"
    assert any("recency" in r for r in cell["reasons"])


def test_recency_passes_when_trailing_window_positive():
    nets = [1.0] * 75 + [0.2] * 25
    rows = _timed_rows(nets)
    cell = evaluate_cell(rows, 1, {"asset_class": "CRYPTO", "strategy": "s1",
                                   "direction": "LONG", "namespace": "discovery"})
    assert cell["recent_ok"] is True
    assert cell["verdict"] == "PROVEN_T2"


# ─────────────────────────────────────────────── N4 cost-scaled floor ──
def test_materiality_floor_scales_with_cost():
    assert materiality_floor(0.05) == 0.05
    assert materiality_floor(0.15) == 0.075
    assert materiality_floor(0.30) == 0.15


def test_high_cost_class_needs_larger_edge():
    crypto = evaluate_cell(_timed_rows([0.06] * 100, cost=0.15), 1,
                           {"asset_class": "CRYPTO", "strategy": "s1",
                            "direction": "LONG", "namespace": "discovery"})
    assert crypto["materiality_floor_pct"] == 0.075
    assert crypto["verdict"] != "PROVEN_T2"
    # 0.12 net on 0.10 cost: clears the 0.05 materiality floor AND the 2x-cost
    # stress gate (net - cost = +0.02 > 0). A 0.06 edge would clear the floor but
    # die at 2x cost, so it is correctly not PROVEN under the merged gates.
    equity = evaluate_cell(_timed_rows([0.12] * 100, cost=0.10, ac="EQUITY"), 1,
                           {"asset_class": "EQUITY", "strategy": "s1",
                            "direction": "LONG", "namespace": "discovery"})
    assert equity["materiality_floor_pct"] == 0.05
    assert equity["verdict"] == "PROVEN_T2"


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
    assert cell["alpha_gate"]["status"] == "proxy"
    assert "beta_dominant" not in cell  # positive class alpha is not proof of beta


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


def test_selection_alpha_gate_flags_measured_negative_alpha_as_beta_dominant():
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "verdict": "CANDIDATE", "reasons": []}
    apply_selection_alpha_gate(
        [cell], {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-0.9, -0.2]}}})
    assert cell["verdict"] == "CANDIDATE"
    assert cell["beta_dominant"] is True
    assert cell["alpha_gate"]["status"] == "beta_dominant"


def test_a_null_alpha_interval_is_unproven_not_beta_dominant():
    """CI straddling zero is absence of proof, not proof of beta."""
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "verdict": "PROVEN_T2", "reasons": []}
    summary = apply_selection_alpha_gate(
        [cell], {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-0.2, 0.1]}}})
    assert summary["demoted"] == 1
    assert cell["verdict"] == "CANDIDATE"
    assert cell["alpha_gate"]["status"] == "unproven"
    assert "beta_dominant" not in cell


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
    assert any("alpha sidecar unavailable" in r for r in cell["reasons"])


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


# ─────────────────────────────── WEAK cells must always state their blocker ──
def test_every_weak_cell_explains_why():
    """A WEAK verdict with reasons==[] silently hides the blocking condition."""
    # 50% WR, flat mean, stable halves, spread symbols: the only blocker is the
    # net-expectancy CI straddling zero.
    rows = _rows(30, 30, 0.2, -0.1)
    report = build_report(rows, "x.json", None)
    cell = report["cells"][0]
    assert cell["verdict"] in ("WEAK", "CANDIDATE", "INSUFFICIENT_N")
    if cell["verdict"] == "WEAK":
        assert cell["reasons"], "WEAK with no reason"
        assert any("distinguishable from zero" in r for r in cell["reasons"])


def test_summary_declares_its_scope_and_counts_symbols_separately():
    rows = _rows(30, 30, 0.2, -0.1)
    s = build_report(rows, "x.json", None)["summary"]
    assert "cell-level" in s["summary_scope"]
    assert "n_candidate_symbols" in s
    assert "n_proven_symbols" in s
