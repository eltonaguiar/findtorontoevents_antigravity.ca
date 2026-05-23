import json
import pandas as pd
import numpy as np
import os

def analyze_closed_picks(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return
    
    df = pd.DataFrame(data)
    
    # Filter for needed columns
    cols = ['symbol', 'strategy', 'pnl_pct', 'exit_reason', 'elite_score', 'ml_composite_score', 'method_a_score', 'confidence']
    available_cols = [c for c in cols if c in df.columns]
    df = df[available_cols]
    
    # Pre-process columns to avoid numeric conversion errors
    numeric_cols = ['pnl_pct', 'elite_score', 'ml_composite_score', 'method_a_score', 'confidence']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # Correlation with PnL
    if 'pnl_pct' in df.columns:
        numeric_avail = [c for c in df.columns if c in numeric_cols]
        corrs = df[numeric_avail].corr()
        print("Correlations with PnL:")
        print(corrs['pnl_pct'].sort_values(ascending=False))
    
    # Exit Reason Analysis
    if 'exit_reason' in df.columns and 'pnl_pct' in df.columns:
        exit_stats = df.groupby('exit_reason')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum')
        print("\nExit Reason Stats:")
        print(exit_stats)
    
    # Toxic Symbols (bottom 10 by total PnL)
    if 'symbol' in df.columns and 'pnl_pct' in df.columns:
        toxic_symbols = df.groupby('symbol')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum').head(10)
        print("\nToxic Symbols (Bottom 10):")
        print(toxic_symbols)
    
    # Strategy Analysis
    if 'strategy' in df.columns and 'pnl_pct' in df.columns:
        strat_stats = df.groupby('strategy')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum')
        print("\nStrategy Stats (Worst 10):")
        print(strat_stats.head(10))
        print("\nStrategy Stats (Best 10):")
        print(strat_stats.tail(10))

if __name__ == "__main__":
    analyze_closed_picks('e:/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json')
