import sqlite3
import json
import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime

# Paths
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
OPTIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optim')
BACKTEST_DIR = 'backtest_results'
os.makedirs(BACKTEST_DIR, exist_ok=True)
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
    # Handle inf and nan
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
    return features

def load_optimal_tp_sl(pair):
    optim_path = os.path.join(OPTIM_DIR, 'optimal_tpsl.json')
    if not os.path.exists(optim_path):
        return 0.02, -0.01
    optim = json.load(open(optim_path))
    return optim['results'].get(pair, {}).get('tp', 0.02), optim['results'].get(pair, {}).get('sl', -0.01)

def backtest_pair(pair, df, model_path, scaler_path, tp, sl):
    features = build_features(df)
    scaler = joblib.load(scaler_path)
    model = joblib.load(model_path)
    X = scaler.transform(features)
    predictions = model.predict_proba(X)[:,1] if hasattr(model, 'predict_proba') else model.predict(X)
    # Simple backtest simulation
    returns = df['close'].pct_change().fillna(0)
    strategy_returns = returns * (predictions > 0.5)  # Dummy strategy
    sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(365) if np.std(strategy_returns) > 0 else 0
    return {'sharpe': round(sharpe, 2), 'n_trades': int(np.sum(predictions > 0.5))}

def run_backtest():
    # Optional W&B drift logging (no-op if WANDB_API_KEY unset). See
    # tools/wandb_logger.py and Hermes UNUSED_TOOLS_VALUE_ADD.md item #3.
    try:
        from tools.wandb_logger import wb_init, wb_log, wb_finish
    except Exception:
        wb_init = wb_log = wb_finish = lambda *a, **k: False
    wb_init(project="findtorontoevents-ml",
            name="ml_crypto_predictor_backtest",
            tags=["ml_crypto_predictor", "backtest"],
            config={"commission": COMMISSION_RATE, "slippage": SLIPPAGE_RATE})
    conn = sqlite3.connect(DB_PATH)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    results = {}
    for pair in pairs:
        df = pd.read_sql("SELECT * FROM klines WHERE pair = ? ORDER BY timestamp DESC LIMIT 500", conn, params=(pair,))
        if len(df) < 50: continue
        model_path = os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_random_forest.pkl')  # Example, use winner
        scaler_path = os.path.join(MODELS_DIR, f'{pair.replace("/","_")}_scaler.pkl')
        if not (os.path.exists(model_path) and os.path.exists(scaler_path)): continue
        tp, sl = load_optimal_tp_sl(pair)
        pair_result = backtest_pair(pair, df, model_path, scaler_path, tp, sl)
        results[pair] = pair_result
        wb_log({
            f"{pair}/sharpe": pair_result.get("sharpe"),
            f"{pair}/n_trades": pair_result.get("n_trades"),
        })
    conn.close()
    # Generate picks
    picks = sorted(results.items(), key=lambda x: x[1]['sharpe'], reverse=True)[:5]
    output = "Top Crypto Picks:\n"
    for p, r in picks:
        output += f"{p}: Sharpe {r['sharpe']}, Trades {r['n_trades']}\n"
    print(output)
    with open(os.path.join(BACKTEST_DIR, 'latest.txt'), 'w') as f:
        f.write(output)
    if results:
        sharpes = [r["sharpe"] for r in results.values() if r.get("sharpe") is not None]
        wb_log({
            "summary/n_pairs": len(results),
            "summary/mean_sharpe": (sum(sharpes) / len(sharpes)) if sharpes else 0,
            "summary/max_sharpe": max(sharpes) if sharpes else 0,
            "summary/min_sharpe": min(sharpes) if sharpes else 0,
        })
    wb_finish()
    print("Backtest complete. Results in backtest_results/latest.txt")

if __name__ == '__main__':
    run_backtest()