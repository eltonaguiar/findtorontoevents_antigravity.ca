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
    
    # Pre-process columns
    numeric_cols = ['pnl_pct', 'elite_score', 'ml_composite_score', 'method_a_score', 'confidence']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # DOW Analysis
    if 'entry_time' in df.columns:
        df['dt'] = pd.to_datetime(df['entry_time'], errors='coerce')
        df['dow'] = df['dt'].dt.day_name()
        df['hour'] = df['dt'].dt.hour
        
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_stats = df.groupby('dow')['pnl_pct'].agg(['count', 'mean', 'sum']).reindex(dow_order)
        
        # Calculate win rate by DOW
        win_rate = df[df['pnl_pct'] > 0].groupby('dow')['pnl_pct'].count() / df.groupby('dow')['pnl_pct'].count()
        dow_stats['win_rate'] = (win_rate * 100).round(2).reindex(dow_order)
        
        print("\n=== Day-of-Week (DOW) Performance ===")
        print(dow_stats)
        
        # Best/Worst DOW
        best_dow = dow_stats['mean'].idxmax()
        worst_dow = dow_stats['mean'].idxmin()
        print(f"\nBest Performing Day: {best_dow} (Avg PnL: {dow_stats.loc[best_dow, 'mean']:.2f}%)")
        print(f"Worst Performing Day: {worst_dow} (Avg PnL: {dow_stats.loc[worst_dow, 'mean']:.2f}%)")
        
    # Correlation with PnL
    if 'pnl_pct' in df.columns:
        numeric_avail = [c for c in df.columns if c in numeric_cols]
        corrs = df[numeric_avail].corr()
        print("\n=== Correlations with PnL ===")
        print(corrs['pnl_pct'].sort_values(ascending=False))
    
    # Toxic Symbols (bottom 10 by total PnL)
    if 'symbol' in df.columns and 'pnl_pct' in df.columns:
        toxic_symbols = df.groupby('symbol')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum').head(10)
        print("\n=== Toxic Symbols (Bottom 10) ===")
        print(toxic_symbols)
    
if __name__ == "__main__":
    analyze_closed_picks('e:/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json')
