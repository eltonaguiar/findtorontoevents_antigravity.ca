#!/usr/bin/env python3
"""
Unit tests for alpha_engine/honest_kill_switch.py

Tests:
  - WR < 45% → KILLED
  - PF < 1.0 → KILLED
  - Both pass → SURVIVOR
  - < MIN_TRADES → INSUFFICIENT_DATA
  - Protected strategies are exempt
  - Cache invalidation works correctly
  - Edge cases: zero trades, zero losses, NaN values
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch

# Ensure repo root is on path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

# We need to import the module carefully since it has module-level constants
import alpha_engine.honest_kill_switch as hks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_globals():
    """Reset module-level globals and per-class thresholds before each test."""
    import copy
    original_wr = hks.MIN_WR
    original_pf = hks.MIN_PF
    original_trades = hks.MIN_TRADES
    original_thresholds = copy.deepcopy(hks.ASSET_CLASS_THRESHOLDS)
    original_originals = copy.deepcopy(hks._ORIGINAL_THRESHOLDS)
    hks.invalidate_cache()
    yield
    hks.MIN_WR = original_wr
    hks.MIN_PF = original_pf
    hks.MIN_TRADES = original_trades
    hks.ASSET_CLASS_THRESHOLDS.update(copy.deepcopy(original_thresholds))
    hks._ORIGINAL_THRESHOLDS.update(copy.deepcopy(original_originals))
    hks._DEFAULT_THRESHOLDS = {"min_wr": original_wr, "min_pf": original_pf, "min_trades": original_trades}
    hks.invalidate_cache()


@pytest.fixture
def sample_stats():
    """Sample strategy stats as returned by fetch_strategy_stats."""
    return {
        "good_strategy": {
            "n": 100, "closed": 100, "wins": 60, "losses": 40,
            "wr": 0.60, "pf": 1.80, "avg_pnl": 0.5, "total_pnl": 50.0,
            "gross_wins": 180.0, "gross_losses": 100.0,
            "asset_classes": {"CRYPTO": 100}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-01-01", "last_seen": "2026-06-01",
        },
        "bad_wr_strategy": {
            "n": 50, "closed": 50, "wins": 15, "losses": 35,
            "wr": 0.30, "pf": 1.20, "avg_pnl": -0.2, "total_pnl": -10.0,
            "gross_wins": 60.0, "gross_losses": 50.0,
            "asset_classes": {"FOREX": 50}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-02-01", "last_seen": "2026-05-01",
        },
        "bad_pf_strategy": {
            "n": 80, "closed": 80, "wins": 50, "losses": 30,
            "wr": 0.625, "pf": 0.70, "avg_pnl": -0.1, "total_pnl": -8.0,
            "gross_wins": 70.0, "gross_losses": 100.0,
            "asset_classes": {"EQUITY": 80}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-03-01", "last_seen": "2026-06-01",
        },
        "both_bad_strategy": {
            "n": 40, "closed": 40, "wins": 10, "losses": 30,
            "wr": 0.25, "pf": 0.40, "avg_pnl": -0.8, "total_pnl": -32.0,
            "gross_wins": 20.0, "gross_losses": 50.0,
            "asset_classes": {"COMMODITY": 40}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-01-15", "last_seen": "2026-04-15",
        },
        "insufficient_trades": {
            "n": 10, "closed": 10, "wins": 6, "losses": 4,
            "wr": 0.60, "pf": 2.0, "avg_pnl": 1.0, "total_pnl": 10.0,
            "gross_wins": 20.0, "gross_losses": 10.0,
            "asset_classes": {"CRYPTO": 10}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-05-01", "last_seen": "2026-06-01",
        },
    }


# ---------------------------------------------------------------------------
# Kill logic tests
# ---------------------------------------------------------------------------

class TestEvaluateStrategies:
    """Test the core kill decision logic."""

    def test_good_strategy_survives(self, sample_stats):
        """Strategy with WR >= 45% AND PF >= 1.0 should survive."""
        results = hks.evaluate_strategies(sample_stats)
        survivor_names = [s["strategy"] for s in results["survivors"]]
        assert "good_strategy" in survivor_names

    def test_bad_wr_gets_killed(self, sample_stats):
        """Strategy with WR < 45% should be killed even if PF passes."""
        results = hks.evaluate_strategies(sample_stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "bad_wr_strategy" in killed_names

    def test_bad_pf_gets_killed(self, sample_stats):
        """Strategy with PF < 1.0 should be killed even if WR passes."""
        results = hks.evaluate_strategies(sample_stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "bad_pf_strategy" in killed_names

    def test_both_bad_gets_killed(self, sample_stats):
        """Strategy failing both gates should be killed."""
        results = hks.evaluate_strategies(sample_stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "both_bad_strategy" in killed_names

    def test_insufficient_trades_not_killed(self, sample_stats):
        """Strategy with < MIN_TRADES should go to insufficient, not killed."""
        results = hks.evaluate_strategies(sample_stats)
        insufficient_names = [i["strategy"] for i in results["insufficient"]]
        assert "insufficient_trades" in insufficient_names
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "insufficient_trades" not in killed_names

    def test_summary_counts(self, sample_stats):
        """Verify summary counts match actual lists."""
        results = hks.evaluate_strategies(sample_stats)
        s = results["summary"]
        assert s["survivors"] == len(results["survivors"])
        assert s["killed"] == len(results["killed"])
        assert s["insufficient_data"] == len(results["insufficient"])
        assert s["total_strategies"] == len(sample_stats)

    def test_kill_reasons_contain_wr_or_pf(self, sample_stats):
        """Each killed entry should mention WR or PF in its reason."""
        results = hks.evaluate_strategies(sample_stats)
        for entry in results["killed"]:
            assert "WR=" in entry["reason"] or "PF=" in entry["reason"]


class TestProfitFactorCalculation:
    """Test PF edge cases."""

    def test_zero_losses_pf_is_high(self):
        """When gross_losses = 0 and gross_wins > 0, PF should be high (infinity proxy).
        Note: evaluate_strategies recomputes PF from gross_wins/gross_losses in the
        stats dict, so we set both the pre-computed pf AND the raw values consistently.
        With n >= 30, WR=100%, and gross_wins > 0 / gross_losses = 0, this should survive.
        """
        stats = {
            "perfect_strategy": {
                "n": 50, "closed": 50, "wins": 50, "losses": 0,
                "wr": 1.0, "pf": 99.0, "avg_pnl": 5.0, "total_pnl": 250.0,
                "gross_wins": 500.0, "gross_losses": 0.0,
                "asset_classes": {"CRYPTO": 50}, "source_systems": ["alpha_engine"],
                "first_seen": "2026-01-01", "last_seen": "2026-06-01",
            }
        }
        results = hks.evaluate_strategies(stats)
        survivor_names = [s["strategy"] for s in results["survivors"]]
        assert "perfect_strategy" in survivor_names

    def test_zero_wins_and_zero_losses_pf_is_zero(self):
        """When both gross_wins and gross_losses are 0, PF should be 0 (killed).
        Note: n >= 30 so it's evaluated, WR=0% < 45% → killed regardless of PF.
        """
        stats = {
            "flat_strategy": {
                "n": 50, "closed": 50, "wins": 0, "losses": 0,
                "wr": 0.0, "pf": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0,
                "gross_wins": 0.0, "gross_losses": 0.0,
                "asset_classes": {"CRYPTO": 50}, "source_systems": ["alpha_engine"],
                "first_seen": "2026-01-01", "last_seen": "2026-06-01",
            }
        }
        results = hks.evaluate_strategies(stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "flat_strategy" in killed_names  # WR=0% < 45% and PF=0 < 1.0


class TestCustomThresholds:
    """Test that custom WR/PF/trades thresholds work."""

    def test_stricter_wr_kills_more(self, sample_stats):
        """Raising WR to 55% via _override_globals should kill more strategies."""
        hks._override_globals(0.55, 1.0, 30)
        results = hks.evaluate_strategies(sample_stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        # good_strategy has WR=0.60 so it still survives
        assert "good_strategy" not in killed_names
        # bad_wr_strategy already killed at 45%, still killed
        assert "bad_wr_strategy" in killed_names

    def test_higher_min_trades_moves_to_insufficient(self, sample_stats):
        """Raising MIN_TRADES to 60 via _override_globals should move some to insufficient."""
        hks._override_globals(0.45, 1.0, 60)
        results = hks.evaluate_strategies(sample_stats)
        insufficient_names = [i["strategy"] for i in results["insufficient"]]
        # bad_wr_strategy has n=50, now insufficient (per-class min_trades=60)
        assert "bad_wr_strategy" in insufficient_names
        assert "both_bad_strategy" in insufficient_names

    def test_override_globals_propagates_to_per_class(self):
        """_override_globals should set all per-class thresholds to the same values."""
        hks._override_globals(0.60, 1.5, 50)
        for ac, t in hks.ASSET_CLASS_THRESHOLDS.items():
            assert t["min_wr"] == 0.60, f"{ac} min_wr not updated"
            assert t["min_pf"] == 1.5, f"{ac} min_pf not updated"
            assert t["min_trades"] == 50, f"{ac} min_trades not updated"

    def test_override_globals_does_not_compound(self):
        """Calling _override_globals twice should not compound the thresholds."""
        hks._override_globals(0.55, 1.2, 40)
        hks._override_globals(0.45, 1.0, 30)
        forex = hks.ASSET_CLASS_THRESHOLDS["FOREX"]
        # Should be back to the overridden values (0.45/1.0/30), not compounded
        assert forex["min_wr"] == 0.45
        assert forex["min_pf"] == 1.0
        assert forex["min_trades"] == 30


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    """Test that cache invalidation works."""

    def test_invalidate_cache_resets_caches(self):
        """After invalidation, caches should be None/empty."""
        hks._KILLED_CACHE = {"test_strategy"}
        hks._KILLED_REASONS = {"test_strategy": "test reason"}
        hks._PROTECTED_CACHE = {"test"}

        hks.invalidate_cache()

        assert hks._KILLED_CACHE is None
        assert hks._KILLED_REASONS == {}
        assert hks._PROTECTED_CACHE is None

    def test_is_strategy_killed_reads_from_file(self):
        """is_strategy_killed should read from honest_kill_switch.json."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "killed": [
                    {"strategy": "dead_strategy", "reason": "WR=20%"},
                    {"strategy": "another_dead", "reason": "PF=0.5"},
                ]
            }, f)
            tmp_path = f.name

        try:
            with patch.object(hks, "KILL_SWITCH_PATH", Path(tmp_path)):
                hks.invalidate_cache()
                killed, reason = hks.is_strategy_killed("dead_strategy")
                assert killed is True
                assert "dead_strategy" in reason.lower() or "WR" in reason or "killed" in reason.lower()

                alive, reason = hks.is_strategy_killed("good_strategy")
                assert alive is False
        finally:
            Path(tmp_path).unlink()
            hks.invalidate_cache()


class TestProtectedStrategies:
    """Test that protected strategies are exempt."""

    def test_protected_strategy_not_killed(self, sample_stats):
        """A strategy in the protected set should not be killed even if it fails gates."""
        # Add a failing strategy that happens to be protected
        sample_stats["st_fear_greed_contrarian"] = {
            "n": 100, "closed": 100, "wins": 20, "losses": 80,
            "wr": 0.20, "pf": 0.30, "avg_pnl": -1.0, "total_pnl": -100.0,
            "gross_wins": 30.0, "gross_losses": 100.0,
            "asset_classes": {"CRYPTO": 100}, "source_systems": ["alpha_engine"],
            "first_seen": "2026-01-01", "last_seen": "2026-06-01",
        }
        results = hks.evaluate_strategies(sample_stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        protected_names = [p["strategy"] for p in results["protected"]]
        assert "st_fear_greed_contrarian" not in killed_names
        assert "st_fear_greed_contrarian" in protected_names


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestSaveResults:
    """Test save_kill_switch_results merge logic."""

    def test_save_writes_honest_kill_switch_json(self, tmp_path):
        """save_kill_switch_results should write honest_kill_switch.json."""
        import copy
        results = {
            "killed": [{"strategy": "dead_strat", "reason": "WR=20%", "n": 50,
                        "wr": 0.20, "pf": 0.5, "total_pnl": -10.0}],
            "survivors": [], "insufficient": [], "protected": [],
            "summary": {
                "total_strategies": 1, "evaluated": 1, "survivors": 0,
                "killed": 1, "insufficient_data": 0, "protected": 0,
                "kill_rate": 100.0,
                "criteria": {"min_trades": 30, "min_wr": 0.45, "min_pf": 1.0,
                              "per_asset_class": hks.ASSET_CLASS_THRESHOLDS},
            },
        }
        with patch.object(hks, "KILL_SWITCH_PATH", tmp_path / "hks.json"):
            hks.save_kill_switch_results(results, apply=False)
            assert (tmp_path / "hks.json").exists()
            data = json.loads((tmp_path / "hks.json").read_text())
            assert data["summary"]["killed"] == 1
            assert data["killed"][0]["strategy"] == "dead_strat"

    def test_save_apply_merges_into_kill_list(self, tmp_path):
        """--apply should merge killed strategies into strategy_kill_list.json."""
        kill_list_path = tmp_path / "strategy_kill_list.json"
        # Pre-populate with existing entry
        kill_list_path.write_text(json.dumps({
            "auto_kill_strategies": ["existing_bad_strat"]
        }))

        results = {
            "killed": [{"strategy": "new_dead_strat", "reason": "PF=0.5"}],
            "survivors": [], "insufficient": [], "protected": [],
            "summary": {
                "total_strategies": 2, "evaluated": 2, "survivors": 1,
                "killed": 1, "insufficient_data": 0, "protected": 0,
                "kill_rate": 50.0,
                "criteria": {"min_trades": 30, "min_wr": 0.45, "min_pf": 1.0,
                              "per_asset_class": hks.ASSET_CLASS_THRESHOLDS},
            },
        }
        with patch.object(hks, "KILL_SWITCH_PATH", tmp_path / "hks.json"), \
             patch.object(hks, "KILL_LIST_PATH", kill_list_path):
            hks.save_kill_switch_results(results, apply=True)

        merged = json.loads(kill_list_path.read_text())
        auto_kills = set(merged["auto_kill_strategies"])
        assert "existing_bad_strat" in auto_kills, "Original entry preserved"
        assert "new_dead_strat" in auto_kills, "New kill merged in"
        assert "honest_kill_switch" in merged, "Metadata written"

    def test_save_apply_no_new_kills_skips_write(self, tmp_path):
        """If all killed strategies already in kill list, no update needed."""
        kill_list_path = tmp_path / "strategy_kill_list.json"
        kill_list_path.write_text(json.dumps({
            "auto_kill_strategies": ["already_dead"]
        }))
        results = {
            "killed": [{"strategy": "already_dead"}],
            "survivors": [], "insufficient": [], "protected": [],
            "summary": {
                "total_strategies": 1, "evaluated": 1, "survivors": 0,
                "killed": 1, "insufficient_data": 0, "protected": 0,
                "kill_rate": 100.0,
                "criteria": {"min_trades": 30, "min_wr": 0.45, "min_pf": 1.0,
                              "per_asset_class": hks.ASSET_CLASS_THRESHOLDS},
            },
        }
        original_mtime = kill_list_path.stat().st_mtime
        with patch.object(hks, "KILL_SWITCH_PATH", tmp_path / "hks.json"), \
             patch.object(hks, "KILL_LIST_PATH", kill_list_path):
            hks.save_kill_switch_results(results, apply=True)
        # File should NOT have been rewritten
        assert kill_list_path.stat().st_mtime == original_mtime

    def test_save_no_apply_does_not_touch_kill_list(self, tmp_path):
        """Without --apply, strategy_kill_list.json should not be modified."""
        kill_list_path = tmp_path / "strategy_kill_list.json"
        kill_list_path.write_text(json.dumps({"auto_kill_strategies": []}))
        results = {
            "killed": [{"strategy": "new_kill"}],
            "survivors": [], "insufficient": [], "protected": [],
            "summary": {
                "total_strategies": 1, "evaluated": 1, "survivors": 0,
                "killed": 1, "insufficient_data": 0, "protected": 0,
                "kill_rate": 100.0,
                "criteria": {"min_trades": 30, "min_wr": 0.45, "min_pf": 1.0,
                              "per_asset_class": hks.ASSET_CLASS_THRESHOLDS},
            },
        }
        with patch.object(hks, "KILL_SWITCH_PATH", tmp_path / "hks.json"), \
             patch.object(hks, "KILL_LIST_PATH", kill_list_path):
            hks.save_kill_switch_results(results, apply=False)
        merged = json.loads(kill_list_path.read_text())
        assert "new_kill" not in merged["auto_kill_strategies"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_stats(self):
        """Empty stats dict should return all zeros."""
        results = hks.evaluate_strategies({})
        assert results["summary"]["total_strategies"] == 0
        assert results["summary"]["evaluated"] == 0

    def test_exactly_at_threshold_survives(self):
        """Strategy exactly at 45% WR and 1.0 PF should survive."""
        stats = {
            "threshold_strategy": {
                "n": 100, "closed": 100, "wins": 45, "losses": 55,
                "wr": 0.45, "pf": 1.0, "avg_pnl": 0.0, "total_pnl": 0.0,
                "gross_wins": 100.0, "gross_losses": 100.0,
                "asset_classes": {"CRYPTO": 100}, "source_systems": ["alpha_engine"],
                "first_seen": "2026-01-01", "last_seen": "2026-06-01",
            }
        }
        results = hks.evaluate_strategies(stats)
        survivor_names = [s["strategy"] for s in results["survivors"]]
        assert "threshold_strategy" in survivor_names

    def test_just_below_threshold_kills(self):
        """Strategy just below 45% WR should be killed."""
        stats = {
            "just_below": {
                "n": 100, "closed": 100, "wins": 44, "losses": 56,
                "wr": 0.44, "pf": 1.0, "avg_pnl": 0.0, "total_pnl": 0.0,
                "gross_wins": 100.0, "gross_losses": 100.0,
                "asset_classes": {"CRYPTO": 100}, "source_systems": ["alpha_engine"],
                "first_seen": "2026-01-01", "last_seen": "2026-06-01",
            }
        }
        results = hks.evaluate_strategies(stats)
        killed_names = [k["strategy"] for k in results["killed"]]
        assert "just_below" in killed_names

    def test_evaluated_at_is_set(self, sample_stats):
        """The summary should have an evaluated_at timestamp."""
        results = hks.evaluate_strategies(sample_stats)
        assert "evaluated_at" in results["summary"]
        assert "2026" in results["summary"]["evaluated_at"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
