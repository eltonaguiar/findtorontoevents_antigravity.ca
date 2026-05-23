"""Tests for alpha_engine.atomic_json — atomic JSON read/write + merge + prune."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

# Allow `import alpha_engine.atomic_json` from tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alpha_engine.atomic_json import (
    atomic_write_json,
    merge_write_json,
    prune_stale,
    read_json,
)


# ---------------------------------------------------------------------------
# read_json
# ---------------------------------------------------------------------------

def test_read_missing_returns_default(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert read_json(p) == {}
    assert read_json(p, default=[]) == []
    assert read_json(p, default={"x": 1}) == {"x": 1}


def test_read_valid(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text('{"a": 1, "b": [1,2,3]}', encoding="utf-8")
    assert read_json(p) == {"a": 1, "b": [1, 2, 3]}


def test_read_corrupt_returns_default(tmp_path: Path):
    p = tmp_path / "corrupt.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert read_json(p) == {}
    assert read_json(p, default={"fallback": True}) == {"fallback": True}


def test_read_empty_file_returns_default(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert read_json(p) == {}


# ---------------------------------------------------------------------------
# atomic_write_json
# ---------------------------------------------------------------------------

def test_atomic_write_creates_file(tmp_path: Path):
    p = tmp_path / "out.json"
    atomic_write_json(p, {"hello": "world"})
    assert p.exists()
    assert json.loads(p.read_text()) == {"hello": "world"}


def test_atomic_write_creates_parent_dirs(tmp_path: Path):
    p = tmp_path / "deep" / "nested" / "out.json"
    atomic_write_json(p, [1, 2, 3])
    assert p.exists()
    assert json.loads(p.read_text()) == [1, 2, 3]


def test_atomic_write_no_temp_file_left_behind(tmp_path: Path):
    p = tmp_path / "x.json"
    atomic_write_json(p, {"v": 1})
    # Only the target file should remain — no .tmp leftovers
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].name == "x.json"


def test_atomic_write_overwrites_existing(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text('{"old": true}', encoding="utf-8")
    atomic_write_json(p, {"new": True})
    assert json.loads(p.read_text()) == {"new": True}


def test_atomic_write_handles_non_serializable_via_default_str(tmp_path: Path):
    """default=str converts datetime/path objects to string instead of raising."""
    p = tmp_path / "x.json"
    atomic_write_json(p, {"ts": dt.datetime(2026, 4, 17, 12, 0, 0)})
    # datetime gets stringified; we just need NOT to raise
    loaded = json.loads(p.read_text())
    assert "ts" in loaded
    assert isinstance(loaded["ts"], str)


def test_atomic_write_failure_cleans_temp(tmp_path: Path, monkeypatch):
    """If json.dump fails mid-write, no .tmp file is left behind."""
    p = tmp_path / "x.json"

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        # default=str catches MOST things but a custom class with no __str__
        # override + a deliberate dump-side failure is hard to fake; instead
        # patch json.dump to raise after temp is created.
        import alpha_engine.atomic_json as mod
        original = mod.json.dump
        def boom(*a, **k):
            raise TypeError("simulated dump failure")
        monkeypatch.setattr(mod.json, "dump", boom)
        atomic_write_json(p, {"v": 1})

    # Final target should NOT exist; temp files should NOT be left
    assert not p.exists()
    leftovers = [f for f in tmp_path.iterdir() if f.name.startswith("x.json.")]
    assert leftovers == [], f"temp files left behind: {leftovers}"


# ---------------------------------------------------------------------------
# merge_write_json
# ---------------------------------------------------------------------------

def test_merge_into_empty(tmp_path: Path):
    p = tmp_path / "m.json"
    result = merge_write_json(p, {"a": {"v": 1}}, stamp_field=None)
    assert result == {"a": {"v": 1}}
    assert read_json(p) == {"a": {"v": 1}}


def test_merge_preserves_existing_keys(tmp_path: Path):
    p = tmp_path / "m.json"
    atomic_write_json(p, {"old_key": {"v": 1}, "shared": {"v": "old"}})
    merge_write_json(p, {"new_key": {"v": 2}, "shared": {"v": "new"}}, stamp_field=None)
    final = read_json(p)
    assert "old_key" in final  # preserved
    assert "new_key" in final  # added
    assert final["shared"]["v"] == "new"  # overridden


def test_merge_stamps_last_seen(tmp_path: Path):
    p = tmp_path / "m.json"
    merge_write_json(p, {"strat_a": {"closed_picks": 5, "wr": 0.6}})
    final = read_json(p)
    assert "last_seen" in final["strat_a"]
    # Should be ISO format
    ts = final["strat_a"]["last_seen"]
    assert "T" in ts


def test_merge_rejects_non_dict_input(tmp_path: Path):
    p = tmp_path / "m.json"
    with pytest.raises(TypeError):
        merge_write_json(p, [1, 2, 3])  # type: ignore


def test_merge_handles_corrupt_existing(tmp_path: Path):
    """If existing file is corrupt, treat as empty dict and proceed."""
    p = tmp_path / "m.json"
    p.write_text("garbage", encoding="utf-8")
    result = merge_write_json(p, {"a": {"v": 1}}, stamp_field=None)
    assert result == {"a": {"v": 1}}


# ---------------------------------------------------------------------------
# prune_stale
# ---------------------------------------------------------------------------

def test_prune_drops_old_entries():
    now = dt.datetime(2026, 4, 17, 12, 0, 0, tzinfo=dt.timezone.utc)
    data = {
        "fresh": {"v": 1, "last_seen": "2026-04-15T12:00:00+00:00"},
        "stale": {"v": 2, "last_seen": "2026-03-01T12:00:00+00:00"},
        "borderline": {"v": 3, "last_seen": "2026-04-10T12:00:00+00:00"},  # 7 days ago, < 30
    }
    pruned = prune_stale(data, max_age_days=30, now=now)
    assert "fresh" in pruned
    assert "borderline" in pruned
    assert "stale" not in pruned


def test_prune_keeps_unparseable_timestamps():
    now = dt.datetime(2026, 4, 17, 12, 0, 0, tzinfo=dt.timezone.utc)
    data = {
        "good": {"v": 1, "last_seen": "2026-04-15T12:00:00+00:00"},
        "bad_ts": {"v": 2, "last_seen": "not a date"},
        "no_ts": {"v": 3},
    }
    pruned = prune_stale(data, max_age_days=30, now=now)
    assert "good" in pruned
    assert "bad_ts" in pruned   # kept (defensive)
    assert "no_ts" in pruned    # kept (defensive)


def test_prune_keeps_non_dict_values():
    now = dt.datetime(2026, 4, 17, 12, 0, 0, tzinfo=dt.timezone.utc)
    data = {
        "string_val": "raw_value",
        "int_val": 42,
        "list_val": [1, 2],
        "dict_val": {"v": 1, "last_seen": "2026-03-01T12:00:00+00:00"},  # stale
    }
    pruned = prune_stale(data, max_age_days=30, now=now)
    assert pruned["string_val"] == "raw_value"
    assert pruned["int_val"] == 42
    assert pruned["list_val"] == [1, 2]
    assert "dict_val" not in pruned  # only the stale dict gets pruned


def test_prune_handles_z_suffix():
    """ISO timestamps with Z suffix (instead of +00:00) are accepted."""
    now = dt.datetime(2026, 4, 17, 12, 0, 0, tzinfo=dt.timezone.utc)
    data = {
        "z_format": {"v": 1, "last_seen": "2026-04-15T12:00:00Z"},
    }
    pruned = prune_stale(data, max_age_days=30, now=now)
    assert "z_format" in pruned


# ---------------------------------------------------------------------------
# Integration: atomic survives a partial-read race scenario
# ---------------------------------------------------------------------------

def test_concurrent_read_during_write_sees_old_or_new(tmp_path: Path):
    """Smoke test: while atomic_write_json runs, reads only see complete files.

    We can't truly simulate concurrent processes in pytest, but we verify that
    the temp file is invisible to readers (because os.replace is atomic).
    """
    p = tmp_path / "x.json"
    atomic_write_json(p, {"version": "v1"})
    # Read it back — should see v1
    assert read_json(p) == {"version": "v1"}

    # Now write v2; readers between writes should NEVER see partial content
    # (we can verify this by checking that during the write, only one valid
    # file exists in the dir at a time, but that requires threading)
    atomic_write_json(p, {"version": "v2"})
    assert read_json(p) == {"version": "v2"}

    # No leftover .tmp files
    files_in_dir = sorted(f.name for f in tmp_path.iterdir())
    assert files_in_dir == ["x.json"]
