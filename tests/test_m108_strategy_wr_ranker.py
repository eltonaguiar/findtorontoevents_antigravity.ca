"""Tests for alpha_engine/strategy_wr_ranker.py (M-108)."""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.strategy_wr_ranker import (
    compute_strategy_rolling_wr,
    enrich_picks_with_strategy_wr,
    compute_rank_score,
    rank_picks,
    _wr_weight_for_n,
    MIN_N,
)


def _closed_pick(strategy: str, won: bool, ac: str = "COMMODITY") -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "strategy": strategy,
        "status": "WIN" if won else "LOSS",
        "pnl_pct": 0.02 if won else -0.01,
        "closed_at": ts,
        "asset_class": ac,
    }


def _make_closed(strategy: str, n_win: int, n_loss: int, ac: str = "COMMODITY") -> list:
    return (
        [_closed_pick(strategy, True, ac) for _ in range(n_win)]
        + [_closed_pick(strategy, False, ac) for _ in range(n_loss)]
    )


class TestComputeStrategyRollingWr:
    def test_high_wr_strategy(self):
        picks = _make_closed("cot_positioning", 78, 22)  # ~78% WR
        result = compute_strategy_rolling_wr(picks, min_n=MIN_N)
        assert "cot_positioning" in result
        assert abs(result["cot_positioning"]["wr"] - 0.78) < 0.01
        assert result["cot_positioning"]["n"] == 100

    def test_below_min_n_excluded(self):
        picks = _make_closed("rare_strategy", 5, 2)  # n=7 < MIN_N=10
        result = compute_strategy_rolling_wr(picks, min_n=10)
        assert "rare_strategy" not in result

    def test_multiple_strategies(self):
        picks = (
            _make_closed("strat_a", 80, 20)
            + _make_closed("strat_b", 30, 70)
        )
        result = compute_strategy_rolling_wr(picks, min_n=10)
        assert "strat_a" in result and "strat_b" in result
        assert result["strat_a"]["wr"] > result["strat_b"]["wr"]

    def test_empty_picks_returns_empty(self):
        result = compute_strategy_rolling_wr([], min_n=10)
        assert result == {}

    def test_win_loss_status_variants(self):
        ts = datetime.now(timezone.utc).isoformat()
        picks = [
            {"strategy": "s", "status": "WON", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "LOST", "pnl_pct": -0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "WIN", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "LOSS", "pnl_pct": -0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "TARGET_HIT", "pnl_pct": 0.02, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "STOPPED", "pnl_pct": -0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "WIN", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "WIN", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "WIN", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
            {"strategy": "s", "status": "WIN", "pnl_pct": 0.01, "closed_at": ts, "asset_class": "EQUITY"},
        ]
        result = compute_strategy_rolling_wr(picks, min_n=10)
        assert "s" in result
        assert result["s"]["n"] == 10


class TestEnrichPicks:
    def test_strategy_wr_added_when_sufficient_history(self):
        closed = _make_closed("cot_positioning", 40, 10)
        lookup = compute_strategy_rolling_wr(closed, min_n=10)
        picks = [{"strategy": "cot_positioning", "symbol": "CT=F"}]
        enrich_picks_with_strategy_wr(picks, lookup)
        assert picks[0]["strategy_rolling_wr"] is not None
        assert picks[0]["strategy_rolling_n"] == 50

    def test_none_when_insufficient_history(self):
        lookup = {}  # no strategies known
        picks = [{"strategy": "unknown_strat", "symbol": "X"}]
        enrich_picks_with_strategy_wr(picks, lookup)
        assert picks[0]["strategy_rolling_wr"] is None
        assert picks[0]["strategy_rolling_n"] == 0

    def test_multiple_picks_enriched(self):
        closed = _make_closed("s_a", 30, 10) + _make_closed("s_b", 10, 30)
        lookup = compute_strategy_rolling_wr(closed, min_n=10)
        picks = [
            {"strategy": "s_a", "symbol": "A"},
            {"strategy": "s_b", "symbol": "B"},
            {"strategy": "unknown", "symbol": "C"},
        ]
        enrich_picks_with_strategy_wr(picks, lookup)
        assert picks[0]["strategy_rolling_wr"] > picks[1]["strategy_rolling_wr"]
        assert picks[2]["strategy_rolling_wr"] is None


class TestWrWeightForN:
    def test_full_weight_at_n_ge_30(self):
        assert abs(_wr_weight_for_n(30) - 0.70) < 1e-6
        assert abs(_wr_weight_for_n(100) - 0.70) < 1e-6

    def test_min_weight_at_min_n(self):
        # At n=MIN_N (10), weight = 0.50
        assert abs(_wr_weight_for_n(MIN_N) - 0.50) < 1e-6

    def test_linear_ramp(self):
        # At n=20 (midpoint of 10-30): weight = 0.60
        assert abs(_wr_weight_for_n(20) - 0.60) < 1e-6

    def test_weight_bounded(self):
        # n < MIN_N is not a valid input (guarded by compute_rank_score); test valid range only
        for n in [MIN_N, 15, 20, 25, 30, 50, 200]:
            w = _wr_weight_for_n(n)
            assert 0.50 <= w <= 0.70


class TestComputeRankScore:
    def test_high_wr_strategy_ranks_higher(self):
        p_high = {
            "strategy_rolling_wr": 0.78,
            "strategy_rolling_n": 50,
            "ml_composite_score": 0.6,
        }
        p_low = {
            "strategy_rolling_wr": 0.35,
            "strategy_rolling_n": 50,
            "ml_composite_score": 0.6,
        }
        assert compute_rank_score(p_high) > compute_rank_score(p_low)

    def test_fallback_when_no_strategy_history(self):
        p = {
            "strategy_rolling_wr": None,
            "strategy_rolling_n": 0,
            "ml_composite_score": 0.7,
            "confidence": 0.8,
        }
        score = compute_rank_score(p)
        # Fallback: 100% ml_composite = 0.7 (confidence removed per v2)
        assert abs(score - 0.7) < 1e-4

    def test_score_clamped_to_0_1(self):
        p = {
            "strategy_rolling_wr": 2.0,   # out of range
            "strategy_rolling_n": 100,
            "ml_composite_score": 5.0,    # out of range
            "confidence": -1.0,           # out of range
        }
        score = compute_rank_score(p)
        assert 0.0 <= score <= 1.0

    def test_dynamic_weight_low_n(self):
        # At n=MIN_N=10, weight is 0.50/0.50 not 0.70/0.30
        p = {
            "strategy_rolling_wr": 1.0,   # max WR
            "strategy_rolling_n": MIN_N,
            "ml_composite_score": 0.0,
        }
        score = compute_rank_score(p)
        # Expected: 0.50 * 1.0 + 0.50 * 0.0 = 0.50
        assert abs(score - 0.50) < 1e-4

    def test_dynamic_weight_full_n(self):
        # At n=30, weight is full 0.70/0.30
        p = {
            "strategy_rolling_wr": 1.0,
            "strategy_rolling_n": 30,
            "ml_composite_score": 0.0,
        }
        score = compute_rank_score(p)
        # Expected: 0.70 * 1.0 + 0.30 * 0.0 = 0.70
        assert abs(score - 0.70) < 1e-4


class TestRankPicks:
    def test_picks_sorted_by_rank_score(self):
        closed = _make_closed("good_strat", 80, 20) + _make_closed("bad_strat", 20, 80)
        lookup = compute_strategy_rolling_wr(closed, min_n=10)
        picks = [
            {"strategy": "bad_strat", "symbol": "B", "elite_score": 90, "confidence": 0.9},
            {"strategy": "good_strat", "symbol": "A", "elite_score": 20, "confidence": 0.3},
        ]
        ranked = rank_picks(picks, lookup)
        # good_strat (WR=80%) should rank above bad_strat (WR=20%) even with lower elite_score
        assert ranked[0]["symbol"] == "A"
        assert ranked[1]["symbol"] == "B"

    def test_m108_rank_score_added(self):
        picks = [{"strategy": "s", "symbol": "X", "confidence": 0.5}]
        rank_picks(picks)
        assert "m108_rank_score" in picks[0]

    def test_empty_picks_safe(self):
        result = rank_picks([])
        assert result == []
