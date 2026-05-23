"""
TA Ensemble ML Pilot -- Technical Analysis feature ensemble + LightGBM
Part of ml_battleground/pilots/

Concept: Train a LightGBM binary classifier on 20+ TA features across
multiple crypto pairs. The model learns which combinations of technical
indicators predict profitable 4h-ahead moves.

Modes:
  train   -- Fetch data, build features, train walk-forward, save model
  scan    -- Load model, fetch latest bars, predict, output picks

Usage:
  python ta_ensemble.py train
  python ta_ensemble.py scan
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

# ── Constants ────────────────────────────────────────────────────────────────

# Rotated Feb 26 2026: DOT → TAO (AI narrative momentum)
PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "TAOUSDT",
]
INTERVAL = "1h"
TRAIN_BARS = 2000
PREDICT_HORIZON = 4   # bars ahead
MIN_RETURN = 0.003    # 0.3% threshold for positive label
SCAN_CONFIDENCE = 0.60  # minimum probability to emit a pick

DATA_DIR = Path(__file__).resolve().parent / "data" / "ta_ensemble"
MODEL_PATH = DATA_DIR / "model.pkl"
SCALER_PATH = DATA_DIR / "scaler.pkl"
RESULTS_PATH = DATA_DIR / "results.json"
PICKS_PATH = DATA_DIR / "picks.json"

logger = logging.getLogger("ta_ensemble")


# ── Data fetching ────────────────────────────────────────────────────────────

def fetch_binance_ohlcv(pair: str, interval: str = "1h",
                        limit: int = 1500) -> pd.DataFrame:
    """Fetch OHLCV from Binance public REST API (no key required)."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": pair, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)

    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


# ── Feature engineering ──────────────────────────────────────────────────────

def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Classic Wilder RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - 100 / (1 + rs)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 22 TA features from OHLCV dataframe."""
    c = df["close"]
    h = df["high"]
    low = df["low"]
    v = df["volume"]

    feat = pd.DataFrame(index=df.index)

    # ── Momentum returns ──
    feat["ret_1h"] = c.pct_change(1)
    feat["ret_4h"] = c.pct_change(4)
    feat["ret_12h"] = c.pct_change(12)
    feat["ret_24h"] = c.pct_change(24)
    feat["ret_3d"] = c.pct_change(72)

    # ── RSI variants ──
    feat["rsi_14"] = _rsi(c, 14)
    feat["rsi_7"] = _rsi(c, 7)

    # StochRSI
    rsi14 = feat["rsi_14"]
    rsi_min = rsi14.rolling(14).min()
    rsi_max = rsi14.rolling(14).max()
    feat["stoch_rsi"] = (rsi14 - rsi_min) / (rsi_max - rsi_min + 1e-10)

    # ── MACD ──
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    feat["macd_hist"] = macd_line - macd_signal
    feat["macd_cross"] = np.sign(macd_line) - np.sign(macd_line.shift(1))

    # ── Bollinger Bands ──
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    feat["bb_width"] = (bb_upper - bb_lower) / (sma20 + 1e-10)
    feat["bb_percentb"] = (c - bb_lower) / (bb_upper - bb_lower + 1e-10)

    # ── Volume features ──
    vol_sma20 = v.rolling(20).mean()
    feat["vol_ratio"] = v / (vol_sma20 + 1e-10)
    feat["vol_momentum"] = v.pct_change(5)

    # ── Volatility ──
    tr = pd.concat([
        h - low,
        (h - c.shift(1)).abs(),
        (low - c.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    feat["atr_pct"] = atr14 / (c + 1e-10)
    feat["realized_vol"] = c.pct_change().rolling(20).std()

    # ── Trend features ──
    ema9 = c.ewm(span=9, adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    feat["ema_9_21_dist"] = (ema9 - ema21) / (c + 1e-10)
    feat["sma_50_200_dist"] = (sma50 - sma200) / (c + 1e-10)

    # ── ADX ──
    plus_dm = h.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_di = 100 * plus_dm.rolling(14).mean() / (atr14 + 1e-10)
    minus_di = 100 * minus_dm.rolling(14).mean() / (atr14 + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    feat["adx"] = dx.rolling(14).mean()

    # ── Mean reversion ──
    feat["zscore_sma20"] = (c - sma20) / (std20 + 1e-10)

    # ── OBV slope ──
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    feat["obv_slope"] = obv.diff(10) / (obv.rolling(10).mean().abs() + 1e-10)

    # ── Fractional differentiation d=0.4 — Lopez de Prado AFML Ch.5 ──
    # Makes price series stationary while preserving memory (unlike returns
    # which destroy all memory). d=0.4 retains ~60% correlation with original.
    try:
        from crypto_ml_edge.features.fracdiff import frac_diff_ffd
        feat["close_ffd"] = frac_diff_ffd(c, d=0.4)
    except ImportError:
        # Fallback: inline FFD implementation (pure numpy)
        weights = [1.0]
        k = 1
        while True:
            w = -weights[-1] * (0.4 - k + 1) / k
            if abs(w) < 1e-5:
                break
            weights.append(w)
            k += 1
        w_arr = np.array(weights[::-1])
        width = len(w_arr)
        ffd = pd.Series(index=c.index, dtype=float)
        vals = c.values
        for i in range(width - 1, len(vals)):
            ffd.iloc[i] = np.dot(w_arr, vals[i - width + 1: i + 1])
        feat["close_ffd"] = ffd

    return feat


# ── Labeling ─────────────────────────────────────────────────────────────────

def make_labels(df: pd.DataFrame, horizon: int = PREDICT_HORIZON,
                min_ret: float = MIN_RETURN) -> pd.Series:
    """Binary label: 1 if close[t+horizon] > close[t] * (1 + min_ret)."""
    future_ret = df["close"].shift(-horizon) / df["close"] - 1
    return (future_ret > min_ret).astype(int)


# ── Training ─────────────────────────────────────────────────────────────────

def train(pairs: list = None):
    """Walk-forward train across multiple pairs, save model + results."""
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, roc_auc_score
    import joblib

    # Try LightGBM, fall back to sklearn GBM
    try:
        import lightgbm as lgb
        USE_LGB = True
        logger.info("Using LightGBM backend")
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        USE_LGB = False
        logger.warning("LightGBM not available, falling back to sklearn GradientBoostingClassifier")

    if pairs is None:
        pairs = PAIRS

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Collect training data from all pairs ──
    all_X, all_y = [], []
    for pair in pairs:
        logger.info("Fetching %s ...", pair)
        try:
            df = fetch_binance_ohlcv(pair, INTERVAL, TRAIN_BARS)
            features = compute_features(df)
            labels = make_labels(df)

            combined = pd.concat(
                [features, labels.rename("label")], axis=1
            ).dropna()
            X = combined.drop("label", axis=1)
            y = combined["label"]

            all_X.append(X)
            all_y.append(y)
            logger.info("  %s: %d samples, %.1f%% positive",
                        pair, len(y), y.mean() * 100)
            time.sleep(0.5)  # respect rate limits
        except Exception as e:
            logger.warning("  %s failed: %s", pair, e)

    if not all_X:
        logger.error("No data collected -- cannot train")
        return {}

    X = pd.concat(all_X)
    y = pd.concat(all_y)
    logger.info("Total dataset: %d samples, %.1f%% positive",
                len(y), y.mean() * 100)

    # ── Walk-forward validation (5-fold TimeSeriesSplit) ──
    tscv = TimeSeriesSplit(n_splits=5)
    fold_results = []

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        if USE_LGB:
            model = lgb.LGBMClassifier(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                verbose=-1,
            )
            model.fit(
                X_train_s, y_train,
                eval_set=[(X_test_s, y_test)],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )
        else:
            model = GradientBoostingClassifier(
                n_estimators=200, learning_rate=0.05, max_depth=5,
            )
            model.fit(X_train_s, y_train)

        proba = model.predict_proba(X_test_s)[:, 1]
        preds = (proba > 0.5).astype(int)
        acc = accuracy_score(y_test, preds)
        try:
            auc = roc_auc_score(y_test, proba)
        except ValueError:
            auc = 0.5

        fold_results.append({
            "fold": fold_idx,
            "accuracy": round(acc, 4),
            "auc": round(auc, 4),
            "samples": len(y_test),
        })
        logger.info("  Fold %d: acc=%.3f  auc=%.3f  (%d samples)",
                     fold_idx, acc, auc, len(y_test))

    # ── Final model trained on all data ──
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if USE_LGB:
        final_model = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            verbose=-1,
        )
        final_model.fit(X_scaled, y)
    else:
        final_model = GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=5,
        )
        final_model.fit(X_scaled, y)

    joblib.dump(final_model, str(MODEL_PATH))
    joblib.dump(scaler, str(SCALER_PATH))
    logger.info("Model saved to %s", MODEL_PATH)
    logger.info("Scaler saved to %s", SCALER_PATH)

    # ── Feature importance ──
    importances = dict(zip(X.columns, final_model.feature_importances_))
    top_features = sorted(importances.items(), key=lambda x: x[1],
                          reverse=True)[:10]

    # ── Persist results ──
    results = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "pairs": pairs,
        "total_samples": len(y),
        "positive_rate": round(float(y.mean()), 4),
        "folds": fold_results,
        "avg_accuracy": round(
            float(np.mean([f["accuracy"] for f in fold_results])), 4),
        "avg_auc": round(
            float(np.mean([f["auc"] for f in fold_results])), 4),
        "top_features": {k: round(float(v), 4) for k, v in top_features},
        "feature_count": len(X.columns),
        "backend": "lightgbm" if USE_LGB else "sklearn_gbm",
    }

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    logger.info("Results saved to %s", RESULTS_PATH)
    logger.info("Avg accuracy: %.3f | Avg AUC: %.3f",
                results["avg_accuracy"], results["avg_auc"])

    return results


# ── Scanner ──────────────────────────────────────────────────────────────────

def scan(pairs: list = None):
    """Load trained model, fetch latest bars, generate predictions."""
    import joblib

    if not MODEL_PATH.exists():
        logger.error("No trained model found at %s. Run 'train' first.",
                      MODEL_PATH)
        return []

    model = joblib.load(str(MODEL_PATH))
    scaler = joblib.load(str(SCALER_PATH))
    feature_names = list(scaler.feature_names_in_)

    if pairs is None:
        pairs = PAIRS

    picks = []
    for pair in pairs:
        try:
            df = fetch_binance_ohlcv(pair, INTERVAL, 250)
            features = compute_features(df)
            latest = features.iloc[[-1]].copy()

            # Ensure columns match training set exactly
            for col in feature_names:
                if col not in latest.columns:
                    latest[col] = 0.0
            latest = latest[feature_names]

            # Fill any remaining NaN from short rolling windows
            latest = latest.fillna(0.0)

            X_scaled = scaler.transform(latest)
            proba = float(model.predict_proba(X_scaled)[0, 1])

            if proba >= SCAN_CONFIDENCE:
                price = float(df["close"].iloc[-1])
                atr = float(
                    (df["high"] - df["low"]).rolling(14).mean().iloc[-1]
                )

                pick = {
                    "pair": pair,
                    "direction": "long",
                    "confidence": round(proba, 3),
                    "entry_price": round(price, 6),
                    "tp_price": round(price + 2.0 * atr, 6),
                    "sl_price": round(price - 1.5 * atr, 6),
                    "rr_ratio": round(2.0 / 1.5, 2),
                    "signal_time": datetime.now(timezone.utc).isoformat(),
                    "strategy": "ta_ensemble",
                    "features": {
                        "rsi_14": round(
                            float(features["rsi_14"].iloc[-1]), 2),
                        "macd_hist": round(
                            float(features["macd_hist"].iloc[-1]), 6),
                        "bb_percentb": round(
                            float(features["bb_percentb"].iloc[-1]), 3),
                        "adx": round(
                            float(features["adx"].iloc[-1]), 2),
                        "vol_ratio": round(
                            float(features["vol_ratio"].iloc[-1]), 2),
                    },
                }
                picks.append(pick)
                logger.info("SIGNAL: %s long @ %.2f (conf=%.3f)",
                            pair, price, proba)
            else:
                logger.info("  %s: prob=%.3f (below %.2f threshold)",
                            pair, proba, SCAN_CONFIDENCE)

            time.sleep(0.3)  # respect rate limits
        except Exception as e:
            logger.warning("%s scan failed: %s", pair, e)

    # ── Persist picks ──
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "ta_ensemble",
        "total_pairs_scanned": len(pairs),
        "picks": picks,
    }
    PICKS_PATH.write_text(json.dumps(output, indent=2))

    logger.info("Scan complete: %d signals from %d pairs",
                len(picks), len(pairs))
    return picks


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if mode == "train":
        results = train()
        print(json.dumps(results, indent=2))
    elif mode == "scan":
        picks = scan()
        print(json.dumps(picks, indent=2))
    else:
        print(f"Usage: {sys.argv[0]} [train|scan]")
        sys.exit(1)
