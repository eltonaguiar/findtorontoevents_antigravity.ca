"""
Meta-Learner / Strategy Arbitrator

The "God-Mode" meta-ensemble: an AI agent that monitors all strategies
and decides which to trust based on current market conditions.

This is the StrategyArbitrator class from the spec.
"""
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .regime_allocator import RegimeAllocator
from .signal_combiner import SignalCombiner

logger = logging.getLogger(__name__)


class MetaLearner:
    """
    Meta-learner that orchestrates multi-strategy allocation.
    
    Architecture:
    1. Input Layer: technicals + fundamentals from all strategies
    2. Sentiment/News Layer: sentiment velocity scoring
    3. Regime Layer: macro regime classification
    4. Arbitrator: combines all signals with regime-aware weighting
    5. Risk Layer: Kelly criterion + position limits
    
    The arbitrator decides:
    - Which strategies to listen to right now
    - How much weight each strategy gets
    - Overall risk exposure level
    """

    def __init__(self):
        self.regime_allocator = RegimeAllocator()
        self.signal_combiner = SignalCombiner(method="performance_weighted")
        self._strategy_track_record: Dict[str, List[float]] = {}

    def generate_picks(
        self,
        strategy_signals: Dict[str, pd.DataFrame],
        macro_data: Dict,
        insider_data: Optional[pd.DataFrame] = None,
        sentiment_data: Optional[pd.DataFrame] = None,
        earnings_data: Optional[pd.DataFrame] = None,
        top_k: int = 20,
    ) -> pd.DataFrame:
        """
        The master pick generation function.
        
        Takes signals from ALL strategies + alternative data,
        applies regime-aware weighting, and produces final picks.
        
        Args:
            strategy_signals: Dict of strategy_name -> signals DataFrame
            macro_data: Current macro regime data
            insider_data: Insider cluster buy data
            sentiment_data: Sentiment scores
            earnings_data: Earnings beat data
            top_k: Number of picks to output
            
        Returns:
            DataFrame with final picks, scores, conviction, and rationale
        """
        # Step 1: Classify regime and get strategy weights
        regime_scores = self.regime_allocator.classify_regime(macro_data)
        dominant_regime = max(regime_scores, key=regime_scores.get)
        strategy_weights = self.regime_allocator.compute_blended_weights(regime_scores)

        # Apply DXY filter
        dxy_dist = macro_data.get("dxy_sma50_dist", 0)
        if isinstance(dxy_dist, (int, float)):
            strategy_weights = self.regime_allocator.apply_dxy_filter(strategy_weights, dxy_dist)

        logger.info(f"Regime: {dominant_regime} ({regime_scores[dominant_regime]:.1%})")
        logger.info(f"Strategy weights: {strategy_weights}")

        # Step 2: Map strategy signals to weight categories
        weighted_signals = self._map_strategy_weights(strategy_signals, strategy_weights)

        # Step 3: Combine signals
        combined = self.signal_combiner.combine(weighted_signals, strategy_weights)

        if combined.empty:
            return pd.DataFrame()

        # Step 4: Apply alternative data multipliers
        combined = self._apply_insider_multiplier(combined, insider_data)
        combined = self._apply_sentiment_filter(combined, sentiment_data)
        combined = self._apply_earnings_boost(combined, earnings_data)

        # Step 5: Apply "do not trade" filters
        combined = self._apply_do_not_trade_filters(combined, macro_data)

        # Step 6: Final ranking and selection
        combined = combined.sort_values("score", ascending=False).head(top_k)
        combined["rank"] = range(1, len(combined) + 1)
        combined["regime"] = dominant_regime

        # Add conviction level
        combined["conviction"] = combined["score"].apply(self._score_to_conviction)

        # Add expected horizon
        combined["expected_horizon"] = combined.apply(
            lambda row: self._estimate_horizon(row, dominant_regime), axis=1
        )

        return combined

    def _map_strategy_weights(
        self,
        strategy_signals: Dict[str, pd.DataFrame],
        strategy_weights: Dict[str, float],
    ) -> Dict[str, pd.DataFrame]:
        """Map strategy names to weight categories."""
        # Mapping from strategy config tags to allocator categories
        tag_to_category = {
            "momentum": "momentum",
            "trend": "trend",
            "breakout": "breakout",
            "mean_reversion": "mean_reversion",
            "earnings": "earnings_drift",
            "pead": "earnings_drift",
            "quality": "quality",
            "value": "value",
            "dividend": "dividend",
            "ml": "ml",
        }

        mapped = {}
        for strat_name, signals_df in strategy_signals.items():
            # Find best matching category
            best_category = "ml"  # Default
            for tag, category in tag_to_category.items():
                if tag in strat_name.lower():
                    best_category = category
                    break
            mapped[best_category] = signals_df

        return mapped

    def _apply_insider_multiplier(
        self,
        picks: pd.DataFrame,
        insider_data: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Apply insider cluster buy multiplier.
        If 3+ insiders bought in last 14 days → 1.5x score boost.
        """
        if insider_data is None or insider_data.empty or "ticker" not in picks.columns:
            return picks

        for idx, row in picks.iterrows():
            ticker = row["ticker"]
            if ticker in insider_data.index:
                insider_row = insider_data.loc[ticker]
                if insider_row.get("is_cluster_buy", False):
                    picks.at[idx, "score"] = min(row["score"] * 1.5, 1.0)
                    picks.at[idx, "confidence"] = min(row.get("confidence", 0.5) * 1.3, 0.99)
                    existing = row.get("contributing_strategies", "")
                    picks.at[idx, "contributing_strategies"] = f"{existing}, INSIDER_CLUSTER_BUY"

        return picks

    def _apply_sentiment_filter(
        self,
        picks: pd.DataFrame,
        sentiment_data: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Apply sentiment velocity filter.
        Positive sentiment velocity → boost. Negative → reduce.
        High-momentum picks MUST be confirmed by positive sentiment.
        """
        if sentiment_data is None or sentiment_data.empty or "ticker" not in picks.columns:
            return picks

        for idx, row in picks.iterrows():
            ticker = row["ticker"]
            if ticker in sentiment_data.index:
                sent = sentiment_data.loc[ticker]
                velocity = sent.get("sentiment_velocity", 0)

                if velocity > 0.2:
                    picks.at[idx, "score"] = min(row["score"] * 1.2, 1.0)
                elif velocity < -0.3:
                    # Negative sentiment → penalize momentum picks
                    if "momentum" in str(row.get("contributing_strategies", "")):
                        picks.at[idx, "score"] = row["score"] * 0.7

        return picks

    def _apply_earnings_boost(
        self,
        picks: pd.DataFrame,
        earnings_data: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Apply earnings beat boost.
        3+ consecutive beats of 5%+ → "Safe Bet" flag + score boost.
        """
        if earnings_data is None or earnings_data.empty or "ticker" not in picks.columns:
            return picks

        for idx, row in picks.iterrows():
            ticker = row["ticker"]
            if ticker in earnings_data.index:
                earn = earnings_data.loc[ticker]
                if earn.get("is_safe_bet", False):
                    picks.at[idx, "score"] = min(row["score"] * 1.3, 1.0)
                    picks.at[idx, "category"] = "safe_bet"

        return picks

    def _apply_do_not_trade_filters(self, picks: pd.DataFrame, macro_data: Dict) -> pd.DataFrame:
        """
        Remove picks that should NOT be traded:
        - Illiquid stocks (dollar volume too low)
        - Earnings within 3 days (unless earnings strategy)
        - Excessive spread proxy
        """
        # In a full implementation, we'd check:
        # 1. Dollar volume floor
        # 2. Upcoming earnings calendar
        # 3. Spread width estimates
        # For now, return as-is (filters applied in universe manager)
        return picks

    def _score_to_conviction(self, score: float) -> str:
        """Convert numeric score to conviction level."""
        if score >= 0.8:
            return "STRONG BUY"
        elif score >= 0.6:
            return "BUY"
        elif score >= 0.4:
            return "MODERATE BUY"
        elif score >= 0.2:
            return "WEAK BUY"
        else:
            return "WATCH"

    def _estimate_horizon(self, row, regime: str) -> str:
        """Estimate expected holding period based on signal and regime."""
        category = row.get("category", "")
        if category in ["safe_bet", "dividend_aristocrat", "quality"]:
            return "6-12 months"
        elif category in ["earnings_drift"]:
            return "6-8 weeks"
        elif regime in ["risk_off", "crisis"]:
            return "1-3 months (defensive)"
        elif category in ["momentum", "breakout"]:
            return "1-4 weeks"
        elif category in ["mean_reversion", "reversal"]:
            return "3-5 days"
        return "1-4 weeks"

    def generate_watchlist(
        self,
        all_signals: pd.DataFrame,
        top_k: int = 10,
    ) -> pd.DataFrame:
        """Generate watchlist: stocks that are close to triggering but not yet."""
        if all_signals.empty:
            return pd.DataFrame()

        # Watchlist = stocks scoring 0.3-0.5 (almost good enough)
        watch = all_signals[
            (all_signals["score"] >= 0.3) & (all_signals["score"] < 0.5)
        ].head(top_k)
        watch["status"] = "WATCHLIST"
        watch["reason"] = "Score approaching buy threshold"
        return watch

    def generate_avoid_list(
        self,
        all_signals: pd.DataFrame,
        earnings_upcoming: List[str] = None,
    ) -> pd.DataFrame:
        """Generate avoid list: stocks that should NOT be bought."""
        avoid = []

        # Stocks with negative scores
        if not all_signals.empty:
            negative = all_signals[all_signals["score"] < 0]
            for _, row in negative.iterrows():
                avoid.append({
                    "ticker": row["ticker"],
                    "reason": "Negative composite score",
                    "score": row["score"],
                })

        # Stocks with upcoming earnings (unless earnings strategy)
        if earnings_upcoming:
            for ticker in earnings_upcoming:
                avoid.append({
                    "ticker": ticker,
                    "reason": "Earnings within 3 days",
                    "score": None,
                })

        return pd.DataFrame(avoid) if avoid else pd.DataFrame(columns=["ticker", "reason", "score"])

    def get_allocation_report(self) -> str:
        """Get human-readable allocation report."""
        return self.regime_allocator.get_allocation_summary()
