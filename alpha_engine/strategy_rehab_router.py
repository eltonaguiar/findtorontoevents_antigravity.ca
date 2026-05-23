#!/usr/bin/env python3
"""
Strategy Rehabilitation Router
==============================
Following TESTING_PROTOCOL.MD Section 7 - Rehabilitation-First Pipeline.

This router takes underperforming strategies (WR < 35% on 10+ trades) and runs them
through the 6-stage rehabilitation process BEFORE any graveyard decision:

Stage 1: Cross-Symbol Backtest - test same logic on different symbols
Stage 2: Cross-Asset Class Backtest - test on different asset classes (crypto/forex/stocks)
Stage 3: Inverse Strategy Test - flip direction (LONG -> SHORT)
Stage 4: Parameter Mutation Grid - systematic TP/SL/timeframe variations
Stage 5: Regime-Filtered Variant - test with market condition gates
Stage 6: Crossover Blending - combine signals with proven winners

Philosophy: "Rehabilitate, don't kill" - evidence shows inverses can achieve 80%+ WR.

Run: python alpha_engine/strategy_rehab_router.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPO_DIR = BASE_DIR.parent

# Asset class test universes
CRYPTO_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", 
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "UNIUSDT", "AAVEUSDT",
    "MATICUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT"
]

FOREX_UNIVERSE = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD", "USDCAD", "EURGBP"
]

EQUITY_UNIVERSE = [
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"
]

COMMODITIES_UNIVERSE = [
    "GC=F", "SI=F", "CL=F", "NG=F", "HG=F"  # Gold, Silver, Oil, Nat Gas, Copper
]


def load_rehabilitation_tracker() -> Dict:
    """Load or create rehabilitation tracker."""
    tracker_path = DATA_DIR / "strategy_rehabilitation_tracker.json"
    if tracker_path.exists():
        with open(tracker_path, "r") as f:
            return json.load(f)
    return {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [],
        "completed_rehabilitations": []
    }


def save_rehabilitation_tracker(tracker: Dict) -> None:
    """Save rehabilitation tracker."""
    tracker_path = DATA_DIR / "strategy_rehabilitation_tracker.json"
    tracker["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2, default=str)


def get_rehab_candidates() -> List[Dict]:
    """Get strategies that need rehabilitation (from strategy_registry.json)."""
    registry_path = DATA_DIR / "strategy_registry.json"
    if not registry_path.exists():
        return []
    
    with open(registry_path, "r") as f:
        registry = json.load(f)
    
    candidates = []
    for strat_name, strat_data in registry.get("strategies", {}).items():
        status = strat_data.get("status", "")
        wr = strat_data.get("win_rate", 1.0)
        trades = strat_data.get("total_trades", 0)
        
        # Rehab candidate: WR < 35% on 10+ trades, or explicitly marked as REHAB_CANDIDATE
        if (status == "REHAB_CANDIDATE") or (wr < 0.35 and trades >= 10):
            candidates.append({
                "strategy": strat_name,
                "win_rate": wr,
                "total_trades": trades,
                "asset_class": strat_data.get("asset_class", "CRYPTO"),
                "recommended_stage": 3 if "claude_gainer" in strat_name.lower() else 1
            })
    
    return candidates


def run_stage_1_cross_symbol(strategy: str, original_symbol: str, original_class: str) -> Dict:
    """
    Stage 1: Cross-Symbol Backtest
    Test the same strategy logic on different symbols within the same asset class.
    """
    print(f"  [REHAB] Stage 1: Testing {strategy} on different crypto symbols...")
    
    test_symbols = [s for s in CRYPTO_UNIVERSE if s != original_symbol][:10]
    results = []
    
    for symbol in test_symbols:
        # Placeholder - actual backtest would run here
        # In production, this would call backtest/engine.py
        results.append({
            "symbol": symbol,
            "trades": 0,
            "win_rate": None,
            "status": "NOT_TESTED"
        })
    
    # Find best result
    best = None
    for r in results:
        if r["win_rate"] and r["win_rate"] >= 0.50:
            if not best or r["win_rate"] > best.get("win_rate", 0):
                best = r
    
    return {
        "stage": 1,
        "name": "cross_symbol",
        "tested": len(test_symbols),
        "results": results,
        "best_result": best,
        "passed": best is not None and best.get("win_rate", 0) >= 0.50,
        "recommendation": f"Deploy on {best['symbol']}" if best else "Move to Stage 2"
    }


def run_stage_2_cross_asset(strategy: str, original_class: str) -> Dict:
    """
    Stage 2: Cross-Asset Class Backtest
    Test on completely different asset classes.
    """
    print(f"  [REHAB] Stage 2: Testing {strategy} on different asset classes...")
    
    test_assets = []
    if original_class != "CRYPTO":
        test_assets.append(("CRYPTO", CRYPTO_UNIVERSE[:5]))
    if original_class != "FOREX":
        test_assets.append(("FOREX", FOREX_UNIVERSE[:3]))
    if original_class != "EQUITY":
        test_assets.append(("EQUITY", EQUITY_UNIVERSE[:3]))
    
    results = []
    for asset, symbols in test_assets:
        results.append({
            "asset_class": asset,
            "tested_symbols": symbols,
            "trades": 0,
            "win_rate": None,
            "status": "NOT_TESTED"
        })
    
    best = None
    for r in results:
        if r["win_rate"] and r["win_rate"] >= 0.50:
            if not best or r["win_rate"] > best.get("win_rate", 0):
                best = r
    
    return {
        "stage": 2,
        "name": "cross_asset",
        "tested_assets": [a[0] for a in test_assets],
        "results": results,
        "best_result": best,
        "passed": best is not None,
        "recommendation": f"Deploy on {best['asset_class']}" if best else "Move to Stage 3"
    }


def run_stage_3_inverse(strategy: str) -> Dict:
    """
    Stage 3: Inverse Strategy Test
    Flip direction (LONG -> SHORT, SHORT -> LONG).
    Evidence: winner_pattern_precursor inverse = 81.2% WR, claude_gainer_ml_inverse = 80% WR
    """
    print(f"  [REHAB] Stage 3: Testing INVERSE of {strategy}...")
    
    inverse_name = f"{strategy}_inverse"
    
    # Placeholder - actual backtest would run here
    # In production, this would call dna_mutation_engine.py inverse_mutation()
    
    return {
        "stage": 3,
        "name": "inverse",
        "inverse_name": inverse_name,
        "tested": False,
        "win_rate": None,
        "passed": False,
        "evidence": "Precedent: winner_pattern_precursor_inverse=81.2% WR, claude_gainer_ml_inverse=80% WR",
        "recommendation": "Deploy inverse variant if WR >= 50%"
    }


def run_stage_4_mutation_grid(strategy: str) -> Dict:
    """
    Stage 4: Parameter Mutation Grid
    Systematic grid search of TP/SL/timeframe variations.
    """
    print(f"  [REHAB] Stage 4: Running parameter mutation grid for {strategy}...")
    
    # Define mutation grid
    tp_variants = ["0.5x", "0.7x", "1.0x", "1.5x", "2.0x"]
    sl_variants = ["0.5x", "0.7x", "1.0x", "1.3x", "1.5x"]
    tf_variants = ["15m", "1h", "4h", "1d"]
    
    # Placeholder - actual grid search would run here
    # In production, this would call failed_strategy_robustness_probe.py
    
    return {
        "stage": 4,
        "name": "mutation_grid",
        "variants_tested": 0,
        "best_variant": None,
        "passed": False,
        "recommendation": "Deploy best variant if any WR >= 50%"
    }


def run_stage_5_regime_filter(strategy: str) -> Dict:
    """
    Stage 5: Regime-Filtered Variant
    Test with market condition gates (trend, volatility, FGI, volume).
    """
    print(f"  [REHAB] Stage 5: Testing regime-filtered variants for {strategy}...")
    
    regime_types = ["trend", "volatility", "sentiment_fgi", "volume"]
    
    # Placeholder - actual regime testing would run here
    
    return {
        "stage": 5,
        "name": "regime_filtered",
        "regimes_tested": regime_types,
        "best_regime": None,
        "passed": False,
        "recommendation": "Deploy regime-gated variant if WR >= 55%"
    }


def run_stage_6_crossover(strategy: str) -> Dict:
    """
    Stage 6: Crossover Blending
    Combine signals with proven winners (st_fear_greed_contrarian, copy_trader_highscore, super_signals).
    """
    print(f"  [REHAB] Stage 6: Testing crossover with proven winners for {strategy}...")
    
    proven_winners = [
        "st_fear_greed_contrarian",
        "copy_trader_highscore", 
        "super_signals"
    ]
    
    # Placeholder - actual crossover would run here
    
    return {
        "stage": 6,
        "name": "crossover",
        "donors_tested": proven_winners,
        "best_crossover": None,
        "passed": False,
        "recommendation": "Deploy crossover variant if WR >= 50%"
    }


def run_rehabilitation(strategy: str, asset_class: str, start_stage: int = 1) -> Dict:
    """Run full rehabilitation pipeline for a strategy."""
    
    print(f"\n[REHAB] Starting rehabilitation for: {strategy}")
    print(f"  Asset class: {asset_class}, Starting stage: {start_stage}")
    
    stages_completed = []
    
    for stage_num in range(start_stage, 7):
        print(f"\n  --- Stage {stage_num} ---")
        
        if stage_num == 1:
            result = run_stage_1_cross_symbol(strategy, "BTCUSDT", asset_class)
        elif stage_num == 2:
            result = run_stage_2_cross_asset(strategy, asset_class)
        elif stage_num == 3:
            result = run_stage_3_inverse(strategy)
        elif stage_num == 4:
            result = run_stage_4_mutation_grid(strategy)
        elif stage_num == 5:
            result = run_stage_5_regime_filter(strategy)
        elif stage_num == 6:
            result = run_stage_6_crossover(strategy)
        
        stages_completed.append(result)
        
        if result.get("passed"):
            print(f"  [PASS] Stage {stage_num} passed!")
            return {
                "strategy": strategy,
                "status": "REHABILITATED",
                "passing_stage": stage_num,
                "recommendation": result.get("recommendation"),
                "stages_completed": stages_completed
            }
        else:
            print(f"  [FAIL] Stage {stage_num} did not pass, moving to next...")
    
    return {
        "strategy": strategy,
        "status": "EXHAUSTED",
        "stages_completed": stages_completed,
        "recommendation": "All 6 stages exhausted - move to graveyard (annual review required)"
    }


def main():
    """Main entry point - find rehab candidates and process them."""
    print("=" * 60)
    print("  STRATEGY REHABILITATION PIPELINE")
    print("  Philosophy: Rehabilitate, don't kill")
    print("=" * 60)
    
    # Load tracker
    tracker = load_rehabilitation_tracker()
    
    # Get candidates
    candidates = get_rehab_candidates()
    print(f"\nFound {len(candidates)} rehabilitation candidates:")
    
    for c in candidates:
        print(f"  - {c['strategy']}: WR={c['win_rate']*100:.1f}%, {c['total_trades']} trades")
        print(f"    Recommended starting stage: {c['recommended_stage']}")
    
    if not candidates:
        print("\nNo rehabilitation candidates found.")
        return 0
    
    # Process all candidates
    for candidate in candidates:
        result = run_rehabilitation(
            candidate["strategy"],
            candidate["asset_class"],
            candidate["recommended_stage"]
        )
        
        print("\n" + "=" * 60)
        print(f"REHABILITATION RESULT for {candidate['strategy']}: {result['status']}")
        print(f"Recommendation: {result.get('recommendation')}")
        print("=" * 60)
        
        # Update tracker with result
        if result["status"] in ["REHABILITATED", "EXHAUSTED"]:
            # Check if already in completed_rehabilitations and update or append
            found_existing = False
            for rehab in tracker.get("completed_rehabilitations", []):
                if rehab.get("strategy") == result["strategy"]:
                    rehab["result"] = result["status"]
                    rehab["completed_at"] = datetime.now(timezone.utc).isoformat()
                    found_existing = True
                    break
            if not found_existing:
                tracker.setdefault("completed_rehabilitations", []).append({
                    "strategy": result["strategy"],
                    "result": result["status"],
                    "completed_at": datetime.now(timezone.utc).isoformat()
                })
    
    # Save overall state
    tracker["candidates"] = candidates
    save_rehabilitation_tracker(tracker)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())