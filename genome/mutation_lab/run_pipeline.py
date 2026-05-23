#!/usr/bin/env python3
"""Mutation Lab — Sequential Pipeline Orchestrator.

Runs all three stages in sequence:
  1. SCOUT    → mutation_targets.json
  2. MUTATE   → mutation_results.json (A, B, C combined)
  3. PROMOTE  → mutation_lab_picks.json

This is the local/CI single-process entry point. For parallel execution
across GitHub Actions matrix jobs, use the workflow directly.

Usage:
    python -m genome.mutation_lab.run_pipeline [--output-dir genome/data]
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def scout(work_dir: Path) -> dict:
    """Stage 1: Identify mutation targets from strategy performance data."""
    from genome.mutation_lab.scout import run_scout

    targets_path = str(work_dir / "mutation_targets.json")
    logger.info("=" * 60)
    logger.info("STAGE 1: SCOUT — Identifying mutation targets")
    logger.info("=" * 60)
    t0 = time.time()
    targets = run_scout(targets_path)
    elapsed = time.time() - t0
    logger.info(f"SCOUT complete in {elapsed:.1f}s: "
                f"{len(targets.get('winners', []))} winners, "
                f"{len(targets.get('losers', []))} losers")
    return targets


def mutate(work_dir: Path) -> list[dict]:
    """Stage 2: Generate mutations and backtest each on 3 symbols x 750 bars."""
    from genome.mutation_lab.mutator_amplify import run_amplify
    from genome.mutation_lab.mutator_invert import run_invert
    from genome.mutation_lab.mutator_hybrid import run_hybrid

    targets_path = str(work_dir / "mutation_targets.json")
    all_results = []

    logger.info("=" * 60)
    logger.info("STAGE 2: MUTATE + BACKTEST — Running all mutation types")
    logger.info("=" * 60)

    # Type A: Winner Amplification
    logger.info("-" * 40)
    logger.info("Type A: Winner Amplification")
    t0 = time.time()
    try:
        results_a_path = str(work_dir / "mutation_results_a.json")
        results_a = run_amplify(targets_path, results_a_path)
        passed_a = sum(1 for r in results_a if r.get("backtest_results", {}).get("passed"))
        logger.info(f"Type A complete in {time.time() - t0:.1f}s: "
                     f"{passed_a}/{len(results_a)} passed")
    except Exception as e:
        logger.error(f"Type A failed: {e}")
        results_a = []

    # Type B: Loser Inversion + Pure Flip
    logger.info("-" * 40)
    logger.info("Type B: Loser Inversion + Pure Flip")
    t0 = time.time()
    try:
        results_b_path = str(work_dir / "mutation_results_b.json")
        results_b = run_invert(targets_path, results_b_path)
        passed_b = sum(1 for r in results_b if r.get("backtest_results", {}).get("passed"))
        logger.info(f"Type B complete in {time.time() - t0:.1f}s: "
                     f"{passed_b}/{len(results_b)} passed")
    except Exception as e:
        logger.error(f"Type B failed: {e}")
        results_b = []

    # Type C: Loser Fix + Crossbreed
    logger.info("-" * 40)
    logger.info("Type C: Loser Fix + Crossbreed")
    t0 = time.time()
    try:
        results_c_path = str(work_dir / "mutation_results_c.json")
        results_c = run_hybrid(targets_path, results_c_path)
        passed_c = sum(1 for r in results_c if r.get("backtest_results", {}).get("passed"))
        logger.info(f"Type C complete in {time.time() - t0:.1f}s: "
                     f"{passed_c}/{len(results_c)} passed")
    except Exception as e:
        logger.error(f"Type C failed: {e}")
        results_c = []

    all_results = results_a + results_b + results_c
    total_passed = sum(1 for r in all_results if r.get("backtest_results", {}).get("passed"))
    logger.info(f"MUTATE complete: {total_passed}/{len(all_results)} passed quality gates")
    return all_results


def promote(work_dir: Path, output_dir: Path) -> dict:
    """Stage 3: Apply quality gates, register winners, write final picks."""
    from genome.mutation_lab.promoter import run_promoter

    logger.info("=" * 60)
    logger.info("STAGE 3: PROMOTE — Quality gates + live picks analysis")
    logger.info("=" * 60)
    t0 = time.time()
    output_path = str(output_dir / "mutation_lab_picks.json")
    output = run_promoter(str(work_dir), output_path)
    elapsed = time.time() - t0

    stats = output.get("mutation_stats", {})
    logger.info(f"PROMOTE complete in {elapsed:.1f}s:")
    logger.info(f"  Mutations tested:  {stats.get('total_mutations_tested', 0)}")
    logger.info(f"  Passed gates:      {stats.get('passed_quality_gates', 0)}")
    logger.info(f"  Live picks:        {stats.get('live_signals_generated', 0)}")
    logger.info(f"  Type breakdown:    {stats.get('mutation_type_breakdown', {})}")
    return output


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Mutation Lab Pipeline Orchestrator")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "genome" / "data"),
                        help="Directory for final output files")
    parser.add_argument("--work-dir", default=None,
                        help="Working directory for intermediate files (default: output-dir)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(args.work_dir) if args.work_dir else output_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    pipeline_start = time.time()
    logger.info("=" * 60)
    logger.info("MUTATION LAB PIPELINE — Starting full run")
    logger.info(f"  Work dir:   {work_dir}")
    logger.info(f"  Output dir: {output_dir}")
    logger.info(f"  Time:       {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # Stage 1: SCOUT
    targets = scout(work_dir)
    if not targets.get("winners") and not targets.get("losers"):
        logger.warning("No targets found — aborting pipeline")
        sys.exit(0)

    # Stage 2: MUTATE + BACKTEST
    all_results = mutate(work_dir)
    if not all_results:
        logger.warning("No mutation results — aborting pipeline")
        sys.exit(0)

    # Stage 2.5: SUPER MUTATIONS (run alongside promoter via import)
    logger.info("-" * 40)
    logger.info("Super Mutations: 5 blended strategies from top-3 profitable systems")
    try:
        from genome.mutation_lab.super_mutations import SUPER_MUTATION_STRATEGIES
        logger.info(f"  Loaded {len(SUPER_MUTATION_STRATEGIES)} super mutation strategies: "
                     f"{', '.join(SUPER_MUTATION_STRATEGIES.keys())}")
    except Exception as e:
        logger.warning(f"  Super mutations import failed (non-fatal): {e}")

    # Stage 3: PROMOTE (includes super mutations in live picks generation)
    output = promote(work_dir, output_dir)

    # Final summary
    total_elapsed = time.time() - pipeline_start
    stats = output.get("mutation_stats", {})
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE in {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    logger.info(f"  Mutations tested:  {stats.get('total_mutations_tested', 0)}")
    logger.info(f"  Passed gates:      {stats.get('passed_quality_gates', 0)}")
    logger.info(f"  Live picks:        {stats.get('live_signals_generated', 0)}")
    logger.info(f"  Output:            {output_dir / 'mutation_lab_picks.json'}")
    logger.info("=" * 60)

    # Print top picks for quick review
    picks = output.get("picks", [])
    if picks:
        print(f"\nTop {min(5, len(picks))} picks:")
        for i, p in enumerate(picks[:5], 1):
            print(f"  {i}. {p['symbol']} {p['direction']} @ {p['entry_price']} "
                  f"conf={p['confidence']:.2f} WR={p.get('win_rate', 0):.1%} "
                  f"({p['strategy']})")
    else:
        print("\nNo live picks generated this run.")


if __name__ == "__main__":
    main()
