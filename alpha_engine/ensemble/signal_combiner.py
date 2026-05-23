"""
Signal Combiner

Combines signals from multiple strategies into a unified ranking.
Methods: simple average, weighted average, rank aggregation, stacking.
"""
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SignalCombiner:
    """
    Combine signals from multiple strategies.
    
    Methods:
    - equal_weight: simple average of all strategy scores
    - performance_weighted: weight by recent performance
    - rank_average: average of cross-sectional ranks
    - stacking: ML model combines strategy signals
    - diversity_weighted: boost strategies with low correlation to others
    """

    def __init__(self, method: str = "performance_weighted"):
        self.method = method
        self._strategy_performance: Dict[str, float] = {}

    def combine(
        self,
        strategy_signals: Dict[str, pd.DataFrame],
        weights: Dict[str, float] = None,
    ) -> pd.DataFrame:
        """
        Combine signals from multiple strategies.
        
        Args:
            strategy_signals: Dict of strategy_name -> DataFrame with 
                            columns [ticker, score, direction, confidence]
            weights: Optional strategy weights (from RegimeAllocator)
            
        Returns:
            Combined DataFrame with composite scores
        """
        if not strategy_signals:
            return pd.DataFrame()

        if self.method == "equal_weight":
            return self._equal_weight_combine(strategy_signals)
        elif self.method == "performance_weighted":
            return self._performance_weighted_combine(strategy_signals, weights)
        elif self.method == "rank_average":
            return self._rank_average_combine(strategy_signals)
        else:
            return self._performance_weighted_combine(strategy_signals, weights)

    def _equal_weight_combine(self, signals: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Simple average of all strategy scores."""
        all_tickers = set()
        for df in signals.values():
            if "ticker" in df.columns:
                all_tickers.update(df["ticker"].tolist())

        combined = {}
        for ticker in all_tickers:
            scores = []
            directions = []
            confidences = []
            drivers = {}

            for strat_name, df in signals.items():
                ticker_rows = df[df["ticker"] == ticker] if "ticker" in df.columns else pd.DataFrame()
                if not ticker_rows.empty:
                    row = ticker_rows.iloc[0]
                    scores.append(row.get("score", 0))
                    directions.append(row.get("direction", 1))
                    confidences.append(row.get("confidence", 0.5))
                    drivers[strat_name] = row.get("score", 0)

            if scores:
                combined[ticker] = {
                    "ticker": ticker,
                    "score": np.mean(scores),
                    "direction": int(np.sign(np.mean(directions))),
                    "confidence": np.mean(confidences),
                    "n_strategies": len(scores),
                    "strategy_agreement": np.std(directions) == 0,
                    "drivers": str(drivers),
                }

        result = pd.DataFrame(combined.values())
        if not result.empty:
            result = result.sort_values("score", ascending=False)
        return result

    def _performance_weighted_combine(
        self,
        signals: Dict[str, pd.DataFrame],
        weights: Dict[str, float] = None,
    ) -> pd.DataFrame:
        """Weight strategies by their recent performance + regime weights."""
        if weights is None:
            weights = {name: 1.0 / len(signals) for name in signals}

        # Normalize weights
        total_w = sum(weights.get(name, 0) for name in signals)
        if total_w <= 0:
            total_w = 1

        all_tickers = set()
        for df in signals.values():
            if "ticker" in df.columns:
                all_tickers.update(df["ticker"].tolist())

        combined = {}
        for ticker in all_tickers:
            weighted_score = 0
            weighted_confidence = 0
            weighted_direction = 0
            total_weight = 0
            n_strats = 0
            contributing = []

            for strat_name, df in signals.items():
                w = weights.get(strat_name, 0) / total_w
                ticker_rows = df[df["ticker"] == ticker] if "ticker" in df.columns else pd.DataFrame()
                if not ticker_rows.empty:
                    row = ticker_rows.iloc[0]
                    s = row.get("score", 0)
                    weighted_score += s * w
                    weighted_confidence += row.get("confidence", 0.5) * w
                    weighted_direction += row.get("direction", 1) * w
                    total_weight += w
                    n_strats += 1
                    contributing.append(f"{strat_name}({s:.2f})")

            if total_weight > 0:
                combined[ticker] = {
                    "ticker": ticker,
                    "score": weighted_score / total_weight,
                    "direction": int(np.sign(weighted_direction)),
                    "confidence": weighted_confidence / total_weight,
                    "n_strategies": n_strats,
                    "contributing_strategies": ", ".join(contributing),
                }

        result = pd.DataFrame(combined.values())
        if not result.empty:
            result = result.sort_values("score", ascending=False)
        return result

    def _rank_average_combine(self, signals: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Average of cross-sectional ranks (more robust to outliers)."""
        all_tickers = set()
        for df in signals.values():
            if "ticker" in df.columns:
                all_tickers.update(df["ticker"].tolist())

        ticker_ranks = {t: [] for t in all_tickers}

        for strat_name, df in signals.items():
            if "ticker" not in df.columns or "score" not in df.columns:
                continue
            ranked = df.set_index("ticker")["score"].rank(pct=True, ascending=True)
            for ticker in all_tickers:
                if ticker in ranked.index:
                    ticker_ranks[ticker].append(ranked[ticker])

        combined = {}
        for ticker, ranks in ticker_ranks.items():
            if ranks:
                combined[ticker] = {
                    "ticker": ticker,
                    "score": np.mean(ranks),
                    "direction": 1,
                    "confidence": np.mean(ranks),
                    "n_strategies": len(ranks),
                }

        result = pd.DataFrame(combined.values())
        if not result.empty:
            result = result.sort_values("score", ascending=False)
        return result

    def update_strategy_performance(self, strategy_name: str, recent_sharpe: float):
        """Update tracked performance for adaptive weighting."""
        self._strategy_performance[strategy_name] = recent_sharpe

    def compute_strategy_diversity(
        self,
        strategy_returns: Dict[str, pd.Series],
    ) -> pd.DataFrame:
        """
        Compute correlation matrix between strategy returns.
        Low correlation = high diversification value.
        """
        df = pd.DataFrame(strategy_returns)
        return df.corr()
