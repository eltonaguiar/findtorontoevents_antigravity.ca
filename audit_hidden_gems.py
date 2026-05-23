#!/usr/bin/env python3
"""Audit active picks for hidden gems (high ML score, low elite score)"""
import json

with open('alpha_engine/data/active_picks.json') as f:
    picks = json.load(f)

hidden_gems = []
for p in picks:
    ml_score = p.get('ml_score') or p.get('ml_composite_score') or 0
    elite = p.get('elite_score') or 0
    
    if ml_score >= 0.7 and elite < 30:
        hidden_gems.append({
            'symbol': p.get('symbol'),
            'ml_score': ml_score,
            'elite_score': elite,
            'strategy': p.get('strategy'),
            'confidence': p.get('confidence', 0),
            'entry': p.get('entry_price'),
            'tp': p.get('take_profit'),
            'sl': p.get('stop_loss'),
            'direction': p.get('direction')
        })

print(f"Hidden gems found: {len(hidden_gems)} (ML>=0.7, Elite<30)")
print()

for g in sorted(hidden_gems, key=lambda x: x['ml_score'], reverse=True)[:15]:
    print(f"  {g['symbol']:12} ML={g['ml_score']:.2f} Elite={g['elite_score']:4.0f} Conf={g['confidence']:.2f} Strat={g['strategy'][:40]}")

# Also check for score=0 but high ML
print("\n" + "="*80)
print("CRITICAL: Picks with elite_score=0 but high ML score")
zero_elite = [p for p in picks if (p.get('elite_score') or 0) == 0 and (p.get('ml_score') or p.get('ml_composite_score') or 0) > 0.5]
print(f"Found: {len(zero_elite)}")
for p in sorted(zero_elite, key=lambda x: x.get('ml_score') or x.get('ml_composite_score') or 0, reverse=True)[:10]:
    ml = p.get('ml_score') or p.get('ml_composite_score') or 0
    print(f"  {p.get('symbol')}: ML={ml:.2f}, Elite=0, Conf={p.get('confidence', 0):.2f}")
