# Baby strategy wrapper for the RL adaptive trader
# Provides the same `generate_signals()` API as other baby strategies.
# Handles missing RL model gracefully — returns empty signals.

import logging

logger = logging.getLogger(__name__)


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class RLAdaptiveStrategy:
    """Expose RL PPO signals as a baby strategy.

    If the RL model is not trained yet, returns empty signals.
    """
    def __init__(self, context=None):
        self.scanner = None
        try:
            from rl_agent.production_scanner import RLProductionScanner
            self.scanner = RLProductionScanner(context=context)
        except Exception as e:
            logger.warning("RL scanner unavailable: %s — strategy disabled", e)

    def generate_signals(self):
        if self.scanner is None:
            return []
        try:
            return self.scanner.generate_signals()
        except Exception as e:
            logger.warning("RL signal generation failed: %s", e)
            return []
