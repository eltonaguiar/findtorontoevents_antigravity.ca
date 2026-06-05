#!/usr/bin/env python3
"""mlflow_high_quality_picks.py — Surface bias-survivor picks per persona x class x symbol.

Operator ask 2026-06-05: "get us some proper high-quality picks, or set a plan
to get us there."

This script applies a 3-stage filter to tournament_picks:
  Stage 1: persona x asset_class cells must survive bias scrutiny
           (sym_HHI<0.5, fam_HHI<0.5, replay<25%, >=3 syms, >=3 model families)
  Stage 2: within survivor cells, symbol-level breakdown for n>=5 by direction
  Stage 3: high-quality flag for symbol-level WR>=60% AND n>=5

Logs to mlflow.db experiment 'high_quality_picks_2026-06-05' with metrics:
  hist_n, hist_wr, hist_avg_pnl, current_open_models, current_avg_entry

Companion to:
  - tools/mlflow_bias_detector.py  (cell-level bias scoring)
  - tools/mlflow_persona_edge_scan.py  (raw persona x class metrics)
"""
from __future__ import annotations

import os
import sys
import warnings

import mlflow
import pymysql

warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLRUNS_DB = os.path.join(REPO, "mlflow.db")
sys.path.insert(0, REPO)
from tools.mlflow_bias_detector import scrutinize_cell


def _connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(**get_stocks_creds())


def main():
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("high_quality_picks_2026-06-05")
    print(f"mlflow: sqlite:///{MLRUNS_DB}")

    # Stage 1: survivor cells (n>=15, WR>=55%, sym_HHI<0.5, fam_HHI<0.5, replay<25%, >=3 syms, >=3 families)
    conn = _connect()
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            """SELECT persona_id, asset_class, COUNT(*) n
               FROM tournament_picks WHERE status IN ('WIN','LOSS') AND persona_id IS NOT NULL
               GROUP BY persona_id, asset_class HAVING n>=15"""
        )
        cells = cur.fetchall()
    conn.close()

    survivors = []
    for cell in cells:
        res = scrutinize_cell(cell["persona_id"], cell["asset_class"])
        if not res or res["n"] < 15:
            continue
        if (
            res["wr"] >= 0.55
            and res["sym_hhi"] < 0.5
            and res["fam_hhi"] < 0.5
            and res["replay_share"] < 0.25
            and res["unique_symbols"] >= 3
            and res["unique_model_families"] >= 3
        ):
            survivors.append((cell["persona_id"], cell["asset_class"], res))

    print(f"\n{len(survivors)} bias-survivor persona x class cells")

    # Stage 2-3: within survivors, find high-quality symbol picks
    print("\n=== HIGH-QUALITY PICKS (bias-survivor cell + symbol-level WR>=60%, n>=5) ===")
    print(f"{'persona':22} {'class':10} {'sym':8} {'dir':5} {'hist_n':>6} {'WR':>5} {'avg':>6} {'open_models':>11}")

    high_quality = []
    conn = _connect()
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        for persona, ac, cell_res in survivors:
            cur.execute(
                """SELECT symbol, direction, COUNT(*) n,
                          SUM(status='WIN')/COUNT(*) wr,
                          AVG(pnl_pct) avg
                   FROM tournament_picks
                   WHERE persona_id=%s AND asset_class=%s AND status IN ('WIN','LOSS')
                   GROUP BY symbol, direction HAVING n>=5 AND wr>=0.6""",
                (persona, ac),
            )
            symbol_picks = cur.fetchall()
            for sp in symbol_picks:
                # Is this currently OPEN with multi-model consensus?
                cur.execute(
                    """SELECT COUNT(*) n_open, COUNT(DISTINCT model_id) n_models,
                              ROUND(AVG(entry_price),4) avg_entry
                       FROM tournament_picks
                       WHERE persona_id=%s AND asset_class=%s AND symbol=%s AND direction=%s
                         AND status='OPEN'""",
                    (persona, ac, sp["symbol"], sp["direction"]),
                )
                open_info = cur.fetchone()
                hq = {
                    "persona": persona,
                    "asset_class": ac,
                    "symbol": sp["symbol"],
                    "direction": sp["direction"],
                    "hist_n": sp["n"],
                    "hist_wr": round(float(sp["wr"]), 4),
                    "hist_avg_pnl": round(float(sp["avg"] or 0), 4),
                    "open_n": open_info["n_open"] or 0,
                    "open_models": open_info["n_models"] or 0,
                    "open_avg_entry": float(open_info["avg_entry"]) if open_info["avg_entry"] else None,
                    "bias_score": cell_res["bias_score"],
                }
                high_quality.append(hq)

                with mlflow.start_run(run_name=f"{persona}_{ac}_{sp['symbol']}_{sp['direction']}"):
                    for k, v in hq.items():
                        if isinstance(v, (int, float)) and v is not None:
                            mlflow.log_metric(k, float(v))
                        else:
                            mlflow.log_param(k, str(v))
                    mlflow.set_tag("scan_date", "2026-06-05")

    conn.close()

    high_quality.sort(key=lambda h: (-h["hist_wr"], -h["hist_n"]))
    for h in high_quality:
        om = f"{h['open_models']} @ ${h['open_avg_entry']}" if h["open_n"] else "no"
        print(
            f"  {h['persona']:22} {h['asset_class']:10} {h['symbol']:8} {h['direction']:5} "
            f"{h['hist_n']:>6} {h['hist_wr']*100:>4.1f}% {h['hist_avg_pnl']:>+5.2f}% "
            f"{om:>11}"
        )

    print(f"\n{len(high_quality)} high-quality picks logged to mlflow.db")
    print("View: mlflow ui --backend-store-uri sqlite:///mlflow.db")


if __name__ == "__main__":
    main()
