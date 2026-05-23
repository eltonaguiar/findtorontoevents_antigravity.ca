"""Stablecoin Supply Ratio - SSR declining = buying power building."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

BUY_TOKENS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TP_PCT = 0.06
SL_PCT = 0.03


class StablecoinSupply(BaseStrategy):
    name = "stablecoin_supply"
    display_name = "Stablecoin Supply Ratio"
    source = "CoinGecko"
    category = "crypto"
    portfolio_type = "onchain"

    @rate_limited("coingecko", 1.5)
    @cached(ttl_seconds=7200)
    def fetch_data(self) -> dict:
        btc = fetch_json("https://api.coingecko.com/api/v3/coins/bitcoin",
                         params={"localization": "false", "tickers": "false",
                                 "community_data": "false", "developer_data": "false"})
        usdt = fetch_json("https://api.coingecko.com/api/v3/coins/tether",
                          params={"localization": "false", "tickers": "false",
                                  "community_data": "false", "developer_data": "false"})
        usdc = fetch_json("https://api.coingecko.com/api/v3/coins/usd-coin",
                          params={"localization": "false", "tickers": "false",
                                  "community_data": "false", "developer_data": "false"})
        return {"btc": btc, "usdt": usdt, "usdc": usdc}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        try:
            btc_mcap = data["btc"]["market_data"]["market_cap"]["usd"]
            usdt_mcap = data["usdt"]["market_data"]["market_cap"]["usd"]
            usdc_mcap = data["usdc"]["market_data"]["market_cap"]["usd"]
            stable_mcap = usdt_mcap + usdc_mcap

            ssr = btc_mcap / stable_mcap if stable_mcap > 0 else 999

            if ssr < 5:
                confidence = min(0.85, 0.5 + (5 - ssr) / 10)
                for symbol in BUY_TOKENS:
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
                        reason=f"SSR={ssr:.2f} (low) - stablecoin buying power building",
                        raw_signal={"ssr": ssr, "btc_mcap": btc_mcap, "stable_mcap": stable_mcap},
                    ))
        except (KeyError, TypeError):
            pass

        return picks
