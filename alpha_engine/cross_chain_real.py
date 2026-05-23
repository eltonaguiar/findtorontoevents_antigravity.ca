# Full Cross-Exchange Arbitrage Strategy with Real CCXT Exchanges
#
# Compares spot prices across Binance, Bybit, OKX for BTC, ETH, SOL.
# Generates LONG on low-price exchange if spread >1%.
#
import ccxt
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrossExchangeArbitrageStrategy:
    SPREAD_THRESHOLD = 1.0  # %
    SIZE = 0.01
    TP_MULT = 0.995
    SL_MULT = 1.005
    SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance(),
            'bybit': ccxt.bybit(),
            'okx': ccxt.okx()
        }

    def fetch_prices(self, symbol: str) -> Dict[str, float]:
        prices = {}
        for name, ex in self.exchanges.items():
            try:
                ticker = ex.fetch_ticker(symbol)
                prices[name] = ticker['last']
            except Exception as e:
                logger.warning("Failed to fetch %s from %s: %s", symbol, name, e)
        return prices

    def generate_signals(self) -> List[Dict]:
        signals = []
        for symbol in self.SYMBOLS:
            prices = self.fetch_prices(symbol)
            if len(prices) < 2:
                continue
            low_ex = min(prices, key=prices.get)
            high_ex = max(prices, key=prices.get)
            low_price = prices[low_ex]
            high_price = prices[high_ex]
            spread_pct = (high_price - low_price) / low_price * 100
            if spread_pct > self.SPREAD_THRESHOLD:
                signals.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "direction": "LONG",
                    "entry": low_price,
                    "tp": high_price * self.TP_MULT,
                    "sl": low_price * self.SL_MULT,
                    "size": self.SIZE,
                    "reason": f"Arb {low_ex} ({low_price}) -> {high_ex} ({high_price}) spread {spread_pct:.2f}%"
                })
                logger.info("Arb signal for %s: %s -> %s spread %.2f%%", symbol, low_ex, high_ex, spread_pct)
        logger.info("Generated %d arb signals", len(signals))
        return signals