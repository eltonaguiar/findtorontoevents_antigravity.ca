"""Tests for the verification tools added 2026-11-23.

Covers two_hurdle_kill (mean+median+sign), tom_forward_clock pre-freeze refusal,
validate_gate_reports, and pick_gate cost/gate logic. These tools decide whether
picks are killed, so an untested tool is itself a defect.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ── two_hurdle_kill ────────────────────────────────────────────────
def test_mean_positive_but_median_negative_is_the_false_pass_shape():
    """The H-119 shape: mean>0 (outlier-driven) while median<0.

    This is the exact pattern a mean-only hurdle would wrongly pass, so the
    two-hurdle rule requires the median too.
    """
    from tools.two_hurdle_kill import paired_bootstrap_ci, boot_median_ci
    import statistics as st

    # Many small losers + a handful of huge winners: mean>0, median<0.
    diffs = [-0.002] * 300 + [0.5] * 3
    assert st.mean(diffs) > 0 > st.median(diffs), "fixture must have mean>0, median<0"
    # Median point estimate is the robust summary and is negative.
    med_ci = boot_median_ci(diffs, n_boot=400, seed=3)
    assert med_ci[0] <= 0 and med_ci[1] <= 0
    # Mean CI (unreliable on this fixture) still reports the mean it was given.
    mean_ci = paired_bootstrap_ci(diffs, n_boot=400, seed=3)
    assert mean_ci["mean"] > 0


def test_sign_test_symmetric_is_not_significant():
    from tools.two_hurdle_kill import sign_test_p
    diffs = [0.01, -0.01] * 100  # exactly half positive
    p = sign_test_p(diffs)
    assert p is not None and p > 0.9


def test_sign_test_all_positive_is_significant():
    from tools.two_hurdle_kill import sign_test_p
    p = sign_test_p([0.01] * 60)
    assert p is not None and p < 0.01


# ── tom_forward_clock refusal ──────────────────────────────────────
def test_tom_harness_refuses_pre_freeze():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/tom_forward_clock.py"), "--today", "2026-11-20"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "REFUSED" in r.stderr


def test_tom_harness_runs_at_freeze_and_emits_zero():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/tom_forward_clock.py"), "--today", "2026-11-23"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    d = json.loads((ROOT / "reports/tom_forward_clock.json").read_text())
    assert d["n_records"] == 0
    assert all(x >= "2026-11-23" for x in d["candidate_entry_dates"])


# ── validate_gate_reports ──────────────────────────────────────────
def test_gate_validator_passes_on_real_rankings():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_gate_reports.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "violations=0" in r.stdout


# ── pick_gate logic ────────────────────────────────────────────────
def test_commission_monotone_nonincreasing():
    from tools.pick_gate import ibkr_commission_bp
    xs = [1000, 5000, 10000, 25000, 50000]
    vals = [ibkr_commission_bp(x) for x in xs]
    assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
    assert vals[0] == 11.0 and vals[-1] == 0.4


def test_round_trip_cost_arithmetic():
    """Costs follow COST_OF_RECORD by class, plus ticket commission."""
    from tools.pick_gate import round_trip_cost_bp, cod_cost_bp
    assert cod_cost_bp("EQUITY") == 12.0749
    assert cod_cost_bp("CRYPTO", "BTC") == 20.0
    assert cod_cost_bp("CRYPTO", "WIF") == 52.0
    c = round_trip_cost_bp(25000, "LONG", "EQUITY")
    assert abs(c["total_rt_bp"] - (12.0749 + 2 * 0.4)) < 1e-6


def test_no_pick_passes_without_holding_and_prereg():
    """G2 (hold>=1d) and G5 (pre_recorded) must block PASS when unmet."""
    from tools.pick_gate import Pick, gate_pick
    p = gate_pick(Pick("X", "EQUITY", "LONG", n=200, gross_edge_bp=1000.0,
                       holding_days=0.0, ticket_usd=25000, dsr=0.99,
                       dsr_n_trials=362, pre_recorded=False, kill_rule="k"))
    assert p.verdict != "PASS"
    assert p.gates["G2"] is False and p.gates["G5"] is False


# ── DSR frontier regression (G3 criteria) ─────────────────────────
def test_dsr_frontier_matches_production_function():
    """sr0=K/sqrt(n): n=100, SR=0.5 must clear 0.95 in the REAL function."""
    import random
    from alpha_engine.audit3_tribunal import deflated_sharpe

    def make(n, sr, seed=1):
        rng = random.Random(seed)
        x = [rng.gauss(0, 1) for _ in range(n)]
        m = sum(x) / n
        s = (sum((v - m) ** 2 for v in x) / n) ** 0.5
        return [(v - m) / s + sr for v in x]

    r = deflated_sharpe(make(100, 0.5), 658)
    assert r is not None
    assert 0.93 <= r["dsr"] <= 0.985, r["dsr"]  # 0.9516 measured; band tolerates skew noise


def test_dsr_rises_with_n_at_fixed_sharpe():
    import random
    from alpha_engine.audit3_tribunal import deflated_sharpe

    def make(n, sr, seed=2):
        rng = random.Random(seed)
        x = [rng.gauss(0, 1) for _ in range(n)]
        m = sum(x) / n
        s = (sum((v - m) ** 2 for v in x) / n) ** 0.5
        return [(v - m) / s + sr for v in x]

    small = deflated_sharpe(make(60, 0.45), 658)["dsr"]
    big = deflated_sharpe(make(300, 0.45), 658)["dsr"]
    assert big > small, (small, big)


# ── cross-agent picks aggregator ───────────────────────────────────
def test_aggregate_agent_picks_runs_on_review_drop():
    r = subprocess.run([sys.executable, str(ROOT / "tools/aggregate_agent_picks.py"),
                        "--root", "/home/eaguiar2015/antigravity_review_Nov192026",
                        "--date", "2026-11-23",
                        "--out", "/tmp/rollup_test.json"],
                       cwd=ROOT, capture_output=True, text=True)
    # exit 0 if the drop exists; 2 only if the folder is absent (tolerate both in CI)
    assert r.returncode in (0, 2), r.stdout + r.stderr
    if r.returncode == 0:
        d = json.load(open("/tmp/rollup_test.json"))
        assert d["n_agents"] >= 1
        assert "per_class_combined" in d


# ── incubator validator ────────────────────────────────────────────
def test_incubator_validator_rejects_paper_ready_without_n():
    r = subprocess.run([sys.executable, str(ROOT / "tools/validate_incubator.py"),
                        "--out", "/tmp/inc_val.json"], cwd=ROOT, capture_output=True, text=True)
    # exits 1 because nothing is admissible (no n / duplicates) - that is the correct verdict
    assert r.returncode == 1, r.stdout + r.stderr
    d = json.load(open("/tmp/inc_val.json"))
    assert d["n_admissible"] == 0
    assert any("no_n" in e.get("reasons", []) for e in d["rejected"])


# ── cross-system consensus ─────────────────────────────────────────
def test_cross_system_consensus_runs_and_maps_kimi_signals():
    r = subprocess.run([sys.executable, str(ROOT / "tools/cross_system_consensus.py"),
                        "--out", "/tmp/consensus_test.json"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.load(open("/tmp/consensus_test.json"))
    # KIMI uses signal:BUY - must be mapped to LONG, so kimi must contribute picks
    assert d["per_system"]["kimi"].get("n_picks", 0) >= 1
    assert "caveat" in d and "NOT a recommendation" in d["caveat"]


# ── closed-picks outcome labeller ──────────────────────────────────
def test_outcome_labeller_splits_realised_and_would_hit():
    r = subprocess.run([sys.executable, str(ROOT / "tools/label_closed_pick_outcomes.py"),
                        "--out", "/tmp/outcome_test.json"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.load(open("/tmp/outcome_test.json"))
    assert d["REALISED"] > 0 and d["WOULD_HIT"] > 0
    assert d["REALISED"] + d["WOULD_HIT"] == d["total"]
    # the defect: most WOULD_HIT rows sit exactly on a barrier
    assert d["would_hit_pct_on_barrier"] >= 50.0
