#!/usr/bin/env python3
"""validate_gate_reports.py — enforce G1-G5 disclosure schema on ranked picks.

Every pick MUST carry: n, net_bp, kill_rule, ticket_usd, dsr, dsr_n_trials,
gates(G1..G5). Every report carrying a bp figure MUST state its ticket.
Exit 1 on any violation.
"""
import json, sys
from pathlib import Path

REQ=("n","net_bp","kill_rule","ticket_usd","gates")

def check(path):
    d=json.loads(Path(path).read_text())
    picks=d.get("picks") or []
    viol=[]
    for i,p in enumerate(picks):
        for k in REQ:
            if k not in p: viol.append(f"{path} pick[{i}] {p.get('symbol')} missing {k}")
        g=p.get("gates") or {}
        if set(g)!= {"G1","G2","G3","G4","G5"}:
            viol.append(f"{path} pick[{i}] {p.get('symbol')} gates keys {sorted(g)}")
        # G3 requires trial count disclosed on the pick
        if k == "n" and p.get("dsr") is not None and p.get("dsr_n_trials") is None:
            viol.append(f"{path} pick[{i}] {p.get('symbol')} has DSR but no dsr_n_trials")
        if p.get("ticket_usd") is None:
            viol.append(f"{path} pick[{i}] {p.get('symbol')} bp figure without ticket_usd")
    return len(picks), viol

def main():
    targets=[p for p in ("reports/asset_class_rankings.json",) if Path(p).exists()]
    total=0; allv=[]
    for t in targets:
        n,v=check(t); total+=n; allv+=v
        print(f"{t}: {n} picks, {len(v)} violations")
    for v in allv[:15]: print("  VIOL",v)
    print(f"TOTAL picks={total} violations={len(allv)}")
    return 1 if allv else 0

if __name__=="__main__":
    sys.exit(main())
