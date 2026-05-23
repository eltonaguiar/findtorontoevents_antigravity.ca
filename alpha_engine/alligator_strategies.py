"""
ALPHA_ENGINE -- Super Alligator Strategies
============================================
Bill Williams' Alligator indicator (3 SMMA lines with offsets) plus VWAP/SMA
filters for trend-following entries with ATR-based TP/SL.

Strategies:
  1. super_alligator      -- 4h timeframe, standard TP/SL (3x/1.5x ATR), 0.1% gap
  2. alligator_scalp      -- 1h timeframe, tight TP/SL (1.5x/1x ATR), 0.05% gap
  3. alligator_swing      -- 4h timeframe, wide TP/SL (4x/2x ATR), 0.15% gap
  4. alligator_daily      -- 1d timeframe, widest TP/SL (5x/2.5x ATR), 0.2% gap + SMA200

Reference: Bill Williams, "Trading Chaos" (1995, 2004)
  - Jaw:   SMMA(hl2, 13) offset 8 bars
  - Teeth: SMMA(hl2, 8)  offset 5 bars
  - Lips:  SMMA(hl2, 5)  offset 3 bars

Data sources:
  - Binance mirrors: api/api1/api2/api3.binance.com (klines)
  - CoinGecko fallback (OHLCV)

stdlib only (urllib.request, json, datetime, math, ssl).
"""

from __future__ import annotations

import json
import math
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

try:
    _SSL_CTX = ssl.create_default_context()
except Exception:
    _SSL_CTX = ssl._create_unverified_context()

_REQUEST_TIMEOUT = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: int = _REQUEST_TIMEOUT) -> Optional[Any]:
    """Fetch JSON from URL with error handling. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# OHLCV fetching with Binance API failover (api, api1, api2, api3) + CoinGecko
# ---------------------------------------------------------------------------

# Map strategy timeframe labels to Binance kline intervals
_BINANCE_INTERVALS = {
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Number of candles to fetch per timeframe (need enough for SMMA warmup + ATR)
_CANDLE_COUNTS = {
    "1h": 200,
    "4h": 200,
    "1d": 250,
}


def _fetch_binance_klines(symbol: str, interval: str, limit: int) -> Optional[List[Dict[str, float]]]:
    """
    Fetch OHLCV klines from Binance with 4-mirror failover.
    Returns list of dicts with open/high/low/close/volume keys, oldest first.
    """
    for mirror in ["api", "api1", "api2", "api3"]:
        url = (
            f"https://{mirror}.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={limit}"
        )
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            try:
                candles = []
                for k in data:
                    candles.append({
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    })
                return candles
            except (IndexError, ValueError, TypeError):
                continue
    return None


def _fetch_coingecko_ohlcv(symbol: str, days: int) -> Optional[List[Dict[str, float]]]:
    """
    Fallback: fetch OHLCV from CoinGecko (limited to daily candles).
    Only works for major coins; maps symbol to CoinGecko ID.
    """
    _SYMBOL_MAP = {
        "BTCUSDT": "bitcoin",
        "ETHUSDT": "ethereum",
        "BNBUSDT": "binancecoin",
        "SOLUSDT": "solana",
        "XRPUSDT": "ripple",
        "ADAUSDT": "cardano",
        "DOGEUSDT": "dogecoin",
        "AVAXUSDT": "avalanche-2",
        "DOTUSDT": "polkadot",
        "MATICUSDT": "matic-network",
        "LINKUSDT": "chainlink",
        "LTCUSDT": "litecoin",
    }
    cg_id = _SYMBOL_MAP.get(symbol)
    if not cg_id:
        return None

    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    data = _fetch_json(url)
    if data and isinstance(data, list) and len(data) > 0:
        try:
            candles = []
            for row in data:
                # CoinGecko OHLC format: [timestamp, open, high, low, close]
                candles.append({
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": 0.0,  # CoinGecko OHLC endpoint has no volume
                })
            return candles
        except (IndexError, ValueError, TypeError):
            pass
    return None


def fetch_ohlcv(symbol: str, interval: str = "4h", limit: int = 200) -> Optional[List[Dict[str, float]]]:
    """
    Fetch OHLCV data with full failover chain:
    Binance mirrors (api, api1, api2, api3) -> CoinGecko.
    """
    candles = _fetch_binance_klines(symbol, interval, limit)
    if candles and len(candles) >= 50:
        return candles

    # CoinGecko fallback (daily only, map interval to days)
    days_map = {"1h": 7, "4h": 30, "1d": 365}
    days = days_map.get(interval, 30)
    candles = _fetch_coingecko_ohlcv(symbol, days)
    if candles and len(candles) >= 50:
        return candles

    return None


# ---------------------------------------------------------------------------
# Core indicator computations (stdlib math only)
# ---------------------------------------------------------------------------

def compute_smma(prices: List[float], length: int) -> List[Optional[float]]:
    """
    Compute Smoothed Moving Average (SMMA / RMA).
    Formula: smma[i] = (smma[i-1] * (length - 1) + price[i]) / length
    First value is SMA of the first 'length' prices.
    Returns list same length as prices; first (length-1) entries are None.
    """
    if len(prices) < length:
        return [None] * len(prices)

    result: List[Optional[float]] = [None] * len(prices)

    # Seed with SMA of first 'length' values
    sma = sum(prices[:length]) / length
    result[length - 1] = sma

    # SMMA from there
    prev = sma
    for i in range(length, len(prices)):
        val = (prev * (length - 1) + prices[i]) / length
        result[i] = val
        prev = val

    return result


def _compute_sma(prices: List[float], length: int) -> List[Optional[float]]:
    """Simple Moving Average."""
    result: List[Optional[float]] = [None] * len(prices)
    if len(prices) < length:
        return result
    for i in range(length - 1, len(prices)):
        result[i] = sum(prices[i - length + 1: i + 1]) / length
    return result


def _compute_atr(candles: List[Dict[str, float]], period: int = 14) -> List[Optional[float]]:
    """
    Average True Range using SMMA (Wilder's smoothing).
    Returns list same length as candles; first entries are None.
    """
    if len(candles) < period + 1:
        return [None] * len(candles)

    tr_values: List[float] = [candles[0]["high"] - candles[0]["low"]]
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr_values.append(max(h - l, abs(h - pc), abs(l - pc)))

    return compute_smma(tr_values, period)


def _compute_vwap(candles: List[Dict[str, float]], period: int = 20) -> List[Optional[float]]:
    """
    Rolling VWAP over `period` bars.
    VWAP = cumulative(typical_price * volume) / cumulative(volume) over window.
    If volume is 0 (e.g. CoinGecko fallback), falls back to SMA of typical price.
    """
    result: List[Optional[float]] = [None] * len(candles)
    if len(candles) < period:
        return result

    # Check if volume data is meaningful
    total_vol = sum(c["volume"] for c in candles)
    if total_vol < 1e-10:
        # No volume data -- use SMA of typical price as proxy
        tp_list = [(c["high"] + c["low"] + c["close"]) / 3.0 for c in candles]
        return _compute_sma(tp_list, period)

    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1: i + 1]
        cum_tpv = 0.0
        cum_vol = 0.0
        for c in window:
            tp = (c["high"] + c["low"] + c["close"]) / 3.0
            cum_tpv += tp * c["volume"]
            cum_vol += c["volume"]
        if cum_vol > 0:
            result[i] = cum_tpv / cum_vol
        else:
            result[i] = (candles[i]["high"] + candles[i]["low"] + candles[i]["close"]) / 3.0

    return result


# ---------------------------------------------------------------------------
# Super Alligator signal logic
# ---------------------------------------------------------------------------

def super_alligator_signal(
    ohlcv_data: List[Dict[str, float]],
    gap_pct: float = 0.001,
    tp_atr_mult: float = 3.0,
    sl_atr_mult: float = 1.5,
    use_vwap: bool = True,
    use_sma200: bool = False,
    atr_period: int = 14,
) -> Optional[Dict[str, Any]]:
    """
    Compute Super Alligator signal from OHLCV data.

    Parameters:
        ohlcv_data: list of dicts with open/high/low/close/volume
        gap_pct: minimum gap between close and lips (0.001 = 0.1%)
        tp_atr_mult: take-profit multiplier on ATR
        sl_atr_mult: stop-loss multiplier on ATR
        use_vwap: require close vs VWAP alignment (default True)
        use_sma200: require close vs SMA200 alignment (default False)
        atr_period: ATR lookback period

    Returns signal dict or None if no signal.
    """
    if not ohlcv_data or len(ohlcv_data) < 60:
        return None

    # HL2 series for Alligator
    hl2 = [(c["high"] + c["low"]) / 2.0 for c in ohlcv_data]

    # Compute SMMA lines
    jaw_raw = compute_smma(hl2, 13)    # offset 8
    teeth_raw = compute_smma(hl2, 8)   # offset 5
    lips_raw = compute_smma(hl2, 5)    # offset 3

    # Apply offsets: shift forward (use earlier values for current bar)
    # For the current bar at index i, the offset value is from i - offset
    n = len(ohlcv_data)

    def _offset_val(series: List[Optional[float]], offset: int, idx: int) -> Optional[float]:
        src_idx = idx - offset
        if src_idx < 0 or src_idx >= len(series):
            return None
        return series[src_idx]

    # Get values for the latest bar
    i = n - 1
    jaw = _offset_val(jaw_raw, 8, i)
    teeth = _offset_val(teeth_raw, 5, i)
    lips = _offset_val(lips_raw, 3, i)

    # Previous bar values (to detect "first bar" -- conditions just aligned)
    prev_jaw = _offset_val(jaw_raw, 8, i - 1)
    prev_teeth = _offset_val(teeth_raw, 5, i - 1)
    prev_lips = _offset_val(lips_raw, 3, i - 1)

    if any(v is None for v in [jaw, teeth, lips, prev_jaw, prev_teeth, prev_lips]):
        return None

    close = ohlcv_data[i]["close"]

    # ATR for TP/SL and mouth-closing detection
    atr_series = _compute_atr(ohlcv_data, atr_period)
    atr = atr_series[i] if i < len(atr_series) else None
    if atr is None or atr <= 0:
        return None

    # VWAP filter
    vwap_series = _compute_vwap(ohlcv_data, 20)
    vwap = vwap_series[i] if i < len(vwap_series) else None

    # SMA200 filter (for daily variant)
    sma200 = None
    if use_sma200:
        closes = [c["close"] for c in ohlcv_data]
        sma200_series = _compute_sma(closes, 200)
        sma200 = sma200_series[i] if i < len(sma200_series) else None

    # Check if alligator mouth is closing (sleeping) -- exit condition
    mouth_width = abs(lips - jaw)
    if mouth_width < atr * 0.3:
        return None  # Alligator sleeping, no trade

    # Bull signal: lips > teeth > jaw (mouth open upward)
    bull_aligned = (lips > teeth > jaw)
    # Bear signal: jaw > teeth > lips (mouth open downward)
    bear_aligned = (jaw > teeth > lips)

    # "First bar" detection: was not aligned on previous bar
    prev_bull = (prev_lips > prev_teeth > prev_jaw)
    prev_bear = (prev_jaw > prev_teeth > prev_lips)

    direction = None
    tooltip_parts = []

    if bull_aligned and not prev_bull:
        # Gap confirmation: close must be >= gap_pct above lips
        gap = (close - lips) / lips if lips > 0 else 0
        if gap < gap_pct:
            return None

        # VWAP filter
        if use_vwap and vwap is not None and close < vwap:
            return None

        # SMA200 filter
        if use_sma200 and sma200 is not None and close < sma200:
            return None

        direction = "LONG"
        tooltip_parts.append("Alligator mouth open UP")
        tooltip_parts.append("lips>teeth>jaw")
        tooltip_parts.append(f"close {gap * 100:.2f}% above lips")
        if use_vwap and vwap is not None:
            tooltip_parts.append("above VWAP")
        if use_sma200 and sma200 is not None:
            tooltip_parts.append("above SMA200")

    elif bear_aligned and not prev_bear:
        # Gap confirmation: close must be >= gap_pct below lips
        gap = (lips - close) / lips if lips > 0 else 0
        if gap < gap_pct:
            return None

        # VWAP filter
        if use_vwap and vwap is not None and close > vwap:
            return None

        # SMA200 filter
        if use_sma200 and sma200 is not None and close > sma200:
            return None

        direction = "SHORT"
        tooltip_parts.append("Alligator mouth open DOWN")
        tooltip_parts.append("jaw>teeth>lips")
        tooltip_parts.append(f"close {gap * 100:.2f}% below lips")
        if use_vwap and vwap is not None:
            tooltip_parts.append("below VWAP")
        if use_sma200 and sma200 is not None:
            tooltip_parts.append("below SMA200")

    else:
        return None  # No fresh alignment

    # Compute entry, TP, SL
    entry = round(close, 8)
    if direction == "LONG":
        tp = round(entry + atr * tp_atr_mult, 8)
        sl = round(entry - atr * sl_atr_mult, 8)
    else:
        tp = round(entry - atr * tp_atr_mult, 8)
        sl = round(entry + atr * sl_atr_mult, 8)

    # Confidence: based on mouth width relative to ATR and gap strength
    gap_val = abs(close - lips) / lips if lips > 0 else 0
    mouth_score = min(1.0, mouth_width / (atr * 2.0))  # wider mouth = stronger
    gap_score = min(1.0, gap_val / (gap_pct * 5.0))    # bigger gap = stronger
    confidence = round(0.4 + 0.3 * mouth_score + 0.3 * gap_score, 2)
    confidence = min(0.85, max(0.35, confidence))

    rr = abs(tp - entry) / max(abs(entry - sl), 1e-10)

    return {
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "confidence": confidence,
        "risk_reward": round(rr, 2),
        "tooltip": ", ".join(tooltip_parts),
        "jaw": round(jaw, 8),
        "teeth": round(teeth, 8),
        "lips": round(lips, 8),
        "atr": round(atr, 8),
        "vwap": round(vwap, 8) if vwap is not None else None,
        "mouth_width_atr": round(mouth_width / atr, 2),
    }


# ---------------------------------------------------------------------------
# Strategy variant definitions
# ---------------------------------------------------------------------------

_VARIANTS = {
    "super_alligator": {
        "timeframe": "4h",
        "interval": "4h",
        "gap_pct": 0.001,      # 0.1%
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 1.5,
        "use_vwap": True,
        "use_sma200": False,
        "description": "Super Alligator (4H) -- Bill Williams Alligator + VWAP, standard ATR targets",
        "win_rate_est": "55-62%",
    },
    "alligator_scalp": {
        "timeframe": "1h",
        "interval": "1h",
        "gap_pct": 0.0005,     # 0.05%
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "use_vwap": True,
        "use_sma200": False,
        "description": "Alligator Scalp (1H) -- tight ATR targets for quick scalps",
        "win_rate_est": "50-58%",
    },
    "alligator_swing": {
        "timeframe": "4h",
        "interval": "4h",
        "gap_pct": 0.0015,     # 0.15%
        "tp_atr_mult": 4.0,
        "sl_atr_mult": 2.0,
        "use_vwap": True,
        "use_sma200": False,
        "description": "Alligator Swing (4H) -- wider ATR targets for swing trades",
        "win_rate_est": "52-60%",
    },
    "alligator_daily": {
        "timeframe": "1d",
        "interval": "1d",
        "gap_pct": 0.002,      # 0.2%
        "tp_atr_mult": 5.0,
        "sl_atr_mult": 2.5,
        "use_vwap": False,     # daily uses SMA200 instead
        "use_sma200": True,
        "description": "Alligator Daily (1D) -- wide targets with SMA200 trend filter",
        "win_rate_est": "55-65%",
    },
}

# Default symbols to scan
_DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "LTCUSDT", "MATICUSDT",
]


# ---------------------------------------------------------------------------
# Pick generator
# ---------------------------------------------------------------------------

def generate_alligator_picks(
    symbols: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Run all Super Alligator variants across symbols.
    Fetches price data from Binance API (with failover) and returns picks
    in alpha_engine standard format.

    Parameters:
        symbols: list of Binance symbols to scan (default: major crypto pairs)

    Returns list of pick dicts compatible with scanner.py signals format.
    """
    if symbols is None:
        symbols = _DEFAULT_SYMBOLS

    picks: List[Dict[str, Any]] = []

    for variant_name, cfg in _VARIANTS.items():
        interval = cfg["interval"]
        limit = _CANDLE_COUNTS.get(interval, 200)

        for symbol in symbols:
            try:
                candles = fetch_ohlcv(symbol, interval, limit)
                if not candles or len(candles) < 60:
                    continue

                signal = super_alligator_signal(
                    ohlcv_data=candles,
                    gap_pct=cfg["gap_pct"],
                    tp_atr_mult=cfg["tp_atr_mult"],
                    sl_atr_mult=cfg["sl_atr_mult"],
                    use_vwap=cfg["use_vwap"],
                    use_sma200=cfg["use_sma200"],
                )

                if signal is None:
                    continue

                signal_type = "BUY" if signal["direction"] == "LONG" else "SELL"

                picks.append({
                    "strategy": variant_name,
                    "symbol": symbol,
                    "direction": signal["direction"],
                    "category": "crypto",
                    "signal_type": signal_type,
                    "entry_price": signal["entry"],
                    "take_profit": signal["tp"],
                    "stop_loss": signal["sl"],
                    "confidence": signal["confidence"],
                    "risk_reward": signal["risk_reward"],
                    "reason": signal["tooltip"],
                    "timeframe": cfg["timeframe"],
                    "source_system": "alpha_engine",
                    "extra": {
                        "jaw": signal["jaw"],
                        "teeth": signal["teeth"],
                        "lips": signal["lips"],
                        "atr": signal["atr"],
                        "vwap": signal["vwap"],
                        "mouth_width_atr": signal["mouth_width_atr"],
                        "variant": variant_name,
                    },
                    "timestamp": _now_iso(),
                })

            except Exception:
                continue  # graceful per-symbol error handling

    return picks


# ---------------------------------------------------------------------------
# Strategy dict for scanner integration (same pattern as other modules)
# ---------------------------------------------------------------------------

ALLIGATOR_STRATEGIES: Dict[str, Dict[str, Any]] = {}
for _name, _cfg in _VARIANTS.items():
    ALLIGATOR_STRATEGIES[_name] = {
        "name": _cfg["description"].split(" -- ")[0],
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": _cfg["timeframe"],
        "description": _cfg["description"],
        "win_rate_est": _cfg["win_rate_est"],
        "references": [
            "Bill Williams, Trading Chaos (1995, 2004)",
            "Alligator indicator: SMMA(13/8/5) with offsets (8/5/3)",
        ],
    }
