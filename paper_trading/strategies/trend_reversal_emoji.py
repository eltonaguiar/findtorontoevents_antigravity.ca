"""Advanced Trend Reversal Emoji — EMA(21/55/200) + RSI(14) + ATR volatility gate.

Four paper-trading classes, one per timeframe: 5m, 15m, 1h, 4h.
All go to the incubator portfolio for forward-testing.

Strategy Logic (matches Pine Script by FundedRelay):
  LONG  when: EMA(21) crosses up EMA(55) AND close > EMA(200)
              AND RSI(14) > 55 AND current TR > ATR(14)
  SHORT when: EMA(21) crosses down EMA(55) AND close < EMA(200)
              AND RSI(14) < 45 AND current TR > ATR(14)

TP/SL (ATR-based):
  LONG  TP = entry + 2.5×ATR   SL = entry - 1.5×ATR
  SHORT TP = entry - 2.5×ATR   SL = entry + 1.5×ATR   (R:R ≈ 1.67)

Literature:
  - Brock, Lakonishok & LeBaron (1992): MA crossover profitability
  - Hsu & Kuan (2005): intraday 10-30m optimal for MA rules
  - Elder Triple Screen (1985): multi-timeframe confirmation
"""
from __future__ import annotations

import logging
from typing import List

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

logger = logging.getLogger("paper_trading")

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
    "ETCUSDT", "HBARUSDT", "ALGOUSDT",
]


# ---------------------------------------------------------------------------
# Indicator helpers (pure-Python, no numpy dependency)
# ---------------------------------------------------------------------------

def _ema(values: list, span: int) -> list:
    """EMA matching Pine ta.ema (adjust=False recursive form)."""
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _rsi(closes: list, period: int = 14) -> list:
    """Wilder RSI, returns list aligned to closes."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    rsi = [50.0] * (period + 1)
    rs = avg_g / avg_l if avg_l > 0 else 100.0
    rsi[-1] = 100.0 - (100.0 / (1.0 + rs))
    for i in range(period, len(deltas)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100.0
        rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi


def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
    """ATR with Wilder smoothing."""
    if len(closes) < 2:
        return [0.0] * len(closes)
    tr_list = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    if len(tr_list) < period:
        return tr_list
    atr_vals = [0.0] * (period - 1)
    atr_vals.append(sum(tr_list[:period]) / period)
    for i in range(period, len(tr_list)):
        atr_vals.append((atr_vals[-1] * (period - 1) + tr_list[i]) / period)
    return atr_vals


# ---------------------------------------------------------------------------
# Shared signal logic as a mixin — subclasses only set class-level config
# ---------------------------------------------------------------------------

class _TrendReversalBase(BaseStrategy):
    """Mixin with all signal logic. Subclasses configure interval and name."""

    _INTERVAL: str = "1h"
    _KLINE_LIMIT: int = 250
    _MAX_PICKS: int = 5

    category = "crypto"
    portfolio_type = "incubator"
    source = "Multi-Source"

    # Indicator parameters (fixed to match Pine Script)
    _EMA_FAST = 21
    _EMA_SLOW = 55
    _EMA_TREND = 200
    _RSI_PERIOD = 14
    _ATR_PERIOD = 14
    _RSI_LONG_THRESH = 55
    _RSI_SHORT_THRESH = 45
    _ATR_VOL_MULT = 1.0
    _TP_ATR = 2.5
    _SL_ATR = 1.5

    def fetch_data(self) -> dict:
        all_data: dict = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval=self._INTERVAL,
                                           limit=self._KLINE_LIMIT)
                if klines and len(klines) >= self._EMA_TREND + 10:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            if len(klines) < self._EMA_TREND + 10:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]

            ema21 = _ema(closes, self._EMA_FAST)
            ema55 = _ema(closes, self._EMA_SLOW)
            ema200 = _ema(closes, self._EMA_TREND)
            rsi = _rsi(closes, self._RSI_PERIOD)
            atr = _atr(highs, lows, closes, self._ATR_PERIOD)

            if len(closes) < 2 or not atr or atr[-1] <= 0:
                continue

            # Current-bar true range
            tr_now = max(
                highs[-1] - lows[-1],
                abs(highs[-1] - closes[-2]),
                abs(lows[-1] - closes[-2]),
            )

            price = closes[-1]
            atr_now = atr[-1]
            rsi_now = rsi[-1] if len(rsi) >= len(closes) else 50.0

            cross_up = ema21[-1] > ema55[-1] and ema21[-2] <= ema55[-2]
            cross_down = ema21[-1] < ema55[-1] and ema21[-2] >= ema55[-2]
            vol_ok = tr_now > self._ATR_VOL_MULT * atr_now

            direction = None
            if cross_up and price > ema200[-1] and rsi_now > self._RSI_LONG_THRESH and vol_ok:
                direction = "LONG"
            elif cross_down and price < ema200[-1] and rsi_now < self._RSI_SHORT_THRESH and vol_ok:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price + self._TP_ATR * atr_now, 6)
                sl = round(price - self._SL_ATR * atr_now, 6)
            else:
                tp = round(price - self._TP_ATR * atr_now, 6)
                sl = round(price + self._SL_ATR * atr_now, 6)

            # Confidence: RSI distance from 50 + EMA crossover gap
            ema_gap = abs(ema21[-1] - ema55[-1]) / price if price > 0 else 0
            rsi_dist = abs(rsi_now - 50) / 50
            confidence = round(min(0.90, 0.50 + ema_gap * 10 + rsi_dist * 0.15), 3)

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
                    f"EMA(21)x EMA(55) {direction} [{self._INTERVAL}] | "
                    f"{'>' if direction == 'LONG' else '<'} EMA(200) | "
                    f"RSI={rsi_now:.1f} | TR/ATR={tr_now / atr_now:.2f}"
                ),
                raw_signal={
                    "interval": self._INTERVAL,
                    "ema21": round(ema21[-1], 4),
                    "ema55": round(ema55[-1], 4),
                    "ema200": round(ema200[-1], 4),
                    "rsi": round(rsi_now, 2),
                    "atr": round(atr_now, 4),
                    "tr": round(tr_now, 4),
                    "tr_atr_ratio": round(tr_now / atr_now, 3),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:self._MAX_PICKS]


# ===========================================================================
# Four timeframe variants
# ===========================================================================

class TrendReversalEmoji5m(_TrendReversalBase):
    """Advanced Trend Reversal Emoji — 5-minute timeframe."""
    name = "trend_reversal_emoji_5m"
    display_name = "Trend Reversal Emoji (5m)"
    _INTERVAL = "5m"
    _KLINE_LIMIT = 300
    _MAX_PICKS = 3


class TrendReversalEmoji15m(_TrendReversalBase):
    """Advanced Trend Reversal Emoji — 15-minute timeframe."""
    name = "trend_reversal_emoji_15m"
    display_name = "Trend Reversal Emoji (15m)"
    _INTERVAL = "15m"
    _KLINE_LIMIT = 260
    _MAX_PICKS = 4


class TrendReversalEmoji1h(_TrendReversalBase):
    """Advanced Trend Reversal Emoji — 1-hour timeframe."""
    name = "trend_reversal_emoji_1h"
    display_name = "Trend Reversal Emoji (1h)"
    _INTERVAL = "1h"
    _KLINE_LIMIT = 250
    _MAX_PICKS = 5


class TrendReversalEmoji4h(_TrendReversalBase):
    """Advanced Trend Reversal Emoji — 4-hour timeframe."""
    name = "trend_reversal_emoji_4h"
    display_name = "Trend Reversal Emoji (4h)"
    _INTERVAL = "4h"
    _KLINE_LIMIT = 250
    _MAX_PICKS = 5
