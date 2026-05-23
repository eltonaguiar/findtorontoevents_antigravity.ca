"""Whale Accumulation - unusual volume spike + price dip = smart money buying."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

TP_PCT = 0.06
SL_PCT = 0.03


class WhaleAccumulation(BaseStrategy):
    name = "whale_accumulation"
    display_name = "Whale Accumulation"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "smart_money"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1d", limit=30)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 20:
                continue

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]
            current_vol = volumes[-1]
            avg_vol = sum(volumes[-20:-1]) / 19

            sma_10 = sum(closes[-10:]) / 10
            price_below_sma = price < sma_10

            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0

            if vol_ratio >= 5 and price_below_sma:
                confidence = min(0.9, 0.55 + (vol_ratio - 5) / 30)
                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"Vol {vol_ratio:.1f}x avg + price below 10d SMA - whale accumulation",
                    raw_signal={"vol_ratio": vol_ratio, "sma_10": sma_10, "price": price},
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:3]
