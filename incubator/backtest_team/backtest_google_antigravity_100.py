#!/usr/bin/env python3
"""
Backtest the 100-strategy "google antigravity" set on real data.

Target set construction:
- 11 pre-existing web_ai strategies (from PROGRESS.md baseline list)
- 89 strategies introduced in batch commits #12-100
  (commit range entries listed in BATCH_COMMITS)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from incubator.backtest_team.real_data_sweep_runner import RealDataSweepRunner, SweepResult

BATCH_COMMITS = [
    "3c4fa541",  # #12-21
    "51c0d04f",  # #22-31
    "a37ddc1e",  # #32-41
    "09938426",  # #42-51
    "04e1dc44",  # #52-61
    "2db1d764",  # #62-71
    "98d9859a",  # #72-81
    "c1fdd9e2",  # #82-100
]

PREEXISTING_11 = [
    "atr_regime_rsi",
    "vol_contraction_breakout",
    "drawdown_recovery_rsi",
    "multi_period_rsi_confluence",
    "lower_wick_absorption",
    "false_low_break_reversal",
    "atr_percentile_gate",
    "dxy_divergence_alpha",
    "mean_reversion_momentum",
    "volume_breakout_regime_switch",
    "whale_vwap_breakout",
]

# These were added in batch commit windows but are outside the canonical
# "100 strategy" list provided in the batch table.
EXCLUDED_FROM_100 = {
    "crossasset_spxbtc_zscore_divergence_v1",
    "fear_greed_reversion",
}


def _run_git(args: List[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def resolve_batch_files() -> List[Path]:
    out = _run_git(["show", "--name-only", "--pretty=format:", *BATCH_COMMITS])
    rels = []
    seen = set()
    for line in out.splitlines():
        rel = line.strip()
        if not rel.startswith("incubator/agents/web_ai/") or not rel.endswith(".py"):
            continue
        if rel in seen:
            continue
        seen.add(rel)
        rels.append(ROOT / rel)
    return rels


def build_target_list() -> Tuple[List[Path], List[Path]]:
    batch_paths = resolve_batch_files()
    pre_paths = [ROOT / "incubator" / "agents" / "web_ai" / f"{name}.py" for name in PREEXISTING_11]

    ordered: List[Path] = []
    seen = set()
    for p in [*pre_paths, *batch_paths]:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        ordered.append(p)

    ordered = [p for p in ordered if p.stem not in EXCLUDED_FROM_100]
    missing_local = [p for p in ordered if not p.exists()]
    return ordered, missing_local


def exists_on_origin_main(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"origin/main:{rel}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def write_outputs(results: List[SweepResult], targets: List[Path], missing_local: List[Path], missing_origin: List[Path], out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"google_antigravity_100_backtest_{stamp}.json"
    csv_path = out_dir / f"google_antigravity_100_backtest_{stamp}.csv"

    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status.startswith("failed"))
    timeouts = sum(1 for r in results if r.status == "timeout")
    errors = sum(1 for r in results if r.status == "error")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "target_count": len(targets),
        "tested_count": len(results),
        "passed": passed,
        "failed": failed,
        "timeouts": timeouts,
        "errors": errors,
        "missing_local_count": len(missing_local),
        "missing_origin_main_count": len(missing_origin),
        "target_files": [str(p.relative_to(ROOT)) for p in targets],
        "missing_local": [str(p.relative_to(ROOT)) for p in missing_local],
        "missing_origin_main": [str(p.relative_to(ROOT)) for p in missing_origin],
        "results": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    df = pd.DataFrame([asdict(r) for r in results])
    if not df.empty:
        for c in ("status", "sharpe", "win_rate", "total_return", "total_trades"):
            if c not in df.columns:
                df[c] = None
        df = df.sort_values(
            ["status", "sharpe", "win_rate", "total_return", "total_trades"],
            ascending=[True, False, False, False, False],
            na_position="last",
        )
        df.to_csv(csv_path, index=False)
    else:
        csv_path.write_text("", encoding="utf-8")

    return json_path, csv_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest google antigravity 100 strategy set.")
    p.add_argument("--db-path", default="crypto_data.db")
    p.add_argument("--pair", default="BTC/USDT")
    p.add_argument("--bars", type=int, default=1808)
    p.add_argument("--initial-capital", type=float, default=10000.0)
    p.add_argument("--commission", type=float, default=0.001)
    p.add_argument("--max-hold-bars", type=int, default=20)
    p.add_argument("--min-bars", type=int, default=80)
    p.add_argument("--bar-step", type=int, default=2)
    p.add_argument("--strategy-timeout-sec", type=int, default=25)
    p.add_argument("--output-dir", default="incubator/backtest_results")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    targets, missing_local = build_target_list()
    print(f"[SET] target strategies (deduped): {len(targets)}")
    print(f"[SET] missing locally: {len(missing_local)}")
    if len(targets) != 100:
        print(f"[WARN] Expected 100 strategies, got {len(targets)}")

    # Ensure remote refs are fresh for origin/main existence checks.
    try:
        _run_git(["fetch", "origin", "main"])
    except Exception as exc:
        print(f"[WARN] origin/main fetch failed: {exc}")

    missing_origin = [p for p in targets if not exists_on_origin_main(p)]
    print(f"[SET] missing on origin/main: {len(missing_origin)}")

    runner = RealDataSweepRunner(
        db_path=str(ROOT / args.db_path),
        pair=args.pair,
        bars=args.bars,
        initial_capital=args.initial_capital,
        commission=args.commission,
        max_hold_bars=args.max_hold_bars,
        min_bars=args.min_bars,
        bar_step=args.bar_step,
        strategy_timeout_sec=args.strategy_timeout_sec,
    )

    results: List[SweepResult] = []
    test_targets = [p for p in targets if p.exists()]
    total = len(test_targets)
    for i, path in enumerate(test_targets, 1):
        print(f"[{i}/{total}] Backtesting {path.parent.name}/{path.stem} ...")
        res = runner.run_strategy(path)
        results.append(res)
        print(
            f"    -> {res.status} | trades={res.total_trades} | "
            f"sharpe={res.sharpe} | win={res.win_rate} | dd={res.max_drawdown} | "
            f"{res.duration_sec:.2f}s"
        )

    json_path, csv_path = write_outputs(
        results=results,
        targets=targets,
        missing_local=missing_local,
        missing_origin=missing_origin,
        out_dir=ROOT / args.output_dir,
    )

    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status.startswith("failed"))
    timeouts = sum(1 for r in results if r.status == "timeout")
    errors = sum(1 for r in results if r.status == "error")

    print("\n" + "=" * 80)
    print("GOOGLE ANTIGRAVITY 100 BACKTEST COMPLETE")
    print("=" * 80)
    print(
        f"Target: {len(targets)} | Tested: {len(results)} | Passed: {passed} | "
        f"Failed: {failed} | Timeouts: {timeouts} | Errors: {errors}"
    )
    print(f"Missing local: {len(missing_local)} | Missing on origin/main: {len(missing_origin)}")
    print(f"JSON: {json_path}")
    print(f"CSV : {csv_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
