"""
Funding Rate Feature Decomposition — 5 ML features from raw funding rate.
==========================================================================

Instead of feeding a single raw funding rate to the ML filter, we decompose
it into 5 informative features that capture different aspects of the funding
rate signal.  Identified as an easy win (+5-15% accuracy) by researchers
R001 (Dr. Vasquez) and R009 in the synthesis report.

Features:
    1. funding_current        — latest 8h funding rate (raw signal)
    2. funding_8h_roc         — rate of change vs previous 8h period
    3. funding_zscore_30d     — z-score of current rate vs 30-day distribution
    4. funding_vs_basis       — funding rate minus spot-perp basis spread
    5. funding_momentum       — 3-period EMA trend of funding rate history

Data Source:
    Binance Futures public API — no API key required.
    GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=<SYM>&limit=<N>
    Returns 8-hourly funding rate snapshots (3 per day, 90 per 30 days).

Academic References:
    - R001 Dr. Vasquez: "Decomposing derivatives micro-structure signals
      into regime, momentum, and mean-reversion components improves
      classifier AUC by 0.06-0.12 across crypto pairs."
    - R009: "Funding rate z-score over 30d window is the single strongest
      predictor of 8h forward returns among free perpetual-swap features."
    - Alexander & Heck (2020), "Crypto Perpetual Futures": funding rate
      reflects leveraged-positioning imbalance.
    - Jansen (2020), "Machine Learning for Algorithmic Trading", Ch.4:
      feature engineering via rolling statistics and z-scores.

Author: battleground / antigravity
Date: 2026-03-13
"""

from __future__ import annotations

import logging
import math
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "NEARUSDT"]

_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
BINANCE_SPOT_TICKER = "https://api.binance.com/api/v3/ticker/price"
BINANCE_FUTURES_TICKER = "https://fapi.binance.com/fapi/v1/ticker/price"

# Funding rate is posted every 8h — 90 entries covers 30 days
HISTORY_LIMIT = 90
REQUEST_TIMEOUT = 10

# EMA smoothing for 3-period momentum
EMA_PERIODS = 3


@dataclass
class FundingRateFeatures:
    """Decomposed funding rate features for ML consumption.

    All values are floats suitable for direct injection into a feature vector.
    NaN-safe: any computation failure yields 0.0 with a logged warning.
    """
    symbol: str
    funding_current: float = 0.0
    funding_8h_roc: float = 0.0
    funding_zscore_30d: float = 0.0
    funding_vs_basis: float = 0.0
    funding_momentum: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, float]:
        """Return the 5 ML features as a flat dict."""
        return {
            "funding_current": self.funding_current,
            "funding_8h_roc": self.funding_8h_roc,
            "funding_zscore_30d": self.funding_zscore_30d,
            "funding_vs_basis": self.funding_vs_basis,
            "funding_momentum": self.funding_momentum,
        }

    def to_list(self) -> List[float]:
        """Return the 5 ML features as an ordered list (for np.array injection)."""
        return [
            self.funding_current,
            self.funding_8h_roc,
            self.funding_zscore_30d,
            self.funding_vs_basis,
            self.funding_momentum,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        """Column names matching to_list() ordering — for FEATURE_NAMES registry."""
        return [
            "funding_current",
            "funding_8h_roc",
            "funding_zscore_30d",
            "funding_vs_basis",
            "funding_momentum",
        ]


# ── Internal helpers ─────────────────────────────────────────────────

def _fetch_json(url: str, params: dict = None, timeout: int = REQUEST_TIMEOUT) -> Optional[list | dict]:
    """Fetch JSON with error handling and Binance endpoint failover."""
    if requests is None:
        logger.error("requests library not available")
        return None
    urls_to_try = [url]
    if "fapi.binance.com" in url:
        for fb in _FAPI_BASES:
            alt = url.replace("https://fapi.binance.com", fb)
            if alt not in urls_to_try:
                urls_to_try.append(alt)
    elif "api.binance.com" in url:
        for sb in _SPOT_BASES:
            alt = url.replace("https://api.binance.com", sb)
            if alt not in urls_to_try:
                urls_to_try.append(alt)
    for try_url in urls_to_try:
        try:
            resp = requests.get(try_url, params=params, timeout=timeout)
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            continue
    logger.warning("All endpoints failed for %s", url)
    return None


def _safe_float(val, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _ema(values: List[float], periods: int) -> float:
    """Compute the last value of an EMA over a list of floats.

    Uses standard EMA: multiplier = 2 / (periods + 1).
    """
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    k = 2.0 / (periods + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1.0 - k)
    return ema_val


# ── Data fetching ────────────────────────────────────────────────────

def _fetch_funding_history(symbol: str, limit: int = HISTORY_LIMIT) -> List[dict]:
    """Fetch funding rate history from Binance Futures (free, no key).

    Returns list of {fundingRate, fundingTime, symbol} dicts,
    ordered oldest-first.
    """
    data = _fetch_json(
        BINANCE_FUNDING_URL,
        params={"symbol": symbol, "limit": limit},
    )
    if not isinstance(data, list) or len(data) == 0:
        return []
    # Binance returns newest-last by default for fundingRate endpoint
    # but we sort by time to be safe
    data.sort(key=lambda x: x.get("fundingTime", 0))
    return data


def _fetch_spot_perp_prices(symbol: str) -> tuple[float, float]:
    """Fetch current spot and perpetual-futures mark price.

    Returns (spot_price, futures_price). Both 0.0 on failure.
    """
    spot = 0.0
    futures = 0.0

    # Spot price
    spot_data = _fetch_json(BINANCE_SPOT_TICKER, params={"symbol": symbol})
    if isinstance(spot_data, dict) and "price" in spot_data:
        spot = _safe_float(spot_data["price"])

    # Futures price
    futures_data = _fetch_json(BINANCE_FUTURES_TICKER, params={"symbol": symbol})
    if isinstance(futures_data, dict) and "price" in futures_data:
        futures = _safe_float(futures_data["price"])

    return spot, futures


# ── Feature computation ──────────────────────────────────────────────

def compute_funding_features(
    symbol: str = "BTCUSDT",
    history: Optional[List[dict]] = None,
    spot_price: Optional[float] = None,
    futures_price: Optional[float] = None,
) -> FundingRateFeatures:
    """Compute 5 decomposed funding rate features for a single symbol.

    Parameters
    ----------
    symbol : str
        Binance perpetual symbol (e.g. "BTCUSDT").
    history : list[dict], optional
        Pre-fetched funding rate history (for testing / caching).
        If None, fetches live from Binance.
    spot_price / futures_price : float, optional
        Pre-fetched prices.  If None, fetches live.

    Returns
    -------
    FundingRateFeatures
        Dataclass with 5 float features + metadata.
    """
    result = FundingRateFeatures(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # 1. Fetch funding rate history
    if history is None:
        history = _fetch_funding_history(symbol)
    if not history:
        result.error = f"No funding history available for {symbol}"
        logger.warning(result.error)
        return result

    rates = [_safe_float(h.get("fundingRate")) for h in history]

    # ── Feature 1: funding_current ──
    result.funding_current = rates[-1]

    # ── Feature 2: funding_8h_roc (rate of change vs previous period) ──
    if len(rates) >= 2:
        prev = rates[-2]
        if abs(prev) > 1e-10:
            result.funding_8h_roc = (rates[-1] - prev) / abs(prev)
        else:
            # Previous rate ~0: use absolute difference instead
            result.funding_8h_roc = rates[-1] - prev

    # ── Feature 3: funding_zscore_30d ──
    if len(rates) >= 10:
        # Use all available history (up to 90 = 30 days)
        mean_30d = statistics.mean(rates)
        std_30d = statistics.stdev(rates) if len(rates) >= 2 else 0.0
        if std_30d > 1e-12:
            result.funding_zscore_30d = (rates[-1] - mean_30d) / std_30d
        else:
            result.funding_zscore_30d = 0.0
    # else: too few data points, leave at 0.0

    # ── Feature 4: funding_vs_basis (funding rate - annualized basis) ──
    if spot_price is None or futures_price is None:
        spot_price, futures_price = _fetch_spot_perp_prices(symbol)

    if spot_price > 0 and futures_price > 0:
        # Basis = (futures - spot) / spot, annualized to 8h scale
        # Funding is per 8h, so we compare like-for-like (no annualization)
        basis_8h = (futures_price - spot_price) / spot_price
        result.funding_vs_basis = rates[-1] - basis_8h
    # else: prices unavailable, leave at 0.0

    # ── Feature 5: funding_momentum (3-period EMA trend) ──
    if len(rates) >= EMA_PERIODS:
        ema_current = _ema(rates, EMA_PERIODS)
        # Momentum = direction of EMA: positive means rising funding
        # Compute previous EMA for comparison
        ema_prev = _ema(rates[:-1], EMA_PERIODS)
        result.funding_momentum = ema_current - ema_prev

    return result


def compute_all_symbols(
    symbols: Optional[List[str]] = None,
    rate_limit_ms: int = 150,
) -> Dict[str, FundingRateFeatures]:
    """Compute funding features for all supported symbols.

    Parameters
    ----------
    symbols : list[str], optional
        Override default symbol list.
    rate_limit_ms : int
        Delay between per-symbol API calls to respect rate limits.

    Returns
    -------
    dict[str, FundingRateFeatures]
        Mapping symbol -> decomposed features.
    """
    symbols = symbols or SUPPORTED_SYMBOLS
    results = {}

    for sym in symbols:
        results[sym] = compute_funding_features(symbol=sym)
        if rate_limit_ms > 0:
            time.sleep(rate_limit_ms / 1000.0)

    return results


# ── CLI entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 70)
    print("  FUNDING RATE FEATURE DECOMPOSITION — 5 ML Features")
    print("  Researchers R001 (Dr. Vasquez) & R009")
    print("=" * 70)
    print()

    all_features = compute_all_symbols()

    for sym, feat in all_features.items():
        if feat.error:
            print(f"  {sym}: ERROR — {feat.error}")
            continue

        print(f"  {sym}:")
        print(f"    funding_current     = {feat.funding_current:+.6f}")
        print(f"    funding_8h_roc      = {feat.funding_8h_roc:+.6f}")
        print(f"    funding_zscore_30d  = {feat.funding_zscore_30d:+.4f}")
        print(f"    funding_vs_basis    = {feat.funding_vs_basis:+.8f}")
        print(f"    funding_momentum    = {feat.funding_momentum:+.8f}")
        print()

    print("Feature names for ML registry:")
    print(f"  {FundingRateFeatures.feature_names()}")
