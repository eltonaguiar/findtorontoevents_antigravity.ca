#!/usr/bin/env python3
"""
Cross-Sectional Ranking Features for Alpha Engine Scanner
==========================================================
Instead of predicting "will BTC go up?", rank "which of N coins will
outperform?" -- ranking is easier than absolute forecasting.

Academic basis: Liu, Tsyvinski & Wu (2022, JFE) confirm cross-sectional
momentum works in crypto with Sharpe ~2.1.

This module computes per-symbol features RELATIVE to all tracked symbols,
designed to be injected onto signal dicts before ML ranking.

Features produced:
  - cs_momentum_rank: percentile rank of 7d return [0, 1]
  - cs_relative_strength: 7d return minus BTC 7d return [-1, 1] (clipped)
  - cs_dispersion: std dev of all symbols' 7d returns [0, 1] (normalized)
  - cs_leader_lag: correlation of symbol's returns with BTC lagged returns [-1, 1]
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_return(series: pd.Series, periods: int = 7) -> float:
    """Compute return over N periods, NaN-safe."""
    if series is None or len(series) < periods + 1:
        return 0.0
    try:
        start = series.iloc[-(periods + 1)]
        end = series.iloc[-1]
        if start is None or end is None or start == 0:
            return 0.0
        ret = (float(end) - float(start)) / float(start)
        if math.isnan(ret) or math.isinf(ret):
            return 0.0
        return ret
    except (TypeError, ValueError, IndexError):
        return 0.0


def compute_cross_sectional_features(
    prices_dict: dict[str, pd.DataFrame],
    symbol: str,
    lookback_days: int = 7,
) -> dict[str, float]:
    """Compute how a symbol ranks relative to all tracked symbols.

    Args:
        prices_dict: {symbol: DataFrame with at least a 'Close' column}
        symbol: the symbol to compute features for
        lookback_days: return lookback period (default 7)

    Returns dict with:
        - cs_momentum_rank: percentile rank of 7d return (0=worst, 1=best)
        - cs_relative_strength: symbol 7d return minus BTC 7d return, clipped [-1, 1]
        - cs_dispersion: std dev of all symbols' 7d returns, normalized [0, 1]
        - cs_leader_lag: correlation of symbol's 1d returns with BTC's lagged 1d returns [-1, 1]
    """
    result = {
        "cs_momentum_rank": 0.5,       # neutral default
        "cs_relative_strength": 0.0,   # no edge default
        "cs_dispersion": 0.5,          # middle default
        "cs_leader_lag": 0.0,          # no correlation default
    }

    # Need at least the target symbol's data
    if symbol not in prices_dict:
        return result

    target_df = prices_dict[symbol]
    if target_df is None or len(target_df) < lookback_days + 1:
        return result

    if "Close" not in target_df.columns:
        return result

    target_close = target_df["Close"].dropna()
    if len(target_close) < lookback_days + 1:
        return result

    # ---- Step 1: Compute returns for all symbols ----
    all_returns: dict[str, float] = {}
    for sym, df in prices_dict.items():
        if df is None or len(df) < lookback_days + 1:
            continue
        if "Close" not in df.columns:
            continue
        close = df["Close"].dropna()
        ret = _safe_return(close, lookback_days)
        all_returns[sym] = ret

    if symbol not in all_returns or len(all_returns) < 2:
        return result

    target_return = all_returns[symbol]
    returns_array = np.array(list(all_returns.values()))

    # ---- Feature 1: cs_momentum_rank ----
    # Percentile rank: fraction of symbols with return <= target
    n_total = len(returns_array)
    n_below = np.sum(returns_array <= target_return)
    rank = float(n_below) / float(n_total)
    # Clamp to [0, 1]
    result["cs_momentum_rank"] = max(0.0, min(1.0, rank))

    # ---- Feature 2: cs_relative_strength (vs BTC) ----
    # Find BTC symbol (try common variants)
    btc_return = _find_benchmark_return(all_returns, ["BTC-USD", "BTCUSDT", "BTCUSD"])
    if btc_return is not None:
        rel_strength = target_return - btc_return
        # Clip to [-1, 1] for ML stability
        result["cs_relative_strength"] = max(-1.0, min(1.0, rel_strength))

    # ---- Feature 3: cs_dispersion ----
    # Std dev of all symbols' returns = market breadth/dispersion
    # High dispersion = opportunity for cross-sectional alpha
    # Normalize: typical crypto weekly vol std is 0.05-0.20, cap at 0.30
    dispersion = float(np.std(returns_array))
    if math.isnan(dispersion) or math.isinf(dispersion):
        dispersion = 0.0
    # Normalize to [0, 1]: divide by 0.30 (empirical cap for crypto weekly)
    result["cs_dispersion"] = max(0.0, min(1.0, dispersion / 0.30))

    # ---- Feature 4: cs_leader_lag ----
    # Correlation of symbol's daily returns with BTC's lagged daily returns
    # Positive = symbol follows BTC (can use BTC as leading indicator)
    # Negative = symbol moves opposite to lagged BTC
    btc_close = _find_benchmark_close(prices_dict, ["BTC-USD", "BTCUSDT", "BTCUSD"])
    if btc_close is not None:
        result["cs_leader_lag"] = _compute_leader_lag(
            target_close, btc_close, min_periods=10
        )

    return result


def compute_cross_sectional_batch(
    prices_dict: dict[str, pd.DataFrame],
    symbols: list[str],
    lookback_days: int = 7,
) -> dict[str, dict[str, float]]:
    """Compute cross-sectional features for multiple symbols efficiently.

    Pre-computes shared data (all returns, BTC close) once, then
    produces per-symbol feature dicts.

    Args:
        prices_dict: {symbol: DataFrame with Close column}
        symbols: list of symbols to compute for
        lookback_days: return lookback (default 7)

    Returns:
        {symbol: {feature_name: value}} for each symbol in symbols
    """
    batch_results: dict[str, dict[str, float]] = {}

    # Pre-compute all returns once
    all_returns: dict[str, float] = {}
    for sym, df in prices_dict.items():
        if df is None or len(df) < lookback_days + 1:
            continue
        if "Close" not in df.columns:
            continue
        close = df["Close"].dropna()
        ret = _safe_return(close, lookback_days)
        all_returns[sym] = ret

    returns_array = np.array(list(all_returns.values())) if all_returns else np.array([])
    n_total = len(returns_array)

    # Pre-compute shared benchmarks
    btc_return = _find_benchmark_return(all_returns, ["BTC-USD", "BTCUSDT", "BTCUSD"])
    btc_close = _find_benchmark_close(prices_dict, ["BTC-USD", "BTCUSDT", "BTCUSD"])

    # Dispersion is the same for all symbols (market-wide stat)
    dispersion = 0.0
    if n_total >= 2:
        dispersion = float(np.std(returns_array))
        if math.isnan(dispersion) or math.isinf(dispersion):
            dispersion = 0.0
    cs_dispersion = max(0.0, min(1.0, dispersion / 0.30))

    defaults = {
        "cs_momentum_rank": 0.5,
        "cs_relative_strength": 0.0,
        "cs_dispersion": cs_dispersion,
        "cs_leader_lag": 0.0,
    }

    for sym in symbols:
        if sym not in all_returns or n_total < 2:
            batch_results[sym] = dict(defaults)
            continue

        feat = dict(defaults)
        target_return = all_returns[sym]

        # Momentum rank
        n_below = int(np.sum(returns_array <= target_return))
        feat["cs_momentum_rank"] = max(0.0, min(1.0, float(n_below) / float(n_total)))

        # Relative strength vs BTC
        if btc_return is not None:
            rel = target_return - btc_return
            feat["cs_relative_strength"] = max(-1.0, min(1.0, rel))

        # Leader-lag with BTC
        if btc_close is not None and sym in prices_dict:
            sym_df = prices_dict[sym]
            if sym_df is not None and "Close" in sym_df.columns:
                sym_close = sym_df["Close"].dropna()
                feat["cs_leader_lag"] = _compute_leader_lag(
                    sym_close, btc_close, min_periods=10
                )

        batch_results[sym] = feat

    return batch_results


def inject_cross_sectional_features(
    signals: list[dict],
    prices_dict: dict[str, pd.DataFrame],
) -> list[dict]:
    """Inject cross-sectional features onto each signal dict.

    Called from scanner.py after fetching price data. Computes batch
    features and adds cs_momentum_rank, cs_relative_strength,
    cs_dispersion, cs_leader_lag to each signal.

    Args:
        signals: list of signal dicts (must have 'symbol' key)
        prices_dict: {symbol: DataFrame with Close}

    Returns:
        signals list with cross-sectional features injected
    """
    if not signals or not prices_dict:
        return signals

    # Gather unique symbols from signals
    unique_symbols = list({s.get("symbol", "") for s in signals if s.get("symbol")})
    if not unique_symbols:
        return signals

    # Batch compute
    try:
        batch = compute_cross_sectional_batch(prices_dict, unique_symbols)
    except Exception as e:
        logger.warning("Cross-sectional batch computation failed: %s", e)
        # Set defaults on all signals
        for sig in signals:
            sig.setdefault("cs_momentum_rank", 0.5)
            sig.setdefault("cs_relative_strength", 0.0)
            sig.setdefault("cs_dispersion", 0.5)
            sig.setdefault("cs_leader_lag", 0.0)
        return signals

    injected = 0
    for sig in signals:
        sym = sig.get("symbol", "")
        feats = batch.get(sym, {})
        sig["cs_momentum_rank"] = feats.get("cs_momentum_rank", 0.5)
        sig["cs_relative_strength"] = feats.get("cs_relative_strength", 0.0)
        sig["cs_dispersion"] = feats.get("cs_dispersion", 0.5)
        sig["cs_leader_lag"] = feats.get("cs_leader_lag", 0.0)
        injected += 1

    logger.info("Cross-sectional features injected: %d/%d signals", injected, len(signals))
    print(f"  Cross-sectional ranking: {injected}/{len(signals)} signals enriched "
          f"({len(unique_symbols)} symbols, {len(prices_dict)} in universe)")

    return signals


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_benchmark_return(
    all_returns: dict[str, float],
    candidates: list[str],
) -> Optional[float]:
    """Find BTC (or other benchmark) return from candidates list."""
    for sym in candidates:
        if sym in all_returns:
            return all_returns[sym]
    return None


def _find_benchmark_close(
    prices_dict: dict[str, pd.DataFrame],
    candidates: list[str],
) -> Optional[pd.Series]:
    """Find BTC (or other benchmark) close series from candidates list."""
    for sym in candidates:
        if sym in prices_dict:
            df = prices_dict[sym]
            if df is not None and "Close" in df.columns:
                return df["Close"].dropna()
    return None


def _compute_leader_lag(
    target_close: pd.Series,
    btc_close: pd.Series,
    lag: int = 1,
    min_periods: int = 10,
) -> float:
    """Compute correlation of target's returns with BTC's lagged returns.

    A positive value means the symbol tends to follow BTC's moves
    with a delay (BTC leads, symbol lags).

    Args:
        target_close: symbol's close price series
        btc_close: BTC's close price series
        lag: number of periods to lag BTC returns (default 1)
        min_periods: minimum overlapping points for valid correlation

    Returns:
        correlation [-1, 1], or 0.0 if insufficient data
    """
    try:
        # Compute daily returns
        target_ret = target_close.pct_change().dropna()
        btc_ret = btc_close.pct_change().dropna()

        if len(target_ret) < min_periods + lag or len(btc_ret) < min_periods + lag:
            return 0.0

        # Lag BTC returns (shift forward = BTC's past vs symbol's present)
        btc_lagged = btc_ret.shift(lag).dropna()

        # Align on common index
        common_idx = target_ret.index.intersection(btc_lagged.index)
        if len(common_idx) < min_periods:
            return 0.0

        target_aligned = target_ret.loc[common_idx]
        btc_aligned = btc_lagged.loc[common_idx]

        corr = float(target_aligned.corr(btc_aligned))

        if math.isnan(corr) or math.isinf(corr):
            return 0.0

        return max(-1.0, min(1.0, corr))

    except Exception:
        return 0.0
