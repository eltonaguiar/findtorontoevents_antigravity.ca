"""
Take Profit / Stop Loss Calculator V2 - ATR-Scaled with Dynamic R:R

Enhancements from V1:
1. ATR-scaled TP/SL (2.5x ATR TP, 1.5x ATR SL for ~1.67 R:R)
2. HMA trend filter integration
3. Regime-aware adjustments
4. Better handling for tight ranges
"""

import json
import math
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class RiskProfile(Enum):
    """Risk profile categories"""
    CONSERVATIVE = "conservative"
    MEDIUM = "medium"
    AGGRESSIVE = "aggressive"


class MarketRegime(Enum):
    """Market regime for adjustments"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CHOPPY = "choppy"


@dataclass
class TPSLConfig:
    """Configuration for TP/SL calculation"""
    atr_tp_mult: float = 2.5       # TP at 2.5x ATR
    atr_sl_mult: float = 1.5       # SL at 1.5x ATR
    min_rr_ratio: float = 1.5      # Minimum R:R
    target_rr_ratio: float = 2.0   # Target R:R
    max_position_pct: float = 5.0  # Max 5% per trade
    kelly_fraction: float = 0.25   # Conservative Kelly
    use_hma_filter: bool = True    # Enable HMA trend filter
    regime_adjust: bool = True     # Enable regime adjustments


class TPSLCalculatorV2:
    """
    Enhanced TP/SL calculator with ATR scaling and trend filters.
    
    Key formula:
    - Stop Loss = Entry ± (ATR × 1.5)
    - Take Profit = Entry ± (ATR × 2.5)
    - Resulting R:R ≈ 1.67:1 (2.5/1.5)
    
    Adjustments:
    - Trending markets: Wider stops (2x ATR) to avoid whipsaws
    - Ranging markets: Tighter stops (1.2x ATR) for quick exits
    - Volatile markets: Reduced position size, wider stops
    """
    
    def __init__(self, config: Optional[TPSLConfig] = None):
        """Initialize calculator with config."""
        self.config = config or TPSLConfig()
    
    def calculate_levels(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        strategy_dna: Dict,
        market_data: Optional[Dict] = None,
        hma_slope: Optional[int] = None
    ) -> Dict:
        """
        Calculate optimal TP/SL levels.
        
        Args:
            symbol: Trading pair
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            strategy_dna: Strategy configuration
            market_data: Market data including ATR
            hma_slope: HMA trend slope (+1 uptrend, -1 downtrend, 0 neutral)
            
        Returns:
            Dict with take_profit, stop_loss, risk_reward, etc.
        """
        direction = direction.upper()
        
        # Get ATR
        atr = self._get_atr(symbol, entry_price, market_data)
        
        # Get regime
        regime = self._detect_regime(market_data)
        
        # Calculate multipliers based on regime
        tp_mult, sl_mult = self._get_regime_multipliers(regime)
        
        # Apply HMA filter if enabled
        if self.config.use_hma_filter and hma_slope is not None:
            tp_mult, sl_mult = self._apply_hma_adjustment(
                tp_mult, sl_mult, direction, hma_slope
            )
        
        # Calculate distances
        tp_distance = atr * tp_mult
        sl_distance = atr * sl_mult
        
        # Calculate levels
        if direction == 'LONG':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # SHORT
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Ensure stop is reasonable (max 50% loss)
        if direction == 'LONG':
            stop_loss = max(stop_loss, entry_price * 0.5)
        else:
            stop_loss = min(stop_loss, entry_price * 1.5)
        
        # Calculate actual R:R
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        actual_rr = reward / risk if risk > 0 else 0
        
        # Adjust if R:R is below minimum
        if actual_rr < self.config.min_rr_ratio:
            take_profit = self._adjust_for_min_rr(
                entry_price, stop_loss, direction, self.config.min_rr_ratio
            )
            reward = abs(take_profit - entry_price)
            actual_rr = reward / risk
        
        # Position sizing with Kelly
        win_rate = strategy_dna.get('win_rate', 0.55)
        avg_win = strategy_dna.get('avg_win_pct', 5.0)
        avg_loss = strategy_dna.get('avg_loss_pct', 2.5)
        
        kelly = self._calculate_kelly(win_rate, avg_win, avg_loss)
        position_size_pct = min(kelly * 100, self.config.max_position_pct)
        
        # Reduce size in volatile/choppy regimes
        if regime in [MarketRegime.VOLATILE, MarketRegime.CHOPPY]:
            position_size_pct *= 0.7
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            entry_price, stop_loss, take_profit, win_rate, regime
        )
        
        precision = self._get_price_precision(entry_price)
        
        return {
            'take_profit': round(take_profit, precision),
            'stop_loss': round(stop_loss, precision),
            'risk_reward': round(actual_rr, 2),
            'position_size_pct': round(position_size_pct, 2),
            'confidence': round(confidence, 2),
            'atr_used': round(atr, precision),
            'atr_tp_mult': tp_mult,
            'atr_sl_mult': sl_mult,
            'kelly_fraction': round(kelly, 4),
            'regime': regime.value,
            'hma_filtered': self.config.use_hma_filter and hma_slope is not None
        }
    
    def _get_atr(self, symbol: str, entry_price: float, market_data: Optional[Dict]) -> float:
        """Get ATR value."""
        if market_data and 'atr_14' in market_data:
            return market_data['atr_14']
        
        if market_data and 'atr_pct_14' in market_data:
            return entry_price * market_data['atr_pct_14']
        
        # Default ATR percentages by asset type
        base = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
        
        atr_pct_map = {
            'BTC': 0.025,
            'ETH': 0.035,
            'SOL': 0.055,
            'BNB': 0.04,
            'ADA': 0.045,
            'DOT': 0.050,
            'LINK': 0.060,
            'MATIC': 0.065,
            'AVAX': 0.070,
            'UNI': 0.080,
            'ATOM': 0.075,
            'XRP': 0.04,
            'DOGE': 0.06,
        }
        
        atr_pct = atr_pct_map.get(base, 0.05)
        return entry_price * atr_pct
    
    def _detect_regime(self, market_data: Optional[Dict]) -> MarketRegime:
        """Detect market regime from data."""
        if not market_data:
            return MarketRegime.RANGING
        
        volatility = market_data.get('volatility_24h', 0.05)
        adx = market_data.get('adx', 25)
        
        if volatility > 0.10:
            if adx > 30:
                return MarketRegime.VOLATILE
            else:
                return MarketRegime.CHOPPY
        elif adx > 30:
            # Trending - determine direction from price action
            price_change = market_data.get('price_change_24h', 0)
            if price_change > 0.05:
                return MarketRegime.TRENDING_BULL
            elif price_change < -0.05:
                return MarketRegime.TRENDING_BEAR
            else:
                return MarketRegime.RANGING
        elif adx < 20:
            return MarketRegime.RANGING
        else:
            return MarketRegime.RANGING
    
    def _get_regime_multipliers(self, regime: MarketRegime) -> Tuple[float, float]:
        """Get ATR multipliers based on regime."""
        multipliers = {
            MarketRegime.TRENDING_BULL: (3.0, 2.0),   # Wider for trend following
            MarketRegime.TRENDING_BEAR: (3.0, 2.0),
            MarketRegime.RANGING: (2.0, 1.2),         # Tighter for ranges
            MarketRegime.VOLATILE: (2.5, 2.0),        # Wider stops in volatility
            MarketRegime.CHOPPY: (2.0, 1.0),          # Very tight in chop
        }
        return multipliers.get(regime, (2.5, 1.5))
    
    def _apply_hma_adjustment(
        self,
        tp_mult: float,
        sl_mult: float,
        direction: str,
        hma_slope: int
    ) -> Tuple[float, float]:
        """
        Adjust multipliers based on HMA trend.
        
        HMA slope: +1 (uptrend), -1 (downtrend), 0 (neutral)
        """
        if direction == 'LONG':
            if hma_slope > 0:  # Uptrend - normal sizing
                return tp_mult, sl_mult
            elif hma_slope < 0:  # Downtrend - tighter stops, reduce size
                return tp_mult * 0.8, sl_mult * 0.7
            else:  # Neutral
                return tp_mult * 0.9, sl_mult * 0.9
        else:  # SHORT
            if hma_slope < 0:  # Downtrend - normal sizing
                return tp_mult, sl_mult
            elif hma_slope > 0:  # Uptrend - tighter stops, reduce size
                return tp_mult * 0.8, sl_mult * 0.7
            else:  # Neutral
                return tp_mult * 0.9, sl_mult * 0.9
    
    def _adjust_for_min_rr(
        self,
        entry: float,
        stop: float,
        direction: str,
        min_rr: float
    ) -> float:
        """Adjust take profit to meet minimum R:R."""
        risk = abs(entry - stop)
        min_reward = risk * min_rr
        
        if direction == 'LONG':
            return entry + min_reward
        else:
            return entry - min_reward
    
    def _calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly criterion fraction."""
        if avg_loss <= 0:
            return 0.01
        
        win_loss_ratio = avg_win / avg_loss
        if win_loss_ratio <= 0:
            return 0.01
        
        full_kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        fractional_kelly = full_kelly * self.config.kelly_fraction
        
        return max(0.01, min(fractional_kelly, 0.20))
    
    def _calculate_confidence(
        self,
        entry: float,
        stop: float,
        take_profit: float,
        win_rate: float,
        regime: MarketRegime
    ) -> float:
        """Calculate confidence score."""
        risk = abs(entry - stop)
        reward = abs(take_profit - entry)
        
        if risk == 0:
            return 0.5
        
        actual_rr = reward / risk
        
        # R:R score
        if actual_rr >= 2.5:
            rr_score = 1.0
        elif actual_rr >= 2.0:
            rr_score = 0.9
        elif actual_rr >= 1.5:
            rr_score = 0.75
        else:
            rr_score = 0.5
        
        # Win rate score
        if win_rate >= 0.65:
            wr_score = 1.0
        elif win_rate >= 0.55:
            wr_score = 0.85
        elif win_rate >= 0.50:
            wr_score = 0.7
        else:
            wr_score = 0.5
        
        # Regime adjustment
        if regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            regime_mult = 1.1
        elif regime == MarketRegime.RANGING:
            regime_mult = 0.95
        else:  # Volatile/Choppy
            regime_mult = 0.85
        
        return min(1.0, (rr_score * 0.6 + wr_score * 0.4) * regime_mult)
    
    def _get_price_precision(self, price: float) -> int:
        """Determine decimal precision."""
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
        entry: float,
        current: float,
        direction: str,
        activation_pct: float = 1.0,
        trail_atr_mult: float = 1.5,
        atr: Optional[float] = None
    ) -> Optional[float]:
        """Calculate trailing stop based on ATR."""
        if atr is None:
            atr = entry * 0.03  # Default 3%
        
        trail_distance = atr * trail_atr_mult
        
        if direction.upper() == 'LONG':
            profit_pct = (current - entry) / entry * 100
            if profit_pct >= activation_pct:
                return current - trail_distance
        else:
            profit_pct = (entry - current) / entry * 100
            if profit_pct >= activation_pct:
                return current + trail_distance
        
        return None


if __name__ == '__main__':
    calc = TPSLCalculatorV2()
    
    # Test LONG in trending bull
    result1 = calc.calculate_levels(
        symbol='BTCUSDT',
        entry_price=85000,
        direction='LONG',
        strategy_dna={'win_rate': 0.65, 'avg_win_pct': 8, 'avg_loss_pct': 4},
        market_data={'volatility_24h': 0.04, 'adx': 35, 'price_change_24h': 0.08},
        hma_slope=1
    )
    
    print("=" * 60)
    print("V2 ATR-SCALED TP/SL - LONG BTC (Trending Bull)")
    print("=" * 60)
    print(f"Entry: $85,000")
    print(f"Take Profit: ${result1['take_profit']:,} ({result1['atr_tp_mult']}x ATR)")
    print(f"Stop Loss: ${result1['stop_loss']:,} ({result1['atr_sl_mult']}x ATR)")
    print(f"Risk:Reward: 1:{result1['risk_reward']}")
    print(f"Position Size: {result1['position_size_pct']}%")
    print(f"Regime: {result1['regime']}")
    print(f"ATR Used: ${result1['atr_used']:,.2f}")
    
    # Test SHORT in ranging market
    result2 = calc.calculate_levels(
        symbol='ETHUSDT',
        entry_price=3200,
        direction='SHORT',
        strategy_dna={'win_rate': 0.60, 'avg_win_pct': 6, 'avg_loss_pct': 3},
        market_data={'volatility_24h': 0.03, 'adx': 18},
        hma_slope=0
    )
    
    print("\n" + "=" * 60)
    print("V2 ATR-SCALED TP/SL - SHORT ETH (Ranging)")
    print("=" * 60)
    print(f"Entry: $3,200")
    print(f"Take Profit: ${result2['take_profit']:,} ({result2['atr_tp_mult']}x ATR)")
    print(f"Stop Loss: ${result2['stop_loss']:,} ({result2['atr_sl_mult']}x ATR)")
    print(f"Risk:Reward: 1:{result2['risk_reward']}")
    print(f"Position Size: {result2['position_size_pct']}%")
    print(f"Regime: {result2['regime']}")
    print("=" * 60)
