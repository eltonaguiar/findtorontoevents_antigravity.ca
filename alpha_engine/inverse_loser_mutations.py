#!/usr/bin/env python3
"""
Inverse Loser Mutations — Alpha Engine
=======================================
Takes consistently LOSING strategies and creates inverse mutations.
If a strategy always loses going LONG, the INVERSE (SHORT) should win.

Mutations per loser:
  - inverse_{strategy}         — flip LONG↔SHORT, same TP/SL ratios
  - inverse_{strategy}_tighter — flip + 0.7x TP/SL distance
  - inverse_{strategy}_wider   — flip + 1.5x TP/SL distance

Standalone runnable:
  python alpha_engine/inverse_loser_mutations.py
"""

import sys, os, io, json, copy, statistics
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DASHBOARD_PAYLOAD = BASE / "audit_trail" / "data" / "dashboard_payload.json"
ACTIVE_PICKS_PATH = BASE / "alpha_engine" / "data" / "active_picks.json"
INVERSE_PICKS_PATH = BASE / "alpha_engine" / "data" / "inverse_picks.json"
INVERSE_REPORT_PATH = BASE / "alpha_engine" / "data" / "inverse_loser_report.json"

# ── Thresholds ─────────────────────────────────────────────────────
MIN_TRADES = 10
MAX_WIN_RATE = 40.0       # % — must be below this to qualify as loser
MAX_TOTAL_PNL = -10.0     # % — must be worse than this
INVERSE_CONFIDENCE_LOW = 0.55
INVERSE_CONFIDENCE_HIGH = 0.65


def load_closed_picks() -> list[dict]:
    """Load recent_closed picks from dashboard payload."""
    with open(DASHBOARD_PAYLOAD, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])
    print(f"[DATA] Loaded {len(picks)} closed picks from dashboard payload")
    return picks


def load_active_picks() -> list[dict]:
    """Load current active picks from alpha engine."""
    if not ACTIVE_PICKS_PATH.exists():
        print("[WARN] No active_picks.json found")
        return []
    with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[DATA] Loaded {len(data)} active picks")
    return data


def group_by_strategy(picks: list[dict]) -> dict[str, list[dict]]:
    """Group picks by strategy family name."""
    groups = defaultdict(list)
    for p in picks:
        strat = p.get("strategy", "unknown")
        groups[strat].append(p)
    return dict(groups)


def compute_stats(picks: list[dict]) -> dict:
    """Compute WR, total PnL, avg PnL for a set of closed picks."""
    resolved = [p for p in picks if p.get("pnl_pct") is not None
                and p.get("status") in ("WON", "LOST", "STOPPED")]
    if not resolved:
        return {"trades": 0, "wr": 0, "pnl": 0, "avg_pnl": 0, "wins": 0, "losses": 0}

    pnls = [p["pnl_pct"] for p in resolved]
    wins = sum(1 for p in resolved if p.get("status") == "WON" or p["pnl_pct"] > 0)
    losses = len(resolved) - wins
    total_pnl = sum(pnls)
    wr = (wins / len(resolved)) * 100 if resolved else 0
    avg_pnl = statistics.mean(pnls) if pnls else 0

    return {
        "trades": len(resolved),
        "wr": round(wr, 1),
        "pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 3),
        "wins": wins,
        "losses": losses,
    }


def is_consistent_loser(stats: dict) -> bool:
    """Check if strategy qualifies as a consistent loser."""
    return (
        stats["trades"] >= MIN_TRADES
        and stats["wr"] < MAX_WIN_RATE
        and stats["pnl"] < MAX_TOTAL_PNL
    )


def flip_direction(direction: str) -> str:
    """Flip LONG to SHORT and vice versa."""
    d = direction.upper().strip()
    if d in ("LONG", "BUY"):
        return "SHORT"
    elif d in ("SHORT", "SELL"):
        return "LONG"
    return d


def compute_inverse_backtest(picks: list[dict], tp_mult: float = 1.0, sl_mult: float = 1.0) -> dict:
    """
    Backtest inverse: for each closed losing trade, compute what PnL
    would have been with flipped direction and optionally adjusted TP/SL.

    The key insight: if original LONG lost X%, inverse SHORT would have gained ~X%.
    We adjust for TP/SL multipliers on the distance.
    """
    resolved = [p for p in picks if p.get("pnl_pct") is not None
                and p.get("status") in ("WON", "LOST", "STOPPED")]
    if not resolved:
        return {"trades": 0, "wr": 0, "pnl": 0, "avg_pnl": 0}

    inverse_pnls = []
    inverse_wins = 0

    for p in resolved:
        orig_pnl = p["pnl_pct"]
        entry = p.get("entry_price", 0)
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        direction = p.get("direction", "LONG").upper()

        if entry <= 0:
            continue

        # Compute original TP/SL distances as percentages
        if direction in ("LONG", "BUY"):
            tp_dist_pct = ((tp - entry) / entry * 100) if tp and entry else 0
            sl_dist_pct = ((entry - sl) / entry * 100) if sl and entry else 0
        else:
            tp_dist_pct = ((entry - tp) / entry * 100) if tp and entry else 0
            sl_dist_pct = ((sl - entry) / entry * 100) if sl and entry else 0

        # Apply multipliers
        adj_tp_dist = tp_dist_pct * tp_mult
        adj_sl_dist = sl_dist_pct * sl_mult

        # Inverse logic: flip the PnL
        # If original was a loss, inverse would be a win (approximately)
        # Scale by TP/SL multiplier ratio
        if orig_pnl < 0:
            # Original lost — inverse wins
            # The gain is capped at the adjusted TP distance
            inv_pnl = min(abs(orig_pnl) * tp_mult, adj_tp_dist) if adj_tp_dist > 0 else abs(orig_pnl) * tp_mult
            inverse_wins += 1
        elif orig_pnl > 0:
            # Original won — inverse loses
            # The loss is capped at the adjusted SL distance
            inv_pnl = -min(orig_pnl * sl_mult, adj_sl_dist) if adj_sl_dist > 0 else -orig_pnl * sl_mult
        else:
            inv_pnl = 0

        inverse_pnls.append(round(inv_pnl, 4))

    total = len(inverse_pnls)
    wr = (inverse_wins / total * 100) if total else 0

    return {
        "trades": total,
        "wr": round(wr, 1),
        "pnl": round(sum(inverse_pnls), 2),
        "avg_pnl": round(statistics.mean(inverse_pnls), 3) if inverse_pnls else 0,
        "wins": inverse_wins,
        "losses": total - inverse_wins,
        "best_trade": round(max(inverse_pnls), 3) if inverse_pnls else 0,
        "worst_trade": round(min(inverse_pnls), 3) if inverse_pnls else 0,
    }


def create_inverse_active_pick(pick: dict, mutation_type: str, strat_name: str) -> dict:
    """
    Create an inverse version of an active pick.
    mutation_type: 'standard', 'tighter', 'wider'
    """
    inv = copy.deepcopy(pick)
    orig_strategy = pick.get("strategy", "unknown")

    # Mutation naming
    if mutation_type == "standard":
        inv_strategy = f"inverse_{orig_strategy}"
        tp_mult, sl_mult = 1.0, 1.0
    elif mutation_type == "tighter":
        inv_strategy = f"inverse_{orig_strategy}_tighter"
        tp_mult, sl_mult = 0.7, 0.7
    elif mutation_type == "wider":
        inv_strategy = f"inverse_{orig_strategy}_wider"
        tp_mult, sl_mult = 1.5, 1.5
    else:
        inv_strategy = f"inverse_{orig_strategy}"
        tp_mult, sl_mult = 1.0, 1.0

    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    orig_direction = pick.get("signal_type", pick.get("direction", "BUY")).upper()

    # Flip direction
    new_direction = flip_direction(orig_direction)

    # Compute new TP/SL for flipped direction
    if orig_direction in ("BUY", "LONG"):
        # Original was LONG, now SHORT
        orig_tp_dist = tp - entry if tp and entry else 0
        orig_sl_dist = entry - sl if sl and entry else 0
        # For SHORT: TP below entry, SL above entry
        new_tp = entry - (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 - 0.05 * tp_mult)
        new_sl = entry + (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 + 0.025 * sl_mult)
    else:
        # Original was SHORT, now LONG
        orig_tp_dist = entry - tp if tp and entry else 0
        orig_sl_dist = sl - entry if sl and entry else 0
        # For LONG: TP above entry, SL below entry
        new_tp = entry + (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 + 0.05 * tp_mult)
        new_sl = entry - (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 - 0.025 * sl_mult)

    # Update pick fields
    inv["id"] = f"{inv_strategy}::{pick.get('symbol', 'UNK')}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    inv["strategy"] = inv_strategy
    inv["signal_type"] = new_direction
    if "direction" in inv:
        inv["direction"] = new_direction
    inv["take_profit"] = round(new_tp, 6)
    inv["stop_loss"] = round(new_sl, 6)
    inv["confidence"] = round(INVERSE_CONFIDENCE_LOW + (INVERSE_CONFIDENCE_HIGH - INVERSE_CONFIDENCE_LOW) * 0.5, 3)
    inv["source_system"] = "inverse_loser_mutation"
    inv["status"] = "OPEN"
    inv["exit_price"] = None
    inv["exit_date"] = None
    inv["exit_reason"] = None
    inv["pnl_pct"] = None
    inv["pnl_dollar"] = None
    inv["scan_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inv["forward_validated"] = False
    inv["forward_status"] = f"inverse_mutation of {orig_strategy}"
    inv["inverse_mutation"] = {
        "original_strategy": orig_strategy,
        "mutation_type": mutation_type,
        "tp_multiplier": tp_mult,
        "sl_multiplier": sl_mult,
        "original_direction": orig_direction,
        "inverted_direction": new_direction,
    }

    # Reset tracking fields
    inv["high_water_mark"] = None
    inv["mfe"] = None
    inv["mae"] = None
    inv["current_price"] = None
    inv["unrealized_pnl_pct"] = None

    return inv


def generate_recommendation(inv_stats: dict, orig_stats: dict) -> str:
    """Generate a recommendation label based on inverse backtest quality."""
    inv_wr = inv_stats["wr"]
    inv_pnl = inv_stats["pnl"]

    if inv_wr >= 65 and inv_pnl > 50:
        return f"STRONG INVERSE -- {inv_wr}% WR when flipped"
    elif inv_wr >= 55 and inv_pnl > 20:
        return f"GOOD INVERSE -- {inv_wr}% WR, +{inv_pnl}% PnL"
    elif inv_wr >= 50 and inv_pnl > 0:
        return f"MODERATE INVERSE -- {inv_wr}% WR, marginal edge"
    else:
        return f"WEAK INVERSE -- {inv_wr}% WR, may not be profitable"


def run_inverse_mutations():
    """Main entry point: identify losers, backtest inverses, generate picks."""
    print("=" * 70)
    print("  INVERSE LOSER MUTATIONS ENGINE")
    print("  Flipping consistent losers into potential winners")
    print("=" * 70)
    print()

    # ── 1. Load data ───────────────────────────────────────────────
    closed_picks = load_closed_picks()
    active_picks = load_active_picks()

    # ── 2. Group by strategy and compute stats ─────────────────────
    groups = group_by_strategy(closed_picks)
    print(f"\n[ANALYSIS] Found {len(groups)} unique strategies in closed picks\n")

    all_stats = {}
    for strat, picks in groups.items():
        all_stats[strat] = compute_stats(picks)

    # ── 3. Identify consistent losers ──────────────────────────────
    losers = {}
    for strat, stats in sorted(all_stats.items(), key=lambda x: x[1]["pnl"]):
        if is_consistent_loser(stats):
            losers[strat] = stats

    print(f"{'='*70}")
    print(f"  CONSISTENT LOSERS (WR < {MAX_WIN_RATE}%, PnL < {MAX_TOTAL_PNL}%, trades >= {MIN_TRADES})")
    print(f"{'='*70}")
    print(f"  {'Strategy':<35} {'Trades':>7} {'WR%':>7} {'Total PnL':>10}")
    print(f"  {'-'*35} {'-'*7} {'-'*7} {'-'*10}")
    for strat, stats in sorted(losers.items(), key=lambda x: x[1]["pnl"]):
        print(f"  {strat:<35} {stats['trades']:>7} {stats['wr']:>6.1f}% {stats['pnl']:>+9.1f}%")
    print()

    if not losers:
        print("[INFO] No consistent losers found matching criteria. Nothing to invert.")
        return

    # ── 4. Backtest inverses ───────────────────────────────────────
    report_entries = []

    print(f"{'='*70}")
    print(f"  INVERSE BACKTEST RESULTS")
    print(f"{'='*70}")

    for strat in sorted(losers.keys(), key=lambda s: losers[s]["pnl"]):
        orig_stats = losers[strat]
        strat_picks = groups[strat]

        # Three mutations
        inv_standard = compute_inverse_backtest(strat_picks, tp_mult=1.0, sl_mult=1.0)
        inv_tighter = compute_inverse_backtest(strat_picks, tp_mult=0.7, sl_mult=0.7)
        inv_wider = compute_inverse_backtest(strat_picks, tp_mult=1.5, sl_mult=1.5)

        recommendation = generate_recommendation(inv_standard, orig_stats)

        entry = {
            "original": strat,
            "original_stats": {
                "trades": orig_stats["trades"],
                "wr": orig_stats["wr"],
                "pnl": orig_stats["pnl"],
                "avg_pnl": orig_stats["avg_pnl"],
            },
            "inverse_backtest": inv_standard,
            "inverse_tighter_backtest": inv_tighter,
            "inverse_wider_backtest": inv_wider,
            "mutations": [
                f"inverse_{strat}",
                f"inverse_{strat}_tighter",
                f"inverse_{strat}_wider",
            ],
            "recommendation": recommendation,
        }
        report_entries.append(entry)

        # Print results
        print(f"\n  >> {strat}")
        print(f"     Original:        {orig_stats['trades']} trades | {orig_stats['wr']:.1f}% WR | {orig_stats['pnl']:+.1f}% PnL")
        print(f"     Inverse STD:     {inv_standard['trades']} trades | {inv_standard['wr']:.1f}% WR | {inv_standard['pnl']:+.1f}% PnL | avg {inv_standard['avg_pnl']:+.3f}%")
        print(f"     Inverse TIGHT:   {inv_tighter['trades']} trades | {inv_tighter['wr']:.1f}% WR | {inv_tighter['pnl']:+.1f}% PnL | avg {inv_tighter['avg_pnl']:+.3f}%")
        print(f"     Inverse WIDE:    {inv_wider['trades']} trades | {inv_wider['wr']:.1f}% WR | {inv_wider['pnl']:+.1f}% PnL | avg {inv_wider['avg_pnl']:+.3f}%")
        print(f"     Recommendation:  {recommendation}")

    # ── 5. Generate inverse picks from active picks ────────────────
    print(f"\n{'='*70}")
    print(f"  GENERATING INVERSE PICKS FROM ACTIVE LOSER STRATEGIES")
    print(f"{'='*70}")

    loser_strategy_names = set(losers.keys())
    inverse_picks = []

    for pick in active_picks:
        strat = pick.get("strategy", "")
        if strat not in loser_strategy_names:
            continue

        # Create all three mutations
        for mut_type in ("standard", "tighter", "wider"):
            inv_pick = create_inverse_active_pick(pick, mut_type, strat)
            inverse_picks.append(inv_pick)

    print(f"\n  Active picks from loser strategies found: {sum(1 for p in active_picks if p.get('strategy') in loser_strategy_names)}")
    print(f"  Inverse picks generated: {len(inverse_picks)} (3 mutations each)")

    if inverse_picks:
        # Show sample
        strats_generated = set(p["strategy"] for p in inverse_picks)
        for s in sorted(strats_generated):
            count = sum(1 for p in inverse_picks if p["strategy"] == s)
            print(f"    - {s}: {count} picks")

    # ── 6. Save inverse picks ──────────────────────────────────────
    INVERSE_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INVERSE_PICKS_PATH, "w", encoding="utf-8") as f:
        json.dump(inverse_picks, f, indent=2, default=str)
    print(f"\n  [SAVED] {len(inverse_picks)} inverse picks -> {INVERSE_PICKS_PATH}")

    # ── 7. Save report ─────────────────────────────────────────────
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "min_trades": MIN_TRADES,
            "max_win_rate_pct": MAX_WIN_RATE,
            "max_total_pnl_pct": MAX_TOTAL_PNL,
        },
        "total_losers_found": len(losers),
        "total_mutations_created": len(inverse_picks),
        "loser_strategies": report_entries,
        "summary": {
            "best_inverse": max(report_entries, key=lambda x: x["inverse_backtest"]["pnl"])["original"] if report_entries else None,
            "worst_inverse": min(report_entries, key=lambda x: x["inverse_backtest"]["pnl"])["original"] if report_entries else None,
            "total_inverse_pnl": round(sum(e["inverse_backtest"]["pnl"] for e in report_entries), 2),
            "avg_inverse_wr": round(statistics.mean([e["inverse_backtest"]["wr"] for e in report_entries]), 1) if report_entries else 0,
        },
    }

    with open(INVERSE_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  [SAVED] Report -> {INVERSE_REPORT_PATH}")

    # ── 8. Final summary ──────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Loser strategies identified:  {len(losers)}")
    print(f"  Inverse mutations created:    {len(losers) * 3} strategy variants")
    print(f"  Inverse active picks:         {len(inverse_picks)}")
    print(f"  Combined inverse backtest PnL: {report['summary']['total_inverse_pnl']:+.1f}%")
    print(f"  Average inverse WR:           {report['summary']['avg_inverse_wr']:.1f}%")
    if report["summary"]["best_inverse"]:
        best = [e for e in report_entries if e["original"] == report["summary"]["best_inverse"]][0]
        print(f"  Best inverse candidate:       {best['original']} -> {best['inverse_backtest']['wr']:.1f}% WR, {best['inverse_backtest']['pnl']:+.1f}% PnL")
    print(f"\n  Files written:")
    print(f"    - {INVERSE_PICKS_PATH}")
    print(f"    - {INVERSE_REPORT_PATH}")
    print()

    return report


if __name__ == "__main__":
    run_inverse_mutations()
