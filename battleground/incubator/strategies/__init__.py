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
