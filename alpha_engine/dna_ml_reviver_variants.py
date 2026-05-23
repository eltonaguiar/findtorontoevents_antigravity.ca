import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Paths
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
sys.path.append(str(_THIS_DIR))

# Import the core reviver to use its functions
try:
    import ml_strategy_reviver as rev
except ImportError:
    import imp
    rev = imp.load_source('ml_strategy_reviver', str(_THIS_DIR / 'ml_strategy_reviver.py'))

def generate_dna_variants():
    print("--- [DNA] ML Reviver Variant Generator + Consensus ---")
    proven = rev.PROVEN_STRATEGIES
    
    all_dna_picks = []
    symbol_consensus = {} # symbol -> list of picks

    # Step 1: Collect variants for all proven strategies
    for name, config in proven.items():
        symbol = config['symbol']
        timeframe = config['timeframe']
        
        # Fetch current data once
        price = rev.fetch_price(symbol)
        if not price: continue
        
        klines = rev.fetch_klines(symbol, timeframe, limit=30)
        if len(klines) < 14: continue
        
        closes = [k['close'] for k in klines]
        rsi = rev.compute_rsi(closes, 14)

        # DNA 1: AGGRESSIVE (Relaxed RSI 15-85)
        if 15 <= rsi <= 85:
            p = rev._generate_standalone_pick(name + "_dna_agg", config)
            if p:
                p['strategy'] = name + "_dna_agg"
                p['reasoning'].append("DNA Mutation: Aggressive (Relaxed RSI 15-85)")
                all_dna_picks.append(p)
                symbol_consensus.setdefault(symbol, []).append(p)

        # DNA 2: REVERSAL (Oversold < 30)
        if rsi < 30:
            p = rev._generate_standalone_pick(name + "_dna_rev", config)
            if p:
                p['strategy'] = name + "_dna_rev"
                p['direction'] = "BUY"
                p['reasoning'].append(f"DNA Mutation: Reversal (Oversold RSI {rsi:.1f})")
                all_dna_picks.append(p)
                symbol_consensus.setdefault(symbol, []).append(p)

    # Step 2: Apply Consensus Boost
    print("\n--- Applying Consensus Check ---")
    for symbol, picks in symbol_consensus.items():
        if len(picks) >= 2:
            print(f"  [CONSENSUS] Found {len(picks)} variant agreement for {symbol}")
            boost = 0.05 * (len(picks) - 1)
            for p in picks:
                old_conf = p['confidence']
                p['confidence'] = min(0.99, old_conf + boost)
                p['reasoning'].append(f"CONSENSUS BOOST: {len(picks)} variants agree (Conf {old_conf} -> {p['confidence']})")

    # Save to dedicated file
    output_path = _DATA_DIR / "dna_reviver_picks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_dna_picks, f, indent=2, default=str)
    
    print(f"\n--- [DNA] Finished. Saved to {output_path}")

if __name__ == "__main__":
    generate_dna_variants()
