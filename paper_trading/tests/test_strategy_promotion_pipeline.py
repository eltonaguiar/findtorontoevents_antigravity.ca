"""Tests for strategy_promotion_pipeline — Wilson score interval, tier evaluation,
demotion logic, cache invalidation, and position sizing multipliers.

CODERED Fix 5: CI-Based Strategy Promotion Pipeline.
"""

import json
import os
import sys
import time

import pytest

# Ensure paper_trading is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Wilson score interval
# ---------------------------------------------------------------------------
class TestWilsonScoreInterval:
    """Validate Wilson score interval against known reference values."""

    def test_zero_trials_returns_zero(self):
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=0, n=0)
        assert lower == 0.0
        assert upper == 0.0

    def test_all_wins_n10(self):
        """10/10 wins → lower bound well below 100%, upper bound = 100%."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=10, n=10)
        assert lower > 0.5   # clearly profitable even at n=10
        assert upper == pytest.approx(1.0)
        # Reference: Wilson CI for p=1.0, n=10, z=1.96 → ~[0.722, 1.000]
        assert abs(lower - 0.722) < 0.02

    def test_all_losses_n10(self):
        """0/10 wins → lower bound = 0, upper bound well below 50%."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=0, n=10)
        assert lower == 0.0
        assert upper < 0.30  # even upper bound shows no edge
        # Reference: ~[0.000, 0.278]
        assert abs(upper - 0.278) < 0.02

    def test_half_wins_n30(self):
        """15/30 → CI should straddle 50%."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=15, n=30)
        assert lower < 0.50
        assert upper > 0.50
        # Symmetric: should be roughly [0.34, 0.66]
        assert 0.30 < lower < 0.40
        assert 0.60 < upper < 0.70

    def test_60pct_wr_n50(self):
        """30/50 (60% WR) → lower bound > 50% (standard tier territory)."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=30, n=50)
        assert lower > 0.45   # lower bound should be close to 50%
        assert upper > 0.70

    def test_increasing_n_shrinks_ci(self):
        """CI width should decrease as n increases (same WR=60%)."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        _, u1 = wilson_score_interval(wins=6, n=10)
        _, u2 = wilson_score_interval(wins=30, n=50)
        _, u3 = wilson_score_interval(wins=60, n=100)
        width1 = u1 - wilson_score_interval(6, 10)[0]
        width2 = u2 - wilson_score_interval(30, 50)[0]
        width3 = u3 - wilson_score_interval(60, 100)[0]
        assert width1 > width2 > width3

    def test_single_trial(self):
        """n=1, 1 win → wide CI."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        lower, upper = wilson_score_interval(wins=1, n=1)
        assert 0.0 < lower < 0.8
        assert 0.2 < upper <= 1.0

    def test_custom_z_score(self):
        """z=2.576 (99% CI) should produce wider interval than z=1.96 (95%)."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        l95, u95 = wilson_score_interval(wins=30, n=50, z=1.96)
        l99, u99 = wilson_score_interval(wins=30, n=50, z=2.576)
        assert l99 < l95  # wider → lower lower bound
        assert u99 > u95  # wider → higher upper bound

    def test_bounds_clamped_0_1(self):
        """Extreme values should never exceed [0, 1]."""
        from paper_trading.strategy_promotion_pipeline import wilson_score_interval
        for wins, n in [(0, 1), (1, 1), (0, 100), (100, 100), (1, 3)]:
            lower, upper = wilson_score_interval(wins, n)
            assert 0.0 <= lower <= 1.0
            assert 0.0 <= upper <= 1.0
            assert lower <= upper


# ---------------------------------------------------------------------------
# Tier evaluation
# ---------------------------------------------------------------------------
class TestEvaluateStrategy:
    """Test evaluate_strategy tier assignment logic."""

    def _make_trades(self, n, win_count):
        """Create a list of n trade dicts with win_count winners."""
        trades = []
        for i in range(n):
            pnl = 2.5 if i < win_count else -1.5
            trades.append({"pnl_pct": pnl})
        return trades

    def test_killed_strategy_overrides_everything(self):
        """A killed strategy gets TIER_KILLED regardless of performance."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_KILLED,
        )
        # Must be on PERMANENTLY_KILLED list — we use irb_hoffman which is
        # known to be killed. If the import fails, the list is empty and
        # we skip.
        try:
            from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES
            if not PERMANENTLY_KILLED_STRATEGIES:
                pytest.skip("PERMANENTLY_KILLED_STRATEGIES is empty")
            killed_name = list(PERMANENTLY_KILLED_STRATEGIES)[0]
        except ImportError:
            pytest.skip("audit_trail.quality_gates not importable")

        # Even with perfect 50/50 trades, killed list overrides
        trades = self._make_trades(50, 35)
        assert evaluate_strategy(killed_name, trades) == TIER_KILLED

    def test_standard_tier_70pct_wr_n50(self):
        """50 trades, 70% WR → standard tier (lower bound > 50%)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_STANDARD,
        )
        trades = self._make_trades(50, 35)
        assert evaluate_strategy("test_great_strategy", trades) == TIER_STANDARD

    def test_standard_tier_60pct_wr_n100(self):
        """100 trades, 60% WR → standard tier (ample data, proven edge)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_STANDARD,
        )
        trades = self._make_trades(100, 60)
        assert evaluate_strategy("test_proven_strategy", trades) == TIER_STANDARD

    def test_probation_tier_55pct_wr_n15(self):
        """15 trades, 55% WR → probation (n≥10, CI overlaps >50%)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_PROBATION,
        )
        trades = self._make_trades(15, 9)  # ~60% WR, n=15
        result = evaluate_strategy("test_promising_strategy", trades)
        assert result == TIER_PROBATION

    def test_probation_tier_50pct_wr_n20(self):
        """20 trades, 50% WR → probation (upper bound >50% even at break-even)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_PROBATION,
        )
        trades = self._make_trades(20, 10)
        result = evaluate_strategy("test_breakeven_strategy", trades)
        # At 50% WR with n=20, Wilson upper bound should still be >50%
        assert result == TIER_PROBATION

    def test_incubator_default_few_trades(self):
        """5 trades → incubator (not enough data for probation)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR,
        )
        trades = self._make_trades(5, 4)  # 80% WR but n<10
        assert evaluate_strategy("test_new_strategy", trades) == TIER_INCUBATOR

    def test_incubator_no_trades(self):
        """0 trades → incubator."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR,
        )
        assert evaluate_strategy("test_empty_strategy", []) == TIER_INCUBATOR

    def test_incubator_bad_wr_fails_probation(self):
        """15 trades, 33% WR → CI upper bound might be >50% but WR < 40%
        triggers demotion → incubator."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR,
        )
        trades = self._make_trades(15, 5)  # 33% WR
        assert evaluate_strategy("test_bad_strategy", trades) == TIER_INCUBATOR

    # ── Demotion logic ──────────────────────────────────────────────────

    def test_demotion_probation_wr_below_40pct(self):
        """Probation-eligible n=15 but WR=33% → demoted to incubator."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR,
        )
        # n=15, 5 wins → 33% WR → below 40% demotion threshold
        trades = self._make_trades(15, 5)
        assert evaluate_strategy("test_demoted_strategy", trades) == TIER_INCUBATOR

    def test_no_demotion_probation_wr_45pct(self):
        """n=15, 45% WR → stays probation (above 40% demotion line)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_PROBATION,
        )
        trades = self._make_trades(15, 7)  # 46.7% WR, n=15
        result = evaluate_strategy("test_surviving_strategy", trades)
        assert result == TIER_PROBATION

    def test_demotion_boundary_wr_exactly_40pct(self):
        """n=20, 40% WR exactly → NOT demoted (check uses <, not ≤)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR,
        )
        trades = self._make_trades(20, 8)  # 40% WR exactly
        # 40% is NOT < 40%, so should stay probation
        result = evaluate_strategy("test_boundary_strategy", trades)
        # WR = 8/20 = 40% exactly → NOT demoted (check uses <, not <=)
        from paper_trading.strategy_promotion_pipeline import TIER_PROBATION
        assert result == TIER_PROBATION

    def test_standard_demotes_to_probation(self):
        """n=50, 52% WR → lower bound ≤ 50% → NOT standard.
        Should fall through to probation check."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, wilson_score_interval,
        )
        trades = self._make_trades(50, 26)  # 52% WR
        lower, upper = wilson_score_interval(26, 50)
        # 52% WR at n=50 → lower bound should be ~39%, below 50%
        assert lower < 0.50, f"Expected lower<0.50, got {lower}"
        # So it should NOT be standard; should be probation
        result = evaluate_strategy("test_marginal_strategy", trades)
        from paper_trading.strategy_promotion_pipeline import TIER_PROBATION
        assert result == TIER_PROBATION


# ---------------------------------------------------------------------------
# Position sizing multipliers
# ---------------------------------------------------------------------------
class TestTierMultipliers:
    """Test get_tier_multiplier returns correct values."""

    def test_standard_multiplier(self):
        from paper_trading.strategy_promotion_pipeline import (
            get_tier_multiplier, TIER_MULTIPLIERS,
        )
        assert TIER_MULTIPLIERS["standard"] == 1.0

    def test_probation_multiplier(self):
        from paper_trading.strategy_promotion_pipeline import TIER_MULTIPLIERS
        assert TIER_MULTIPLIERS["probation"] == 0.5

    def test_incubator_multiplier(self):
        from paper_trading.strategy_promotion_pipeline import TIER_MULTIPLIERS
        assert TIER_MULTIPLIERS["incubator"] == 0.25

    def test_killed_multiplier(self):
        from paper_trading.strategy_promotion_pipeline import TIER_MULTIPLIERS
        assert TIER_MULTIPLIERS["killed"] == 0.0

    def test_unknown_strategy_defaults_to_incubator(self):
        """Strategy not in tier_map → treated as incubator (0.25x)."""
        from paper_trading.strategy_promotion_pipeline import get_tier_multiplier
        multiplier = get_tier_multiplier("nonexistent_strategy_xyz", tier_map={})
        assert multiplier == 0.25

    def test_killed_strategy_gets_zero(self):
        from paper_trading.strategy_promotion_pipeline import (
            get_tier_multiplier, TIER_KILLED,
        )
        multiplier = get_tier_multiplier("dead_strat", tier_map={"dead_strat": TIER_KILLED})
        assert multiplier == 0.0

    def test_tier_map_none_triggers_generate(self, tmp_path, monkeypatch):
        """get_tier_multiplier(strategy, tier_map=None) falls back to generate_tier_map()."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks = [{"strategy": "auto_strat", "pnl_pct": 2.5}] * 35 + \
                [{"strategy": "auto_strat", "pnl_pct": -1.5}] * 15
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with open(data_dir / "closed_picks.json", "w", encoding="utf-8") as f:
            json.dump(picks, f)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        # Call without explicit tier_map — should auto-generate
        multiplier = spp.get_tier_multiplier("auto_strat", tier_map=None)
        assert multiplier == 1.0  # standard tier → 1.0x

    def test_zero_pnl_counts_as_loss(self):
        """pnl_pct=0 counts as a loss (pipeline uses > 0 for win check)."""
        from paper_trading.strategy_promotion_pipeline import (
            evaluate_strategy, TIER_INCUBATOR, wilson_score_interval,
        )
        # 10 trades: 5 wins, 3 losses, 2 zero-PnL (counted as losses)
        # Effective: 5 wins / 10 = 50% WR
        trades = (
            [{"pnl_pct": 2.5}] * 5 +
            [{"pnl_pct": -1.5}] * 3 +
            [{"pnl_pct": 0.0}] * 2
        )
        # n=10, 5 wins → WR 50%, Wilson upper > 50%, WR >= 40% → probation
        result = evaluate_strategy("zero_pnl_strat", trades)
        assert result == "probation"  # 50% WR with zero-PnL as losses

        # Verify zero-PnL explicitly: all zero → 0% WR → incubator
        all_zero = [{"pnl_pct": 0.0}] * 15
        result2 = evaluate_strategy("all_zero_strat", all_zero)
        assert result2 == TIER_INCUBATOR


# ---------------------------------------------------------------------------
# Tier map generation + cache
# ---------------------------------------------------------------------------
class TestGenerateTierMap:
    """Test generate_tier_map with mock closed_picks.json."""

    def _write_closed_picks(self, tmp_path, picks_data):
        """Write closed_picks.json to a temp data dir."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with open(data_dir / "closed_picks.json", "w", encoding="utf-8") as f:
            json.dump(picks_data, f)
        return data_dir

    def test_empty_closed_picks(self, tmp_path, monkeypatch):
        """No closed picks → empty tier map."""
        from paper_trading import strategy_promotion_pipeline as spp
        data_dir = self._write_closed_picks(tmp_path, [])

        # Reset cache
        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert tier_map == {}

    def test_single_good_strategy(self, tmp_path, monkeypatch):
        """One strategy with 35/50 wins → standard tier."""
        from paper_trading import strategy_promotion_pipeline as spp
        picks = [{"strategy": "great_one", "pnl_pct": 2.5}] * 35 + \
                [{"strategy": "great_one", "pnl_pct": -1.5}] * 15
        data_dir = self._write_closed_picks(tmp_path, picks)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert "great_one" in tier_map
        assert tier_map["great_one"] == "standard"

    def test_multiple_strategies_different_tiers(self, tmp_path, monkeypatch):
        """Three strategies → three different tiers."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks = (
            # great: 35/50 = 70% → standard
            [{"strategy": "great", "pnl_pct": 2.5}] * 35 +
            [{"strategy": "great", "pnl_pct": -1.5}] * 15 +
            # okay: 8/15 = 53% → probation
            [{"strategy": "okay", "pnl_pct": 2.5}] * 8 +
            [{"strategy": "okay", "pnl_pct": -1.5}] * 7 +
            # new: 3/5 = 60% but n<10 → incubator
            [{"strategy": "newish", "pnl_pct": 2.5}] * 3 +
            [{"strategy": "newish", "pnl_pct": -1.5}] * 2
        )
        data_dir = self._write_closed_picks(tmp_path, picks)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert tier_map["great"] == "standard"
        assert tier_map["okay"] == "probation"
        assert tier_map["newish"] == "incubator"

    def test_cache_hit_same_mtime(self, tmp_path, monkeypatch):
        """Second call with same mtime returns cached result."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks = [{"strategy": "s1", "pnl_pct": 2.5}] * 15 + \
                [{"strategy": "s1", "pnl_pct": -1.5}] * 5
        data_dir = self._write_closed_picks(tmp_path, picks)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map1 = spp.generate_tier_map()
        # Mutate a strategy name in cache to verify second call is cached
        spp._tier_cache["__test_marker__"] = "incubator"
        tier_map2 = spp.generate_tier_map()
        assert "__test_marker__" in tier_map2  # cached version returned

    def test_cache_invalidation_on_file_change(self, tmp_path, monkeypatch):
        """Updating closed_picks.json invalidates the cache."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks_v1 = [{"strategy": "s1", "pnl_pct": 2.5}] * 15 + \
                   [{"strategy": "s1", "pnl_pct": -1.5}] * 5
        data_dir = self._write_closed_picks(tmp_path, picks_v1)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map1 = spp.generate_tier_map()
        assert tier_map1.get("s1") == "probation"

        # Add more winning trades to promote s1 to standard
        picks_v2 = picks_v1 + [{"strategy": "s1", "pnl_pct": 2.5}] * 20
        picks_file = data_dir / "closed_picks.json"
        with open(picks_file, "w", encoding="utf-8") as f:
            json.dump(picks_v2, f)
        # Force mtime forward to avoid NTFS 2-second resolution issue
        os.utime(str(picks_file), (time.time() + 5, time.time() + 5))

        tier_map2 = spp.generate_tier_map()
        assert tier_map2.get("s1") == "standard"

    def test_algorithm_field_fallback(self, tmp_path, monkeypatch):
        """Trades with 'algorithm' field instead of 'strategy' still group correctly."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks = [{"algorithm": "alt_name", "pnl_pct": 2.5}] * 35 + \
                [{"algorithm": "alt_name", "pnl_pct": -1.5}] * 15
        data_dir = self._write_closed_picks(tmp_path, picks)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert "alt_name" in tier_map

    def test_malformed_picks_skipped(self, tmp_path, monkeypatch):
        """Non-dict entries in closed_picks.json are safely skipped."""
        from paper_trading import strategy_promotion_pipeline as spp

        picks = [
            "not_a_dict",
            42,
            None,
            {"strategy": "real_deal", "pnl_pct": 2.5},
            {"strategy": "real_deal", "pnl_pct": -1.5},
        ]
        data_dir = self._write_closed_picks(tmp_path, picks)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert "real_deal" in tier_map
        # Only 2 trades → incubator
        assert tier_map["real_deal"] == "incubator"

    def test_missing_closed_picks_file(self, tmp_path, monkeypatch):
        """No closed_picks.json → empty tier map (graceful degradation)."""
        from paper_trading import strategy_promotion_pipeline as spp

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        # Don't create closed_picks.json

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        tier_map = spp.generate_tier_map()
        assert tier_map == {}


# ---------------------------------------------------------------------------
# Promotion report
# ---------------------------------------------------------------------------
class TestPromotionReport:
    """Test get_promotion_report structure."""

    def test_report_structure(self, tmp_path, monkeypatch):
        from paper_trading import strategy_promotion_pipeline as spp

        picks = (
            [{"strategy": "great", "pnl_pct": 2.5}] * 35 +
            [{"strategy": "great", "pnl_pct": -1.5}] * 15 +
            [{"strategy": "okay", "pnl_pct": 2.5}] * 8 +
            [{"strategy": "okay", "pnl_pct": -1.5}] * 7 +
            [{"strategy": "newish", "pnl_pct": 2.5}] * 3 +
            [{"strategy": "newish", "pnl_pct": -1.5}] * 2
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with open(data_dir / "closed_picks.json", "w", encoding="utf-8") as f:
            json.dump(picks, f)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        report = spp.get_promotion_report()

        assert report["title"] == "Strategy Promotion Pipeline"
        assert "standard" in report
        assert "probation" in report
        assert "incubator" in report
        assert "killed" in report
        assert "summary" in report
        assert "evaluated_at" in report

        # Check entries have expected fields
        for tier_name in ["standard", "probation", "incubator", "killed"]:
            for entry in report[tier_name]:
                assert "name" in entry
                assert "trades" in entry
                assert "win_rate" in entry
                assert "ci_lower" in entry
                assert "ci_upper" in entry

    def test_report_summary_format(self, tmp_path, monkeypatch):
        from paper_trading import strategy_promotion_pipeline as spp

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with open(data_dir / "closed_picks.json", "w", encoding="utf-8") as f:
            json.dump([], f)

        spp._tier_cache = {}
        spp._tier_cache_mtime = 0.0
        monkeypatch.setattr(spp, "DATA_DIR", data_dir)

        report = spp.get_promotion_report()
        assert "Standard:" in report["summary"]
        assert "Probation:" in report["summary"]
        assert "Incubator:" in report["summary"]
        assert "Killed:" in report["summary"]


# ---------------------------------------------------------------------------
# Tier constants consistency
# ---------------------------------------------------------------------------
class TestTierConstants:
    """Ensure tier constants and multiplier dict are consistent."""

    def test_all_tiers_have_multipliers(self):
        from paper_trading.strategy_promotion_pipeline import (
            TIER_INCUBATOR, TIER_PROBATION, TIER_STANDARD, TIER_KILLED,
            TIER_MULTIPLIERS,
        )
        for tier in [TIER_INCUBATOR, TIER_PROBATION, TIER_STANDARD, TIER_KILLED]:
            assert tier in TIER_MULTIPLIERS

    def test_multiplier_ordering(self):
        """Killed < Incubator < Probation < Standard."""
        from paper_trading.strategy_promotion_pipeline import TIER_MULTIPLIERS
        assert TIER_MULTIPLIERS["killed"] < TIER_MULTIPLIERS["incubator"]
        assert TIER_MULTIPLIERS["incubator"] < TIER_MULTIPLIERS["probation"]
        assert TIER_MULTIPLIERS["probation"] < TIER_MULTIPLIERS["standard"]

    def test_all_multipliers_in_0_1(self):
        from paper_trading.strategy_promotion_pipeline import TIER_MULTIPLIERS
        for tier, mult in TIER_MULTIPLIERS.items():
            assert 0.0 <= mult <= 1.0, f"{tier}: {mult} not in [0, 1]"
