"""Unit tests for mtf_rsi_confluence_gate.

Synthetic OHLCV cases:
  1. Clear LONG confluence (rising trend, neutral RSIs) -> pass
  2. LONG with overbought daily (vertical rally) -> block
  3. Missing data for symbol -> pass (safe default)
  4. SHORT with oversold higher-TF (collapse) -> block
  5. Clean SHORT (falling trend, neutral RSIs) -> pass
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "alpha_engine"))

from non_crypto_quality_gate import mtf_rsi_confluence_gate  # noqa: E402


def _make_df(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range(end="2026-04-12", periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.005 for c in closes],
            "Low": [c * 0.995 for c in closes],
            "Close": closes,
            "Volume": [1000] * len(closes),
        },
        index=idx,
    )


def _gentle_uptrend(n: int = 250, start: float = 100.0, drift: float = 0.05) -> list[float]:
    """Choppy mild uptrend that keeps both daily and weekly RSI in 45-65."""
    rng = np.random.default_rng(42)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] + drift + rng.normal(0, 1.5))
    return closes


def _vertical_rally(n: int = 250, start: float = 100.0) -> list[float]:
    """Choppy base, then a strong but noisy melt-up that drives daily RSI > 75
    while keeping weekly RSI in a "high but not extreme" 60-72 zone — which
    means the pick gets blocked by the signal-TF >75 rule."""
    rng = np.random.default_rng(11)
    base_n = n - 25
    closes = [start]
    for _ in range(base_n - 1):
        closes.append(closes[-1] + rng.normal(0, 1.0))
    last = closes[-1]
    # Strong rally with small pullbacks so avg_loss stays nonzero
    for i in range(25):
        step = 2.5 + rng.normal(0, 0.4)
        if i % 6 == 5:
            step = -0.6  # tiny pullback so RSI denominator isn't zero
        last = last + step
        closes.append(last)
    return closes


def _gentle_downtrend(n: int = 250, start: float = 200.0) -> list[float]:
    """Choppy near-sideways series with very mild bearish lean — keeps daily
    and weekly RSI in the 35-55 zone (no oversold, no overbought)."""
    rng = np.random.default_rng(3)
    closes = []
    for i in range(n):
        # Sinusoidal mean-reverting around start with noise
        wave = 5.0 * np.sin(i / 12.0)
        noise = rng.normal(0, 1.0)
        closes.append(max(1.0, start + wave + noise))
    return closes


def _collapse(n: int = 250, start: float = 200.0) -> list[float]:
    """Choppy base then sharp collapse driving weekly RSI < 30."""
    rng = np.random.default_rng(5)
    base_n = n - 60
    closes = [start]
    for _ in range(base_n - 1):
        closes.append(max(1.0, closes[-1] + rng.normal(0, 1.0)))
    last = closes[-1]
    for i in range(60):
        step = -3.0 + rng.normal(0, 0.4)
        if i % 7 == 6:
            step = 0.5
        last = max(1.0, last + step)
        closes.append(last)
    return closes


def test_long_clear_confluence_passes() -> None:
    data = {"AAA": _make_df(_gentle_uptrend())}
    ok, reason = mtf_rsi_confluence_gate(data, "AAA", "1d", "LONG")
    assert ok, f"expected pass, got block: {reason}"
    assert "OK" in reason or "passing" in reason


def test_long_overbought_daily_blocks() -> None:
    data = {"BBB": _make_df(_vertical_rally())}
    ok, reason = mtf_rsi_confluence_gate(data, "BBB", "1d", "LONG")
    assert not ok, f"expected block, got pass: {reason}"
    assert "LONG blocked" in reason


def test_missing_data_passes_safely() -> None:
    data: dict = {}
    ok, reason = mtf_rsi_confluence_gate(data, "MISSING", "1d", "LONG")
    assert ok, f"expected pass on missing data, got block: {reason}"
    assert "insufficient data" in reason or "passing" in reason


def test_short_oversold_higher_tf_blocks() -> None:
    data = {"CCC": _make_df(_collapse())}
    ok, reason = mtf_rsi_confluence_gate(data, "CCC", "1d", "SHORT")
    assert not ok, f"expected block, got pass: {reason}"
    assert "SHORT blocked" in reason


def test_short_clean_downtrend_passes() -> None:
    data = {"DDD": _make_df(_gentle_downtrend())}
    ok, reason = mtf_rsi_confluence_gate(data, "DDD", "1d", "SHORT")
    assert ok, f"expected pass, got block: {reason}"


def test_unknown_direction_passes() -> None:
    data = {"EEE": _make_df(_gentle_uptrend())}
    ok, reason = mtf_rsi_confluence_gate(data, "EEE", "1d", "FLAT")
    assert ok
    assert "unknown direction" in reason


if __name__ == "__main__":
    tests = [
        test_long_clear_confluence_passes,
        test_long_overbought_daily_blocks,
        test_missing_data_passes_safely,
        test_short_oversold_higher_tf_blocks,
        test_short_clean_downtrend_passes,
        test_unknown_direction_passes,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"\nAll {len(tests)} tests passed.")
