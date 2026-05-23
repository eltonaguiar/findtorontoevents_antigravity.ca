import pandas as pd
import numpy as np
from collections import Counter
import re

def analyze_file(filepath):
    df = pd.read_csv(filepath)
    print(f"Analysis for {filepath}")
    print(f"Total rows: {len(df)}")
    
    # Clean PnL
    df['PnL_num'] = pd.to_numeric(df['PnL%'].astype(str).str.replace('%', ''), errors='coerce')
    pnl_valid = df.dropna(subset=['PnL_num'])
    print(f"Valid PnL rows: {len(pnl_valid)}")
    if len(pnl_valid) > 0:
        print("PnL stats:")
        print(pnl_valid['PnL_num'].describe())
        win_rate = (pnl_valid['PnL_num'] > 0).mean()
        print(f"Win rate: {win_rate:.2%}")
    
    # Score
    df['Score_num'] = df['Score'].astype(str).str.extract('(\\d+)').astype(float)
    if 'PnL_num' in df.columns and 'Score_num' in df.columns:
        corr = df.dropna(subset=['PnL_num', 'Score_num'])['Score_num'].corr(df.dropna(subset=['PnL_num', 'Score_num'])['PnL_num'])
        print(f"Score vs PnL correlation: {corr:.3f}")
    
    # Group by key columns
    groups = ['System', 'Strategy', 'Trust Tier', 'Grade']
    for col in groups:
        if col in df.columns:
            agg = pnl_valid.groupby(col)['PnL_num'].agg(['mean', 'count', 'std']).round(3)
            agg = agg[agg['count'] >= 5].sort_values('mean', ascending=False)
            print(f"\nTop {col} by avg PnL (min 5 trades):")
            print(agg.head(10))
    
    # Confluence Count
    if 'Confluence Count' in df.columns:
        df['Confluence_num'] = pd.to_numeric(df['Confluence Count'], errors='coerce')
        corr_conf = df.dropna(subset=['PnL_num', 'Confluence_num'])['Confluence_num'].corr(df.dropna(subset=['PnL_num', 'Confluence_num'])['PnL_num'])
        print(f"Confluence Count vs PnL correlation: {corr_conf:.3f}")
    
    # Direction in regime
    print("\nDirection Reason patterns:")
    reasons = ' '.join(df['Direction Reason'].dropna().astype(str))
    common = Counter(re.findall(r'\w+', reasons.lower()))
    print(common.most_common(20))
    
    return df

# Analyze both
closed_df = analyze_file('antigravity_closed_picks_2026-03-16.csv')
active_df = analyze_file('antigravity_active_picks_2026-03-16.csv')

print("\nActive picks live PnL stats:")
if 'PnL%' in active_df.columns:
    active_df['Live_PnL'] = pd.to_numeric(active_df['PnL%'].astype(str).str.replace('%', ''), errors='coerce')
    print(active_df['Live_PnL'].describe())

print("\nSummary complete.")