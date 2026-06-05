#!/usr/bin/env python3
"""Walk-forward rolling-window OOS validation per strategy×category cell.

Complementary to `tools/walk_forward_backtest.py` (which does Brier-score
confidence calibration on dashboard_data.json closed picks). This one rolls a
per-strategy IS/OOS window over the live MySQL trading_picks pnl series and
flags strategies whose OOS PF collapses vs their IS PF — the "lab-vs-forward
divergence" pattern that killed stocks_rsi2_pullback (PF 7.88 → 0.47) and
luxalgo_confluence (lab PF 2.36 → live 0.97).

Methodology
-----------
For each (strategy, category) cell with n >= MIN_N_TOTAL closed picks:
  - Sort closes chronologically by closed_at
  - Build rolling windows: IS = first IN_WINDOW picks, OOS = next OUT_WINDOW picks
  - Step forward by STEP picks
  - For each window: compute IS PF/WR, OOS PF/WR
  - Survival rule: OOS PF must be >= 0.85 * IS PF (per MASTERPLAN Action 4 §4)
  - Aggregate: count surviving windows / total windows = WF_SURVIVAL_RATE

PASS criteria:
  - n_windows >= MIN_WINDOWS
  - survival_rate >= SURVIVAL_THRESHOLD (default 0.60)
  - mean_oos_pf >= 1.2
  - mean_oos_wr >= 0.50

Source: Mercury 2 (Inception Labs) audit-toolkit Sec 2.3 + the operator-shared
enhancement plan's walk_forward_backtest_example.py.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

OUT_JSON = REPO / "audit_dashboard" / "data" / "walk_forward_per_strategy_latest.json"

MIN_N_TOTAL_DEFAULT = 100
IN_WINDOW_DEFAULT = 60
OUT_WINDOW_DEFAULT = 20
STEP_DEFAULT = 10
MIN_WINDOWS_FOR_VERDICT = 3
SURVIVAL_THRESHOLD = 0.60
IS_OOS_PF_DECAY_TOLERANCE = 0.85


def _f(x):
    return float(x) if isinstance(x, Decimal) else x


def _connect():
    return pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)


def _pf_wr(pnls: list[float]) -> tuple[float, float]:
    if not pnls:
        return 0.0, 0.0
    gw = sum(x for x in pnls if x > 0)
    gl = sum(-x for x in pnls if x < 0)
    pf = gw / gl if gl else (float("inf") if gw > 0 else 0.0)
    wr = sum(1 for x in pnls if x > 0) / len(pnls)
    return pf, wr


def _eligible_cells(cur, min_n: int, strategy_filter: str | None) -> list[dict]:
    where_extra = ""
    params: tuple = ()
    if strategy_filter:
        where_extra = "AND strategy = %s"
        params = (strategy_filter,)
    # Exclude 2026-06-04 resolver backfill (5,960 commodity rows in one day;
    # see reports/deep_dive_commodity_2026-06-05.md). Without this, walk-forward
    # reports spurious PASS for futures_bb_mean_reversion::commodity that
    # contradicts the LOW_CONFIDENCE_STRATEGIES auto_tuner ban.
    backfill_filter = "AND DATE(closed_at) != '2026-06-04'"
    cur.execute(f"""
        SELECT strategy, category, COUNT(*) n
        FROM trading_picks
        WHERE closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','WON')
          {backfill_filter}
          {where_extra}
        GROUP BY strategy, category
        HAVING n >= %s
        ORDER BY n DESC
    """, params + (min_n,))
    return cur.fetchall()


def walk_forward_one(cur, strategy: str, category: str,
                     in_window: int, out_window: int, step: int) -> dict:
    cur.execute("""
        SELECT pnl_pct FROM trading_picks
        WHERE strategy=%s AND category=%s
          AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','WON')
          AND DATE(closed_at) != '2026-06-04'
        ORDER BY closed_at ASC
    """, (strategy, category))
    pnls = [_f(r["pnl_pct"]) for r in cur.fetchall()]
    n = len(pnls)
    windows = []
    surviving = 0
    is_pfs: list[float] = []
    oos_pfs: list[float] = []
    oos_wrs: list[float] = []
    start_idx = in_window
    while start_idx + out_window <= n:
        is_chunk = pnls[start_idx - in_window:start_idx]
        oos_chunk = pnls[start_idx:start_idx + out_window]
        is_pf, _ = _pf_wr(is_chunk)
        oos_pf, oos_wr = _pf_wr(oos_chunk)
        survived = (oos_pf >= IS_OOS_PF_DECAY_TOLERANCE * is_pf
                    if (is_pf > 0 and is_pf != float("inf")) else False)
        if survived:
            surviving += 1
        windows.append({
            "is_pf": round(is_pf, 4) if is_pf != float("inf") else None,
            "oos_pf": round(oos_pf, 4) if oos_pf != float("inf") else None,
            "oos_wr": round(oos_wr, 4),
            "survived": survived,
        })
        if is_pf != float("inf"): is_pfs.append(is_pf)
        if oos_pf != float("inf"): oos_pfs.append(oos_pf)
        oos_wrs.append(oos_wr)
        start_idx += step

    n_windows = len(windows)
    survival_rate = surviving / n_windows if n_windows else 0.0
    mean_oos_pf = sum(oos_pfs) / len(oos_pfs) if oos_pfs else 0.0
    mean_oos_wr = sum(oos_wrs) / len(oos_wrs) if oos_wrs else 0.0
    mean_is_pf = sum(is_pfs) / len(is_pfs) if is_pfs else 0.0

    if n_windows < MIN_WINDOWS_FOR_VERDICT:
        verdict = "INSUFF_N"
        reasons = [f"n_windows={n_windows} < {MIN_WINDOWS_FOR_VERDICT}"]
    else:
        reasons: list[str] = []
        if survival_rate < SURVIVAL_THRESHOLD:
            reasons.append(f"survival_rate={survival_rate:.2f} < {SURVIVAL_THRESHOLD}")
        if mean_oos_pf < 1.2:
            reasons.append(f"mean_oos_pf={mean_oos_pf:.2f} < 1.2")
        if mean_oos_wr < 0.50:
            reasons.append(f"mean_oos_wr={mean_oos_wr:.2f} < 0.50")
        verdict = "FAIL" if reasons else "PASS"

    return {
        "strategy": strategy,
        "category": category,
        "n_total": n,
        "n_windows": n_windows,
        "n_surviving": surviving,
        "survival_rate": round(survival_rate, 4),
        "mean_oos_pf": round(mean_oos_pf, 4),
        "mean_oos_wr": round(mean_oos_wr, 4),
        "mean_is_pf": round(mean_is_pf, 4),
        "verdict": verdict,
        "reasons": reasons,
    }


def run(args) -> dict:
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {
            "in_window": args.in_window,
            "out_window": args.out_window,
            "step": args.step,
            "min_n_total": args.min_n,
            "survival_threshold": SURVIVAL_THRESHOLD,
            "is_oos_pf_decay_tolerance": IS_OOS_PF_DECAY_TOLERANCE,
        },
        "cells": [],
        "summary": {},
    }
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cells = _eligible_cells(cur, args.min_n, args.strategy)
            for c in cells:
                out["cells"].append(
                    walk_forward_one(cur, c["strategy"], c["category"],
                                     args.in_window, args.out_window, args.step)
                )
    finally:
        conn.close()

    counts = {"PASS": 0, "FAIL": 0, "INSUFF_N": 0}
    for c in out["cells"]:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    out["summary"] = {
        "total_cells": len(out["cells"]),
        "verdict_counts": counts,
        "pass_candidates": [
            f"{c['strategy']}::{c['category']}"
            for c in out["cells"] if c["verdict"] == "PASS"
        ],
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-strategy rolling-window walk-forward (live trading_picks)")
    ap.add_argument("--strategy", help="Limit to one strategy")
    ap.add_argument("--min-n", type=int, default=MIN_N_TOTAL_DEFAULT)
    ap.add_argument("--in-window", type=int, default=IN_WINDOW_DEFAULT)
    ap.add_argument("--out-window", type=int, default=OUT_WINDOW_DEFAULT)
    ap.add_argument("--step", type=int, default=STEP_DEFAULT)
    args = ap.parse_args()

    out = run(args)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(json.dumps(out["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
