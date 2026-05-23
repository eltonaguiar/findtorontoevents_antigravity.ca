"""Incubator strategies — 5 experimental crypto strategies for paper trading validation.

Strategies:
  1. KeltnerSqueezeBreakout   — EMA(20) +/- 2*ATR(10), squeeze detection + breakout
  2. FundingRateContrarian     — Binance funding rate contrarian with RSI confirmation
  3. StochasticMomentumIndex   — SMI crossover with trend filter
  4. ADXBreakoutMomentum       — Fresh ADX trend breakout (+DI/-DI directional)
  5. MACDHistogramDivergence   — Price vs MACD-H divergence detection
"""
from typing import List
import logging
import numpy as np

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json

logger = logging.getLogger("paper_trading")

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
    "ETCUSDT", "HBARUSDT", "ALGOUSDT",
]


# ---------------------------------------------------------------------------
# Shared numpy helpers
# ---------------------------------------------------------------------------

def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average (full-length output, NaN-padded)."""
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = np.mean(arr[:period])
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1.0 - k)
    return out


def _sma(arr: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average (NaN-padded)."""
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return out
    cs = np.cumsum(arr)
    cs = np.insert(cs, 0, 0.0)
    out[period - 1:] = (cs[period:] - cs[:-period]) / period
    return out


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
         period: int) -> np.ndarray:
    """Average True Range (Wilder smoothing, NaN-padded)."""
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i - 1]),
                     abs(lows[i] - closes[i - 1]))
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period
    for i in range(period, n):
        out[i] = out[i - 1] * (1.0 - alpha) + tr[i] * alpha
    return out


def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder RSI (NaN-padded)."""
    n = len(closes)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g = np.mean(gain[:period])
    avg_l = np.mean(loss[:period])
    if avg_l == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    for i in range(period, len(delta)):
        avg_g = (avg_g * (period - 1) + gain[i]) / period
        avg_l = (avg_l * (period - 1) + loss[i]) / period
        if avg_l == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    return out


def _extract_ohlcv(klines: list):
    """Extract numpy O/H/L/C/V arrays from Binance-format klines."""
    o = np.array([float(k[1]) for k in klines])
    h = np.array([float(k[2]) for k in klines])
    l = np.array([float(k[3]) for k in klines])
    c = np.array([float(k[4]) for k in klines])
    v = np.array([float(k[5]) for k in klines])
    return o, h, l, c, v


# ===========================================================================
# 1. Keltner Squeeze Breakout
# ===========================================================================

class KeltnerSqueezeBreakout(BaseStrategy):
    """EMA(20) +/- 2*ATR(10) Keltner channel.

    Detects low-volatility squeezes (ATR < 20th percentile of last 100 bars)
    and triggers on breakout beyond bands with SMA-200 trend filter.
    """

    name = "incub_keltner_squeeze"
    display_name = "Keltner Squeeze Breakout"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"
    symbols = SYMBOLS

    _EMA_PERIOD = 20
    _ATR_PERIOD = 10
    _ATR_LOOKBACK = 100
    _ATR_SQUEEZE_PCT = 20
    _SMA_TREND = 200
    _TP_PCT = 0.05
    _SL_PCT = 0.025

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines and len(klines) >= self._SMA_TREND:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = _extract_ohlcv(klines)
            n = len(closes)
            if n < self._SMA_TREND:
                continue

            ema20 = _ema(closes, self._EMA_PERIOD)
            atr10 = _atr(highs, lows, closes, self._ATR_PERIOD)
            sma200 = _sma(closes, self._SMA_TREND)

            # Require valid indicator values at tip
            if np.isnan(ema20[-1]) or np.isnan(atr10[-1]) or np.isnan(sma200[-1]):
                continue

            # Squeeze detection: current ATR below 20th percentile of last 100 ATR
            lookback_start = max(0, n - self._ATR_LOOKBACK)
            atr_window = atr10[lookback_start:]
            valid_atr = atr_window[~np.isnan(atr_window)]
            if len(valid_atr) < 10:
                continue
            squeeze_threshold = np.percentile(valid_atr, self._ATR_SQUEEZE_PCT)
            in_squeeze = atr10[-1] < squeeze_threshold

            if not in_squeeze:
                continue

            price = closes[-1]
            upper = ema20[-1] + 2.0 * atr10[-1]
            lower = ema20[-1] - 2.0 * atr10[-1]
            prev_price = closes[-2]
            prev_upper = ema20[-2] + 2.0 * atr10[-2] if not np.isnan(atr10[-2]) else upper
            prev_lower = ema20[-2] - 2.0 * atr10[-2] if not np.isnan(atr10[-2]) else lower

            direction = None
            # Bullish breakout: cross above upper band, trend up
            if price > upper and prev_price <= prev_upper and price > sma200[-1]:
                direction = "LONG"
            # Bearish breakout: cross below lower band, trend down
            elif price < lower and prev_price >= prev_lower and price < sma200[-1]:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1.0 + self._TP_PCT), 6)
                sl = round(price * (1.0 - self._SL_PCT), 6)
            else:
                tp = round(price * (1.0 - self._TP_PCT), 6)
                sl = round(price * (1.0 + self._SL_PCT), 6)

            # Confidence: scales with how tight the squeeze is (tighter = higher)
            squeeze_ratio = float(atr10[-1] / squeeze_threshold) if squeeze_threshold > 0 else 1.0
            confidence = round(np.clip(0.88 - 0.33 * squeeze_ratio, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=confidence,
                reason=(
                    f"Keltner squeeze breakout {direction} | "
                    f"ATR={atr10[-1]:.4f} < threshold={squeeze_threshold:.4f} | "
                    f"EMA20={ema20[-1]:.2f} SMA200={sma200[-1]:.2f}"
                ),
                raw_signal={
                    "atr": float(atr10[-1]),
                    "squeeze_threshold": float(squeeze_threshold),
                    "ema20": float(ema20[-1]),
                    "sma200": float(sma200[-1]),
                    "upper": float(upper),
                    "lower": float(lower),
                    "price": float(price),
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 2. Funding Rate Contrarian
# ===========================================================================

_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"


class FundingRateContrarian(BaseStrategy):
    """Contrarian strategy based on Binance perpetual funding rates.

    Extreme positive funding (>+0.05%) signals overleveraged longs  -> SHORT.
    Extreme negative funding (<-0.03%) signals overleveraged shorts -> LONG.
    Requires RSI-14 confirmation before entry.
    """

    name = "incub_funding_contrarian"
    display_name = "Funding Rate Contrarian"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"
    symbols = SYMBOLS

    _FUND_HIGH = 0.0005   # +0.05%
    _FUND_LOW = -0.0003   # -0.03%
    _RSI_SHORT_THRESH = 60
    _RSI_LONG_THRESH = 40
    _TP_PCT = 0.04
    _SL_PCT = 0.02

    def fetch_data(self) -> dict:
        payload: dict = {"funding": {}, "klines": {}}
        for sym in self.symbols:
            try:
                fr = fetch_json(_FUNDING_URL, params={"symbol": sym, "limit": 1})
                if fr and isinstance(fr, list) and len(fr) > 0:
                    payload["funding"][sym] = float(fr[-1].get("fundingRate", 0))
            except Exception:
                continue
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=20)
                if klines:
                    payload["klines"][sym] = klines
            except Exception:
                continue
        return payload

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        funding_map = data.get("funding", {})
        klines_map = data.get("klines", {})

        for symbol in self.symbols:
            rate = funding_map.get(symbol)
            klines = klines_map.get(symbol)
            if rate is None or not klines or len(klines) < 16:
                continue

            _, _, _, closes, _ = _extract_ohlcv(klines)
            price = float(closes[-1])
            rsi_arr = _rsi(closes, 14)
            rsi_val = rsi_arr[-1]
            if np.isnan(rsi_val):
                continue

            direction = None
            if rate > self._FUND_HIGH and rsi_val > self._RSI_SHORT_THRESH:
                direction = "SHORT"
            elif rate < self._FUND_LOW and rsi_val < self._RSI_LONG_THRESH:
                direction = "LONG"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1.0 + self._TP_PCT), 6)
                sl = round(price * (1.0 - self._SL_PCT), 6)
            else:
                tp = round(price * (1.0 - self._TP_PCT), 6)
                sl = round(price * (1.0 + self._SL_PCT), 6)

            # Confidence scales with funding rate extremity
            if direction == "SHORT":
                extremity = min((rate - self._FUND_HIGH) / 0.001, 1.0)
            else:
                extremity = min((self._FUND_LOW - rate) / 0.001, 1.0)
            confidence = round(np.clip(0.55 + 0.33 * extremity, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=confidence,
                reason=(
                    f"Funding rate {rate*100:.4f}% contrarian {direction} | "
                    f"RSI(14)={rsi_val:.1f}"
                ),
                raw_signal={
                    "funding_rate": rate,
                    "funding_rate_pct": round(rate * 100, 4),
                    "rsi14": round(float(rsi_val), 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 3. Stochastic Momentum Index
# ===========================================================================

class StochasticMomentumIndex(BaseStrategy):
    """SMI oscillator with EMA smoothing.

    SMI = 100 * EMA(EMA(close - midpoint, smooth), smooth)
          / (0.5 * EMA(EMA(highest - lowest, smooth), smooth))

    Buy when SMI crosses above -40; sell when SMI crosses below +40.
    SMA-200 trend filter.
    """

    name = "incub_smi"
    display_name = "Stochastic Momentum Index"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"
    symbols = SYMBOLS

    _PERIOD = 14
    _SMOOTH = 3
    _BUY_LEVEL = -40
    _SELL_LEVEL = 40
    _SMA_TREND = 200
    _TP_PCT = 0.06
    _SL_PCT = 0.03

    @staticmethod
    def _rolling_max(arr: np.ndarray, period: int) -> np.ndarray:
        out = np.full_like(arr, np.nan)
        for i in range(period - 1, len(arr)):
            out[i] = np.max(arr[i - period + 1: i + 1])
        return out

    @staticmethod
    def _rolling_min(arr: np.ndarray, period: int) -> np.ndarray:
        out = np.full_like(arr, np.nan)
        for i in range(period - 1, len(arr)):
            out[i] = np.min(arr[i - period + 1: i + 1])
        return out

    def _compute_smi(self, highs: np.ndarray, lows: np.ndarray,
                     closes: np.ndarray) -> np.ndarray:
        hh = self._rolling_max(highs, self._PERIOD)
        ll = self._rolling_min(lows, self._PERIOD)
        midpoint = (hh + ll) / 2.0
        diff = closes - midpoint
        hl_range = hh - ll

        # Double EMA smoothing
        diff_s1 = _ema(diff, self._SMOOTH)
        diff_s2 = _ema(diff_s1, self._SMOOTH)
        range_s1 = _ema(hl_range, self._SMOOTH)
        range_s2 = _ema(range_s1, self._SMOOTH)

        smi = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            denom = 0.5 * range_s2[i]
            if not np.isnan(diff_s2[i]) and not np.isnan(denom) and denom > 0:
                smi[i] = 100.0 * diff_s2[i] / denom
        return np.clip(smi, -100, 100)

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines and len(klines) >= self._SMA_TREND:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = _extract_ohlcv(klines)
            if len(closes) < self._SMA_TREND:
                continue

            smi = self._compute_smi(highs, lows, closes)
            sma200 = _sma(closes, self._SMA_TREND)

            if np.isnan(smi[-1]) or np.isnan(smi[-2]) or np.isnan(sma200[-1]):
                continue

            price = float(closes[-1])
            direction = None

            # Bullish: SMI crosses above -40 in uptrend
            if smi[-2] < self._BUY_LEVEL and smi[-1] >= self._BUY_LEVEL and price > sma200[-1]:
                direction = "LONG"
            # Bearish: SMI crosses below +40 in downtrend
            elif smi[-2] > self._SELL_LEVEL and smi[-1] <= self._SELL_LEVEL and price < sma200[-1]:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1.0 + self._TP_PCT), 6)
                sl = round(price * (1.0 - self._SL_PCT), 6)
            else:
                tp = round(price * (1.0 - self._TP_PCT), 6)
                sl = round(price * (1.0 + self._SL_PCT), 6)

            # Confidence: larger cross magnitude = higher
            cross_magnitude = abs(float(smi[-1]) - float(smi[-2]))
            confidence = round(np.clip(0.55 + cross_magnitude / 80.0, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=confidence,
                reason=(
                    f"SMI crossover {direction} | "
                    f"SMI={smi[-1]:.1f} (prev={smi[-2]:.1f}) | "
                    f"SMA200={sma200[-1]:.2f}"
                ),
                raw_signal={
                    "smi": round(float(smi[-1]), 2),
                    "smi_prev": round(float(smi[-2]), 2),
                    "sma200": round(float(sma200[-1]), 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 4. ADX Breakout Momentum
# ===========================================================================

class ADXBreakoutMomentum(BaseStrategy):
    """ADX(14) crossing above 25 from a recent low (<20 within 5 bars).

    +DI > -DI -> LONG, -DI > +DI -> SHORT.
    Confidence scales with ADX strength.
    """

    name = "incub_adx_breakout"
    display_name = "ADX Breakout Momentum"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"
    symbols = SYMBOLS

    _ADX_PERIOD = 14
    _ADX_ENTRY = 25
    _ADX_RECENT_LOW = 20
    _LOOKBACK_BARS = 5
    _TP_PCT = 0.08
    _SL_PCT = 0.03

    @staticmethod
    def _compute_dx(highs: np.ndarray, lows: np.ndarray,
                    closes: np.ndarray, period: int = 14):
        """Compute +DI, -DI, and ADX arrays."""
        n = len(closes)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        tr = np.zeros(n)

        for i in range(1, n):
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm[i] = up if (up > down and up > 0) else 0.0
            minus_dm[i] = down if (down > up and down > 0) else 0.0
            tr[i] = max(highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]))

        # Wilder smoothing
        atr_s = np.full(n, np.nan)
        plus_dm_s = np.full(n, np.nan)
        minus_dm_s = np.full(n, np.nan)

        if n < period + 1:
            return (np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan))

        atr_s[period] = np.sum(tr[1:period + 1])
        plus_dm_s[period] = np.sum(plus_dm[1:period + 1])
        minus_dm_s[period] = np.sum(minus_dm[1:period + 1])

        for i in range(period + 1, n):
            atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / period + tr[i]
            plus_dm_s[i] = plus_dm_s[i - 1] - plus_dm_s[i - 1] / period + plus_dm[i]
            minus_dm_s[i] = minus_dm_s[i - 1] - minus_dm_s[i - 1] / period + minus_dm[i]

        plus_di = np.full(n, np.nan)
        minus_di = np.full(n, np.nan)
        dx = np.full(n, np.nan)

        for i in range(period, n):
            if atr_s[i] and atr_s[i] > 0:
                plus_di[i] = 100.0 * plus_dm_s[i] / atr_s[i]
                minus_di[i] = 100.0 * minus_dm_s[i] / atr_s[i]
                di_sum = plus_di[i] + minus_di[i]
                dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / di_sum if di_sum > 0 else 0.0

        # ADX = Wilder-smoothed DX
        adx = np.full(n, np.nan)
        start = period + period  # need 2*period bars
        if n <= start:
            return plus_di, minus_di, adx
        valid_dx = dx[period: start]
        valid_dx = valid_dx[~np.isnan(valid_dx)]
        if len(valid_dx) == 0:
            return plus_di, minus_di, adx
        adx[start - 1] = np.mean(valid_dx)
        for i in range(start, n):
            if not np.isnan(dx[i]) and not np.isnan(adx[i - 1]):
                adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

        return plus_di, minus_di, adx

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines and len(klines) >= 50:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = _extract_ohlcv(klines)
            if len(closes) < 50:
                continue

            plus_di, minus_di, adx = self._compute_dx(
                highs, lows, closes, self._ADX_PERIOD
            )

            if np.isnan(adx[-1]) or np.isnan(plus_di[-1]) or np.isnan(minus_di[-1]):
                continue

            # ADX must be crossing above 25 now
            if adx[-1] < self._ADX_ENTRY:
                continue

            # Must have been below 20 within last 5 bars (fresh trend)
            recent_adx = adx[-self._LOOKBACK_BARS - 1: -1]
            valid_recent = recent_adx[~np.isnan(recent_adx)]
            if len(valid_recent) == 0 or np.min(valid_recent) >= self._ADX_RECENT_LOW:
                continue

            price = float(closes[-1])
            if plus_di[-1] > minus_di[-1]:
                direction = "LONG"
                tp = round(price * (1.0 + self._TP_PCT), 6)
                sl = round(price * (1.0 - self._SL_PCT), 6)
            else:
                direction = "SHORT"
                tp = round(price * (1.0 - self._TP_PCT), 6)
                sl = round(price * (1.0 + self._SL_PCT), 6)

            # Confidence scales linearly with ADX: 25->0.55, 50->0.88
            confidence = round(np.clip(
                0.55 + (float(adx[-1]) - 25.0) / 25.0 * 0.33, 0.55, 0.88
            ), 3)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=confidence,
                reason=(
                    f"ADX breakout {direction} | "
                    f"ADX={adx[-1]:.1f} +DI={plus_di[-1]:.1f} -DI={minus_di[-1]:.1f}"
                ),
                raw_signal={
                    "adx": round(float(adx[-1]), 2),
                    "plus_di": round(float(plus_di[-1]), 2),
                    "minus_di": round(float(minus_di[-1]), 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 5. MACD Histogram Divergence
# ===========================================================================

class MACDHistogramDivergence(BaseStrategy):
    """Detects price vs MACD-histogram divergence within a 20-bar window.

    Bullish divergence: price lower-low but MACD-H higher-low.
    Bearish divergence: price higher-high but MACD-H lower-high.
    SMA-50 trend confirmation.
    """

    name = "incub_macd_divergence"
    display_name = "MACD Histogram Divergence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"
    symbols = SYMBOLS

    _FAST = 12
    _SLOW = 26
    _SIGNAL = 9
    _SWING_WINDOW = 20
    _SMA_TREND = 50
    _TP_PCT = 0.07
    _SL_PCT = 0.03

    @staticmethod
    def _macd_histogram(closes: np.ndarray, fast: int, slow: int,
                        signal: int) -> np.ndarray:
        ema_fast = _ema(closes, fast)
        ema_slow = _ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, signal)
        return macd_line - signal_line

    @staticmethod
    def _find_swing_lows(arr: np.ndarray, window: int, count: int = 2):
        """Find indices of the last *count* local minima within the window."""
        n = len(arr)
        start = max(0, n - window)
        lows = []
        for i in range(start + 1, n - 1):
            if np.isnan(arr[i]):
                continue
            left = arr[i - 1] if not np.isnan(arr[i - 1]) else arr[i]
            right = arr[i + 1] if not np.isnan(arr[i + 1]) else arr[i]
            if arr[i] <= left and arr[i] <= right:
                lows.append(i)
        return lows[-count:] if len(lows) >= count else []

    @staticmethod
    def _find_swing_highs(arr: np.ndarray, window: int, count: int = 2):
        """Find indices of the last *count* local maxima within the window."""
        n = len(arr)
        start = max(0, n - window)
        highs = []
        for i in range(start + 1, n - 1):
            if np.isnan(arr[i]):
                continue
            left = arr[i - 1] if not np.isnan(arr[i - 1]) else arr[i]
            right = arr[i + 1] if not np.isnan(arr[i + 1]) else arr[i]
            if arr[i] >= left and arr[i] >= right:
                highs.append(i)
        return highs[-count:] if len(highs) >= count else []

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines and len(klines) >= 60:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = _extract_ohlcv(klines)
            if len(closes) < 60:
                continue

            hist = self._macd_histogram(closes, self._FAST, self._SLOW, self._SIGNAL)
            sma50 = _sma(closes, self._SMA_TREND)

            if np.isnan(hist[-1]) or np.isnan(sma50[-1]):
                continue

            price = float(closes[-1])
            direction = None
            reason_detail = ""

            # Bullish divergence: price lower-low, histogram higher-low
            price_lows = self._find_swing_lows(closes, self._SWING_WINDOW)
            hist_lows = self._find_swing_lows(hist, self._SWING_WINDOW)
            if len(price_lows) >= 2 and len(hist_lows) >= 2:
                p1, p2 = price_lows[-2], price_lows[-1]
                h1, h2 = hist_lows[-2], hist_lows[-1]
                if (closes[p2] < closes[p1] and hist[h2] > hist[h1]
                        and price > sma50[-1]):
                    direction = "LONG"
                    reason_detail = (
                        f"price LL ({closes[p1]:.2f}->{closes[p2]:.2f}) "
                        f"hist HL ({hist[h1]:.4f}->{hist[h2]:.4f})"
                    )

            # Bearish divergence: price higher-high, histogram lower-high
            if direction is None:
                price_highs = self._find_swing_highs(closes, self._SWING_WINDOW)
                hist_highs = self._find_swing_highs(hist, self._SWING_WINDOW)
                if len(price_highs) >= 2 and len(hist_highs) >= 2:
                    p1, p2 = price_highs[-2], price_highs[-1]
                    h1, h2 = hist_highs[-2], hist_highs[-1]
                    if (closes[p2] > closes[p1] and hist[h2] < hist[h1]
                            and price < sma50[-1]):
                        direction = "SHORT"
                        reason_detail = (
                            f"price HH ({closes[p1]:.2f}->{closes[p2]:.2f}) "
                            f"hist LH ({hist[h1]:.4f}->{hist[h2]:.4f})"
                        )

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1.0 + self._TP_PCT), 6)
                sl = round(price * (1.0 - self._SL_PCT), 6)
            else:
                tp = round(price * (1.0 - self._TP_PCT), 6)
                sl = round(price * (1.0 + self._SL_PCT), 6)

            # Confidence based on divergence magnitude
            confidence = round(np.clip(0.55 + abs(float(hist[-1])) * 50, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=confidence,
                reason=(
                    f"MACD-H divergence {direction} | {reason_detail} | "
                    f"SMA50={sma50[-1]:.2f}"
                ),
                raw_signal={
                    "macd_hist": round(float(hist[-1]), 6),
                    "sma50": round(float(sma50[-1]), 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ---------------------------------------------------------------------------
# Registry — importable list of all incubator strategy classes
# ---------------------------------------------------------------------------

INCUBATOR_STRATEGIES = [
    KeltnerSqueezeBreakout,
    FundingRateContrarian,
    StochasticMomentumIndex,
    ADXBreakoutMomentum,
    MACDHistogramDivergence,
]
