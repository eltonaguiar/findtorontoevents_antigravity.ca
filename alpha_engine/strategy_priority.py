#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Strategy Priority Tier System
================================================
Cross-AI consensus: "Your system is fighting itself. 5 uncorrelated strategies max."

We can't literally reduce to 5 strategies, but we CAN prioritize ruthlessly.

Tiers:
  ELITE (top 5):        3x position sizing, relaxed gates (confidence >= 0.65)
  PROVEN (next 10):     1x position sizing, all gates apply
  EXPERIMENTAL (rest):  0.5x position sizing, stricter gates (confidence >= 0.80)

Auto-kill: Any strategy with 20+ trades and WR < 30% -> HARD_DISABLED
  BUT ONLY if mutation was already attempted (mutate-before-kill rule).
  If no mutation tried yet, strategy goes to MUTATION_CANDIDATES instead.

"Don't trade" states (ChatGPT):
  - Fewer than 3 strategies generate signals -> output 0 picks (market unclear)
  - Overall active portfolio losing >5% unrealized -> halve all new position sizes

Usage:
  from strategy_priority import (
      get_strategy_tier, get_position_multiplier,
      get_auto_kill_list, should_trade_now,
      apply_tier_gates, compute_portfolio_stress_multiplier,
  )
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum closed trades to be evaluated for tier placement
MIN_TRADES_FOR_TIER = 10

# Minimum trades for auto-kill evaluation
MIN_TRADES_FOR_KILL = 20

# Auto-kill WR threshold (20+ trades below this -> HARD_DISABLED)
AUTO_KILL_WR_THRESHOLD = 0.30

# Tier sizes
ELITE_SIZE = 5
PROVEN_SIZE = 10

# Tier confidence gates
ELITE_MIN_CONFIDENCE = 0.65
PROVEN_MIN_CONFIDENCE = 0.70   # same as current QUALITY_GATE_MIN_CONFIDENCE
EXPERIMENTAL_MIN_CONFIDENCE = 0.80
QUAN_ENGINE_MIN_CONFIDENCE = 0.50

# Tier position multipliers
ELITE_MULTIPLIER = 3.0
PROVEN_MULTIPLIER = 1.0
EXPERIMENTAL_MULTIPLIER = 0.5

# "Don't trade" thresholds
MIN_STRATEGIES_FOR_TRADE = 3   # fewer unique strategies -> 0 picks
PORTFOLIO_STRESS_THRESHOLD = -0.05  # -5% unrealized -> halve new positions

# Composite score weights: WR, PF_norm, avg_pnl_norm
W_WR = 0.4
W_PF = 0.3
W_PNL = 0.3

# Kill list output path
KILL_LIST_PATH = DATA_DIR / "strategy_kill_list.json"
TIER_REPORT_PATH = DATA_DIR / "strategy_tiers.json"
MUTATION_CANDIDATES_PATH = DATA_DIR / "mutation_candidates.json"


# ---------------------------------------------------------------------------
# Core: Analyze closed picks and build tier rankings
# ---------------------------------------------------------------------------

def _load_closed_picks() -> list[dict]:
    """Load closed_picks.json."""
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _compute_strategy_stats(closed_picks: list[dict]) -> dict[str, dict]:
    """Compute per-strategy stats from closed picks.

    Returns dict of strategy_name -> {
        trades, wins, losses, wr, pf, avg_pnl, sharpe_proxy,
        total_pnl, composite_score
    }
    """
    # Group by strategy
    by_strategy: dict[str, list[dict]] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "unknown")
        by_strategy.setdefault(strat, []).append(pick)

    stats = {}
    for strat, picks in by_strategy.items():
        pnls = []
        wins = 0
        losses = 0
        gross_wins = 0.0
        gross_losses = 0.0

        for p in picks:
            pnl = p.get("pnl_pct")
            if pnl is None:
                continue
            # Handle both fractional (0.03) and percentage (3.0) formats
            # Closed picks use fractional format based on data inspection
            pnl_val = float(pnl)
            pnls.append(pnl_val)

            status = str(p.get("status", "") or "").upper()
            if status in {"WON", "TP_HIT", "EXPIRED_WIN"}:
                wins += 1
                gross_wins += abs(pnl_val)
            elif status in {"LOST", "SL_HIT", "EXPIRED_LOSS"}:
                losses += 1
                gross_losses += abs(pnl_val)
            elif pnl_val > 0:
                wins += 1
                gross_wins += abs(pnl_val)
            else:
                losses += 1
                gross_losses += abs(pnl_val)

        total_trades = wins + losses
        if total_trades == 0:
            continue

        wr = wins / total_trades
        pf = (gross_wins / gross_losses) if gross_losses > 0 else (10.0 if gross_wins > 0 else 0.0)
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        total_pnl = sum(pnls)

        # Sharpe proxy: mean / stdev of pnl (annualized not needed for ranking)
        if len(pnls) >= 2:
            std = statistics.stdev(pnls)
            sharpe_proxy = (avg_pnl / std) if std > 0 else 0.0
        else:
            sharpe_proxy = 0.0

        stats[strat] = {
            "trades": total_trades,
            "wins": wins,
            "losses": losses,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "avg_pnl": round(avg_pnl, 6),
            "total_pnl": round(total_pnl, 6),
            "sharpe_proxy": round(sharpe_proxy, 4),
        }

    return stats


def _compute_composite_scores(stats: dict[str, dict]) -> dict[str, float]:
    """Compute composite ranking score for strategies with MIN_TRADES_FOR_TIER+ trades.

    Score = 0.4*WR + 0.3*PF_norm + 0.3*avg_pnl_norm
    Normalization: min-max scaling to [0, 1] range.
    """
    # Filter to strategies with enough trades
    eligible = {s: v for s, v in stats.items() if v["trades"] >= MIN_TRADES_FOR_TIER}
    if not eligible:
        return {}

    # Collect raw values for normalization
    wrs = [v["wr"] for v in eligible.values()]
    pfs = [v["pf"] for v in eligible.values()]
    avg_pnls = [v["avg_pnl"] for v in eligible.values()]

    def _normalize(val: float, vals: list[float]) -> float:
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return 0.5
        return (val - mn) / (mx - mn)

    scores = {}
    for strat, v in eligible.items():
        wr_norm = _normalize(v["wr"], wrs)
        pf_norm = _normalize(min(v["pf"], 10.0), pfs)  # cap PF at 10 for normalization
        pnl_norm = _normalize(v["avg_pnl"], avg_pnls)

        composite = W_WR * wr_norm + W_PF * pf_norm + W_PNL * pnl_norm
        scores[strat] = round(composite, 6)

    return scores


def _load_mutation_records() -> dict:
    """Load mutation data from multiple sources to check if mutation was attempted.

    Checks:
      1. dna_mutation_report.json -- super_losers with mutations_created
      2. dna_mutation_tracker.json -- tracked mutation stats
      3. strategy_mutations.json -- mutation suggestions (NOT proof of attempt)

    Returns dict of strategy_name -> {
        "mutation_attempted": bool,
        "inverse_attempted": bool,
        "parameter_mutation_attempted": bool,
        "mutation_variants": [str, ...],
        "mutation_results": {...} or None,
    }
    """
    records: dict[str, dict] = {}

    # Source 1: dna_mutation_report.json -- concrete mutations that were created
    report_path = DATA_DIR / "dna_mutation_report.json"
    if report_path.exists():
        try:
            with open(report_path) as f:
                report = json.load(f)
            for entry in report.get("super_losers", []):
                strat = entry.get("strategy", "")
                if not strat:
                    continue
                variants = entry.get("mutations_created", [])
                rec = records.setdefault(strat, {
                    "mutation_attempted": False,
                    "inverse_attempted": False,
                    "parameter_mutation_attempted": False,
                    "mutation_variants": [],
                    "mutation_results": None,
                })
                rec["mutation_variants"].extend(variants)
                if variants:
                    rec["mutation_attempted"] = True
                for v in variants:
                    if v.startswith("inverse_"):
                        rec["inverse_attempted"] = True
                    if v.endswith("_tight") or v.endswith("_wide"):
                        rec["parameter_mutation_attempted"] = True
        except (json.JSONDecodeError, IOError):
            pass

    # Source 2: dna_mutation_tracker.json -- tracked mutation performance
    tracker_path = DATA_DIR / "dna_mutation_tracker.json"
    if tracker_path.exists():
        try:
            with open(tracker_path) as f:
                tracker = json.load(f)
            for variant_name, variant_stats in tracker.get("mutation_stats", {}).items():
                # Find parent strategy from variant name
                # Variants are named like: inverse_<parent>_tight, inverse_<parent>_wide
                parent = variant_stats.get("parent_strategy", "")
                # Also try to derive parent from variant name
                for prefix in ("inverse_",):
                    if variant_name.startswith(prefix):
                        base = variant_name[len(prefix):]
                        # Strip _tight/_wide suffix to get original
                        for suffix in ("_tight", "_wide"):
                            if base.endswith(suffix):
                                base = base[:-len(suffix)]
                                break
                        if base and base not in records:
                            records.setdefault(base, {
                                "mutation_attempted": True,
                                "inverse_attempted": True,
                                "parameter_mutation_attempted": False,
                                "mutation_variants": [variant_name],
                                "mutation_results": None,
                            })
                        elif base:
                            rec = records[base]
                            rec["mutation_attempted"] = True
                            rec["inverse_attempted"] = True
                            if variant_name not in rec["mutation_variants"]:
                                rec["mutation_variants"].append(variant_name)

                # Attach results if available
                if parent:
                    for suffix in ("_tight", "_wide"):
                        if parent.endswith(suffix):
                            parent = parent[:-len(suffix)]
                            break
                    if parent.startswith("inverse_"):
                        parent = parent[len("inverse_"):]
                    if parent in records:
                        records[parent]["mutation_results"] = variant_stats
        except (json.JSONDecodeError, IOError):
            pass

    # Source 3: Check closed_picks for inverse_ variants (proof they actually ran)
    closed_path = DATA_DIR / "closed_picks.json"
    if closed_path.exists():
        try:
            with open(closed_path) as f:
                closed = json.load(f)
            inverse_strategies_seen = set()
            for pick in closed:
                strat = pick.get("strategy", "")
                if strat.startswith("inverse_"):
                    inverse_strategies_seen.add(strat)

            # Map inverse picks back to parent
            for inv_strat in inverse_strategies_seen:
                base = inv_strat[len("inverse_"):]
                for suffix in ("_tight", "_wide"):
                    if base.endswith(suffix):
                        base = base[:-len(suffix)]
                        break
                rec = records.setdefault(base, {
                    "mutation_attempted": True,
                    "inverse_attempted": True,
                    "parameter_mutation_attempted": False,
                    "mutation_variants": [],
                    "mutation_results": None,
                })
                rec["mutation_attempted"] = True
                rec["inverse_attempted"] = True
                if inv_strat not in rec["mutation_variants"]:
                    rec["mutation_variants"].append(inv_strat)
        except (json.JSONDecodeError, IOError):
            pass

    return records


def _check_mutation_variant_failed(strategy_name: str, mutation_records: dict,
                                    stats: dict[str, dict]) -> bool:
    """Check if a strategy's mutation variants also failed (WR < 30%).

    Returns True if mutation was attempted AND all variants also failed.
    """
    rec = mutation_records.get(strategy_name)
    if not rec or not rec.get("mutation_attempted"):
        return False  # No mutation attempted

    variants = rec.get("mutation_variants", [])
    if not variants:
        return False  # Mutation record exists but no variants created

    # Check each variant's performance in closed picks stats
    for variant in variants:
        variant_stats = stats.get(variant)
        if variant_stats is None:
            # Variant exists but hasn't accumulated enough trades yet -- give it time
            return False
        if variant_stats["trades"] < MIN_TRADES_FOR_KILL:
            # Not enough trades to evaluate yet -- don't kill parent
            return False
        if variant_stats["wr"] >= AUTO_KILL_WR_THRESHOLD:
            # At least one variant is working -- don't kill parent (variant lives on)
            return False

    # All variants have enough trades and all failed
    return True


def build_tiers(closed_picks: list[dict] | None = None) -> dict:
    """Build the full tier system from closed picks data.

    Enforces the MUTATE-BEFORE-KILL rule:
      - Strategies with WR < 30% on 20+ trades are NOT auto-killed unless
        a mutation (inverse/parameter variant) was already attempted and also failed.
      - Unmutated failing strategies go to "mutation_candidates" instead.

    Returns {
        "elite": [str, ...],       # top 5 strategy names
        "proven": [str, ...],      # next 10
        "experimental": [str, ...], # everything else (with some trades)
        "auto_kill": [str, ...],   # strategies to hard-disable (mutation tried & failed)
        "mutation_candidates": [str, ...],  # need mutation before any kill decision
        "stats": {strategy -> stats_dict},
        "scores": {strategy -> composite_score},
    }
    """
    if closed_picks is None:
        closed_picks = _load_closed_picks()

    stats = _compute_strategy_stats(closed_picks)
    scores = _compute_composite_scores(stats)

    # Load mutation records to enforce mutate-before-kill
    mutation_records = _load_mutation_records()

    # Separate failing strategies into auto_kill vs mutation_candidates
    auto_kill = []
    mutation_candidates = []

    # Load protected strategies that can NEVER be killed
    _protected_strats = set()
    try:
        import json as _json_sp
        _wl_sp_path = Path(__file__).parent / "data" / "core_whitelist.json"
        if _wl_sp_path.exists():
            _wl_sp = _json_sp.loads(_wl_sp_path.read_text(encoding="utf-8"))
            for _grp in ("protected_strategies", "core_strategies", "incubator_strategies"):
                _protected_strats.update(
                    s.lower() for s in _wl_sp.get(_grp, []) if isinstance(s, str)
                )
    except Exception:
        pass

    for strat, v in stats.items():
        if strat.lower() in _protected_strats:
            continue  # NEVER kill protected strategies
        if v["trades"] >= MIN_TRADES_FOR_KILL and v["wr"] < AUTO_KILL_WR_THRESHOLD:
            rec = mutation_records.get(strat)
            mutation_attempted = rec and rec.get("mutation_attempted", False)

            if not mutation_attempted:
                # MUTATE-BEFORE-KILL: no mutation tried yet -> candidate, not kill
                mutation_candidates.append(strat)
                print(f"  [PRIORITY] MUTATE-BEFORE-KILL: {strat} "
                      f"(WR={v['wr']:.1%}, {v['trades']} trades) -> mutation candidate "
                      f"(no mutation attempted yet)")
            elif _check_mutation_variant_failed(strat, mutation_records, stats):
                # Mutation was tried AND all variants also failed -> OK to kill
                auto_kill.append(strat)
                variants = rec.get("mutation_variants", []) if rec else []
                print(f"  [PRIORITY] AUTO-KILL (mutation exhausted): {strat} "
                      f"(WR={v['wr']:.1%}, {v['trades']} trades) -- "
                      f"variants tried: {variants}")
            else:
                # Mutation attempted but variants still running or haven't accumulated
                # enough trades -- keep as candidate, don't kill yet
                mutation_candidates.append(strat)
                variants = rec.get("mutation_variants", []) if rec else []
                print(f"  [PRIORITY] MUTATE-BEFORE-KILL: {strat} "
                      f"(WR={v['wr']:.1%}, {v['trades']} trades) -> mutation candidate "
                      f"(variants still being evaluated: {variants})")

    # Rank eligible strategies by composite score (descending)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Remove auto-killed AND mutation candidate strategies from ranking
    excluded = set(auto_kill) | set(mutation_candidates)
    ranked = [(s, sc) for s, sc in ranked if s not in excluded]

    # Assign tiers with QUALITY GATES
    # ELITE: Top strategies with min 50% WR and min 10 trades
    # PROVEN: Next tier with min 40% WR and min 5 trades
    elite = []
    proven = []

    # 1. Fill Elite tier (top scores that pass gate)
    for s, sc in ranked:
        if len(elite) >= ELITE_SIZE:
            break
        v = stats.get(s, {})
        if v.get("wr", 0) >= 0.50 and v.get("trades", 0) >= 10:
            elite.append(s)

    # 2. Fill Proven tier (remaining top scores that pass gate)
    elite_set = set(elite)
    for s, sc in ranked:
        if s in elite_set:
            continue
        if len(proven) >= PROVEN_SIZE:
            break
        v = stats.get(s, {})
        # Proven gate: min 40% WR and min 5 trades
        if v.get("wr", 0) >= 0.40 and v.get("trades", 0) >= 5:
            proven.append(s)

    # Experimental: EVERYTHING ELSE that is not elite/proven/killed/candidate
    top_set = set(elite) | set(proven) | excluded
    experimental = [s for s in stats if s not in top_set]

    return {
        "elite": elite,
        "proven": proven,
        "experimental": experimental,
        "auto_kill": auto_kill,
        "mutation_candidates": mutation_candidates,
        "stats": stats,
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# Cached tier data (lazy-loaded once per process)
# ---------------------------------------------------------------------------

_CACHED_TIERS: dict | None = None


def _get_tiers() -> dict:
    """Get cached tier data, building it on first call."""
    global _CACHED_TIERS
    if _CACHED_TIERS is None:
        _CACHED_TIERS = build_tiers()
    return _CACHED_TIERS


def refresh_tiers(closed_picks: list[dict] | None = None) -> dict:
    """Force-refresh the tier cache. Call after new picks close."""
    global _CACHED_TIERS
    _CACHED_TIERS = build_tiers(closed_picks)
    return _CACHED_TIERS


# ---------------------------------------------------------------------------
# Public API: get_strategy_tier, get_position_multiplier, etc.
# ---------------------------------------------------------------------------

def get_strategy_tier(strategy_name: str) -> str:
    """Return the tier for a strategy: 'ELITE', 'PROVEN', or 'EXPERIMENTAL'."""
    tiers = _get_tiers()
    if strategy_name in tiers["elite"]:
        return "ELITE"
    if strategy_name in tiers["proven"]:
        return "PROVEN"
    return "EXPERIMENTAL"


def get_position_multiplier(strategy_name: str) -> float:
    """Return position sizing multiplier: 3.0 (ELITE), 1.0 (PROVEN), 0.5 (EXPERIMENTAL)."""
    tier = get_strategy_tier(strategy_name)
    if tier == "ELITE":
        return ELITE_MULTIPLIER
    if tier == "PROVEN":
        return PROVEN_MULTIPLIER
    return EXPERIMENTAL_MULTIPLIER


def get_confidence_gate(strategy_name: str) -> float:
    """Return minimum confidence threshold for this strategy's tier."""
    tier = get_strategy_tier(strategy_name)
    if tier == "ELITE":
        return ELITE_MIN_CONFIDENCE
    if tier == "PROVEN":
        return PROVEN_MIN_CONFIDENCE
    return EXPERIMENTAL_MIN_CONFIDENCE


def get_pick_confidence_gate(pick: dict) -> float:
    """Return the effective confidence gate for a specific pick."""
    strat = str(pick.get("strategy", "") or "")
    source = str(pick.get("source_system", "") or "").lower()
    if source == "quan_engine" or strat.startswith("quan_engine_"):
        return QUAN_ENGINE_MIN_CONFIDENCE
    return get_confidence_gate(strat)


def get_auto_kill_list() -> list[str]:
    """Return list of strategies that should be HARD_DISABLED.

    Only includes strategies where mutation was attempted and also failed.
    Strategies needing mutation first are in get_mutation_candidates().
    """
    tiers = _get_tiers()
    return list(tiers["auto_kill"])


def get_mutation_candidates() -> list[str]:
    """Return list of strategies that need mutation before any kill decision.

    These strategies have WR < 30% on 20+ trades but NO mutation was attempted yet,
    or mutation variants are still being evaluated.
    """
    tiers = _get_tiers()
    return list(tiers.get("mutation_candidates", []))


def should_trade_now(active_picks: list[dict]) -> bool:
    """Determine if the system should emit new picks this cycle.

    Returns False (don't trade) when:
      - Fewer than MIN_STRATEGIES_FOR_TRADE unique strategies have signals
        (market is unclear -- no consensus across strategies)

    Note: Portfolio stress (>5% unrealized loss) is handled separately via
    compute_portfolio_stress_multiplier() which halves position sizes rather
    than blocking all trades.
    """
    unique_strategies = set()
    for pick in active_picks:
        strat = pick.get("strategy", "")
        if strat:
            unique_strategies.add(strat)

    if len(unique_strategies) < MIN_STRATEGIES_FOR_TRADE:
        print(f"  [PRIORITY] DON'T TRADE: only {len(unique_strategies)} unique strategies "
              f"(need >= {MIN_STRATEGIES_FOR_TRADE}) -- market unclear")
        return False

    return True


def compute_portfolio_stress_multiplier(active_picks: list[dict]) -> float:
    """Compute a position size multiplier based on portfolio stress.

    Returns:
        1.0 if portfolio is healthy
        0.5 if overall active portfolio is losing >5% unrealized (halve new positions)
    """
    if not active_picks:
        return 1.0

    unrealized_pnls = []
    for pick in active_picks:
        pnl = pick.get("unrealized_pnl_pct")
        if pnl is not None:
            try:
                unrealized_pnls.append(float(pnl))
            except (TypeError, ValueError):
                pass

    if not unrealized_pnls:
        return 1.0

    avg_unrealized = sum(unrealized_pnls) / len(unrealized_pnls)

    if avg_unrealized < PORTFOLIO_STRESS_THRESHOLD:
        print(f"  [PRIORITY] PORTFOLIO STRESS: avg unrealized PnL = {avg_unrealized:.2%} "
              f"(threshold = {PORTFOLIO_STRESS_THRESHOLD:.0%}) -- halving new position sizes")
        return 0.5

    return 1.0


# ---------------------------------------------------------------------------
# Apply tier-based gates to picks (called from production_scanner.py)
# ---------------------------------------------------------------------------

def apply_tier_gates(picks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply tier-specific confidence gates and position multipliers.

    For each pick:
      - Check if strategy is on auto-kill list -> reject
      - Apply tier-specific confidence gate -> reject if below threshold
      - Set 'tier_priority' field ("ELITE", "PROVEN", "EXPERIMENTAL")
      - Set 'position_multiplier' field (3.0, 1.0, 0.5)

    Returns (passed, rejected) tuple.
    """
    tiers = _get_tiers()
    kill_set = set(tiers["auto_kill"])
    mutation_set = set(tiers.get("mutation_candidates", []))

    # S1 FIX: Load institutional kill list (hard suppresses)
    institutional_kills = set()
    inst_path = DATA_DIR.parent / "strategy_kill_list.json"
    if inst_path.exists():
        try:
            with open(inst_path) as f:
                inst_data = json.load(f)
                institutional_kills.update(
                    k.lower() for k in inst_data.get("institutional_kill_list", [])
                )
        except Exception:
            pass

    passed = []
    rejected = []

    for pick in picks:
        strat = pick.get("strategy", "")
        strat_low = strat.lower()
        conf = pick.get("confidence", 0) or 0

        # Institutional hard-kill gate
        if strat_low in institutional_kills:
            pick["_tier_rejected"] = (
                f"INSTITUTIONAL-KILL: {strat} -- hard suppressed by April 2026 Audit"
            )
            rejected.append(pick)
            continue

        # Auto-kill gate (mutation was tried and failed)
        if strat in kill_set:
            pick["_tier_rejected"] = (
                f"AUTO-KILL: {strat} -- mutation attempted & failed, WR < 30%"
            )
            rejected.append(pick)
            continue

        # Mutation candidate gate (needs mutation before kill, but still paused)
        if strat in mutation_set:
            pick["_tier_rejected"] = (
                f"MUTATION-PENDING: {strat} -- WR < 30%, awaiting mutation "
                f"(inverse/parameter variant). Original paused."
            )
            rejected.append(pick)
            continue

        # Tier assignment
        tier = get_strategy_tier(strat)
        min_conf = get_pick_confidence_gate(pick)

        # Tier-specific confidence gate
        if conf < min_conf:
            pick["_tier_rejected"] = (
                f"TIER {tier}: conf={conf:.2f} < {min_conf:.2f} threshold"
            )
            rejected.append(pick)
            continue

        # Enrich pick with tier info
        pick["tier_priority"] = tier
        pick["position_multiplier"] = get_position_multiplier(strat)
        passed.append(pick)

    return passed, rejected


# ---------------------------------------------------------------------------
# Persistence: write kill list + tier report to JSON
# ---------------------------------------------------------------------------

def save_kill_list() -> list[str]:
    """Compute and save auto-kill list to strategy_kill_list.json.

    Also saves mutation_candidates.json for strategies needing mutation first.
    Returns the kill list.
    """
    tiers = _get_tiers()
    kill_list = tiers["auto_kill"]
    mutation_candidates = tiers.get("mutation_candidates", [])
    mutation_records = _load_mutation_records()

    # --- Save kill list (only mutation-exhausted strategies) ---
    kill_data = {
        "auto_kill_strategies": kill_list,
        "criteria": (f"WR < {AUTO_KILL_WR_THRESHOLD:.0%} on {MIN_TRADES_FOR_KILL}+ trades "
                     f"AND mutation attempted & failed"),
        "details": {},
    }

    for strat in kill_list:
        st = tiers["stats"].get(strat, {})
        rec = mutation_records.get(strat, {})
        kill_data["details"][strat] = {
            "trades": st.get("trades", 0),
            "wr": st.get("wr", 0),
            "avg_pnl": st.get("avg_pnl", 0),
            "total_pnl": st.get("total_pnl", 0),
            "mutation_history": {
                "variants_tried": rec.get("mutation_variants", []),
                "inverse_attempted": rec.get("inverse_attempted", False),
                "parameter_mutation_attempted": rec.get("parameter_mutation_attempted", False),
            },
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(KILL_LIST_PATH, "w") as f:
        json.dump(kill_data, f, indent=2)

    print(f"  [PRIORITY] Saved kill list ({len(kill_list)} strategies) to {KILL_LIST_PATH.name}")

    # --- Save mutation candidates ---
    _save_mutation_candidates(tiers, mutation_records)

    return kill_list


def _save_mutation_candidates(tiers: dict, mutation_records: dict) -> None:
    """Save mutation_candidates.json for the Codex monitor's mutation loop."""
    candidates = tiers.get("mutation_candidates", [])

    candidate_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mutation_candidates": [],
        "criteria": (f"WR < {AUTO_KILL_WR_THRESHOLD:.0%} on {MIN_TRADES_FOR_KILL}+ trades "
                     f"but mutation not yet attempted or still evaluating"),
    }

    for strat in candidates:
        st = tiers["stats"].get(strat, {})
        rec = mutation_records.get(strat, {})
        entry = {
            "strategy": strat,
            "needs_mutation": True,
            "mutation_reason": (f"WR {st.get('wr', 0):.1%} < {AUTO_KILL_WR_THRESHOLD:.0%} "
                                f"on {st.get('trades', 0)} trades"),
            "trades": st.get("trades", 0),
            "wr": st.get("wr", 0),
            "avg_pnl": st.get("avg_pnl", 0),
            "total_pnl": st.get("total_pnl", 0),
            "existing_mutations": rec.get("mutation_variants", []),
            "inverse_attempted": rec.get("inverse_attempted", False),
            "parameter_mutation_attempted": rec.get("parameter_mutation_attempted", False),
        }
        candidate_data["mutation_candidates"].append(entry)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MUTATION_CANDIDATES_PATH, "w") as f:
        json.dump(candidate_data, f, indent=2)

    if candidates:
        print(f"  [PRIORITY] Saved {len(candidates)} mutation candidates to "
              f"{MUTATION_CANDIDATES_PATH.name} (mutate-before-kill rule)")


def save_tier_report() -> None:
    """Save full tier report to strategy_tiers.json for audit/dashboard."""
    tiers = _get_tiers()

    report = {
        "elite": tiers["elite"],
        "proven": tiers["proven"],
        "experimental_count": len(tiers["experimental"]),
        "auto_kill": tiers["auto_kill"],
        "mutation_candidates": tiers.get("mutation_candidates", []),
        "composite_scores": tiers["scores"],
        "strategy_stats": {},
    }

    # Include stats for elite + proven (full detail)
    for strat in tiers["elite"] + tiers["proven"]:
        if strat in tiers["stats"]:
            report["strategy_stats"][strat] = tiers["stats"][strat]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TIER_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"  [PRIORITY] Tier report saved to {TIER_REPORT_PATH.name}")
    print(f"    ELITE ({len(tiers['elite'])}): {', '.join(tiers['elite']) or 'none'}")
    print(f"    PROVEN ({len(tiers['proven'])}): {', '.join(tiers['proven']) or 'none'}")
    print(f"    EXPERIMENTAL: {len(tiers['experimental'])} strategies")
    print(f"    MUTATION CANDIDATES: {len(tiers.get('mutation_candidates', []))} strategies (need mutation first)")
    print(f"    AUTO-KILL: {len(tiers['auto_kill'])} strategies (mutation exhausted)")


# ---------------------------------------------------------------------------
# CLI: run standalone to see tier report
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    tiers = build_tiers()

    print("=" * 70)
    print("STRATEGY PRIORITY TIER SYSTEM")
    print("=" * 70)

    print(f"\nELITE (top {ELITE_SIZE} -- 3x sizing, conf >= {ELITE_MIN_CONFIDENCE}):")
    for i, strat in enumerate(tiers["elite"], 1):
        st = tiers["stats"].get(strat, {})
        sc = tiers["scores"].get(strat, 0)
        print(f"  {i}. {strat}: {st.get('trades',0)} trades, "
              f"WR={st.get('wr',0):.1%}, PF={st.get('pf',0):.2f}, "
              f"avg_pnl={st.get('avg_pnl',0):.3%}, score={sc:.4f}")

    print(f"\nPROVEN (next {PROVEN_SIZE} -- 1x sizing, standard gates):")
    for i, strat in enumerate(tiers["proven"], 1):
        st = tiers["stats"].get(strat, {})
        sc = tiers["scores"].get(strat, 0)
        print(f"  {i}. {strat}: {st.get('trades',0)} trades, "
              f"WR={st.get('wr',0):.1%}, PF={st.get('pf',0):.2f}, "
              f"avg_pnl={st.get('avg_pnl',0):.3%}, score={sc:.4f}")

    print(f"\nEXPERIMENTAL ({len(tiers['experimental'])} strategies -- 0.5x sizing, conf >= {EXPERIMENTAL_MIN_CONFIDENCE})")

    print(f"\nMUTATION CANDIDATES ({len(tiers.get('mutation_candidates', []))} strategies -- need mutation before kill):")
    for strat in tiers.get("mutation_candidates", []):
        st = tiers["stats"].get(strat, {})
        print(f"  - {strat}: {st.get('trades',0)} trades, "
              f"WR={st.get('wr',0):.1%}, avg_pnl={st.get('avg_pnl',0):.3%}")

    print(f"\nAUTO-KILL ({len(tiers['auto_kill'])} strategies -- mutation tried & failed, "
          f"WR < {AUTO_KILL_WR_THRESHOLD:.0%} on {MIN_TRADES_FOR_KILL}+ trades):")
    for strat in tiers["auto_kill"]:
        st = tiers["stats"].get(strat, {})
        print(f"  - {strat}: {st.get('trades',0)} trades, "
              f"WR={st.get('wr',0):.1%}, avg_pnl={st.get('avg_pnl',0):.3%}")

    # Save outputs
    save_kill_list()
    save_tier_report()

    print(f"\nTotal strategies analyzed: {len(tiers['stats'])}")
    print(f"Strategies with {MIN_TRADES_FOR_TIER}+ trades (tier-eligible): {len(tiers['scores'])}")
