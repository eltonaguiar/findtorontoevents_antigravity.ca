"""Tests for FeatureFlagManager.

Uses tmp_path to provide real JSON files — no open() mocks needed,
so no risk of shadowing builtin imports.
"""

import json
import time
from pathlib import Path

import pytest

from alpha_engine.feature_flags import FeatureFlagManager


# ── helpers ─────────────────────────────────────────────────────────

SAMPLE_FLAGS = {
    "enable_non_crypto_hf": False,
    "goldmine_score_floor_enabled": False,
    "quarantine_enabled": False,
    "structured_logging_enabled": True,
    "policy_version": "v3-2026-04-10",
    "last_policy_change_at": "2026-04-10T03:08:00+08:00",
}


def _write_flags(tmp_path: Path, data: dict | None = None) -> Path:
    p = tmp_path / "feature_flags.json"
    p.write_text(json.dumps(data or SAMPLE_FLAGS))
    return p


# ── construction ────────────────────────────────────────────────────

class TestInit:
    def test_loads_flags(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        assert mgr.is_enabled("quarantine_enabled") is False
        assert mgr.is_enabled("structured_logging_enabled") is True

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FeatureFlagManager(tmp_path / "nope.json")

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json}")
        with pytest.raises(ValueError):
            FeatureFlagManager(p)


# ── is_enabled ──────────────────────────────────────────────────────

class TestIsEnabled:
    def test_bool_flag_true(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.is_enabled("structured_logging_enabled") is True

    def test_bool_flag_false(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.is_enabled("quarantine_enabled") is False

    def test_missing_flag_returns_false(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.is_enabled("nonexistent_flag") is False

    def test_string_flag_is_truthy(self, tmp_path):
        """Non-empty string values are truthy in Python — is_enabled returns True."""
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.is_enabled("policy_version") is True
        # But get() returns the actual string
        assert mgr.get("policy_version") == "v3-2026-04-10"


# ── get ─────────────────────────────────────────────────────────────

class TestGet:
    def test_returns_value(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.get("policy_version") == "v3-2026-04-10"

    def test_returns_default_for_missing(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.get("nope", 42) == 42

    def test_default_default_is_none(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        assert mgr.get("nope") is None


# ── set_flag ────────────────────────────────────────────────────────

class TestSetFlag:
    def test_updates_existing(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        mgr.set_flag("quarantine_enabled", True)
        assert mgr.is_enabled("quarantine_enabled") is True
        # persisted to disk
        assert json.loads(p.read_text())["quarantine_enabled"] is True

    def test_creates_new_flag(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        mgr.set_flag("brand_new_flag", True)
        assert mgr.is_enabled("brand_new_flag") is True


# ── list_flags ──────────────────────────────────────────────────────

class TestListFlags:
    def test_returns_all_flags(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        flags = mgr.list_flags()
        assert set(flags.keys()) == set(SAMPLE_FLAGS.keys())

    def test_returns_copy(self, tmp_path):
        mgr = FeatureFlagManager(_write_flags(tmp_path))
        flags = mgr.list_flags()
        flags["quarantine_enabled"] = True
        assert mgr.is_enabled("quarantine_enabled") is False  # internal state unchanged


# ── reload (mtime-based) ───────────────────────────────────────────

class TestReload:
    def test_reload_picks_up_external_change(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        assert mgr.is_enabled("quarantine_enabled") is False

        # Simulate external writer: modify file on disk
        data = {**SAMPLE_FLAGS, "quarantine_enabled": True}
        time.sleep(0.05)  # ensure mtime differs
        p.write_text(json.dumps(data))

        changed = mgr.reload()
        assert changed is True
        assert mgr.is_enabled("quarantine_enabled") is True

    def test_reload_noop_when_unchanged(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        changed = mgr.reload()
        assert changed is False

    def test_reload_catches_content_change_same_second(self, tmp_path):
        """If mtime might be identical but content differs, content hash fallback kicks in."""
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)

        # Write different content (mtime may equal due to coarse granularity)
        data = {**SAMPLE_FLAGS, "quarantine_enabled": True}
        p.write_text(json.dumps(data))

        # Force mtime to be the same as before (simulate same-second write)
        import os
        old_stat = os.stat(p)
        os.utime(p, (old_stat.st_atime, old_stat.st_mtime))

        changed = mgr.reload()
        assert changed is True
        assert mgr.is_enabled("quarantine_enabled") is True


# ── diff ────────────────────────────────────────────────────────────

class TestDiff:
    def test_detects_added(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)

        data = {**SAMPLE_FLAGS, "new_flag": True}
        p.write_text(json.dumps(data))
        result = mgr.diff()
        assert "new_flag" in result["added"]

    def test_detects_removed(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)

        data = {k: v for k, v in SAMPLE_FLAGS.items() if k != "quarantine_enabled"}
        p.write_text(json.dumps(data))
        result = mgr.diff()
        assert "quarantine_enabled" in result["removed"]

    def test_detects_changed(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)

        data = {**SAMPLE_FLAGS, "quarantine_enabled": True}
        p.write_text(json.dumps(data))
        result = mgr.diff()
        assert "quarantine_enabled" in result["changed"]

    def test_no_changes(self, tmp_path):
        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        result = mgr.diff()
        assert result == {"added": [], "removed": [], "changed": []}


# ── thread safety ───────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_reads(self, tmp_path):
        """Multiple reader threads should all get consistent snapshots."""
        import threading

        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        results = []
        barrier = threading.Barrier(10)

        def reader():
            barrier.wait()
            for _ in range(50):
                results.append(mgr.is_enabled("quarantine_enabled"))

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should see False (no writer thread)
        assert all(r is False for r in results)
        assert len(results) == 500

    def test_concurrent_write_and_read(self, tmp_path):
        """Writer + readers: readers never see partial/corrupt state."""
        import threading

        p = _write_flags(tmp_path)
        mgr = FeatureFlagManager(p)
        errors = []

        def writer():
            for val in [True, False, True, False]:
                time.sleep(0.01)
                mgr.set_flag("quarantine_enabled", val)

        def reader():
            for _ in range(20):
                try:
                    v = mgr.is_enabled("quarantine_enabled")
                    assert isinstance(v, bool)
                except Exception as e:
                    errors.append(e)

        wt = threading.Thread(target=writer)
        rts = [threading.Thread(target=reader) for _ in range(5)]
        wt.start()
        for t in rts:
            t.start()
        wt.join()
        for t in rts:
            t.join()

        assert errors == []
