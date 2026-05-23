#!/usr/bin/env python3
"""
Sync Forward Test Picks
========================
Reads forward_test_state.json and syncs open positions to live_forward_test_picks.json
for dashboard display. This fixes the broken Layer 6 pipeline.

Run: python alpha_engine/sync_forward_test_picks.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

STATE_FILE = DATA_DIR / "forward_test_state.json"
OUTPUT_FILE = DATA_DIR / "live_forward_test_picks.json"


def load_state() -> dict:
    """Load forward test state."""
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_picks():
    """Sync open positions from all portfolios to live_forward_test_picks.json."""
    state = load_state()
    
    all_picks = []
    strategies = set()
    symbols = set()
    
    for portfolio_name, portfolio in state.items():
        for pos in portfolio.get("positions", []):
            pick = {
                "symbol": pos.get("symbol", ""),
                "direction": pos.get("direction", "LONG"),
                "entry_price": pos.get("entry_price", 0),
                "take_profit": pos.get("take_profit", 0),
                "stop_loss": pos.get("stop_loss", 0),
                "strategy": pos.get("strategy", portfolio_name),
                "entry_date": pos.get("entry_time_utc", ""),
                "asset_class": pos.get("asset_class", "CRYPTO"),
                "entry_score": pos.get("entry_score", 50),
                "source": f"forward_test_portfolio::{portfolio_name}",
                "status": "OPEN",
            }
            all_picks.append(pick)
            strategies.add(pos.get("strategy", portfolio_name))
            symbols.add(pos.get("symbol", ""))
    
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": "crypto",
        "market_status": "OPEN",
        "total_picks": len(all_picks),
        "strategies_scanned": sorted(list(strategies)),
        "symbols_scanned": sorted(list(symbols)),
        "picks": all_picks,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"[sync] Updated live_forward_test_picks.json with {len(all_picks)} picks from forward test portfolios")
    return output


if __name__ == "__main__":
    result = sync_picks()
    print(f"Total picks: {result['total_picks']}")
    print(f"Strategies: {len(result['strategies_scanned'])}")
    print(f"Symbols: {len(result['symbols_scanned'])}")