#!/usr/bin/env python3
"""
What-If Consensus Profitability Analysis
=========================================
Analyses which system+strategy combinations would have been most profitable
if traded based on cross-system agreement.

Reads closed picks from audit_trail/data/dashboard_payload.json and computes:
  1. Profitability by agreement level (1 system, 2 systems, 3+)
  2. Strategy-level breakdown — which strategy PAIRS profit together
  3. Best/worst system combos
  4. Optimal consensus formula
"""

import sys, os, json, pathlib
from collections import defaultdict
from itertools import combinations
from datetime import datetime, timezone

# Windows UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT  = ROOT / "alpha_engine" / "data" / "consensus_what_if.json"


def load_payload():
    with open(PAYLOAD, "r", encoding="utf-8") as f:
        return json.load(f)


def is_valid_closed(p):
    """Only count actual resolved trades (WON/LOST), skip auto-expired."""
    if p.get("_auto_expired"):
        return False
    return p.get("status") in ("WON", "LOST")


def compute_stats(picks):
    """Compute WR, total PnL, avg PnL for a list of picks."""
    if not picks:
        return {"trades": 0, "wr": 0, "pnl": 0, "avg_pnl": 0, "wins": 0, "losses": 0}
    wins = sum(1 for p in picks if p["status"] == "WON")
    losses = sum(1 for p in picks if p["status"] == "LOST")
    total_pnl = sum(p.get("pnl_pct", 0) or 0 for p in picks)
    return {
        "trades": len(picks),
        "wr": round(wins / len(picks) * 100, 1) if picks else 0,
        "pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(picks), 3) if picks else 0,
        "wins": wins,
        "losses": losses,
    }


def group_by_signal(picks):
    """Group picks by (symbol, direction) to find concurrent signals."""
    groups = defaultdict(list)
    for p in picks:
        key = (p["symbol"], p["direction"])
        groups[key].append(p)
    return groups


def build_agreement_levels(closed):
    """
    For each closed pick, determine how many SYSTEMS had the same symbol+direction
    active at the same time. Uses system_agreement_count (pre-computed) or
    falls back to len(source_systems).
    """
    for p in closed:
        # system_agreement_count is the number of systems that had this signal
        sys_count = p.get("system_agreement_count", 0)
        if sys_count == 0:
            src = p.get("source_systems", [])
            sys_count = len(src) if src else 1
        p["_sys_agree"] = sys_count

    # Bucket into levels
    buckets = {
        "1_system":  [p for p in closed if p["_sys_agree"] <= 1],
        "2_3_systems": [p for p in closed if 2 <= p["_sys_agree"] <= 3],
        "4_7_systems": [p for p in closed if 4 <= p["_sys_agree"] <= 7],
        "8_14_systems": [p for p in closed if 8 <= p["_sys_agree"] <= 14],
        "15_plus":   [p for p in closed if p["_sys_agree"] >= 15],
    }

    result = {}
    for label, picks in buckets.items():
        result[label] = compute_stats(picks)
    return result


def find_strategy_pairs(closed, min_trades=3):
    """
    Group picks by (symbol, direction). For each group, collect all unique
    strategies from source_system+strategy. Find strategy pairs that co-occur
    and measure their joint performance.
    """
    # Group by symbol+direction to find simultaneous signals
    signal_groups = defaultdict(list)
    for p in closed:
        key = (p["symbol"], p["direction"])
        signal_groups[key].append(p)

    # For each symbol+direction group, find which strategies are present
    # A "strategy" here is source_system::strategy
    pair_outcomes = defaultdict(list)  # (stratA, stratB) -> [pick outcomes]

    for (sym, direction), group_picks in signal_groups.items():
        if len(group_picks) < 2:
            continue

        # Collect unique strategies in this group
        strats_in_group = set()
        strat_to_picks = defaultdict(list)
        for p in group_picks:
            strat_id = f"{p.get('source_system', 'unknown')}::{p.get('strategy', 'unknown')}"
            strats_in_group.add(strat_id)
            strat_to_picks[strat_id].append(p)

        # For each pair of strategies present in this group,
        # record the outcomes of ALL picks in the group
        if len(strats_in_group) < 2:
            continue

        sorted_strats = sorted(strats_in_group)
        for s1, s2 in combinations(sorted_strats, 2):
            # The "consensus" picks are all picks in this group (all benefited from agreement)
            for p in group_picks:
                pair_outcomes[(s1, s2)].append(p)

    # Compute stats for each pair
    pairs = []
    seen_picks = set()
    for (s1, s2), picks in pair_outcomes.items():
        # Deduplicate picks
        unique_picks = []
        pick_ids = set()
        for p in picks:
            pid = f"{p['symbol']}_{p['direction']}_{p.get('timestamp','')}_{p.get('strategy','')}"
            if pid not in pick_ids:
                pick_ids.add(pid)
                unique_picks.append(p)

        if len(unique_picks) < min_trades:
            continue

        stats = compute_stats(unique_picks)
        symbols = sorted(set(p["symbol"] for p in unique_picks))

        pairs.append({
            "pair": [s1, s2],
            "trades": stats["trades"],
            "wr": stats["wr"],
            "pnl": stats["pnl"],
            "avg_pnl": stats["avg_pnl"],
            "symbols": symbols[:10],
            "wins": stats["wins"],
            "losses": stats["losses"],
        })

    # Sort by profitability (WR * trades for significance-weighted)
    pairs.sort(key=lambda x: (x["wr"] * min(x["trades"], 50), x["pnl"]), reverse=True)
    return pairs


def find_system_combos(closed, min_trades=5):
    """
    For each pick, look at source_systems. Find which system COMBINATIONS
    correlate with higher win rates.
    """
    # Group by number of agreeing systems AND the specific systems
    combo_outcomes = defaultdict(list)

    for p in closed:
        systems = sorted(set(p.get("source_systems", [])))
        if len(systems) < 2:
            continue

        # Record outcomes for each pair of systems
        for s1, s2 in combinations(systems[:10], 2):  # cap to avoid combinatorial explosion
            combo_outcomes[(s1, s2)].append(p)

    combos = []
    for (s1, s2), picks in combo_outcomes.items():
        if len(picks) < min_trades:
            continue
        stats = compute_stats(picks)
        combos.append({
            "combo": [s1, s2],
            "trades": stats["trades"],
            "wr": stats["wr"],
            "pnl": stats["pnl"],
            "avg_pnl": stats["avg_pnl"],
            "wins": stats["wins"],
            "losses": stats["losses"],
        })

    combos.sort(key=lambda x: (x["wr"] * min(x["trades"], 50), x["pnl"]), reverse=True)
    return combos


def find_direction_breakdown(closed):
    """Break down agreement performance by direction (LONG vs SHORT)."""
    result = {}
    for direction in ("LONG", "SHORT"):
        dir_picks = [p for p in closed if p["direction"] == direction]
        low = [p for p in dir_picks if p["_sys_agree"] <= 3]
        med = [p for p in dir_picks if 4 <= p["_sys_agree"] <= 14]
        high = [p for p in dir_picks if p["_sys_agree"] >= 15]
        result[direction] = {
            "low_agreement": compute_stats(low),
            "medium_agreement": compute_stats(med),
            "high_agreement": compute_stats(high),
            "total": compute_stats(dir_picks),
        }
    return result


def generate_insights(by_level, best_pairs, best_combos, direction_breakdown):
    """Generate human-readable TLDR insights."""
    lines = []

    # Agreement level insight
    levels = list(by_level.items())
    if len(levels) >= 2:
        solo = by_level.get("1_system", {})
        multi = by_level.get("15_plus", {}) or by_level.get("8_14_systems", {})
        if solo.get("trades") and multi.get("trades"):
            lines.append(
                f"Solo-system picks: {solo['wr']}% WR ({solo['trades']} trades). "
                f"High-agreement (15+ systems): {multi['wr']}% WR ({multi['trades']} trades)."
            )

    # Best strategy pair
    if best_pairs:
        bp = best_pairs[0]
        s1, s2 = bp["pair"]
        lines.append(
            f"Best strategy pair: {s1} + {s2} — "
            f"{bp['wr']}% WR, {bp['avg_pnl']:+.2f}% avg PnL ({bp['trades']} trades)."
        )

    # Best system combo
    if best_combos:
        bc = best_combos[0]
        lines.append(
            f"Best system combo: {bc['combo'][0]} + {bc['combo'][1]} — "
            f"{bc['wr']}% WR ({bc['trades']} trades)."
        )

    # Direction insight
    for d in ("LONG", "SHORT"):
        db = direction_breakdown.get(d, {})
        hi = db.get("high_agreement", {})
        lo = db.get("low_agreement", {})
        if hi.get("trades", 0) >= 5 and lo.get("trades", 0) >= 5:
            diff = hi["wr"] - lo["wr"]
            if abs(diff) > 3:
                lines.append(
                    f"{d}: High agreement {hi['wr']}% WR vs low agreement {lo['wr']}% WR "
                    f"({diff:+.1f}pp boost)."
                )

    return " ".join(lines) if lines else "Insufficient data for consensus insights."


def main():
    print("Loading dashboard payload...")
    data = load_payload()
    picks = data.get("picks", {})
    closed_raw = picks.get("recent_closed", [])

    # Filter to valid closed trades
    closed = [p for p in closed_raw if is_valid_closed(p)]
    print(f"Valid closed picks: {len(closed)} (from {len(closed_raw)} raw)")

    # 1. Agreement level performance
    print("Computing agreement level performance...")
    by_level = build_agreement_levels(closed)
    for label, stats in by_level.items():
        print(f"  {label}: {stats['trades']} trades, {stats['wr']}% WR, {stats['pnl']:+.2f} PnL")

    # 2. Strategy pairs
    print("Finding profitable strategy pairs...")
    best_pairs = find_strategy_pairs(closed, min_trades=3)
    print(f"  Found {len(best_pairs)} qualifying strategy pairs")
    worst_pairs = sorted(best_pairs, key=lambda x: (x["wr"], x["pnl"]))[:20]

    # 3. System combos
    print("Finding profitable system combos...")
    best_combos = find_system_combos(closed, min_trades=10)
    print(f"  Found {len(best_combos)} qualifying system combos")
    worst_combos = sorted(best_combos, key=lambda x: (x["wr"], x["pnl"]))[:20]

    # 4. Direction breakdown
    print("Computing direction breakdown...")
    direction_breakdown = find_direction_breakdown(closed)

    # 5. Generate TLDR
    tldr = generate_insights(by_level, best_pairs[:20], best_combos[:20], direction_breakdown)
    print(f"\nTLDR: {tldr}")

    # 6. Build output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed_analyzed": len(closed),
        "by_agreement_level": by_level,
        "direction_breakdown": direction_breakdown,
        "best_strategy_pairs": best_pairs[:30],
        "worst_strategy_pairs": worst_pairs[:20],
        "best_system_combos": best_combos[:30],
        "worst_system_combos": worst_combos[:20],
        "tldr": tldr,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT}")


if __name__ == "__main__":
    main()
