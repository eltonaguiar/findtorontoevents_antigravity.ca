#!/usr/bin/env python3
"""
Phase 7: TradingView Paper Trading Deployment

Deploys active picks to SCALPER, TESTER, TRUSTOURSCORE paper accounts.
Implements mandatory TP/SL verification per tv-paper-trade skill guidelines.

Deployment strategy:
- SCALPER (high-conf, tight stops): Picks with confidence >= 0.80, elite_grade A/B
- TESTER (experimental): Picks with confidence 0.70-0.79, elite_grade C/D
- TRUSTOURSCORE (verified): Picks with confidence >= 0.75 AND historical_wr >= 0.60

Gate: NEVER execute order without confirmed TP/SL set at correct side.
TP/SL side sanity:
  - LONG: TP > entry > SL
  - SHORT: SL > entry > TP

If any verification fails, skip that trade and log reason.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────

ACCOUNTS = {
    "SCALPER": {
        "balance_approx": 2000,
        "filter": lambda p: p.get("confidence", 0) >= 0.80 and p.get("elite_grade") in ["A", "B"],
        "max_picks": 5,
        "position_size_pct": 4,
        "description": "High-confidence, tight stops"
    },
    "TESTER": {
        "balance_approx": 3000,
        "filter": lambda p: 0.70 <= p.get("confidence", 0) < 0.80,
        "max_picks": 5,
        "position_size_pct": 3,
        "description": "Experimental, SHORT bias"
    },
    "TRUSTOURSCORE": {
        "balance_approx": 90000,
        "filter": lambda p: p.get("confidence", 0) >= 0.75 and p.get("historical_wr", 0) >= 0.60,
        "max_picks": 10,
        "position_size_pct": 5,
        "description": "Verified alpha, highest conviction"
    }
}


# ────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────

def normalize_wr(value: object) -> float | None:
    """Convert WR to 0..1 range if stored as percentage."""
    try:
        f = float(value or 0)
        if f > 1.5:  # Likely stored as percentage
            return f / 100.0
        return f
    except (TypeError, ValueError):
        return None


def validate_tp_sl_side(direction: str, entry: float, tp: float, sl: float) -> tuple[bool, str]:
    """
    Validate TP/SL are on correct side of entry.

    Returns: (is_valid, error_message)
    """
    if direction.upper() in ("BUY", "LONG"):
        if not (tp > entry > sl):
            return False, f"LONG side fail: TP({tp}) must be > entry({entry}) > SL({sl})"
        return True, ""
    elif direction.upper() in ("SELL", "SHORT"):
        if not (sl > entry > tp):
            return False, f"SHORT side fail: SL({sl}) must be > entry({entry}) > TP({tp})"
        return True, ""
    return False, f"Unknown direction: {direction}"


def filter_picks_for_account(picks: list, account_name: str) -> list:
    """Filter picks matching account criteria."""
    account_cfg = ACCOUNTS.get(account_name, {})
    filter_fn = account_cfg.get("filter", lambda p: True)
    max_picks = account_cfg.get("max_picks", 9999)

    matching = [p for p in picks if filter_fn(p)]
    return matching[:max_picks]


def calculate_position_size(balance: float, pick_confidence: float, pct_default: float) -> float:
    """
    Calculate position size as % of balance.

    Adjust based on confidence:
    - High conf (0.85+): +10% premium
    - Medium conf (0.75-0.84): default
    - Low conf (0.70-0.74): -20% penalty
    """
    if pick_confidence >= 0.85:
        multiplier = 1.1
    elif pick_confidence < 0.75:
        multiplier = 0.8
    else:
        multiplier = 1.0

    return balance * (pct_default / 100.0) * multiplier


# ────────────────────────────────────────────────────────────────
# DEPLOYMENT
# ────────────────────────────────────────────────────────────────

def load_active_picks() -> list:
    """Load active picks from dashboard data."""
    try:
        with open("alpha_engine/data/active_picks.json", "r") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data.get("picks", [])
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[ERROR] Failed to load active_picks.json: {e}")
        return []


def build_deployment_plan(picks: list) -> dict:
    """
    Build per-account deployment plan.

    Returns: {"account_name": [{"pick": {}, "position_size_pct": float, "reason": str}, ...]}
    """
    plan = {}

    for account_name, account_cfg in ACCOUNTS.items():
        matching_picks = filter_picks_for_account(picks, account_name)
        plan[account_name] = []

        for pick in matching_picks:
            confidence = pick.get("confidence", 0)
            entry = pick.get("entry_price")
            tp = pick.get("take_profit")
            sl = pick.get("stop_loss")
            direction = pick.get("direction", "")

            # Validation checks
            if not all([entry, tp, sl]):
                plan[account_name].append({
                    "pick": pick,
                    "valid": False,
                    "reason": f"Missing TP/SL: entry={entry}, tp={tp}, sl={sl}"
                })
                continue

            is_valid, error = validate_tp_sl_side(direction, entry, tp, sl)
            if not is_valid:
                plan[account_name].append({
                    "pick": pick,
                    "valid": False,
                    "reason": error
                })
                continue

            balance = account_cfg["balance_approx"]
            pos_size = calculate_position_size(balance, confidence, account_cfg["position_size_pct"])

            reason = f"Tier: {pick.get('elite_grade', '?')} | Conf: {confidence:.2f} | " \
                     f"Size: {pos_size:.1f}% ({account_cfg['position_size_pct']}% base * " \
                     f"{'1.1' if confidence >= 0.85 else '0.8' if confidence < 0.75 else '1.0'} conf multiplier)"

            plan[account_name].append({
                "pick": pick,
                "valid": True,
                "position_size_pct": pos_size,
                "reason": reason
            })

    return plan


def format_deployment_report(plan: dict, picks: list) -> str:
    """Format deployment plan as readable report."""
    lines = [
        "=" * 80,
        "PHASE 7: TradingView Paper Trading Deployment Plan",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 80,
        f"\nTotal active picks available: {len(picks)}",
        ""
    ]

    total_trades = 0
    for account_name, trades in plan.items():
        valid_trades = [t for t in trades if t.get("valid")]
        lines.append(f"\n{'─' * 80}")
        lines.append(f"Account: {account_name}")
        lines.append(f"Balance (approx): ${ACCOUNTS[account_name]['balance_approx']:,}")
        lines.append(f"Description: {ACCOUNTS[account_name]['description']}")
        lines.append(f"Deployable trades: {len(valid_trades)}/{len(trades)}")
        lines.append(f"{'─' * 80}")

        if not valid_trades:
            lines.append("  [No matching picks]")
            continue

        for i, trade in enumerate(valid_trades, 1):
            pick = trade["pick"]
            lines.append(f"\n  Trade {i}: {pick.get('symbol')}")
            lines.append(f"    Strategy: {pick.get('strategy')}")
            lines.append(f"    Direction: {pick.get('direction')}")
            lines.append(f"    Entry: {pick.get('entry_price')}")
            lines.append(f"    TP: {pick.get('take_profit')}")
            lines.append(f"    SL: {pick.get('stop_loss')}")
            lines.append(f"    Confidence: {pick.get('confidence', 0):.2f}")
            lines.append(f"    Elite Grade: {pick.get('elite_grade', '?')}")
            lines.append(f"    Position Size: {trade.get('position_size_pct', 0):.1f}%")
            lines.append(f"    Justification: {trade.get('reason', 'N/A')}")
            total_trades += 1

        # Invalid trades summary
        invalid_trades = [t for t in trades if not t.get("valid")]
        if invalid_trades:
            lines.append(f"\n  [SKIPPED: {len(invalid_trades)} trades]")
            for trade in invalid_trades:
                lines.append(f"    - {trade['pick'].get('symbol')}: {trade.get('reason', 'unknown')}")

    lines.extend([
        "",
        "=" * 80,
        f"DEPLOYMENT SUMMARY",
        f"{'─' * 80}",
        f"Total valid trades ready: {total_trades}",
        f"Execution order: Place trades in account order (SCALPER → TESTER → TRUSTOURSCORE)",
        "",
        "CRITICAL GATES (tv-paper-trade skill):",
        "  1. ✓ Account verified before each trade (DOM switch + name check)",
        "  2. ✓ TP/SL side-sanity checked (LONG: TP>entry>SL, SHORT: SL>entry>TP)",
        "  3. ✓ Every position has TP/SL set before order execution",
        "  4. ✓ Post-execution: Audit position TP/SL columns populated",
        "  5. ✓ If violation detected: Click Protect Position to set missing TP/SL",
        "",
        "Next: Connect to TradingView, open trading panel, and execute in sequence.",
        "=" * 80,
    ])

    return "\n".join(lines)


def save_deployment_plan(plan: dict, picks: list):
    """Save plan to JSON and text for reference."""
    # JSON
    with open("alpha_engine/data/phase7_deployment_plan.json", "w") as f:
        plan_serializable = {}
        for account, trades in plan.items():
            plan_serializable[account] = [
                {
                    "symbol": t["pick"].get("symbol"),
                    "direction": t["pick"].get("direction"),
                    "entry_price": t["pick"].get("entry_price"),
                    "take_profit": t["pick"].get("take_profit"),
                    "stop_loss": t["pick"].get("stop_loss"),
                    "confidence": t["pick"].get("confidence"),
                    "position_size_pct": t.get("position_size_pct"),
                    "reason": t.get("reason"),
                    "valid": t.get("valid"),
                }
                for t in trades
            ]
        json.dump(plan_serializable, f, indent=2)

    # Text report
    report = format_deployment_report(plan, picks)
    with open("alpha_engine/data/phase7_deployment_report.txt", "w") as f:
        f.write(report)

    print(report)
    print(f"\n[SAVED] alpha_engine/data/phase7_deployment_plan.json")
    print(f"[SAVED] alpha_engine/data/phase7_deployment_report.txt")


def main():
    print("\nPhase 7: TradingView Deployment Preparation")
    print("=" * 80)

    # Load picks
    picks = load_active_picks()
    if not picks:
        print("[ERROR] No active picks loaded")
        return 1

    print(f"[LOADED] {len(picks)} active picks from dashboard")

    # Build plan
    plan = build_deployment_plan(picks)

    # Save & display
    save_deployment_plan(plan, picks)

    # Count valid trades
    valid_total = sum(len([t for t in trades if t.get("valid")]) for trades in plan.values())
    print(f"\n[READY] {valid_total} trades queued for TradingView deployment")
    print("[NEXT] Execute trades via tv-paper-trade skill with mandatory TP/SL verification")
    print("[GATE] Verify account before EACH trade (use DOM account switch, not coordinates)")
    print("[GATE] Check TP/SL side-sanity BEFORE clicking Buy/Sell")
    print("[GATE] Audit each filled position has TP/SL columns populated")

    return 0


if __name__ == "__main__":
    sys.exit(main())
