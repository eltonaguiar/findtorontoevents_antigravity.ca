#!/usr/bin/env python3
"""
Master orchestrator for Smart Money Intelligence scripts.

Usage:
  python run_all.py --all           Run everything
  python run_all.py --13f           SEC 13F tracker only
  python run_all.py --insider       Insider tracker only
  python run_all.py --wsb           WSB sentiment only
  python run_all.py --consensus     Consensus engine only (always runs)
  python run_all.py --perf          Performance tracker only
  python run_all.py                 Consensus engine only (default)

Multiple flags can be combined:
  python run_all.py --13f --wsb     Run 13F + WSB + consensus

Exit code: 0 if all steps succeed, 1 if any step fails.
"""
import sys
import os
import traceback
import logging

# Ensure scripts directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('run_all')


def run_step(name, func):
    """Run a step, catch errors, continue."""
    try:
        logger.info(f"=== Starting: {name} ===")
        result = func()
        logger.info(f"=== Completed: {name} ===")
        return True
    except Exception as e:
        logger.error(f"=== FAILED: {name} -- {e} ===")
        traceback.print_exc()
        return False


def main():
    results = {}
    args = sys.argv[1:]
    run_all = '--all' in args

    logger.info("=" * 60)
    logger.info("Smart Money Intelligence — Master Orchestrator")
    logger.info(f"Arguments: {args if args else '(none — consensus only)'}")
    logger.info("=" * 60)

    # Step 1: SEC 13F (weekly — run with --13f or --all)
    if '--13f' in args or run_all:
        from sec_13f_tracker import main as sec_13f_main
        results['sec_13f'] = run_step('SEC 13F Tracker', sec_13f_main)

    # Step 2: Insider Tracker
    if '--insider' in args or run_all:
        from insider_tracker import main as insider_main
        results['insider'] = run_step('Insider Tracker', insider_main)

    # Step 3: WSB Sentiment
    if '--wsb' in args or run_all:
        from wsb_sentiment import main as wsb_main
        results['wsb'] = run_step('WSB Sentiment', wsb_main)

    # Step 4: Consensus Engine (always runs)
    if '--consensus' in args or run_all or not any(
        flag in args for flag in ['--13f', '--insider', '--wsb', '--perf']
    ):
        from consensus_engine import main as consensus_main
        results['consensus'] = run_step('Consensus Engine', consensus_main)

    # Step 5: Performance Tracker
    if '--perf' in args or run_all:
        from performance_tracker import main as perf_main
        results['performance'] = run_step('Performance Tracker', perf_main)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("MASTER ORCHESTRATOR SUMMARY")
    logger.info("=" * 60)

    all_ok = True
    for step, ok in results.items():
        status = "OK" if ok else "FAILED"
        if not ok:
            all_ok = False
        logger.info(f"  {step:20s}: {status}")

    if not results:
        logger.info("  (no steps were run)")

    logger.info("=" * 60)

    if all_ok:
        logger.info("All steps completed successfully.")
    else:
        logger.error("One or more steps FAILED. Check logs above for details.")

    # Exit with error if any step failed
    if not all_ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
