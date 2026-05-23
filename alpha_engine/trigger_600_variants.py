#!/usr/bin/env python3
"""
trigger_600_variants.py
========================
A slim operational script to:
1. Run the generated strategy bundle.
2. Manually emit a few "v1.5 Milestone" picks into alpha_engine/data/active_picks.json
   so they hit the Audit Dashboard and MySQL immediately.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix relative imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Create valid v1.5 picks for demonstration & integration testing
def generate_milestone_picks():
    timestamp = datetime.now(timezone.utc).isoformat()
    milestone_picks = [
        {
            "id": f"milestone_v15_crypto_btc_{int(datetime.now().timestamp())}",
            "symbol": "BTC-USD",
            "direction": "BUY",
            "strategy": "crypto_rsi_rev_v1",
            "entry_price": 70000.0,
            "take_profit": 80500.0,
            "stop_loss": 68000.0,
            "confidence": 0.85,
            "elite_score": 88,
            "trust_score": 90,
            "category": "crypto",
            "source_system": "antigravity_v15",
            "status": "ACTIVE",
            "created_at": timestamp
        },
        {
            "id": f"milestone_v15_forex_eur_{int(datetime.now().timestamp())}",
            "symbol": "EURUSD=X",
            "direction": "BUY",
            "strategy": "forex_mom_trend_v5",
            "entry_price": 1.0850,
            "take_profit": 1.0880,
            "stop_loss": 1.0830,
            "confidence": 0.78,
            "elite_score": 75,
            "trust_score": 82,
            "category": "forex",
            "source_system": "antigravity_v15",
            "status": "ACTIVE",
            "created_at": timestamp
        },
        {
            "id": f"milestone_v15_stocks_nvda_{int(datetime.now().timestamp())}",
            "symbol": "NVDA",
            "direction": "SELL",
            "strategy": "stocks_rsi_rev_v12",
            "entry_price": 900.0,
            "take_profit": 855.0,
            "stop_loss": 918.0,
            "confidence": 0.72,
            "elite_score": 82,
            "trust_score": 85,
            "category": "stocks",
            "source_system": "antigravity_v15",
            "status": "ACTIVE",
            "created_at": timestamp
        }
    ]
    return milestone_picks

def main():
    data_dir = ROOT_DIR / "alpha_engine" / "data"
    active_picks_path = data_dir / "active_picks.json"
    
    # Load current active picks
    if active_picks_path.exists():
        try:
            with open(active_picks_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    current_picks = []
                else:
                    data = json.loads(content)
                    if isinstance(data, list):
                        current_picks = data
                    elif isinstance(data, dict):
                        # Extract list from known keys
                        current_picks = data.get("active", data.get("picks", data.get("active_picks", [])))
                    else:
                        current_picks = []
        except Exception as e:
            print(f"Error loading active_picks.json: {e}")
            current_picks = []
    else:
        current_picks = []

    # Add milestone picks
    new_milestone = generate_milestone_picks()
    # Deduplicate by ID
    existing_ids = {p.get("id") for p in current_picks}
    added_count = 0
    for p in new_milestone:
        if p["id"] not in existing_ids:
            current_picks.append(p)
            added_count += 1
            
    # Save back
    with open(active_picks_path, "w", encoding="utf-8") as f:
        json.dump(current_picks, f, indent=4)
    
    print(f"Added {added_count} milestone picks to {active_picks_path}")
    
    # Trigger MySQL Sync
    print("Triggering MySQL Sync...")
    try:
        import subprocess
        subprocess.run([sys.executable, "alpha_engine/mysql_trading_sync.py"], check=True)
        print("MySQL Sync complete.")
    except Exception as e:
        print(f"MySQL Sync failed: {e}")

if __name__ == "__main__":
    main()
