#!/usr/bin/env python3
"""population_cost_audit.py — cost-adjust the FULL policy-clean population.

`audit_dashboard/data/dashboard_data.json::picks.recent_closed` is a 3,500-pick
recent window; quoting a class PF from it is a window statistic, not the class
(the 2026-11-20 reconcile showed CRYPTO 1.31 there vs 0.26 over the full resolved
population). This reads the canonical registry cells
(`pf_registry.json::by_asset_class_strategy_date`, 25k cells) and re-derives every
class at a stated round-trip cost.

Two numbers behave differently under a uniform per-trade cost c:
  expectancy  : mean_net = total_pnl_pct/n - c        EXACT
  win rate    : wins/n, with winners <= c flipping     UPPER BOUND (stated)
  PF          : (gp - c*wins) / (gl + c*losses)        APPROX, exact only while
                every winner exceeds c; reported with that caveat.
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict

COST_BPS = {"CRYPTO": 20, "EQUITY": 10, "ETF": 10, "FOREX": 8,
            "COMMODITY": 12, "FUTURES": 12, "BOND": 10}
DEFAULT = 15


def agg(rows):
    a = defaultdict(float)
    for r in rows:
        a["n"] += r.get("n") or 0
        a["wins"] += r.get("wins") or 0
        a["losses"] += r.get("losses") or 0
        a["gp"] += r.get("gross_profit") or 0.0
        a["gl"] += r.get("gross_loss") or 0.0
        a["pnl"] += r.get("total_pnl_pct") or 0.0
    return a


def report(reg_path, key):
    d = json.load(open(reg_path))
    rows = d.get(key) or []
    if not rows:
        raise SystemExit(f"{key} missing in {reg_path}")
    by = defaultdict(list)
    for r in rows:
        by[str(r.get("asset_class") or "UNKNOWN").upper()].append(r)
    out = {"registry": reg_path, "view": key, "cells": len(rows), "classes": {}}
    for cls, rs in sorted(by.items(), key=lambda kv: -sum(r.get("n") or 0 for r in kv[1])):
        a = agg(rs)
        if not a["n"]:
            continue
        c = COST_BPS.get(cls, DEFAULT) / 100.0
        pf_g = a["gp"] / a["gl"] if a["gl"] else None
        gl_n = a["gl"] + c * a["losses"]
        pf_n = ((a["gp"] - c * a["wins"]) / gl_n) if gl_n > 0 else None
        out["classes"][cls] = {
            "n": int(a["n"]), "wins": int(a["wins"]), "losses": int(a["losses"]),
            "cost_bps": COST_BPS.get(cls, DEFAULT),
            "gross_pf": round(pf_g, 4) if pf_g else None,
            "net_pf_approx": round(pf_n, 4) if pf_n else None,
            "gross_wr": round(a["wins"] / a["n"], 4),
            "net_wr_upper": round(a["wins"] / a["n"], 4),
            "gross_expectancy_pct": round(a["pnl"] / a["n"], 4),
            "net_expectancy_pct": round(a["pnl"] / a["n"] - c, 4),
            "breakeven_cost_bps": round(100 * a["pnl"] / a["n"], 1),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="audit_dashboard/data/pf_registry.json")
    ap.add_argument("--view", default="by_asset_class_policy_clean")
    ap.add_argument("--json", default="reports/2026-11-22-population-cost-audit.json")
    ap.add_argument("--md", default="reports/2026-11-22-population-cost-audit.md")
    a = ap.parse_args()
    o = report(a.registry, a.view)
    json.dump(o, open(a.json, "w"), indent=2)
    L = [f"# Cost-adjusted FULL population — {o['cells']} registry cells", "",
         f"Source: `{a.registry}` view `{a.view}`. Expectancy is exact under a uniform "
         "per-trade cost; net PF is an approximation that holds while every winner exceeds "
         "the cost, so read it as slightly optimistic; net WR is an upper bound.", "",
         "| class | n | cost bp | PF gross | PF net (approx) | WR | exp gross % | exp net % | breakeven cost bp |",
         "|---|---|---|---|---|---|---|---|---|"]
    for cls, r in o["classes"].items():
        L.append(f"| {cls} | {r['n']:,} | {r['cost_bps']} | {r['gross_pf']} | {r['net_pf_approx']} | "
                 f"{r['gross_wr']:.1%} | {r['gross_expectancy_pct']:+.4f} | "
                 f"{r['net_expectancy_pct']:+.4f} | {r['breakeven_cost_bps']:+.1f} |")
    open(a.md, "w").write("\n".join(L) + "\n")
    print(f"{'class':10}{'n':>8}{'PFg':>8}{'PFn~':>8}{'expg':>9}{'expn':>9}{'be_bp':>8}")
    for cls, r in o["classes"].items():
        print(f"{cls:10}{r['n']:8d}{str(r['gross_pf']):>8}{str(r['net_pf_approx']):>8}"
              f"{r['gross_expectancy_pct']:+9.4f}{r['net_expectancy_pct']:+9.4f}"
              f"{r['breakeven_cost_bps']:+8.1f}")
    print(f"\nwrote {a.json} and {a.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
