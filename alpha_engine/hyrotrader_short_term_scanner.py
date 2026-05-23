"""
Hyrotrader Short-Term Entry Scanner
====================================
Actionable entry detection for 4-24h horizon trades.
Wraps hyrotrader_enhanced_scoring.py indicators into a scanner.

Usage:
    python alpha_engine/hyrotrader_short_term_scanner.py
    
Or import:
    from alpha_engine.hyrotrader_short_term_scanner import scan_for_entries
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
import pandas as pd
import numpy as np

# Import existing indicators from hyrotrader_enhanced_scoring
from alpha_engine.hyrotrader_enhanced_scoring import (
    fetch_klines,
    compute_all_indicators,
    compute_short_term_entry_profile,
    run_backtest,
    BINANCE_MIRRORS
)

# Project paths
_REPO = Path(__file__).resolve().parents[1]
_PICKS_PATH = _REPO / "audit_dashboard" / "data" / "hyrotrader_picks.json"
_OUTPUT_PATH = _REPO / "audit_dashboard" / "data" / "hyrotrader_short_term_entries.json"

# Scanner parameters — tuned 2026-04-14 based on compound filter analysis.
# The filter trust>=3 AND score>=50 AND LONG lifts crypto PF from 1.57 to 3.09.
# These thresholds are set to produce picks that would pass that gate.
MIN_ENTRY_QUALITY = 65       # lowered from 68 — was too restrictive, filtering proven setups
MIN_BACKTEST_WR = 50         # lowered from 55 — PF matters more than WR for prop challenges
MIN_CONFIDENCE = 55          # lowered from 60 — canonical data shows conf>=0.5 is sufficient
LOOKBACK_BARS = 100


def load_hyrotrader_picks() -> List[Dict]:
    """Load picks from hyrotrader_picks.json"""
    try:
        with open(_PICKS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("picks", [])
    except FileNotFoundError:
        print(f"Warning: {PICKS_PATH} not found, using sample data")
        return []


def generate_crypto_universe() -> List[str]:
    """Generate universe of crypto symbols to scan.

    Tier 1 (PF > 2.0 on canonical data, n >= 20): prioritized for scanning.
    Tier 2 (PF 1.3-2.0, n >= 20): secondary candidates.
    Tier 3 (broad coverage): lower priority, scanned if time permits.

    Source: universal_resolved_picks.json cross-checked 2026-04-14.
    Removed: MATICUSDT (delisted/migrated to POL, 738 ghost picks in closed_picks.json).
    """
    # Tier 1: proven edge (PF > 2.0 in canonical, all available on Bybit USDT perps)
    tier1 = [
        "BTCUSDT",   # PF=2.44, WR=55.1%, n=256, +237%
        "ETHUSDT",   # PF=2.37, WR=55.6%, n=241, +249%
        "XRPUSDT",   # PF=2.24, WR=62.5%, n=112, +81%
        "SEIUSDT",   # PF=2.40, WR=60.2%, n=83,  +78%
        "FETUSDT",   # PF=2.44, WR=53.3%, n=30,  +38%
        "ETCUSDT",   # PF=4.39, WR=68.5%, n=54,  +77%
    ]
    # Tier 2: modest edge (PF 1.3-2.0, sufficient sample)
    tier2 = [
        "AVAXUSDT",  # PF=1.80, WR=51.3%, n=119, +74%
        "APTUSDT",   # PF=1.87, WR=55.6%, n=144, +100%
        "SOLUSDT",   # PF=1.30, WR=43.6%, n=250, +76%
        "LINKUSDT",  # PF=1.62, WR=48.9%, n=88,  +43%
        "JUPUSDT",   # PF=1.69, WR=48.0%, n=50,  +27%
        "BNBUSDT",   # PF=1.43, WR=46.8%, n=77,  +25%
        "DOTUSDT",   # PF=1.22 (cross-ref), broad coverage
    ]
    # Tier 3: liquidity coverage (lower/unproven edge)
    tier3 = [
        "ADAUSDT", "DOGEUSDT", "NEARUSDT", "ARBUSDT",
        "OPUSDT", "FILUSDT", "WIFUSDT", "ATOMUSDT",
    ]
    return tier1 + tier2 + tier3


def scan_symbol(symbol: str, direction: str = "LONG") -> Optional[Dict]:
    """
    Scan a single symbol for short-term entry opportunity.
    
    Returns dict with entry quality score and reasons if actionable,
    or None if not actionable.
    """
    # Fetch 4h data for indicators, 1h for backtest
    klines_4h = fetch_klines(symbol, "4h", LOOKBACK_BARS)
    klines_1h = fetch_klines(symbol, "1h", 200)
    
    if not klines_4h:
        return None
    
    # Compute indicators
    indicators = compute_all_indicators(klines_4h)
    
    # Build mock pick for scoring
    pick = {
        "symbol": symbol,
        "direction": direction,
        "confidence_pct": 70,  # Base confidence
        "source": "hyrotrader_short_term_scanner"
    }
    
    # Run backtest
    current_price = indicators.get("current_price", 0) if indicators else 0
    backtest = run_backtest(symbol, direction, current_price,
                            stop_loss_pct=0.02, take_profit_pct=0.04,
                            klines=klines_1h)
    
    # Compute entry profile
    entry_profile = compute_short_term_entry_profile(pick, indicators, backtest)
    
    return {
        "symbol": symbol,
        "direction": direction,
        "entry_quality": entry_profile["entry_quality"],
        "actionable": entry_profile["actionable"],
        "horizon": entry_profile["horizon"],
        "reasons": entry_profile["reasons"],
        "indicators": {
            "rsi": indicators.get("rsi"),
            "trend": indicators.get("trend"),
            "macd_direction": (indicators.get("macd") or {}).get("direction"),
            "atr_pct": indicators.get("atr_pct"),
            "volume_ratio": (indicators.get("volume") or {}).get("ratio"),
        },
        "backtest": {
            "status": backtest.get("status"),
            "win_rate": backtest.get("win_rate"),
            "avg_pnl": backtest.get("avg_pnl"),
            "total_trades": backtest.get("total_trades"),
        }
    }


def scan_universe(min_quality: int = MIN_ENTRY_QUALITY, 
                  min_wr: int = MIN_BACKTEST_WR) -> List[Dict]:
    """
    Scan entire crypto universe for actionable entries.
    
    Returns list of actionable picks sorted by entry_quality.
    """
    universe = generate_crypto_universe()
    results = []
    
    print(f"Scanning {len(universe)} symbols for short-term entries...")
    print(f"Filters: min_entry_quality={min_quality}, min_backtest_wr={min_wr}")
    print("-" * 60)
    
    for symbol in universe:
        # Check both directions
        for direction in ["LONG", "SHORT"]:
            result = scan_symbol(symbol, direction)
            
            if result and result["actionable"]:
                # Double-check backtest WR meets minimum
                bt_wr = result["backtest"].get("win_rate", 0) or 0
                if bt_wr >= min_wr:
                    results.append(result)
                    print(f"  ACTIONABLE: {symbol} {direction} - "
                          f"Quality:{result['entry_quality']} WR:{bt_wr}%")
            
            time.sleep(0.3)  # Rate limit
    
    # Sort by entry quality
    results.sort(key=lambda x: x["entry_quality"], reverse=True)
    
    return results


def generate_entry_signals(results: List[Dict]) -> Dict:
    """
    Convert scan results into entry signals for trading.
    """
    signals = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_actionable": len(results),
        "longs": [],
        "shorts": [],
        "by_quality_tier": {
            "elite": [],      # 85+
            "high": [],       # 75-84
            "moderate": [],   # 68-74
        }
    }
    
    for r in results:
        signal = {
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_quality": r["entry_quality"],
            "horizon": r["horizon"],
            "reasons": r["reasons"],
            "indicators": r["indicators"],
            "backtest": r["backtest"],
            "entry_price_hint": r["indicators"].get("current_price") if r["indicators"] else None,
        }
        
        if r["direction"] == "LONG":
            signals["longs"].append(signal)
        else:
            signals["shorts"].append(signal)
        
        # Categorize by tier
        quality = r["entry_quality"]
        if quality >= 85:
            signals["by_quality_tier"]["elite"].append(signal)
        elif quality >= 75:
            signals["by_quality_tier"]["high"].append(signal)
        else:
            signals["by_quality_tier"]["moderate"].append(signal)
    
    return signals


def main():
    """Main entry point for scanner."""
    print("=" * 60)
    print("HYROTRADER SHORT-TERM ENTRY SCANNER")
    print("=" * 60)
    print(f"Target horizon: 4-24h")
    print(f"Min entry quality: {MIN_ENTRY_QUALITY}")
    print(f"Min backtest WR: {MIN_BACKTEST_WR}%")
    print()
    
    # Run scan
    start_time = datetime.now(timezone.utc)
    results = scan_universe()
    end_time = datetime.now(timezone.utc)
    
    # Generate signals
    signals = generate_entry_signals(results)
    signals["scan_duration_seconds"] = (end_time - start_time).total_seconds()
    
    # Print summary
    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Total actionable entries: {signals['total_actionable']}")
    print(f"  LONGs: {len(signals['longs'])}")
    print(f"  SHORTs: {len(signals['shorts'])}")
    print()
    print("By quality tier:")
    print(f"  Elite (85+): {len(signals['by_quality_tier']['elite'])}")
    print(f"  High (75-84): {len(signals['by_quality_tier']['high'])}")
    print(f"  Moderate (68-74): {len(signals['by_quality_tier']['moderate'])}")
    print()
    print(f"Scan duration: {signals['scan_duration_seconds']:.1f}s")
    
    # Save to file
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2)
    
    print(f"\nOutput saved to: {_OUTPUT_PATH}")
    
    # Print top 5
    if results:
        print()
        print("TOP 5 ACTIONABLE ENTRIES:")
        for i, r in enumerate(results[:5], 1):
            print(f"  {i}. {r['symbol']} {r['direction']} - "
                  f"Quality:{r['entry_quality']} WR:{r['backtest'].get('win_rate', 'N/A')}%")
    
    return signals


if __name__ == "__main__":
    main()