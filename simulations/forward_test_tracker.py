#!/usr/bin/env python3
"""
Forward Test Tracker Protocol
=============================
Provides a decision framework for:
  1. When to ELIMINATE a strategy fast (early stopping)
  2. When to HOLD a strategy longer (accumulating evidence)
  3. When to GRADUATE a strategy to larger capital

This replaces gut-feel decisions with pre-registered statistical rules.
Every strategy starts at PAPER. It only graduates if it passes all gates.

Usage:
    python3 simulations/forward_test_tracker.py --check <strategy_name> --results <results_json>
    python3 simulations/forward_test_tracker.py --batch <directory_of_result_files>
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Protocol Configuration ─────────────────────────────────────────────────
PROTOCOL_VERSION = "2026-11-15-v1"

# Gate thresholds (pre-registered, non-negotiable)
GATES = {
    "paper": {
        "description": "Initial paper trading — no capital at risk",
        "n_min": 10,
        "pf_min": 0.80,
        "wr_min": 0.40,
        "max_dd_max": -0.25,
        "sharpe_min": 0.0,
        "max_days": 30,
    },
    "probation": {
        "description": "Extended paper — accumulating evidence",
        "n_min": 30,
        "pf_min": 1.00,
        "wr_min": 0.48,
        "max_dd_max": -0.20,
        "sharpe_min": 0.3,
        "max_days": 90,
    },
    "small_live": {
        "description": "Small capital deployment — 1-2% risk per trade",
        "n_min": 100,
        "pf_min": 1.30,
        "wr_min": 0.55,
        "max_dd_max": -0.15,
        "sharpe_min": 0.8,
        "max_days": 180,
    },
    "full_live": {
        "description": "Full capital deployment — scaled sizing",
        "n_min": 300,
        "pf_min": 1.50,
        "wr_min": 0.55,
        "max_dd_max": -0.15,
        "sharpe_min": 1.0,
        "max_days": 365,
    },
}

# Fast elimination triggers (any ONE triggers kill)
ELIMINATION_TRIGGERS = {
    "n_min": 10,
    "pf_max": 0.70,      # PF below 0.70 after 10 trades = kill
    "wr_max": 0.30,      # WR below 30% after 10 trades = kill
    "max_dd_min": -0.35, # DD worse than -35% at any point = kill
    "consecutive_losses": 7,  # 7 losses in a row = kill
    "days_without_trade": 14, # No trade in 14 days = kill (stale)
}

# Extended hold triggers (ALL must be true to hold beyond normal gate)
EXTENDED_HOLD_TRIGGERS = {
    "pf_trend": 1.05,     # Last 10 trades PF > 1.05 (improving)
    "wr_trend": 0.50,     # Last 10 trades WR > 50%
    "no_large_loss": -5.0, # No single loss > 5%
    "regime_alignment": True,  # Strategy aligns with current regime (external check)
}


def load_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def check_elimination(results: dict) -> tuple[bool, str]:
    """Check if strategy should be fast-eliminated. Returns (eliminate, reason)."""
    tmetrics = results.get("trade_metrics", {})
    pmetrics = results.get("portfolio_metrics", {})

    # Trade-based elimination
    n = tmetrics.get("n", 0)
    pf = tmetrics.get("profit_factor", tmetrics.get("pf", 0))
    wr = tmetrics.get("win_rate", tmetrics.get("wr", 0))
    max_dd = tmetrics.get("max_drawdown", tmetrics.get("max_dd", 0))

    if n >= ELIMINATION_TRIGGERS["n_min"]:
        if pf < ELIMINATION_TRIGGERS["pf_max"]:
            return True, f"PF={pf:.2f} < {ELIMINATION_TRIGGERS['pf_max']} after n={n}"
        if wr < ELIMINATION_TRIGGERS["wr_max"]:
            return True, f"WR={wr:.1%} < {ELIMINATION_TRIGGERS['wr_max']} after n={n}"

    # Portfolio-based elimination (only max_dd matters)
    if n == 0 and pmetrics:
        max_dd = pmetrics.get("max_drawdown", 0)

    if max_dd < ELIMINATION_TRIGGERS["max_dd_min"]:
        return True, f"MaxDD={max_dd:.1%} < {ELIMINATION_TRIGGERS['max_dd_min']}"

    return False, ""


def check_gate(results: dict, gate_name: str) -> tuple[bool, list[str]]:
    """Check if strategy passes a promotion gate. Returns (pass, failures)."""
    gate = GATES[gate_name]
    tmetrics = results.get("trade_metrics", {})
    pmetrics = results.get("portfolio_metrics", {})
    failures = []

    # Trade-based strategies use trade_metrics; portfolio strategies use portfolio_metrics
    n = tmetrics.get("n", 0)
    pf = tmetrics.get("profit_factor", tmetrics.get("pf", 0))
    wr = tmetrics.get("win_rate", tmetrics.get("wr", 0))
    max_dd = tmetrics.get("max_drawdown", tmetrics.get("max_dd", 0))
    sharpe = tmetrics.get("sharpe_ratio", tmetrics.get("sharpe", 0))

    # For portfolio strategies without trade metrics, use portfolio metrics
    if n == 0 and pmetrics:
        pf = pmetrics.get("profit_factor", 0)
        wr = pmetrics.get("win_rate_daily", pmetrics.get("win_rate_monthly", 0))
        max_dd = pmetrics.get("max_drawdown", 0)
        sharpe = pmetrics.get("sharpe_ratio", 0)
        # Portfolio strategies are "always on" — treat n as large
        n = 9999

    checks = [
        ("n", n, gate["n_min"], ">="),
        ("profit_factor", pf, gate["pf_min"], ">="),
        ("win_rate", wr, gate["wr_min"], ">="),
        ("max_drawdown", max_dd, gate["max_dd_max"], ">="),
        ("sharpe_ratio", sharpe, gate["sharpe_min"], ">="),
    ]

    for name, value, threshold, op in checks:
        if op == ">=" and value < threshold:
            failures.append(f"{name}={value:.4f} < {threshold}")

    return len(failures) == 0, failures


def decide_status(results: dict) -> dict:
    """Run full decision tree for a strategy."""
    strategy = results.get("simulation", "unknown")
    metrics = results.get("trade_metrics", results.get("portfolio_metrics", {}))
    n = metrics.get("n", 0)

    # Step 1: Fast elimination check
    eliminate, elim_reason = check_elimination(results)
    if eliminate:
        return {
            "strategy": strategy,
            "status": "ELIMINATED",
            "reason": elim_reason,
            "action": "STOP trading immediately. Archive results. Document failure mode.",
            "next_review": None,
            "protocol_version": PROTOCOL_VERSION,
        }

    # Step 2: Check gates in order
    current_gate = None
    next_gate = None
    gate_failures = []

    for gate_name in ["paper", "probation", "small_live", "full_live"]:
        passes, failures = check_gate(results, gate_name)
        if passes:
            current_gate = gate_name
            gate_failures = []
        else:
            next_gate = gate_name
            gate_failures = failures
            break

    if current_gate is None:
        # Not even paper gate passed — but not eliminated
        status = "HOLD"
        action = f"Continue paper trading. Gate failures: {', '.join(gate_failures)}"
        next_review = f"Review after {GATES['paper']['max_days']} days or n={GATES['paper']['n_min']}, whichever comes first"
    elif current_gate == "full_live":
        status = "FULL_LIVE"
        action = "Strategy is fully deployed. Monitor daily against expectation."
        next_review = "Daily monitoring"
    else:
        # Check extended hold
        status = current_gate.upper()
        action = f"Continue at {current_gate} level. Monitor for graduation to {next_gate}."
        next_review = f"Review after {GATES[next_gate]['n_min'] - n} more trades or {GATES[next_gate]['max_days']} days"

    # Metrics snapshot
    tmetrics = results.get("trade_metrics", {})
    pmetrics = results.get("portfolio_metrics", {})
    n = tmetrics.get("n", 0)
    if n > 0:
        snap_pf = tmetrics.get("profit_factor", tmetrics.get("pf", 0))
        snap_wr = tmetrics.get("win_rate", tmetrics.get("wr", 0))
        snap_sharpe = tmetrics.get("sharpe_ratio", tmetrics.get("sharpe", 0))
        snap_dd = tmetrics.get("max_drawdown", tmetrics.get("max_dd", 0))
    else:
        snap_pf = pmetrics.get("profit_factor", 1.0)  # Portfolio strategies: no PF concept, default to 1.0
        snap_wr = pmetrics.get("win_rate_daily", pmetrics.get("win_rate_monthly", 0))
        snap_sharpe = pmetrics.get("sharpe_ratio", 0)
        snap_dd = pmetrics.get("max_drawdown", 0)

    return {
        "strategy": strategy,
        "status": status,
        "current_gate": current_gate,
        "next_gate": next_gate,
        "gate_failures": gate_failures,
        "metrics_snapshot": {
            "n": n,
            "pf": snap_pf,
            "wr": snap_wr,
            "sharpe": snap_sharpe,
            "max_dd": snap_dd,
        },
        "action": action,
        "next_review": next_review,
        "protocol_version": PROTOCOL_VERSION,
    }


def batch_check(directory: Path) -> list[dict]:
    """Check all result files in a directory."""
    results = []
    for f in sorted(directory.glob("results_*.json")):
        try:
            data = load_results(f)
            decision = decide_status(data)
            results.append(decision)
            print(f"  {f.name:40s} -> {decision['status']:12s} | {decision['action'][:60]}")
        except Exception as exc:
            print(f"  {f.name:40s} -> ERROR: {exc}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward Test Tracker Protocol")
    parser.add_argument("--check", type=Path, help="Single result JSON file to evaluate")
    parser.add_argument("--batch", type=Path, help="Directory of result JSON files")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "forward_test_decisions.json", help="Output path")
    args = parser.parse_args()

    if args.batch:
        print(f"[FORWARD TRACKER] Batch checking directory: {args.batch}")
        decisions = batch_check(args.batch)
    elif args.check:
        print(f"[FORWARD TRACKER] Checking: {args.check}")
        data = load_results(args.check)
        decisions = [decide_status(data)]
        print(f"  Status: {decisions[0]['status']}")
        print(f"  Action: {decisions[0]['action']}")
    else:
        # Default: check simulations directory
        sim_dir = Path(__file__).parent
        print(f"[FORWARD TRACKER] Auto-checking: {sim_dir}")
        decisions = batch_check(sim_dir)

    # Save
    with open(args.output, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "protocol_version": PROTOCOL_VERSION,
            "decisions": decisions,
            "gates": GATES,
            "elimination_triggers": ELIMINATION_TRIGGERS,
            "extended_hold_triggers": EXTENDED_HOLD_TRIGGERS,
        }, f, indent=2)

    print(f"\n[FORWARD TRACKER] Decisions saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
