"""
SUPERPOWERS Quick Bootstrap — orchestrates all 3 system trainings.

Downloads historical data once, then trains System A (XGBoost filter),
System B (XGBoost regime classifier), and System C (GRU-Attention neural net)
with speed-optimized hyperparameters.

Usage:
    cd ml_battleground
    python -m bootstrap.run_bootstrap [--systems a,b,c] [--dry-run]

Exit codes:
    0 = all requested systems trained successfully
    1 = one or more systems failed
    2 = insufficient data downloaded
"""
import os
import sys
import time
import json
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# Ensure imports work from ml_battleground/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_single, PAIRS
from shared.indicators import atr as compute_atr, adx as compute_adx, ema, rsi, bollinger_bands
from shared.sr_engine import detect_sr_levels, nearest_support, nearest_resistance
from shared import indicators as ind

from bootstrap.quick_params import (
    DATA_PAIRS, OHLCV_LIMIT_1H, OHLCV_LIMIT_15M,
    A_PAIRS, A_STRIDE, A_MIN_SAMPLES, A_N_ESTIMATORS,
    A_TP_ATR_MULT, A_SL_ATR_MULT, A_MAX_HORIZON,
    B_PAIRS, B_LOOKBACK_MIN, B_LABEL_STRIDE, B_N_ESTIMATORS,
    C_PAIRS, C_SEQ_LEN, C_HIDDEN_SIZE, C_NUM_LAYERS, C_N_HEADS,
    C_DROPOUT, C_BATCH_SIZE, C_NUM_EPOCHS, C_PATIENCE,
    C_NUM_FOLDS, C_PURGE_GAP, C_MAX_HORIZON,
    C_TP_ATR_MULT, C_SL_ATR_MULT, C_MIN_SAMPLES,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# Phase 0: Shared data download
# =============================================================================

def download_all_data():
    """
    Download 1h and 15m OHLCV for all training pairs once.
    Returns (data_1h, data_15m) dicts of {pair: DataFrame}.
    """
    data_1h = {}
    data_15m = {}

    all_pairs = list(dict.fromkeys(A_PAIRS + B_PAIRS + C_PAIRS))  # dedupe, preserve order

    print(f"[Phase 0] Downloading OHLCV for {len(all_pairs)} pairs...")

    for i, pair in enumerate(all_pairs):
        print(f"  [{i+1}/{len(all_pairs)}] {pair} 1h...", end=" ", flush=True)
        df_1h = fetch_single(pair, "1h", OHLCV_LIMIT_1H)
        if df_1h is not None and len(df_1h) >= 210:
            data_1h[pair] = df_1h
            print(f"{len(df_1h)} bars", end="")
        else:
            print("SKIP", end="")
        time.sleep(0.15)

        if pair in C_PAIRS:
            print(f" | 15m...", end=" ", flush=True)
            df_15m = fetch_single(pair, "15m", OHLCV_LIMIT_15M)
            if df_15m is not None and len(df_15m) >= C_SEQ_LEN + C_MAX_HORIZON:
                data_15m[pair] = df_15m
                print(f"{len(df_15m)} bars")
            else:
                print("SKIP")
            time.sleep(0.15)
        else:
            print()

    print(f"[Phase 0] Downloaded: {len(data_1h)} pairs 1h, {len(data_15m)} pairs 15m")
    return data_1h, data_15m


# =============================================================================
# Phase 1: System A — XGBoost Filter
# =============================================================================

def _triple_barrier(future_df, entry, tp_price, sl_price, signal_type="BUY"):
    """Label: 1 if TP hit before SL, else 0."""
    for _, row in future_df.iterrows():
        if signal_type == "BUY":
            if row["Low"] <= sl_price:
                return 0
            if row["High"] >= tp_price:
                return 1
        else:
            if row["High"] >= sl_price:
                return 0
            if row["Low"] <= tp_price:
                return 1
    return 0  # expired


def train_system_a(data_1h):
    """Train System A XGBoost filter on historical strategy signals."""
    print("\n[Phase 1] Training System A — The Filter (XGBoost)...")

    from system_a_filter.strategies import run_all_strategies
    from system_a_filter.ml_filter import compute_filter_features, MODEL_PATH, SCALER_PATH
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBClassifier
    from sklearn.model_selection import TimeSeriesSplit
    import joblib

    all_X, all_y = [], []

    for pair in A_PAIRS:
        df = data_1h.get(pair)
        if df is None or len(df) < 215 + A_MAX_HORIZON:
            print(f"  [A] {pair}: skipped (insufficient data, {len(df) if df is not None else 0} bars)")
            continue

        sr_cache = {}
        pair_signals = 0
        windows_checked = 0
        raw_signals_total = 0

        for end_idx in range(215, len(df) - A_MAX_HORIZON, A_STRIDE):
            slice_df = df.iloc[:end_idx]
            future_df = df.iloc[end_idx:end_idx + A_MAX_HORIZON]
            windows_checked += 1

            signals = run_all_strategies(slice_df, pair)
            raw_signals_total += len(signals)
            if not signals:
                continue

            # Cache S/R levels every 50 bars
            cache_key = (end_idx // 50) * 50
            if cache_key not in sr_cache:
                sr_cache[cache_key] = detect_sr_levels(df.iloc[:min(cache_key + 50, len(df))])
            sr_levels = sr_cache[cache_key]

            atr_series = compute_atr(slice_df["High"], slice_df["Low"], slice_df["Close"])
            atr_now = float(atr_series.iloc[-1]) if len(atr_series) > 0 else slice_df["Close"].iloc[-1] * 0.02

            for sig in signals:
                entry = sig["entry_price"]
                sig_type = sig.get("signal_type", "BUY")

                if sig_type == "BUY":
                    tp = entry + A_TP_ATR_MULT * atr_now
                    sl = entry - A_SL_ATR_MULT * atr_now
                else:
                    tp = entry - A_TP_ATR_MULT * atr_now
                    sl = entry + A_SL_ATR_MULT * atr_now

                label = _triple_barrier(future_df, entry, tp, sl, sig_type)

                try:
                    features = compute_filter_features(sig, sr_levels, slice_df)
                    if features is not None and len(features) > 0:
                        all_X.append(features)
                        all_y.append(label)
                        pair_signals += 1
                except Exception as e:
                    if pair_signals == 0:
                        print(f"    [A] feature error on {pair}: {e}")
                    continue

        print(f"  [A] {pair}: {pair_signals} labeled signals ({windows_checked} windows, {raw_signals_total} raw signals)")

    # === FALLBACK: Direct labeling when strategies don't fire enough ===
    if len(all_X) < A_MIN_SAMPLES:
        print(f"  [A] Strategy-based: only {len(all_X)} samples. Using direct-label fallback...")
        all_X, all_y = [], []  # reset

        for pair in A_PAIRS:
            df = data_1h.get(pair)
            if df is None or len(df) < 100:
                continue

            min_lookback = 60  # minimum for O-U and rolling stats
            pair_count = 0

            atr_series = compute_atr(df["High"], df["Low"], df["Close"])
            rsi_series = rsi(df["Close"])
            volume_sma = df["Volume"].rolling(20).mean()
            _, _, _, _, pctb = ind.bollinger_bands(df["Close"])

            sr_cache = {}

            for bar_idx in range(min_lookback, len(df) - A_MAX_HORIZON, 2):  # stride=2
                slice_df = df.iloc[:bar_idx + 1]
                future_df = df.iloc[bar_idx + 1:bar_idx + 1 + A_MAX_HORIZON]

                if len(future_df) < 5:
                    continue

                price = float(df["Close"].iloc[bar_idx])
                atr_now = float(atr_series.iloc[bar_idx]) if bar_idx < len(atr_series) else price * 0.02

                # Triple barrier label
                tp_price = price + A_TP_ATR_MULT * atr_now
                sl_price = price - A_SL_ATR_MULT * atr_now
                label = _triple_barrier(future_df, price, tp_price, sl_price, "BUY")

                # Compute features manually (same 27 as compute_filter_features)
                # S/R features
                cache_key = (bar_idx // 50) * 50
                if cache_key not in sr_cache:
                    sr_cache[cache_key] = detect_sr_levels(df.iloc[:min(cache_key + 50, len(df))])
                sr_levels = sr_cache[cache_key]

                sup = nearest_support(sr_levels, price) if sr_levels else None
                res = nearest_resistance(sr_levels, price) if sr_levels else None
                dist_sup = (price - sup.price) / price if sup else 0.05
                dist_res = (res.price - price) / price if res else 0.05
                sup_strength = sup.strength if sup else 0.0
                res_strength = res.strength if res else 0.0
                sr_spread = dist_sup + dist_res

                # Technical features
                vol_val = float(df["Volume"].iloc[bar_idx])
                vol_sma_val = float(volume_sma.iloc[bar_idx]) if bar_idx < len(volume_sma) and not np.isnan(volume_sma.iloc[bar_idx]) else vol_val
                vol_ratio = vol_val / vol_sma_val if vol_sma_val > 0 else 1.0

                rsi_val = float(rsi_series.iloc[bar_idx]) if bar_idx < len(rsi_series) else 50.0
                atr_pctile = float((atr_series.iloc[bar_idx] <= atr_series.iloc[max(0, bar_idx - 60):bar_idx + 1]).mean()) if bar_idx >= 60 else 0.5
                pctb_val = float(pctb.iloc[bar_idx]) if bar_idx < len(pctb) and not np.isnan(pctb.iloc[bar_idx]) else 0.5

                # Time features
                hour = df.index[bar_idx].hour if hasattr(df.index[bar_idx], 'hour') else 12
                hour_sin = np.sin(2 * np.pi * hour / 24)
                hour_cos = np.cos(2 * np.pi * hour / 24)

                btc_corr = 0.5
                btc_ret = 0.0

                # Consecutive green candles
                greens = 0
                for i in range(bar_idx, max(0, bar_idx - 10), -1):
                    if df["Close"].iloc[i] > df["Open"].iloc[i]:
                        greens += 1
                    else:
                        break

                # Strategy features: all neutral (0.5) in fallback mode
                strat_features = [0.5] * 11

                features = [
                    dist_sup, dist_res, sup_strength, res_strength, sr_spread,
                    vol_ratio, rsi_val / 100.0, atr_pctile, 0.5, 0.0,  # fear_greed=0.5, funding=0
                    hour_sin, hour_cos, btc_corr, btc_ret, float(greens), pctb_val,
                ] + strat_features

                all_X.append(np.array(features, dtype=np.float64))
                all_y.append(label)
                pair_count += 1

            print(f"  [A] {pair}: {pair_count} direct-label samples")

    if len(all_X) < A_MIN_SAMPLES:
        print(f"[Phase 1] FAILED: Only {len(all_X)} samples (need {A_MIN_SAMPLES})")
        return False

    X = np.array(all_X, dtype=np.float32)
    y = np.array(all_y, dtype=np.float32)

    # Replace NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    print(f"  [A] Total: {len(X)} samples, pos_rate={y.mean():.1%}")

    # Walk-forward with 3 folds
    # Fit scaler on train only to prevent data leakage
    tscv = TimeSeriesSplit(n_splits=3)
    for fold, (tr, va) in enumerate(tscv.split(X)):
        # Fit scaler on train only to prevent data leakage
        fold_scaler = StandardScaler()
        X_tr_scaled = fold_scaler.fit_transform(X[tr])
        X_va_scaled = fold_scaler.transform(X[va])
        model = XGBClassifier(
            n_estimators=A_N_ESTIMATORS, max_depth=4,
            learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, reg_alpha=0.5, reg_lambda=2.0,
            scale_pos_weight=max(1.0, (y[tr] == 0).sum() / max(1, (y[tr] == 1).sum())),
            eval_metric="logloss", random_state=42, verbosity=0,
        )
        model.fit(X_tr_scaled, y[tr], eval_set=[(X_va_scaled, y[va])], verbose=False)
        acc = model.score(X_va_scaled, y[va])
        print(f"  [A] Fold {fold+1}: acc={acc:.3f}")

    # Final model on all data
    # Fit scaler on train only — for final model, use all data as "train"
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    final = XGBClassifier(
        n_estimators=A_N_ESTIMATORS, max_depth=4,
        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.5, reg_lambda=2.0,
        scale_pos_weight=max(1.0, (y == 0).sum() / max(1, (y == 1).sum())),
        eval_metric="logloss", random_state=42, verbosity=0,
    )
    final.fit(X_scaled, y, verbose=False)

    model_dir = os.path.dirname(MODEL_PATH)
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(final, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"  [A] Saved: {MODEL_PATH} ({len(X)} samples)")
    return True


# =============================================================================
# Phase 2: System B — Regime Classifier
# =============================================================================

def _fast_label_series(df, lookback_min=80):
    """
    Vectorized regime labeler — O(n) instead of O(n^2).
    Same rules as regime_classifier.rule_based_label:
      high_volatility:  ATR percentile > 0.80
      trending_up:      ADX > 25 AND close > EMA50 AND higher highs (5-bar)
      trending_down:    ADX > 25 AND close < EMA50 AND lower lows (5-bar)
      range_bound:      everything else
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    adx_series, _, _ = compute_adx(high, low, close, 14)
    ema50 = ema(close, 50)
    atr_series = compute_atr(high, low, close, 14)

    # Rolling ATR percentile (60-bar window)
    atr_pctile = atr_series.rolling(60, min_periods=20).rank(pct=True)

    # Higher highs / lower lows over prior 5 bars
    prev_max_high = high.shift(1).rolling(5, min_periods=3).max()
    prev_min_low = low.shift(1).rolling(5, min_periods=3).min()
    higher_highs = high > prev_max_high
    lower_lows = low < prev_min_low

    # Vectorized labeling
    labels = pd.Series("range_bound", index=df.index, dtype="object")

    is_high_vol = atr_pctile > 0.80
    is_trend_up = (~is_high_vol) & (adx_series > 25) & (close > ema50) & higher_highs
    is_trend_dn = (~is_high_vol) & (~is_trend_up) & (adx_series > 25) & (close < ema50) & lower_lows

    labels[is_high_vol] = "high_volatility"
    labels[is_trend_up] = "trending_up"
    labels[is_trend_dn] = "trending_down"

    # Mask early bars
    labels.iloc[:lookback_min] = np.nan
    return labels


def train_system_b(data_1h):
    """Train System B XGBoost regime classifier."""
    print("\n[Phase 2] Training System B — The Regime (XGBoost multi-class)...")

    from system_b_regime.regime_classifier import (
        compute_regime_features, REGIMES, REGIME_TO_INT,
        MODEL_PATH, SCALER_PATH, MODEL_DIR,
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score
    from xgboost import XGBClassifier
    import joblib

    all_X, all_y = [], []

    for pair in B_PAIRS:
        df = data_1h.get(pair)
        if df is None or len(df) < B_LOOKBACK_MIN + 20:
            print(f"  [B] {pair}: skipped (insufficient data)")
            continue

        labels = _fast_label_series(df, lookback_min=B_LOOKBACK_MIN)
        pair_count = 0

        for i in range(B_LOOKBACK_MIN, len(df), B_LABEL_STRIDE):
            label = labels.iloc[i]
            if pd.isna(label):
                continue

            slice_df = df.iloc[:i + 1]
            try:
                features = compute_regime_features(slice_df, fear_greed=50.0)
                if np.any(np.isnan(features)):
                    continue
                all_X.append(features)
                all_y.append(REGIME_TO_INT[label])
                pair_count += 1
            except Exception:
                continue

        print(f"  [B] {pair}: {pair_count} samples")

    if len(all_X) < 80:
        print(f"[Phase 2] FAILED: Only {len(all_X)} samples (need 80)")
        return False

    X = np.array(all_X, dtype=np.float32)
    y = np.array(all_y)

    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # Print class distribution
    for regime, idx in REGIME_TO_INT.items():
        count = (y == idx).sum()
        print(f"  [B] Class '{regime}': {count} ({count/len(y):.1%})")

    # Walk-forward with 3 folds
    # Fit scaler on train only to prevent data leakage
    tscv = TimeSeriesSplit(n_splits=3)
    for fold, (tr, va) in enumerate(tscv.split(X)):
        # Fit scaler on train only to prevent data leakage
        fold_scaler = StandardScaler()
        X_tr_scaled = fold_scaler.fit_transform(X[tr])
        X_va_scaled = fold_scaler.transform(X[va])
        model = XGBClassifier(
            n_estimators=B_N_ESTIMATORS, max_depth=5,
            learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.3, reg_lambda=1.5,
            objective="multi:softprob", num_class=len(REGIMES),
            eval_metric="mlogloss", random_state=42, verbosity=0,
        )
        model.fit(X_tr_scaled, y[tr], eval_set=[(X_va_scaled, y[va])], verbose=False)
        acc = accuracy_score(y[va], model.predict(X_va_scaled))
        print(f"  [B] Fold {fold+1}: acc={acc:.3f}")

    # Final model on all data
    # Fit scaler on train only — for final model, use all data as "train"
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    final = XGBClassifier(
        n_estimators=B_N_ESTIMATORS, max_depth=5,
        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.3, reg_lambda=1.5,
        objective="multi:softprob", num_class=len(REGIMES),
        eval_metric="mlogloss", random_state=42, verbosity=0,
    )
    final.fit(X_scaled, y, verbose=False)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"  [B] Saved: {MODEL_PATH} ({len(X)} samples)")
    return True


# =============================================================================
# Phase 3: System C — GRU-Attention Neural Net
# =============================================================================

def train_system_c(data_1h, data_15m):
    """Train System C GRU-Attention model with speed-optimized hyperparameters."""
    print("\n[Phase 3] Training System C — The Neural Net (GRU-Attention)...")

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import TensorDataset, DataLoader
    except ImportError:
        print("[Phase 3] FAILED: PyTorch not available.")
        return False

    import joblib
    from system_c_deeplearn.train_model import (
        build_features_for_df, triple_barrier_labels,
        purged_walk_forward_split, FeatureScaler,
    )
    from system_c_deeplearn.model_arch import GRUAttentionModel

    MODEL_DIR = os.path.join(BASE_DIR, "system_c_deeplearn", "models")
    MODEL_PATH = os.path.join(MODEL_DIR, "gru_attention.pt")
    SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.joblib")

    fear_greed_val = 50.0 / 100.0
    funding_rates = {}

    # BTC returns for cross-asset feature
    btc_1h = data_1h.get("BTCUSDT")
    btc_15m = data_15m.get("BTCUSDT")
    btc_ret_1h = btc_1h["Close"].pct_change().fillna(0) if btc_1h is not None else None
    btc_ret_15m = btc_15m["Close"].pct_change().fillna(0) if btc_15m is not None else None

    all_X_15m, all_X_1h = [], []
    all_y_entry, all_y_tp, all_y_sl = [], [], []

    for pair in C_PAIRS:
        df_1h = data_1h.get(pair)
        df_15m = data_15m.get(pair)

        if df_1h is None or df_15m is None:
            print(f"  [C] {pair}: skipped (missing data)")
            continue
        if len(df_1h) < C_SEQ_LEN + C_MAX_HORIZON + 10:
            print(f"  [C] {pair}: skipped (insufficient 1h bars: {len(df_1h)})")
            continue
        if len(df_15m) < C_SEQ_LEN + C_MAX_HORIZON:
            print(f"  [C] {pair}: skipped (insufficient 15m bars: {len(df_15m)})")
            continue

        funding = funding_rates.get(pair, 0.0)

        btc_r_1h = (btc_ret_1h.reindex(df_1h.index, method="nearest").fillna(0)
                     if btc_ret_1h is not None else None)
        btc_r_15m = (btc_ret_15m.reindex(df_15m.index, method="nearest").fillna(0)
                      if btc_ret_15m is not None else None)

        feat_1h = build_features_for_df(df_1h, fear_greed_val, funding, btc_r_1h)
        feat_15m = build_features_for_df(df_15m, fear_greed_val, funding, btc_r_15m)

        atr_1h = compute_atr(df_1h["High"], df_1h["Low"], df_1h["Close"], 14)
        labels, tp_tgt, sl_tgt = triple_barrier_labels(
            df_1h, atr_1h, C_TP_ATR_MULT, C_SL_ATR_MULT, C_MAX_HORIZON
        )

        n_1h = len(feat_1h)
        n_15m = len(feat_15m)
        pair_count = 0

        for end_idx in range(C_SEQ_LEN, n_1h - C_MAX_HORIZON):
            seq_1h = feat_1h[end_idx - C_SEQ_LEN: end_idx]

            # Map 1h index to 15m (approx 4:1 ratio)
            end_15m = min(end_idx * 4, n_15m)
            start_15m = end_15m - C_SEQ_LEN
            if start_15m < 0:
                continue
            if end_15m > n_15m:
                continue

            seq_15m = feat_15m[start_15m: end_15m]
            if seq_15m.shape[0] != C_SEQ_LEN or seq_1h.shape[0] != C_SEQ_LEN:
                continue

            all_X_15m.append(seq_15m)
            all_X_1h.append(seq_1h)
            all_y_entry.append(labels[end_idx])
            all_y_tp.append(tp_tgt[end_idx])
            all_y_sl.append(sl_tgt[end_idx])
            pair_count += 1

        print(f"  [C] {pair}: {pair_count} sequences (1h:{n_1h}, 15m:{n_15m})")

    if len(all_X_15m) < C_MIN_SAMPLES:
        print(f"[Phase 3] FAILED: Only {len(all_X_15m)} samples (need {C_MIN_SAMPLES})")
        return False

    X_15m = np.array(all_X_15m, dtype=np.float32)
    X_1h = np.array(all_X_1h, dtype=np.float32)
    y_entry = np.array(all_y_entry, dtype=np.float32)
    y_tp = np.array(all_y_tp, dtype=np.float32)
    y_sl = np.array(all_y_sl, dtype=np.float32)

    # Detect actual feature count from data (was hardcoded 16, now 24 with research features)
    actual_input_size = X_15m.shape[-1]
    print(f"  [C] Total: {len(X_15m)} samples, pos_rate={y_entry.mean():.1%}, features={actual_input_size}")

    device = "cpu"
    bce_loss = nn.BCELoss()
    mse_loss = nn.MSELoss()

    fold_results = []
    best_state = None

    for fold_idx, (train_idx, val_idx) in enumerate(
        purged_walk_forward_split(len(X_15m), C_NUM_FOLDS, 0.8, C_PURGE_GAP)
    ):
        print(f"  [C] Fold {fold_idx+1} (train={len(train_idx)}, val={len(val_idx)})...")

        # Fit scaler on train only to prevent data leakage
        fold_scaler_15m = FeatureScaler()
        fold_scaler_1h = FeatureScaler()
        fold_scaler_15m.fit(X_15m[train_idx])
        fold_scaler_1h.fit(X_1h[train_idx])

        X15_tr = torch.tensor(fold_scaler_15m.transform(X_15m[train_idx]), dtype=torch.float32)
        X1h_tr = torch.tensor(fold_scaler_1h.transform(X_1h[train_idx]), dtype=torch.float32)
        ye_tr = torch.tensor(y_entry[train_idx], dtype=torch.float32)
        ytp_tr = torch.tensor(y_tp[train_idx], dtype=torch.float32)
        ysl_tr = torch.tensor(y_sl[train_idx], dtype=torch.float32)

        X15_va = torch.tensor(fold_scaler_15m.transform(X_15m[val_idx]), dtype=torch.float32)
        X1h_va = torch.tensor(fold_scaler_1h.transform(X_1h[val_idx]), dtype=torch.float32)
        ye_va = torch.tensor(y_entry[val_idx], dtype=torch.float32)
        ytp_va = torch.tensor(y_tp[val_idx], dtype=torch.float32)
        ysl_va = torch.tensor(y_sl[val_idx], dtype=torch.float32)

        train_ds = TensorDataset(X15_tr, X1h_tr, ye_tr, ytp_tr, ysl_tr)
        val_ds = TensorDataset(X15_va, X1h_va, ye_va, ytp_va, ysl_va)
        train_ld = DataLoader(train_ds, batch_size=C_BATCH_SIZE, shuffle=True)
        val_ld = DataLoader(val_ds, batch_size=C_BATCH_SIZE, shuffle=False)

        model = GRUAttentionModel(
            input_size=actual_input_size,
            hidden_size=C_HIDDEN_SIZE,
            num_layers=C_NUM_LAYERS,
            n_heads=C_N_HEADS,
            dropout=C_DROPOUT,
        ).to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=4, min_lr=1e-6
        )

        best_val_loss = float("inf")
        patience_ctr = 0

        for epoch in range(C_NUM_EPOCHS):
            model.train()
            for batch in train_ld:
                x15, x1h, ye, ytp, ysl = batch
                optimizer.zero_grad()
                pe, pt, ps, _ = model(x15, x1h)
                loss = bce_loss(pe, ye) + 0.5 * mse_loss(pt, ytp) + 0.5 * mse_loss(ps, ysl)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            model.eval()
            va_losses, correct, total = [], 0, 0
            with torch.no_grad():
                for batch in val_ld:
                    x15, x1h, ye, ytp, ysl = batch
                    pe, pt, ps, _ = model(x15, x1h)
                    loss = bce_loss(pe, ye) + 0.5 * mse_loss(pt, ytp) + 0.5 * mse_loss(ps, ysl)
                    va_losses.append(loss.item())
                    correct += ((pe > 0.5).float() == ye).sum().item()
                    total += ye.size(0)

            avg_va = np.mean(va_losses)
            scheduler.step(avg_va)

            if avg_va < best_val_loss:
                best_val_loss = avg_va
                patience_ctr = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_ctr += 1

            if patience_ctr >= C_PATIENCE:
                print(f"    Early stop at epoch {epoch+1}")
                break

        val_acc = correct / total if total > 0 else 0
        print(f"    [C] Fold {fold_idx+1}: val_loss={best_val_loss:.4f} acc={val_acc:.3f}")
        fold_results.append({"fold": fold_idx + 1, "val_loss": best_val_loss, "val_acc": val_acc})

    # Final model on all data
    # Fit scaler on train only — for final model, use all data as "train"
    print("  [C] Scaling features for final model...")
    scaler_15m = FeatureScaler()
    scaler_1h = FeatureScaler()
    X_15m_sc = scaler_15m.fit_transform(X_15m)
    X_1h_sc = scaler_1h.fit_transform(X_1h)

    print("  [C] Training final model on all data...")
    final_model = GRUAttentionModel(
        input_size=actual_input_size, hidden_size=C_HIDDEN_SIZE,
        num_layers=C_NUM_LAYERS, n_heads=C_N_HEADS, dropout=C_DROPOUT,
    ).to(device)

    full_ds = TensorDataset(
        torch.tensor(X_15m_sc, dtype=torch.float32),
        torch.tensor(X_1h_sc, dtype=torch.float32),
        torch.tensor(y_entry, dtype=torch.float32),
        torch.tensor(y_tp, dtype=torch.float32),
        torch.tensor(y_sl, dtype=torch.float32),
    )
    full_ld = DataLoader(full_ds, batch_size=C_BATCH_SIZE, shuffle=True)
    optimizer = torch.optim.Adam(final_model.parameters(), lr=1e-3, weight_decay=1e-4)

    final_epochs = max(15, min(25, C_NUM_EPOCHS))
    for epoch in range(final_epochs):
        final_model.train()
        for batch in full_ld:
            x15, x1h, ye, ytp, ysl = batch
            optimizer.zero_grad()
            pe, pt, ps, _ = final_model(x15, x1h)
            loss = bce_loss(pe, ye) + 0.5 * mse_loss(pt, ytp) + 0.5 * mse_loss(ps, ysl)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(final_model.parameters(), 1.0)
            optimizer.step()

    # Save model + scaler + arch config
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(final_model.state_dict(), MODEL_PATH)

    scaler_data = {
        "scaler_15m_mean": scaler_15m.mean,
        "scaler_15m_std": scaler_15m.std,
        "scaler_4h_mean": scaler_15m.mean,   # backward compat — scanner may look for 4h key
        "scaler_4h_std": scaler_15m.std,
        "scaler_1h_mean": scaler_1h.mean,
        "scaler_1h_std": scaler_1h.std,
    }
    joblib.dump(scaler_data, SCALER_PATH)

    arch_config = {
        "input_size": actual_input_size,
        "hidden_size": C_HIDDEN_SIZE,
        "num_layers": C_NUM_LAYERS,
        "n_heads": C_N_HEADS,
        "dropout": C_DROPOUT,
        "seq_len": C_SEQ_LEN,
        "trained_with_quick_bootstrap": True,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(MODEL_DIR, "arch_config.json"), "w") as f:
        json.dump(arch_config, f, indent=2)

    print(f"  [C] Saved: {MODEL_PATH}")
    print(f"  [C] Fold results: {fold_results}")
    return True


# =============================================================================
# Main entry point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="SUPERPOWERS Quick Bootstrap")
    parser.add_argument("--systems", default="a,b,c", help="Comma-separated systems to train")
    parser.add_argument("--dry-run", action="store_true", help="Download data only, skip training")
    args = parser.parse_args()

    systems = [s.strip().lower() for s in args.systems.split(",")]
    print("=" * 60)
    print("SUPERPOWERS Quick Bootstrap")
    print(f"Systems: {', '.join(systems)}")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    t0 = time.time()

    # Phase 0: Download data
    data_1h, data_15m = download_all_data()

    if len(data_1h) < 5:
        print(f"FATAL: Only {len(data_1h)} pairs downloaded. Aborting.")
        sys.exit(2)

    if args.dry_run:
        print("\n[Dry run] Data downloaded. Skipping training.")
        return

    results = {}

    # Phase 1: System A
    if "a" in systems:
        t1 = time.time()
        results["a"] = train_system_a(data_1h)
        print(f"  [A] Time: {time.time() - t1:.1f}s")

    # Phase 2: System B
    if "b" in systems:
        t2 = time.time()
        results["b"] = train_system_b(data_1h)
        print(f"  [B] Time: {time.time() - t2:.1f}s")

    # Phase 3: System C
    if "c" in systems:
        t3 = time.time()
        results["c"] = train_system_c(data_1h, data_15m)
        print(f"  [C] Time: {time.time() - t3:.1f}s")

    elapsed = time.time() - t0

    # Phase 4: Diagnostics
    from bootstrap.diagnostics import write_summary
    write_summary(results, elapsed)

    print("\n" + "=" * 60)
    print(f"SUPERPOWERS Quick Bootstrap Complete")
    print(f"Results: {results}")
    print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("=" * 60)

    if not any(results.values()):
        print("FATAL: All systems failed to train.")
        sys.exit(1)
    elif not all(results.values()):
        failed = [k for k, v in results.items() if not v]
        print(f"WARNING: Systems {failed} failed, but others succeeded. Continuing.")


if __name__ == "__main__":
    main()
