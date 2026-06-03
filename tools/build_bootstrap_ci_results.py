"""Bootstrap CI for Profit Factor — EAGLE-6 v2 third gate.

For each WF OOS PASS strategy (from tools/walkforward_oos_results.json),
compute a 95% bootstrap CI for PF (gross_profit / abs(gross_loss)).
Verdict: PASS if lower CI bound > 1.0 (i.e., even in the worst-case
resample, PF stays above 1.0). This is stricter than WF OOS ratio.

Usage:
    DB_PASS_STOCKS=$DB_PASS_STOCKS python3 tools/build_bootstrap_ci_results.py

Output: tools/bootstrap_ci_results.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pymysql


def _pf(pnls: list[float]) -> float:
    """Profit factor with no-losses -> 0.0 (post-PR-#464 sentinel)."""
    if not pnls:
        return 0.0
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = sum(abs(p) for p in pnls if p < 0)
    if gross_loss == 0:
        return 0.0
    return gross_profit / gross_loss


def bootstrap_pf_ci(pnls: list[float], n_boot: int = 5000, seed: int = 42) -> tuple[float, float, float]:
    """95% bootstrap CI for PF. Returns (lower_2.5pct, median, upper_97.5pct)."""
    arr = np.array(pnls, dtype=float)
    if len(arr) < 5:
        return (0.0, 0.0, 0.0)
    rng = np.random.RandomState(seed)
    boot_pfs: list[float] = []
    for _ in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        gp = float(np.sum(sample[sample > 0])) if np.any(sample > 0) else 0.0
        gl = float(np.sum(np.abs(sample[sample < 0]))) if np.any(sample < 0) else 0.0
        if gl == 0:
            boot_pfs.append(0.0)  # sentinel: no losses in resample = no signal
        else:
            boot_pfs.append(gp / gl)
    if not boot_pfs:
        return (0.0, 0.0, 0.0)
    arr_b = np.array(boot_pfs)
    return (
        round(float(np.percentile(arr_b, 2.5)), 3),
        round(float(np.percentile(arr_b, 50)), 3),
        round(float(np.percentile(arr_b, 97.5)), 3),
    )


def _verdict(pf_point: float, pf_lo: float, pf_hi: float, n: int) -> str:
    """EAGLE-6 v2 bootstrap CI gate: PASS if lower_95 > 1.0 (worst-case PF > 1.0).
    BORDERLINE if median > 1.0 but lower_95 <= 1.0
    FAIL if median <= 1.0
    INSUFFICIENT if n < 30
    """
    if n < 30:
        return "INSUFFICIENT"
    if pf_lo > 1.0:
        return "PASS"
    if pf_point > 1.0:
        return "BORDERLINE"
    return "FAIL"


def main(n_boot: int = 5000, only_verdicts: tuple[str, ...] = ("PASS", "BORDERLINE")) -> None:
    pwd = os.environ.get("DB_PASS_STOCKS")
    if not pwd:
        raise SystemExit("DB_PASS_STOCKS env var not set")

    wf_path = os.path.join(ROOT, "tools", "walkforward_oos_results.json")
    if not os.path.exists(wf_path):
        raise SystemExit(f"Run tools/build_walkforward_oos_results.py first ({wf_path} not found)")
    with open(wf_path) as f:
        wf = json.load(f)
    candidates = [s for s in wf["per_strategy"] if s["verdict"] in only_verdicts]
    print(f"[boot-ci] {len(candidates)} candidate strategies from WF OOS gate", flush=True)

    conn = pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pwd,
        database="ejaguiar1_stocks",
        port=3306,
    )
    try:
        cur = conn.cursor()
        per_strategy: list[dict] = []
        for i, s in enumerate(candidates, 1):
            strat = s["strategy"]
            cls = s["asset_class"]
            cur.execute(
                """
                SELECT pnl_pct FROM at_signal_outcomes
                WHERE strategy = %s
                  AND outcome IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','CLOSED')
                  AND pnl_pct IS NOT NULL
                ORDER BY closed_at ASC
                """,
                (strat,),
            )
            pnls = [float(r[0]) for r in cur.fetchall() if r[0] is not None]
            n = len(pnls)
            pf_point = _pf(pnls)
            pf_lo, pf_med, pf_hi = bootstrap_pf_ci(pnls, n_boot=n_boot)
            per_strategy.append({
                "strategy": strat,
                "asset_class": cls,
                "n": n,
                "wr": round(sum(1 for p in pnls if p > 0) / n, 4) if n else 0.0,
                "sum_pnl_pct": round(sum(pnls), 3),
                "is_pf": round(pf_point, 3),
                "pf_lo_95": pf_lo,
                "pf_med_95": pf_med,
                "pf_hi_95": pf_hi,
                "verdict": _verdict(pf_point, pf_lo, pf_hi, n),
            })
            if i % 5 == 0 or i == len(candidates):
                print(f"[boot-ci]   {i}/{len(candidates)} processed", flush=True)

        n_pass = sum(1 for s in per_strategy if s["verdict"] == "PASS")
        n_border = sum(1 for s in per_strategy if s["verdict"] == "BORDERLINE")
        n_fail = sum(1 for s in per_strategy if s["verdict"] == "FAIL")
        n_insuf = sum(1 for s in per_strategy if s["verdict"] == "INSUFFICIENT")

        out = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "n_candidates": len(per_strategy),
            "n_boot": n_boot,
            "seed": 42,
            "gate_rule": "PASS if pf_lo_95 > 1.0 (worst-case 95% CI bootstrap PF stays above 1.0)",
            "eagle6_v2_bootstrap_ci_gate": (
                f"PASS={n_pass} BORDERLINE={n_border} FAIL={n_fail} INSUFFICIENT={n_insuf} "
                f"total={len(per_strategy)}"
            ),
            "per_strategy": per_strategy,
        }
        out_path = os.path.join(ROOT, "tools", "bootstrap_ci_results.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(
            f"[boot-ci] PASS={n_pass} BORDERLINE={n_border} FAIL={n_fail} "
            f"INSUFFICIENT={n_insuf} -> {out_path}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
