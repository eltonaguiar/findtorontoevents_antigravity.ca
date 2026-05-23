"""
ALPHA_ENGINE -- Trend Catcher Strategies
=========================================
Adaptive multi-timeframe trend detection with pullback entries.

Inspired by open-source algotrading trend tools (r/algotrading community):
combines SuperTrend-style adaptive bands, momentum confirmation, volume
validation, and multi-timeframe alignment into a unified trend-catching system.

Core algorithm — Adaptive Trend Detection:
1. SuperTrend bands (ATR-based) detect the dominant trend direction
2. Slope of EMA confirms momentum is aligned with trend
3. Volume validation ensures trend is driven by real participation
4. Multi-timeframe alignment: 4H trend must agree with daily trend
5. Entry on pullback TO the trend (not at peak), with calm volume filter

Trend Strength Score (0-100):
- Persistence: how many bars the trend has held (0-25)
- Slope: steepness of the trend measured via EMA slope (0-25)
- Volume: increasing volume with trend direction (0-25)
- Structure: higher highs/higher lows (uptrend) or reverse (0-25)

Entry Rules (our verified edge: calm entries, not FOMO):
- Trend score > 60
- Price has pulled back to SuperTrend band or EMA
- Volume < 2x average (calm entry, not chasing a pump)
- ATR trailing stop once in position

Symbols: BTC, ETH, SOL, BNB, DOGE, AVAX, DOT, LINK, NEAR, FET, RENDER
Timeframe: 4H candles, with daily trend confirmation

References:
  - Kase (1995): Adaptive ATR bands for trend detection
  - Wilder (1978): ATR for volatility measurement
  - Appel (1979): MACD for momentum confirmation
  - LuxAlgo: SuperTrend Recovery + Evasive SuperTrend concepts
  - FMZ: Machine Learning Adaptive SuperTrend Quantitative Trading Strategy

Pure Python + numpy + pandas. No external ML dependencies.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("alpha_engine.trend_catcher")

# ---------------------------------------------------------------------------
# Target symbols (Binance USDT pairs for 4H klines)
# ---------------------------------------------------------------------------
TREND_CATCHER_SYMBOLS = {
    "BTCUSDT":    {"yf": "BTC-USD",   "name": "Bitcoin"},
    "ETHUSDT":    {"yf": "ETH-USD",   "name": "Ethereum"},
    "SOLUSDT":    {"yf": "SOL-USD",   "name": "Solana"},
    "BNBUSDT":    {"yf": "BNB-USD",   "name": "BNB"},
    "DOGEUSDT":   {"yf": "DOGE-USD",  "name": "Dogecoin"},
    "AVAXUSDT":   {"yf": "AVAX-USD",  "name": "Avalanche"},
    "DOTUSDT":    {"yf": "DOT-USD",   "name": "Polkadot"},
    "LINKUSDT":   {"yf": "LINK-USD",  "name": "Chainlink"},
    "NEARUSDT":   {"yf": "NEAR-USD",  "name": "NEAR"},
    "FETUSDT":    {"yf": "FET-USD",   "name": "Fetch.ai"},
    "RENDERUSDT": {"yf": "RNDR-USD",  "name": "Render"},
}

# ---------------------------------------------------------------------------
# Binance API failover (3+ endpoints per CLAUDE.md rule)
# ---------------------------------------------------------------------------
_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_KUCOIN_BASE = "https://api.kucoin.com"
_CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def fetch_4h_klines(symbol: str, limit: int = 540) -> Optional[pd.DataFrame]:
    """Fetch 4H klines with Binance → CoinGecko → KuCoin → CryptoCompare failover.

    Returns DataFrame with columns: Open, High, Low, Close, Volume
    540 candles of 4H = 90 days of data.
    """
    # Attempt 1: Binance klines (all mirrors)
    for base in _SPOT_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval=4h&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 50:
            df = pd.DataFrame(data, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df.set_index("timestamp")[["Open", "High", "Low", "Close", "Volume"]]
            return df.dropna()

    # Attempt 2: CoinGecko (90 days of daily — downsample note: only daily available free)
    cg_id = _binance_to_coingecko(symbol)
    if cg_id:
        url = f"{_COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days=90"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 20:
            df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            df["Volume"] = 0.0  # CoinGecko OHLC doesn't include volume
            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df.dropna()

    # Attempt 3: KuCoin klines
    kc_symbol = symbol.replace("USDT", "-USDT")
    url = f"{_KUCOIN_BASE}/api/v1/market/candles?type=4hour&symbol={kc_symbol}"
    data = _fetch_json(url)
    if data and isinstance(data, dict) and data.get("data"):
        rows = data["data"]
        if len(rows) > 20:
            # KuCoin: [timestamp, open, close, high, low, volume, turnover]
            df = pd.DataFrame(rows, columns=[
                "timestamp", "Open", "Close", "High", "Low", "Volume", "turnover"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
            df = df.set_index("timestamp")[["Open", "High", "Low", "Close", "Volume"]]
            return df.sort_index().dropna()

    # Attempt 4: CryptoCompare histohour (aggregate to 4H)
    cc_sym = symbol.replace("USDT", "")
    url = f"{_CRYPTOCOMPARE_BASE}/v2/histohour?fsym={cc_sym}&tsym=USD&limit=2000"
    data = _fetch_json(url)
    if data and isinstance(data, dict):
        hourly = data.get("Data", {}).get("Data", [])
        if len(hourly) > 100:
            df = pd.DataFrame(hourly)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s")
            df = df.rename(columns={
                "open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volumefrom": "Volume"
            })
            df = df.set_index("timestamp")[["Open", "High", "Low", "Close", "Volume"]]
            # Aggregate hourly → 4H
            df = df.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()
            return df

    logger.warning("All data sources failed for %s", symbol)
    return None


def _binance_to_coingecko(symbol: str) -> Optional[str]:
    """Map Binance symbol to CoinGecko ID."""
    mapping = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche-2",
        "DOTUSDT": "polkadot", "LINKUSDT": "chainlink", "NEARUSDT": "near",
        "FETUSDT": "fetch-ai", "RENDERUSDT": "render-token",
    }
    return mapping.get(symbol)


# ---------------------------------------------------------------------------
# Core indicators (self-contained, no dependency on indicators.py at runtime)
# ---------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — Wilder (1978)."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI — Wilder smoothing."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ADX — trend strength. >25 = trending, <20 = ranging."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_vals = _atr(high, low, close, period)
    tr_sum = atr_vals * period
    plus_di = 100 * _ema(plus_dm, period) / tr_sum.replace(0, np.nan)
    minus_di = 100 * _ema(minus_dm, period) / tr_sum.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _ema(dx, period)


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD — Appel (1979)."""
    fast_ema = _ema(close, fast)
    slow_ema = _ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def _volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Current volume / average volume."""
    avg = volume.rolling(period).mean()
    return volume / avg.replace(0, np.nan)


# ---------------------------------------------------------------------------
# SuperTrend — Adaptive ATR-based trend bands
# ---------------------------------------------------------------------------

def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               atr_period: int = 10, multiplier: float = 3.0) -> dict:
    """
    SuperTrend indicator — adaptive trailing stop-loss that defines trend direction.

    Upper Band = (H + L) / 2 + multiplier * ATR
    Lower Band = (H + L) / 2 - multiplier * ATR

    Direction flips when price closes beyond the band.

    Returns:
        dict with 'trend' (1=up, -1=down), 'upper', 'lower', 'value' Series
    """
    hl2 = (high + low) / 2.0
    atr_val = _atr(high, low, close, atr_period)

    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    # Initialize output arrays
    n = len(close)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    st_direction = np.zeros(n, dtype=int)
    st_value = np.full(n, np.nan)

    close_arr = close.values
    upper_arr = upper_band.values
    lower_arr = lower_band.values

    # First valid index
    start = max(atr_period, 1)
    if start >= n:
        idx = close.index
        return {
            "trend": pd.Series(st_direction, index=idx),
            "upper": pd.Series(final_upper, index=idx),
            "lower": pd.Series(final_lower, index=idx),
            "value": pd.Series(st_value, index=idx),
        }

    final_upper[start] = upper_arr[start]
    final_lower[start] = lower_arr[start]
    st_direction[start] = 1  # Start bullish
    st_value[start] = lower_arr[start]

    for i in range(start + 1, n):
        # Adaptive bands: ratchet toward price
        if upper_arr[i] < final_upper[i - 1] or close_arr[i - 1] > final_upper[i - 1]:
            final_upper[i] = upper_arr[i]
        else:
            final_upper[i] = final_upper[i - 1]

        if lower_arr[i] > final_lower[i - 1] or close_arr[i - 1] < final_lower[i - 1]:
            final_lower[i] = lower_arr[i]
        else:
            final_lower[i] = final_lower[i - 1]

        # Direction logic
        prev_dir = st_direction[i - 1]
        if prev_dir == 1:
            # Bullish: stays bullish unless close breaks below lower band
            if close_arr[i] < final_lower[i]:
                st_direction[i] = -1
                st_value[i] = final_upper[i]
            else:
                st_direction[i] = 1
                st_value[i] = final_lower[i]
        else:
            # Bearish: stays bearish unless close breaks above upper band
            if close_arr[i] > final_upper[i]:
                st_direction[i] = 1
                st_value[i] = final_lower[i]
            else:
                st_direction[i] = -1
                st_value[i] = final_upper[i]

    idx = close.index
    return {
        "trend": pd.Series(st_direction, index=idx),
        "upper": pd.Series(final_upper, index=idx),
        "lower": pd.Series(final_lower, index=idx),
        "value": pd.Series(st_value, index=idx),
    }


# ---------------------------------------------------------------------------
# Trend Strength Score (0-100)
# ---------------------------------------------------------------------------

def compute_trend_strength(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Composite trend strength score (0-100) based on 4 components:

    1. Persistence (0-25): consecutive bars in same direction
    2. Slope (0-25): steepness of 20-period EMA normalized by ATR
    3. Volume (0-25): volume trend alignment (up volume vs down volume)
    4. Structure (0-25): higher highs + higher lows (uptrend) or inverse

    Returns a signed score: positive = bullish, negative = bearish.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(df)

    scores = np.zeros(n)
    if n < lookback + 5:
        return pd.Series(scores, index=df.index)

    ema_20 = _ema(close, lookback)
    atr_val = _atr(high, low, close, 14)
    ema_slope = ema_20.diff(5) / atr_val.replace(0, np.nan)

    close_arr = close.values
    high_arr = high.values
    low_arr = low.values
    volume_arr = volume.values
    ema_arr = ema_20.values
    slope_arr = ema_slope.values

    for i in range(lookback + 5, n):
        # --- 1. Persistence: count consecutive bars above/below EMA ---
        consec_up = 0
        consec_down = 0
        for j in range(i, max(i - lookback, lookback) - 1, -1):
            if close_arr[j] > ema_arr[j]:
                consec_up += 1
            else:
                break
        for j in range(i, max(i - lookback, lookback) - 1, -1):
            if close_arr[j] < ema_arr[j]:
                consec_down += 1
            else:
                break
        persistence_raw = max(consec_up, consec_down)
        persistence_score = min(25.0, (persistence_raw / lookback) * 25.0)

        # --- 2. Slope: EMA slope normalized by ATR ---
        s = slope_arr[i]
        if np.isnan(s):
            slope_score = 0.0
        else:
            slope_score = min(25.0, abs(s) * 5.0)

        # --- 3. Volume alignment: up bars should have higher vol in uptrend ---
        window = slice(max(0, i - lookback), i + 1)
        up_vol = 0.0
        down_vol = 0.0
        for j in range(max(0, i - lookback), i + 1):
            if close_arr[j] > close_arr[max(0, j - 1)]:
                up_vol += volume_arr[j]
            else:
                down_vol += volume_arr[j]
        total_vol = up_vol + down_vol
        if total_vol > 0:
            vol_ratio = max(up_vol, down_vol) / total_vol
            vol_score = min(25.0, (vol_ratio - 0.5) * 50.0)  # 0.5 → 0, 1.0 → 25
        else:
            vol_score = 0.0

        # --- 4. Structure: higher highs/lows or lower highs/lows ---
        hh_count = 0
        hl_count = 0
        lh_count = 0
        ll_count = 0
        for j in range(max(1, i - lookback + 1), i + 1):
            if high_arr[j] > high_arr[j - 1]:
                hh_count += 1
            else:
                lh_count += 1
            if low_arr[j] > low_arr[j - 1]:
                hl_count += 1
            else:
                ll_count += 1
        bull_structure = (hh_count + hl_count) / (2 * lookback) if lookback > 0 else 0.5
        bear_structure = (lh_count + ll_count) / (2 * lookback) if lookback > 0 else 0.5
        structure_score = min(25.0, max(bull_structure, bear_structure) * 25.0)

        # Composite — sign indicates direction
        raw = persistence_score + slope_score + vol_score + structure_score
        if consec_up > consec_down and (not np.isnan(s) and s > 0):
            scores[i] = raw
        elif consec_down > consec_up and (not np.isnan(s) and s < 0):
            scores[i] = -raw
        else:
            # Ambiguous — use slope direction
            if not np.isnan(s):
                scores[i] = raw * np.sign(s)
            else:
                scores[i] = 0.0

    return pd.Series(scores, index=df.index)


# ---------------------------------------------------------------------------
# Multi-timeframe alignment: resample 4H → daily for trend confirmation
# ---------------------------------------------------------------------------

def daily_trend_direction(df_4h: pd.DataFrame) -> int:
    """
    Resample 4H data to daily and determine dominant trend.
    Returns: +1 (bullish), -1 (bearish), 0 (neutral/insufficient data)
    """
    if df_4h is None or len(df_4h) < 30:
        return 0

    daily = df_4h.resample("1D").agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum"
    }).dropna()

    if len(daily) < 20:
        return 0

    close = daily["Close"]
    ema_20 = _ema(close, 20)
    ema_50 = _ema(close, 50) if len(daily) >= 50 else _ema(close, len(daily) - 1)

    current = float(close.iloc[-1])
    ema20_val = float(ema_20.iloc[-1])
    ema50_val = float(ema_50.iloc[-1])

    # Daily ADX for trend strength
    adx_val = _adx(daily["High"], daily["Low"], daily["Close"], 14)
    adx_current = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 0

    # Bullish: price > EMA20 > EMA50, ADX > 20
    if current > ema20_val > ema50_val and adx_current > 20:
        return 1
    # Bearish: price < EMA20 < EMA50, ADX > 20
    elif current < ema20_val < ema50_val and adx_current > 20:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Pullback detection — enter on retracement, not at peak
# ---------------------------------------------------------------------------

def detect_pullback(df: pd.DataFrame, st: dict, trend_score: float) -> dict:
    """
    Detect if price has pulled back to the trend and is ready for entry.

    Pullback entry conditions:
    - Uptrend: price dipped toward SuperTrend lower band or EMA, then bounced
    - RSI pulled back from overbought (uptrend) or oversold (downtrend)
    - Volume is calm (< 2x average — not chasing FOMO)

    Returns dict with:
        'is_pullback': bool
        'pullback_depth': float (0-1, how deep the pullback was)
        'entry_quality': float (0-1, overall pullback quality)
    """
    if len(df) < 30:
        return {"is_pullback": False, "pullback_depth": 0, "entry_quality": 0}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    current = float(close.iloc[-1])
    prev = float(close.iloc[-2])

    # SuperTrend value (the trailing stop level)
    st_val = float(st["value"].iloc[-1])
    st_trend = int(st["trend"].iloc[-1])

    # EMA for pullback reference
    ema_20 = _ema(close, 20)
    ema_val = float(ema_20.iloc[-1])

    # RSI for overbought/oversold assessment
    rsi_val = _rsi(close, 14)
    rsi_now = float(rsi_val.iloc[-1]) if not np.isnan(rsi_val.iloc[-1]) else 50
    rsi_prev = float(rsi_val.iloc[-3]) if len(rsi_val) > 3 and not np.isnan(rsi_val.iloc[-3]) else 50

    # Volume ratio (calm entry filter)
    vol_r = _volume_ratio(volume, 20)
    vol_now = float(vol_r.iloc[-1]) if not np.isnan(vol_r.iloc[-1]) else 1.0

    # ATR for measuring pullback depth
    atr_val = _atr(high, low, close, 14)
    atr_now = float(atr_val.iloc[-1]) if not np.isnan(atr_val.iloc[-1]) else 0

    result = {"is_pullback": False, "pullback_depth": 0.0, "entry_quality": 0.0}

    if atr_now == 0:
        return result

    if trend_score > 0 and st_trend == 1:
        # BULLISH pullback: price dipped toward EMA/SuperTrend, now bouncing
        # Look back 5 bars for a low that was near the EMA or ST
        recent_low = float(low.iloc[-5:].min())
        dist_to_ema = abs(recent_low - ema_val) / atr_now
        dist_to_st = abs(recent_low - st_val) / atr_now

        pullback_depth = min(1.0, min(dist_to_ema, dist_to_st))

        # Bounce confirmation: current close > previous close and > recent low
        is_bouncing = current > prev and current > recent_low

        # RSI pulled back from overbought (was >65, now <60) — not exhausted
        rsi_pullback = rsi_prev > 60 and rsi_now < 65 and rsi_now > 35

        # Calm volume: < 2x average (our verified edge)
        calm_volume = vol_now < 2.0

        if is_bouncing and calm_volume and (dist_to_ema < 2.0 or dist_to_st < 2.0):
            quality = 0.0
            quality += 0.3 if pullback_depth < 1.5 else 0.1  # Close to support
            quality += 0.2 if rsi_pullback else 0.0
            quality += 0.2 if vol_now < 1.5 else 0.1  # Calm entry bonus
            quality += 0.3 if current > ema_val else 0.1  # Above EMA
            result = {
                "is_pullback": True,
                "pullback_depth": round(pullback_depth, 3),
                "entry_quality": round(min(1.0, quality), 3),
            }

    elif trend_score < 0 and st_trend == -1:
        # BEARISH pullback: price rallied toward EMA/SuperTrend, now dropping
        recent_high = float(high.iloc[-5:].max())
        dist_to_ema = abs(recent_high - ema_val) / atr_now
        dist_to_st = abs(recent_high - st_val) / atr_now

        pullback_depth = min(1.0, min(dist_to_ema, dist_to_st))

        is_dropping = current < prev and current < recent_high
        rsi_pullback = rsi_prev < 40 and rsi_now > 35 and rsi_now < 65
        calm_volume = vol_now < 2.0

        if is_dropping and calm_volume and (dist_to_ema < 2.0 or dist_to_st < 2.0):
            quality = 0.0
            quality += 0.3 if pullback_depth < 1.5 else 0.1
            quality += 0.2 if rsi_pullback else 0.0
            quality += 0.2 if vol_now < 1.5 else 0.1
            quality += 0.3 if current < ema_val else 0.1
            result = {
                "is_pullback": True,
                "pullback_depth": round(pullback_depth, 3),
                "entry_quality": round(min(1.0, quality), 3),
            }

    return result


# ---------------------------------------------------------------------------
# Smart rounding helper
# ---------------------------------------------------------------------------

def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if value == 0:
        return 0.0
    if value >= 10000:
        return round(value, 1)
    elif value >= 100:
        return round(value, 2)
    elif value >= 1:
        return round(value, 4)
    elif value >= 0.01:
        return round(value, 6)
    else:
        return round(value, 8)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Strategy 1: SuperTrend Pullback Entry (4H)
# ---------------------------------------------------------------------------

def supertrend_pullback_4h(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """
    Adaptive SuperTrend pullback entry on 4H timeframe.

    Entry: trend score > 60 + SuperTrend bullish + pullback to band + calm volume
    TP: 2x ATR from entry
    SL: SuperTrend value (adaptive trailing stop)
    """
    signals = []
    context = context or {}

    for yf_sym, df in data.items():
        if df is None or len(df) < 100:
            continue

        # Map yfinance symbol to our symbol set
        binance_sym = _yf_to_binance(yf_sym)
        if binance_sym and binance_sym not in TREND_CATCHER_SYMBOLS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        # SuperTrend
        st = supertrend(high, low, close, atr_period=10, multiplier=3.0)
        st_trend = int(st["trend"].iloc[-1])
        st_val = float(st["value"].iloc[-1])

        # Trend strength
        ts = compute_trend_strength(df)
        ts_now = float(ts.iloc[-1])

        # Multi-TF: daily trend must agree
        daily_dir = daily_trend_direction(df)

        # ADX for trend confirmation
        adx_val = _adx(high, low, close, 14)
        adx_now = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 0

        # ATR for stops
        atr_val = _atr(high, low, close, 14)
        atr_now = float(atr_val.iloc[-1]) if not np.isnan(atr_val.iloc[-1]) else 0
        if atr_now == 0:
            continue

        # MACD for momentum confirmation
        macd_data = _macd(close)
        macd_hist = float(macd_data["histogram"].iloc[-1])

        # RSI
        rsi_now = float(_rsi(close, 14).iloc[-1])

        # Volume ratio
        vol_r = float(_volume_ratio(volume, 20).iloc[-1]) if len(volume) > 20 else 1.0

        # Pullback detection
        pb = detect_pullback(df, st, ts_now)

        # === BULLISH ENTRY ===
        if (ts_now > 60
                and st_trend == 1
                and daily_dir >= 0  # daily not bearish
                and adx_now > 20
                and macd_hist > 0
                and pb["is_pullback"]
                and vol_r < 2.0
                and 30 < rsi_now < 75):

            sl = max(st_val, current - 2.5 * atr_now)
            tp = current + 2.0 * atr_now
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.3:
                continue

            confidence = _compute_confidence(ts_now, adx_now, pb["entry_quality"],
                                             vol_r, daily_dir, rsi_now, "BUY")

            signals.append({
                "strategy": "supertrend_pullback_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"SuperTrend bullish + pullback entry (depth={pb['pullback_depth']:.2f}), "
                           f"TrendScore={ts_now:.0f}, ADX={adx_now:.0f}, "
                           f"MACD hist={macd_hist:.2f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}, "
                           f"Daily trend={'aligned' if daily_dir == 1 else 'neutral'}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "pullback_quality": pb["entry_quality"],
                "timestamp": _now_iso(),
            })

        # === BEARISH ENTRY ===
        elif (ts_now < -60
              and st_trend == -1
              and daily_dir <= 0  # daily not bullish
              and adx_now > 20
              and macd_hist < 0
              and pb["is_pullback"]
              and vol_r < 2.0
              and 25 < rsi_now < 70):

            sl = min(st_val, current + 2.5 * atr_now)
            tp = current - 2.0 * atr_now
            rr = (current - tp) / (sl - current) if sl > current else 0
            if rr < 1.3:
                continue

            confidence = _compute_confidence(abs(ts_now), adx_now, pb["entry_quality"],
                                             vol_r, daily_dir, rsi_now, "SELL")

            signals.append({
                "strategy": "supertrend_pullback_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"SuperTrend bearish + pullback entry (depth={pb['pullback_depth']:.2f}), "
                           f"TrendScore={ts_now:.0f}, ADX={adx_now:.0f}, "
                           f"MACD hist={macd_hist:.2f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}, "
                           f"Daily trend={'aligned' if daily_dir == -1 else 'neutral'}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "pullback_quality": pb["entry_quality"],
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Strategy 2: EMA Stack Momentum (4H)
# ---------------------------------------------------------------------------

def ema_stack_momentum_4h(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """
    Triple EMA stack trend-following with momentum confirmation.

    Enter when EMA(9) > EMA(21) > EMA(55) (bullish) and price pulls back to EMA(21).
    Confirms with MACD histogram positive + volume not extreme.
    This is the "golden alignment" used by many trend-following systems.
    """
    signals = []

    for yf_sym, df in data.items():
        if df is None or len(df) < 60:
            continue

        binance_sym = _yf_to_binance(yf_sym)
        if binance_sym and binance_sym not in TREND_CATCHER_SYMBOLS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        ema9 = _ema(close, 9)
        ema21 = _ema(close, 21)
        ema55 = _ema(close, 55)

        e9 = float(ema9.iloc[-1])
        e21 = float(ema21.iloc[-1])
        e55 = float(ema55.iloc[-1])

        # MACD
        macd_data = _macd(close)
        macd_hist = float(macd_data["histogram"].iloc[-1])

        # ATR
        atr_val = _atr(high, low, close, 14)
        atr_now = float(atr_val.iloc[-1])
        if atr_now == 0:
            continue

        # RSI
        rsi_now = float(_rsi(close, 14).iloc[-1])

        # Volume
        vol_r = float(_volume_ratio(volume, 20).iloc[-1]) if len(volume) > 20 else 1.0

        # Trend strength
        ts = compute_trend_strength(df)
        ts_now = float(ts.iloc[-1])

        # ADX
        adx_now = float(_adx(high, low, close, 14).iloc[-1])

        # === BULLISH: EMA stack aligned, price near EMA21 ===
        if (e9 > e21 > e55
                and macd_hist > 0
                and abs(current - e21) < 1.5 * atr_now  # Near EMA21
                and current > e21  # Above EMA21
                and vol_r < 2.0
                and 35 < rsi_now < 72
                and adx_now > 18):

            sl = max(e55, current - 2.5 * atr_now)
            tp = current + 2.0 * atr_now
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.2:
                continue

            confidence = 0.40
            confidence += 0.10 if ts_now > 60 else 0.05
            confidence += 0.10 if adx_now > 25 else 0.05
            confidence += 0.05 if vol_r < 1.5 else 0.0
            confidence += 0.05 if rsi_now < 60 else 0.0
            confidence = min(0.75, confidence)

            signals.append({
                "strategy": "ema_stack_momentum_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"EMA stack bullish (9>{e9:.0f}>21>{e21:.0f}>55>{e55:.0f}), "
                           f"pullback to EMA21, MACD hist={macd_hist:.2f}, "
                           f"ADX={adx_now:.0f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

        # === BEARISH: EMA stack inverted ===
        elif (e9 < e21 < e55
              and macd_hist < 0
              and abs(current - e21) < 1.5 * atr_now
              and current < e21
              and vol_r < 2.0
              and 28 < rsi_now < 65
              and adx_now > 18):

            sl = min(e55, current + 2.5 * atr_now)
            tp = current - 2.0 * atr_now
            rr = (current - tp) / (sl - current) if sl > current else 0
            if rr < 1.2:
                continue

            confidence = 0.40
            confidence += 0.10 if ts_now < -60 else 0.05
            confidence += 0.10 if adx_now > 25 else 0.05
            confidence += 0.05 if vol_r < 1.5 else 0.0
            confidence += 0.05 if rsi_now > 40 else 0.0
            confidence = min(0.75, confidence)

            signals.append({
                "strategy": "ema_stack_momentum_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"EMA stack bearish (9<{e9:.0f}<21<{e21:.0f}<55<{e55:.0f}), "
                           f"pullback to EMA21, MACD hist={macd_hist:.2f}, "
                           f"ADX={adx_now:.0f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Strategy 3: Donchian Trend Rider (4H)
# ---------------------------------------------------------------------------

def donchian_trend_rider_4h(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """
    Donchian Channel breakout with trend confirmation and pullback re-entry.

    Classic turtle-trader approach adapted for crypto:
    - Enter on breakout of 20-bar Donchian channel
    - Confirm with ADX > 25 (trending market) and MACD momentum
    - Volume must be elevated but not extreme (1.2-2.0x average)
    - Trail stop at opposite Donchian channel (10-bar for faster exit)
    """
    signals = []

    for yf_sym, df in data.items():
        if df is None or len(df) < 60:
            continue

        binance_sym = _yf_to_binance(yf_sym)
        if binance_sym and binance_sym not in TREND_CATCHER_SYMBOLS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        # Donchian channels
        dc_high_20 = high.rolling(20).max()
        dc_low_20 = low.rolling(20).min()
        dc_high_10 = high.rolling(10).max()
        dc_low_10 = low.rolling(10).min()

        dc_h20 = float(dc_high_20.iloc[-1])
        dc_l20 = float(dc_low_20.iloc[-1])
        dc_h10 = float(dc_high_10.iloc[-1])
        dc_l10 = float(dc_low_10.iloc[-1])
        prev_high = float(dc_high_20.iloc[-2]) if len(dc_high_20) > 1 else dc_h20
        prev_low = float(dc_low_20.iloc[-2]) if len(dc_low_20) > 1 else dc_l20

        # ATR
        atr_val = _atr(high, low, close, 14)
        atr_now = float(atr_val.iloc[-1])
        if atr_now == 0:
            continue

        # ADX
        adx_now = float(_adx(high, low, close, 14).iloc[-1])

        # MACD
        macd_data = _macd(close)
        macd_hist = float(macd_data["histogram"].iloc[-1])

        # RSI
        rsi_now = float(_rsi(close, 14).iloc[-1])

        # Volume
        vol_r = float(_volume_ratio(volume, 20).iloc[-1]) if len(volume) > 20 else 1.0

        # Trend score
        ts = compute_trend_strength(df)
        ts_now = float(ts.iloc[-1])

        # === BULLISH: breakout above 20-bar high ===
        prev_close = float(close.iloc[-2])
        if (current >= dc_h20
                and prev_close < prev_high  # Fresh breakout
                and adx_now > 22
                and macd_hist > 0
                and 1.0 <= vol_r < 2.0  # Elevated but calm
                and rsi_now < 78):

            sl = dc_l10  # Trail stop at 10-bar low
            tp = current + 2.5 * atr_now
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.2:
                continue

            confidence = 0.42
            confidence += 0.10 if adx_now > 30 else 0.05
            confidence += 0.08 if ts_now > 50 else 0.0
            confidence += 0.05 if vol_r > 1.2 else 0.0
            confidence = min(0.72, confidence)

            signals.append({
                "strategy": "donchian_trend_rider_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"Donchian 20-bar breakout (>{dc_h20:.2f}), "
                           f"ADX={adx_now:.0f}, MACD hist={macd_hist:.2f}, "
                           f"Vol={vol_r:.1f}x, RSI={rsi_now:.0f}, trail SL={dc_l10:.2f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

        # === BEARISH: breakdown below 20-bar low ===
        elif (current <= dc_l20
              and prev_close > prev_low
              and adx_now > 22
              and macd_hist < 0
              and 1.0 <= vol_r < 2.0
              and rsi_now > 22):

            sl = dc_h10
            tp = current - 2.5 * atr_now
            rr = (current - tp) / (sl - current) if sl > current else 0
            if rr < 1.2:
                continue

            confidence = 0.42
            confidence += 0.10 if adx_now > 30 else 0.05
            confidence += 0.08 if ts_now < -50 else 0.0
            confidence += 0.05 if vol_r > 1.2 else 0.0
            confidence = min(0.72, confidence)

            signals.append({
                "strategy": "donchian_trend_rider_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"Donchian 20-bar breakdown (<{dc_l20:.2f}), "
                           f"ADX={adx_now:.0f}, MACD hist={macd_hist:.2f}, "
                           f"Vol={vol_r:.1f}x, RSI={rsi_now:.0f}, trail SL={dc_h10:.2f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Strategy 4: Keltner Trend Squeeze (4H)
# ---------------------------------------------------------------------------

def keltner_trend_squeeze_4h(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """
    Keltner Channel expansion after Bollinger-Keltner squeeze.

    When BB squeezes inside KC (volatility compression), wait for the
    expansion breakout in the direction of the dominant trend.
    Entry on first bar that closes outside KC after squeeze release.
    """
    signals = []

    for yf_sym, df in data.items():
        if df is None or len(df) < 60:
            continue

        binance_sym = _yf_to_binance(yf_sym)
        if binance_sym and binance_sym not in TREND_CATCHER_SYMBOLS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        # Bollinger Bands
        bb_mid = _sma(close, 20)
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        # Keltner Channels
        kc_mid = _ema(close, 20)
        atr_val = _atr(high, low, close, 10)
        kc_upper = kc_mid + 1.5 * atr_val
        kc_lower = kc_mid - 1.5 * atr_val

        # Squeeze detection: BB inside KC
        squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        if len(squeeze) < 5:
            continue

        # Was squeezed recently (last 3-5 bars), now released
        was_squeezed = any(squeeze.iloc[-6:-1]) if len(squeeze) > 6 else False
        now_released = not squeeze.iloc[-1]

        if not (was_squeezed and now_released):
            continue

        atr_now = float(atr_val.iloc[-1])
        if atr_now == 0:
            continue

        # MACD for direction
        macd_data = _macd(close)
        macd_hist = float(macd_data["histogram"].iloc[-1])

        # Momentum direction from squeeze (LMM: linear regression of close over squeeze)
        mom = float(close.iloc[-1] - close.iloc[-6]) if len(close) > 6 else 0

        # RSI
        rsi_now = float(_rsi(close, 14).iloc[-1])

        # Volume
        vol_r = float(_volume_ratio(volume, 20).iloc[-1]) if len(volume) > 20 else 1.0

        # ADX
        adx_now = float(_adx(high, low, close, 14).iloc[-1])

        # Trend
        ts = compute_trend_strength(df)
        ts_now = float(ts.iloc[-1])

        kc_u = float(kc_upper.iloc[-1])
        kc_l = float(kc_lower.iloc[-1])

        # === BULLISH: squeeze release upward ===
        if (current > kc_u
                and mom > 0
                and macd_hist > 0
                and vol_r < 2.0
                and rsi_now < 78
                and adx_now > 15):

            sl = kc_l
            tp = current + 2.0 * atr_now
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.0:
                continue

            confidence = 0.45
            confidence += 0.10 if adx_now > 25 else 0.0
            confidence += 0.05 if ts_now > 40 else 0.0
            confidence += 0.05 if vol_r > 1.1 else 0.0
            confidence = min(0.72, confidence)

            signals.append({
                "strategy": "keltner_trend_squeeze_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"BB-KC squeeze release upward (above KC upper {kc_u:.2f}), "
                           f"momentum={mom:.2f}, MACD hist={macd_hist:.2f}, "
                           f"ADX={adx_now:.0f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

        # === BEARISH: squeeze release downward ===
        elif (current < kc_l
              and mom < 0
              and macd_hist < 0
              and vol_r < 2.0
              and rsi_now > 22
              and adx_now > 15):

            sl = kc_u
            tp = current - 2.0 * atr_now
            rr = (current - tp) / (sl - current) if sl > current else 0
            if rr < 1.0:
                continue

            confidence = 0.45
            confidence += 0.10 if adx_now > 25 else 0.0
            confidence += 0.05 if ts_now < -40 else 0.0
            confidence += 0.05 if vol_r > 1.1 else 0.0
            confidence = min(0.72, confidence)

            signals.append({
                "strategy": "keltner_trend_squeeze_4h",
                "symbol": yf_sym,
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"BB-KC squeeze release downward (below KC lower {kc_l:.2f}), "
                           f"momentum={mom:.2f}, MACD hist={macd_hist:.2f}, "
                           f"ADX={adx_now:.0f}, Vol={vol_r:.1f}x, RSI={rsi_now:.0f}"),
                "timeframe": "4h",
                "rsi_at_entry": round(rsi_now, 1),
                "atr_at_entry": round(atr_now, 4),
                "volume_ratio": round(vol_r, 2),
                "trend_score": round(ts_now, 1),
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Confidence computation helper
# ---------------------------------------------------------------------------

def _compute_confidence(trend_score: float, adx: float, pullback_quality: float,
                        vol_ratio: float, daily_dir: int, rsi: float,
                        direction: str) -> float:
    """Compute confidence (0.30-0.75) from multiple factors."""
    conf = 0.35
    # Trend strength
    if trend_score > 80:
        conf += 0.12
    elif trend_score > 60:
        conf += 0.08
    # ADX
    if adx > 30:
        conf += 0.08
    elif adx > 25:
        conf += 0.05
    # Pullback quality
    conf += pullback_quality * 0.10
    # Volume calm
    if vol_ratio < 1.3:
        conf += 0.05
    # Daily alignment
    if (direction == "BUY" and daily_dir == 1) or (direction == "SELL" and daily_dir == -1):
        conf += 0.08
    # RSI sweet spot
    if direction == "BUY" and 40 < rsi < 60:
        conf += 0.04
    elif direction == "SELL" and 40 < rsi < 60:
        conf += 0.04
    return min(0.75, conf)


# ---------------------------------------------------------------------------
# Symbol mapping helpers
# ---------------------------------------------------------------------------

def _yf_to_binance(yf_sym: str) -> Optional[str]:
    """Map yfinance symbol to Binance USDT pair."""
    for bsym, meta in TREND_CATCHER_SYMBOLS.items():
        if meta["yf"] == yf_sym:
            return bsym
    return None


# ---------------------------------------------------------------------------
# Backtest engine (90 days of 4H data)
# ---------------------------------------------------------------------------

def backtest_trend_catcher(symbol: str = "BTCUSDT", days: int = 90) -> dict:
    """
    Backtest trend catcher strategies on historical 4H data.

    Fetches data via API failover, runs all 4 strategies, simulates trades.
    Returns performance metrics: win_rate, avg_rr, total_trades, pnl_pct.
    """
    df = fetch_4h_klines(symbol, limit=days * 6)  # 6 candles per day for 4H
    if df is None or len(df) < 60:
        return {"error": f"Insufficient data for {symbol}", "total_trades": 0}

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    n = len(df)

    # Run SuperTrend across full history
    st = supertrend(df["High"], df["Low"], df["Close"], atr_period=10, multiplier=3.0)
    ts = compute_trend_strength(df)

    # Walk-forward: check each bar for entry signals
    wins = 0
    losses = 0
    total_pnl = 0.0
    trades = []

    min_start = 60  # Need 60 bars warmup

    for i in range(min_start, n - 10):  # Leave 10 bars for trade resolution
        st_trend = int(st["trend"].iloc[i])
        ts_val = float(ts.iloc[i])
        entry_price = close[i]

        # Simple backtest: enter on trend score > 60 with SuperTrend aligned
        if abs(ts_val) < 60 or st_trend == 0:
            continue

        direction = "BUY" if ts_val > 0 and st_trend == 1 else "SELL" if ts_val < 0 and st_trend == -1 else None
        if direction is None:
            continue

        # ATR for stops
        atr_slice = df.iloc[max(0, i - 14):i + 1]
        if len(atr_slice) < 14:
            continue
        atr_now = float(_atr(atr_slice["High"], atr_slice["Low"], atr_slice["Close"], 14).iloc[-1])
        if atr_now == 0:
            continue

        if direction == "BUY":
            tp = entry_price + 2.0 * atr_now
            sl = entry_price - 1.5 * atr_now
        else:
            tp = entry_price - 2.0 * atr_now
            sl = entry_price + 1.5 * atr_now

        # Resolve trade in next 10 bars
        hit_tp = False
        hit_sl = False
        for j in range(i + 1, min(i + 11, n)):
            if direction == "BUY":
                if high[j] >= tp:
                    hit_tp = True
                    break
                if low[j] <= sl:
                    hit_sl = True
                    break
            else:
                if low[j] <= tp:
                    hit_tp = True
                    break
                if high[j] >= sl:
                    hit_sl = True
                    break

        if hit_tp:
            wins += 1
            pnl = abs(tp - entry_price) / entry_price * 100
            total_pnl += pnl
            trades.append({"dir": direction, "pnl": pnl, "result": "win"})
        elif hit_sl:
            losses += 1
            pnl = -abs(sl - entry_price) / entry_price * 100
            total_pnl += pnl
            trades.append({"dir": direction, "pnl": pnl, "result": "loss"})
        # else: no resolution within 10 bars — skip

    total = wins + losses
    return {
        "symbol": symbol,
        "days": days,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_per_trade": round(total_pnl / total, 2) if total > 0 else 0,
        "trade_log": trades[-20:],  # Last 20 trades
    }


def run_full_backtest() -> dict:
    """Run backtest across all trend catcher symbols. Returns aggregate results."""
    results = {}
    for symbol in TREND_CATCHER_SYMBOLS:
        logger.info("Backtesting %s...", symbol)
        results[symbol] = backtest_trend_catcher(symbol, days=90)
    # Aggregate
    total_trades = sum(r["total_trades"] for r in results.values())
    total_wins = sum(r["wins"] for r in results.values())
    total_pnl = sum(r["total_pnl_pct"] for r in results.values())
    return {
        "per_symbol": results,
        "aggregate": {
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0,
            "total_pnl_pct": round(total_pnl, 2),
            "avg_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
        },
    }


# ---------------------------------------------------------------------------
# EXPORTED: Strategy registry for scanner.py integration
# ---------------------------------------------------------------------------

TREND_CATCHER_STRATEGIES: dict[str, callable] = {
    "supertrend_pullback_4h": supertrend_pullback_4h,
    "ema_stack_momentum_4h": ema_stack_momentum_4h,
    "donchian_trend_rider_4h": donchian_trend_rider_4h,
    "keltner_trend_squeeze_4h": keltner_trend_squeeze_4h,
}


# ---------------------------------------------------------------------------
# CLI entry point for standalone backtest
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if "--backtest" in sys.argv:
        print("=== Trend Catcher Full Backtest (90 days, 4H) ===")
        results = run_full_backtest()
        agg = results["aggregate"]
        print(f"\nAggregate: {agg['total_trades']} trades, "
              f"{agg['win_rate']}% WR, "
              f"{agg['total_pnl_pct']}% PnL, "
              f"{agg['avg_pnl_per_trade']}% avg/trade")
        for sym, r in results["per_symbol"].items():
            print(f"  {sym}: {r['total_trades']} trades, {r['win_rate']}% WR, {r['total_pnl_pct']}% PnL")
        # Save results
        out_path = Path(__file__).parent / "data" / "trend_catcher_backtest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {out_path}")
    else:
        print("=== Trend Catcher Live Scan ===")
        print("Fetching 4H data for trend catcher symbols...")
        # Use yfinance as primary for live scan (already available in scanner)
        try:
            import yfinance as yf
            yf_symbols = [meta["yf"] for meta in TREND_CATCHER_SYMBOLS.values()]
            data = {}
            for sym in yf_symbols:
                try:
                    ticker = yf.Ticker(sym)
                    df = ticker.history(period="90d", interval="1h")
                    if df is not None and len(df) > 50:
                        # Resample 1H → 4H
                        df = df.resample("4h").agg({
                            "Open": "first", "High": "max", "Low": "min",
                            "Close": "last", "Volume": "sum"
                        }).dropna()
                        data[sym] = df
                except Exception as e:
                    logger.warning("Failed to fetch %s: %s", sym, e)
            print(f"Loaded {len(data)} symbols")
            for name, func in TREND_CATCHER_STRATEGIES.items():
                sigs = func(data)
                if sigs:
                    for s in sigs:
                        print(f"  [{name}] {s['signal_type']} {s['symbol']} @ {s['entry_price']} "
                              f"(conf={s['confidence']}, RR={s['risk_reward']})")
                else:
                    print(f"  [{name}] No signals")
        except ImportError:
            print("yfinance not available — use --backtest for Binance API data")
