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
    ap.add_argument("--filing-check", action="store_true", help="also report who filed in 34_FINAL_PICKS vs expected")
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
    # Consensus requires the symbol to have REAL evidence (n>0 AND a net_bp) from
    # >=2 agents. A symbol merely mentioned with n=0 / net_bp=null is NOT agreement;
    # counting it produces a false consensus (caught 2026-11-23: XLE/XLK/IWM were
    # named by buffy with n=0 and by kilo with numbers, and IWM was -45.9 bp).
    sym_agents=defaultdict(set)
    sym_no_evidence=defaultdict(set)
    for agent,d in agents.items():
        for cls,lst in (d.get("per_class") or {}).items():
            if isinstance(lst,list):
                for p in lst:
                    s=p.get("symbol")
                    if p.get("n") and p.get("net_bp") is not None:
                        sym_agents[s].add(agent)
                    else:
                        sym_no_evidence[s].add(agent)
    consensus={s:sorted(a) for s,a in sym_agents.items() if len(a)>=2}
    name_overlap_no_evidence={s:sorted(a) for s,a in sym_no_evidence.items() if len(a)>=1}
    out={"generated_at":__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
         "date":a.date,"n_agents":len(agents),"agents":sorted(agents),
         "n_picks_total":sum(len(v) for v in combined.values()),
         "per_class_combined":combined,"cross_agent_consensus":consensus,
         "name_overlap_without_evidence":name_overlap_no_evidence,
         "data_quality_issues":issues,
         "any_agent_reports_full_pass":any(
             any(p.get("gates_passed")=="5/5" for p in (d.get("per_class",{}).get(c) or []) if isinstance(d.get("per_class",{}).get(c),list))
             for d in agents.values() for c in d.get("per_class",{}))}
    if a.filing_check:
        fp=Path(a.root)/"34_FINAL_PICKS_2026-11-23"
        filed_md={p.stem for p in fp.glob("*.md")} if fp.exists() else set()
        subdirs={p.name for p in fp.iterdir() if p.is_dir()} if fp.exists() else set()
        expected=["copilot","zoo","kilo","ag-swarm","hermes","buffy-freebuff","kilo-vscode","KILOCODE_VSCODE"]
        out["filing_check"]={
            "final_picks_dir_exists": fp.exists(),
            "md_files": sorted(filed_md),
            "subdirs": sorted(subdirs),
            "expected_agents": expected,
            "note": "an agent is FILED only if its file/subdir exists with header block + all ten class rows",
        }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
    print(f"agents={len(agents)} picks={out['n_picks_total']} consensus={len(consensus)} issues={len(issues)} full_pass_any={out['any_agent_reports_full_pass']}")
    for i in issues[:8]: print("  ISSUE",i)
    return 0

if __name__=="__main__":
    sys.exit(main())
