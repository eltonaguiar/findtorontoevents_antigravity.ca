"""Tests for tools/prune_strategy_performance.py.

Covers:
1. --dry-run flag prints count without writing
2. Actual run writes only when changes occur (no-op path)
3. Actual run writes when stale entries exist (prune path)
4. Idempotent: second run on already-pruned file is a no-op
5. Missing target file -> exit 0, no-op
6. Custom --max-age-days respected
7. Failures are non-fatal (exit 0 even when prune_stale raises)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

# Make repo root importable for `tools.prune_strategy_performance`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.atomic_json import atomic_write_json, read_json  # noqa: E402

import tools.prune_strategy_performance as prune_mod  # noqa: E402


# --- Fixtures --------------------------------------------------------------

def _utc_iso(days_ago: int) -> str:
    """ISO-format UTC timestamp `days_ago` days before now."""
    return (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)
    ).isoformat()


@pytest.fixture
def mixed_age_file(tmp_path: Path) -> Path:
    """Create a JSON file with fresh, stale, and unparseable-ts entries."""
    p = tmp_path / "strategy_performance.json"
    data = {
        "fresh_strat":  {"closed_picks": 5, "wr": 0.6, "last_seen": _utc_iso(1)},
        "stale_strat":  {"closed_picks": 2, "wr": 0.3, "last_seen": _utc_iso(60)},
        "no_ts_strat":  {"closed_picks": 1, "wr": 0.5},  # no last_seen -> kept
        "borderline":   {"closed_picks": 8, "wr": 0.55, "last_seen": _utc_iso(29)},
    }
    atomic_write_json(p, data)
    return p


@pytest.fixture
def fresh_only_file(tmp_path: Path) -> Path:
    """File with only fresh entries -- no-op expected."""
    p = tmp_path / "strategy_performance.json"
    data = {
        "a": {"v": 1, "last_seen": _utc_iso(1)},
        "b": {"v": 2, "last_seen": _utc_iso(5)},
    }
    atomic_write_json(p, data)
    return p


# --- Tests -----------------------------------------------------------------

def test_dry_run_does_not_write(mixed_age_file: Path, capsys):
    """--dry-run reports the count but leaves the file untouched."""
    before_bytes = mixed_age_file.read_bytes()
    before_mtime = mixed_age_file.stat().st_mtime_ns

    rc = prune_mod.main(["--path", str(mixed_age_file), "--dry-run"])
    assert rc == 0

    # File contents unchanged
    assert mixed_age_file.read_bytes() == before_bytes
    assert mixed_age_file.stat().st_mtime_ns == before_mtime

    # Count reported
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "before=4" in out
    assert "after=3" in out
    assert "would_prune=1" in out
    assert "stale_strat" in out  # listed in keys_to_drop


def test_actual_run_writes_when_changes(mixed_age_file: Path, capsys):
    """When stale entries exist, the file is rewritten with them removed."""
    rc = prune_mod.main(["--path", str(mixed_age_file)])
    assert rc == 0

    after = read_json(mixed_age_file)
    assert "fresh_strat" in after
    assert "borderline" in after
    assert "no_ts_strat" in after  # kept defensively
    assert "stale_strat" not in after  # pruned

    out = capsys.readouterr().out
    assert "pruned" in out
    assert "removed=1" in out


def test_no_op_when_nothing_to_prune(fresh_only_file: Path, capsys):
    """No stale entries -> file untouched, log says no-op."""
    before_bytes = fresh_only_file.read_bytes()
    before_mtime = fresh_only_file.stat().st_mtime_ns

    rc = prune_mod.main(["--path", str(fresh_only_file)])
    assert rc == 0

    # File completely untouched (atomic_write_json NOT called)
    assert fresh_only_file.read_bytes() == before_bytes
    assert fresh_only_file.stat().st_mtime_ns == before_mtime

    out = capsys.readouterr().out
    assert "no-op" in out


def test_idempotent_second_run_is_noop(mixed_age_file: Path, capsys):
    """Running prune twice in a row: first prunes, second is a no-op."""
    # First run: prunes stale_strat
    rc1 = prune_mod.main(["--path", str(mixed_age_file)])
    assert rc1 == 0
    capsys.readouterr()  # discard first-run log

    mid_bytes = mixed_age_file.read_bytes()
    mid_mtime = mixed_age_file.stat().st_mtime_ns

    # Second run: nothing left to prune
    rc2 = prune_mod.main(["--path", str(mixed_age_file)])
    assert rc2 == 0

    # File untouched between runs 1 and 2
    assert mixed_age_file.read_bytes() == mid_bytes
    assert mixed_age_file.stat().st_mtime_ns == mid_mtime

    out2 = capsys.readouterr().out
    assert "no-op" in out2


def test_missing_target_exits_zero(tmp_path: Path, capsys):
    """If the target file doesn't exist, exit 0 with a log line (cron-safe)."""
    missing = tmp_path / "does_not_exist.json"
    rc = prune_mod.main(["--path", str(missing)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "target not found" in out


def test_custom_max_age_days(tmp_path: Path, capsys):
    """--max-age-days overrides the default 30-day cutoff."""
    p = tmp_path / "x.json"
    data = {
        "ten_days":    {"v": 1, "last_seen": _utc_iso(10)},
        "twenty_days": {"v": 2, "last_seen": _utc_iso(20)},
    }
    atomic_write_json(p, data)

    # Cutoff = 15 days -> only twenty_days should drop
    rc = prune_mod.main(["--path", str(p), "--max-age-days", "15"])
    assert rc == 0
    after = read_json(p)
    assert "ten_days" in after
    assert "twenty_days" not in after


def test_dry_run_with_custom_age(tmp_path: Path, capsys):
    """Dry-run + custom max-age combine correctly."""
    p = tmp_path / "x.json"
    data = {
        "five":  {"v": 1, "last_seen": _utc_iso(5)},
        "fifty": {"v": 2, "last_seen": _utc_iso(50)},
    }
    atomic_write_json(p, data)

    rc = prune_mod.main(["--path", str(p), "--max-age-days", "7", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "would_prune=1" in out
    # File untouched
    assert read_json(p) == data


def test_failure_in_prune_stale_is_non_fatal(monkeypatch, mixed_age_file: Path, capsys):
    """If prune_stale raises, exit 0 with an error log (cron must keep running)."""
    def boom(*a, **kw):
        raise RuntimeError("simulated prune failure")

    # Patch the symbol on the imported module so the local import inside main()
    # picks up the bomb (the script does `from alpha_engine.atomic_json import prune_stale`).
    import alpha_engine.atomic_json as aj
    monkeypatch.setattr(aj, "prune_stale", boom)

    rc = prune_mod.main(["--path", str(mixed_age_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ERROR in prune_stale" in out


def test_non_dict_data_skipped(tmp_path: Path, capsys):
    """If the JSON file contains a list (not dict), exit 0 with a skip log."""
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    rc = prune_mod.main(["--path", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "not dict" in out
