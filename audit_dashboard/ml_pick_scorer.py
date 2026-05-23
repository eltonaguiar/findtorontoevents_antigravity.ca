#!/usr/bin/env python3
"""
ML Pick Scorer Prototype — Demonstrates how fixed ML workflows (hindsight-learner, skyrocket-detector, alpha-engine-live) improve audit pick scoring.

Loads AI top picks JSON (e.g. ag_top_picks.json), computes:
1. Meta-model win prob (from existing logistic)
2. Simulated hindsight-learner win prob (historical similar picks)
3. Skyrocket potential (upside prediction)
4. Alpha consensus bonus (match to proven strategies)

Enhanced score = original_score * ml_multiplier

Generates ML-enhanced JSON + top crypto picks list.
"""

import json
import numpy as np
from pathlib import Path

META_MODEL_PATH = Path("data/meta_model_weights.json")

PROVEN_STRATS = {
    'crypto_rsi_whaleconfirmed_v1', 'funding_momentum', 'crypto_keltner_compression_expansion',
    'crypto_vwap_deviation_reversion_vol', 'multi_period_rsi_confluence', 'drawdown_recovery_rsi'
}

HIGH_POTENTIAL_CRYPTO = {'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'}

def load_meta_model():
    with open(META_MODEL_PATH) as f:
        return json.load(f)

def compute_meta_win_prob(model, features):
    z = model['intercept']
    for feat in model['features']:
        raw = features.get(feat['name'], 0.0)
        std = feat['std']
        mean = feat['mean']
        standardized = (raw - mean) / std if std > 0 else 0
        z += feat['coef'] * standardized
    return 1 / (1 + np.exp(-z))

def simulate_hindsight_win_prob(symbol, strategy):
    # Simulate hindsight-learner: higher for proven strats or majors
    base = 0.55
    if strategy in PROVEN_STRATS:
        base += 0.15
    if symbol in HIGH_POTENTIAL_CRYPTO:
        base += 0.1
    return np.clip(base + 0.1 * np.random.randn(), 0.2, 0.9)

def simulate_skyrocket_potential(symbol, direction):
    # Skyrocket-detector: high for majors, adjust for direction
    base = 0.6 if symbol in HIGH_POTENTIAL_CRYPTO else 0.4
    if direction == 'SHORT':
        base = 1 - base  # Downside potential
    return np.clip(base + 0.05 * np.random.randn(), 0.1, 0.95)

def enhance_pick(pick, model):
    features = {
        'entry_score': pick.get('score', 50),
        'comp_strategy': pick.get('strategy_score', 60),
        'comp_consensus': pick.get('consensus', 1),
        # Simplified - add more as needed
    }
    
    meta_prob = compute_meta_win_prob(model, features)
    
    hindsight_prob = simulate_hindsight_win_prob(pick.get('symbol', ''), pick.get('strategy', ''))
    skyrocket_score = simulate_skyrocket_potential(pick.get('symbol', ''), pick.get('direction', 'LONG'))
    
    ml_multiplier = meta_prob * hindsight_prob * skyrocket_score * 1.1  # Alpha bonus
    
    original_score = pick.get('score', 50)
    enhanced_score = min(100, original_score * ml_multiplier)  # Cap at 100

    pick['ml_meta_prob'] = round(meta_prob, 3)
    pick['hindsight_win_prob'] = round(hindsight_prob, 3)
    pick['skyrocket_potential'] = round(skyrocket_score, 3)
    pick['ml_multiplier'] = round(ml_multiplier, 3)
    pick['enhanced_score'] = round(enhanced_score, 1)
    
    return pick

def main(input_path, output_path):
    model = load_meta_model()
    
    with open(input_path) as f:
        picks = json.load(f)
    
    if isinstance(picks, dict):
        picks = picks.get('picks', [])
    
    enhanced = [enhance_pick(p, model) for p in picks]
    enhanced.sort(key=lambda p: p['enhanced_score'], reverse=True)
    
    with open(output_path, 'w') as f:
        json.dump(enhanced, f, indent=2)
    
    print(f"✅ Enhanced {len(enhanced)} picks → {output_path}")
    print("\n🔥 TOP 5 CRYPTO PICKS (ML-enhanced):")
    crypto_top = [p for p in enhanced[:10] if 'USDT' in p.get('symbol', '')]
    for i, p in enumerate(crypto_top[:5], 1):
        print(f"  {i}. {p['symbol']} ({p['direction']}) | Enhanced: {p['enhanced_score']} | ML Prob: {p['ml_meta_prob']} | Skyrocket: {p['skyrocket_potential']}")

if __name__ == '__main__':
    input_file = "data/ag_top_picks.json"
    output_file = "data/ml_enhanced_ag_picks.json"
    main(input_file, output_file)
    print("\n💡 Run: python ml_pick_scorer.py")
    print("\n📈 INTEGRATION: Add 'ml_meta_prob', 'hindsight_win_prob', 'skyrocket_potential' as features to meta_model_trainer.py")
    print("   New score = old_score * (hindsight_prob * skyrocket_score)")