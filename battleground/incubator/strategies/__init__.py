# Every strategy module imports its sibling ``api_helpers`` by BARE name
# (``from api_helpers import fetch_klines``) because each one can also be executed
# standalone as a script, where the script's own directory is sys.path[0].
# Under a package import there is no such entry, so the bare import raised
# ModuleNotFoundError: No module named 'api_helpers' and the registry died on the
# very first strategy -- that is what killed baby-strat-forward-paper run 45749409243.
# Registering this directory here fixes all thirteen importers at once and leaves
# standalone execution working exactly as before.
import os as _os
import sys as _sys

_STRATEGY_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _STRATEGY_DIR not in _sys.path:
    _sys.path.insert(0, _STRATEGY_DIR)

from .funding_rate_carry_v1 import FundingRateCarryStrategy
from .chronos_bolt_v1 import ChronosBoltStrategy
from .dlinear_baseline_v1 import DLinearBaselineStrategy
from .gas_urgency_index_v1 import GasUrgencyIndexStrategy
from .liquidity_adjusted_volume_v1 import LiquidityAdjustedVolumeStrategy
from .oi_divergence_liquidation_v1 import OIDivergenceLiquidationStrategy
from .smc_fair_value_gap_v1 import SMCFairValueGapStrategy
from .spike_macd_divergence_v1 import SpikeMacdDivergenceStrategy
from .tournament_ema_momentum_v1 import TournamentEmaMomentumStrategy
from .tournament_macd_rsi_v1 import TournamentMacdRsiStrategy
from .volatility_regime_switch_v1 import VolatilityRegimeSwitchStrategy
from .nadaraya_watson_envelope_v1 import NadarayaWatsonEnvelopeStrategy
from .keltner_compression_generic_v1 import KeltnerCompressionGenericV1

# Registry: name -> class. The runner iterates this dict.
STRATEGY_REGISTRY = {
    "chronos_bolt_v1": ChronosBoltStrategy,
    "dlinear_baseline_v1": DLinearBaselineStrategy,
    "funding_rate_carry_v1": FundingRateCarryStrategy,
    "gas_urgency_index_v1": GasUrgencyIndexStrategy,
    "liquidity_adjusted_volume_v1": LiquidityAdjustedVolumeStrategy,
    "oi_divergence_liquidation_v1": OIDivergenceLiquidationStrategy,
    "smc_fair_value_gap_v1": SMCFairValueGapStrategy,
    "spike_macd_divergence_v1": SpikeMacdDivergenceStrategy,
    "tournament_ema_momentum_v1": TournamentEmaMomentumStrategy,
    "tournament_macd_rsi_v1": TournamentMacdRsiStrategy,
    "volatility_regime_switch_v1": VolatilityRegimeSwitchStrategy,
    "nadaraya_watson_envelope_v1": NadarayaWatsonEnvelopeStrategy,
    "keltner_compression_generic_v1": KeltnerCompressionGenericV1,
}

__all__ = [
    "FundingRateCarryStrategy",
    "ChronosBoltStrategy",
    "DLinearBaselineStrategy",
    "GasUrgencyIndexStrategy",
    "LiquidityAdjustedVolumeStrategy",
    "OIDivergenceLiquidationStrategy",
    "SMCFairValueGapStrategy",
    "SpikeMacdDivergenceStrategy",
    "TournamentEmaMomentumStrategy",
    "TournamentMacdRsiStrategy",
    "VolatilityRegimeSwitchStrategy",
    "NadarayaWatsonEnvelopeStrategy",
    "KeltnerCompressionGenericV1",
    "STRATEGY_REGISTRY",
]
