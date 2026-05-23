"""Unit tests for the ETF relative-strength gate in non_crypto_agent.main.

The gate keeps only ETF picks whose 3-month relative performance vs SPY is in
the top half of the ranked ETF universe. Safe defaults: pass-through when SPY
data is missing or fewer than 60 bars are available.

Backed by multi_asset/FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md ETF
Relative Strength section (PF 1.55, Sharpe 2.57, 178 trades).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# alpha_engine must be importable for main.py's own imports (config, etc.)
sys.path.insert(0, str(ROOT / "alpha_engine"))

# Load non_crypto_agent/main.py by file path under a unique module name to
# avoid colliding with alpha_engine/main.py.
_NC_MAIN_PATH = ROOT / "non_crypto_agent" / "main.py"
_spec = importlib.util.spec_from_file_location("nc_agent_main", _NC_MAIN_PATH)
nc_main = importlib.util.module_from_spec(_spec)
sys.modules["nc_agent_main"] = nc_main
_spec.loader.exec_module(nc_main)


def _ohlcv(prices: list[float]) -> pd.DataFrame:
    idx = pd.date_range(end="2026-04-12", periods=len(prices), freq="D")
    arr = np.array(prices, dtype=float)
    return pd.DataFrame(
        {
            "Open": arr,
            "High": arr * 1.01,
            "Low": arr * 0.99,
            "Close": arr,
            "Volume": np.full(len(prices), 1_000_000),
        },
        index=idx,
    )


def _linear(start: float, end: float, n: int = 90) -> list[float]:
    return list(np.linspace(start, end, n))


def _build_universe(returns: dict[str, float], spy_return: float | None = 0.10):
    """Build a synthetic data dict.

    `returns` maps ETF symbol -> 60d total return (e.g. 0.20 = +20%).
    `spy_return` is the SPY 60d return (None to omit SPY entirely).

    All series have 90 bars so the 60-bar lookback (close[-1] / close[-60])
    yields the requested return.
    """
    data: dict[str, pd.DataFrame] = {}
    if spy_return is not None:
        # Tail 60 bars must rise from 1.0 -> 1+spy_return; pad with 30 leading
        # bars at the same starting price so len >= 60 holds at the lookback.
        tail = _linear(1.0, 1.0 + spy_return, 60)
        head = [1.0] * 30
        data["SPY"] = _ohlcv(head + tail)
    for sym, r in returns.items():
        tail = _linear(1.0, 1.0 + r, 60)
        head = [1.0] * 30
        data[sym] = _ohlcv(head + tail)
    return data


def test_strong_etf_top_three_passes():
    """An ETF in the top half of the 5-symbol universe should pass."""
    returns = {
        "XLK": 0.30,  # +30% — strongest
        "GLD": 0.25,  # +25%
        "XLF": 0.20,  # +20% — top half (3rd of 5; ceiling top half = 3)
        "XLV": 0.05,  # +5%  — bottom half
        "TLT": 0.00,  # flat — bottom half
    }
    data = _build_universe(returns, spy_return=0.10)
    ranking = nc_main.compute_etf_relative_strength_ranking(data)
    assert ranking is not None
    assert "XLK" in ranking
    assert "GLD" in ranking
    assert "XLF" in ranking

    ok, reason = nc_main.etf_relative_strength_gate(data, "XLK", ranking)
    assert ok is True, reason
    assert "leader" in reason.lower()


def test_weak_etf_bottom_two_blocked():
    """An ETF in the bottom half should be blocked."""
    returns = {
        "XLK": 0.30,
        "GLD": 0.25,
        "XLF": 0.20,
        "XLV": 0.05,
        "TLT": 0.00,
    }
    data = _build_universe(returns, spy_return=0.10)
    ranking = nc_main.compute_etf_relative_strength_ranking(data)
    assert ranking is not None
    assert "XLV" not in ranking
    assert "TLT" not in ranking

    ok, reason = nc_main.etf_relative_strength_gate(data, "XLV", ranking)
    assert ok is False, reason
    assert "below median" in reason.lower()

    ok2, _ = nc_main.etf_relative_strength_gate(data, "TLT", ranking)
    assert ok2 is False


def test_missing_spy_passes_safe_default():
    """If SPY is absent the ranking is None and the gate must pass-through."""
    returns = {
        "XLK": 0.30,
        "GLD": 0.25,
        "XLV": 0.05,
    }
    data = _build_universe(returns, spy_return=None)  # no SPY
    ranking = nc_main.compute_etf_relative_strength_ranking(data)
    assert ranking is None

    # Even a weak ETF should pass-through when SPY is missing
    ok, reason = nc_main.etf_relative_strength_gate(data, "XLV", ranking)
    assert ok is True
    assert "unavailable" in reason.lower()


def test_insufficient_bars_passes_safe_default():
    """If SPY has fewer than 60 bars the gate must pass-through."""
    short_spy = _ohlcv([1.0 + 0.001 * i for i in range(40)])  # only 40 bars
    data: dict[str, pd.DataFrame] = {"SPY": short_spy}
    # Add an ETF with plenty of bars — irrelevant since SPY is the gate
    data["XLK"] = _ohlcv(_linear(1.0, 1.30, 90))

    ranking = nc_main.compute_etf_relative_strength_ranking(data)
    assert ranking is None

    ok, reason = nc_main.etf_relative_strength_gate(data, "XLK", ranking)
    assert ok is True
    assert "unavailable" in reason.lower()


if __name__ == "__main__":
    test_strong_etf_top_three_passes()
    test_weak_etf_bottom_two_blocked()
    test_missing_spy_passes_safe_default()
    test_insufficient_bars_passes_safe_default()
    print("All ETF relative-strength gate tests passed.")
