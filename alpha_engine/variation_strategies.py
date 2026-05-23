#!/usr/bin/env python3
""" 
ALPHA_ENGINE -- Enhanced Variation Strategies with Validation & Dynamic Thresholds
===========================================================================
Enhanced with:
- Input validation
- Dynamic thresholds from config/thresholds.json
- Volatility-adjusted TP/SL
- Comprehensive logging
- Exception handling per symbol

Strategies:
1. keltner_hma_filter: Keltner squeeze + dynamic HMA slope
2. multi_sigma_volume: Dynamic sigma reversion + volume confirm
3. hurst_rsi_extreme: Hurst regime + dynamic RSI extremes
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone

from config import ALL_SYMBOLS
from indicators import (atr, bollinger_squeeze, hma_slope, keltner_channels, 
                       volume_expansion, zscore, rsi, hurst_exponent)
from alpha_engine.utils.validation import (
    validate_dataframe, load_thresholds, adjust_thresholds, AlgorithmInputError
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_category(symbol: str) -> str:
    return ALL_SYMBOLS.get(symbol, {}).get("cat", "crypto")

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
    else:
        return round(value, 10)

def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series, tp_mult: float, sl_mult: float, atr_period: int = 14):
    # Avoid data leakage: calculate ATR on historical data only
    atr_series = atr(high.iloc[:-1], low.iloc[:-1], close.iloc[:-1], atr_period)
    atr_val = atr_series.iloc[-1] if not atr_series.empty else atr(high, low, close, atr_period).iloc[-1]
    price = close.iloc[-1]
    tp_long = price + tp_mult * atr_val
    sl_long = price - sl_mult * atr_val
    return _smart_round(price), _smart_round(tp_long), _smart_round(sl_long)

def keltner_hma_filter(data: Dict[str, pd.DataFrame], context: Optional[Dict] = None) -> list[dict]:
    """Enhanced Keltner squeeze breakout with dynamic HMA slope threshold."""
    thresholds = load_thresholds()
    signals = []
    for symbol in data:
        try:
            df = validate_dataframe(data[symbol])
            volatility = df['Close'].pct_change().rolling(20).std().iloc[-1] or 1.0
            
            kc = keltner_channels(df['High'], df['Low'], df['Close'])
            bs = bollinger_squeeze(df['Close'], df['High'], df['Low'])
            hs = hma_slope(df['Close'])
            
            if pd.isna(bs.iloc[-1]) or pd.isna(hs.iloc[-1]):
                continue
                
            strat_config = thresholds.get('keltner_hma_filter', {})
            slope_threshold = adjust_thresholds(strat_config.get('slope_threshold', 0.0), volatility, thresholds)
            
            global_config = thresholds.get('global', {})
            tp_mult = adjust_thresholds(global_config.get('tp_mult_base', 2.5), volatility, thresholds)
            sl_mult = adjust_thresholds(global_config.get('sl_mult_base', 1.5), volatility, thresholds)
            atr_period = global_config.get('atr_period', 14)
            
            price = df['Close'].iloc[-1]
            if bs.iloc[-1]:
                if price > kc['upper'].iloc[-1] and hs.iloc[-1] > slope_threshold:
                    entry, tp, sl = _atr_tp_sl(df['Close'], df['High'], df['Low'], tp_mult, sl_mult, atr_period)
                    signals.append({
                        "strategy": "keltner_hma_filter_enhanced",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "BUY",
                        "entry_price": entry,
                        "take_profit": tp,
                        "stop_loss": sl,
                        "confidence": 0.80,
                        "risk_reward": tp_mult / sl_mult,
                        "reason": f"Keltner squeeze breakout + HMA slope>{slope_threshold:.3f} (vol={volatility:.2f}) on {symbol}",
                        "timestamp": _now_iso()
                    })
                    logger.info(f"BUY signal generated for {symbol}")
                elif price < kc['lower'].iloc[-1] and hs.iloc[-1] < -slope_threshold:
                    entry, _, _ = _atr_tp_sl(df['Close'], df['High'], df['Low'], tp_mult, sl_mult, atr_period)
                    atr_val = atr(df['High'].iloc[:-1], df['Low'].iloc[:-1], df['Close'].iloc[:-1], atr_period).iloc[-1]
                    tp = _smart_round(entry - tp_mult * atr_val)
                    sl = _smart_round(entry + sl_mult * atr_val)
                    signals.append({
                        "strategy": "keltner_hma_filter_enhanced",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "entry_price": entry,
                        "take_profit": tp,
                        "stop_loss": sl,
                        "confidence": 0.80,
                        "risk_reward": tp_mult / sl_mult,
                        "reason": f"Keltner squeeze breakdown + HMA slope<{-slope_threshold:.3f} (vol={volatility:.2f}) on {symbol}",
                        "timestamp": _now_iso()
                    })
                    logger.info(f"SELL signal generated for {symbol}")
        except AlgorithmInputError as e:
            logger.warning(f"Invalid data for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Error processing {symbol} in keltner_hma_filter: {e}")
    logger.info(f"Generated {len(signals)} signals from keltner_hma_filter")
    return signals

def multi_sigma_volume(data: Dict[str, pd.DataFrame], context: Optional[Dict] = None) -> list[dict]:
    """Enhanced multi-sigma reversion with dynamic threshold and volume confirm."""
    thresholds = load_thresholds()
    signals = []
    for symbol in data:
        try:
            df = validate_dataframe(data[symbol])
            volatility = df['Close'].pct_change().rolling(20).std().iloc[-1] or 1.0
            
            rets = df['Close'].pct_change()
            z = zscore(rets, thresholds.get('multi_sigma_volume', {}).get('lookback', 100))
            ve = volume_expansion(df['Volume'])
            
            if pd.isna(z.iloc[-1]) or pd.isna(ve.iloc[-1]):
                continue
                
            strat_config = thresholds.get('multi_sigma_volume', {})
            sigma_threshold = adjust_thresholds(strat_config.get('sigma_threshold', 2.5), volatility, thresholds)
            
            global_config = thresholds.get('global', {})
            tp_mult = adjust_thresholds(global_config.get('tp_mult_base', 2.0), volatility, thresholds)
            sl_mult = adjust_thresholds(global_config.get('sl_mult_base', 1.5), volatility, thresholds)
            
            if abs(z.iloc[-1]) > sigma_threshold and ve.iloc[-1]:
                price = df['Close'].iloc[-1]
                entry, tp_long, sl_long = _atr_tp_sl(df['Close'], df['High'], df['Low'], tp_mult, sl_mult)
                if z.iloc[-1] > sigma_threshold:
                    atr_val = atr(df['High'].iloc[:-1], df['Low'].iloc[:-1], df['Close'].iloc[:-1]).iloc[-1]
                    tp = _smart_round(entry - tp_mult * atr_val)
                    sl = sl_long
                    sig_type = "SELL"
                else:
                    atr_val = atr(df['High'].iloc[:-1], df['Low'].iloc[:-1], df['Close'].iloc[:-1]).iloc[-1]
                    tp = tp_long
                    sl = _smart_round(entry - sl_mult * atr_val)
                    sig_type = "BUY"
                signals.append({
                    "strategy": "multi_sigma_volume_enhanced",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": sig_type,
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": 0.85,
                    "risk_reward": tp_mult / sl_mult,
                    "reason": f"{z.iloc[-1]:.1f}sigma (thresh={sigma_threshold:.1f}) + vol exp (vol={volatility:.2f}) on {symbol}",
                    "timestamp": _now_iso()
                })
                logger.info(f"{sig_type} signal generated for {symbol}")
        except AlgorithmInputError as e:
            logger.warning(f"Invalid data for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Error processing {symbol} in multi_sigma_volume: {e}")
    logger.info(f"Generated {len(signals)} signals from multi_sigma_volume")
    return signals

def hurst_rsi_extreme(data: Dict[str, pd.DataFrame], context: Optional[Dict] = None) -> list[dict]:
    """Enhanced Hurst regime + dynamic RSI extremes."""
    thresholds = load_thresholds()
    signals = []
    for symbol in data:
        try:
            df = validate_dataframe(data[symbol])
            volatility = df['Close'].pct_change().rolling(20).std().iloc[-1] or 1.0
            
            strat_config = thresholds.get('hurst_rsi_extreme', {})
            h = hurst_exponent(df['Close'])
            rsi_period = strat_config.get('rsi_period', 2)
            rsi2 = rsi(df['Close'], rsi_period).iloc[-1]
            
            hurst_threshold = adjust_thresholds(strat_config.get('hurst_threshold', 0.40), volatility, thresholds)
            rsi_low = adjust_thresholds(strat_config.get('rsi_low', 10), volatility, thresholds)
            rsi_high = adjust_thresholds(strat_config.get('rsi_high', 90), volatility, thresholds)
            
            if h < hurst_threshold:
                price = df['Close'].iloc[-1]
                global_config = thresholds.get('global', {})
                tp_mult = adjust_thresholds(global_config.get('tp_mult_base', 2.5), volatility, thresholds)
                sl_mult = adjust_thresholds(global_config.get('sl_mult_base', 1.5), volatility, thresholds)
                entry, tp_long, sl_long = _atr_tp_sl(df['Close'], df['High'], df['Low'], tp_mult, sl_mult)
                
                if rsi2 < rsi_low:
                    tp = tp_long
                    sl = sl_long
                    sig_type = "BUY"
                elif rsi2 > rsi_high:
                    atr_val = atr(df['High'].iloc[:-1], df['Low'].iloc[:-1], df['Close'].iloc[:-1]).iloc[-1]
                    tp = _smart_round(entry - tp_mult * atr_val)
                    sl = _smart_round(entry + sl_mult * atr_val)
                    sig_type = "SELL"
                else:
                    continue
                
                signals.append({
                    "strategy": "hurst_rsi_extreme_enhanced",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": sig_type,
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": 0.82,
                    "risk_reward": tp_mult / sl_mult,
                    "reason": f"Hurst H={h:.2f}<{hurst_threshold:.2f} + RSI{rsi_period}={rsi2:.0f} extreme (vol={volatility:.2f}) on {symbol}",
                    "timestamp": _now_iso()
                })
                logger.info(f"{sig_type} signal generated for {symbol}")
        except AlgorithmInputError as e:
            logger.warning(f"Invalid data for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Error processing {symbol} in hurst_rsi_extreme: {e}")
    logger.info(f"Generated {len(signals)} signals from hurst_rsi_extreme")
    return signals