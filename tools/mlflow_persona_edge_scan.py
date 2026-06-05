#!/usr/bin/env python3
"""mlflow_persona_edge_scan.py — Persona-level edge scan, logged to mlflow.

Per operator question 2026-06-04: "apply mlflow + statsmodels to existing
picks/strategies, what about persona picks on /audit/ai-tournament.html?"

Scans tournament_picks for every (persona_id, asset_class) cell with n>=10.
For each: computes WR / PF / avg pnl / cumulative pnl / Augmented Dickey-Fuller
test on cumulative pnl curve. Logs to mlflow.db local SQLite.

Top finding from initial scan (2026-06-04):
- cta_trend × COMMODITY: n=15 / WR 86.7% / avg +7.15% (single strongest signal)
- macro_hedge × COMMODITY: n=18 / WR 77.8% / +5.21%
- trend_continuation × ETF: n=25 / WR 76.0% / +1.8%
- macro_hedge overall: n=23 / WR 60.9% / +3.22%

ADF interpretation:
  p < 0.05 -> stationary cum-pnl -> MEAN_REVERTING persona (size up after losses)
  p >= 0.5 -> non-stationary -> TRENDING (durably winning or losing; resize after run)

Usage: python3 tools/mlflow_persona_edge_scan.py
View: mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
from __future__ import annotations

import os
import warnings

import mlflow
import numpy as np
import pymysql
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLRUNS_DB = os.path.join(REPO, "mlflow.db")


def _connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(**get_stocks_creds())


def main():
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("persona_edge_scan_2026-06-04")
    print(f"mlflow: sqlite:///{MLRUNS_DB} (local, no cloud)")

    conn = _connect()
    cells = []
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        # All persona × asset_class cells with n>=10 closed
        cur.execute(
            """SELECT persona_id, asset_class, COUNT(*) n
               FROM tournament_picks
               WHERE status IN ('WIN','LOSS') AND persona_id IS NOT NULL
               GROUP BY persona_id, asset_class HAVING n>=10"""
        )
        cells = cur.fetchall()
    print(f"\nScanning {len(cells)} persona × class cells (n>=10)...\n")
    print(f"  {'persona':28} {'class':10} {'n':>4} {'WR':>5} {'PF':>5} {'avg':>7} {'cum':>8} {'MDD':>7} {'ADF_p':>6} verdict")

    standouts = []
    for cell in cells:
        persona = cell["persona_id"]
        ac = cell["asset_class"]
        conn2 = _connect()
        with conn2.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                """SELECT pnl_pct FROM tournament_picks
                   WHERE persona_id=%s AND asset_class=%s AND status IN ('WIN','LOSS')
                     AND pnl_pct IS NOT NULL
                   ORDER BY resolved_at""",
                (persona, ac),
            )
            pnls = [float(r["pnl_pct"]) for r in cur.fetchall()]
        conn2.close()
        if len(pnls) < 5:
            continue
        n = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        wr = len(wins) / n
        gross_w = sum(wins) if wins else 0.0
        gross_l = abs(sum(losses)) if losses else 0.0001
        pf = gross_w / gross_l if gross_l else 0
        avg = sum(pnls) / n
        cum = np.cumsum(pnls)
        mdd = float((cum - np.maximum.accumulate(cum)).min())
        try:
            _, adf_p, *_ = adfuller(cum, autolag="AIC")
        except Exception:
            adf_p = float("nan")
        verdict = "MEAN_REVERT" if (not np.isnan(adf_p) and adf_p < 0.05) else \
                  ("TRENDING_UP" if cum[-1] > 0 else "TRENDING_DOWN")

        with mlflow.start_run(run_name=f"{persona}__x__{ac}"):
            mlflow.log_param("persona_id", persona)
            mlflow.log_param("asset_class", ac)
            mlflow.log_param("verdict", verdict)
            mlflow.log_metric("n", n)
            mlflow.log_metric("wr", round(wr, 4))
            mlflow.log_metric("pf", round(pf, 4))
            mlflow.log_metric("avg_pnl_pct", round(avg, 4))
            mlflow.log_metric("cum_pnl_pct", round(float(cum[-1]), 4))
            mlflow.log_metric("max_drawdown_pct", round(mdd, 4))
            mlflow.log_metric("adf_pvalue", float(adf_p) if not np.isnan(adf_p) else 0.0)
            mlflow.set_tag("scan_date", "2026-06-04")

        # Standouts to surface
        if wr >= 0.6 and n >= 15 and avg > 0.5:
            standouts.append((persona, ac, n, wr, pf, avg, float(cum[-1]), mdd, adf_p, verdict))

        if wr >= 0.55 or wr <= 0.40:
            # Print only interesting cells (top/bottom)
            print(
                f"  {(persona or '?')[:28]:28} {ac:10} {n:>4} {wr*100:>4.1f}% "
                f"{pf:>4.2f} {avg:>6.2f}% {cum[-1]:>7.1f}% {mdd:>6.1f}% "
                f"{adf_p:>5.3f} {verdict}"
            )

    print("\n=== STANDOUT EDGES (WR>=60% n>=15 avg>=0.5%) ===")
    standouts.sort(key=lambda x: -x[3] * x[5])  # rank by WR * avg
    for p, ac, n, wr, pf, avg, cum, mdd, adf, v in standouts:
        print(
            f"  {(p or '?')[:28]:28} x {ac:10} n={n:>3} WR={wr*100:>4.1f}% "
            f"PF={pf:>4.2f} avg={avg:>+5.2f}% cum={cum:>+6.1f}% MDD={mdd:>5.1f}% "
            f"ADF_p={adf:.3f} {v}"
        )

    print(f"\nView all logged cells: mlflow ui --backend-store-uri sqlite:///{MLRUNS_DB}")


if __name__ == "__main__":
    main()
