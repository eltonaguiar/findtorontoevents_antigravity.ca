"""Strategy generators - rules-based, ML, and hybrid strategies."""
from .base import BaseStrategy
from .generator import StrategyGenerator
from .unique_algorithmic_strategies import (
    CryptoVolRegimeAccumulationStrategy,
    EquitySectorDispersionConvergenceStrategy,
    FxCrossPairMomentumStrategy,
    CommodityCurrencyBetaDivergenceStrategy,
    EtfFactorRegimeRotationStrategy,
    BondRealRateMomentumStrategy,
    FuturesCotExtremeStrategy,
)
