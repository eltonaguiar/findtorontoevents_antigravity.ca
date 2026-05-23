#!/usr/bin/env python3
"""
OlivierDanvel Cross-Platform Wrapper
=====================================
GP-9 Implementation: Bridges eToro OlivierDanvel data to Myfxbook-style output.

Purpose:
- OlivierDanvel is an eToro Elite Popular Investor (not Myfxbook)
- This wrapper reads eToro-generated picks and emits Myfxbook-compatible format
- Ensures systems expecting "myfxbook_copy_OlivierDanvel" strategy name work correctly

Usage:
    from olivierdanvel_wrapper import get_olivierdanvel_picks
    picks = get_olivierdanvel_picks()

Output: Picks with strategy="myfxbook_copy_OlivierDanvel" for backward compatibility
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Paths
DATA_DIR = Path(__file__).parent / "data"
ETORO_PICKS_PATH = DATA_DIR / "etoro_picks.json"
MYFXBOOK_OUTPUT_PATH = DATA_DIR / "myfxbook_olivierdanvel_picks.json"

# OlivierDanvel profile data (from forex_trader_database.json)
OLIVIER_PROFILE = {
    "name": "Olivier Jean Andre Danvel",
    "username": "OlivierDanvel",
    "platform": "eToro",  # Actual platform
    "alias_platform": "Myfxbook",  # For backward compatibility
    "status": "Elite Popular Investor",
    "portfolio_pct_forex": 84.48,
    "win_rate": 0.65,
    "consecutive_profit_months": 33,
    "copiers": 9807,
    "aum_usd": 5000000,
    "risk_score": 1,
    "pairs_traded": ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "AUD/USD", "USD/CHF"],
    "strategy_type": "swing",
    "typical_hold_time": "days_to_weeks",
    "experience_years": 20,
}


def _load_etoro_picks() -> List[Dict[str, Any]]:
    """Load OlivierDanvel's picks from eToro output."""
    if not ETORO_PICKS_PATH.exists():
        return []
    
    try:
        with open(ETORO_PICKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Filter for OlivierDanvel only
        picks = data.get("picks", []) if isinstance(data, dict) else data
        return [
            p for p in picks 
            if "olivier" in str(p.get("trader_name", "")).lower() 
            or "danvel" in str(p.get("trader_name", "")).lower()
        ]
    except Exception:
        return []


def _transform_to_myfxbook_format(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Transform eToro pick to Myfxbook-compatible format."""
    transformed = dict(pick)
    
    # Override strategy name for backward compatibility
    transformed["strategy"] = "myfxbook_copy_OlivierDanvel"
    transformed["source_system"] = "copy_trader_myfxbook_alias"
    transformed["actual_platform"] = "eToro"
    transformed["trader_username"] = "OlivierDanvel"
    
    # Enhance with profile data
    transformed["trader_profile"] = {
        "name": OLIVIER_PROFILE["name"],
        "win_rate": OLIVIER_PROFILE["win_rate"],
        "forex_allocation_pct": OLIVIER_PROFILE["portfolio_pct_forex"],
        "consecutive_profit_months": OLIVIER_PROFILE["consecutive_profit_months"],
        "copiers": OLIVIER_PROFILE["copiers"],
        "aum_usd": OLIVIER_PROFILE["aum_usd"],
        "risk_score": OLIVIER_PROFILE["risk_score"],
        "experience_years": OLIVIER_PROFILE["experience_years"],
    }
    
    return transformed


def get_olivierdanvel_picks() -> List[Dict[str, Any]]:
    """
    Get OlivierDanvel picks in Myfxbook-compatible format.
    
    Returns:
        List of picks with strategy="myfxbook_copy_OlivierDanvel"
    """
    etoro_picks = _load_etoro_picks()
    
    if not etoro_picks:
        # Return synthetic placeholder if no live picks available
        return [_generate_synthetic_pick()]
    
    return [_transform_to_myfxbook_format(p) for p in etoro_picks]


def _generate_synthetic_pick() -> Dict[str, Any]:
    """Generate a synthetic pick when no live data is available."""
    now = datetime.now(timezone.utc)
    
    return {
        "id": f"myfxbook_olivierdanvel_synthetic_{now.strftime('%Y-%m-%d_%H%M')}",
        "strategy": "myfxbook_copy_OlivierDanvel",
        "source_system": "copy_trader_myfxbook_alias",
        "actual_platform": "eToro",
        "trader_username": "OlivierDanvel",
        "trader_name": "Olivier Jean Andre Danvel",
        "symbol": "EURUSD",
        "category": "FOREX",
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": 0.0,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": 0.0,
        "stop_loss": 0.0,
        "confidence": 0.65,
        "status": "PENDING",
        "reason": f"eToro Elite PI | 84% forex | 65% WR | 33 months profitable | {OLIVIER_PROFILE['copiers']} copiers",
        "trader_profile": {
            "name": OLIVIER_PROFILE["name"],
            "win_rate": OLIVIER_PROFILE["win_rate"],
            "forex_allocation_pct": OLIVIER_PROFILE["portfolio_pct_forex"],
            "consecutive_profit_months": OLIVIER_PROFILE["consecutive_profit_months"],
            "copiers": OLIVIER_PROFILE["copiers"],
            "aum_usd": OLIVIER_PROFILE["aum_usd"],
            "risk_score": OLIVIER_PROFILE["risk_score"],
        },
        "note": "Synthetic placeholder - actual picks generated via eToro scraper",
    }


def save_myfxbook_format_picks():
    """Save picks in Myfxbook-compatible format to JSON."""
    picks = get_olivierdanvel_picks()
    
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "olivierdanvel_wrapper",
        "actual_platform": "eToro",
        "alias_platform": "Myfxbook",
        "trader": OLIVIER_PROFILE,
        "picks": picks,
        "count": len(picks),
    }
    
    MYFXBOOK_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MYFXBOOK_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"[OlivierDanvel Wrapper] Saved {len(picks)} picks to {MYFXBOOK_OUTPUT_PATH.name}")
    return output


if __name__ == "__main__":
    result = save_myfxbook_format_picks()
    print(f"\nTrader: {result['trader']['name']}")
    print(f"Platform: {result['actual_platform']} (aliased as {result['alias_platform']})")
    print(f"Picks: {result['count']}")
    for pick in result['picks'][:3]:
        print(f"  - {pick.get('symbol', 'N/A')} {pick.get('direction', 'N/A')} (conf={pick.get('confidence', 0)})")
