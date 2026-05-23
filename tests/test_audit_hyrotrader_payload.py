"""Schema/freshness tests for audit_dashboard/data/hyro_*.json artifacts.

The /audit/hyrotrader tab reads several JSON sidecar files. This module
verifies their shape (top-level keys + entry schema) plus a freshness check
on hyro_quan_bridge.json (the only hyro file read live by template.html
fetch — see audit_dashboard/template.html:2609).

Tests skip when the file is absent so the suite stays green on fresh clones.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"

# Files known to be consumed by hyrotrader tab, generators, or validators.
# (Discovered via repo grep on 2026-05-09 — see tools/hyro_pick_performance_validator.py,
# alpha_engine/hyrotrader_enhanced_scoring.py, audit_dashboard/template.html:2609.)
KNOWN_HYRO_FILES = {
    "hyro_ml_pick_rankings.json",
    "hyro_quan_bridge.json",
    "hyro_pick_performance.json",
    "hyro_live_strategies.json",
    "hyro_playbook_combined.json",
    "hyro_backtest_results.json",
    "hyro_backtest_extended_results.json",
    "hyro_backtest_new_strategies.json",
    "hyro_backtest_12m_new_strategies.json",
    "hyro_batch2_results.json",
    "hyro_signal_history.json",
    "hyro_signal_monitor.json",
    "hyro_risk_optimization_smoke.json",
    "hyrotrader_picks.json",
    "hyrotrader_journal.json",
    "hyrotrader_enhanced_picks.json",
    "hyrotrader_short_term_entries.json",
}

ML_RANKINGS = DATA_DIR / "hyro_ml_pick_rankings.json"
QUAN_BRIDGE = DATA_DIR / "hyro_quan_bridge.json"
PICK_PERF = DATA_DIR / "hyro_pick_performance.json"


def _skip_if_missing(path: Path):
    return pytest.mark.skipif(not path.exists(), reason=f"{path.name} absent")


@_skip_if_missing(ML_RANKINGS)
def test_hyro_ml_pick_rankings_shape():
    with ML_RANKINGS.open(encoding="utf-8") as fh:
        d = json.load(fh)
    assert isinstance(d, dict)
    required = {"generated_at", "scoring_method", "top_10"}
    missing = required - set(d.keys())
    assert not missing, f"hyro_ml_pick_rankings missing keys: {missing}"

    top = d.get("top_10") or d.get("top_picks") or []
    assert isinstance(top, list)
    if not top:
        pytest.skip("top_10 list empty")

    for i, entry in enumerate(top):
        assert isinstance(entry, dict), f"top[{i}] not a dict"
        for k in ("symbol", "score", "strategy"):
            assert k in entry, f"top[{i}] missing key {k!r}: {entry}"


@_skip_if_missing(QUAN_BRIDGE)
def test_hyro_quan_bridge_freshness():
    with QUAN_BRIDGE.open(encoding="utf-8") as fh:
        d = json.load(fh)
    assert isinstance(d, dict)
    required = {"generated_at", "data_source", "symbols"}
    missing = required - set(d.keys())
    assert not missing, f"hyro_quan_bridge missing keys: {missing}"

    # symbols must be a non-empty mapping (the live hyrotrader cross-check uses
    # this — empty symbols breaks the consensus gate at template.html:2626+).
    symbols = d["symbols"]
    assert isinstance(symbols, dict), \
        f"hyro_quan_bridge.symbols should be dict, got {type(symbols).__name__}"
    assert len(symbols) >= 1, "hyro_quan_bridge.symbols is empty"

    # Mtime freshness gate: warn (skip rather than fail) if > 7d stale because
    # this test should not break unrelated PRs — but record the signal.
    mtime = QUAN_BRIDGE.stat().st_mtime
    age_days = (time.time() - mtime) / 86400.0
    if age_days > 7.0:
        pytest.skip(
            f"hyro_quan_bridge.json is {age_days:.1f}d old — "
            f"refresh via .github/workflows/hyro-bridge-regen.yml"
        )


@_skip_if_missing(PICK_PERF)
def test_hyro_pick_performance_shape():
    with PICK_PERF.open(encoding="utf-8") as fh:
        d = json.load(fh)
    assert isinstance(d, dict)
    assert "strategy_scores" in d, "hyro_pick_performance missing strategy_scores"

    ss = d["strategy_scores"]
    # Accept either dict-keyed-by-strategy OR list-of-rows shape.
    rows = list(ss.values()) if isinstance(ss, dict) else ss
    assert isinstance(rows, list), f"strategy_scores rows should be list, got {type(rows).__name__}"
    if not rows:
        pytest.skip("strategy_scores empty")

    for i, row in enumerate(rows[:50]):  # spot-check first 50
        assert isinstance(row, dict), f"row[{i}] not a dict"
        # Required shape per tools/hyro_pick_performance_validator.py
        for k in ("win_rate", "total_signals"):
            assert k in row, f"strategy_scores row[{i}] missing key {k!r}"


def test_no_orphan_hyro_files():
    """Every hyro_*.json / hyrotrader_*.json file in audit_dashboard/data/
    must be in the KNOWN registry above (which means a reader/writer exists
    and was vetted on 2026-05-09). Add new files to KNOWN_HYRO_FILES when
    they ship.
    """
    if not DATA_DIR.exists():
        pytest.skip("audit_dashboard/data dir absent")
    actual = {
        p.name for p in DATA_DIR.iterdir()
        if p.is_file() and p.suffix == ".json"
        and (p.name.startswith("hyro_") or p.name.startswith("hyrotrader_"))
    }
    orphans = actual - KNOWN_HYRO_FILES
    assert not orphans, (
        f"undocumented hyro json artifacts: {sorted(orphans)} — add to "
        f"KNOWN_HYRO_FILES in {Path(__file__).name} after confirming a reader exists"
    )
