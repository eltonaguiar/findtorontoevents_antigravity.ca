"""Tests for health_check.

Uses tmp_path + real FeatureFlagManager to avoid open() mock conflicts.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from alpha_engine.feature_flags import FeatureFlagManager
from alpha_engine.health_check import HealthChecker, DEFAULT_MAX_LAG_HOURS


# ── helpers ─────────────────────────────────────────────────────────

TZ_PLUS_8 = timezone(timedelta(hours=8))


def _recent_ts() -> str:
    return datetime.now(TZ_PLUS_8).isoformat()


def _old_ts(hours: int = 48) -> str:
    return (datetime.now(TZ_PLUS_8) - timedelta(hours=hours)).isoformat()


def _make_flags(tmp_path: Path, **overrides) -> Path:
    data = {
        "enable_non_crypto_hf": False,
        "goldmine_score_floor_enabled": False,
        "direction_penalty_regime_aware": False,
        "dynamic_non_crypto_cap_enabled": False,
        "statistical_kill_enabled": False,
        "quarantine_enabled": False,
        "structured_logging_enabled": False,
        "concentration_alerts_enabled": False,
        "asset_class_composite_enabled": False,
        "big_mover_monitor_enabled": False,
        "data_lag_monitor_enabled": False,
        "health_check_enabled": False,
        "policy_version": "v3-2026-04-10",
        "last_policy_change_at": "2026-04-10T03:08:00+08:00",
    }
    data.update(overrides)
    p = tmp_path / "feature_flags.json"
    p.write_text(json.dumps(data))
    return p


# ── basic health check ─────────────────────────────────────────────

class TestHealthCheck:
    def test_returns_expected_keys(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert "status" in result
        assert "policy_version" in result
        assert "last_policy_change_at" in result
        assert "active_flags" in result
        assert "payload_lag_hours" in result
        assert "last_check" in result

    def test_status_healthy_no_flags(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert result["status"] == "healthy"

    def test_policy_version_matches(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert result["policy_version"] == "v3-2026-04-10"

    def test_active_flags_empty_when_all_disabled(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        # Only meta keys should be present, no real flags active
        assert result["active_flags"] == []

    def test_active_flags_lists_enabled(self, tmp_path):
        p = _make_flags(tmp_path, quarantine_enabled=True, structured_logging_enabled=True)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert "quarantine_enabled" in result["active_flags"]
        assert "structured_logging_enabled" in result["active_flags"]
        assert len(result["active_flags"]) == 2

    def test_last_check_is_iso_timestamp(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        # Should parse without error
        datetime.fromisoformat(result["last_check"])


# ── payload lag ─────────────────────────────────────────────────────

class TestPayloadLag:
    def test_lag_is_none_when_no_callback(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert result["payload_lag_hours"] is None

    def test_lag_from_callback(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr, payload_lag_provider=lambda: 2.5)
        result = checker.check()
        assert result["payload_lag_hours"] == 2.5

    def test_lag_callback_exception(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr, payload_lag_provider=lambda: 1 / 0)
        result = checker.check()
        assert result["payload_lag_hours"] is None


# ── status determination ───────────────────────────────────────────

class TestStatusDetermination:
    def test_degraded_when_many_flags_on(self, tmp_path):
        p = _make_flags(tmp_path,
            quarantine_enabled=True,
            statistical_kill_enabled=True,
            big_mover_monitor_enabled=True,
        )
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert result["status"] == "degraded"

    def test_unhealthy_when_lag_excessive(self, tmp_path):
        p = _make_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr, payload_lag_provider=lambda: 48.0)
        result = checker.check()
        assert result["status"] == "unhealthy"

    def test_healthy_with_one_flag(self, tmp_path):
        p = _make_flags(tmp_path, structured_logging_enabled=True)
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr)
        result = checker.check()
        assert result["status"] == "healthy"

    def test_unhealthy_overrides_degraded(self, tmp_path):
        """If both many flags AND high lag, unhealthy wins."""
        p = _make_flags(tmp_path,
            quarantine_enabled=True,
            statistical_kill_enabled=True,
            big_mover_monitor_enabled=True,
        )
        mgr = FeatureFlagManager(p)
        checker = HealthChecker(mgr, payload_lag_provider=lambda: 100.0)
        result = checker.check()
        assert result["status"] == "unhealthy"
