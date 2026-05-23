"""RSI-2 Mean Reversion - Connors RSI-2 oversold/overbought on crypto."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

RSI_OVERSOLD = 10
RSI_OVERBOUGHT = 90
TP_PCT = 0.04
SL_PCT = 0.02


class Rsi2MeanReversion(BaseStrategy):
    name = "rsi2_mean_reversion"
    display_name = "RSI-2 Mean Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1d", limit=10)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _rsi(self, closes: list, period: int = 2) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains[-period:]) / period if gains else 0.001
        avg_loss = sum(losses[-period:]) / period if losses else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        return 100 - (100 / (1 + rs))

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 5:
                continue

            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            rsi = self._rsi(closes, period=2)

            if rsi < RSI_OVERSOLD:
                direction = "LONG"
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                confidence = min(0.9, 0.5 + (RSI_OVERSOLD - rsi) / 20)
                reason = f"RSI(2)={rsi:.1f} oversold -> mean reversion LONG"
            elif rsi > RSI_OVERBOUGHT:
                direction = "SHORT"
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                confidence = min(0.9, 0.5 + (rsi - RSI_OVERBOUGHT) / 20)
                reason = f"RSI(2)={rsi:.1f} overbought -> mean reversion SHORT"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp, sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"rsi2": rsi, "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
