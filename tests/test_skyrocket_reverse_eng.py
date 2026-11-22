"""Deterministic tests for the discovery-arm tool.

Every test uses a fixed seed and synthetic rows, so a failure means the
statistics changed, not the dice.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.skyrocket_reverse_eng import (  # noqa: E402
    analyze, bh_adjust, bump_trial_counter, deciles, direction_check, labels,
    load_trial_counter, matched_diff, permutation_p, resolve_objective,
    spearman, wilson,
)


def _rows(n=300, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        pnl = rng.gauss(0, 12)
        rows.append({
            "id": i,
            "symbol": f"S{i}",
            "asset_class": "CRYPTO" if i % 2 else "EQUITY",
            "hold_days": rng.choice([1, 2, 3, 5]),
            "pnl_pct": pnl,
            # predictive: high rvol tends to skyrocket
            "rvol": rng.gauss(1.0, 0.3) + 0.8 * (1 if pnl >= 20 else 0),
            # pure noise, independent of the outcome
            "noise_feat": rng.gauss(0, 1),
        })
    return rows


def test_wilson_bounds_are_sane():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and 0 < hi < 0.4
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and lo > 0.6
    assert wilson(0, 0) == (0.0, 1.0)


def test_labels_skip_missing_values():
    rows = [{"pnl_pct": 25}, {"pnl_pct": 5}, {"pnl_pct": None}, {}]
    assert labels(rows, "pnl_pct", 20) == [1, 0, None, None]


def test_spearman_is_rank_based():
    xs = [1, 2, 3, 4, 5]
    # Invariant to any monotone rescaling of either input.
    assert abs(spearman(xs, [0, 0, 1, 1, 1]) - spearman([10, 20, 30, 40, 50], [0, 0, 1, 1, 1])) < 1e-12
    assert abs(spearman(xs, [1, 2, 3, 4, 5]) - 1.0) < 1e-12


def test_bh_adjust_monotone_and_bounded():
    q = bh_adjust([0.01, 0.04, 0.03, 0.5])
    assert all(0 <= v <= 1 for v in q)
    assert q[0] == min(q)


def test_deciles_cover_all_rows():
    xs = [float(i) for i in range(100)]
    ys = [1 if i > 90 else 0 for i in range(100)]
    dec = deciles(xs, ys)
    assert len(dec) == 10
    assert sum(d["n"] for d in dec) == 100
    assert dec[-1]["rate"] >= dec[0]["rate"]


def test_predictive_feature_is_detected():
    rows = _rows()
    ys = labels(rows, "pnl_pct", 20)
    xs = [r["rvol"] for r in rows]
    assert permutation_p(xs, ys, b=500, seed=0) < 0.05


def test_noise_feature_is_calibrated_across_datasets():
    # The permutation seed does not resample the data — the observed rho is
    # fixed, so re-running one dataset with new seeds tests the same number.
    # Calibration must be measured over independent datasets: an independent
    # feature should cross p<=0.05 at roughly its nominal rate, not always.
    ps = []
    for data_seed in range(20):
        rows = _rows(seed=data_seed)
        ys = labels(rows, "pnl_pct", 20)
        xs = [r["noise_feat"] for r in rows]
        ps.append(permutation_p(xs, ys, b=200, seed=0))
    hits = sum(p <= 0.05 for p in ps)
    assert hits <= 4, f"{hits}/20 significant at 5% — nominal is ~1: {ps}"
    assert sorted(ps)[len(ps) // 2] > 0.15, f"median p too small: {ps}"


def test_matching_removes_a_class_wide_effect():
    # Winners are concentrated in the long-hold stratum where the feature is
    # high for everyone. Within a stratum winners and controls are identical,
    # so the naive winner-vs-rest mean is inflated while the matched one is ~0.
    OFF = [0.0, 0.01, -0.01, 0.02, -0.02]
    rows, ys = [], []

    def add(hold, base, y, k):
        for i in range(k):
            rows.append({"asset_class": "CRYPTO", "hold_days": hold,
                         "feat": base + OFF[i % len(OFF)]})
            ys.append(y)

    add(8, 10.0, 1, 40)   # winners, long holds
    add(8, 10.0, 0, 10)   # controls, long holds
    add(2, 5.0, 1, 10)    # winners, short holds
    add(2, 5.0, 0, 40)    # controls, short holds
    out = matched_diff(rows, ys, "feat", b=400, seed=0)
    assert out is not None
    assert out["naive_diff"] > 2.0, "the class-wide effect should inflate the naive mean"
    assert abs(out["matched_diff"]) < 0.2
    assert out["cancels_zero"], f"matched CI {out['ci']} should cover zero"


def test_objective_prefers_net_over_gross():
    rows = [{"pnl_pct": 1.0, "pnl_net_pct": 0.5}]
    field, note = resolve_objective(rows, "pnl_pct")
    assert field == "pnl_net_pct"
    assert "gross" in note


def test_objective_keeps_gross_when_no_net_and_says_so():
    rows = [{"pnl_pct": 1.0}]
    field, note = resolve_objective(rows, "pnl_pct")
    assert field == "pnl_pct"
    assert "cost-checked" in note


def test_objective_does_not_rewrite_an_explicit_net_request():
    rows = [{"pnl_pct": 1.0, "pnl_net_pct": 0.5}]
    assert resolve_objective(rows, "pnl_net_pct") == ("pnl_net_pct", None)


def test_direction_check_flags_disagreeing_signs():
    ok = direction_check(0.2, 0.1, {"matched_diff": 0.05})
    assert ok == "consistent"
    # rho positive but the decile spread negative: one view is measuring a confound
    assert direction_check(0.2, -0.1, {"matched_diff": 0.05}) == "inconsistent"
    # rho positive while both the spread and the matched diff are negative is a
    # real disagreement, not a tie to be broken in rho's favour.
    assert direction_check(0.2, -0.1, {"matched_diff": -0.05}) == "inconsistent"
    assert direction_check(-0.2, -0.1, {"matched_diff": -0.05}) == "consistent"
    assert direction_check(0.2, None, None) == "unknown"


def test_trial_counter_accumulates_across_runs(tmp_path):
    p = str(tmp_path / "trials.json")
    assert load_trial_counter(p) == 0
    assert bump_trial_counter(p, 5) == 5
    assert bump_trial_counter(p, 3) == 8
    assert load_trial_counter(p) == 8


def test_missing_counter_file_is_zero_not_an_error(tmp_path):
    assert load_trial_counter(str(tmp_path / "nope.json")) == 0


def test_analyze_records_why_a_feature_was_skipped():
    # constant feature: many rows, but only one distinct value
    rows = [{"pnl_pct": float(i % 2), "flat": 1.0} for i in range(60)]
    rep = analyze({"picks": rows})
    assert rep["features_skipped"] >= 1
    reasons = {s["feature"]: s["reason"] for s in rep["skipped"]}
    assert "flat" in reasons
    assert "distinct" in reasons["flat"]


def test_analyze_marks_inconclusive_when_nothing_was_testable():
    rows = [{"pnl_pct": float(i % 2), "flat": 1.0} for i in range(60)]
    rep = analyze({"picks": rows})
    assert rep["features_tested"] == 0
    assert rep["inconclusive"] is True


def test_analyze_threads_the_trial_counter(tmp_path):
    p = str(tmp_path / "trials.json")
    rows = [{"pnl_pct": float(i % 2), "f": float(i)} for i in range(60)]
    rep = analyze({"picks": rows}, trial_counter=p)
    assert rep["trials"]["cumulative"] == rep["trials"]["this_run"]
    rep2 = analyze({"picks": rows}, trial_counter=p)
    assert rep2["trials"]["cumulative"] == 2 * rep2["trials"]["this_run"]


def test_analyze_reports_base_rate_and_doctrine():
    rep = analyze(_rows(), "pnl_pct", 20, perm=200, seed=0)
    assert rep["n_rows"] == 300
    assert 0 < rep["event"]["base_rate"] < 1
    assert rep["event"]["n_hit"] <= rep["event"]["n_labelled"]
    lo, hi = rep["event"]["wilson_ci"]
    assert lo <= rep["event"]["base_rate"] <= hi
    assert "discovery only" in rep["doctrine"]
    names = [f["feature"] for f in rep["features"]]
    assert "rvol" in names and "noise_feat" in names
    # sorted by raw p, and every feature carries a q value
    assert [f["p"] for f in rep["features"]] == sorted(f["p"] for f in rep["features"])
    assert all("q" in f for f in rep["features"])
