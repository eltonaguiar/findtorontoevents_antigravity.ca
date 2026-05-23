"""
Unified Feature Store — singleton cache for shared indicator computation.

All signal systems (KIMI, Alpha Engine, Mercury2, Crypto Signal Engine, etc.)
can call FeatureStore.get("rsi", symbol="BTCUSDT", period=14) instead of
computing their own indicators independently.

Dependencies: numpy, requests (stdlib: threading, time, logging)
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton metaclass
# ---------------------------------------------------------------------------

class _SingletonMeta(type):
    """Thread-safe singleton metaclass."""
    _instances: Dict[type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


# ---------------------------------------------------------------------------
# TTL Cache Entry
# ---------------------------------------------------------------------------

class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at


# ---------------------------------------------------------------------------
# Feature Store
# ---------------------------------------------------------------------------

class FeatureStore(metaclass=_SingletonMeta):
    """
    Central feature store with in-memory TTL cache.

    Usage::

        fs = FeatureStore()
        rsi = fs.get("rsi", symbol="BTCUSDT", period=14)
        vals = fs.get_all("BTCUSDT", ["rsi", "atr", "fear_greed"])
    """

    DEFAULT_TTL = 300  # 5 minutes
    BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
    BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
    BINANCE_DEPTH = "https://api.binance.com/api/v3/depth"
    BINANCE_FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
    FEAR_GREED_URL = "https://api.alternative.me/fng/"
    COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"
    OKX_FUNDING = "https://www.okx.com/api/v5/public/funding-rate"

    def __init__(self, ttl: float = DEFAULT_TTL):
        self._ttl = ttl
        self._cache: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        # Map feature names to computation methods
        self._dispatchers = {
            "rsi": self._compute_rsi,
            "atr": self._compute_atr,
            "ema": self._compute_ema,
            "sma": self._compute_sma,
            "vwap_delta": self._compute_vwap_delta,
            "obv": self._compute_obv,
            "funding_rate": self._compute_funding_rate,
            "orderbook_imbalance": self._compute_orderbook_imbalance,
            "btc_dominance": self._compute_btc_dominance,
            "fear_greed": self._compute_fear_greed,
            "volume_zscore": self._compute_volume_zscore,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        feature: str,
        symbol: str = "BTCUSDT",
        prices: Optional[np.ndarray] = None,
        **kwargs,
    ) -> Optional[Union[float, np.ndarray]]:
        """
        Retrieve a feature value.  Returns cached result if still valid,
        otherwise computes fresh.

        Parameters
        ----------
        feature : str
            One of: rsi, atr, ema, sma, vwap_delta, obv, funding_rate,
            orderbook_imbalance, btc_dominance, fear_greed, volume_zscore.
        symbol : str
            Trading pair (Binance format, e.g. "BTCUSDT").
        prices : np.ndarray, optional
            Pre-fetched OHLCV data as (N, 6) array with columns
            [timestamp, open, high, low, close, volume].
            If None, the store fetches from Binance spot API.
        **kwargs
            Extra params forwarded to the feature function (e.g. period=14).

        Returns
        -------
        float, np.ndarray, or None on error.
        """
        if feature not in self._dispatchers:
            logger.error("Unknown feature: %s", feature)
            return None

        cache_key = self._make_key(feature, symbol, **kwargs)

        with self._lock:
            entry = self._cache.get(cache_key)
            if entry is not None and not entry.expired:
                return entry.value

        # Compute outside lock to avoid blocking other threads
        try:
            value = self._dispatchers[feature](symbol, prices, **kwargs)
        except Exception:
            logger.exception("Error computing %s for %s", feature, symbol)
            return None

        with self._lock:
            self._cache[cache_key] = _CacheEntry(value, self._ttl)

        return value

    def get_all(
        self,
        symbol: str,
        features: List[str],
        prices: Optional[np.ndarray] = None,
        **kwargs,
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Compute multiple features for the same symbol in one call."""
        results: Dict[str, Optional[Union[float, np.ndarray]]] = {}
        for feat in features:
            results[feat] = self.get(feat, symbol=symbol, prices=prices, **kwargs)
        return results

    def clear_cache(self) -> None:
        """Flush all cached values."""
        with self._lock:
            self._cache.clear()
        logger.info("FeatureStore cache cleared")

    @property
    def available_features(self) -> List[str]:
        """List of registered feature names."""
        return list(self._dispatchers.keys())

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(feature: str, symbol: str, **kwargs) -> str:
        extra = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{feature}|{symbol}|{extra}"

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_klines(
        self, symbol: str, interval: str = "1h", limit: int = 200
    ) -> Optional[np.ndarray]:
        """
        Fetch Binance spot klines.  Returns (N, 6) float64 array:
        [timestamp, open, high, low, close, volume].
        """
        cache_key = f"_klines|{symbol}|{interval}|{limit}"
        with self._lock:
            entry = self._cache.get(cache_key)
            if entry is not None and not entry.expired:
                return entry.value

        try:
            resp = requests.get(
                self.BINANCE_KLINES,
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=10,
            )
            resp.raise_for_status()
            raw = resp.json()
            arr = np.array(
                [[float(k[0]), float(k[1]), float(k[2]),
                  float(k[3]), float(k[4]), float(k[5])] for k in raw],
                dtype=np.float64,
            )
            with self._lock:
                self._cache[cache_key] = _CacheEntry(arr, self._ttl)
            return arr
        except Exception:
            logger.exception("Failed to fetch klines for %s", symbol)
            return None

    def _ensure_prices(
        self, symbol: str, prices: Optional[np.ndarray], limit: int = 200
    ) -> Optional[np.ndarray]:
        """Return caller-supplied prices or fetch from Binance."""
        if prices is not None:
            return prices
        return self._fetch_klines(symbol, limit=limit)

    # ------------------------------------------------------------------
    # Feature computations
    # ------------------------------------------------------------------

    def _compute_rsi(
        self, symbol: str, prices: Optional[np.ndarray], period: int = 14, **_
    ) -> Optional[float]:
        """Relative Strength Index (Wilder smoothing). Returns latest value."""
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < period + 1:
            return None
        closes = data[:, 4]
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100.0 - 100.0 / (1.0 + rs))

    def _compute_atr(
        self, symbol: str, prices: Optional[np.ndarray], period: int = 14, **_
    ) -> Optional[float]:
        """Average True Range. Returns latest value."""
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < period + 1:
            return None
        high = data[:, 2]
        low = data[:, 3]
        close = data[:, 4]

        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1]),
            ),
        )
        # Wilder smoothing
        atr = np.mean(tr[:period])
        for i in range(period, len(tr)):
            atr = (atr * (period - 1) + tr[i]) / period
        return float(atr)

    def _compute_ema(
        self, symbol: str, prices: Optional[np.ndarray], period: int = 20, **_
    ) -> Optional[float]:
        """Exponential Moving Average. Returns latest value."""
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < period:
            return None
        closes = data[:, 4]
        k = 2.0 / (period + 1)
        ema = float(np.mean(closes[:period]))
        for i in range(period, len(closes)):
            ema = closes[i] * k + ema * (1 - k)
        return float(ema)

    def _compute_sma(
        self, symbol: str, prices: Optional[np.ndarray], period: int = 20, **_
    ) -> Optional[float]:
        """Simple Moving Average. Returns latest value."""
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < period:
            return None
        closes = data[:, 4]
        return float(np.mean(closes[-period:]))

    def _compute_vwap_delta(
        self, symbol: str, prices: Optional[np.ndarray], **_
    ) -> Optional[float]:
        """
        VWAP delta: (current_close - VWAP) / VWAP as a percentage.
        Positive = above VWAP (bullish), negative = below.
        """
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < 2:
            return None
        # Typical price = (H + L + C) / 3
        tp = (data[:, 2] + data[:, 3] + data[:, 4]) / 3.0
        vol = data[:, 5]
        cum_tp_vol = np.cumsum(tp * vol)
        cum_vol = np.cumsum(vol)
        if cum_vol[-1] == 0:
            return None
        vwap = cum_tp_vol[-1] / cum_vol[-1]
        current_close = data[-1, 4]
        return float((current_close - vwap) / vwap * 100.0)

    def _compute_obv(
        self, symbol: str, prices: Optional[np.ndarray], **_
    ) -> Optional[float]:
        """On-Balance Volume. Returns latest cumulative OBV value."""
        data = self._ensure_prices(symbol, prices)
        if data is None or len(data) < 2:
            return None
        closes = data[:, 4]
        volume = data[:, 5]
        obv = np.zeros(len(closes))
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif closes[i] < closes[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]
        return float(obv[-1])

    def _compute_funding_rate(
        self, symbol: str, prices: Optional[np.ndarray], **_
    ) -> Optional[float]:
        """
        Fetch latest funding rate from Binance Futures.
        Falls back to OKX if Binance fails.
        """
        # Try Binance Futures
        try:
            resp = requests.get(
                self.BINANCE_FUNDING,
                params={"symbol": symbol, "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return float(data[-1]["fundingRate"])
        except Exception:
            logger.debug("Binance funding rate failed for %s, trying OKX", symbol)

        # Fallback: OKX (uses dash-separated instId like BTC-USDT-SWAP)
        try:
            base = symbol.replace("USDT", "")
            inst_id = f"{base}-USDT-SWAP"
            resp = requests.get(
                self.OKX_FUNDING,
                params={"instId": inst_id},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("data"):
                return float(data["data"][0]["fundingRate"])
        except Exception:
            logger.exception("OKX funding rate also failed for %s", symbol)

        return None

    def _compute_orderbook_imbalance(
        self, symbol: str, prices: Optional[np.ndarray], depth: int = 20, **_
    ) -> Optional[float]:
        """
        Order book imbalance = (total_bid_qty - total_ask_qty) /
                               (total_bid_qty + total_ask_qty).
        Range: -1 (all asks) to +1 (all bids).
        """
        try:
            resp = requests.get(
                self.BINANCE_DEPTH,
                params={"symbol": symbol, "limit": depth},
                timeout=10,
            )
            resp.raise_for_status()
            book = resp.json()
            bid_qty = sum(float(b[1]) for b in book.get("bids", []))
            ask_qty = sum(float(a[1]) for a in book.get("asks", []))
            total = bid_qty + ask_qty
            if total == 0:
                return 0.0
            return float((bid_qty - ask_qty) / total)
        except Exception:
            logger.exception("Order book fetch failed for %s", symbol)
            return None

    def _compute_btc_dominance(
        self, symbol: str, prices: Optional[np.ndarray], **_
    ) -> Optional[float]:
        """BTC market cap dominance percentage from CoinGecko."""
        try:
            resp = requests.get(self.COINGECKO_GLOBAL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return float(data["data"]["market_cap_percentage"]["btc"])
        except Exception:
            logger.exception("BTC dominance fetch failed")
            return None

    def _compute_fear_greed(
        self, symbol: str, prices: Optional[np.ndarray], **_
    ) -> Optional[float]:
        """Crypto Fear & Greed Index (0-100) from alternative.me."""
        try:
            resp = requests.get(
                self.FEAR_GREED_URL, params={"limit": 1}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data["data"][0]["value"])
        except Exception:
            logger.exception("Fear & Greed fetch failed")
            return None

    def _compute_volume_zscore(
        self, symbol: str, prices: Optional[np.ndarray], period: int = 20, **_
    ) -> Optional[float]:
        """
        Z-score of current volume vs the last `period` bars.
        Positive = unusually high volume, negative = unusually low.
        """
        data = self._ensure_prices(symbol, prices, limit=max(200, period + 10))
        if data is None or len(data) < period + 1:
            return None
        volumes = data[:, 5]
        recent = volumes[-(period + 1):-1]
        current = volumes[-1]
        mean = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0.0
        return float((current - mean) / std)
