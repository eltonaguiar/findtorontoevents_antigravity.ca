"""
Position Sizing

Kelly Criterion, risk-based sizing, and maximum exposure controls.
"Never risk more than 2% on momentum, up to 5% on Safe Bets."
"""
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""
    target_weight: float      # Portfolio weight [0, 1]
    target_shares: int        # Number of shares
    target_value: float       # Dollar value of position
    sizing_method: str        # Which method was used
    kelly_fraction: float     # Full Kelly fraction
    risk_amount: float        # Dollar amount at risk
    max_loss_pct: float       # Max loss as % of portfolio


class PositionSizer:
    """
    Position sizing engine implementing multiple methods.
    
    Methods:
    - Kelly Criterion (full and fractional)
    - Fixed percentage risk
    - Volatility targeting
    - Equal weight
    - Risk parity
    """

    def __init__(self, portfolio_value: float = 100000):
        from .. import config
        self.portfolio_value = portfolio_value
        self.max_position_pct = config.MAX_POSITION_PCT
        self.min_position_pct = config.MIN_POSITION_PCT
        self.max_sector_pct = config.MAX_SECTOR_PCT
        self.kelly_fraction = config.KELLY_FRACTION
        self.momentum_max_risk = config.MOMENTUM_MAX_RISK
        self.safe_bet_max_risk = config.SAFE_BET_MAX_RISK

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = None,
    ) -> float:
        """
        Kelly Criterion for optimal bet sizing.
        
        f* = (p * b - q) / b
        where p = win_rate, q = 1 - p, b = avg_win / avg_loss
        
        Returns fraction of portfolio to bet [0, max_position_pct].
        """
        if fraction is None:
            fraction = self.kelly_fraction

        if avg_loss <= 0 or avg_win <= 0:
            return self.min_position_pct

        p = min(max(win_rate, 0.01), 0.99)
        q = 1 - p
        b = avg_win / avg_loss

        kelly_full = (p * b - q) / b
        kelly_full = max(kelly_full, 0)

        # Apply fraction (quarter-Kelly for safety)
        kelly_fractional = kelly_full * fraction

        # Enforce limits
        return min(max(kelly_fractional, self.min_position_pct), self.max_position_pct)

    def fixed_risk_size(
        self,
        price: float,
        stop_loss_pct: float,
        risk_per_trade_pct: float = 0.02,
    ) -> PositionSizeResult:
        """
        Fixed percentage risk sizing.
        
        Determine position size so that hitting the stop loss = risk_per_trade_pct of portfolio.
        """
        risk_amount = self.portfolio_value * risk_per_trade_pct
        loss_per_share = price * stop_loss_pct

        if loss_per_share <= 0:
            shares = 0
            target_weight = 0
        else:
            shares = int(risk_amount / loss_per_share)
            target_value = shares * price
            target_weight = target_value / self.portfolio_value

        # Cap at max position
        if target_weight > self.max_position_pct:
            target_weight = self.max_position_pct
            target_value = self.portfolio_value * target_weight
            shares = int(target_value / price)

        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="fixed_risk",
            kelly_fraction=0,
            risk_amount=risk_amount,
            max_loss_pct=risk_per_trade_pct,
        )

    def volatility_target_size(
        self,
        price: float,
        annualized_vol: float,
        target_vol: float = 0.15,
    ) -> PositionSizeResult:
        """
        Volatility targeting: size positions inversely proportional to volatility.
        
        Higher vol → smaller position. Lower vol → bigger position.
        Target portfolio vol = target_vol.
        """
        if annualized_vol <= 0:
            annualized_vol = 0.20  # Default 20%

        # Weight = target_vol / stock_vol (inversely proportional)
        target_weight = target_vol / annualized_vol
        target_weight = min(max(target_weight, self.min_position_pct), self.max_position_pct)

        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="vol_target",
            kelly_fraction=0,
            risk_amount=target_value * annualized_vol,
            max_loss_pct=target_weight * annualized_vol,
        )

    def equal_weight_size(
        self,
        price: float,
        n_positions: int,
    ) -> PositionSizeResult:
        """Equal weight across all positions."""
        target_weight = min(1.0 / max(n_positions, 1), self.max_position_pct)
        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="equal_weight",
            kelly_fraction=0,
            risk_amount=target_value,
            max_loss_pct=target_weight,
        )

    def compute_position_size(
        self,
        price: float,
        signal_confidence: float,
        signal_category: str,
        stop_loss_pct: float = 0.10,
        annualized_vol: float = 0.25,
        n_positions: int = 20,
        win_rate: float = 0.55,
        avg_win: float = 0.08,
        avg_loss: float = 0.04,
    ) -> PositionSizeResult:
        """
        Master position sizing method that combines all approaches.
        
        For momentum trades: max 2% risk per trade.
        For safe bet / dividend aristocrats: up to 5% risk.
        Uses Kelly + vol targeting as inputs, takes the minimum.
        """
        # Determine risk budget based on category
        if signal_category in ["safe_bet", "dividend_aristocrat", "quality"]:
            max_risk = self.safe_bet_max_risk
        else:
            max_risk = self.momentum_max_risk

        # Method 1: Fixed risk
        risk_result = self.fixed_risk_size(price, stop_loss_pct, max_risk)

        # Method 2: Vol targeting
        vol_result = self.volatility_target_size(price, annualized_vol)

        # Method 3: Kelly
        kelly_weight = self.kelly_criterion(win_rate, avg_win, avg_loss)

        # Method 4: Equal weight (floor)
        eq_result = self.equal_weight_size(price, n_positions)

        # Take the minimum of risk-based and vol-based (conservative)
        target_weight = min(risk_result.target_weight, vol_result.target_weight)

        # Scale by confidence
        target_weight *= signal_confidence

        # Apply Kelly as upper bound
        target_weight = min(target_weight, kelly_weight)

        # Floor at equal weight (don't go below)
        target_weight = max(target_weight, self.min_position_pct)

        # Cap at max
        target_weight = min(target_weight, self.max_position_pct)

        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="composite",
            kelly_fraction=kelly_weight,
            risk_amount=target_value * stop_loss_pct,
            max_loss_pct=target_weight * stop_loss_pct,
        )
