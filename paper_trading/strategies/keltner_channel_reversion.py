"""Keltner Channel Mean Reversion — price at outer band + RSI confirmation.

Academic source: Keltner (1960), modernized by Raschke & Connors (1996).
Target: 58-65% WR, 25-50 trades/year per symbol.
"""
from typing import List
import numpy as np
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

EMA_PERIOD = 20
ATR_PERIOD = 14
ATR_MULT = 2.5           # Keltner band width
RSI_PERIOD = 14
SMA_PERIOD = 200          # Trend filter
TP_PCT = 0.06             # 6% TP
SL_PCT = 0.04             # 4% SL (1.5:1 R:R)


class KeltnerChannelReversionPT(BaseStrategy):
    name = "keltner_channel_reversion"
    display_name = "Keltner Channel Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

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
    def _ema(values, period):
        """EMA over numpy array, returns last value."""
        if len(values) < period:
            return float(np.mean(values))
        k = 2.0 / (period + 1)
        ema = float(np.mean(values[:period]))
        for i in range(period, len(values)):
            ema = values[i] * k + ema * (1 - k)
        return ema

    @staticmethod
    def _atr(highs, lows, closes, period=ATR_PERIOD):
        """Wilder ATR, returns last value."""
        n = len(closes)
        if n < period + 1:
            return 0.0
        tr = np.empty(n)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]))
        atr_val = float(np.mean(tr[:period]))
        alpha = 1.0 / period
        for i in range(period, n):
            atr_val = atr_val * (1 - alpha) + tr[i] * alpha
        return atr_val

    @staticmethod
    def _rsi_last(closes, period=RSI_PERIOD):
        """Wilder RSI, returns last value only."""
        n = len(closes)
        if n < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_g = float(np.mean(gains[:period]))
        avg_l = float(np.mean(losses[:period]))
        alpha = 1.0 / period
        for i in range(period, len(deltas)):
            avg_g = avg_g * (1 - alpha) + gains[i] * alpha
            avg_l = avg_l * (1 - alpha) + losses[i] * alpha
        if avg_l == 0:
            return 100.0
        return 100 - 100 / (1 + avg_g / avg_l)

    @staticmethod
    def _sma(values, period):
        if len(values) < period:
            return float(np.mean(values))
        return float(np.mean(values[-period:]))

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < SMA_PERIOD:
                continue

            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])
            price = float(closes[-1])

            ema20 = self._ema(closes, EMA_PERIOD)
            atr_val = self._atr(highs, lows, closes, ATR_PERIOD)
            rsi = self._rsi_last(closes, RSI_PERIOD)
            sma200 = self._sma(closes, SMA_PERIOD)

            if atr_val <= 0:
                continue

            upper = ema20 + ATR_MULT * atr_val
            lower = ema20 - ATR_MULT * atr_val

            # LONG: Price at/below lower Keltner, RSI < 40, above 200 SMA
            if price <= lower and rsi < 40 and price > sma200:
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                depth = (lower - price) / atr_val if atr_val > 0 else 0
                confidence = min(0.88, 0.55 + depth * 0.1 + (40 - rsi) * 0.005)
                reason = (f"Price ${price:.2f} at lower Keltner ${lower:.2f}, "
                          f"RSI={rsi:.1f}, above SMA200, target EMA20=${ema20:.2f}")

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=price,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "ema20": round(ema20, 2),
                        "atr": round(atr_val, 2),
                        "rsi": round(rsi, 2),
                        "upper_keltner": round(upper, 2),
                        "lower_keltner": round(lower, 2),
                    },
                ))

            # SHORT: Price at/above upper Keltner, RSI > 60, below 200 SMA
            elif price >= upper and rsi > 60 and price < sma200:
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                depth = (price - upper) / atr_val if atr_val > 0 else 0
                confidence = min(0.88, 0.55 + depth * 0.1 + (rsi - 60) * 0.005)
                reason = (f"Price ${price:.2f} at upper Keltner ${upper:.2f}, "
                          f"RSI={rsi:.1f}, below SMA200, target EMA20=${ema20:.2f}")

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="SHORT",
                    entry_price=price,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "ema20": round(ema20, 2),
                        "atr": round(atr_val, 2),
                        "rsi": round(rsi, 2),
                        "upper_keltner": round(upper, 2),
                        "lower_keltner": round(lower, 2),
                    },
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
