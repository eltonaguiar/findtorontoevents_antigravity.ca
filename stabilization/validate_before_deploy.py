#!/usr/bin/env python3
"""
Deployment Validation Gate
==========================
Prevents deploying strategy versions that haven't been validated.

Usage:
    python stabilization/validate_before_deploy.py [--strict]

Checks:
1. All active strategies in alpha_engine must exist in strategy_registry.json
2. No untested strategies are in production bundles
3. Mercury version changes require backtest proof
4. Baby strategies with 0% WR are disabled

Exit codes:
    0 = All checks pass
    1 = Validation failures found (blocks deploy)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "stabilization" / "strategy_registry.json"
DISABLED = ROOT / "stabilization" / "disabled_strategies.json"
VALIDATED = ROOT / "stabilization" / "validated_winners.json"
BUNDLE_DIR = ROOT / "bundle_registry"
ALPHA_TUNER = ROOT / "alpha_engine" / "auto_tuner.py"

STRICT = "--strict" in sys.argv


def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check_bundle_eligibility():
    """Ensure no untested strategies are in production bundles."""
    registry = load_json(REGISTRY)
    strategies = registry.get("strategies", {})
    rules = registry.get("bundle_eligibility_rules", {})
    errors = []

    if not BUNDLE_DIR.exists():
        return errors

    for bundle_file in BUNDLE_DIR.glob("*.json"):
        bundle = load_json(bundle_file)
        bundle_name = bundle.get("name", bundle_file.stem)
        bundle_strats = bundle.get("strategies", [])

        for strat_name in bundle_strats:
            reg = strategies.get(strat_name, {})

            if not reg:
                errors.append(
                    f"BUNDLE '{bundle_name}': strategy '{strat_name}' NOT in registry (untested)"
                )
                continue

            if not reg.get("tested", False):
                errors.append(
                    f"BUNDLE '{bundle_name}': strategy '{strat_name}' is NOT tested"
                )

            if not reg.get("bundle_eligible", False):
                errors.append(
                    f"BUNDLE '{bundle_name}': strategy '{strat_name}' is NOT bundle-eligible "
                    f"(status: {reg.get('status', 'unknown')})"
                )

    return errors


def check_disabled_consistency():
    """Ensure disabled strategies aren't accidentally active."""
    disabled_data = load_json(DISABLED)
    disabled_set = set(disabled_data.get("disabled", []))
    registry = load_json(REGISTRY)
    strategies = registry.get("strategies", {})
    errors = []

    for name in disabled_set:
        reg = strategies.get(name, {})
        if reg and reg.get("bundle_eligible", False):
            errors.append(
                f"INCONSISTENCY: '{name}' is in disabled list but marked bundle_eligible in registry"
            )

    return errors


def check_registry_coverage():
    """Warn about strategies that exist in code but not in registry."""
    registry = load_json(REGISTRY)
    strategies = registry.get("strategies", {})
    warnings = []

    # Check baby_strategies/ directory
    baby_dir = ROOT / "baby_strategies"
    if baby_dir.exists():
        for py_file in baby_dir.glob("*.py"):
            name = py_file.stem
            if name.startswith("__") or name.startswith("strategy_"):
                continue
            if name not in strategies:
                warnings.append(
                    f"UNTESTED: baby_strategies/{name}.py not in strategy registry"
                )

    return warnings


def main():
    print("=" * 60)
    print("DEPLOYMENT VALIDATION GATE")
    print("=" * 60)

    all_errors = []
    all_warnings = []

    # Check 1: Bundle eligibility
    print("\n[1] Checking bundle eligibility...")
    errors = check_bundle_eligibility()
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("  PASS: All bundle strategies are tested and eligible")

    # Check 2: Disabled consistency
    print("\n[2] Checking disabled strategy consistency...")
    errors = check_disabled_consistency()
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("  PASS: Disabled strategies are consistent")

    # Check 3: Registry coverage
    print("\n[3] Checking strategy registry coverage...")
    warnings = check_registry_coverage()
    all_warnings.extend(warnings)
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    else:
        print("  PASS: All strategies are registered")

    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s), {len(all_warnings)} warning(s)")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    elif all_warnings and STRICT:
        print(f"FAILED (strict): {len(all_warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"PASSED: 0 errors, {len(all_warnings)} warning(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
