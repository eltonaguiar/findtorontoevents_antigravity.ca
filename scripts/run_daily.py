# run_daily.py - Run daily quant tasks
# Orchestrates: HMM regime, Kelly sizing, correlation pruning,
# Sharpe analysis, XGBoost meta-labeling, GARCH vol forecasting

import os
import sys
import subprocess
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(name, script_path, args=None):
    """Run a script step and report result."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    print(f"\n{'='*60}")
    print(f"  [{time.strftime('%H:%M:%S')}] Running: {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"  WARNING: {name} exited with code {result.returncode}")
    return result.returncode


def main():
    print("=" * 60)
    print("  DAILY QUANT PIPELINE")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    steps = [
        ("HMM Regime Detection", os.path.join(SCRIPTS_DIR, "hmm_regime.py")),
        ("Kelly Sizing", os.path.join(SCRIPTS_DIR, "kelly_sizer.py")),
        ("Correlation Pruner", os.path.join(SCRIPTS_DIR, "corr_pruner.py")),
        ("Sharpe Ratio Analysis", os.path.join(SCRIPTS_DIR, "compute_sharpe_all_assets.py")),
        ("XGBoost Meta-Labeler", os.path.join(SCRIPTS_DIR, "meta_label.py")),
        ("GARCH Vol Forecasting", os.path.join(SCRIPTS_DIR, "garch_vol.py")),
    ]

    results = []
    for name, script in steps:
        if not os.path.exists(script):
            print(f"\n  SKIP: {name} — script not found: {script}")
            results.append((name, -1))
            continue
        rc = run_step(name, script)
        results.append((name, rc))

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    for name, rc in results:
        status = "OK" if rc == 0 else ("SKIP" if rc == -1 else f"FAIL ({rc})")
        print(f"  {name:35s} [{status}]")

    failed = sum(1 for _, rc in results if rc > 0)
    print(f"\n  Total: {len(results)} steps | Failed: {failed}")
    print("  Daily tasks completed.")

    return 1 if failed > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
