import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_cost_headroom import headroom  # noqa: E402


def test_headroom_is_the_ci_low_distance_to_break_even():
    # net_ci_pct low = -0.699 means the CI itself is below zero: no headroom.
    assert headroom({"net_ci_pct": [-0.699, -0.1602],
                     "pf_cost_pct": 0.0994})["headroom_pct"] == 0.0


def test_positive_ci_reports_distance_from_zero():
    out = headroom({"net_ci_pct": [0.25, 0.60], "pf_cost_pct": 0.0994})
    assert out["headroom_pct"] == 0.25


def test_cost_is_reported_alongside_headroom():
    out = headroom({"net_ci_pct": [0.25, 0.60], "pf_cost_pct": 0.0994})
    assert out["cost_pct"] == 0.0994
    assert out["cost_exceeds_headroom"] is False


def test_cost_exceeding_headroom_is_flagged():
    out = headroom({"net_ci_pct": [0.02, 0.30], "pf_cost_pct": 0.0994})
    assert out["cost_exceeds_headroom"] is True
