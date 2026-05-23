"""
Momentum Strategies

Multiple variants of trend-following and momentum strategies:
- Classic momentum (buy past winners)
- Trend following (buy stocks in uptrend)
- Breakout momentum (buy new highs with volume)
- Momentum + quality filter
"""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal


class ClassicMomentumStrategy(BaseStrategy):
    """
    Classic cross-sectional momentum: buy top-K past winners.
    
    Edge source: Behavioral (herding, underreaction to information).
    Historically 5-15% annual alpha before costs.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="classic_momentum",
            description="Buy top-K stocks by 6-month return, skip most recent month",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SWING,
            max_positions=20,
            top_k=20,
            rebalance_frequency="monthly",
            tags=["momentum", "cross-sectional"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        # Use 6-month return, skip most recent month (Jegadeesh & Titman style)
        # The "skip month" avoids short-term reversal contamination
        ret_126 = self._get_feature(features, date, "mom_ret_126d", universe)
        ret_21 = self._get_feature(features, date, "mom_ret_21d", universe)

        if ret_126 is None:
            return signals

        # Momentum = 6m return - 1m return (skip-month momentum)
        momentum = ret_126.copy()
        if ret_21 is not None:
            momentum = ret_126 - ret_21

        # Rank and pick top-K
        ranked = momentum.dropna().sort_values(ascending=False)
        top_k = ranked.head(self.config.top_k)

        for ticker, score in top_k.items():
            if ticker not in universe:
                continue
            # Normalize score to [0, 1]
            if len(ranked) > 1:
                norm_score = (score - ranked.min()) / (ranked.max() - ranked.min() + 1e-10)
            else:
                norm_score = 0.5

            signals.append(Signal(
                ticker=ticker,
                date=date,
                score=norm_score,
                direction=1,
                confidence=min(norm_score, 0.9),
                holding_period=self.config.holding_period.value,
                drivers={"6m_return": float(ret_126.get(ticker, 0)),
                         "1m_return": float(ret_21.get(ticker, 0)) if ret_21 is not None else 0},
                category="momentum",
            ))

        return sorted(signals, key=lambda s: s.score, reverse=True)

    def _get_feature(self, features, date, col, universe):
        """Extract a feature for a date across universe."""
        try:
            if isinstance(features.index, pd.MultiIndex):
                if date in features.index.get_level_values(0):
                    row = features.loc[date]
                    if col in row.columns:
                        return row[col]
            else:
                if date in features.index and col in features.columns:
                    return features.loc[date, col]
        except Exception:
            pass
        return None


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend following: buy stocks above key moving averages with strong trend.
    
    Edge source: Behavioral (anchoring, slow information diffusion).
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="trend_following",
            description="Buy stocks above 50/200 MA with strong trend strength",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SWING,
            max_positions=15,
            top_k=15,
            rebalance_frequency="weekly",
            tags=["momentum", "trend"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        # Get trend indicators
        above_50 = self._get_feature(features, date, "mom_price_vs_ma50", universe)
        above_200 = self._get_feature(features, date, "mom_price_vs_ma200", universe)
        trend_str = self._get_feature(features, date, "mom_trend_strength_21d", universe)

        if above_50 is None or above_200 is None:
            return signals

        for ticker in universe:
            try:
                a50 = above_50.get(ticker, -1)
                a200 = above_200.get(ticker, -1)
                ts = trend_str.get(ticker, 0) if trend_str is not None else 0

                # Must be above both MAs
                if a50 <= 0 or a200 <= 0:
                    continue

                # Score based on trend strength and MA distances
                score = 0.3 * min(a50, 0.3) / 0.3 + 0.3 * min(a200, 0.3) / 0.3 + 0.4 * max(min(ts, 2), 0) / 2

                if score > 0.3:
                    signals.append(Signal(
                        ticker=ticker, date=date, score=score,
                        direction=1, confidence=min(score, 0.85),
                        holding_period=self.config.holding_period.value,
                        drivers={"above_ma50": float(a50), "above_ma200": float(a200), "trend_strength": float(ts)},
                        category="trend",
                    ))
            except Exception:
                continue

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex):
                if date in features.index.get_level_values(0):
                    row = features.loc[date]
                    if col in row.columns:
                        return row[col]
            elif col in features.columns:
                return features.loc[date] if date in features.index else None
        except Exception:
            pass
        return None


class BreakoutMomentumStrategy(BaseStrategy):
    """
    Breakout momentum: buy stocks making new 52-week highs with volume.
    
    Edge source: Attention + anchoring bias.
    """

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="breakout_momentum",
            description="Buy stocks near 52-week highs with volume confirmation",
            strategy_type=StrategyType.LONG_ONLY,
            holding_period=HoldingPeriod.SHORT_TERM,
            max_positions=10,
            top_k=10,
            rebalance_frequency="weekly",
            tags=["momentum", "breakout"],
        )

    def generate_signals(self, features: pd.DataFrame, date: pd.Timestamp, universe: List[str]) -> List[Signal]:
        signals = []

        dist_high = self._get_feature(features, date, "mom_dist_from_252d_high", universe)
        vol_ratio = self._get_feature(features, date, "vlm_vol_ratio_20d", universe)

        if dist_high is None:
            return signals

        for ticker in universe:
            try:
                dh = dist_high.get(ticker, -1)
                vr = vol_ratio.get(ticker, 1) if vol_ratio is not None else 1

                # Within 5% of 52-week high
                if dh < -0.05:
                    continue

                # Volume confirmation: above average
                if vr < 1.0:
                    continue

                score = (1 + dh) * 0.5 + min(vr / 3, 0.5)

                if score > 0.3:
                    signals.append(Signal(
                        ticker=ticker, date=date, score=min(score, 1.0),
                        direction=1, confidence=min(score * 0.8, 0.85),
                        holding_period=self.config.holding_period.value,
                        drivers={"dist_from_high": float(dh), "volume_ratio": float(vr)},
                        category="breakout",
                    ))
            except Exception:
                continue

        return sorted(signals, key=lambda s: s.score, reverse=True)[:self.config.top_k]

    def _get_feature(self, features, date, col, universe):
        try:
            if isinstance(features.index, pd.MultiIndex) and date in features.index.get_level_values(0):
                row = features.loc[date]
                if col in row.columns:
                    return row[col]
        except Exception:
            pass
        return None
