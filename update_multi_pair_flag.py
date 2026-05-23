#!/usr/bin/env python3
"""
Add multi_pair_verified flag to all strategies in baby_strats_dashboard.json
"""
import json
from datetime import datetime
from pathlib import Path

# Load the dashboard JSON
json_path = Path("battleground/data/baby_strats_dashboard.json")
with open(json_path, 'r') as f:
    data = json.load(f)

# Add multi_pair_analysis section to schema if not present
if 'multi_pair_analysis' not in data:
    data['multi_pair_analysis'] = {
        "description": "Multi-pair validation status - strategies tested on BTC, ETH, and SOL",
        "pairs_tested": ["BTC", "ETH", "SOL"],
        "criteria": {
            "sharpe_threshold": 1.0,
            "win_rate_threshold": 0.45,
            "max_drawdown_threshold": 0.25,
            "min_trades": 12
        }
    }

# Update each strategy with multi_pair_verified flag
strategies_updated = 0
for strategy in data.get('strategies', []):
    # Add the flag - default to False since none have passed yet
    strategy['multi_pair_verified'] = False
    
    # Add multi_pair_metrics structure for future use
    if 'multi_pair_metrics' not in strategy:
        strategy['multi_pair_metrics'] = {
            "tested_pairs": [],
            "best_pair": None,
            "best_sharpe": None,
            "best_direction": None,
            "verified_at": None
        }
    
    strategies_updated += 1

# Update timestamp
data['updated_at'] = datetime.now().isoformat()

# Add summary stats
if 'multi_pair_summary' not in data:
    data['multi_pair_summary'] = {
        "verified_count": 0,
        "pending_count": strategies_updated,
        "total_count": strategies_updated
    }

# Save back
with open(json_path, 'w') as f:
    json.dump(data, f, indent=2, default=str)

print(f"[OK] Updated {strategies_updated} strategies with multi_pair_verified flag")
print(f"[OK] Added multi_pair_analysis schema definition")
print(f"[OK] Updated timestamp: {data['updated_at']}")
