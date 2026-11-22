#!/usr/bin/env python3
"""first_touch_resolve.py — honest first-touch re-resolution with real bars.

The ledger records an exit reason (TP_HIT / SL_HIT) but not WHICH level was
touched first. H-120 measured that daily-resolution PF can be inflated ~2x by
this; this tool re-walks real daily bars from entry to exit and re-derives the
exit, using the conservative rule **SL wins a same-bar tie**.

Scope: crypto only for now (Binance is the one bar source that answers without a
key; Stooq serves a JS challenge). Coverage is limited to picks that carry
`entry_time` — the ledger has it on 1,909/3,500.

Usage: python3 tools/first_touch_resolve.py --dashboard PATH [--max-symbols N]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ohlc_bars import daily_bars  # noqa: E402


def stats(pnls):
    n = len(pnls)
    if not n:
        return {"n": 0}
    w = [p for p in pnls if p > 0]
    l = [abs(p) for p in pnls if p < 0]
    return {"n": n, "win_rate": len(w) / n,
            "profit_factor": (sum(w) / sum(l)) if l else None,
            "expectancy_pct": sum(pnls) / n}


def fnum(r, k):
    try:
        v = float(r.get(k))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def resolve(r, bars_by_symbol):
    sym = str(r.get("symbol") or "")
    bars = bars_by_symbol.get(sym)
    if not bars:
        return {"status": "NO_BARS"}
    entry = fnum(r, "entry_price")
    sl, tp = fnum(r, "stop_loss"), fnum(r, "take_profit")
    if not (entry and sl and tp):
        return {"status": "NO_LEVELS"}
    ed = str(r.get("entry_time") or "")[:10]
    xd = str(r.get("closed_at") or r.get("timestamp") or "")[:10]
    if not ed or not xd:
        return {"status": "NO_TIMES"}
    window = [b for b in bars if ed <= b[0] <= xd]
    if not window:
        return {"status": "NO_WINDOW"}
    long = str(r.get("direction", "LONG")).upper() != "SHORT"
    first, tie = None, False
    for b in window:
        _, o, hi, lo, c = b
        sl_hit = (lo <= sl) if long else (hi >= sl)
        tp_hit = (hi >= tp) if long else (lo <= tp)
        if sl_hit and tp_hit:
            first, tie = "SL", True
            break
        if sl_hit:
            first = "SL"
            break
        if tp_hit:
            first = "TP"
            break
    if first is None:
        return {"status": "NEITHER_HIT", "bars": len(window)}
    lvl = sl if first == "SL" else tp
    honest = ((lvl - entry) / entry * 100.0) if long else ((entry - lvl) / entry * 100.0)
    rec = str(r.get("exit_reason") or "").upper()
    rec_kind = "SL" if "SL" in rec else ("TP" if "TP" in rec else "OTHER")
    return {"status": "RESOLVED", "first": first, "tie": tie, "bars": len(window),
            "honest_pnl_pct": round(honest, 4), "recorded_pnl_pct": fnum(r, "pnl_pct"),
            "recorded_kind": rec_kind, "changed": rec_kind != first,
            "asset_class": str(r.get("asset_class") or "").upper(),
            "strategy": r.get("strategy")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", required=True)
    ap.add_argument("--json", default="reports/2026-11-22-first-touch.json")
    ap.add_argument("--md", default="reports/2026-11-22-first-touch.md")
    a = ap.parse_args()

    d = json.load(open(a.dashboard, encoding="utf-8"))
    closed = (d.get("picks") or {}).get("recent_closed") or []

    # one bar pull per symbol, not per pick
    syms = {str(r.get("symbol")) for r in closed
            if str(r.get("asset_class", "")).upper() == "CRYPTO" and r.get("entry_time")}
    bars, failed = {}, {}
    for s in sorted(syms):
        try:
            bars[s] = daily_bars(s)
        except Exception as exc:  # noqa: BLE001
            failed[s] = f"{type(exc).__name__}: {exc}"[:120]

    res = defaultdict(list)
    meta = defaultdict(int)
    rows = []
    for r in closed:
        if str(r.get("asset_class", "")).upper() != "CRYPTO":
            continue
        out = resolve(r, bars)
        meta[out["status"]] += 1
        if out["status"] == "RESOLVED":
            res[out["strategy"]].append(out)
            rows.append(out)

    changed = [o for o in rows if o["changed"]]
    rec = stats([o["recorded_pnl_pct"] for o in rows if o["recorded_pnl_pct"] is not None])
    hon = stats([o["honest_pnl_pct"] for o in rows])
    out = {
        "symbols_attempted": len(syms), "symbols_ok": len(bars),
        "symbol_failures": list(failed.items())[:10],
        "crypto_picks": sum(1 for r in closed if str(r.get("asset_class","")).upper()=="CRYPTO"),
        "status_counts": dict(meta),
        "resolved": len(rows), "changed": len(changed),
        "ties_sl_wins": sum(1 for o in rows if o["tie"]),
        "recorded": rec, "honest": hon,
        "pf_ratio_recorded_over_honest":
            (round(rec["profit_factor"] / hon["profit_factor"], 3)
             if rec.get("profit_factor") and hon.get("profit_factor") else None),
        "by_strategy": {k: {"n": len(v), "changed": sum(1 for o in v if o["changed"]),
                            "recorded": stats([o["recorded_pnl_pct"] for o in v
                                               if o["recorded_pnl_pct"] is not None]),
                            "honest": stats([o["honest_pnl_pct"] for o in v])}
                        for k, v in sorted(res.items(), key=lambda kv: -len(kv[1]))},
        "examples_changed": changed[:10],
    }
    json.dump(out, open(a.json, "w"), indent=2)

    L = ["# Honest first-touch re-resolution (real Binance daily bars) — 2026-11-22", "",
         f"CRYPTO picks in ledger: {out['crypto_picks']} · symbols attempted: "
         f"{out['symbols_attempted']} (ok {out['symbols_ok']}) · resolved: {out['resolved']}", "",
         f"Status: `{out['status_counts']}`", "",
         "Rule: **SL wins a same-bar tie** (conservative). Ties seen: "
         f"{out['ties_sl_wins']}.", "",
         "| measure | recorded (ledger) | honest (re-walked) |", "|---|---|---|",
         f"| n | {rec.get('n')} | {hon.get('n')} |",
         f"| win rate | {rec.get('win_rate',0):.1%} | {hon.get('win_rate',0):.1%} |",
         f"| profit factor | {rec.get('profit_factor')} | {hon.get('profit_factor')} |",
         f"| expectancy % | {rec.get('expectancy_pct',0):+.4f} | {hon.get('expectancy_pct',0):+.4f} |",
         "", f"Exits whose first-touch level differs from the recorded reason: "
             f"**{out['changed']}/{out['resolved']}**.", "",
         "## By strategy", "",
         "| strategy | n | changed | PF recorded | PF honest | exp recorded % | exp honest % |",
         "|---|---|---|---|---|---|---|"]
    for k, v in out["by_strategy"].items():
        L.append(f"| {k} | {v['n']} | {v['changed']} | {v['recorded'].get('profit_factor')} | "
                 f"{v['honest'].get('profit_factor')} | {v['recorded'].get('expectancy_pct',0):+.4f} | "
                 f"{v['honest'].get('expectancy_pct',0):+.4f} |")
    open(a.md, "w").write("\n".join(L) + "\n")

    print(f"symbols ok {len(bars)}/{len(syms)} · statuses {dict(meta)}")
    print(f"resolved {len(rows)} · changed {len(changed)} · ties {out['ties_sl_wins']}")
    print(f"recorded PF {rec.get('profit_factor')} -> honest PF {hon.get('profit_factor')} "
          f"(ratio {out['pf_ratio_recorded_over_honest']})")
    print(f"recorded exp {rec.get('expectancy_pct',0):+.4f}% -> honest {hon.get('expectancy_pct',0):+.4f}%")
    if failed:
        print("symbol failures:", list(failed.items())[:5])
    return 0


if __name__ == "__main__":
    sys.exit(main())
