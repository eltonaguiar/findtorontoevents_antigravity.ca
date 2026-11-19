"""Deterministic tests for audit3's statistical gates and verdict logic."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    apply_harm_gate,
    apply_persistence_gate,
    benjamini_hochberg,
    binom_sf,
    bootstrap_mean_ci,
    build_report,
    cell_key,
    compute_verdict_churn,
    deflated_sharpe,
    evaluate_cell,
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
    assert len(prev) == 2
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
                   "namespace": "discovery", "verdict": "WEAK"}]}))
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
    equity = evaluate_cell(_timed_rows([0.06] * 100, cost=0.10, ac="EQUITY"), 1,
                           {"asset_class": "EQUITY", "strategy": "s1",
                            "direction": "LONG", "namespace": "discovery"})
    assert equity["materiality_floor_pct"] == 0.05
    # Equity clears the N4 materiality floor (0.06 >= 0.05) but its 0.06% edge
    # is wiped at 2x cost (0.10), so the G9 cost-stress gate caps it one tier.
    assert equity["verdict"] == "CANDIDATE"
