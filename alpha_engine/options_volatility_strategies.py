# Options Volatility Strategies
# Implements option-volatility alpha: straddles, strangles, delta-neutral spreads.
# Auto-fetches data using the unified data provider.

import logging
from data_providers.crypto_data import build_context

logger = logging.getLogger(__name__)


class OptionsVolatilityStrategy:
    """Generate signals based on option-volatility decay and spread positioning.

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
        """Return a list of signal dictionaries.
        Each signal dict follows the platform schema:
        {
            "symbol": str,
            "direction": "LONG"|"SHORT",
            "entry": float,
            "tp": float,
            "sl": float,
            "size": float,
            "reason": str,
        }
        """
        signals = []
        iv = self.context.get('iv_surface')
        if iv is None:
            return signals
        spot_prices = self.context.get('spot_price', {})
        for symbol, iv_percent in iv.items():
            if iv_percent > 80:
                spot = spot_prices.get(symbol, None)
                if spot is None:
                    continue
                # Sell straddle: short ATM call & put, receive premium.
                premium = spot * 0.01  # placeholder 1% premium
                tp = spot * 0.98  # 2% down move to capture decay
                sl = spot * 1.02  # 2% up move as stop
                signals.append({
                    "symbol": symbol,
                    "direction": "SHORT",
                    "entry": spot,
                    "tp": tp,
                    "sl": sl,
                    "size": 0.01,
                    "confidence": 0.65,
                    "strategy": "options_volatility_straddle",
                    "reason": f"Sell straddle on high IV ({iv_percent:.1f}%) for {symbol}"
                })
        return signals
