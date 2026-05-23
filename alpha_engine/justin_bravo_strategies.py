"""
ALPHA_ENGINE -- Justin & J Bravo (ChartPrime) Trading Strategies
================================================================
Based on winning trader Justin's advice and ChartPrime J Bravo Kit methods:

Justin Methods:
- EMA9 candle close crossovers (5m, 15m primary timeframes)
- HTF RSI confirmation (1h/4h for direction bias)
- Multi-timeframe confluence
- Volume confirmation

ChartPrime J Bravo Kit Components:
- Bravo 9 Count System (trend angle analysis)
- Bravo Bands (Fibonacci-based dynamic S/R)
- Bravo Candles (angle-based coloring)
- EMA ribbons (9, 200-day, 100-week)
- Pattern recognition (double top, tweezer bottoms)

Timeframes: 5m (primary), 15m (confirmation), 1h/4h (trend bias)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
import numpy as np
import pandas as pd

try:
    from alpha_engine.config import CRYPTO_SYMBOLS, CATEGORY_RISK
    from alpha_engine.indicators import ema, rsi, atr, volume_ratio
except ImportError:
    # Standalone mode
    CRYPTO_SYMBOLS = {}
    CATEGORY_RISK = {}
    
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


def _atr_based_levels(close: pd.Series, high: pd.Series, low: pd.Series,
                      tp_mult: float = 2.0, sl_mult: float = 1.0,
                      atr_period: int = 14) -> Tuple[float, float, float]:
    """Calculate entry, TP, and SL based on ATR."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp_long = price + tp_mult * current_atr
    sl_long = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp_long), _smart_round(sl_long)


def _fibonacci_levels(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels (J Bravo Bands concept)."""
    period = min(20, len(close) - 1)
    highest = high.tail(period).max()
    lowest = low.tail(period).min()
    diff = highest - lowest
    
    return {
        'high': highest,
        'low': lowest,
        '236': lowest + 0.236 * diff,
        '382': lowest + 0.382 * diff,
        '500': lowest + 0.500 * diff,
        '618': lowest + 0.618 * diff,
        '786': lowest + 0.786 * diff,
    }


def _detect_crossover(series1: pd.Series, series2: pd.Series, lookback: int = 2) -> int:
    """
    Detect crossover between two series.
    Returns: 1 for bullish crossover, -1 for bearish, 0 for none.
    """
    if len(series1) < lookback or len(series2) < lookback:
        return 0
    
    # Current and previous values
    s1_curr, s1_prev = series1.iloc[-1], series1.iloc[-2]
    s2_curr, s2_prev = series2.iloc[-1], series2.iloc[-2]
    
    # Bullish crossover: s1 crosses above s2
    if s1_prev <= s2_prev and s1_curr > s2_curr:
        return 1
    # Bearish crossover: s1 crosses below s2
    if s1_prev >= s2_prev and s1_curr < s2_curr:
        return -1
    return 0


def _calculate_trend_angle(series: pd.Series, period: int = 9) -> float:
    """
    Calculate trend angle (J Bravo 9 Count concept).
    Returns angle in degrees (-90 to +90).
    """
    if len(series) < period:
        return 0.0
    
    # Linear regression slope
    x = np.arange(period)
    y = series.tail(period).values
    slope = np.polyfit(x, y, 1)[0]
    
    # Convert to angle (normalized by average price)
    avg_price = y.mean()
    if avg_price == 0:
        return 0.0
    
    # Angle in degrees
    angle = np.degrees(np.arctan(slope / avg_price * 100))
    return np.clip(angle, -90, 90)


def _bravo_nine_count(close: pd.Series, high: pd.Series, low: pd.Series) -> Dict:
    """
    J Bravo 9 Count System - trend exhaustion detection using angle analysis.
    Returns count and trend strength.
    """
    period = 9
    if len(close) < period:
        return {'count': 0, 'angle': 0, 'exhaustion': False}
    
    angle = _calculate_trend_angle(close, period)
    
    # Count consecutive candles in trend direction
    returns = close.pct_change().tail(period)
    bullish_count = (returns > 0).sum()
    bearish_count = (returns < 0).sum()
    
    # Trend exhaustion when count reaches 9 with extreme angle
    exhaustion = False
    if bullish_count >= 9 and angle > 45:
        exhaustion = True
    elif bearish_count >= 9 and angle < -45:
        exhaustion = True
    
    return {
        'count': bullish_count if angle > 0 else bearish_count,
        'angle': angle,
        'exhaustion': exhaustion,
        'direction': 'UP' if angle > 0 else 'DOWN'
    }


def _detect_double_top(high: pd.Series, low: pd.Series, close: pd.Series, 
                       tolerance: float = 0.02) -> int:
    """
    Detect double top pattern.
    Returns: -1 for double top (bearish), 1 for double bottom (bullish), 0 for none.
    """
    if len(close) < 20:
        return 0
    
    lookback = min(20, len(close) - 5)
    recent_highs = high.tail(lookback)
    recent_lows = low.tail(lookback)
    
    # Find local maxima and minima
    max_val = recent_highs.max()
    min_val = recent_lows.min()
    max_idx = recent_highs.idxmax()
    min_idx = recent_lows.idxmin()
    
    # Double top: two peaks at similar level with valley in between
    if max_idx > min_idx:  # Peak after valley
        first_peak = high.loc[:min_idx].max()
        if abs(first_peak - max_val) / max_val < tolerance:
            return -1  # Double top (bearish)
    
    # Double bottom: two troughs at similar level with peak in between
    if min_idx > max_idx:  # Valley after peak
        first_trough = low.loc[:max_idx].min()
        if abs(first_trough - min_val) / min_val < tolerance:
            return 1  # Double bottom (bullish)
    
    return 0


def _detect_tweezer(high: pd.Series, low: pd.Series, open_s: pd.Series, close: pd.Series) -> int:
    """
    Detect tweezer top/bottom patterns.
    Returns: -1 for tweezer top, 1 for tweezer bottom, 0 for none.
    """
    if len(close) < 2:
        return 0
    
    h1, h2 = high.iloc[-2], high.iloc[-1]
    l1, l2 = low.iloc[-2], low.iloc[-1]
    o1, o2 = open_s.iloc[-2], open_s.iloc[-1]
    c1, c2 = close.iloc[-2], close.iloc[-1]
    
    # Tweezer top: two candles with same high, first bullish, second bearish
    if abs(h1 - h2) / h1 < 0.001 and c1 > o1 and c2 < o2:
        return -1
    
    # Tweezer bottom: two candles with same low, first bearish, second bullish
    if abs(l1 - l2) / l1 < 0.001 and c1 < o1 and c2 > o2:
        return 1
    
    return 0


# =============================================================================
# STRATEGY 1: Justin EMA9 Close Cross (Basic)
# =============================================================================

def justin_ema9_basic_crypto(data: Dict[str, pd.DataFrame], 
                              context: Optional[dict] = None) -> List[dict]:
    """
    Justin's Basic EMA9 Strategy:
    - LONG: Close crosses above EMA9
    - SHORT: Close crosses below EMA9
    - No additional filters (pure price action)
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 20:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Calculate EMA9
        ema9 = ema(close, 9)
        
        # Detect crossover
        cross = _detect_crossover(close, ema9)
        
        if cross == 1:  # Bullish crossover
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.0, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.55,
                'strategy': 'justin_ema9_basic',
                'timestamp': _now_iso(),
                'reason': 'Close crossed above EMA9'
            })
        elif cross == -1:  # Bearish crossover
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.0, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.55,
                'strategy': 'justin_ema9_basic',
                'timestamp': _now_iso(),
                'reason': 'Close crossed below EMA9'
            })
    
    return picks


# =============================================================================
# STRATEGY 2: Justin EMA9 + RSI Filter
# =============================================================================

def justin_ema9_rsi_crypto(data: Dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> List[dict]:
    """
    Justin's EMA9 + RSI Confirmation:
    - LONG: Close > EMA9 + RSI > 45 (not overbought)
    - SHORT: Close < EMA9 + RSI < 55 (not oversold)
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 20:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Indicators
        ema9 = ema(close, 9)
        rsi_val = rsi(close, 14)
        vol_ratio = volume_ratio(volume, 20)
        
        # Current values
        curr_close = close.iloc[-1]
        curr_ema9 = ema9.iloc[-1]
        curr_rsi = rsi_val.iloc[-1]
        curr_vol = vol_ratio.iloc[-1] if len(vol_ratio) > 0 else 1.0
        
        # Volume confirmation threshold
        vol_confirm = curr_vol > 1.2
        
        cross = _detect_crossover(close, ema9)
        
        if cross == 1 and curr_rsi > 45 and curr_rsi < 75:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.5, sl_mult=1.2)
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.60 + (0.05 if vol_confirm else 0),
                'strategy': 'justin_ema9_rsi',
                'timestamp': _now_iso(),
                'reason': f'EMA9 cross + RSI {curr_rsi:.1f} + Vol {curr_vol:.2f}'
            })
        elif cross == -1 and curr_rsi < 55 and curr_rsi > 25:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.5, sl_mult=1.2)
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.60 + (0.05 if vol_confirm else 0),
                'strategy': 'justin_ema9_rsi',
                'timestamp': _now_iso(),
                'reason': f'EMA9 cross + RSI {curr_rsi:.1f} + Vol {curr_vol:.2f}'
            })
    
    return picks


# =============================================================================
# STRATEGY 3: Justin EMA9 + HTF RSI Bias (1h/4h simulation)
# =============================================================================

def justin_ema9_htf_bias_crypto(data: Dict[str, pd.DataFrame],
                                 context: Optional[dict] = None) -> List[dict]:
    """
    Justin's Multi-Timeframe Strategy:
    - Use EMA9 on current timeframe for entry
    - Use RSI on longer lookback for trend bias
    - Only take trades aligned with HTF trend
    """
    picks = []
    htf_lookback = 48  # Simulate 4h bias on 5m data (48 * 5m = 4h)
    
    for symbol, df in data.items():
        if len(df) < htf_lookback:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Current timeframe indicators
        ema9 = ema(close, 9)
        
        # HTF trend bias (using longer RSI)
        htf_rsi = rsi(close, htf_lookback)
        htf_bias = 'UP' if htf_rsi.iloc[-1] > 50 else 'DOWN'
        
        cross = _detect_crossover(close, ema9)
        
        # Only take trades aligned with HTF bias
        if cross == 1 and htf_bias == 'UP':
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=3.0, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.65,
                'strategy': 'justin_ema9_htf_bias',
                'timestamp': _now_iso(),
                'reason': f'EMA9 cross aligned with HTF {htf_bias} bias'
            })
        elif cross == -1 and htf_bias == 'DOWN':
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=3.0, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.65,
                'strategy': 'justin_ema9_htf_bias',
                'timestamp': _now_iso(),
                'reason': f'EMA9 cross aligned with HTF {htf_bias} bias'
            })
    
    return picks


# =============================================================================
# STRATEGY 4: J Bravo 9 Count + Bands
# =============================================================================

def bravo_nine_count_crypto(data: Dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> List[dict]:
    """
    J Bravo 9 Count System with Bravo Bands:
    - Trade trend exhaustion/reversal after 9-count
    - Use Fibonacci bands for TP/SL levels
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 30:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Bravo 9 Count analysis
        nine = _bravo_nine_count(close, high, low)
        
        # Fibonacci levels (Bravo Bands)
        fib = _fibonacci_levels(high, low, close)
        curr_price = close.iloc[-1]
        
        # Trade exhaustion reversals
        if nine['exhaustion']:
            if nine['direction'] == 'UP':
                # Bullish exhaustion - look for short
                entry = curr_price
                tp = fib['382']  # Pullback to 38.2%
                sl = fib['high'] * 1.02  # Above recent high
                picks.append({
                    'symbol': symbol,
                    'direction': 'SHORT',
                    'entry_price': _smart_round(entry),
                    'take_profit': _smart_round(tp),
                    'stop_loss': _smart_round(sl),
                    'confidence': 0.60,
                    'strategy': 'bravo_nine_count',
                    'timestamp': _now_iso(),
                    'reason': f'9-count exhaustion UP (angle: {nine["angle"]:.1f}°)'
                })
            else:
                # Bearish exhaustion - look for long
                entry = curr_price
                tp = fib['618']  # Rally to 61.8%
                sl = fib['low'] * 0.98  # Below recent low
                picks.append({
                    'symbol': symbol,
                    'direction': 'LONG',
                    'entry_price': _smart_round(entry),
                    'take_profit': _smart_round(tp),
                    'stop_loss': _smart_round(sl),
                    'confidence': 0.60,
                    'strategy': 'bravo_nine_count',
                    'timestamp': _now_iso(),
                    'reason': f'9-count exhaustion DOWN (angle: {nine["angle"]:.1f}°)'
                })
    
    return picks


# =============================================================================
# STRATEGY 5: Pattern Recognition (Double Top/Bottom + Tweezer)
# =============================================================================

def pattern_reversal_crypto(data: Dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> List[dict]:
    """
    Pattern-based reversal strategy:
    - Double tops/bottoms
    - Tweezer tops/bottoms
    - Combined with RSI for confirmation
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 25:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        open_s = df['open']
        
        # Pattern detection
        double = _detect_double_top(high, low, close)
        tweezer = _detect_tweezer(high, low, open_s, close)
        
        # RSI confirmation
        rsi_val = rsi(close, 14).iloc[-1]
        
        # Combine patterns (either double or tweezer)
        pattern_signal = double if double != 0 else tweezer
        
        if pattern_signal == -1 and rsi_val > 60:  # Bearish pattern + overbought
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.0, sl_mult=1.0)
            pattern_name = 'Double Top' if double == -1 else 'Tweezer Top'
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.62,
                'strategy': 'pattern_reversal',
                'timestamp': _now_iso(),
                'reason': f'{pattern_name} + RSI {rsi_val:.1f}'
            })
        elif pattern_signal == 1 and rsi_val < 40:  # Bullish pattern + oversold
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.0, sl_mult=1.0)
            pattern_name = 'Double Bottom' if double == 1 else 'Tweezer Bottom'
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.62,
                'strategy': 'pattern_reversal',
                'timestamp': _now_iso(),
                'reason': f'{pattern_name} + RSI {rsi_val:.1f}'
            })
    
    return picks


# =============================================================================
# STRATEGY 6: EMA Ribbon Confluence (J Bravo Method)
# =============================================================================

def ema_ribbon_confluence_crypto(data: Dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> List[dict]:
    """
    J Bravo EMA Ribbon Strategy:
    - Multiple EMAs (9, 21, 50) for trend alignment
    - Trade when price aligns with all EMAs
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 55:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # EMA Ribbon
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        ema50 = ema(close, 50)
        
        curr_close = close.iloc[-1]
        curr_9 = ema9.iloc[-1]
        curr_21 = ema21.iloc[-1]
        curr_50 = ema50.iloc[-1]
        
        # Strong uptrend: price > EMA9 > EMA21 > EMA50
        strong_up = curr_close > curr_9 > curr_21 > curr_50
        # Strong downtrend: price < EMA9 < EMA21 < EMA50
        strong_down = curr_close < curr_9 < curr_21 < curr_50
        
        # RSI filter
        rsi_val = rsi(close, 14).iloc[-1]
        
        if strong_up and rsi_val > 50 and rsi_val < 80:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=3.0, sl_mult=1.5)
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.68,
                'strategy': 'ema_ribbon_confluence',
                'timestamp': _now_iso(),
                'reason': f'EMA Ribbon aligned UP (RSI {rsi_val:.1f})'
            })
        elif strong_down and rsi_val < 50 and rsi_val > 20:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=3.0, sl_mult=1.5)
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.68,
                'strategy': 'ema_ribbon_confluence',
                'timestamp': _now_iso(),
                'reason': f'EMA Ribbon aligned DOWN (RSI {rsi_val:.1f})'
            })
    
    return picks


# =============================================================================
# STRATEGY 7: Justin Full System (Combined)
# =============================================================================

def justin_full_system_crypto(data: Dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> List[dict]:
    """
    Justin's Complete Trading System:
    - EMA9 crossover for entry
    - RSI confirmation (not overbought/oversold)
    - Volume confirmation
    - HTF trend alignment
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 50:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Indicators
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)  # Trend filter
        rsi_val = rsi(close, 14)
        vol_ratio_val = volume_ratio(volume, 20)
        
        # HTF RSI (trend bias)
        htf_rsi = rsi(close, 48)
        
        curr_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        curr_ema9 = ema9.iloc[-1]
        prev_ema9 = ema9.iloc[-2]
        curr_ema21 = ema21.iloc[-1]
        curr_rsi = rsi_val.iloc[-1]
        curr_vol = vol_ratio_val.iloc[-1] if len(vol_ratio_val) > 0 else 1.0
        htf_bias = htf_rsi.iloc[-1]
        
        # Cross detection
        bullish_cross = prev_close <= prev_ema9 and curr_close > curr_ema9
        bearish_cross = prev_close >= prev_ema9 and curr_close < curr_ema9
        
        confidence = 0.55
        reasons = []
        
        # LONG conditions
        if bullish_cross:
            direction = 'LONG'
            
            # RSI confirmation (not overbought)
            if 45 < curr_rsi < 70:
                confidence += 0.05
                reasons.append(f'RSI {curr_rsi:.1f}')
            
            # Volume confirmation
            if curr_vol > 1.2:
                confidence += 0.05
                reasons.append(f'Vol {curr_vol:.2f}x')
            
            # HTF trend alignment
            if htf_bias > 55:
                confidence += 0.08
                reasons.append('HTF UP')
            
            # Trend alignment (EMA9 > EMA21)
            if curr_ema9 > curr_ema21:
                confidence += 0.05
                reasons.append('EMA9>21')
            
            if confidence >= 0.65:  # Minimum threshold
                entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.5, sl_mult=1.0)
                picks.append({
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': entry,
                    'take_profit': tp,
                    'stop_loss': sl,
                    'confidence': min(confidence, 0.85),
                    'strategy': 'justin_full_system',
                    'timestamp': _now_iso(),
                    'reason': 'EMA9 cross + ' + ', '.join(reasons)
                })
        
        # SHORT conditions
        elif bearish_cross:
            direction = 'SHORT'
            
            # RSI confirmation (not oversold)
            if 30 < curr_rsi < 55:
                confidence += 0.05
                reasons.append(f'RSI {curr_rsi:.1f}')
            
            # Volume confirmation
            if curr_vol > 1.2:
                confidence += 0.05
                reasons.append(f'Vol {curr_vol:.2f}x')
            
            # HTF trend alignment
            if htf_bias < 45:
                confidence += 0.08
                reasons.append('HTF DOWN')
            
            # Trend alignment (EMA9 < EMA21)
            if curr_ema9 < curr_ema21:
                confidence += 0.05
                reasons.append('EMA9<21')
            
            if confidence >= 0.65:
                entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.5, sl_mult=1.0)
                picks.append({
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': entry,
                    'take_profit': tp,
                    'stop_loss': sl,
                    'confidence': min(confidence, 0.85),
                    'strategy': 'justin_full_system',
                    'timestamp': _now_iso(),
                    'reason': 'EMA9 cross + ' + ', '.join(reasons)
                })
    
    return picks


# =============================================================================
# STRATEGY 8: Volume-Weighted EMA9 (J Bravo Enhancement)
# =============================================================================

def volume_weighted_ema9_crypto(data: Dict[str, pd.DataFrame],
                                 context: Optional[dict] = None) -> List[dict]:
    """
    Volume-Weighted EMA9 Strategy:
    - Weight EMA by volume for better signals
    - Only trade on above-average volume
    """
    picks = []
    
    for symbol, df in data.items():
        if len(df) < 30:
            continue
            
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([1] * len(df)))
        
        # Volume-weighted close
        vol_ma = volume.rolling(window=20).mean()
        vol_multiplier = volume / vol_ma
        weighted_close = close * vol_multiplier
        
        # Standard and volume-weighted EMA9
        std_ema9 = ema(close, 9)
        vw_ema9 = ema(weighted_close, 9)
        
        curr_close = close.iloc[-1]
        curr_vol_ratio = vol_multiplier.iloc[-1]
        
        # Only trade on volume confirmation
        if curr_vol_ratio < 1.3:
            continue
        
        # Cross of price vs volume-weighted EMA9
        cross = _detect_crossover(close, vw_ema9)
        
        rsi_val = rsi(close, 14).iloc[-1]
        
        if cross == 1 and rsi_val > 45:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.2, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.62,
                'strategy': 'volume_weighted_ema9',
                'timestamp': _now_iso(),
                'reason': f'VW-EMA9 cross + Vol {curr_vol_ratio:.2f}x'
            })
        elif cross == -1 and rsi_val < 55:
            entry, tp, sl = _atr_based_levels(close, high, low, tp_mult=2.2, sl_mult=1.0)
            picks.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'confidence': 0.62,
                'strategy': 'volume_weighted_ema9',
                'timestamp': _now_iso(),
                'reason': f'VW-EMA9 cross + Vol {curr_vol_ratio:.2f}x'
            })
    
    return picks


# =============================================================================
# STRATEGY REGISTRY
# =============================================================================

JUSTIN_BRAVO_STRATEGIES = {
    'justin_ema9_basic': justin_ema9_basic_crypto,
    'justin_ema9_rsi': justin_ema9_rsi_crypto,
    'justin_ema9_htf_bias': justin_ema9_htf_bias_crypto,
    'bravo_nine_count': bravo_nine_count_crypto,
    'pattern_reversal': pattern_reversal_crypto,
    'ema_ribbon_confluence': ema_ribbon_confluence_crypto,
    'justin_full_system': justin_full_system_crypto,
    'volume_weighted_ema9': volume_weighted_ema9_crypto,
}


def run_all_justin_strategies(data: Dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> List[dict]:
    """Run all Justin/Bravo strategies and return combined picks."""
    all_picks = []
    
    for name, strategy_fn in JUSTIN_BRAVO_STRATEGIES.items():
        try:
            picks = strategy_fn(data, context)
            all_picks.extend(picks)
        except Exception as e:
            print(f"Error in {name}: {e}")
    
    return all_picks


if __name__ == '__main__':
    print("Justin & J Bravo Strategies Module")
    print("Available strategies:")
    for name in JUSTIN_BRAVO_STRATEGIES.keys():
        print(f"  - {name}")
