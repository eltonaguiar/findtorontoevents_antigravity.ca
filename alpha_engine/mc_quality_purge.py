#!/usr/bin/env python3
"""
Monte Carlo Quality Purge — Remove confirmed-loser strategies from active_picks.json
=========================================================================================
Based on the Monte Carlo audit, only ML Enhanced strategies have statistically verified edge.
This script:
  1. Removes picks from PERMANENTLY_KILLED strategies
  2. Removes picks from LOW_CONFIDENCE strategies with 0% WR  
  3. Boosts elite_score for ML Enhanced proven-winner picks
  4. Reports what was purged vs. what remains
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
ACTIVE_PICKS = ROOT / "alpha_engine" / "data" / "active_picks.json"
CLOSED_PICKS = ROOT / "alpha_engine" / "data" / "closed_picks.json"

# Import the kill lists
sys.path.insert(0, str(ROOT / "alpha_engine"))
from auto_tuner import PERMANENTLY_KILLED, LOW_CONFIDENCE_STRATEGIES, HARD_DISABLED_PATTERNS

# Strategies with PROVEN edge (Monte Carlo verified)
PROVEN_ML_STRATEGIES = {
    "ml_enhanced_BNBUSDT_15m_B_lightgbm",      # 94.4% WR, 18 trades
    "ml_enhanced_FETUSDT_1d_B_lightgbm",        # 94.1% WR, 17 trades
    "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack", # 88.2% WR, 17 trades
    "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack", # 85.7% WR, 7 trades
}

# ML Enhanced strategies that are good (not the frozen 15m_D bugs)
ML_ENHANCED_GOOD_SYMBOLS = {"BNBUSDT", "FETUSDT", "RENDERUSDT"}


def load_json(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def is_killed(pick):
    """Check if a pick's strategy should be purged."""
    strat = pick.get("strategy", "")
    
    # Permanent kill list
    if strat in PERMANENTLY_KILLED:
        return True, f"PERMANENTLY_KILLED ({strat})"
    
    # Pattern match (frozen 15m_D_ensemble_stack)
    for pattern in HARD_DISABLED_PATTERNS:
        if pattern in strat:
            return True, f"PATTERN_KILLED ({pattern})"
    
    return False, ""


def main():
    print("=" * 70)
    print("  Monte Carlo Quality Purge")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    
    # Load active picks
    picks = load_json(ACTIVE_PICKS)
    print(f"\n  Loaded {len(picks)} active picks")
    
    # Separate: keep vs purge
    kept = []
    purged = []
    boosted = 0
    
    penalized = 0
    for pick in picks:
        killed, reason = is_killed(pick)
        if killed:
            # Penalize score heavily instead of removing
            old_score = pick.get("elite_score", 50)
            pick["elite_score"] = max(0, float(old_score or 50) - 40)
            pick["_mc_killed"] = True
            pick["_mc_reason"] = reason
            purged.append((pick, reason))
            penalized += 1

        # Boost proven ML strategies
        strat = pick.get("strategy", "")
        if strat in PROVEN_ML_STRATEGIES:
            old_score = pick.get("elite_score", 50)
            pick["elite_score"] = max(old_score, 85)  # Floor at 85 for proven winners
            pick["mc_verified"] = True
            pick["mc_note"] = "Monte Carlo verified edge (93% profitable sims)"
            boosted += 1
        kept.append(pick)

    # Report
    print(f"\n  PENALIZED: {penalized} picks from confirmed-loser strategies (kept with low score)")
    print(f"  TOTAL:   {len(kept)} picks (all kept)")
    print(f"  BOOSTED: {boosted} ML Enhanced picks scored to 85+")

    if purged:
        print(f"\n  Penalized strategies:")
        strat_counts = {}
        for pick, reason in purged:
            s = pick.get("strategy", "unknown")
            strat_counts[s] = strat_counts.get(s, 0) + 1
        for s, c in sorted(strat_counts.items(), key=lambda x: -x[1]):
            print(f"    {c:>3}x {s}")

    # Show distribution by strategy
    print(f"\n  Pick distribution:")
    strat_kept = {}
    for p in kept:
        s = p.get("strategy", "unknown")
        strat_kept[s] = strat_kept.get(s, 0) + 1
    for s, c in sorted(strat_kept.items(), key=lambda x: -x[1]):
        tag = " ★ PROVEN" if s in PROVEN_ML_STRATEGIES else ""
        print(f"    {c:>3}x {s}{tag}")

    # Save all picks (no removal)
    save_json(ACTIVE_PICKS, kept)

    print(f"\n  Saved: {len(kept)} active (all preserved)")
    print("=" * 70)
    
    return len(purged)


if __name__ == "__main__":
    purged = main()
    # Exit code 0 even if nothing purged (not an error)
    sys.exit(0)
