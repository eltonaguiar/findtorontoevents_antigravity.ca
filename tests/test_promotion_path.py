"""ENHANCEMENT #66 — unified promotion path + two-scoreboard drift detector."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import promotion_path as pp  # noqa: E402


def test_reconcile_agrees_within_tolerance():
    r = pp.reconcile_scoreboards("deepseek_v4", tournament_pf=1.10, production_pf=1.00)
    assert r["ok"] is True
    assert r["divergence"] <= pp.SCOREBOARD_PF_TOLERANCE


def test_reconcile_flags_two_scoreboard_drift():
    # tournament PF 3.46 vs production 0.92 = the real EAGLE2 deepseek_v4 split
    r = pp.reconcile_scoreboards("deepseek_v4", tournament_pf=3.46, production_pf=0.92)
    assert r["ok"] is False
    assert r["promotable_on_tournament"] is False
    assert "production board only" in r["note"]


def test_reconcile_missing_side_is_none():
    r = pp.reconcile_scoreboards("x", tournament_pf=2.0, production_pf=None)
    assert r["ok"] is None


def test_batch_reconcile_counts_drift():
    pairs = [
        {"sleeve": "a", "tournament_pf": 3.46, "production_pf": 0.92},  # drift
        {"sleeve": "b", "tournament_pf": 1.05, "production_pf": 1.00},  # ok
        {"sleeve": "c", "tournament_pf": 3.14, "production_pf": 0.90},  # drift
    ]
    out = pp.batch_reconcile(pairs)
    assert out["n"] == 3
    assert out["n_drift"] == 2
    assert set(out["drifting_sleeves"]) == {"a", "c"}


def test_canonical_cost_model_is_single_source():
    cm = pp.canonical_cost_model("CRYPTO")
    assert cm.slippage_bps == 10 and cm.commission_bps == 10
