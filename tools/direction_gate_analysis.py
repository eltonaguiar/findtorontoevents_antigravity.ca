#!/usr/bin/env python3
"""Counterfactual test for the two suspected inverted direction books.

Checks, on every ledger that carries direction:
  * per class x direction: n, win rate, mean, profit factor
  * stability: same split done on the first and second half of the timeline
    (an inversion that only exists in one half is a regime artefact, not a bug)
  * the effect of blocking CRYPTO LONG and ETF SHORT on the class and overall
    numbers - before vs after, no other change

Read-only. Prints tables; writes nothing.
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys

LEDGERS = [
    "audit_dashboard/data/ai_tournament_picks_latest.json",
    "audit_dashboard/data/dashboard_data.json",
]


def norm_dir(d) -> str:
    s = str(d or "").strip().upper()
    if s in ("LONG", "BUY", "BULL", "BULLISH"):
        return "LONG"
    if s in ("SHORT", "SELL", "BEAR", "BEARISH"):
        return "SHORT"
    return s or "?"


def harvest(obj, depth=0):
    if depth > 5:
        return None
    if isinstance(obj, list):
        rows = [x for x in obj if isinstance(x, dict) and "pnl_pct" in x and "direction" in x]
        return rows or None
    if isinstance(obj, dict):
        best = None
        for v in obj.values():
            got = harvest(v, depth + 1)
            if got and (best is None or len(got) > len(best)):
                best = got
        return best
    return None


def load(path: str):
    if not os.path.exists(path):
        return []
    try:
        rows = harvest(json.load(open(path, encoding="utf-8", errors="replace")))
    except Exception:
        return []
    out = []
    for p in rows or []:
        try:
            pnl = float(p["pnl_pct"])
        except (TypeError, ValueError):
            continue
        if pnl != pnl:  # NaN
            continue
        out.append({
            "cls": str(p.get("asset_class") or "?").upper(),
            "dir": norm_dir(p.get("direction")),
            "pnl": pnl,
            "t": str(p.get("exit_time") or p.get("resolved_at") or p.get("timestamp") or ""),
            "sym": p.get("symbol"),
        })
    out.sort(key=lambda r: r["t"])
    return out


def stat(vals):
    if not vals:
        return None
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    gw = sum(wins) or 1e-9
    gl = -sum(losses) or 1e-9
    return {
        "n": len(vals),
        "wr": round(100 * len(wins) / len(vals), 1),
        "mean": round(statistics.mean(vals), 2),
        "pf": round(gw / gl, 2),
        "sum": round(sum(vals), 1),
    }


def compound(vals, cap=10.0):
    eq = 1.0
    for x in vals:
        eq *= 1 + max(-cap, min(cap, x)) / 100.0
        if eq <= 0:
            return -100.0
    return round((eq - 1) * 100, 1)


def table(rows, title):
    print(f"\n  {title}")
    print(f"  {'class':10} {'dir':6} {'n':>5} {'wr%':>6} {'mean':>7} {'PF':>5} {'sum':>9}   "
          f"{'h1_wr':>6} {'h2_wr':>6} {'verdict':>12}")
    classes = sorted({r["cls"] for r in rows})
    for cls in classes:
        for direction in ("LONG", "SHORT"):
            sub = [r for r in rows if r["cls"] == cls and r["dir"] == direction]
            if len(sub) < 10:
                continue
            s = stat([r["pnl"] for r in sub])
            half = len(sub) // 2
            h1 = stat([r["pnl"] for r in sub[:half]])
            h2 = stat([r["pnl"] for r in sub[half:]])
            verdict = ""
            if h1 and h2:
                if h1["wr"] < 40 and h2["wr"] < 40:
                    verdict = "INVERTED"
                elif h1["wr"] > 55 and h2["wr"] > 55:
                    verdict = "healthy"
                else:
                    verdict = "unstable"
            print(f"  {cls:10} {direction:6} {s['n']:>5} {s['wr']:>6} {s['mean']:>+7} {s['pf']:>5} {s['sum']:>+9}   "
                  f"{h1['wr'] if h1 else 0:>6} {h2['wr'] if h2 else 0:>6} {verdict:>12}")


def gate_effect(rows, gates, label):
    """gates: {(class, direction)} to drop."""
    kept = [r for r in rows if (r["cls"], r["dir"]) not in gates]
    dropped = [r for r in rows if (r["cls"], r["dir"]) in gates]
    print(f"\n  --- {label}: drop {sorted(gates)} ---")
    for cls in sorted({r["cls"] for r in rows}):
        b = [r["pnl"] for r in rows if r["cls"] == cls]
        a = [r["pnl"] for r in kept if r["cls"] == cls]
        if len(b) < 5:
            continue
        sb, sa = stat(b), stat(a)
        print(f"  {cls:10} n {sb['n']:>4}->{sa['n'] if sa else 0:>4}  wr {sb['wr']:>5}->{sa['wr'] if sa else 0:>5}  "
              f"mean {sb['mean']:>+6}->{(sa['mean'] if sa else 0):>+6}  PF {sb['pf']:>5}->{(sa['pf'] if sa else 0):>4}  "
              f"compound {compound(b):>9}->{compound(a) if a else 0:>9}")
    b, a = stat([r["pnl"] for r in rows]), stat([r["pnl"] for r in kept])
    if b and a:
        print(f"  {'ALL':10} n {b['n']:>4}->{a['n']:>4}  wr {b['wr']:>5}->{a['wr']:>5}  "
              f"mean {b['mean']:>+6}->{a['mean']:>+6}  PF {b['pf']:>5}->{a['pf']:>4}  "
              f"compound {compound([r['pnl'] for r in rows]):>9}->{compound([r['pnl'] for r in kept]):>9}")
        print(f"  dropped: n={len(dropped)} mean={statistics.mean([r['pnl'] for r in dropped]):+.2f}% "
              f"sum={sum(r['pnl'] for r in dropped):+.1f}  "
              f"best-of-dropped={max((r['pnl'] for r in dropped), default=0):+.1f}%")


def main() -> int:
    # scenario 1 is the change actually being shipped (ETF SHORT only); scenario 2 is
    # for reference — crypto LONG is ALREADY blocked in production via
    # CRYPTO_BLOCKED_DIRECTIONS, so removing it here would double-count a live fix.
    scenarios = [
        ({("ETF", "SHORT")}, "SHIPPED: ETF SHORT gate"),
        ({("CRYPTO", "LONG"), ("ETF", "SHORT")}, "REFERENCE: also drop crypto LONG (already gated live)"),
    ]
    paths, seen = [], set()
    for p in LEDGERS + sorted(glob.glob("audit_dashboard/data/*picks*.json")):
        if p in seen or not os.path.exists(p):
            continue
        seen.add(p)
        paths.append(p)
    for path in paths:
        rows = load(path)
        if len(rows) < 60:
            continue
        print(f"\n=== {path}  ({len(rows)} rows with direction+pnl) ===")
        table(rows, "class x direction (h1/h2 = first/second half win rate)")
        for gates, label in scenarios:
            gate_effect(rows, gates, label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
