"""Unit tests for tools/edge_filter_engine_v3.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from edge_filter_engine_v3 import (
    compute_filter_metrics,
    compute_concentration_risk,
    kelly_position_size,
    simulate_balance_kelly,
    apply_filter,
    walk_forward_split,
)


# ── compute_filter_metrics ──

def test_compute_filter_metrics_empty():
    m = compute_filter_metrics([])
    assert m["n"] == 0
    assert m["wr"] == 0.0
    assert m["pf"] == 0.0
    assert m["expectancy"] == 0.0


def test_compute_filter_metrics_all_wins():
    picks = [{"status": "WON", "pnl_pct": 2.0} for _ in range(5)]
    m = compute_filter_metrics(picks)
    assert m["n"] == 5
    assert m["wr"] == 1.0
    assert m["pf"] == 99.99
    assert m["total_pnl"] == pytest.approx(10.0)
    assert m["avg_win"] == pytest.approx(2.0)
    assert m["avg_loss"] == 0.0


def test_compute_filter_metrics_all_losses():
    picks = [{"status": "LOST", "pnl_pct": -1.5} for _ in range(4)]
    m = compute_filter_metrics(picks)
    assert m["n"] == 4
    assert m["wr"] == 0.0
    assert m["pf"] == 0.0
    assert m["avg_loss"] == pytest.approx(1.5)


def test_compute_filter_metrics_mixed():
    picks = [
        {"status": "WON", "pnl_pct": 3.0},
        {"status": "WON", "pnl_pct": 2.0},
        {"status": "LOST", "pnl_pct": -1.0},
        {"status": "LOST", "pnl_pct": -2.0},
    ]
    m = compute_filter_metrics(picks)
    assert m["n"] == 4
    assert m["wr"] == 0.5
    # gross_win = 5.0, gross_loss = 3.0
    assert m["pf"] == pytest.approx(5.0 / 3.0)
    assert m["total_pnl"] == pytest.approx(2.0)
    assert m["avg_pnl"] == pytest.approx(0.5)
    assert m["avg_win"] == pytest.approx(2.5)
    assert m["avg_loss"] == pytest.approx(1.5)
    # expectancy = (0.5 * 2.5) - (0.5 * 1.5) = 0.5
    assert m["expectancy"] == pytest.approx(0.5)


# ── kelly_position_size ──

def test_kelly_zero_avg_loss():
    assert kelly_position_size(0.6, 2.0, 0.0) == 0.0


def test_kelly_capped_at_10pct():
    # Very high edge should cap at 10%
    size = kelly_position_size(0.9, 5.0, 1.0, fraction=0.25)
    assert size == pytest.approx(0.10)


def test_kelly_negative():
    # Negative kelly -> 0
    size = kelly_position_size(0.3, 1.0, 2.0, fraction=0.25)
    assert size == 0.0


def test_kelly_standard():
    # wr=0.6, avg_win=2.0, avg_loss=1.0
    # r = 2.0, kelly = 0.6 - (0.4/2.0) = 0.4
    # fraction 0.25 -> 0.10
    size = kelly_position_size(0.6, 2.0, 1.0, fraction=0.25)
    assert size == pytest.approx(0.10)


def test_kelly_half_fraction():
    # wr=0.55, avg_win=1.5, avg_loss=1.0
    # r = 1.5, kelly = 0.55 - (0.45/1.5) = 0.55 - 0.30 = 0.25
    # fraction 0.25 -> 0.0625
    size = kelly_position_size(0.55, 1.5, 1.0, fraction=0.25)
    assert size == pytest.approx(0.0625)


# ── simulate_balance_kelly ──

def test_simulate_empty():
    sim = simulate_balance_kelly([], kelly_pct=0.10, initial=10000.0)
    assert sim["final_balance"] == pytest.approx(10000.0)
    assert sim["total_return_pct"] == pytest.approx(0.0)
    assert sim["max_drawdown_pct"] == pytest.approx(0.0)


def test_simulate_all_wins():
    picks = [{"pnl_pct": 5.0} for _ in range(10)]
    sim = simulate_balance_kelly(picks, kelly_pct=0.10, initial=10000.0)
    # Each trade: balance *= 1 + 0.10 * 0.05 = 1.005
    expected = 10000.0 * (1.005 ** 10)
    assert sim["final_balance"] == pytest.approx(expected, rel=1e-6)
    assert sim["max_drawdown_pct"] == pytest.approx(0.0)


def test_simulate_all_losses():
    picks = [{"pnl_pct": -5.0} for _ in range(10)]
    sim = simulate_balance_kelly(picks, kelly_pct=0.10, initial=10000.0)
    expected = 10000.0 * (0.995 ** 10)
    assert sim["final_balance"] == pytest.approx(expected, rel=1e-6)
    # Max DD should be significant
    assert sim["max_drawdown_pct"] > 0.0


def test_simulate_mixed():
    picks = [
        {"pnl_pct": 10.0},
        {"pnl_pct": -5.0},
        {"pnl_pct": 8.0},
        {"pnl_pct": -12.0},
    ]
    sim = simulate_balance_kelly(picks, kelly_pct=0.10, initial=10000.0)
    # Manually compute
    b = 10000.0
    b *= 1.01  # 10000 * 1.01 = 10100
    b *= 0.995  # 10100 * 0.995 = 10049.5
    b *= 1.008  # 10049.5 * 1.008 = 10129.896
    b *= 0.988  # 10129.896 * 0.988 = 10008.337
    assert sim["final_balance"] == pytest.approx(b, rel=1e-4)
    assert sim["max_drawdown_pct"] > 0.0


# ── apply_filter ──

def test_apply_filter_direction():
    picks = [
        {"direction": "LONG", "score": 50},
        {"direction": "SHORT", "score": 50},
        {"direction": "LONG", "score": 30},
    ]
    result = apply_filter(picks, {"direction": "LONG"})
    assert len(result) == 2
    assert all(p["direction"] == "LONG" for p in result)


def test_apply_filter_strategies_whitelist():
    picks = [
        {"strategy": "a", "score": 50},
        {"strategy": "b", "score": 50},
        {"strategy": "c", "score": 50},
    ]
    result = apply_filter(picks, {"strategies": ["a", "c"]})
    assert len(result) == 2
    assert result[0]["strategy"] == "a"
    assert result[1]["strategy"] == "c"


def test_apply_filter_strategies_blacklist():
    picks = [
        {"strategy": "toxic", "score": 50},
        {"strategy": "good", "score": 50},
        {"strategy": "toxic", "score": 60},
    ]
    result = apply_filter(picks, {"exclude_strategies": ["toxic"]})
    assert len(result) == 1
    assert result[0]["strategy"] == "good"


def test_apply_filter_score():
    picks = [
        {"score": 40},
        {"score": 55},
        {"score": 60},
    ]
    result = apply_filter(picks, {"min_score": 55})
    assert len(result) == 2
    assert all(p["score"] >= 55 for p in result)


def test_apply_filter_elite_score():
    picks = [
        {"elite_score": 40},
        {"elite_score": 55},
        {"elite_score": None},
    ]
    result = apply_filter(picks, {"min_elite_score": 50})
    assert len(result) == 1
    assert result[0]["elite_score"] == 55


def test_apply_filter_confidence():
    picks = [
        {"confidence": 0.5},
        {"confidence": 0.7},
        {"confidence": 0.9},
    ]
    result = apply_filter(picks, {"min_confidence": 0.7})
    assert len(result) == 2


def test_apply_filter_grade():
    picks = [
        {"grade": "A"},
        {"grade": "B"},
        {"grade": "C"},
    ]
    result = apply_filter(picks, {"grade": "B"})
    assert len(result) == 1
    assert result[0]["grade"] == "B"


def test_apply_filter_combined():
    picks = [
        {"direction": "LONG", "strategy": "a", "score": 60, "confidence": 0.8},
        {"direction": "LONG", "strategy": "b", "score": 60, "confidence": 0.5},
        {"direction": "SHORT", "strategy": "a", "score": 60, "confidence": 0.8},
    ]
    result = apply_filter(picks, {
        "direction": "LONG",
        "strategies": ["a"],
        "min_score": 55,
        "min_confidence": 0.7,
    })
    assert len(result) == 1
    assert result[0]["direction"] == "LONG"


# ── walk_forward_split ──

def test_walk_forward_empty():
    is_picks, oos_picks = walk_forward_split([], days=30)
    assert is_picks == []
    assert oos_picks == []


def test_walk_forward_no_timestamp():
    picks = [{"id": "a"}, {"id": "b"}]
    is_picks, oos_picks = walk_forward_split(picks, days=30)
    assert len(is_picks) == 2
    assert len(oos_picks) == 0


def test_walk_forward_split():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=5)
    old = now - timedelta(days=60)
    picks = [
        {"timestamp": recent.isoformat().replace("+00:00", "Z")},
        {"timestamp": old.isoformat().replace("+00:00", "Z")},
    ]
    is_picks, oos_picks = walk_forward_split(picks, days=30)
    assert len(is_picks) == 1
    assert len(oos_picks) == 1
    assert is_picks[0]["timestamp"] == old.isoformat().replace("+00:00", "Z")
    assert oos_picks[0]["timestamp"] == recent.isoformat().replace("+00:00", "Z")


# ── compute_concentration_risk ──

def test_concentration_empty():
    conc = compute_concentration_risk([])
    assert conc["max_strategy_share"] == 0.0
    assert conc["top_strategy_name"] is None
    assert conc["hhi"] == 0.0
    assert conc["warning"] is None


def test_concentration_single_strategy():
    picks = [{"strategy": "a"} for _ in range(10)]
    conc = compute_concentration_risk(picks)
    assert conc["max_strategy_share"] == 1.0
    assert conc["top_strategy_name"] == "a"
    assert conc["hhi"] == pytest.approx(1.0)
    assert conc["warning"] is not None
    assert "dominates" in conc["warning"]


def test_concentration_balanced():
    picks = [{"strategy": "a"} for _ in range(5)] + [{"strategy": "b"} for _ in range(5)]
    conc = compute_concentration_risk(picks)
    assert conc["max_strategy_share"] == 0.5
    assert conc["top_strategy_name"] in ("a", "b")
    assert conc["hhi"] == pytest.approx(0.5)
    # 50% share triggers warning (>40%)
    assert conc["warning"] is not None


def test_concentration_low_risk():
    picks = [{"strategy": f"s{i}"} for i in range(10)]
    conc = compute_concentration_risk(picks)
    assert conc["max_strategy_share"] == 0.1
    assert conc["hhi"] == pytest.approx(0.1)
    assert conc["warning"] is None


def test_concentration_hhi_warning():
    # 4 strategies, one at 35%, rest split — HHI should be below 0.25 so no warning from HHI
    picks = [{"strategy": "a"} for _ in range(35)]
    picks += [{"strategy": "b"} for _ in range(35)]
    picks += [{"strategy": "c"} for _ in range(20)]
    picks += [{"strategy": "d"} for _ in range(10)]
    conc = compute_concentration_risk(picks)
    assert conc["max_strategy_share"] == pytest.approx(0.35)
    # max share is 35% (<40%), so warning should be None if HHI <=0.25
    hhi = (0.35 ** 2) + (0.35 ** 2) + (0.20 ** 2) + (0.10 ** 2)
    assert conc["hhi"] == pytest.approx(hhi, rel=1e-5)
    # HHI = 0.1225 + 0.1225 + 0.04 + 0.01 = 0.295 > 0.25, so HHI warning should fire
    assert conc["warning"] is not None
    assert "HHI" in conc["warning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
