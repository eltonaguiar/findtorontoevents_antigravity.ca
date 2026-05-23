#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Backfill ML Features
=====================================
Backfill dead ML features for existing closed and active picks.

Run this to fix the 75% dead feature problem:
    python backfill_ml_features.py --closed --active

This will:
1. Extract time features from timestamps (hour_utc, hour_sin, etc.)
2. Extract strategy performance from pick metadata
3. Recompute feature health report
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from feature_health import generate_health_report, _extract_ml_features
from ml_feature_improvements import enrich_pick_features


def backfill_picks(picks_path: Path, output_path: Path = None) -> dict:
    """Backfill ML features for picks in a JSON file."""
    
    if not picks_path.exists():
        print(f"File not found: {picks_path}")
        return {"status": "error", "reason": "file_not_found"}
    
    with open(picks_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(data, list):
        picks = data
        wrapper = None
    elif isinstance(data, dict):
        # Look for picks in common keys
        for key in ["active_picks", "picks", "closed_picks", "data"]:
            if key in data and isinstance(data[key], list):
                picks = data[key]
                wrapper = key
                break
        else:
            print(f"Could not find picks list in {picks_path}")
            return {"status": "error", "reason": "no_picks_found"}
    else:
        return {"status": "error", "reason": "invalid_format"}
    
    print(f"Processing {len(picks)} picks from {picks_path.name}...")
    
    # Count features before
    before_counts = {}
    for pick in picks[:100]:  # Sample first 100
        ml_feat = pick.get("ml_features_at_entry", {}) or {}
        for k in ml_feat:
            before_counts[k] = before_counts.get(k, 0) + 1
    
    # Backfill each pick
    enriched_count = 0
    for pick in picks:
        original_feat = pick.get("ml_features_at_entry", {}) or {}
        
        # Enrich with new features
        enriched = enrich_pick_features(pick.copy())
        new_feat = enriched.get("ml_features_at_entry", {})
        
        # Merge: new features take precedence, keep old ones not overwritten
        merged = {**original_feat, **new_feat}
        pick["ml_features_at_entry"] = merged
        
        if len(merged) > len(original_feat):
            enriched_count += 1
    
    # Count features after
    after_counts = {}
    for pick in picks[:100]:  # Sample first 100
        ml_feat = pick.get("ml_features_at_entry", {}) or {}
        for k in ml_feat:
            after_counts[k] = after_counts.get(k, 0) + 1
    
    # Save if output path specified
    if output_path:
        if wrapper:
            data[wrapper] = picks
        else:
            data = picks
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to {output_path}")
    
    return {
        "status": "ok",
        "total_picks": len(picks),
        "enriched_count": enriched_count,
        "features_before": len(before_counts),
        "features_after": len(after_counts),
        "new_features": list(set(after_counts.keys()) - set(before_counts.keys())),
    }


def main():
    parser = argparse.ArgumentParser(description="Backfill ML features for existing picks")
    parser.add_argument("--closed", action="store_true", help="Process closed_picks.json")
    parser.add_argument("--active", action="store_true", help="Process active_picks.json")
    parser.add_argument("--all", action="store_true", help="Process all pick files")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument("--health-check", action="store_true", help="Regenerate health report after")
    
    args = parser.parse_args()
    
    data_dir = Path(__file__).parent / "data"
    results = []
    
    if args.all or args.closed:
        closed_path = data_dir / "closed_picks.json"
        output_path = None if args.dry_run else closed_path
        result = backfill_picks(closed_path, output_path)
        results.append(("closed_picks", result))
    
    if args.all or args.active:
        active_path = data_dir / "active_picks.json"
        output_path = None if args.dry_run else active_path
        result = backfill_picks(active_path, output_path)
        results.append(("active_picks", result))
    
    # Print summary
    print("\n" + "="*60)
    print("BACKFILL SUMMARY")
    print("="*60)
    
    for name, result in results:
        print(f"\n{name}:")
        print(f"  Status: {result['status']}")
        if result['status'] == 'ok':
            print(f"  Total picks: {result['total_picks']}")
            print(f"  Enriched: {result['enriched_count']}")
            print(f"  Features before: {result['features_before']}")
            print(f"  Features after: {result['features_after']}")
            if result['new_features']:
                print(f"  New features added: {', '.join(result['new_features'][:5])}")
    
    # Regenerate health report
    if args.health_check and not args.dry_run:
        print("\nRegenerating feature health report...")
        report = generate_health_report()
        print(f"\nNew health score: {report['health_score']:.2%}")
        print(f"Alive features: {report['alive_features']}/{report['total_features']}")
        print(f"Dead features: {report['dead_features']}/{report['total_features']}")
        
        # Show improvement
        if report['health_score'] >= 0.5:
            print("\n[OK] Health score improved to acceptable level (>=50%)")
        elif report['health_score'] >= 0.3:
            print("\n[WARN] Health score improved but still below target (30-50%)")
        else:
            print("\n[FAIL] Health score still critically low (<30%)")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
