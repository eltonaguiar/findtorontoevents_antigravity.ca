#!/usr/bin/env python3
"""
DNA Mutation Engine -- Automatic Strategy Variant Generator
============================================================
Identifies underperforming strategies and generates mutated variants
to salvage alpha. Follows the "mutate before kill" rule -- always try
DNA mutation before giving up on any strategy.

Mutation types:
  - inverse: Flip BUY->SELL, swap TP/SL
  - tighter_stops: Reduce TP/SL distance (faster exits)
  - wider_stops: Increase TP/SL distance (more room)
  - regime_gate: Only allow picks matching current regime
  - timeframe_shift: Move to higher/lower timeframe
  - confidence_threshold: Only allow high-confidence picks
  - crossover: Blend strong strategy params into weak strategy's inverse

Usage:
  python alpha_engine/dna_mutation_engine.py              # Generate mutations
  python alpha_engine/dna_mutation_engine.py --evaluate    # Evaluate existing mutations
  python alpha_engine/dna_mutation_engine.py --report      # Print mutation report

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# -- Windows UTF-8 fix ---------------------------------------------------------
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# -- Paths ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# -- Thresholds ----------------------------------------------------------------
CANDIDATE_MIN_TRADES = 10
CANDIDATE_MAX_WR = 0.40        # Below 40% WR = mutation candidate
DONOR_MIN_TRADES = 10
DONOR_MIN_WR = 0.55             # Above 55% WR = donor DNA for crossover
PROMOTE_MIN_TRADES = 10
PROMOTE_MIN_WR = 0.50           # Above 50% WR on 10+ trades = promote
KILL_MIN_TRADES = 10
KILL_MAX_WR = 0.35              # Below 35% WR on 10+ trades = kill mutation

# Timeframe mapping for shifts
_TIMEFRAME_UP = {
    "1m": "5m", "5m": "15m", "15m": "1h", "1h": "4h",
    "4h": "1d", "1d": "1w",
}
_TIMEFRAME_DOWN = {v: k for k, v in _TIMEFRAME_UP.items()}


# ==============================================================================
# DATA LOADING
# ==============================================================================

def _load_json(path: str | Path) -> list | dict:
    """Load a JSON file, returning [] on any failure."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[DNA] Warning: failed to load {p.name}: {e}")
        return []


def _save_json(path: str | Path, data: dict | list) -> None:
    """Atomically write JSON with pretty-print."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(p)


# ==============================================================================
# STRATEGY ANALYSIS
# ==============================================================================

def _compute_strategy_stats(picks: list) -> dict[str, dict]:
    """Group closed picks by strategy and compute WR, PnL, avg confidence."""
    groups: dict[str, list] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy", "unknown")
        groups[strat].append(p)

    stats = {}
    for strat, trades in groups.items():
        wins = sum(1 for t in trades if t.get("status") == "WON" or t.get("pnl_pct", 0) > 0)
        total = len(trades)
        wr = wins / total if total > 0 else 0.0
        pnl_values = [t.get("pnl_pct", 0) or 0 for t in trades]
        avg_pnl = statistics.mean(pnl_values) if pnl_values else 0.0
        total_pnl = sum(pnl_values)
        confidences = [t.get("confidence", 0.5) or 0.5 for t in trades]
        avg_conf = statistics.mean(confidences)

        # Extract typical TP/SL distances for crossover
        tp_dists = []
        sl_dists = []
        for t in trades:
            entry = t.get("entry_price", 0) or 0
            tp = t.get("take_profit", 0) or 0
            sl = t.get("stop_loss", 0) or 0
            if entry > 0 and tp > 0:
                tp_dists.append(abs(tp - entry) / entry)
            if entry > 0 and sl > 0:
                sl_dists.append(abs(sl - entry) / entry)

        stats[strat] = {
            "strategy": strat,
            "total_trades": total,
            "wins": wins,
            "win_rate": round(wr, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "total_pnl_pct": round(total_pnl, 4),
            "avg_confidence": round(avg_conf, 4),
            "avg_tp_dist": round(statistics.mean(tp_dists), 6) if tp_dists else 0.03,
            "avg_sl_dist": round(statistics.mean(sl_dists), 6) if sl_dists else 0.02,
            "trades": trades,
        }
    return stats


# ==============================================================================
# CANDIDATE IDENTIFICATION
# ==============================================================================

def identify_mutation_candidates(closed_picks_path: str = "data/closed_picks.json") -> dict:
    """
    Find strategies needing mutation (underperformers) and donor DNA (strong strategies).

    Returns:
        {
            "candidates": [{"strategy": ..., "win_rate": ..., ...}],
            "donors": [{"strategy": ..., "win_rate": ..., ...}],
            "stats": {strategy_name: {...}, ...}
        }
    """
    # Resolve relative path from alpha_engine dir
    path = Path(closed_picks_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    picks = _load_json(path)
    if not picks:
        print("[DNA] No closed picks found -- nothing to analyze")
        return {"candidates": [], "donors": [], "stats": {}}

    stats = _compute_strategy_stats(picks)

    candidates = []
    donors = []

    for strat, s in stats.items():
        # Skip already-mutated strategies from being re-mutated
        if "_mut_" in strat or strat.startswith("mut_"):
            continue

        if s["total_trades"] >= CANDIDATE_MIN_TRADES and s["win_rate"] < CANDIDATE_MAX_WR:
            candidates.append({
                "strategy": strat,
                "total_trades": s["total_trades"],
                "win_rate": s["win_rate"],
                "avg_pnl_pct": s["avg_pnl_pct"],
                "total_pnl_pct": s["total_pnl_pct"],
            })

        if s["total_trades"] >= DONOR_MIN_TRADES and s["win_rate"] >= DONOR_MIN_WR:
            donors.append({
                "strategy": strat,
                "total_trades": s["total_trades"],
                "win_rate": s["win_rate"],
                "avg_pnl_pct": s["avg_pnl_pct"],
                "avg_tp_dist": s["avg_tp_dist"],
                "avg_sl_dist": s["avg_sl_dist"],
            })

    # Sort: worst candidates first, best donors first
    candidates.sort(key=lambda x: x["win_rate"])
    donors.sort(key=lambda x: x["win_rate"], reverse=True)

    print(f"[DNA] Found {len(candidates)} mutation candidates (<{CANDIDATE_MAX_WR*100:.0f}% WR)")
    print(f"[DNA] Found {len(donors)} donor strategies (>{DONOR_MIN_WR*100:.0f}% WR)")

    return {"candidates": candidates, "donors": donors, "stats": stats}


# ==============================================================================
# MUTATION FUNCTIONS
# ==============================================================================

def inverse_mutation(pick: dict) -> dict:
    """Flip direction: BUY->SELL, swap TP/SL."""
    m = copy.deepcopy(pick)
    sig = m.get("signal_type", "BUY").upper()

    if sig in ("BUY", "LONG"):
        m["signal_type"] = "SELL"
    elif sig in ("SELL", "SHORT"):
        m["signal_type"] = "BUY"
    else:
        m["signal_type"] = "SELL" if sig == "BUY" else "BUY"

    # Swap TP and SL distances relative to entry
    entry = m.get("entry_price", 0) or 0
    tp = m.get("take_profit", 0) or 0
    sl = m.get("stop_loss", 0) or 0

    if entry > 0:
        tp_dist = abs(tp - entry)
        sl_dist = abs(sl - entry)

        if m["signal_type"] in ("BUY", "LONG"):
            m["take_profit"] = round(entry + tp_dist, 8)
            m["stop_loss"] = round(entry - sl_dist, 8)
        else:
            m["take_profit"] = round(entry - tp_dist, 8)
            m["stop_loss"] = round(entry + sl_dist, 8)

    m["mutation_type"] = "inverse"
    return m


def tighter_stops(pick: dict, factor: float = 0.6) -> dict:
    """Multiply TP/SL distance by factor (tighter exits)."""
    m = copy.deepcopy(pick)
    entry = m.get("entry_price", 0) or 0
    tp = m.get("take_profit", 0) or 0
    sl = m.get("stop_loss", 0) or 0

    if entry > 0:
        if tp > 0:
            tp_dist = (tp - entry)
            m["take_profit"] = round(entry + tp_dist * factor, 8)
        if sl > 0:
            sl_dist = (sl - entry)
            m["stop_loss"] = round(entry + sl_dist * factor, 8)

    m["mutation_type"] = "tighter_stops"
    return m


def wider_stops(pick: dict, factor: float = 1.5) -> dict:
    """Multiply TP/SL distance by factor (more room to breathe)."""
    m = copy.deepcopy(pick)
    entry = m.get("entry_price", 0) or 0
    tp = m.get("take_profit", 0) or 0
    sl = m.get("stop_loss", 0) or 0

    if entry > 0:
        if tp > 0:
            tp_dist = (tp - entry)
            m["take_profit"] = round(entry + tp_dist * factor, 8)
        if sl > 0:
            sl_dist = (sl - entry)
            m["stop_loss"] = round(entry + sl_dist * factor, 8)

    m["mutation_type"] = "wider_stops"
    return m


def regime_gate(pick: dict, regime: str = "") -> dict:
    """Only allow picks that match current market regime."""
    m = copy.deepcopy(pick)
    m["mutation_type"] = "regime_gate"
    m["required_regime"] = regime or m.get("regime_at_entry", "any")

    # If regime was specified and pick has regime info, check match
    if regime and m.get("regime_at_entry"):
        if m["regime_at_entry"] != regime:
            m["regime_blocked"] = True
        else:
            m["regime_blocked"] = False
    else:
        m["regime_blocked"] = False

    return m


def timeframe_shift(pick: dict, shift: str = "up") -> dict:
    """Move to higher or lower timeframe (1h->4h or 4h->1h)."""
    m = copy.deepcopy(pick)

    # Extract timeframe from extra_json if available
    extra = {}
    extra_raw = m.get("extra_json", "")
    if isinstance(extra_raw, str) and extra_raw:
        try:
            extra = json.loads(extra_raw)
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(extra_raw, dict):
        extra = extra_raw

    current_tf = extra.get("timeframe", m.get("timeframe", "1h"))

    if shift == "up":
        new_tf = _TIMEFRAME_UP.get(current_tf, current_tf)
    else:
        new_tf = _TIMEFRAME_DOWN.get(current_tf, current_tf)

    m["mutation_type"] = "timeframe_shift"
    m["mutation_timeframe"] = new_tf
    m["original_timeframe"] = current_tf

    if isinstance(extra_raw, str):
        extra["timeframe"] = new_tf
        m["extra_json"] = json.dumps(extra)
    else:
        m.setdefault("timeframe", new_tf)

    return m


def confidence_threshold(pick: dict, min_conf: float = 0.7) -> dict:
    """Only allow high-confidence picks through."""
    m = copy.deepcopy(pick)
    m["mutation_type"] = "confidence_threshold"
    m["min_confidence_required"] = min_conf

    current_conf = m.get("confidence", 0.5) or 0.5
    if current_conf < min_conf:
        m["confidence_blocked"] = True
    else:
        m["confidence_blocked"] = False

    return m


def crossover_mutation(weak_pick: dict, strong_strategy_params: dict) -> dict:
    """
    Crossover: take TP/SL distances from strong strategy,
    direction from weak strategy's inverse.
    """
    # First invert the weak pick
    m = inverse_mutation(weak_pick)
    m["mutation_type"] = "crossover"

    entry = m.get("entry_price", 0) or 0
    if entry <= 0:
        return m

    donor_tp_dist = strong_strategy_params.get("avg_tp_dist", 0.03)
    donor_sl_dist = strong_strategy_params.get("avg_sl_dist", 0.02)

    if m.get("signal_type") in ("BUY", "LONG"):
        m["take_profit"] = round(entry * (1 + donor_tp_dist), 8)
        m["stop_loss"] = round(entry * (1 - donor_sl_dist), 8)
    else:
        m["take_profit"] = round(entry * (1 - donor_tp_dist), 8)
        m["stop_loss"] = round(entry * (1 + donor_sl_dist), 8)

    m["crossover_donor"] = strong_strategy_params.get("strategy", "unknown")
    return m


# ==============================================================================
# MUTATION GENERATION
# ==============================================================================

def generate_mutations(closed_picks_path: str = "data/closed_picks.json") -> dict:
    """
    Main entry point. For each underperforming strategy, generate 3 mutation
    variants (inverse, tighter_stops, regime_gate). Save to data/dna_mutations.json.

    Returns the full mutation state dict.
    """
    result = identify_mutation_candidates(closed_picks_path)
    candidates = result["candidates"]
    donors = result["donors"]
    stats = result["stats"]

    # Load existing mutations to preserve history
    mutations_path = DATA_DIR / "dna_mutations.json"
    existing = _load_json(mutations_path)
    if isinstance(existing, dict):
        promoted = existing.get("promoted", [])
        killed = existing.get("killed", [])
        prev_mutations = existing.get("mutations", [])
    else:
        promoted = []
        killed = []
        prev_mutations = []

    # Track which mutations already exist (avoid duplicates)
    existing_keys = set()
    for m in prev_mutations:
        key = f"{m.get('parent', '')}::{m.get('type', '')}::gen{m.get('generation', 0)}"
        existing_keys.add(key)

    # Best donor for crossover mutations
    best_donor = donors[0] if donors else None

    new_mutations = []
    for cand in candidates:
        strat = cand["strategy"]
        gen = 1  # First generation

        # Check if this strategy already has mutations from a previous generation
        for pm in prev_mutations:
            if pm.get("parent") == strat:
                gen = max(gen, pm.get("generation", 1) + 1)

        # Mutation 1: Inverse
        key1 = f"{strat}::inverse::gen{gen}"
        if key1 not in existing_keys:
            new_mutations.append({
                "parent": strat,
                "type": "inverse",
                "generation": gen,
                "status": "active",
                "mutated_strategy_name": f"{strat}_mut_inverse_g{gen}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "parent_wr": cand["win_rate"],
                "parent_trades": cand["total_trades"],
                "params": {"flip": True, "tp_mult": 1.0, "sl_mult": 1.0},
            })

        # Mutation 2: Tighter stops
        key2 = f"{strat}::tighter_stops::gen{gen}"
        if key2 not in existing_keys:
            new_mutations.append({
                "parent": strat,
                "type": "tighter_stops",
                "generation": gen,
                "status": "active",
                "mutated_strategy_name": f"{strat}_mut_tight_g{gen}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "parent_wr": cand["win_rate"],
                "parent_trades": cand["total_trades"],
                "params": {"flip": False, "tp_mult": 0.6, "sl_mult": 0.6},
            })

        # Mutation 3: Regime-gated
        key3 = f"{strat}::regime_gate::gen{gen}"
        if key3 not in existing_keys:
            # Determine best regime for this strategy from its trades
            regime_wins: dict[str, int] = defaultdict(int)
            regime_total: dict[str, int] = defaultdict(int)
            for t in stats.get(strat, {}).get("trades", []):
                r = t.get("regime_at_entry", "unknown")
                regime_total[r] += 1
                if t.get("status") == "WON" or (t.get("pnl_pct", 0) or 0) > 0:
                    regime_wins[r] += 1

            best_regime = "any"
            best_regime_wr = 0.0
            for r, total in regime_total.items():
                if total >= 3:
                    wr = regime_wins.get(r, 0) / total
                    if wr > best_regime_wr:
                        best_regime_wr = wr
                        best_regime = r

            new_mutations.append({
                "parent": strat,
                "type": "regime_gate",
                "generation": gen,
                "status": "active",
                "mutated_strategy_name": f"{strat}_mut_regime_g{gen}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "parent_wr": cand["win_rate"],
                "parent_trades": cand["total_trades"],
                "params": {"required_regime": best_regime, "best_regime_wr": round(best_regime_wr, 4)},
            })

        # Bonus: crossover if donor available
        if best_donor and best_donor["strategy"] != strat:
            key4 = f"{strat}::crossover::gen{gen}"
            if key4 not in existing_keys:
                new_mutations.append({
                    "parent": strat,
                    "type": "crossover",
                    "generation": gen,
                    "status": "active",
                    "mutated_strategy_name": f"{strat}_mut_cross_g{gen}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "parent_wr": cand["win_rate"],
                    "parent_trades": cand["total_trades"],
                    "params": {
                        "flip": True,
                        "donor": best_donor["strategy"],
                        "donor_wr": best_donor["win_rate"],
                        "donor_tp_dist": best_donor.get("avg_tp_dist", 0.03),
                        "donor_sl_dist": best_donor.get("avg_sl_dist", 0.02),
                    },
                })

    # Merge with existing
    all_mutations = prev_mutations + new_mutations

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": candidates,
        "donors": [
            {k: v for k, v in d.items() if k != "trades"}
            for d in donors
        ],
        "mutations": all_mutations,
        "promoted": promoted,
        "killed": killed,
        "summary": {
            "total_candidates": len(candidates),
            "total_donors": len(donors),
            "new_mutations_created": len(new_mutations),
            "total_active_mutations": sum(1 for m in all_mutations if m.get("status") == "active"),
            "total_promoted": len(promoted),
            "total_killed": len(killed),
        },
    }

    _save_json(mutations_path, output)
    print(f"[DNA] Generated {len(new_mutations)} new mutations "
          f"({sum(1 for m in all_mutations if m.get('status') == 'active')} total active)")
    print(f"[DNA] Saved to {mutations_path}")

    return output


# ==============================================================================
# MUTATION EVALUATION
# ==============================================================================

def evaluate_mutations(
    mutations_path: str = "data/dna_mutations.json",
    closed_picks_path: str = "data/closed_picks.json",
) -> dict:
    """
    Check if any mutation variants have accumulated enough closed trades.
    Promote successful mutations (>50% WR on 10+ trades).
    Kill failed ones (<35% WR on 10+ trades).
    """
    # Resolve paths
    m_path = Path(mutations_path)
    if not m_path.is_absolute():
        m_path = DATA_DIR / mutations_path.replace("data/", "")

    c_path = Path(closed_picks_path)
    if not c_path.is_absolute():
        c_path = BASE_DIR / closed_picks_path

    mutations_data = _load_json(m_path)
    if not mutations_data or not isinstance(mutations_data, dict):
        print("[DNA] No mutations data to evaluate")
        return {}

    picks = _load_json(c_path)
    if not picks:
        print("[DNA] No closed picks to evaluate mutations against")
        return mutations_data

    # Build stats for mutation strategy names
    stats = _compute_strategy_stats(picks)

    mutations = mutations_data.get("mutations", [])
    promoted = mutations_data.get("promoted", [])
    killed = mutations_data.get("killed", [])

    newly_promoted = 0
    newly_killed = 0

    for mut in mutations:
        if mut.get("status") != "active":
            continue

        mut_name = mut.get("mutated_strategy_name", "")
        if not mut_name or mut_name not in stats:
            continue

        s = stats[mut_name]
        if s["total_trades"] < PROMOTE_MIN_TRADES:
            # Not enough data yet
            mut["eval_trades"] = s["total_trades"]
            mut["eval_wr"] = s["win_rate"]
            continue

        if s["win_rate"] >= PROMOTE_MIN_WR:
            # Promote -- mutation is working
            mut["status"] = "promoted"
            mut["promoted_at"] = datetime.now(timezone.utc).isoformat()
            mut["eval_trades"] = s["total_trades"]
            mut["eval_wr"] = s["win_rate"]
            mut["eval_pnl"] = s["total_pnl_pct"]
            promoted.append({
                "strategy": mut_name,
                "parent": mut.get("parent"),
                "type": mut.get("type"),
                "generation": mut.get("generation"),
                "win_rate": s["win_rate"],
                "total_trades": s["total_trades"],
                "promoted_at": mut["promoted_at"],
            })
            newly_promoted += 1
            print(f"[DNA] PROMOTED: {mut_name} (WR={s['win_rate']*100:.1f}%, {s['total_trades']} trades)")

        elif s["win_rate"] < KILL_MAX_WR:
            # Kill -- mutation is also failing
            mut["status"] = "killed"
            mut["killed_at"] = datetime.now(timezone.utc).isoformat()
            mut["eval_trades"] = s["total_trades"]
            mut["eval_wr"] = s["win_rate"]
            mut["eval_pnl"] = s["total_pnl_pct"]
            killed.append({
                "strategy": mut_name,
                "parent": mut.get("parent"),
                "type": mut.get("type"),
                "generation": mut.get("generation"),
                "win_rate": s["win_rate"],
                "total_trades": s["total_trades"],
                "killed_at": mut["killed_at"],
            })
            newly_killed += 1
            print(f"[DNA] KILLED: {mut_name} (WR={s['win_rate']*100:.1f}%, {s['total_trades']} trades)")

    mutations_data["mutations"] = mutations
    mutations_data["promoted"] = promoted
    mutations_data["killed"] = killed
    mutations_data["evaluated_at"] = datetime.now(timezone.utc).isoformat()

    _save_json(m_path, mutations_data)

    print(f"[DNA] Evaluation complete: {newly_promoted} promoted, {newly_killed} killed")
    return mutations_data


# ==============================================================================
# LIVE PICK TRANSFORMATION
# ==============================================================================

def _load_active_mutations() -> list[dict]:
    """Load active mutations from dna_mutations.json."""
    path = DATA_DIR / "dna_mutations.json"
    data = _load_json(path)
    if not data or not isinstance(data, dict):
        return []
    return [m for m in data.get("mutations", []) if m.get("status") == "active"]


def apply_mutations_to_scanner(picks: list[dict]) -> list[dict]:
    """
    For each pick from a mutation-candidate strategy, apply the registered
    mutation transformation before it enters the pipeline.

    This does NOT replace the original pick -- it ADDS mutated variants
    alongside the original. The original continues through the pipeline
    normally. Mutated variants are tagged so performance can be tracked
    independently.

    Args:
        picks: List of signal dicts from the strategy scan.

    Returns:
        Extended list with original picks + any mutated variants appended.
    """
    mutations = _load_active_mutations()
    if not mutations:
        return picks

    # Index mutations by parent strategy
    mut_by_parent: dict[str, list[dict]] = defaultdict(list)
    for m in mutations:
        parent = m.get("parent", "")
        if parent:
            mut_by_parent[parent].append(m)

    if not mut_by_parent:
        return picks

    mutated_picks = []
    for pick in picks:
        strat = pick.get("strategy", "")
        if strat not in mut_by_parent:
            continue

        for mut in mut_by_parent[strat]:
            mut_type = mut.get("type", "")
            params = mut.get("params", {})
            mut_name = mut.get("mutated_strategy_name", f"{strat}_mut_{mut_type}")

            try:
                if mut_type == "inverse":
                    variant = inverse_mutation(pick)
                elif mut_type == "tighter_stops":
                    factor = params.get("tp_mult", 0.6)
                    variant = tighter_stops(pick, factor=factor)
                elif mut_type == "wider_stops":
                    factor = params.get("tp_mult", 1.5)
                    variant = wider_stops(pick, factor=factor)
                elif mut_type == "regime_gate":
                    required = params.get("required_regime", "any")
                    variant = regime_gate(pick, regime=required)
                    if variant.get("regime_blocked"):
                        continue  # Skip this variant -- wrong regime
                elif mut_type == "timeframe_shift":
                    shift_dir = params.get("shift", "up")
                    variant = timeframe_shift(pick, shift=shift_dir)
                elif mut_type == "confidence_threshold":
                    min_conf = params.get("min_confidence", 0.7)
                    variant = confidence_threshold(pick, min_conf=min_conf)
                    if variant.get("confidence_blocked"):
                        continue  # Skip -- below confidence threshold
                elif mut_type == "crossover":
                    donor_params = {
                        "strategy": params.get("donor", "unknown"),
                        "avg_tp_dist": params.get("donor_tp_dist", 0.03),
                        "avg_sl_dist": params.get("donor_sl_dist", 0.02),
                    }
                    variant = crossover_mutation(pick, donor_params)
                else:
                    continue  # Unknown mutation type

                # Tag the variant
                variant["strategy"] = mut_name
                variant["mutation_parent"] = strat
                variant["mutation_type"] = mut_type
                variant["mutation_generation"] = mut.get("generation", 1)
                variant["is_mutation"] = True

                mutated_picks.append(variant)

            except Exception as e:
                print(f"[DNA] Warning: mutation {mut_type} failed for {strat}: {e}")
                continue

    if mutated_picks:
        print(f"[DNA] Generated {len(mutated_picks)} mutated variant(s) from {len(mut_by_parent)} strategies")

    return picks + mutated_picks


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="DNA Mutation Engine")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate existing mutations")
    parser.add_argument("--report", action="store_true", help="Print mutation report")
    parser.add_argument("--closed-picks", default="data/closed_picks.json",
                        help="Path to closed picks JSON")
    args = parser.parse_args()

    if args.evaluate:
        evaluate_mutations(closed_picks_path=args.closed_picks)
    elif args.report:
        path = DATA_DIR / "dna_mutations.json"
        data = _load_json(path)
        if not data:
            print("[DNA] No mutations data found")
            return
        print(f"\n{'='*60}")
        print(f"DNA MUTATION REPORT")
        print(f"{'='*60}")
        print(f"Generated at: {data.get('generated_at', 'unknown')}")
        print(f"Candidates:   {len(data.get('candidates', []))}")
        print(f"Donors:       {len(data.get('donors', []))}")
        mutations = data.get("mutations", [])
        active = [m for m in mutations if m.get("status") == "active"]
        print(f"Active:       {len(active)}")
        print(f"Promoted:     {len(data.get('promoted', []))}")
        print(f"Killed:       {len(data.get('killed', []))}")
        print()
        for m in active[:20]:
            print(f"  [{m.get('type'):15s}] {m.get('mutated_strategy_name', '?'):40s} "
                  f"parent_wr={m.get('parent_wr', 0)*100:.1f}% "
                  f"gen={m.get('generation', 0)}")
        if len(active) > 20:
            print(f"  ... and {len(active) - 20} more")
        print(f"{'='*60}\n")
    else:
        generate_mutations(closed_picks_path=args.closed_picks)


if __name__ == "__main__":
    main()
