"""Regression test for tiered n-guard in compute_asset_class_health.

Tier-A #3 from reports/audit_unified_implementation_queue_2026_05_04.md.
Charter T2 floor (CLAUDE.md) = n>=100; previously min_stable_n was 50.
"""
from audit_trail.dashboard_generator import compute_asset_class_health


def _row(wins: int, losses: int, *, wr: float, pf: float = 1.5, pnl: float = 0.0):
    return {"wins": wins, "losses": losses, "win_rate": wr, "profit_factor": pf, "pnl": pnl}


def test_n_below_10_is_insufficient_data():
    out = compute_asset_class_health({"FUTURES": _row(2, 0, wr=100.0, pf=99.0)})
    assert out["FUTURES"]["status"] == "insufficient_data"
    assert out["FUTURES"]["resolved_n"] == 2


def test_n_10_to_49_is_thin_sample():
    out = compute_asset_class_health({"BOND": _row(10, 8, wr=55.6, pf=1.72, pnl=10.0)})
    assert out["BOND"]["status"] == "thin_sample"
    assert out["BOND"]["resolved_n"] == 18


def test_n_50_to_99_is_candidate_not_stable():
    """ETF n=87 with PF/WR meeting thresholds should NOT earn 'stable' badge.

    Pre-fix this would have been status='stable' because old min_stable_n=50.
    Post-fix it must be 'candidate' (n below charter T2 floor of 100).
    """
    out = compute_asset_class_health(
        {"ETF": _row(48, 39, wr=55.2, pf=1.24, pnl=12.5)}
    )
    assert out["ETF"]["status"] == "candidate"
    assert out["ETF"]["resolved_n"] == 87
    assert out["ETF"]["min_stable_n"] == 100


def test_n_at_100_with_passing_metrics_is_stable():
    out = compute_asset_class_health(
        {"EQUITY": _row(53, 47, wr=53.0, pf=1.5, pnl=20.0)}
    )
    assert out["EQUITY"]["status"] == "stable"
    assert out["EQUITY"]["resolved_n"] == 100


def test_n_above_floor_with_failing_metrics_is_stressed():
    out = compute_asset_class_health(
        {"FOREX": _row(540, 629, wr=46.4, pf=0.27, pnl=-986.5)}
    )
    assert out["FOREX"]["status"] == "stressed"
    assert out["FOREX"]["resolved_n"] == 1169


def test_thresholds_emitted_in_payload():
    """Dashboard / downstream consumers can read all 3 thresholds."""
    out = compute_asset_class_health({"X": _row(50, 50, wr=50.0, pf=1.0)})
    row = out["X"]
    assert row["min_display_n"] == 10
    assert row["min_candidate_n"] == 50
    assert row["min_stable_n"] == 100
