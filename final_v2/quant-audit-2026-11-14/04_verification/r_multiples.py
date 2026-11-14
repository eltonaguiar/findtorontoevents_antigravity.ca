import json, math, statistics as st, collections
D=json.load(open("/tmp/peercheck/dashboard_payload.json"))
rc=D["picks"]["recent_closed"]
def f(x):
    try:
        v=float(x); return v if math.isfinite(v) else None
    except: return None
print("### PLANNED RISK AND R-MULTIPLES PER CLASS")
for c in ["CRYPTO","EQUITY","ETF","FOREX","BOND"]:
    rows=[r for r in rc if r["asset_class"]==c]
    risk=[];R=[];rr=[];slip=[]
    for r in rows:
        e=f(r.get("entry_price")); s=f(r.get("stop_loss")); p=f(r.get("pnl_pct")); t=f(r.get("take_profit")); q=f(r.get("rr_ratio"))
        if e and s and e!=0:
            k=abs(e-s)/e*100
            if k>1e-9:
                risk.append(k)
                if p is not None: R.append(p/k)
                if t: rr.append(abs(t-e)/abs(e-s))
        if q: rr.append(q)
    if not risk: continue
    loss=[x for x in R if x<0]
    print(f"{c:<9} n={len(rows):<5} planned_risk med={st.median(risk):.2f}% mean={sum(risk)/len(risk):.2f}% | plannedRR med={st.median(rr):.2f} | R: mean={sum(R)/len(R):+.3f} med={st.median(R):+.2f} | avg_loss_R={sum(loss)/len(loss):+.2f} | %R>-1={100*sum(1 for x in R if x>-1)/len(R):.1f}% | %R>=1={100*sum(1 for x in R if x>=1)/len(R):.1f}%")
print("\n### TIMEFRAME x CLASS (n>=25)")
tf=collections.Counter((r["asset_class"],r.get("trade_timeframe")) for r in rc)
for (c,t),n in sorted(tf.items(),key=lambda x:-x[1]):
    if n<25: continue
    rows=[r for r in rc if r["asset_class"]==c and r.get("trade_timeframe")==t]
    p=[f(r["pnl_pct"]) for r in rows]; p=[x for x in p if x is not None]
    w=sum(1 for x in p if x>0); gw=sum(x for x in p if x>0); gl=abs(sum(x for x in p if x<0))
    print(f"{c:<9} {str(t):<12} n={len(p):<5} WR={100*w/len(p):5.1f} PF={(gw/gl if gl else float('inf')):6.3f} mean={sum(p)/len(p):+.3f} sum={sum(p):+8.1f}")
print("\n### STOP DISCIPLINE: realized avg loss vs planned risk")
for c in ["CRYPTO","EQUITY","ETF","FOREX"]:
    rows=[r for r in rc if r["asset_class"]==c and r.get("exit_reason")=="SL_HIT"]
    pr=[];lp=[]
    for r in rows:
        e=f(r.get("entry_price")); s=f(r.get("stop_loss")); p=f(r.get("pnl_pct"))
        if e and s and e!=0: pr.append(abs(e-s)/e*100)
        if p is not None: lp.append(abs(p))
    if pr and lp:
        print(f"{c:<9} SL rows={len(rows):<4} planned_risk_med={st.median(pr):.2f}% realized_loss_med={st.median(lp):.2f}% overshoot={(st.median(lp)/st.median(pr)-1)*100:+.1f}%")
print("\n### TP_HIT realized vs planned TP", )
for c in ["CRYPTO","EQUITY","ETF","FOREX"]:
    rows=[r for r in rc if r["asset_class"]==c and r.get("exit_reason")=="TP_HIT"]
    ex=[];tp=[]
    for r in rows:
        e=f(r.get("entry_price")); s=f(r.get("stop_loss")); t=f(r.get("take_profit")); p=f(r.get("pnl_pct"))
        if e and s and t and abs(e-s)>1e-9: tp.append(abs(t-e)/abs(e-s))
        if p is not None: ex.append(p)
    if tp and ex: print(f"{c:<9} TP rows={len(rows):<4} plannedRR_med={st.median(tp):.2f} realized_win_med={st.median(ex):.2f}%")
print("\n### BREAKEVEN WR NEEDED (from realized W/L) vs ACTUAL")
for c in ["CRYPTO","EQUITY","ETF","FOREX","BOND"]:
    p=[f(r["pnl_pct"]) for r in rc if r["asset_class"]==c]; p=[x for x in p if x is not None]
    w=[x for x in p if x>0]; l=[x for x in p if x<0]
    if not w or not l: continue
    aw=sum(w)/len(w); al=abs(sum(l))/len(l)
    be=al/(aw+al)*100; act=100*len(w)/len(p)
    # with costs: assume 0.10% crypto round trip, 0.05 others
    cost={"CRYPTO":0.20,"EQUITY":0.05,"ETF":0.05,"FOREX":0.04,"BOND":0.05}[c]
    aw2=aw-cost; al2=al+cost; be2=al2/(aw2+al2)*100
    print(f"{c:<9} avg_win={aw:.2f} avg_loss={al:.2f} breakeven_WR={be:.1f}% actual_WR={act:.1f}% margin={act-be:+.1f}pp | after_cost breakeven={be2:.1f}% margin={act-be2:+.1f}pp")
