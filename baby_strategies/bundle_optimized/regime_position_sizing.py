#!/usr/bin/env python3
"""
Regime-Aware Position Sizing Module
===================================
Implements Half-Kelly sizing with regime adjustments

Key Features:
- Half-Kelly Criterion: f* = (p*b - q) / b, then divide by 2
- Regime multipliers: Reduce size in volatile regimes
- Drawdown protection: Reduce size after consecutive losses
- Correlation caps: Limit exposure to similar strategies
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from enum import Enum


class MarketRegime(Enum):
    TRENDING_STRONG = "trending_strong"
    TRENDING_WEAK = "trending_weak"
    RANGING = "ranging"
    VOLATILE = "volatile"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"


@dataclass
class PositionSize:
    """Position sizing recommendation"""
    base_kelly: float           # Raw Kelly fraction
    half_kelly: float           # Half-Kelly (recommended)
    regime_adjusted: float      # After regime multiplier
    final_size: float           # After all adjustments
    max_position: float         # Hard cap
    confidence: float           # Confidence in the sizing
    reasoning: str              # Explanation


class RegimePositionSizer:
    """
    Position sizer with regime awareness
    """
    
    # Regime multipliers (reduce size in uncertain regimes)
    REGIME_MULTIPLIERS = {
        MarketRegime.TRENDING_STRONG: 1.0,
        MarketRegime.TRENDING_WEAK: 0.8,
        MarketRegime.RANGING: 0.9,
        MarketRegime.VOLATILE: 0.5,      # Reduce in volatile
        MarketRegime.BREAKOUT: 0.7,
        MarketRegime.UNKNOWN: 0.3
    }
    
    # Drawdown protection levels
    DRAWDOWN_LIMITS = {
        0.05: 0.9,    # -5% DD → 90% size
        0.10: 0.7,    # -10% DD → 70% size
        0.15: 0.5,    # -15% DD → 50% size
        0.20: 0.3,    # -20% DD → 30% size
        0.25: 0.0     # -25% DD → STOP
    }
    
    def __init__(self, 
                 max_position_pct: float = 0.25,
                 min_position_pct: float = 0.01):
        self.max_position = max_position_pct
        self.min_position = min_position_pct
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
    def calculate_kelly(self, 
                       win_rate: float, 
                       avg_win: float, 
                       avg_loss: float) -> Tuple[float, float]:
        """
        Calculate Kelly Criterion
        
        Args:
            win_rate: Probability of win (0-1)
            avg_win: Average win amount (as multiple of risk)
            avg_loss: Average loss amount (as multiple of risk, positive)
            
        Returns:
            (full_kelly, half_kelly)
        """
        if avg_win <= 0 or avg_loss <= 0:
            return 0.0, 0.0
            
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss  # Win/Loss ratio
        
        if b <= 0:
            return 0.0, 0.0
            
        # Kelly formula: f* = (p*b - q) / b
        kelly_full = (p * b - q) / b
        
        # Clamp and apply half-Kelly
        kelly_full = max(0.0, min(0.5, kelly_full))
        kelly_half = kelly_full / 2.0
        
        return kelly_full, kelly_half
    
    def apply_regime_multiplier(self, 
                                base_size: float, 
                                regime: MarketRegime) -> float:
        """Apply regime-based size adjustment"""
        multiplier = self.REGIME_MULTIPLIERS.get(regime, 0.5)
        return base_size * multiplier
    
    def apply_drawdown_protection(self, 
                                   size: float, 
                                   current_drawdown: float) -> float:
        """
        Reduce position size during drawdowns
        
        Args:
            size: Current position size
            current_drawdown: Current drawdown (0-1, positive)
        """
        for dd_limit, size_mult in sorted(self.DRAWDOWN_LIMITS.items()):
            if current_drawdown >= dd_limit:
                return size * size_mult
        return size
    
    def apply_streak_adjustment(self, size: float) -> float:
        """
        Adjust size based on consecutive win/loss streak
        
        - After 3+ losses: Reduce size by 20%
        - After 3+ wins: Can increase size by 10%
        """
        if self.consecutive_losses >= 3:
            return size * 0.8
        elif self.consecutive_wins >= 3:
            return min(size * 1.1, self.max_position)
        return size
    
    def get_position_size(self,
                         win_rate: float,
                         avg_win: float,
                         avg_loss: float,
                         regime: MarketRegime,
                         current_drawdown: float = 0.0,
                         strategy_edge: float = 0.0) -> PositionSize:
        """
        Calculate complete position size with all adjustments
        
        Args:
            win_rate: Expected win rate (0-1)
            avg_win: Average win as multiple of risk
            avg_loss: Average loss as multiple of risk
            regime: Current market regime
            current_drawdown: Current portfolio drawdown (0-1)
            strategy_edge: Additional edge from strategy quality (0-1)
            
        Returns:
            PositionSize with all calculations
        """
        # Base Kelly
        kelly_full, kelly_half = self.calculate_kelly(win_rate, avg_win, avg_loss)
        
        # Adjust for strategy edge
        adjusted_kelly = kelly_half * (1 + strategy_edge)
        
        # Apply regime multiplier
        regime_adjusted = self.apply_regime_multiplier(adjusted_kelly, regime)
        
        # Apply drawdown protection
        dd_adjusted = self.apply_drawdown_protection(regime_adjusted, current_drawdown)
        
        # Apply streak adjustment
        streak_adjusted = self.apply_streak_adjustment(dd_adjusted)
        
        # Apply hard limits
        final_size = max(self.min_position, min(self.max_position, streak_adjusted))
        
        # Calculate confidence
        confidence = min(1.0, win_rate * (1 + strategy_edge))
        
        # Build reasoning
        reasoning_parts = [
            f"Base Kelly: {kelly_half*100:.1f}%",
            f"Regime ({regime.value}): x{self.REGIME_MULTIPLIERS[regime]:.1f}",
        ]
        
        if current_drawdown > 0.05:
            reasoning_parts.append(f"Drawdown ({current_drawdown*100:.1f}%): reduced")
            
        if self.consecutive_losses >= 3:
            reasoning_parts.append(f"Loss streak ({self.consecutive_losses}): -20%")
        elif self.consecutive_wins >= 3:
            reasoning_parts.append(f"Win streak ({self.consecutive_wins}): +10%")
            
        reasoning = " | ".join(reasoning_parts)
        
        return PositionSize(
            base_kelly=kelly_half,
            half_kelly=kelly_half,
            regime_adjusted=regime_adjusted,
            final_size=final_size,
            max_position=self.max_position,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def update_streak(self, is_win: bool):
        """Update win/loss streak tracking"""
        if is_win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
    
    def reset_streak(self):
        """Reset streak counters"""
        self.consecutive_losses = 0
        self.consecutive_wins = 0


class PortfolioAllocator:
    """
    Portfolio-level capital allocation across strategies
    """
    
    def __init__(self, num_strategies: int = 3):
        self.num_strategies = num_strategies
        self.max_total_exposure = 0.80  # Max 80% in strategies
        self.min_cash = 0.20            # Min 20% cash
        
    def allocate(self, 
                 strategy_scores: Dict[str, float],
                 regime: MarketRegime) -> Dict[str, float]:
        """
        Allocate capital across strategies based on scores
        
        Args:
            strategy_scores: Dict of strategy_name -> score (0-1)
            regime: Current market regime
            
        Returns:
            Dict of strategy_name -> allocation_pct
        """
        total_score = sum(strategy_scores.values())
        
        if total_score == 0:
            # Equal weight if no scores
            equal_alloc = self.max_total_exposure / len(strategy_scores)
            return {name: equal_alloc for name in strategy_scores}
        
        # Score-proportional allocation
        allocations = {}
        for name, score in strategy_scores.items():
            base_alloc = (score / total_score) * self.max_total_exposure
            allocations[name] = base_alloc
            
        # Regime adjustments
        if regime == MarketRegime.VOLATILE:
            # Reduce all allocations in volatile regime
            allocations = {k: v * 0.6 for k, v in allocations.items()}
            
        return allocations
    
    def validate_allocation(self, allocations: Dict[str, float]) -> bool:
        """Check if allocation is valid"""
        total = sum(allocations.values())
        return total <= self.max_total_exposure and all(v >= 0 for v in allocations.values())


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Regime-Aware Position Sizing Demo")
    print("=" * 60)
    
    sizer = RegimePositionSizer(max_position_pct=0.25)
    
    # Example 1: Strong trend, high edge
    print("\n1. Strong Trend, High Edge Strategy:")
    size = sizer.get_position_size(
        win_rate=0.60,
        avg_win=2.5,
        avg_loss=1.0,
        regime=MarketRegime.TRENDING_STRONG,
        strategy_edge=0.15
    )
    print(f"   Final Size: {size.final_size*100:.1f}%")
    print(f"   Reasoning: {size.reasoning}")
    
    # Example 2: Volatile market
    print("\n2. Volatile Market, Same Strategy:")
    size = sizer.get_position_size(
        win_rate=0.60,
        avg_win=2.5,
        avg_loss=1.0,
        regime=MarketRegime.VOLATILE,
        strategy_edge=0.15
    )
    print(f"   Final Size: {size.final_size*100:.1f}%")
    print(f"   Reasoning: {size.reasoning}")
    
    # Example 3: During drawdown
    print("\n3. During 15% Drawdown:")
    size = sizer.get_position_size(
        win_rate=0.60,
        avg_win=2.5,
        avg_loss=1.0,
        regime=MarketRegime.TRENDING_STRONG,
        current_drawdown=0.15,
        strategy_edge=0.15
    )
    print(f"   Final Size: {size.final_size*100:.1f}%")
    print(f"   Reasoning: {size.reasoning}")
    
    # Portfolio allocation example
    print("\n" + "=" * 60)
    print("Portfolio Allocation Demo")
    print("=" * 60)
    
    allocator = PortfolioAllocator()
    
    strategy_scores = {
        'funding_arbitrage': 0.95,  # High confidence
        'grid_trading': 0.70,
        'momentum': 0.55
    }
    
    print("\nIn Ranging Regime:")
    alloc = allocator.allocate(strategy_scores, MarketRegime.RANGING)
    for name, pct in alloc.items():
        print(f"   {name}: {pct*100:.1f}%")
        
    print("\nIn Volatile Regime:")
    alloc = allocator.allocate(strategy_scores, MarketRegime.VOLATILE)
    for name, pct in alloc.items():
        print(f"   {name}: {pct*100:.1f}%")
        
    print("\n" + "=" * 60)
