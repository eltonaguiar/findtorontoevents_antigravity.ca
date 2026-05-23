import json
import os
from pathlib import Path

def analyze_orphans():
    data_dir = Path("alpha_engine/data")
    orphans = []
    
    # Standard sources we already know
    known = {"active_picks.json", "closed_picks.json", "active_picks_fast.json", "closed_picks_fast.json"}
    
    for f in data_dir.glob("*.json"):
        if f.name in known: continue
        
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                
            # Look for lists of picks/trades
            picks = []
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                for k in ["picks", "trades", "winners", "results", "historical_picks"]:
                    if k in data and isinstance(data[k], list):
                        picks = data[k]
                        break
            
            if not picks or not isinstance(picks[0], dict):
                continue
                
            # Performance heuristics
            wins = sum(1 for p in picks if float(p.get("pnl_pct", 0) or 0) > 0)
            losses = sum(1 for p in picks if float(p.get("pnl_pct", 0) or 0) < 0)
            total = len(picks)
            
            if total < 5: continue
            
            win_rate = (wins / total) * 100 if total > 0 else 0
            
            # Identify high performers
            if win_rate > 60 or (total > 50 and win_rate > 52):
                orphans.append({
                    "file": str(f),
                    "total": total,
                    "win_rate": round(win_rate, 2),
                    "first_symbol": picks[0].get("symbol"),
                    "sample_strategy": picks[0].get("strategy") or picks[0].get("system")
                })
        except:
            continue
            
    # Sort by performance
    orphans.sort(key=lambda x: x["win_rate"], reverse=True)
    
    print(f"--- Orphans Found in {data_dir} ---")
    for o in orphans:
        print(f"File: {o['file']}")
        print(f"  Trades: {o['total']}, WR: {o['win_rate']}%")
        print(f"  Example: {o['first_symbol']} ({o['sample_strategy']})")
        print("-" * 20)

if __name__ == "__main__":
    analyze_orphans()
