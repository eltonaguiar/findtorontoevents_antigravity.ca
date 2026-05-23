"""Cross-Exchange Spread - price divergence between Binance and Kraken."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

PAIRS = {
    "BTCUSDT": "XXBTZUSD",
    "ETHUSDT": "XETHZUSD",
    "SOLUSDT": "SOLUSD",
    "ADAUSDT": "ADAUSD",
    "DOTUSDT": "DOTUSD",
    "LINKUSDT": "LINKUSD",
    "XRPUSDT": "XXRPZUSD",
    "AVAXUSDT": "AVAXUSD",
}

SPREAD_THRESHOLD = 0.003
TP_PCT = 0.025
SL_PCT = 0.015


class CrossExchangeSpread(BaseStrategy):
    name = "cross_exchange_spread"
    display_name = "Cross-Exchange Spread"
    source = "Binance + Kraken"
    category = "crypto"
    portfolio_type = "smart_money"

    def fetch_data(self) -> dict:
        binance_prices = {}
        kraken_prices = {}

        for binance_sym in PAIRS:
            try:
                t = self._fetch_binance(binance_sym)
                binance_prices[binance_sym] = float(t.get("price", 0))
            except Exception:
                continue

        try:
            kraken_data = self._fetch_kraken()
            for binance_sym, kraken_sym in PAIRS.items():
                pair_data = kraken_data.get("result", {}).get(kraken_sym)
                if pair_data:
                    kraken_prices[binance_sym] = float(pair_data["c"][0])
        except Exception:
            pass

        return {"binance": binance_prices, "kraken": kraken_prices}

    @rate_limited("binance", 0.2)
    def _fetch_binance(self, symbol: str) -> dict:
        return fetch_json("https://api.binance.com/api/v3/ticker/price",
                          params={"symbol": symbol})

    @rate_limited("kraken", 1.0)
    @cached(ttl_seconds=300)
    def _fetch_kraken(self) -> dict:
        pairs = ",".join(PAIRS.values())
        return fetch_json("https://api.kraken.com/0/public/Ticker",
                          params={"pair": pairs})

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        binance = data.get("binance", {})
        kraken = data.get("kraken", {})

        for symbol in PAIRS:
            b_price = binance.get(symbol, 0)
            k_price = kraken.get(symbol, 0)
            if b_price <= 0 or k_price <= 0:
                continue

            mid = (b_price + k_price) / 2
            spread = (b_price - k_price) / mid

            if abs(spread) > SPREAD_THRESHOLD:
                if spread > SPREAD_THRESHOLD:
                    direction = "SHORT"
                    reason = f"Binance premium +{spread*100:.2f}% vs Kraken -> convergence SHORT"
                else:
                    direction = "LONG"
                    reason = f"Binance discount {spread*100:.2f}% vs Kraken -> convergence LONG"

                entry = b_price
                if direction == "LONG":
                    tp = round(entry * (1 + TP_PCT), 6)
                    sl = round(entry * (1 - SL_PCT), 6)
                else:
                    tp = round(entry * (1 - TP_PCT), 6)
                    sl = round(entry * (1 + SL_PCT), 6)

                confidence = min(0.8, 0.5 + abs(spread) * 50)

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={"binance_price": b_price, "kraken_price": k_price, "spread": spread},
                ))

        return picks
