#!/usr/bin/env python3
"""
Strategy Promotion Workflow — formal gate for adding strategies to the
anti-overfit registry.

A strategy can only reach Smart Picks / live trading through this process:
  1. DSR check: must survive Deflated Sharpe Ratio haircut
  2. FDR check: must pass False Discovery Rate significance test
  3. Forward WR >= 40% on real closed trades
  4. Minimum 30 closed trades (statistical significance)

Usage:
    python tools/promote_strategy.py <strategy_name>
    python tools/promote_strategy.py --list          # show promotable candidates
    python tools/promote_strategy.py --audit         # audit all active strategies

Exit codes:
    0 = promoted successfully (or --list/--audit)
    1 = promotion denied (failed one or more gates)
    2 = strategy not found in data
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DSR_PATH = REPO_ROOT / "tools" / "deflated_sharpe_results.json"
FDR_PATH = REPO_ROOT / "tools" / "data" / "fdr_results.json"
STRATEGY_PERF_PATH = REPO_ROOT / "alpha_engine" / "data" / "strategy_performance.json"
REGISTRY_PATH = REPO_ROOT / "alpha_engine" / "data" / "anti_overfit_registry.json"

# Gate thresholds
MIN_FORWARD_WR = 0.40       # 40% win rate
MIN_CLOSED_TRADES = 30      # statistical significance


def _load_json(path: Path) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"  [WARN] Could not load {path.name}: {exc}")
        return None


def _check_dsr(strategy_name: str) -> tuple[bool, str]:
    """Check if strategy survives DSR haircut."""
    data = _load_json(DSR_PATH)
    if not data:
        return False, "DSR results file not found"

    # Search in top20_by_dsr and all_results
    for section in ["top20_by_dsr", "all_results"]:
        for entry in data.get(section, []):
            if entry.get("key") == strategy_name:
                if entry.get("survives"):
                    return True, f"DSR={entry.get('dsr', '?'):.2f}, survives=True"
                else:
                    return False, f"DSR={entry.get('dsr', '?'):.2f}, survives=False (below haircut)"

    return False, f"Strategy '{strategy_name}' not found in DSR results"


def _check_fdr(strategy_name: str) -> tuple[bool, str]:
    """Check if strategy passes FDR significance test."""
    data = _load_json(FDR_PATH)
    if not data:
        return False, "FDR results file not found"

    for entry in data.get("strategies", []):
        if entry.get("strategy") == strategy_name:
            if entry.get("fdr_significant"):
                return True, f"p={entry.get('p_value', '?')}, FDR significant=True"
            else:
                return False, f"p={entry.get('p_value', '?')}, FDR significant=False"

    return False, f"Strategy '{strategy_name}' not found in FDR results"


def _check_forward_performance(strategy_name: str) -> tuple[bool, str, float, int]:
    """Check forward WR >= 40% and >= 30 closed trades.

    Returns (passed, reason, wr, n_trades).
    """
    data = _load_json(STRATEGY_PERF_PATH)
    if not data:
        return False, "strategy_performance.json not found", 0.0, 0

    perf = data.get(strategy_name)
    if not perf:
        return False, f"Strategy '{strategy_name}' not found in strategy_performance.json", 0.0, 0

    wr = perf.get("win_rate", 0)
    n_trades = perf.get("closed_picks", 0)
    reasons = []

    if n_trades < MIN_CLOSED_TRADES:
        reasons.append(f"trades={n_trades} < {MIN_CLOSED_TRADES} minimum")
    if wr < MIN_FORWARD_WR:
        reasons.append(f"WR={wr*100:.1f}% < {MIN_FORWARD_WR*100:.0f}% minimum")

    if reasons:
        return False, "; ".join(reasons), wr, n_trades

    return True, f"WR={wr*100:.1f}%, trades={n_trades}", wr, n_trades


def promote(strategy_name: str, dry_run: bool = False) -> bool:
    """Run all 4 gates and promote strategy if all pass.

    Returns True if promoted, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"  STRATEGY PROMOTION: {strategy_name}")
    print(f"{'='*60}\n")

    gates = []

    # Gate 1: DSR
    passed, reason = _check_dsr(strategy_name)
    status = "PASS" if passed else "FAIL"
    gates.append(("DSR (Deflated Sharpe)", passed, reason))
    print(f"  [{status}] Gate 1 — DSR: {reason}")

    # Gate 2: FDR
    passed, reason = _check_fdr(strategy_name)
    status = "PASS" if passed else "FAIL"
    gates.append(("FDR (False Discovery)", passed, reason))
    print(f"  [{status}] Gate 2 — FDR: {reason}")

    # Gate 3+4: Forward performance (WR + trade count)
    passed, reason, wr, n_trades = _check_forward_performance(strategy_name)
    status = "PASS" if passed else "FAIL"
    gates.append(("Forward Performance", passed, reason))
    print(f"  [{status}] Gate 3 — Forward WR + trades: {reason}")

    print()
    all_passed = all(g[1] for g in gates)

    if not all_passed:
        failed = [g[0] for g in gates if not g[1]]
        print(f"  DENIED: {strategy_name} failed {len(failed)} gate(s): {', '.join(failed)}")
        print(f"  Strategy will NOT be added to anti-overfit registry.")
        print(f"  It remains blocked from Smart Picks / live trading.\n")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would promote {strategy_name} to registry.")
        return True

    # All gates passed — add to registry
    registry = _load_json(REGISTRY_PATH) or {
        "_comment": "Anti-overfit registry",
        "gold_standard": [],
        "validated_strategies": {},
    }

    registry.setdefault("validated_strategies", {})[strategy_name] = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "source": "promote_strategy.py (DSR+FDR+forward_wr gates)",
        "promotion_details": {
            "dsr": gates[0][2],
            "fdr": gates[1][2],
            "forward_wr": round(wr * 100, 1),
            "forward_trades": n_trades,
        },
    }

    # If both DSR + FDR pass, also add to gold_standard
    dsr_pass = gates[0][1]
    fdr_pass = gates[1][1]
    if dsr_pass and fdr_pass:
        gold = registry.setdefault("gold_standard", [])
        if strategy_name not in gold:
            gold.append(strategy_name)
            gold.sort()

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"  PROMOTED: {strategy_name} added to anti-overfit registry!")
    gold_tag = " (+ gold_standard)" if dsr_pass and fdr_pass else ""
    print(f"  Registry updated{gold_tag}.\n")
    return True


def list_candidates():
    """Show strategies that could potentially be promoted."""
    print("\n  Promotion Candidates (in DSR results):\n")

    dsr_data = _load_json(DSR_PATH)
    fdr_data = _load_json(FDR_PATH)
    perf_data = _load_json(STRATEGY_PERF_PATH) or {}
    registry = _load_json(REGISTRY_PATH) or {}
    validated = set(registry.get("validated_strategies", {}).keys())

    fdr_map = {}
    if fdr_data:
        for entry in fdr_data.get("strategies", []):
            fdr_map[entry["strategy"]] = entry.get("fdr_significant", False)

    if not dsr_data:
        print("  No DSR results available.")
        return

    for section in ["top20_by_dsr", "all_results"]:
        for entry in dsr_data.get(section, []):
            name = entry.get("key", "?")
            dsr_ok = entry.get("survives", False)
            fdr_ok = fdr_map.get(name, False)
            perf = perf_data.get(name, {})
            wr = perf.get("win_rate", 0)
            trades = perf.get("closed_picks", 0)
            in_reg = name in validated

            status = "REGISTERED" if in_reg else ("READY" if (dsr_ok and fdr_ok and wr >= MIN_FORWARD_WR and trades >= MIN_CLOSED_TRADES) else "NOT READY")
            print(f"  {status:12s} {name:40s} DSR={'Y' if dsr_ok else 'N'} FDR={'Y' if fdr_ok else 'N'} WR={wr*100:5.1f}% trades={trades:3d}")


def audit_active():
    """Audit all strategies in active_picks against the registry."""
    sys.path.insert(0, str(REPO_ROOT))
    from alpha_engine.anti_overfit_gate import audit_active_picks_against_registry
    result = audit_active_picks_against_registry()
    print(f"\n  Anti-Overfit Registry Audit")
    print(f"  {'='*40}")
    print(f"  Total picks:          {result['total_picks']}")
    print(f"  Approved strategies:  {result['approved']}")
    print(f"  Unapproved picks:     {result['unapproved']}")
    if result["unapproved_strategies"]:
        print(f"\n  Unapproved strategies (blocked from Smart Picks):")
        for s in sorted(result["unapproved_strategies"]):
            print(f"    - {s}")
    else:
        print(f"\n  All strategies are in the registry.")


def main():
    parser = argparse.ArgumentParser(
        description="Strategy Promotion Workflow — gate strategies into anti-overfit registry"
    )
    parser.add_argument("strategy", nargs="?", help="Strategy name to promote")
    parser.add_argument("--list", action="store_true", help="List promotable candidates")
    parser.add_argument("--audit", action="store_true", help="Audit active picks against registry")
    parser.add_argument("--dry-run", action="store_true", help="Check gates without modifying registry")
    args = parser.parse_args()

    if args.list:
        list_candidates()
        sys.exit(0)

    if args.audit:
        audit_active()
        sys.exit(0)

    if not args.strategy:
        parser.print_help()
        sys.exit(2)

    success = promote(args.strategy, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
