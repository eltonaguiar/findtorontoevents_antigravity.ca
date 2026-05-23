"""Wire-up regression tests for the penny skyrocket detector (2026-04-30).

Background: ``alpha_engine/strategies/skyrocket_detector.py`` existed with
its own ``main()`` + scan() but had **no scheduled emitter** — it was a
193-line orphan per Gemma4-cloud's audit. This PR wires it via:

  1. ``.github/workflows/penny-skyrocket-runner.yml`` — daily cron emitter.
  2. JSON_PICK_SOURCES registration in
     ``audit_trail/dashboard_generator.py``.

These tests pin both surfaces so future YAML refactors / dashboard-source
churn cannot silently re-orphan the detector.
"""
from __future__ import annotations

from pathlib import Path

import yaml

import pytest


REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "penny-skyrocket-runner.yml"


# ────────────────────────────────────────────────────────────────────────
# Workflow surface
# ────────────────────────────────────────────────────────────────────────

def test_penny_skyrocket_workflow_exists() -> None:
    assert WORKFLOW.exists(), f"workflow missing at {WORKFLOW}"


def test_workflow_yaml_is_valid() -> None:
    """Bare YAML parse — catches syntax errors that GH Actions only catches
    after push."""
    with WORKFLOW.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    assert loaded is not None
    assert "jobs" in loaded


def test_workflow_invokes_correct_module() -> None:
    """The runner must call the `alpha_engine.strategies.skyrocket_detector`
    module, NOT the unrelated `skyrocket_detector` crypto-ML project at the
    repo root (which has its own workflow at .github/workflows/skyrocket-detector.yml)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "alpha_engine.strategies.skyrocket_detector" in text, (
        "Workflow must invoke alpha_engine.strategies.skyrocket_detector "
        "(the EQUITY penny-stock detector); naming collision with the "
        "crypto-ML skyrocket_detector/ project would otherwise be silent."
    )


def test_workflow_commits_skyrocket_picks_json() -> None:
    """Without this, the runner writes to the ephemeral runner FS and the
    JSON vanishes at job end — exactly the bug fixed in PR #545 for the
    PEAD earnings cache. Pin the persistence step here."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "alpha_engine/data/skyrocket_picks.json" in text
    assert "git add" in text
    assert "safe_push.sh" in text, (
        "Use safe_push.sh for retry-with-rebase to coexist with concurrent "
        "data-commit workflows."
    )


def test_workflow_has_daily_cron() -> None:
    """Daily cron is sufficient — penny stocks don't need hourly scans and
    yfinance rate-limits get spicy with frequent runs."""
    text = WORKFLOW.read_text(encoding="utf-8")
    # 14:48 UTC = offset from etf-agent (:30) + bond-agent (:32) per file comment
    assert "'48 14 * * 1-5'" in text or "48 14 * * 1-5" in text


# ────────────────────────────────────────────────────────────────────────
# JSON_PICK_SOURCES registration
# ────────────────────────────────────────────────────────────────────────

def test_skyrocket_detector_registered_in_json_pick_sources() -> None:
    """Picks reach /audit via JSON_PICK_SOURCES. Without registration the
    workflow runs but the dashboard never reads its output."""
    from audit_trail.dashboard_generator import JSON_PICK_SOURCES

    skyrocket_entries = [
        entry for entry in JSON_PICK_SOURCES if entry[0] == "skyrocket_detector"
    ]
    assert len(skyrocket_entries) == 1, (
        f"Expected exactly one skyrocket_detector source, got {len(skyrocket_entries)}: "
        f"{skyrocket_entries}"
    )
    sys_name, active_path, closed_path = skyrocket_entries[0]
    assert active_path == "alpha_engine/data/skyrocket_picks.json"
    # closed_path is None — outcomes settle via the universal resolver.


def test_detector_module_importable() -> None:
    """The detector module must import cleanly without yfinance installed
    (it lazy-imports yfinance inside fetch_data). Guards against an import
    refactor breaking the workflow path."""
    import alpha_engine.strategies.skyrocket_detector as sd  # noqa: F401

    assert hasattr(sd, "scan"), "detector must expose `scan()` for the workflow"
    assert hasattr(sd, "main"), "detector must expose `main()` for `python -m`"


def test_detector_pick_schema_compatible_with_dashboard_extract():
    """The detector's _save_picks writes {generated_at, strategy, count,
    picks: [...]}. The dashboard's _extract_picks() recognizes the `picks`
    key. Pin that contract here so a future schema change can't silently
    de-wire the source."""
    from audit_trail.dashboard_generator import _extract_picks

    fake_payload = {
        "generated_at": "2026-04-30T20:00:00+00:00",
        "strategy": "skyrocket_detector",
        "count": 1,
        "picks": [
            {
                "id": "skyrocket_detector::SIDU::2026-04-30_2000",
                "symbol": "SIDU",
                "asset_class": "EQUITY",
                "strategy": "skyrocket_detector",
                "source_system": "skyrocket_detector",
                "category": "penny",
                "direction": "LONG",
                "entry_price": 1.50,
                "take_profit": 2.10,
                "stop_loss": 1.275,
                "confidence": 0.75,
                "max_hold_days": 5,
                "status": "OPEN",
            },
        ],
    }
    extracted = _extract_picks(fake_payload)
    assert isinstance(extracted, list)
    assert len(extracted) == 1
    assert extracted[0]["symbol"] == "SIDU"
