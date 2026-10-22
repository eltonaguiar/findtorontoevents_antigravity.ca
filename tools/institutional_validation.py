"""Institutional-grade validation metrics for a candidate strategy.

Computes Sharpe, Sortino, Calmar, DSR, Monte Carlo p-value, Omega, CVaR
from resolved trade returns (pnl_pct) pulled from at_raw_picks.

Usage:
    python tools/institutional_validation.py --strategy luxalgo_confluence --source AlphaEngine --direction SHORT --symbols XRPUSDT,ETHUSDT,BTCUSDT,STXUSDT
"""
import argparse, json, os, sys, random, statistics, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql

DB_HOST=os.getenv("AUDIT_DB_HOST","mysql.50webs.com")
DB_PORT=int(os.getenv("AUDIT_DB_PORT","3306"))
DB_USER=os.getenv("AUDIT_DB_USER","ejaguiar1_stocks")
DB_PASS=os.getenv("AUDIT_DB_PASS","stocks1234560")
DB_NAME=os.getenv("AUDIT_DB_NAME","ejaguiar1_stocks")

def fetch(strategy, source, direction=None, symbols=None):
    conn=pymysql.connect(host=DB_HOST,port=DB_PORT,user=DB_USER,password=DB_PASS,database=DB_NAME,connect_timeout=15)
    cur=conn.cursor()
    q="SELECT pnl_pct, recorded_at, closed_at FROM at_raw_picks WHERE source_system=%s AND strategy=%s AND status IN ('WON','LOST')"
    params=[source,strategy]
    if direction:
        q+=" AND direction=%s"; params.append(direction)
    if symbols:
        q+=" AND symbol IN (%s)" % ",".join(["%s"]*len(symbols)); params.extend(symbols)
    cur.execute(q,params)
    rows=cur.fetchall(); conn.close()
    return [float(r[0]) for r in rows], [r[1] for r in rows], [r[2] for r in rows]

def sharpe(returns, rf=0.0):
    if len(returns)<2: return 0.0
    mean=statistics.mean(returns); std=statistics.stdev(returns)
    return (mean-rf)/std if std>0 else 0.0

def sortino(returns, rf=0.0):
    if len(returns)<2: return 0.0
    mean=statistics.mean(returns)
    downside=[r for r in returns if r<0]
    if not downside: return float('inf')
    dstd=statistics.stdev(downside) if len(downside)>1 else abs(downside[0])
    return (mean-rf)/dstd if dstd>0 else 0.0

def max_drawdown(returns):
    # cumulative returns
    cum=0; peak=0; mdd=0
    for r in returns:
        cum+=r
        peak=max(peak,cum)
        mdd=max(mdd,peak-cum)
    return mdd

def calmar(returns):
    if not returns: return 0.0
    ann=statistics.mean(returns)*252  # daily annualization
    mdd=max_drawdown(returns)
    return ann/mdd if mdd>0 else float('inf')

def omega(returns, threshold=0.0):
    gains=sum(r-threshold for r in returns if r>threshold)
    losses=sum(threshold-r for r in returns if r<=threshold)
    return gains/losses if losses>0 else float('inf')

def cvar(returns, alpha=0.01):
    if not returns: return 0.0
    sorted_r=sorted(returns)
    cutoff=int(len(sorted_r)*alpha)
    if cutoff==0: cutoff=1
    return statistics.mean(sorted_r[:cutoff])

def deflated_sharpe(returns, n_trials=1):
    # Lopez de Prado simplified: DSR = (SR - E[max SR]) / std(SR)
    # Approximate using bootstrap of SR
    if len(returns)<2: return 0.0
    sr=sharpe(returns)
    # bootstrap SRs
    random.seed(42)
    srs=[]
    for _ in range(1000):
        sample=[random.choice(returns) for _ in range(len(returns))]
        srs.append(sharpe(sample))
    mean_sr=statistics.mean(srs)
    std_sr=statistics.stdev(srs) if len(srs)>1 else 1.0
    # expected max SR under null (Euler-Mascheroni approx)
    import math
    e_max_sr = (statistics.mean(srs) + std_sr*math.sqrt(2*math.log(n_trials))) if n_trials>1 else mean_sr
    return (sr - e_max_sr)/std_sr if std_sr>0 else 0.0

def monte_carlo_pvalue(returns, n_iter=10000, seed=42):
    random.seed(seed)
    observed=statistics.mean(returns)
    count=0
    for _ in range(n_iter):
        # shuffle signs
        shuffled=[r*random.choice([-1,1]) for r in returns]
        if statistics.mean(shuffled) >= observed:
            count+=1
    return count/n_iter

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--source", default="AlphaEngine")
    ap.add_argument("--direction", default=None)
    ap.add_argument("--symbols", default=None)
    args=ap.parse_args()
    symbols=args.symbols.split(",") if args.symbols else None
    returns, ts, closed = fetch(args.strategy, args.source, args.direction, symbols)
    if len(returns)<30:
        print("INSUFFICIENT_DATA", len(returns)); sys.exit(1)
    # daily returns: assume each trade is one observation
    res={
        "strategy": args.strategy,
        "source": args.source,
        "direction": args.direction,
        "symbols": symbols,
        "n": len(returns),
        "win_rate": sum(1 for r in returns if r>0)/len(returns),
        "profit_factor": sum(r for r in returns if r>0)/abs(sum(r for r in returns if r<0)),
        "avg_return_pct": statistics.mean(returns),
        "sharpe": sharpe(returns),
        "sortino": sortino(returns),
        "calmar": calmar(returns),
        "omega": omega(returns),
        "cvar_1pct": cvar(returns, 0.01),
        "max_drawdown": max_drawdown(returns),
        "monte_carlo_p_value": monte_carlo_pvalue(returns),
        "deflated_sharpe_ratio": deflated_sharpe(returns, n_trials=100),
        "verdict": None,
    }
    # verdict
    passes = (res["sharpe"]>2.0 and res["calmar"]>2.0 and res["monte_carlo_p_value"]<0.01
              and res["profit_factor"]>1.25 and res["avg_return_pct"]>0)
    res["verdict"] = "INSTITUTIONAL_PASS" if passes else "FAIL"
    out=f"audit_dashboard/data/institutional_validation_{args.strategy}.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out,"w"), indent=2)
    print(json.dumps(res, indent=2))

if __name__=="__main__":
    main()
