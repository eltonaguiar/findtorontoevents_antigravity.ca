#!/usr/bin/env python3
"""
World-Class Intelligence — Master Runner
Runs all intelligence scripts in sequence.
Called by GitHub Actions daily.
"""

import sys
import traceback
from datetime import datetime


def run_module(name, module_func):
    """Run a module and handle errors gracefully."""
    print(f"\n{'#' * 70}")
    print(f"# RUNNING: {name}")
    print(f"# Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'#' * 70}\n")

    try:
        module_func()
        print(f"\n[OK] {name} completed successfully")
        return True
    except Exception as e:
        print(f"\n[ERROR] {name} failed: {e}")
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("WORLD-CLASS INTELLIGENCE — MASTER PIPELINE")
    print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    results = {}
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    # ──── Module 1: HMM Regime + Hurst Exponent ────
    if mode in ("all", "regime", "hmm"):
        try:
            from hmm_regime import main as hmm_main
            results["HMM Regime + Hurst"] = run_module("HMM Regime + Hurst Exponent", hmm_main)
        except ImportError as e:
            print(f"[SKIP] HMM Regime: {e}")
            results["HMM Regime + Hurst"] = False

    # ──── Module 2: Macro Intelligence ────
    if mode in ("all", "macro"):
        try:
            from macro_intelligence import main as macro_main
            results["Macro Intelligence"] = run_module("Macro + VIX + Cross-Asset", macro_main)
        except ImportError as e:
            print(f"[SKIP] Macro Intelligence: {e}")
            results["Macro Intelligence"] = False

    # ──── Module 3: Meta-Labeling + Kelly + Alpha Decay ────
    if mode in ("all", "meta", "kelly"):
        try:
            from meta_labeling import main as meta_main
            results["Meta-Labeling"] = run_module("Meta-Labeling + Kelly + Alpha Decay", meta_main)
        except ImportError as e:
            print(f"[SKIP] Meta-Labeling: {e}")
            results["Meta-Labeling"] = False

    # ──── Module 4: WorldQuant Alphas ────
    if mode in ("all", "alphas", "worldquant"):
        try:
            from worldquant_alphas import main as wq_main
            results["WorldQuant Alphas"] = run_module("WorldQuant 101 Alphas", wq_main)
        except ImportError as e:
            print(f"[SKIP] WorldQuant Alphas: {e}")
            results["WorldQuant Alphas"] = False

    # ──── Summary ────
    print(f"\n{'=' * 70}")
    print("PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    for module, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  [{status:6s}] {module}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  Total: {passed}/{total} modules succeeded")
    print(f"  Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'=' * 70}")

    # Exit with error if any module failed
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
