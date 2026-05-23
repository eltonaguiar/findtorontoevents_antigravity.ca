"""Tests for tools/backtest_crypto_onchain.py.

Covers aggregate(), verdict(), signal logic, proxy MVRV, and DATA_GAP fallback.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "backtest_crypto_onchain",
    REPO / "tools" / "backtest_crypto_onchain.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)  # type: ignore[union-attr]


def test_aggregate_mixed_pf_and_wr():
    trades = [
        {"pnl_pct": 3.0},
        {"pnl_pct": 2.0},
        {"pnl_pct": -1.0},
        {"pnl_pct": -1.0},
    ]
    out = mod.aggregate(trades)
    assert out["n"] == 4
    assert out["wr_pct"] == 50.0
    assert out["pf"] == 2.5
    assert out["expectancy"] == 0.75


def test_verdict_thresholds():
    assert mod.verdict("inf") == "PASS"
    assert mod.verdict(1.5) == "PASS"
    assert mod.verdict(1.0) == "WARN"
    assert mod.verdict(0.5) == "FAIL"


def test_signal_long_when_oversold_and_addr_rising():
    mvrv_map = {"2025-01-01": -1.0}
    addr_map = {"2025-01-01": 0.10}
    exch_map = {"2025-01-01": 0.0}
    assert mod._signal_for_date(mvrv_map, addr_map, exch_map, "2025-01-01") == "LONG"


def test_signal_short_when_overbought_and_exch_falling():
    mvrv_map = {"2025-01-01": 2.5}
    addr_map = {"2025-01-01": 0.0}
    exch_map = {"2025-01-01": -0.05}
    assert mod._signal_for_date(mvrv_map, addr_map, exch_map, "2025-01-01") == "SHORT"


def test_signal_none_when_neutral_mvrv():
    mvrv_map = {"2025-01-01": 0.5}
    addr_map = {"2025-01-01": 0.10}
    exch_map = {"2025-01-01": -0.10}
    assert mod._signal_for_date(mvrv_map, addr_map, exch_map, "2025-01-01") is None


def test_proxy_mvrv_zscore_negative_on_dip():
    # 180 slowly-rising prices then sharp dip to 50 -> very negative z at last
    # index. The window must have non-zero variance; flat 100s produce std=0
    # and the function correctly skips that index per its zero-variance guard
    # at tools/backtest_crypto_onchain.py line ~150.
    closes = [100.0 + 0.01 * i for i in range(180)] + [50.0]
    dates = [f"d{i}" for i in range(len(closes))]
    out = mod._build_proxy_mvrv(closes, dates)
    assert dates[-1] in out
    assert out[dates[-1]] < -1.0


def test_graceful_no_yfinance(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_try_yfinance", lambda: None)
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["x", "--output", str(out), "--years", "1"])
    mod.main()
    content = out.read_text(encoding="utf-8")
    assert "DATA_GAP" in content
