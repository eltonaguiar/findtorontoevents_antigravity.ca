"""Picks audit — turn the dashboard CSV exports into a verdict.

Reads the three exports (all / closed / active) and answers, in order:
  1. What is the book actually made of? (class, strategy, timeframe concentration)
  2. Does it survive friction? (breakeven cost per trade)
  3. Is the result broad or carried by a handful of outliers? (concentration)
  4. How are positions actually exiting? (bracket vs force-closed)
  5. Is any scoring column predictive? (grade monotonicity)
  6. Is the data even analysable? (timestamps, benchmarks, cost columns, label errors)

Usage:
    python proof/picks_audit.py --dir ~/Downloads --date 2026-11-15
    python proof/picks_audit.py --all a.csv --closed c.csv --active v.csv

Exit code 0 always: this is a reporter, not a gate. A separate gate should
consume its JSON output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COST_GRID = [0.05, 0.10, 0.15, 0.20, 0.30]


def _pf(x: pd.Series) -> float:
    w = x[x > 0].sum()
    l = abs(x[x < 0].sum())
    return float(w / l) if l > 0 else float("inf")


def _fmt_pf(v: float) -> str:
    return "inf" if v == float("inf") else f"{v:.3f}"


def load(dirpath: Path | None, date: str, all_p: str | None,
         closed_p: str | None, active_p: str | None):
    def pick(explicit, kind):
        if explicit:
            return Path(explicit)
        if dirpath:
            return dirpath / f"antigravity_{kind}_picks_{date}.csv"
        raise SystemExit("need --dir or explicit paths")
    return (pd.read_csv(pick(all_p, "all")),
            pd.read_csv(pick(closed_p, "closed")),
            pd.read_csv(pick(active_p, "active")))


def integrity(a: pd.DataFrame, c: pd.DataFrame, act: pd.DataFrame) -> dict:
    out = {}
    out["rows"] = {"all": len(a), "closed": len(c), "active": len(act)}
    has_bench = any("bench" in str(x).lower() for x in c.columns)
    has_cost = any(k in " ".join(map(str, c.columns)).lower()
                   for k in ("fee", "cost", "slip", "commission"))
    out["has_benchmark_column"] = bool(has_bench)
    out["has_cost_column"] = bool(has_cost)

    for col in ("Entry Time", "Exit Time"):
        if col in c.columns:
            s = pd.to_datetime(c[col], errors="coerce", utc=True)
            out[f"{col}_present"] = int(s.notna().sum())
            out[f"{col}_nulls"] = int(s.isna().sum())
    if "Entry Time" in c.columns and "Exit Time" in c.columns:
        et = pd.to_datetime(c["Entry Time"], errors="coerce", utc=True)
        xt = pd.to_datetime(c["Exit Time"], errors="coerce", utc=True)
        both = (et.notna() & xt.notna())
        out["both_timestamps"] = int(both.sum())
        if both.any():
            hold = (xt[both] - et[both]).dt.total_seconds() / 3600
            out["holding_hours_median"] = float(hold.median())

    if "Status" in a.columns:
        won_bad = a[(a["Status"] == "WON") & (a["PnL%"] < 0)]
        lost_bad = a[(a["Status"] == "LOST") & (a["PnL%"] > 0)]
        out["label_errors"] = {"won_but_negative": len(won_bad),
                               "lost_but_positive": len(lost_bad)}
        out["unresolved_zero_closed"] = int(
            ((a["Status"] == "CLOSED") & (a["PnL%"] == 0)).sum())
    if "Dup Status" in a.columns:
        out["dups"] = a["Dup Status"].dropna().value_counts().to_dict()
    if "Age (hours)" in act.columns:
        age = pd.to_numeric(act["Age (hours)"], errors="coerce")
        out["active"] = {"n": len(act), "max_age_h": float(age.max()) if age.notna().any() else None,
                         "open_over_72h": int((age > 72).sum())}
    return out


def by_class(c: pd.DataFrame) -> list[dict]:
    rows = []
    for cls, d in c.groupby("Asset Class"):
        p = d["PnL%"].dropna()
        if p.empty:
            continue
        rows.append({
            "class": cls, "n": int(len(p)),
            "share": round(len(p) / len(c), 3),
            "win_rate": round(float((p > 0).mean()), 3),
            "avg_pnl": round(float(p.mean()), 3),
            "median_pnl": round(float(p.median()), 3),
            "profit_factor": round(_pf(p), 3),
            "total_pnl_pts": round(float(p.sum()), 1),
        })
    return sorted(rows, key=lambda r: -r["n"])


def cost_sensitivity(c: pd.DataFrame, subset: str | None = None) -> dict:
    d = c if subset is None else c[c["Asset Class"] == subset]
    x = d["PnL%"].dropna()
    out = {"label": subset or "ALL", "n": int(len(x)),
           "gross_avg": round(float(x.mean()), 3), "gross_pf": round(_pf(x), 3),
           "grid": []}
    for cost in COST_GRID:
        net = x - cost
        out["grid"].append({"cost_pct": cost,
                            "avg": round(float(net.mean()), 3),
                            "win_rate": round(float((net > 0).mean()), 3),
                            "profit_factor": round(_pf(net), 3),
                            "total": round(float(net.sum()), 1)})
    # breakeven = cost at which mean net crosses zero
    be = float(x.mean()) if x.mean() > 0 else 0.0
    out["breakeven_cost_pct"] = round(be, 3)
    return out


def concentration(c: pd.DataFrame, cls: str = "CRYPTO") -> dict:
    d = c[c["Asset Class"] == cls].sort_values("PnL%", ascending=False)
    p = d["PnL%"]
    tot = float(p.sum())
    out = {"class": cls, "n": int(len(p)), "net_total": round(tot, 1)}
    if tot != 0:
        for k in (5, 10, 25, 50):
            s = float(p.head(k).sum())
            out[f"top{k}_sum"] = round(s, 1)
            out[f"top{k}_share_of_net"] = round(s / tot, 3)
    if len(p) > 10:
        out["ex_top10_total"] = round(float(p.iloc[10:].sum()), 1)
        out["ex_top10_avg"] = round(float(p.iloc[10:].mean()), 3)
    return out


def exit_mix(c: pd.DataFrame, cls: str = "CRYPTO") -> dict:
    d = c[c["Asset Class"] == cls]
    out = {"class": cls, "n": int(len(d)), "reasons": []}
    for reason, g in d.groupby("Exit Reason"):
        p = g["PnL%"].dropna()
        if p.empty:
            continue
        out["reasons"].append({
            "reason": reason, "n": int(len(p)),
            "share": round(len(p) / len(d), 3),
            "win_rate": round(float((p > 0).mean()), 3),
            "avg_pnl": round(float(p.mean()), 3),
            "profit_factor": round(_pf(p), 3),
        })
    out["reasons"].sort(key=lambda r: -r["n"])
    clean = d[d["Exit Reason"] != "FORCE_CLOSED"]["PnL%"].dropna()
    if len(clean):
        w, l = clean[clean > 0], clean[clean < 0]
        payoff = abs(w.mean() / l.mean()) if len(w) and len(l) else float("nan")
        out["excluding_force_closed"] = {
            "n": int(len(clean)),
            "win_rate": round(float((clean > 0).mean()), 3),
            "avg_pnl": round(float(clean.mean()), 3),
            "profit_factor": round(_pf(clean), 3),
            "payoff_ratio": round(float(payoff), 2) if payoff == payoff else None,
            "breakeven_wr": round(float(100 / (1 + payoff)), 1) if payoff == payoff else None,
            "avg_after_10bps": round(float((clean - 0.10).mean()), 3),
        }
    return out


def grade_monotonic(c: pd.DataFrame, cls: str = "CRYPTO") -> dict:
    d = c[c["Asset Class"] == cls]
    rows = []
    for g, sub in d.groupby("Grade"):
        p = sub["PnL%"].dropna()
        if len(p) < 5:
            continue
        rows.append({"grade": g, "n": int(len(p)),
                     "win_rate": round(float((p > 0).mean()), 3),
                     "avg": round(float(p.mean()), 3),
                     "profit_factor": round(_pf(p), 3)})
    rows.sort(key=lambda r: str(r["grade"]))
    ordered = rows if len(rows) < 2 else (
        all(rows[i]["profit_factor"] >= rows[i + 1]["profit_factor"]
            for i in range(len(rows) - 1)))
    return {"class": cls, "by_grade": rows, "monotonic": bool(ordered)}


def timeframe(c: pd.DataFrame, cls: str = "CRYPTO") -> list[dict]:
    d = c[c["Asset Class"] == cls]
    out = []
    for tf, g in d.groupby("Timeframe"):
        p = g["PnL%"].dropna()
        if p.empty:
            continue
        out.append({"timeframe": tf, "n": int(len(p)),
                    "win_rate": round(float((p > 0).mean()), 3),
                    "avg": round(float(p.mean()), 3),
                    "profit_factor": round(_pf(p), 3)})
    return sorted(out, key=lambda r: -r["n"])


def strategy_table(c: pd.DataFrame, min_n: int = 30) -> list[dict]:
    out = []
    for (cls, strat), g in c.groupby(["Asset Class", "Strategy"]):
        p = g["PnL%"].dropna()
        if len(p) < min_n:
            continue
        out.append({"class": cls, "strategy": strat, "n": int(len(p)),
                    "win_rate": round(float((p > 0).mean()), 3),
                    "avg": round(float(p.mean()), 3),
                    "profit_factor": round(_pf(p), 3)})
    return sorted(out, key=lambda r: -r["n"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--date", default="2026-11-15")
    ap.add_argument("--all"); ap.add_argument("--closed"); ap.add_argument("--active")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = Path(a.dir).expanduser() if a.dir else None
    allp, closed, active = load(d, a.date, a.all, a.closed, a.active)

    c = closed[closed["PnL%"].notna()].copy()
    report = {
        "generated_from": {"all": len(allp), "closed": len(closed), "active": len(active)},
        "integrity": integrity(allp, closed, active),
        "by_class": by_class(c),
        "cost_sensitivity": [cost_sensitivity(c), cost_sensitivity(c, "CRYPTO")],
        "concentration_crypto": concentration(c),
        "exit_mix_crypto": exit_mix(c),
        "grade_crypto": grade_monotonic(c),
        "timeframe_crypto": timeframe(c),
        "strategies": strategy_table(c),
    }

    if a.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print("=" * 72)
    print(f"PICKS AUDIT — all={len(allp)} closed={len(closed)} active={len(active)}")
    print("=" * 72)

    print("\n[1] BOOK COMPOSITION")
    for r in report["by_class"]:
        print(f"  {r['class']:<10} n={r['n']:<5} share={r['share']:.1%}  "
              f"WR={r['win_rate']:.1%}  avg={r['avg_pnl']:+.3f}%  med={r['median_pnl']:+.2f}%  "
              f"PF={_fmt_pf(r['profit_factor'])}")

    print("\n[2] COST SENSITIVITY (does it survive friction?)")
    for cs in report["cost_sensitivity"]:
        print(f"  -- {cs['label']}: n={cs['n']} gross avg={cs['gross_avg']:+.3f}% "
              f"PF={_fmt_pf(cs['gross_pf'])}  breakeven≈{cs['breakeven_cost_pct']:.3f}%/trade")
        for g in cs["grid"]:
            flag = "  <-- breakeven cliff" if abs(g["avg"]) < 0.05 else ""
            print(f"     cost {g['cost_pct']:.2f}%  avg={g['avg']:+.3f}%  "
                  f"PF={_fmt_pf(g['profit_factor'])}  total={g['total']:+.1f}{flag}")

    cc = report["concentration_crypto"]
    print(f"\n[3] CONCENTRATION ({cc['class']}, net={cc['net_total']:+.1f} pts)")
    for k in (5, 10, 25, 50):
        if f"top{k}_share_of_net" in cc:
            print(f"  top {k:2d} winners = {cc[f'top{k}_sum']:+.1f} pts "
                  f"({cc[f'top{k}_share_of_net']:.0%} of net)")
    if "ex_top10_total" in cc:
        print(f"  excluding top 10: total={cc['ex_top10_total']:+.1f}  avg={cc['ex_top10_avg']:+.3f}%")

    em = report["exit_mix_crypto"]
    print(f"\n[4] EXIT MIX ({em['class']}, n={em['n']})")
    for r in em["reasons"]:
        print(f"  {r['reason']:<15} n={r['n']:<5} share={r['share']:.1%}  "
              f"WR={r['win_rate']:.1%}  avg={r['avg_pnl']:+.3f}%  PF={_fmt_pf(r['profit_factor'])}")
    x = em.get("excluding_force_closed")
    if x:
        print(f"  EXCLUDING FORCE_CLOSED: n={x['n']} WR={x['win_rate']:.1%} "
              f"avg={x['avg_pnl']:+.3f}% PF={_fmt_pf(x['profit_factor'])} "
              f"payoff={x['payoff_ratio']} breakeven_WR={x['breakeven_wr']}% "
              f"after10bps={x['avg_after_10bps']:+.3f}%")

    gr = report["grade_crypto"]
    print(f"\n[5] GRADE MONOTONICITY ({gr['class']}): {'YES' if gr['monotonic'] else 'no'}")
    for r in gr["by_grade"]:
        print(f"  grade {r['grade']}: n={r['n']:<5} WR={r['win_rate']:.1%}  "
              f"avg={r['avg']:+.3f}%  PF={_fmt_pf(r['profit_factor'])}")

    print(f"\n[6] TIMEFRAME (crypto)")
    for r in report["timeframe_crypto"]:
        print(f"  {r['timeframe']:<10} n={r['n']:<5} WR={r['win_rate']:.1%}  "
              f"avg={r['avg']:+.3f}%  PF={_fmt_pf(r['profit_factor'])}")

    print("\n[7] STRATEGIES (n>=30)")
    for r in report["strategies"]:
        print(f"  {r['class']:<8} {r['strategy'][:38]:<38} n={r['n']:<5} "
              f"WR={r['win_rate']:.1%}  PF={_fmt_pf(r['profit_factor'])}")

    it = report["integrity"]
    print("\n[8] DATA INTEGRITY")
    print(f"  benchmark column: {it['has_benchmark_column']}   cost column: {it['has_cost_column']}")
    for k in ("Entry Time_present", "Exit Time_present", "both_timestamps",
              "holding_hours_median", "unresolved_zero_closed"):
        if k in it:
            print(f"  {k}: {it[k]}")
    if "label_errors" in it:
        print(f"  label errors: {it['label_errors']}")
    if "active" in it:
        print(f"  active: {it['active']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
