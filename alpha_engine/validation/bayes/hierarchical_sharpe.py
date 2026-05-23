"""
Hierarchical Sharpe updater (Empirical-Bayes approximation).

Reads strategy-level test stats from MySQL and writes posterior-like edge fields
used by promotion gates:
- posterior_mean_sharpe
- prob_sharpe_gt_zero
"""

from __future__ import annotations

import os
import math
from datetime import datetime, timezone
from typing import List, Dict, Any

import mysql.connector
import numpy as np
import pandas as pd


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _db():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST") or "mysql.50webs.com",
        user=os.environ.get("MYSQL_USER") or "ejaguiar1_stocks",
        password=os.environ.get("MYSQL_PASSWORD") or "",
        database=os.environ.get("MYSQL_DB") or "ejaguiar1_stocks",
    )


def _load_strategy_stats(conn) -> pd.DataFrame:
    q = """
    SELECT strategy_id,
           COUNT(*) AS n_obs,
           AVG(COALESCE(sharpe,0)) AS mean_sharpe,
           STDDEV_POP(COALESCE(sharpe,0)) AS sd_sharpe
    FROM strategy_test_runs
    WHERE test_layer IN ('walk_forward','forward_test','stats')
    GROUP BY strategy_id
    """
    return pd.read_sql(q, conn)


def _empirical_bayes(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    global_mu = float(df["mean_sharpe"].mean())
    tau2 = float(df["mean_sharpe"].var(ddof=0)) if len(df) > 1 else 0.05
    tau2 = max(tau2, 1e-4)

    out: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        sid = str(row["strategy_id"])
        n = max(int(row["n_obs"]), 1)
        y = float(row["mean_sharpe"])
        sd = float(row["sd_sharpe"]) if not np.isnan(row["sd_sharpe"]) else 0.5
        se2 = max((sd * sd) / n, 1e-4)

        # Normal-normal shrinkage posterior
        post_var = 1.0 / (1.0 / tau2 + 1.0 / se2)
        post_mean = post_var * (global_mu / tau2 + y / se2)
        post_sd = math.sqrt(post_var)
        prob_gt_zero = 1.0 - _norm_cdf((0.0 - post_mean) / max(post_sd, 1e-6))

        out.append(
            {
                "strategy_id": sid,
                "posterior_mean_sharpe": round(float(post_mean), 6),
                "prob_sharpe_gt_zero": round(float(prob_gt_zero), 6),
                "n_obs": n,
            }
        )
    return out


def _persist(conn, rows: List[Dict[str, Any]]) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_bayes_edge (
          strategy_id VARCHAR(128) PRIMARY KEY,
          posterior_mean_sharpe DECIMAL(12,6) NOT NULL,
          prob_sharpe_gt_zero DECIMAL(12,6) NOT NULL,
          n_obs INT NOT NULL,
          updated_at DATETIME NOT NULL
        )
        """
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        cur.execute(
            """
            INSERT INTO strategy_bayes_edge
              (strategy_id, posterior_mean_sharpe, prob_sharpe_gt_zero, n_obs, updated_at)
            VALUES (%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              posterior_mean_sharpe=VALUES(posterior_mean_sharpe),
              prob_sharpe_gt_zero=VALUES(prob_sharpe_gt_zero),
              n_obs=VALUES(n_obs),
              updated_at=VALUES(updated_at)
            """,
            (
                r["strategy_id"],
                r["posterior_mean_sharpe"],
                r["prob_sharpe_gt_zero"],
                r["n_obs"],
                now,
            ),
        )
    conn.commit()


def main() -> None:
    conn = _db()
    df = _load_strategy_stats(conn)
    rows = _empirical_bayes(df)
    _persist(conn, rows)
    print(f"Updated strategy_bayes_edge rows: {len(rows)}")


if __name__ == "__main__":
    main()

