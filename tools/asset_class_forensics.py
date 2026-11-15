#!/usr/bin/env python3
"""Per-asset-class forensics.

Answers three questions with numbers instead of vibes:
  1. Is any asset class actually profitable over the whole closed ledger?
  2. Is the dashboard headline (compounded_rolling_100 = last 100 trades) hiding a
     profitable long-run ledger, or is the recent stretch genuinely bad?
  3. What mechanism is losing the money - stop-loss asymmetry, one toxic symbol,
     one inverted strategy, or just costs?

Reads whichever closed-pick file actually has the most rows with numeric pnl_pct.
No network, no writes outside /tmp.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics
import sys

MAX_MB = 60


def candidate_rows(path: str):
    """Return the largest list of pick dicts carrying pnl_pct in this file."""
    try:
        if os.path.getsize(path) > MAX_MB * 1024 * 1024:
            return None
    except OSError:
        return None
    try:
        d = json.load(open(path, encoding="utf-8", errors="replace"))
    except Exception:
        return None

    def harvest(o, depth=0):
        if depth > 4:
            return None
        if isinstance(o, list):
            rows = [x for x in o if isinstance(x, dict) and "pnl_pct" in x]
            return rows or None
        if isinstance(o, dict):
            best = None
            for v in o.values():
                got = harvest(v, depth + 1)
                if got and (best is None or len(got) > len(best)):
                    best = got
            return best
        return None

    return harvest(d)


def find_ledger() -> tuple[str, list[dict]]:
    best: tuple[str, list[dict]] = ("", [])
    patterns = ["audit_dashboard/data/*.json", "data/*.json", "reports/*.json", "*.json"]
    seen = set()
    for pat in patterns:
        for f in glob.glob(pat):
            if f in seen:
                continue
            seen.add(f)
            rows = candidate_rows(f)
            if rows and len(rows) > len(best[1]):
                best = (f, rows)
    return best


def stats(vals: list[float]) -> dict:
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    gross_win = sum(wins) or 1e-9
    gross_loss = -sum(losses) or 1e-9
    return {
        "n": len(vals),
        "wr": round(100 * len(wins) / len(vals), 1),
        "mean": round(statistics.mean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "pf": round(gross_win / gross_loss, 2),
        "sum": round(sum(vals), 1),
        "avg_win": round(statistics.mean(wins), 2) if wins else 0.0,
        "avg_loss": round(statistics.mean(losses), 2) if losses else 0.0,
    }


def compound(vals: list[float], cap: float | None = 10.0, size: float = 1.0) -> float:
    eq = 1.0
    for x in vals:
        if cap is not None:
            x = max(-cap, min(cap, x))
        eq *= 1 + size * x / 100.0
        if eq <= 0:
            return -100.0
    return round((eq - 1) * 100, 1)


def main() -> int:
    path, rows = find_ledger()
    if not rows:
        print("no ledger found", file=sys.stderr)
        return 1
    rows = [p for p in rows if isinstance(p.get("pnl_pct"), (int, float)) and p.get("pnl_pct") is not None]
    rows.sort(key=lambda p: str(p.get("exit_time") or p.get("resolved_at") or p.get("timestamp") or ""))
    print(f"ledger: {path}  ({len(rows)} closed picks with numeric pnl_pct)")
    print(f"span:   {str(rows[0].get('exit_time') or rows[0].get('timestamp'))[:10]} -> "
          f"{str(rows[-1].get('exit_time') or rows[-1].get('timestamp'))[:10]}")
    print(f"overall: {stats([p['pnl_pct'] for p in rows])}")
    print(f"overall compound(±10 cap, full size): {compound([p['pnl_pct'] for p in rows])}%")
    print()

    by_class = collections.defaultdict(list)
    for p in rows:
        by_class[p.get("asset_class") or "?"].append(p)

    print(f"{'class':10} {'n':>6} {'wr%':>6} {'mean':>7} {'median':>7} {'PF':>5} {'sum':>9}  "
          f"{'all-cap10':>10} {'last100':>9} {'last100_wr':>10} {'top_sym_share':>13}")
    for cls, ps in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        vals = [p["pnl_pct"] for p in ps]
        if len(vals) < 5:
            continue
        s = stats(vals)
        last100 = compound(vals[-100:])
        last100_wr = round(100 * sum(v > 0 for v in vals[-100:]) / min(100, len(vals)), 1)
        sym_pnl = collections.Counter()
        for p in ps:
            if p["pnl_pct"] > 0:
                sym_pnl[p.get("symbol") or "?"] += p["pnl_pct"]
        total_pos = sum(sym_pnl.values()) or 1e-9
        top_share = round(100 * sym_pnl.most_common(1)[0][1] / total_pos, 1) if sym_pnl else 0.0
        print(f"{cls:10} {s['n']:>6} {s['wr']:>6} {s['mean']:>+7} {s['median']:>+7} {s['pf']:>5} {s['sum']:>+9}  "
              f"{compound(vals):>10} {last100:>9} {last100_wr:>10} {top_share:>13}")
    print()

    for cls, ps in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        if len(ps) < 30:
            continue
        print(f"--- {cls} ---")
        strat = collections.defaultdict(list)
        for p in ps:
            strat[p.get("strategy") or p.get("source_system") or "?"].append(p["pnl_pct"])
        ranked = sorted(((k, v) for k, v in strat.items() if len(v) >= 15), key=lambda kv: -statistics.mean(kv[1]))
        for k, v in ranked[:3]:
            print(f"   + {k[:44]:44} mean={statistics.mean(v):+6.2f}% n={len(v):4} wr={100*sum(x>0 for x in v)/len(v):5.1f}%")
        for k, v in ranked[-3:]:
            print(f"   - {k[:44]:44} mean={statistics.mean(v):+6.2f}% n={len(v):4} wr={100*sum(x>0 for x in v)/len(v):5.1f}%")
        exits = collections.defaultdict(list)
        for p in ps:
            exits[str(p.get("exit_reason") or p.get("exit_reason_raw") or "?")[:22]].append(p["pnl_pct"])
        print("   exits: " + " | ".join(
            f"{k} n={len(v)} mean={statistics.mean(v):+.2f}%" for k, v in sorted(exits.items(), key=lambda kv: -len(kv[1]))[:4]))
        dirs = collections.defaultdict(list)
        for p in ps:
            dirs[str(p.get("direction") or "?")].append(p["pnl_pct"])
        if len(dirs) > 1:
            print("   direction: " + " | ".join(
                f"{k} n={len(v)} wr={100*sum(x>0 for x in v)/len(v):.1f}%" for k, v in dirs.items()))
        print()

    # where the recent pain is concentrated
    print("--- last 100 trades, by class ---")
    tail = rows[-100:]
    for cls, ps in sorted(collections.Counter(p.get("asset_class") for p in tail).items(), key=lambda kv: -kv[1]):
        v = [p["pnl_pct"] for p in tail if p.get("asset_class") == cls]
        if v:
            print(f"   {str(cls):10} n={len(v):3} mean={statistics.mean(v):+6.2f}% sum={sum(v):+8.1f} "
                  f"compound={compound(v)}%")
    print("\n--- worst 8 individual trades in the last 100 ---")
    for p in sorted(tail, key=lambda p: p["pnl_pct"])[:8]:
        print(f"   {str(p.get('symbol'))[:14]:14} {p['pnl_pct']:+8.1f}%  {str(p.get('asset_class')):9} "
              f"{str(p.get('strategy'))[:30]:30} exit={str(p.get('exit_reason'))[:18]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
