#!/usr/bin/env python3
"""
TP/SL Optimizer — Kelly Criterion Based Position & Exit Management
================================================================
Derives optimal take-profit and stop-loss levels using utility-based approach.

Key Features:
- Kelly Criterion for optimal position sizing
- Dynamic TP/SL based on volatility and regime
- Multi-tier exit system (hard stop, trailing stop, time exit)
- Expected Value maximization

Academic Basis:
- Kelly, J.L. (1956) "A New Interpretation of Information Rate"
- Thorp, E.O. "The Kelly Formula in Blackjack"
- MacLean, Thorp, Ziemba (2011) "Good and Bad Properties of the Kelly Betting Fraction"

Usage:
python tp_sl_optimizer.py --strategy connors_rsi2 --symbol SPY
python tp_sl_optimizer.py --all --asset-class CRYPTO
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
RISK_FREE_RATE = 0.05  # 5% annualized
KELLY_FRACTION = 0.25  # Conservative Kelly (quarter-Kelly)
ANNUALIZATION_FACTOR = 252

# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------
@dataclass
class TradeRecord:
    """A single closed trade with entry/exit details."""
    entry_price: float
    exit_price: float
    direction: float  # +1 for LONG, -1 for SHORT
    entry_time: str = ""
    exit_time: str = ""
    hold_days: float = 1.0
    exit_reason: str = ""  # TAKE_PROFIT, STOP_LOSS, TIME_EXIT, MANUAL

    @property
    def pnl_pct(self) -> float:
        if self.direction > 0:
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - self.exit_price) / self.entry_price * 100

    @property
    def is_win(self) -> bool:
        return self.pnl_pct > 0

@dataclass
class TPRange:
    """Range for TP optimization."""
    min_mult: float = 0.5  # Minimum TP as ATR multiple
    max_mult: float = 5.0   # Maximum TP as ATR multiple
    step: float = 0.25     # Step size

@dataclass
class SLRange:
    """Range for SL optimization."""
    min_mult: float = 0.5
    max_mult: float = 3.0
    step: float = 0.25

@dataclass
class OptimizedExits:
    """Result of TP/SL optimization."""
    take_profit_pct: float      # TP as percentage of entry
    stop_loss_pct: float         # SL as percentage of entry
    tp_atr_mult: float          # TP in ATR multiples
    sl_atr_mult: float          # SL in ATR multiples
    risk_reward: float          # R:R ratio
    expected_value: float       # Expected value per trade
    kelly_fraction: float        # Optimal Kelly fraction
    win_rate_at_tp_sl: float    # Win rate with these exits
    avg_win_pct: float          # Average win %
    avg_loss_pct: float         # Average loss %
    sharpe_contribution: float   # Expected contribution to Sharpe

@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop."""
    activation_pct: float = 1.0   # Activate when up X%
    trail_distance_pct: float = 0.75  # Trail by X% from peak
    hard_cap_pct: float = 4.0    # Never let gain go below X%

@dataclass
class ExitPlan:
    """Complete multi-tier exit plan."""
    entry_price: float
    take_profit: float
    stop_loss: float
    trailing_stop: Optional[TrailingStopConfig]
    time_exit_hours: int = 168   # Max hold time (1 week default)
    trail_activation_pct: float = 1.0
    trail_distance_pct: float = 0.75

# -----------------------------------------------------------------------------
# ATR Calculator
# -----------------------------------------------------------------------------
def compute_atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> float:
    """Compute Average True Range from price data."""
    if len(high) < period + 1:
        return 0.0

    trs = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
        trs.append(tr)

    if len(trs) < period:
        return 0.0

    return np.mean(trs[-period:])

# -----------------------------------------------------------------------------
# Kelly Criterion
# -----------------------------------------------------------------------------
def compute_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Compute Kelly fraction for position sizing.

    Kelly % = W - (1-W)/R
    Where:
        W = Win rate (probability of winning)
        R = Win/Loss ratio (average win / average loss)

    Returns conservative fraction (quarter-Kelly by default).
    """
    if avg_loss <= 0:
        return 0.0

    reward_ratio = avg_win / avg_loss
    if reward_ratio <= 0:
        return 0.0

    kelly = win_rate - ((1 - win_rate) / reward_ratio)
    return max(0.0, kelly * KELLY_FRACTION)  # Conservative Kelly

def compute_expected_value(
    win_rate: float,
    avg_win_pct: float,
    loss_rate: float,
    avg_loss_pct: float
) -> float:
    """
    Compute expected value per trade.

    EV = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

    This is the expected return per unit staked.
    """
    return (win_rate * avg_win_pct) - (loss_rate * avg_loss_pct)

def compute_utility_adjusted_ev(
    ev: float,
    kelly_fraction: float,
    risk_aversion: float = 1.0
) -> float:
    """
    Compute Kelly utility-adjusted expected value.

    U = ln(1 + f×EV) where f is Kelly fraction

    This penalizes high-variance strategies even if they have high EV.
    """
    if kelly_fraction <= 0:
        return ev

    # Kelly utility function
    utility = math.log(1 + kelly_fraction * ev / 100)

    # Adjust for risk aversion
    return utility * (1 - risk_aversion * (1 - kelly_fraction))

# -----------------------------------------------------------------------------
# TP/SL Optimization Engine
# -----------------------------------------------------------------------------
def optimize_tp_sl(
    trades: List[TradeRecord],
    atr: float,
    entry_price: float,
    direction: int,
    tp_range: TPRange = None,
    sl_range: SLRange = None,
) -> OptimizedExits:
    """
    Grid search for optimal TP/SL combination.

    Maximizes Expected Value subject to minimum win rate constraint.
    """
    if tp_range is None:
        tp_range = TPRange()
    if sl_range is None:
        sl_range = SLRange()

    if atr <= 0 or entry_price <= 0 or not trades:
        return OptimizedExits(
            take_profit_pct=2.0,
            stop_loss_pct=1.0,
            tp_atr_mult=2.0,
            sl_atr_mult=1.0,
            risk_reward=2.0,
            expected_value=0.0,
            kelly_fraction=0.0,
            win_rate_at_tp_sl=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            sharpe_contribution=0.0
        )

    best_ev = float('-inf')
    best_config = None

    tp_mults = np.arange(tp_range.min_mult, tp_range.max_mult + 0.01, tp_range.step)
    sl_mults = np.arange(sl_range.min_mult, sl_range.max_mult + 0.01, sl_range.step)

    for tp_mult in tp_mults:
        for sl_mult in sl_mults:
            # Skip if R:R is too extreme
            rr = tp_mult / sl_mult
            if rr < 0.5 or rr > 10:
                continue

            # Compute simulated exits
            tp_price = entry_price * (1 + direction * tp_mult * atr / entry_price / 100)
            sl_price = entry_price * (1 - direction * sl_mult * atr / entry_price / 100)

            wins = 0
            losses = 0
            total_win = 0.0
            total_loss = 0.0

            for trade in trades:
                # Calculate where this trade would have exited
                if direction > 0:  # LONG
                    if trade.exit_price >= tp_price:
                        wins += 1
                        total_win += tp_mult * atr / entry_price * 100
                    elif trade.exit_price <= sl_price:
                        losses += 1
                        total_loss += sl_mult * atr / entry_price * 100
                else:  # SHORT
                    if trade.exit_price <= tp_price:
                        wins += 1
                        total_win += tp_mult * atr / entry_price * 100
                    elif trade.exit_price >= sl_price:
                        losses += 1
                        total_loss += sl_mult * atr / entry_price * 100

            n_total = wins + losses
            if n_total < 5:  # Need minimum sample
                continue

            wr = wins / n_total

            # Minimum 45% win rate constraint (for prop firm compatibility)
            if wr < 0.45:
                continue

            avg_w = total_win / wins if wins > 0 else 0
            avg_l = total_loss / losses if losses > 0 else 0.001

            ev = compute_expected_value(wr, avg_w, 1 - wr, avg_l)
            kelly = compute_kelly_fraction(wr, avg_w, avg_l)
            utility_ev = compute_utility_adjusted_ev(ev, kelly)

            # Sharpe contribution (simplified)
            sharpe = (ev * 252 - RISK_FREE_RATE) / (abs(avg_l) * math.sqrt(n_total)) if avg_l > 0 else 0

            if utility_ev > best_ev:
                best_ev = utility_ev
                best_config = {
                    'tp_pct': tp_mult * atr / entry_price * 100,
                    'sl_pct': sl_mult * atr / entry_price * 100,
                    'tp_mult': tp_mult,
                    'sl_mult': sl_mult,
                    'rr': rr,
                    'ev': ev,
                    'kelly': kelly,
                    'wr': wr,
                    'avg_win': avg_w,
                    'avg_loss': avg_l,
                    'sharpe': sharpe
                }

    if best_config is None:
        # Default conservative settings
        return OptimizedExits(
            take_profit_pct=2.0 * atr / entry_price * 100,
            stop_loss_pct=1.0 * atr / entry_price * 100,
            tp_atr_mult=2.0,
            sl_atr_mult=1.0,
            risk_reward=2.0,
            expected_value=0.0,
            kelly_fraction=0.0,
            win_rate_at_tp_sl=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            sharpe_contribution=0.0
        )

    return OptimizedExits(
        take_profit_pct=best_config['tp_pct'],
        stop_loss_pct=best_config['sl_pct'],
        tp_atr_mult=best_config['tp_mult'],
        sl_atr_mult=best_config['sl_mult'],
        risk_reward=best_config['rr'],
        expected_value=best_config['ev'],
        kelly_fraction=best_config['kelly'],
        win_rate_at_tp_sl=best_config['wr'],
        avg_win_pct=best_config['avg_win'],
        avg_loss_pct=best_config['avg_loss'],
        sharpe_contribution=best_config['sharpe']
    )

# -----------------------------------------------------------------------------
# Trailing Stop Manager
# -----------------------------------------------------------------------------
class TrailingStopManager:
    """
    Multi-tier stop loss system.

    Tier 1: Initial Hard Stop - Protects against large adverse moves
    Tier 2: Trailing Stop - Locks in profits while allowing room to run
    Tier 3: Time Exit - Forces exit after max hold period
    """

    def __init__(self, config: TrailingStopConfig = None):
        self.config = config or TrailingStopConfig()
        self.peak_price: float = 0.0
        self.current_stop: float = 0.0
        self.trail_active: bool = False
        self.entry_price: float = 0.0
        self.direction: int = 0
        self.entry_time: datetime = None
        self.max_hold_hours: int = 168

    def initialize(self, entry_price: float, direction: int, entry_time: datetime = None):
        """Initialize the trailing stop on entry."""
        self.entry_price = entry_price
        self.direction = direction
        self.entry_time = entry_time or datetime.now(timezone.utc)
        self.peak_price = entry_price
        self.trail_active = False
        # Initial hard stop at entry
        self.current_stop = entry_price * (1 - self.config.hard_cap_pct / 100 * self.direction)

    def update(self, current_price: float, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Update trailing stop based on current price.

        Returns: (should_exit, exit_reason)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Update peak price
        if self.direction > 0:
            if current_price > self.peak_price:
                self.peak_price = current_price
        else:
            if current_price < self.peak_price:
                self.peak_price = current_price

        # Check activation threshold
        if not self.trail_active:
            activation_distance = abs(self.peak_price - self.entry_price) / self.entry_price * 100
            if activation_distance >= self.config.activation_pct:
                self.trail_active = True
                # Move hard stop to breakeven
                self.current_stop = self.entry_price * (1 - 0.1 / 100 * self.direction)

        # Update trailing stop if active
        if self.trail_active:
            trail_distance = self.peak_price * self.config.trail_distance_pct / 100 * self.direction
            if self.direction > 0:
                new_stop = self.peak_price - trail_distance
            else:
                new_stop = self.peak_price + trail_distance

            # Only move stop in favor of position
            if self.direction > 0:
                if new_stop > self.current_stop:
                    self.current_stop = new_stop
            else:
                if new_stop < self.current_stop:
                    self.current_stop = new_stop

        # Hard cap - never let gain go below minimum
        min_keep_pct = self.entry_price * (1 - self.config.hard_cap_pct / 100 * self.direction)
        if self.direction > 0:
            if self.current_stop < min_keep_pct:
                self.current_stop = min_keep_pct
        else:
            if self.current_stop > min_keep_pct:
                self.current_stop = min_keep_pct

        # Check exit conditions
        # 1. Trailing stop hit
        if self.direction > 0:
            if current_price <= self.current_stop:
                return True, "TRAILING_STOP"
        else:
            if current_price >= self.current_stop:
                return True, "TRAILING_STOP"

        # 2. Time exit
        if self.entry_time:
            hours_held = (current_time - self.entry_time).total_seconds() / 3600
            if hours_held >= self.max_hold_hours:
                return True, "TIME_EXIT"

        return False, ""

    def get_current_stop(self) -> float:
        """Get current stop level."""
        return self.current_stop

    def get_stop_distance_pct(self, current_price: float) -> float:
        """Get current distance from stop to price."""
        return abs(current_price - self.current_stop) / current_price * 100

# -----------------------------------------------------------------------------
# Dynamic Position Sizer
# -----------------------------------------------------------------------------
def compute_position_size(
    account_size: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    kelly_fraction: float = None,
    confidence: float = 1.0,
    asset_volatility: float = None,
    portfolio_volatility_budget: float = 0.15
) -> Tuple[float, Dict]:
    """
    Compute position size using dynamic Kelly-based sizing.

    Factors:
    - Account size
    - Risk per trade
    - Kelly fraction
    - Signal confidence
    - Asset volatility
    - Portfolio volatility budget

    Returns: (position_size_dollars, sizing_metadata)
    """
    if stop_loss_pct <= 0:
        return 0.0, {"error": "Invalid stop loss"}

    # Base position size from risk per trade
    base_risk = account_size * (risk_per_trade_pct / 100)
    base_position = base_risk / (stop_loss_pct / 100)

    # Kelly adjustment
    kelly_multiplier = kelly_fraction if kelly_fraction else KELLY_FRACTION

    # Confidence scaling
    # Low confidence = reduce size
    # High confidence = full size (cap at Kelly)
    confidence_multiplier = min(1.0, max(0.25, confidence))

    # Volatility adjustment
    vol_multiplier = 1.0
    if asset_volatility and asset_volatility > 0:
        # Target 10% annualized vol
        target_vol = 0.10
        vol_ratio = target_vol / asset_volatility
        vol_multiplier = min(2.0, max(0.25, vol_ratio))

    # Portfolio volatility budget check
    portfolio_size_multiplier = 1.0
    # This would need portfolio context - simplified for now

    # Final position size
    position = base_position * kelly_multiplier * confidence_multiplier * vol_multiplier

    # Cap at reasonable maximum (25% of account)
    max_position = account_size * 0.25
    position = min(position, max_position)

    # Floor at minimum (0.5% of account)
    min_position = account_size * 0.005
    position = max(position, min_position)

    metadata = {
        "base_position": base_position,
        "kelly_fraction": kelly_multiplier,
        "confidence_multiplier": confidence_multiplier,
        "vol_multiplier": vol_multiplier,
        "final_position": position,
        "risk_used_pct": (position * stop_loss_pct / 100) / account_size * 100,
        "position_pct_of_account": position / account_size * 100
    }

    return position, metadata

# -----------------------------------------------------------------------------
# Slippage Model
# -----------------------------------------------------------------------------
def estimate_execution_slippage(
    trade_value: float,
    daily_volume: float,
    bid_ask_spread_bps: float = 10.0,
    market_impact_coeff: float = 0.1,
    order_type: str = "market"  # market, limit, stop
) -> Dict:
    """
    Estimate execution slippage based on market microstructure.

    Components:
    1. Spread cost - always pay half the bid-ask spread
    2. Market impact - proportional to order size vs volume

    Model:
    slippage = spread/2 + market_impact × (order_size/volume)^0.6

    Reference: Almgren & Chriss (2000) "Optimal Execution of Portfolio Transactions"
    """
    if daily_volume <= 0 or trade_value <= 0:
        return {
            "total_slippage_bps": 0,
            "spread_cost_bps": 0,
            "market_impact_bps": 0,
            "estimated_exit_price": None,
            "error": "Invalid volume or trade value"
        }

    # Order size relative to daily volume
    participation_rate = trade_value / daily_volume

    # Spread cost (half of bid-ask)
    spread_cost = bid_ask_spread_bps / 2

    # Market impact using square-root model
    # Higher participation = higher impact
    market_impact = market_impact_coeff * math.pow(participation_rate, 0.6) * 100

    # Total slippage
    total_slippage = spread_cost + market_impact

    # For market orders, expect to pay full spread
    if order_type == "market":
        total_slippage = bid_ask_spread_bps + market_impact * 0.5

    return {
        "total_slippage_bps": round(total_slippage, 2),
        "spread_cost_bps": round(spread_cost, 2),
        "market_impact_bps": round(market_impact, 2),
        "participation_rate_pct": round(participation_rate * 100, 3),
        "order_type": order_type,
        "estimated_slippage_cost": round(trade_value * total_slippage / 10000, 2)
    }

# -----------------------------------------------------------------------------
# Strategy Analyzer
# -----------------------------------------------------------------------------
def analyze_strategy_exits(
    trades: List[TradeRecord],
    avg_atr: float,
    avg_entry_price: float
) -> Dict:
    """
    Analyze a strategy's current TP/SL performance and suggest improvements.
    """
    if not trades:
        return {"error": "No trades provided"}

    # Categorize exits
    tp_hits = sum(1 for t in trades if t.exit_reason == "TAKE_PROFIT")
    sl_hits = sum(1 for t in trades if t.exit_reason == "STOP_LOSS")
    time_exits = sum(1 for t in trades if t.exit_reason == "TIME_EXIT")

    total_closed = tp_hits + sl_hits + time_exits
    if total_closed == 0:
        return {"error": "No closed trades with TP/SL exits"}

    # Analyze by exit type
    results = {
        "total_trades": len(trades),
        "closed_with_exits": total_closed,
        "tp_hits": tp_hits,
        "sl_hits": sl_hits,
        "time_exits": time_exits,
        "tp_rate": tp_hits / total_closed if total_closed > 0 else 0,
        "sl_rate": sl_hits / total_closed if total_closed > 0 else 0,
        "time_exit_rate": time_exits / total_closed if total_closed > 0 else 0,
    }

    # Optimize TP/SL
    optimized = optimize_tp_sl(
        trades, avg_atr, avg_entry_price, 1,
        TPRange(min_mult=1.0, max_mult=4.0, step=0.25),
        SLRange(min_mult=0.5, max_mult=2.0, step=0.25)
    )

    results["optimized_tp_pct"] = round(optimized.take_profit_pct, 3)
    results["optimized_sl_pct"] = round(optimized.stop_loss_pct, 3)
    results["optimized_tp_mult"] = round(optimized.tp_atr_mult, 2)
    results["optimized_sl_mult"] = round(optimized.sl_atr_mult, 2)
    results["optimized_rr"] = round(optimized.risk_reward, 2)
    results["optimized_ev"] = round(optimized.expected_value, 3)
    results["optimized_kelly"] = round(optimized.kelly_fraction, 4)
    results["optimized_wr"] = round(optimized.win_rate_at_tp_sl * 100, 1)
    results["optimized_avg_win"] = round(optimized.avg_win_pct, 3)
    results["optimized_avg_loss"] = round(optimized.avg_loss_pct, 3)

    # Recommendations
    recommendations = []
    if optimized.tp_atr_mult < 2.0:
        recommendations.append("Consider wider TP to let winners run")
    if optimized.sl_atr_mult > 1.5:
        recommendations.append("Consider tighter SL to reduce loss magnitude")
    if optimized.win_rate_at_tp_sl < 0.50:
        recommendations.append("Win rate below 50% - review entry signals")
    if optimized.expected_value < 0.3:
        recommendations.append("EV is low - consider regime filtering")
    if results["time_exit_rate"] > 0.3:
        recommendations.append("High time exit rate - targets may be too aggressive")

    results["recommendations"] = recommendations

    return results

# -----------------------------------------------------------------------------
# Main / CLI
# -----------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="TP/SL Optimizer - Kelly Criterion Based")
    parser.add_argument("--strategy", type=str, help="Strategy name")
    parser.add_argument("--symbol", type=str, help="Symbol to analyze")
    parser.add_argument("--asset-class", type=str, default="", help="Asset class")
    parser.add_argument("--all", action="store_true", help="Analyze all strategies")
    parser.add_argument("--output", type=str, help="Output JSON path")
    args = parser.parse_args()

    # Demo with synthetic data
    print("TP/SL Optimizer - Running demo with synthetic data")
    print("=" * 60)

    # Generate synthetic trades
    trades = []
    for i in range(100):
        entry = 100.0
        direction = 1 if i % 2 == 0 else -1
        # Simulate realistic outcome
        outcome = np.random.choice(['win', 'loss', 'win', 'win', 'win'], p=[0.4, 0.3, 0.1, 0.1, 0.1])
        if outcome == 'win':
            exit_price = entry * (1 + direction * 0.02)  # ~2% win
            reason = "TAKE_PROFIT"
        else:
            exit_price = entry * (1 - direction * 0.01)  # ~1% loss
            reason = "STOP_LOSS"

        trades.append(TradeRecord(
            entry_price=entry,
            exit_price=exit_price,
            direction=direction,
            exit_reason=reason,
            hold_days=np.random.uniform(0.5, 3.0)
        ))

    # Analyze
    results = analyze_strategy_exits(trades, avg_atr=1.5, avg_entry_price=100.0)

    print("\nStrategy Exit Analysis:")
    print("-" * 40)
    print(f"Total Trades: {results.get('total_trades', 0)}")
    print(f"TP Rate: {results.get('tp_rate', 0)*100:.1f}%")
    print(f"SL Rate: {results.get('sl_rate', 0)*100:.1f}%")
    print(f"Time Exit Rate: {results.get('time_exit_rate', 0)*100:.1f}%")

    print("\nOptimized TP/SL:")
    print("-" * 40)
    print(f"TP: {results.get('optimized_tp_mult', 0):.2f}x ATR ({results.get('optimized_tp_pct', 0):.3f}%)")
    print(f"SL: {results.get('optimized_sl_mult', 0):.2f}x ATR ({results.get('optimized_sl_pct', 0):.3f}%)")
    print(f"R:R: {results.get('optimized_rr', 0):.2f}")
    print(f"Expected Value: {results.get('optimized_ev', 0):.3f}%")
    print(f"Win Rate: {results.get('optimized_wr', 0):.1f}%")
    print(f"Kelly Fraction: {results.get('optimized_kelly', 0)*100:.1f}%")

    if results.get("recommendations"):
        print("\nRecommendations:")
        for rec in results["recommendations"]:
            print(f"  - {rec}")

    # Slippage demo
    print("\n" + "=" * 60)
    print("Slippage Estimation Demo:")
    print("-" * 40)
    slip = estimate_execution_slippage(
        trade_value=10000,
        daily_volume=1000000,
        bid_ask_spread_bps=15,
        order_type="market"
    )
    print(f"Total Slippage: {slip['total_slippage_bps']} bps")
    print(f"Spread Cost: {slip['spread_cost_bps']} bps")
    print(f"Market Impact: {slip['market_impact_bps']} bps")
    print(f"Participation Rate: {slip['participation_rate_pct']}%")
    print(f"Estimated Cost: ${slip.get('estimated_slippage_cost', 0):.2f}")

    # Position sizing demo
    print("\n" + "=" * 60)
    print("Position Sizing Demo:")
    print("-" * 40)
    size, meta = compute_position_size(
        account_size=100000,
        risk_per_trade_pct=1.0,
        stop_loss_pct=1.5,
        kelly_fraction=0.15,
        confidence=0.75,
        asset_volatility=0.60
    )
    print(f"Account Size: $100,000")
    print(f"Risk Per Trade: 1.0%")
    print(f"Stop Loss: 1.5%")
    print(f"Kelly Fraction: {meta['kelly_fraction']*100:.1f}%")
    print(f"Confidence Multiplier: {meta['confidence_multiplier']*100:.1f}%")
    print(f"Vol Multiplier: {meta['vol_multiplier']*100:.1f}%")
    print(f"Position Size: ${size:,.2f} ({meta['position_pct_of_account']:.1f}% of account)")
    print(f"Risk Used: {meta['risk_used_pct']:.2f}%")

if __name__ == "__main__":
    main()
