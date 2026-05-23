import json
import pandas as pd
import numpy as np
import os

def analyze_asset_classes(file_path):
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
    
    # Ensure asset_class column exists
    if 'asset_class' not in df.columns:
        # Infer if possible or use default
        df['asset_class'] = 'CRYPTO'
        if 'symbol' in df.columns:
            # Simple heuristic: symbols with '-' or no 'USDT' might be non-crypto
            df.loc[df['symbol'].str.contains('-USD|AAPL|TSLA|SPY|QQQ|EUR|GBP|JPY|GLD'), 'asset_class'] = 'NON-CRYPTO'
            df.loc[df['symbol'].str.contains('EUR|GBP|JPY|USD='), 'asset_class'] = 'FOREX'
            df.loc[df['symbol'].str.contains('AAPL|TSLA|NVDA|SPY|QQQ|IWM'), 'asset_class'] = 'EQUITY'
            df.loc[df['symbol'].str.contains('GLD|SLV|USO|CPER'), 'asset_class'] = 'COMMODITY'

    # Pre-process columns
    numeric_cols = ['pnl_pct', 'elite_score', 'ml_composite_score', 'method_a_score', 'confidence', 'trust_score', 'score']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    results = {}
    
    for asset, group in df.groupby('asset_class'):
        print(f"\n=== Analysis: {asset} (n={len(group)}) ===")
        
        # 1. Performance
        avg_pnl = group['pnl_pct'].mean()
        win_rate = (group['pnl_pct'] > 0).mean() * 100
        print(f"Avg PnL: {avg_pnl:.4f}% | Win Rate: {win_rate:.2f}%")
        
        # 2. Scoring Correlation (FLAW DETECTION)
        avail_scores = [c for c in numeric_cols if c in group.columns and c != 'pnl_pct']
        if avail_scores:
            corrs = group[['pnl_pct'] + avail_scores].corr()['pnl_pct'].sort_values(ascending=False)
            print("\nScoring Correlation (Spearman heuristic):")
            print(corrs.drop('pnl_pct'))
            
            # Identify "Broken" scores (Correlation < 0.05 or negative)
            broken = corrs[corrs < 0.05].index.tolist()
            if broken:
                print(f"FLAWS: Scores {broken} are nearly non-predictive for {asset}.")

        # 3. Strategy Edge (EDGE DETECTION)
        if 'strategy' in group.columns:
            strat_stats = group.groupby('strategy')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum', ascending=False)
            top_strat = strat_stats.head(3)
            worst_strat = strat_stats.tail(3)
            print("\nTop 3 Strategies (Edge):")
            print(top_strat)
            print("\nWorst 3 Strategies (Toxic Mix):")
            print(worst_strat)

        results[asset] = {
            "n": len(group),
            "avg_pnl": avg_pnl,
            "win_rate": win_rate,
            "broken_scores": [c for c in avail_scores if group[['pnl_pct', c]].corr().iloc[0,1] < 0.05]
        }
    
    # Save to file
    with open('e:/findtorontoevents_antigravity.ca/ASSET_CLASS_EDGE_ANALYSIS.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to ASSET_CLASS_EDGE_ANALYSIS.json")

if __name__ == "__main__":
    # We use universal_resolved_picks.json first as it likely has the broader asset set
    target = 'e:/findtorontoevents_antigravity.ca/audit_trail/data/universal_resolved_picks.json'
    if not os.path.exists(target):
        target = 'e:/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json'
    
    print(f"Targeting: {target}")
    analyze_asset_classes(target)
