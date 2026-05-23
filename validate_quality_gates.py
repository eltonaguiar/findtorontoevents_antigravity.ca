#!/usr/bin/env python3
"""Validate quality gates implementation."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    
    print("=" * 60)
    print("QUALITY GATES VALIDATION REPORT")
    print("=" * 60)
    
    with open(payload_path) as f:
        data = json.load(f)
    
    picks = data['picks']['active']
    smart_picks = data['picks'].get('smart_picks', [])
    
    print(f"\nTotal active picks: {len(picks)}")
    print(f"Smart picks: {len(smart_picks)}")
    
    # Analyze scores
    scores = [p.get('score', 0) or 0 for p in picks]
    print(f"\n--- Score Distribution ---")
    print(f"  Min: {min(scores) if scores else 0}")
    print(f"  Max: {max(scores) if scores else 0}")
    print(f"  Avg: {sum(scores)/len(scores) if scores else 0:.1f}")
    print(f"  >= 55: {sum(1 for s in scores if s >= 55)}")
    print(f"  >= 65 (Smart Picks min): {sum(1 for s in scores if s >= 65)}")
    
    # Analyze confidence
    confs = [p.get('confidence', 0) or 0 for p in picks]
    print(f"\n--- Confidence Distribution ---")
    print(f"  Min: {min(confs) if confs else 0:.3f}")
    print(f"  Max: {max(confs) if confs else 0:.3f}")
    print(f"  0.58-0.80 (sweet spot): {sum(1 for c in confs if 0.58 <= c <= 0.80)}")
    
    # Analyze ml_score
    ml_scores = [p.get('ml_score') for p in picks]
    ml_scores_nonzero = [m for m in ml_scores if m is not None and m > 0]
    print(f"\n--- ML Score Distribution ---")
    print(f"  Populated: {len(ml_scores_nonzero)}/{len(picks)}")
    if ml_scores_nonzero:
        print(f"  Min: {min(ml_scores_nonzero):.3f}")
        print(f"  Max: {max(ml_scores_nonzero):.3f}")
    
    # Check entry prices
    entries = [p.get('entry_price', 0) or 0 for p in picks]
    print(f"\n--- Entry Prices ---")
    print(f"  > 0: {sum(1 for e in entries if e > 0)}")
    print(f"  = 0: {sum(1 for e in entries if e == 0)}")
    
    # Show top picks by score
    print(f"\n--- Top 5 Picks by Score ---")
    sorted_picks = sorted(picks, key=lambda x: x.get('score', 0) or 0, reverse=True)[:5]
    for p in sorted_picks:
        print(f"  {p['symbol']} {p['direction']}: score={p.get('score', 0)}, conf={p.get('confidence', 0):.3f}, ml={p.get('ml_score')}, entry={p.get('entry_price', 0)}")
    
    # Check why no smart picks
    print(f"\n--- Smart Picks Gate Analysis ---")
    from audit_trail.quality_gates import passes_smart_gate, calculate_smart_score
    
    checks = {
        'score_ge_65': 0,
        'confidence_ge_0.58': 0,
        'ml_score_populated': 0,
        'entry_gt_0': 0,
        'all_passed': 0
    }
    
    for p in picks:
        if (p.get('score') or 0) >= 65:
            checks['score_ge_65'] += 1
        if (p.get('confidence') or 0) >= 0.58:
            checks['confidence_ge_0.58'] += 1
        if p.get('ml_score') is not None and p.get('ml_score') > 0:
            checks['ml_score_populated'] += 1
        if (p.get('entry_price') or 0) > 0:
            checks['entry_gt_0'] += 1
        if passes_smart_gate(p):
            checks['all_passed'] += 1
    
    print(f"  Score >= 65: {checks['score_ge_65']}")
    print(f"  Confidence >= 0.58: {checks['confidence_ge_0.58']}")
    print(f"  ML score populated: {checks['ml_score_populated']}")
    print(f"  Entry > 0: {checks['entry_gt_0']}")
    print(f"  ALL criteria (Smart Picks): {checks['all_passed']}")
    
    # Quality stats from payload
    print(f"\n--- Payload Quality Stats ---")
    qstats = data['summary'].get('quality_stats', {})
    if qstats:
        print(f"  Total before gates: {qstats.get('total_active_before_gates')}")
        print(f"  After active gate: {qstats.get('active_after_gates')}")
        print(f"  Smart picks: {qstats.get('smart_picks_count')}")
        print(f"  Smart %: {qstats.get('smart_picks_percentage')}%")
    
    print("\n" + "=" * 60)
    
    # Recommendations
    print("\n--- RECOMMENDATIONS ---")
    if checks['all_passed'] == 0:
        print("ISSUE: No picks are passing the Smart Picks gate!")
        if checks['score_ge_65'] == 0:
            print("  -> Lower SMART_PICKS_MIN_SCORE from 65 to 55")
        if checks['ml_score_populated'] == 0:
            print("  -> ML scores are not populated - check feature pipeline")
        if checks['confidence_ge_0.58'] < 10:
            print("  -> Lower SMART_PICKS_MIN_CONFIDENCE from 0.58 to 0.50")
    else:
        print(f"OK: {checks['all_passed']} picks pass Smart Picks gate")

if __name__ == "__main__":
    main()
