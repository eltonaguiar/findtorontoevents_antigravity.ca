import json, math, statistics as st, collections
from math import comb
D=json.load(open("/tmp/peercheck/dashboard_payload.json"))
rc=D["picks"]["recent_closed"]
def f(x):
    try:
        v=float(x); return v if math.isfinite(v) else None
    except: return None
def binom_p(k,n):
    from math import lgamma, exp, log
    if n<=0: return 1.0
    lp=[]
    for i in range(n+1):
        lp.append(lgamma(n+1)-lgamma(i+1)-lgamma(n-i+1)-n*log(2))
    pk=lp[k]
    return min(1.0, sum(exp(x) for x in lp if x<=pk+1e-12))
def stats(rows,label):
    p=[f(r["pnl_pct"]) for r in rows]; p=[x for x in p if x is not None]
    if not p: return None
    n=len(p); wins=[x for x in p if x>0]; losses=[x for x in p if x<0]; z=[x for x in p if x==0]
    gw=sum(wins); gl=abs(sum(losses))
    mean=sum(p)/n; sd=st.pstdev(p) if n>1 else 0
    t=(mean/(sd/math.sqrt(n))) if sd>0 else 0
    srt=sorted(p); med=st.median(p)
    conc=(sum(sorted(wins)[-5:])/gw*100) if gw>0 else float('nan')
    return dict(label=label,n=n,wins=len(wins),losses=len(losses),zeros=len(z),
        wr=round(100*len(wins)/n,1),pf=round(gw/gl,3) if gl>0 else None,
        mean=round(mean,3),med=round(med,3),sum=round(sum(p),1),
        sd=round(sd,2),t=round(t,2),binp=round(binom_p(len(wins),n-len(z)) if n-len(z)>0 else 1,4),
        top5share=round(conc,1),avgwin=round(gw/len(wins),2) if wins else None,
        avgloss=round(gl/len(losses),2) if losses else None,
        best=round(srt[-1],2),worst=round(srt[0],2))
def show(d):
    if d: print(f"{d['label']:<28} n={d['n']:<5} WR={d['wr']:<5} PF={str(d['pf']):<7} mean={d['mean']:<7} med={d['med']:<7} sum={d['sum']:<8} t={d['t']:<6} binp={d['binp']:<7} top5%={d['top5share']:<5} W/L={d['avgwin']}/{d['avgloss']}")
print("### PER ASSET CLASS (all 3500)")
res={}
for c in ["CRYPTO","EQUITY","ETF","FOREX","BOND","COMMODITY"]:
    d=stats([r for r in rc if r["asset_class"]==c],c); res[c]=d; show(d)
show(stats(rc,"ALL"))
print("\n### EXIT REASON x CLASS")
for c in ["CRYPTO","EQUITY","ETF","FOREX","BOND"]:
    for e in ["TP_HIT","SL_HIT","FORCE_CLOSED","TIME_EXIT","EXPIRED","UNKNOWN"]:
        rows=[r for r in rc if r["asset_class"]==c and r.get("exit_reason")==e]
        if len(rows)>=15: show(stats(rows,f"{c}/{e}"))
print("\n### BY EXIT REASON (all)")
for e in ["TP_HIT","SL_HIT","FORCE_CLOSED","TIME_EXIT","EXPIRED","UNKNOWN"]:
    show(stats([r for r in rc if r.get("exit_reason")==e],e))
print("\n### BY SOURCE SYSTEM (n>=60)")
sc=collections.Counter(r.get("source_system") for r in rc)
for s,_ in sc.most_common():
    rows=[r for r in rc if r.get("source_system")==s]
    if len(rows)>=60: show(stats(rows,str(s)))
print("\n### TOP STRATEGIES (n>=40)")
sc2=collections.Counter(r.get("strategy") for r in rc)
for s,_ in sc2.most_common(14):
    rows=[r for r in rc if r.get("strategy")==s]
    if len(rows)>=40: show(stats(rows,str(s)[:28]))
print("\n### MEGA_MUTATION LEDGER CHECK")
mm=[r for r in rc if "mega_mut" in json.dumps(r).lower() or r.get("source_system")=="mega_mutation"]
show(stats(mm,"mega_mutation@payload"))
for s in sorted({r.get("strategy") for r in mm}):
    show(stats([r for r in mm if r.get("strategy")==s],f"  strat {s}"))
for sy in sorted({r.get("symbol") for r in mm}):
    sub=[r for r in mm if r.get("symbol")==sy]
    if len(sub)>=2: show(stats(sub,f"  sym {sy}"))
print("\n### UNIT CHECK: pnl_pct vs recomputed from prices")
tot=0; ok=0; bad=0; diffs=[]
per=collections.defaultdict(lambda:[0,0,[]])
for r in rc:
    e=f(r.get("entry_price")); x=f(r.get("exit_price")); p=f(r.get("pnl_pct"))
    if not e or not x or p is None or e==0: continue
    r_= (x/e-1) if r.get("direction")=="LONG" else (1-x/e)
    exp=r_*100
    d=abs(p-exp); tot+=1; diffs.append(d)
    c=per[r["asset_class"]]; c[0]+=1; c[2].append(d)
    if d<=0.05: ok+=1; c[1]+=1
    else: bad+=1
print(f"checkable rows={tot} within0.05pp={ok} ({100*ok/tot:.1f}%) mismatch={bad}")
print(f"median abs diff={st.median(diffs):.3f}pp  p90={sorted(diffs)[int(.9*len(diffs))]:.3f}")
for c,v in per.items(): print(f"  {c}: n={v[0]} consistent={v[1]} ({100*v[1]/v[0]:.1f}%) median_diff={st.median(v[2]):.3f}")
print("\n### ID / DUP CHECKS")
ids=collections.Counter(r.get("id") for r in rc)
print("unique ids:",len(ids),"of",len(rc),"| dup ids:",sum(1 for k,v in ids.items() if v>1))
k3=collections.Counter((r.get("strategy"),r.get("symbol"),r.get("timestamp")) for r in rc)
print("dup (strategy,symbol,timestamp) groups:",sum(1 for k,v in k3.items() if v>1),"extra rows:",sum(v-1 for v in k3.values() if v>1))
print("distinct symbols:",len({r.get('symbol') for r in rc}),"| window:",min(r['closed_at'] for r in rc if r.get('closed_at')),"->",max(r['closed_at'] for r in rc if r.get('closed_at')))
print("\n### AFTER-COST FIELD")
ac=[r.get("after_cost_net_per_trade") for r in rc]
print("non-null after_cost:",sum(1 for x in ac if x is not None),"/",len(rc))
print("\n### SAME-CLASS SPLIT-HALF (by closed_at)")
for c in ["CRYPTO","EQUITY","ETF","FOREX"]:
    rows=sorted([r for r in rc if r["asset_class"]==c and r.get("closed_at")],key=lambda r:r["closed_at"])
    h=len(rows)//2
    show(stats(rows[:h],f"{c} 1st half")); show(stats(rows[h:],f"{c} 2nd half"))
json.dump({"classes":res},open("/tmp/v2/class_stats.json","w"),indent=1)
