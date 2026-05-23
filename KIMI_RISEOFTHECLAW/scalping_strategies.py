#!/usr/bin/env python3
"""
KIMI Scalping Strategies v1.0
==============================
5 research-validated scalping signal functions derived from:
  - YouTube strategy channels (Rayner Teo, Adam Khoo, ICT community)
  - Reddit r/algotrading community verified results
  - QuantifiedStrategies.com backtests
  - Binance Futures API (funding rates)

Strategies:
  1. VWAP Deviation Scalp     -- 15M crypto/stock, realistic WR 55-65%
  2. EMA Ribbon Momentum      -- 1H crypto/forex, realistic WR 50-58%
  3. Bollinger Band Squeeze   -- 4H crypto/stock, WR 33-47% w/ 1:3 RR
  4. Funding Rate Reversal    -- crypto perps, Binance Futures API
  5. RSI Divergence Scalp     -- 1H crypto/forex, realistic WR 50-60%

Each function returns a tuple compatible with live_scanner.py signal format:
  ("BUY", "reason string")   — signal fired
  (None, "")                 — no signal

Signature: (symbol: str, df: pd.DataFrame, all_data: dict) -> tuple[str | None, str]
  - df:       per-symbol DataFrame from live_scanner (unused — these strategies
              fetch their own intraday bars via _get_bars)
  - all_data: full data dict from live_scanner (unused by most strategies)
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ema(arr, n):
    if not HAS_NP:
        return [0.0] * len(arr)
    e = np.zeros(len(arr)); e[0] = arr[0]; k = 2 / (n + 1)
    for i in range(1, len(arr)):
        e[i] = arr[i] * k + e[i - 1] * (1 - k)
    return e


def _rsi(closes, period=14):
    if not HAS_NP or len(closes) < period + 1:
        return [50.0] * len(closes)
    closes = np.array(closes, dtype=float)
    d = np.diff(closes, prepend=closes[0])
    gain = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    avg_g = np.zeros(len(d)); avg_l = np.zeros(len(d))
    avg_g[period - 1] = np.mean(gain[:period])
    avg_l[period - 1] = np.mean(loss[:period])
    for i in range(period, len(d)):
        avg_g[i] = (avg_g[i - 1] * (period - 1) + gain[i]) / period
        avg_l[i] = (avg_l[i - 1] * (period - 1) + loss[i]) / period
    return 100 - 100 / (1 + avg_g / (avg_l + 1e-9))


def _fetch_bars(symbol: str, interval="1h", period="60d"):
    """Fetch OHLCV bars. Returns (opens, highs, lows, closes, volumes) as lists or None."""
    if not HAS_YF:
        return None
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None
        df.index = df.index.tz_localize(None) if hasattr(df.index, "tz_localize") else df.index
        return (
            df["Open"].values.tolist(),
            df["High"].values.tolist(),
            df["Low"].values.tolist(),
            df["Close"].values.tolist(),
            df["Volume"].values.tolist(),
        )
    except Exception:
        return None


def _fetch_binance_klines(symbol_bn: str, interval="15m", limit=200):
    """Fetch OHLCV from Binance public API. Returns (opens,highs,lows,closes,vols)."""
    if not HAS_REQUESTS:
        return None
    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={"symbol": symbol_bn, "interval": interval, "limit": limit}, timeout=8)
        data = r.json()
        if not isinstance(data, list) or len(data) < 20:
            return None
        opens  = [float(k[1]) for k in data]
        highs  = [float(k[2]) for k in data]
        lows   = [float(k[3]) for k in data]
        closes = [float(k[4]) for k in data]
        vols   = [float(k[5]) for k in data]
        return opens, highs, lows, closes, vols
    except Exception:
        return None


YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "XRP-USD": "XRPUSDT", "DOGE-USD": "DOGEUSDT",
    "AVAX-USD": "AVAXUSDT", "LINK-USD": "LINKUSDT", "DOT-USD": "DOTUSDT",
    "NEAR-USD": "NEARUSDT", "LTC-USD": "LTCUSDT", "INJ-USD": "INJUSDT",
    "OP-USD": "OPUSDT", "ARB11841-USD": "ARBUSDT", "SUI20947-USD": "SUIUSDT",
    "SEI-USD": "SEIUSDT", "FLOKI-USD": "FLOKIUSDT", "BONK-USD": "BONKUSDT",
    "WIF-USD": "WIFUSDT", "PEPE-USD": "PEPEUSDT", "SHIB-USD": "SHIBUSDT",
    "ADA-USD": "ADAUSDT", "ATOM-USD": "ATOMUSDT", "APT21794-USD": "APTUSDT",
    "BCH-USD": "BCHUSDT", "TIA-USD": "TIAUSDT", "MATIC-USD": "MATICUSDT",
}


def _get_bars(symbol: str, interval="1h", limit=200):
    """Try Binance first (crypto), fall back to yfinance."""
    bn = YF_TO_BINANCE.get(symbol)
    if bn:
        result = _fetch_binance_klines(bn, interval=interval, limit=limit)
        if result:
            return result
    # Map yfinance interval names
    yf_interval = interval.replace("m", "m")  # Binance "15m" -> yfinance "15m"
    period_map = {200: "60d", 500: "6mo", 100: "30d"}
    period = period_map.get(limit, "60d")
    return _fetch_bars(symbol, interval=yf_interval, period=period)


# ==============================================================================
# STRATEGY 1: VWAP Deviation Scalp
# ==============================================================================

def signal_vwap_deviation_scalp(symbol: str, df: "pd.DataFrame", all_data: dict) -> tuple:
    """
    VWAP Deviation Mean Reversion Scalp.
    Source: Institutional standard (Brian Shannon, SMB Capital, Rayner Teo).
    Realistic WR: 55-65% on liquid assets. Implementability: 8/10.

    Entry: Price at -2 std dev from intraday VWAP + RSI < 35 + volume spike.
    TP: VWAP midline (+1.5%). SL: -1.5% below VWAP lower band.

    Uses Binance 15-min klines for crypto, yfinance 15m for stocks.
    Args df and all_data are unused (own data fetched via _get_bars).
    """
    result = _get_bars(symbol, interval="15m", limit=100)
    if result is None:
        return None, ""
    opens, highs, lows, closes, vols = result
    n = len(closes)
    if n < 30:
        return None, ""

    # Intraday VWAP (simple rolling, not session-anchored — approximation)
    if not HAS_NP:
        return None, ""
    hi = np.array(highs); lo = np.array(lows); cl = np.array(closes); vo = np.array(vols)
    tp = (hi + lo + cl) / 3
    cum_pv  = np.cumsum(tp * vo)
    cum_v   = np.cumsum(vo) + 1e-9
    vwap_arr = cum_pv / cum_v

    # Rolling std of (typical price - vwap) over last 20 bars
    window = 20
    vwap_std_arr = np.zeros(n)
    for i in range(window - 1, n):
        dev = tp[i - window + 1:i + 1] - vwap_arr[i - window + 1:i + 1]
        vwap_std_arr[i] = np.std(dev) if np.std(dev) > 0 else 1e-6

    # Current values
    vwap      = vwap_arr[-1]
    vwap_std  = vwap_std_arr[-1]
    lower_2sd = vwap - 2.0 * vwap_std
    upper_2sd = vwap + 2.0 * vwap_std
    price     = closes[-1]
    prev_price = closes[-2]

    # Volume spike
    avg_vol = np.mean(vo[-21:-1]) if n > 21 else np.mean(vo)
    rvol = vo[-1] / (avg_vol + 1e-9)

    # RSI-14
    rsi_arr = _rsi(closes, 14)
    rsi = rsi_arr[-1]

    # LONG: price crossed back ABOVE -2sd from below + RSI < 40 + RVOL
    crossed_up_from_lower = prev_price < lower_2sd and price >= lower_2sd
    # Also catch: price is within 0.3% of -2sd band
    near_lower = abs(price - lower_2sd) / (lower_2sd + 1e-9) < 0.003 and rsi < 35

    if (crossed_up_from_lower or near_lower) and rvol >= 1.2 and rsi < 40:
        sl_pct  = abs(price - (lower_2sd - vwap_std)) / price * 100
        tp_pct  = abs(vwap - price) / price * 100
        if tp_pct < 0.2:
            return None, ""  # too close to VWAP, skip
        reason = f"VWAP Deviation Scalp: price near -2sd ({lower_2sd:.4f}), RSI={rsi:.1f}, RVOL={rvol:.2f}x — mean reversion to VWAP ({vwap:.4f})"
        return "BUY", reason

    return None, ""


# ==============================================================================
# STRATEGY 2: EMA Ribbon Momentum
# ==============================================================================

def signal_ema_ribbon_momentum(symbol: str, df: "pd.DataFrame", all_data: dict) -> tuple:
    """
    EMA Ribbon (5, 8, 13, 21, 34) Momentum Pullback.
    Source: YouTube community consensus; Fibonacci EMA ribbon.
    Realistic WR: 50-58%. Implementability: 9/10.

    Entry: Ribbon fanned bullish + pullback to EMA21 + reclaim EMA8.
    TP: +3-5% (swing high). SL: Below EMA34 (~1.5-2%).
    Args df and all_data are unused (own data fetched via _get_bars).
    """
    result = _get_bars(symbol, interval="1h", limit=200)
    if result is None:
        return None, ""
    opens, highs, lows, closes, vols = result
    n = len(closes)
    if n < 50:
        return None, ""

    if not HAS_NP:
        return None, ""
    cl = np.array(closes)

    e5  = _ema(cl, 5)
    e8  = _ema(cl, 8)
    e13 = _ema(cl, 13)
    e21 = _ema(cl, 21)
    e34 = _ema(cl, 34)

    # Current bar values
    c_e5, c_e8, c_e13, c_e21, c_e34 = e5[-1], e8[-1], e13[-1], e21[-1], e34[-1]
    p_e5, p_e8, p_e13, p_e21, p_e34 = e5[-2], e8[-2], e13[-2], e21[-2], e34[-2]

    price = cl[-1]; prev = cl[-2]

    # Ribbon fanned bullish (all in order)
    ribbon_bull = c_e5 > c_e8 > c_e13 > c_e21 > c_e34

    # Pullback: previous candle was at or below EMA21
    pullback = cl[-3] <= e21[-3] or cl[-2] <= e21[-2]

    # Reclaim: price crosses back above EMA8
    reclaim = prev <= p_e8 and price > c_e8

    # Confirm ribbon is expanding (e5 slope up)
    ribbon_expanding = e5[-1] > e5[-3]

    if ribbon_bull and pullback and reclaim and ribbon_expanding:
        sl_price = c_e34 * 0.998  # just below EMA34
        sl_pct   = abs(price - sl_price) / price * 100
        tp_pct   = sl_pct * 2.5  # 2.5:1 RR minimum

        # Recent highest high for TP cap
        recent_high = max(highs[-20:])
        tp_pct_cap = abs(recent_high - price) / price * 100
        tp_pct = min(tp_pct, max(tp_pct_cap, 2.0))

        rsi_arr = _rsi(closes, 14)
        rsi = rsi_arr[-1]
        if rsi > 75:  # already overbought, skip
            return None, ""

        reason = f"EMA Ribbon Momentum: ribbon fanned (5>{8}>{13}>{21}>{34}), pullback+reclaim EMA8 ({c_e8:.4f}), SL=EMA34 ({c_e34:.4f})"
        return "BUY", reason

    return None, ""


# ==============================================================================
# STRATEGY 3: Bollinger Band Squeeze Breakout
# ==============================================================================

def signal_bb_squeeze_breakout(symbol: str, df: "pd.DataFrame", all_data: dict) -> tuple:
    """
    Bollinger Band Squeeze Breakout (John Carter / TTM Squeeze concept).
    Source: John Carter (Simpler Trading), QuantifiedStrategies backtests.
    Realistic WR: 33-47% but RR 1:3 = positive expectancy.
    Implementability: 9/10.

    Entry: BB inside Keltner Channel (squeeze) for 5+ bars, then close outside BB.
    TP: 1.5x BB width from breakout. SL: BB midline (SMA20).
    Args df and all_data are unused (own data fetched via _get_bars).
    """
    result = _get_bars(symbol, interval="4h", limit=100)
    if result is None:
        result = _get_bars(symbol, interval="1h", limit=200)
    if result is None:
        return None, ""

    opens, highs, lows, closes, vols = result
    n = len(closes)
    if n < 30:
        return None, ""

    if not HAS_NP:
        return None, ""
    hi = np.array(highs); lo = np.array(lows); cl = np.array(closes); vo = np.array(vols)

    # Bollinger Bands (SMA20, 2 std)
    bb_period = 20
    bb_upper = np.full(n, np.nan); bb_lower = np.full(n, np.nan); bb_mid = np.full(n, np.nan)
    for i in range(bb_period - 1, n):
        w = cl[i - bb_period + 1:i + 1]
        m = np.mean(w); s = np.std(w)
        bb_mid[i] = m; bb_upper[i] = m + 2 * s; bb_lower[i] = m - 2 * s

    # Keltner Channel (EMA20, 1.5x ATR10)
    ema20 = _ema(cl, 20)
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
    atr10 = np.zeros(n); atr10[0] = tr[0]
    for i in range(1, n):
        atr10[i] = tr[i] / 10 + atr10[i - 1] * 9 / 10
    kc_upper = np.array(ema20) + 1.5 * atr10
    kc_lower = np.array(ema20) - 1.5 * atr10

    # Squeeze = BB inside KC
    squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)

    # Count recent squeeze bars
    squeeze_bars = int(np.sum(squeeze[-10:]))
    was_squeezed = squeeze[-2]  # previous bar was in squeeze
    now_free = not squeeze[-1]  # current bar broke out

    price = cl[-1]
    bb_u = bb_upper[-1]; bb_l = bb_lower[-1]; bb_m = bb_mid[-1]

    if np.isnan(bb_u) or np.isnan(bb_l):
        return None, ""

    bb_width = bb_u - bb_l

    # Volume filter
    avg_vol = np.mean(vo[-21:-1])
    rvol = vo[-1] / (avg_vol + 1e-9)

    # Breakout LONG: squeeze then close above upper BB with volume
    if squeeze_bars >= 4 and was_squeezed and now_free and price > bb_u and rvol >= 1.3:
        tp_price = price + 1.5 * bb_width
        tp_pct   = (tp_price - price) / price * 100
        sl_pct   = (price - bb_m) / price * 100

        if tp_pct < 1.0 or sl_pct < 0.3:
            return None, ""

        reason = f"BB Squeeze Breakout: {squeeze_bars} bars squeezed, price ({price:.4f}) broke above upper BB ({bb_u:.4f}), RVOL={rvol:.2f}x — target +{tp_pct:.1f}%"
        return "BUY", reason

    return None, ""


# ==============================================================================
# STRATEGY 4: Funding Rate Reversal (Crypto Only)
# ==============================================================================

_FUNDING_CACHE: dict = {}  # symbol -> (rate, timestamp)
_FUNDING_TTL = 900  # 15 min cache


def _get_funding_rate(binance_symbol: str) -> Optional[float]:
    """Fetch current funding rate from Binance Futures. Returns rate as float (e.g., 0.0001)."""
    global _FUNDING_CACHE
    now = datetime.now(timezone.utc).timestamp()
    cached = _FUNDING_CACHE.get(binance_symbol)
    if cached and now - cached[1] < _FUNDING_TTL:
        return cached[0]
    if not HAS_REQUESTS:
        return None
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        r = requests.get(url, params={"symbol": binance_symbol, "limit": 3}, timeout=5)
        data = r.json()
        if isinstance(data, list) and data:
            rate = float(data[-1]["fundingRate"])
            _FUNDING_CACHE[binance_symbol] = (rate, now)
            return rate
    except Exception:
        pass
    return None


def _get_open_interest_change(binance_symbol: str) -> Optional[float]:
    """Fetch open interest change (%) over last 1H. Positive = OI rising."""
    if not HAS_REQUESTS:
        return None
    try:
        url = "https://fapi.binance.com/futures/data/openInterestHist"
        r = requests.get(url, params={"symbol": binance_symbol, "period": "1h", "limit": 3}, timeout=5)
        data = r.json()
        if isinstance(data, list) and len(data) >= 2:
            oi_new = float(data[-1]["sumOpenInterest"])
            oi_old = float(data[-2]["sumOpenInterest"])
            return (oi_new - oi_old) / (oi_old + 1e-9) * 100
    except Exception:
        pass
    return None


def signal_funding_rate_reversal(symbol: str, df: "pd.DataFrame", all_data: dict) -> tuple:
    """
    Funding Rate Reversal — Crypto Perpetuals.
    Source: Crypto quant research, Binance Futures mechanics.
    Realistic return: 18-31% annual (ScienceDirect 2025 study). Unique alpha.

    Entry LONG: Funding rate highly negative (shorts over-leveraged)
                + OI declining (shorts covering) + RSI < 40.
    Entry SHORT bias NOT implemented (long-only system).
    TP: +3-5% (funding correction rally). SL: -2.5%.
    Args df and all_data are unused (own data fetched via _get_bars / API).
    """
    bn = YF_TO_BINANCE.get(symbol)
    if not bn:
        return None, ""

    # Funding rate (Binance Futures)
    funding = _get_funding_rate(bn)
    if funding is None:
        return None, ""

    # Only fire on extreme NEGATIVE funding (over-leveraged shorts = long squeeze ending)
    # Threshold: -0.05% per 8H (annualizes to -54%) = serious short squeeze territory
    FUNDING_THRESHOLD = -0.0003  # -0.03% per 8H

    if funding >= FUNDING_THRESHOLD:
        return None, ""  # funding not extreme enough

    # OI change: check if shorts starting to cover
    oi_change = _get_open_interest_change(bn)

    # RSI from 4H bars for confirmation
    result = _get_bars(symbol, interval="4h", limit=50)
    rsi_val = 50.0
    if result:
        _, _, _, closes, _ = result
        rsi_arr = _rsi(closes, 14)
        rsi_val = rsi_arr[-1]

    if rsi_val > 50:  # not oversold enough for contrarian long
        return None, ""

    # Confidence based on how extreme the funding is
    funding_pct = funding * 100

    oi_note = ""
    if oi_change is not None:
        oi_note = f", OI change={oi_change:+.2f}%"

    reason = f"Funding Rate Reversal: rate={funding_pct:.4f}% per 8H (shorts over-leveraged), RSI={rsi_val:.1f}{oi_note} — short squeeze setup"
    return "BUY", reason


# ==============================================================================
# STRATEGY 5: RSI Divergence Scalp
# ==============================================================================

def signal_rsi_divergence_scalp(symbol: str, df: "pd.DataFrame", all_data: dict) -> tuple:
    """
    RSI Divergence Scalp.
    Source: Andrew Cardwell (RSI authority), Rayner Teo, community backtests.
    Realistic WR: 50-60% with confirmation filter. Implementability: 8/10.

    Entry: Bullish divergence (price LL, RSI HL) + RSI < 40 + confirming candle.
    TP: 1:2 RR from entry. SL: Below divergence low.
    Args df and all_data are unused (own data fetched via _get_bars).
    """
    result = _get_bars(symbol, interval="1h", limit=120)
    if result is None:
        return None, ""
    opens, highs, lows, closes, vols = result
    n = len(closes)
    if n < 40:
        return None, ""

    if not HAS_NP:
        return None, ""
    cl = np.array(closes); lo = np.array(lows)
    rsi_arr = _rsi(closes, 14)

    # Find swing lows: a swing low is where the bar is lower than 3 bars on each side
    def find_swing_lows(arr, lookback=5):
        lows_idx = []
        for i in range(lookback, len(arr) - lookback):
            if all(arr[i] <= arr[i - j] for j in range(1, lookback + 1)) and \
               all(arr[i] <= arr[i + j] for j in range(1, lookback + 1)):
                lows_idx.append(i)
        return lows_idx

    swing_low_idxs = find_swing_lows(lo, lookback=3)

    if len(swing_low_idxs) < 2:
        return None, ""

    # Get last two swing lows
    sl2_idx = swing_low_idxs[-1]
    sl1_idx = swing_low_idxs[-2]

    # Bullish divergence: price lower low BUT RSI higher low
    price_ll  = lo[sl2_idx] < lo[sl1_idx]  # price made lower low
    rsi_hl    = rsi_arr[sl2_idx] > rsi_arr[sl1_idx]  # RSI made higher low
    rsi_level = rsi_arr[sl2_idx] < 42  # must be in oversold zone

    if not (price_ll and rsi_hl and rsi_level):
        return None, ""

    # Confirmation: current price above the sl2 low and RSI recovering
    # and swing low is recent (within last 15 bars)
    bars_since_sl2 = n - 1 - sl2_idx
    if bars_since_sl2 > 10:
        return None, ""  # divergence too old

    price     = cl[-1]
    rsi_now   = rsi_arr[-1]
    rsi_prev  = rsi_arr[-2]

    # Confirmation: RSI turning up + price above swing low
    rsi_recovering = rsi_now > rsi_prev
    price_above_sl = price > lo[sl2_idx]
    bullish_candle = cl[-1] > opens[-1]  # green candle

    if not (rsi_recovering and price_above_sl and bullish_candle):
        return None, ""

    sl_price = lo[sl2_idx] * 0.997  # 0.3% below swing low
    sl_pct   = abs(price - sl_price) / price * 100
    tp_pct   = sl_pct * 2.0  # 1:2 minimum RR

    divergence_str = f"RSI at SL1={rsi_arr[sl1_idx]:.1f} -> SL2={rsi_arr[sl2_idx]:.1f} (HL), price SL1={lo[sl1_idx]:.4f} -> SL2={lo[sl2_idx]:.4f} (LL)"

    reason = f"RSI Divergence Scalp: bullish div {divergence_str}, RSI now={rsi_now:.1f} (recovering), {bars_since_sl2} bars ago"
    return "BUY", reason


# ==============================================================================
# Signal function registry (compatible with live_scanner.py SIGNAL_FUNCS)
# ==============================================================================

SCALPING_SIGNAL_FUNCS = {
    "vwap-deviation-scalp":      signal_vwap_deviation_scalp,
    "ema-ribbon-momentum":       signal_ema_ribbon_momentum,
    "bb-squeeze-breakout":       signal_bb_squeeze_breakout,
    "funding-rate-reversal":     signal_funding_rate_reversal,
    "rsi-divergence-scalp":      signal_rsi_divergence_scalp,
}

# ALGO_DEFS entries to inject into live_scanner.py
SCALPING_ALGO_DEFS = {
    "vwap-deviation-scalp-scout": {
        "name": "VWAP Deviation Scalp",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "VWAPDeviationScalp",
        "description": "Mean-reversion buy at -2 std dev from VWAP. 55-65% WR. Institutional anchor. Rayner Teo / SMB Capital method.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD", "DOGE-USD",
                    "LINK-USD", "MATIC-USD", "NEAR-USD", "INJ-USD", "TIA-USD", "SUI20947-USD"],
    },
    "ema-ribbon-momentum-scout": {
        "name": "EMA Ribbon Momentum Pullback",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "EMARibbonMomentum",
        "description": "5/8/13/21/34 EMA ribbon fanned bullish, pullback+reclaim EMA8. 50-58% WR. Fibonacci EMA community consensus.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "XRP-USD", "ADA-USD",
                    "LINK-USD", "DOT-USD", "ATOM-USD", "BNB-USD", "INJ-USD", "NEAR-USD"],
    },
    "bb-squeeze-breakout-scout": {
        "name": "Bollinger Band Squeeze Breakout",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "BBSqueezeBreakout",
        "description": "Volatility compression (BB inside KC) then breakout. 33-47% WR but 1:3 RR = positive expectancy. John Carter TTM Squeeze method.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD",
                    "XRP-USD", "DOGE-USD", "LINK-USD", "ADA-USD", "MATIC-USD"],
    },
    "funding-rate-reversal-scout": {
        "name": "Funding Rate Reversal",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "FundingRateReversal",
        "description": "Fires when Binance Futures funding rate extreme negative (shorts over-leveraged). Short squeeze setup. 18-31% annual per ScienceDirect 2025.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD",
                    "XRP-USD", "LINK-USD", "DOGE-USD", "MATIC-USD", "ADA-USD"],
    },
    "rsi-divergence-scalp-scout": {
        "name": "RSI Divergence Scalp",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "RSIDivergenceScalp",
        "description": "Bullish RSI divergence (price LL, RSI HL) with confirming candle. 50-60% WR. Andrew Cardwell / Rayner Teo method.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "XRP-USD",
                    "DOGE-USD", "LINK-USD", "NEAR-USD", "INJ-USD", "TIA-USD",
                    "SUI20947-USD", "BNB-USD", "ADA-USD", "ATOM-USD"],
    },
}


# ==============================================================================
# Standalone test
# ==============================================================================

if __name__ == "__main__":
    import sys
    test_symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    print("\n" + "=" * 60)
    print("  SCALPING STRATEGY TEST")
    print("=" * 60)
    for sym in test_symbols:
        print(f"\n--- {sym} ---")
        for name, fn in SCALPING_SIGNAL_FUNCS.items():
            try:
                result = fn(sym, {})
                if result.get("signal"):
                    print(f"  [{name}] SIGNAL: {result['signal']} | conf={result.get('confidence','?')} | {result.get('reason','')[:80]}")
                else:
                    print(f"  [{name}] no signal")
            except Exception as ex:
                print(f"  [{name}] ERROR: {ex}")
    print("\n" + "=" * 60)
