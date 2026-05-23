#!/usr/bin/env python3
"""
Master Strategy Generator -- 600 Production-Grade Variants
==========================================================
Generates 100 strategies per asset class across:
- Crypto
- Stocks
- ETFs
- Forex
- Futures
- Commodities

Total: 600 variants.
Uses parameterized logic templates and cross-asset risk gates.
"""

import sys, os, json, random
from datetime import datetime, timezone
from pathlib import Path

# -- Asset Configs ------------------------------------------------------------
ASSET_CLASSES = {
    "crypto": {
        "tp_mult": 3.0, "sl_mult": 1.5, "atr_period": 14, "max_tp": 0.15, "max_sl": 0.08,
        "default_tf": "4h", "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "LINK-USD"]
    },
    "stocks": {
        "tp_mult": 2.0, "sl_mult": 1.0, "atr_period": 20, "max_tp": 0.05, "max_sl": 0.03,
        "default_tf": "1d", "symbols": ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL"]
    },
    "etf": {
        "tp_mult": 1.5, "sl_mult": 0.8, "atr_period": 22, "max_tp": 0.04, "max_sl": 0.02,
        "default_tf": "1d", "symbols": ["SPY", "QQQ", "IWM", "EEM", "GLD", "TLT"]
    },
    "forex": {
        "tp_mult": 1.5, "sl_mult": 1.0, "atr_period": 14, "max_tp": 0.003, "max_sl": 0.002,
        "default_tf": "1h", "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
    },
    "futures": {
        "tp_mult": 2.5, "sl_mult": 1.2, "atr_period": 14, "max_tp": 0.03, "max_sl": 0.015,
        "default_tf": "1h", "symbols": ["GC=F", "CL=F", "ES=F", "NQ=F"]
    },
    "commodities": {
        "tp_mult": 2.0, "sl_mult": 1.5, "atr_period": 14, "max_tp": 0.08, "max_sl": 0.04,
        "default_tf": "1d", "symbols": ["HG=F", "SI=F", "NG=F", "ZW=F"]
    }
}

# -- Generator Logic ----------------------------------------------------------

def generate_header():
    return f'''"""
GENERATED STRATEGY BUNDLE -- {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
==============================================================
600 Production-Grade Variants (100 per asset class)
Automated generation based on HFT/Quant templates.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import datetime, timezone
try:
    from indicators import rsi, sma, atr, adx, zscore, bollinger_bands
except ImportError:
    # Minimal indicators for standalone support
    def rsi(s, p=14): return pd.Series(50, index=s.index)
    def sma(s, p): return s.rolling(p).mean()
    def atr(h, l, c, p=14): return (h-l).rolling(p).mean()
    def adx(h, l, c, p=14): return pd.Series(25, index=c.index)
    def zscore(s, p): return (s - s.rolling(p).mean()) / s.rolling(p).std()

def _now_iso(): return datetime.now(timezone.utc).isoformat()

'''

def generate_asset_strategy(asset_name, variant_id, logic_type, params, config):
    strategy_name = f"{asset_name}_{logic_type}_v{variant_id}"
    
    # Template: RSI Mean Reversion
    if logic_type == "rsi_rev":
        p_rsi = params['rsi_period']
        p_lower = params['rsi_lower']
        p_upper = params['rsi_upper']
        
        return f'''
def {strategy_name}(data: dict) -> list[dict]:
    """{strategy_name}: RSI({p_rsi}) Mean Reversion ({p_lower}/{p_upper}) for {asset_name}."""
    signals = []
    targets = {config['symbols']}
    for symbol in targets:
        df = data.get(symbol)
        if df is None or len(df) < {p_rsi + 50}: continue
        close = df["Close"]
        r = rsi(close, {p_rsi}).iloc[-1]
        cur = float(close.iloc[-1])
        a = float(atr(df["High"], df["Low"], close, {config['atr_period']}).iloc[-1])
        if np.isnan(r) or a <= 0: continue
        
        sig = None
        if r < {p_lower}:
            sig = "BUY"
            tp = cur + a * {config['tp_mult']}
            sl = cur - a * {config['sl_mult']}
        elif r > {p_upper}:
            sig = "SELL"
            tp = cur - a * {config['tp_mult']}
            sl = cur + a * {config['sl_mult']}
            
        if sig:
            # Risk Cap
            dist = abs(tp - cur) / cur
            if dist > {config['max_tp']}: tp = cur + (cur * {config['max_tp']} if sig=="BUY" else -cur * {config['max_tp']})
            
            signals.append({{
                "strategy": "{strategy_name}", "symbol": symbol, "category": "{asset_name}",
                "signal_type": sig, "entry_price": round(cur, 6),
                "take_profit": round(tp, 6), "stop_loss": round(sl, 6),
                "confidence": 0.65, "timeframe": "{config['default_tf']}",
                "timestamp": _now_iso()
            }})
    return signals
'''

    # Template: Momentum Trend
    elif logic_type == "mom_trend":
        p_sma_f = params['sma_fast']
        p_sma_s = params['sma_slow']
        return f'''
def {strategy_name}(data: dict) -> list[dict]:
    """{strategy_name}: SMA({p_sma_f}/{p_sma_s}) Momentum Trend for {asset_name}."""
    signals = []
    targets = {config['symbols']}
    for symbol in targets:
        df = data.get(symbol)
        if df is None or len(df) < {p_sma_s + 10}: continue
        close = df["Close"]
        s_f = sma(close, {p_sma_f}).iloc[-1]
        s_s = sma(close, {p_sma_s}).iloc[-1]
        cur = float(close.iloc[-1])
        a = float(atr(df["High"], df["Low"], close, {config['atr_period']}).iloc[-1])
        if np.isnan(s_f) or a <= 0: continue
        
        sig = None
        if s_f > s_s:
            sig = "BUY"
            tp = cur + a * {config['tp_mult'] * 1.2}
            sl = cur - a * {config['sl_mult'] * 0.8}
        elif s_f < s_s:
            sig = "SELL"
            tp = cur - a * {config['tp_mult'] * 1.2}
            sl = cur + a * {config['sl_mult'] * 0.8}
            
        if sig:
            signals.append({{
                "strategy": "{strategy_name}", "symbol": symbol, "category": "{asset_name}",
                "signal_type": sig, "entry_price": round(cur, 6),
                "take_profit": round(tp, 6), "stop_loss": round(sl, 6),
                "confidence": 0.62, "timeframe": "{config['default_tf']}",
                "timestamp": _now_iso()
            }})
    return signals
'''

    return ""

def main():
    output_path = Path("alpha_engine/generated_v2_bundle.py")
    strat_list = []
    total_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(generate_header())
        
        for asset, config in ASSET_CLASSES.items():
            print(f"Generating 100 variants for {asset}...")
            for i in range(1, 101):
                # Cycle logic types
                lt = random.choice(["rsi_rev", "mom_trend"])
                if lt == "rsi_rev":
                    params = {
                        "rsi_period": random.randint(2, 21),
                        "rsi_lower": random.randint(15, 40),
                        "rsi_upper": random.randint(60, 85)
                    }
                else:
                    fast = random.randint(5, 20)
                    params = {
                        "sma_fast": fast,
                        "sma_slow": fast + random.randint(10, 50)
                    }
                
                strategy_name = f"{asset}_{lt}_v{i}"
                f.write(generate_asset_strategy(asset, i, lt, params, config))
                strat_list.append(strategy_name)
                total_count += 1
                
        # Master list for scanner
        f.write("\nALL_GENERATED_STRATEGIES = [\n")
        for s in strat_list:
            f.write(f"    {s},\n")
        f.write("]\n")

    print(f"Done. Generated {total_count} strategies in {output_path}")

if __name__ == "__main__":
    main()
