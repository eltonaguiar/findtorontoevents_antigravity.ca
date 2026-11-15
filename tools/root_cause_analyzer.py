#!/usr/bin/env python3
"""
ROOT-CAUSE ANALYZER — why picks fail, per asset class
=====================================================
Buckets open/closed picks by the dimensions that reveal WHY a class or
strategy fails, per PROFITABILITY_PLAN_PER_CLASS.md §4:

  - asset class
  - direction (LONG vs SHORT asymmetry)
  - PnL sign / magnitude (net, by class)
  - symbol concentration (HHI) — one bad ticker can sink a class
  - PnL anomaly (QA verdicts: unpriced, stale-equal zero, extreme)
  - timeframe proxy (generated_at age / hold age)

Output: audit_dashboard/data/root_cause_analysis.json + printed summary.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DASH = REPO / "audit_dashboard" / "data"
LIVE_JSON = DASH / "picks_now_live_pnl.json"
OUT_JSON = DASH / "root_cause_analysis.json"


def analyze(picks):
    classes = defaultdict(lambda: {"n": 0, "n_positive": 0, "n_negative": 0,
                                  "positive_pnl": 0.0, "negative_pnl": 0.0,
                                  "long": 0, "short": 0, "n_long_win": 0,
                                  "n_short_win": 0, "unpriced": 0,
                                  "stale_zero": 0, "extreme": 0,
                                  "symbols": defaultdict(int)})
    now = datetime.now(timezone.utc)
    for p in picks:
        aclass = (p.get("asset_class") or p.get("class") or "UNKNOWN").upper()
        c = classes[aclass]
        c["n"] += 1
        sym = p.get("symbol", "")
        c["symbols"][sym] += 1

        direction = str(p.get("direction", "")).upper()
        if direction in ("SHORT", "SELL", "STRONG_SELL"):
            c["short"] += 1
        else:
            c["long"] += 1

        pnl = p.get("pnl_pct")
        cur = p.get("current_price")
        entry = p.get("entry_price")
        # unpriced
        if pnl is None or cur is None:
            c["unpriced"] += 1
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            c["unpriced"] += 1
            continue
        # stale-equal zero
        if abs(pnl_f) < 1e-9:
            if entry and cur and abs(float(cur) - float(entry)) / float(entry) >= 1e-3:
                c["stale_zero"] += 1
            continue
        # extreme
        if abs(pnl_f) > 100:
            c["extreme"] += 1
        if pnl_f > 0:
            c["n_positive"] += 1
            c["positive_pnl"] += pnl_f
            if direction in ("SHORT", "SELL", "STRONG_SELL"):
                c["n_short_win"] += 1
            else:
                c["n_long_win"] += 1
        else:
            c["n_negative"] += 1
            c["negative_pnl"] += abs(pnl_f)

    out = {}
    for aclass, c in classes.items():
        n = c["n"]
        hhi = sum((cnt / n) ** 2 for cnt in c["symbols"].values()) if n else 0
        win_rate = (c["n_positive"] / n * 100) if n else 0
        long_wr = (c["n_long_win"] / c["long"] * 100) if c["long"] else None
        short_wr = (c["n_short_win"] / c["short"] * 100) if c["short"] else None
        net = c["positive_pnl"] - c["negative_pnl"]
        pf = (c["positive_pnl"] / c["negative_pnl"]) if c["negative_pnl"] > 0 else None

        # dominant failure reason
        reasons = []
        if c["unpriced"] / n > 0.10:
            reasons.append(f"UNPRICED {c['unpriced']}/{n} (data gap)")
        if c["stale_zero"] > 0:
            reasons.append(f"STALE_EQUAL_ZERO {c['stale_zero']} (price not advancing)")
        if c["extreme"] > 0:
            reasons.append(f"EXTREME_PNL {c['extreme']} (corrupt rows)")
        if short_wr is not None and long_wr is not None and abs(short_wr - long_wr) > 15:
            dominant = "SHORT" if short_wr > long_wr else "LONG"
            reasons.append(f"DIRECTION_ASYMMETRY {dominant} wr {max(short_wr, long_wr):.0f}% vs other {min(short_wr, long_wr):.0f}%")
        if hhi > 0.5:
            top = max(c["symbols"], key=c["symbols"].get)
            reasons.append(f"CONCENTRATION HHI={hhi:.2f} on {top}")
        if win_rate < 45 and pf is not None and pf < 1.0:
            reasons.append("LOW_WR_LOW_PF (structural edge failure)")
        if not reasons:
            reasons.append("OK")
        out[aclass] = {
            "n": n, "win_rate_pct": round(win_rate, 1),
            "net_pnl_pct": round(net, 2),
            "profit_factor": round(pf, 3) if pf is not None else None,
            "long_n": c["long"], "short_n": c["short"],
            "long_wr_pct": round(long_wr, 1) if long_wr is not None else None,
            "short_wr_pct": round(short_wr, 1) if short_wr is not None else None,
            "hhi": round(hhi, 3),
            "top_symbol": max(c["symbols"], key=c["symbols"].get),
            "unpriced": c["unpriced"], "stale_zero": c["stale_zero"],
            "extreme": c["extreme"],
            "dominant_reason": "; ".join(reasons),
        }
    return out


def main():
    if not LIVE_JSON.exists():
        print(f"no live json at {LIVE_JSON}")
        return 1
    d = json.loads(LIVE_JSON.read_text())
    picks = d.get("picks", [])
    result = analyze(picks)
    result = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "n_picks": len(picks), "by_class": result}
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"ROOT-CAUSE by class ({len(picks)} picks):")
    for aclass, r in sorted(result["by_class"].items()):
        print(f"  {aclass:12} n={r['n']:5} WR={r['win_rate_pct']:5.1f}% "
              f"net={r['net_pnl_pct']:7.2f}% PF={r['profit_factor']} "
              f"HHI={r['hhi']} | {r['dominant_reason']}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
