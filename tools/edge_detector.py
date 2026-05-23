"""
Edge Detector — implementation of Prompt #2 from DAILY_IDEAS_PROMPTS.MD.
Calculates a robust "edge score" per asset class and strategy.
Edge score = (mean_sharpe * win_rate) / max_dd
"""

import json
import os
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_PATH = REPO_ROOT / "reports" / f"edge_detection_{datetime.now().strftime('%Y%m%d')}.md"

def load_data():
    if not DASHBOARD_DATA_PATH.exists():
        return {}
    with open(DASHBOARD_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_edge_scores(data):
    # Flatten closed picks across all systems
    closed_picks = []
    
    # In dashboard_data.json, picks are often grouped by system
    systems = data.get("systems", [])
    for sys in systems:
        sys_name = sys.get("name", "unknown")
        # Check for closed list
        if "closed" in sys:
            for p in sys["closed"]:
                p["source_system"] = sys_name
                closed_picks.append(p)
    
    if not closed_picks and "picks" in data:
        closed_picks = data["picks"].get("recent_closed", [])

    if not closed_picks:
        print("No closed picks found in dashboard_data.json")
        return pd.DataFrame()

    df = pd.DataFrame(closed_picks)
    
    # Ensure necessary columns exist
    required_cols = ['source_system', 'asset_class', 'pnl_pct']
    for col in required_cols:
        if col not in df.columns:
            if col == 'asset_class' and 'category' in df.columns:
                df['asset_class'] = df['category']
            else:
                print(f"Missing required column: {col}")
                return pd.DataFrame()

    # Pre-process
    df['pnl_pct'] = pd.to_numeric(df['pnl_pct'], errors='coerce').fillna(0)
    df['asset_class'] = df['asset_class'].str.upper()
    
    # Group by asset class and strategy
    groups = df.groupby(['asset_class', 'source_system'])
    
    results = []
    for (ac, strat), group in groups:
        n = len(group)
        if n < 5: continue # Small sample size filter
        
        wr = (group['pnl_pct'] > 0).mean() * 100
        mean_pnl = group['pnl_pct'].mean()
        std_pnl = group['pnl_pct'].std()
        
        # Sharpe Ratio (approximate using trade returns)
        sharpe = (mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0
        
        # Max Drawdown (per strategy in this sample)
        cum_pnl = group['pnl_pct'].cumsum()
        running_max = cum_pnl.cummax()
        drawdown = running_max - cum_pnl
        max_dd = drawdown.max() if not drawdown.empty else 0.01 # Avoid div by zero
        if max_dd == 0: max_dd = 0.01
        
        edge_score = (sharpe * wr) / max_dd
        
        # 95% CI for Mean PnL
        ci_half = 1.96 * (std_pnl / np.sqrt(n)) if n > 0 else 0
        
        results.append({
            "asset_class": ac,
            "strategy": strat,
            "n": n,
            "win_rate": round(wr, 1),
            "mean_pnl": round(mean_pnl, 4),
            "sharpe": round(sharpe, 2),
            "max_dd": round(max_dd, 4),
            "edge_score": round(edge_score, 2),
            "ci_low": round(mean_pnl - ci_half, 4),
            "ci_high": round(mean_pnl + ci_half, 4)
        })
    
    return pd.DataFrame(results).sort_values("edge_score", ascending=False)

def generate_report(df):
    if df.empty:
        return "No data to generate report."
    
    report = f"# Edge Detection Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "## Statistical Edge per Asset Class and Strategy\n"
    report += "Edge Score Formula: `(Sharpe * WinRate) / MaxDD` (higher is better)\n\n"
    
    for ac in df['asset_class'].unique():
        report += f"### {ac}\n"
        ac_df = df[df['asset_class'] == ac]
        report += ac_df.to_markdown(index=False)
        report += "\n\n"
    
    return report

def main():
    data = load_data()
    df = calculate_edge_scores(data)
    report = generate_report(df)
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"Report written to {OUT_PATH}")
    print("\nTop 10 Edge Strategies:")
    print(df.head(10)[['asset_class', 'strategy', 'edge_score', 'win_rate', 'n']])

if __name__ == "__main__":
    main()
