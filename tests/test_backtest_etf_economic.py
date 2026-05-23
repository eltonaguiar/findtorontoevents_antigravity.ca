"""Tests for tools/backtest_etf_economic.py.

Covers aggregate(), verdict(), signal_from_fred logic, and data-gap path.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "backtest_etf_economic",
    REPO / "tools" / "backtest_etf_economic.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)  # type: ignore[union-attr]


def test_aggregate_pf_wr_mdd():
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
    # Equity path 2,5,4,3. Peak 5, trough 3 → MDD 2.0
    assert out["mdd_pct"] == 2.0


def test_verdict_thresholds():
    assert mod.verdict("inf") == "PASS"
    assert mod.verdict(1.5) == "PASS"
    assert mod.verdict(1.49) == "WARN"
    assert mod.verdict(1.0) == "WARN"
    assert mod.verdict(0.99) == "FAIL"


def test_signal_from_fred_long_short_neutral():
    # Build 16 quarterly GDP points rising steeply (latest is high z)
    gdp_dates = [f"20{y:02d}-{m:02d}-01" for y in range(20, 26) for m in (1, 4, 7, 10)]
    gdp_dates = gdp_dates[:16]
    gdp_long = {d: 100.0 + i for i, d in enumerate(gdp_dates)}
    # M2 13 monthly points, rising (positive YoY)
    m2_dates = [f"2025-{m:02d}-01" for m in range(1, 13)] + ["2026-01-01"]
    m2 = {d: 1000.0 + i * 5 for i, d in enumerate(m2_dates)}
    # NAPM > 50 for LONG case
    napm_long = {"2026-01-01": 55.0}

    asof = "2026-02-15"
    long_data = {"NAPM": napm_long, "M2SL": m2, "GDPC1": gdp_long}
    assert mod.signal_from_fred(long_data, asof) == "LONG"

    # SHORT: ISM < 50, GDP declining (negative z)
    gdp_short = {d: 100.0 - i for i, d in enumerate(gdp_dates)}
    napm_short = {"2026-01-01": 45.0}
    short_data = {"NAPM": napm_short, "M2SL": m2, "GDPC1": gdp_short}
    assert mod.signal_from_fred(short_data, asof) == "SHORT"

    # NEUTRAL: ISM=50 mid-band, flat GDP
    gdp_flat = {d: 100.0 for d in gdp_dates}
    napm_mid = {"2026-01-01": 50.0}
    flat_data = {"NAPM": napm_mid, "M2SL": m2, "GDPC1": gdp_flat}
    assert mod.signal_from_fred(flat_data, asof) is None


def test_graceful_no_yfinance(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_try_yfinance", lambda: None)
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["x", "--output", str(out), "--years", "1"])
    mod.main()
    content = out.read_text(encoding="utf-8")
    assert "DATA_GAP" in content
