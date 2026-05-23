import pandas as pd
import numpy as np
from datetime import datetime, time
import logging

# World-Class v2.1 "Truly Strong" Suite
# Engineering Principles:
# 1. Dynamic Edge Targeting (DET): Percentile-based thresholds over rolling windows.
# 2. Execution Realism: ATR-based TP/SL with 1.5x R:R.
# 3. Regime Awareness: Adaptive logic for Bull/Bear/Chop.


def dynamic_night_alpha_v21(data: dict[str, pd.DataFrame], symbol: str, params: dict = None) -> list:
    """
    (Crypto/Forex Scalp) - Targets night mean-reversion with dynamic RSI percentile filters.
    Compatible with scanner: func(data, symbol)
    """
    df = data.get(symbol)
    if df is None or len(df) < 50: return []
    p = params or {'window': 14, 'rsi_period': 2, 'target_percentile': 10}
    
    # 1. MultiIndex Column Handling
    try:
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0]
            high = df["High"].iloc[:, 0]
            low = df["Low"].iloc[:, 0]
        else:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
    except Exception as e:
        logging.error(f"DET: Error accessing columns: {e}")
        return []

    # 2. Night Window Check (UTC)
    try:
        current_time = df.index[-1].time()
    except: return []
    if not (time(0, 0) <= current_time <= time(5, 0)):
        return []

    # 3. Dynamic RSI Calculation
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=p['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=p['rsi_period']).mean()
    rs = gain / (loss + 1e-10) # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    # 4. Percentile Threshold (DET)
    rsi_history = rsi.rolling(window=200).apply(lambda x: np.percentile(x, p['target_percentile']) if len(x) > 0 else 50)
    lower_threshold = rsi_history.iloc[-1]
    
    # 5. Signal Logic
    if rsi.iloc[-1] < lower_threshold and close.iloc[-1] < close.rolling(20).mean().iloc[-1]:
        atr_series = (high - low).rolling(14).mean()
        if len(atr_series) < 1: return []
        atr = atr_series.iloc[-1]
        return [{
            "symbol": symbol,
            "direction": "LONG",
            "entry_price": float(close.iloc[-1]),
            "take_profit": float(close.iloc[-1] + (atr * 1.5)),
            "stop_loss": float(close.iloc[-1] - (atr * 1.0)),
            "confidence": 0.72,
            "system": "world_class_v21_night_alpha"
        }]
    return []

def regime_adaptive_momentum_v21(data: dict[str, pd.DataFrame], symbol: str, regime: str = "BULL") -> list:
    """
    (Universal) - Directional logic that shifts with market regime.
    Compatible with scanner: func(data, symbol)
    """
    df = data.get(symbol)
    if df is None or len(df) < 100: return []
    
    try:
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0]
            high = df["High"].iloc[:, 0]
            low = df["Low"].iloc[:, 0]
        else:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
    except: return []

    ema_fast = close.ewm(span=20).mean()
    ema_slow = close.ewm(span=50).mean()
    atr_series = (high - low).rolling(14).mean()
    if len(atr_series) < 2: return []
    atr = atr_series.iloc[-1]

    if regime == "BULL":
        # Trend Following: Buy breakout of EMA20 while EMA50 is sloped up
        if close.iloc[-1] > ema_fast.iloc[-1] and ema_slow.iloc[-1] > ema_slow.iloc[-2]:
            if close.iloc[-2] <= ema_fast.iloc[-2]: # Cross-up
                return [{
                    "symbol": symbol,
                    "direction": "LONG",
                    "entry_price": float(close.iloc[-1]),
                    "take_profit": float(close.iloc[-1] + (atr * 2.5)),
                    "stop_loss": float(close.iloc[-1] - (atr * 1.5)),
                    "confidence": 0.81,
                    "system": "world_class_v21_regime_mom"
                }]
    elif regime == "BEAR":
        # Mean Reversion: Buy panic sells when RSI < 20
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain/(loss+1e-10))))
        if rsi.iloc[-1] < 20:
             return [{
                "symbol": symbol,
                "direction": "LONG",
                "entry_price": float(close.iloc[-1]),
                "take_profit": float(close.iloc[-1] + (atr * 1.2)),
                "stop_loss": float(close.iloc[-1] - (atr * 1.0)),
                "confidence": 0.65,
                "system": "world_class_v21_regime_mom"
            }]
    
    return []

def sector_relative_alpha_v21(data: dict[str, pd.DataFrame], symbol: str) -> list:
    """
    (Equities) - Identifies leading strength by comparing asset returns against benchmark.
    Compatible with scanner: func(data, symbol)
    Uses BTCUSDT or SPY as benchmark depending on available data.
    """
    df = data.get(symbol)
    if df is None or len(df) < 30: return []
    
    # Select benchmark (Crypto uses BTC, Equities uses SPY)
    benchmark_sym = "BTCUSDT" if symbol.endswith("USDT") else "SPY"
    benchmark_df = data.get(benchmark_sym)
    if benchmark_df is None or len(benchmark_df) < 30: return []
    
    try:
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0]
        else: close = df["Close"]
        
        if isinstance(benchmark_df.columns, pd.MultiIndex):
            bench_close = benchmark_df["Close"].iloc[:, 0]
        else: bench_close = benchmark_df["Close"]
    except: return []

    # Calculate 20-day relative strength
    asset_ret = close.pct_change(20).iloc[-1]
    # Sync index using nearest date
    try:
        idx_match = bench_close.index.get_indexer([close.index[-1]], method='pad')[0]
        if idx_match < 20: return []
        bench_ret = bench_close.pct_change(20).iloc[idx_match]
    except: return []
    
    if asset_ret > bench_ret * 1.5: # 50% relative outperformance
        # Wait for trend confirmation
        if close.iloc[-1] > close.rolling(20).mean().iloc[-1]:
            return [{
                "symbol": symbol,
                "direction": "LONG",
                "entry_price": float(close.iloc[-1]),
                "take_profit": float(close.iloc[-1] * 1.05), # Conservative 5%
                "stop_loss": float(close.iloc[-1] * 0.97),   # 3% SL
                "confidence": 0.77,
                "system": "world_class_v21_sector_rel"
            }]
    return []

# Strategy Dictionary for Scanner Integration
WORLD_CLASS_V21_STRATEGIES = {
    "world_class_v21_night_alpha": dynamic_night_alpha_v21,
    "world_class_v21_regime_mom": regime_adaptive_momentum_v21,
    "world_class_v21_sector_rel": sector_relative_alpha_v21
}
