"""Protective Momentum — Multi-factor momentum with contrarian fade (Triton Quant + Lake Forest)."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class ProtectiveMomentum(BaseStrategy):
    name = "protective_momentum"
    display_name = "Protective Momentum"
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

    @staticmethod
    def _sma(values: list, period: int) -> list:
        result = [None] * (period - 1)
        for i in range(period - 1, len(values)):
            result.append(sum(values[i - period + 1:i + 1]) / period)
        return result

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            if len(klines) < 100:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            ema12 = self._ema(closes, 12)
            ema26 = self._ema(closes, 26)
            macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
            macd_signal = self._ema(macd_line, 9)
            macd_hist = [macd_line[i] - macd_signal[i] for i in range(len(closes))]

            ema50 = self._ema(closes, 50)
            rsi_vals = self._rsi(closes, 14)
            atr_vals = self._atr(highs, lows, closes, 14)
            vol_ma = self._sma(volumes, 20)
            atr_ma = self._sma(atr_vals, 50)

            i = len(closes) - 1
            if i < 60 or atr_vals[i] <= 0 or vol_ma[i] is None or atr_ma[i] is None:
                continue

            price = closes[i]
            rsi_now = rsi_vals[i]
            rsi_prev = rsi_vals[i - 1]
            macd_h = macd_hist[i]
            macd_h_prev = macd_hist[i - 1]
            vol_ratio = volumes[i] / vol_ma[i] if vol_ma[i] > 0 else 0
            vol_confirmed = vol_ratio > 1.5
            vol_elevated = atr_vals[i] > 2.0 * atr_ma[i]
            strength_mod = 0.5 if vol_elevated else 1.0

            stop_dist = 1.5 * atr_vals[i]
            direction = None
            signal_type = ""

            # MOMENTUM LONG
            if (rsi_now > 50 and rsi_now > rsi_prev and
                macd_h > 0 and macd_h > macd_h_prev and
                price > ema50[i] and vol_confirmed):
                direction = "LONG"
                tp = round(price + 2.0 * atr_vals[i], 6)
                sl = round(price - stop_dist, 6)
                signal_type = "Momentum"
                base_conf = 0.45 + (rsi_now - 50) / 200

            # MOMENTUM SHORT
            elif (rsi_now < 50 and rsi_now < rsi_prev and
                  macd_h < 0 and macd_h < macd_h_prev and
                  price < ema50[i] and vol_confirmed):
                direction = "SHORT"
                tp = round(price - 2.0 * atr_vals[i], 6)
                sl = round(price + stop_dist, 6)
                signal_type = "Momentum"
                base_conf = 0.45 + (50 - rsi_now) / 200

            # CONTRARIAN LONG
            elif rsi_now < 25 and macd_h > macd_h_prev and vol_confirmed:
                direction = "LONG"
                tp = round(price + 1.5 * atr_vals[i], 6)
                sl = round(price - stop_dist, 6)
                signal_type = "Contrarian"
                base_conf = 0.5 + (25 - rsi_now) / 100

            # CONTRARIAN SHORT
            elif rsi_now > 75 and macd_h < macd_h_prev and vol_confirmed:
                direction = "SHORT"
                tp = round(price - 1.5 * atr_vals[i], 6)
                sl = round(price + stop_dist, 6)
                signal_type = "Contrarian"
                base_conf = 0.5 + (rsi_now - 75) / 100

            if direction is None:
                continue

            confidence = round(min(0.9, base_conf * strength_mod), 3)
            prot_tag = " [VOL PROTECTED]" if vol_elevated else ""

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=confidence,
                reason=(f"Protective {signal_type} {direction} | "
                        f"RSI={rsi_now:.1f} | MACD hist={macd_h:.4f} | "
                        f"Vol={vol_ratio:.1f}x{prot_tag}"),
                raw_signal={"rsi": round(rsi_now, 2), "macd_hist": round(macd_h, 6),
                            "vol_ratio": round(vol_ratio, 2), "signal_type": signal_type},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
