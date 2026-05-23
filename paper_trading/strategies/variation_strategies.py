"""Variation strategies — parameter variations of existing strategies backed by literature.

Created from audit of scrapped/disabled strategies + parameter optimization research.

Strategies (6):
  1. WilliamsR5Reversion       — Williams %R(5) per QuantifiedStrategies crypto research
  2. KeltnerTightSqueeze       — Keltner 1.5x ATR per Raschke & Connors (1996)
  3. FastMACDDivergence        — MACD(8/17/9) per Bernstein fast variant
  4. BB25VolBreakout           — BB 2.5 std dev per Bollinger (2001) for volatile instruments
  5. FundingContrarian30_70    — Funding rate contrarian with strict RSI 30/70 per Wilder (1978)
  6. EMA9_21CrossTrend         — 9/21 EMA cross per Brock et al. (1992) scalping cross

All go to incubator portfolio to prove themselves before promotion.
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
# Shared numpy helpers (same as incubator_strategies.py)
# ---------------------------------------------------------------------------

def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = np.mean(arr[:period])
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1.0 - k)
    return out


def _sma(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return out
    cs = np.cumsum(arr)
    cs = np.insert(cs, 0, 0.0)
    out[period - 1:] = (cs[period:] - cs[:-period]) / period
    return out


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
         period: int) -> np.ndarray:
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
    o = np.array([float(k[1]) for k in klines])
    h = np.array([float(k[2]) for k in klines])
    l = np.array([float(k[3]) for k in klines])
    c = np.array([float(k[4]) for k in klines])
    v = np.array([float(k[5]) for k in klines])
    return o, h, l, c, v


# ===========================================================================
# 1. Williams %R(5) Mean Reversion
#    Variation of: WilliamsRReversion (period=14)
#    Literature: QuantifiedStrategies — %R(5) dominates period=14 for crypto
# ===========================================================================

class WilliamsR5Reversion(BaseStrategy):
    """Williams %R(5) mean reversion — faster period for crypto.

    QuantifiedStrategies research shows period=5 with -90/-10 thresholds
    produces better risk-adjusted returns on hourly crypto data than period=14.
    Fires ~2x more often with ~2-4% lower WR but higher Sharpe.
    """
    name = "var_williams_r5"
    display_name = "Williams %R(5) Fast Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _WR_PERIOD = 5
    _WR_OVERSOLD = -90
    _WR_OVERBOUGHT = -10
    _SMA_TREND = 200
    _TP_PCT = 0.04    # Tighter TP for faster reversion
    _SL_PCT = 0.02

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
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
            if len(klines) < self._SMA_TREND:
                continue

            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])
            price = float(closes[-1])

            # Williams %R(5)
            if len(closes) < self._WR_PERIOD:
                continue
            w_highs = highs[-self._WR_PERIOD:]
            w_lows = lows[-self._WR_PERIOD:]
            hh = float(np.max(w_highs))
            ll = float(np.min(w_lows))
            hl_range = hh - ll
            if hl_range == 0:
                continue
            wr = ((hh - price) / hl_range) * -100

            sma200 = float(np.mean(closes[-self._SMA_TREND:]))

            direction = None
            if wr < self._WR_OVERSOLD and price > sma200:
                direction = "LONG"
            elif wr > self._WR_OVERBOUGHT and price < sma200:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            distance = abs(wr - (self._WR_OVERSOLD if direction == "LONG" else self._WR_OVERBOUGHT))
            confidence = round(min(0.90, 0.55 + distance * 0.03), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"Williams %R(5)={wr:.1f} {'<' + str(self._WR_OVERSOLD) if direction == 'LONG' else '>' + str(self._WR_OVERBOUGHT)} | price {'>' if direction == 'LONG' else '<'} SMA200={sma200:.2f}",
                raw_signal={"williams_r": round(wr, 2), "period": self._WR_PERIOD, "sma200": round(sma200, 2), "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 2. Keltner Tight Squeeze (1.5x ATR)
#    Variation of: KeltnerSqueezeBreakout (2.0x ATR)
#    Literature: Raschke & Connors (1996) "Street Smarts" — original 1.5x spec
# ===========================================================================

class KeltnerTightSqueeze(BaseStrategy):
    """Keltner channel with 1.5x ATR — original Raschke & Connors specification.

    Tighter bands generate more signals in crypto's higher-volatility environment.
    Uses 10th percentile squeeze detection (vs 20th in the standard variant).
    """
    name = "var_keltner_tight"
    display_name = "Keltner 1.5x Tight Squeeze"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _EMA_PERIOD = 20
    _ATR_PERIOD = 10
    _ATR_MULT = 1.5     # Tighter than standard 2.0x
    _SQUEEZE_PCT = 10    # Stricter squeeze percentile
    _SMA_TREND = 200
    _TP_PCT = 0.04
    _SL_PCT = 0.02

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
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

            if np.isnan(ema20[-1]) or np.isnan(atr10[-1]) or np.isnan(sma200[-1]):
                continue

            lookback_start = max(0, n - 100)
            atr_window = atr10[lookback_start:]
            valid_atr = atr_window[~np.isnan(atr_window)]
            if len(valid_atr) < 10:
                continue
            squeeze_threshold = np.percentile(valid_atr, self._SQUEEZE_PCT)
            in_squeeze = atr10[-1] < squeeze_threshold

            if not in_squeeze:
                continue

            price = closes[-1]
            upper = ema20[-1] + self._ATR_MULT * atr10[-1]
            lower = ema20[-1] - self._ATR_MULT * atr10[-1]
            prev_price = closes[-2]
            prev_upper = ema20[-2] + self._ATR_MULT * atr10[-2] if not np.isnan(atr10[-2]) else upper
            prev_lower = ema20[-2] - self._ATR_MULT * atr10[-2] if not np.isnan(atr10[-2]) else lower

            direction = None
            if price > upper and prev_price <= prev_upper and price > sma200[-1]:
                direction = "LONG"
            elif price < lower and prev_price >= prev_lower and price < sma200[-1]:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            squeeze_ratio = float(atr10[-1] / squeeze_threshold) if squeeze_threshold > 0 else 1.0
            confidence = round(np.clip(0.88 - 0.33 * squeeze_ratio, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=float(price),
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"Keltner 1.5x squeeze breakout {direction} | ATR={atr10[-1]:.4f} < {squeeze_threshold:.4f} | EMA20={ema20[-1]:.2f}",
                raw_signal={"atr": float(atr10[-1]), "squeeze_threshold": float(squeeze_threshold), "atr_mult": self._ATR_MULT, "price": float(price)},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 3. Fast MACD Divergence (8/17/9)
#    Variation of: MACDHistogramDivergence (12/26/9)
#    Literature: Bernstein — fast MACD produces signals ~40% faster
# ===========================================================================

class FastMACDDivergence(BaseStrategy):
    """MACD(8/17/9) histogram divergence — Bernstein fast variant.

    Standard 12/26/9 is ~40% too slow for 1h crypto. The 8/17/9 variant
    captures divergences in time for entry. Uses 15-bar swing window
    (vs 20 in standard) for faster divergence detection.
    """
    name = "var_fast_macd_div"
    display_name = "Fast MACD(8/17/9) Divergence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _FAST = 8
    _SLOW = 17
    _SIGNAL = 9
    _SWING_WINDOW = 15
    _SMA_TREND = 50
    _TP_PCT = 0.05
    _SL_PCT = 0.025

    @staticmethod
    def _macd_histogram(closes, fast, slow, signal):
        ema_fast = _ema(closes, fast)
        ema_slow = _ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, signal)
        return macd_line - signal_line

    @staticmethod
    def _find_swing_lows(arr, window, count=2):
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
    def _find_swing_highs(arr, window, count=2):
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
        for sym in SYMBOLS:
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

            # Bullish divergence
            price_lows = self._find_swing_lows(closes, self._SWING_WINDOW)
            hist_lows = self._find_swing_lows(hist, self._SWING_WINDOW)
            if len(price_lows) >= 2 and len(hist_lows) >= 2:
                p1, p2 = price_lows[-2], price_lows[-1]
                h1, h2 = hist_lows[-2], hist_lows[-1]
                if closes[p2] < closes[p1] and hist[h2] > hist[h1] and price > sma50[-1]:
                    direction = "LONG"
                    reason_detail = f"price LL, fast MACD-H HL"

            # Bearish divergence
            if direction is None:
                price_highs = self._find_swing_highs(closes, self._SWING_WINDOW)
                hist_highs = self._find_swing_highs(hist, self._SWING_WINDOW)
                if len(price_highs) >= 2 and len(hist_highs) >= 2:
                    p1, p2 = price_highs[-2], price_highs[-1]
                    h1, h2 = hist_highs[-2], hist_highs[-1]
                    if closes[p2] > closes[p1] and hist[h2] < hist[h1] and price < sma50[-1]:
                        direction = "SHORT"
                        reason_detail = f"price HH, fast MACD-H LH"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            confidence = round(np.clip(0.55 + abs(float(hist[-1])) * 50, 0.55, 0.88), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"Fast MACD(8/17/9) divergence {direction} | {reason_detail} | SMA50={sma50[-1]:.2f}",
                raw_signal={"macd_hist": round(float(hist[-1]), 6), "fast": self._FAST, "slow": self._SLOW, "signal": self._SIGNAL, "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 4. BB 2.5 Std Dev Volatility Breakout
#    Variation of: GenericVolatilityBreakout (BB 2.0 std dev)
#    Literature: Bollinger (2001) — 2.5 std dev for volatile instruments
# ===========================================================================

class BB25VolBreakout(BaseStrategy):
    """Bollinger Band 2.5 std dev breakout — for volatile crypto.

    Bollinger (2001) recommended 2.5 std dev for volatile instruments.
    Fewer false breakouts than 2.0 std dev. Uses same squeeze + volume filters.
    """
    name = "var_bb25_breakout"
    display_name = "BB 2.5 StdDev Breakout"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _BB_PERIOD = 20
    _BB_STD = 2.5        # Wider than standard 2.0
    _SMA_TREND = 200
    _SQUEEZE_PCT = 10
    _VOL_MULT = 2.0
    _TP_PCT = 0.05       # Wider TP for bigger breakouts
    _SL_PCT = 0.025

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=500)
                if klines and len(klines) >= self._SMA_TREND + 20:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = _extract_ohlcv(klines)
            vols = np.array([float(k[5]) for k in klines])
            if len(closes) < self._SMA_TREND + 20:
                continue

            price = float(closes[-1])
            sma200 = float(np.mean(closes[-self._SMA_TREND:]))

            bb_closes = closes[-self._BB_PERIOD:]
            ma = float(np.mean(bb_closes))
            std = float(np.std(bb_closes))
            if std == 0:
                continue
            upper = ma + self._BB_STD * std
            lower = ma - self._BB_STD * std

            # Squeeze detection
            min_hist = self._BB_PERIOD + 100
            if len(closes) < min_hist:
                continue
            widths = []
            for i in range(len(closes) - 100, len(closes)):
                w_slice = closes[i - self._BB_PERIOD + 1:i + 1]
                w_std = float(np.std(w_slice))
                widths.append(2 * self._BB_STD * w_std)
            widths_arr = np.array(widths)
            current_width = widths_arr[-1]
            width_thresh = float(np.percentile(widths_arr, self._SQUEEZE_PCT))
            squeeze = current_width <= width_thresh

            # Volume filter
            avg_vol = float(np.mean(vols[-20:]))
            vol_ok = float(vols[-1]) >= self._VOL_MULT * avg_vol

            direction = None
            if price > upper and price > sma200 and squeeze and vol_ok:
                direction = "LONG"
            elif price < lower and price < sma200 and squeeze and vol_ok:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            squeeze_factor = min((width_thresh - current_width) / width_thresh, 1.0) if width_thresh > 0 else 0.5
            confidence = round(0.6 + 0.3 * squeeze_factor, 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"BB(2.5) breakout {direction} | squeeze width={current_width:.4f} <= {width_thresh:.4f} | vol {vols[-1]:.0f} >= {self._VOL_MULT}x avg {avg_vol:.0f}",
                raw_signal={"bb_std": self._BB_STD, "bb_upper": round(upper, 2), "bb_lower": round(lower, 2), "price": round(price, 2)},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 5. Funding Rate Contrarian (Strict RSI 30/70)
#    Variation of: FundingRateContrarian (RSI 40/60)
#    Literature: Wilder (1978) — 30/70 are the standard oversold/overbought levels
# ===========================================================================

_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"


class FundingContrarian30_70(BaseStrategy):
    """Funding rate contrarian with strict RSI(14) 30/70 thresholds.

    The standard variant uses RSI 40/60 which is too permissive — Wilder (1978)
    defined 30/70 as the oversold/overbought levels. Stricter thresholds
    produce fewer signals but higher WR.
    """
    name = "var_funding_strict"
    display_name = "Funding Contrarian (RSI 30/70)"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _FUND_HIGH = 0.0005
    _FUND_LOW = -0.0003
    _RSI_SHORT_THRESH = 70   # Stricter: 70 instead of 60
    _RSI_LONG_THRESH = 30    # Stricter: 30 instead of 40
    _TP_PCT = 0.05
    _SL_PCT = 0.025

    def fetch_data(self) -> dict:
        payload: dict = {"funding": {}, "klines": {}}
        for sym in SYMBOLS:
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

        for symbol in SYMBOLS:
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
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            if direction == "SHORT":
                extremity = min((rate - self._FUND_HIGH) / 0.001, 1.0)
            else:
                extremity = min((self._FUND_LOW - rate) / 0.001, 1.0)
            confidence = round(np.clip(0.58 + 0.30 * extremity, 0.58, 0.90), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"Funding {rate*100:.4f}% contrarian {direction} | RSI(14)={rsi_val:.1f} ({'>' + str(self._RSI_SHORT_THRESH) if direction == 'SHORT' else '<' + str(self._RSI_LONG_THRESH)})",
                raw_signal={"funding_rate": rate, "rsi14": round(float(rsi_val), 2), "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 6. EMA 9/21 Cross Trend
#    New variant — the most common scalping cross, entirely absent from system
#    Literature: Brock et al. (1992) — short MA crosses consistently profitable
# ===========================================================================

class EMA9_21CrossTrend(BaseStrategy):
    """EMA(9/21) fast cross with EMA(200) trend filter.

    The 9/21 EMA cross is the standard scalping/day-trading signal.
    Brock et al. (1992) showed shorter EMA crosses consistently outperform
    longer crosses on trending markets. Generates 3-5x more signals than 21/55.
    Uses RSI(14) > 50 for momentum confirmation.
    """
    name = "var_ema_9_21_cross"
    display_name = "EMA(9/21) Fast Cross"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _EMA_FAST = 9
    _EMA_SLOW = 21
    _EMA_TREND = 200
    _RSI_PERIOD = 14
    _RSI_LONG = 50
    _RSI_SHORT = 50
    _TP_PCT = 0.03     # Tighter for faster entries
    _SL_PCT = 0.015

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines and len(klines) >= self._EMA_TREND + 5:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = _extract_ohlcv(klines)
            if len(closes) < self._EMA_TREND + 5:
                continue

            ema9 = _ema(closes, self._EMA_FAST)
            ema21 = _ema(closes, self._EMA_SLOW)
            ema200 = _ema(closes, self._EMA_TREND)
            rsi_arr = _rsi(closes, self._RSI_PERIOD)

            if any(np.isnan(x[-1]) for x in [ema9, ema21, ema200]) or np.isnan(rsi_arr[-1]):
                continue
            if np.isnan(ema9[-2]) or np.isnan(ema21[-2]):
                continue

            price = float(closes[-1])
            rsi_now = float(rsi_arr[-1])

            cross_up = ema9[-1] > ema21[-1] and ema9[-2] <= ema21[-2]
            cross_down = ema9[-1] < ema21[-1] and ema9[-2] >= ema21[-2]

            direction = None
            if cross_up and price > ema200[-1] and rsi_now > self._RSI_LONG:
                direction = "LONG"
            elif cross_down and price < ema200[-1] and rsi_now < self._RSI_SHORT:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            ema_gap = abs(float(ema9[-1]) - float(ema21[-1])) / price if price > 0 else 0
            rsi_dist = abs(rsi_now - 50) / 50
            confidence = round(min(0.88, 0.52 + ema_gap * 15 + rsi_dist * 0.15), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"EMA(9)x EMA(21) {direction} | {'>' if direction == 'LONG' else '<'} EMA(200) | RSI={rsi_now:.1f}",
                raw_signal={"ema9": round(float(ema9[-1]), 4), "ema21": round(float(ema21[-1]), 4), "ema200": round(float(ema200[-1]), 4), "rsi": round(rsi_now, 2), "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
