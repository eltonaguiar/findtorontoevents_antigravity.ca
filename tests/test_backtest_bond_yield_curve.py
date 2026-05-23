"""Tests for tools/backtest_bond_yield_curve.py.

Covers aggregate(), verdict(), and graceful-data-missing path.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "backtest_bond_yield_curve",
    REPO / "tools" / "backtest_bond_yield_curve.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)  # type: ignore[union-attr]


def test_aggregate_empty():
    out = mod.aggregate([])
    assert out["n"] == 0
    assert out["wr_pct"] == 0.0
    assert out["pf"] == 0.0
    assert out["mdd_pct"] == 0.0
    assert out["expectancy"] == 0.0


def test_aggregate_mixed_pf_and_wr():
    trades = [
        {"pnl_pct": 2.0},
        {"pnl_pct": 3.0},
        {"pnl_pct": -1.0},
        {"pnl_pct": -1.0},
    ]
    out = mod.aggregate(trades)
    assert out["n"] == 4
    assert out["wr_pct"] == 50.0
    # PF = (2+3)/(1+1) = 2.5
    assert out["pf"] == 2.5
    # expectancy = 3/4 = 0.75
    assert out["expectancy"] == 0.75


def test_aggregate_all_wins_returns_inf_pf():
    trades = [{"pnl_pct": 1.0}, {"pnl_pct": 2.0}]
    out = mod.aggregate(trades)
    assert out["wr_pct"] == 100.0
    assert out["pf"] == "inf"


def test_verdict_thresholds():
    assert mod.verdict("inf") == "PASS"
    assert mod.verdict(1.5) == "PASS"
    assert mod.verdict(2.0) == "PASS"
    assert mod.verdict(1.49) == "WARN"
    assert mod.verdict(1.0) == "WARN"
    assert mod.verdict(0.99) == "FAIL"
    assert mod.verdict(0.0) == "FAIL"


def test_signal_long_when_inverted_and_deepening():
    # 31 dates, spread starts at +0.10, ends at -0.20 (drop = 30bp, > 5bp threshold)
    dates = [f"2025-01-{i:02d}" for i in range(1, 32)]
    spread = {d: 0.10 - (i * 0.01) for i, d in enumerate(dates)}
    # idx 30 = last; lookback 30 → prev idx 0
    sig = mod._signal_for_date(spread, dates, 30)
    assert sig == "LONG"


def test_signal_short_when_positive_and_steepening():
    dates = [f"2025-02-{i:02d}" for i in range(1, 32)]
    # start at +0.05, rise to +0.25 → +20bp, positive
    spread = {d: 0.05 + (i * 0.0067) for i, d in enumerate(dates)}
    sig = mod._signal_for_date(spread, dates, 30)
    assert sig == "SHORT"


def test_signal_none_when_flat():
    dates = [f"2025-03-{i:02d}" for i in range(1, 32)]
    spread = {d: 0.50 for d in dates}
    assert mod._signal_for_date(spread, dates, 30) is None


def test_graceful_missing_spread_data(tmp_path, monkeypatch):
    """When all spread fetchers return None, main() must write DATA_GAP report."""
    monkeypatch.setattr(mod, "_fetch_spread_fred", lambda y: None)
    monkeypatch.setattr(mod, "_fetch_spread_yfinance_proxy", lambda yf, y: None)
    monkeypatch.setattr(mod, "_fetch_spread_tlt_momentum", lambda yf, y: None)

    class FakeYF:
        pass

    monkeypatch.setattr(mod, "_try_yfinance", lambda: FakeYF())
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["x", "--output", str(out), "--years", "1"])
    mod.main()
    content = out.read_text(encoding="utf-8")
    assert "DATA_GAP" in content


def test_graceful_no_yfinance(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_try_yfinance", lambda: None)
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["x", "--output", str(out), "--years", "1"])
    mod.main()
    content = out.read_text(encoding="utf-8")
    assert "DATA_GAP" in content
