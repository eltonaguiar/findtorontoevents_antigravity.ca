"""
Ghost Pick Cleaner
===================
Removes the 663 MATIC→POL placeholder rows from closed_picks.json
that have 0% win rate and drag system WR down from ~36.5% to 28.3%.

These are not real trades — they are placeholder rows created during the
MATIC→POL token migration that were never cleaned up.

Usage:
    python tools/fixes_v2/ghost_pick_cleaner.py
    
    # Or import:
    from tools.fixes_v2.ghost_pick_cleaner import clean_ghost_picks
    cleaned = clean_ghost_picks(picks_data)

Author: Live Performance Analysis Fix
Date: 2026-04-11
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def identify_ghost_picks(picks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Separate ghost/placeholder picks from real trades.
    
    Ghost pick detection criteria:
    1. MATICUSDT with pnl_pct exactly -0.15 (placeholder value)
    2. MATICUSDT with exit_price == entry_price (no actual price movement)

    Note: an earlier draft included a third check that deleted any pick with
    an exit_reason outside a narrow whitelist. Audit on 2026-04-12 against
    closed_picks.json (n=3331) showed that check would have dropped 103 real
    trades with variant-but-valid exit strings (SL_HIT, TP_HIT,
    TP_HIT_RESOLVED, PRICE_RESOLVED, FORCE_CLOSED_TOXIC, TRAILING_STOP). The
    check was removed — Checks 1+2 catch all 660 MATIC placeholders (every
    MATIC row in the ledger has exit_reason=TIME_EXIT + pnl_pct=-0.15 exact).

    Returns:
        (real_picks, ghost_picks)
    """
    real = []
    ghosts = []

    for pick in picks:
        is_ghost = False
        reason = ""

        symbol = pick.get("symbol", "")
        entry = pick.get("entry_price", 0)
        exit_p = pick.get("exit_price", 0)
        pnl = pick.get("pnl_pct", 0)

        # Check 1: MATIC with exact -0.15 pnl (placeholder)
        if symbol == "MATICUSDT" and abs(pnl - (-0.15)) < 0.001:
            is_ghost = True
            reason = "MATIC placeholder (pnl=-0.15 exact)"

        # Check 2: MATIC with exit_price == entry_price
        elif symbol == "MATICUSDT" and entry > 0 and abs(exit_p - entry) < 1e-8:
            is_ghost = True
            reason = "MATIC placeholder (exit==entry)"
        
        if is_ghost:
            pick["_ghost_reason"] = reason
            ghosts.append(pick)
        else:
            real.append(pick)
    
    return real, ghosts


def clean_ghost_picks(picks: List[Dict]) -> Dict[str, Any]:
    """
    Clean ghost picks and return stats.
    
    Returns:
        Dict with: cleaned_picks, ghost_picks, stats
    """
    real, ghosts = identify_ghost_picks(picks)
    
    # Stats before/after
    total_before = len(picks)
    real_before = [p for p in picks if p.get("exit_reason") in ("TP", "SL", "TIME_EXIT")]
    wins_before = sum(1 for p in real_before if p.get("pnl_pct", 0) > 0)
    wr_before = wins_before / len(real_before) * 100 if real_before else 0
    
    real_after = [p for p in real if p.get("exit_reason") in ("TP", "SL", "TIME_EXIT")]
    wins_after = sum(1 for p in real_after if p.get("pnl_pct", 0) > 0)
    wr_after = wins_after / len(real_after) * 100 if real_after else 0
    
    avg_pnl_before = sum(p.get("pnl_pct", 0) for p in real_before) / len(real_before) if real_before else 0
    avg_pnl_after = sum(p.get("pnl_pct", 0) for p in real_after) / len(real_after) if real_after else 0
    
    stats = {
        "total_before": total_before,
        "total_after": len(real),
        "ghosts_removed": len(ghosts),
        "wr_before": round(wr_before, 1),
        "wr_after": round(wr_after, 1),
        "wr_improvement_pp": round(wr_after - wr_before, 1),
        "avg_pnl_before": round(avg_pnl_before, 4),
        "avg_pnl_after": round(avg_pnl_after, 4),
        "ghost_symbols": {},
    }
    
    # Count ghosts by symbol
    for g in ghosts:
        sym = g.get("symbol", "?")
        stats["ghost_symbols"][sym] = stats["ghost_symbols"].get(sym, 0) + 1
    
    logger.info(
        f"Ghost cleaner: removed {len(ghosts)} ghost picks. "
        f"WR: {wr_before:.1f}% → {wr_after:.1f}% (+{wr_after-wr_before:.1f}pp). "
        f"Avg PnL: {avg_pnl_before:+.4f}% → {avg_pnl_after:+.4f}%"
    )
    
    return {
        "cleaned_picks": real,
        "ghost_picks": ghosts,
        "stats": stats,
    }


def main():
    """CLI: clean closed_picks.json in-place (with backup)."""
    # Find the file
    candidates = [
        Path("alpha_engine/data/closed_picks.json"),
        Path("data/closed_picks.json"),
        Path("closed_picks.json"),
    ]
    
    picks_path = None
    for c in candidates:
        if c.exists():
            picks_path = c
            break
    
    if picks_path is None:
        print("ERROR: closed_picks.json not found. Run from repo root.")
        sys.exit(1)
    
    print(f"Loading {picks_path}...")
    with open(picks_path) as f:
        picks = json.load(f)
    
    result = clean_ghost_picks(picks)
    stats = result["stats"]
    
    print(f"\n{'='*60}")
    print(f"Ghost Pick Cleaner Results")
    print(f"{'='*60}")
    print(f"  Total before:     {stats['total_before']}")
    print(f"  Ghosts removed:   {stats['ghosts_removed']}")
    print(f"  Total after:      {stats['total_after']}")
    print(f"  WR before:        {stats['wr_before']}%")
    print(f"  WR after:         {stats['wr_after']}%")
    print(f"  WR improvement:   +{stats['wr_improvement_pp']}pp")
    print(f"  Avg PnL before:   {stats['avg_pnl_before']:+.4f}%")
    print(f"  Avg PnL after:    {stats['avg_pnl_after']:+.4f}%")
    print(f"  Ghost symbols:    {stats['ghost_symbols']}")
    print(f"{'='*60}")
    
    # Backup original
    backup_path = picks_path.with_suffix(".json.bak")
    import shutil
    shutil.copy2(picks_path, backup_path)
    print(f"\n  Backup saved to: {backup_path}")
    
    # Write cleaned
    with open(picks_path, "w") as f:
        json.dump(result["cleaned_picks"], f, indent=2)
    print(f"  Cleaned file written to: {picks_path}")
    
    # Write ghost log
    ghost_path = picks_path.parent / "ghost_picks_removed.json"
    with open(ghost_path, "w") as f:
        json.dump(result["ghost_picks"], f, indent=2)
    print(f"  Ghost log written to: {ghost_path}")


if __name__ == "__main__":
    main()
