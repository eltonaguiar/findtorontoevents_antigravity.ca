#!/usr/bin/env python3
"""
Volatility-Adjusted Position Sizing
Implements Kelly Criterion with volatility targeting.
"""

import numpy as np
from typing import Dict


class PositionSizer:
    """Advanced position sizing with risk controls."""
    
    def __init__(self,
                 target_volatility: float = 0.20,
                 max_position_pct: float = 0.10,
                 kelly_fraction: float = 0.25):
        self.target_volatility = target_volatility
        self.max_position_pct = max_position_pct
        self.kelly_fraction = kelly_fraction
    
    def calculate_kelly_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly Criterion position size."""
        if avg_loss == 0:
            return 0
        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        return max(0, kelly * self.kelly_fraction)
    
    def calculate_position_size(self,
                               portfolio_value: float,
                               entry_price: float,
                               stop_loss: float,
                               win_rate: float = 0.55,
                               avg_win: float = 0.03,
                               avg_loss: float = 0.02,
                               current_volatility: float = 0.25) -> Dict:
        """Calculate comprehensive position size."""
        kelly_size = self.calculate_kelly_size(win_rate, avg_win, avg_loss)
        adjustment = self.target_volatility / current_volatility if current_volatility > 0 else 0
        vol_adjusted = kelly_size * adjustment
        
        risk_per_trade = portfolio_value * vol_adjusted
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return {'error': 'Invalid stop loss'}
        
        quantity = risk_per_trade / price_risk
        position_value = quantity * entry_price
        position_pct = min(position_value / portfolio_value, self.max_position_pct)
        
        return {
            'quantity': quantity,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_per_trade,
            'kelly_size': kelly_size
        }


if __name__ == "__main__":
    sizer = PositionSizer()
    result = sizer.calculate_position_size(
        portfolio_value=100000,
        entry_price=85000,
        stop_loss=80000
    )
    print(f"Position: {result['position_pct']:.2%} of portfolio")
