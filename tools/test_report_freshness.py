#!/usr/bin/env python3
"""Unit tests for the report freshness framework.

Covers:
  - tools/regenerate_stale_reports.py (staleness detection, classification,
    timestamp extraction, dry-run/execute modes)
  - tools/report_freshness_tracker.py (freshness scanning, classification,
    output writing)

These are deterministic, no-network, no-large-fixture tests.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.regenerate_stale_reports import (
    _extract_generated_at as rfr_extract_ts,
    _age_hours,
    _age_days,
    classify_freshness as rfr_classify,
)
from tools.report_freshness_tracker import (
    _extract_generated_at as rft_extract_ts,
    _age_hours as rft_age_hours,
    classify_freshness as rft_classify,
)


# ===========================================================================
# Timestamp extraction — regenerate_stale_reports
# ===========================================================================

class TestExtractTimestampRegenerate:
    """Test _extract_generated_at from regenerate_stale_reports."""

    def test_standard_iso_format(self):
        data = {"generated_at": "2026-05-24T10:00:00+00:00"}
        dt = rfr_extract_ts(data)
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 24

    def test_z_suffix(self):
        data = {"generated_at": "2026-05-24T10:00:00Z"}
        dt = rfr_extract_ts(data)
        assert dt is not None
        assert dt.tzinfo is not None

    def test_utc_variant(self):
        data = {"generated_at_utc": "2026-05-24T10:00:00.123456Z"}
        dt = rfr_extract_ts(data)
        assert dt is not None
        assert dt.year == 2026

    def test_unix_timestamp_int(self):
        data = {"generated_at": 1716541200}
        dt = rfr_extract_ts(data)
        assert dt is not None
        assert dt.tzinfo is not None

    def test_unix_timestamp_float(self):
        data = {"generated_at": 1716541200.5}
        dt = rfr_extract_ts(data)
        assert dt is not None

    def test_missing_field(self):
        data = {"foo": "bar"}
        assert rfr_extract_ts(data) is None

    def test_empty_string(self):
        data = {"generated_at": ""}
        assert rfr_extract_ts(data) is None

    def test_invalid_date_string(self):
        data = {"generated_at": "not-a-date"}
        assert rfr_extract_ts(data) is None

    def test_none_value(self):
        data = {"generated_at": None}
        assert rfr_extract_ts(data) is None


# ===========================================================================
# Timestamp extraction — report_freshness_tracker
# ===========================================================================

class TestExtractTimestampFreshnessTracker:
    """Test _extract_generated_at from report_freshness_tracker."""

    def test_standard_iso(self):
        data = {"generated_at": "2026-05-24T10:00:00+00:00"}
        dt = rft_extract_ts(data)
        assert dt is not None

    def test_timestamp_key(self):
        data = {"timestamp": "2026-05-24T10:00:00Z"}
        dt = rft_extract_ts(data)
        assert dt is not None

    def test_snapshot_ts_key(self):
        data = {"snapshot_ts": 1716541200}
        dt = rft_extract_ts(data)
        assert dt is not None


# ===========================================================================
# Age calculations
# ===========================================================================

class TestAgeCalculations:
    """Test age calculation functions."""

    def test_age_hours_exact(self):
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        past = now - timedelta(hours=6)
        assert abs(_age_hours(past, now) - 6.0) < 0.01

    def test_age_days_exact(self):
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        past = now - timedelta(days=3)
        assert abs(_age_days(past, now) - 3.0) < 0.01

    def test_age_hours_negative_clamped(self):
        """Future timestamps should not produce negative age."""
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        future = now + timedelta(hours=2)
        assert rft_age_hours(future, now) >= 0

    def test_age_hours_large(self):
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        past = now - timedelta(days=74)
        age_d = _age_hours(past, now)
        assert abs(age_d - 74 * 24) < 1


# ===========================================================================
# Freshness classification
# ===========================================================================

class TestFreshnessClassification:
    """Test freshness classification logic."""

    def test_green_under_24h(self):
        assert rfr_classify(0.5, 7) == "GREEN"
        assert rfr_classify(23.9 / 24, 7) == "GREEN"

    def test_yellow_under_7d(self):
        assert rfr_classify(1.0, 7) == "YELLOW"
        assert rfr_classify(6.9, 7) == "YELLOW"

    def test_red_over_7d(self):
        assert rfr_classify(7.0, 7) == "RED"
        assert rfr_classify(34.0, 7) == "RED"
        assert rfr_classify(74.0, 7) == "RED"

    def test_freshness_tracker_green(self):
        assert rft_classify(12.0, 24, 168) == "GREEN"
        assert rft_classify(0.0, 24, 168) == "GREEN"

    def test_freshness_tracker_yellow(self):
        assert rft_classify(48.0, 24, 168) == "YELLOW"
        assert rft_classify(167.9, 24, 168) == "YELLOW"

    def test_freshness_tracker_red(self):
        assert rft_classify(168.0, 24, 168) == "RED"
        assert rft_classify(500.0, 24, 168) == "RED"

    def test_custom_thresholds(self):
        """Custom green/yellow thresholds."""
        assert rft_classify(6.0, 12, 72) == "GREEN"
        assert rft_classify(24.0, 12, 72) == "YELLOW"
        assert rft_classify(96.0, 12, 72) == "RED"


# ===========================================================================
# Registry integrity — regenerate_stale_reports
# ===========================================================================

class TestRegistryIntegrity:
    """Test the generator registry is well-formed."""

    def test_registry_importable(self):
        from tools.regenerate_stale_reports import REGISTRY
        assert isinstance(REGISTRY, dict)
        assert len(REGISTRY) > 0

    def test_all_entries_have_scan_dirs(self):
        from tools.regenerate_stale_reports import REGISTRY
        for name, meta in REGISTRY.items():
            assert "scan_dirs" in meta, f"{name} missing scan_dirs"
            assert isinstance(meta["scan_dirs"], list)
            assert len(meta["scan_dirs"]) > 0

    def test_all_entries_have_freshness_days(self):
        from tools.regenerate_stale_reports import REGISTRY
        for name, meta in REGISTRY.items():
            assert "freshness_days" in meta, f"{name} missing freshness_days"
            assert meta["freshness_days"] > 0

    def test_known_reports_registered(self):
        """Verify the key stale reports from the task are in the registry."""
        from tools.regenerate_stale_reports import REGISTRY
        expected = [
            "health_report.json",
            "qa_report.json",
            "edge_decay_heatmap.json",
            "hourly_asset_class_24h_report.json",
            "hf_quality_report.json",
            "system_concentration.json",
        ]
        for name in expected:
            assert name in REGISTRY, f"{name} not in registry"


# ===========================================================================
# Staleness detection — end-to-end with mocked files
# ===========================================================================

class TestStalenessDetection:
    """Test check_staleness with temporary files."""

    def _make_temp_report(self, tmpdir: Path, filename: str, age_days: float) -> Path:
        """Create a fake JSON report file with a generated_at timestamp."""
        now = datetime.now(timezone.utc)
        gen_at = now - timedelta(days=age_days)
        data = {
            "generated_at": gen_at.isoformat(),
            "data": "test",
        }
        path = tmpdir / filename
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_stale_report_detected(self):
        """A report older than its threshold should be STALE."""
        import importlib
        import tools.regenerate_stale_reports as rfr_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            data_dir.mkdir(parents=True)
            self._make_temp_report(data_dir, "health_report.json", age_days=34)

            original_root = rfr_mod.ROOT
            try:
                importlib.reload(rfr_mod)
                rfr_mod.ROOT = td

                findings = rfr_mod.check_staleness(only="health_report.json")
                assert len(findings) == 1
                assert findings[0]["status"] == "STALE"
                assert findings[0]["age_days"] >= 33  # allow for test runtime
            finally:
                rfr_mod.ROOT = original_root

    def test_fresh_report_not_flagged(self):
        """A recent report should be FRESH."""
        import importlib
        import tools.regenerate_stale_reports as rfr_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            data_dir.mkdir(parents=True)
            self._make_temp_report(data_dir, "health_report.json", age_days=0.5)

            original_root = rfr_mod.ROOT
            try:
                importlib.reload(rfr_mod)
                rfr_mod.ROOT = td

                findings = rfr_mod.check_staleness(only="health_report.json")
                assert len(findings) == 1
                assert findings[0]["status"] == "FRESH"
            finally:
                rfr_mod.ROOT = original_root


# ===========================================================================
# Freshness tracker scan — end-to-end with mocked files
# ===========================================================================

class TestFreshnessTrackerScan:
    """Test report_freshness_tracker scanning."""

    def _make_file(self, parent: Path, name: str, age_hours: float) -> Path:
        now = datetime.now(timezone.utc)
        gen_at = now - timedelta(hours=age_hours)
        data = {"generated_at": gen_at.isoformat(), "content": "x" * 100}
        path = parent / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_scan_classifies_correctly(self):
        """GREEN, YELLOW, RED files should be classified correctly."""
        import importlib
        import tools.report_freshness_tracker as rft_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            data_dir.mkdir(parents=True)

            self._make_file(data_dir, "fresh.json", age_hours=2)
            self._make_file(data_dir, "aging.json", age_hours=72)
            self._make_file(data_dir, "stale.json", age_hours=200)

            original_root = rft_mod.ROOT
            try:
                importlib.reload(rft_mod)
                rft_mod.ROOT = td

                summary = rft_mod.run_tracker(
                    scan_dirs=["audit_dashboard/data"],
                    green_hours=24,
                    yellow_hours=168,
                    output_dir=str(td / "reports"),
                )

                files = summary["files"]
                fresh = [f for f in files if f["file"].endswith("fresh.json")]
                aging = [f for f in files if f["file"].endswith("aging.json")]
                stale = [f for f in files if f["file"].endswith("stale.json")]

                assert len(fresh) == 1
                assert fresh[0]["freshness"] == "GREEN"
                assert len(aging) == 1
                assert aging[0]["freshness"] == "YELLOW"
                assert len(stale) == 1
                assert stale[0]["freshness"] == "RED"
            finally:
                rft_mod.ROOT = original_root

    def test_skips_tiny_files(self):
        """Files smaller than min_size_bytes should be skipped."""
        import importlib
        import tools.report_freshness_tracker as rft_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            data_dir.mkdir(parents=True)

            # Tiny file (< 50 bytes) — should be skipped
            tiny = data_dir / "tiny.json"
            tiny.write_text('{"a":1}', encoding="utf-8")

            # Normal file — should be scanned
            self._make_file(data_dir, "normal.json", age_hours=1)

            original_root = rft_mod.ROOT
            try:
                importlib.reload(rft_mod)
                rft_mod.ROOT = td

                summary = rft_mod.run_tracker(
                    scan_dirs=["audit_dashboard/data"],
                    output_dir=str(td / "reports"),
                )

                file_names = [f["file"] for f in summary["files"]]
                assert not any("tiny.json" in f for f in file_names)
                assert any("normal.json" in f for f in file_names)
            finally:
                rft_mod.ROOT = original_root

    def test_skips_ignored_subdirs(self):
        """Files in SKIP_SUBDIRS should not be scanned."""
        import importlib
        import tools.report_freshness_tracker as rft_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            ai_dir = data_dir / "ai_leaderboard"
            ai_dir.mkdir(parents=True)

            self._make_file(ai_dir, "leaderboard.json", age_hours=1)

            original_root = rft_mod.ROOT
            try:
                importlib.reload(rft_mod)
                rft_mod.ROOT = td

                summary = rft_mod.run_tracker(
                    scan_dirs=["audit_dashboard/data"],
                    output_dir=str(td / "reports"),
                )

                file_names = [f["file"] for f in summary["files"]]
                assert not any("leaderboard.json" in f for f in file_names)
            finally:
                rft_mod.ROOT = original_root

    def test_output_file_written(self):
        """A JSON output file should be written to the reports directory."""
        import importlib
        import tools.report_freshness_tracker as rft_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            data_dir = td / "audit_dashboard" / "data"
            data_dir.mkdir(parents=True)
            self._make_file(data_dir, "test.json", age_hours=1)

            original_root = rft_mod.ROOT
            try:
                importlib.reload(rft_mod)
                rft_mod.ROOT = td

                summary = rft_mod.run_tracker(
                    scan_dirs=["audit_dashboard/data"],
                    output_dir=str(td / "reports"),
                )

                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                output_path = td / "reports" / f"report_freshness_{date_str}.json"
                assert output_path.exists()

                with open(output_path, "r") as f:
                    loaded = json.load(f)
                assert "scan_at" in loaded
                assert "counts" in loaded
                assert "files" in loaded
            finally:
                rft_mod.ROOT = original_root


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_json_file(self):
        """Corrupted JSON should be handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            bad_file = td / "bad.json"
            bad_file.write_text("{invalid json", encoding="utf-8")

            from tools.regenerate_stale_reports import _load_json
            result = _load_json(bad_file)
            assert result is None

    def test_missing_file(self):
        """Non-existent file should return None."""
        from tools.regenerate_stale_reports import _load_json
        assert _load_json(Path("/nonexistent/path/file.json")) is None

    def test_empty_json_object(self):
        """Empty JSON object has no timestamp."""
        data = {}
        assert rfr_extract_ts(data) is None

    def test_nested_generated_at_in_snapshot(self):
        """generated_at nested in snapshot SHOULD be found (common pattern)."""
        data = {"snapshot": {"generated_at": "2026-05-24T10:00:00Z"}}
        dt = rfr_extract_ts(data)
        assert dt is not None
        assert dt.year == 2026

    def test_nested_generated_at_in_snapshot_metadata(self):
        """generated_at nested in snapshot.metadata SHOULD also be found."""
        data = {"snapshot": {"metadata": {"generated_at": "2026-05-24T10:00:00Z"}}}
        dt = rfr_extract_ts(data)
        assert dt is not None

    def test_deeply_nested_random_object(self):
        """generated_at in an arbitrary deep nested object should NOT be found."""
        data = {"some_other_key": {"generated_at": "2026-05-24T10:00:00Z"}}
        assert rfr_extract_ts(data) is None

    def test_classification_boundary_green_yellow(self):
        """Exactly 24h should be YELLOW (not GREEN)."""
        assert rft_classify(24.0, 24, 168) == "YELLOW"

    def test_classification_boundary_yellow_red(self):
        """Exactly 168h (7d) should be RED (not YELLOW)."""
        assert rft_classify(168.0, 24, 168) == "RED"
