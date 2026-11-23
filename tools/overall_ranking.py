#!/usr/bin/env python3
"""overall_ranking.py — aggregate per-symbol picks across asset classes.

Reads reports/asset_class_rankings.json, sorts by (gates_passed desc, net_bp desc),
emits reports/overall_ranking.json (top 20) + human summary of the single best real-money option(s).

Usage:
  python3 tools/overall_ranking.py
"""
import json
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
IN = REPO / "reports/asset_class_rankings.json"
OUT = REPO / "reports/overall_ranking.json"
SUMMARY = REPO / "reports/overall_ranking_summary.txt"


def gates_passed(g):
    return sum(1 for v in g.values() if v)


def main():
    d = json.loads(IN.read_text())
    picks = d.get("picks", [])
    ranked = sorted(picks, key=lambda p: (-gates_passed(p.get("gates", {})), p.get("net_bp", 0)), reverse=False)
    # reverse=False because we want highest gates first, then highest net_bp; sort is stable ascending on the tuple
    ranked = sorted(picks, key=lambda p: (-gates_passed(p.get("gates", {})), p.get("net_bp", 0)), reverse=True)

    top20 = ranked[:20]
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": str(IN),
        "ticket_usd": d.get("ticket_usd", 25000),
        "n_total": len(picks),
        "top20": top20,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    # human summary: the single best real-money option(s)
    best = ranked[0] if ranked else None
    lines = []
    lines.append("OVERALL RANKING (gates_passed desc, net_bp desc)")
    lines.append(f"source: {IN}  ticket=${d.get('ticket_usd', 25000):,.0f}")
    lines.append("")
    if best:
        lines.append("BEST REAL-MONEY OPTION (highest gates passed):")
        lines.append(f"  {best['symbol']} {best['side']}  n={best['n']}  net_bp={best['net_bp']:.2f}")
        lines.append(f"  gates: {best['gates']}  verdict={best['verdict']}")
        lines.append(f"  ticket=${best['ticket_usd']:,.0f}  kill_rule={best['kill_rule']}")
        lines.append(f"  DSR={best.get('dsr')} (trials={best.get('dsr_n_trials')})")
    else:
        lines.append("NO PICKS")
    lines.append("")
    lines.append("Top 5:")
    for i, p in enumerate(ranked[:5], 1):
        gp = gates_passed(p.get("gates", {}))
        lines.append(f"  {i}. {p['symbol']} {p['side']}  gates={gp}  net_bp={p['net_bp']:.2f}  verdict={p['verdict']}")

    SUMMARY.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
