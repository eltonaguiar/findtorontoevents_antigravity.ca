
import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("e:/findtorontoevents_antigravity.ca/alpha_engine/data/alpha.db")

def audit_performance():
    if not DB_PATH.exists():
        return {"error": "Database not found"}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Get all strategy stats
    stats_df = pd.read_sql_query("SELECT * FROM strategy_stats", conn)
    
    # Get all closed picks
    picks_df = pd.read_sql_query("SELECT * FROM picks WHERE status IN ('WON', 'LOST', 'BREAKEVEN', 'EXPIRED')", conn)
    
    # Mapping symbols to categories if not present
    # (The picks table already has a 'category' column)
    
    asset_results = []
    categories = picks_df['category'].unique()
    
    for cat in categories:
        if not cat: continue
        
        cat_picks = picks_df[picks_df['category'] == cat]
        
        # Top Winners
        winners = cat_picks.groupby('symbol').agg({
            'pnl_dollar': 'sum',
            'id': 'count',
            'pnl_pct': 'mean',
            'status': lambda x: (x == 'WON').sum() / len(x) if len(x) > 0 else 0
        }).rename(columns={'id': 'trades', 'status': 'winrate', 'pnl_dollar': 'total_pnl'}).sort_values('total_pnl', ascending=False)
        
        # Top Losers
        losers = winners.sort_values('total_pnl', ascending=True)
        
        # Aggregate stats for the category
        summary = {
            "class_name": cat,
            "top_winners": winners.head(5).reset_index().to_dict(orient='records'),
            "top_losers": losers.head(5).reset_index().to_dict(orient='records'),
            "total_pnl": float(cat_picks['pnl_dollar'].sum()),
            "overall_winrate": float((cat_picks['status'] == 'WON').sum() / len(cat_picks)) if len(cat_picks) > 0 else 0
        }
        asset_results.append(summary)
        
    conn.close()
    return asset_results

if __name__ == "__main__":
    results = audit_performance()
    print(json.dumps(results, indent=2))
