#!/usr/bin/env python3
"""
Deep Mutation Engine — 5-Type DNA Mutations for Worst-Performing Strategies
============================================================================
Implements the "mutate before kill" policy with 5 distinct mutation types:

  1. inverse_signal    — flip BUY->SELL, SELL->BUY (contrarian bet)
  2. tighten_stops     — halve SL distance, keep TP (cut losses faster)
  3. widen_targets     — increase TP by 50% (let winners run)
  4. regime_gate       — only trade in favorable market regime
  5. timeframe_shift   — move to higher timeframe (reduce noise)

For each of the worst 10 LOW_CONFIDENCE_STRATEGIES, generates all 5 mutations
and registers them in strategy_mutations.json for tracking and validation.

Also provides evaluate_mutations() to auto-promote or auto-fail mutations
based on forward-test results.

Standalone runnable:
  python alpha_engine/deep_mutation_engine.py
"""

from __future__ import annotations

import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
MUTATION_REGISTRY_PATH = DATA_DIR / "strategy_mutations.json"
DASHBOARD_PAYLOAD_PATH = BASE / "audit_trail" / "data" / "dashboard_payload.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
DEEP_MUTATION_REPORT_PATH = DATA_DIR / "deep_mutation_report.json"

# ── Import LOW_CONFIDENCE_STRATEGIES from auto_tuner ───────────────
sys.path.insert(0, str(ENGINE_DIR))
try:
    from auto_tuner import LOW_CONFIDENCE_STRATEGIES
except ImportError:
    # Fallback: hardcoded worst 10 if import fails in CI
    LOW_CONFIDENCE_STRATEGIES = set()

# ── Mutation evaluation thresholds ─────────────────────────────────
MIN_TRADES_FOR_EVAL = 10          # need 10+ closed trades to judge
PROMOTE_WR_IMPROVEMENT_PP = 5.0   # must beat parent WR by 5 percentage points
FAIL_IF_WORSE = True              # mark failed if mutation WR < parent WR


# ════════════════════════════════════════════════════════════════════
# WORST STRATEGY SELECTOR
# ════════════════════════════════════════════════════════════════════

# The 10 worst strategies by impact (losses * trades), curated from
# LOW_CONFIDENCE_STRATEGIES comments in auto_tuner.py.
# Ordered by severity: most damaging first.
WORST_10_STRATEGIES = [
    {
        "name": "rapid_fire",
        "wr": 25.0, "trades": 152, "pf": 0.34, "pnl_note": "-429% PnL",
        "default_timeframe": "15m", "asset_class": "crypto",
    },
    {
        "name": "stocks_competition",
        "wr": 26.4, "trades": 174, "pf": None, "pnl_note": "system banned",
        "default_timeframe": "1d", "asset_class": "equity",
    },
    {
        "name": "winner_pattern_precursor",
        "wr": 20.0, "trades": 104, "pf": 0.379, "pnl_note": "consistently wrong",
        "default_timeframe": "1h", "asset_class": "crypto",
    },
    {
        "name": "smart_money_fvg",
        "wr": 0.0, "trades": 9, "pf": 0.0, "pnl_note": "-$928, -5.2% avg",
        "default_timeframe": "1h", "asset_class": "crypto",
    },
    {
        "name": "halloween_effect",
        "wr": 0.0, "trades": 5, "pf": 0.0, "pnl_note": "-$943, -9.4% avg",
        "default_timeframe": "1d", "asset_class": "crypto",
    },
    {
        "name": "fourier_cycle_detector",
        "wr": 0.0, "trades": 6, "pf": 0.0, "pnl_note": "-$935, ML total failure",
        "default_timeframe": "4h", "asset_class": "crypto",
    },
    {
        "name": "m2_liquidity_lag",
        "wr": 22.0, "trades": 9, "pf": None, "pnl_note": "-$879, -4.9% avg",
        "default_timeframe": "1d", "asset_class": "crypto",
    },
    {
        "name": "seasonal_factor_rotation",
        "wr": 0.0, "trades": 11, "pf": 0.0, "pnl_note": "-1.20% avg, 100% SL_HIT",
        "default_timeframe": "1d", "asset_class": "crypto",
    },
    {
        "name": "momentum_catcher",
        "wr": 43.0, "trades": 7, "pf": None, "pnl_note": "-131% PnL, wins tiny losses massive",
        "default_timeframe": "1h", "asset_class": "crypto",
    },
    {
        "name": "double_top_bottom_detector",
        "wr": 25.0, "trades": 4, "pf": None, "pnl_note": "-$1134, massive losses SOL/ETH",
        "default_timeframe": "4h", "asset_class": "crypto",
    },
]

# Timeframe shift map: current -> one step higher
TIMEFRAME_UP = {
    "5m": "15m", "15m": "1h", "1h": "4h", "4h": "1d", "1d": "1w",
}
TIMEFRAME_DOWN = {
    "1w": "1d", "1d": "4h", "4h": "1h", "1h": "15m", "15m": "5m",
}


# ════════════════════════════════════════════════════════════════════
# MUTATION GENERATORS
# ════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def inverse_signal(strategy: dict) -> dict:
    """Mutation type 1: Flip BUY->SELL, SELL->BUY (contrarian)."""
    name = strategy["name"]
    wr = strategy["wr"]
    return {
        "mutation_id": f"deep_inverse__{name}",
        "parent_strategy": name,
        "mutation_type": "inverse_signal",
        "parameters": {
            "flip_direction": True,
            "tp_multiplier": 1.0,
            "sl_multiplier": 1.0,
        },
        "created_at": _now_iso(),
        "status": "pending_validation",
        "expected_improvement": (
            f"Parent WR={wr}% — inverting should yield ~{100.0 - wr:.0f}% WR. "
            f"Low WR strategies are often anti-predictive; flipping captures the edge."
        ),
    }


def tighten_stops(strategy: dict, factor: float = 0.5) -> dict:
    """Mutation type 2: Halve the SL distance, keep TP."""
    name = strategy["name"]
    return {
        "mutation_id": f"deep_tightstop__{name}",
        "parent_strategy": name,
        "mutation_type": "tighten_stops",
        "parameters": {
            "flip_direction": False,
            "tp_multiplier": 1.0,
            "sl_multiplier": factor,
        },
        "created_at": _now_iso(),
        "status": "pending_validation",
        "expected_improvement": (
            f"SL cut to {factor:.0%} of original. Reduces max loss per trade. "
            f"If strategy has directional edge but wide stops, this recovers it."
        ),
    }


def widen_targets(strategy: dict, factor: float = 1.5) -> dict:
    """Mutation type 3: Increase TP by 50%."""
    name = strategy["name"]
    return {
        "mutation_id": f"deep_widetp__{name}",
        "parent_strategy": name,
        "mutation_type": "widen_targets",
        "parameters": {
            "flip_direction": False,
            "tp_multiplier": factor,
            "sl_multiplier": 1.0,
        },
        "created_at": _now_iso(),
        "status": "pending_validation",
        "expected_improvement": (
            f"TP widened to {factor:.0%} of original. Lets winners run further. "
            f"If WR is low but avg win is close to avg loss, wider TP can flip PnL positive."
        ),
    }


def regime_gate(strategy: dict, allowed_regimes: list[str] | None = None) -> dict:
    """Mutation type 4: Only trade in favorable market regime."""
    if allowed_regimes is None:
        allowed_regimes = ["bull"]
    name = strategy["name"]
    return {
        "mutation_id": f"deep_regime__{name}",
        "parent_strategy": name,
        "mutation_type": "regime_gate",
        "parameters": {
            "flip_direction": False,
            "tp_multiplier": 1.0,
            "sl_multiplier": 1.0,
            "allowed_regimes": allowed_regimes,
            "regime_indicator": "btc_20d_sma_trend",
        },
        "created_at": _now_iso(),
        "status": "pending_validation",
        "expected_improvement": (
            f"Only trade when market regime in {allowed_regimes}. "
            f"Many strategies fail in wrong regime (e.g., long-only in bear). "
            f"Filtering to favorable regime can dramatically improve WR."
        ),
    }


def timeframe_shift(strategy: dict, shift: str = "up") -> dict:
    """Mutation type 5: Move to higher (or lower) timeframe."""
    name = strategy["name"]
    current_tf = strategy.get("default_timeframe", "1h")
    tf_map = TIMEFRAME_UP if shift == "up" else TIMEFRAME_DOWN
    new_tf = tf_map.get(current_tf, current_tf)
    return {
        "mutation_id": f"deep_tfshift__{name}",
        "parent_strategy": name,
        "mutation_type": "timeframe_shift",
        "parameters": {
            "flip_direction": False,
            "tp_multiplier": 1.0,
            "sl_multiplier": 1.0,
            "original_timeframe": current_tf,
            "new_timeframe": new_tf,
            "shift_direction": shift,
        },
        "created_at": _now_iso(),
        "status": "pending_validation",
        "expected_improvement": (
            f"Shift from {current_tf} to {new_tf}. Higher timeframes reduce noise "
            f"and false signals. If strategy logic is sound but whipsawed on low TF, "
            f"this can recover the edge."
        ),
    }


# ════════════════════════════════════════════════════════════════════
# GENERATE ALL MUTATIONS
# ════════════════════════════════════════════════════════════════════

def generate_all_mutations() -> list[dict]:
    """Generate all 5 mutation types for each of the worst 10 strategies."""
    mutations = []
    for strat in WORST_10_STRATEGIES:
        mutations.append(inverse_signal(strat))
        mutations.append(tighten_stops(strat, factor=0.5))
        mutations.append(widen_targets(strat, factor=1.5))
        mutations.append(regime_gate(strat, allowed_regimes=["bull"]))
        mutations.append(timeframe_shift(strat, shift="up"))
    return mutations


def register_mutations(mutations: list[dict]) -> dict:
    """
    Register mutations in strategy_mutations.json.
    Preserves existing data; merges new mutations by mutation_id.
    Returns the full registry.
    """
    # Load existing
    registry = {"timestamp": _now_iso(), "mutations": [], "bottom_5": [], "top_5": []}
    if MUTATION_REGISTRY_PATH.exists():
        try:
            with open(MUTATION_REGISTRY_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
            # Preserve top-level fields from existing file
            registry.update(existing)
        except Exception as e:
            print(f"[WARN] Could not load existing registry: {e}")

    # Build index of existing deep mutations by mutation_id
    deep_key = "deep_mutations"
    existing_deep = {m["mutation_id"]: m for m in registry.get(deep_key, [])}

    # Merge: new mutations overwrite by mutation_id, preserving status if already validated
    for mut in mutations:
        mid = mut["mutation_id"]
        if mid in existing_deep:
            old = existing_deep[mid]
            # Don't overwrite if already validated or failed
            if old.get("status") in ("validated", "failed"):
                continue
        existing_deep[mid] = mut

    registry[deep_key] = list(existing_deep.values())
    registry["timestamp"] = _now_iso()
    registry["deep_mutation_count"] = len(registry[deep_key])
    registry["deep_mutation_summary"] = {
        "total": len(registry[deep_key]),
        "pending": sum(1 for m in registry[deep_key] if m["status"] == "pending_validation"),
        "validated": sum(1 for m in registry[deep_key] if m["status"] == "validated"),
        "failed": sum(1 for m in registry[deep_key] if m["status"] == "failed"),
    }

    # Write
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MUTATION_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"[REGISTRY] Wrote {len(registry[deep_key])} deep mutations to {MUTATION_REGISTRY_PATH.name}")
    return registry


# ════════════════════════════════════════════════════════════════════
# EVALUATE MUTATIONS (forward-test validation)
# ════════════════════════════════════════════════════════════════════

def _load_closed_picks() -> list:
    """Load closed picks from dashboard payload or fallback."""
    if DASHBOARD_PAYLOAD_PATH.exists():
        try:
            with open(DASHBOARD_PAYLOAD_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            picks = data.get("picks", {}).get("recent_closed", [])
            if picks:
                return picks
        except Exception:
            pass
    if CLOSED_PICKS_PATH.exists():
        try:
            with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _compute_strategy_wr(picks: list, strategy_name: str) -> tuple[float, int]:
    """Compute win rate and trade count for a strategy from closed picks."""
    strat_picks = [
        p for p in picks
        if p.get("strategy") == strategy_name
        and p.get("status") in ("WON", "LOST", "STOPPED")
    ]
    if not strat_picks:
        return 0.0, 0
    wins = sum(1 for p in strat_picks if p.get("status") == "WON" or (p.get("pnl_pct") or 0) > 0)
    wr = (wins / len(strat_picks)) * 100.0
    return round(wr, 1), len(strat_picks)


def evaluate_mutations(closed_picks: list | None = None) -> dict:
    """
    Evaluate active deep mutations against forward-test results.

    For each mutation with status "pending_validation":
      - Check if it has 10+ closed trades (by mutation_id as strategy name)
      - Compare WR to parent strategy WR
      - If mutation WR > parent WR + 5pp -> "validated"
      - If mutation WR < parent WR -> "failed"

    Returns dict with evaluation summary.
    """
    if closed_picks is None:
        closed_picks = _load_closed_picks()

    if not MUTATION_REGISTRY_PATH.exists():
        return {"error": "No mutation registry found", "evaluated": 0}

    with open(MUTATION_REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    deep_mutations = registry.get("deep_mutations", [])
    if not deep_mutations:
        return {"error": "No deep mutations registered", "evaluated": 0}

    # Group closed picks by strategy
    picks_by_strategy = defaultdict(list)
    for p in closed_picks:
        s = p.get("strategy", "unknown")
        picks_by_strategy[s].append(p)

    # Also compute parent strategy WR from the WORST_10 data
    parent_wr_map = {s["name"]: s["wr"] for s in WORST_10_STRATEGIES}

    results = {
        "evaluated_at": _now_iso(),
        "total_mutations": len(deep_mutations),
        "evaluated": 0,
        "promoted": 0,
        "failed": 0,
        "pending": 0,
        "details": [],
    }

    for mut in deep_mutations:
        if mut["status"] != "pending_validation":
            # Already resolved
            continue

        mid = mut["mutation_id"]
        parent = mut["parent_strategy"]
        parent_wr = parent_wr_map.get(parent, 0.0)

        # Check if mutation has been traded (mutation_id used as strategy name)
        mut_wr, mut_trades = _compute_strategy_wr(closed_picks, mid)

        detail = {
            "mutation_id": mid,
            "parent_strategy": parent,
            "parent_wr": parent_wr,
            "mutation_wr": mut_wr,
            "mutation_trades": mut_trades,
            "action": "waiting",
        }

        if mut_trades < MIN_TRADES_FOR_EVAL:
            detail["action"] = f"waiting ({mut_trades}/{MIN_TRADES_FOR_EVAL} trades)"
            results["pending"] += 1
        elif mut_wr >= parent_wr + PROMOTE_WR_IMPROVEMENT_PP:
            mut["status"] = "validated"
            mut["validated_at"] = _now_iso()
            mut["validation_wr"] = mut_wr
            mut["validation_trades"] = mut_trades
            detail["action"] = "PROMOTED"
            results["promoted"] += 1
            results["evaluated"] += 1
        elif FAIL_IF_WORSE and mut_wr < parent_wr:
            mut["status"] = "failed"
            mut["failed_at"] = _now_iso()
            mut["fail_wr"] = mut_wr
            mut["fail_trades"] = mut_trades
            detail["action"] = "FAILED"
            results["failed"] += 1
            results["evaluated"] += 1
        else:
            # WR improved but not by 5pp — keep pending
            detail["action"] = f"inconclusive (WR {mut_wr}% vs parent {parent_wr}%)"
            results["pending"] += 1

        results["details"].append(detail)

    # Update registry summary
    registry["deep_mutation_summary"] = {
        "total": len(deep_mutations),
        "pending": sum(1 for m in deep_mutations if m["status"] == "pending_validation"),
        "validated": sum(1 for m in deep_mutations if m["status"] == "validated"),
        "failed": sum(1 for m in deep_mutations if m["status"] == "failed"),
    }
    registry["timestamp"] = _now_iso()

    # Save updated registry
    with open(MUTATION_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    # Save evaluation report
    with open(DEEP_MUTATION_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[EVAL] Evaluated {results['evaluated']} mutations: "
          f"{results['promoted']} promoted, {results['failed']} failed, "
          f"{results['pending']} pending")

    return results


# ════════════════════════════════════════════════════════════════════
# MAIN — Generate & register mutations, then evaluate
# ════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("DEEP MUTATION ENGINE — Mutate Before Kill")
    print(f"Timestamp: {_now_iso()}")
    print("=" * 70)

    # Step 1: Generate all 5 mutation types for worst 10 strategies
    mutations = generate_all_mutations()
    print(f"\n[GEN] Generated {len(mutations)} mutations for {len(WORST_10_STRATEGIES)} strategies")

    # Log summary by type
    by_type = defaultdict(int)
    for m in mutations:
        by_type[m["mutation_type"]] += 1
    for mtype, count in sorted(by_type.items()):
        print(f"  {mtype}: {count}")

    # Step 2: Register in strategy_mutations.json
    registry = register_mutations(mutations)

    # Step 3: Evaluate existing mutations against forward-test data
    print("\n[EVAL] Evaluating mutations against closed picks...")
    results = evaluate_mutations()

    # Step 4: Print summary
    summary = registry.get("deep_mutation_summary", {})
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"  Total deep mutations: {summary.get('total', 0)}")
    print(f"  Pending validation:   {summary.get('pending', 0)}")
    print(f"  Validated (promoted): {summary.get('validated', 0)}")
    print(f"  Failed:               {summary.get('failed', 0)}")
    print(f"{'=' * 70}")

    return registry


if __name__ == "__main__":
    main()
