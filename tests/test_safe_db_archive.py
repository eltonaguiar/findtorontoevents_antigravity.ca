"""Smoke tests for tools/safe_db_archive.py — Hermes rule #1 gate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "safe_db_archive.py"


def test_tool_exists():
    assert TOOL.exists()


def test_help_runs():
    r = subprocess.run([sys.executable, str(TOOL), "--help"],
                       capture_output=True, text=True, timeout=20)
    assert r.returncode == 0
    assert "SAFE DB ARCHIVE" in r.stdout
    assert "Hermes rule #1" in r.stdout


def test_required_args_enforced():
    r = subprocess.run([sys.executable, str(TOOL)],
                       capture_output=True, text=True, timeout=20)
    assert r.returncode != 0
    assert "required" in (r.stderr.lower() + r.stdout.lower())


def test_dry_run_default():
    src = TOOL.read_text(encoding="utf-8")
    assert 'action="store_true"' in src or "action='store_true'" in src
    assert "if not args.apply" in src


def test_archive_name_pattern():
    src = TOOL.read_text(encoding="utf-8")
    assert "{args.source_table}_{args.purpose}_{ts_utc}" in src


def test_log_path_documented():
    src = TOOL.read_text(encoding="utf-8")
    assert "reports/db_archives_log.md" in src


def test_max_rows_safety_default():
    src = TOOL.read_text(encoding="utf-8")
    assert "max-rows" in src or "max_rows" in src
    assert "100_000" in src or "100000" in src


def test_batched_insert():
    src = TOOL.read_text(encoding="utf-8")
    assert "BATCH = 1000" in src
    assert "fetchmany" in src


def test_count_parity_verification():
    src = TOOL.read_text(encoding="utf-8")
    assert "Parity confirmed" in src or "parity" in src.lower()
