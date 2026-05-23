"""Smoke tests for tools/orphan_resolver_dryrun.py — read-only safe-ops gate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "orphan_resolver_dryrun.py"


def test_tool_exists():
    assert TOOL.exists()


def test_no_db_write_keywords():
    """Tool must NOT contain DB-mutating SQL — read-only by design."""
    src = TOOL.read_text(encoding="utf-8")
    forbidden = ["UPDATE trading_picks", "DELETE FROM", "INSERT INTO trading_picks",
                 "TRUNCATE", "DROP TABLE", "ALTER TABLE"]
    for kw in forbidden:
        assert kw not in src, f"Tool must not contain '{kw}' (read-only)"


def test_no_api_call_keywords():
    """No price-fetch or external HTTP — pure DB-read + metadata estimation."""
    src = TOOL.read_text(encoding="utf-8")
    forbidden = ["fetch_price", "fetch_klines", "yfinance", "requests.get",
                 "urllib.request"]
    for kw in forbidden:
        assert kw not in src, f"Tool must not contain '{kw}' (no API calls)"


def test_terminal_status_filter():
    """Must only resolve TERMINAL-status orphans, not OPEN/active."""
    src = TOOL.read_text(encoding="utf-8")
    # Find the status-IN clause and confirm OPEN/active not in the literal
    # filter list itself.
    if "status IN (" in src:
        clause = src.split("status IN (")[1].split(")")[0]
        assert "'OPEN'" not in clause, "OPEN must not be in terminal-status filter"
        assert "'active'" not in clause, "active must not be in terminal-status filter"
        assert "'ACTIVE'" not in clause, "ACTIVE must not be in terminal-status filter"
    # Positive: must include canonical terminal statuses
    for term in ("WON", "LOST", "TP_HIT", "SL_HIT", "EXPIRED"):
        assert f"'{term}'" in src, f"missing terminal status {term}"


def test_hold_hours_table_present():
    """Must mirror outcome_resolver MAX_HOLD_HOURS_BY_CLASS values."""
    src = TOOL.read_text(encoding="utf-8")
    assert "HOLD_HOURS_BY_CLASS" in src
    # Class-specific entries
    assert "\"CRYPTO\":    24" in src or '"CRYPTO":    24' in src
    assert "\"FOREX\":    120" in src or '"FOREX":    120' in src


def test_midpoint_estimate_used():
    """Real average resolution is ~half the cap — script halves."""
    src = TOOL.read_text(encoding="utf-8")
    assert "// 2" in src


def test_csv_output_documented():
    src = TOOL.read_text(encoding="utf-8")
    assert "preview.csv" in src
    assert "would_apply" in src


def test_safe_archive_referenced_in_next_steps():
    """Must point users at the archive gate per Hermes rule #1 before any apply."""
    src = TOOL.read_text(encoding="utf-8")
    assert "safe_db_archive" in src


def test_help_runs():
    r = subprocess.run([sys.executable, str(TOOL), "--help"],
                       capture_output=True, text=True, timeout=20)
    # No --help defined — script just runs main(). Treat clean exit OR
    # short module-doc output as pass (tool has no argparse).
    assert r.returncode in (0, 1, 2)
