"""
KIMI_FEB172026 - Asset Class Specific Strategies
Optimized parameters and signal logic for each asset class
Crypto, Forex, Stocks, Meme coins
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_STRATEGIES")


@dataclass
class AssetClassConfig:
    """Configuration for specific asset class"""
    name: str
    volatility_profile: str  # high, medium, low
    avg_daily_range_pct: float
    liquidity_profile: str  # high, medium, low
    session_hours: str  # 24h, market_hours
    typical_holding_period: str  # scalping, day_trade, swing
    optimal_rr_ratio: float
    confidence_threshold: float
    

class CryptoStrategy:
    """
    Crypto-specific strategies
    Optimized for: 24/7 trading, high volatility, momentum
    """
    
    CONFIG = AssetClassConfig(
        name="crypto",
        volatility_profile="high",
        avg_daily_range_pct=5.0,
        liquidity_profile="high",
        session_hours="24h",
        typical_holding_period="scalping",
        optimal_rr_ratio=2.5,
        confidence_threshold=0.65
    )
    
    @staticmethod
    def detect_pump_acceleration(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Crypto-specific pump detection
        More sensitive to volume spikes due to crypto's volatility
        """
        if len(df) < 20:
            return None
        
        # Crypto uses shorter timeframes
        price_change_4h = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
        
        # Higher volume threshold for crypto (more noise)
        volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Crypto-specific thresholds (more aggressive)
        if (price_change_4h >= 6 and  # Lower than traditional 8%
            volume_ratio >= params.get('volume_threshold', 4.0) and
            rsi < params.get('rsi_overbought', 70)):
            
            # Calculate dynamic TP/SL for crypto
            atr = CryptoStrategy._calculate_atr(df)
            entry = df['close'].iloc[-1]
            
            # Crypto can have wider targets due to volatility
            tp = entry + (atr * params.get('tp_multiplier', 3.0))
            sl = entry - (atr * params.get('sl_multiplier', 1.5))
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": min(0.95, 0.5 + volume_ratio/20 + price_change_4h/40),
                "metadata": {
                    "price_change_4h": price_change_4h,
                    "volume_ratio": volume_ratio,
                    "rsi": rsi,
                    "atr": atr
                }
            }
        
        return None
    
    @staticmethod
    def detect_liquidation_cascade(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Detect liquidation cascades (crypto-specific)
        Large wicks + volume spikes = forced liquidations
        """
        if len(df) < 5:
            return None
        
        # Look for large wicks
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['close'], candle['open'])
        lower_wick = min(candle['close'], candle['open']) - candle['low']
        range_pct = (candle['high'] - candle['low']) / candle['open'] * 100
        
        # Volume spike
        volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = candle['volume'] / volume_sma if volume_sma > 0 else 0
        
        # Long wick down + volume + recovery = short liquidation (buy signal)
        if (lower_wick > body * 2 and 
            range_pct > 3 and 
            volume_ratio > 5 and
            candle['close'] > candle['open']):
            
            entry = df['close'].iloc[-1]
            atr = CryptoStrategy._calculate_atr(df)
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": entry + (atr * 2.5),
                "stop_loss": candle['low'] * 0.995,  # Below the wick
                "confidence": 0.75,
                "metadata": {
                    "range_pct": range_pct,
                    "volume_ratio": volume_ratio,
                    "wick_size": lower_wick
                }
            }
        
        return None
    
    @staticmethod
    def detect_smc_order_block(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Smart Money Concepts for crypto
        Institutional footprints in crypto markets
        """
        if len(df) < 20:
            return None
        
        # Look for bullish order block (bearish candle before strong up move)
        for i in range(-10, -2):
            if i >= len(df) or i + 2 >= len(df):
                continue
            
            candle = df.iloc[i]
            next_candle = df.iloc[i + 1]
            
            # Bearish candle
            is_bearish = candle['close'] < candle['open']
            
            # Strong bullish follow-through
            bullish_displacement = (next_candle['close'] - next_candle['open']) / next_candle['open'] > 0.015
            breaks_high = next_candle['close'] > candle['high']
            
            if is_bearish and bullish_displacement and breaks_high:
                order_block_low = candle['low']
                order_block_high = candle['high']
                
                current_price = df['close'].iloc[-1]
                
                # Price retraced to order block zone
                if order_block_low <= current_price <= order_block_high * 1.02:
                    return {
                        "signal": True,
                        "direction": "LONG",
                        "entry_price": current_price,
                        "take_profit": current_price + (current_price - order_block_low) * 2,
                        "stop_loss": order_block_low * 0.995,
                        "confidence": 0.78,
                        "metadata": {
                            "order_block_low": order_block_low,
                            "order_block_high": order_block_high,
                            "pattern": "bullish_ob_retest"
                        }
                    }
        
        return None
    
    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(df) < period:
            return df['close'].iloc[-1] * 0.02
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else df['close'].iloc[-1] * 0.02


class ForexStrategy:
    """
    Forex-specific strategies
    Optimized for: Lower volatility, session-based, technical levels
    """
    
    CONFIG = AssetClassConfig(
        name="forex",
        volatility_profile="low",
        avg_daily_range_pct=0.8,
        liquidity_profile="high",
        session_hours="market_hours",
        typical_holding_period="day_trade",
        optimal_rr_ratio=2.0,
        confidence_threshold=0.70
    )
    
    @staticmethod
    def detect_session_breakout(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Forex session breakout (London/NY)
        Trade breakouts of Asian session range
        """
        if len(df) < 24:
            return None
        
        # Get Asian session range (last 8 hours)
        asian_session = df.iloc[-24:-16]
        asian_high = asian_session['high'].max()
        asian_low = asian_session['low'].min()
        asian_range = asian_high - asian_low
        
        current = df['close'].iloc[-1]
        
        # Breakout above Asian high
        if current > asian_high * 1.001:  # Small buffer
            entry = current
            tp = entry + (asian_range * 1.5)
            sl = asian_low
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.72,
                "metadata": {
                    "session": "london_ny",
                    "asian_high": asian_high,
                    "asian_low": asian_low,
                    "range": asian_range
                }
            }
        
        # Breakout below Asian low
        if current < asian_low * 0.999:
            entry = current
            tp = entry - (asian_range * 1.5)
            sl = asian_high
            
            return {
                "signal": True,
                "direction": "SHORT",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.72,
                "metadata": {
                    "session": "london_ny",
                    "asian_high": asian_high,
                    "asian_low": asian_low,
                    "range": asian_range
                }
            }
        
        return None
    
    @staticmethod
    def detect_support_resistance(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Key level bounce for forex
        Uses pivot points and round numbers
        """
        if len(df) < 50:
            return None
        
        current = df['close'].iloc[-1]
        
        # Calculate pivot points
        prev = df.iloc[-2]
        pivot = (prev['high'] + prev['low'] + prev['close']) / 3
        r1 = (2 * pivot) - prev['low']
        s1 = (2 * pivot) - prev['high']
        
        # Check for bounce off S1 (buy)
        distance_to_s1 = abs(current - s1) / current * 100
        
        if distance_to_s1 < 0.1 and current > df['open'].iloc[-1]:
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": current,
                "take_profit": pivot,
                "stop_loss": s1 - (s1 * 0.002),
                "confidence": 0.70,
                "metadata": {
                    "level": "S1",
                    "pivot": pivot,
                    "distance_pct": distance_to_s1
                }
            }
        
        # Check for rejection at R1 (sell)
        distance_to_r1 = abs(current - r1) / current * 100
        
        if distance_to_r1 < 0.1 and current < df['open'].iloc[-1]:
            return {
                "signal": True,
                "direction": "SHORT",
                "entry_price": current,
                "take_profit": pivot,
                "stop_loss": r1 + (r1 * 0.002),
                "confidence": 0.70,
                "metadata": {
                    "level": "R1",
                    "pivot": pivot,
                    "distance_pct": distance_to_r1
                }
            }
        
        return None


class StockStrategy:
    """
    Stock-specific strategies
    Optimized for: Market hours, fundamental momentum, sector rotation
    """
    
    CONFIG = AssetClassConfig(
        name="stock",
        volatility_profile="medium",
        avg_daily_range_pct=2.0,
        liquidity_profile="high",
        session_hours="market_hours",
        typical_holding_period="swing",
        optimal_rr_ratio=3.0,
        confidence_threshold=0.70
    )
    
    @staticmethod
    def detect_earnings_momentum(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Post-earnings momentum for stocks
        Large gap + volume continuation
        """
        if len(df) < 5:
            return None
        
        # Gap up
        prev_close = df['close'].iloc[-2]
        current_open = df['open'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        gap_pct = (current_open - prev_close) / prev_close * 100
        
        # Volume confirmation
        volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
        
        # Gap up + strong close = continuation
        if (gap_pct > 3 and 
            current_close > current_open and
            volume_ratio > 2):
            
            entry = current_close
            tp = entry + (entry * 0.06)  # 6% target
            sl = current_open  # Gap fill as stop
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.72,
                "metadata": {
                    "gap_pct": gap_pct,
                    "volume_ratio": volume_ratio,
                    "setup": "earnings_gap_go"
                }
            }
        
        return None
    
    @staticmethod
    def detect_sector_rotation(df: pd.DataFrame, sector_data: Dict, params: Dict) -> Optional[Dict]:
        """
        Sector rotation momentum
        Strong sector + relative strength
        """
        if len(df) < 20:
            return None
        
        # Stock making new 20-day high
        high_20d = df['high'].rolling(window=20).max().iloc[-1]
        current = df['close'].iloc[-1]
        
        if current >= high_20d * 0.99:  # Near 20d high
            # Volume confirmation
            volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
            volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
            
            if volume_ratio > 1.5:
                entry = current
                atr = StockStrategy._calculate_atr(df)
                
                return {
                    "signal": True,
                    "direction": "LONG",
                    "entry_price": entry,
                    "take_profit": entry + (atr * 3.0),
                    "stop_loss": entry - (atr * 1.5),
                    "confidence": 0.70,
                    "metadata": {
                        "setup": "20d_high_breakout",
                        "volume_ratio": volume_ratio,
                        "new_high": True
                    }
                }
        
        return None
    
    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for stocks"""
        if len(df) < period:
            return df['close'].iloc[-1] * 0.01
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else df['close'].iloc[-1] * 0.01


class MemeStrategy:
    """
    Meme coin specific strategies
    Optimized for: Extreme volatility, social sentiment, rapid moves
    """
    
    CONFIG = AssetClassConfig(
        name="meme",
        volatility_profile="extreme",
        avg_daily_range_pct=20.0,
        liquidity_profile="medium",
        session_hours="24h",
        typical_holding_period="scalping",
        optimal_rr_ratio=4.0,
        confidence_threshold=0.55  # Lower threshold due to fast moves
    )
    
    @staticmethod
    def detect_social_momentum(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Detect meme coin pumps based on volume + price velocity
        Extremely fast timeframe
        """
        if len(df) < 5:
            return None
        
        # Short timeframe (1h candles, look at last 3)
        price_change_1h = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
        price_change_3h = (df['close'].iloc[-1] - df['close'].iloc[-4]) / df['close'].iloc[-4] * 100
        
        # Massive volume spike
        volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
        
        # Meme coin criteria: explosive move + volume
        if (price_change_1h > 10 and 
            volume_ratio > 8 and
            price_change_3h > 15):
            
            entry = df['close'].iloc[-1]
            
            # Wide targets for meme coins
            tp = entry * 1.50  # 50% target
            sl = entry * 0.90  # 10% stop (tight due to volatility)
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.60,
                "metadata": {
                    "price_change_1h": price_change_1h,
                    "price_change_3h": price_change_3h,
                    "volume_ratio": volume_ratio,
                    "setup": "meme_explosion"
                }
            }
        
        return None
    
    @staticmethod
    def detect_whale_accumulation(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
        """
        Detect whale accumulation patterns in meme coins
        Large wicks with volume = smart money buying
        """
        if len(df) < 10:
            return None
        
        candle = df.iloc[-1]
        
        # Large lower wick = rejection of lows
        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['close'], candle['open']) - candle['low']
        
        # Volume spike
        volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = candle['volume'] / volume_sma if volume_sma > 0 else 0
        
        if (lower_wick > body * 3 and  # Long wick
            volume_ratio > 5 and
            candle['close'] > candle['open']):  # Bullish close
            
            entry = candle['close']
            
            return {
                "signal": True,
                "direction": "LONG",
                "entry_price": entry,
                "take_profit": entry * 1.30,
                "stop_loss": candle['low'] * 0.98,
                "confidence": 0.58,
                "metadata": {
                    "wick_ratio": lower_wick / body if body > 0 else 999,
                    "volume_ratio": volume_ratio,
                    "setup": "meme_whale_wick"
                }
            }
        
        return None


# =============================================================================
# Strategy Registry
# =============================================================================
STRATEGY_REGISTRY = {
    "crypto": {
        "pump_acceleration": CryptoStrategy.detect_pump_acceleration,
        "liquidation_cascade": CryptoStrategy.detect_liquidation_cascade,
        "smc_order_block": CryptoStrategy.detect_smc_order_block
    },
    "forex": {
        "session_breakout": ForexStrategy.detect_session_breakout,
        "support_resistance": ForexStrategy.detect_support_resistance
    },
    "stock": {
        "earnings_momentum": StockStrategy.detect_earnings_momentum,
        "sector_rotation": StockStrategy.detect_sector_rotation
    },
    "meme": {
        "social_momentum": MemeStrategy.detect_social_momentum,
        "whale_accumulation": MemeStrategy.detect_whale_accumulation
    }
}


def get_strategy_for_asset(asset_class: str, strategy_name: str):
    """Get strategy function for asset class"""
    return STRATEGY_REGISTRY.get(asset_class, {}).get(strategy_name)


def get_all_strategies_for_asset(asset_class: str) -> Dict:
    """Get all strategies for an asset class"""
    return STRATEGY_REGISTRY.get(asset_class, {})


def get_config_for_asset(asset_class: str) -> AssetClassConfig:
    """Get configuration for asset class"""
    configs = {
        "crypto": CryptoStrategy.CONFIG,
        "forex": ForexStrategy.CONFIG,
        "stock": StockStrategy.CONFIG,
        "meme": MemeStrategy.CONFIG
    }
    return configs.get(asset_class, CryptoStrategy.CONFIG)


# =============================================================================
# Entry point for testing
# =============================================================================
def main():
    """Test strategies"""
    print("=" * 80)
    print("KIMI_FEB172026 - Asset Class Strategy Test")
    print("=" * 80)
    
    # Show configurations
    for asset in ["crypto", "forex", "stock", "meme"]:
        config = get_config_for_asset(asset)
        print(f"\n{asset.upper()}:")
        print(f"  Volatility: {config.volatility_profile}")
        print(f"  Avg Daily Range: {config.avg_daily_range_pct}%")
        print(f"  Optimal R:R: {config.optimal_rr_ratio}")
        print(f"  Confidence Threshold: {config.confidence_threshold}")
        print(f"  Strategies: {list(get_all_strategies_for_asset(asset).keys())}")


if __name__ == "__main__":
    main()
