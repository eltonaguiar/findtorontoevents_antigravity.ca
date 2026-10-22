"""Minimal ML candidate evaluation using logistic regression on DB picks.

Features: confidence, asset_class (one-hot), direction.
Target: win (pnl_pct > 0).
Evaluation: chronological 70/30 split, bootstrap CI for expectancy.
"""
import argparse, os, sys, random, statistics, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

DB_HOST=os.getenv("AUDIT_DB_HOST","mysql.50webs.com")
DB_PORT=int(os.getenv("AUDIT_DB_PORT","3306"))
DB_USER=os.getenv("AUDIT_DB_USER","ejaguiar1_stocks")
DB_PASS=os.getenv("AUDIT_DB_PASS","stocks1234560")
DB_NAME=os.getenv("AUDIT_DB_NAME","ejaguiar1_stocks")

def fetch(limit=20000):
    conn=pymysql.connect(host=DB_HOST,port=DB_PORT,user=DB_USER,password=DB_PASS,database=DB_NAME,connect_timeout=15)
    cur=conn.cursor()
    cur.execute("""
        SELECT asset_class, direction, confidence, pnl_pct, recorded_at, closed_at
        FROM at_raw_picks
        WHERE status IN ('WON','LOST') AND pnl_pct IS NOT NULL AND confidence IS NOT NULL
        ORDER BY recorded_at LIMIT %s
    """,(limit,))
    rows=cur.fetchall(); conn.close()
    return rows

def main():
    rows=fetch()
    n=len(rows); split=int(n*0.7)
    train=rows[:split]; test=rows[split:]
    X_train=[[r[0], r[1], float(r[2])] for r in train]
    y_train=[1 if float(r[3])>0 else 0 for r in train]
    X_test=[[r[0], r[1], float(r[2])] for r in test]
    y_test=[1 if float(r[3])>0 else 0 for r in test]
    pnl_test=[float(r[3]) for r in test]
    ts_test=[r[4] for r in test]
    closed_test=[r[5] for r in test]

    pre=ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), [0,1]), ("num","passthrough",[2])])
    model=Pipeline([("pre",pre),("clf",LogisticRegression(max_iter=200))])
    model.fit(X_train,y_train)
    proba=model.predict_proba(X_test)[:,1]
    selected=[(pnl_test[i], proba[i], ts_test[i], closed_test[i]) for i in range(len(proba)) if proba[i]>=0.6]
    if not selected:
        print("No selected trades"); return
    pnls=[s[0] for s in selected]
    w=sum(1 for p in pnls if p>0)
    pf=sum(p for p in pnls if p>0)/abs(sum(p for p in pnls if p<0)) if any(p<0 for p in pnls) else float('inf')
    # one-position-at-a-time
    opt=[]; last=None
    for pnl,prob,ts,closed in sorted(selected, key=lambda x:x[2]):
        if last is None or ts>=last:
            opt.append(pnl); last=closed
    # bootstrap
    random.seed(42)
    exps=[]
    for _ in range(5000):
        sample=[random.choice(pnls) for _ in range(len(pnls))]
        ww=sum(1 for p in sample if p>0)/len(sample)
        aw=statistics.mean([p for p in sample if p>0]) if any(p>0 for p in sample) else 0
        al=statistics.mean([p for p in sample if p<=0]) if any(p<=0 for p in sample) else 0
        exps.append(ww*aw+(1-ww)*al)
    exps.sort(); N=5000
    res={
        "strategy":"ml_logistic_regression",
        "features":["asset_class","direction","confidence"],
        "threshold":0.6,
        "n_selected":len(pnls),
        "n_one_position":len(opt),
        "win_rate":w/len(pnls),
        "profit_factor":pf,
        "avg_return_pct":statistics.mean(pnls),
        "one_pos_pf": (sum(p for p in opt if p>0)/abs(sum(p for p in opt if p<0))) if any(p<0 for p in opt) else float('inf'),
        "bootstrap_exp_ci95":[exps[int(.025*N)],exps[int(.975*N)]],
        "bootstrap_p_positive":sum(1 for e in exps if e>0)/N,
        "baseline_n":len(pnl_test),
        "baseline_wr":sum(1 for p in pnl_test if p>0)/len(pnl_test),
        "baseline_pf":sum(p for p in pnl_test if p>0)/abs(sum(p for p in pnl_test if p<0)),
    }
    os.makedirs("audit_dashboard/data",exist_ok=True)
    json.dump(res, open("audit_dashboard/data/ml_candidate_eval.json","w"), indent=2)
    print(json.dumps(res,indent=2))

if __name__=="__main__":
    main()
