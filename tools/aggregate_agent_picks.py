#!/usr/bin/env python3
"""aggregate_agent_picks.py — combine every agent's dated picks drop into one view.

Reads <drop-root>/<date>/*/picks.json (schema in that folder's README.md) and emits:
  - per-asset-class combined table (agent, symbol, net_bp, gates_passed, FAILS)
  - a cross-agent consensus: symbols picked by >=2 agents
  - a data-quality report: agents missing required fields
No network, no DB. This is the rollup that makes multi-agent drops comparable.
"""
import argparse, json, sys
from pathlib import Path
REQ=("symbol","n","gross_bp","cost_bp","net_bp","dsr","hold_days","gates","gates_passed")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/eaguiar2015/antigravity_review_Nov192026")
    ap.add_argument("--date", default="2026-11-23")
    ap.add_argument("--out", default="reports/agent_picks_rollup.json")
    a=ap.parse_args()
    base=Path(a.root)/a.date
    if not base.exists():
        print(f"no drop folder {base}",file=sys.stderr); return 2
    agents={}
    issues=[]
    for f in sorted(base.glob("*/picks.json")):
        agent=f.parent.name
        try: d=json.loads(f.read_text())
        except Exception as e:
            issues.append(f"{agent}: unparseable picks.json ({e})"); continue
        agents[agent]=d
        for cls,lst in (d.get("per_class") or {}).items():
            if not isinstance(lst,list): continue
            for p in lst:
                miss=[k for k in REQ if k not in p]
                if miss: issues.append(f"{agent}/{cls}/{p.get('symbol')}: missing {miss}")
    # per class combined
    combined={}
    for agent,d in agents.items():
        for cls,lst in (d.get("per_class") or {}).items():
            if not isinstance(lst,list): continue
            for p in lst:
                combined.setdefault(cls,[]).append({
                    "agent":agent,"symbol":p.get("symbol"),"n":p.get("n"),
                    "net_bp":p.get("net_bp"),"dsr":p.get("dsr"),
                    "gates_passed":p.get("gates_passed"),"FAILS":p.get("FAILS")})
    for cls in combined: combined[cls].sort(key=lambda x:-(x["net_bp"] or -1e9))
    # consensus: symbol named by >=2 agents
    from collections import defaultdict
    sym_agents=defaultdict(set)
    for agent,d in agents.items():
        for cls,lst in (d.get("per_class") or {}).items():
            if isinstance(lst,list):
                for p in lst: sym_agents[p.get("symbol")].add(agent)
    consensus={s:sorted(a) for s,a in sym_agents.items() if len(a)>=2}
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "date":a.date,"n_agents":len(agents),"agents":sorted(agents),
         "n_picks_total":sum(len(v) for v in combined.values()),
         "per_class_combined":combined,"cross_agent_consensus":consensus,
         "data_quality_issues":issues,
         "any_agent_reports_full_pass":any(
             any(p.get("gates_passed")=="5/5" for p in (d.get("per_class",{}).get(c) or []) if isinstance(d.get("per_class",{}).get(c),list))
             for d in agents.values() for c in d.get("per_class",{}))}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
    print(f"agents={len(agents)} picks={out['n_picks_total']} consensus={len(consensus)} issues={len(issues)} full_pass_any={out['any_agent_reports_full_pass']}")
    for i in issues[:8]: print("  ISSUE",i)
    return 0

if __name__=="__main__":
    sys.exit(main())
