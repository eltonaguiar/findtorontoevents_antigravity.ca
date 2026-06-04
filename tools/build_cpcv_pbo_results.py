"""Generate tools/cpcv_pbo_results.json from at_signal_outcomes (minimax-m3-free, 2026-06-02).

Builds a (T dates, S strategies) daily-aggregated pnl_pct returns matrix for
strategies with n>=30 closed picks, then runs cpcv_pbo() from
alpha_engine.anti_overfit_validator on the candidate set.

Repro:
  DB_PASS_STOCKS=<from-dbpasses.txt> python3 tools/build_cpcv_pbo_results.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "tools" / "cpcv_pbo_results.json"
MIN_N = 30
N_FOLDS = 10
N_TEST_GROUPS = 2


def get_conn():
    pw = os.environ.get("DB_PASS_STOCKS")
    if not pw:
        raise SystemExit("Set DB_PASS_STOCKS env var (ejaguiar1_stocks password)")
    return pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pw,
        database="ejaguiar1_stocks",
        port=3306,
    )


def load_pivot():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT strategy, asset_class, DATE(closed_at) as d, pnl_pct
        FROM at_signal_outcomes
        WHERE strategy IS NOT NULL AND strategy != ''
          AND closed_at IS NOT NULL
          AND pnl_pct IS NOT NULL
        """
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise SystemExit("No rows in at_signal_outcomes")
    df = pd.DataFrame(rows, columns=["strategy", "asset_class", "d", "pnl_pct"])
    df["d"] = pd.to_datetime(df["d"])
    df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce").fillna(0.0)

    counts = df.groupby(["strategy", "asset_class"]).size().reset_index(name="n")
    eligible = counts[counts["n"] >= MIN_N].copy()
    eligible = eligible.sort_values("n", ascending=False).reset_index(drop=True)
    selected = eligible["strategy"].tolist()

    df_sel = df[df["strategy"].isin(selected)].copy()
    daily = (
        df_sel.groupby(["d", "strategy", "asset_class"])["pnl_pct"]
        .sum()
        .reset_index()
    )
    pivot = daily.pivot_table(
        index="d", columns="strategy", values="pnl_pct", aggfunc="sum", fill_value=0.0
    )
    pivot = pivot.sort_index()
    pivot = pivot.reindex(columns=selected, fill_value=0.0)

    meta_rows = []
    for _, r in eligible.iterrows():
        strat = r["strategy"]
        sub = df_sel[df_sel["strategy"] == strat]
        n = int(r["n"])
        wins = int((sub["pnl_pct"] > 0).sum())
        wr = wins / n if n else 0.0
        sum_pnl = float(sub["pnl_pct"].sum())
        std = sub["pnl_pct"].std()
        sharpe = (
            float(sub["pnl_pct"].mean() / std * np.sqrt(252))
            if std and n > 1
            else 0.0
        )
        meta_rows.append(
            {
                "strategy": strat,
                "asset_class": r["asset_class"],
                "n": n,
                "wr": round(wr, 4),
                "sum_pnl_pct": round(sum_pnl, 4),
                "sharpe": round(sharpe, 4),
            }
        )
    meta = pd.DataFrame(meta_rows)
    return pivot, meta, selected


def interpret_pbo(pbo: float) -> str:
    if pbo < 0.3:
        return "STRONG selection edge survives out-of-sample (PBO<0.3)"
    if pbo < 0.5:
        return "PASS selection not worse than random (PBO<0.5)"
    if pbo < 0.7:
        return "BORDERLINE selection suspect (0.5<=PBO<0.7)"
    return "FAIL backtest overfit (PBO>=0.7)"


def main() -> int:
    sys.path.insert(0, str(REPO / "alpha_engine"))
    from anti_overfit_validator import cpcv_pbo  # noqa: E402

    pivot, meta, selected = load_pivot()
    T, S = pivot.shape
    if S < 2:
        raise SystemExit(f"Need >=2 strategies, got {S}")
    if T < N_FOLDS * 2:
        raise SystemExit(f"Need >={N_FOLDS*2} time periods, got T={T}")

    matrix = pivot.to_numpy(dtype=np.float64)
    pbo = cpcv_pbo(matrix, n_folds=N_FOLDS, n_test_groups=N_TEST_GROUPS)

    top10 = meta.sort_values("sharpe", ascending=False)["strategy"].head(10).tolist()
    per_strategy = []
    for r in meta.to_dict(orient="records"):
        r["selected_top10"] = r["strategy"] in top10
        per_strategy.append(r)

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_strategies": int(S),
        "T_dates": int(T),
        "min_n_per_strategy": MIN_N,
        "matrix_shape": [int(T), int(S)],
        "date_range": [
            str(pivot.index.min().date()),
            str(pivot.index.max().date()),
        ],
        "n_folds": N_FOLDS,
        "n_test_groups": N_TEST_GROUPS,
        "pbo": round(float(pbo), 4),
        "pbo_interpretation": interpret_pbo(float(pbo)),
        "per_strategy": per_strategy,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        json.dump(out, f, indent=2, sort_keys=False)
    print(f"pbo={pbo:.4f}  T={T}  S={S}  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
