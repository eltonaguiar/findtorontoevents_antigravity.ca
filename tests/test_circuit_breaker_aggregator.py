"""Regression tests for alpha_engine.circuit_breaker_aggregator.

The 2026-04-27 incident: ``circuit_breaker_state.json`` was 5 weeks stale with
``level=HALT, max_picks=0, min_confidence=1.0``. The aggregator's staleness
check (>2h old → force level=GREEN) reset the *level* but the override step
``min(max_picks, pf_state.get("max_picks"))`` still pulled the stale ``0``,
silently locking pick generation while reporting "Level: GREEN".

These tests pin the fix so the bug can't regress.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import alpha_engine.circuit_breaker_aggregator as cba


def _write_state(path: Path, payload: dict, age_hours: float | None) -> None:
    """Write a CB state file. ``age_hours=None`` omits the timestamp (which the
    aggregator reads as 999h-stale). Otherwise embeds ``timestamp`` so the
    aggregator's age computation sees the requested age."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    if age_hours is not None:
        ts = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        payload["timestamp"] = ts.isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_stale_halt_state_does_not_leak_max_picks(tmp_path, monkeypatch):
    """A 5-week-stale HALT state must NOT lock pick generation.

    Reproduces the 2026-04-27 alpha_engine_fast 115h-no-picks bug.
    """
    dd = tmp_path / "drawdown_circuit_breaker.json"
    pf = tmp_path / "circuit_breaker_state.json"
    macro = tmp_path / "macro_circuit_breaker.json"

    # Simulate the bug repro: pf_state is 5 weeks old, level=HALT, max_picks=0
    _write_state(
        pf,
        {
            "level": "HALT",
            "max_picks": 0,
            "min_confidence": 1.0,
            "reason": "ancient loss streak",
        },
        age_hours=5 * 7 * 24,  # 5 weeks
    )
    # Other states fresh & GREEN
    _write_state(dd, {"level": "GREEN"}, age_hours=0.1)
    _write_state(macro, {"level": "GREEN"}, age_hours=0.1)

    monkeypatch.setattr(cba, "DRAWDOWN_CB_PATH", dd)
    monkeypatch.setattr(cba, "PORTFOLIO_CB_PATH", pf)
    monkeypatch.setattr(cba, "MACRO_CB_PATH", macro)

    out = cba.get_unified_breaker_state()
    assert out["level"] == "GREEN", "stale HALT state must not bubble up to overall level"
    assert out["max_picks"] == 100, (
        f"GREEN default max_picks=100 must apply; got {out['max_picks']} "
        "(stale max_picks=0 leaked through min())"
    )
    assert out["min_confidence"] == 0.55, (
        f"GREEN default min_confidence=0.55 must apply; got {out['min_confidence']} "
        "(stale min_confidence=1.0 leaked through max())"
    )


def test_fresh_red_portfolio_state_still_restricts(tmp_path, monkeypatch):
    """A fresh non-GREEN state still reduces max_picks correctly.

    Sanity check that the staleness fix didn't disable real overrides.
    """
    dd = tmp_path / "drawdown_circuit_breaker.json"
    pf = tmp_path / "circuit_breaker_state.json"
    macro = tmp_path / "macro_circuit_breaker.json"

    _write_state(
        pf,
        {
            "level": "YELLOW",
            "max_picks": 10,
            "min_confidence": 0.90,
            "reason": "real drawdown event",
        },
        age_hours=0.5,  # fresh
    )
    _write_state(dd, {"level": "GREEN"}, age_hours=0.1)
    _write_state(macro, {"level": "GREEN"}, age_hours=0.1)

    monkeypatch.setattr(cba, "DRAWDOWN_CB_PATH", dd)
    monkeypatch.setattr(cba, "PORTFOLIO_CB_PATH", pf)
    monkeypatch.setattr(cba, "MACRO_CB_PATH", macro)

    out = cba.get_unified_breaker_state()
    assert out["level"] == "YELLOW", "fresh YELLOW pf must lift level to YELLOW"
    assert out["max_picks"] <= 10, "fresh max_picks=10 override must apply"
    assert out["min_confidence"] >= 0.90, "fresh min_confidence=0.90 override must apply"
