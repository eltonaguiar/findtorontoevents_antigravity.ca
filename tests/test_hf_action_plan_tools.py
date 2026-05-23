"""Tests for HF action plan tooling (walk-forward wrapper, equity backtest stub, weekly report)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_backtest_equity_catalyst_momentum_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(REPO / "tools" / "backtest_equity_catalyst_momentum.py"), "--dry-run"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "scaffold OK" in r.stdout


def test_generate_hf_weekly_audit_report_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "hf_weekly.json"
    r = subprocess.run(
        [sys.executable, str(REPO / "tools" / "generate_hf_weekly_audit_report.py"), "--output", str(out)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("version") == 1
    assert "generated_at_utc" in doc
    assert "sources_read" in doc


def test_build_report_empty_repo_dir(tmp_path: Path) -> None:
    import importlib.util

    path = REPO / "tools" / "generate_hf_weekly_audit_report.py"
    spec = importlib.util.spec_from_file_location("ghf_weekly", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.build_report(tmp_path)
    assert r["version"] == 1
    assert r["sources_read"] == []
    assert r["dashboard"] is None


def test_hf_quality_gates_config_has_action_plan_thresholds() -> None:
    from alpha_engine.hf_quality_gate import load_hf_quality_gates

    cfg = load_hf_quality_gates()
    # v2 (PR #660, 2026-05-03) replaced elite_score-based gating with
    # ml_score-based gating after elite_score showed -0.17 correlation
    # with profitability. Per-asset score floors live in
    # `per_asset_score_floors` instead of a single min_elite_score.
    assert cfg.get("version") == 2
    assert cfg.get("enabled") is True
    assert float(cfg.get("min_ml_score", 0)) == 0.82
    # min_risk_reward bumped 0.8 -> 1.25 (captures 85% of profitable
    # sub-1.5 trades while blocking RR < 1.0 toxicity).
    assert float(cfg.get("min_risk_reward", 0)) == 1.25
    # max_risk_reward bumped 2.0 -> 3.0 to allow asymmetric setups.
    assert float(cfg.get("max_risk_reward", 0)) == 3.0
    assert cfg.get("max_signal_age_hours") == 4
    # v2 introduces per-asset-class score floors; sanity-check the block.
    floors = cfg.get("per_asset_score_floors") or {}
    assert isinstance(floors, dict)
    for cls in ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF", "FUTURES"):
        assert cls in floors


def test_walk_forward_validate_module_loads() -> None:
    import importlib.util

    path = REPO / "tools" / "walk_forward_validate.py"
    spec = importlib.util.spec_from_file_location("wfval", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)


@pytest.mark.skipif(
    not (REPO / "audit_dashboard" / "data" / "dashboard_data.json").is_file(),
    reason="dashboard_data.json not present",
)
def test_walk_forward_validate_runs_when_dashboard_exists() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "walk_forward_validate.py"),
            "--max-oos-dd-pct",
            "99",
            "--min-sharpe",
            "-999",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 1)
