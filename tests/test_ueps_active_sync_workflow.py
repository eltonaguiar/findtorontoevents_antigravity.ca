"""Regression tests for the UEPS workflow (ueps-pick-runner.yml).

History:
- PR #547 fixed the UEPS sync bug: workflow was not committing
  active_picks.json, so sync_to_active_picks() output was discarded.
- B28 (2026-05-01) replaced the sync approach entirely: ueps_picks.json
  is now registered directly in JSON_PICK_SOURCES (dashboard_generator.py)
  so the dashboard reads it without relying on active_picks.json.
  The workflow no longer stages active_picks.json; --skip-active-sync
  is passed to run_ueps_pickers.py to prevent double-population.
"""
from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "ueps-pick-runner.yml"
)


def test_workflow_exists() -> None:
    assert WORKFLOW.exists()


def test_workflow_yaml_is_valid() -> None:
    with WORKFLOW.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    assert loaded is not None
    assert "jobs" in loaded


def test_workflow_commits_ueps_picks_json() -> None:
    """ueps_picks.json must be committed — it is the dashboard's direct feed
    now that the source is registered in JSON_PICK_SOURCES (B28)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "audit_dashboard/data/ueps_picks.json" in text, (
        "ueps_picks.json must remain in the git add line — it is the "
        "primary feed registered in JSON_PICK_SOURCES."
    )


def test_workflow_uses_skip_active_sync() -> None:
    """B28 fix: workflow must pass --skip-active-sync to prevent the race
    condition where alpha-engine-live.yml overwrites active_picks.json
    and wipes inserted UEPS rows within ~4h of each sync."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--skip-active-sync" in text, (
        "B28 fix requires --skip-active-sync flag on run_ueps_pickers. "
        "Without it, UEPS picks are double-populated (JSON_PICK_SOURCES "
        "reads ueps_picks.json AND sync writes to active_picks.json) and "
        "the race condition with alpha-engine-live.yml is re-introduced."
    )


def test_workflow_does_not_commit_active_picks() -> None:
    """B28 fix: active_picks.json must NOT be in the git add line.
    UEPS picks now reach /audit via JSON_PICK_SOURCES → ueps_picks.json,
    not via the racy active_picks.json sync path."""
    text = WORKFLOW.read_text(encoding="utf-8")
    # The git add line should only stage ueps_picks.json
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("git add") and "alpha_engine/data/active_picks.json" in stripped:
            raise AssertionError(
                "active_picks.json must not be in the git add line after B28. "
                "UEPS picks reach /audit via JSON_PICK_SOURCES registration."
            )


def test_workflow_uses_safe_push_for_concurrency_safety() -> None:
    """safe_push.sh retries with rebase on non-fast-forward rejections."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "safe_push.sh" in text


def test_workflow_does_not_force_push_or_skip_hooks() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--force" not in text
    assert "--no-verify" not in text


def test_legacy_does_not_mutate_comment_removed() -> None:
    """Legacy comment inverted by PR #547 should no longer appear."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Does NOT mutate" not in text, (
        "Legacy comment was inverted by PR #547; remove it from the file "
        "header so the documentation matches behavior."
    )
