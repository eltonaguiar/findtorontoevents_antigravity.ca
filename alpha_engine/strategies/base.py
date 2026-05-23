"""
Base Strategy Class

All strategies inherit from this. Defines the contract for signal generation,
position sizing, and metadata.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import numpy as np
import pandas as pd


class StrategyType(Enum):
    LONG_ONLY = "long_only"
    LONG_SHORT = "long_short"
    MARKET_NEUTRAL = "market_neutral"
    SECTOR_NEUTRAL = "sector_neutral"


class HoldingPeriod(Enum):
    INTRADAY = 1
    SHORT_TERM = 5       # 1 week
    SWING = 21           # 1 month
    MEDIUM = 63          # 3 months
    LONG = 126           # 6 months
    BUY_AND_HOLD = 252   # 1 year


@dataclass
class StrategyConfig:
    """Configuration for a strategy."""
    name: str
    description: str
    strategy_type: StrategyType = StrategyType.LONG_ONLY
    holding_period: HoldingPeriod = HoldingPeriod.SWING
    max_positions: int = 20
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly
    min_score: float = 0.0
    top_k: int = 10
    # Risk params
    max_position_pct: float = 0.05
    max_sector_pct: float = 0.25
    stop_loss_pct: float = 0.10
    take_profit_pct: float = 0.50
    # Tags for classification
    tags: List[str] = field(default_factory=list)


@dataclass
class Signal:
    """A trading signal for a single ticker on a date."""
    ticker: str
    date: pd.Timestamp
    score: float           # Composite score [-1, 1] or [0, 1]
    direction: int         # 1 = long, -1 = short, 0 = flat
    confidence: float      # [0, 1]
    holding_period: int    # Expected days
    drivers: Dict[str, float] = field(default_factory=dict)  # Why this signal
    category: str = ""     # e.g. "momentum", "value", "safe_bet"


class BaseStrategy(ABC):
    """
    Abstract base for all strategies.
    
    Subclasses must implement:
    - generate_signals(): produce ranked signals for each date
    - get_config(): return strategy configuration
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or self._default_config()

    @abstractmethod
    def _default_config(self) -> StrategyConfig:
        """Return default configuration for this strategy."""
        pass

    @abstractmethod
    def generate_signals(
        self,
        features: pd.DataFrame,
        date: pd.Timestamp,
        universe: List[str],
    ) -> List[Signal]:
        """
        Generate trading signals for a given date.
        
        Args:
            features: Feature matrix (may be multi-index or wide)
            date: Current date
            universe: List of tradeable tickers
            
        Returns:
            List of Signal objects, sorted by score (best first)
        """
        pass

    def generate_signals_bulk(
        self,
        features: pd.DataFrame,
        dates: pd.DatetimeIndex,
        universe: List[str],
    ) -> pd.DataFrame:
        """
        Generate signals for multiple dates (vectorized when possible).
        
        Returns DataFrame: (date, ticker) -> score, direction, confidence
        """
        all_signals = []
        for date in dates:
            try:
                signals = self.generate_signals(features, date, universe)
                for s in signals:
                    all_signals.append({
                        "date": s.date,
                        "ticker": s.ticker,
                        "score": s.score,
                        "direction": s.direction,
                        "confidence": s.confidence,
                        "holding_period": s.holding_period,
                        "category": s.category,
                        "strategy": self.config.name,
                    })
            except Exception:
                continue

        if not all_signals:
            return pd.DataFrame()

        df = pd.DataFrame(all_signals)
        return df

    def get_config(self) -> StrategyConfig:
        return self.config

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.config.name})"
