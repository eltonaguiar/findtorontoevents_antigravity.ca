#!/usr/bin/env python3
"""ledger_data_health.py — can these rows physically be true?

Checks, per asset class, on closed picks:

  BLANK        required field missing/empty (symbol, direction, asset_class,
               strategy, entry_price, exit_price, pnl_pct, closed_at)
  FLAT         pnl_pct is exactly 0.0 on a closed pick (no trade resolves to
               exactly zero to 4dp; a flat exit recorded as a closed trade is
               either unrefreshed or a resolver default)
  SIGN         direction contradicts the price move (LONG with exit<entry but
               pnl>0, or SHORT with exit>entry but pnl>0) — arithmetically
               impossible without an unstated short/leverage flip
  NO_MOVE      entry_price == exit_price while pnl_pct != 0
  BAD_PRICE    entry_price or exit_price <= 0
  LEVELS       stop/target on the wrong side of entry for the stated direction
  EXIT_SIGN    SL_HIT with pnl>0 or TP_HIT with pnl<0
  EXTREME      |pnl_pct| > 100 (a >100% move on one position)
  MISMATCH     stated pnl_pct disagrees with the price-implied return by >2pp
               (leverage/fees can explain some; the count is the point)
  DUP_ID       duplicate pick id
  OUTLIER      robust z (MAD) on pnl_pct > 10 within the class
  WINRATE100   n>=20 and every single pick won

Aggregate-only view: pf_registry's own `impossible_winrate` flags.

Usage: python3 tools/ledger_data_health.py --dashboard PATH [--resolved PATH]
"""
from __future__ import annotations
import argparse, json, math, statistics as st, sys
from collections import Counter, defaultdict

REQUIRED = ("symbol", "direction", "asset_class", "strategy",
            "entry_price", "exit_price", "pnl_pct", "closed_at")


def fnum(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def flags_for(r):
    f = []
    for k in REQUIRED:
        if blank(r.get(k)):
            f.append(f"BLANK:{k}")
    e, x, p = fnum(r.get("entry_price")), fnum(r.get("exit_price")), fnum(r.get("pnl_pct"))
    d = str(r.get("direction") or "").upper()
    if p == 0.0:
        f.append("FLAT")
    if e is not None and x is not None:
        if e <= 0 or x <= 0:
            f.append("BAD_PRICE")
        if e == x and p not in (None, 0.0):
            f.append("NO_MOVE")
        if p is not None and e > 0:
            move = (x - e) / e * 100.0
            implied = move if d != "SHORT" else -move
            if abs(implied - p) > 2.0:
                f.append("MISMATCH")
            if d != "SHORT" and move < -0.01 and p > 0.01:
                f.append("SIGN")
            if d == "SHORT" and move > 0.01 and p > 0.01:
                f.append("SIGN")
            if d != "SHORT" and move > 0.01 and p < -0.01:
                f.append("SIGN")
            if d == "SHORT" and move < -0.01 and p < -0.01:
                f.append("SIGN")
    sl, tp = fnum(r.get("stop_loss")), fnum(r.get("take_profit"))
    if e and sl and tp:
        if d != "SHORT" and not (sl < e < tp):
            f.append("LEVELS")
        if d == "SHORT" and not (tp < e < sl):
            f.append("LEVELS")
    if p is not None and abs(p) > 100:
        f.append("EXTREME")
    reason = str(r.get("exit_reason") or r.get("exit_reason_raw") or "").upper()
    if e and x and e == x and ("TP" in reason or "SL" in reason):
        # a TP/SL exit that did not move the price at all cannot have happened
        f.append("NO_MOVE_EXIT")
    if e and sl and tp and p is not None:
        # ceiling/floor implied by the pick's OWN stated levels: a pnl outside
        # them cannot be produced by this trade as specced, no matter the bars
        if d != "SHORT":
            cap, floor = (tp - e) / e * 100.0, (sl - e) / e * 100.0
        else:
            cap, floor = (e - tp) / e * 100.0, (e - sl) / e * 100.0
        if cap > 0 and p > cap + 2.0:
            f.append("GAIN_BEYOND_LEVELS")
        if floor < 0 and p < floor - 2.0:
            f.append("GAIN_BEYOND_LEVELS")
    if p is not None:
        if "SL" in reason and p > 0:
            f.append("EXIT_SIGN")
        if "TP" in reason and p < 0:
            f.append("EXIT_SIGN")
    return f


def scan(rows, label):
    ids = Counter(str(r.get("id")) for r in rows if r.get("id"))
    per = defaultdict(Counter)
    offenders = defaultdict(list)
    pnls = defaultdict(list)
    for r in rows:
        cls = str(r.get("asset_class") or "UNKNOWN").upper()
        p = fnum(r.get("pnl_pct"))
        if p is not None:
            pnls[cls].append(p)
        for fl in flags_for(r):
            per[cls][fl.split(":")[0]] += 1
            if len(offenders[fl.split(":")[0]]) < 40:
                offenders[fl.split(":")[0]].append(
                    {"id": r.get("id"), "symbol": r.get("symbol"), "cls": cls,
                     "pnl": p, "entry": fnum(r.get("entry_price")),
                     "exit": fnum(r.get("exit_price")), "dir": r.get("direction"),
                     "reason": r.get("exit_reason"), "detail": fl})
        if ids and ids.get(str(r.get("id")), 0) > 1:
            per[cls]["DUP_ID"] += 1
    outliers = {}
    for cls, ps in pnls.items():
        if len(ps) < 20:
            continue
        med = st.median(ps)
        mad = st.median([abs(x - med) for x in ps]) or 1e-9
        z = [abs(x - med) / (1.4826 * mad) for x in ps]
        n_out = sum(1 for v in z if v > 10)
        if n_out:
            per[cls]["OUTLIER"] += n_out
        outliers[cls] = {"median": round(med, 4), "mad": round(mad, 4),
                         "n_robust_z_gt10": n_out,
                         "worst_z": round(max(z), 1) if z else None,
                         "max_pnl": round(max(ps), 3), "min_pnl": round(min(ps), 3)}
        wins = sum(1 for x in ps if x > 0)
        if len(ps) >= 20 and wins == len(ps):
            per[cls]["WINRATE100"] += 1
    return {"source": label, "rows": len(rows), "by_class": {k: dict(v) for k, v in per.items()},
            "outliers": outliers,
            "offenders": {k: v[:15] for k, v in offenders.items()}}


def registry_flags(path):
    try:
        d = json.load(open(path))
    except Exception:
        return {}
    out = {}
    for view in ("by_asset_class_policy_clean", "by_asset_class_raw"):
        for r in d.get(view) or []:
            cls = str(r.get("asset_class") or "").upper()
            if r.get("impossible_winrate"):
                out.setdefault(cls, {})[view] = {
                    "n": r.get("n"), "win_rate_pct": r.get("win_rate_pct"),
                    "pf": r.get("profit_factor")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", required=True)
    ap.add_argument("--resolved", default="")
    ap.add_argument("--registry", default="")
    ap.add_argument("--json", default="reports/2026-11-22-data-health.json")
    ap.add_argument("--md", default="reports/2026-11-22-data-health.md")
    a = ap.parse_args()

    d = json.load(open(a.dashboard, encoding="utf-8"))
    closed = (d.get("picks") or {}).get("recent_closed") or []
    res = [scan(closed, "dashboard recent_closed")]
    if a.resolved:
        try:
            rows = json.load(open(a.resolved, encoding="utf-8"))
            if isinstance(rows, dict):
                rows = rows.get("picks") or rows.get("resolved") or []
            res.append(scan(rows, "universal_resolved_picks"))
        except Exception as exc:  # noqa: BLE001
            res.append({"source": a.resolved, "error": str(exc)[:200]})
    if a.registry:
        r = res[0]
        r["registry_impossible_winrate"] = registry_flags(a.registry)

    json.dump({"runs": res}, open(a.json, "w"), indent=2)
    L = ["# Ledger data health — 2026-11-22", "",
         "Every check below is arithmetic or structural, not statistical taste. "
         "`SIGN`, `NO_MOVE`, `BAD_PRICE`, `LEVELS` and `EXIT_SIGN` are impossible as "
         "written; `FLAT`, `MISMATCH`, `EXTREME`, `OUTLIER` are improbable and need "
         "an explanation from the writer.", ""]
    for run in res:
        if "error" in run:
            L += [f"## {run['source']} — FAILED: {run['error']}", ""]
            continue
        L += [f"## {run['source']} ({run['rows']} rows)", "",
              "| class | " + " | ".join(sorted({k for v in run["by_class"].values() for k in v})) + " |",
              "|---|" + "---|" * len(sorted({k for v in run["by_class"].values() for k in v}))]
        cols = sorted({k for v in run["by_class"].values() for k in v})
        for cls, v in sorted(run["by_class"].items(), key=lambda kv: -sum(kv[1].values())):
            L.append(f"| {cls} | " + " | ".join(str(v.get(c, 0)) for c in cols) + " |")
        L.append("")
        if run.get("outliers"):
            L += ["| class | median pnl | MAD | robust z>10 | max pnl | min pnl |",
                  "|---|---|---|---|---|---|"]
            for cls, o in run["outliers"].items():
                L.append(f"| {cls} | {o['median']} | {o['mad']} | {o['n_robust_z_gt10']} | "
                         f"{o['max_pnl']} | {o['min_pnl']} |")
            L.append("")
        if run.get("registry_impossible_winrate"):
            L += ["Registry `impossible_winrate` flags: "
                  + json.dumps(run["registry_impossible_winrate"]), ""]
    open(a.md, "w").write("\n".join(L) + "\n")

    for run in res:
        if "error" in run:
            print(f"{run['source']}: ERROR {run['error']}"); continue
        print(f"\n== {run['source']}: {run['rows']} rows ==")
        for cls, v in sorted(run["by_class"].items(), key=lambda kv: -sum(kv[1].values())):
            print(f"  {cls:12s} " + " ".join(f"{k}={n}" for k, n in sorted(v.items())))
        for cls, o in run.get("outliers", {}).items():
            print(f"  OUTLIER {cls}: median={o['median']} mad={o['mad']} "
                  f"z>10={o['n_robust_z_gt10']} worst_z={o['worst_z']} "
                  f"range=[{o['min_pnl']},{o['max_pnl']}]")
    print(f"\nwrote {a.json} and {a.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
