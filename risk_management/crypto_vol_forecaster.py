"""
Crypto Volatility Forecaster — GARCH(1,1) adapter for live signal pipeline.

Wraps the existing arch-based GARCH from scripts/garch_vol.py, but uses
crypto OHLCV data from ml_battleground/shared/data_fetcher.py instead of yfinance.

Falls back to EWMA (exponentially weighted moving average) if arch is unavailable
or data is insufficient.
"""

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False
    logger.info("arch library not installed — using EWMA fallback for volatility")

# Cache to avoid re-fetching within the same scan cycle
_vol_cache: dict = {}
_cache_ts: float = 0


def forecast_crypto_vol(pair: str, interval: str = "1h", lookback: int = 200) -> float:
    """
    Forecast 1-step-ahead volatility for a crypto pair.

    Returns volatility as a decimal (e.g., 0.02 = 2% per bar).
    Falls back to EWMA if GARCH fails or arch is unavailable.

    Uses ml_battleground/shared/data_fetcher.fetch_single() for data.
    """
    import time
    global _vol_cache, _cache_ts

    # Cache for 15 minutes (one scan cycle)
    now = time.time()
    if now - _cache_ts > 900:
        _vol_cache.clear()
        _cache_ts = now

    if pair in _vol_cache:
        return _vol_cache[pair]

    vol = _compute_vol(pair, interval, lookback)
    _vol_cache[pair] = vol
    return vol


def _compute_vol(pair: str, interval: str, lookback: int) -> float:
    """Compute volatility — GARCH(1,1) with EWMA fallback."""
    try:
        from ml_battleground.shared.data_fetcher import fetch_single
        df = fetch_single(pair, interval=interval, limit=lookback)
    except Exception as e:
        logger.warning("Data fetch failed for %s: %s — using default vol", pair, e)
        return 0.02  # 2% default

    if df is None or len(df) < 30:
        return 0.02

    # Compute log returns in percentage (arch expects %)
    close = df["Close"].values.astype(float)
    returns_pct = 100 * np.diff(np.log(close))
    returns_pct = returns_pct[~np.isnan(returns_pct)]

    if len(returns_pct) < 30:
        return 0.02

    # Try GARCH(1,1)
    if HAS_ARCH and len(returns_pct) >= 100:
        try:
            am = arch_model(returns_pct, vol="Garch", p=1, q=1, dist="t")
            res = am.fit(disp="off", show_warning=False)
            fc = res.forecast(horizon=1)
            var_fwd = fc.variance.values[-1, 0]
            vol = float(np.sqrt(var_fwd)) / 100  # back to decimal
            if 0.001 < vol < 0.50:  # sanity check
                return vol
        except Exception as e:
            logger.debug("GARCH failed for %s: %s — falling back to EWMA", pair, e)

    # EWMA fallback (span=20)
    returns_dec = returns_pct / 100
    weights = np.exp(-np.arange(len(returns_dec)) / 20.0)
    weights = weights[::-1]
    weights /= weights.sum()
    ewma_var = float(np.sum(weights * (returns_dec - returns_dec.mean()) ** 2))
    vol = float(np.sqrt(ewma_var))
    return max(0.005, min(vol, 0.50))  # clamp to reasonable range


def clear_cache():
    """Clear the volatility cache (useful for testing)."""
    global _vol_cache, _cache_ts
    _vol_cache.clear()
    _cache_ts = 0
