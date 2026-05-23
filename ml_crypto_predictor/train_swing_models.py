"""Train Swing Models — Trend indicators, wider TP/SL (4%/2%)"""
import sqlite3, pandas as pd, numpy as np, os, json, sys, warnings
from datetime import datetime
warnings.filterwarnings('ignore')
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, f1_score
from sklearn.preprocessing import StandardScaler
import joblib

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'swing')
os.makedirs(MODELS_DIR, exist_ok=True)
DB_PATH = 'crypto_data.db'

def build_swing_features(df):
    f = pd.DataFrame(index=df.index)
    c, h, l, v = df['close'].astype(float), df['high'].astype(float), df['low'].astype(float), df['volume'].astype(float)
    for p in [14, 21, 50]:
        d = c.diff(); g = d.where(d>0,0).rolling(p).mean(); lo = (-d.where(d<0,0)).rolling(p).mean()
        f[f'rsi_{p}'] = 100-(100/(1+g/(lo+1e-10)))
    for p in [9,21,50,100,200]:
        f[f'ema_{p}_dist'] = (c - c.ewm(span=p).mean())/(c+1e-10)*100
    f['trend_score'] = sum((c > c.ewm(span=p).mean()).astype(int) for p in [9,21,50,100])/4
    ema12 = c.ewm(span=12).mean(); ema26 = c.ewm(span=26).mean()
    f['macd'] = ema12 - ema26; f['macd_signal'] = f['macd'].ewm(span=9).mean(); f['macd_hist'] = f['macd'] - f['macd_signal']
    for p in [5,10,20,50]: f[f'return_{p}'] = c.pct_change(p)
    f['vol_20'] = c.pct_change().rolling(20).std(); f['vol_50'] = c.pct_change().rolling(50).std()
    f['vol_regime'] = f['vol_20']/(f['vol_50']+1e-10)
    hi20 = h.rolling(20).max(); lo20 = l.rolling(20).min()
    f['sr_position'] = (c-lo20)/((hi20-lo20)+1e-10)
    vs = v.rolling(20).mean(); f['vol_trend'] = v/(vs+1e-10)
    tr = pd.concat([h-l, abs(h-c.shift(1)), abs(l-c.shift(1))], axis=1).max(axis=1)
    f['atr_pct'] = tr.rolling(14).mean()/(c+1e-10)*100
    return f

def train_swing():
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB"); json.dump({"status":"no_data"}, open(os.path.join(MODELS_DIR,'swing_results.json'),'w'), indent=2); return
    conn = sqlite3.connect(DB_PATH)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    print(f"Training swing models for {len(pairs)} pairs...")
    results = {}
    for pair in pairs:
        df = pd.read_sql("SELECT * FROM klines WHERE pair = ? ORDER BY timestamp", conn, params=(pair,))
        if len(df) < 300: print(f"  [SKIP] {pair}"); continue
        feat = build_swing_features(df).replace([np.inf,-np.inf], np.nan).dropna()
        tgt = pd.Series(0, index=df.index)
        cv = df['close'].astype(float).values
        for i in range(len(cv)-24):
            e = cv[i]
            if e == 0: continue
            for j in range(1,25):
                r = (cv[i+j]-e)/e
                if r >= 0.04: tgt.iloc[i]=1; break
                elif r <= -0.02: break
        combined = feat.copy(); combined['target'] = tgt.loc[feat.index]; combined = combined.dropna()
        if len(combined) < 100: continue
        X, y = combined.drop('target', axis=1).fillna(0), combined['target']
        si = int(len(X)*0.8)
        sc = StandardScaler(); Xtr = sc.fit_transform(X.iloc[:si]); Xte = sc.transform(X.iloc[si:])
        m = GradientBoostingClassifier(n_estimators=300, max_depth=5, learning_rate=0.03, subsample=0.8)
        m.fit(Xtr, y.iloc[:si]); yp = m.predict(Xte)
        acc, prec, f1 = accuracy_score(y.iloc[si:],yp), precision_score(y.iloc[si:],yp,zero_division=0), f1_score(y.iloc[si:],yp,zero_division=0)
        pc = pair.replace("/","_")
        joblib.dump(m, os.path.join(MODELS_DIR, f'{pc}_swing.pkl'))
        joblib.dump(sc, os.path.join(MODELS_DIR, f'{pc}_swing_scaler.pkl'))
        results[pair] = {'accuracy':round(acc,4),'precision':round(prec,4),'f1':round(f1,4)}
        print(f"  {pair}: acc={acc:.3f} prec={prec:.3f} f1={f1:.3f}")
    conn.close()
    json.dump({'trained_at':datetime.now().isoformat(),'pairs':len(results),'results':results,'status':'complete'},
              open(os.path.join(MODELS_DIR,'swing_results.json'),'w'), indent=2)
    print(f"\nSwing training complete. {len(results)} pairs.")

if __name__ == '__main__':
    train_swing()