"""
Equity Momentum with Regime Filter (H-037 candidate).

Fully point-in-time — no lookahead anywhere:
- Rolling vol computed with .rolling(252).std().shift(1) (not global .std())
- Quantile threshold computed on rolling window, not full-df quantile
- Momentum lookback uses .shift(1) to avoid current-bar leakage

Grok v1/v2/v3 bugs fixed:
- vol benchmark was df['close'].pct_change(252).std() — global stat, leaks future
- regime comparison used same full-df std as threshold — double lookahead
- correct fix is rolling(252).std().shift(1) for the benchmark
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd


def equity_momentum_regime_signal(
    df: pd.DataFrame,
    mom_lookback: int = 5,
    vol_window: int = 252,
    current_vol_window: int = 21,
    low_vol_pct: float = 0.8,
    score_quantile: float = 0.75,
) -> pd.Series:
    """
    Returns a boolean Series: True at bars where EQUITY momentum signal fires.

    Point-in-time guarantees:
    - current_vol uses rolling(current_vol_window).std() — no future data
    - vol_benchmark uses rolling(vol_window).std().shift(1) — t-1 data only
    - regime indicator is based only on past bars at each t
    - score quantile threshold computed on rolling window, not full-df

    Args:
        df: DataFrame with a 'close' column, indexed by date.
        mom_lookback: Short-term momentum window in bars.
        vol_window: Annualization window for vol benchmark (default 252 = 1yr daily).
        current_vol_window: Window for current realized vol (default 21 = 1mo).
        low_vol_pct: Regime is "low vol" if current_vol < benchmark * this factor.
        score_quantile: Signal fires when score > rolling quantile of this percentile.

    Returns:
        Boolean pd.Series aligned to df.index.
    """
    if "close" not in df.columns:
        raise ValueError("df must contain a 'close' column")

    daily_ret = df["close"].pct_change()

    # Short-term momentum (shift to avoid current-bar leakage)
    mom = daily_ret.rolling(mom_lookback).sum().shift(1)

    # Current realized vol (annualized) — no lookahead
    current_vol = daily_ret.rolling(current_vol_window).std() * np.sqrt(252)

    # Vol benchmark: trailing 1-year realized vol, shifted 1 bar to ensure
    # at time t we only see data through t-1
    vol_benchmark = daily_ret.rolling(vol_window).std().shift(1) * np.sqrt(252)

    # Regime: 1 in low-vol environment, 0 in high-vol environment
    # low_vol_pct=0.8 means current vol < 80% of 1-year benchmark
    regime = (current_vol < vol_benchmark * low_vol_pct).astype(float)

    # Composite score: momentum boosted in low-vol regime
    score = mom * (1.0 + regime * 0.3)

    # Point-in-time quantile threshold: rolling window prevents future extremes
    score_threshold = score.rolling(vol_window).quantile(score_quantile).shift(1)

    return score > score_threshold


def equity_momentum_regime_score(
    df: pd.DataFrame,
    mom_lookback: int = 5,
    vol_window: int = 252,
    current_vol_window: int = 21,
    low_vol_pct: float = 0.8,
) -> pd.Series:
    """
    Continuous score version (0-1 range, suitable for ranking).
    Same point-in-time guarantees as the signal version.
    """
    daily_ret = df["close"].pct_change()
    mom = daily_ret.rolling(mom_lookback).sum().shift(1)
    current_vol = daily_ret.rolling(current_vol_window).std() * np.sqrt(252)
    vol_benchmark = daily_ret.rolling(vol_window).std().shift(1) * np.sqrt(252)
    regime = (current_vol < vol_benchmark * low_vol_pct).astype(float)
    score = mom * (1.0 + regime * 0.3)

    # Rank-normalize within a rolling window for cross-sectional comparison
    rolling_min = score.rolling(vol_window).min().shift(1)
    rolling_max = score.rolling(vol_window).max().shift(1)
    score_range = rolling_max - rolling_min
    normalized = (score - rolling_min) / score_range.replace(0, np.nan)
    return normalized.clip(0.0, 1.0).fillna(0.5)
