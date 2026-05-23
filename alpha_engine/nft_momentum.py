# NFT / Metaverse Momentum Strategy
# Tracks floor price and volume for a given NFT collection and generates breakout signals.
# Uses the unified data provider for market data.

import logging
from data_providers.crypto_data import build_context

logger = logging.getLogger(__name__)


class NFTMomentumStrategy:
    """Detect momentum in NFT collections based on floor price and sales volume.

    The strategy builds its own context using the unified data provider.
    External context values can override the defaults.
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
        nft_data = self.context.get('nft_data', {})
        for collection, data in nft_data.items():
            floor = data.get('floor')
            volume = data.get('volume')
            momentum = data.get('momentum')
            # Require momentum > 1% and volume > 1000
            if floor and volume and momentum and momentum > 1.0 and volume > 1000:
                tp = floor * 1.10
                sl = floor * 0.95
                signals.append({
                    "symbol": collection,
                    "direction": "LONG",
                    "entry": floor,
                    "tp": tp,
                    "sl": sl,
                    "size": 0.01,
                    "reason": f"NFT momentum breakout for {collection} "
                              f"(floor={floor:.0f}, vol={volume}, mom={momentum:.2f})"
                })
        return signals
