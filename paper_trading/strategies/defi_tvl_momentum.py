"""DeFi TVL Momentum - buy tokens whose protocol TVL is growing >10%/week."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

PROTOCOL_TOKEN_MAP = {
    "Lido": "LDOUSDT",
    "AAVE": "AAVEUSDT",
    "Uniswap": "UNIUSDT",
    "MakerDAO": "MKRUSDT",
    "Curve DEX": "CRVUSDT",
    "Compound": "COMPUSDT",
    "Synthetix": "SNXUSDT",
    "Balancer": "BALUSDT",
    "SushiSwap": "SUSHIUSDT",
    "PancakeSwap": "CAKEUSDT",
    "Convex Finance": "CVXUSDT",
    "Yearn Finance": "YFIUSDT",
    "1inch": "1INCHUSDT",
    "dYdX": "DYDXUSDT",
    "GMX": "GMXUSDT",
    "Pendle": "PENDLEUSDT",
    "Ethena": "ENAUSDT",
    "Jupiter": "JUPUSDT",
    "Raydium": "RAYUSDT",
    "Ondo Finance": "ONDOUSDT",
}

TP_PCT = 0.08
SL_PCT = 0.04


class DefiTvlMomentum(BaseStrategy):
    name = "defi_tvl_momentum"
    display_name = "DeFi TVL Momentum"
    source = "DeFiLlama"
    category = "defi"
    portfolio_type = "onchain"

    @rate_limited("defillama", 1.0)
    @cached(ttl_seconds=3600)
    def fetch_data(self) -> dict:
        protocols = fetch_json("https://api.llama.fi/protocols")
        return {"protocols": protocols}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        protocols = data.get("protocols", [])

        for p in protocols:
            name = p.get("name", "")
            token = PROTOCOL_TOKEN_MAP.get(name)
            if not token:
                continue

            tvl_now = p.get("tvl", 0) or 0
            tvl_1w = p.get("change_7d", 0) or 0

            if tvl_now < 50_000_000:
                continue

            if tvl_1w > 10:
                try:
                    ticker = fetch_json(
                        "https://api.binance.com/api/v3/ticker/price",
                        params={"symbol": token}
                    )
                    price = float(ticker.get("price", 0))
                except Exception:
                    continue

                if price <= 0:
                    continue

                confidence = min(0.9, 0.5 + (tvl_1w - 10) / 100)

                picks.append(NormalizedPick(
                    symbol=token,
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"TVL {name}: ${tvl_now/1e6:.0f}M (+{tvl_1w:.1f}% 7d)",
                    raw_signal={"protocol": name, "tvl": tvl_now, "change_7d": tvl_1w},
                ))

        return picks[:5]
