"""
MeanReversionEngine - Consolidated Base Class
==============================================

Replaces 12 duplicate mean-reversion scripts with one parameterized engine.

Each variant is defined by its indicator type, period, thresholds, and name.
The engine computes the relevant indicator, checks oversold/overbought conditions,
and generates picks in a standard format.

Existing individual scripts remain for backwards compatibility.

Dependencies: numpy, requests (no pandas required)
"""

import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import requests

# ---------------------------------------------------------------------------
# Variant configurations — one entry per existing script
# ---------------------------------------------------------------------------

VARIANTS: Dict[str, dict] = {
    "bollinger": {
        "name": "Bollinger Mean Reversion",
        "indicator": "bollinger",
        "period": 20,
        "std_mult": 2.0,
        "trend_period": 200,
        "oversold_desc": "Price at/below lower Bollinger Band in uptrend",
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.5,
    },
    "connors_rsi2": {
        "name": "Connors RSI-2 Mean Reversion",
        "indicator": "rsi",
        "period": 2,
        "oversold": 5,
        "overbought": 95,
        "trend_period": 200,
        "oversold_desc": "RSI(2) < 5 in uptrend (Connors & Alvarez 2008)",
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 2.0,
    },
    "connors_r3": {
        "name": "Connors R3 Mean Reversion",
        "indicator": "connors_r3",
        "period": 2,
        "oversold": 10,
        "overbought": 90,
        "consec_days": 3,
        "trend_period": 200,
        "oversold_desc": "3 consecutive lower closes + RSI(2) < 10 in uptrend",
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 2.0,
    },
    "zscore": {
        "name": "Z-Score Mean Reversion",
        "indicator": "zscore",
        "period": 20,
        "oversold": -2.0,
        "overbought": 2.0,
        "extreme": -3.0,
        "rsi_confirm": True,
        "oversold_desc": "Z-score <= -2.0 with RSI confirmation",
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.5,
    },
    "keltner": {
        "name": "Keltner Mean Reversion",
        "indicator": "keltner",
        "ema_period": 20,
        "atr_mult": 2.0,
        "trend_period": 200,
        "oversold_desc": "Price at/below lower Keltner channel in uptrend",
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 2.0,
    },
    "williams_r": {
        "name": "Williams %R Mean Reversion",
        "indicator": "williams_r",
        "period": 14,
        "oversold": -80,
        "overbought": -20,
        "trend_period": 200,
        "oversold_desc": "Williams %R < -80 oversold in uptrend",
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 2.0,
    },
    "stochastic": {
        "name": "Stochastic Mean Reversion",
        "indicator": "stochastic",
        "k_period": 14,
        "d_period": 3,
        "oversold": 20,
        "overbought": 80,
        "oversold_desc": "Stochastic %K oversold crossover",
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.5,
    },
    "adx_range": {
        "name": "ADX Range Mean Reversion",
        "indicator": "adx_range",
        "adx_period": 14,
        "adx_max": 20,
        "rsi_period": 14,
        "bb_period": 20,
        "bb_mult": 2.0,
        "oversold_desc": "ADX < 20 (ranging) + RSI oversold + BB lower touch",
        "tp_pct": 2.0,
        "sl_pct": 1.5,
    },
    "rsi_volume": {
        "name": "RSI Volume Mean Reversion",
        "indicator": "rsi_volume",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "volume_period": 20,
        "volume_mult": 1.2,
        "oversold_desc": "RSI oversold + volume spike confirmation",
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.5,
    },
    "kalman": {
        "name": "Kalman Mean Reversion",
        "indicator": "kalman",
        "process_variance": 1e-5,
        "measurement_variance": 1e-3,
        "deviation_threshold": 2.0,
        "oversold_desc": "Price deviates significantly from Kalman filter estimate",
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.5,
    },
    "kama": {
        "name": "KAMA Mean Reversion",
        "indicator": "kama",
        "er_period": 10,
        "fast_sc": 2,
        "slow_sc": 30,
        "z_threshold": 1.5,
        "trend_period": 200,
        "oversold_desc": "Price below KAMA by z_threshold std devs in uptrend",
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.5,
    },
    "red_candle": {
        "name": "Red Candle Mean Reversion",
        "indicator": "red_candle",
        "min_red_candles": 3,
        "rsi_period": 2,
        "rsi_threshold": 10,
        "ema_trend": 200,
        "oversold_desc": "3+ red candles + RSI(2) < 10 above EMA200",
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 2.0,
    },
}


# ---------------------------------------------------------------------------
# Binance price fetcher (reuse project pattern, numpy-only)
# ---------------------------------------------------------------------------

def fetch_binance_klines(symbol: str = "BTCUSDT", interval: str = "1h",
                         limit: int = 300) -> Optional[dict]:
    """Fetch OHLCV from Binance spot API. Returns dict with numpy arrays."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        if not raw:
            return None
        opens = np.array([float(c[1]) for c in raw])
        highs = np.array([float(c[2]) for c in raw])
        lows = np.array([float(c[3]) for c in raw])
        closes = np.array([float(c[4]) for c in raw])
        volumes = np.array([float(c[5]) for c in raw])
        return {
            "open": opens, "high": highs, "low": lows,
            "close": closes, "volume": volumes,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Indicator helper functions (all operate on numpy arrays)
# ---------------------------------------------------------------------------

def _rsi(closes: np.ndarray, period: int) -> np.ndarray:
    """Wilder RSI."""
    n = len(closes)
    result = np.full(n, 50.0)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    if len(gains) < period:
        return result
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for j in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[j]) / period
        avg_loss = (avg_loss * (period - 1) + losses[j]) / period
        if avg_loss == 0:
            result[j + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[j + 1] = 100.0 - (100.0 / (1.0 + rs))
    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    result = np.zeros(len(data))
    k = 2.0 / (period + 1)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average (NaN for first period-1 values)."""
    result = np.full(len(data), np.nan)
    for i in range(period - 1, len(data)):
        result[i] = float(np.mean(data[i - period + 1: i + 1]))
    return result


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
         period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i - 1]),
                     abs(lows[i] - closes[i - 1]))
    atr_arr = np.zeros(n)
    if n >= period:
        atr_arr[period - 1] = float(np.mean(tr[:period]))
        for i in range(period, n):
            atr_arr[i] = (atr_arr[i - 1] * (period - 1) + tr[i]) / period
    return atr_arr


def _adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
         period: int = 14) -> np.ndarray:
    """Average Directional Index."""
    n = len(closes)
    result = np.zeros(n)
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for j in range(1, n):
        h_diff = highs[j] - highs[j - 1]
        l_diff = lows[j - 1] - lows[j]
        tr[j] = max(highs[j] - lows[j],
                     abs(highs[j] - closes[j - 1]),
                     abs(lows[j] - closes[j - 1]))
        plus_dm[j] = h_diff if h_diff > l_diff and h_diff > 0 else 0
        minus_dm[j] = l_diff if l_diff > h_diff and l_diff > 0 else 0
    if n <= period:
        return result
    atr_sm = np.zeros(n)
    dx = np.zeros(n)
    atr_sm[period] = float(np.mean(tr[1:period + 1]))
    s_plus = float(np.mean(plus_dm[1:period + 1]))
    s_minus = float(np.mean(minus_dm[1:period + 1]))
    for j in range(period + 1, n):
        atr_sm[j] = (atr_sm[j - 1] * (period - 1) + tr[j]) / period
        s_plus = (s_plus * (period - 1) + plus_dm[j]) / period
        s_minus = (s_minus * (period - 1) + minus_dm[j]) / period
        if atr_sm[j] > 0:
            pdi = 100 * s_plus / atr_sm[j]
            mdi = 100 * s_minus / atr_sm[j]
        else:
            pdi = mdi = 0
        di_sum = pdi + mdi
        if di_sum > 0:
            dx[j] = 100 * abs(pdi - mdi) / di_sum
    start = period * 2
    if start < n:
        result[start] = float(np.mean(dx[period + 1:start + 1]))
        for j in range(start + 1, n):
            result[j] = (result[j - 1] * (period - 1) + dx[j]) / period
    return result


def _stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                k_period: int = 14, d_period: int = 3):
    """Stochastic %K and %D."""
    n = len(closes)
    k = np.full(n, 50.0)
    for i in range(k_period - 1, n):
        hh = float(np.max(highs[i - k_period + 1: i + 1]))
        ll = float(np.min(lows[i - k_period + 1: i + 1]))
        rng = hh - ll
        if rng > 0:
            k[i] = 100.0 * (closes[i] - ll) / rng
        else:
            k[i] = 50.0
    d = _sma(k, d_period)
    return k, d


def _williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                period: int = 14) -> np.ndarray:
    """Williams %R."""
    n = len(closes)
    wr = np.full(n, -50.0)
    for i in range(period - 1, n):
        hh = float(np.max(highs[i - period + 1: i + 1]))
        ll = float(np.min(lows[i - period + 1: i + 1]))
        rng = hh - ll
        if rng > 0:
            wr[i] = -100.0 * (hh - closes[i]) / rng
        else:
            wr[i] = -50.0
    return wr


def _kalman_filter(closes: np.ndarray, process_var: float = 1e-5,
                   measurement_var: float = 1e-3):
    """Simple 1D Kalman filter. Returns (estimates, errors)."""
    n = len(closes)
    estimates = np.zeros(n)
    errors = np.zeros(n)
    x = closes[0]
    p = 1.0
    for i in range(n):
        # Predict
        p = p + process_var
        # Update
        k_gain = p / (p + measurement_var)
        x = x + k_gain * (closes[i] - x)
        p = (1 - k_gain) * p
        estimates[i] = x
        errors[i] = abs(closes[i] - x)
    return estimates, errors


def _kama(closes: np.ndarray, er_period: int = 10,
          fast_sc: int = 2, slow_sc: int = 30) -> np.ndarray:
    """Kaufman Adaptive Moving Average."""
    n = len(closes)
    result = np.zeros(n)
    result[0] = closes[0]
    fast_alpha = 2.0 / (fast_sc + 1)
    slow_alpha = 2.0 / (slow_sc + 1)
    for i in range(1, n):
        if i >= er_period:
            direction = abs(closes[i] - closes[i - er_period])
            volatility = float(np.sum(np.abs(np.diff(closes[i - er_period:i + 1]))))
            er = direction / volatility if volatility > 0 else 0
            sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        else:
            sc = slow_alpha
        result[i] = result[i - 1] + sc * (closes[i] - result[i - 1])
    return result


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class MeanReversionEngine:
    """Unified mean-reversion engine supporting 12 indicator variants."""

    def __init__(self, variant: str):
        if variant not in VARIANTS:
            raise ValueError(
                f"Unknown variant '{variant}'. Available: {list(VARIANTS.keys())}"
            )
        self.variant = variant
        self.config = VARIANTS[variant]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, symbol: str, prices: dict,
             volumes: Optional[np.ndarray] = None) -> Optional[dict]:
        """
        Scan a single variant for a signal.

        Parameters
        ----------
        symbol : str  — e.g. "BTCUSDT"
        prices : dict — must contain "close" (np.ndarray), optionally
                        "high", "low", "open", "volume"
        volumes : optional override for volume data

        Returns
        -------
        dict pick or None
        """
        closes = np.asarray(prices["close"], dtype=float)
        highs = np.asarray(prices.get("high", closes), dtype=float)
        lows = np.asarray(prices.get("low", closes), dtype=float)
        opens = np.asarray(prices.get("open", closes), dtype=float)
        vols = volumes if volumes is not None else np.asarray(
            prices.get("volume", np.ones(len(closes))), dtype=float
        )

        indicator = self.config["indicator"]
        handler = getattr(self, f"_scan_{indicator}", None)
        if handler is None:
            return None
        return handler(symbol, closes, highs, lows, opens, vols)

    @classmethod
    def scan_all_variants(cls, symbol: str, prices: dict,
                          volumes: Optional[np.ndarray] = None) -> List[dict]:
        """Run all 12 variants and return a list of picks (non-None only)."""
        picks = []
        for variant_name in VARIANTS:
            engine = cls(variant_name)
            pick = engine.scan(symbol, prices, volumes)
            if pick is not None:
                picks.append(pick)
        return picks

    def backtest(self, symbol: str, prices: dict,
                 volumes: Optional[np.ndarray] = None) -> dict:
        """
        Simple walk-forward backtest over the price array.

        Returns dict with win_rate, total_trades, sharpe, avg_return, max_dd.
        """
        closes = np.asarray(prices["close"], dtype=float)
        highs = np.asarray(prices.get("high", closes), dtype=float)
        lows = np.asarray(prices.get("low", closes), dtype=float)
        opens = np.asarray(prices.get("open", closes), dtype=float)
        vols = volumes if volumes is not None else np.asarray(
            prices.get("volume", np.ones(len(closes))), dtype=float
        )

        min_bars = 220  # need enough history for 200-period indicators
        if len(closes) < min_bars:
            return {"win_rate": 0, "total_trades": 0, "sharpe": 0,
                    "avg_return": 0, "max_dd": 0, "variant": self.variant}

        trades: List[float] = []
        max_hold = 12

        i = min_bars
        while i < len(closes) - max_hold:
            # Build a slice of prices up to bar i
            slice_prices = {
                "close": closes[:i + 1],
                "high": highs[:i + 1],
                "low": lows[:i + 1],
                "open": opens[:i + 1],
                "volume": vols[:i + 1],
            }
            pick = self.scan(symbol, slice_prices)
            if pick is not None:
                entry = closes[i]
                direction = 1.0 if pick["direction"] == "LONG" else -1.0
                # Hold up to max_hold bars, exit at TP/SL or end
                tp = pick.get("take_profit", entry * (1 + 0.03 * direction))
                sl = pick.get("stop_loss", entry * (1 - 0.02 * direction))
                exit_price = closes[min(i + max_hold, len(closes) - 1)]
                for j in range(i + 1, min(i + max_hold + 1, len(closes))):
                    if direction > 0:
                        if highs[j] >= tp:
                            exit_price = tp
                            break
                        if lows[j] <= sl:
                            exit_price = sl
                            break
                    else:
                        if lows[j] <= tp:
                            exit_price = tp
                            break
                        if highs[j] >= sl:
                            exit_price = sl
                            break
                    exit_price = closes[j]
                ret = direction * (exit_price - entry) / entry
                trades.append(ret)
                i += max_hold + 1  # skip ahead
            else:
                i += 1

        if not trades:
            return {"win_rate": 0, "total_trades": 0, "sharpe": 0,
                    "avg_return": 0, "max_dd": 0, "variant": self.variant}

        wins = sum(1 for t in trades if t > 0)
        avg_ret = float(np.mean(trades))
        std_ret = float(np.std(trades)) if len(trades) > 1 else 1e-10
        sharpe = (avg_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0

        # Max drawdown
        equity = np.cumprod(1 + np.array(trades))
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0

        return {
            "variant": self.variant,
            "win_rate": round(wins / len(trades) * 100, 1),
            "total_trades": len(trades),
            "sharpe": round(sharpe, 2),
            "avg_return": round(avg_ret * 100, 3),
            "max_dd": round(max_dd * 100, 2),
        }

    @classmethod
    def list_variants(cls) -> List[str]:
        """Return available variant names."""
        return list(VARIANTS.keys())

    # ------------------------------------------------------------------
    # Pick builder
    # ------------------------------------------------------------------

    def _make_pick(self, symbol: str, direction: str, confidence: float,
                   entry_price: float, reason: str,
                   tp: float = 0, sl: float = 0) -> dict:
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(min(max(confidence, 0.1), 0.95), 3),
            "entry_price": round(entry_price, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "strategy": self.config["name"],
            "source": f"mean_reversion_base:{self.variant}",
            "reason": reason,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ------------------------------------------------------------------
    # Variant scan implementations
    # ------------------------------------------------------------------

    def _scan_bollinger(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        period = cfg["period"]
        std_mult = cfg["std_mult"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        sma_bb = _sma(closes, period)
        std_arr = np.full(len(closes), np.nan)
        for i in range(period - 1, len(closes)):
            std_arr[i] = float(np.std(closes[i - period + 1: i + 1]))
        lower = sma_bb - std_mult * std_arr
        sma_trend = _sma(closes, trend_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if np.isnan(sma_bb[i]) or np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        if price <= lower[i] and price > sma_trend[i] * 0.9:
            depth = (lower[i] - price) / atr_arr[i] if atr_arr[i] > 0 else 0
            conf = 0.5 + depth * 0.15 + 0.1
            tp = sma_bb[i]  # target middle band
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Price {price:.2f} at lower BB {lower[i]:.2f}, target middle {sma_bb[i]:.2f}",
                tp=tp, sl=sl)
        return None

    def _scan_rsi(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        period = cfg["period"]
        oversold = cfg["oversold"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        rsi_arr = _rsi(closes, period)
        sma_trend = _sma(closes, trend_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        cur_rsi = rsi_arr[i]
        prev_rsi = rsi_arr[i - 1] if i > 0 else 50
        # BUY: uptrend + RSI oversold + fresh cross
        if price > sma_trend[i] and cur_rsi < oversold and prev_rsi >= oversold:
            depth = (oversold - cur_rsi) / oversold
            trend_str = (price - sma_trend[i]) / sma_trend[i]
            conf = 0.5 + depth * 0.3 + trend_str * 0.2
            tp = price + atr_arr[i] * cfg["tp_atr_mult"]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"RSI({period})={cur_rsi:.1f} < {oversold} in uptrend",
                tp=tp, sl=sl)
        return None

    def _scan_connors_r3(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        period = cfg["period"]
        oversold = cfg["oversold"]
        consec = cfg["consec_days"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        # Check consecutive lower closes
        n = len(closes)
        count = 0
        for j in range(n - 1, max(n - 10, 0), -1):
            if j > 0 and closes[j] < closes[j - 1]:
                count += 1
            else:
                break
        if count < consec:
            return None
        rsi_arr = _rsi(closes, period)
        sma_trend = _sma(closes, trend_p)
        atr_arr = _atr(highs, lows, closes)
        i = n - 1
        if np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        cur_rsi = rsi_arr[i]
        if price > sma_trend[i] and cur_rsi < oversold:
            depth = (oversold - cur_rsi) / oversold
            conf = 0.55 + depth * 0.3 + count * 0.03
            tp = price + atr_arr[i] * cfg["tp_atr_mult"]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Connors R3: {count} lower closes + RSI({period})={cur_rsi:.1f} < {oversold}",
                tp=tp, sl=sl)
        return None

    def _scan_zscore(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        period = cfg["period"]
        oversold = cfg["oversold"]
        overbought = cfg["overbought"]
        if len(closes) < period + 20:
            return None
        sma_arr = _sma(closes, period)
        std_arr = np.full(len(closes), np.nan)
        for j in range(period - 1, len(closes)):
            std_arr[j] = float(np.std(closes[j - period + 1: j + 1]))
        i = len(closes) - 1
        if np.isnan(sma_arr[i]) or std_arr[i] <= 0:
            return None
        zscore = (closes[i] - sma_arr[i]) / (std_arr[i] + 1e-10)
        atr_arr = _atr(highs, lows, closes)
        price = closes[i]
        if atr_arr[i] <= 0:
            return None
        rsi_arr = _rsi(closes, 14) if cfg.get("rsi_confirm") else None
        # BUY: extreme negative z-score
        if zscore <= oversold:
            if rsi_arr is not None and rsi_arr[i] >= 35:
                return None
            extreme = cfg.get("extreme", -3.0)
            strength = min(abs(zscore) / abs(extreme), 1.0)
            conf = 0.55 + strength * 0.35
            tp_to_mean = sma_arr[i] - price
            tp = price + max(tp_to_mean * 0.6, atr_arr[i] * cfg["tp_atr_mult"])
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Z-score={zscore:.2f} <= {oversold}",
                tp=tp, sl=sl)
        # SELL: extreme positive z-score
        if zscore >= overbought:
            if rsi_arr is not None and rsi_arr[i] <= 65:
                return None
            extreme = cfg.get("extreme", 3.0)
            strength = min(abs(zscore) / abs(extreme), 1.0)
            conf = 0.55 + strength * 0.35
            tp_to_mean = price - sma_arr[i]
            tp = price - max(tp_to_mean * 0.6, atr_arr[i] * cfg["tp_atr_mult"])
            sl = price + atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "SHORT", conf, price,
                f"Z-score={zscore:.2f} >= {overbought}",
                tp=tp, sl=sl)
        return None

    def _scan_keltner(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        ema_p = cfg["ema_period"]
        atr_m = cfg["atr_mult"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        ema_arr = _ema(closes, ema_p)
        atr_arr = _atr(highs, lows, closes)
        lower = ema_arr - atr_m * atr_arr
        sma_trend = _sma(closes, trend_p)
        i = len(closes) - 1
        if np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        prev = closes[i - 1] if i > 0 else price
        prev_lower = lower[i - 1] if i > 0 else lower[i]
        if price > sma_trend[i] and price <= lower[i] and prev > prev_lower:
            depth = (lower[i] - price) / atr_arr[i] if atr_arr[i] > 0 else 0
            trend_str = (price - sma_trend[i]) / sma_trend[i]
            conf = 0.6 + depth * 0.2 + trend_str * 0.1
            tp = ema_arr[i]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Keltner lower touch: price {price:.2f} <= lower {lower[i]:.2f}",
                tp=tp, sl=sl)
        return None

    def _scan_williams_r(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        period = cfg["period"]
        oversold = cfg["oversold"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        wr = _williams_r(highs, lows, closes, period)
        sma_trend = _sma(closes, trend_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        cur_wr = wr[i]
        prev_wr = wr[i - 1] if i > 0 else -50
        if price > sma_trend[i] and cur_wr < oversold and prev_wr >= oversold:
            depth = (oversold - cur_wr) / abs(oversold)
            conf = 0.5 + depth * 0.3
            tp = price + atr_arr[i] * cfg["tp_atr_mult"]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Williams %R={cur_wr:.1f} < {oversold} oversold in uptrend",
                tp=tp, sl=sl)
        return None

    def _scan_stochastic(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        k_p = cfg["k_period"]
        d_p = cfg["d_period"]
        oversold = cfg["oversold"]
        overbought = cfg["overbought"]
        if len(closes) < k_p + d_p + 20:
            return None
        k, d = _stochastic(highs, lows, closes, k_p, d_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if atr_arr[i] <= 0 or np.isnan(d[i]):
            return None
        price = closes[i]
        # BUY: oversold + K crosses above D
        if k[i] < oversold and i > 0 and k[i - 1] <= d[i - 1] and k[i] > d[i]:
            conf = (oversold - k[i]) / oversold
            tp = price + atr_arr[i] * cfg["tp_atr_mult"]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Stochastic oversold crossover K:{k[i]:.1f} D:{d[i]:.1f}",
                tp=tp, sl=sl)
        # SELL: overbought + K crosses below D
        if k[i] > overbought and i > 0 and k[i - 1] >= d[i - 1] and k[i] < d[i]:
            conf = (k[i] - overbought) / (100 - overbought)
            tp = price - atr_arr[i] * cfg["tp_atr_mult"]
            sl = price + atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "SHORT", conf, price,
                f"Stochastic overbought crossover K:{k[i]:.1f} D:{d[i]:.1f}",
                tp=tp, sl=sl)
        return None

    def _scan_adx_range(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        adx_p = cfg["adx_period"]
        adx_max = cfg["adx_max"]
        rsi_p = cfg["rsi_period"]
        bb_p = cfg["bb_period"]
        bb_m = cfg["bb_mult"]
        n = len(closes)
        if n < max(adx_p * 2, bb_p, rsi_p) + 20:
            return None
        adx_arr = _adx(highs, lows, closes, adx_p)
        i = n - 1
        if adx_arr[i] >= adx_max:
            return None  # not ranging
        rsi_arr = _rsi(closes, rsi_p)
        bb_mid = float(np.mean(closes[i - bb_p + 1: i + 1]))
        bb_std = float(np.std(closes[i - bb_p + 1: i + 1]))
        bb_upper = bb_mid + bb_m * bb_std
        bb_lower = bb_mid - bb_m * bb_std
        price = closes[i]
        tp_pct = cfg["tp_pct"]
        sl_pct = cfg["sl_pct"]
        # BUY: RSI oversold + at lower BB
        if rsi_arr[i] < 30 and price <= bb_lower * 1.005:
            conf = min((30 - rsi_arr[i]) / 30, 0.90)
            conf = max(conf, 0.3)
            tp = price * (1 + tp_pct / 100)
            sl = price * (1 - sl_pct / 100)
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"ADX range MR BUY (ADX={adx_arr[i]:.1f}, RSI={rsi_arr[i]:.1f})",
                tp=tp, sl=sl)
        # SELL: RSI overbought + at upper BB
        if rsi_arr[i] > 70 and price >= bb_upper * 0.995:
            conf = min((rsi_arr[i] - 70) / 30, 0.90)
            conf = max(conf, 0.3)
            tp = price * (1 - tp_pct / 100)
            sl = price * (1 + sl_pct / 100)
            return self._make_pick(
                symbol, "SHORT", conf, price,
                f"ADX range MR SELL (ADX={adx_arr[i]:.1f}, RSI={rsi_arr[i]:.1f})",
                tp=tp, sl=sl)
        return None

    def _scan_rsi_volume(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        rsi_p = cfg["rsi_period"]
        oversold = cfg["oversold"]
        overbought = cfg["overbought"]
        vol_p = cfg["volume_period"]
        vol_m = cfg["volume_mult"]
        if len(closes) < max(rsi_p, vol_p) + 10:
            return None
        rsi_arr = _rsi(closes, rsi_p)
        vol_ma = _sma(vols, vol_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if np.isnan(vol_ma[i]) or atr_arr[i] <= 0 or vol_ma[i] <= 0:
            return None
        price = closes[i]
        cur_vol = vols[i]
        # BUY: oversold + volume spike
        if rsi_arr[i] < oversold and cur_vol > vol_ma[i] * vol_m:
            conf = (oversold - rsi_arr[i]) / oversold
            conf = conf * (cur_vol / vol_ma[i])
            tp = price + atr_arr[i] * cfg["tp_atr_mult"]
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"RSI oversold ({rsi_arr[i]:.1f}) + volume spike ({cur_vol / vol_ma[i]:.1f}x)",
                tp=tp, sl=sl)
        # SELL: overbought + volume spike
        if rsi_arr[i] > overbought and cur_vol > vol_ma[i] * vol_m:
            conf = (rsi_arr[i] - overbought) / (100 - overbought)
            conf = conf * (cur_vol / vol_ma[i])
            tp = price - atr_arr[i] * cfg["tp_atr_mult"]
            sl = price + atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "SHORT", conf, price,
                f"RSI overbought ({rsi_arr[i]:.1f}) + volume spike ({cur_vol / vol_ma[i]:.1f}x)",
                tp=tp, sl=sl)
        return None

    def _scan_kalman(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        pv = cfg["process_variance"]
        mv = cfg["measurement_variance"]
        dev_thresh = cfg["deviation_threshold"]
        if len(closes) < 50:
            return None
        estimates, errors = _kalman_filter(closes, pv, mv)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if atr_arr[i] <= 0:
            return None
        price = closes[i]
        kalman_est = estimates[i]
        # Use rolling std of errors as deviation measure
        recent_errors = errors[max(0, i - 20):i + 1]
        err_std = float(np.std(recent_errors)) if len(recent_errors) > 2 else 1e-10
        deviation = (price - kalman_est) / (err_std + 1e-10)
        if deviation < -dev_thresh:
            strength = min(abs(deviation) / (dev_thresh * 1.5), 1.0)
            conf = 0.5 + strength * 0.35
            tp = kalman_est  # revert to Kalman estimate
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"Kalman deviation={deviation:.2f} (below estimate {kalman_est:.2f})",
                tp=tp, sl=sl)
        if deviation > dev_thresh:
            strength = min(abs(deviation) / (dev_thresh * 1.5), 1.0)
            conf = 0.5 + strength * 0.35
            tp = kalman_est
            sl = price + atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "SHORT", conf, price,
                f"Kalman deviation={deviation:.2f} (above estimate {kalman_est:.2f})",
                tp=tp, sl=sl)
        return None

    def _scan_kama(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        er_p = cfg["er_period"]
        fast_sc = cfg["fast_sc"]
        slow_sc = cfg["slow_sc"]
        z_thresh = cfg["z_threshold"]
        trend_p = cfg["trend_period"]
        if len(closes) < trend_p + 10:
            return None
        kama_arr = _kama(closes, er_p, fast_sc, slow_sc)
        sma_trend = _sma(closes, trend_p)
        atr_arr = _atr(highs, lows, closes)
        i = len(closes) - 1
        if np.isnan(sma_trend[i]) or atr_arr[i] <= 0:
            return None
        price = closes[i]
        # Z-score of price relative to KAMA
        diffs = closes[max(0, i - 20):i + 1] - kama_arr[max(0, i - 20):i + 1]
        std_diff = float(np.std(diffs)) if len(diffs) > 2 else 1e-10
        z = (price - kama_arr[i]) / (std_diff + 1e-10)
        if price > sma_trend[i] and z < -z_thresh:
            strength = min(abs(z) / (z_thresh * 2), 1.0)
            conf = 0.5 + strength * 0.35
            tp = kama_arr[i]  # revert to KAMA
            sl = price - atr_arr[i] * cfg["sl_atr_mult"]
            return self._make_pick(
                symbol, "LONG", conf, price,
                f"KAMA MR: z={z:.2f} below KAMA {kama_arr[i]:.2f} in uptrend",
                tp=tp, sl=sl)
        return None

    def _scan_red_candle(self, symbol, closes, highs, lows, opens, vols):
        cfg = self.config
        min_reds = cfg["min_red_candles"]
        rsi_p = cfg["rsi_period"]
        rsi_thresh = cfg["rsi_threshold"]
        ema_trend_p = cfg["ema_trend"]
        n = len(closes)
        if n < ema_trend_p + 10:
            return None
        # Count consecutive red candles
        red_count = 0
        for j in range(n - 1, max(n - 10, -1), -1):
            if closes[j] < opens[j]:
                red_count += 1
            else:
                break
        if red_count < min_reds:
            return None
        rsi_arr = _rsi(closes, rsi_p)
        if rsi_arr[n - 1] > rsi_thresh:
            return None
        ema_trend = _ema(closes, ema_trend_p)
        price = closes[n - 1]
        if price < ema_trend[n - 1]:
            return None
        atr_arr = _atr(highs, lows, closes)
        # BB upper for TP
        bb_p = 20
        bb_mid = float(np.mean(closes[-bb_p:]))
        bb_std = float(np.std(closes[-bb_p:]))
        bb_upper = bb_mid + 2.0 * bb_std
        # Confidence scales with oversold depth
        cur_rsi = rsi_arr[n - 1]
        if red_count >= 5 and cur_rsi < 5:
            conf = 0.85
        elif red_count >= 4 and cur_rsi < 5:
            conf = 0.75
        elif red_count >= 4:
            conf = 0.70
        else:
            conf = 0.65
        tp = min(bb_upper, price * 1.05)
        sl = price - 2 * atr_arr[n - 1]
        return self._make_pick(
            symbol, "LONG", conf, price,
            f"Red candle MR ({red_count} reds, RSI2={cur_rsi:.1f})",
            tp=tp, sl=sl)


# ---------------------------------------------------------------------------
# CLI entry point for quick testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"MeanReversionEngine — {len(VARIANTS)} variants loaded")
    print(f"Variants: {MeanReversionEngine.list_variants()}")
    print()

    # Fetch live data for a quick test
    print("Fetching BTCUSDT 1h candles from Binance...")
    data = fetch_binance_klines("BTCUSDT", "1h", 300)
    if data is None:
        print("ERROR: Could not fetch Binance data")
    else:
        print(f"Got {len(data['close'])} candles")
        print()

        # Scan all variants
        picks = MeanReversionEngine.scan_all_variants("BTCUSDT", data)
        print(f"Active picks from all variants: {len(picks)}")
        for p in picks:
            print(f"  [{p['direction']}] {p['strategy']} — conf={p['confidence']}, "
                  f"reason: {p['reason']}")

        # Backtest one variant as a demo
        print()
        engine = MeanReversionEngine("bollinger")
        bt = engine.backtest("BTCUSDT", data)
        print(f"Backtest (bollinger, 300 bars): {bt}")
