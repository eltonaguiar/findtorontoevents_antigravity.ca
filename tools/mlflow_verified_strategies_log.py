#!/usr/bin/env python3
"""mlflow_verified_strategies_log.py — Log post-INCIDENT-94 verified-strategy stats to MLflow.

Reads the 6 verified-strategy sleeves from trading_picks DB (post-backfill),
computes per-strategy WR/PF/avg_pnl + a statsmodels Augmented Dickey-Fuller
test on the cumulative-pnl curve to flag mean-reversion vs trend signature,
and logs everything to mlflow at ./mlruns/.

Run from repo root: python3 tools/mlflow_verified_strategies_log.py

After running, view the UI: mlflow ui --backend-store-uri file:./mlruns
(default :5000)

Refs:
- INCIDENT #94 backfill (commit 575b5b6153)
- reports/verified_strategies_unlock_2026-06-04.md
- 6-engine swarm consensus 2026-06-04: mlflow #1 high-ROI pick
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import mlflow
import numpy as np
import pymysql
from statsmodels.tsa.stattools import adfuller

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLRUNS_DB = os.path.join(REPO, "mlflow.db")
# mlflow 3.x deprecated the filesystem backend in favor of SQL. Use local SQLite
# — no cloud server needed; the .db file lives in repo root and is gitignored.
ARTIFACTS = os.path.join(REPO, "mlruns_artifacts")

STRATEGIES = [
    "B_flip_PriceRocMeanReversion",
    "inverse_ml_enhanced_BTCUSDT_15m_D",
    "inverse_ml_enhanced_ADAUSDT_15m_D",
    "inverse_ml_enhanced_RENDERUSDT_1h_D",
    "inverse_ml_enhanced_RENDERUSDT_4h_D",
    "etf_dual_momentum",
]


def _connect():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS_STOCKS", "stocks1234560"),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        connect_timeout=20,
    )


def fetch_pnls(strategy: str) -> list[float]:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT pnl_pct FROM trading_picks
               WHERE strategy=%s AND pnl_pct IS NOT NULL AND pnl_pct != 0
                 AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT')
               ORDER BY closed_at""",
            (strategy,),
        )
        rows = [float(r[0]) for r in cur.fetchall()]
    conn.close()
    return rows


def main() -> int:
    os.makedirs(ARTIFACTS, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("verified_strategies_post_incident_94")
    print(f"mlflow tracking: sqlite:///{MLRUNS_DB}")

    for strat in STRATEGIES:
        pnls = fetch_pnls(strat)
        if not pnls:
            print(f"  {strat}: no rows, skip")
            continue
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        n = len(pnls)
        wr = len(wins) / n if n else 0
        gross_w = sum(wins) if wins else 0.0
        gross_l = abs(sum(losses)) if losses else 0.0001
        pf = gross_w / gross_l if gross_l else 0
        avg = sum(pnls) / n if n else 0
        cum = np.cumsum(pnls)
        # ADF test: H0=non-stationary. p<0.05 => stationary => mean-revert signature.
        try:
            adf_stat, adf_p, *_ = adfuller(cum, autolag="AIC")
        except Exception:
            adf_stat, adf_p = float("nan"), float("nan")

        with mlflow.start_run(run_name=strat):
            mlflow.log_param("strategy_id", strat)
            mlflow.log_param("data_source", "trading_picks post INCIDENT #94 backfill")
            mlflow.log_metric("n_closed", n)
            mlflow.log_metric("wr", round(wr, 4))
            mlflow.log_metric("pf", round(pf, 4))
            mlflow.log_metric("avg_pnl_pct", round(avg, 4))
            mlflow.log_metric("cum_pnl_pct", round(float(cum[-1]), 4))
            mlflow.log_metric("max_drawdown_pct", round(float((cum - np.maximum.accumulate(cum)).min()), 4))
            mlflow.log_metric("adf_stat", float(adf_stat))
            mlflow.log_metric("adf_pvalue", float(adf_p))
            verdict = "MEAN_REVERT" if adf_p < 0.05 else "TREND_OR_NOISE"
            mlflow.log_param("adf_verdict", verdict)
            mlflow.set_tag("incident_ref", "INCIDENT_94_resolved_2026-06-04")
        print(f"  {strat:42} n={n:>3} WR={wr*100:5.1f}% PF={pf:5.2f} cum={cum[-1]:7.2f}% ADF_p={adf_p:.3f} {verdict}")

    print(f"\nView UI locally (no cloud): mlflow ui --backend-store-uri sqlite:///{MLRUNS_DB}")
    print("Then open http://localhost:5000 in browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
