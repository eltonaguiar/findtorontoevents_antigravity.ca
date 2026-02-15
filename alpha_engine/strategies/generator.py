"""
Strategy Generator

Creates and manages all strategy candidates across the search space.
Implements the "Strategy Generator" from the God-Mode spec.
"""
import logging
from typing import Dict, List, Optional

import pandas as pd

from .base import BaseStrategy, StrategyConfig
from .momentum_strategies import ClassicMomentumStrategy, TrendFollowingStrategy, BreakoutMomentumStrategy
from .mean_reversion_strategies import BollingerMeanReversionStrategy, ShortTermReversalStrategy
from .earnings_drift import EarningsDriftStrategy, ConsecutiveBeatsStrategy
from .quality_value import QualityCompoundersStrategy, ValueQualityStrategy, DividendAristocratsStrategy
from .ml_ranker import MLRankerStrategy
from .sector_rotation_strategy import SectorRotationStrategy

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """
    Generate and manage strategy candidates.
    
    Provides:
    - Pre-built strategies across all styles
    - Strategy candidate generation for systematic testing
    - Strategy registry for ensemble selection
    """

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register all built-in strategies."""
        defaults = [
            # Momentum family
            ClassicMomentumStrategy(),
            TrendFollowingStrategy(),
            BreakoutMomentumStrategy(),
            # Mean reversion family
            BollingerMeanReversionStrategy(),
            ShortTermReversalStrategy(),
            # Earnings family
            EarningsDriftStrategy(),
            ConsecutiveBeatsStrategy(),
            # Quality/Value family
            QualityCompoundersStrategy(),
            ValueQualityStrategy(),
            DividendAristocratsStrategy(),
            # ML
            MLRankerStrategy(model_type="lightgbm"),
        ]

        for strategy in defaults:
            self.register(strategy)

    def register(self, strategy: BaseStrategy):
        """Register a strategy."""
        name = strategy.config.name
        self.strategies[name] = strategy
        logger.debug(f"Registered strategy: {name}")

    def get(self, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name."""
        return self.strategies.get(name)

    def get_all(self) -> Dict[str, BaseStrategy]:
        """Get all registered strategies."""
        return self.strategies.copy()

    def get_by_tag(self, tag: str) -> List[BaseStrategy]:
        """Get strategies by tag."""
        return [s for s in self.strategies.values() if tag in s.config.tags]

    def get_by_type(self, strategy_type: str) -> List[BaseStrategy]:
        """Get strategies by type (momentum, value, quality, etc.)."""
        return self.get_by_tag(strategy_type)

    def list_strategies(self) -> pd.DataFrame:
        """List all strategies with their configs."""
        rows = []
        for name, strategy in self.strategies.items():
            cfg = strategy.config
            rows.append({
                "name": name,
                "description": cfg.description,
                "type": cfg.strategy_type.value,
                "holding_period": cfg.holding_period.value,
                "max_positions": cfg.max_positions,
                "top_k": cfg.top_k,
                "rebalance": cfg.rebalance_frequency,
                "tags": ", ".join(cfg.tags),
            })
        return pd.DataFrame(rows).set_index("name")

    def generate_candidates(
        self,
        styles: List[str] = None,
        holding_periods: List[int] = None,
        top_k_values: List[int] = None,
    ) -> List[BaseStrategy]:
        """
        Generate strategy candidates by varying parameters across the search space.
        
        This creates variations of each base strategy with different parameters
        for systematic testing.
        """
        if styles is None:
            styles = ["momentum", "mean_reversion", "earnings", "quality", "value"]
        if holding_periods is None:
            holding_periods = [5, 21, 63]
        if top_k_values is None:
            top_k_values = [10, 20]

        candidates = []

        # Classic momentum variations
        if "momentum" in styles:
            for hp in holding_periods:
                for k in top_k_values:
                    cfg = StrategyConfig(
                        name=f"momentum_hp{hp}_k{k}",
                        description=f"Classic momentum, hold {hp}d, top {k}",
                        top_k=k,
                        max_positions=k,
                        tags=["momentum", "candidate"],
                    )
                    candidates.append(ClassicMomentumStrategy(config=cfg))

        # Trend following variations
        if "momentum" in styles:
            for hp in [21, 63]:
                cfg = StrategyConfig(
                    name=f"trend_following_hp{hp}",
                    description=f"Trend following, hold {hp}d",
                    top_k=15,
                    max_positions=15,
                    tags=["trend", "candidate"],
                )
                candidates.append(TrendFollowingStrategy(config=cfg))

        # Mean reversion variations
        if "mean_reversion" in styles:
            for hp in [3, 5, 10]:
                cfg = StrategyConfig(
                    name=f"mean_reversion_hp{hp}",
                    description=f"Mean reversion, hold {hp}d",
                    top_k=10,
                    max_positions=10,
                    tags=["mean_reversion", "candidate"],
                )
                candidates.append(BollingerMeanReversionStrategy(config=cfg))

        # Earnings drift variations
        if "earnings" in styles:
            for k in [10, 20]:
                cfg = StrategyConfig(
                    name=f"pead_k{k}",
                    description=f"PEAD strategy, top {k}",
                    top_k=k,
                    max_positions=k,
                    tags=["earnings", "pead", "candidate"],
                )
                candidates.append(EarningsDriftStrategy(config=cfg))

        # Quality variations
        if "quality" in styles:
            for k in [15, 25]:
                cfg = StrategyConfig(
                    name=f"quality_k{k}",
                    description=f"Quality compounders, top {k}",
                    top_k=k,
                    max_positions=k,
                    tags=["quality", "candidate"],
                )
                candidates.append(QualityCompoundersStrategy(config=cfg))

        logger.info(f"Generated {len(candidates)} strategy candidates")
        return candidates

    def get_strategy_sleeves(self) -> Dict[str, List[BaseStrategy]]:
        """
        Organize strategies into portfolio "sleeves" for allocation.
        
        Returns:
            Dict with sleeve names mapping to strategy lists
        """
        return {
            "momentum": self.get_by_tag("momentum"),
            "mean_reversion": self.get_by_tag("mean_reversion"),
            "earnings": self.get_by_tag("earnings"),
            "quality": self.get_by_tag("quality"),
            "value": self.get_by_tag("value"),
            "safe_bet": self.get_by_tag("safe_bet"),
            "ml": self.get_by_tag("ml"),
        }
