#!/usr/bin/env python3
"""
Backtest 10 codex_gpt5 v2 strategies on live scraped market data.

Uses RealDataSweepRunner over multiple pairs and writes JSON/CSV outputs.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from incubator.backtest_team.real_data_sweep_runner import RealDataSweepRunner


DB_PATH = PROJECT_ROOT / "crypto_data.db"
STRATEGY_DIR = PROJECT_ROOT / "incubator" / "agents" / "codex_gpt5"
RESULTS_DIR = PROJECT_ROOT / "incubator" / "backtest_results"

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
STRATEGY_FILES = sorted(STRATEGY_DIR.glob("*_v2.py"))


def run() -> Dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    rows: List[Dict] = []
    for pair in PAIRS:
        runner = RealDataSweepRunner(
            db_path=str(DB_PATH),
            pair=pair,
            bars=1800,
            initial_capital=10000.0,
            commission=0.001,
            max_hold_bars=20,
            min_bars=100,
            bar_step=2,
            strategy_timeout_sec=45,
        )
        for py_file in STRATEGY_FILES:
            result = runner.run_strategy(py_file)
            rows.append(
                {
                    "pair": pair,
                    "strategy_name": result.strategy_name,
                    "status": result.status,
                    "sharpe": result.sharpe,
                    "win_rate": result.win_rate,
                    "max_drawdown": result.max_drawdown,
                    "profit_factor": result.profit_factor,
                    "total_return": result.total_return,
                    "total_trades": result.total_trades,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                }
            )
            print(
                f"{pair:9s} | {result.strategy_name:45s} | {result.status:24s} | "
                f"Sharpe={result.sharpe} WR={result.win_rate} DD={result.max_drawdown} Ret={result.total_return} Trades={result.total_trades}"
            )

    df = pd.DataFrame(rows)
    summary = (
        df.groupby("strategy_name", as_index=False)
        .agg(
            pairs=("pair", "count"),
            passed_count=("status", lambda s: int((s == "passed").sum())),
            avg_sharpe=("sharpe", "mean"),
            avg_win_rate=("win_rate", "mean"),
            avg_max_drawdown=("max_drawdown", "mean"),
            avg_profit_factor=("profit_factor", "mean"),
            avg_total_return=("total_return", "mean"),
            total_trades=("total_trades", "sum"),
        )
        .sort_values(["passed_count", "avg_sharpe", "avg_total_return"], ascending=[False, False, False])
        .reset_index(drop=True)
    )

    out_json = RESULTS_DIR / f"codex10_live_multipair_{ts}.json"
    out_csv = RESULTS_DIR / f"codex10_live_multipair_{ts}.csv"
    out_summary_csv = RESULTS_DIR / f"codex10_live_multipair_{ts}_summary.csv"

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pairs": PAIRS,
        "strategy_count": len(STRATEGY_FILES),
        "rows": rows,
        "summary": summary.to_dict(orient="records"),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    df.to_csv(out_csv, index=False)
    summary.to_csv(out_summary_csv, index=False)

    print(f"\nSaved: {out_json}")
    print(f"Saved: {out_csv}")
    print(f"Saved: {out_summary_csv}")

    return payload


if __name__ == "__main__":
    run()
