"""Tests for B28: UEPS direct registration in JSON_PICK_SOURCES.

Verifies that audit_trail/dashboard_generator.py registers
audit_dashboard/data/ueps_picks.json in JSON_PICK_SOURCES and that
_extract_picks() correctly reads the multi-list UEPS schema.

Root cause addressed: sync_to_active_picks() → active_picks.json was
overwritten by competing crons within ~4h, wiping UEPS rows permanently.
Fix: ueps_picks.json registered directly in JSON_PICK_SOURCES so the
dashboard reads it without the racy shared-ledger hop.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ── JSON_PICK_SOURCES registration ─────────────────────────────────────────


def test_ueps_registered_in_json_pick_sources() -> None:
    """ueps_picks.json must appear in JSON_PICK_SOURCES so the dashboard
    loader reads it on every rebuild without relying on active_picks.json."""
    from audit_trail import dashboard_generator as dg

    ueps_path = "audit_dashboard/data/ueps_picks.json"
    registered_paths = [path for _, path, _ in dg.JSON_PICK_SOURCES]
    assert ueps_path in registered_paths, (
        f"'{ueps_path}' not found in JSON_PICK_SOURCES. "
        "B28 fix requires direct registration so UEPS picks survive "
        "competing crons overwriting active_picks.json."
    )


def test_ueps_source_name_in_json_pick_sources() -> None:
    """The source name 'ueps' must be registered (not just the path)."""
    from audit_trail import dashboard_generator as dg

    registered_names = [name for name, _, _ in dg.JSON_PICK_SOURCES]
    assert "ueps" in registered_names, (
        "'ueps' source name not in JSON_PICK_SOURCES. "
        "The source name drives system-level filtering and display labels."
    )


# ── _extract_picks multi-list handling ─────────────────────────────────────


def test_extract_picks_handles_ueps_long_picks() -> None:
    """_extract_picks must return the long_picks list for UEPS schema."""
    from audit_trail.dashboard_generator import _extract_picks

    data = {
        "generated_at": "2026-05-01T12:00:00Z",
        "long_picks": [{"symbol": "ADBE", "direction": "LONG", "pick_type": "long_term_value"}],
        "swing_picks": [],
        "short_picks": [],
        "summary": {"n_long": 1, "n_short": 0, "n_swing": 0},
    }
    result = _extract_picks(data)
    assert len(result) == 1
    assert result[0]["symbol"] == "ADBE"


def test_extract_picks_concatenates_all_ueps_sublists() -> None:
    """_extract_picks must concatenate long + swing + short lists."""
    from audit_trail.dashboard_generator import _extract_picks

    data = {
        "generated_at": "2026-05-01T12:00:00Z",
        "long_picks": [{"symbol": "AAPL", "direction": "LONG"}],
        "swing_picks": [{"symbol": "MSFT", "direction": "LONG"}],
        "short_picks": [{"symbol": "TSLA", "direction": "SHORT"}],
        "summary": {"n_long": 1, "n_short": 1, "n_swing": 1},
    }
    result = _extract_picks(data)
    assert len(result) == 3
    symbols = {p["symbol"] for p in result}
    assert symbols == {"AAPL", "MSFT", "TSLA"}


def test_extract_picks_propagates_parent_timestamp_to_ueps_picks() -> None:
    """generated_at from the top-level UEPS dict must propagate to picks
    that lack their own timestamp (UEPS picks have no per-pick timestamp)."""
    from audit_trail.dashboard_generator import _extract_picks

    ts = "2026-05-01T12:54:36.298722+00:00"
    data = {
        "generated_at": ts,
        "long_picks": [{"symbol": "GOOG", "direction": "LONG"}],
        "swing_picks": [],
        "short_picks": [],
    }
    result = _extract_picks(data)
    assert result[0].get("generated_at") == ts


def test_extract_picks_ueps_empty_sublists_returns_empty() -> None:
    """If all three UEPS sub-lists are empty, _extract_picks returns []."""
    from audit_trail.dashboard_generator import _extract_picks

    data = {
        "generated_at": "2026-05-01T12:00:00Z",
        "long_picks": [],
        "swing_picks": [],
        "short_picks": [],
        "summary": {"n_long": 0, "n_short": 0, "n_swing": 0},
    }
    result = _extract_picks(data)
    assert result == []


def test_extract_picks_live_ueps_file() -> None:
    """Verify _extract_picks returns ≥1 pick from the live ueps_picks.json."""
    from audit_trail.dashboard_generator import _extract_picks

    path = ROOT / "audit_dashboard" / "data" / "ueps_picks.json"
    if not path.exists():
        pytest.skip("ueps_picks.json not found (runner may lack data)")
    data = json.loads(path.read_text(encoding="utf-8"))
    result = _extract_picks(data)
    assert len(result) >= 1, (
        f"Expected ≥1 pick from live ueps_picks.json, got {len(result)}. "
        "Check that long_picks is non-empty in the file."
    )
    # Spot-check first pick has required fields
    p = result[0]
    assert "symbol" in p
    assert "direction" in p


# ── Workflow consistency ────────────────────────────────────────────────────


def test_workflow_no_longer_syncs_active_picks() -> None:
    """After B28, the workflow must use --skip-active-sync so the dashboard
    reads ueps_picks.json directly instead of the racy active_picks.json."""
    workflow_path = ROOT / ".github" / "workflows" / "ueps-pick-runner.yml"
    if not workflow_path.exists():
        pytest.skip("Workflow file not found")
    text = workflow_path.read_text(encoding="utf-8")
    assert "--skip-active-sync" in text, (
        "Workflow must pass --skip-active-sync to run_ueps_pickers. "
        "Without it, the race condition with alpha-engine-live.yml is active."
    )
