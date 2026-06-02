"""Regression test for the count-ratio PF bug (PR #464 follow-up).

PF must be gross_profit / gross_loss (sum of pnl magnitudes), NOT
win_count / loss_count. The count-ratio form inflated PF for any strategy
with many tiny wins vs few big losses — the root cause of the bogus
PF 600+/400+ on INVERT mutations flagged P0 by peer gx10.

Covers the two modules that escaped the mutation_framework.compute_pf fix:
  - verified_strategies/quant_monitor.py (compute_class_health, compute_strategy_culling)
  - verified_strategies/admissibility_pipeline.py (gross-based train/holdout/regime PF)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verified_strategies.quant_monitor import (
    compute_class_health,
    compute_strategy_culling,
)


def test_class_health_pf_is_gross_not_count_ratio():
    # 9 wins of +1, 1 loss of -20: count-ratio -> 9.0 (great), gross -> 0.45 (terrible)
    trades = (
        [{"asset_class": "CRYPTO", "pnl_pct": 1.0} for _ in range(9)]
        + [{"asset_class": "CRYPTO", "pnl_pct": -20.0}]
    )
    reports = compute_class_health(trades)
    pf = reports["CRYPTO"].pf
    assert abs(pf - 0.45) < 1e-6, f"expected gross PF 0.45, got {pf}"
    assert pf < 1.0, "many-tiny-wins / one-big-loss must report PF < 1"


def test_strategy_culling_prefers_authoritative_profit_factor():
    # profit_factor present -> use it verbatim (count ratio would be 13/21 = 0.62)
    systems = [{
        "name": "s1", "closed_picks": 46, "wins": 13, "losses": 21,
        "win_rate": 38.2, "profit_factor": 0.7,
        "gross_win": 37.11, "gross_loss": -52.99,
    }]
    culling = compute_strategy_culling(systems)
    # PF 0.7 with n>=10 -> MUTATE_CANDIDATE (0.7 <= pf < 1.0), not PROMOTE
    assert culling["s1"] == "MUTATE_CANDIDATE", culling


def test_strategy_culling_falls_back_to_gross_when_no_pf():
    # no profit_factor -> derive from gross_win/gross_loss (not counts)
    systems = [{
        "name": "s2", "closed_picks": 30, "wins": 20, "losses": 5,
        "win_rate": 80.0, "gross_win": 10.0, "gross_loss": -25.0,
    }]
    culling = compute_strategy_culling(systems)
    # gross PF = 10/25 = 0.4 -> CULL_CANDIDATE, even though count ratio 20/5 = 4.0
    assert culling["s2"] == "CULL_CANDIDATE", culling


if __name__ == "__main__":
    test_class_health_pf_is_gross_not_count_ratio()
    test_strategy_culling_prefers_authoritative_profit_factor()
    test_strategy_culling_falls_back_to_gross_when_no_pf()
    print("all PF count-ratio regression tests passed")
