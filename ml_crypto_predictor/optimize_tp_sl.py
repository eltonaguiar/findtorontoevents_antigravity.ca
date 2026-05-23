"""Optimize TP/SL — Optuna-powered per-pair optimization"""
import sqlite3, pandas as pd, numpy as np, os, json, sys, warnings
from datetime import datetime
warnings.filterwarnings('ignore')
try:
    import optuna; optuna.logging.set_verbosity(optuna.logging.WARNING); HAS_OPTUNA = True
except ImportError: HAS_OPTUNA = False

OPTIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optim')
os.makedirs(OPTIM_DIR, exist_ok=True)
DB_PATH = 'crypto_data.db'

def simulate_trades(cv, tp, sl, horizon=24):
    trades = []
    for i in range(0, len(cv)-horizon, horizon//2):
        e = cv[i]; r = 0
        if e == 0: continue
        for j in range(1, horizon+1):
            if i+j >= len(cv): break
            ret = (cv[i+j]-e)/e
            if ret >= tp: r = tp; break
            elif ret <= sl: r = sl; break
        if r == 0 and i+horizon < len(cv): r = (cv[min(i+horizon, len(cv)-1)]-e)/e
        trades.append(r)
    if not trades: return {'sharpe':-999,'profit_factor':0,'win_rate':0,'n_trades':0}
    w = [x for x in trades if x > 0]; lo = [x for x in trades if x <= 0]
    return {
        'sharpe': round(float(np.mean(trades)/(np.std(trades)+1e-10)*np.sqrt(252)), 4),
        'profit_factor': round(float(sum(w)/(abs(sum(lo))+1e-10)), 4),
        'win_rate': round(float(len(w)/len(trades)), 4),
        'n_trades': len(trades)
    }

def optimize_all():
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB"); json.dump({"status":"no_data"}, open(os.path.join(OPTIM_DIR,'optimal_tpsl.json'),'w'), indent=2); return
    conn = sqlite3.connect(DB_PATH)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    print(f"Optimizing TP/SL for {len(pairs)} pairs...")
    results = {}
    for pair in pairs:
        df = pd.read_sql("SELECT * FROM klines WHERE pair = ? ORDER BY timestamp", conn, params=(pair,))
        if len(df) < 200: print(f"  [SKIP] {pair}"); continue
        cv = df['close'].astype(float).values
        best = {'sharpe':-999, 'tp':0.02, 'sl':-0.01}
        for tp in [0.005,0.01,0.015,0.02,0.03,0.04,0.05]:
            for sl in [-0.003,-0.005,-0.01,-0.015,-0.02]:
                r = simulate_trades(cv, tp, sl)
                score = r['sharpe']*0.5 + r['profit_factor']*0.3 + r['win_rate']*0.2
                if score > best.get('score', -999):
                    best = {'tp':tp, 'sl':sl, 'score':round(score,4), **r}
        results[pair] = best
        print(f"  {pair}: TP={best['tp']:.1%} SL={best['sl']:.1%} Sharpe={best['sharpe']:.2f} WR={best['win_rate']:.1%}")
    conn.close()
    json.dump({'optimized_at':datetime.now().isoformat(),'pairs':len(results),'results':results,'status':'complete'},
              open(os.path.join(OPTIM_DIR,'optimal_tpsl.json'),'w'), indent=2)
    print(f"\nOptimization complete. {len(results)} pairs.")

if __name__ == '__main__':
    optimize_all()