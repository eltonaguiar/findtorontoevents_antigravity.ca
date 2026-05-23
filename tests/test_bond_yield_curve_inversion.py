"""Tests for alpha_engine.bond_yield_curve_inversion.

Covers:
  - default-OFF gating via BOND_YIELD_CURVE_INVERSION_ENABLED
  - inversion + deepening triggers LONG TLT/IEF/SHY (asset_class=BOND, paper_only)
  - positive + steepening triggers SHORT TLT (+ TBT secondary)
  - inverted but NOT deepening => no signal
  - pick shape: required fields incl asset_class, paper_only, exit_rules, T10Y2Y
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from alpha_engine.bond_yield_curve_inversion import bond_yield_curve_inversion


def _mk_rows(values: list[float]) -> list[dict]:
    """Build {'date','value'} rows ending today, one per day, oldest first."""
    end = date(2026, 5, 11)
    n = len(values)
    return [
        {"date": (end - timedelta(days=n - 1 - i)).isoformat(), "value": float(v)}
        for i, v in enumerate(values)
    ]


def test_default_off_returns_empty(monkeypatch):
    monkeypatch.delenv("BOND_YIELD_CURVE_INVERSION_ENABLED", raising=False)
    # Even with a strong inversion signal, default-OFF returns nothing
    vals = [0.20] * 30 + [-0.50]  # inverted + huge 30d drop
    out = bond_yield_curve_inversion(rows=_mk_rows(vals))
    assert out == []


def test_long_signal_when_inverted_and_deepening(monkeypatch):
    monkeypatch.setenv("BOND_YIELD_CURVE_INVERSION_ENABLED", "1")
    # 30d ago = +0.10pp, now = -0.30pp -> delta = -40bp (deepening, inverted)
    vals = [0.10] * 30 + [-0.30]
    out = bond_yield_curve_inversion(rows=_mk_rows(vals))
    assert out, "expected at least one pick"
    p = out[0]
    assert p["strategy"] == "bond_yield_curve_inversion"
    assert p["signal_type"] == "BUY"
    assert p["asset_class"] == "BOND"
    assert p["paper_only"] is True
    assert p["symbol"] in {"TLT", "IEF", "SHY"}
    assert p["timeframe"] == "12h"
    assert p["extra"]["series"] == "T10Y2Y"
    assert p["extra"]["delta_30d_bp"] < -5.0
    assert 0.55 <= p["confidence"] <= 0.70
    assert p["exit_rules"]["max_hold_days"] == 90
    symbols = {x["symbol"] for x in out}
    assert {"TLT", "IEF", "SHY"}.issubset(symbols)


def test_short_signal_when_steepening_from_positive(monkeypatch):
    monkeypatch.setenv("BOND_YIELD_CURVE_INVERSION_ENABLED", "1")
    # 30d ago = +0.05pp, now = +0.40pp -> +35bp rise (steepening)
    vals = [0.05] * 30 + [0.40]
    out = bond_yield_curve_inversion(rows=_mk_rows(vals))
    assert out and out[0]["signal_type"] == "SELL"
    symbols = {x["symbol"] for x in out}
    assert "TLT" in symbols and "TBT" in symbols
    # No defensive SHY on the SHORT side
    assert "SHY" not in symbols


def test_no_signal_when_inverted_but_not_deepening(monkeypatch):
    monkeypatch.setenv("BOND_YIELD_CURVE_INVERSION_ENABLED", "1")
    # inverted but flat (delta ~0bp)
    vals = [-0.15] * 31
    out = bond_yield_curve_inversion(rows=_mk_rows(vals))
    assert out == []


def test_insufficient_history_returns_empty(monkeypatch):
    monkeypatch.setenv("BOND_YIELD_CURVE_INVERSION_ENABLED", "1")
    vals = [-0.10] * 10  # < 31 rows
    out = bond_yield_curve_inversion(rows=_mk_rows(vals))
    assert out == []


def test_family_registration_macro():
    from alpha_engine.config import STRATEGY_FAMILIES, INDICATOR_FAMILIES
    assert STRATEGY_FAMILIES.get("bond_yield_curve_inversion") == "macro"
    assert "macro" in INDICATOR_FAMILIES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
