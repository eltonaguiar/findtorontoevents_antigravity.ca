"""
Tests for code review fixes:
- Threshold validation (AssetClassThreshold model matching score_thresholds.json)
- Demotion audit trail (optional - may not exist in all branches)
"""

import pytest
import json
import tempfile
from pathlib import Path
from alpha_engine.validate_thresholds import ThresholdValidator, AssetClassThreshold, validate_and_apply_thresholds

# Demotion audit trail may not exist in all branches
try:
    from alpha_engine.demotion_audit_trail import DemotionAuditTrail
    _HAS_DEMOTION = True
except ImportError:
    _HAS_DEMOTION = False


class TestAssetClassThreshold:
    """Test the AssetClassThreshold model."""

    def test_valid_threshold_config(self):
        """Test that valid threshold config passes."""
        config = AssetClassThreshold(
            threshold=60,
            profit_factor=1.89,
            win_rate=52.3,
            weighted_trades=312.5,
            raw_trades=287,
            asset_class="CRYPTO"
        )
        assert config.asset_class == "CRYPTO"
        assert config.threshold == 60

    def test_negative_profit_factor_rejected(self):
        """Test that negative profit_factor is rejected."""
        with pytest.raises(ValueError):
            AssetClassThreshold(
                threshold=70,
                profit_factor=-1.5,  # Invalid: negative
                win_rate=45.0,
                weighted_trades=50.0,
                raw_trades=40,
                asset_class="FOREX"
            )

    def test_bounds_checking(self):
        """Test that threshold bounds are enforced (0-100)."""
        with pytest.raises(ValueError):
            AssetClassThreshold(
                threshold=-10,  # Invalid: negative
                profit_factor=1.0,
                win_rate=50.0,
                weighted_trades=50.0,
                raw_trades=40,
                asset_class="EQUITY"
            )

        with pytest.raises(ValueError):
            AssetClassThreshold(
                threshold=150,  # Invalid: exceeds 100
                profit_factor=1.0,
                win_rate=50.0,
                weighted_trades=50.0,
                raw_trades=40,
                asset_class="EQUITY"
            )

    def test_zero_threshold_allowed(self):
        """Test that threshold=0 is valid (used for fallback/insufficient data)."""
        config = AssetClassThreshold(
            threshold=0,
            profit_factor=0.0,
            win_rate=0.0,
            weighted_trades=0.0,
            raw_trades=0,
            asset_class="BOND",
            reason="insufficient_data"
        )
        assert config.threshold == 0

    def test_optional_fields(self):
        """Test that weighted_win_pnl, weighted_loss_pnl, and reason are optional."""
        config = AssetClassThreshold(
            threshold=65,
            profit_factor=1.89,
            win_rate=52.3,
            weighted_trades=312.5,
            raw_trades=287,
            asset_class="CRYPTO",
            weighted_win_pnl=125.3,
            weighted_loss_pnl=-66.3
        )
        assert config.weighted_win_pnl == 125.3
        assert config.reason is None


class TestThresholdValidator:
    """Test the ThresholdValidator file-level validation."""

    def test_validator_with_valid_file(self, tmp_path):
        """Test validator loading valid file (matches engine/dynamic_threshold.py output)."""
        thresholds_file = tmp_path / "thresholds.json"
        thresholds_file.write_text(json.dumps({
            "generated_at": "2026-04-15T03:30:00Z",
            "config": {"half_life_days": 30, "lookback_days": 90},
            "total_closed_picks": 3500,
            "asset_class_thresholds": {
                "CRYPTO": {
                    "threshold": 65,
                    "profit_factor": 1.89,
                    "win_rate": 52.3,
                    "weighted_trades": 312.5,
                    "raw_trades": 287,
                    "asset_class": "CRYPTO",
                    "weighted_win_pnl": 125.3,
                    "weighted_loss_pnl": -66.3
                },
                "FOREX": {
                    "threshold": 40,
                    "profit_factor": 0.72,
                    "win_rate": 38.1,
                    "weighted_trades": 45.0,
                    "raw_trades": 38,
                    "asset_class": "FOREX"
                }
            }
        }))

        validator = ThresholdValidator(thresholds_file)
        is_valid, report = validator.validate_file()

        assert is_valid
        assert len(report["thresholds"]) == 2
        assert report["thresholds"]["CRYPTO"]["status"] == "valid"
        assert report["timestamp"] == "2026-04-15T03:30:00Z"

    def test_validator_with_invalid_json(self, tmp_path):
        """Test validator catches invalid JSON."""
        thresholds_file = tmp_path / "broken.json"
        thresholds_file.write_text("{ not valid json")

        validator = ThresholdValidator(thresholds_file)
        is_valid, report = validator.validate_file()

        assert not is_valid
        assert any("Invalid JSON" in err for err in report["errors"])

    def test_validator_with_out_of_bounds(self, tmp_path):
        """Test validator catches out-of-bounds threshold values."""
        thresholds_file = tmp_path / "oob.json"
        thresholds_file.write_text(json.dumps({
            "asset_class_thresholds": {
                "CRYPTO": {
                    "threshold": 200,  # Out of bounds (>100)
                    "profit_factor": 1.5,
                    "win_rate": 52.0,
                    "weighted_trades": 100.0,
                    "raw_trades": 80,
                    "asset_class": "CRYPTO"
                }
            }
        }))

        validator = ThresholdValidator(thresholds_file)
        is_valid, report = validator.validate_file()

        assert not is_valid
        assert any("CRYPTO" in err for err in report["errors"])

    def test_validator_warns_high_threshold(self, tmp_path):
        """Test validator warns when threshold > 80 (too restrictive)."""
        thresholds_file = tmp_path / "high.json"
        thresholds_file.write_text(json.dumps({
            "asset_class_thresholds": {
                "CRYPTO": {
                    "threshold": 90,
                    "profit_factor": 1.5,
                    "win_rate": 52.0,
                    "weighted_trades": 100.0,
                    "raw_trades": 80,
                    "asset_class": "CRYPTO"
                }
            }
        }))

        validator = ThresholdValidator(thresholds_file)
        is_valid, report = validator.validate_file()

        assert is_valid  # Valid but warned
        assert any("very high" in w for w in report["warnings"])

    def test_validator_missing_file(self, tmp_path):
        """Test validator handles missing file."""
        validator = ThresholdValidator(tmp_path / "nonexistent.json")
        is_valid, report = validator.validate_file()

        assert not is_valid
        assert any("not found" in err for err in report["errors"])

    def test_get_threshold_fallback(self, tmp_path):
        """Test get_threshold returns safe default for unknown asset class."""
        thresholds_file = tmp_path / "thresholds.json"
        thresholds_file.write_text(json.dumps({
            "asset_class_thresholds": {
                "CRYPTO": {
                    "threshold": 65,
                    "profit_factor": 1.89,
                    "win_rate": 52.3,
                    "weighted_trades": 312.5,
                    "raw_trades": 287,
                    "asset_class": "CRYPTO"
                }
            }
        }))

        validator = ThresholdValidator(thresholds_file)
        validator.validate_file()

        # Unknown asset class returns safe default
        assert validator.get_threshold("UNKNOWN") == 50.0
        # Known asset class returns its value
        assert validator.get_threshold("CRYPTO") == 65.0


# Only run demotion audit trail tests if the module is available
if _HAS_DEMOTION:
    class TestDemotionAuditTrail:
        """Test demotion audit trail."""

        def test_record_demotion(self, tmp_path):
            """Test recording a demotion."""
            trail = DemotionAuditTrail(tmp_path / "audit.jsonl")

            entry = trail.record_tier_change(
                system_name="super_signals",
                old_tier="PROVEN",
                new_tier="WATCH",
                reason="WR degraded from 68.6% to 50.4%",
                source_data={"wr": 0.504, "pf": 0.77, "n": 119},
                triggered_by="attribution_tracker"
            )

            assert entry["system"] == "super_signals"
            assert entry["old_tier"] == "PROVEN"
            assert entry["new_tier"] == "WATCH"
            assert "data_hash" in entry

        def test_get_system_history(self, tmp_path):
            """Test retrieving system history."""
            trail = DemotionAuditTrail(tmp_path / "audit.jsonl")

            trail.record_tier_change("system_a", "PROVEN", "RELIABLE", "Test 1", {})
            trail.record_tier_change("system_b", "RELIABLE", "WATCH", "Test 2", {})
            trail.record_tier_change("system_a", "RELIABLE", "WATCH", "Test 3", {})

            history_a = trail.get_system_history("system_a")
            assert len(history_a) == 2
            assert history_a[0]["old_tier"] == "PROVEN"
            assert history_a[1]["old_tier"] == "RELIABLE"

        def test_demotion_stats(self, tmp_path):
            """Test demotion statistics."""
            trail = DemotionAuditTrail(tmp_path / "audit.jsonl")

            trail.record_tier_change("sys1", "PROVEN", "RELIABLE", "Demotion", {})
            trail.record_tier_change("sys2", "WATCH", "PROVEN", "Promotion", {})
            trail.record_tier_change("sys1", "RELIABLE", "WATCH", "Demotion", {})

            stats = trail.get_demotion_stats()
            assert stats["total_changes"] == 3
            assert stats["demotions"] == 2
            assert stats["promotions"] == 1
            assert len(stats["systems_affected"]) == 2

        def test_generate_report(self, tmp_path):
            """Test report generation."""
            trail = DemotionAuditTrail(tmp_path / "audit.jsonl")

            trail.record_tier_change("test_system", "PROVEN", "WATCH", "Test reason", {})

            report = trail.generate_report()
            assert "Strategy Tier Change Audit Trail" in report
            assert "Total Changes: 1" in report
            assert "test_system" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
