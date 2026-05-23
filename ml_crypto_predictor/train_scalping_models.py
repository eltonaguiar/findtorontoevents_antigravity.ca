"""Train Scalping Models — Fast indicators, tight TP/SL (0.5%/0.3%)"""
import sqlite3, pandas as pd, numpy as np, os, json, sys, warnings
from datetime import datetime
warnings.filterwarnings('ignore')
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, f1_score
from sklearn.preprocessing import StandardScaler
import joblib

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'scalping')
os.makedirs(MODELS_DIR, exist_ok=True)
DB_PATH = 'crypto_data.db'

def build_scalp_features(df):
    f = pd.DataFrame(index=df.index)
    c, v, h, l = df['close'].astype(float), df['volume'].astype(float), df['high'].astype(float), df['low'].astype(float)
    for p in [5, 9]:
        d = c.diff(); g = d.where(d>0,0).rolling(p).mean(); lo = (-d.where(d<0,0)).rolling(p).mean()
        f[f'rsi_{p}'] = 100-(100/(1+g/(lo+1e-10)))
    f['ema_5'] = c.ewm(span=5).mean(); f['ema_13'] = c.ewm(span=13).mean()
    f['ema_cross'] = (f['ema_5']-f['ema_13'])/(c+1e-10)*100
    for p in [1,2,3]: f[f'return_{p}'] = c.pct_change(p)
    vs = v.rolling(10).mean(); f['vol_spike'] = v/(vs+1e-10); f['vol_accel'] = f['vol_spike'].diff()
    f['range_pct'] = (h-l)/(c+1e-10)*100; f['volatility_5'] = c.pct_change().rolling(5).std()
    f['volatility_10'] = c.pct_change().rolling(10).std()
    return f

def train_scalping():
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB"); os.makedirs(MODELS_DIR, exist_ok=True)
        json.dump({"status":"no_data"}, open(os.path.join(MODELS_DIR,'scalp_results.json'),'w'), indent=2); return
    conn = sqlite3.connect(DB_PATH)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    print(f"Training scalping models for {len(pairs)} pairs...")
    results = {}
    for pair in pairs:
        df = pd.read_sql("SELECT * FROM klines WHERE pair = ? ORDER BY timestamp", conn, params=(pair,))
        if len(df) < 100: print(f"  [SKIP] {pair}"); continue
        feat = build_scalp_features(df).replace([np.inf,-np.inf], np.nan).dropna()
        tgt = pd.Series(0, index=df.index)
        cv = df['close'].astype(float).values
        for i in range(len(cv)-6):
            e = cv[i]
            if e == 0: continue
            for j in range(1,7):
                r = (cv[i+j]-e)/e
                if r >= 0.005: tgt.iloc[i]=1; break
                elif r <= -0.003: break
        combined = feat.copy(); combined['target'] = tgt.loc[feat.index]
        combined = combined.dropna()
        if len(combined) < 50: continue
        X, y = combined.drop('target', axis=1).fillna(0), combined['target']
        si = int(len(X)*0.8)
        sc = StandardScaler(); Xtr = sc.fit_transform(X.iloc[:si]); Xte = sc.transform(X.iloc[si:])
        m = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8)
        m.fit(Xtr, y.iloc[:si]); yp = m.predict(Xte)
        acc, prec, f1 = accuracy_score(y.iloc[si:],yp), precision_score(y.iloc[si:],yp,zero_division=0), f1_score(y.iloc[si:],yp,zero_division=0)
        joblib.dump(m, os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_scalp.pkl'))
        joblib.dump(sc, os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_scalp_scaler.pkl'))
        results[pair] = {'accuracy':round(acc,4),'precision':round(prec,4),'f1':round(f1,4)}
        print(f"  {pair}: acc={acc:.3f} prec={prec:.3f} f1={f1:.3f}")
    conn.close()
    json.dump({'trained_at':datetime.now().isoformat(),'pairs':len(results),'results':results,'status':'complete'},
              open(os.path.join(MODELS_DIR,'scalp_results.json'),'w'), indent=2)
    print(f"\nScalping training complete. {len(results)} pairs.")

if __name__ == '__main__':
    train_scalping()