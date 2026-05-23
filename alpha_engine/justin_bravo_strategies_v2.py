"""
ALPHA_ENGINE -- Justin & J Bravo Strategies V2 (Improved)
=========================================================
Refined based on backtest results with better filters and risk management.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Try importing from alpha_engine, fallback to local implementations
try:
    from alpha_engine.indicators import ema, rsi, atr, volume_ratio
except ImportError:
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()
    
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        return volume / volume.rolling(window=period).mean()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    return round(value, 10)


def _calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index (trend strength)."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    
    atr_val = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_val)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_val)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    
    return adx


def _detect_pullback_to_ema(close: pd.Series, ema_line: pd.Series, 
                            lookback: int = 3, tolerance: float = 0.005) -> int:
    """
    Detect price pulling back to EMA (better entry than crossover).
    Returns: 1 for bullish pullback, -1 for bearish, 0 for none.
    """
    if len(close) < lookback + 1:
        return 0
    
    # Check if price recently crossed above EMA and now pulling back to it
    recent_close = close.tail(lookback)
    recent_ema = ema_line.tail(lookback)
    
    # Price was above EMA
    was_above = (recent_close.iloc[:-1] > recent_ema.iloc[:-1]).any()
    # Now near EMA (pullback)
    current_distance = abs(close.iloc[-1] - ema_line.iloc[-1]) / ema_line.iloc[-1]
    still_bullish = close.iloc[-1] > ema_line.iloc[-1] * 0.995
    
    if was_above and current_distance < tolerance and still_bullish:
        # Check trend alignment (price making higher lows)
        if close.tail(10).is_monotonic_increasing:
            return 0  # Too extended
        return 1
    
    # Bearish pullback
    was_below = (recent_close.iloc[:-1] < recent_ema.iloc[:-1]).any()
    still_bearish = close.iloc[-1] < ema_line.iloc[-1] * 1.005
    
    if was_below and current_distance < tolerance and still_bearish:
        if close.tail(10).is_monotonic_decreasing:
            return 0
        return -1
    
    return 0


def _calculate_bb_position(close: pd.Series, period: int = 20, std_dev: float = 2) -> float:
    """Calculate position within Bollinger Bands (0=lower, 0.5=middle, 1=upper)."""
    if len(close) < period:
        return 0.5
    
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    current = close.iloc[-1]
    position = (current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
    
    return max(0, min(1, position))


# =============================================================================
# IMPROVED STRATEGY 1: EMA9 Pullback (Mean Reversion Enhancement)
# =============================================================================

def justin_ema9_pullback_v2(data: Dict[str, pd.DataFrame], 
                             context: Optional[dict] = None) -> List[dict]:
    """
    Improved EMA9 Strategy:
    - Trade pullbacks to EMA9 (not crossovers)
    - Require ADX > 20 (trending market)
    - Bollinger Band position filter (avoid overbought/oversold)
    - RSI confirmation
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 55:
            continue
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Indicators
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        rsi_val = rsi(close, 14).iloc[-1]
        adx_val = _calculate_adx(high, low, close).iloc[-1]
        bb_pos = _calculate_bb_position(close)
        vol_ratio_val = volume_ratio(volume, 20).iloc[-1]
        
        curr_close = close.iloc[-1]
        curr_ema9 = ema9.iloc[-1]
        
        # Skip if ADX too low (choppy market)
        if adx_val < 20:
            return []
        
        # LONG: Pullback to EMA9 in uptrend
        if curr_close > curr_ema9 * 0.995 and curr_close < curr_ema9 * 1.015:
            # Trend alignment
            if ema9.iloc[-1] > ema21.iloc[-1]:
                # RSI not overbought
                if 40 < rsi_val < 65:
                    # Not at upper Bollinger Band
                    if bb_pos < 0.7:
                        # ATR-based levels
                        atr_val = atr(high, low, close, 14).iloc[-1]
                        entry = curr_close
                        tp = entry + 2.5 * atr_val
                        sl = entry - 1.0 * atr_val
                        
                        picks.append({
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_price': _smart_round(entry),
                            'take_profit': _smart_round(tp),
                            'stop_loss': _smart_round(sl),
                            'confidence': 0.65 + (0.05 if vol_ratio_val > 1.2 else 0),
                            'strategy': 'justin_ema9_pullback_v2',
                            'timestamp': _now_iso(),
                            'reason': f'EMA9 pullback | ADX {adx_val:.1f} | RSI {rsi_val:.1f} | BB {bb_pos:.2f}'
                        })
        
        # SHORT: Pullback to EMA9 in downtrend
        elif curr_close < curr_ema9 * 1.005 and curr_close > curr_ema9 * 0.985:
            if ema9.iloc[-1] < ema21.iloc[-1]:
                if 35 < rsi_val < 60:
                    if bb_pos > 0.3:
                        atr_val = atr(high, low, close, 14).iloc[-1]
                        entry = curr_close
                        tp = entry - 2.5 * atr_val
                        sl = entry + 1.0 * atr_val
                        
                        picks.append({
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_price': _smart_round(entry),
                            'take_profit': _smart_round(tp),
                            'stop_loss': _smart_round(sl),
                            'confidence': 0.65 + (0.05 if vol_ratio_val > 1.2 else 0),
                            'strategy': 'justin_ema9_pullback_v2',
                            'timestamp': _now_iso(),
                            'reason': f'EMA9 pullback | ADX {adx_val:.1f} | RSI {rsi_val:.1f} | BB {bb_pos:.2f}'
                        })
    
    return picks


# =============================================================================
# IMPROVED STRATEGY 2: RSI Divergence with EMA
# =============================================================================

def justin_rsi_divergence_v2(data: Dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> List[dict]:
    """
    RSI Divergence Strategy:
    - Bullish: Price makes lower low, RSI makes higher low
    - Bearish: Price makes higher high, RSI makes lower high
    - Confirmed by EMA9 direction
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Get swing points (last 20 bars)
        lookback = 20
        recent_close = close.tail(lookback)
        recent_rsi = rsi(close, 14).tail(lookback)
        recent_lows = low.tail(lookback)
        recent_highs = high.tail(lookback)
        
        # Find local min/max
        local_min_idx = recent_close.idxmin()
        local_max_idx = recent_close.idxmax()
        
        # Bullish divergence
        if local_min_idx != recent_close.index[-1]:
            # Price made lower low
            price_now = close.iloc[-1]
            price_then = close.loc[local_min_idx]
            
            if price_now < price_then * 1.02:  # Price near the low
                rsi_now = rsi(close, 14).iloc[-1]
                rsi_then = rsi(close, 14).loc[local_min_idx]
                
                # RSI making higher low (divergence)
                if rsi_now > rsi_then + 5 and rsi_now < 50:
                    # EMA9 turning up
                    ema9 = ema(close, 9)
                    if ema9.iloc[-1] > ema9.iloc[-3]:
                        atr_val = atr(high, low, close, 14).iloc[-1]
                        entry = close.iloc[-1]
                        tp = entry + 3.0 * atr_val
                        sl = entry - 1.2 * atr_val
                        
                        picks.append({
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_price': _smart_round(entry),
                            'take_profit': _smart_round(tp),
                            'stop_loss': _smart_round(sl),
                            'confidence': 0.68,
                            'strategy': 'justin_rsi_divergence_v2',
                            'timestamp': _now_iso(),
                            'reason': f'RSI Bull Div | Price {price_then:.2f}->{price_now:.2f} | RSI {rsi_then:.1f}->{rsi_now:.1f}'
                        })
        
        # Bearish divergence
        if local_max_idx != recent_close.index[-1]:
            price_now = close.iloc[-1]
            price_then = close.loc[local_max_idx]
            
            if price_now > price_then * 0.98:  # Price near the high
                rsi_now = rsi(close, 14).iloc[-1]
                rsi_then = rsi(close, 14).loc[local_max_idx]
                
                # RSI making lower high (divergence)
                if rsi_now < rsi_then - 5 and rsi_now > 50:
                    ema9 = ema(close, 9)
                    if ema9.iloc[-1] < ema9.iloc[-3]:
                        atr_val = atr(high, low, close, 14).iloc[-1]
                        entry = close.iloc[-1]
                        tp = entry - 3.0 * atr_val
                        sl = entry + 1.2 * atr_val
                        
                        picks.append({
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_price': _smart_round(entry),
                            'take_profit': _smart_round(tp),
                            'stop_loss': _smart_round(sl),
                            'confidence': 0.68,
                            'strategy': 'justin_rsi_divergence_v2',
                            'timestamp': _now_iso(),
                            'reason': f'RSI Bear Div | Price {price_then:.2f}->{price_now:.2f} | RSI {rsi_then:.1f}->{rsi_now:.1f}'
                        })
    
    return picks


# =============================================================================
# IMPROVED STRATEGY 3: Trend Following with EMA21
# =============================================================================

def justin_trend_follow_v2(data: Dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> List[dict]:
    """
    Trend Following Strategy:
    - Use EMA21 as trend filter
    - Enter on EMA9 pullbacks in trend direction
    - Higher timeframe alignment
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 50:
            continue
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Multiple timeframe EMAs
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        ema50 = ema(close, 50)
        
        curr_close = close.iloc[-1]
        
        # Strong trend conditions
        strong_uptrend = ema9.iloc[-1] > ema21.iloc[-1] > ema50.iloc[-1]
        strong_downtrend = ema9.iloc[-1] < ema21.iloc[-1] < ema50.iloc[-1]
        
        # Distance from EMA9 (pullback measurement)
        dist_from_ema9 = (curr_close - ema9.iloc[-1]) / ema9.iloc[-1]
        
        rsi_val = rsi(close, 14).iloc[-1]
        adx_val = _calculate_adx(high, low, close).iloc[-1]
        
        # Only trade strong trends
        if adx_val < 25:
            return []
        
        # LONG: Strong uptrend + pullback to EMA9
        if strong_uptrend and -0.015 < dist_from_ema9 < 0.005:
            if 45 < rsi_val < 70:
                # Volume confirmation
                vol_ratio_val = volume_ratio(volume, 20).iloc[-1]
                if vol_ratio_val > 1.0:
                    atr_val = atr(high, low, close, 14).iloc[-1]
                    entry = curr_close
                    tp = entry + 3.0 * atr_val
                    sl = max(entry - 1.5 * atr_val, ema21.iloc[-1] * 0.98)
                    
                    picks.append({
                        'symbol': symbol,
                        'direction': 'LONG',
                        'entry_price': _smart_round(entry),
                        'take_profit': _smart_round(tp),
                        'stop_loss': _smart_round(sl),
                        'confidence': 0.70 + (0.05 if adx_val > 30 else 0),
                        'strategy': 'justin_trend_follow_v2',
                        'timestamp': _now_iso(),
                        'reason': f'Trend LONG | ADX {adx_val:.1f} | Pullback {dist_from_ema9*100:.2f}% | RSI {rsi_val:.1f}'
                    })
        
        # SHORT: Strong downtrend + pullback to EMA9
        elif strong_downtrend and -0.005 < dist_from_ema9 < 0.015:
            if 30 < rsi_val < 55:
                vol_ratio_val = volume_ratio(volume, 20).iloc[-1]
                if vol_ratio_val > 1.0:
                    atr_val = atr(high, low, close, 14).iloc[-1]
                    entry = curr_close
                    tp = entry - 3.0 * atr_val
                    sl = min(entry + 1.5 * atr_val, ema21.iloc[-1] * 1.02)
                    
                    picks.append({
                        'symbol': symbol,
                        'direction': 'SHORT',
                        'entry_price': _smart_round(entry),
                        'take_profit': _smart_round(tp),
                        'stop_loss': _smart_round(sl),
                        'confidence': 0.70 + (0.05 if adx_val > 30 else 0),
                        'strategy': 'justin_trend_follow_v2',
                        'timestamp': _now_iso(),
                        'reason': f'Trend SHORT | ADX {adx_val:.1f} | Pullback {dist_from_ema9*100:.2f}% | RSI {rsi_val:.1f}'
                    })
    
    return picks


# =============================================================================
# IMPROVED STRATEGY 4: Breakout with Volume
# =============================================================================

def justin_breakout_volume_v2(data: Dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> List[dict]:
    """
    Breakout Strategy:
    - Break above/below recent range
    - Volume confirmation (>1.5x average)
    - RSI not extreme
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Recent range (20 bars)
        lookback = 20
        recent_high = high.tail(lookback).max()
        recent_low = low.tail(lookback).min()
        
        curr_close = close.iloc[-1]
        curr_high = high.iloc[-1]
        curr_low = low.iloc[-1]
        
        # Volume check
        vol_ma = volume.tail(20).mean()
        curr_vol = volume.iloc[-1]
        
        if curr_vol < vol_ma * 1.3:
            return []
        
        rsi_val = rsi(close, 14).iloc[-1]
        
        # LONG breakout
        if curr_high > recent_high * 0.998 and curr_close > close.shift(1).iloc[-1]:
            if rsi_val < 75:  # Not extremely overbought
                # Check if breaking from consolidation
                range_pct = (recent_high - recent_low) / recent_low
                if range_pct < 0.15:  # Tight range
                    atr_val = atr(high, low, close, 14).iloc[-1]
                    entry = curr_close
                    tp = entry + 2.0 * atr_val
                    sl = recent_low * 0.995
                    
                    picks.append({
                        'symbol': symbol,
                        'direction': 'LONG',
                        'entry_price': _smart_round(entry),
                        'take_profit': _smart_round(tp),
                        'stop_loss': _smart_round(sl),
                        'confidence': 0.65,
                        'strategy': 'justin_breakout_volume_v2',
                        'timestamp': _now_iso(),
                        'reason': f'Breakout LONG | Vol {curr_vol/vol_ma:.2f}x | RSI {rsi_val:.1f}'
                    })
        
        # SHORT breakdown
        elif curr_low < recent_low * 1.002 and curr_close < close.shift(1).iloc[-1]:
            if rsi_val > 25:  # Not extremely oversold
                range_pct = (recent_high - recent_low) / recent_low
                if range_pct < 0.15:
                    atr_val = atr(high, low, close, 14).iloc[-1]
                    entry = curr_close
                    tp = entry - 2.0 * atr_val
                    sl = recent_high * 1.005
                    
                    picks.append({
                        'symbol': symbol,
                        'direction': 'SHORT',
                        'entry_price': _smart_round(entry),
                        'take_profit': _smart_round(tp),
                        'stop_loss': _smart_round(sl),
                        'confidence': 0.65,
                        'strategy': 'justin_breakout_volume_v2',
                        'timestamp': _now_iso(),
                        'reason': f'Breakout SHORT | Vol {curr_vol/vol_ma:.2f}x | RSI {rsi_val:.1f}'
                    })
    
    return picks


# =============================================================================
# STRATEGY REGISTRY
# =============================================================================

JUSTIN_BRAVO_STRATEGIES_V2 = {
    'justin_ema9_pullback_v2': justin_ema9_pullback_v2,
    'justin_rsi_divergence_v2': justin_rsi_divergence_v2,
    'justin_trend_follow_v2': justin_trend_follow_v2,
    'justin_breakout_volume_v2': justin_breakout_volume_v2,
}


def run_all_v2_strategies(data: Dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> List[dict]:
    """Run all V2 strategies."""
    all_picks = []
    
    for name, strategy_fn in JUSTIN_BRAVO_STRATEGIES_V2.items():
        try:
            picks = strategy_fn(data, context)
            all_picks.extend(picks)
        except Exception as e:
            print(f"Error in {name}: {e}")
    
    return all_picks


if __name__ == '__main__':
    print("Justin & J Bravo Strategies V2 (Improved)")
    print("Available strategies:")
    for name in JUSTIN_BRAVO_STRATEGIES_V2.keys():
        print(f"  - {name}")
