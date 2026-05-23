#!/usr/bin/env python3
"""
Batch Backtest All Unregistered Strategies
==========================================

Runs real_data_sweep_runner against ALL strategy files that haven't been backtested yet.
Writes results to incubator/backtest_results/real_data_sweep_YYYYMMDD_HHMMSS.json
Then regenerates the battleground dashboard.

Usage:
    python incubator/backtest_team/batch_backtest_all.py [--max N] [--timeout SEC] [--force]
    python incubator/backtest_team/batch_backtest_all.py --agents-only
    python incubator/backtest_team/batch_backtest_all.py --babies-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

AGENTS_ROOT = ROOT / "incubator" / "agents"
BABY_ROOT = ROOT / "baby_strategies"
RESULTS_DIR = ROOT / "incubator" / "backtest_results"
DASHBOARD_FILE = ROOT / "battleground" / "data" / "baby_strats_dashboard.json"
DB_PATH = ROOT / "crypto_data.db"


def _get_already_tested() -> Set[str]:
    """Get strategy names that already have backtest results."""
    if not DASHBOARD_FILE.exists():
        return set()
    try:
        data = json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))
        return {
            s["name"]
            for s in data.get("strategies", [])
            if s.get("status") not in ("validating",)
        }
    except Exception:
        return set()


def _discover_all_strategy_files(
    agents_only: bool = False,
    babies_only: bool = False,
) -> List[Path]:
    """Find all .py strategy files."""
    files: List[Path] = []

    if not babies_only:
        for p in sorted(AGENTS_ROOT.rglob("*.py")):
            if "__pycache__" in str(p).replace("\\", "/"):
                continue
            if p.name.startswith("test_") or p.name.startswith("__"):
                continue
            files.append(p)

    if not agents_only and BABY_ROOT.exists():
        for p in sorted(BABY_ROOT.glob("*.py")):
            if p.name.startswith("test_") or p.name.startswith("__"):
                continue
            files.append(p)

    return files


def run_batch(
    max_strategies: int = 0,
    timeout_sec: int = 25,
    force: bool = False,
    agents_only: bool = False,
    babies_only: bool = False,
) -> Dict[str, Any]:
    """Run backtest sweep on all untested strategies."""
    from incubator.backtest_team.real_data_sweep_runner import RealDataSweepRunner

    if not DB_PATH.exists():
        print(f"ERROR: crypto_data.db not found at {DB_PATH}")
        print("Download it or run the data collector first.")
        sys.exit(1)

    already_tested = set() if force else _get_already_tested()
    all_files = _discover_all_strategy_files(agents_only, babies_only)

    # Filter to untested only
    to_test = [f for f in all_files if f.stem not in already_tested]

    if max_strategies > 0:
        to_test = to_test[:max_strategies]

    total = len(to_test)
    print(f"=== Batch Backtest: {total} strategies to test ===")
    print(f"    Already tested: {len(already_tested)}")
    print(f"    Total files found: {len(all_files)}")
    print(f"    DB: {DB_PATH} ({DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"    Timeout per strategy: {timeout_sec}s")
    print()

    # Initialize runner once (loads data into memory)
    print("Loading market data...")
    runner = RealDataSweepRunner(
        db_path=str(DB_PATH),
        pair="BTC/USDT",
        bars=1808,
        strategy_timeout_sec=timeout_sec,
    )
    print(f"Market data loaded: {len(runner._base_ohlcv)} bars\n")

    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    errors = 0
    started = time.time()

    for i, py_file in enumerate(to_test, 1):
        agent_id = py_file.parent.name
        name = py_file.stem
        elapsed = time.time() - started
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0

        print(f"[{i}/{total}] {agent_id}/{name}", end=" ... ", flush=True)

        try:
            result = runner.run_strategy(py_file)
            r = {
                "strategy_name": result.strategy_name,
                "agent_id": result.agent_id,
                "file_path": str(result.file_path),
                "status": result.status,
                "sharpe": result.sharpe,
                "win_rate": result.win_rate,
                "max_drawdown": result.max_drawdown,
                "profit_factor": result.profit_factor,
                "total_return": result.total_return,
                "total_trades": result.total_trades,
                "duration_sec": result.duration_sec,
                "error_message": result.error,
            }
            results.append(r)

            if result.status == "passed":
                passed += 1
                print(f"PASSED (Sharpe={result.sharpe:.2f}, WR={result.win_rate:.1%}, "
                      f"PF={result.profit_factor:.2f}, {result.total_trades} trades) "
                      f"[{result.duration_sec:.1f}s]")
            elif result.status == "failed":
                failed += 1
                print(f"FAILED (Sharpe={result.sharpe:.2f}, WR={result.win_rate:.1%}, "
                      f"DD={result.max_drawdown:.1%}) [{result.duration_sec:.1f}s]")
            elif result.status == "failed_insufficient_trades":
                failed += 1
                print(f"INSUFFICIENT ({result.total_trades} trades) [{result.duration_sec:.1f}s]")
            else:
                errors += 1
                err_short = (result.error or "unknown")[:60]
                print(f"{result.status.upper()}: {err_short} [{result.duration_sec:.1f}s]")

        except Exception as exc:
            errors += 1
            results.append({
                "strategy_name": name,
                "agent_id": agent_id,
                "file_path": str(py_file),
                "status": "error",
                "sharpe": None,
                "win_rate": None,
                "max_drawdown": None,
                "profit_factor": None,
                "total_return": None,
                "total_trades": 0,
                "duration_sec": 0,
                "error_message": str(exc)[:200],
            })
            print(f"ERROR: {str(exc)[:60]}")

        # Progress every 25 strategies
        if i % 25 == 0:
            print(f"\n--- Progress: {i}/{total} ({i/total*100:.0f}%) | "
                  f"Passed: {passed} | Failed: {failed} | Errors: {errors} | "
                  f"ETA: {eta/60:.1f}min ---\n")

    total_time = time.time() - started

    # Build output
    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(DB_PATH),
        "total_tested": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration_sec": round(total_time, 1),
        "results": results,
    }

    # Write results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"real_data_sweep_{ts}.json"
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"BATCH BACKTEST COMPLETE")
    print(f"  Total: {len(results)} strategies in {total_time/60:.1f} min")
    print(f"  Passed: {passed} ({passed/max(len(results),1)*100:.0f}%)")
    print(f"  Failed: {failed}")
    print(f"  Errors: {errors}")
    print(f"  Results: {out_file}")
    print(f"{'='*60}")

    # Generate .meta.json for strategies that don't have one
    # (needed for dashboard generator to discover them)
    meta_created = 0
    for r in results:
        fp = Path(r["file_path"])
        meta_path = Path(str(fp) + ".meta.json")
        if not meta_path.exists():
            meta = {
                "status": "backtest_passed" if r["status"] == "passed" else
                          "backtest_failed" if r["status"] == "failed" else
                          "awaiting_backtest",
                "strategy_type": "auto_detected",
                "unique_value": f"Strategy by {r['agent_id']}",
                "backtest_metrics": {
                    "win_rate": r["win_rate"],
                    "sharpe": r["sharpe"],
                    "max_drawdown": r["max_drawdown"],
                    "profit_factor": r["profit_factor"],
                    "total_return": r["total_return"],
                    "total_trades": r["total_trades"],
                },
                "batch_tested_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                meta_created += 1
            except Exception:
                pass
    if meta_created:
        print(f"Created {meta_created} .meta.json files for dashboard discovery")

    # Record to audit trail (backtest results → bt_backtest_runs table)
    print("\nRecording to audit trail...")
    try:
        from audit_trail.recorder import record_backtest_batch
        audit_result = record_backtest_batch(results, source_db=f"real_data_sweep_{ts}")
        print(f"Audit trail: {audit_result['recorded']} recorded, {audit_result['skipped']} skipped")
    except Exception as exc:
        print(f"Audit trail recording failed (non-fatal): {exc}")

    # Regenerate dashboard
    print("\nRegenerating battleground dashboard...")
    try:
        from incubator.backtest_team.generate_baby_strats_dashboard import (
            generate_dashboard,
            write_dashboard,
        )
        dashboard = generate_dashboard()
        write_dashboard(dashboard)
        print(f"Dashboard updated: {dashboard['total_strategies']} strategies, "
              f"{dashboard['passed_backtest']} passed")
    except Exception as exc:
        print(f"Dashboard regeneration failed: {exc}")

    return output


def main():
    parser = argparse.ArgumentParser(description="Batch backtest all unregistered strategies")
    parser.add_argument("--max", type=int, default=0, help="Max strategies to test (0=all)")
    parser.add_argument("--timeout", type=int, default=25, help="Timeout per strategy in seconds")
    parser.add_argument("--force", action="store_true", help="Re-test already tested strategies")
    parser.add_argument("--agents-only", action="store_true", help="Only test incubator/agents")
    parser.add_argument("--babies-only", action="store_true", help="Only test baby_strategies")
    args = parser.parse_args()

    run_batch(
        max_strategies=args.max,
        timeout_sec=args.timeout,
        force=args.force,
        agents_only=args.agents_only,
        babies_only=args.babies_only,
    )


if __name__ == "__main__":
    main()
