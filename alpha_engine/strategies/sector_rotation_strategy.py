"""
Sector Rotation Strategy
A macro-driven strategy that rotates exposure across sectors based on regime signals.
"""

from typing import List
import numpy as np
import pandas as pd
from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal


class SectorRotationStrategy(BaseStrategy):
    """
    Strategy that uses macro regime classification to determine which sectors to overweight.
    It then selects top stocks within those sectors based on momentum score.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="sector_rotation",
            description="Macro regime-based sector rotation with momentum selection",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SWING,
            max_positions=20,
            top_k=20,
            rebalance_frequency="weekly",
            tags=["sector", "macro", "rotation"],
            # Risk params
            max_position_pct=0.05,
            max_sector_pct=0.25,
            stop_loss_pct=0.10,
            take_profit_pct=0.50,
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        """
        Generate signals based on macro regime and sector momentum.
        """
        signals = []

        # Get macro regime (e.g., risk_on, risk_off, etc.)
        # Assume there is a feature 'macro_regime' that returns a regime label
        regime = self._get_feature(features, date, "macro_regime", universe)
        if regime is None:
            return signals

        # Define sector mapping based on regime
        # This is a simple example mapping; can be expanded
        regime_to_sectors = {
            "risk_on": ["technology", "consumer_cyclical", "industrial"],
            "risk_off": ["utilities", "healthcare", "consumer_defensive"],
            "neutral": ["financials", "energy", "basic_materials"],
        }

        # Get sector information for tickers (assume feature 'sector' exists)
        sector = self._get_feature(features, date, "sector", universe)
        if sector is None:
            return signals

        # Get momentum score (e.g., 6m return) for ranking
        mom_ret = self._get_feature(features, date, "mom_ret_126d", universe)

        # Iterate through universe and select stocks in favorable sectors
        if regime in regime_to_sectors:
            target_sectors = set(regime_to_sectors[regime])
        else:
            target_sectors = set()

        # Collect signals for stocks in target sectors
        for ticker in universe:
            try:
                ticker_sector = sector.get(ticker)
                if ticker_sector not in target_sectors:
                    continue

                # Get momentum score
                if mom_ret is not None and ticker in mom_ret:
                    momentum = mom_ret[ticker]
                else:
                    momentum = 0.0

                # Skip if momentum is non-positive (only want positive momentum)
                if momentum <= 0:
                    continue

                # Generate score based on momentum (normalize)
                # Use a simple normalization
                score = min(momentum / 0.2, 1.0)  # assuming returns are in decimal

                # Create signal
                signals.append(
                    Signal(
                        ticker=ticker,
                        date=date,
                        score=score,
                        direction=1,
                        confidence=min(score * 0.8, 0.85),
                        holding_period=self.config.holding_period.value,
                        drivers={
                            "momentum_126d": float(momentum),
                            "sector": ticker_sector,
                            "regime": regime,
                        },
                        category="sector_rotation",
                    )
                )
            except Exception:
                continue

        # Sort signals by score descending
        return sorted(signals, key=lambda s: s.score, reverse=True)[: self.config.top_k]