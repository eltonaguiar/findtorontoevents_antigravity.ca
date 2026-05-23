"""
Backtest the Quick Guess model on historical data to find:
1. Which features actually help prediction at each horizon
2. What accuracy is achievable with current features
3. Whether adding more features (RSI, BB, funding rate) improves it

Fetches 7 days of 1-minute candles for BTC, ETH, SOL from Binance,
builds features, trains GradientBoosting on 80%, tests on 20%.
"""

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report
from sklearn.preprocessing import StandardScaler

# Import build_features from the main agent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from quick_guess_agent import build_features, fetch_klines


# ---------------------------------------------------------------------------
# Fetch extended historical data (7 days of 1m candles = ~10080 candles)
# ---------------------------------------------------------------------------

def fetch_extended_klines(symbol: str, interval: str = '1m', total: int = 10080) -> pd.DataFrame:
    """Fetch up to 7 days of 1m candles by paginating Binance API (max 1000 per call)."""
    all_data = []
    end_time = None
    remaining = total

    while remaining > 0:
        limit = min(remaining, 1000)
        base_url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
        if end_time is not None:
            base_url += f'&endTime={end_time}'

        urls = [
            base_url,
            base_url.replace('api.binance.com', 'api1.binance.com'),
            base_url.replace('api.binance.com', 'api4.binance.com'),
        ]

        fetched = False
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                raw = urllib.request.urlopen(req, timeout=15).read()
                data = json.loads(raw)
                if not data:
                    continue
                all_data = data + all_data  # prepend older data
                end_time = data[0][0] - 1  # next page ends before first candle
                remaining -= len(data)
                fetched = True
                break
            except Exception as e:
                continue

        if not fetched:
            print(f"  Warning: could only fetch {total - remaining} candles for {symbol}")
            break

    if not all_data:
        return None

    df = pd.DataFrame(all_data, columns=[
        'ts', 'open', 'high', 'low', 'close', 'vol',
        'close_ts', 'quote_vol', 'trades', 'taker_buy_vol',
        'taker_buy_quote', 'ignore',
    ])
    for c in ['open', 'high', 'low', 'close', 'vol', 'quote_vol',
              'taker_buy_vol', 'taker_buy_quote']:
        df[c] = df[c].astype(float)
    df['trades'] = df['trades'].astype(int)
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def run_backtest():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    horizons = [1, 3, 5, 15, 60]

    print("=" * 70)
    print("QUICK GUESS ML BACKTEST — 7 days historical data")
    print("=" * 70)

    all_results = []

    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Fetching 7 days of 1m candles for {symbol}...")
        df = fetch_extended_klines(symbol, '1m', total=10080)
        if df is None or len(df) < 500:
            print(f"  SKIP {symbol}: insufficient data ({0 if df is None else len(df)} candles)")
            continue
        print(f"  Got {len(df)} candles ({df['ts'].iloc[0]} to {df['ts'].iloc[-1]})")

        # Build features
        features = build_features(df)
        feat_cols = [c for c in features.columns if c != 'atr']
        close = df['close'].values

        for h in horizons:
            # Target: did price go up after h minutes?
            target = (pd.Series(close).shift(-h) > pd.Series(close)).astype(int)

            # Valid rows: have features AND target
            min_lookback = 50
            valid = (~target.isna()) & (features.index >= min_lookback)
            valid_idx = valid[valid].index

            if len(valid_idx) < 100:
                print(f"  {symbol} +{h}m: insufficient valid rows ({len(valid_idx)})")
                continue

            X = features.loc[valid_idx, feat_cols].values
            y = target[valid_idx].values.astype(int)

            # 80/20 split (chronological, no shuffle)
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            # Scale
            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            # Train
            model = GradientBoostingClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1,
                subsample=0.8, random_state=42,
            )
            model.fit(X_train_s, y_train)

            # Predict
            y_pred = model.predict(X_test_s)
            y_proba = model.predict_proba(X_test_s)[:, 1]

            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)

            # High-confidence subset (>60% either way)
            high_conf_mask = (y_proba > 0.6) | (y_proba < 0.4)
            if high_conf_mask.sum() > 10:
                hc_acc = accuracy_score(y_test[high_conf_mask], y_pred[high_conf_mask])
                hc_count = high_conf_mask.sum()
            else:
                hc_acc = None
                hc_count = 0

            # Feature importance
            importances = model.feature_importances_
            feat_imp = sorted(zip(feat_cols, importances), key=lambda x: -x[1])

            # Base rate (what % of test labels are UP)
            base_rate = y_test.mean()

            result = {
                'symbol': symbol,
                'horizon': h,
                'accuracy': acc,
                'precision': prec,
                'recall': rec,
                'base_rate': base_rate,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'high_conf_acc': hc_acc,
                'high_conf_count': hc_count,
                'top_features': feat_imp[:5],
            }
            all_results.append(result)

            # Print
            hc_str = f", HC: {hc_acc:.1%} ({hc_count} samples)" if hc_acc else ""
            print(
                f"  {symbol} +{h:>2}m: "
                f"ACC={acc:.1%}  PREC={prec:.1%}  REC={rec:.1%}  "
                f"base={base_rate:.1%}  train={len(X_train)} test={len(X_test)}"
                f"{hc_str}"
            )
            print(f"    Top features: {', '.join(f'{n}={v:.3f}' for n, v in feat_imp[:5])}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY BY HORIZON")
    print("=" * 70)
    print(f"{'Horizon':>8} | {'Avg Acc':>8} | {'Avg HC Acc':>10} | {'Best':>15} | {'Worst':>15}")
    print("-" * 70)

    for h in horizons:
        h_results = [r for r in all_results if r['horizon'] == h]
        if not h_results:
            continue
        avg_acc = np.mean([r['accuracy'] for r in h_results])
        hc_accs = [r['high_conf_acc'] for r in h_results if r['high_conf_acc'] is not None]
        avg_hc = np.mean(hc_accs) if hc_accs else None

        best = max(h_results, key=lambda r: r['accuracy'])
        worst = min(h_results, key=lambda r: r['accuracy'])

        hc_str = f"{avg_hc:.1%}" if avg_hc else "N/A"
        print(
            f"  +{h:>3}m  | {avg_acc:>7.1%} | {hc_str:>10} | "
            f"{best['symbol']} {best['accuracy']:.1%} | "
            f"{worst['symbol']} {worst['accuracy']:.1%}"
        )

    # Overall feature importance
    print("\n" + "=" * 70)
    print("OVERALL FEATURE IMPORTANCE (averaged across all tests)")
    print("=" * 70)
    feat_totals = {}
    for r in all_results:
        for name, imp in r['top_features']:
            feat_totals.setdefault(name, []).append(imp)
    feat_avg = sorted(
        [(name, np.mean(vals)) for name, vals in feat_totals.items()],
        key=lambda x: -x[1]
    )
    for name, avg_imp in feat_avg[:10]:
        bar = '#' * int(avg_imp * 200)
        print(f"  {name:>18}: {avg_imp:.4f} {bar}")

    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    for h in horizons:
        h_results = [r for r in all_results if r['horizon'] == h]
        if not h_results:
            continue
        avg_acc = np.mean([r['accuracy'] for r in h_results])
        avg_base = np.mean([r['base_rate'] for r in h_results])
        edge = avg_acc - 0.5
        print(f"  +{h:>3}m: avg_acc={avg_acc:.1%}, base_rate={avg_base:.1%}, edge={edge:+.1%}")
        if avg_acc < 0.50:
            print(f"         -> BELOW RANDOM. Model is anti-predictive. Use contrarian flip.")
        elif avg_acc < 0.52:
            print(f"         -> Marginal. Need better features or more data.")
        elif avg_acc < 0.55:
            print(f"         -> Decent. Room for improvement with feature engineering.")
        else:
            print(f"         -> Good predictive edge.")

    return all_results


if __name__ == '__main__':
    results = run_backtest()
