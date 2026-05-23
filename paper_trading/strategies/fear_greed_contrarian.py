"""Fear & Greed Contrarian - buy when extreme fear, sell when extreme greed."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

SENTIMENT_TOKENS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
]

TP_PCT = 0.06
SL_PCT = 0.03


class FearGreedContrarian(BaseStrategy):
    name = "fear_greed_contrarian"
    display_name = "Fear & Greed Contrarian"
    source = "Alternative.me"
    category = "crypto"
    portfolio_type = "sentiment"

    @rate_limited("alternative_me", 2.0)
    @cached(ttl_seconds=3600)
    def fetch_data(self) -> dict:
        data = fetch_json("https://api.alternative.me/fng/?limit=7")
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        fng_data = data.get("data", [])
        if not fng_data:
            return picks

        current_value = int(fng_data[0].get("value", 50))
        classification = fng_data[0].get("value_classification", "Neutral")

        if 20 < current_value < 80:
            return picks

        direction = "LONG" if current_value <= 20 else "SHORT"
        confidence = min(0.9, 0.5 + abs(current_value - 50) / 100)

        for symbol in SENTIMENT_TOKENS[:5]:
            try:
                ticker = fetch_json(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol}
                )
                price = float(ticker.get("price", 0))
            except Exception:
                continue

            if price <= 0:
                continue

            if direction == "LONG":
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
            else:
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)

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
                reason=f"F&G Index: {current_value} ({classification}) -> contrarian {direction}",
                raw_signal={"fng_value": current_value, "classification": classification},
            ))

        return picks
