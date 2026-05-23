"""
Audit strategy gaps: asset class coverage, low pick count, low WR/PF systems.
Outputs a JSON + printed report for the MIMO doc.
"""
import json
import os
from collections import defaultdict
from datetime import datetime

PERF_FILE = "alpha_engine/data/strategy_performance.json"
OUT_FILE = "audit_dashboard/data/strategy_gap_audit.json"

def main():
    d = json.load(open(PERF_FILE))
    by_ac = defaultdict(list)
    for sys_name, m in d.items():
        if not isinstance(m, dict):
            continue
        picks = int(m.get("total_picks", 0) or 0)
        wr = float(m.get("win_rate", 0) or 0)
        pf = float(m.get("profit_factor", 0) or 0)
        ac = str(m.get("asset_class", "unknown") or "unknown")
        by_ac[ac].append({"name": sys_name, "picks": picks, "wr": wr, "pf": pf})

    print("=== ASSET CLASS SUMMARY ===")
    ac_summary = {}
    for ac, systems in sorted(by_ac.items()):
        avg_picks = sum(s["picks"] for s in systems) / len(systems)
        avg_wr = sum(s["wr"] for s in systems) / len(systems)
        avg_pf = sum(s["pf"] for s in systems) / len(systems)
        weak = [s for s in systems if s["picks"] < 10 or s["wr"] < 0.45 or (s["pf"] < 1.0 and s["picks"] > 3)]
        top = sorted(systems, key=lambda x: -x["wr"])[:3]
        ac_summary[ac] = {
            "count": len(systems),
            "avg_picks": round(avg_picks, 1),
            "avg_wr": round(avg_wr, 3),
            "avg_pf": round(avg_pf, 3),
            "weak_count": len(weak),
            "top_performers": top,
            "weak": weak[:5],
        }
        print(f"  {ac}: {len(systems)} strats, avg_picks={avg_picks:.1f}, WR={avg_wr:.2f}, PF={avg_pf:.2f}, weak={len(weak)}")

    print()
    print("=== TOP PERFORMERS (picks>=5, WR>=0.50) ===")
    top_all = []
    for sys_name, m in d.items():
        if not isinstance(m, dict):
            continue
        picks = int(m.get("total_picks", 0) or 0)
        wr = float(m.get("win_rate", 0) or 0)
        pf = float(m.get("profit_factor", 0) or 0)
        ac = str(m.get("asset_class", "?") or "?")
        if picks >= 5 and wr >= 0.50:
            top_all.append({"name": sys_name, "picks": picks, "wr": wr, "pf": pf, "ac": ac})
    top_all.sort(key=lambda x: -x["wr"])
    for s in top_all[:20]:
        print(f"  {s['name']}: picks={s['picks']}, WR={s['wr']:.2f}, PF={s['pf']:.2f}, AC={s['ac']}")

    print()
    print("=== LOW PERFORMERS (picks<5 OR WR<0.45 OR PF<1.0) ===")
    low_all = []
    for sys_name, m in d.items():
        if not isinstance(m, dict):
            continue
        picks = int(m.get("total_picks", 0) or 0)
        wr = float(m.get("win_rate", 0) or 0)
        pf = float(m.get("profit_factor", 0) or 0)
        ac = str(m.get("asset_class", "?") or "?")
        if picks < 5 or wr < 0.45 or (pf < 1.0 and picks > 3):
            low_all.append({"name": sys_name, "picks": picks, "wr": wr, "pf": pf, "ac": ac})
    low_all.sort(key=lambda x: x["picks"])
    for s in low_all[:25]:
        print(f"  {s['name']}: picks={s['picks']}, WR={s['wr']:.2f}, PF={s['pf']:.2f}, AC={s['ac']}")

    # Gaps: asset classes with <5 strategies or no high-performer
    print()
    print("=== COVERAGE GAPS ===")
    all_asset_classes = ["crypto", "stocks", "etf", "forex", "futures", "commodities", "indices"]
    for ac in all_asset_classes:
        info = ac_summary.get(ac, None)
        if info is None:
            print(f"  MISSING: {ac} — no strategies at all")
        elif info["count"] < 5:
            print(f"  THIN: {ac} — only {info['count']} strategies")
        elif info["avg_wr"] < 0.50:
            print(f"  WEAK: {ac} — avg WR={info['avg_wr']:.2f}")

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "asset_class_summary": ac_summary,
        "top_performers": top_all[:20],
        "low_performers": low_all[:30],
    }
    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {OUT_FILE}")

if __name__ == "__main__":
    main()
