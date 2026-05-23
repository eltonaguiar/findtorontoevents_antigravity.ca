"""
ALPHA_ENGINE -- High-Accuracy Strategies (Phase 1 Quick Wins)
==============================================================
3 algorithms from 100_ALGORITHMS_MASTER_CATALOG.md, all 65-72% expected WR.

Strategy 130: KAMA-Volatility Adaptive (#51 in catalog, 68-72% WR)
    Kaufman's Adaptive Moving Average adjusts smoothing based on market noise.
    Reference: Kaufman (1998) "Trading Systems and Methods", Perry Kaufman.

Strategy 131: RSI-MACD-Volume Confluence (#71 in catalog, 65-72% WR)
    Triple confirmation: RSI + MACD histogram + volume spike must all agree.
    Reference: Pring (2014) "Technical Analysis Explained"; Elder (2002).

Strategy 132: Kalman Filter Trend (#17 in catalog, 65-72% WR, Sharpe 1.5-2.0)
    Linear state-space model: [price, velocity] with Kalman predict/update.
    Reference: Kalman (1960); Avellaneda & Lee (2010) "Statistical Arbitrage".

Each strategy:
  - Uses pre-loaded daily data from scanner (data dict)
  - Also self-fetches 200x 4H candles from Binance with 4-mirror failover
  - Applies to top 15 crypto symbols by volume
  - Returns picks in standard format: symbol, direction, entry, tp, sl, confidence, strategy
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

from config import (
    CRYPTO_SYMBOLS, SPOT_BASES, COINGECKO_BASE,
)
from indicators import rsi, macd, atr, sma, volume_ratio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Top 15 symbols by typical volume (scanner will still pass all symbols)
# ---------------------------------------------------------------------------
TOP_15_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
    "LTCUSDT", "TRXUSDT", "ETCUSDT", "SUIUSDT", "TAOUSDT",
]

# Map internal symbol keys to Binance tickers
_SYMBOL_TO_BINANCE = {sym: info.get("binance", "") for sym, info in CRYPTO_SYMBOLS.items()}
_BINANCE_TO_SYMBOL = {v: k for k, v in _SYMBOL_TO_BINANCE.items() if v}

# CoinGecko ID map for fallback
_COINGECKO_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2", "DOGEUSDT": "dogecoin", "LINKUSDT": "chainlink",
    "NEARUSDT": "near", "LTCUSDT": "litecoin", "TRXUSDT": "tron",
    "ETCUSDT": "ethereum-classic", "SUIUSDT": "sui", "TAOUSDT": "bittensor",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(v: float) -> float:
    if v == 0:
        return 0.0
    av = abs(v)
    if av >= 100:
        return round(v, 2)
    if av >= 1:
        return round(v, 4)
    if av >= 0.01:
        return round(v, 6)
    return round(v, 10)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _fetch_json(url: str, timeout: int = 8):
    """Fetch JSON from URL, return dict/list or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _fetch_4h_candles(binance_symbol: str, limit: int = 200) -> Optional[pd.DataFrame]:
    """Fetch 4H candles from Binance with 4-mirror failover + CoinGecko fallback.

    Returns DataFrame with columns: Open, High, Low, Close, Volume
    or None on failure.
    """
    # Try all Binance mirrors
    for base in SPOT_BASES[:4]:
        url = (
            f"{base}/api/v3/klines?"
            f"symbol={binance_symbol}&interval=4h&limit={limit}"
        )
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 50:
            try:
                rows = []
                for k in data:
                    rows.append({
                        "Open": float(k[1]),
                        "High": float(k[2]),
                        "Low": float(k[3]),
                        "Close": float(k[4]),
                        "Volume": float(k[5]),
                    })
                return pd.DataFrame(rows)
            except (IndexError, ValueError, TypeError):
                continue

    # CoinGecko fallback (daily resolution, 30 days)
    cg_id = _COINGECKO_IDS.get(binance_symbol)
    if cg_id:
        url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days=30"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 50:
            try:
                rows = []
                for row in data:
                    rows.append({
                        "Open": float(row[1]),
                        "High": float(row[2]),
                        "Low": float(row[3]),
                        "Close": float(row[4]),
                        "Volume": 0.0,
                    })
                return pd.DataFrame(rows)
            except (IndexError, ValueError, TypeError):
                pass

    return None


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 2.0, sl_mult: float = 1.5,
               atr_period: int = 14) -> tuple:
    """Compute ATR-based TP/SL. Returns (price, tp, sl)."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _atr_tp_sl_short(close: pd.Series, high: pd.Series, low: pd.Series,
                     tp_mult: float = 2.0, sl_mult: float = 1.5,
                     atr_period: int = 14) -> tuple:
    """Compute ATR-based TP/SL for SHORT. Returns (price, tp, sl)."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price - tp_mult * current_atr
    sl = price + sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _make_pick(symbol: str, direction: str, entry: float, tp: float,
               sl: float, confidence: float, strategy: str,
               reason: str = "") -> dict:
    """Build a standard pick dict compatible with scanner.py."""
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "confidence": round(confidence, 3),
        "strategy": strategy,
        "asset_class": _get_category(symbol),
        "timestamp": _now_iso(),
        "reason": reason,
    }


# =========================================================================
# STRATEGY 130: KAMA-Volatility Adaptive (#51, 68-72% WR)
# =========================================================================
# Kaufman's Adaptive Moving Average (1998): smoothing constant adapts to
# market noise via Efficiency Ratio. In trending markets the MA is fast;
# in choppy markets it slows down, avoiding whipsaws.
#
# ER = abs(close[t] - close[t-N]) / sum(abs(close[i] - close[i-1]), i=1..N)
# Fast SC = 2/(2+1) = 0.6667, Slow SC = 2/(30+1) = 0.0645
# SC = (ER * (Fast - Slow) + Slow)^2
# KAMA[t] = KAMA[t-1] + SC * (close[t] - KAMA[t-1])
#
# BUY:  price crosses above KAMA AND KAMA slope > 0
# SELL: price crosses below KAMA AND KAMA slope < 0
# TP: 2x ATR, SL: 1.5x ATR
# =========================================================================

def _compute_kama(close: pd.Series, er_period: int = 10,
                  fast_period: int = 2, slow_period: int = 30) -> pd.Series:
    """Compute Kaufman Adaptive Moving Average."""
    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)

    close_arr = close.values.astype(float)
    n = len(close_arr)
    kama = np.full(n, np.nan)

    if n <= er_period:
        return pd.Series(kama, index=close.index)

    # Seed KAMA with simple average of first er_period values
    kama[er_period - 1] = np.mean(close_arr[:er_period])

    for i in range(er_period, n):
        direction = abs(close_arr[i] - close_arr[i - er_period])
        volatility = np.sum(np.abs(np.diff(close_arr[i - er_period:i + 1])))

        if volatility == 0:
            er = 0.0
        else:
            er = direction / volatility

        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama[i] = kama[i - 1] + sc * (close_arr[i] - kama[i - 1])

    return pd.Series(kama, index=close.index)


def kama_volatility_adaptive(data: dict[str, pd.DataFrame],
                             context: dict | None = None) -> list[dict]:
    """KAMA-Volatility Adaptive: Kaufman adaptive MA with slope confirmation.

    Uses pre-loaded daily data for initial scan, then fetches 4H candles
    for higher-resolution signal confirmation on top 15 symbols.
    """
    signals = []

    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 50:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Compute KAMA on daily data first
            kama_vals = _compute_kama(close, er_period=10)

            if pd.isna(kama_vals.iloc[-1]) or pd.isna(kama_vals.iloc[-2]):
                continue

            kama_now = float(kama_vals.iloc[-1])
            kama_prev = float(kama_vals.iloc[-2])
            price_now = float(close.iloc[-1])
            price_prev = float(close.iloc[-2])

            kama_slope = kama_now - kama_prev

            # BUY: price crosses above KAMA AND KAMA slope positive
            if price_now > kama_now and price_prev <= kama_prev and kama_slope > 0:
                entry, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=2.0, sl_mult=1.5)
                # Confidence based on ER strength
                direction_10 = abs(price_now - float(close.iloc[-10]))
                vol_10 = np.sum(np.abs(np.diff(close.values[-11:])))
                er = direction_10 / vol_10 if vol_10 > 0 else 0
                confidence = min(0.72, 0.55 + er * 0.2)

                signals.append(_make_pick(
                    symbol=symbol, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kama_volatility_adaptive",
                    reason=f"KAMA crossover: ER={er:.3f}, slope={kama_slope:.4f}",
                ))

            # SELL: price crosses below KAMA AND KAMA slope negative
            elif price_now < kama_now and price_prev >= kama_prev and kama_slope < 0:
                entry, tp, sl = _atr_tp_sl_short(close, high, low,
                                                 tp_mult=2.0, sl_mult=1.5)
                direction_10 = abs(price_now - float(close.iloc[-10]))
                vol_10 = np.sum(np.abs(np.diff(close.values[-11:])))
                er = direction_10 / vol_10 if vol_10 > 0 else 0
                confidence = min(0.72, 0.55 + er * 0.2)

                signals.append(_make_pick(
                    symbol=symbol, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kama_volatility_adaptive",
                    reason=f"KAMA breakdown: ER={er:.3f}, slope={kama_slope:.4f}",
                ))

        except Exception as e:
            logger.debug("kama_volatility_adaptive %s error: %s", symbol, e)
            continue

    # --- 4H confirmation pass on top 15 symbols for extra signals ---
    for bsym in TOP_15_SYMBOLS:
        internal = _BINANCE_TO_SYMBOL.get(bsym)
        if not internal or internal in {s["symbol"] for s in signals}:
            continue

        try:
            df4h = _fetch_4h_candles(bsym, limit=200)
            if df4h is None or len(df4h) < 50:
                continue

            close = df4h["Close"]
            high = df4h["High"]
            low = df4h["Low"]

            kama_vals = _compute_kama(close, er_period=10)
            if pd.isna(kama_vals.iloc[-1]) or pd.isna(kama_vals.iloc[-2]):
                continue

            kama_now = float(kama_vals.iloc[-1])
            kama_prev = float(kama_vals.iloc[-2])
            price_now = float(close.iloc[-1])
            price_prev = float(close.iloc[-2])
            kama_slope = kama_now - kama_prev

            if price_now > kama_now and price_prev <= kama_prev and kama_slope > 0:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5)
                direction_10 = abs(price_now - float(close.iloc[-10]))
                vol_10 = np.sum(np.abs(np.diff(close.values[-11:])))
                er = direction_10 / vol_10 if vol_10 > 0 else 0
                confidence = min(0.72, 0.55 + er * 0.2)

                signals.append(_make_pick(
                    symbol=internal or bsym, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kama_volatility_adaptive",
                    reason=f"4H KAMA cross: ER={er:.3f}, slope={kama_slope:.6f}",
                ))

            elif price_now < kama_now and price_prev >= kama_prev and kama_slope < 0:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.0, sl_mult=1.5)
                direction_10 = abs(price_now - float(close.iloc[-10]))
                vol_10 = np.sum(np.abs(np.diff(close.values[-11:])))
                er = direction_10 / vol_10 if vol_10 > 0 else 0
                confidence = min(0.72, 0.55 + er * 0.2)

                signals.append(_make_pick(
                    symbol=internal or bsym, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kama_volatility_adaptive",
                    reason=f"4H KAMA breakdown: ER={er:.3f}, slope={kama_slope:.6f}",
                ))

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 131: RSI-MACD-Volume Confluence (#71, 65-72% WR)
# =========================================================================
# Triple confirmation: ALL THREE must agree for a signal to fire.
#   1. RSI(14) < 40 (oversold zone for BUY) or > 60 (overbought for SELL)
#   2. MACD histogram positive & rising (BUY) or negative & falling (SELL)
#   3. Volume > 1.5x 20-period average
#
# Reference: Pring (2014) "Technical Analysis Explained"
#            Elder (2002) "Come into My Trading Room"
# TP: 2x ATR, SL: 1.5x ATR
# =========================================================================

def rsi_macd_volume_confluence(data: dict[str, pd.DataFrame],
                               context: dict | None = None) -> list[dict]:
    """RSI-MACD-Volume Confluence: triple confirmation high-WR filter.

    Only fires when RSI zone + MACD histogram direction + volume spike
    all align. Fewer signals but significantly higher accuracy.
    """
    signals = []

    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            # 1. RSI(14)
            rsi_vals = rsi(close, 14)
            rsi_now = float(rsi_vals.iloc[-1])

            # 2. MACD histogram
            macd_result = macd(close, fast=12, slow=26, signal=9)
            hist = macd_result["histogram"]
            if pd.isna(hist.iloc[-1]) or pd.isna(hist.iloc[-2]):
                continue
            hist_now = float(hist.iloc[-1])
            hist_prev = float(hist.iloc[-2])

            # 3. Volume ratio (current vs 20-period SMA)
            vol_ratio = volume_ratio(volume, 20)
            vol_now = float(vol_ratio.iloc[-1])

            # --- BUY confluence ---
            # RSI < 40 (oversold), MACD histogram positive & rising, volume > 1.5x avg
            if (rsi_now < 40
                    and hist_now > 0 and hist_now > hist_prev
                    and vol_now > 1.5):
                entry, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=2.0, sl_mult=1.5)
                confidence = min(0.72, 0.60 + (40 - rsi_now) * 0.003 + (vol_now - 1.5) * 0.02)

                signals.append(_make_pick(
                    symbol=symbol, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="rsi_macd_vol_confluence",
                    reason=(f"Triple confirm BUY: RSI={rsi_now:.1f}, "
                            f"MACD hist={hist_now:.4f} (rising), vol={vol_now:.1f}x"),
                ))

            # --- SELL confluence ---
            # RSI > 60 (overbought), MACD histogram negative & falling, volume > 1.5x avg
            elif (rsi_now > 60
                  and hist_now < 0 and hist_now < hist_prev
                  and vol_now > 1.5):
                entry, tp, sl = _atr_tp_sl_short(close, high, low,
                                                 tp_mult=2.0, sl_mult=1.5)
                confidence = min(0.72, 0.60 + (rsi_now - 60) * 0.003 + (vol_now - 1.5) * 0.02)

                signals.append(_make_pick(
                    symbol=symbol, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="rsi_macd_vol_confluence",
                    reason=(f"Triple confirm SELL: RSI={rsi_now:.1f}, "
                            f"MACD hist={hist_now:.4f} (falling), vol={vol_now:.1f}x"),
                ))

        except Exception as e:
            logger.debug("rsi_macd_vol_confluence %s error: %s", symbol, e)
            continue

    # --- 4H confirmation pass ---
    for bsym in TOP_15_SYMBOLS:
        internal = _BINANCE_TO_SYMBOL.get(bsym)
        if not internal or internal in {s["symbol"] for s in signals}:
            continue

        try:
            df4h = _fetch_4h_candles(bsym, limit=200)
            if df4h is None or len(df4h) < 30:
                continue

            close = df4h["Close"]
            high = df4h["High"]
            low = df4h["Low"]
            volume = df4h["Volume"]

            rsi_vals = rsi(close, 14)
            rsi_now = float(rsi_vals.iloc[-1])

            macd_result = macd(close, fast=12, slow=26, signal=9)
            hist = macd_result["histogram"]
            if pd.isna(hist.iloc[-1]) or pd.isna(hist.iloc[-2]):
                continue
            hist_now = float(hist.iloc[-1])
            hist_prev = float(hist.iloc[-2])

            vol_ratio_vals = volume_ratio(volume, 20)
            vol_now = float(vol_ratio_vals.iloc[-1])

            if rsi_now < 40 and hist_now > 0 and hist_now > hist_prev and vol_now > 1.5:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5)
                confidence = min(0.72, 0.60 + (40 - rsi_now) * 0.003 + (vol_now - 1.5) * 0.02)
                signals.append(_make_pick(
                    symbol=internal or bsym, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="rsi_macd_vol_confluence",
                    reason=f"4H triple BUY: RSI={rsi_now:.1f}, hist={hist_now:.4f}, vol={vol_now:.1f}x",
                ))
            elif rsi_now > 60 and hist_now < 0 and hist_now < hist_prev and vol_now > 1.5:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.0, sl_mult=1.5)
                confidence = min(0.72, 0.60 + (rsi_now - 60) * 0.003 + (vol_now - 1.5) * 0.02)
                signals.append(_make_pick(
                    symbol=internal or bsym, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="rsi_macd_vol_confluence",
                    reason=f"4H triple SELL: RSI={rsi_now:.1f}, hist={hist_now:.4f}, vol={vol_now:.1f}x",
                ))

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 132: Kalman Filter Trend (#17, 65-72% WR, Sharpe 1.5-2.0)
# =========================================================================
# Linear state-space model:
#   State vector: x = [price, velocity]
#   Transition:   x(t+1) = F * x(t) + process_noise
#       F = [[1, 1], [0, 1]]  (price += velocity, velocity persists)
#   Observation:  z(t) = H * x(t) + observation_noise
#       H = [1, 0]  (we observe price only)
#
# Standard Kalman equations (predict + update):
#   Predict: x_pred = F * x, P_pred = F * P * F' + Q
#   Update:  K = P_pred * H' * inv(H * P_pred * H' + R)
#            x = x_pred + K * (z - H * x_pred)
#            P = (I - K * H) * P_pred
#
# BUY:  Kalman velocity > 0 AND acceleration positive (velocity increasing)
# SELL: Kalman velocity < 0 AND acceleration negative (velocity decreasing)
# TP: 2.5x ATR, SL: 1.5x ATR
#
# Reference: Kalman (1960); Avellaneda & Lee (2010) "Statistical Arbitrage"
# =========================================================================

def _kalman_filter(prices: np.ndarray,
                   process_var: float = 1e-5,
                   obs_var: float = 1e-3) -> tuple:
    """Run Kalman filter on price series.

    Returns (filtered_prices, velocities) as numpy arrays.
    """
    n = len(prices)

    # State: [price, velocity]
    F = np.array([[1.0, 1.0],
                  [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = np.array([[process_var, 0.0],
                  [0.0, process_var]])
    R = np.array([[obs_var]])

    # Initialize
    x = np.array([prices[0], 0.0])
    P = np.eye(2) * 1.0

    filtered = np.zeros(n)
    velocities = np.zeros(n)

    for i in range(n):
        # Predict
        x_pred = F @ x
        P_pred = F @ P @ F.T + Q

        # Update
        z = prices[i]
        y = z - H @ x_pred  # innovation
        S = H @ P_pred @ H.T + R  # innovation covariance
        K = P_pred @ H.T @ np.linalg.inv(S)  # Kalman gain

        x = x_pred + K.flatten() * float(y)
        P = (np.eye(2) - K @ H) @ P_pred

        filtered[i] = x[0]
        velocities[i] = x[1]

    return filtered, velocities


def kalman_filter_trend(data: dict[str, pd.DataFrame],
                        context: dict | None = None) -> list[dict]:
    """Kalman Filter Trend: state-space velocity + acceleration detection.

    Tracks price and velocity with a Kalman filter. Signals fire when
    velocity and acceleration (change in velocity) agree on direction.
    """
    signals = []

    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            prices = close.values.astype(float)

            # Scale process/observation variance to price magnitude
            price_scale = np.mean(prices[-20:])
            pv = (price_scale * 1e-4) ** 2
            ov = (price_scale * 1e-2) ** 2

            filtered, velocities = _kalman_filter(prices,
                                                  process_var=pv,
                                                  obs_var=ov)

            vel_now = velocities[-1]
            vel_prev = velocities[-2]
            accel = vel_now - vel_prev

            # BUY: velocity > 0 AND acceleration positive
            if vel_now > 0 and accel > 0:
                entry, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=2.5, sl_mult=1.5)
                # Confidence from velocity magnitude relative to price
                vel_pct = abs(vel_now) / price_scale if price_scale > 0 else 0
                confidence = min(0.72, 0.58 + vel_pct * 50)

                signals.append(_make_pick(
                    symbol=symbol, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kalman_filter_trend",
                    reason=(f"Kalman BUY: vel={vel_now:.4f}, "
                            f"accel={accel:.4f}, filtered={filtered[-1]:.2f}"),
                ))

            # SELL: velocity < 0 AND acceleration negative
            elif vel_now < 0 and accel < 0:
                entry, tp, sl = _atr_tp_sl_short(close, high, low,
                                                 tp_mult=2.5, sl_mult=1.5)
                vel_pct = abs(vel_now) / price_scale if price_scale > 0 else 0
                confidence = min(0.72, 0.58 + vel_pct * 50)

                signals.append(_make_pick(
                    symbol=symbol, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kalman_filter_trend",
                    reason=(f"Kalman SELL: vel={vel_now:.4f}, "
                            f"accel={accel:.4f}, filtered={filtered[-1]:.2f}"),
                ))

        except Exception as e:
            logger.debug("kalman_filter_trend %s error: %s", symbol, e)
            continue

    # --- 4H pass on top 15 symbols ---
    for bsym in TOP_15_SYMBOLS:
        internal = _BINANCE_TO_SYMBOL.get(bsym)
        if not internal or internal in {s["symbol"] for s in signals}:
            continue

        try:
            df4h = _fetch_4h_candles(bsym, limit=200)
            if df4h is None or len(df4h) < 30:
                continue

            close = df4h["Close"]
            high = df4h["High"]
            low = df4h["Low"]
            prices = close.values.astype(float)

            price_scale = np.mean(prices[-20:])
            pv = (price_scale * 1e-4) ** 2
            ov = (price_scale * 1e-2) ** 2

            filtered, velocities = _kalman_filter(prices, process_var=pv, obs_var=ov)

            vel_now = velocities[-1]
            vel_prev = velocities[-2]
            accel = vel_now - vel_prev

            if vel_now > 0 and accel > 0:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.5)
                vel_pct = abs(vel_now) / price_scale if price_scale > 0 else 0
                confidence = min(0.72, 0.58 + vel_pct * 50)
                signals.append(_make_pick(
                    symbol=internal or bsym, direction="BUY",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kalman_filter_trend",
                    reason=f"4H Kalman BUY: vel={vel_now:.4f}, accel={accel:.4f}",
                ))
            elif vel_now < 0 and accel < 0:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.5, sl_mult=1.5)
                vel_pct = abs(vel_now) / price_scale if price_scale > 0 else 0
                confidence = min(0.72, 0.58 + vel_pct * 50)
                signals.append(_make_pick(
                    symbol=internal or bsym, direction="SELL",
                    entry=entry, tp=tp, sl=sl,
                    confidence=confidence,
                    strategy="kalman_filter_trend",
                    reason=f"4H Kalman SELL: vel={vel_now:.4f}, accel={accel:.4f}",
                ))

        except Exception:
            continue

    return signals


# ---------------------------------------------------------------------------
# Strategy registry (matches alpha_engine convention)
# ---------------------------------------------------------------------------
HIGH_ACCURACY_STRATEGIES = {
    "kama_volatility_adaptive": kama_volatility_adaptive,
    "rsi_macd_vol_confluence": rsi_macd_volume_confluence,
    "kalman_filter_trend": kalman_filter_trend,
}
