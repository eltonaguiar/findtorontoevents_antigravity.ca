#!/usr/bin/env python3
"""
Dynamic Position Sizer — Volatility-Adjusted Portfolio Risk Management
====================================================================
Computes optimal position sizes using Kelly criterion with volatility targeting.

Key Features:
- Kelly fraction with conservative multipliers
- Volatility targeting (10% annualized vol)
- Confidence-adjusted sizing
- Portfolio-level risk budget
- Correlation-aware allocation

Usage:
python dynamic_position_sizer.py --portfolio
python dynamic_position_sizer.py --symbol BTC --account 100000
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
RISK_FREE_RATE = 0.05
ANNUALIZATION_FACTOR = 252
TARGET_VOLATILITY = 0.10  # 10% annualized vol target
KELLY_FRACTION = 0.25    # Conservative Kelly (quarter-Kelly)
MAX_POSITION_PCT = 0.25   # Max 25% of account in one position
MIN_POSITION_PCT = 0.005  # Min 0.5% of account

# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------
@dataclass
class PositionSizingConfig:
    """Configuration for position sizing."""
    account_size: float
    risk_per_trade_pct: float = 1.0
    max_positions: int = 10
    portfolio_vol_target: float = 0.15
    kelly_fraction: float = KELLY_FRACTION
    vollookback_days: int = 20

@dataclass
class Position:
    """A single position with sizing details."""
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: float
    position_size: float
    position_pct: float
    stop_loss_pct: float
    risk_amount: float
    kelly_fraction: float
    confidence: float
    vol_adjustment: float
    expected_return: float

@dataclass
class PortfolioAllocation:
    """Complete portfolio allocation with all positions."""
    total_value: float
    positions: List[Position]
    total_exposure_pct: float
    total_risk_pct: float
    portfolio_volatility: float
    expected_return: float
    sharpe_contribution: float

# -----------------------------------------------------------------------------
# Kelly Calculator
# -----------------------------------------------------------------------------
def kelly_fraction(win_rate: float, avg_win_pct: float, avg_loss_pct: float) -> float:
    """
    Compute Kelly fraction for position sizing.

    Kelly % = W - (1-W)/R
    """
    if avg_loss_pct <= 0:
        return 0.0

    reward_ratio = avg_win_pct / avg_loss_pct
    if reward_ratio <= 0:
        return 0.0

    kelly = win_rate - ((1 - win_rate) / reward_ratio)
    return max(0.0, min(1.0, kelly * KELLY_FRACTION))

def expected_value(win_rate: float, avg_win_pct: float, loss_rate: float, avg_loss_pct: float) -> float:
    """Compute expected value per trade."""
    return (win_rate * avg_win_pct) - (loss_rate * avg_loss_pct)

# -----------------------------------------------------------------------------
# Volatility Calculator
# -----------------------------------------------------------------------------
def compute_realized_volatility(returns: List[float], annualize: bool = True) -> float:
    """Compute realized volatility from returns."""
    if len(returns) < 2:
        return 0.0

    daily_vol = np.std(returns, ddof=1)

    if annualize:
        return daily_vol * math.sqrt(ANNUALIZATION_FACTOR)

    return daily_vol

def compute_vol_scalar(
    realized_vol: float,
    target_vol: float = TARGET_VOLATILITY
) -> float:
    """
    Compute volatility scaling factor.

    vol_scalar = target_vol / realized_vol

    If realized > target, reduce position.
    If realized < target, can increase position.
    """
    if realized_vol <= 0:
        return 1.0

    return target_vol / realized_vol

# -----------------------------------------------------------------------------
# Position Size Calculator
# -----------------------------------------------------------------------------
def compute_position_size(
    account_size: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    kelly: float = None,
    confidence: float = 1.0,
    vol_scalar: float = 1.0,
    max_position_pct: float = MAX_POSITION_PCT,
    min_position_pct: float = MIN_POSITION_PCT
) -> Tuple[float, Dict]:
    """
    Compute position size with all adjustments.

    Size = Base × Kelly × Confidence × VolScalar

    Where Base = Risk / StopLoss
    """
    if stop_loss_pct <= 0:
        return 0.0, {"error": "Invalid stop loss"}

    # Base position from risk
    risk_amount = account_size * (risk_per_trade_pct / 100)
    base_position = risk_amount / (stop_loss_pct / 100)

    # Kelly adjustment (if not provided, use conservative default)
    kelly_mult = kelly if kelly else KELLY_FRACTION

    # Confidence scaling (low confidence = reduce)
    conf_mult = min(1.0, max(0.25, confidence))

    # Volatility scaling
    vol_mult = min(2.0, max(0.25, vol_scalar))

    # Combined multiplier
    total_mult = kelly_mult * conf_mult * vol_mult

    # Final position
    position = base_position * total_mult

    # Apply caps
    max_pos = account_size * max_position_pct
    min_pos = account_size * min_position_pct

    position = min(position, max_pos)
    position = max(position, min_pos)

    metadata = {
        "base_position": base_position,
        "risk_amount": risk_amount,
        "kelly_mult": kelly_mult,
        "conf_mult": conf_mult,
        "vol_mult": vol_mult,
        "total_mult": total_mult,
        "position_raw": base_position * total_mult,
        "position_capped": position,
        "position_pct": position / account_size * 100,
        "risk_used_pct": (position * stop_loss_pct / 100) / account_size * 100
    }

    return position, metadata

# -----------------------------------------------------------------------------
# Correlation-Aware Portfolio Allocator
# -----------------------------------------------------------------------------
def compute_correlation_matrix(returns: Dict[str, List[float]]) -> np.ndarray:
    """Compute correlation matrix from returns dict."""
    symbols = list(returns.keys())
    n = len(symbols)

    if n < 2:
        return None

    # Pad to same length
    max_len = max(len(r) for r in returns.values())

    padded = []
    for sym in symbols:
        r = returns[sym]
        if len(r) < max_len:
            r = [0.0] * (max_len - len(r)) + r
        padded.append(r)

    matrix = np.corrcoef(padded)

    return matrix

def compute_portfolio_volatility(
    weights: np.ndarray,
    correlation_matrix: np.ndarray,
    volatilities: np.ndarray
) -> float:
    """
    Compute portfolio volatility from weights, correlations, and vols.

    σ_portfolio² = w' × Σ × w
    where Σ = correlation_matrix × outer(vols, vols)
    """
    if correlation_matrix is None or len(weights) < 2:
        # Simple case: sum of weighted vols
        return np.sum(weights * volatilities)

    # Covariance matrix
    vols_outer = np.outer(volatilities, volatilities)
    cov_matrix = correlation_matrix * vols_outer

    # Portfolio variance
    portfolio_var = weights @ cov_matrix @ weights

    return math.sqrt(portfolio_var)

def optimize_portfolio_weights(
    signals: Dict[str, Dict],
    returns: Dict[str, List[float]],
    max_positions: int = 10
) -> Dict[str, float]:
    """
    Optimize portfolio weights using risk parity with Kelly adjustments.

    1. Rank signals by Kelly-adjusted expected value
    2. Select top N positions
    3. Allocate using inverse-vol weighting
    4. Apply correlation adjustment
    """
    # Score each signal
    scored = []
    for symbol, data in signals.items():
        kelly = kelly_fraction(
            data.get("win_rate", 0.5),
            data.get("avg_win", 1.0),
            data.get("avg_loss", 1.0)
        )
        ev = expected_value(
            data.get("win_rate", 0.5),
            data.get("avg_win", 1.0),
            1 - data.get("win_rate", 0.5),
            data.get("avg_loss", 1.0)
        )

        # Kelly-adjusted score
        score = kelly * ev * data.get("confidence", 1.0)

        scored.append({
            "symbol": symbol,
            "score": score,
            "kelly": kelly,
            "ev": ev,
            "weight": 0.0  # To be filled
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Take top N
    top_signals = scored[:max_positions]

    if not top_signals:
        return {}

    # Compute inverse-vol weights for top signals
    vols = []
    for sig in top_signals:
        sym = sig["symbol"]
        if sym in returns and len(returns[sym]) > 1:
            vol = compute_realized_volatility(returns[sym])
            vols.append(max(vol, 0.001))  # Floor
        else:
            vols.append(TARGET_VOLATILITY)

    # Inverse vol weights
    inv_vols = [1.0 / v for v in vols]
    total_inv = sum(inv_vols)

    weights = [iv / total_inv for iv in inv_vols]

    # Apply correlation adjustment (simple: reduce correlated positions)
    corr_matrix = compute_correlation_matrix({sig["symbol"]: returns.get(sig["symbol"], []) for sig in top_signals})

    if corr_matrix is not None and len(corr_matrix) > 1:
        # Simple correlation penalty
        avg_corr = (np.sum(corr_matrix) - len(corr_matrix)) / (len(corr_matrix) * (len(corr_matrix) - 1))
        corr_penalty = max(0.5, 1 - avg_corr)

        for i, sig in enumerate(top_signals):
            sig["weight"] = weights[i] * corr_penalty

        # Renormalize
        total = sum(s["weight"] for s in top_signals)
        for sig in top_signals:
            sig["weight"] /= total
    else:
        for i, sig in enumerate(top_signals):
            sig["weight"] = weights[i]

    return {sig["symbol"]: sig["weight"] for sig in top_signals}

# -----------------------------------------------------------------------------
# Portfolio Risk Manager
# -----------------------------------------------------------------------------
class PortfolioRiskManager:
    """
    Manages portfolio-level risk with position sizing and limits.
    """

    def __init__(self, config: PositionSizingConfig):
        self.config = config
        self.positions: List[Position] = []
        self.equity_curve: List[float] = [config.account_size]

    def add_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss_pct: float,
        confidence: float = 0.7,
        avg_win_pct: float = 2.0,
        avg_loss_pct: float = 1.0,
        win_rate: float = 0.55,
        realized_vol: float = None
    ) -> Optional[Position]:
        """Add a new position with dynamic sizing."""

        # Check max positions
        if len(self.positions) >= self.config.max_positions:
            return None

        # Compute Kelly
        kelly = kelly_fraction(win_rate, avg_win_pct, avg_loss_pct)

        # Compute vol scalar
        if realized_vol:
            vol_scalar = compute_vol_scalar(realized_vol)
        else:
            vol_scalar = 1.0

        # Compute position size
        position_value, metadata = compute_position_size(
            self.config.account_size,
            self.config.risk_per_trade_pct,
            stop_loss_pct,
            kelly,
            confidence,
            vol_scalar
        )

        # Check portfolio exposure
        current_exposure = sum(p.position_size for p in self.positions)
        new_exposure = current_exposure + position_value

        if new_exposure > self.config.account_size * 0.95:
            # Would exceed account
            return None

        # Create position
        position = Position(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            position_size=position_value,
            position_pct=position_value / self.config.account_size * 100,
            stop_loss_pct=stop_loss_pct,
            risk_amount=position_value * stop_loss_pct / 100,
            kelly_fraction=kelly,
            confidence=confidence,
            vol_adjustment=vol_scalar,
            expected_return=expected_value(win_rate, avg_win_pct, 1-win_rate, avg_loss_pct)
        )

        self.positions.append(position)
        return position

    def remove_position(self, symbol: str) -> bool:
        """Remove a position from the portfolio."""
        for i, pos in enumerate(self.positions):
            if pos.symbol == symbol:
                self.positions.pop(i)
                return True
        return False

    def get_portfolio_allocation(self) -> PortfolioAllocation:
        """Get current portfolio allocation."""
        total_value = self.config.account_size
        total_exposure = sum(p.position_size for p in self.positions)
        total_risk = sum(p.risk_amount for p in self.positions)

        # Portfolio volatility (simplified)
        if self.positions:
            weighted_vol = sum(p.position_pct / 100 * p.vol_adjustment * TARGET_VOLATILITY for p in self.positions)
        else:
            weighted_vol = 0.0

        # Expected return
        expected_ret = sum(p.position_pct / 100 * p.expected_return for p in self.positions) if self.positions else 0.0

        # Sharpe contribution
        if weighted_vol > 0:
            sharpe = (expected_ret * ANNUALIZATION_FACTOR - RISK_FREE_RATE) / (weighted_vol * math.sqrt(ANNUALIZATION_FACTOR))
        else:
            sharpe = 0.0

        return PortfolioAllocation(
            total_value=total_value,
            positions=self.positions,
            total_exposure_pct=total_exposure / total_value * 100,
            total_risk_pct=total_risk / total_value * 100,
            portfolio_volatility=weighted_vol,
            expected_return=expected_ret,
            sharpe_contribution=sharpe
        )

    def check_risk_limits(self) -> Dict:
        """Check if portfolio is within risk limits."""
        alloc = self.get_portfolio_allocation()

        violations = []

        # Total exposure
        if alloc.total_exposure_pct > 95:
            violations.append(f"Exposure too high: {alloc.total_exposure_pct:.1f}%")

        # Total risk
        if alloc.total_risk_pct > 10:
            violations.append(f"Total risk too high: {alloc.total_risk_pct:.1f}%")

        # Volatility
        if alloc.portfolio_volatility > TARGET_VOLATILITY * 1.5:
            violations.append(f"Volatility too high: {alloc.portfolio_volatility:.1%}")

        # Position limits
        for pos in alloc.positions:
            if pos.position_pct > MAX_POSITION_PCT * 100:
                violations.append(f"{pos.symbol} exceeds max position: {pos.position_pct:.1f}%")

        return {
            "within_limits": len(violations) == 0,
            "violations": violations,
            "warnings": [],
            "allocation": alloc
        }

    def update_equity(self, new_value: float):
        """Update equity curve for tracking."""
        self.equity_curve.append(new_value)

    def get_drawdown(self) -> float:
        """Compute current drawdown."""
        if len(self.equity_curve) < 2:
            return 0.0

        peak = max(self.equity_curve)
        current = self.equity_curve[-1]

        return (peak - current) / peak * 100 if peak > 0 else 0.0

# -----------------------------------------------------------------------------
# Main / CLI
# -----------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dynamic Position Sizer")
    parser.add_argument("--portfolio", action="store_true", help="Run portfolio optimizer")
    parser.add_argument("--symbol", type=str, help="Symbol for sizing")
    parser.add_argument("--account", type=float, default=100000, help="Account size")
    args = parser.parse_args()

    print("Dynamic Position Sizer - Demo")
    print("=" * 60)

    # Create config
    config = PositionSizingConfig(account_size=100000)

    # Create risk manager
    rm = PortfolioRiskManager(config)

    # Add some positions
    positions_added = []

    positions_added.append(rm.add_position(
        symbol="BTC",
        direction="LONG",
        entry_price=65000,
        stop_loss_pct=1.5,
        confidence=0.85,
        avg_win_pct=3.0,
        avg_loss_pct=1.5,
        win_rate=0.58,
        realized_vol=0.60
    ))

    positions_added.append(rm.add_position(
        symbol="ETH",
        direction="LONG",
        entry_price=3500,
        stop_loss_pct=2.0,
        confidence=0.75,
        avg_win_pct=4.0,
        avg_loss_pct=2.0,
        win_rate=0.52,
        realized_vol=0.80
    ))

    positions_added.append(rm.add_position(
        symbol="SOL",
        direction="LONG",
        entry_price=180,
        stop_loss_pct=2.5,
        confidence=0.70,
        avg_win_pct=5.0,
        avg_loss_pct=2.5,
        win_rate=0.48,
        realized_vol=1.20
    ))

    print("\nPositions Added:")
    print("-" * 60)

    alloc = rm.get_portfolio_allocation()

    for pos in alloc.positions:
        print(f"\n{pos.symbol} ({pos.direction})")
        print(f"  Entry: ${pos.entry_price:,.2f}")
        print(f"  Size: ${pos.position_size:,.2f} ({pos.position_pct:.1f}%)")
        print(f"  Stop Loss: {pos.stop_loss_pct:.1f}%")
        print(f"  Risk: ${pos.risk_amount:,.2f} ({pos.position_size * pos.stop_loss_pct / 100 / config.account_size * 100:.2f}%)")
        print(f"  Kelly: {pos.kelly_fraction*100:.1f}%")
        print(f"  Confidence: {pos.confidence*100:.0f}%")
        print(f"  Vol Adj: {pos.vol_adjustment:.2f}")
        print(f"  Expected Return: {pos.expected_return:.3f}%")

    print("\n" + "=" * 60)
    print("Portfolio Summary:")
    print("-" * 60)
    print(f"Total Exposure: {alloc.total_exposure_pct:.1f}%")
    print(f"Total Risk: {alloc.total_risk_pct:.2f}%")
    print(f"Portfolio Volatility: {alloc.portfolio_volatility:.1%}")
    print(f"Expected Return: {alloc.expected_return:.3f}%")
    print(f"Sharpe Contribution: {alloc.sharpe_contribution:.2f}")
    print(f"Current Drawdown: {rm.get_drawdown():.2f}%")

    print("\n" + "=" * 60)
    print("Risk Limit Check:")
    print("-" * 60)
    limits = rm.check_risk_limits()
    print(f"Within Limits: {limits['within_limits']}")
    if limits['violations']:
        print("Violations:")
        for v in limits['violations']:
            print(f"  - {v}")
    else:
        print("No violations - portfolio is within risk limits")

if __name__ == "__main__":
    main()
