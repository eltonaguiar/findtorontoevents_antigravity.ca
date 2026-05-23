"""
ALPHA_ENGINE -- Crypto Feature Pipeline
========================================
10 crypto-specific ML features for enriching picks before ML ranking.

Each feature is:
  - Fetchable with stdlib only (urllib.request)
  - Gracefully returns None if API fails
  - Normalized to roughly 0-1 or -1 to 1 range

Features:
  1. funding_rate_ma        -- 8h MA of Binance funding rate
  2. fear_greed_momentum    -- F&G 3-day rate of change (normalized)
  3. exchange_volume_ratio  -- current vol / 30d avg vol
  4. price_vs_realized_price -- close / realized price proxy
  5. social_volume_zscore   -- z-score of social mentions (LunarCrush)
  6. btc_dominance_trend    -- BTC.D direction from CoinGecko global
  7. stablecoin_flow_signal -- USDT market cap change (DefiLlama)
  8. volatility_regime      -- current ATR / median ATR (high/low/normal)
  9. rsi_divergence_score   -- RSI direction vs price direction (-1 to 1)
  10. correlation_to_btc    -- 30-bar Pearson correlation of returns to BTC

Usage:
    from crypto_feature_pipeline import compute_crypto_features
    features = compute_crypto_features("BTCUSDT", ohlcv_data)
    pick["ml_features"].update(features)
"""

from __future__ import annotations

import json
import logging
import math
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("alpha_engine.crypto_feature_pipeline")

# ---------------------------------------------------------------------------
# API helpers (stdlib only, Binance failover per CLAUDE.md)
# ---------------------------------------------------------------------------

_BINANCE_SPOT_BASES = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_BINANCE_FUTURES_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]


def _fetch_json(url: str, timeout: int = 8) -> Optional[Any]:
    """Fetch JSON from a URL with timeout. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_binance(path: str, *, futures: bool = False, timeout: int = 8) -> Optional[Any]:
    """Fetch from Binance with multi-mirror failover."""
    bases = _BINANCE_FUTURES_BASES if futures else _BINANCE_SPOT_BASES
    for base in bases:
        result = _fetch_json(f"{base}{path}", timeout=timeout)
        if result is not None:
            return result
    return None


# ---------------------------------------------------------------------------
# Feature 1: Funding Rate MA (8h moving average of funding rate)
# ---------------------------------------------------------------------------

def _funding_rate_ma(symbol: str) -> Optional[float]:
    """8-hour MA of recent funding rates from Binance futures.

    Normalized: typical range -0.01 to 0.05, we scale to roughly -1..1
    by dividing by 0.03 and clamping.
    """
    data = _fetch_binance(
        f"/fapi/v1/fundingRate?symbol={symbol}&limit=8", futures=True
    )
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    rates = []
    for item in data:
        try:
            rates.append(float(item.get("fundingRate", 0)))
        except (TypeError, ValueError):
            continue
    if not rates:
        return None
    ma = sum(rates) / len(rates)
    # Normalize: divide by 0.03 (typical extreme), clamp to -1..1
    normalized = max(-1.0, min(1.0, ma / 0.03))
    return round(normalized, 4)


# ---------------------------------------------------------------------------
# Feature 2: Fear & Greed Momentum (3-day rate of change)
# ---------------------------------------------------------------------------

def _fear_greed_momentum() -> Optional[float]:
    """3-day rate of change of Fear & Greed index.

    Returns normalized value: positive = sentiment improving, negative = worsening.
    Range: roughly -1 to 1 (delta / 50).
    """
    data = _fetch_json("https://api.alternative.me/fng/?limit=4")
    if not data or "data" not in data:
        return None
    entries = data["data"]
    if len(entries) < 4:
        return None
    try:
        current = float(entries[0]["value"])
        three_days_ago = float(entries[3]["value"])
    except (KeyError, TypeError, ValueError):
        return None
    delta = current - three_days_ago
    # Normalize: divide by 50 (max realistic swing), clamp to -1..1
    normalized = max(-1.0, min(1.0, delta / 50.0))
    return round(normalized, 4)


# ---------------------------------------------------------------------------
# Feature 3: Exchange Volume Ratio (current vol / 30d avg vol)
# ---------------------------------------------------------------------------

def _exchange_volume_ratio(ohlcv: Dict[str, List[float]]) -> Optional[float]:
    """Ratio of latest volume bar to 30-period average volume.

    Normalized: 1.0 = normal, >2.0 = spike. Clamped to 0..5 then /5 -> 0..1.
    """
    volumes = ohlcv.get("volume", [])
    if len(volumes) < 30:
        return None
    avg_30 = sum(volumes[-30:]) / 30.0
    if avg_30 <= 0:
        return None
    ratio = volumes[-1] / avg_30
    normalized = max(0.0, min(1.0, ratio / 5.0))
    return round(normalized, 4)


# ---------------------------------------------------------------------------
# Feature 4: Price vs Realized Price (approximation)
# ---------------------------------------------------------------------------

def _price_vs_realized_price(ohlcv: Dict[str, List[float]]) -> Optional[float]:
    """Proxy for MVRV: close / volume-weighted average price over lookback.

    realized_price_proxy = SMA(close * volume) / SMA(volume)
    Result normalized: 1.0 = fair value, >1.2 = overvalued, <0.8 = undervalued.
    Mapped to 0..1 range: (ratio - 0.5) / 1.0, clamped.
    """
    closes = ohlcv.get("close", [])
    volumes = ohlcv.get("volume", [])
    lookback = 60
    if len(closes) < lookback or len(volumes) < lookback:
        return None
    c = closes[-lookback:]
    v = volumes[-lookback:]
    vol_sum = sum(v)
    if vol_sum <= 0:
        return None
    realized_proxy = sum(c[i] * v[i] for i in range(lookback)) / vol_sum
    if realized_proxy <= 0:
        return None
    ratio = closes[-1] / realized_proxy
    # Normalize: ratio typically 0.7-1.5, map to 0..1
    normalized = max(0.0, min(1.0, (ratio - 0.5) / 1.0))
    return round(normalized, 4)


# ---------------------------------------------------------------------------
# Feature 5: Social Volume Z-Score (LunarCrush if available)
# ---------------------------------------------------------------------------

def _social_volume_zscore(symbol: str) -> Optional[float]:
    """Z-score of social mentions from LunarCrush.

    Requires LUNARCRUSH_API env var. Returns None if not available.
    Normalized to -1..1 range.
    """
    api_key = os.environ.get("LUNARCRUSH_API", "")
    if not api_key:
        return None
    # Strip USDT/USD suffix for LunarCrush
    coin = symbol.replace("USDT", "").replace("USD", "").lower()
    data = _fetch_json(
        f"https://lunarcrush.com/api4/public/coins/{coin}/v1?"
        f"key={api_key}"
    )
    if not data or not isinstance(data, dict):
        return None
    try:
        # LunarCrush v4 returns social_volume and related metrics
        social_vol = data.get("data", {}).get("social_volume", None)
        avg = data.get("data", {}).get("social_volume_avg", None)
        if social_vol is None or avg is None or avg <= 0:
            return None
        # Simple z-score approximation: (current - avg) / avg
        z = (social_vol - avg) / avg
        normalized = max(-1.0, min(1.0, z / 3.0))
        return round(normalized, 4)
    except (TypeError, ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Feature 6: BTC Dominance Trend (from CoinGecko global data)
# ---------------------------------------------------------------------------

def _btc_dominance_trend() -> Optional[float]:
    """BTC market dominance percentage, normalized to 0..1.

    >60% = BTC dominant (altcoin rotation unlikely)
    <40% = Alt season territory
    """
    data = _fetch_json("https://api.coingecko.com/api/v3/global")
    if not data or "data" not in data:
        return None
    try:
        btc_dom = data["data"]["market_cap_percentage"]["btc"]
        # Normalize: typical range 35-70, map to 0..1
        normalized = max(0.0, min(1.0, (btc_dom - 30.0) / 50.0))
        return round(normalized, 4)
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Feature 7: Stablecoin Flow Signal (USDT market cap change via DefiLlama)
# ---------------------------------------------------------------------------

def _stablecoin_flow_signal() -> Optional[float]:
    """USDT market cap trend from DefiLlama.

    Rising stablecoin supply = dry powder entering = bullish.
    Normalized change over recent data to -1..1.
    """
    data = _fetch_json("https://stablecoins.llama.fi/stablecoin/1")  # USDT = id 1
    if not data or "chainBalances" not in data:
        return None
    try:
        # Get total circulating
        tokens = data.get("tokens", [])
        if len(tokens) < 2:
            return None
        latest = tokens[-1].get("circulating", {}).get("peggedUSD", 0)
        prev = tokens[-2].get("circulating", {}).get("peggedUSD", 0)
        if prev <= 0:
            return None
        pct_change = (latest - prev) / prev
        # Normalize: typical weekly change is -2% to +2%
        normalized = max(-1.0, min(1.0, pct_change / 0.02))
        return round(normalized, 4)
    except (KeyError, TypeError, ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Feature 8: Volatility Regime (current ATR / median ATR)
# ---------------------------------------------------------------------------

def _volatility_regime(ohlcv: Dict[str, List[float]], period: int = 14) -> Optional[float]:
    """Current ATR / median ATR over lookback.

    >1.5 = high volatility regime
    <0.7 = low volatility regime
    Normalized to 0..1: ratio / 3.0.
    """
    highs = ohlcv.get("high", [])
    lows = ohlcv.get("low", [])
    closes = ohlcv.get("close", [])
    n = len(closes)
    if n < period + 20:
        return None
    # Compute ATR series
    tr_list = []
    for i in range(1, n):
        h_l = highs[i] - lows[i]
        h_pc = abs(highs[i] - closes[i - 1])
        l_pc = abs(lows[i] - closes[i - 1])
        tr_list.append(max(h_l, h_pc, l_pc))
    if len(tr_list) < period:
        return None
    # Rolling ATR (simple average)
    atr_values = []
    for i in range(period - 1, len(tr_list)):
        window = tr_list[i - period + 1: i + 1]
        atr_values.append(sum(window) / period)
    if len(atr_values) < 5:
        return None
    current_atr = atr_values[-1]
    sorted_atr = sorted(atr_values)
    median_atr = sorted_atr[len(sorted_atr) // 2]
    if median_atr <= 0:
        return None
    ratio = current_atr / median_atr
    normalized = max(0.0, min(1.0, ratio / 3.0))
    return round(normalized, 4)


# ---------------------------------------------------------------------------
# Feature 9: RSI Divergence Score
# ---------------------------------------------------------------------------

def _rsi_divergence_score(ohlcv: Dict[str, List[float]], period: int = 14) -> Optional[float]:
    """RSI direction vs price direction.

    +1 = both rising (confirmation), -1 = divergence (potential reversal).
    0 = neutral.
    """
    closes = ohlcv.get("close", [])
    if len(closes) < period + 10:
        return None
    # Compute RSI
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    if len(gains) < period:
        return None
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # RSI at end
    if avg_loss == 0:
        rsi_now = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_now = 100.0 - (100.0 / (1.0 + rs))

    # Compute RSI 5 bars ago
    avg_gain_5 = sum(gains[:period]) / period
    avg_loss_5 = sum(losses[:period]) / period
    for i in range(period, max(period, len(gains) - 5)):
        avg_gain_5 = (avg_gain_5 * (period - 1) + gains[i]) / period
        avg_loss_5 = (avg_loss_5 * (period - 1) + losses[i]) / period
    if avg_loss_5 == 0:
        rsi_5ago = 100.0
    else:
        rs_5 = avg_gain_5 / avg_loss_5
        rsi_5ago = 100.0 - (100.0 / (1.0 + rs_5))

    price_dir = 1.0 if closes[-1] > closes[-6] else (-1.0 if closes[-1] < closes[-6] else 0.0)
    rsi_dir = 1.0 if rsi_now > rsi_5ago else (-1.0 if rsi_now < rsi_5ago else 0.0)

    # Score: +1 if same direction, -1 if divergent
    if price_dir == 0 or rsi_dir == 0:
        return 0.0
    score = 1.0 if price_dir == rsi_dir else -1.0
    return round(score, 4)


# ---------------------------------------------------------------------------
# Feature 10: Correlation to BTC (30-bar Pearson)
# ---------------------------------------------------------------------------

def _correlation_to_btc(
    ohlcv: Dict[str, List[float]],
    btc_closes: Optional[List[float]] = None,
    lookback: int = 30,
) -> Optional[float]:
    """30-bar Pearson correlation of returns vs BTC.

    High correlation (>0.8) = moves with BTC, low (<0.3) = independent alpha.
    Returns -1 to 1 (raw Pearson r).
    """
    closes = ohlcv.get("close", [])
    if len(closes) < lookback + 1:
        return None

    # Fetch BTC klines if not provided
    if btc_closes is None:
        klines = _fetch_binance(
            f"/api/v3/klines?symbol=BTCUSDT&interval=4h&limit={lookback + 5}"
        )
        if not klines or not isinstance(klines, list):
            return None
        btc_closes = [float(k[4]) for k in klines]

    if len(btc_closes) < lookback + 1:
        return None

    # Compute returns
    asset_returns = [
        (closes[-lookback + i] - closes[-lookback + i - 1]) / closes[-lookback + i - 1]
        if closes[-lookback + i - 1] != 0 else 0.0
        for i in range(1, lookback)
    ]
    btc_returns = [
        (btc_closes[-lookback + i] - btc_closes[-lookback + i - 1]) / btc_closes[-lookback + i - 1]
        if btc_closes[-lookback + i - 1] != 0 else 0.0
        for i in range(1, lookback)
    ]

    n = min(len(asset_returns), len(btc_returns))
    if n < 10:
        return None

    a = asset_returns[:n]
    b = btc_returns[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / n)
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / n)
    if std_a == 0 or std_b == 0:
        return 0.0
    r = cov / (std_a * std_b)
    return round(max(-1.0, min(1.0, r)), 4)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_crypto_features(
    symbol: str,
    ohlcv_data: Dict[str, List[float]],
    btc_closes: Optional[List[float]] = None,
) -> Dict[str, Optional[float]]:
    """Compute all 10 crypto-specific ML features for a symbol.

    Parameters:
        symbol: Trading pair (e.g., "BTCUSDT")
        ohlcv_data: Dict with keys "open", "high", "low", "close", "volume"
                    as lists of floats.
        btc_closes: Optional pre-fetched BTC close prices for correlation.

    Returns:
        Dict of 10 features. Each value is a normalized float or None if
        the data source was unavailable.
    """
    return {
        "funding_rate_ma": _funding_rate_ma(symbol),
        "fear_greed_momentum": _fear_greed_momentum(),
        "exchange_volume_ratio": _exchange_volume_ratio(ohlcv_data),
        "price_vs_realized_price": _price_vs_realized_price(ohlcv_data),
        "social_volume_zscore": _social_volume_zscore(symbol),
        "btc_dominance_trend": _btc_dominance_trend(),
        "stablecoin_flow_signal": _stablecoin_flow_signal(),
        "volatility_regime": _volatility_regime(ohlcv_data),
        "rsi_divergence_score": _rsi_divergence_score(ohlcv_data),
        "correlation_to_btc": _correlation_to_btc(ohlcv_data, btc_closes),
    }
