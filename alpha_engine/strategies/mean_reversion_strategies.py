"""
Mean Reversion Strategies

Counter-trend strategies that buy oversold / sell overbought conditions.
Best in range-bound and high-volatility regimes.
"""
from typing import List
import numpy as np
import pandas as pd
from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal


class BollingerMeanReversionStrategy(BaseStrategy):
    """
    Mean reversion using Bollinger Bands: buy when price is below lower band,
    sell when above upper band.
    
    Edge source: Behavioral overreaction + statistical mean reversion.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="bollinger_mean_reversion",
            description="Buy oversold (below lower BB), sell overbought (above upper BB)",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SHORT_TERM,
            max_positions=10,
            top_k=10,
            rebalance_frequency="daily",
            stop_loss_pct=0.05,
            take_profit_pct=0.08,
            tags=["mean_reversion", "bollinger"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        bb_zscore = self._get_feature(features, date, "mr_bb_zscore_20d", universe)
        hurst = self._get_feature(features, date, "mr_hurst_63d", universe)

        if bb_zscore is None:
            return signals

        for ticker in universe:
            try:
                z = bb_zscore.get(ticker, 0)
                h = hurst.get(ticker, 0.5) if hurst is not None else 0.5

                # Only trade mean reverting stocks (Hurst < 0.5)
                if h > 0.55:
                    continue

                # Buy when deeply oversold (z < -2)
                if z < -1.5:
                    score = min(abs(z) / 3, 1.0)
                    # Boost score if Hurst confirms mean reversion
                    if h < 0.4:
                        score *= 1.2

                    signals.append(Signal(
                        ticker=ticker, date=date, score=min(score, 1.0),
                        direction=1, confidence=min(score * 0.7, 0.8),
                        holding_period=self.config.holding_period.value,
                        drivers={"bb_zscore": float(z), "hurst": float(h)},
                        category="mean_reversion",
                    ))
            except Exception:
                continue

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex) and date in features.index.get_level_values(0):
                return features.loc[date].get(col)
        except Exception:
            pass
        return None


class ShortTermReversalStrategy(BaseStrategy):
    """
    Short-term reversal: buy recent losers, sell recent winners.
    Works at 1-5 day horizons. One of the oldest documented anomalies.
    
    Edge source: Overreaction + liquidity provision.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="short_term_reversal",
            description="Buy 5-day losers (oversold bounce), hold 3-5 days",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.INTRADAY,
            max_positions=10,
            top_k=10,
            rebalance_frequency="daily",
            stop_loss_pct=0.03,
            take_profit_pct=0.05,
            tags=["mean_reversion", "reversal", "short_term"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        reversal_5d = self._get_feature(features, date, "mr_reversal_5d", universe)
        vol_shock = self._get_feature(features, date, "vlm_vol_shock", universe)

        if reversal_5d is None:
            return signals

        # Sort by reversal signal (most oversold first)
        ranked = reversal_5d.dropna().sort_values(ascending=False)
        top = ranked.head(self.config.top_k * 2)  # Wider pool, then filter

        for ticker, rev_score in top.items():
            if ticker not in universe:
                continue
            if rev_score < 0.02:  # Must have meaningful 5d decline
                continue

            # Boost if volume spike (capitulation selling)
            vshock = vol_shock.get(ticker, 0) if vol_shock is not None else 0
            score = min(rev_score * 5, 0.8)
            if vshock > 2:
                score *= 1.2

            signals.append(Signal(
                ticker=ticker, date=date, score=min(score, 1.0),
                direction=1, confidence=min(score * 0.6, 0.7),
                holding_period=3,
                drivers={"reversal_5d": float(rev_score), "vol_shock": float(vshock)},
                category="reversal",
            ))

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex) and date in features.index.get_level_values(0):
                return features.loc[date].get(col)
        except Exception:
            pass
        return None
