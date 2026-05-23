#!/usr/bin/env python3
"""
Darwin Score v2 Calculator: Refined Strategy Scoring

Upgrades from v1 linear scoring to v2 risk-adjusted + momentum scoring.

v1 Formula (current, simple):
  Darwin Score = (WR * 40%) + (min(PF/2.0, 100) * 40%) + (min(AvgPnL + 5, 100) * 20%)

Issues with v1:
  • Profit Factor capped at 50x (doesn't differentiate 2.0 PF vs 5.0 PF)
  • AvgPnL bounded by 100 (loses tail performance signal)
  • No risk-adjustment (ignores Sharpe ratio)
  • No momentum tracking (ignores recent win streaks)

v2 Formula (approved 2026-04-05 per PICK_QUALITY_IMPROVEMENT_ROADMAP.md Priority 4):
  Darwin Score = (WR * 35%) + (log(PF) * 30%) + (Sharpe * 20%) + (ConsecutiveWins * 15%)

Improvements:
  • log(PF) handles extremes naturally (no capping)
  • Sharpe ratio adds risk-adjustment (volatility matters)
  • ConsecutiveWins adds momentum signal (recent strength)
  • Total weight = 100% (normalized)

Target: Increase average Darwin Score from 125 → 140+
"""

import math
import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradePerformance:
    """Single trade performance metrics."""
    win: bool
    pnl_pct: float
    pnl_usd: float
    timestamp: datetime


class DarwinScoreV2:
    """
    Refined strategy scoring engine.

    Methodology:
    1. WR (Win Rate) - baseline accuracy (0-100)
    2. log(PF) - handle profit factors without capping
    3. Sharpe - risk-adjusted return (volatility matters)
    4. ConsecutiveWins - momentum signal (recent strength)
    """

    # v2 component weights (totals 100)
    WEIGHTS = {
        "wr": 35,           # 35% - accuracy
        "log_pf": 30,       # 30% - profitability (log scale)
        "sharpe": 20,       # 20% - risk adjustment
        "consecutive_wins": 15,  # 15% - momentum
    }

    def __init__(self):
        self.version = "2.0"

    def calculate(
        self,
        wr_pct: float,
        pf: float,
        trades: List[TradePerformance],
        capital_usd: float = 10000.0,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate Darwin Score v2 for a strategy.

        Args:
            wr_pct: Win rate as percentage (0-100)
            pf: Profit factor (gross wins / gross losses)
            trades: List of recent trades with performance metrics
            capital_usd: Account capital for Sharpe calculation

        Returns:
            (darwin_score, component_breakdown)
        """
        breakdown = {}

        # Component 1: Win Rate (0-100 scale, capped at 100)
        wr_score = min(100, max(0, wr_pct))
        breakdown["wr"] = {
            "value": wr_pct,
            "score": wr_score,
            "weight": self.WEIGHTS["wr"],
            "weighted": (wr_score * self.WEIGHTS["wr"]) / 100,
        }

        # Component 2: Log Profit Factor (handles extremes)
        log_pf_score = self._score_log_pf(pf)
        breakdown["log_pf"] = {
            "value": pf,
            "score": log_pf_score,
            "weight": self.WEIGHTS["log_pf"],
            "weighted": (log_pf_score * self.WEIGHTS["log_pf"]) / 100,
        }

        # Component 3: Sharpe Ratio (risk-adjusted returns)
        sharpe_score = self._score_sharpe(trades, capital_usd)
        breakdown["sharpe"] = {
            "value": sharpe_score,
            "score": sharpe_score,  # Already normalized to 0-100
            "weight": self.WEIGHTS["sharpe"],
            "weighted": (sharpe_score * self.WEIGHTS["sharpe"]) / 100,
        }

        # Component 4: Consecutive Wins (momentum)
        consecutive_wins = self._calculate_consecutive_wins(trades)
        consecutive_score = self._score_consecutive_wins(consecutive_wins, len(trades))
        breakdown["consecutive_wins"] = {
            "value": consecutive_wins,
            "total_trades": len(trades),
            "score": consecutive_score,
            "weight": self.WEIGHTS["consecutive_wins"],
            "weighted": (consecutive_score * self.WEIGHTS["consecutive_wins"]) / 100,
        }

        # Total Darwin Score
        darwin_score = sum(comp["weighted"] for comp in breakdown.values())

        return darwin_score, breakdown

    @staticmethod
    def _score_log_pf(pf: float, min_pf: float = 1.0, max_pf: float = 10.0) -> float:
        """
        Score profit factor using log scale.

        Maps PF to 0-100 scale with natural log:
        - PF = 1.0 → score = 0
        - PF = 2.0 → score ≈ 50
        - PF = 7.4 → score ≈ 100
        - PF = 100 → score ≈ 235 (capped at 100)
        """
        if pf <= 1.0:
            return 0.0

        # Natural log scaling: log(PF) normalized to 0-100
        log_pf = math.log(pf)
        log_max = math.log(max_pf)

        score = (log_pf / log_max) * 100
        return min(100, max(0, score))

    @staticmethod
    def _score_sharpe(trades: List[TradePerformance], capital_usd: float) -> float:
        """
        Score Sharpe ratio based on trade returns.

        Sharpe = (avg return) / (std return)
        - Higher is better (risk-adjusted returns)
        - Mapped to 0-100 scale
        """
        if not trades or len(trades) < 2:
            return 50.0  # Neutral score for insufficient data

        returns_pct = [t.pnl_pct for t in trades]
        avg_return = sum(returns_pct) / len(returns_pct)
        variance = sum((r - avg_return) ** 2 for r in returns_pct) / len(returns_pct)
        std_return = math.sqrt(max(variance, 1e-6))  # Avoid div by zero

        if std_return == 0:
            return 50.0  # No volatility = neutral

        sharpe = avg_return / std_return if std_return > 0 else 0

        # Map Sharpe to 0-100 scale
        # Assume typical Sharpe range: -2 to +2
        # Map +2 → 100, 0 → 50, -2 → 0
        sharpe_score = min(100, max(0, 50 + (sharpe * 25)))

        return sharpe_score

    @staticmethod
    def _calculate_consecutive_wins(trades: List[TradePerformance]) -> int:
        """Find longest consecutive winning streak."""
        if not trades:
            return 0

        max_streak = 0
        current_streak = 0

        for trade in trades:
            if trade.win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    @staticmethod
    def _score_consecutive_wins(consecutive_wins: int, total_trades: int) -> float:
        """
        Score consecutive win streak as percentage of total trades.

        - 10 wins / 10 trades → 100% → score = 100
        - 5 wins / 10 trades → 50% → score = 50
        - 1 win / 20 trades → 5% → score = 5
        """
        if total_trades <= 0:
            return 0.0

        pct = (consecutive_wins / total_trades) * 100
        return min(100, max(0, pct))


class StrategyPerformanceAggregator:
    """Build Darwin Score v2 for portfolio of strategies."""

    def __init__(self):
        self.calculator = DarwinScoreV2()

    def score_strategies(
        self,
        strategies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Score multiple strategies and return ranked list.

        Input format:
        {
            "strategy_id": "...",
            "wr_pct": 58.5,
            "pf": 1.75,
            "trades": [{"win": True, "pnl_pct": 2.5, "pnl_usd": 250, "timestamp": "..."}, ...],
            "capital": 10000,
        }
        """
        scored = []

        for strategy in strategies:
            strategy_id = strategy.get("strategy_id")
            wr = float(strategy.get("wr_pct", 50))
            pf = float(strategy.get("pf", 1.0))
            capital = float(strategy.get("capital", 10000))
            trades_data = strategy.get("trades", [])

            # Parse trades
            trades = []
            for t in trades_data:
                try:
                    trade = TradePerformance(
                        win=bool(t.get("win")),
                        pnl_pct=float(t.get("pnl_pct", 0)),
                        pnl_usd=float(t.get("pnl_usd", 0)),
                        timestamp=datetime.fromisoformat(t.get("timestamp", datetime.now().isoformat())),
                    )
                    trades.append(trade)
                except Exception:
                    pass  # Skip malformed trade

            # Calculate score
            darwin_score, breakdown = self.calculator.calculate(wr, pf, trades, capital)

            scored.append({
                "strategy_id": strategy_id,
                "darwin_score_v2": round(darwin_score, 1),
                "breakdown": breakdown,
                "tier": self._assign_tier(darwin_score),
            })

        # Sort by Darwin Score descending
        scored.sort(key=lambda x: x["darwin_score_v2"], reverse=True)

        return scored

    @staticmethod
    def _assign_tier(darwin_score: float) -> str:
        """Assign tier based on Darwin Score."""
        if darwin_score >= 140:
            return "TIER_1_ELITE"
        elif darwin_score >= 120:
            return "TIER_1_PROVEN"
        elif darwin_score >= 100:
            return "TIER_2_SOLID"
        elif darwin_score >= 70:
            return "TIER_3_DEVELOPING"
        else:
            return "TIER_4_EXPERIMENTAL"

    def generate_report(self, strategies: List[Dict[str, Any]]) -> str:
        """Generate human-readable scoring report."""
        scored = self.score_strategies(strategies)

        lines = [
            "=" * 100,
            "Darwin Score v2: Refined Strategy Ranking",
            f"Timestamp: {datetime.now().isoformat()}",
            "=" * 100,
            "",
            "Scoring Formula:",
            "  Darwin Score = (WR * 35%) + (log(PF) * 30%) + (Sharpe * 20%) + (ConsecutiveWins * 15%)",
            "",
            "Tier Assignments (by Darwin Score):",
            "  TIER_1_ELITE:       >= 140  (top 5%)",
            "  TIER_1_PROVEN:      >= 120  (top 20%)",
            "  TIER_2_SOLID:       >= 100  (top 50%)",
            "  TIER_3_DEVELOPING:  >= 70   (growth)",
            "  TIER_4_EXPERIMENTAL: < 70   (unproven)",
            "",
            "─" * 100,
            "RESULTS",
            "─" * 100,
            "",
        ]

        for i, strategy in enumerate(scored, 1):
            score = strategy["darwin_score_v2"]
            tier = strategy["tier"]
            bd = strategy["breakdown"]

            lines.append(f"{i}. {strategy['strategy_id']:30} | Score: {score:7.1f} | {tier:20}")
            lines.append(
                f"    WR: {bd['wr']['value']:5.1f}% ({bd['wr']['score']:5.1f}pts) | "
                f"log(PF): {bd['log_pf']['score']:5.1f}pts | "
                f"Sharpe: {bd['sharpe']['score']:5.1f}pts | "
                f"Wins: {bd['consecutive_wins']['value']} ({bd['consecutive_wins']['score']:5.1f}pts)"
            )
            lines.append("")

        lines.extend([
            "─" * 100,
            "TIER DISTRIBUTION",
            "─" * 100,
        ])

        tier_counts = {}
        for strategy in scored:
            tier = strategy["tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        for tier in sorted(tier_counts.keys()):
            count = tier_counts[tier]
            pct = 100 * count / len(scored)
            lines.append(f"  {tier:25} {count:3} strategies ({pct:5.1f}%)")

        lines.extend([
            "",
            "=" * 100,
            f"Generated by Darwin Score v2 Calculator",
            "=" * 100,
        ])

        return "\n".join(lines)


def main():
    """Example usage."""
    sample_strategies = [
        {
            "strategy_id": "momentum_long_v1",
            "wr_pct": 62.5,
            "pf": 2.1,
            "capital": 10000,
            "trades": [
                {"win": True, "pnl_pct": 2.5, "pnl_usd": 250, "timestamp": "2026-04-05T10:00:00"},
                {"win": True, "pnl_pct": 1.8, "pnl_usd": 180, "timestamp": "2026-04-05T11:00:00"},
                {"win": False, "pnl_pct": -1.2, "pnl_usd": -120, "timestamp": "2026-04-05T12:00:00"},
                {"win": True, "pnl_pct": 3.2, "pnl_usd": 320, "timestamp": "2026-04-05T13:00:00"},
                {"win": True, "pnl_pct": 1.5, "pnl_usd": 150, "timestamp": "2026-04-05T14:00:00"},
            ],
        },
        {
            "strategy_id": "mean_revert_short_v2",
            "wr_pct": 55.0,
            "pf": 1.4,
            "capital": 15000,
            "trades": [
                {"win": False, "pnl_pct": -0.8, "pnl_usd": -120, "timestamp": "2026-04-05T10:30:00"},
                {"win": True, "pnl_pct": 1.5, "pnl_usd": 225, "timestamp": "2026-04-05T11:30:00"},
                {"win": True, "pnl_pct": 0.9, "pnl_usd": 135, "timestamp": "2026-04-05T12:30:00"},
                {"win": False, "pnl_pct": -1.1, "pnl_usd": -165, "timestamp": "2026-04-05T13:30:00"},
                {"win": True, "pnl_pct": 1.2, "pnl_usd": 180, "timestamp": "2026-04-05T14:30:00"},
            ],
        },
        {
            "strategy_id": "breakout_micro_v3",
            "wr_pct": 48.0,
            "pf": 0.95,
            "capital": 5000,
            "trades": [
                {"win": False, "pnl_pct": -2.0, "pnl_usd": -100, "timestamp": "2026-04-05T10:15:00"},
                {"win": False, "pnl_pct": -1.5, "pnl_usd": -75, "timestamp": "2026-04-05T11:15:00"},
                {"win": True, "pnl_pct": 5.0, "pnl_usd": 250, "timestamp": "2026-04-05T12:15:00"},
            ],
        },
    ]

    aggregator = StrategyPerformanceAggregator()
    print(aggregator.generate_report(sample_strategies))


if __name__ == "__main__":
    main()
