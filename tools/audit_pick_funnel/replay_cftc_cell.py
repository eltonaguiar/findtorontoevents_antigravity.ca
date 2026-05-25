"""One-shot replay: verify the COMMODITY cftc edge cell from top_edges_per_class.json.

Cell: conf=C0.60-0.70 & rr=RR1.0-1.5 & fam=cftc
Expected: n=136, wins=96, PF=3.283, avg_pnl=0.0257%
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.audit_pick_funnel._db import connect_stocks
from tools.audit_pick_funnel.extract_funnel import fetch_picks, _classify_status, _normalize_class
from tools.audit_pick_funnel.top_edges import expand_pick_tags, bayes_wr, profit_factor


def main() -> int:
    conn = connect_stocks()
    try:
        picks = fetch_picks(conn, 90)
    finally:
        conn.close()
    print(f"[replay] fetched {len(picks)} rows from trading_picks (90d)")

    matched = []
    cftc_any_class = 0
    cftc_commodity_any = 0
    for p in picks:
        if _normalize_class(p.get("category")) != "COMMODITY":
            continue
        st = _classify_status(p.get("status"))
        if st not in ("WIN", "LOSS"):
            continue
        tags = expand_pick_tags(p)
        if tags["fam"] == "cftc":
            cftc_commodity_any += 1
        if tags["conf"] == "C0.60-0.70" and tags["rr"] == "RR1.0-1.5" and tags["fam"] == "cftc":
            matched.append({
                "id": p.get("id"),
                "symbol": p.get("symbol"),
                "strategy": p.get("strategy"),
                "won": st == "WIN",
                "pnl_pct": float(p["pnl_pct"]) if p.get("pnl_pct") is not None else 0.0,
            })
    for p in picks:
        tags = expand_pick_tags(p) if _classify_status(p.get("status")) in ("WIN","LOSS") else None
        if tags and tags["fam"] == "cftc":
            cftc_any_class += 1

    n = len(matched)
    wins = sum(1 for m in matched if m["won"])
    pnls = [m["pnl_pct"] for m in matched]
    pf = profit_factor(pnls) if pnls else 0.0
    avg = (sum(pnls) / n) if n else 0.0
    wr_shrunk = bayes_wr(wins, n) if n else 0.0

    print(f"[replay] COMMODITY cftc-family decisive picks: {cftc_commodity_any}")
    print(f"[replay] cftc-family decisive (all classes):    {cftc_any_class}")
    print(f"[replay] matched cell rows: n={n}, wins={wins}")
    print(f"[replay] PF={pf:.3f}  avg_pnl%={avg:.4f}  WR_shrunk%={100*wr_shrunk:.2f}")
    print(f"[replay] expected:   n=136  wins=96  PF=3.283  avg=0.0257  WR_shrunk=67.95")

    # Sample strategy strings that produced cftc family
    samples = sorted({m["strategy"] for m in matched})[:10]
    print(f"[replay] strategy samples in cell: {samples}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
