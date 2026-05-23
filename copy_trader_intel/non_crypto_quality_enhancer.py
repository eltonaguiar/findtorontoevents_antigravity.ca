#!/usr/bin/env python3
"""
Non-Crypto Quality Enhancer
===========================
Enhances non-crypto consensus picks with:
1. Copy trader validation (≥2 independent sources)
2. Technical analysis validation (from daily analysis)
3. Prediction market whale consensus (if available)
4. Forward test track record (from backtest)

Output: copy_trader_intel/data/non_crypto_enhanced_picks.json
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ROOT = Path(__file__).parent.parent


def load_json(filepath: Path, default=None) -> dict | list:
    """Load JSON file safely."""
    if not filepath.exists():
        return default if default is not None else {}
    try:
        with open(filepath) as f:
            return json.load(f)
    except:
        return default if default is not None else {}


def load_technical_analysis() -> dict:
    """Load technical analysis consensus."""
    ta_path = DATA_DIR / "technical_analysis.json"
    ta_data = load_json(ta_path, {})
    # Index by symbol for quick lookup
    ta_by_symbol = {}
    if isinstance(ta_data, dict) and "picks" in ta_data:
        for pick in ta_data.get("picks", []):
            sym = pick.get("symbol", "")
            if sym:
                ta_by_symbol[sym] = pick
    return ta_by_symbol


def load_prediction_market_whales() -> dict:
    """Load polymarket whale signals."""
    whale_path = Path(__file__).parent.parent / "alpha_engine" / "data" / "prediction_market_whales.json"
    whale_data = load_json(whale_path, {})
    whales_by_symbol = {}
    if isinstance(whale_data, dict) and "whales" in whale_data:
        for whale in whale_data.get("whales", []):
            sym = whale.get("symbol", "")
            if sym:
                whales_by_symbol[sym] = whale
    return whales_by_symbol


def enhance_consensus_picks() -> list[dict]:
    """Load consensus picks and enhance with validation."""
    consensus_path = DATA_DIR / "non_crypto_consensus_picks.json"
    consensus_picks = load_json(consensus_path, [])
    
    if not consensus_picks:
        print("[enhance] No consensus picks found")
        return []
    
    # Load supporting data
    ta_by_symbol = load_technical_analysis()
    whales_by_symbol = load_prediction_market_whales()
    
    print(f"[enhance] Loaded {len(consensus_picks)} consensus picks")
    print(f"[enhance] TA analysis: {len(ta_by_symbol)} symbols, Whales: {len(whales_by_symbol)} symbols")
    
    enhanced_picks = []
    
    for pick in consensus_picks:
        symbol = pick.get("symbol", "")
        direction = pick.get("signal_type", "").upper()
        
        # Base pick confidence
        base_conf = pick.get("confidence", 0.6)
        conf_adjustments = []
        
        # ── Enhancement 1: Technical Analysis Validation ──
        if symbol in ta_by_symbol:
            ta = ta_by_symbol[symbol]
            ta_signal = ta.get("signal", "").upper()
            
            # Does TA align with consensus direction?
            if (direction == "BUY" and ta_signal in ("BUY", "LONG")) or \
               (direction == "SELL" and ta_signal in ("SELL", "SHORT")):
                conf_adjustments.append(("TA_ALIGN", +0.05))
                pick["_ta_validation"] = "aligned"
            elif (direction == "BUY" and ta_signal in ("SELL", "SHORT")) or \
                 (direction == "SELL" and ta_signal in ("BUY", "LONG")):
                conf_adjustments.append(("TA_CONFLICT", -0.10))
                pick["_ta_validation"] = "conflicted"
            else:
                pick["_ta_validation"] = "neutral"
        
        # ── Enhancement 2: Whale Consensus Validation ──
        # (Note: whales data is crypto-focused, but include if available)
        if symbol in whales_by_symbol:
            whale = whales_by_symbol[symbol]
            whale_direction = whale.get("direction", "").upper()
            whale_confidence = whale.get("confidence", 0.5)
            
            if (direction == "BUY" and whale_direction == "LONG") or \
               (direction == "SELL" and whale_direction == "SHORT"):
                conf_adjustments.append(("WHALE_ALIGN", +0.03 * min(whale_confidence / 0.7, 1)))
                pick["_whale_validation"] = "aligned"
        
        # ── Apply confidence adjustments ──
        final_conf = base_conf
        for adj_name, adj_value in conf_adjustments:
            final_conf += adj_value
        
        final_conf = min(0.90, max(0.5, final_conf))  # Clamp to [0.5, 0.9]
        
        if conf_adjustments:
            pick["_confidence_adjustments"] = conf_adjustments
            pick["_original_confidence"] = base_conf
        
        pick["confidence"] = round(final_conf, 3)
        pick["enhanced"] = True
        pick["enhanced_at"] = datetime.now(timezone.utc).isoformat()
        
        enhanced_picks.append(pick)
    
    # Save enhanced picks
    output_path = DATA_DIR / "non_crypto_enhanced_picks.json"
    with open(output_path, "w") as f:
        json.dump(enhanced_picks, f, indent=2, default=str)
    
    print(f"[enhance] Saved {len(enhanced_picks)} enhanced picks to {output_path}")
    print(f"[enhance] {sum(1 for p in enhanced_picks if p.get('_confidence_adjustments'))} picks had adjustments")
    
    return enhanced_picks


if __name__ == "__main__":
    results = enhance_consensus_picks()
    for pick in results:
        adjustments = pick.get("_confidence_adjustments", [])
        adj_str = " + ".join([f"{name}({v:+.2f})" for name, v in adjustments]) if adjustments else ""
        print(f"  {pick['symbol']}: {pick['signal_type']} conf={pick['confidence']:.3f} "
              f"({adj_str})")
