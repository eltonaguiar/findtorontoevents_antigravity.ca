"""Build per-strategy walk-forward OOS results for EAGLE-6 v2 WF OOS gate.

Queries at_signal_outcomes, runs alpha_engine.walkforward_validator.walk_forward_validate
per strategy (rolling train/test windows), and writes tools/walkforward_oos_results.json
with per-strategy IS-PF, OOS-PF, OOS-Sharpe, decay, and the EAGLE-6 v2 verdict
(OOS_PF >= 0.8 * IS_PF for PASS).

Usage:
    DB_PASS_STOCKS=<from-dbpasses.txt> python3 tools/build_walkforward_oos_results.py

Output: tools/walkforward_oos_results.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pymysql

from alpha_engine.walkforward_validator import walk_forward_validate


def _pf(pnls: list[float]) -> float:
    """Profit factor: gross_profit / abs(gross_loss). Returns 0.0 if no losses,
    mirroring the post-PR-#464 mutation_framework behavior (no 999.0 sentinel)."""
    if not pnls:
        return 0.0
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = sum(abs(p) for p in pnls if p < 0)
    if gross_loss == 0:
        return 0.0
    return round(gross_profit / gross_loss, 3)


def _query_per_strategy(conn, min_n: int) -> list[dict]:
    """Return one row per (strategy, asset_class) with n>=min_n closed picks."""
    sql = """
        SELECT
            strategy,
            asset_class,
            COUNT(*) AS n,
            SUM(pnl_pct) AS sum_pnl_pct,
            SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS wins
        FROM at_signal_outcomes
        WHERE outcome IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','CLOSED')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL AND strategy <> '' AND strategy <> 'unknown'
        GROUP BY strategy, asset_class
        HAVING n >= %s
        ORDER BY n DESC
    """
    cur = conn.cursor()
    cur.execute(sql, (min_n,))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _query_trades(conn, strategy: str) -> list[dict]:
    """Return ordered trades for a single strategy: {pnl_pct, timestamp}."""
    sql = """
        SELECT pnl_pct, closed_at
        FROM at_signal_outcomes
        WHERE strategy = %s
          AND outcome IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','CLOSED')
        ORDER BY closed_at ASC
    """
    cur = conn.cursor()
    cur.execute(sql, (strategy,))
    out: list[dict] = []
    for r in cur.fetchall():
        if r[0] is None:
            continue
        out.append({"pnl_pct": float(r[0]), "timestamp": str(r[1])})
    return out


def _verdict(is_pf: float, oos_pf: float, oos_sharpe: float, n_folds: int) -> str:
    """EAGLE-6 v2 WF OOS gate verdict.
    PASS   if IS_PF > 0 AND OOS_PF >= 0.8 * IS_PF AND OOS_Sharpe > 0 AND n_folds >= 3
    BORDERLINE if IS_PF > 0 AND OOS_PF >= 0.5 * IS_PF AND OOS_Sharpe > 0
    FAIL   otherwise (incl. IS_PF=0 sentinel)
    """
    if n_folds < 3:
        return "INSUFFICIENT_FOLDS"
    if is_pf <= 0:
        return "FAIL"  # IS_PF=0 means either no wins or no losses - not promotable
    if oos_pf >= 0.8 * is_pf and oos_sharpe > 0:
        return "PASS"
    if oos_pf >= 0.5 * is_pf and oos_sharpe > 0:
        return "BORDERLINE"
    return "FAIL"


def main(min_n: int = 30, train_size: int = 20, test_size: int = 10, step: int = 5) -> None:
    pwd = os.environ.get("DB_PASS_STOCKS")
    if not pwd:
        raise SystemExit("DB_PASS_STOCKS env var not set")
    conn = pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pwd,
        database="ejaguiar1_stocks",
        port=3306,
    )
    try:
        rows = _query_per_strategy(conn, min_n)
        print(f"[wf-oos] {len(rows)} strategies with n>={min_n}", flush=True)

        per_strategy: list[dict] = []
        for i, r in enumerate(rows, 1):
            strat = r["strategy"]
            cls = r.get("asset_class") or "UNKNOWN"
            n = int(r["n"])
            wins = int(r["wins"] or 0)
            sum_pnl = float(r["sum_pnl_pct"] or 0.0)
            trades = _query_trades(conn, strat)
            pnls = [t["pnl_pct"] for t in trades]
            is_pf = _pf(pnls)
            wf = walk_forward_validate(
                trades, train_size=train_size, test_size=test_size, step=step
            )
            n_folds = wf.get("folds", 0)
            oos_wr = wf.get("oos_wr")
            oos_sharpe = wf.get("oos_sharpe")
            oos_sharpe_std = wf.get("oos_sharpe_std")
            decay = wf.get("decay")
            consistency = wf.get("consistency")
            oos_pnls: list[float] = []
            for f in wf.get("folds_detail", []):
                start, end = f["test_start"], f["test_end"]
                oos_pnls.extend(pnls[start:end])
            oos_pf = _pf(oos_pnls)
            oos_n_trades = len(oos_pnls)
            per_strategy.append({
                "strategy": strat,
                "asset_class": cls,
                "n": n,
                "wins": wins,
                "wr": round(wins / n, 4) if n else 0.0,
                "sum_pnl_pct": round(sum_pnl, 3),
                "is_pf": is_pf,
                "n_folds": n_folds,
                "oos_n_trades": oos_n_trades,
                "oos_pf": oos_pf,
                "oos_wr": oos_wr,
                "oos_sharpe": oos_sharpe,
                "oos_sharpe_std": oos_sharpe_std,
                "decay": decay,
                "consistency": consistency,
                "ratio_oos_is_pf": round(oos_pf / is_pf, 3) if is_pf > 0 else 0.0,
                "verdict": _verdict(is_pf, oos_pf, oos_sharpe or 0.0, n_folds),
            })
            if i % 10 == 0:
                print(f"[wf-oos]   {i}/{len(rows)} processed", flush=True)

        n_pass = sum(1 for s in per_strategy if s["verdict"] == "PASS")
        n_borderline = sum(1 for s in per_strategy if s["verdict"] == "BORDERLINE")
        n_fail = sum(1 for s in per_strategy if s["verdict"] == "FAIL")
        n_insuf = sum(1 for s in per_strategy if s["verdict"] == "INSUFFICIENT_FOLDS")

        out = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "min_n_per_strategy": min_n,
            "train_size": train_size,
            "test_size": test_size,
            "step": step,
            "n_strategies": len(per_strategy),
            "n_pass": n_pass,
            "n_borderline": n_borderline,
            "n_fail": n_fail,
            "n_insufficient_folds": n_insuf,
            "eagle6_v2_wf_oos_gate": (
                f"PASS={n_pass} BORDERLINE={n_borderline} FAIL={n_fail} "
                f"INSUFFICIENT_FOLDS={n_insuf} total={len(per_strategy)}"
            ),
            "per_strategy": per_strategy,
        }
        out_path = os.path.join(ROOT, "tools", "walkforward_oos_results.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(
            f"[wf-oos] PASS={n_pass} BORDERLINE={n_borderline} FAIL={n_fail} "
            f"INSUFFICIENT_FOLDS={n_insuf} -> {out_path}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
