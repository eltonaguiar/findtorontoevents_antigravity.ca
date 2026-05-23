"""Quick probe of model probabilities for profitable pairs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_crypto_predictor.production_engine import *
import json

bt_path = BACKTEST_DIR / 'walk_forward_results.json'
with open(bt_path) as f:
    bt = json.load(f)

# Check ALL pairs, not just profitable
print("=== MODEL PROBABILITIES (Current Market) ===\n")

import ccxt
exchange = ccxt.kraken()

for pair, result in sorted(bt.items(), key=lambda x: x[1].get('profit_factor', 0) if x[1] else 0, reverse=True):
    if result is None:
        continue
    pair_clean = pair.replace('/', '_')
    model_path = PRODUCTION_DIR / f'{pair_clean}_production.pkl'
    if not model_path.exists():
        continue
    model_pack = joblib.load(model_path)
    
    pf = result.get('profit_factor', 0)
    wr = result.get('win_rate', 0)
    is_profitable = pf >= 1.0 and wr >= 0.35
    
    try:
        kraken_sym = pair.replace('/USDT', '/USD')
        ohlcv = exchange.fetch_ohlcv(kraken_sym, '1h', limit=250)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        features = build_production_features(df)
        latest = features.iloc[-1:].fillna(0)
        
        model_features = model_pack['features']
        for col in model_features:
            if col not in latest.columns:
                latest[col] = 0
        latest = latest[model_features]
        
        X_scaled = model_pack['scaler'].transform(latest)
        prob_rf = model_pack['rf'].predict_proba(X_scaled)[0][1]
        prob_gbt = model_pack['gbt'].predict_proba(X_scaled)[0][1]
        prob = 0.4 * prob_rf + 0.6 * prob_gbt
        
        price = float(df['close'].iloc[-1])
        status = "PROFITABLE" if is_profitable else "unprofitable"
        signal = "BUY" if prob >= 0.60 else ("WATCH" if prob >= 0.45 else "SKIP")
        print(f"  {'*' if is_profitable else ' '} {pair:12s} | PF={pf:.2f} WR={wr:.0%} | prob={prob:.3f} ({signal:5s}) | ${price:.4f}")
    except Exception as e:
        print(f"  {pair}: ERROR - {e}")

print("\n* = Backtest-validated profitable pair")
