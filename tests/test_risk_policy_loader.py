"""Tests for alpha_engine.risk_policy_loader."""

import json
from pathlib import Path

from alpha_engine.risk_policy_loader import load_risk_policy


def test_load_default_from_repo_file(tmp_path: Path) -> None:
    # Updated 2026-05-12: risk policy tightened to v2 (per_trade_cap_pct 5->3)
    # by PR #885 (risk_policy v2 crypto caps). Tests updated to match
    # production reality.
    p = load_risk_policy()
    assert p["version"] == 2
    assert p["crypto"]["per_trade_cap_pct"] == 3


def test_load_missing_file_uses_fallback(tmp_path: Path) -> None:
    p = load_risk_policy(tmp_path / "nope.json")
    # Fallback returns current default policy (post-v2 tightening).
    assert p["crypto"]["per_trade_cap_pct"] == 3


def test_load_custom_override(tmp_path: Path) -> None:
    f = tmp_path / "rp.json"
    f.write_text(
        json.dumps({"version": 2, "crypto": {"per_trade_cap_pct": 3}}),
        encoding="utf-8",
    )
    p = load_risk_policy(f)
    assert p["version"] == 2
    assert p["crypto"]["per_trade_cap_pct"] == 3
    # max_equity_pct_per_symbol comes from default merge, now 5 (post-v2).
    assert p["crypto"]["max_equity_pct_per_symbol"] == 5
