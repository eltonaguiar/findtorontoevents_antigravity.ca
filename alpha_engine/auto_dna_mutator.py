#!/usr/bin/env python3
"""
Auto DNA Mutator — Unified Mutation Engine for Alpha Engine
============================================================
Continuously monitors strategy performance and automatically creates
mutations for BOTH super losers AND super winners.

Super Losers  → INVERSE mutations (flip direction)
Super Winners → AMPLIFICATION mutations (tighter/wider/faster/aggressive)

Mutations are tracked, auto-promoted if they work, auto-killed if they don't.
Follows the "mutate before kill" rule — always try DNA mutation before
giving up on any strategy.

Standalone runnable:
  python alpha_engine/auto_dna_mutator.py
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
MUTATION_PICKS_PATH = BASE / "alpha_engine" / "data" / "mutation_picks.json"
MUTATION_TRACKER_PATH = BASE / "alpha_engine" / "data" / "dna_mutation_tracker.json"
MUTATION_REPORT_PATH = BASE / "alpha_engine" / "data" / "dna_mutation_report.json"
CLOSED_PICKS_PATH = BASE / "alpha_engine" / "data" / "closed_picks.json"

# ── Thresholds ─────────────────────────────────────────────────────
# Super losers: consistent underperformers worth inverting
LOSER_MIN_TRADES = 10
LOSER_MAX_WR = 35.0        # % — below this = super loser
LOSER_MAX_PNL = -10.0       # % — total PnL worse than this

# Super winners: high performers worth amplifying
WINNER_MIN_TRADES = 10
WINNER_MIN_WR = 60.0        # % — above this = super winner
WINNER_MIN_PNL = 10.0        # % — total PnL better than this

# Mutation settings
MAX_MUTATION_PICKS = 50      # cap per cycle to avoid flooding
MUTATION_CONFIDENCE_LOW = 0.55
MUTATION_CONFIDENCE_HIGH = 0.70

# Auto-kill / auto-promote rules
AUTO_KILL_MIN_TRADES = 5
AUTO_KILL_WR = 35.0          # % — kill mutation below this WR
AUTO_KILL_PNL = -5.0         # % — kill mutation below this PnL
AUTO_PROMOTE_WR = 55.0       # % — promote above this
AUTO_PROMOTE_PNL = 5.0       # % — promote above this

# ── Mutation Definitions ───────────────────────────────────────────
LOSER_MUTATIONS = {
    "inverse":      {"flip": True,  "tp_mult": 1.0, "sl_mult": 1.0, "hold_mult": 1.0},
    "inverse_tight": {"flip": True,  "tp_mult": 0.7, "sl_mult": 0.7, "hold_mult": 1.0},
    "inverse_wide":  {"flip": True,  "tp_mult": 1.5, "sl_mult": 1.5, "hold_mult": 1.0},
}

WINNER_MUTATIONS = {
    "tight":      {"flip": False, "tp_mult": 0.7,  "sl_mult": 0.7, "hold_mult": 1.0},
    "wide":       {"flip": False, "tp_mult": 1.5,  "sl_mult": 1.3, "hold_mult": 1.0},
    "fast":       {"flip": False, "tp_mult": 1.0,  "sl_mult": 1.0, "hold_mult": 0.5},
    "slow":       {"flip": False, "tp_mult": 1.0,  "sl_mult": 1.0, "hold_mult": 2.0},
    "aggressive": {"flip": False, "tp_mult": 2.0,  "sl_mult": 1.0, "hold_mult": 1.0},
}


# ════════════════════════════════════════════════════════════════════
# DATA LOADING
# ════════════════════════════════════════════════════════════════════

def load_closed_picks() -> list:
    """Load closed picks from dashboard payload (primary) or closed_picks.json (fallback)."""
    # Try dashboard payload first
    if DASHBOARD_PAYLOAD.exists():
        try:
            with open(DASHBOARD_PAYLOAD, "r", encoding="utf-8") as f:
                data = json.load(f)
            picks = data.get("picks", {}).get("recent_closed", [])
            if picks:
                print(f"[DATA] Loaded {len(picks)} closed picks from dashboard payload")
                return picks
        except Exception as e:
            print(f"[WARN] Failed to load dashboard payload: {e}")

    # Fallback to closed_picks.json
    if CLOSED_PICKS_PATH.exists():
        try:
            with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
                picks = json.load(f)
            print(f"[DATA] Loaded {len(picks)} closed picks from closed_picks.json")
            return picks
        except Exception as e:
            print(f"[WARN] Failed to load closed_picks.json: {e}")

    print("[WARN] No closed picks data found")
    return []


def load_active_picks() -> list:
    """Load current active picks."""
    if not ACTIVE_PICKS_PATH.exists():
        print("[WARN] No active_picks.json found")
        return []
    try:
        with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[DATA] Loaded {len(data)} active picks")
        return data
    except Exception as e:
        print(f"[WARN] Failed to load active picks: {e}")
        return []


def load_mutation_tracker() -> dict:
    """Load existing mutation tracker or create empty one."""
    if MUTATION_TRACKER_PATH.exists():
        try:
            with open(MUTATION_TRACKER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mutation_stats": {},
        "auto_kill_rules": {
            "min_trades_before_eval": AUTO_KILL_MIN_TRADES,
            "kill_wr_threshold": AUTO_KILL_WR,
            "kill_pnl_threshold": AUTO_KILL_PNL,
            "promote_wr_threshold": AUTO_PROMOTE_WR,
            "promote_pnl_threshold": AUTO_PROMOTE_PNL,
        },
        "killed_mutations": [],
        "promoted_mutations": [],
    }


# ════════════════════════════════════════════════════════════════════
# STRATEGY ANALYSIS
# ════════════════════════════════════════════════════════════════════

def group_by_strategy(picks: list) -> dict:
    """Group picks by strategy name."""
    groups = defaultdict(list)
    for p in picks:
        strat = p.get("strategy", "unknown")
        groups[strat].append(p)
    return dict(groups)


def compute_stats(picks: list) -> dict:
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


def identify_super_losers(all_stats: dict) -> dict:
    """Find strategies with WR < 35% and PnL < -10% with 10+ trades."""
    losers = {}
    for strat, stats in all_stats.items():
        # Skip strategies that are already mutations
        if _is_mutation_strategy(strat):
            continue
        if (stats["trades"] >= LOSER_MIN_TRADES
                and stats["wr"] < LOSER_MAX_WR
                and stats["pnl"] < LOSER_MAX_PNL):
            losers[strat] = stats
    return losers


def identify_super_winners(all_stats: dict) -> dict:
    """Find strategies with WR > 60% and PnL > +10% with 10+ trades."""
    winners = {}
    for strat, stats in all_stats.items():
        # Skip strategies that are already mutations
        if _is_mutation_strategy(strat):
            continue
        if (stats["trades"] >= WINNER_MIN_TRADES
                and stats["wr"] > WINNER_MIN_WR
                and stats["pnl"] > WINNER_MIN_PNL):
            winners[strat] = stats
    return winners


def _is_mutation_strategy(name: str) -> bool:
    """Check if a strategy name is already a mutation (avoid recursive mutations)."""
    mutation_suffixes = ("_tight", "_wide", "_fast", "_slow", "_aggressive")
    if name.startswith("inverse_"):
        return True
    for suffix in mutation_suffixes:
        if name.endswith(suffix):
            return True
    if "auto_dna_mutation" in name:
        return True
    return False


# ════════════════════════════════════════════════════════════════════
# DIRECTION HELPERS
# ════════════════════════════════════════════════════════════════════

def flip_direction(direction: str) -> str:
    """Flip LONG to SHORT and vice versa."""
    d = direction.upper().strip()
    if d in ("LONG", "BUY"):
        return "SHORT"
    elif d in ("SHORT", "SELL"):
        return "LONG"
    return d


# ════════════════════════════════════════════════════════════════════
# MUTATION CREATION
# ════════════════════════════════════════════════════════════════════

def create_mutated_pick(pick: dict, mutation_name: str, mutation_config: dict,
                        parent_strategy: str, mutation_category: str) -> dict:
    """
    Create a mutated version of an active pick.

    mutation_config keys:
      flip       — bool: reverse direction
      tp_mult    — float: multiply TP distance
      sl_mult    — float: multiply SL distance
      hold_mult  — float: multiply max hold time
    """
    mut = copy.deepcopy(pick)

    do_flip = mutation_config["flip"]
    tp_mult = mutation_config["tp_mult"]
    sl_mult = mutation_config["sl_mult"]
    hold_mult = mutation_config["hold_mult"]

    # Build mutation strategy name
    if do_flip:
        mut_strategy = f"inverse_{parent_strategy}" if mutation_name == "inverse" else f"inverse_{parent_strategy}_{mutation_name.replace('inverse_', '')}"
    else:
        mut_strategy = f"{parent_strategy}_{mutation_name}"

    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    orig_direction = pick.get("signal_type", pick.get("direction", "BUY")).upper()

    # Determine new direction
    new_direction = flip_direction(orig_direction) if do_flip else orig_direction

    # Compute new TP/SL
    if orig_direction in ("BUY", "LONG"):
        orig_tp_dist = tp - entry if tp and entry else 0
        orig_sl_dist = entry - sl if sl and entry else 0

        if do_flip:
            # Flipping to SHORT: TP below, SL above
            new_tp = entry - (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 - 0.05 * tp_mult)
            new_sl = entry + (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 + 0.025 * sl_mult)
        else:
            # Same direction LONG: adjust distances
            new_tp = entry + (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 + 0.05 * tp_mult)
            new_sl = entry - (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 - 0.025 * sl_mult)
    else:
        orig_tp_dist = entry - tp if tp and entry else 0
        orig_sl_dist = sl - entry if sl and entry else 0

        if do_flip:
            # Flipping to LONG: TP above, SL below
            new_tp = entry + (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 + 0.05 * tp_mult)
            new_sl = entry - (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 - 0.025 * sl_mult)
        else:
            # Same direction SHORT: adjust distances
            new_tp = entry - (orig_tp_dist * tp_mult) if orig_tp_dist else entry * (1 - 0.05 * tp_mult)
            new_sl = entry + (orig_sl_dist * sl_mult) if orig_sl_dist else entry * (1 + 0.025 * sl_mult)

    # Adjust hold time
    orig_hold = pick.get("hold_days", 3)
    new_hold = max(0.25, orig_hold * hold_mult)

    # Confidence: slightly lower than parent since experimental
    parent_conf = pick.get("confidence", 0.6)
    mut_conf = round(max(MUTATION_CONFIDENCE_LOW,
                         min(MUTATION_CONFIDENCE_HIGH, parent_conf * 0.85)), 3)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Update pick fields
    mut["id"] = f"{mut_strategy}::{pick.get('symbol', 'UNK')}::{date_str}"
    mut["strategy"] = mut_strategy
    mut["signal_type"] = new_direction
    if "direction" in mut:
        mut["direction"] = new_direction
    mut["take_profit"] = round(new_tp, 8)
    mut["stop_loss"] = round(new_sl, 8)
    mut["confidence"] = mut_conf
    mut["hold_days"] = round(new_hold, 2)
    mut["source_system"] = "auto_dna_mutation"
    mut["mutation_type"] = mutation_name
    mut["parent_strategy"] = parent_strategy
    mut["mutation_category"] = mutation_category  # "loser_inverse" or "winner_amplify"
    mut["status"] = "OPEN"
    mut["exit_price"] = None
    mut["exit_date"] = None
    mut["exit_reason"] = None
    mut["pnl_pct"] = None
    mut["pnl_dollar"] = None
    mut["scan_timestamp"] = now_str
    mut["forward_validated"] = False
    mut["forward_status"] = f"dna_mutation({mutation_name}) of {parent_strategy}"

    # Mutation metadata
    mut["dna_mutation"] = {
        "parent_strategy": parent_strategy,
        "mutation_name": mutation_name,
        "mutation_category": mutation_category,
        "flip_direction": do_flip,
        "tp_multiplier": tp_mult,
        "sl_multiplier": sl_mult,
        "hold_multiplier": hold_mult,
        "original_direction": orig_direction,
        "mutated_direction": new_direction,
        "created_at": now_str,
    }

    # Also update gross_tp / net_tp if present
    if "gross_tp" in mut:
        mut["gross_tp"] = mut["take_profit"]
    if "net_tp" in mut:
        cost = pick.get("transaction_cost_pct", 0.001)
        if new_direction in ("BUY", "LONG"):
            mut["net_tp"] = round(new_tp * (1 - cost), 8)
        else:
            mut["net_tp"] = round(new_tp * (1 + cost), 8)

    # Reset tracking fields
    mut["high_water_mark"] = None
    mut["mfe"] = None
    mut["mae"] = None
    mut["current_price"] = None
    mut["unrealized_pnl_pct"] = None

    return mut


# ════════════════════════════════════════════════════════════════════
# MUTATION TRACKING & LIFECYCLE
# ════════════════════════════════════════════════════════════════════

def update_mutation_stats(tracker: dict, closed_picks: list) -> dict:
    """
    Update mutation_stats from closed picks that are mutations.
    Evaluate for auto-kill or auto-promote.
    """
    mutation_stats = tracker.get("mutation_stats", {})
    killed = tracker.get("killed_mutations", [])
    promoted = tracker.get("promoted_mutations", [])
    killed_set = set(killed)

    # Find closed picks that are mutations
    for pick in closed_picks:
        strat = pick.get("strategy", "")
        source = pick.get("source_system", "")

        # Match mutations by source_system or by naming convention
        is_mutation = (source == "auto_dna_mutation"
                       or source == "inverse_loser_mutation"
                       or _is_mutation_strategy(strat))

        if not is_mutation:
            continue

        pnl = pick.get("pnl_pct")
        status = pick.get("status", "")
        if pnl is None or status not in ("WON", "LOST", "STOPPED"):
            continue

        if strat not in mutation_stats:
            mutation_stats[strat] = {
                "trades": 0, "wins": 0, "losses": 0,
                "pnl": 0.0, "status": "ACTIVE",
                "first_seen": pick.get("entry_date", ""),
                "parent_strategy": pick.get("parent_strategy", strat),
            }

        entry = mutation_stats[strat]
        entry["trades"] += 1
        if status == "WON" or pnl > 0:
            entry["wins"] += 1
        else:
            entry["losses"] += 1
        entry["pnl"] = round(entry["pnl"] + pnl, 4)

    # Evaluate auto-kill / auto-promote
    rules = tracker.get("auto_kill_rules", {})
    min_trades = rules.get("min_trades_before_eval", AUTO_KILL_MIN_TRADES)
    kill_wr = rules.get("kill_wr_threshold", AUTO_KILL_WR)
    kill_pnl = rules.get("kill_pnl_threshold", AUTO_KILL_PNL)
    promote_wr = rules.get("promote_wr_threshold", AUTO_PROMOTE_WR)
    promote_pnl = rules.get("promote_pnl_threshold", AUTO_PROMOTE_PNL)

    for strat, entry in mutation_stats.items():
        if entry["status"] not in ("ACTIVE",):
            continue
        if entry["trades"] < min_trades:
            continue

        wr = (entry["wins"] / entry["trades"] * 100) if entry["trades"] > 0 else 0

        # Auto-kill check
        if wr < kill_wr or entry["pnl"] < kill_pnl:
            entry["status"] = "KILLED"
            entry["killed_at"] = datetime.now(timezone.utc).isoformat()
            entry["kill_reason"] = f"WR={wr:.1f}% PnL={entry['pnl']:+.2f}% after {entry['trades']} trades"
            if strat not in killed_set:
                killed.append(strat)
                killed_set.add(strat)
            print(f"  [KILL] {strat}: WR={wr:.1f}%, PnL={entry['pnl']:+.2f}% -- auto-killed")

        # Auto-promote check
        elif wr >= promote_wr and entry["pnl"] >= promote_pnl:
            entry["status"] = "PROMOTED"
            entry["promoted_at"] = datetime.now(timezone.utc).isoformat()
            entry["promote_reason"] = f"WR={wr:.1f}% PnL={entry['pnl']:+.2f}% after {entry['trades']} trades"
            if strat not in promoted:
                promoted.append(strat)
            print(f"  [PROMOTE] {strat}: WR={wr:.1f}%, PnL={entry['pnl']:+.2f}% -- promoted!")

    tracker["mutation_stats"] = mutation_stats
    tracker["killed_mutations"] = killed
    tracker["promoted_mutations"] = promoted
    return tracker


def filter_killed_mutations(picks: list, tracker: dict) -> list:
    """Remove picks from killed mutation strategies."""
    killed_set = set(tracker.get("killed_mutations", []))
    if not killed_set:
        return picks

    filtered = []
    removed = 0
    for p in picks:
        if p.get("strategy", "") in killed_set:
            removed += 1
        else:
            filtered.append(p)

    if removed:
        print(f"  [CLEANUP] Removed {removed} picks from killed mutation strategies")
    return filtered


# ════════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ════════════════════════════════════════════════════════════════════

def run_auto_dna_mutator():
    """Main entry point: identify losers + winners, create mutations, track lifecycle."""
    print("=" * 70)
    print("  AUTO DNA MUTATOR ENGINE")
    print("  Unified mutation system for losers (inverse) + winners (amplify)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    print()

    # ── 1. Load data ───────────────────────────────────────────────
    try:
        closed_picks = load_closed_picks()
    except Exception as e:
        print(f"[ERROR] Failed to load closed picks: {e}")
        closed_picks = []

    try:
        active_picks = load_active_picks()
    except Exception as e:
        print(f"[ERROR] Failed to load active picks: {e}")
        active_picks = []

    tracker = load_mutation_tracker()

    if not closed_picks:
        print("[INFO] No closed picks available. Nothing to analyze.")
        _save_empty_report(tracker)
        return

    # ── 2. Group by strategy and compute stats ─────────────────────
    groups = group_by_strategy(closed_picks)
    print(f"\n[ANALYSIS] Found {len(groups)} unique strategies in closed picks\n")

    all_stats = {}
    for strat, picks in groups.items():
        all_stats[strat] = compute_stats(picks)

    # ── 3. Identify super losers and super winners ─────────────────
    losers = identify_super_losers(all_stats)
    winners = identify_super_winners(all_stats)

    _print_category("SUPER LOSERS", losers,
                    f"WR < {LOSER_MAX_WR}%, PnL < {LOSER_MAX_PNL}%, trades >= {LOSER_MIN_TRADES}")
    _print_category("SUPER WINNERS", winners,
                    f"WR > {WINNER_MIN_WR}%, PnL > +{WINNER_MIN_PNL}%, trades >= {WINNER_MIN_TRADES}")

    if not losers and not winners:
        print("[INFO] No super losers or super winners found. No mutations needed.")
        # Still update tracker for existing mutations
        tracker = update_mutation_stats(tracker, closed_picks)
        _save_tracker(tracker)
        _save_empty_report(tracker)
        return

    # ── 4. Update mutation tracker from closed picks ───────────────
    print(f"\n{'='*70}")
    print(f"  MUTATION LIFECYCLE CHECK")
    print(f"{'='*70}")
    tracker = update_mutation_stats(tracker, closed_picks)

    # ── 5. Generate mutation picks from active picks ───────────────
    print(f"\n{'='*70}")
    print(f"  GENERATING MUTATION PICKS")
    print(f"{'='*70}")

    killed_set = set(tracker.get("killed_mutations", []))
    loser_names = set(losers.keys())
    winner_names = set(winners.keys())
    mutation_picks = []

    # Collect existing mutation IDs to avoid duplicates
    existing_ids = set()
    if MUTATION_PICKS_PATH.exists():
        try:
            with open(MUTATION_PICKS_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_ids = {p.get("id", "") for p in existing}
        except Exception:
            pass

    # Also check active picks for existing mutations
    active_ids = {p.get("id", "") for p in active_picks}

    for pick in active_picks:
        strat = pick.get("strategy", "")

        # Skip picks that are already mutations
        if _is_mutation_strategy(strat):
            continue

        # Process loser strategies -> inverse mutations
        if strat in loser_names:
            for mut_name, mut_config in LOSER_MUTATIONS.items():
                mut_strat_name = f"inverse_{strat}" if mut_name == "inverse" else f"inverse_{strat}_{mut_name.replace('inverse_', '')}"
                if mut_strat_name in killed_set:
                    continue
                try:
                    mut_pick = create_mutated_pick(pick, mut_name, mut_config, strat, "loser_inverse")
                    if mut_pick["id"] not in existing_ids and mut_pick["id"] not in active_ids:
                        mutation_picks.append(mut_pick)
                except Exception as e:
                    print(f"  [WARN] Failed to create {mut_name} mutation for {strat}: {e}")

        # Process winner strategies -> amplification mutations
        if strat in winner_names:
            for mut_name, mut_config in WINNER_MUTATIONS.items():
                mut_strat_name = f"{strat}_{mut_name}"
                if mut_strat_name in killed_set:
                    continue
                try:
                    mut_pick = create_mutated_pick(pick, mut_name, mut_config, strat, "winner_amplify")
                    if mut_pick["id"] not in existing_ids and mut_pick["id"] not in active_ids:
                        mutation_picks.append(mut_pick)
                except Exception as e:
                    print(f"  [WARN] Failed to create {mut_name} mutation for {strat}: {e}")

    # ── 6. Cap mutations ───────────────────────────────────────────
    if len(mutation_picks) > MAX_MUTATION_PICKS:
        print(f"\n  [CAP] {len(mutation_picks)} mutations generated, capping to {MAX_MUTATION_PICKS}")
        # Prioritize: promoted parents first, then by parent PnL
        def _sort_key(p):
            parent = p.get("parent_strategy", "")
            stats = all_stats.get(parent, {})
            # Inverse mutations of worst losers first (highest potential)
            if p.get("mutation_category") == "loser_inverse":
                return (0, -abs(stats.get("pnl", 0)))
            # Winner amplifications by best PnL
            return (1, -stats.get("pnl", 0))

        mutation_picks.sort(key=_sort_key)
        mutation_picks = mutation_picks[:MAX_MUTATION_PICKS]

    # Remove picks from killed strategies
    mutation_picks = filter_killed_mutations(mutation_picks, tracker)

    # ── 7. Print summary of generated mutations ────────────────────
    if mutation_picks:
        inverse_count = sum(1 for p in mutation_picks if p.get("mutation_category") == "loser_inverse")
        amplify_count = sum(1 for p in mutation_picks if p.get("mutation_category") == "winner_amplify")
        print(f"\n  Generated {len(mutation_picks)} mutation picks:")
        print(f"    Inverse (from losers):      {inverse_count}")
        print(f"    Amplification (from winners): {amplify_count}")

        strats_generated = defaultdict(int)
        for p in mutation_picks:
            strats_generated[p["strategy"]] += 1
        for s in sorted(strats_generated.keys()):
            print(f"    - {s}: {strats_generated[s]} picks")
    else:
        print("\n  No new mutation picks generated this cycle.")

    # ── 8. Merge mutations into active picks ───────────────────────
    merged_count = 0
    if mutation_picks:
        try:
            # Load fresh active picks (in case updated during our run)
            if ACTIVE_PICKS_PATH.exists():
                with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
                    current_active = json.load(f)
            else:
                current_active = []

            current_ids = {p.get("id", "") for p in current_active}

            for mp in mutation_picks:
                if mp["id"] not in current_ids:
                    current_active.append(mp)
                    merged_count += 1

            ACTIVE_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(ACTIVE_PICKS_PATH, "w", encoding="utf-8") as f:
                json.dump(current_active, f, indent=2, default=str)
            print(f"\n  [MERGED] {merged_count} mutation picks into active_picks.json (total: {len(current_active)})")
        except Exception as e:
            print(f"  [ERROR] Failed to merge into active_picks.json: {e}")
            # Save separately as fallback
            merged_count = 0

    # ── 9. Save mutation picks separately (backup) ─────────────────
    try:
        MUTATION_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MUTATION_PICKS_PATH, "w", encoding="utf-8") as f:
            json.dump(mutation_picks, f, indent=2, default=str)
        print(f"  [SAVED] {len(mutation_picks)} mutation picks -> {MUTATION_PICKS_PATH}")
    except Exception as e:
        print(f"  [ERROR] Failed to save mutation picks: {e}")

    # ── 10. Save tracker ───────────────────────────────────────────
    _save_tracker(tracker)

    # ── 11. Save report ────────────────────────────────────────────
    _save_report(losers, winners, all_stats, groups, mutation_picks, tracker, merged_count)

    # ── 12. Final summary ──────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  AUTO DNA MUTATOR - FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Super losers identified:     {len(losers)}")
    print(f"  Super winners identified:    {len(winners)}")
    print(f"  Mutation picks generated:    {len(mutation_picks)}")
    print(f"  Merged into active picks:    {merged_count}")
    print(f"  Killed mutations (lifetime): {len(tracker.get('killed_mutations', []))}")
    print(f"  Promoted mutations:          {len(tracker.get('promoted_mutations', []))}")
    print(f"  Tracked mutation strategies: {len(tracker.get('mutation_stats', {}))}")
    print(f"\n  Files written:")
    print(f"    - {MUTATION_PICKS_PATH}")
    print(f"    - {MUTATION_TRACKER_PATH}")
    print(f"    - {MUTATION_REPORT_PATH}")
    print(f"    - {ACTIVE_PICKS_PATH} (merged)")
    print()

    return {
        "losers": len(losers),
        "winners": len(winners),
        "mutations_generated": len(mutation_picks),
        "merged": merged_count,
        "killed": len(tracker.get("killed_mutations", [])),
        "promoted": len(tracker.get("promoted_mutations", [])),
    }


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _print_category(title: str, strategies: dict, criteria: str):
    """Print a formatted category table."""
    print(f"{'='*70}")
    print(f"  {title} ({criteria})")
    print(f"{'='*70}")
    if not strategies:
        print(f"  (none found)")
        print()
        return

    print(f"  {'Strategy':<35} {'Trades':>7} {'WR%':>7} {'Total PnL':>10}")
    print(f"  {'-'*35} {'-'*7} {'-'*7} {'-'*10}")
    for strat, stats in sorted(strategies.items(), key=lambda x: x[1]["pnl"]):
        print(f"  {strat:<35} {stats['trades']:>7} {stats['wr']:>6.1f}% {stats['pnl']:>+9.1f}%")
    print()


def _save_tracker(tracker: dict):
    """Save mutation tracker to disk."""
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        MUTATION_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MUTATION_TRACKER_PATH, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2, default=str)
        print(f"  [SAVED] Mutation tracker -> {MUTATION_TRACKER_PATH}")
    except Exception as e:
        print(f"  [ERROR] Failed to save tracker: {e}")


def _save_empty_report(tracker: dict):
    """Save an empty report when no mutations are needed."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "super_losers": [],
        "super_winners": [],
        "mutations_generated": 0,
        "tracker_summary": {
            "tracked_mutations": len(tracker.get("mutation_stats", {})),
            "killed": len(tracker.get("killed_mutations", [])),
            "promoted": len(tracker.get("promoted_mutations", [])),
        },
    }
    try:
        MUTATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MUTATION_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    except Exception:
        pass


def _save_report(losers, winners, all_stats, groups, mutation_picks, tracker, merged_count):
    """Save a detailed mutation report."""
    loser_entries = []
    for strat, stats in sorted(losers.items(), key=lambda x: x[1]["pnl"]):
        loser_entries.append({
            "strategy": strat,
            "stats": stats,
            "mutations_created": [
                f"inverse_{strat}",
                f"inverse_{strat}_tight",
                f"inverse_{strat}_wide",
            ],
        })

    winner_entries = []
    for strat, stats in sorted(winners.items(), key=lambda x: -x[1]["pnl"]):
        winner_entries.append({
            "strategy": strat,
            "stats": stats,
            "mutations_created": [
                f"{strat}_tight",
                f"{strat}_wide",
                f"{strat}_fast",
                f"{strat}_slow",
                f"{strat}_aggressive",
            ],
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "super_losers": loser_entries,
        "super_winners": winner_entries,
        "mutations_generated": len(mutation_picks),
        "merged_into_active": merged_count,
        "tracker_summary": {
            "tracked_mutations": len(tracker.get("mutation_stats", {})),
            "killed": len(tracker.get("killed_mutations", [])),
            "promoted": len(tracker.get("promoted_mutations", [])),
            "active": sum(1 for s in tracker.get("mutation_stats", {}).values()
                         if s.get("status") == "ACTIVE"),
        },
        "mutation_picks_by_category": {
            "loser_inverse": sum(1 for p in mutation_picks
                                if p.get("mutation_category") == "loser_inverse"),
            "winner_amplify": sum(1 for p in mutation_picks
                                 if p.get("mutation_category") == "winner_amplify"),
        },
    }

    try:
        MUTATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MUTATION_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  [SAVED] Mutation report -> {MUTATION_REPORT_PATH}")
    except Exception as e:
        print(f"  [ERROR] Failed to save report: {e}")


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        result = run_auto_dna_mutator()
        if result:
            print(f"\n[DONE] Auto DNA Mutator completed successfully.")
        else:
            print(f"\n[DONE] Auto DNA Mutator completed (no mutations this cycle).")
    except Exception as e:
        print(f"\n[FATAL] Auto DNA Mutator crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
