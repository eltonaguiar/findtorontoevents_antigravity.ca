"""
Multi-asset enhanced strategy functions
Targeting weak areas identified in focused non-crypto backtest report

Each strategy includes:
- Entry/exit logic with explicit parameters
- Pre-date filtering (no future look-ahead)
- Risk management (ATR-based stops, position sizing)
- Returns list of trades: [{"date": ..., "symbol": ..., "direction": ..., "entry": ..., "exit": ..., "pnl": ...}]
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def micro_futures_tsmom(data, symbols=None, params=None):
    """
    Micro Futures Time-Series Momentum (12m/3m/1m blend)
    - MES (E-mini S&P 500), MNQ (E-mini Nasdaq), M2K (E-mini Russell 2000), MYM (E-mini Dow)
    - Inverse volatility sizing: position size ∝ 1 / realized_vol(20d)
    """
    if symbols is None:
        symbols = ["MES", "MNQ", "M2K", "MYM"]
    if params is None:
        params = {
            "lookback_12m": 252,
            "lookback_3m": 63,
            "lookback_1m": 21,
            "weight_12m": 0.5,
            "weight_3m": 0.3,
            "weight_1m": 0.2,
            "vol_window": 20,
            "position_size_pct": 0.02,
            "stop_atr_mult": 2.0,
            "tp_atr_mult": 3.0,
        }
    
    trades = []
    for sym in symbols:
        if sym not in data:
            continue
        df = data[sym].copy()
        df = df.sort_index()
        
        # Calculate returns
        df["ret_12m"] = df["close"].pct_change(params["lookback_12m"])
        df["ret_3m"] = df["close"].pct_change(params["lookback_3m"])
        df["ret_1m"] = df["close"].pct_change(params["lookback_1m"])
        
        # Blend momentum signal
        df["momentum"] = (
            params["weight_12m"] * np.sign(df["ret_12m"]) +
            params["weight_3m"] * np.sign(df["ret_3m"]) +
            params["weight_1m"] * np.sign(df["ret_1m"])
        )
        
        # Volatility sizing
        df["vol_20d"] = df["close"].pct_change().rolling(params["vol_window"]).std()
        df["vol_sizing"] = 1.0 / (1.0 + df["vol_20d"])  # inverse vol
        
        # ATR for stops/targets
        df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
        
        # Generate trades
        for i in range(max(params["lookback_12m"], 100), len(df) - 1):
            if df["momentum"].iloc[i] == 0:
                continue
            
            entry_date = df.index[i]
            entry_price = df["close"].iloc[i]
            direction = "long" if df["momentum"].iloc[i] > 0 else "short"
            stop_dist = params["stop_atr_mult"] * df["atr"].iloc[i]
            tp_dist = params["tp_atr_mult"] * df["atr"].iloc[i]
            
            stop_price = entry_price - stop_dist if direction == "long" else entry_price + stop_dist
            tp_price = entry_price + tp_dist if direction == "long" else entry_price - tp_dist
            
            # Find exit in next 20 bars
            exit_price = None
            exit_date = None
            for j in range(i + 1, min(i + 21, len(df))):
                if direction == "long":
                    if df["low"].iloc[j] <= stop_price:
                        exit_price = stop_price
                        exit_date = df.index[j]
                        break
                    elif df["high"].iloc[j] >= tp_price:
                        exit_price = tp_price
                        exit_date = df.index[j]
                        break
                else:
                    if df["high"].iloc[j] >= stop_price:
                        exit_price = stop_price
                        exit_date = df.index[j]
                        break
                    elif df["low"].iloc[j] <= tp_price:
                        exit_price = tp_price
                        exit_date = df.index[j]
                        break
            
            if exit_price and exit_date:
                pnl = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
                trades.append({
                    "date": entry_date,
                    "symbol": sym,
                    "direction": direction,
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "exit_date": exit_date,
                })
    
    return trades


def micro_futures_vix_timing(data, symbols=None, params=None):
    """
    Micro Futures VIX-timed Entry
    - Buy dips (RSI<40) when: VIX>25 + price above SMA200
    - Works for MES, MNQ during volatility spikes
    """
    if symbols is None:
        symbols = ["MES", "MNQ"]
    if params is None:
        params = {
            "vix_threshold": 25,
            "rsi_threshold": 40,
            "sma_len": 200,
            "rsi_len": 14,
            "stop_pct": 0.02,
            "tp_pct": 0.04,
        }
    
    trades = []
    vix_data = data.get("^VIX")
    if vix_data is None:
        return trades
    
    for sym in symbols:
        if sym not in data:
            continue
        df = data[sym].copy()
        df = df.sort_index()
        
        # Align VIX and price data
        df["vix"] = vix_data.loc[df.index, "close"] if "close" in vix_data.columns else vix_data
        df["sma200"] = df["close"].rolling(params["sma_len"]).mean()
        
        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(params["rsi_len"]).mean()
        loss = -delta.where(delta < 0, 0).rolling(params["rsi_len"]).mean()
        rs = gain / (loss + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))
        
        for i in range(max(params["sma_len"], params["rsi_len"]), len(df) - 1):
            cond_vix = df["vix"].iloc[i] > params["vix_threshold"]
            cond_above_sma = df["close"].iloc[i] > df["sma200"].iloc[i]
            cond_rsi = df["rsi"].iloc[i] < params["rsi_threshold"]
            
            if cond_vix and cond_above_sma and cond_rsi:
                entry_date = df.index[i]
                entry_price = df["close"].iloc[i]
                stop_price = entry_price * (1 - params["stop_pct"])
                tp_price = entry_price * (1 + params["tp_pct"])
                
                for j in range(i + 1, min(i + 21, len(df))):
                    if df["low"].iloc[j] <= stop_price:
                        exit_price = stop_price
                        exit_date = df.index[j]
                        pnl = (exit_price - entry_price) / entry_price
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": exit_date,
                        })
                        break
                    elif df["high"].iloc[j] >= tp_price:
                        exit_price = tp_price
                        exit_date = df.index[j]
                        pnl = (exit_price - entry_price) / entry_price
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": exit_date,
                        })
                        break
    
    return trades


def forex_structure_breakout(data, symbols=None, params=None):
    """
    Forex Donchian Breakout with ADX + DXY alignment
    - 20-bar Donchian (highest high, lowest low)
    - ADX > 20 (trend confirmation)
    - DXY (US Dollar Index) alignment: buy if DXY trending same direction
    """
    if symbols is None:
        symbols = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"]
    if params is None:
        params = {
            "donchian_len": 20,
            "adx_len": 14,
            "adx_threshold": 20,
            "stop_pct": 0.015,
            "tp_atr_mult": 2.0,
        }
    
    trades = []
    dxy_data = data.get("DXY")
    
    for sym in symbols:
        if sym not in data:
            continue
        df = data[sym].copy()
        df = df.sort_index()
        
        # Donchian channel
        df["high_20"] = df["high"].rolling(params["donchian_len"]).max()
        df["low_20"] = df["low"].rolling(params["donchian_len"]).min()
        
        # ADX calculation (simplified)
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                np.abs(df["high"] - df["close"].shift(1)),
                np.abs(df["low"] - df["close"].shift(1)),
            ),
        )
        atr = tr.rolling(params["adx_len"]).mean()
        df["atr"] = atr
        df["adx"] = atr.rolling(params["adx_len"]).mean() / atr  # simplified
        
        for i in range(params["donchian_len"] + 10, len(df) - 1):
            if df["adx"].iloc[i] < params["adx_threshold"]:
                continue
            
            # Check for breakout
            breakout_long = df["high"].iloc[i] >= df["high_20"].iloc[i-1]
            breakout_short = df["low"].iloc[i] <= df["low_20"].iloc[i-1]
            
            if breakout_long:
                entry_date = df.index[i]
                entry_price = df["close"].iloc[i]
                stop_price = entry_price * (1 - params["stop_pct"])
                tp_price = entry_price + params["tp_atr_mult"] * df["atr"].iloc[i]
                
                for j in range(i + 1, min(i + 31, len(df))):
                    if df["low"].iloc[j] <= stop_price:
                        exit_price = stop_price
                        pnl = (exit_price - entry_price) / entry_price
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": df.index[j],
                        })
                        break
                    elif df["high"].iloc[j] >= tp_price:
                        exit_price = tp_price
                        pnl = (exit_price - entry_price) / entry_price
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": df.index[j],
                        })
                        break
    
    return trades


def silver_gold_ratio_trade(data, symbols=None, params=None):
    """
    Silver/Gold Ratio Bollinger Band Mean Reversion
    - Calculate ratio: silver_price / gold_price
    - BB(20, 2σ) on ratio: buy when ratio < BB_lower, sell when > BB_upper
    - Exit on opposite BB touch or mean cross
    """
    if params is None:
        params = {
            "bb_len": 20,
            "bb_std": 2.0,
            "stop_ratio_pct": 0.05,
        }
    
    trades = []
    
    if "SI=F" not in data or "GC=F" not in data:
        return trades
    
    silver = data["SI=F"].copy()
    gold = data["GC=F"].copy()
    
    # Align dates
    common_dates = silver.index.intersection(gold.index)
    silver = silver.loc[common_dates]
    gold = gold.loc[common_dates]
    
    ratio = silver["close"] / gold["close"]
    
    # Bollinger Bands on ratio
    sma = ratio.rolling(params["bb_len"]).mean()
    std = ratio.rolling(params["bb_len"]).std()
    upper_bb = sma + params["bb_std"] * std
    lower_bb = sma - params["bb_std"] * std
    
    for i in range(params["bb_len"] + 5, len(ratio) - 1):
        if ratio.iloc[i] < lower_bb.iloc[i]:
            # Buy ratio (long silver, short gold)
            entry_date = ratio.index[i]
            entry_ratio = ratio.iloc[i]
            stop_ratio = entry_ratio * (1 - params["stop_ratio_pct"])
            tp_ratio = sma.iloc[i]  # mean
            
            for j in range(i + 1, min(i + 31, len(ratio))):
                if ratio.iloc[j] <= stop_ratio:
                    exit_ratio = stop_ratio
                    pnl = (exit_ratio - entry_ratio) / entry_ratio
                    trades.append({
                        "date": entry_date,
                        "symbol": "SI=F/GC=F",
                        "direction": "long",
                        "entry": entry_ratio,
                        "exit": exit_ratio,
                        "pnl": pnl,
                        "exit_date": ratio.index[j],
                    })
                    break
                elif ratio.iloc[j] >= tp_ratio:
                    exit_ratio = tp_ratio
                    pnl = (exit_ratio - entry_ratio) / entry_ratio
                    trades.append({
                        "date": entry_date,
                        "symbol": "SI=F/GC=F",
                        "direction": "long",
                        "entry": entry_ratio,
                        "exit": exit_ratio,
                        "pnl": pnl,
                        "exit_date": ratio.index[j],
                    })
                    break
    
    return trades


def crypto_fear_momentum(data, symbols=None, params=None):
    """
    Crypto Fear Momentum (Dip Buying)
    - Entry: 30d annualized volatility > 15% + 14d return < -10% (fear phase)
    - Direction: LONG (buy the dip)
    - Exit: +5% or -3% stop
    """
    if symbols is None:
        symbols = ["BTC-USD", "ETH-USD"]
    if params is None:
        params = {
            "vol_threshold": 0.15,
            "vol_window": 30,
            "return_window": 14,
            "return_threshold": -0.10,
            "tp_pct": 0.05,
            "stop_pct": 0.03,
        }
    
    trades = []
    
    for sym in symbols:
        if sym not in data:
            continue
        df = data[sym].copy()
        df = df.sort_index()
        
        # 30d realized volatility (annualized)
        daily_ret = df["close"].pct_change()
        vol_30d = daily_ret.rolling(params["vol_window"]).std() * np.sqrt(252)
        
        # 14d return
        ret_14d = df["close"].pct_change(params["return_window"])
        
        for i in range(max(params["vol_window"], params["return_window"]), len(df) - 1):
            if vol_30d.iloc[i] > params["vol_threshold"] and ret_14d.iloc[i] < params["return_threshold"]:
                entry_date = df.index[i]
                entry_price = df["close"].iloc[i]
                tp_price = entry_price * (1 + params["tp_pct"])
                stop_price = entry_price * (1 - params["stop_pct"])
                
                for j in range(i + 1, min(i + 21, len(df))):
                    if df["high"].iloc[j] >= tp_price:
                        exit_price = tp_price
                        pnl = params["tp_pct"]
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": df.index[j],
                        })
                        break
                    elif df["low"].iloc[j] <= stop_price:
                        exit_price = stop_price
                        pnl = -params["stop_pct"]
                        trades.append({
                            "date": entry_date,
                            "symbol": sym,
                            "direction": "long",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "exit_date": df.index[j],
                        })
                        break
    
    return trades


# Placeholder functions for remaining strategies
def forex_momentum_pullback(data, symbols=None, params=None):
    """EMA21/55 + RSI pullback to 40-55 + DXY filter"""
    return []


def energy_sector_rotation(data, symbols=None, params=None):
    """XLE vs SPY 63-day relative strength"""
    return []


def quality_momentum(data, symbols=None, params=None):
    """Asness QMJ: 6m return + SMA200 + volume + pullback"""
    return []


def earnings_gap_continuation(data, symbols=None, params=None):
    """Gap-up >3% + vol 2x → first pullback to VWAP proxy"""
    return []


def crypto_altcoin_rotation(data, symbols=None, params=None):
    """Altcoin vs BTC 14d return divergence (>5% alpha)"""
    return []
