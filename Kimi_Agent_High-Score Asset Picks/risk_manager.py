#!/usr/bin/env python3
"""
Risk Management & Position Sizing Calculator
Multi-Asset Trading System
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TrustTier(Enum):
    SANDBOX = "sandbox"
    PROBATION = "probation"
    WATCH = "watch"
    PROVEN = "proven"

class DrawdownLevel(Enum):
    NONE = 0
    YELLOW = 5      # 5% drawdown
    ORANGE = 10     # 10% drawdown
    RED = 15        # 15% drawdown
    BLACKOUT = 20   # 20% drawdown

@dataclass
class PositionSizingConfig:
    """Configuration for position sizing"""
    portfolio_value: float = 10000.0
    base_risk_percent: float = 0.01  # 1%

    # Trust tier multipliers
    sandbox_mult: float = 0.25
    probation_mult: float = 0.50
    watch_mult: float = 0.75
    proven_mult: float = 1.50

    # Drawdown multipliers
    dd_yellow_mult: float = 0.75
    dd_orange_mult: float = 0.50
    dd_red_mult: float = 0.0
    dd_blackout_mult: float = 0.0

class RiskManager:
    """Main risk management class"""

    def __init__(self, config: Optional[PositionSizingConfig] = None):
        self.config = config or PositionSizingConfig()

    def get_score_multiplier(self, score: float) -> float:
        """Get position size multiplier based on signal score"""
        if score >= 85:
            return 1.00
        elif score >= 75:
            return 0.75
        elif score >= 65:
            return 0.50
        elif score >= 55:
            return 0.25
        else:
            return 0.0  # Do not trade

    def get_trust_multiplier(self, tier: TrustTier) -> float:
        """Get position size multiplier based on trust tier"""
        multipliers = {
            TrustTier.SANDBOX: self.config.sandbox_mult,
            TrustTier.PROBATION: self.config.probation_mult,
            TrustTier.WATCH: self.config.watch_mult,
            TrustTier.PROVEN: self.config.proven_mult
        }
        return multipliers.get(tier, 0.0)

    def get_drawdown_multiplier(self, drawdown_pct: float) -> float:
        """Get position size multiplier based on current drawdown"""
        if drawdown_pct >= 20:
            return self.config.dd_blackout_mult
        elif drawdown_pct >= 15:
            return self.config.dd_red_mult
        elif drawdown_pct >= 10:
            return self.config.dd_orange_mult
        elif drawdown_pct >= 5:
            return self.config.dd_yellow_mult
        else:
            return 1.0

    def get_min_rr_ratio(self, score: float) -> float:
        """Get minimum required R:R ratio based on score"""
        if score >= 85:
            return 1.33
        elif score >= 75:
            return 1.75
        elif score >= 65:
            return 2.00
        elif score >= 55:
            return 2.50
        else:
            return float('inf')  # Do not trade

    def calculate_position_size(
        self,
        score: float,
        tier: TrustTier,
        drawdown_pct: float = 0.0
    ) -> dict:
        """
        Calculate position size based on all risk factors

        Returns dict with:
            - position_size: dollar amount
            - percent_of_portfolio: percentage
            - score_mult: score multiplier used
            - trust_mult: trust multiplier used
            - dd_mult: drawdown multiplier used
            - should_trade: boolean indicating if trade is allowed
        """
        score_mult = self.get_score_multiplier(score)
        trust_mult = self.get_trust_multiplier(tier)
        dd_mult = self.get_drawdown_multiplier(drawdown_pct)

        # Calculate position size
        position_size = (
            self.config.portfolio_value *
            self.config.base_risk_percent *
            score_mult *
            trust_mult *
            dd_mult
        )

        percent = (position_size / self.config.portfolio_value) * 100
        should_trade = position_size > 0 and score >= 55

        return {
            "position_size": round(position_size, 2),
            "percent_of_portfolio": round(percent, 2),
            "score_mult": score_mult,
            "trust_mult": trust_mult,
            "dd_mult": dd_mult,
            "should_trade": should_trade,
            "min_rr_required": self.get_min_rr_ratio(score)
        }

    def check_loss_limits(
        self,
        daily_pnl_pct: float,
        weekly_pnl_pct: float,
        monthly_pnl_pct: float
    ) -> dict:
        """
        Check if loss limits have been breached

        Returns dict with:
            - breach_detected: boolean
            - breach_type: type of breach (daily/weekly/monthly/none)
            - action_required: recommended action
        """
        if monthly_pnl_pct <= -10:
            return {
                "breach_detected": True,
                "breach_type": "monthly",
                "action_required": "EMERGENCY: Close all positions, reassess strategy"
            }
        elif weekly_pnl_pct <= -5:
            return {
                "breach_detected": True,
                "breach_type": "weekly",
                "action_required": "REDUCE all positions 50%, halt new positions"
            }
        elif daily_pnl_pct <= -2:
            return {
                "breach_detected": True,
                "breach_type": "daily",
                "action_required": "HALT new positions for 24 hours"
            }
        else:
            return {
                "breach_detected": False,
                "breach_type": "none",
                "action_required": "Continue normal operations"
            }

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_fraction: float = 0.5
    ) -> dict:
        """
        Calculate Kelly criterion position size

        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount per winning trade
            avg_loss: Average loss amount per losing trade
            kelly_fraction: Fraction of Kelly to use (0.5 = Half-Kelly)

        Returns dict with:
            - full_kelly: Full Kelly fraction
            - fractional_kelly: Fractional Kelly fraction
            - percent_to_risk: Percentage of portfolio to risk
        """
        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss if avg_loss != 0 else 0

        if b == 0:
            return {
                "full_kelly": 0,
                "fractional_kelly": 0,
                "percent_to_risk": 0,
                "error": "Invalid avg_loss"
            }

        full_kelly = (b * p - q) / b
        full_kelly = max(0, full_kelly)  # Can't be negative

        fractional_kelly = full_kelly * kelly_fraction
        percent = fractional_kelly * 100

        return {
            "full_kelly": round(full_kelly, 4),
            "fractional_kelly": round(fractional_kelly, 4),
            "percent_to_risk": round(percent, 2)
        }


# Example usage
if __name__ == "__main__":
    # Initialize risk manager
    config = PositionSizingConfig(portfolio_value=10000)
    rm = RiskManager(config)

    print("=" * 60)
    print("RISK MANAGEMENT CALCULATOR - EXAMPLES")
    print("=" * 60)

    # Example 1: High score, proven tier, no drawdown
    result = rm.calculate_position_size(score=90, tier=TrustTier.PROVEN, drawdown_pct=0)
    print("\n1. High Score (90) + Proven + No Drawdown:")
    print(f"   Position Size: ${result['position_size']}")
    print(f"   % of Portfolio: {result['percent_of_portfolio']}%")
    print(f"   Should Trade: {result['should_trade']}")
    print(f"   Min R:R Required: {result['min_rr_required']}:1")

    # Example 2: Medium score, watch tier, 5% drawdown
    result = rm.calculate_position_size(score=70, tier=TrustTier.WATCH, drawdown_pct=5)
    print("\n2. Medium Score (70) + Watch + 5% Drawdown:")
    print(f"   Position Size: ${result['position_size']}")
    print(f"   % of Portfolio: {result['percent_of_portfolio']}%")
    print(f"   Should Trade: {result['should_trade']}")
    print(f"   Min R:R Required: {result['min_rr_required']}:1")

    # Example 3: Sandbox tier (any score)
    result = rm.calculate_position_size(score=80, tier=TrustTier.SANDBOX, drawdown_pct=0)
    print("\n3. Sandbox Tier (Score 80):")
    print(f"   Position Size: ${result['position_size']}")
    print(f"   % of Portfolio: {result['percent_of_portfolio']}%")
    print(f"   Should Trade: {result['should_trade']}")

    # Example 4: Kelly calculation
    kelly = rm.calculate_kelly_fraction(win_rate=0.55, avg_win=2.5, avg_loss=1.0)
    print("\n4. Kelly Criterion (55% win rate, 2.5:1 R:R):")
    print(f"   Full Kelly: {kelly['full_kelly']*100:.2f}%")
    print(f"   Half Kelly: {kelly['fractional_kelly']*100:.2f}%")
    print(f"   Recommended Risk: {kelly['percent_to_risk']}%")

    # Example 5: Loss limit check
    limits = rm.check_loss_limits(daily_pnl_pct=-2.5, weekly_pnl_pct=-4.0, monthly_pnl_pct=-6.0)
    print("\n5. Loss Limit Check (Daily: -2.5%, Weekly: -4%, Monthly: -6%):")
    print(f"   Breach Detected: {limits['breach_detected']}")
    print(f"   Breach Type: {limits['breach_type']}")
    print(f"   Action: {limits['action_required']}")
