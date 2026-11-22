#!/usr/bin/env python3
"""
edge_screen.py — wide, honest screen for cells worth forward-testing.

This is E4 of the edge-hunt plan, run for real against `trading_picks`.
For every (source_system, asset_class) cell with n >= --min-n it computes the
numbers that decide whether a cell deserves a forward test:

  gross PF / net PF      net subtracts the class round-trip cost
  net mean + CI          seeded bootstrap, one-sided lower bound
  split halves           chronological, both halves must be net positive
  concentration          top symbol share, top close-date share
  WR                     descriptor only

A cell is only ADVANCE if ALL hold: net CI lower bound > 0, both halves > 0,
top symbol share < 0.30, top date share < 0.35, n >= min-n. Everything else is
WATCH or REJECT with the failing reason named.

It promotes nothing. Its only output is a ranked list for the confirmatory
stage, and it prints the trial count so multiplicity can be accounted for.

Read-only. Usage:
    python3 tools/edge_screen.py
    python3 tools/edge_screen.py --min-n 100 --resamples 2000
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "reports"
SEED = 42

POP = (
    "closed_at IS NOT NULL AND pnl_pct IS NOT NULL "
    "AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') "
    "AND closed_at > '2026-01-01' AND DATE(closed_at) != '2026-06-04' "
    "AND pnl_pct BETWEEN -100 AND 100"
)

CATEGORY_TO_CLASS = {
    "crypto": "CRYPTO", "equity": "EQUITY", "commodity": "COMMODITY",
    "etf": "ETF", "forex": "FOREX", "bond": "BOND", "futures": "FUTURES",
    "meme": "MEME", "memecoin": "MEME", "penny_stock": "PENNY_STOCK",
    "mutual_fund": "MUTUAL_FUND", "index": "INDEX",
}


def pf(vals):
    gw = sum(v for v in vals if v > 0)
    gl = abs(sum(v for v in vals if v < 0))
    return round(gw / gl, 4) if gl > 0 else None


def boot_ci(vals, resamples, seed):
    """One-sided 95% lower bound of the mean, seeded."""
    if len(vals) < 10:
        return None, None
    rnd = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(resamples):
        s = 0.0
        for _ in range(n):
            s += vals[rnd.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.05 * resamples)]
    hi = means[int(0.95 * resamples)]
    return round(lo, 4), round(hi, 4)


def crowd_ok(p):
    n = p["n"]
    if n < 30:
        return False
    mean = p["net_mean"]
    if mean is None or mean <= 0:
        return False
    if p["net_ci_lo"] is None or p["net_ci_lo"] <= 0:
        return False
    if p["top_symbol_share"] is None or p["top_symbol_share"] >= 0.30:
        return False
    if p["top_date_share"] is None or p["top_date_share"] >= 0.35:
        return False
    halves = p.get("halves") or {}
    if halves.get("h1_net_mean") is None or halves.get("h2_net_mean") is None:
        return False
    return halves["h1_net_mean"] > 0 and halves["h2_net_mean"] > 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-n", type=int, default=100)
    ap.add_argument("--resamples", type=int, default=2000)
    args = ap.parse_args(argv)

    import pymysql
    from tools.db_env import get_stocks_creds

    ledger = json.loads((ROOT / "docs" / "audit_review_2026-11-22" / "_raw" /
                         "audit3_audit3_ledger.json").read_text(encoding="utf-8"))
    slip = ledger["conventions"]["slippage_pct_by_class"]
    default_cost = 0.12

    creds = get_stocks_creds()
    creds["connect_timeout"] = 10
    creds["read_timeout"] = 120
    conn = pymysql.connect(**creds)
    cells: dict[tuple, list] = defaultdict(list)
    meta: dict[tuple, dict] = {}
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT source_system, LOWER(TRIM(category)), symbol, closed_at, pnl_pct "
            f"FROM trading_picks WHERE {POP}"
        )
        for src, cat, sym, closed, pnl in cur.fetchall():
            cls = CATEGORY_TO_CLASS.get(cat or "", (cat or "").upper() or "UNCATEGORIZED")
            key = (src or "?", cls)
            cells[key].append((closed, float(pnl), sym or "?"))
            meta[key] = {"category": cat}
    finally:
        conn.close()

    rows = []
    for (src, cls), trades in cells.items():
        if len(trades) < args.min_n:
            continue
        cost = slip.get(cls, default_cost)
        trades.sort(key=lambda t: (t[0] is None, t[0]))
        gross = [t[1] for t in trades]
        net = [t[1] - cost for t in trades]
        syms = defaultdict(int)
        dates = defaultdict(int)
        for closed, _, sym in trades:
            syms[sym] += 1
            dates[str(closed)[:10]] += 1
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        lo, hi = boot_ci(net, args.resamples, SEED)
        r = {
            "source_system": src, "asset_class": cls, "n": len(trades),
            "cost_pct": cost,
            "wr": round(sum(1 for v in gross if v > 0) / len(gross), 4),
            "gross_pf": pf(gross), "net_pf": pf(net),
            "net_mean": round(sum(net) / len(net), 4),
            "net_ci_lo": lo, "net_ci_hi": hi,
            "halves": {"h1_net_mean": round(sum(h1) / len(h1), 4) if h1 else None,
                       "h2_net_mean": round(sum(h2) / len(h2), 4) if h2 else None},
            "top_symbol_share": round(max(syms.values()) / len(trades), 4),
            "top_symbol": max(syms, key=syms.get),
            "top_date_share": round(max(dates.values()) / len(trades), 4),
            "top_date": max(dates, key=dates.get),
        }
        fails = []
        if not r["net_ci_lo"] or r["net_ci_lo"] <= 0:
            fails.append("net CI-LB <= 0")
        if (r["halves"]["h1_net_mean"] or 0) <= 0 or (r["halves"]["h2_net_mean"] or 0) <= 0:
            fails.append("split halves disagree")
        if r["top_symbol_share"] >= 0.30:
            fails.append(f"top symbol {r['top_symbol']} {r['top_symbol_share']:.0%}")
        if r["top_date_share"] >= 0.35:
            fails.append(f"top date {r['top_date']} {r['top_date_share']:.0%}")
        r["fails"] = fails
        r["verdict"] = "ADVANCE" if not fails else ("WATCH" if len(fails) == 1 else "REJECT")
        rows.append(r)

    rows.sort(key=lambda x: (x["verdict"] != "ADVANCE", -(x["net_ci_lo"] or -9e9)))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(),
               "min_n": args.min_n, "resamples": args.resamples, "seed": SEED,
               "population": POP, "n_trials": len(rows), "cells": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jp = OUT_DIR / f"edge_screen_{stamp}.json"
    jp.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [f"# Edge screen — {stamp}", "",
             f"Population: scrutiny filter, pnl in [-100,100]. Trials tested: **{len(rows)}** "
             f"(min n {args.min_n}). ", "",
             "| verdict | source | class | n | WR | gross PF | net PF | net mean | CI-LB | h1 | h2 | top sym | top date | fails |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['verdict']} | {r['source_system']} | {r['asset_class']} | {r['n']} | {r['wr']} | "
            f"{r['gross_pf']} | {r['net_pf']} | {r['net_mean']} | {r['net_ci_lo']} | "
            f"{r['halves']['h1_net_mean']} | {r['halves']['h2_net_mean']} | "
            f"{r['top_symbol']} {r['top_symbol_share']:.0%} | {r['top_date_share']:.0%} | "
            f"{'; '.join(r['fails']) or '-'} |")
    mp = OUT_DIR / f"edge_screen_{stamp}.md"
    mp.write_text("\n".join(lines) + "\n", encoding="utf-8")

    adv = [r for r in rows if r["verdict"] == "ADVANCE"]
    print(f"screened {len(rows)} cells with n >= {args.min_n}")
    print(f"ADVANCE {len(adv)}  WATCH {sum(1 for r in rows if r['verdict']=='WATCH')}  "
          f"REJECT {sum(1 for r in rows if r['verdict']=='REJECT')}")
    for r in rows[:12]:
        print(f"  {r['verdict']:<8}{r['source_system']:<28}{r['asset_class']:<12}"
              f"n={r['n']:<6} netPF={r['net_pf']} CI-LB={r['net_ci_lo']} "
              f"h1={r['halves']['h1_net_mean']} h2={r['halves']['h2_net_mean']} "
              f"| {'; '.join(r['fails']) or 'clean'}")
    print(f"[written] {jp}")
    print(f"[written] {mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
