#!/usr/bin/env python3
"""cross_review_picks.py — apply the operator's admissibility rules to ALL agents' filings.

For every <root>/<date>/*/picks.json, flag the same defects the operator caught in Kilo:
  - ranked row with n == 0 or missing n
  - net edge <= the class COST_OF_RECORD (a 'pick' below cost is net-negative)
  - missing gates/FAILS labelling
Treats it as a peer review aid, not an authority. Prints a per-agent defect list.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pick_gate import cod_cost_bp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/eaguiar2015/antigravity_review_Nov192026")
    ap.add_argument("--date", default="2026-11-23")
    ap.add_argument("--out", default="reports/cross_review_picks.json")
    a = ap.parse_args()
    base = Path(a.root) / a.date
    report = {"agents": {}}
    for f in sorted(base.glob("*/picks.json")):
        agent = f.parent.name
        try: d = json.loads(f.read_text())
        except Exception as e:
            report["agents"][agent] = {"error": str(e)}; continue
        defects = []
        n_picks = 0
        for cls, lst in (d.get("per_class") or {}).items():
            if not isinstance(lst, list):
                continue
            for p in lst:
                n_picks += 1
                sym = p.get("symbol")
                n = p.get("n")
                net = p.get("net_bp")
                if n is None or n == 0:
                    defects.append(f"{cls}/{sym}: n=0 or missing (inadmissible)")
                if net is not None:
                    cost = cod_cost_bp(cls if cls in ("EQUITY","ETF","BOND","FOREX","CRYPTO","COMMODITY") else None, sym)
                    if abs(net) < cost:
                        defects.append(f"{cls}/{sym}: |net {net}bp| < class cost {cost:.2f}bp (net-negative)")
                if "FAILS" not in p and "gates" not in p:
                    defects.append(f"{cls}/{sym}: no gates/FAILS labelling")
        report["agents"][agent] = {"n_picks": n_picks, "defects": defects[:25],
                                    "n_defects": len(defects)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2) + "\n")
    for ag, r in report["agents"].items():
        print(f"=== {ag}: picks={r.get('n_picks','?')} defects={r.get('n_defects','?')} ===")
        for dd in r.get("defects", [])[:8]:
            print("   -", dd)
    return 0

if __name__ == "__main__":
    sys.exit(main())
