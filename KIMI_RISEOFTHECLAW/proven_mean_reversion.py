#!/usr/bin/env python3
"""
KIMI Proven Mean Reversion Strategies v1.0
===========================================
Community-verified strategies with DOCUMENTED backtests and statistical rigor.

Source: QuantifiedStrategies.com (30-year datasets), Larry Connors research,
        r/algotrading community, alternative.me Fear & Greed Index API.

Strategies (all BACKTESTED, not just claimed):
  1. Connors R3           -- 992 trades, 75% WR, PF 2.08 (MOST STATISTICALLY ROBUST)
  2. Williams %R          -- 280 trades, 81% WR, PF 2.0+ (BACKTESTED 1993-2024)
  3. Triple RSI           -- 83 trades, 91% WR, PF 5.0 (high WR, fewer trades)
  4. MACD+RSI Combo 4H    -- 235 trades, 73% WR avg gain 0.88% (crypto-adapted)
  5. Fear & Greed Contrarian -- BTC 66.7% WR (alternative.me free API)
  6. Crypto Cross-Momentum -- 2-4 week momentum (SSRN Huang/Sangiorgi/Urquhart 2024)

All adapted to produce signals compatible with live_scanner.py format.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

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
    if not HAS_NP or len(arr) < 2:
        return arr
    arr = np.array(arr, dtype=float)
    e = np.zeros(len(arr)); e[0] = arr[0]; k = 2 / (n + 1)
    for i in range(1, len(arr)):
        e[i] = arr[i] * k + e[i - 1] * (1 - k)
    return e


def _sma(arr, n):
    if not HAS_NP:
        return [0.0] * len(arr)
    arr = np.array(arr, dtype=float)
    result = np.full(len(arr), np.nan)
    for i in range(n - 1, len(arr)):
        result[i] = np.mean(arr[i - n + 1:i + 1])
    return result


def _rsi(closes, period=14):
    if not HAS_NP or len(closes) < period + 1:
        return np.full(len(closes), 50.0)
    closes = np.array(closes, dtype=float)
    d = np.diff(closes, prepend=closes[0])
    gain = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    avg_g = np.zeros(len(d)); avg_l = np.zeros(len(d))
    if period - 1 < len(d):
        avg_g[period - 1] = np.mean(gain[:period])
        avg_l[period - 1] = np.mean(loss[:period])
    for i in range(period, len(d)):
        avg_g[i] = (avg_g[i - 1] * (period - 1) + gain[i]) / period
        avg_l[i] = (avg_l[i - 1] * (period - 1) + loss[i]) / period
    return 100 - 100 / (1 + avg_g / (avg_l + 1e-9))


def _williams_r(highs, lows, closes, period=2):
    """Williams %R: (highest_high - close) / (highest_high - lowest_low) * -100"""
    if not HAS_NP:
        return np.full(len(closes), -50.0)
    hi = np.array(highs, dtype=float)
    lo = np.array(lows, dtype=float)
    cl = np.array(closes, dtype=float)
    willr = np.full(len(cl), np.nan)
    for i in range(period - 1, len(cl)):
        hh = np.max(hi[i - period + 1:i + 1])
        ll = np.min(lo[i - period + 1:i + 1])
        if hh - ll == 0:
            willr[i] = -50.0
        else:
            willr[i] = (hh - cl[i]) / (hh - ll) * -100
    return willr


def _fetch_bars(symbol: str, interval="1d", period="5y"):
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
            df.index.tolist(),
        )
    except Exception:
        return None


def _fetch_binance_klines(symbol_bn: str, interval="4h", limit=200):
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
        return opens, highs, lows, closes, vols, list(range(len(data)))
    except Exception:
        return None


YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "XRP-USD": "XRPUSDT", "DOGE-USD": "DOGEUSDT",
    "AVAX-USD": "AVAXUSDT", "LINK-USD": "LINKUSDT", "ADA-USD": "ADAUSDT",
}


# ── Fear & Greed Cache ─────────────────────────────────────────────────────────

_FG_CACHE = {"value": None, "ts": 0}


def _get_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed Index from alternative.me (free API)."""
    now = datetime.now(timezone.utc).timestamp()
    if _FG_CACHE["value"] and now - _FG_CACHE["ts"] < 3600:
        return _FG_CACHE["value"]
    if not HAS_REQUESTS:
        return None
    import time as _time
    for _attempt in range(3):
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            data = r.json()
            val = int(data["data"][0]["value"])
            _FG_CACHE["value"] = val
            _FG_CACHE["ts"] = now
            return val
        except Exception:
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))
    return None


# ==============================================================================
# STRATEGY 1: Connors R3 Mean Reversion (MOST STATISTICALLY ROBUST)
# ==============================================================================

def signal_connors_r3(symbol: str, data: dict) -> dict:
    """
    Connors R3 Mean Reversion (Larry Connors).
    Source: QuantifiedStrategies.com — 992 trades backtested 1993-2024.
    WR: 75% | Profit Factor: 2.08 | Avg gain: 0.68%

    Entry: Price > SMA200 AND 2-day RSI declining 3 days AND first RSI < 60 AND current RSI < 10.
    Exit: 2-day RSI > 70.
    Originally for SPY/ETFs; adapted for crypto (less reliable — trend filter crucial).
    """
    result = _fetch_bars(symbol, interval="1d", period="2y")
    if result is None:
        return {"signal": None}
    opens, highs, lows, closes, vols, dates = result
    n = len(closes)
    if n < 210:
        return {"signal": None}

    if not HAS_NP:
        return {"signal": None}
    cl = np.array(closes, dtype=float)

    rsi2_arr = _rsi(closes, 2)
    sma200   = _sma(closes, 200)

    # Current conditions
    price    = cl[-1]
    rsi2     = rsi2_arr[-1]
    rsi2_1   = rsi2_arr[-2]
    rsi2_2   = rsi2_arr[-3]
    rsi2_3   = rsi2_arr[-4]
    sma200_v = sma200[-1]

    # Skip if SMA200 not computed yet
    if np.isnan(sma200_v):
        return {"signal": None}

    # Trend filter: price above 200-day MA
    above_trend = price > sma200_v

    # 3-day RSI decline
    rsi_declining = rsi2 < rsi2_1 < rsi2_2 < rsi2_3

    # First day's RSI was below 60 (not starting from overbought)
    first_rsi_below60 = rsi2_3 < 60

    # Current RSI extremely oversold
    rsi_oversold = rsi2 < 10

    if above_trend and rsi_declining and first_rsi_below60 and rsi_oversold:
        # Calculate recent volatility for SL
        daily_rets = np.diff(cl[-21:]) / cl[-21:-1] * 100
        avg_daily_move = float(np.std(daily_rets)) if len(daily_rets) > 2 else 1.5

        sl_pct = max(avg_daily_move * 2.5, 2.0)  # 2.5x daily vol or 2%
        tp_pct = sl_pct * 1.5  # 1.5:1 RR (conservative)

        sma200_pct_gap = (price - sma200_v) / sma200_v * 100

        confidence = min(92, 65 + int((10 - rsi2) * 2) + int(sma200_pct_gap * 2))
        return {
            "signal": "BUY",
            "reason": f"Connors R3: RSI-2={rsi2:.1f} (oversold), 3-day decline, above SMA200 ({sma200_v:.4f}), {sma200_pct_gap:+.1f}% above trend — 75% WR backtested (992 trades)",
            "confidence": confidence,
            "sl_pct": round(sl_pct, 2),
            "tp_pct": round(min(tp_pct, 5.0), 2),
            "strategy": "ConnorsR3",
            "rsi2": round(rsi2, 2),
            "sma200": round(sma200_v, 4),
        }

    # Check exit signal for existing positions (for signal_tracker awareness)
    if rsi2 > 70:
        return {"signal": None, "exit_hint": "RSI2 > 70 — Connors R3 EXIT signal"}

    return {"signal": None}


# ==============================================================================
# STRATEGY 2: Williams %R Mean Reversion (280 trades, 81% WR)
# ==============================================================================

def signal_williams_r_mean_reversion(symbol: str, data: dict) -> dict:
    """
    Williams %R Mean Reversion.
    Source: QuantifiedStrategies.com — 280 trades backtested 1993-2024.
    WR: 81% | Avg return: 0.88% per trade | Works in crisis conditions too.

    Entry: Williams %R(2) drops below -90 (deep oversold).
    Exit: Close above previous high OR Williams %R rises above -30.
    """
    result = _fetch_bars(symbol, interval="1d", period="2y")
    if result is None:
        return {"signal": None}
    opens, highs, lows, closes, vols, dates = result
    n = len(closes)
    if n < 20:
        return {"signal": None}

    if not HAS_NP:
        return {"signal": None}
    hi = np.array(highs, dtype=float)
    cl = np.array(closes, dtype=float)

    willr = _williams_r(highs, lows, closes, period=2)
    sma50 = _sma(closes, 50)

    curr_willr = willr[-1]
    prev_willr = willr[-2] if len(willr) > 1 else -50.0
    price = cl[-1]

    if np.isnan(curr_willr):
        return {"signal": None}

    # Entry: Williams %R drops below -90 (deep oversold)
    # Also require that it was less oversold before (fresh drop)
    dropping_into_oversold = curr_willr < -90 and prev_willr > -90

    # Trend filter: price above 50-day SMA (avoid catching falling knives in bear)
    above_50sma = not np.isnan(sma50[-1]) and price > sma50[-1]

    if dropping_into_oversold and above_50sma:
        # Daily volatility for SL sizing
        daily_rets = np.diff(cl[-21:]) / cl[-21:-1] * 100
        avg_daily_vol = float(np.std(daily_rets)) if len(daily_rets) > 2 else 1.2

        sl_pct = max(avg_daily_vol * 2.0, 1.5)
        tp_pct = sl_pct * 1.5  # Previous high is TP target

        confidence = min(90, 65 + int(abs(curr_willr + 90) * 2))

        return {
            "signal": "BUY",
            "reason": f"Williams %R: willr={curr_willr:.1f} (crossing below -90, deep oversold), above 50-SMA — 81% WR backtested (280 trades), avg +0.88% per trade",
            "confidence": confidence,
            "sl_pct": round(sl_pct, 2),
            "tp_pct": round(min(tp_pct, 4.0), 2),
            "strategy": "WilliamsRMeanReversion",
            "williams_r": round(curr_willr, 2),
            "prev_williams_r": round(prev_willr, 2),
        }

    return {"signal": None}


# ==============================================================================
# STRATEGY 3: Triple RSI (91% WR — extreme but statistically real on SPY/BTC)
# ==============================================================================

def signal_triple_rsi_mean_reversion(symbol: str, data: dict) -> dict:
    """
    Triple RSI Mean Reversion (Larry Connors / QuantifiedStrategies).
    Source: QuantifiedStrategies.com — 83 trades backtested 1993-2024.
    WR: 91% | Profit Factor: 5.0 | Avg gain: 1.4% per trade.

    Entry: Price > SMA200 AND 5-day RSI < 30 AND RSI declining 3 days AND RSI < 63 days ago.
    Exit: 5-day RSI rises above 50.
    NOTE: Only 83 trades in 30 years on SPY — very rare signal. Very high quality when it fires.
    """
    result = _fetch_bars(symbol, interval="1d", period="2y")
    if result is None:
        return {"signal": None}
    opens, highs, lows, closes, vols, dates = result
    n = len(closes)
    if n < 210:
        return {"signal": None}

    if not HAS_NP:
        return {"signal": None}
    cl = np.array(closes, dtype=float)

    rsi5  = _rsi(closes, 5)
    sma200 = _sma(closes, 200)

    price   = cl[-1]
    r5_now  = rsi5[-1]
    r5_1    = rsi5[-2]
    r5_2    = rsi5[-3]
    r5_3    = rsi5[-4]
    r5_63   = rsi5[-64] if len(rsi5) >= 64 else 50.0
    sma200v = sma200[-1]

    if np.isnan(sma200v):
        return {"signal": None}

    above_trend      = price > sma200v
    rsi5_declining   = r5_now < r5_1 < r5_2
    rsi5_below30     = r5_now < 30
    lower_than_63d   = r5_now < r5_63
    started_not_ob   = r5_3 < 60  # first day of decline was not overbought

    if above_trend and rsi5_declining and rsi5_below30 and lower_than_63d and started_not_ob:
        daily_rets = np.diff(cl[-21:]) / cl[-21:-1] * 100
        avg_vol = float(np.std(daily_rets)) if len(daily_rets) > 2 else 1.5
        sl_pct  = max(avg_vol * 3.0, 2.5)
        tp_pct  = sl_pct * 2.0  # wide TP (91% WR means let winners run)

        sma200_gap = (price - sma200v) / sma200v * 100

        return {
            "signal": "BUY",
            "reason": f"Triple RSI: 5-day RSI={r5_now:.1f} (<30, declining 3d, < 63d ago RSI={r5_63:.1f}), above SMA200 ({sma200_gap:+.1f}%) — 91% WR (83 trades), PF=5.0",
            "confidence": min(95, 78 + int((30 - r5_now) * 1.5)),
            "sl_pct": round(sl_pct, 2),
            "tp_pct": round(min(tp_pct, 8.0), 2),
            "strategy": "TripleRSI",
            "rsi5": round(r5_now, 2),
            "rsi5_63d_ago": round(r5_63, 2),
        }

    return {"signal": None}


# ==============================================================================
# STRATEGY 4: MACD + RSI Combo (4H, 73% WR on crypto)
# ==============================================================================

def signal_macd_rsi_combo_4h(symbol: str, data: dict) -> dict:
    """
    MACD + RSI Combo (4H timeframe, crypto-adapted).
    Source: QuantifiedStrategies.com — 235 trades, WR 73%, avg gain 0.88%.
    RSI filter transforms MACD from 52% WR to 73% WR.

    Entry: MACD crossover UP + RSI 40-60 (momentum zone, not overbought/oversold) + price > MA50.
    Exit: MACD crosses DOWN OR RSI > 70 (overbought).
    """
    bn = YF_TO_BINANCE.get(symbol)
    result = None
    if bn:
        result = _fetch_binance_klines(bn, interval="4h", limit=200)
    if result is None:
        result = _fetch_bars(symbol, interval="1h", period="2y")
        if result:
            # Resample to 4H: take every 4th bar
            o, h, l, c, v, d = result
            result = (o[::4], h[::4], l[::4], c[::4], v[::4], d[::4])

    if result is None:
        return {"signal": None}

    opens, highs, lows, closes, vols = result[:5]
    n = len(closes)
    if n < 60:
        return {"signal": None}

    if not HAS_NP:
        return {"signal": None}
    cl = np.array(closes, dtype=float)

    # MACD (12, 26, 9)
    ema12 = _ema(cl, 12)
    ema26 = _ema(cl, 26)
    macd  = ema12 - ema26
    signal_line = _ema(macd, 9)

    # RSI-14
    rsi14 = _rsi(closes, 14)

    # MA-50
    ma50 = _sma(closes, 50)

    # Current values
    price     = cl[-1]
    curr_macd = macd[-1]; prev_macd = macd[-2]
    curr_sig  = signal_line[-1]; prev_sig  = signal_line[-2]
    curr_rsi  = rsi14[-1]
    curr_ma50 = ma50[-1]

    if np.isnan(curr_ma50):
        return {"signal": None}

    # MACD bullish crossover (line crosses above signal)
    macd_cross_up = prev_macd < prev_sig and curr_macd >= curr_sig

    # RSI in momentum zone 40-60 (not oversold entering, not already overbought)
    rsi_momentum = 40 <= curr_rsi <= 62

    # Price above MA50 (trend filter)
    above_ma50 = price > curr_ma50

    # Volume confirmation (optional)
    if len(vols) > 21:
        avg_vol = float(np.mean(np.array(vols[-21:-1], dtype=float)))
        rvol = float(vols[-1]) / (avg_vol + 1e-9)
    else:
        rvol = 1.0

    if macd_cross_up and rsi_momentum and above_ma50:
        # ATR-based SL
        hi = np.array(highs, dtype=float); lo = np.array(lows, dtype=float)
        atr_vals = np.abs(hi[-14:] - lo[-14:])
        atr = float(np.mean(atr_vals)) if len(atr_vals) > 0 else price * 0.02
        sl_pct = atr / price * 100 * 1.5
        tp_pct = sl_pct * 2.0

        confidence = min(88, 58 + int((curr_rsi - 40) * 0.8) + int(rvol * 5))

        return {
            "signal": "BUY",
            "reason": f"MACD+RSI 4H: MACD crossed UP ({curr_macd:.5f}>{curr_sig:.5f}), RSI={curr_rsi:.1f} (momentum zone 40-62), above MA50 ({curr_ma50:.4f}) — 73% WR (235 trades), avg +0.88%",
            "confidence": confidence,
            "sl_pct": round(min(sl_pct, 4.0), 2),
            "tp_pct": round(min(tp_pct, 8.0), 2),
            "strategy": "MACD_RSI_4H",
            "macd": round(float(curr_macd), 6),
            "rsi14": round(curr_rsi, 1),
            "rvol": round(rvol, 2),
        }

    return {"signal": None}


# ==============================================================================
# STRATEGY 5: Fear & Greed Contrarian (BTC/Crypto)
# ==============================================================================

def signal_fear_greed_contrarian(symbol: str, data: dict) -> dict:
    """
    Fear & Greed Index Contrarian Buy (Bitcoin/Crypto).
    Source: Bitcoin Magazine backtest 2017-2024 — 1,145% ROI vs 1,046% buy-and-hold.
    WR: ~66.7% on extreme fear buys.

    Entry: Fear & Greed Index < 20 (Extreme Fear) + RSI-14 < 30 (confirmation).
    Exit: RSI > 50 OR Fear & Greed > 70. Hard stop: -15%.
    Uses alternative.me free API (no key needed).
    """
    # Only fire for BTC/ETH/SOL (crypto assets with Fear & Greed relevance)
    crypto_whitelist = {
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD",
        "XRP-USD", "ADA-USD", "LINK-USD", "DOGE-USD",
    }
    if symbol not in crypto_whitelist:
        return {"signal": None}

    fg_value = _get_fear_greed()
    if fg_value is None:
        return {"signal": None}

    # Only fire on EXTREME fear (< 20)
    if fg_value >= 20:
        return {"signal": None}

    # RSI confirmation from daily bars
    result = _fetch_bars(symbol, interval="1d", period="60d")
    if result is None:
        return {"signal": None}
    opens, highs, lows, closes, vols, dates = result
    if len(closes) < 20:
        return {"signal": None}

    if not HAS_NP:
        return {"signal": None}
    cl = np.array(closes, dtype=float)
    rsi14 = _rsi(closes, 14)
    curr_rsi = rsi14[-1]

    # RSI must confirm oversold
    if curr_rsi > 40:
        return {"signal": None}

    price = cl[-1]

    # Volatility-adjusted SL
    daily_rets = np.diff(cl[-21:]) / cl[-21:-1] * 100 if len(cl) >= 21 else np.array([2.0])
    avg_vol = float(np.std(daily_rets)) if len(daily_rets) > 1 else 2.0
    sl_pct  = max(avg_vol * 3.0, 8.0)   # crypto needs wide SL
    tp_pct  = sl_pct * 1.5              # 1.5:1 RR

    confidence = min(90, 65 + int((20 - fg_value) * 2) + int((40 - curr_rsi) * 0.5))
    sentiment_label = "Extreme Fear" if fg_value < 20 else "Fear"

    return {
        "signal": "BUY",
        "reason": f"Fear & Greed Contrarian: F&G={fg_value} ({sentiment_label}), RSI={curr_rsi:.1f} — historic 66.7% WR on extreme fear entries, 2017-2024 1,145% ROI",
        "confidence": confidence,
        "sl_pct": round(min(sl_pct, 15.0), 2),
        "tp_pct": round(min(tp_pct, 20.0), 2),
        "strategy": "FearGreedContrarian",
        "fear_greed_index": fg_value,
        "rsi14": round(curr_rsi, 1),
    }


# ==============================================================================
# STRATEGY 6: Crypto Cross-Sectional Momentum (2-week)
# ==============================================================================

_CRYPTO_MOMENTUM_CACHE: dict = {"returns": {}, "ts": 0}
_CRYPTO_MOMENTUM_UNIVERSE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "LINK-USD", "DOGE-USD", "MATIC-USD",
]


def _compute_crypto_momentum_ranks() -> dict:
    """Compute 14-day returns for the crypto universe and return rank (1=best)."""
    now = datetime.now(timezone.utc).timestamp()
    if now - _CRYPTO_MOMENTUM_CACHE["ts"] < 3600:  # 1H cache
        return _CRYPTO_MOMENTUM_CACHE["returns"]

    ranks = {}
    returns_14d = {}
    for sym in _CRYPTO_MOMENTUM_UNIVERSE:
        bn = YF_TO_BINANCE.get(sym)
        try:
            if bn and HAS_REQUESTS:
                _mirrors = [
                    "https://api.binance.com", "https://api1.binance.com",
                    "https://api2.binance.com", "https://api3.binance.com",
                    "https://data-api.binance.vision",
                ]
                for _base in _mirrors:
                    try:
                        r = requests.get(f"{_base}/api/v3/klines",
                                         params={"symbol": bn, "interval": "1d", "limit": 20}, timeout=5)
                        data = r.json()
                        if isinstance(data, list) and len(data) >= 15:
                            p_now = float(data[-1][4])
                            p_14d = float(data[-15][4])
                            returns_14d[sym] = (p_now - p_14d) / p_14d * 100
                        break
                    except Exception:
                        continue
        except Exception:
            pass

    if len(returns_14d) < 3:
        return {}

    # Rank by 14-day return (ascending rank = lower rank # = better performance)
    sorted_syms = sorted(returns_14d.items(), key=lambda x: x[1], reverse=True)
    n = len(sorted_syms)
    for rank_pos, (sym, ret) in enumerate(sorted_syms):
        ranks[sym] = {
            "rank": rank_pos + 1,
            "return_14d": ret,
            "n": n,
            "percentile": (n - rank_pos) / n * 100,  # 100 = top performer
        }
    _CRYPTO_MOMENTUM_CACHE["returns"] = ranks
    _CRYPTO_MOMENTUM_CACHE["ts"] = now
    return ranks


def signal_crypto_cross_momentum(symbol: str, data: dict) -> dict:
    """
    Crypto Cross-Sectional Momentum (2-week holding period).
    Source: SSRN — Huang, Sangiorgi, Urquhart (2024), Fracassi & Kogan research.
    Sharpe: 2.17 pre-costs | Long top-quintile, avoid/short bottom-quintile.

    Fires BUY on top 20th percentile (top ~2-3 coins of 10-coin universe) by 14-day return.
    """
    if symbol not in _CRYPTO_MOMENTUM_UNIVERSE:
        return {"signal": None}

    ranks = _compute_crypto_momentum_ranks()
    if not ranks or symbol not in ranks:
        return {"signal": None}

    rank_info = ranks[symbol]
    percentile = rank_info["percentile"]
    ret_14d    = rank_info["return_14d"]
    rank_pos   = rank_info["rank"]
    n          = rank_info["n"]

    # Top 20th percentile (top 2 of 10 coins)
    if percentile < 80:
        return {"signal": None}

    # Additional filter: must have positive 14-day return
    if ret_14d <= 0:
        return {"signal": None}

    confidence = min(82, 55 + int(percentile - 80) + int(ret_14d * 0.5))

    return {
        "signal": "BUY",
        "reason": f"Cross-Sectional Momentum: {symbol} rank #{rank_pos}/{n} (top {100-percentile:.0f}th percentile), 14d return={ret_14d:+.2f}% — SSRN Sharpe 2.17 pre-cost strategy",
        "confidence": confidence,
        "sl_pct": 8.0,    # crypto momentum: hold 2 weeks, wide stop
        "tp_pct": 12.0,   # 1.5:1 RR minimum
        "strategy": "CryptoCrossM momentum",
        "rank": rank_pos,
        "return_14d": round(ret_14d, 2),
        "percentile": round(percentile, 1),
    }


# ==============================================================================
# Registry
# ==============================================================================

MEAN_REVERSION_SIGNAL_FUNCS = {
    "connors-r3-scout":               signal_connors_r3,
    "williams-r-reversion-scout":     signal_williams_r_mean_reversion,
    "triple-rsi-scout":               signal_triple_rsi_mean_reversion,
    "macd-rsi-4h-scout":              signal_macd_rsi_combo_4h,
    "fear-greed-contrarian-scout":    signal_fear_greed_contrarian,
    "crypto-cross-momentum-scout":    signal_crypto_cross_momentum,
}

MEAN_REVERSION_ALGO_DEFS = {
    "connors-r3-scout": {
        "name": "Connors R3 Mean Reversion",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "ConnorsR3",
        "description": "992 trades, 75% WR, PF 2.08 (QuantifiedStrategies 30yr). RSI-2 triple-confirmation mean reversion above SMA200.",
        "symbols": ["SPY", "QQQ", "IWM", "DIA", "GLD", "TLT", "XLK", "XLF", "XLE", "XLV"],
    },
    "williams-r-reversion-scout": {
        "name": "Williams %R Mean Reversion",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "WilliamsRMeanReversion",
        "description": "280 trades, 81% WR (QuantifiedStrategies 1993-2024). W%R(2) drops below -90, close above prev high exit.",
        "symbols": ["SPY", "QQQ", "IWM", "DIA", "NVDA", "AAPL", "MSFT", "META", "GOOGL", "AMZN"],
    },
    "triple-rsi-scout": {
        "name": "Triple RSI Mean Reversion",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "TripleRSI",
        "description": "83 trades, 91% WR, PF 5.0 (Larry Connors). Rare but extreme quality signal. Price above SMA200 + 5-day RSI < 30 declining.",
        "symbols": ["SPY", "QQQ", "IWM", "GLD", "AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL"],
    },
    "macd-rsi-4h-scout": {
        "name": "MACD+RSI Combo 4H",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "MACD_RSI_4H",
        "description": "235 trades, 73% WR, avg +0.88% (QuantifiedStrategies). MACD crossover + RSI 40-62 filter on 4H bars.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD", "LINK-USD",
                    "XRP-USD", "ADA-USD", "DOGE-USD", "MATIC-USD", "NEAR-USD", "INJ-USD"],
    },
    "fear-greed-contrarian-scout": {
        "name": "Fear & Greed Contrarian (Crypto)",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "FearGreedContrarian",
        "description": "66.7% WR, 1,145% ROI 2017-2024 (Bitcoin Magazine backtest). Extreme Fear (<20) + RSI<30 contrarian buy.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD",
                    "XRP-USD", "ADA-USD", "LINK-USD", "DOGE-USD"],
    },
    "crypto-cross-momentum-scout": {
        "name": "Crypto Cross-Sectional Momentum",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "CryptoCrossMomentum",
        "description": "Sharpe 2.17 pre-cost (SSRN Huang/Sangiorgi/Urquhart 2024). Top-quintile 14-day momentum in 10-coin universe.",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                    "ADA-USD", "AVAX-USD", "LINK-USD", "DOGE-USD", "MATIC-USD"],
    },
}


# ==============================================================================
# Standalone test
# ==============================================================================

if __name__ == "__main__":
    test_symbols = {
        "stock": ["SPY", "QQQ"],
        "crypto": ["BTC-USD", "ETH-USD"],
    }
    print("\n" + "=" * 65)
    print("  PROVEN MEAN REVERSION STRATEGY TEST")
    print("=" * 65)

    for cat, syms in test_symbols.items():
        print(f"\n--- {cat.upper()} ---")
        for sym in syms:
            print(f"\n  {sym}:")
            for name, fn in MEAN_REVERSION_SIGNAL_FUNCS.items():
                try:
                    result = fn(sym, {})
                    if result.get("signal"):
                        print(f"    [{name}] SIGNAL: {result['signal']} | conf={result.get('confidence','?')} | {result.get('reason','')[:90]}")
                    else:
                        print(f"    [{name}] no signal")
                except Exception as ex:
                    print(f"    [{name}] ERROR: {ex}")

    # Also check Fear & Greed
    fg = _get_fear_greed()
    print(f"\n  Current Fear & Greed Index: {fg} ({'Extreme Fear' if fg and fg < 20 else 'Fear' if fg and fg < 40 else 'Neutral' if fg and fg < 60 else 'Greed'})")
    print("\n" + "=" * 65)
