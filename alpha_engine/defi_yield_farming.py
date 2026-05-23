# DeFi Yield-Farming & Staking Strategies
# Simple yield-farming signal based on APY thresholds and token price momentum.
# Auto-fetches data using the unified data provider.

import logging
from data_providers.crypto_data import build_context

logger = logging.getLogger(__name__)


class DeFiYieldFarmingStrategy:
    """Select high-APY pools that also show positive price momentum.

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
        pools = self.context.get('defi_pools', {})
        for symbol, data in pools.items():
            apy = data.get('apy', 0)
            momentum = data.get('momentum', 0)
            # Require APY > 15% and momentum > 0.5% over last 4h
            if apy > 15 and momentum > 0.5:
                price = data.get('price')
                if price is None:
                    continue
                tp = price * 1.10  # 10% target
                sl = price * 0.95  # 5% stop
                signals.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "entry": price,
                    "tp": tp,
                    "sl": sl,
                    "size": 0.02,
                    "confidence": 0.60,
                    "strategy": "defi_yield_farming",
                    "reason": f"Yield-farming pool {symbol} with APY {apy:.1f}% "
                              f"and momentum {momentum:.2f}%"
                })
        return signals
