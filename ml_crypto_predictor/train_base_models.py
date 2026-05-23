"""
Train Base Models — Gradient Boost + Random Forest
====================================================
Standalone trainer with 40+ technical features.
Handles inf/nan gracefully. No external model dependencies.
"""
import sqlite3, pandas as pd, numpy as np, os, json, sys, warnings
from datetime import datetime
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import joblib

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)
DB_PATH = 'crypto_data.db'

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def build_features(df):
    features = pd.DataFrame(index=df.index)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float)
    for p in [7, 14, 21]:
        features[f'rsi_{p}'] = compute_rsi(close, p)
    for p in [9, 21, 50, 100]:
        ema = close.ewm(span=p).mean()
        features[f'ema_{p}'] = ema
        features[f'ema_{p}_dist'] = (close - ema) / (close + 1e-10) * 100
    for p in [20, 50, 200]:
        sma = close.rolling(p).mean()
        features[f'sma_{p}'] = sma
        features[f'sma_{p}_dist'] = (close - sma) / (close + 1e-10) * 100
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    features['macd_line'] = ema12 - ema26
    features['macd_signal'] = features['macd_line'].ewm(span=9).mean()
    features['macd_hist'] = features['macd_line'] - features['macd_signal']
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    features['atr_14'] = tr.rolling(14).mean()
    features['atr_pct'] = features['atr_14'] / (close + 1e-10) * 100
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    features['bb_upper'] = bb_sma + 2 * bb_std
    features['bb_lower'] = bb_sma - 2 * bb_std
    bb_range = features['bb_upper'] - features['bb_lower']
    features['bb_width'] = bb_range / (bb_sma + 1e-10) * 100
    features['bb_pct'] = (close - features['bb_lower']) / (bb_range + 1e-10)
    vol_sma = volume.rolling(20).mean()
    features['volume_sma_20'] = vol_sma
    features['volume_ratio'] = volume / (vol_sma + 1e-10)
    features['volume_change'] = volume.pct_change()
    features['return_1'] = close.pct_change(1)
    features['return_5'] = close.pct_change(5)
    features['return_10'] = close.pct_change(10)
    features['return_20'] = close.pct_change(20)
    features['high_low_range'] = (high - low) / (close + 1e-10) * 100
    features['close_open_range'] = (close - df['open'].astype(float)) / (df['open'].astype(float) + 1e-10) * 100
    features['volatility_10'] = close.pct_change().rolling(10).std()
    features['volatility_20'] = close.pct_change().rolling(20).std()
    features['roc_5'] = (close / (close.shift(5) + 1e-10) - 1) * 100
    features['roc_10'] = (close / (close.shift(10) + 1e-10) - 1) * 100
    return features

def build_target(close, horizon=12, tp_pct=0.02, sl_pct=-0.01):
    target = pd.Series(0, index=close.index)
    close_vals = close.values
    for i in range(len(close_vals) - horizon):
        entry = close_vals[i]
        if entry == 0: continue
        for j in range(1, horizon + 1):
            ret = (close_vals[i + j] - entry) / entry
            if ret >= tp_pct:
                target.iloc[i] = 1
                break
            elif ret <= sl_pct:
                break
    return target

def train_models():
    if not os.path.exists(DB_PATH):
        print("[WARN] No database found.")
        with open(os.path.join(MODELS_DIR, 'training_results.json'), 'w') as f:
            json.dump({"status": "no_data", "trained_at": datetime.now().isoformat()}, f, indent=2)
        return
    conn = sqlite3.connect(DB_PATH)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    if not pairs:
        print("[WARN] No data in database."); conn.close(); return
    print(f"Training base models for {len(pairs)} pairs...")
    results = {}
    for pair in pairs:
        print(f"\n{'='*60}\nTraining models for {pair}\n{'='*60}")
        df = pd.read_sql("SELECT * FROM klines WHERE pair = ? ORDER BY timestamp", conn, params=(pair,))
        if len(df) < 200:
            print(f"  [SKIP] {pair}: only {len(df)} bars (need 200+)"); continue
        features = build_features(df)
        target = build_target(df['close'].astype(float), horizon=12)
        combined = features.copy()
        combined['target'] = target
        combined = combined.replace([np.inf, -np.inf], np.nan).dropna()
        if len(combined) < 100:
            print(f"  [SKIP] {pair}: only {len(combined)} valid samples"); continue
        X = combined.drop('target', axis=1)
        y = combined['target']
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        X_train = X_train.fillna(0); X_test = X_test.fillna(0)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        pos_rate = y_train.mean()
        print(f"  Train: {len(X_train)}, Test: {len(X_test)}, Positive rate: {pos_rate:.1%}")
        pair_results = {}
        try:
            m = GradientBoostingClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, min_samples_leaf=20)
            m.fit(X_train_s, y_train); yp = m.predict(X_test_s)
            acc, prec, f1 = accuracy_score(y_test, yp), precision_score(y_test, yp, zero_division=0), f1_score(y_test, yp, zero_division=0)
            mp = os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_gradient_boost.pkl')
            joblib.dump(m, mp)
            pair_results['gradient_boost'] = {'accuracy': round(acc,4), 'precision': round(prec,4), 'f1': round(f1,4), 'model_path': mp}
            print(f"  [A] Gradient Boost: acc={acc:.3f} prec={prec:.3f} f1={f1:.3f}")
        except Exception as e: print(f"  [A] GB FAILED: {e}")
        try:
            m = RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=10, class_weight='balanced', n_jobs=-1)
            m.fit(X_train_s, y_train); yp = m.predict(X_test_s)
            acc, prec, f1 = accuracy_score(y_test, yp), precision_score(y_test, yp, zero_division=0), f1_score(y_test, yp, zero_division=0)
            mp = os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_random_forest.pkl')
            joblib.dump(m, mp)
            pair_results['random_forest'] = {'accuracy': round(acc,4), 'precision': round(prec,4), 'f1': round(f1,4), 'model_path': mp}
            print(f"  [B] Random Forest: acc={acc:.3f} prec={prec:.3f} f1={f1:.3f}")
        except Exception as e: print(f"  [B] RF FAILED: {e}")
        joblib.dump(scaler, os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_scaler.pkl'))
        if pair_results:
            w = max(pair_results.items(), key=lambda x: x[1]['f1'])
            pair_results['winner'] = w[0]; pair_results['winner_f1'] = w[1]['f1']
            print(f"  WINNER: {w[0]} (F1={w[1]['f1']:.3f})")
        results[pair] = pair_results
    conn.close()
    summary = {'trained_at': datetime.now().isoformat(), 'pairs_trained': len(results), 'total_pairs': len(pairs), 'results': results, 'status': 'complete'}
    with open(os.path.join(MODELS_DIR, 'training_results.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n{'='*60}\nTRAINING COMPLETE — {len(results)}/{len(pairs)} pairs\n{'='*60}")

if __name__ == '__main__':
    train_models()