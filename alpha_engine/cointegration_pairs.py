"""
ALPHA_ENGINE -- Cointegration-Based Pairs Trading
===================================================
Two strategies for crypto pairs trading using cointegration and z-score
reversion. Designed for market-neutral alpha capture.

Strategies:
  crypto_pairs_zscore  -- Trade BTC/ETH, BTC/SOL, ETH/SOL spread reversion
                          using log-spread z-score (Engle-Granger framework)
  crypto_pairs_ratio   -- Trade ratio mean-reversion between correlated pairs
                          using price-ratio z-score

Theory:
  Cointegrated pairs share a long-run equilibrium. When the spread deviates
  beyond 2 standard deviations, it tends to revert. We use OLS hedge ratio,
  check residual stationarity via zero-crossing frequency (no scipy needed),
  and trade z-score extremes with ATR-based TP/SL.

References:
  - Engle & Granger (1987): "Co-integration and Error Correction"
  - Vidyamurthy (2004): "Pairs Trading: Quantitative Methods and Analysis"
  - Springer (2024): "Copula-based Trading of Cointegrated Crypto Pairs"
    79-100% WR in backtests (81,000+ data points)

Data: yfinance (60d daily). No scipy/statsmodels required.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from indicators import atr as calc_atr


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CRYPTO_PAIRS = [
    ("BTC-USD", "ETH-USD"),
    ("BTC-USD", "SOL-USD"),
    ("ETH-USD", "SOL-USD"),
    ("BTC-USD", "BNB-USD"),
    ("ETH-USD", "AVAX-USD"),
]

# Thresholds
ZSCORE_ENTRY = 2.0          # Entry when |z| > 2.0
ZSCORE_EXIT = 0.0           # Theoretical exit (mean)
ZSCORE_STOP = 3.0           # Stop-loss z-score level
LOOKBACK = 20               # Rolling z-score window
MIN_BARS = 30               # Minimum data points required
MIN_CORRELATION = 0.7       # Minimum Pearson correlation
MIN_ZERO_CROSS_FREQ = 0.15  # Residual must cross zero >= 15% of bars (stationarity proxy)
DOWNLOAD_PERIOD = "60d"     # yfinance download period
CACHE_TTL = 3600            # Cache pair data for 1 hour (seconds)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    """Round prices sensibly based on magnitude."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


# ---------------------------------------------------------------------------
# Data cache: avoids hammering yfinance within the same scanner run
# ---------------------------------------------------------------------------

_pair_data_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def _get_pair_data(symbol: str) -> Optional[pd.DataFrame]:
    """Download or return cached OHLCV data for a symbol."""
    now = time.time()
    if symbol in _pair_data_cache:
        cached_time, cached_df = _pair_data_cache[symbol]
        if now - cached_time < CACHE_TTL:
            return cached_df

    try:
        df = yf.download(symbol, period=DOWNLOAD_PERIOD, interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        # Flatten multi-level columns if present (yfinance >= 0.2.31)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        _pair_data_cache[symbol] = (now, df)
        return df
    except Exception:
        return None


def _get_close_series(data: dict[str, pd.DataFrame], symbol: str) -> Optional[pd.Series]:
    """Get close prices from scanner data dict or download if missing."""
    if symbol in data:
        df = data[symbol]
        if len(df) >= MIN_BARS:
            return df["Close"].astype(float)
    # Fallback: download directly (pairs may not be in the main symbol list)
    df = _get_pair_data(symbol)
    if df is not None and len(df) >= MIN_BARS:
        return df["Close"].astype(float)
    return None


def _get_ohlc(data: dict[str, pd.DataFrame], symbol: str) -> Optional[pd.DataFrame]:
    """Get full OHLC DataFrame from scanner data or download."""
    if symbol in data:
        df = data[symbol]
        if len(df) >= MIN_BARS:
            return df
    df = _get_pair_data(symbol)
    if df is not None and len(df) >= MIN_BARS:
        return df
    return None


# ---------------------------------------------------------------------------
# Statistical helpers (no scipy/statsmodels)
# ---------------------------------------------------------------------------

def _ols_hedge_ratio(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    """Simple OLS: y = beta * x + alpha. Returns (beta, alpha)."""
    mean_x = np.mean(x)
    mean_y = np.mean(y)
    cov_xy = np.mean((x - mean_x) * (y - mean_y))
    var_x = np.var(x)
    if var_x == 0:
        return 0.0, 0.0
    beta = cov_xy / var_x
    alpha = mean_y - beta * mean_x
    return float(beta), float(alpha)


def _pearson_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation coefficient."""
    if len(a) < 3:
        return 0.0
    std_a = np.std(a)
    std_b = np.std(b)
    if std_a == 0 or std_b == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _zero_crossing_frequency(series: np.ndarray) -> float:
    """Fraction of indices where the series crosses zero.

    A stationary mean-zero process crosses zero frequently.
    This is a lightweight ADF-stationarity proxy: if residuals cross zero
    at least ~15% of bars, they are likely mean-reverting.
    """
    if len(series) < 5:
        return 0.0
    signs = np.sign(series)
    # Remove zeros for robust crossing count
    signs = signs[signs != 0]
    if len(signs) < 5:
        return 0.0
    crossings = np.sum(np.abs(np.diff(signs)) > 0)
    return float(crossings) / float(len(signs) - 1)


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score: (value - rolling_mean) / rolling_std."""
    roll_mean = series.rolling(window=window, min_periods=window).mean()
    roll_std = series.rolling(window=window, min_periods=window).std()
    # Avoid division by zero
    roll_std = roll_std.replace(0, np.nan)
    return (series - roll_mean) / roll_std


# ---------------------------------------------------------------------------
# STRATEGY: crypto_pairs_zscore
# ---------------------------------------------------------------------------
# Trade log-price spread between cointegrated pairs.
# Entry: z-score of spread < -2.0 (BUY asset A) or > +2.0 (SELL asset A).
# Hedge ratio via OLS regression. Stationarity via zero-crossing frequency.
# ---------------------------------------------------------------------------

def crypto_pairs_zscore(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Cointegration spread z-score pairs trading.

    For each pair (A, B), compute spread = log(A) - beta * log(B).
    Generate signal on A when z-score is extreme.
    """
    signals: list[dict] = []

    for sym_a, sym_b in CRYPTO_PAIRS:
        try:
            close_a = _get_close_series(data, sym_a)
            close_b = _get_close_series(data, sym_b)
            if close_a is None or close_b is None:
                continue

            # Align lengths
            n = min(len(close_a), len(close_b))
            if n < MIN_BARS:
                continue
            ca = close_a.iloc[-n:].values
            cb = close_b.iloc[-n:].values

            # Correlation check
            corr = _pearson_correlation(ca, cb)
            if abs(corr) < MIN_CORRELATION:
                continue

            # Log prices for spread calculation
            log_a = np.log(ca)
            log_b = np.log(cb)

            # OLS hedge ratio: log_a = beta * log_b + alpha + residual
            beta, alpha = _ols_hedge_ratio(log_a, log_b)
            if beta == 0:
                continue

            # Spread (residuals)
            spread = log_a - beta * log_b - alpha

            # Stationarity check: zero-crossing frequency
            zcf = _zero_crossing_frequency(spread)
            if zcf < MIN_ZERO_CROSS_FREQ:
                continue

            # Rolling z-score of spread
            spread_series = pd.Series(spread)
            zscores = _rolling_zscore(spread_series, LOOKBACK)
            if zscores.isna().all():
                continue

            current_z = float(zscores.iloc[-1])
            if np.isnan(current_z):
                continue

            # Need extreme z-score
            if abs(current_z) < ZSCORE_ENTRY:
                continue

            # Get ATR for TP/SL calculation
            df_a = _get_ohlc(data, sym_a)
            if df_a is None:
                continue
            atr_series = calc_atr(df_a["High"].astype(float),
                                  df_a["Low"].astype(float),
                                  df_a["Close"].astype(float), 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr <= 0 or np.isnan(current_atr):
                continue

            price_a = float(ca[-1])
            spread_mean = float(np.mean(spread))
            spread_std = float(np.std(spread))

            if current_z < -ZSCORE_ENTRY:
                # Spread compressed: BUY A (expect spread to widen back)
                signal_type = "BUY"
                # TP: approximate price where z-score returns to 0
                # spread_to_recover = |current_z| * spread_std (in log space)
                log_tp_adjust = abs(current_z) * spread_std
                tp = _smart_round(price_a * np.exp(log_tp_adjust))
                # SL: z-score extends to -3.0
                log_sl_adjust = (ZSCORE_STOP - ZSCORE_ENTRY) * spread_std
                sl = _smart_round(price_a * np.exp(-log_sl_adjust))
            else:
                # Spread extended: SELL A (expect spread to compress back)
                signal_type = "SELL"
                log_tp_adjust = abs(current_z) * spread_std
                tp = _smart_round(price_a * np.exp(-log_tp_adjust))
                log_sl_adjust = (ZSCORE_STOP - ZSCORE_ENTRY) * spread_std
                sl = _smart_round(price_a * np.exp(log_sl_adjust))

            entry = _smart_round(price_a)

            # Risk:Reward check
            reward = abs(tp - entry)
            risk = abs(entry - sl)
            if risk == 0:
                continue
            rr = reward / risk
            if rr < 1.5:
                continue

            # Confidence: based on z-score extremity and correlation strength
            conf = min(0.85, 0.50 + (abs(current_z) - 2.0) * 0.15 + (abs(corr) - 0.7) * 0.30)
            conf = max(0.45, conf)

            signals.append({
                "strategy": "crypto_pairs_zscore",
                "symbol": sym_a,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Coint Z-Score: {sym_a}/{sym_b} spread z={current_z:+.2f} "
                    f"(entry at |z|>{ZSCORE_ENTRY}), corr={corr:.2f}, "
                    f"hedge_ratio={beta:.3f}, zero-cross freq={zcf:.2f}"
                ),
                "timeframe": "5d",
                "extra": {
                    "pair_symbol": sym_b,
                    "zscore": round(current_z, 3),
                    "correlation": round(corr, 3),
                    "hedge_ratio": round(beta, 4),
                    "spread_mean": round(spread_mean, 6),
                    "spread_std": round(spread_std, 6),
                    "zero_cross_freq": round(zcf, 3),
                    "source": "Engle-Granger (1987), Springer (2024) 79-100% WR",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# ---------------------------------------------------------------------------
# STRATEGY: crypto_pairs_ratio
# ---------------------------------------------------------------------------
# Trade price ratio mean-reversion.
# Instead of log-spread, use simple ratio: price_A / price_B.
# When ratio z-score is extreme, trade the denominator asset (B).
# Complementary to zscore strategy (different entry/exit dynamics).
# ---------------------------------------------------------------------------

def crypto_pairs_ratio(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Price-ratio mean-reversion pairs trading.

    For each pair (A, B), compute ratio = price_A / price_B.
    When ratio z-score is extreme, trade asset B for reversion.
    """
    signals: list[dict] = []

    for sym_a, sym_b in CRYPTO_PAIRS:
        try:
            close_a = _get_close_series(data, sym_a)
            close_b = _get_close_series(data, sym_b)
            if close_a is None or close_b is None:
                continue

            n = min(len(close_a), len(close_b))
            if n < MIN_BARS:
                continue
            ca = close_a.iloc[-n:].values
            cb = close_b.iloc[-n:].values

            # Correlation check
            corr = _pearson_correlation(ca, cb)
            if abs(corr) < MIN_CORRELATION:
                continue

            # Price ratio
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = ca / cb
            if np.any(np.isnan(ratio)) or np.any(np.isinf(ratio)):
                # Clean up: forward-fill nans
                ratio = pd.Series(ratio).ffill().bfill().values
                if np.any(np.isnan(ratio)):
                    continue

            # Log-ratio for better statistical properties
            log_ratio = np.log(ratio)

            # Stationarity: zero-crossing of demeaned log-ratio
            demeaned = log_ratio - np.mean(log_ratio)
            zcf = _zero_crossing_frequency(demeaned)
            if zcf < MIN_ZERO_CROSS_FREQ:
                continue

            # Rolling z-score
            ratio_series = pd.Series(log_ratio)
            zscores = _rolling_zscore(ratio_series, LOOKBACK)
            if zscores.isna().all():
                continue

            current_z = float(zscores.iloc[-1])
            if np.isnan(current_z):
                continue
            if abs(current_z) < ZSCORE_ENTRY:
                continue

            # Get ATR on asset B (what we trade)
            df_b = _get_ohlc(data, sym_b)
            if df_b is None:
                continue
            atr_series = calc_atr(df_b["High"].astype(float),
                                  df_b["Low"].astype(float),
                                  df_b["Close"].astype(float), 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr <= 0 or np.isnan(current_atr):
                continue

            price_b = float(cb[-1])
            ratio_mean = float(np.mean(log_ratio))
            ratio_std = float(np.std(log_ratio))

            if current_z > ZSCORE_ENTRY:
                # Ratio A/B is high (A expensive relative to B)
                # B is undervalued => BUY B
                signal_type = "BUY"
                # TP: use ATR-based target with R:R >= 1.5
                tp = _smart_round(price_b + current_atr * 3.0)
                sl = _smart_round(price_b - current_atr * 2.0)
            else:
                # Ratio A/B is low (B expensive relative to A)
                # B is overvalued => SELL B
                signal_type = "SELL"
                tp = _smart_round(price_b - current_atr * 3.0)
                sl = _smart_round(price_b + current_atr * 2.0)

            entry = _smart_round(price_b)

            # R:R check
            reward = abs(tp - entry)
            risk = abs(entry - sl)
            if risk == 0:
                continue
            rr = reward / risk
            if rr < 1.5:
                continue

            # Confidence
            conf = min(0.80, 0.48 + (abs(current_z) - 2.0) * 0.12 + (abs(corr) - 0.7) * 0.25)
            conf = max(0.42, conf)

            signals.append({
                "strategy": "crypto_pairs_ratio",
                "symbol": sym_b,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Ratio MR: {sym_a}/{sym_b} ratio z={current_z:+.2f} "
                    f"(entry at |z|>{ZSCORE_ENTRY}), corr={corr:.2f}, "
                    f"ratio_mean={np.exp(ratio_mean):.4f}, zero-cross={zcf:.2f}"
                ),
                "timeframe": "5d",
                "extra": {
                    "pair_symbol": sym_a,
                    "zscore": round(current_z, 3),
                    "correlation": round(corr, 3),
                    "spread_mean": round(ratio_mean, 6),
                    "ratio_std": round(ratio_std, 6),
                    "zero_cross_freq": round(zcf, 3),
                    "current_ratio": round(float(ratio[-1]), 6),
                    "source": "Vidyamurthy (2004) Pairs Trading, ratio mean-reversion",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# Registry
# =========================================================================

COINTEGRATION_STRATEGIES = {
    "crypto_pairs_zscore": crypto_pairs_zscore,
    "crypto_pairs_ratio": crypto_pairs_ratio,
}
