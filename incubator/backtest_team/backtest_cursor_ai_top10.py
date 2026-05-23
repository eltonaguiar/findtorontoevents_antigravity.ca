#!/usr/bin/env python3
"""
Backtest cursor_ai top-10 baby strategies on real market data.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from incubator.backtest_team.real_data_sweep_runner import RealDataSweepRunner


STRATEGY_FILES = [
    "crypto_liquidation_flow_exhaustion_v1.py",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest cursor_ai top-10 on real crypto data db.")
    p.add_argument("--db-path", default=str(ROOT / "crypto_data.db"))
    p.add_argument("--pairs", default="BTC/USDT,ETH/USDT,SOL/USDT")
    p.add_argument("--bars", type=int, default=1800)
    p.add_argument("--min-bars", type=int, default=80)
    p.add_argument("--bar-step", type=int, default=2)
    p.add_argument("--max-hold-bars", type=int, default=20)
    p.add_argument("--strategy-timeout-sec", type=int, default=25)
    p.add_argument("--output-dir", default=str(ROOT / "incubator" / "backtest_results"))
    return p.parse_args()


def run_for_pair(pair: str, args: argparse.Namespace) -> List[Dict[str, Any]]:
    strategies_dir = ROOT / "incubator" / "agents" / "cursor_ai"
    runner = RealDataSweepRunner(
        db_path=args.db_path,
        pair=pair,
        bars=args.bars,
        min_bars=args.min_bars,
        bar_step=args.bar_step,
        max_hold_bars=args.max_hold_bars,
        strategy_timeout_sec=args.strategy_timeout_sec,
    )
    rows: List[Dict[str, Any]] = []
    for filename in STRATEGY_FILES:
        path = strategies_dir / filename
        result = runner.run_strategy(path)
        row = asdict(result)
        row["pair"] = pair
        rows.append(row)
        print(f"[{pair}] {path.stem}: {result.status} | sharpe={result.sharpe} | win={result.win_rate} | dd={result.max_drawdown} | trades={result.total_trades}")
    return rows


def main() -> int:
    args = parse_args()
    pairs = [x.strip() for x in args.pairs.split(",") if x.strip()]

    all_rows: List[Dict[str, Any]] = []
    for pair in pairs:
        all_rows.extend(run_for_pair(pair, args))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"cursor_ai_top10_realdata_{stamp}.json"
    csv_path = out_dir / f"cursor_ai_top10_realdata_{stamp}.csv"
    summary_path = out_dir / f"cursor_ai_top10_realdata_{stamp}_summary.md"

    payload = {
        "generated_at": datetime.now().isoformat(),
        "pairs": pairs,
        "strategy_files": STRATEGY_FILES,
        "results": all_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df.to_csv(csv_path, index=False)
        agg = (
            df.groupby("strategy_name", as_index=False)
            .agg(
                tested_pairs=("pair", "count"),
                pass_count=("status", lambda s: int((s == "passed").sum())),
                avg_sharpe=("sharpe", "mean"),
                avg_win_rate=("win_rate", "mean"),
                avg_drawdown=("max_drawdown", "mean"),
                avg_return=("total_return", "mean"),
                avg_trades=("total_trades", "mean"),
            )
            .sort_values(["pass_count", "avg_sharpe", "avg_return"], ascending=[False, False, False])
        )
        agg.to_csv(out_dir / f"cursor_ai_top10_realdata_{stamp}_aggregated.csv", index=False)
        lines = [
            "# Cursor AI Top-10 Real-Data Backtest",
            "",
            f"- Generated: {datetime.now().isoformat()}",
            f"- Pairs: {', '.join(pairs)}",
            f"- Total rows: {len(df)}",
            "",
            "## Top Strategies (Aggregated)",
            "",
            agg.head(10).to_markdown(index=False),
            "",
            "## Raw Output Files",
            "",
            f"- JSON: `{json_path}`",
            f"- CSV: `{csv_path}`",
        ]
        summary_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        csv_path.write_text("", encoding="utf-8")
        summary_path.write_text("# No rows generated\n", encoding="utf-8")

    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV : {csv_path}")
    print(f"Saved SUM : {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
