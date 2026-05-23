# Cross-Chain DEX Arbitrage Strategy
# Detects price differences for the same token across multiple DEXs and blockchains.
# Auto-fetches data using the unified data provider.

import logging
from data_providers.crypto_data import build_context

logger = logging.getLogger(__name__)


class CrossChainDEXArbitrageStrategy:
    """Generate arbitrage signals when price spread exceeds a threshold.

    Automatically builds its own context from the data provider.
    External context values can override defaults.
    """
    def __init__(self, context=None):
        try:
            generated = build_context()
        except Exception as e:
            logger.warning("Failed to build context: %s", e)
            generated = {}
        self.context = generated
        if context:
            self.context.update(context)

    def generate_signals(self):
        signals = []
        dex_prices = self.context.get('dex_prices', {})
        for symbol, prices in dex_prices.items():
            if not prices:
                continue
            low_ex = min(prices, key=prices.get)
            high_ex = max(prices, key=prices.get)
            low_price = prices[low_ex]
            high_price = prices[high_ex]
            spread_pct = (high_price - low_price) / low_price * 100
            # Require at least 1% spread after fees
            if spread_pct > 1.0:
                signals.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "entry": low_price,
                    "tp": high_price * 0.995,
                    "sl": low_price * 1.005,
                    "size": 0.01,
                    "confidence": min(0.55 + spread_pct * 0.05, 0.85),
                    "strategy": "cross_chain_dex_arb",
                    "reason": f"Cross-DEX arb {low_ex}->{high_ex} "
                              f"spread {spread_pct:.2f}% for {symbol}"
                })
        return signals
