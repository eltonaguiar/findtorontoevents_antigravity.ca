# -*- coding: utf-8 -*-
"""Lock the G8/DSR/gate contract that main already implements.

The `fix/audit3-alpha-scope` branch proposed these gates; main independently
arrived at the same mechanism in a stricter form (see
updates/2026-11-19-audit3-g8-dsr-port-assessment.md). These tests exist so the two
properties that make the gates honest cannot be flipped later without noticing:

1. ``require_alpha`` defaults to **False** for library callers — an audit helper
   must fail open in code and never block an emitter.
2. The published CLI path passes ``require_alpha=True`` — so the *published*
   ledger cannot call an unmeasured selection alpha "proven".
"""
from __future__ import annotations

import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from alpha_engine.audit3_tribunal import apply_selection_alpha_gate, build_report  # noqa: E402


def test_require_alpha_defaults_off_for_library_callers():
    params = inspect.signature(build_report).parameters
    assert "require_alpha" in params
    assert params["require_alpha"].default is False


def test_published_cli_path_opts_in_to_require_alpha():
    src = (REPO_ROOT / "alpha_engine" / "audit3_tribunal.py").read_text(encoding="utf-8")
    assert "require_alpha=True" in src, "the published path must not fail open on alpha"


def test_g8_demotes_a_strategy_cell_proven_only_by_class_alpha():
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "n": 120, "verdict": "PROVEN_T2", "reasons": []}
    summary = apply_selection_alpha_gate(
        [cell], {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [0.5, 1.0]}},
                 "by_strategy": {}})
    assert summary["demoted"] == 1
    assert cell["verdict"] == "CANDIDATE"
    assert cell["alpha_gate"]["scope"] == "class_proxy"
    assert cell["alpha_gate"]["passed"] is False


def test_g8_accepts_same_scope_strategy_alpha():
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "n": 120, "verdict": "PROVEN_T2", "reasons": []}
    summary = apply_selection_alpha_gate(
        [cell], {"by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-1.0, 1.0]}},
                 "by_strategy": {"CRYPTO/s1/LONG": {"n": 120, "alpha_ci": [0.2, 0.9]}}})
    assert summary["demoted"] == 0
    assert cell["verdict"] == "PROVEN_T2"
    assert cell["alpha_gate"]["scope"] == "strategy"

def _alpha_rows(n: int):
    return [{
        "id": f"s1-{i}",
        "asset_class": "CRYPTO",
        "strategy": "s1",
        "direction": "LONG",
        "symbol": "BTCUSDT",
        "source_system": "alpha_engine",
        "status": "WON" if i % 2 == 0 else "LOST",
        "pnl_pct": 0.5 if i % 2 == 0 else -0.2,
        "closed_at": f"2026-11-{1 + i % 18:02d}T00:00:00+00:00",
    } for i in range(n)]


def test_build_report_publishes_alpha_gate_and_by_strategy():
    """The published ledger must expose both the gate report and strategy alpha.

    Regression: the gate was called but its summary discarded, and by_strategy
    was dropped from the passthrough keys, so /audit3 could not show whether G8
    ran or at what scope.
    """
    alpha = {
        "by_class": {"CRYPTO": {"n": 200, "alpha_ci": [-1.0, 1.0]}},
        "by_strategy": {"CRYPTO/s1/LONG": {"n": 60, "alpha_ci": [0.2, 0.9]}},
    }
    report = build_report(_alpha_rows(60), "synthetic", None, alpha=alpha)
    sa = report["selection_alpha"]
    assert sa["gate"]["applied"] is True
    assert sa["gate"]["tested"] >= 1
    assert "by_strategy" in sa
    assert "CRYPTO/s1/LONG" in sa["by_strategy"]
