"""Tests for tools/source_liveness_watchdog.py (B12).

Verifies:
1. _count_picks() handles all known JSON pick-array schemas.
2. check_sources() flags stale files and missing files correctly.
3. Row-count drop detection works vs a previous snapshot.
4. Report writing creates both dated + latest files.
5. main() always returns 0 (warn-only, never raises).
6. load_previous_snapshot() returns None when no prior run exists.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from tools.source_liveness_watchdog import (
    _count_picks,
    check_sources,
    load_previous_snapshot,
    main,
    write_report,
)


# ── 1. _count_picks() ──────────────────────────────────────────────────────────


def test_count_picks_plain_list():
    assert _count_picks([{"symbol": "A"}, {"symbol": "B"}]) == 2


def test_count_picks_picks_key():
    assert _count_picks({"picks": [1, 2, 3]}) == 3


def test_count_picks_long_picks():
    assert _count_picks({"long_picks": [1, 2], "swing_picks": [], "short_picks": []}) == 2


def test_count_picks_active_picks():
    assert _count_picks({"active_picks": [1, 2, 3, 4]}) == 4


def test_count_picks_empty_dict():
    assert _count_picks({}) == 0


def test_count_picks_non_dict_non_list():
    assert _count_picks("not a container") == 0


# ── 2. check_sources() staleness + missing ─────────────────────────────────────


def _make_source_file(tmp_path: Path, name: str, content: dict, age_seconds: float = 0) -> Path:
    """Create a temp source JSON file, optionally backdating its mtime."""
    f = tmp_path / name
    f.write_text(json.dumps(content), encoding="utf-8")
    if age_seconds > 0:
        mtime = time.time() - age_seconds
        import os
        os.utime(f, (mtime, mtime))
    return f


def test_check_sources_stale_file(tmp_path, monkeypatch):
    """Files older than stale_hours should appear in result['stale']."""
    src = _make_source_file(tmp_path, "stale.json", {"picks": [1, 2]}, age_seconds=50 * 3600)

    # Monkeypatch JSON_PICK_SOURCES to use our temp file
    monkeypatch.setattr(
        "tools.source_liveness_watchdog.ROOT",
        tmp_path.parent,  # so ROOT / path_str resolves correctly
    )

    # Use absolute path trick: set path relative to a fake ROOT
    fake_root = tmp_path.parent
    rel_path = str(src.relative_to(fake_root))

    import tools.source_liveness_watchdog as slw
    monkeypatch.setattr(slw, "ROOT", fake_root)

    # Patch JSON_PICK_SOURCES
    import audit_trail.dashboard_generator as dg
    orig = dg.JSON_PICK_SOURCES
    monkeypatch.setattr(dg, "JSON_PICK_SOURCES", [("test_src", rel_path, None)])

    result = check_sources(stale_hours=24, drop_pct=70, previous_snapshot=None)

    assert result["stale_count"] >= 1
    stale_paths = [s["path"] for s in result["stale"]]
    assert rel_path in stale_paths


def test_check_sources_fresh_file_no_stale(tmp_path, monkeypatch):
    """A freshly written file should not appear in stale."""
    src = _make_source_file(tmp_path, "fresh.json", {"picks": [1]}, age_seconds=0)

    import tools.source_liveness_watchdog as slw
    import audit_trail.dashboard_generator as dg
    fake_root = tmp_path.parent
    rel_path = str(src.relative_to(fake_root))

    monkeypatch.setattr(slw, "ROOT", fake_root)
    monkeypatch.setattr(dg, "JSON_PICK_SOURCES", [("fresh_src", rel_path, None)])

    result = check_sources(stale_hours=24, drop_pct=70, previous_snapshot=None)

    stale_paths = [s["path"] for s in result["stale"]]
    assert rel_path not in stale_paths


def test_check_sources_missing_file(tmp_path, monkeypatch):
    """Non-existent files should appear in result['missing']."""
    import tools.source_liveness_watchdog as slw
    import audit_trail.dashboard_generator as dg
    fake_root = tmp_path
    rel_path = "nonexistent/source.json"

    monkeypatch.setattr(slw, "ROOT", fake_root)
    monkeypatch.setattr(dg, "JSON_PICK_SOURCES", [("ghost_src", rel_path, None)])

    result = check_sources(stale_hours=24, drop_pct=70, previous_snapshot=None)
    assert result["missing_count"] >= 1
    missing_paths = [m["path"] for m in result["missing"]]
    assert rel_path in missing_paths


# ── 3. Row-count drop detection ────────────────────────────────────────────────


def test_check_sources_drop_detected(tmp_path, monkeypatch):
    """A >70% pick-count drop vs previous snapshot should appear in result['dropped']."""
    src = _make_source_file(tmp_path, "drop.json", {"picks": list(range(10))})

    import tools.source_liveness_watchdog as slw
    import audit_trail.dashboard_generator as dg
    fake_root = tmp_path.parent
    rel_path = str(src.relative_to(fake_root))

    monkeypatch.setattr(slw, "ROOT", fake_root)
    monkeypatch.setattr(dg, "JSON_PICK_SOURCES", [("drop_src", rel_path, None)])

    # Simulate previous snapshot with 100 picks
    prev_snapshot = {rel_path: {"count": 100, "mtime": time.time() - 3600}}

    result = check_sources(stale_hours=48, drop_pct=70, previous_snapshot=prev_snapshot)

    assert result["dropped_count"] >= 1
    drop_paths = [d["path"] for d in result["dropped"]]
    assert rel_path in drop_paths
    drop_entry = next(d for d in result["dropped"] if d["path"] == rel_path)
    assert drop_entry["prev_count"] == 100
    assert drop_entry["curr_count"] == 10
    assert drop_entry["drop_pct"] == pytest.approx(90.0)


def test_check_sources_small_drop_not_flagged(tmp_path, monkeypatch):
    """A <70% pick-count drop should NOT appear in result['dropped']."""
    src = _make_source_file(tmp_path, "small_drop.json", {"picks": list(range(80))})

    import tools.source_liveness_watchdog as slw
    import audit_trail.dashboard_generator as dg
    fake_root = tmp_path.parent
    rel_path = str(src.relative_to(fake_root))

    monkeypatch.setattr(slw, "ROOT", fake_root)
    monkeypatch.setattr(dg, "JSON_PICK_SOURCES", [("small_drop_src", rel_path, None)])

    prev_snapshot = {rel_path: {"count": 100, "mtime": time.time() - 3600}}

    result = check_sources(stale_hours=48, drop_pct=70, previous_snapshot=prev_snapshot)
    drop_paths = [d["path"] for d in result["dropped"]]
    assert rel_path not in drop_paths


# ── 4. Report writing ──────────────────────────────────────────────────────────


def test_write_report_creates_dated_and_latest(tmp_path):
    """write_report() must create both a dated file and source_liveness_latest.json."""
    result = {
        "generated_at": "2026-05-01T00:00:00Z",
        "checked": 5, "ok": 5, "stale_count": 0,
        "dropped_count": 0, "missing_count": 0,
        "stale": [], "dropped": [], "missing": [], "snapshot": {},
    }
    dated = write_report(result, tmp_path)
    latest = tmp_path / "source_liveness_latest.json"
    assert dated.exists()
    assert latest.exists()
    assert json.loads(latest.read_text()) == result


# ── 5. main() always exits 0 ──────────────────────────────────────────────────


def test_main_always_returns_0(tmp_path):
    """main() must return 0 even when stale/missing files exist."""
    # Run with --no-snapshot to avoid loading a previous run
    rc = main(["--output-dir", str(tmp_path), "--no-snapshot"])
    assert rc == 0


# ── 6. load_previous_snapshot() ───────────────────────────────────────────────


def test_load_previous_snapshot_returns_none_when_missing(tmp_path):
    """Returns None when source_liveness_latest.json doesn't exist."""
    result = load_previous_snapshot(tmp_path)
    assert result is None


def test_load_previous_snapshot_returns_snapshot(tmp_path):
    """Returns snapshot dict when source_liveness_latest.json exists."""
    snap = {"some/path.json": {"count": 10, "mtime": 1234567890.0}}
    (tmp_path / "source_liveness_latest.json").write_text(
        json.dumps({"snapshot": snap}), encoding="utf-8"
    )
    result = load_previous_snapshot(tmp_path)
    assert result == snap
