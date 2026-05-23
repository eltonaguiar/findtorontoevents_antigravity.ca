"""PR-D (2026-05-12) — FOREX hard-cap sizing gate.

Per CLAUDE.md FOREX directive + docs/MUTATION_THREE_AXIS_PROTOCOL.md:
explicit per-class gate, NOT BLOCKED_SOURCE_SYSTEMS extension. Cap until
asset_class_health.FOREX.profit_factor >= FOREX_SIZING_PF_FLOOR (0.8).

Block reason must be auditable for /audit display.
"""

from __future__ import annotations

from alpha_engine.risk_policy_check import (
    FOREX_SIZING_PF_FLOOR,
    is_forex_sizing_allowed,
)


def test_forex_pf_below_floor_blocked_with_reason():
    """FOREX PF 0.28 (current live state) -> blocked with auditable reason."""
    health = {"FOREX": {"profit_factor": 0.28, "win_rate": 46.4, "resolved_n": 1169}}
    allowed, reason = is_forex_sizing_allowed(health)
    assert allowed is False
    assert reason
    assert "FOREX hard-cap" in reason
    assert "0.28" in reason
    assert str(FOREX_SIZING_PF_FLOOR) in reason
    assert "PR-D" in reason


def test_forex_pf_above_floor_allowed():
    """FOREX PF 0.85 (recovered) -> allowed, empty reason."""
    health = {"FOREX": {"profit_factor": 0.85, "win_rate": 51.0, "resolved_n": 1200}}
    allowed, reason = is_forex_sizing_allowed(health)
    assert allowed is True
    assert reason == ""


def test_forex_pf_exactly_at_floor_allowed():
    """FOREX PF == 0.8 -> allowed (>= boundary, not strict >)."""
    health = {"FOREX": {"profit_factor": FOREX_SIZING_PF_FLOOR, "resolved_n": 1200}}
    allowed, reason = is_forex_sizing_allowed(health)
    assert allowed is True
    assert reason == ""


def test_non_forex_class_untouched():
    """Gate only inspects FOREX; CRYPTO / EQUITY / etc. pass through."""
    health = {
        "CRYPTO": {"profit_factor": 0.25, "resolved_n": 8000},
        "EQUITY": {"profit_factor": 0.10, "resolved_n": 400},
        "COMMODITY": {"profit_factor": 0.50, "resolved_n": 750},
    }
    allowed, reason = is_forex_sizing_allowed(health)
    assert allowed is True
    assert reason == ""


def test_missing_forex_entry_allowed():
    """No FOREX key -> gate silent, allowed."""
    assert is_forex_sizing_allowed({}) == (True, "")
    assert is_forex_sizing_allowed({"CRYPTO": {"profit_factor": 1.2}}) == (True, "")


def test_forex_pf_none_allowed():
    """PF missing/None -> no signal, allowed (don't block on absent data)."""
    allowed, reason = is_forex_sizing_allowed({"FOREX": {"profit_factor": None}})
    assert allowed is True
    assert reason == ""
    allowed, reason = is_forex_sizing_allowed({"FOREX": {}})
    assert allowed is True
    assert reason == ""


def test_invalid_input_safe():
    """Bad inputs degrade safely to allowed (gate is observability, not safety net)."""
    assert is_forex_sizing_allowed(None) == (True, "")  # type: ignore[arg-type]
    assert is_forex_sizing_allowed("nope") == (True, "")  # type: ignore[arg-type]
    assert is_forex_sizing_allowed({"FOREX": "bad"}) == (True, "")
    assert is_forex_sizing_allowed({"FOREX": {"profit_factor": "junk"}}) == (True, "")
