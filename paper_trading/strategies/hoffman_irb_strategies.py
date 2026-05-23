"""Hoffman IRB + EMA Angle strategies — 3 hold-time variants.

Source: Rob Hoffman's Inventory Retracement Bar (IRB) system
  - EMA(20) on 15min close with 45° angle confirmation
  - Higher-TF EMA(20) (1H) for trend alignment
  - Bearish IRB in uptrend = BUY the dip
  - Bullish IRB in downtrend = SELL the rally

Symbols: BTCUSDT, DOGEUSDT, LTCUSDT, SOLUSDT, XRPUSDT
  (from Coinbase perps: BTCUSDC.P, DOGEUSDC.P, LTCUSDC.P, SOLUSDC.P, XRPUSDC.P)

Variants:
  - HoffmanIRB_1H_PT: max 1 hour hold (tighter TP/SL)
  - HoffmanIRB_2H_PT: max 2 hour hold (medium TP/SL)
  - HoffmanIRB_4H_PT: max 4 hour hold (wider TP/SL)
"""

import math
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

IRB_RETRACE_PCT = 45  # Hoffman default


# ── Indicators ─────────────────────────────────────────────────────

def _ema(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for i in range(period, len(values)):
        result.append(values[i] * k + result[-1] * (1 - k))
    return result


def _atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    result = [None] * (period - 1)
    result.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        result.append((result[-1] * (period - 1) + trs[i]) / period)
    return result


def _detect_irb_at(opens, highs, lows, closes, idx, retrace_pct=45):
    """Detect IRB at a specific bar index. Returns (bearish, bullish)."""
    c = retrace_pct / 100.0
    rng = abs(highs[idx] - lows[idx])
    body = abs(closes[idx] - opens[idx])

    if rng == 0:
        return False, False

    rv = body < c * rng
    if not rv:
        return False, False

    x = lows[idx] + c * rng   # lower retracement
    y = highs[idx] - c * rng  # upper retracement

    bearish = highs[idx] > y and closes[idx] < y and opens[idx] < y
    bullish = lows[idx] < x and closes[idx] > x and opens[idx] > x

    return bearish, bullish


def _ema_angle_degrees(ema_vals, idx, lookback=4):
    """Approximate EMA angle in degrees at bar idx."""
    if idx < lookback:
        return 0
    if ema_vals[idx] is None or ema_vals[idx - lookback] is None:
        return 0
    if ema_vals[idx - lookback] == 0:
        return 0
    pct_per_bar = (ema_vals[idx] - ema_vals[idx - lookback]) / ema_vals[idx - lookback] / lookback
    return math.degrees(math.atan(pct_per_bar * 1000))


def _htf_ema_trend(closes, idx, factor=4, ema_period=20):
    """Check higher-TF EMA trend by resampling. Returns 'rising', 'falling', or 'flat'."""
    # Build HTF closes by taking every `factor`-th bar's close
    htf_closes = []
    for i in range(0, idx + 1, factor):
        end = min(i + factor, idx + 1)
        htf_closes.append(closes[end - 1])

    if len(htf_closes) < ema_period + 4:
        return "flat"

    htf_ema = _ema(htf_closes, ema_period)
    if htf_ema[-1] is None or htf_ema[-5] is None:
        return "flat"

    if htf_ema[-1] > htf_ema[-5]:
        return "rising"
    elif htf_ema[-1] < htf_ema[-5]:
        return "falling"
    return "flat"


# ── Base Class ─────────────────────────────────────────────────────

class _HoffmanIRBBase(BaseStrategy):
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "verified"
    max_hold_hours: int = 4
    tp_mult: float = 1.5  # ATR multiplier for TP
    sl_mult: float = 1.0  # ATR multiplier for SL

    def fetch_data(self, symbol=None):
        if symbol:
            return self.fetch_klines(symbol, interval="15m", limit=200)
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _pick(self, symbol, direction, confidence, price,
              tp_price=None, sl_price=None, reason=""):
        return NormalizedPick(
            symbol=symbol, direction=direction, confidence=confidence,
            entry_price=price, tp=tp_price, sl=sl_price,
            strategy=self.name, strategy_name=self.display_name,
            category=self.category, reason=reason,
        )

    def generate_picks(self, data=None) -> List[NormalizedPick]:
        all_data = data if data else self.fetch_data()
        picks = []

        for symbol, data in all_data.items():
            if not data or len(data) < 100:
                continue

            opens = [float(k[1]) for k in data]
            highs = [float(k[2]) for k in data]
            lows = [float(k[3]) for k in data]
            closes = [float(k[4]) for k in data]
            volumes = [float(k[5]) for k in data]

            price = closes[-1]
            idx = len(closes) - 1

            # EMA(20) on 15min close
            ema20 = _ema(closes, 20)
            if ema20[-1] is None:
                continue

            # EMA angle
            angle = _ema_angle_degrees(ema20, idx, lookback=4)

            # ATR for TP/SL
            atr_vals = _atr(highs, lows, closes, 14)
            atr_now = atr_vals[-1]
            if atr_now is None or atr_now == 0:
                continue

            # IRB detection at last bar
            bearish_irb, bullish_irb = _detect_irb_at(
                opens, highs, lows, closes, idx, IRB_RETRACE_PCT)

            # Higher TF EMA trend
            htf_trend = _htf_ema_trend(closes, idx, factor=4, ema_period=20)

            # BUY: EMA rising ≥30° + bearish IRB (buy the dip) + HTF rising
            if bearish_irb and angle >= 30 and htf_trend == "rising":
                angle_conf = min(abs(angle) / 60, 1.0)
                conf = round(0.55 + 0.30 * angle_conf, 2)
                tp = price + self.tp_mult * atr_now
                sl = price - self.sl_mult * atr_now
                picks.append(self._pick(
                    symbol, "LONG", conf, price, tp_price=tp, sl_price=sl,
                    reason=(f"IRB dip-buy | EMA20∠{angle:.0f}° HTF=↑ "
                            f"ATR={atr_now:.2f} hold≤{self.max_hold_hours}h"),
                ))

            # SELL: EMA falling ≤-30° + bullish IRB (sell the rally) + HTF falling
            if bullish_irb and angle <= -30 and htf_trend == "falling":
                angle_conf = min(abs(angle) / 60, 1.0)
                conf = round(0.55 + 0.30 * angle_conf, 2)
                tp = price - self.tp_mult * atr_now
                sl = price + self.sl_mult * atr_now
                picks.append(self._pick(
                    symbol, "SHORT", conf, price, tp_price=tp, sl_price=sl,
                    reason=(f"IRB rally-sell | EMA20∠{angle:.0f}° HTF=↓ "
                            f"ATR={atr_now:.2f} hold≤{self.max_hold_hours}h"),
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── 3 Hold-Time Variants ──────────────────────────────────────────

class HoffmanIRB_1H_PT(_HoffmanIRBBase):
    """Hoffman IRB — 1 hour max hold. Tighter TP/SL for quick scalps."""
    name = "hoffman_irb_1h"
    display_name = "Hoffman IRB 1H Hold"
    source = "Rob Hoffman IRB + EMA angle (1h hold)"
    max_hold_hours = 1
    tp_mult = 1.0   # 1x ATR — tight target for 1h
    sl_mult = 0.75   # 0.75x ATR — tight stop


class HoffmanIRB_2H_PT(_HoffmanIRBBase):
    """Hoffman IRB — 2 hour max hold. Balanced TP/SL."""
    name = "hoffman_irb_2h"
    display_name = "Hoffman IRB 2H Hold"
    source = "Rob Hoffman IRB + EMA angle (2h hold)"
    max_hold_hours = 2
    tp_mult = 1.25   # 1.25x ATR
    sl_mult = 1.0    # 1x ATR


class HoffmanIRB_4H_PT(_HoffmanIRBBase):
    """Hoffman IRB — 4 hour max hold. Wider targets for larger moves."""
    name = "hoffman_irb_4h"
    display_name = "Hoffman IRB 4H Hold"
    source = "Rob Hoffman IRB + EMA angle (4h hold)"
    max_hold_hours = 4
    tp_mult = 1.5    # 1.5x ATR — wider for swing
    sl_mult = 1.0    # 1x ATR
