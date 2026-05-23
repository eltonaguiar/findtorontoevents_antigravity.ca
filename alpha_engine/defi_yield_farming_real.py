# Full DeFi Yield Farming Strategy with Real DeFiLlama API
#
# Fetches live APY from DeFiLlama, filters high APY pools, generates LONG signals.
# Fallback to mock data.
#
import requests
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeFiYieldFarmingStrategy:
    APY_THRESHOLD = 15.0
    MOMENTUM_THRESHOLD = 0.5
    TP_MULT = 1.10
    SL_MULT = 0.95
    SIZE = 0.02

    def __init__(self):
        self.session = requests.Session()

    def fetch_defi_pools(self) -> List[Dict]:
        try:
            r = self.session.get('https://yields.llama.fi/pools', timeout=10)
            r.raise_for_status()
            pools = r.json()
            filtered = []
            for p in pools[:50]:  # Top 50 to limit
                apy = p.get('apyMean30d', 0)
                if apy > self.APY_THRESHOLD:
                    symbol = p['symbol'].split('-')[0]  # e.g., 'USDC-eUSDC' -> 'USDC'
                    filtered.append({
                        'symbol': symbol,
                        'apy': apy,
                        'price': p.get('tvlUsd', 1.0) / p.get('tvl', 1.0),  # proxy price
                        'momentum': 1.0  # placeholder, add ccxt for real
                    })
            logger.info("Fetched %d high-APY pools from DeFiLlama", len(filtered))
            return filtered
        except Exception as e:
            logger.error("DeFiLlama fetch failed: %s, using mock", e)
            return [
                {"symbol": "AAVE", "apy": 18.5, "price": 70.0, "momentum": 1.2},
                {"symbol": "UNI", "apy": 12.0, "price": 5.5, "momentum": 0.8},
            ]

    def generate_signals(self) -> List[Dict]:
        try:
            pools = self.fetch_defi_pools()
            signals = []
            for data in pools:
                apy = data.get('apy', 0)
                momentum = data.get('momentum', 0)
                if apy > self.APY_THRESHOLD and momentum > self.MOMENTUM_THRESHOLD:
                    price = data.get('price')
                    tp = price * self.TP_MULT
                    sl = price * self.SL_MULT
                    signals.append({
                        "symbol": data['symbol'],
                        "direction": "LONG",
                        "entry": price,
                        "tp": tp,
                        "sl": sl,
                        "size": self.SIZE,
                        "reason": f"High APY {apy:.1f}% pool {data['symbol']}"
                    })
            logger.info("DeFi strategy generated %d signals", len(signals))
            return signals
        except Exception as e:
            logger.error("Error in generate_signals: %s", e)
            return []
