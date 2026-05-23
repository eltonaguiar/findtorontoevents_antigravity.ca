"""
pick_accelerator.py -- Alpha Engine ML Training Accelerator
============================================================
Accelerates the path from 2 closed picks → 50 closed picks to unlock
ML auto-training (Random Forest). Three strategies:

1. TURBO TP/SL -- Tighter take-profit/stop-loss for crypto+meme to get
   faster feedback loops (3-day max hold, ±5% TP/SL for crypto)
2. REGIME INJECTION -- Read HMM regime data and inject into scanner context
3. PICK VELOCITY -- Track closed-pick accumulation rate and ETA to ML unlock

Usage:
  python -m alpha_engine.pick_accelerator --status     # Check progress
  python -m alpha_engine.pick_accelerator --apply      # Apply turbo params
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dump never emits invalid tokens."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
ACTIVE_PICKS = DATA_DIR / "active_picks.json"
CLOSED_PICKS = DATA_DIR / "closed_picks.json"
STRATEGY_PERF = DATA_DIR / "strategy_performance.json"
HMM_REGIME = DATA_DIR / "hmm_regime.json"
ML_MODEL = DATA_DIR / "rf_model.pkl"
ACCELERATOR_STATE = DATA_DIR / "accelerator_state.json"

ML_TRAINING_THRESHOLD = 50


# ---------------------------------------------------------------------------
# 1. Turbo Risk Parameters
# ---------------------------------------------------------------------------
# These tighter params give faster feedback:
# - Crypto: TP 12% → 6%, SL 8% → 4%, max hold 7d → 3d
# - Meme:   TP 35% → 15%, SL 15% → 8%, max hold 5d → 2d
# - Forex:  TP 5% → 3%, SL 2.5% → 1.5%, max hold 10d → 5d
# - Stock:  TP 12% → 7%, SL 6% → 3.5%, max hold 10d → 5d
# - Penny:  TP 25% → 12%, SL 12% → 6%, max hold 7d → 3d

TURBO_RISK = {
    "crypto":  {"stop_loss": -0.04, "take_profit": 0.06, "max_hold": 3},
    "meme":    {"stop_loss": -0.08, "take_profit": 0.15, "max_hold": 2},
    "penny":   {"stop_loss": -0.06, "take_profit": 0.12, "max_hold": 3},
    "forex":   {"stop_loss": -0.002, "take_profit": 0.003, "max_hold": 3},
    "stock":   {"stop_loss": -0.035, "take_profit": 0.07, "max_hold": 5},
}

# Original (normal) risk params for reference
NORMAL_RISK = {
    "crypto":  {"stop_loss": -0.08, "take_profit": 0.20, "max_hold": 7},
    "meme":    {"stop_loss": -0.15, "take_profit": 0.35, "max_hold": 5},
    "penny":   {"stop_loss": -0.12, "take_profit": 0.25, "max_hold": 7},
    "forex":   {"stop_loss": -0.002, "take_profit": 0.003, "max_hold": 5},
    "stock":   {"stop_loss": -0.06, "take_profit": 0.12, "max_hold": 10},
}


def get_ml_status() -> dict:
    """Check current ML training status and progress."""
    # Count closed picks
    closed = []
    if CLOSED_PICKS.exists():
        with open(CLOSED_PICKS) as f:
            closed = json.load(f)

    active = []
    if ACTIVE_PICKS.exists():
        with open(ACTIVE_PICKS) as f:
            active = json.load(f)

    n_closed = len(closed)
    n_active = len(active)
    n_remaining = max(0, ML_TRAINING_THRESHOLD - n_closed)

    # Calculate velocity (picks closed per day)
    if len(closed) >= 2:
        dates = []
        for p in closed:
            d = p.get("exit_date")
            if d:
                try:
                    dates.append(datetime.strptime(d, "%Y-%m-%d"))
                except (ValueError, TypeError):
                    pass
        if len(dates) >= 2:
            dates.sort()
            span_days = max((dates[-1] - dates[0]).days, 1)
            velocity = len(dates) / span_days
        else:
            velocity = 0.5  # assume 0.5/day if can't compute
    else:
        velocity = 0.5

    # ETA to ML training
    eta_days = round(n_remaining / velocity) if velocity > 0 else 999

    # Win/loss stats -- check both status field (SQLite uses WON/LOST)
    # and pnl_pct (JSON pipeline sets status="closed"/"expired", so use pnl_pct > 0)
    wins = 0
    losses = 0
    for p in closed:
        st = p.get("status", "")
        if st == "WON":
            wins += 1
        elif st == "LOST":
            losses += 1
        else:
            # JSON pipeline: status is "closed", "expired", etc.
            # Determine win/loss from realized PnL
            pnl = float(p.get("pnl_pct", 0) or 0) or 0
            if pnl > 0:
                wins += 1
            else:
                losses += 1

    # ML model status
    ml_trained = ML_MODEL.exists()

    return {
        "closed_picks": n_closed,
        "active_picks": n_active,
        "remaining_for_ml": n_remaining,
        "velocity_per_day": round(velocity, 2),
        "eta_days": eta_days,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / n_closed, 4) if n_closed > 0 else 0,
        "ml_trained": ml_trained,
        "ml_threshold": ML_TRAINING_THRESHOLD,
        "pct_complete": round(min(n_closed / ML_TRAINING_THRESHOLD * 100, 100), 1),
    }


def apply_turbo_to_active_picks():
    """
    Apply tighter TP/SL to currently active picks to accelerate closure.
    Only tightens -- never loosens existing TP/SL.
    """
    if not ACTIVE_PICKS.exists():
        print("  No active picks to accelerate.")
        return 0

    with open(ACTIVE_PICKS) as f:
        picks = json.load(f)

    modified = 0
    for pick in picks:
        cat = pick.get("category", "crypto")
        turbo = TURBO_RISK.get(cat)
        if not turbo:
            continue

        entry_price = pick.get("entry_price", 0)
        if entry_price <= 0:
            continue

        signal_type = pick.get("signal_type", "BUY")

        # Compute turbo TP/SL prices
        if signal_type == "BUY":
            turbo_tp = entry_price * (1 + turbo["take_profit"])
            turbo_sl = entry_price * (1 + turbo["stop_loss"])
        else:
            turbo_tp = entry_price * (1 - turbo["take_profit"])
            turbo_sl = entry_price * (1 - turbo["stop_loss"])

        changed = False

        # Only TIGHTEN TP (bring closer to entry)
        current_tp = pick.get("take_profit")
        if current_tp is not None and signal_type == "BUY":
            if turbo_tp < current_tp:
                pick["take_profit"] = round(turbo_tp, 8)
                pick["turbo_adjusted"] = True
                changed = True
        elif current_tp is not None and signal_type == "SELL":
            if turbo_tp > current_tp:
                pick["take_profit"] = round(turbo_tp, 8)
                pick["turbo_adjusted"] = True
                changed = True

        # Only TIGHTEN SL (bring closer to entry)
        current_sl = pick.get("stop_loss")
        if current_sl is not None and signal_type == "BUY":
            if turbo_sl > current_sl:
                pick["stop_loss"] = round(turbo_sl, 8)
                pick["turbo_adjusted"] = True
                changed = True
        elif current_sl is not None and signal_type == "SELL":
            if turbo_sl < current_sl:
                pick["stop_loss"] = round(turbo_sl, 8)
                pick["turbo_adjusted"] = True
                changed = True

        if changed:
            modified += 1

    # Save updated picks (sanitize NaN/Infinity → null for valid JSON)
    with open(ACTIVE_PICKS, "w") as f:
        json.dump(_sanitize_for_json(picks), f, indent=2)

    return modified


def load_hmm_regime() -> dict:
    """Load HMM regime data for injection into scanner context."""
    if not HMM_REGIME.exists():
        return {}
    with open(HMM_REGIME) as f:
        return json.load(f)


def get_regime_for_symbol(symbol: str) -> dict:
    """Get HMM regime data for a specific symbol."""
    hmm = load_hmm_regime()
    per_symbol = hmm.get("per_symbol", {})

    if symbol in per_symbol:
        return per_symbol[symbol]

    # Fallback to aggregate regime
    agg = hmm.get("aggregate", {})
    return {
        "regime": "Chop/Neutral",
        "kimi_regime": agg.get("market_regime", "neutral"),
        "alpha_regime": "ranging",
        "confidence": agg.get("hmm_confidence", 0.5),
        "leverage": 1.0,
        "signal": "FLAT",
    }


def should_use_turbo() -> bool:
    """Determine if turbo mode should be active."""
    status = get_ml_status()
    # Use turbo until ML is trained
    return not status["ml_trained"] and status["closed_picks"] < ML_TRAINING_THRESHOLD


def save_accelerator_state(status: dict):
    """Save accelerator state for dashboard tracking."""
    state = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "turbo_active": should_use_turbo(),
        **status,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACCELERATOR_STATE, "w") as f:
        json.dump(_sanitize_for_json(state), f, indent=2)


def print_status():
    """Print ML training progress."""
    status = get_ml_status()

    print("=" * 60)
    print("  ALPHA ENGINE -- ML Training Accelerator")
    print("=" * 60)

    bar_len = 30
    filled = int(bar_len * status["pct_complete"] / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"\n  ML Training Progress: [{bar}] {status['pct_complete']}%")
    print(f"  Closed Picks:    {status['closed_picks']}/{status['ml_threshold']}")
    print(f"  Active Picks:    {status['active_picks']}")
    print(f"  Remaining:       {status['remaining_for_ml']}")
    print(f"  Velocity:        {status['velocity_per_day']} picks/day")
    print(f"  ETA to ML:       ~{status['eta_days']} days")
    print(f"  Win Rate:        {status['win_rate']*100:.1f}%")
    print(f"  ML Trained:      {'YES' if status['ml_trained'] else 'NO (heuristic mode)'}")
    print(f"  Turbo Mode:      {'ACTIVE' if should_use_turbo() else 'OFF (ML trained)'}")

    save_accelerator_state(status)
    print("\n" + "=" * 60)
    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Alpha Engine ML Accelerator")
    parser.add_argument("--status", action="store_true", help="Show ML training progress")
    parser.add_argument("--apply", action="store_true", help="Apply turbo TP/SL to active picks")
    args = parser.parse_args()

    if args.status or (not args.apply):
        print_status()

    if args.apply:
        if should_use_turbo():
            n = apply_turbo_to_active_picks()
            print(f"  Turbo applied to {n} picks")
            print_status()
        else:
            print("  Turbo mode OFF -- ML already trained!")


if __name__ == "__main__":
    main()
