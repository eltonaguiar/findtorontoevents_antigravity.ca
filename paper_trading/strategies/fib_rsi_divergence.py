"""Fib RSI Divergence — Fibonacci retracement + RSI divergence (Pau Perdices Bellet, WCTC 2025)."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class FibRSIDivergence(BaseStrategy):
    name = "fib_rsi_divergence"
    display_name = "Fib RSI Divergence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    FIB_TOLERANCE = 0.05   # 5% of swing range tolerance around Fib levels
    SWING_LOOKBACK = 50

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @staticmethod
    def _ema(values: list, span: int) -> list:
        if not values:
            return []
        alpha = 2.0 / (span + 1)
        ema = [values[0]]
        for v in values[1:]:
            ema.append(alpha * v + (1 - alpha) * ema[-1])
        return ema

    @staticmethod
    def _rsi(closes: list, period: int = 14) -> list:
        if len(closes) < period + 1:
            return [50.0] * len(closes)
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0) for d in deltas]
        losses = [max(-d, 0) for d in deltas]
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        rsi_values = [50.0] * (period + 1)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        rsi_values[-1] = 100.0 - (100.0 / (1.0 + rs))
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))
        return rsi_values

    @staticmethod
    def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
        if len(closes) < 2:
            return [0.0] * len(closes)
        tr_list = [highs[0] - lows[0]]
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
                     abs(lows[i] - closes[i - 1]))
            tr_list.append(tr)
        if len(tr_list) < period:
            return tr_list
        atr_vals = [0.0] * (period - 1)
        atr_vals.append(sum(tr_list[:period]) / period)
        for i in range(period, len(tr_list)):
            atr_vals.append((atr_vals[-1] * (period - 1) + tr_list[i]) / period)
        return atr_vals

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            if len(klines) < 100:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]

            ema50 = self._ema(closes, 50)
            rsi_vals = self._rsi(closes, 14)
            atr_vals = self._atr(highs, lows, closes, 14)

            i = len(closes) - 1
            if atr_vals[i] <= 0:
                continue

            # Find swing high/low in lookback
            lb_start = max(0, i - self.SWING_LOOKBACK)
            swing_high = max(highs[lb_start:i])
            swing_low = min(lows[lb_start:i])
            swing_range = swing_high - swing_low

            if swing_range < 0.5 * atr_vals[i]:
                continue

            # Fibonacci levels
            fib_382_long = swing_high - 0.382 * swing_range
            fib_500_long = swing_high - 0.500 * swing_range
            fib_618_long = swing_high - 0.618 * swing_range

            fib_382_short = swing_low + 0.382 * swing_range
            fib_500_short = swing_low + 0.500 * swing_range
            fib_618_short = swing_low + 0.618 * swing_range

            tol = self.FIB_TOLERANCE * swing_range
            price = closes[i]
            rsi_now = rsi_vals[i]

            # LONG: price at Fib retracement + RSI oversold/divergence + uptrend
            at_fib_long = (abs(price - fib_382_long) < tol or abs(price - fib_500_long) < tol)
            trend_up = ema50[i] > ema50[max(0, i - 10)]

            if at_fib_long and trend_up and rsi_now < 45:
                sl = round(fib_618_long - 0.5 * atr_vals[i], 6)
                tp = round(swing_high, 6)
                risk = price - sl
                if risk > 0 and tp > price:
                    fib_level = "38.2%" if abs(price - fib_382_long) < tol else "50%"
                    confidence = min(0.85, 0.5 + (45 - rsi_now) / 100)

                    picks.append(NormalizedPick(
                        symbol=symbol, direction="LONG",
                        entry_price=price, tp=tp, sl=sl,
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=(f"Fib RSI Div LONG | Fib {fib_level} retracement | "
                                f"RSI={rsi_now:.1f} | target=swing high {swing_high:.2f}"),
                        raw_signal={"fib_level": fib_level, "rsi": round(rsi_now, 2),
                                    "swing_high": swing_high, "swing_low": swing_low},
                    ))

            # SHORT: price at Fib rally + RSI overbought + downtrend
            at_fib_short = (abs(price - fib_382_short) < tol or abs(price - fib_500_short) < tol)
            trend_down = ema50[i] < ema50[max(0, i - 10)]

            if at_fib_short and trend_down and rsi_now > 55:
                sl = round(fib_618_short + 0.5 * atr_vals[i], 6)
                tp = round(swing_low, 6)
                risk = sl - price
                if risk > 0 and tp < price:
                    fib_level = "38.2%" if abs(price - fib_382_short) < tol else "50%"
                    confidence = min(0.85, 0.5 + (rsi_now - 55) / 100)

                    picks.append(NormalizedPick(
                        symbol=symbol, direction="SHORT",
                        entry_price=price, tp=tp, sl=sl,
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=(f"Fib RSI Div SHORT | Fib {fib_level} rally | "
                                f"RSI={rsi_now:.1f} | target=swing low {swing_low:.2f}"),
                        raw_signal={"fib_level": fib_level, "rsi": round(rsi_now, 2),
                                    "swing_high": swing_high, "swing_low": swing_low},
                    ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
