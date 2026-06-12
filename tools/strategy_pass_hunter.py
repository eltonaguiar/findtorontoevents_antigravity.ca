#!/usr/bin/env python3
"""strategy_pass_hunter.py — scan deduped intrabar cohort for Tier-2 + discipline passers.

READ-ONLY MySQL. Uses the same dedup as tools/stamp_entry_conditions.py:
  per (symbol, UPPER(direction), DATE(opened_at)) keep MIN(id).

Tier-2 floor (tools/edge/edge_stability.py TIER2_FLOOR):
  n>=30, WR>=50%, PF>=1.5

Discipline (reports/entry_conditioning_experiment_2026-06-10.json):
  R1: median-opened_at split; BOTH halves WR>=50% and PF>=1.2
  R2: top symbol share <= 35%
  R3: one-sided binomial vs class baseline WR, p<0.005

Usage:
  python3 tools/strategy_pass_hunter.py
  python3 tools/strategy_pass_hunter.py --json reports/strategy_pass_hunter_latest.json
  python3 tools/strategy_pass_hunter.py --min-n 25 --cell luxalgo_confluence:CRYPTO:SHORT
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")
TIER2 = {"n": 30, "wr": 50.0, "pf": 1.5}
CLASS_BASELINE_WR = {
    "CRYPTO": 0.321,
    "FOREX": 0.408,
    "COMMODITY": 0.411,
    "EQUITY": 0.346,
    "ETF": 0.0,
    "BOND": 0.333,
    "FUTURES": 0.286,
    "MEMECOIN": 0.277,
}

DEDUP_SQL = """
SELECT o.id, o.symbol, UPPER(o.direction) AS direction, o.asset_class, o.strategy,
       o.source_system, o.opened_at, o.entry_price, o.intrabar_status, o.intrabar_pnl_pct
FROM at_signal_outcomes o
JOIN (
    SELECT MIN(id) AS id
    FROM at_signal_outcomes
    WHERE intrabar_resolved_at IS NOT NULL
      AND intrabar_status IN ('TP_HIT', 'SL_HIT')
      AND opened_at IS NOT NULL
    GROUP BY symbol, UPPER(direction), DATE(opened_at)
) d ON d.id = o.id
"""


def _conn():
    return pymysql.connect(
        **{k: v for k, v in get_stocks_creds().items() if k in _KEEP},
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_cohort(limit: int | None = None) -> list[dict]:
    sql = DEDUP_SQL + " ORDER BY o.opened_at DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    conn = _conn()
    cur = conn.cursor()
    cur.execute(sql)
    rows = list(cur.fetchall())
    conn.close()
    return rows


def metrics(rows: list[dict]) -> dict[str, Any] | None:
    pnls = [
        float(r["intrabar_pnl_pct"])
        for r in rows
        if r.get("intrabar_pnl_pct") is not None
    ]
    if not pnls:
        return None
    wins = sum(1 for p in pnls if p > 0)
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
    return {
        "n": len(pnls),
        "wins": wins,
        "wr": round(100.0 * wins / len(pnls), 2),
        "pf": round(pf, 3),
        "sum_pos": round(gp, 2),
        "sum_neg": round(-gl, 2),
    }


def wilson_ci(wins: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [round(max(0.0, center - half) * 100, 1), round(min(1.0, center + half) * 100, 1)]


def r1_pass(rows: list[dict]) -> dict[str, Any]:
    if len(rows) < 20:
        return {"pass": False, "reason": "n<20"}
    ordered = sorted(rows, key=lambda r: r["opened_at"])
    mid = len(ordered) // 2
    h1, h2 = metrics(ordered[:mid]), metrics(ordered[mid:])
    ok = (
        h1
        and h2
        and h1["wr"] >= 50
        and h2["wr"] >= 50
        and h1["pf"] >= 1.2
        and h2["pf"] >= 1.2
    )
    return {
        "pass": ok,
        "half1": {k: h1[k] for k in ("n", "wr", "pf")} if h1 else None,
        "half2": {k: h2[k] for k in ("n", "wr", "pf")} if h2 else None,
    }


def r2_pass(rows: list[dict]) -> dict[str, Any]:
    if not rows:
        return {"pass": False}
    counts = Counter(r["symbol"] for r in rows)
    top_sym, top_n = counts.most_common(1)[0]
    share = round(100.0 * top_n / len(rows), 2)
    return {"pass": share <= 35.0, "top_symbol": top_sym, "top_share_pct": share}


def r3_pass(wins: int, n: int, baseline_wr: float) -> dict[str, Any]:
    if n < 10:
        return {"pass": False, "p_value": None}
    p0 = baseline_wr
    mu = n * p0
    se = math.sqrt(n * p0 * (1 - p0))
    if se == 0:
        return {"pass": False, "p_value": None}
    z = (wins - 0.5 - mu) / se
    p_val = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    return {"pass": p_val < 0.005, "p_value": p_val, "baseline_wr": baseline_wr}


def mc_bootstrap(pnls: list[float], seed: int = 42, sims: int = 5000) -> dict[str, Any]:
    if len(pnls) < 10:
        return {}
    rng = random.Random(seed)
    actual_wr = 100.0 * sum(1 for p in pnls if p > 0) / len(pnls)
    flip_wrs = [
        100.0 * sum(rng.choice([0, 1]) for _ in range(len(pnls))) / len(pnls)
        for _ in range(sims)
    ]
    boot_pf: list[float] = []
    for _ in range(sims):
        sample = [pnls[rng.randrange(len(pnls))] for _ in range(len(pnls))]
        gp = sum(x for x in sample if x > 0)
        gl = abs(sum(x for x in sample if x < 0))
        boot_pf.append(gp / gl if gl > 0 else 999.0)
    boot_pf.sort()
    return {
        "mc_wr_pctile": round(sum(1 for x in flip_wrs if x <= actual_wr) / sims, 4),
        "bootstrap_pf_ci": [round(boot_pf[int(0.025 * sims)], 3), round(boot_pf[int(0.975 * sims)], 3)],
    }


def tier2_pass(m: dict[str, Any]) -> bool:
    return m["n"] >= TIER2["n"] and m["wr"] >= TIER2["wr"] and m["pf"] >= TIER2["pf"]


def grade_cell(rows: list[dict], label: str, baseline_wr: float) -> dict[str, Any]:
    m = metrics(rows)
    if not m:
        return {"label": label, "error": "no_metrics"}
    pnls = [float(r["intrabar_pnl_pct"]) for r in rows if r.get("intrabar_pnl_pct") is not None]
    r1 = r1_pass(rows)
    r2 = r2_pass(rows)
    r3 = r3_pass(m["wins"], m["n"], baseline_wr)
    t2 = tier2_pass(m)
    full = t2 and r1["pass"] and r2["pass"] and r3["pass"]
    out: dict[str, Any] = {
        "label": label,
        "metrics": m,
        "wilson_ci_95": wilson_ci(m["wins"], m["n"]),
        "tier2": t2,
        "full_pass": full,
        "R1": r1,
        "R2": r2,
        "R3": r3,
    }
    if pnls:
        out["monte_carlo"] = mc_bootstrap(pnls)
    return out


def cell_key(row: dict, mode: str) -> tuple:
    strat = row.get("strategy") or row.get("source_system") or "?"
    cls = (row.get("asset_class") or "UNKNOWN").upper()
    d = "SHORT" if row["direction"] in ("SHORT", "SELL") else "LONG"
    if mode == "strategy_class_dir":
        return (strat, cls, d)
    if mode == "strategy_class":
        return (strat, cls, "*")
    if mode == "class_dir":
        return ("*", cls, d)
    return (strat, cls, d)


def parse_cell_arg(s: str) -> tuple[str, str, str]:
    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError(f"cell must be strategy:class:direction, got {s!r}")
    return parts[0], parts[1].upper(), parts[2].upper()


def main() -> int:
    ap = argparse.ArgumentParser(description="Hunt Tier-2 passers on deduped intrabar ledger")
    ap.add_argument("--limit", type=int, default=None, help="max cohort rows (newest first)")
    ap.add_argument("--min-n", type=int, default=25, help="minimum n to report a cell")
    ap.add_argument("--json", type=str, default="", help="write full report JSON")
    ap.add_argument(
        "--cell",
        type=str,
        default="",
        help="single cell strategy:class:direction (e.g. luxalgo_confluence:CRYPTO:SHORT)",
    )
    args = ap.parse_args()

    cohort = fetch_cohort(args.limit)
    if args.cell:
        strat, cls, direction = parse_cell_arg(args.cell)
        filt = [
            r
            for r in cohort
            if (r.get("strategy") or r.get("source_system") or "?") == strat
            and (r.get("asset_class") or "").upper() == cls
            and (
                direction == "*"
                or (
                    direction == "SHORT"
                    and r["direction"] in ("SHORT", "SELL")
                )
                or (
                    direction == "LONG"
                    and r["direction"] not in ("SHORT", "SELL")
                )
            )
        ]
        baseline = CLASS_BASELINE_WR.get(cls, 0.40)
        g = grade_cell(filt, args.cell, baseline)
        print(json.dumps(g, indent=2))
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "cells": [g]}, fh, indent=2)
        return 0

    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for mode in ("strategy_class_dir", "strategy_class", "class_dir"):
        for row in cohort:
            buckets[(mode, cell_key(row, mode))].append(row)

    results: list[dict[str, Any]] = []
    for (mode, key), rows in buckets.items():
        if len(rows) < args.min_n:
            continue
        strat, cls, d = key
        label = f"{strat}|{cls}|{d}" if mode != "class_dir" else f"*_{cls}_{d}"
        baseline = CLASS_BASELINE_WR.get(cls, 0.40)
        g = grade_cell(rows, label, baseline)
        g["mode"] = mode
        g["key"] = {"strategy": strat, "class": cls, "direction": d}
        results.append(g)

    full_pass = [r for r in results if r.get("full_pass")]
    t2_only = [r for r in results if r.get("tier2") and not r.get("full_pass")]
    full_pass.sort(key=lambda x: (-x["metrics"]["pf"], -x["metrics"]["n"]))
    t2_only.sort(key=lambda x: (-x["metrics"]["pf"], -x["metrics"]["n"]))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_n_deduped": len(cohort),
        "tier2_floor": TIER2,
        "full_pass_count": len(full_pass),
        "tier2_only_count": len(t2_only),
        "full_pass": full_pass,
        "tier2_only": t2_only[:20],
    }

    print(f"cohort_n_deduped={len(cohort)} full_pass={len(full_pass)} tier2_only={len(t2_only)}")
    print("\n=== FULL PASS (T2 + R1 + R2 + R3) ===")
    for r in full_pass:
        m = r["metrics"]
        mc = r.get("monte_carlo") or {}
        mc_s = f" MC={mc.get('mc_wr_pctile', 'n/a')}" if mc else ""
        print(
            f"  {r['label']}: n={m['n']} WR={m['wr']}% PF={m['pf']} "
            f"Wilson={r['wilson_ci_95']} {mc_s}"
        )

    print("\n=== T2 ONLY (discipline miss) ===")
    for r in t2_only[:10]:
        m = r["metrics"]
        miss = []
        if not r["R1"]["pass"]:
            miss.append("R1")
        if not r["R2"]["pass"]:
            miss.append("R2")
        if not r["R3"]["pass"]:
            miss.append("R3")
        print(f"  {r['label']}: n={m['n']} WR={m['wr']}% PF={m['pf']} miss={','.join(miss)}")

    if args.json:
        out_path = args.json
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nwrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
