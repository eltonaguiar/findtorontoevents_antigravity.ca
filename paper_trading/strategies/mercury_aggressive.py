"""Mercury Aggressive - Relaxed RSI thresholds with tight stops for high RR entries."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class MercuryAggressive(BaseStrategy):
    name = "mercury_aggressive"
    display_name = "Mercury Aggressive"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

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

    # --- Indicators ---

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

    # --- Signal Generation ---

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            if len(klines) < 210:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]

            ema9 = self._ema(closes, 9)
            ema21 = self._ema(closes, 21)
            ema200 = self._ema(closes, 200)
            rsi_vals = self._rsi(closes, 14)
            atr_vals = self._atr(highs, lows, closes, 14)

            price = closes[-1]
            atr_now = atr_vals[-1] if atr_vals[-1] > 0 else 1e-8
            rsi_now = rsi_vals[-1]

            # Crossover detection
            cross_up = ema9[-1] > ema21[-1] and ema9[-2] <= ema21[-2]
            cross_down = ema9[-1] < ema21[-1] and ema9[-2] >= ema21[-2]

            # RSI 3-bar lookback: check if RSI was extreme in last 3 bars
            rsi_recent = rsi_vals[-3:]
            rsi_recent_low = min(rsi_recent) if len(rsi_recent) >= 3 else rsi_now
            rsi_recent_high = max(rsi_recent) if len(rsi_recent) >= 3 else rsi_now

            # Aggressive: RSI < 35 for LONG, > 65 for SHORT (relaxed thresholds, 3-bar lookback)
            direction = None
            if cross_up and price > ema200[-1] and rsi_recent_low < 35:
                direction = "LONG"
            elif cross_down and price < ema200[-1] and rsi_recent_high > 65:
                direction = "SHORT"

            if direction is None:
                continue

            # Aggressive: tight stops (1.5x ATR), generous TP (4.5x ATR) = 3:1 RR
            if direction == "LONG":
                tp = round(price + 4.5 * atr_now, 6)
                sl = round(price - 1.5 * atr_now, 6)
            else:
                tp = round(price - 4.5 * atr_now, 6)
                sl = round(price + 1.5 * atr_now, 6)

            ema_gap = abs(ema9[-1] - ema21[-1]) / price
            rsi_dist = abs(rsi_now - 50) / 50
            confidence = min(0.9, 0.45 + ema_gap * 10 + rsi_dist * 0.15)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=(
                    f"EMA(9)xEMA(21) {direction} [aggressive] | "
                    f"price {'>' if direction == 'LONG' else '<'} EMA(200) | "
                    f"RSI={rsi_now:.1f} | ATR={atr_now:.4f} | RR=3:1"
                ),
                raw_signal={
                    "ema9": round(ema9[-1], 4),
                    "ema21": round(ema21[-1], 4),
                    "ema200": round(ema200[-1], 4),
                    "rsi": round(rsi_now, 2),
                    "atr": round(atr_now, 4),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
