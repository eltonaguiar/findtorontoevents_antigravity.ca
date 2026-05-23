"""Tests for B11 ETF workflow fix (2026-05-02).

Verifies that:
1. etf_decay_picks.json is registered in JSON_PICK_SOURCES under leveraged_etf_decay
2. etf_sector_picks.json is still registered under etf_sector_rotation
3. The workflow YAML calls tools/etf_sector_emitter.py (not just the spike)
4. The workflow YAML calls alpha_engine/strategies/etf_decay_shorts.py
5. The workflow commits both production output files
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "alpha-engine-etf.yml"


# ---------------------------------------------------------------------------
# JSON_PICK_SOURCES registration
# ---------------------------------------------------------------------------

def test_leveraged_etf_decay_points_to_etf_decay_picks():
    """leveraged_etf_decay entry in JSON_PICK_SOURCES must use etf_decay_picks.json."""
    import sys
    sys.path.insert(0, str(ROOT))
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES

    entry = next((e for e in JSON_PICK_SOURCES if e[0] == "leveraged_etf_decay"), None)
    assert entry is not None, "leveraged_etf_decay not found in JSON_PICK_SOURCES"
    assert "etf_decay_picks.json" in entry[1], (
        f"Expected etf_decay_picks.json, got {entry[1]}. "
        "The B11 fix wires the actual script output (etf_decay_picks.json) "
        "into JSON_PICK_SOURCES instead of the stale stub."
    )


def test_etf_sector_rotation_registered():
    """etf_sector_rotation must remain registered in JSON_PICK_SOURCES."""
    import sys
    sys.path.insert(0, str(ROOT))
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES

    entry = next((e for e in JSON_PICK_SOURCES if e[0] == "etf_sector_rotation"), None)
    assert entry is not None, "etf_sector_rotation missing from JSON_PICK_SOURCES"
    assert "etf_sector_picks.json" in entry[1], (
        f"Expected etf_sector_picks.json, got {entry[1]}"
    )


def test_no_leveraged_etf_decay_picks_stale_stub():
    """After B11, leveraged_etf_decay_picks.json should NOT be in JSON_PICK_SOURCES
    (it was a stale manually-crafted stub; the script writes etf_decay_picks.json)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES

    stale_entries = [e for e in JSON_PICK_SOURCES if "leveraged_etf_decay_picks.json" in str(e[1])]
    assert len(stale_entries) == 0, (
        f"leveraged_etf_decay_picks.json (stale stub) is still in JSON_PICK_SOURCES: {stale_entries}. "
        "B11 fix should have replaced it with etf_decay_picks.json."
    )


# ---------------------------------------------------------------------------
# Workflow YAML calls both production emitters
# ---------------------------------------------------------------------------

def _workflow_text():
    return WORKFLOW_PATH.read_text()


def test_workflow_calls_etf_sector_emitter():
    """Workflow must call tools/etf_sector_emitter.py (production emitter)."""
    text = _workflow_text()
    assert "etf_sector_emitter.py" in text, (
        "alpha-engine-etf.yml does not call tools/etf_sector_emitter.py. "
        "B11 fix: add production emitter step so etf_sector_picks.json gets populated."
    )


def test_workflow_calls_etf_decay_shorts():
    """Workflow must call alpha_engine/strategies/etf_decay_shorts.py."""
    text = _workflow_text()
    assert "etf_decay_shorts.py" in text, (
        "alpha-engine-etf.yml does not call alpha_engine/strategies/etf_decay_shorts.py. "
        "B11 fix: add leveraged ETF decay step so etf_decay_picks.json stays fresh."
    )


def test_workflow_etf_sector_emitter_enabled():
    """Workflow must set ETF_SECTOR_EMITTER_ENABLED=1 for the production emitter step."""
    text = _workflow_text()
    assert "ETF_SECTOR_EMITTER_ENABLED" in text, (
        "Workflow does not set ETF_SECTOR_EMITTER_ENABLED. "
        "The emitter is opt-in and requires this flag to emit picks."
    )


def test_workflow_commits_etf_sector_picks():
    """Workflow commit step must add etf_sector_picks.json."""
    text = _workflow_text()
    assert "etf_sector_picks.json" in text, (
        "Workflow commit step does not include etf_sector_picks.json. "
        "B11 fix: the production emitter output must be committed."
    )


def test_workflow_commits_etf_decay_picks():
    """Workflow commit step must add etf_decay_picks.json."""
    text = _workflow_text()
    assert "etf_decay_picks.json" in text, (
        "Workflow commit step does not include etf_decay_picks.json. "
        "B11 fix: the leveraged decay emitter output must be committed."
    )


# ---------------------------------------------------------------------------
# JSON schema compatibility
# ---------------------------------------------------------------------------

def test_etf_decay_picks_schema_compatible_with_extract_picks():
    """etf_decay_picks.json must have a 'picks' key that _extract_picks can handle."""
    import sys
    sys.path.insert(0, str(ROOT))
    from audit_trail.dashboard_generator import _extract_picks

    data = json.loads((ROOT / "alpha_engine/data/etf_decay_picks.json").read_text())
    assert "picks" in data, "etf_decay_picks.json missing top-level 'picks' key"
    picks = _extract_picks(data)
    # May be 0 (yfinance unavailable locally) — just confirm it's a list
    assert isinstance(picks, list), f"_extract_picks returned {type(picks)}, expected list"
