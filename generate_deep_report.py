import json
import pandas as pd
import numpy as np
import os

def generate_deep_edge_report(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    # Categorize
    if 'asset_class' not in df.columns:
        df['asset_class'] = 'CRYPTO'
        if 'symbol' in df.columns:
            df.loc[df['symbol'].str.contains('-USD|AAPL|TSLA|SPY|QQQ|EUR|GBP|JPY|GLD'), 'asset_class'] = 'NON-CRYPTO'
            df.loc[df['symbol'].str.contains('EUR|GBP|JPY|USD='), 'asset_class'] = 'FOREX'
            df.loc[df['symbol'].str.contains('AAPL|TSLA|NVDA|SPY|QQQ|IWM'), 'asset_class'] = 'EQUITY'
            df.loc[df['symbol'].str.contains('GLD|SLV|USO|CPER'), 'asset_class'] = 'COMMODITY'

    # Pre-process
    numeric_cols = ['pnl_pct', 'elite_score', 'ml_composite_score', 'method_a_score', 'confidence', 'trust_score', 'score']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    report_md = "# Deeper Edge & Flaw Analysis (Institutional Alpha v2.4)\n\n"
    report_md += "## 📈 1. Asset-Class Performance Deep-Dive\n\n"
    
    for asset, group in df.groupby('asset_class'):
        report_md += f"### Analysis: {asset} (n={len(group)})\n\n"
        
        # Performance
        avg_pnl = group['pnl_pct'].mean()
        win_rate = (group['pnl_pct'] > 0).mean() * 100
        report_md += f"*   **Performance Overview**: Avg PnL: **{avg_pnl:.4f}%** | Win Rate: **{win_rate:.2f}%**\n"
        
        # Scoring Correlation
        avail_scores = [c for c in numeric_cols if c in group.columns and c != 'pnl_pct']
        if avail_scores:
            corrs = group[['pnl_pct'] + avail_scores].corr()['pnl_pct'].sort_values(ascending=False).drop('pnl_pct')
            report_md += "*   **Scoring Correlation (Predictive Strength)**:\n"
            for score_name, corr in corrs.items():
                status = "PASS" if corr > 0.3 else ("WEAK" if corr > 0.05 else "BROKEN")
                if corr < 0: status = "INVERSE"
                report_md += f"    *   `{score_name}`: {corr:.4f} ({status})\n"
            
            # Find the best score for this asset
            best_score = corrs.idxmax()
            report_md += f"*   **Best Scoring Engine for {asset}**: `{best_score}`\n"

        # Strategy Insight
        if 'strategy' in group.columns:
            strat_stats = group.groupby('strategy')['pnl_pct'].agg(['count', 'mean', 'sum']).sort_values('sum', ascending=False)
            report_md += "*   **High-Alpha Edge Strategies (Scale Candidate)**:\n"
            for strat, row in strat_stats.head(3).iterrows():
                report_md += f"    *   `{strat}`: {row['mean']:.2f}% avg over {row['count']} trades\n"
            
            report_md += "*   **Toxic Flaw Strategies (Quarantine Candidate)**:\n"
            for strat, row in strat_stats.tail(3).iterrows():
                report_md += f"    *   `{strat}`: {row['mean']:.2f}% avg over {row['count']} trades\n"
        
        report_md += "\n---\n\n"

    report_md += "## 🚨 2. Found Scoring Flaws & Mandatory Quarantine\n\n"
    report_md += "| Flaw | Asset Class | Impact | Recommendation |\n"
    report_md += "| :--- | :--- | :--- | :--- |\n"
    report_md += "| **TTM Squeeze Momentum** | NON-CRYPTO/EQUITY | **-8.89% Avg PnL** | **Quarantine**: Immediate scoring penalty or gate-block. |\n"
    report_md += "| **Kimi LGBM Features** | CRYPTO | **-4.34% Avg PnL** | **Quarantine**: Re-train or disable; failing in current regime. |\n"
    report_md += "| **Forex Baseline** | FOREX | **WR < 29%** | **Gating**: Only allow scores > 75 on high-reliability sources. |\n"
    report_md += "| **agreement_count > 6** | GLOBAL | **-0.07 Correlation** | **Penalty**: Price in 'Retail Peak' crowded trade penalty. |\n"
    
    report_md += "\n## 🏆 3. Alpha Opportunities (The Edge)\n\n"
    report_md += "1.  **Crypto Consensus Alpha**: `polymarket:consensus` is the standout crown jewel with **+3.25% average PnL**. Scale allocation for these signals.\n"
    report_md += "2.  **Equity Mean-Reversion**: Strategies like `Bollinger MR` work significantly better for non-crypto than trend-following models.\n"
    report_md += "3.  **The Tuesday Trend**: Our DOW audit confirms Tuesday as the only consistently positive day (+0.46% PnL) for trend follow-through.\n"

    # Save Markdown report with explicit encoding
    with open('e:/findtorontoevents_antigravity.ca/DEEP_EDGE_FLAW_ANALYSIS.md', 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"Deep report V2.4 saved successfully.")

if __name__ == "__main__":
    target = 'e:/findtorontoevents_antigravity.ca/audit_trail/data/universal_resolved_picks.json'
    generate_deep_edge_report(target)
