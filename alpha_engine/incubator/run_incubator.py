#!/usr/bin/env python3
"""
Incubator — Main Orchestrator
================================
End-to-end pipeline:
  1. Extract seed strategies from audit DB
  2. Generate parameter permutations (LHS)
  3. Run fast vectorised backtests on BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD
  4. Rank by composite score
  5. Store incubator candidates in SQLite + MySQL (ejaguiar1_stocks)
  6. Export paper-trading-ready JSON
  7. (Optional) Run full-resolution backtests in parallel

Usage:
  python -m alpha_engine.incubator.run_incubator               # full pipeline
  python -m alpha_engine.incubator.run_incubator --seeds        # show seed strategies
  python -m alpha_engine.incubator.run_incubator --rank         # rank existing results
  python -m alpha_engine.incubator.run_incubator --budget 5000  # custom permutation count
  python -m alpha_engine.incubator.run_incubator --full         # include full backtests
  python -m alpha_engine.incubator.run_incubator --export       # export paper-ready JSON
  python -m alpha_engine.incubator.run_incubator --report       # generate JSON report
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ENGINE_DIR / "data"
sys.path.insert(0, str(ENGINE_DIR))


def run_pipeline(
    budget: int = 8000,
    top_n: int = 15,
    method: str = "lhs",
    symbols: list[str] = None,
    run_full: bool = False,
    min_seeds: int = 5,
    seed: int = 42,
) -> dict:
    """Run the complete incubator pipeline.

    Returns a summary dict with rankings and stats.
    """
    from .seed_extractor import extract_seeds, map_seed_to_archetype
    from .permutation_engine import generate_permutations
    from .parameter_space import ARCHETYPES, get_archetype
    from .fast_backtester import run_batch_backtest, BacktestResult
    from .ranker import rank_results
    from .incubator_db import IncubatorDB

    if symbols is None:
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]

    start_time = time.time()
    print("=" * 60)
    print("  INCUBATOR PIPELINE — Strategy Discovery Engine")
    print("=" * 60)

    # ── Step 1: Extract seed strategies ──────────────────────
    print("\n[STEP 1] Extracting seed strategies from audit DB...")
    seeds = extract_seeds(top_n=30, min_closed_picks=min_seeds)
    print(f"  Found {len(seeds)} seed strategies")

    if len(seeds) > 0:
        # Map seeds to archetypes for targeted permutation
        archetype_boost = {}
        for _, row in seeds.iterrows():
            arch = map_seed_to_archetype(row["strategy"])
            if arch:
                archetype_boost[arch] = archetype_boost.get(arch, 0) + 1
                print(f"  Seed: {row['strategy']:40s} → archetype: {arch}")

    # ── Step 2: Generate permutations ────────────────────────
    print(f"\n[STEP 2] Generating {budget} permutations (method={method})...")
    permutations = generate_permutations(
        total_budget=budget,
        method=method,
        seed=seed,
    )
    print(f"  Generated {len(permutations)} permutations")

    # Tag permutations with seed strategies where applicable
    if len(seeds) > 0:
        for perm in permutations:
            for _, row in seeds.iterrows():
                arch = map_seed_to_archetype(row["strategy"])
                if arch == perm.archetype:
                    perm.seed_strategy = row["strategy"]
                    break

    # ── Step 3: Fast backtests ───────────────────────────────
    print(f"\n[STEP 3] Running fast backtests on {symbols}...")
    # Realistic costs: 0.05% slippage + 0.1% commission (Binance taker). Fixed 2026-03-13 — was 0% causing inflated rankings
    fast_results = run_batch_backtest(
        permutations=permutations,
        symbols=symbols,
        slippage_pct=0.0005,
        commission_pct=0.001,
    )
    print(f"  Completed {len(fast_results)} backtests")

    # ── Step 4: Rank results ─────────────────────────────────
    print(f"\n[STEP 4] Ranking results (top {top_n})...")
    ranked = rank_results(fast_results, top_n=top_n)
    summary = ranked["summary"]
    print(f"  Candidates ranked: {summary.get('candidates_ranked', 0)}")
    print(f"  Paper-ready: {summary.get('paper_ready_count', 0)}")
    print(f"  Best Sharpe: {summary.get('best_sharpe', 0)}")
    print(f"  Best archetype: {summary.get('best_archetype', 'none')}")

    # ── Step 5: Store in database ────────────────────────────
    print("\n[STEP 5] Saving to database (SQLite + MySQL)...")
    db = IncubatorDB()
    saved = db.save_batch(ranked)
    print(f"  Saved {saved} candidates")

    # ── Step 6: Export paper-ready JSON ──────────────────────
    print("\n[STEP 6] Exporting paper-ready strategies...")
    export_path = db.export_paper_trading_json()
    print(f"  Exported to {export_path}")

    # ── Step 7: Full-resolution backtests (optional) ─────────
    if run_full:
        print(f"\n[STEP 7] Running full-resolution backtests (with slippage/commission)...")
        # Only run on paper-ready candidates
        paper_perms = []
        from .permutation_engine import Permutation
        for c in ranked.get("paper_ready", []):
            paper_perms.append(Permutation(
                perm_id=c["perm_id"],
                archetype=c["archetype"],
                params=c["params"],
                seed_strategy=c.get("seed_strategy", ""),
            ))

        if paper_perms:
            full_results = run_batch_backtest(
                permutations=paper_perms,
                symbols=symbols,
                slippage_pct=0.001,   # 0.1% slippage
                commission_pct=0.001,  # 0.1% commission
            )
            # Save full results
            for r in full_results:
                db.save_backtest_result(r.to_dict(), backtest_type="full")
            print(f"  Full backtests completed: {len(full_results)}")
        else:
            print("  No paper-ready candidates to run full backtests on")

    db.close()

    # ── Summary ──────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE — {elapsed:.1f}s")
    print(f"  Seeds: {len(seeds)} | Permutations: {len(permutations)} | "
          f"Backtests: {len(fast_results)}")
    print(f"  Paper-ready: {summary.get('paper_ready_count', 0)} | "
          f"Best Sharpe: {summary.get('best_sharpe', 0):.2f}")
    print(f"{'=' * 60}")

    # Print top candidates
    if ranked.get("combined_ranking"):
        print("\n  TOP INCUBATOR CANDIDATES:")
        print(f"  {'Rank':<5} {'Archetype':<30} {'Sharpe':>8} {'WR':>7} "
              f"{'MaxDD':>8} {'PF':>7} {'Score':>8} {'Paper?':>7}")
        print(f"  {'-'*83}")
        for i, c in enumerate(ranked["combined_ranking"][:15], 1):
            ready = "YES" if c.get("ready_for_paper") else "no"
            print(f"  {i:<5} {c['archetype']:<30} {c['combined_sharpe']:>8.2f} "
                  f"{c['combined_wr']:>6.1%} {c['combined_max_dd']:>8.4f} "
                  f"{c['combined_pf']:>7.2f} {c['composite_score']:>8.4f} {ready:>7}")

    ranked["elapsed_seconds"] = round(elapsed, 1)
    ranked["timestamp"] = datetime.now(timezone.utc).isoformat()
    return ranked


def main():
    parser = argparse.ArgumentParser(
        description="Incubator Pipeline — Strategy Discovery Engine"
    )
    parser.add_argument("--budget", type=int, default=8000,
                        help="Total permutation budget (default: 8000)")
    parser.add_argument("--top-n", type=int, default=15,
                        help="Top N candidates per ranking (default: 15)")
    parser.add_argument("--method", choices=["lhs", "sobol", "grid"], default="lhs",
                        help="Sampling method (default: lhs)")
    parser.add_argument("--symbols", nargs="+",
                        default=["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"],
                        help="Symbols to backtest (default: BTC-USD ETH-USD SOL-USD BNB-USD XRP-USD)")
    parser.add_argument("--full", action="store_true",
                        help="Run full-resolution backtests with slippage/commission")
    parser.add_argument("--seeds", action="store_true",
                        help="Show seed strategies only (no backtesting)")
    parser.add_argument("--rank", action="store_true",
                        help="Rank existing results from database")
    parser.add_argument("--export", action="store_true",
                        help="Export paper-ready JSON only")
    parser.add_argument("--report", action="store_true",
                        help="Generate full JSON report")
    parser.add_argument("--min-seeds", type=int, default=3,
                        help="Minimum closed picks for seed extraction (default: 3)")

    args = parser.parse_args()

    if args.seeds:
        from .seed_extractor import extract_seeds
        seeds = extract_seeds(min_closed_picks=args.min_seeds)
        if len(seeds) > 0:
            print(seeds.to_string())
        else:
            print("No seeds found")
        return

    if args.export:
        from .incubator_db import IncubatorDB
        db = IncubatorDB()
        path = db.export_paper_trading_json()
        db.close()
        print(f"Exported to {path}")
        return

    if args.rank:
        from .incubator_db import IncubatorDB
        db = IncubatorDB()
        candidates = db.get_incubator_strategies()
        print(f"Incubator strategies: {len(candidates)}")
        paper = db.get_paper_ready()
        print(f"Paper-ready: {len(paper)}")
        for c in candidates[:15]:
            print(f"  {c['archetype']:<30} score={c['composite_score']:.4f}  "
                  f"sharpe={c['combined_sharpe']:.2f}  status={c['status']}")
        db.close()
        return

    # Full pipeline
    result = run_pipeline(
        budget=args.budget,
        top_n=args.top_n,
        method=args.method,
        symbols=args.symbols,
        run_full=args.full,
        min_seeds=args.min_seeds,
    )

    if args.report:
        report_path = DATA_DIR / "incubator_report.json"
        report_path.write_text(json.dumps(result, indent=2, default=str))
        print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
