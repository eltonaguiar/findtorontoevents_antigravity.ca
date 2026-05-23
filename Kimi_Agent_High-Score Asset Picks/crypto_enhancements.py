"""
Crypto High-Certainty Enhancements - Implementation Module
==========================================================

This module provides crypto-specific alpha factors, filters, and strategies
to improve win rates and risk-adjusted returns in cryptocurrency trading.

Author: Crypto Trading Specialist
Date: 2026-04-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class VolatilityRegime(Enum):
    LOW_VOL = "low_volatility"
    NORMAL_VOL = "normal_volatility"
    HIGH_VOL = "high_volatility"
    EXTREME_VOL = "extreme_volatility"


class LiquidityTier(Enum):
    TIER_1 = 1  # >$500M daily volume
    TIER_2 = 2  # $100M-$500M
    TIER_3 = 3  # $30M-$100M
    TIER_4 = 4  # $10M-$30M
    TIER_5 = 5  # $3M-$10M
    REJECT = 6  # <$3M


@dataclass
class CryptoPick:
    """Data class for crypto pick analysis"""
    symbol: str
    price: float
    volume_24h: float
    quote_volume_24h: float
    trade_count_24h: int
    price_change_24h: float
    funding_rate: float = 0.0
    confluence_count: int = 0
    

class CryptoLiquidityFilter:
    """
    Liquidity-based filtering system for crypto picks
    """
    
    TIER_THRESHOLDS = {
        LiquidityTier.TIER_1: 500_000_000,   # $500M+
        LiquidityTier.TIER_2: 100_000_000,   # $100M+
        LiquidityTier.TIER_3: 30_000_000,    # $30M+
        LiquidityTier.TIER_4: 10_000_000,    # $10M+
        LiquidityTier.TIER_5: 3_000_000,     # $3M+
    }
    
    POSITION_SIZES = {
        LiquidityTier.TIER_1: 1.0,    # Full size
        LiquidityTier.TIER_2: 0.8,    # 80%
        LiquidityTier.TIER_3: 0.5,    # 50%
        LiquidityTier.TIER_4: 0.25,   # 25%
        LiquidityTier.TIER_5: 0.1,    # 10%
        LiquidityTier.REJECT: 0.0,    # 0% - reject
    }
    
    def get_liquidity_tier(self, quote_volume_24h: float) -> LiquidityTier:
        """Determine liquidity tier based on 24h quote volume"""
        if quote_volume_24h >= self.TIER_THRESHOLDS[LiquidityTier.TIER_1]:
            return LiquidityTier.TIER_1
        elif quote_volume_24h >= self.TIER_THRESHOLDS[LiquidityTier.TIER_2]:
            return LiquidityTier.TIER_2
        elif quote_volume_24h >= self.TIER_THRESHOLDS[LiquidityTier.TIER_3]:
            return LiquidityTier.TIER_3
        elif quote_volume_24h >= self.TIER_THRESHOLDS[LiquidityTier.TIER_4]:
            return LiquidityTier.TIER_4
        elif quote_volume_24h >= self.TIER_THRESHOLDS[LiquidityTier.TIER_5]:
            return LiquidityTier.TIER_5
        else:
            return LiquidityTier.REJECT
    
    def get_position_size_multiplier(self, tier: LiquidityTier) -> float:
        """Get position size multiplier for liquidity tier"""
        return self.POSITION_SIZES[tier]
    
    def filter_pick(self, pick: CryptoPick) -> Dict:
        """Analyze a pick and return filter results"""
        tier = self.get_liquidity_tier(pick.quote_volume_24h)
        size_mult = self.get_position_size_multiplier(tier)
        
        return {
            'symbol': pick.symbol,
            'tier': tier.name,
            'tier_number': tier.value,
            'quote_volume_m': pick.quote_volume_24h / 1_000_000,
            'position_size_multiplier': size_mult,
            'is_tradeable': tier != LiquidityTier.REJECT,
            'recommendation': self._get_recommendation(tier)
        }
    
    def _get_recommendation(self, tier: LiquidityTier) -> str:
        recommendations = {
            LiquidityTier.TIER_1: "HOLD - Excellent liquidity",
            LiquidityTier.TIER_2: "HOLD - Good liquidity",
            LiquidityTier.TIER_3: "REDUCE 25-50% - Monitor closely",
            LiquidityTier.TIER_4: "REDUCE 50-75% - Higher risk",
            LiquidityTier.TIER_5: "REDUCE 75-90% - Minimal size only",
            LiquidityTier.REJECT: "CLOSE - Insufficient liquidity"
        }
        return recommendations[tier]


class FundingRateAnalyzer:
    """
    Funding rate analysis for crypto alpha generation
    """
    
    def calculate_funding_score(self, funding_rate: float) -> Dict:
        """
        Calculate funding-based trading signal
        
        Args:
            funding_rate: 8-hour funding rate (e.g., 0.0001 = 0.01%)
            
        Returns:
            Dictionary with signal, score, and recommendation
        """
        funding_pct = funding_rate * 100  # Convert to percentage
        
        # Extreme negative funding = bullish signal (longs get paid)
        if funding_pct < -0.08:
            return {
                'signal': 'LONG',
                'strength': 'EXTREME',
                'score': 20,
                'edge': abs(funding_pct),
                'rationale': f'Funding {funding_pct:.4f}% - extremely negative, contrarian long'
            }
        elif funding_pct < -0.05:
            return {
                'signal': 'LONG',
                'strength': 'HIGH',
                'score': 16,
                'edge': abs(funding_pct),
                'rationale': f'Funding {funding_pct:.4f}% - very negative, long bias'
            }
        elif funding_pct < -0.02:
            return {
                'signal': 'LONG',
                'strength': 'MODERATE',
                'score': 12,
                'edge': abs(funding_pct),
                'rationale': f'Funding {funding_pct:.4f}% - negative, slight long bias'
            }
        # Extreme positive funding = bearish signal (shorts get paid)
        elif funding_pct > 0.10:
            return {
                'signal': 'SHORT',
                'strength': 'EXTREME',
                'score': 20,
                'edge': funding_pct,
                'rationale': f'Funding {funding_pct:.4f}% - extremely positive, contrarian short'
            }
        elif funding_pct > 0.06:
            return {
                'signal': 'SHORT',
                'strength': 'HIGH',
                'score': 16,
                'edge': funding_pct,
                'rationale': f'Funding {funding_pct:.4f}% - very positive, short bias'
            }
        elif funding_pct > 0.03:
            return {
                'signal': 'SHORT',
                'strength': 'MODERATE',
                'score': 12,
                'edge': funding_pct,
                'rationale': f'Funding {funding_pct:.4f}% - positive, slight short bias'
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'strength': 'NONE',
                'score': 5,
                'edge': 0,
                'rationale': f'Funding {funding_pct:.4f}% - neutral, no edge'
            }
    
    def get_funding_reversion_signal(self, 
                                     current_funding: float,
                                     funding_history: List[float]) -> Dict:
        """
        Generate funding rate reversion signal
        
        Args:
            current_funding: Current 8h funding rate
            funding_history: List of historical funding rates (30 days)
            
        Returns:
            Trading signal dictionary
        """
        if len(funding_history) < 30:
            return {'signal': 'NONE', 'reason': 'Insufficient history'}
        
        percentile = np.percentile(funding_history, [5, 50, 95])
        
        if current_funding > percentile[2]:  # >95th percentile
            return {
                'signal': 'SHORT',
                'confidence': 'HIGH',
                'percentile': 95 + (current_funding - percentile[2]) / (percentile[2] - percentile[1]) * 5,
                'expected_reversion': percentile[1],
                'max_hold_hours': 48
            }
        elif current_funding < percentile[0]:  # <5th percentile
            return {
                'signal': 'LONG',
                'confidence': 'HIGH',
                'percentile': 5 - (percentile[0] - current_funding) / (percentile[1] - percentile[0]) * 5,
                'expected_reversion': percentile[1],
                'max_hold_hours': 48
            }
        else:
            return {
                'signal': 'NONE',
                'confidence': 'NA',
                'percentile': 50,
                'reason': 'Funding within normal range'
            }


class VolatilityRegimeDetector:
    """
    Detect and respond to volatility regimes in crypto markets
    """
    
    def detect_regime(self, prices: pd.Series) -> VolatilityRegime:
        """
        Detect current volatility regime from price series
        
        Args:
            prices: Series of closing prices
            
        Returns:
            VolatilityRegime enum value
        """
        # Calculate 14-day ATR
        high = prices.rolling(14).max()
        low = prices.rolling(14).min()
        close = prices
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean()
        
        # Calculate ATR as percentage of price
        current_price = prices.iloc[-1]
        atr_pct = (atr_14.iloc[-1] / current_price) * 100
        
        if atr_pct < 3.0:
            return VolatilityRegime.LOW_VOL
        elif atr_pct < 6.0:
            return VolatilityRegime.NORMAL_VOL
        elif atr_pct < 10.0:
            return VolatilityRegime.HIGH_VOL
        else:
            return VolatilityRegime.EXTREME_VOL
    
    def get_regime_adjustments(self, regime: VolatilityRegime) -> Dict:
        """
        Get position sizing and strategy adjustments for regime
        """
        adjustments = {
            VolatilityRegime.LOW_VOL: {
                'position_size_mult': 1.5,
                'stop_loss_mult': 2.0,  # Wider stops
                'strategy_type': 'mean_reversion',
                'max_positions': 10,
                'description': 'Low volatility - favor mean reversion'
            },
            VolatilityRegime.NORMAL_VOL: {
                'position_size_mult': 1.0,
                'stop_loss_mult': 1.5,
                'strategy_type': 'trend_following',
                'max_positions': 8,
                'description': 'Normal volatility - trend following'
            },
            VolatilityRegime.HIGH_VOL: {
                'position_size_mult': 0.6,
                'stop_loss_mult': 1.0,  # Tighter stops
                'strategy_type': 'momentum',
                'max_positions': 5,
                'description': 'High volatility - momentum only, tight stops'
            },
            VolatilityRegime.EXTREME_VOL: {
                'position_size_mult': 0.3,
                'stop_loss_mult': 0.8,  # Very tight stops
                'strategy_type': 'scalping',
                'max_positions': 3,
                'description': 'Extreme volatility - scalp only or avoid'
            }
        }
        return adjustments[regime]


class HighCertaintyCryptoScore:
    """
    Calculate High-Certainty Crypto Score (HCCS) for picks
    """
    
    WEIGHTS = {
        'technical': 0.30,
        'funding': 0.20,
        'liquidity': 0.15,
        'on_chain': 0.15,
        'vol_fit': 0.10,
        'flow': 0.10
    }
    
    def __init__(self):
        self.liquidity_filter = CryptoLiquidityFilter()
        self.funding_analyzer = FundingRateAnalyzer()
    
    def calculate_score(self, pick: CryptoPick, 
                        on_chain_score: float = 50,
                        vol_fit_score: float = 50,
                        flow_score: float = 50) -> Dict:
        """
        Calculate comprehensive HCCS score
        
        Args:
            pick: CryptoPick object
            on_chain_score: 0-100 on-chain metric score
            vol_fit_score: 0-100 volatility regime fit score
            flow_score: 0-100 exchange flow score
            
        Returns:
            Dictionary with total score and component breakdown
        """
        # Technical score (based on confluence)
        technical_score = min(pick.confluence_count * 5, 30)
        
        # Funding score
        funding_result = self.funding_analyzer.calculate_funding_score(pick.funding_rate)
        funding_score = funding_result['score']
        
        # Liquidity score
        tier = self.liquidity_filter.get_liquidity_tier(pick.quote_volume_24h)
        liquidity_scores = {
            LiquidityTier.TIER_1: 15,
            LiquidityTier.TIER_2: 13,
            LiquidityTier.TIER_3: 10,
            LiquidityTier.TIER_4: 7,
            LiquidityTier.TIER_5: 4,
            LiquidityTier.REJECT: 0
        }
        liquidity_score = liquidity_scores[tier]
        
        # Calculate weighted total
        total_score = (
            technical_score * self.WEIGHTS['technical'] +
            funding_score * self.WEIGHTS['funding'] +
            liquidity_score * self.WEIGHTS['liquidity'] +
            on_chain_score * self.WEIGHTS['on_chain'] +
            vol_fit_score * self.WEIGHTS['vol_fit'] +
            flow_score * self.WEIGHTS['flow']
        )
        
        return {
            'total_score': round(total_score, 1),
            'certainty_level': self._get_certainty_level(total_score),
            'components': {
                'technical': round(technical_score, 1),
                'funding': round(funding_score, 1),
                'liquidity': round(liquidity_score, 1),
                'on_chain': round(on_chain_score, 1),
                'vol_fit': round(vol_fit_score, 1),
                'flow': round(flow_score, 1)
            },
            'recommendation': self._get_recommendation(total_score)
        }
    
    def _get_certainty_level(self, score: float) -> str:
        if score >= 85:
            return "EXTREME"
        elif score >= 75:
            return "HIGH"
        elif score >= 65:
            return "MEDIUM"
        elif score >= 50:
            return "LOW"
        else:
            return "AVOID"
    
    def _get_recommendation(self, score: float) -> str:
        if score >= 85:
            return "EXTREME CERTAINTY - 2.0x position size"
        elif score >= 75:
            return "HIGH CERTAINTY - 1.5x position size"
        elif score >= 65:
            return "MEDIUM CERTAINTY - 1.0x position size"
        elif score >= 50:
            return "LOW CERTAINTY - 0.5x position size"
        else:
            return "AVOID - Do not trade"


class CryptoStrategyFundingReversion:
    """
    Strategy 1: Funding Rate Reversion
    Exploit extreme funding rates that historically revert
    """
    
    def __init__(self):
        self.funding_analyzer = FundingRateAnalyzer()
    
    def generate_signal(self, symbol: str, 
                        current_funding: float,
                        funding_history: List[float]) -> Dict:
        """
        Generate funding reversion trading signal
        
        Returns:
            Signal dictionary with entry, exit, and sizing info
        """
        signal = self.funding_analyzer.get_funding_reversion_signal(
            current_funding, funding_history
        )
        
        if signal['signal'] == 'NONE':
            return signal
        
        # Add position management parameters
        signal.update({
            'position_size': 1.5,  # 1.5x normal size (high edge)
            'stop_loss_atr': 1.5,  # 1.5x ATR
            'take_profit_when': 'funding_returns_to_50th_percentile',
            'max_hold_hours': 48,
            'expected_win_rate': '60-70%',
            'expected_profit_factor': 2.0
        })
        
        return signal


class CryptoStrategyOnChainMomentum:
    """
    Strategy 2: On-Chain Momentum
    Combine on-chain accumulation with technical breakout
    """
    
    def generate_signal(self, symbol: str,
                        netflow_24h: float,
                        whale_buying_7d: float,
                        address_growth_7d: float,
                        price_above_20ema: bool,
                        volume_spike: bool) -> Dict:
        """
        Generate on-chain momentum signal
        
        Args:
            netflow_24h: Exchange netflow (negative = outflow/bullish)
            whale_buying_7d: Whale accumulation in USD
            address_growth_7d: Active address growth %
            price_above_20ema: Price above 20 EMA
            volume_spike: Volume > 1.5x 20-day average
            
        Returns:
            Signal dictionary
        """
        # Calculate on-chain score
        score = 0
        details = []
        
        if netflow_24h < -5_000_000:  # $5M+ outflow
            score += 30
            details.append(f"Strong outflow: ${abs(netflow_24h)/1e6:.1f}M")
        elif netflow_24h < 0:
            score += 15
            details.append("Moderate outflow")
        
        if whale_buying_7d > 10_000_000:  # $10M+ whale buying
            score += 40
            details.append(f"Whale accumulation: ${whale_buying_7d/1e6:.1f}M")
        elif whale_buying_7d > 5_000_000:
            score += 25
            details.append("Moderate whale buying")
        
        if address_growth_7d > 5:
            score += 30
            details.append(f"Strong address growth: {address_growth_7d:.1f}%")
        elif address_growth_7d > 2:
            score += 15
            details.append("Moderate address growth")
        
        # Check technical confirmation
        if price_above_20ema and volume_spike:
            technical_confirm = True
        else:
            technical_confirm = False
        
        if score >= 70 and technical_confirm:
            return {
                'signal': 'LONG',
                'on_chain_score': score,
                'confidence': 'HIGH' if score >= 85 else 'MEDIUM',
                'details': details,
                'position_size': 1.5 if score >= 85 else 1.0,
                'stop_loss': 'below_20_ema',
                'take_profit': 'trailing_3_atr',
                'expected_hold_days': '3-14',
                'expected_win_rate': '50-55%',
                'expected_profit_factor': 1.8
            }
        else:
            return {
                'signal': 'NONE',
                'on_chain_score': score,
                'reason': 'Insufficient on-chain + technical confluence'
            }


class CryptoStrategyVolatilityScalping:
    """
    Strategy 3: Volatility Regime Scalping
    Adapt position sizing and targets based on realized volatility
    """
    
    def __init__(self):
        self.regime_detector = VolatilityRegimeDetector()
    
    def generate_signal(self, 
                        prices: pd.Series,
                        volumes: pd.Series,
                        bb_position: float = None) -> Dict:
        """
        Generate volatility-based scalping signal
        
        Args:
            prices: Series of closing prices
            volumes: Series of volumes
            bb_position: Bollinger Band position (0-1)
            
        Returns:
            Signal dictionary
        """
        regime = self.regime_detector.detect_regime(prices)
        adjustments = self.regime_detector.get_regime_adjustments(regime)
        
        # Calculate indicators
        ema_9 = prices.ewm(span=9).mean().iloc[-1]
        ema_21 = prices.ewm(span=21).mean().iloc[-1]
        current_price = prices.iloc[-1]
        
        avg_volume = volumes.rolling(20).mean().iloc[-1]
        current_volume = volumes.iloc[-1]
        volume_spike = current_volume > 2 * avg_volume
        
        signal = {'regime': regime.value, 'adjustments': adjustments}
        
        # Regime-specific entry logic
        if regime == VolatilityRegime.LOW_VOL:
            # Mean reversion
            if bb_position is not None:
                if bb_position < 0.1:
                    signal.update({
                        'signal': 'LONG',
                        'reason': 'Lower BB touch in low vol',
                        'target': 'upper_band',
                        'stop': '1x_atr'
                    })
                elif bb_position > 0.9:
                    signal.update({
                        'signal': 'SHORT',
                        'reason': 'Upper BB touch in low vol',
                        'target': 'lower_band',
                        'stop': '1x_atr'
                    })
                    
        elif regime == VolatilityRegime.NORMAL_VOL:
            # Trend following
            if current_price > ema_9 > ema_21:
                signal.update({
                    'signal': 'LONG',
                    'reason': 'EMA bullish alignment',
                    'target': '2R',
                    'stop': '1x_atr'
                })
            elif current_price < ema_9 < ema_21:
                signal.update({
                    'signal': 'SHORT',
                    'reason': 'EMA bearish alignment',
                    'target': '2R',
                    'stop': '1x_atr'
                })
                
        elif regime in [VolatilityRegime.HIGH_VOL, VolatilityRegime.EXTREME_VOL]:
            # Momentum breakout
            prev_high = prices.rolling(20).max().iloc[-2]
            prev_low = prices.rolling(20).min().iloc[-2]
            
            if volume_spike and current_price > prev_high:
                signal.update({
                    'signal': 'LONG',
                    'reason': 'Volume-confirmed breakout',
                    'target': '3R',
                    'stop': '0.8x_atr'
                })
            elif volume_spike and current_price < prev_low:
                signal.update({
                    'signal': 'SHORT',
                    'reason': 'Volume-confirmed breakdown',
                    'target': '3R',
                    'stop': '0.8x_atr'
                })
        
        return signal


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def analyze_current_picks(picks_data: List[Dict]) -> pd.DataFrame:
    """
    Analyze a list of current crypto picks and provide recommendations
    
    Args:
        picks_data: List of dictionaries with pick data
        
    Returns:
        DataFrame with analysis and recommendations
    """
    liquidity_filter = CryptoLiquidityFilter()
    hccs_calculator = HighCertaintyCryptoScore()
    
    results = []
    for data in picks_data:
        pick = CryptoPick(
            symbol=data['symbol'],
            price=data.get('price', 0),
            volume_24h=data.get('volume_24h', 0),
            quote_volume_24h=data.get('quote_volume_24h', 0),
            trade_count_24h=data.get('trade_count_24h', 0),
            price_change_24h=data.get('price_change_24h', 0),
            funding_rate=data.get('funding_rate', 0),
            confluence_count=data.get('confluence_count', 0)
        )
        
        # Liquidity analysis
        liq_result = liquidity_filter.filter_pick(pick)
        
        # HCCS score
        hccs_result = hccs_calculator.calculate_score(pick)
        
        results.append({
            'symbol': pick.symbol,
            'price': pick.price,
            'quote_volume_m': pick.quote_volume_24h / 1_000_000,
            'tier': liq_result['tier'],
            'hccs_score': hccs_result['total_score'],
            'certainty': hccs_result['certainty_level'],
            'position_mult': liq_result['position_size_multiplier'],
            'recommendation': liq_result['recommendation'],
            'confluence': pick.confluence_count
        })
    
    return pd.DataFrame(results)


def get_crypto_risk_checklist() -> Dict:
    """
    Return the crypto-specific risk checklist
    """
    return {
        'liquidity': {
            'min_volume_24h_usd': 3_000_000,
            'max_slippage_1k_usd': 0.005,  # 0.5%
            'min_trade_count_24h': 5000
        },
        'funding': {
            'check_funding_timing': True,
            'max_funding_cost_24h': 0.005,  # 0.5%
            'funding_direction_aligned': True
        },
        'volatility': {
            'max_atr_14_pct': 10.0,
            'vol_regime_appropriate': True,
            'avoid_extreme_vol': True
        },
        'structural': {
            'no_major_unlocks_30d': True,
            'exchange_solvent': True,
            'no_regulatory_risk': True
        },
        'market': {
            'max_btc_correlation': 0.85,
            'not_during_funding_payment': True,
            'min_market_cap_usd': 100_000_000
        }
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Analyze current picks from live data
    current_picks = [
        {'symbol': 'BTCUSDT', 'price': 68783, 'quote_volume_24h': 1.46e9, 'confluence_count': 8},
        {'symbol': 'ETHUSDT', 'price': 2103, 'quote_volume_24h': 7.72e8, 'confluence_count': 7},
        {'symbol': 'SOLUSDT', 'price': 80, 'quote_volume_24h': 2.30e8, 'confluence_count': 6},
        {'symbol': 'INJUSDT', 'price': 2.85, 'quote_volume_24h': 2.07e6, 'confluence_count': 3},
        {'symbol': 'JTOUSDT', 'price': 0.27, 'quote_volume_24h': 0.79e6, 'confluence_count': 2},
    ]
    
    df = analyze_current_picks(current_picks)
    print("\n=== CURRENT PICKS ANALYSIS ===")
    print(df.to_string(index=False))
