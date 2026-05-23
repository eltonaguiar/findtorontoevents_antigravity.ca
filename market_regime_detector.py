#!/usr/bin/env python3
"""
Market Regime Detector
======================

Detects market regimes (trending, sideways, volatile) for better strategy performance.
"""

import pandas as pd
import numpy as np


def calculate_trend_strength(close: np.ndarray, period: int = 20) -> float:
    """
    Calculate trend strength using moving average slope.
    
    Args:
        close: Close price array
        period: Moving average period
        
    Returns:
        Trend strength value between -1 (strong downtrend) and 1 (strong uptrend)
    """
    # Calculate exponential moving average
    ema = np.full_like(close, np.nan, dtype=float)
    if len(close) >= period:
        ema[period - 1] = np.mean(close[:period])
        k = 2.0 / (period + 1)
        for i in range(period, len(close)):
            ema[i] = close[i] * k + ema[i - 1] * (1 - k)
    
    if np.isnan(ema[-1]) or np.isnan(ema[-period]):
        return 0.0
    
    # Calculate slope
    slope = (ema[-1] - ema[-period]) / ema[-period]
    
    # Normalize to -1 to 1 range
    normalized_slope = np.tanh(slope * period)
    
    return normalized_slope


def calculate_volatility_regime(close: np.ndarray, period: int = 20) -> float:
    """
    Calculate volatility regime using ATR and Bollinger Bands.
    
    Args:
        close: Close price array
        period: Lookback period
        
    Returns:
        Volatility regime value between 0 (low volatility) and 1 (high volatility)
    """
    # Calculate ATR-like volatility
    returns = np.diff(close) / close[:-1]
    volatility = np.std(returns[-period:])
    
    # Calculate historical volatility percentile
    if len(returns) > period * 2:
        historical_vol = np.std(returns[-period*2:-period])
        volatility_ratio = volatility / historical_vol
    else:
        volatility_ratio = 1.0
    
    # Normalize to 0-1 range
    normalized_volatility = np.tanh(volatility_ratio)
    
    return max(0.0, min(1.0, normalized_volatility))


def calculate_consolidation_score(close: np.ndarray, period: int = 20) -> float:
    """
    Calculate consolidation score using price range analysis.
    
    Args:
        close: Close price array
        period: Lookback period
        
    Returns:
        Consolidation score between 0 (trending) and 1 (consolidating)
    """
    high = np.max(close[-period:])
    low = np.min(close[-period:])
    avg = np.mean(close[-period:])
    
    range_percent = (high - low) / avg
    
    # Convert range to consolidation score (higher range = less consolidation)
    consolidation_score = 1 - np.tanh(range_percent * period)
    
    return max(0.0, min(1.0, consolidation_score))


def detect_market_regime(df: pd.DataFrame) -> dict:
    """
    Detect current market regime - simplified and permissive.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Dictionary with regime information
    """
    close = df['close'].values.astype(float)
    
    trend_strength = calculate_trend_strength(close)
    volatility_regime = calculate_volatility_regime(close)
    consolidation_score = calculate_consolidation_score(close)
    
    # Determine primary regime - very permissive
    if consolidation_score > 0.9:
        regime = "SIDEWAYS"
    elif trend_strength > 0.1:
        regime = "UPTREND"
    elif trend_strength < -0.1:
        regime = "DOWNTREND"
    else:
        regime = "MIXED"
    
    # Volatility classification - very permissive
    if volatility_regime > 0.9:
        volatility = "HIGH"
    elif volatility_regime < 0.1:
        volatility = "LOW"
    else:
        volatility = "MEDIUM"
    
    return {
        'regime': regime,
        'trend_strength': trend_strength,
        'volatility_regime': volatility_regime,
        'volatility': volatility,
        'consolidation_score': consolidation_score,
        'trend_signal': "BUY" if trend_strength > 0.1 else "SELL" if trend_strength < -0.1 else "NEUTRAL"
    }


def calculate_regime_filtered_signals(df: pd.DataFrame, strategy_function) -> list:
    """
    Calculate strategy signals with regime filtering.
    
    Args:
        df: DataFrame with OHLCV data
        strategy_function: Strategy signal generator
        
    Returns:
        List of filtered signals
    """
    signals = []
    
    for i in range(100, len(df)):
        window_data = df.iloc[:i+1]
        regime = detect_market_regime(window_data)
        
        # Only trade in favorable regimes
        if regime['regime'] in ["UPTREND", "DOWNTREND"] and regime['volatility'] in ["MEDIUM", "HIGH"]:
            strategy_signals = strategy_function(window_data)
            if strategy_signals:
                signals.extend(strategy_signals)
    
    return signals


def backtest_with_regime_filter(df: pd.DataFrame, symbol: str, strategy_function,
                               initial_balance: float = 100000, max_risk: float = 0.02,
                               max_hold: int = 96) -> dict:
    """
    Backtest strategy with regime filtering.
    
    Args:
        df: Historical data
        symbol: Trading symbol
        strategy_function: Strategy signal generator
        initial_balance: Starting capital
        max_risk: Maximum risk per trade
        max_hold: Maximum hold time in bars
        
    Returns:
        Performance metrics
    """
    balance = initial_balance
    peak_balance = initial_balance
    positions = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trade_count = 0
    win_count = 0
    loss_count = 0
    total_pnl = 0
    gross_profit = 0
    gross_loss = 0
    max_drawdown = 0
    
    i = 100
    while i < len(df):
        bar_data = df.iloc[:i+1]
        regime = detect_market_regime(bar_data)
        
        if regime['regime'] in ["UPTREND", "DOWNTREND"] and regime['volatility'] in ["MEDIUM", "HIGH"]:
            signals = strategy_function(bar_data, symbol, account_balance=balance, max_hold_hours=4)
            
            if signals and positions == 0:
                signal = signals[0]
                trade_count += 1
                
                position_size = signal.position_size
                
                if position_size > 0:
                    positions = position_size
                    entry_price = signal.entry_price
                    stop_loss = signal.stop_loss
                    take_profit = signal.take_profit
                    
                    i += 1
                    
                    exit_i = i
                    exit_found = False
                    max_exit_i = min(i + max_hold, len(df))
                    
                    while exit_i < max_exit_i:
                        current_high = df['high'].iloc[exit_i]
                        current_low = df['low'].iloc[exit_i]
                        current_close = df['close'].iloc[exit_i]
                        
                        if signal.direction == "BUY":
                            if current_low <= stop_loss:
                                exit_price = stop_loss
                                pnl = (exit_price - entry_price) * positions
                                exit_found = True
                            elif current_high >= take_profit:
                                exit_price = take_profit
                                pnl = (exit_price - entry_price) * positions
                                exit_found = True
                            elif exit_i == max_exit_i - 1:
                                exit_price = current_close
                                pnl = (exit_price - entry_price) * positions
                                exit_found = True
                        else:
                            if current_high >= stop_loss:
                                exit_price = stop_loss
                                pnl = (entry_price - exit_price) * positions
                                exit_found = True
                            elif current_low <= take_profit:
                                exit_price = take_profit
                                pnl = (entry_price - exit_price) * positions
                                exit_found = True
                            elif exit_i == max_exit_i - 1:
                                exit_price = current_close
                                pnl = (entry_price - exit_price) * positions
                                exit_found = True
                                
                        if exit_found:
                            balance += pnl
                            total_pnl += pnl
                            
                            if pnl > 0:
                                win_count += 1
                                gross_profit += pnl
                            else:
                                loss_count += 1
                                gross_loss += abs(pnl)
                                
                            positions = 0
                            entry_price = 0
                            stop_loss = 0
                            take_profit = 0
                            
                            if balance > peak_balance:
                                peak_balance = balance
                                
                            current_drawdown = (peak_balance - balance) / peak_balance
                            if current_drawdown > max_drawdown:
                                max_drawdown = current_drawdown
                                
                            i = exit_i
                            break
                            
                        exit_i += 1
                        
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
            
    win_rate = win_count / trade_count if trade_count > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    total_return = (balance - initial_balance) / initial_balance
    average_win = gross_profit / win_count if win_count > 0 else 0
    average_loss = gross_loss / loss_count if loss_count > 0 else 0
    
    return {
        'symbol': symbol,
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_return': total_return,
        'total_pnl': total_pnl,
        'total_trades': trade_count,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'average_win': average_win,
        'average_loss': average_loss,
        'peak_balance': peak_balance,
        'max_drawdown': max_drawdown
    }
