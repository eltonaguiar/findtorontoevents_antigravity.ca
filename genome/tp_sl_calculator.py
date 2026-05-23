"""
Take Profit / Stop Loss Calculator

Calculates optimal TP/SL levels based on volatility (ATR), strategy DNA,
and Kelly criterion for position sizing.
"""

import json
import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskProfile(Enum):
    """Risk profile categories"""
    CONSERVATIVE = "conservative"
    MEDIUM = "medium"
    AGGRESSIVE = "aggressive"


@dataclass
class TPSLLevels:
    """Take Profit / Stop Loss levels"""
    take_profit: float
    stop_loss: float
    risk_reward: float
    position_size_pct: float
    confidence: float
    atr_used: float
    kelly_fraction: float


class TPSLCalculator:
    """
    Calculate optimal TP/SL levels for trading signals.
    
    Uses ATR-based volatility stops with risk profile adjustments
    and Kelly criterion for position sizing.
    """
    
    # Risk multipliers by profile
    RISK_MULTIPLIERS = {
        RiskProfile.CONSERVATIVE: 1.5,
        RiskProfile.MEDIUM: 2.0,
        RiskProfile.AGGRESSIVE: 3.0
    }
    
    # Default risk:reward ratios
    DEFAULT_RR_RATIO = 2.0
    MIN_RR_RATIO = 1.5
    TARGET_RR_RATIO = 2.5
    
    # Position sizing limits
    MAX_POSITION_PCT = 5.0  # Max 5% per trade
    KELLY_FRACTION = 0.25   # Use 25% of full Kelly
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the TP/SL calculator.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.max_position_pct = self.config.get('max_position_pct', self.MAX_POSITION_PCT)
        self.kelly_fraction = self.config.get('kelly_fraction', self.KELLY_FRACTION)
        self.default_rr = self.config.get('default_rr', self.DEFAULT_RR_RATIO)
    
    def calculate_levels(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        strategy_dna: Dict,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate TP/SL levels and position sizing.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            entry_price: Entry price for the trade
            direction: 'LONG' or 'SHORT'
            strategy_dna: Strategy DNA with risk profile and metrics
            market_data: Optional market data for ATR calculation
            
        Returns:
            Dict with take_profit, stop_loss, risk_reward, position_size_pct, confidence
        """
        # Get ATR (Average True Range) for volatility-based stops
        atr = self._get_atr(symbol, entry_price, market_data)
        
        # Determine risk profile
        risk_profile = self._get_risk_profile(strategy_dna)
        risk_mult = self.RISK_MULTIPLIERS.get(risk_profile, 2.0)
        
        # Get win rate and profit factor for dynamic adjustments
        win_rate = strategy_dna.get('win_rate', 0.55)
        avg_win = strategy_dna.get('avg_win_pct', 5.0)
        avg_loss = strategy_dna.get('avg_loss_pct', 2.5)
        
        # Calculate optimal R:R based on win rate
        optimal_rr = self._calculate_optimal_rr(win_rate, avg_win, avg_loss)
        
        # Calculate stop loss distance
        stop_distance = atr * risk_mult
        
        # Calculate TP/SL levels
        if direction.upper() == 'LONG':
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * optimal_rr)
        else:  # SHORT
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * optimal_rr)
        
        # Ensure stop loss is positive and reasonable
        stop_loss = max(stop_loss, entry_price * 0.5)  # Max 50% loss
        
        # Calculate Kelly criterion position size
        kelly = self._calculate_kelly(win_rate, avg_win, avg_loss)
        position_size_pct = min(kelly * 100, self.max_position_pct)
        
        # Calculate confidence based on R:R and win rate
        confidence = self._calculate_confidence(entry_price, stop_loss, take_profit, win_rate)
        
        # Round to appropriate precision based on price magnitude
        precision = self._get_price_precision(entry_price)
        
        return {
            'take_profit': round(take_profit, precision),
            'stop_loss': round(stop_loss, precision),
            'risk_reward': round(optimal_rr, 2),
            'position_size_pct': round(position_size_pct, 2),
            'confidence': round(confidence, 2),
            'atr_used': round(atr, precision),
            'kelly_fraction': round(kelly, 4)
        }
    
    def _get_atr(self, symbol: str, entry_price: float, market_data: Optional[Dict] = None) -> float:
        """
        Get ATR (Average True Range) for volatility calculation.
        
        In production, this would fetch from market data API.
        For now, use simulated values based on symbol.
        Returns absolute price value (not percentage).
        """
        if market_data and 'atr_14' in market_data:
            return market_data['atr_14']
        
        # Simulated ATR percentages based on typical crypto volatility
        atr_pct_map = {
            'BTC': 0.025,   # ~2.5% daily ATR
            'ETH': 0.035,   # ~3.5% daily ATR
            'SOL': 0.055,   # ~5.5% daily ATR
            'ADA': 0.045,
            'DOT': 0.050,
            'LINK': 0.060,
            'MATIC': 0.065,
            'AVAX': 0.070,
            'UNI': 0.080,
            'ATOM': 0.075
        }
        
        # Extract base asset from symbol
        base = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
        default_atr_pct = 0.05  # 5% default
        
        atr_pct = atr_pct_map.get(base, default_atr_pct)
        
        # Convert percentage to absolute price value
        return entry_price * atr_pct
    
    def _get_risk_profile(self, strategy_dna: Dict) -> RiskProfile:
        """Extract risk profile from strategy DNA."""
        profile_str = strategy_dna.get('risk_profile', 'medium').lower()
        try:
            return RiskProfile(profile_str)
        except ValueError:
            return RiskProfile.MEDIUM
    
    def _calculate_optimal_rr(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate optimal risk:reward ratio based on win rate.
        
        Uses the formula: Optimal R:R = (Win% / Loss%) * (Avg Win / Avg Loss)
        """
        loss_rate = 1 - win_rate
        if loss_rate == 0 or avg_loss == 0:
            return self.TARGET_RR_RATIO
        
        # Kelly-based optimal R:R
        kelly_rr = (win_rate / loss_rate) * (avg_win / avg_loss)
        
        # Clamp between min and target
        return max(self.MIN_RR_RATIO, min(kelly_rr, self.TARGET_RR_RATIO * 1.5))
    
    def _calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly criterion fraction for position sizing.
        
        Kelly % = W - [(1 - W) / R]
        Where W = win rate, R = win/loss ratio
        """
        if avg_loss == 0:
            return 0.01  # Minimum position
        
        win_loss_ratio = avg_win / avg_loss
        if win_loss_ratio <= 0:
            return 0.01
        
        # Full Kelly calculation
        full_kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Apply Kelly fraction (conservative approach)
        fractional_kelly = full_kelly * self.kelly_fraction
        
        # Ensure positive and reasonable
        return max(0.01, min(fractional_kelly, 0.20))  # Cap at 20% even for Kelly
    
    def _calculate_confidence(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        win_rate: float
    ) -> float:
        """
        Calculate confidence score for the levels.
        
        Based on R:R ratio, distance to stops, and win rate.
        """
        # Calculate actual R:R
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return 0.5
        
        actual_rr = reward / risk
        
        # Score based on R:R adequacy
        if actual_rr >= 2.5:
            rr_score = 1.0
        elif actual_rr >= 2.0:
            rr_score = 0.9
        elif actual_rr >= 1.5:
            rr_score = 0.75
        else:
            rr_score = 0.5
        
        # Score based on win rate
        if win_rate >= 0.65:
            wr_score = 1.0
        elif win_rate >= 0.55:
            wr_score = 0.85
        elif win_rate >= 0.50:
            wr_score = 0.7
        else:
            wr_score = 0.5
        
        # Combined confidence
        return (rr_score * 0.6) + (wr_score * 0.4)
    
    def _get_price_precision(self, price: float) -> int:
        """Determine appropriate decimal precision based on price magnitude."""
        if price >= 10000:
            return 2
        elif price >= 1000:
            return 2
        elif price >= 100:
            return 3
        elif price >= 10:
            return 4
        elif price >= 1:
            return 5
        else:
            return 6
    
    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        activation_pct: float = 1.0,
        trail_pct: float = 2.0
    ) -> Optional[float]:
        """
        Calculate trailing stop level.
        
        Args:
            entry_price: Original entry price
            current_price: Current market price
            direction: 'LONG' or 'SHORT'
            activation_pct: Profit % to activate trailing stop
            trail_pct: Distance to trail behind price
            
        Returns:
            Trailing stop price or None if not activated
        """
        if direction.upper() == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            if profit_pct >= activation_pct:
                # Activate trailing stop
                trail_distance = current_price * (trail_pct / 100)
                return current_price - trail_distance
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            if profit_pct >= activation_pct:
                trail_distance = current_price * (trail_pct / 100)
                return current_price + trail_distance
        
        return None
    
    def calculate_breakeven_stop(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        min_profit_pct: float = 1.0
    ) -> Optional[float]:
        """
        Calculate breakeven stop level.
        
        Moves stop to entry + small buffer once minimum profit is reached.
        """
        if direction.upper() == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price * 100
            if profit_pct >= min_profit_pct:
                buffer = entry_price * 0.001  # 0.1% buffer
                return entry_price + buffer
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price * 100
            if profit_pct >= min_profit_pct:
                buffer = entry_price * 0.001
                return entry_price - buffer
        
        return None
    
    def adjust_for_correlation(
        self,
        base_levels: Dict,
        correlation_with_portfolio: float
    ) -> Dict:
        """
        Adjust position size based on portfolio correlation.
        
        Reduces size for highly correlated positions.
        """
        adjusted = base_levels.copy()
        
        if correlation_with_portfolio > 0.8:
            # Highly correlated - reduce by 50%
            adjusted['position_size_pct'] *= 0.5
        elif correlation_with_portfolio > 0.6:
            # Moderately correlated - reduce by 25%
            adjusted['position_size_pct'] *= 0.75
        elif correlation_with_portfolio > 0.4:
            # Slightly correlated - reduce by 10%
            adjusted['position_size_pct'] *= 0.9
        
        adjusted['position_size_pct'] = round(adjusted['position_size_pct'], 2)
        adjusted['correlation_adjusted'] = True
        adjusted['correlation_factor'] = correlation_with_portfolio
        
        return adjusted


# Example usage
if __name__ == '__main__':
    calculator = TPSLCalculator()
    
    # Test LONG position
    test_dna = {
        'risk_profile': 'medium',
        'win_rate': 0.65,
        'avg_win_pct': 8.5,
        'avg_loss_pct': 3.2
    }
    
    result = calculator.calculate_levels(
        symbol='BTCUSDT',
        entry_price=85000.00,
        direction='LONG',
        strategy_dna=test_dna
    )
    
    print("=" * 60)
    print("TP/SL CALCULATION RESULT - LONG BTC")
    print("=" * 60)
    print(f"Entry Price: $85,000.00")
    print(f"Take Profit: ${result['take_profit']:,}")
    print(f"Stop Loss: ${result['stop_loss']:,}")
    print(f"Risk:Reward: 1:{result['risk_reward']}")
    print(f"Position Size: {result['position_size_pct']}%")
    print(f"Confidence: {result['confidence']}")
    print(f"ATR Used: {result['atr_used']}")
    print(f"Kelly Fraction: {result['kelly_fraction']}")
    
    # Calculate potential profit/loss
    risk_amount = abs(85000 - result['stop_loss'])
    reward_amount = abs(result['take_profit'] - 85000)
    print(f"\nPotential Loss: ${risk_amount:,.2f} per unit")
    print(f"Potential Gain: ${reward_amount:,.2f} per unit")
    print("=" * 60)
    
    # Test SHORT position
    result_short = calculator.calculate_levels(
        symbol='ETHUSDT',
        entry_price=3200.00,
        direction='SHORT',
        strategy_dna=test_dna
    )
    
    print("\n" + "=" * 60)
    print("TP/SL CALCULATION RESULT - SHORT ETH")
    print("=" * 60)
    print(f"Entry Price: $3,200.00")
    print(f"Take Profit: ${result_short['take_profit']:,}")
    print(f"Stop Loss: ${result_short['stop_loss']:,}")
    print(f"Risk:Reward: 1:{result_short['risk_reward']}")
    print(f"Position Size: {result_short['position_size_pct']}%")
    print("=" * 60)
