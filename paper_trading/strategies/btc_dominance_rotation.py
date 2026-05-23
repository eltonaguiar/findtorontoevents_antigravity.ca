"""BTC Dominance Rotation - rotate to alts when BTC.D falling, back to BTC when rising."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

ALT_TOKENS = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT",
              "LINKUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT", "ARBUSDT"]

TP_PCT = 0.08
SL_PCT = 0.04


class BtcDominanceRotation(BaseStrategy):
    name = "btc_dominance_rotation"
    display_name = "BTC Dominance Rotation"
    source = "CoinGecko"
    category = "crypto"
    portfolio_type = "macro"

    @rate_limited("coingecko", 1.5)
    @cached(ttl_seconds=7200)
    def fetch_data(self) -> dict:
        global_data = fetch_json("https://api.coingecko.com/api/v3/global")
        return global_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        try:
            market_data = data.get("data", {})
            btc_dom = market_data.get("market_cap_percentage", {}).get("btc", 50)
            btc_dom_change = market_data.get("market_cap_change_percentage_24h_usd", 0)

            # BTC dominance falling + market rising -> alt season
            if btc_dom < 55 and btc_dom_change < -1:
                for symbol in ALT_TOKENS[:5]:
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

                    confidence = min(0.8, 0.5 + (55 - btc_dom) / 30)
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
                        reason=f"BTC.D={btc_dom:.1f}% falling ({btc_dom_change:+.1f}% 24h) -> alt rotation",
                        raw_signal={"btc_dominance": btc_dom, "change_24h": btc_dom_change},
                    ))

            # BTC dominance rising sharply -> flight to BTC
            elif btc_dom > 55 and btc_dom_change > 1:
                try:
                    ticker = fetch_json("https://api.binance.com/api/v3/ticker/price",
                                        params={"symbol": "BTCUSDT"})
                    price = float(ticker.get("price", 0))
                    if price > 0:
                        confidence = min(0.8, 0.5 + (btc_dom - 55) / 30)
                        picks.append(NormalizedPick(
                            symbol="BTCUSDT",
                            direction="LONG",
                            entry_price=price,
                            tp=round(price * (1 + TP_PCT), 6),
                            sl=round(price * (1 - SL_PCT), 6),
                            strategy=self.name,
                            strategy_name=self.display_name,
                            category=self.category,
                            confidence=round(confidence, 3),
                            reason=f"BTC.D={btc_dom:.1f}% rising ({btc_dom_change:+.1f}%) -> flight to BTC",
                            raw_signal={"btc_dominance": btc_dom, "change_24h": btc_dom_change},
                        ))
                except Exception:
                    pass

        except (KeyError, TypeError):
            pass

        return picks
