"""Exchange Netflow - large outflows = accumulation signal."""
from typing import List
import os
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

CRYPTOQUANT_KEY = os.environ.get("CRYPTOQUANT_API_KEY", "")
TP_PCT = 0.06
SL_PCT = 0.03


class ExchangeNetflow(BaseStrategy):
    name = "exchange_netflow"
    display_name = "Exchange Netflow"
    source = "CryptoQuant"
    category = "crypto"
    portfolio_type = "onchain"

    @rate_limited("cryptoquant", 3.0)
    @cached(ttl_seconds=7200)
    def fetch_data(self) -> dict:
        if not CRYPTOQUANT_KEY:
            return self._fallback_binance_flow()
        headers = {"Authorization": f"Bearer {CRYPTOQUANT_KEY}"}
        try:
            data = fetch_json(
                "https://api.cryptoquant.com/v1/btc/exchange-flows/netflow",
                params={"window": "day", "limit": 7},
                headers=headers
            )
            return {"source": "cryptoquant", "data": data}
        except Exception:
            return self._fallback_binance_flow()

    def _fallback_binance_flow(self) -> dict:
        klines = fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": "BTCUSDT", "interval": "1d", "limit": 7}
        )
        return {"source": "binance_proxy", "klines": klines}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        source = data.get("source", "")

        if source == "cryptoquant":
            result = data.get("data", {}).get("result", {}).get("data", [])
            if len(result) >= 2:
                latest = float(result[-1].get("value", 0))
                prev = float(result[-2].get("value", 0))
                if latest < -1000 and latest < prev:
                    self._add_btc_pick(picks, confidence=0.7,
                                       reason=f"BTC exchange outflow: {latest:.0f} BTC (accumulation)")
        elif source == "binance_proxy":
            klines = data.get("klines", [])
            if len(klines) >= 7:
                volumes = [float(k[5]) for k in klines]
                prices = [float(k[4]) for k in klines]
                vol_trend = volumes[-1] / (sum(volumes[:-1]) / max(len(volumes) - 1, 1))
                price_change = (prices[-1] - prices[-3]) / prices[-3] if prices[-3] else 0
                if vol_trend > 1.5 and price_change < -0.02:
                    self._add_btc_pick(picks, confidence=0.6,
                                       reason=f"Volume proxy: {vol_trend:.1f}x avg + price dip {price_change*100:.1f}%")

        return picks

    def _add_btc_pick(self, picks: list, confidence: float, reason: str):
        try:
            ticker = fetch_json("https://api.binance.com/api/v3/ticker/price",
                                params={"symbol": "BTCUSDT"})
            price = float(ticker.get("price", 0))
            if price > 0:
                picks.append(NormalizedPick(
                    symbol="BTCUSDT",
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=confidence,
                    reason=reason,
                ))
        except Exception:
            pass
