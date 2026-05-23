"""Simpleton-Mercury Hybrid - EMA(21)/EMA(55) cross with RSI and TR>ATR volatility gate."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class SimpletonMercuryHybrid(BaseStrategy):
    name = "simpleton_mercury_hybrid"
    display_name = "Simpleton-Mercury Hybrid"
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

            ema21 = self._ema(closes, 21)
            ema55 = self._ema(closes, 55)
            ema200 = self._ema(closes, 200)
            rsi_vals = self._rsi(closes, 14)
            atr_vals = self._atr(highs, lows, closes, 14)

            price = closes[-1]
            atr_now = atr_vals[-1] if atr_vals[-1] > 0 else 1e-8
            rsi_now = rsi_vals[-1]

            # Compute raw TR for latest bar (Simpleton volatility gate)
            tr_now = max(
                highs[-1] - lows[-1],
                abs(highs[-1] - closes[-2]),
                abs(lows[-1] - closes[-2]),
            )

            # Crossover detection: EMA(21)/EMA(55) like Simpleton
            cross_up = ema21[-1] > ema55[-1] and ema21[-2] <= ema55[-2]
            cross_down = ema21[-1] < ema55[-1] and ema21[-2] >= ema55[-2]

            # Volatility gate: TR must exceed ATR (from Simpleton)
            volatility_ok = tr_now > atr_now

            # RSI 3-bar lookback: check if RSI was extreme in last 3 bars
            rsi_recent = rsi_vals[-3:]
            rsi_recent_low = min(rsi_recent) if len(rsi_recent) >= 3 else rsi_now
            rsi_recent_high = max(rsi_recent) if len(rsi_recent) >= 3 else rsi_now

            # RSI thresholds from Mercury: < 30 LONG, > 70 SHORT (3-bar lookback)
            direction = None
            if cross_up and price > ema200[-1] and rsi_recent_low < 30 and volatility_ok:
                direction = "LONG"
            elif cross_down and price < ema200[-1] and rsi_recent_high > 70 and volatility_ok:
                direction = "SHORT"

            if direction is None:
                continue

            # Hybrid: wide TP (5x ATR), moderate SL (2x ATR) = 2.5:1 RR
            if direction == "LONG":
                tp = round(price + 5 * atr_now, 6)
                sl = round(price - 2 * atr_now, 6)
            else:
                tp = round(price - 5 * atr_now, 6)
                sl = round(price + 2 * atr_now, 6)

            ema_gap = abs(ema21[-1] - ema55[-1]) / price
            rsi_dist = abs(rsi_now - 50) / 50
            tr_ratio = tr_now / atr_now
            confidence = min(0.9, 0.5 + ema_gap * 10 + rsi_dist * 0.15 + (tr_ratio - 1) * 0.05)

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
                    f"EMA(21)xEMA(55) {direction} [hybrid] | "
                    f"price {'>' if direction == 'LONG' else '<'} EMA(200) | "
                    f"RSI={rsi_now:.1f} | TR/ATR={tr_ratio:.2f}"
                ),
                raw_signal={
                    "ema21": round(ema21[-1], 4),
                    "ema55": round(ema55[-1], 4),
                    "ema200": round(ema200[-1], 4),
                    "rsi": round(rsi_now, 2),
                    "atr": round(atr_now, 4),
                    "tr": round(tr_now, 4),
                    "tr_ratio": round(tr_ratio, 4),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
