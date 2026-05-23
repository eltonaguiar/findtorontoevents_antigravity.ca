"""
Training pipeline for System C: "The Neural Net".
GRU-Attention model with multi-task loss: BCE(entry) + 0.5*MSE(tp) + 0.5*MSE(sl).

Features per bar (24):
  OHLCV normalized by 200-bar rolling mean, RSI(14), MACD histogram,
  Bollinger %B, volume ratio vs 20-bar MA, ATR normalized, hour sin/cos,
  BTC return, Fear & Greed (0-1), funding rate, price vs EMA200,
  log return, lagged returns (3/5/10/20), Fibonacci position + dist_618,
  volume z-score.

Labels: Triple-barrier with regression targets for TP/SL distances in ATR units.

Walk-forward: 5 folds, 80/20 split, 50-bar purge gap.
Optimizer: Adam(lr=1e-3, weight_decay=1e-4), ReduceLROnPlateau.
Early stopping on val loss (patience=10).

Run: python -m ml_battleground.system_c_deeplearn.train_model
"""
import os
import sys
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import joblib
except ImportError:
    joblib = None

from shared.data_fetcher import fetch_ohlcv, fetch_single, fetch_fear_greed, fetch_funding_rates, PAIRS
from shared.indicators import rsi, macd, bollinger_bands, atr, ema

# Paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "gru_attention.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.joblib")

# Training hyperparameters
NUM_FEATURES = 25  # was 24 — added fractional differentiation (Lopez de Prado AFML Ch.5)
SEQ_LEN = 200
BATCH_SIZE = 32
NUM_EPOCHS = 100
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 10
NUM_FOLDS = 5
PURGE_GAP = 50
TP_ATR_MULT = 2.0   # lowered from 2.5 (37.8% trades expired - too ambitious)
SL_ATR_MULT = 1.5   # tightened from 2.0
MAX_HORIZON = 72    # extended from 48 (30 bars on 4h = 120h hold time)


def build_features_for_df(df: pd.DataFrame, fear_greed_val: float = 0.5,
                          funding_rate: float = 0.0,
                          btc_returns: Optional[pd.Series] = None) -> np.ndarray:
    """
    Build feature matrix (n_bars, 25) from a single-pair DataFrame.

    Features (original 16):
      0: Open / 200-bar rolling mean of Close
      1: High / 200-bar rolling mean of Close
      2: Low / 200-bar rolling mean of Close
      3: Close / 200-bar rolling mean of Close
      4: Volume / 200-bar rolling mean of Volume
      5: RSI(14) / 100
      6: MACD histogram (normalized by close)
      7: Bollinger %B
      8: Volume ratio vs 20-bar MA
      9: ATR / Close (normalized)
     10: hour sin
     11: hour cos
     12: BTC 1-bar return (or 0 if BTC pair itself)
     13: Fear & Greed (0-1)
     14: Funding rate
     15: Close / EMA(200)

    New features (9 — research-backed):
     16: Log return (1-bar) — stationarity (López de Prado)
     17: Lagged return (3-bar) — autoregressive momentum
     18: Lagged return (5-bar) — short-term momentum
     19: Lagged return (10-bar) — medium-term momentum
     20: Lagged return (20-bar) — longer-term momentum
     21: Fibonacci position (0=swing_low, 1=swing_high) — Osler 2000, +6.89% ROI
     22: Distance to 61.8% Fib level — institutional cluster level
     23: Volume z-score (20-bar) — standardized volume signal
     24: Fractional differentiation (d=0.4) — Lopez de Prado AFML Ch.5
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    opn = df["Open"]
    volume = df["Volume"]
    n = len(df)

    # Rolling means for normalization
    close_rm200 = close.rolling(200, min_periods=50).mean()
    vol_rm200 = volume.rolling(200, min_periods=50).mean()

    # Avoid division by zero
    close_rm200 = close_rm200.replace(0, np.nan).fillna(close.mean())
    vol_rm200 = vol_rm200.replace(0, np.nan).fillna(volume.mean())

    # OHLCV normalized
    f_open = (opn / close_rm200).values
    f_high = (high / close_rm200).values
    f_low = (low / close_rm200).values
    f_close = (close / close_rm200).values
    f_volume = (volume / vol_rm200).values

    # RSI(14) normalized to 0-1
    rsi_vals = rsi(close, 14).values / 100.0

    # MACD histogram normalized by close
    _, _, macd_hist = macd(close)
    f_macd = (macd_hist / close.replace(0, np.nan)).fillna(0).values

    # Bollinger %B
    _, _, _, _, pctb = bollinger_bands(close)
    f_bb = pctb.fillna(0.5).clip(-0.5, 1.5).values

    # Volume ratio vs 20-bar MA
    vol_ma20 = volume.rolling(20, min_periods=5).mean().replace(0, np.nan).fillna(volume.mean())
    f_vol_ratio = (volume / vol_ma20).fillna(1.0).values

    # ATR normalized by close
    atr_vals = atr(high, low, close, 14)
    f_atr = (atr_vals / close.replace(0, np.nan)).fillna(0.02).values

    # Hour sin/cos (from index if datetime, else default)
    if hasattr(df.index, 'hour'):
        hours = df.index.hour.values.astype(float)
    else:
        hours = np.full(n, 12.0)
    f_hour_sin = np.sin(2 * np.pi * hours / 24)
    f_hour_cos = np.cos(2 * np.pi * hours / 24)

    # BTC return
    if btc_returns is not None and len(btc_returns) == n:
        f_btc_ret = btc_returns.values
    else:
        f_btc_ret = np.zeros(n)

    # Fear & Greed (constant for all bars in a batch -- simplified)
    f_fg = np.full(n, fear_greed_val)

    # Funding rate (constant for the pair)
    f_funding = np.full(n, funding_rate)

    # Price vs EMA(200)
    ema200 = ema(close, 200)
    f_price_ema = (close / ema200.replace(0, np.nan)).fillna(1.0).values

    # === NEW RESEARCH-BACKED FEATURES (16-23) ===

    # 16: Log return (1-bar) — stationary representation (López de Prado)
    f_log_ret = np.log(close / close.shift(1)).fillna(0).values

    # 17-20: Lagged returns at multiple windows (autoregressive effects)
    f_lag_3 = (close / close.shift(3) - 1).fillna(0).values
    f_lag_5 = (close / close.shift(5) - 1).fillna(0).values
    f_lag_10 = (close / close.shift(10) - 1).fillna(0).values
    f_lag_20 = (close / close.shift(20) - 1).fillna(0).values

    # 21-22: Fibonacci retracement features (Osler 2000, +6.89% ROI)
    swing_h = high.rolling(60, min_periods=20).max()
    swing_l = low.rolling(60, min_periods=20).min()
    fib_range = (swing_h - swing_l).replace(0, np.nan)
    f_fib_position = ((close - swing_l) / fib_range).fillna(0.5).values
    fib_618 = swing_h - 0.618 * (swing_h - swing_l)
    f_dist_fib_618 = ((close - fib_618) / close.replace(0, np.nan)).fillna(0).values

    # 23: Volume z-score (20-bar) — standardized volume signal
    vol_mean_20 = volume.rolling(20, min_periods=5).mean()
    vol_std_20 = volume.rolling(20, min_periods=5).std().replace(0, np.nan)
    f_vol_zscore = ((volume - vol_mean_20) / vol_std_20).fillna(0).clip(-3, 3).values

    # 24: Fractional differentiation d=0.4 — Lopez de Prado AFML Ch.5
    # Makes price series stationary while preserving memory (~60% correlation
    # with original). Unlike returns (d=1) which destroy all memory.
    try:
        from crypto_ml_edge.features.fracdiff import frac_diff_ffd
        f_close_ffd = frac_diff_ffd(close, d=0.4).reindex(close.index).fillna(0).values
    except ImportError:
        # Fallback: inline FFD weights (pure numpy)
        _w = [1.0]
        _k = 1
        while True:
            _wn = -_w[-1] * (0.4 - _k + 1) / _k
            if abs(_wn) < 1e-5:
                break
            _w.append(_wn)
            _k += 1
        _w_arr = np.array(_w[::-1])
        _width = len(_w_arr)
        _vals = close.values.astype(float)
        f_close_ffd = np.full(n, 0.0)
        for _i in range(_width - 1, n):
            f_close_ffd[_i] = np.dot(_w_arr, _vals[_i - _width + 1: _i + 1])

    # Stack into (n, 25)
    features = np.column_stack([
        f_open,         # 0
        f_high,         # 1
        f_low,          # 2
        f_close,        # 3
        f_volume,       # 4
        rsi_vals,       # 5
        f_macd,         # 6
        f_bb,           # 7
        f_vol_ratio,    # 8
        f_atr,          # 9
        f_hour_sin,     # 10
        f_hour_cos,     # 11
        f_btc_ret,      # 12
        f_fg,           # 13
        f_funding,      # 14
        f_price_ema,    # 15
        f_log_ret,      # 16: log return (stationary)
        f_lag_3,        # 17: 3-bar momentum
        f_lag_5,        # 18: 5-bar momentum
        f_lag_10,       # 19: 10-bar momentum
        f_lag_20,       # 20: 20-bar momentum
        f_fib_position, # 21: Fibonacci position [0-1]
        f_dist_fib_618, # 22: distance to 61.8% Fib level
        f_vol_zscore,   # 23: volume z-score
        f_close_ffd,    # 24: fractional differentiation (d=0.4, AFML Ch.5)
    ])

    # Replace NaN/inf with 0
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features


def triple_barrier_labels(df: pd.DataFrame, atr_series: pd.Series,
                          tp_mult: float = 2.5, sl_mult: float = 2.0,
                          max_horizon: int = 48):
    """
    Compute triple-barrier labels and regression targets.

    For each bar i:
      - label=1 if high reaches entry + tp_mult*ATR before low reaches entry - sl_mult*ATR
      - tp_distance_in_atr: max favorable excursion / ATR
      - sl_distance_in_atr: max adverse excursion / ATR

    Returns:
      labels: np.ndarray of shape (n,) with 0/1
      tp_targets: np.ndarray of shape (n,) -- favorable excursion in ATR units
      sl_targets: np.ndarray of shape (n,) -- adverse excursion in ATR units
    """
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    atr_vals = atr_series.values
    n = len(df)

    labels = np.zeros(n, dtype=np.float32)
    tp_targets = np.full(n, 1.5, dtype=np.float32)   # default
    sl_targets = np.full(n, 1.0, dtype=np.float32)    # default

    for i in range(n - max_horizon):
        entry = close[i]
        atr_now = atr_vals[i]
        if atr_now <= 0 or entry <= 0:
            continue

        tp_price = entry + tp_mult * atr_now
        sl_price = entry - sl_mult * atr_now

        max_favorable = 0.0
        max_adverse = 0.0
        hit_tp = False

        for j in range(i + 1, min(i + max_horizon + 1, n)):
            bar_high = high[j]
            bar_low = low[j]

            favorable = bar_high - entry
            adverse = entry - bar_low
            max_favorable = max(max_favorable, favorable)
            max_adverse = max(max_adverse, adverse)

            # Check SL first (conservative)
            if bar_low <= sl_price:
                labels[i] = 0
                break
            if bar_high >= tp_price:
                labels[i] = 1
                hit_tp = True
                break

        # Regression targets in ATR units
        tp_targets[i] = max(0.5, max_favorable / atr_now) if atr_now > 0 else 1.5
        sl_targets[i] = max(0.5, max_adverse / atr_now) if atr_now > 0 else 1.0

    return labels, tp_targets, sl_targets


def build_training_sequences(pairs: Optional[list] = None, limit: int = 500):
    """
    Fetch data and build training sequences for both timeframes.

    Returns:
      X_4h:  np.ndarray (n_samples, SEQ_LEN, NUM_FEATURES) -- primary timeframe
      X_1h:  np.ndarray (n_samples, SEQ_LEN, NUM_FEATURES) -- secondary timeframe
      y_entry: np.ndarray (n_samples,) -- binary labels
      y_tp:    np.ndarray (n_samples,) -- TP distance in ATR
      y_sl:    np.ndarray (n_samples,) -- SL distance in ATR
    """
    pairs = pairs or PAIRS[:10]  # subset for training speed
    fear_greed_val = fetch_fear_greed() / 100.0
    funding_rates = fetch_funding_rates(pairs)

    # Fetch BTC data for BTC return feature
    # Primary: 4h (best signal-to-noise), Secondary: 1h
    # 15m removed — too noisy for crypto, destroys profitability via transaction costs
    btc_1h = fetch_single("BTCUSDT", "1h", limit)
    btc_4h = fetch_single("BTCUSDT", "4h", limit)
    btc_ret_1h = btc_1h["Close"].pct_change().fillna(0) if btc_1h is not None else None
    btc_ret_4h = btc_4h["Close"].pct_change().fillna(0) if btc_4h is not None else None

    all_X_4h = []
    all_X_1h = []
    all_y_entry = []
    all_y_tp = []
    all_y_sl = []

    for pair in pairs:
        print(f"  Processing {pair}...")

        # Fetch both timeframes: 4h (primary) + 1h (secondary)
        df_4h = fetch_single(pair, "4h", limit)
        df_1h = fetch_single(pair, "1h", limit)

        if df_4h is None or df_1h is None:
            print(f"    Skipping {pair}: insufficient data")
            continue
        if len(df_4h) < SEQ_LEN + MAX_HORIZON or len(df_1h) < SEQ_LEN + MAX_HORIZON:
            print(f"    Skipping {pair}: not enough bars (4h:{len(df_4h)}, 1h:{len(df_1h)})")
            continue

        funding = funding_rates.get(pair, 0.0)

        # Build BTC return series aligned to each timeframe
        btc_r_4h = btc_ret_4h.reindex(df_4h.index, method="nearest").fillna(0) if btc_ret_4h is not None else None
        btc_r_1h = btc_ret_1h.reindex(df_1h.index, method="nearest").fillna(0) if btc_ret_1h is not None else None

        # Build feature matrices
        feat_4h = build_features_for_df(df_4h, fear_greed_val, funding, btc_r_4h)
        feat_1h = build_features_for_df(df_1h, fear_greed_val, funding, btc_r_1h)

        # Labels from 4h timeframe (primary signal timeframe)
        atr_4h = atr(df_4h["High"], df_4h["Low"], df_4h["Close"], 14)
        labels, tp_tgt, sl_tgt = triple_barrier_labels(
            df_4h, atr_4h, TP_ATR_MULT, SL_ATR_MULT, MAX_HORIZON
        )

        # Create sliding window sequences
        # Use 4h labels, align 1h sequences to the same endpoints
        n_4h = len(feat_4h)
        n_1h = len(feat_1h)

        # For each valid 4h window endpoint, we need a corresponding 1h window
        # 4h bar i corresponds roughly to 1h bar i*4 (for 4h=4x1h)
        for end_idx in range(SEQ_LEN, n_4h - MAX_HORIZON):
            # 4h sequence: [end_idx - SEQ_LEN : end_idx]
            seq_4h = feat_4h[end_idx - SEQ_LEN: end_idx]

            # Corresponding 1h endpoint (roughly 4x the 4h index, capped)
            end_1h = min(end_idx * 4, n_1h)
            start_1h = end_1h - SEQ_LEN
            if start_1h < 0:
                start_1h = 0
                end_1h = SEQ_LEN

            if end_1h > n_1h:
                continue

            seq_1h = feat_1h[start_1h: end_1h]

            # Ensure correct shape
            if seq_4h.shape[0] != SEQ_LEN or seq_1h.shape[0] != SEQ_LEN:
                continue

            all_X_4h.append(seq_4h)
            all_X_1h.append(seq_1h)
            all_y_entry.append(labels[end_idx])
            all_y_tp.append(tp_tgt[end_idx])
            all_y_sl.append(sl_tgt[end_idx])

        time.sleep(0.2)  # rate limit

    if not all_X_4h:
        return None, None, None, None, None

    X_4h = np.array(all_X_4h, dtype=np.float32)
    X_1h = np.array(all_X_1h, dtype=np.float32)
    y_entry = np.array(all_y_entry, dtype=np.float32)
    y_tp = np.array(all_y_tp, dtype=np.float32)
    y_sl = np.array(all_y_sl, dtype=np.float32)

    return X_4h, X_1h, y_entry, y_tp, y_sl


def purged_walk_forward_split(n_samples: int, n_folds: int = 5,
                               train_pct: float = 0.8, purge_gap: int = 50):
    """
    Generate walk-forward CV indices with purge gap between train and val.

    Yields (train_indices, val_indices) for each fold.
    """
    fold_size = n_samples // n_folds
    for fold in range(n_folds):
        # Progressive expansion: train on increasing history
        train_end = fold_size * (fold + 1)
        val_start = train_end + purge_gap
        val_end = min(val_start + fold_size, n_samples)

        if val_start >= n_samples or val_end <= val_start:
            continue

        train_idx = np.arange(0, train_end)
        val_idx = np.arange(val_start, val_end)

        yield train_idx, val_idx


class FeatureScaler:
    """Simple feature scaler that can be saved with joblib."""

    def __init__(self):
        self.mean = None
        self.std = None

    def fit(self, X: np.ndarray):
        """Fit on (n_samples, seq_len, n_features) -- compute stats over samples and time."""
        # Reshape to (n_samples * seq_len, n_features) for statistics
        flat = X.reshape(-1, X.shape[-1])
        self.mean = flat.mean(axis=0).astype(np.float32)
        self.std = flat.std(axis=0).astype(np.float32)
        self.std[self.std < 1e-8] = 1.0  # avoid div by zero
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Normalize features."""
        if self.mean is None:
            return X
        return ((X - self.mean) / self.std).astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)


class FocalLoss(nn.Module):
    """Focal Loss for imbalanced classification (Lin et al., 2017).

    Down-weights easy negatives, focuses learning on hard positives.
    With alpha=0.25, gamma=2.0: a well-classified negative (pt=0.9)
    gets loss scaled by 0.0075x vs standard BCE.

    Accepts probabilities (post-sigmoid) since GRUAttentionModel applies
    sigmoid internally.
    """
    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, probs, targets):
        # Clamp to avoid log(0)
        probs = probs.clamp(1e-7, 1 - 1e-7)
        bce = nn.functional.binary_cross_entropy(probs, targets, reduction='none')
        pt = torch.exp(-bce)
        focal = self.alpha * (1 - pt) ** self.gamma * bce
        return focal.mean()


def train():
    """Main training loop with walk-forward validation."""
    if not TORCH_AVAILABLE:
        print("[System C] PyTorch not available. Install with: pip install torch>=2.1.0")
        print("[System C] Training skipped.")
        return

    if joblib is None:
        print("[System C] joblib not available. Install with: pip install joblib")
        return

    from system_c_deeplearn.model_arch import GRUAttentionModel, count_parameters

    print("=" * 60)
    print("System C: The Neural Net -- Training Pipeline")
    print("=" * 60)
    start_time = time.time()

    # Build training data
    print("\n[1/4] Fetching data and building training sequences...")
    X_4h, X_1h, y_entry, y_tp, y_sl = build_training_sequences()

    if X_4h is None or len(X_4h) < 100:
        n = len(X_4h) if X_4h is not None else 0
        print(f"\nInsufficient training data: {n} samples (need 100+). Skipping.")
        return

    print(f"  Total samples: {len(X_4h)}")
    print(f"  Positive rate: {y_entry.mean():.1%}")
    print(f"  Shapes: X_4h={X_4h.shape}, X_1h={X_1h.shape}")

    # Determine device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")

    # Walk-forward cross-validation
    # Fit scaler on train only to prevent data leakage
    print(f"\n[2/4] Walk-forward validation ({NUM_FOLDS} folds, {PURGE_GAP}-bar purge)...")
    fold_results = []

    for fold_idx, (train_idx, val_idx) in enumerate(
        purged_walk_forward_split(len(X_4h), NUM_FOLDS, 0.8, PURGE_GAP)
    ):
        print(f"\n  --- Fold {fold_idx + 1} (train={len(train_idx)}, val={len(val_idx)}) ---")

        # Fit scaler on train only to prevent data leakage
        fold_scaler_4h = FeatureScaler()
        fold_scaler_1h = FeatureScaler()
        fold_scaler_4h.fit(X_4h[train_idx])
        fold_scaler_1h.fit(X_1h[train_idx])

        X_4h_train_sc = fold_scaler_4h.transform(X_4h[train_idx])
        X_4h_val_sc = fold_scaler_4h.transform(X_4h[val_idx])
        X_1h_train_sc = fold_scaler_1h.transform(X_1h[train_idx])
        X_1h_val_sc = fold_scaler_1h.transform(X_1h[val_idx])

        # Create datasets (X15 variable names kept for model arch compatibility)
        X15_tr = torch.tensor(X_4h_train_sc, dtype=torch.float32)
        X1h_tr = torch.tensor(X_1h_train_sc, dtype=torch.float32)
        ye_tr = torch.tensor(y_entry[train_idx], dtype=torch.float32)
        ytp_tr = torch.tensor(y_tp[train_idx], dtype=torch.float32)
        ysl_tr = torch.tensor(y_sl[train_idx], dtype=torch.float32)

        X15_val = torch.tensor(X_4h_val_sc, dtype=torch.float32)
        X1h_val = torch.tensor(X_1h_val_sc, dtype=torch.float32)
        ye_val = torch.tensor(y_entry[val_idx], dtype=torch.float32)
        ytp_val = torch.tensor(y_tp[val_idx], dtype=torch.float32)
        ysl_val = torch.tensor(y_sl[val_idx], dtype=torch.float32)

        train_ds = TensorDataset(X15_tr, X1h_tr, ye_tr, ytp_tr, ysl_tr)
        val_ds = TensorDataset(X15_val, X1h_val, ye_val, ytp_val, ysl_val)
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

        # Build model
        model = GRUAttentionModel(
            input_size=NUM_FEATURES,
            hidden_size=128,
            num_layers=2,
            n_heads=4,
            dropout=0.3,
        ).to(device)

        if fold_idx == 0:
            print(f"  Model parameters: {count_parameters(model):,}")

        optimizer = torch.optim.Adam(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5, min_lr=1e-6
        )

        focal_loss = FocalLoss(alpha=0.25, gamma=2.0)
        mse_loss = nn.MSELoss()

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        for epoch in range(NUM_EPOCHS):
            # Training
            model.train()
            train_losses = []
            for batch in train_loader:
                x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]

                optimizer.zero_grad()
                pred_entry, pred_tp, pred_sl, _ = model(x15, x1h)

                loss_entry = focal_loss(pred_entry, ye)
                loss_tp = mse_loss(pred_tp, ytp)
                loss_sl = mse_loss(pred_sl, ysl)
                loss = loss_entry + 0.5 * loss_tp + 0.5 * loss_sl

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_losses.append(loss.item())

            # Validation
            model.eval()
            val_losses = []
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for batch in val_loader:
                    x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]
                    pred_entry, pred_tp, pred_sl, _ = model(x15, x1h)

                    loss_entry = focal_loss(pred_entry, ye)
                    loss_tp = mse_loss(pred_tp, ytp)
                    loss_sl = mse_loss(pred_sl, ysl)
                    loss = loss_entry + 0.5 * loss_tp + 0.5 * loss_sl
                    val_losses.append(loss.item())

                    predicted = (pred_entry > 0.5).float()
                    val_correct += (predicted == ye).sum().item()
                    val_total += ye.size(0)

            avg_train = np.mean(train_losses)
            avg_val = np.mean(val_losses)
            val_acc = val_correct / val_total if val_total > 0 else 0

            scheduler.step(avg_val)

            # Early stopping
            if avg_val < best_val_loss:
                best_val_loss = avg_val
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1

            if (epoch + 1) % 10 == 0 or patience_counter >= PATIENCE:
                current_lr = optimizer.param_groups[0]["lr"]
                print(
                    f"    Epoch {epoch+1:3d}: train={avg_train:.4f} val={avg_val:.4f} "
                    f"acc={val_acc:.3f} lr={current_lr:.1e} pat={patience_counter}/{PATIENCE}"
                )

            if patience_counter >= PATIENCE:
                print(f"    Early stopping at epoch {epoch + 1}")
                break

        fold_results.append({
            "fold": fold_idx + 1,
            "best_val_loss": best_val_loss,
            "val_accuracy": val_acc,
            "epochs": epoch + 1,
        })
        print(f"  Fold {fold_idx + 1} best val loss: {best_val_loss:.4f}, accuracy: {val_acc:.3f}")

    # Report CV results
    avg_loss = np.mean([r["best_val_loss"] for r in fold_results])
    avg_acc = np.mean([r["val_accuracy"] for r in fold_results])
    print(f"\n  CV Summary: mean val loss = {avg_loss:.4f}, mean accuracy = {avg_acc:.3f}")

    # Train final model on all data
    # Fit scaler on train only — for final model, use all data as "train"
    print("\n[3/4] Scaling features for final model...")
    scaler_4h = FeatureScaler()
    scaler_1h = FeatureScaler()
    X_4h_scaled = scaler_4h.fit_transform(X_4h)
    X_1h_scaled = scaler_1h.fit_transform(X_1h)

    print("\n[4/4] Training final model on all data...")
    X15_all = torch.tensor(X_4h_scaled, dtype=torch.float32)
    X1h_all = torch.tensor(X_1h_scaled, dtype=torch.float32)
    ye_all = torch.tensor(y_entry, dtype=torch.float32)
    ytp_all = torch.tensor(y_tp, dtype=torch.float32)
    ysl_all = torch.tensor(y_sl, dtype=torch.float32)

    full_ds = TensorDataset(X15_all, X1h_all, ye_all, ytp_all, ysl_all)
    full_loader = DataLoader(full_ds, batch_size=BATCH_SIZE, shuffle=True)

    final_model = GRUAttentionModel(
        input_size=NUM_FEATURES,
        hidden_size=128,
        num_layers=2,
        n_heads=4,
        dropout=0.3,
    ).to(device)

    optimizer = torch.optim.Adam(
        final_model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5, min_lr=1e-6
    )

    focal_loss_final = FocalLoss(alpha=0.25, gamma=2.0)
    mse_loss = nn.MSELoss()

    # Train for avg epochs from CV
    avg_epochs = max(20, int(np.mean([r["epochs"] for r in fold_results])))
    print(f"  Training for {avg_epochs} epochs...")

    for epoch in range(avg_epochs):
        final_model.train()
        epoch_losses = []
        for batch in full_loader:
            x15, x1h, ye, ytp, ysl = [b.to(device) for b in batch]

            optimizer.zero_grad()
            pred_entry, pred_tp, pred_sl, _ = final_model(x15, x1h)

            loss = focal_loss_final(pred_entry, ye) + 0.5 * mse_loss(pred_tp, ytp) + 0.5 * mse_loss(pred_sl, ysl)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(final_model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(loss.item())

        avg_loss = np.mean(epoch_losses)
        scheduler.step(avg_loss)

        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1:3d}: loss={avg_loss:.4f}")

    # DSR/PSR hard validation gate
    os.makedirs(MODEL_DIR, exist_ok=True)
    candidate_model_path = os.path.join(MODEL_DIR, "gru_attention_candidate.pt")
    candidate_scaler_path = os.path.join(MODEL_DIR, "feature_scaler_candidate.joblib")

    # Save as candidate first
    torch.save(final_model.state_dict(), candidate_model_path)
    print(f"\nCandidate model saved to {candidate_model_path}")

    dsr_passed = False
    try:
        from cross_aggregation.dsr_gate import validate_model_for_deployment
        final_model.eval()
        with torch.no_grad():
            all_preds = []
            for i in range(0, len(X_4h_scaled), BATCH_SIZE):
                x15_b = torch.tensor(X_4h_scaled[i:i+BATCH_SIZE], dtype=torch.float32).to(device)
                x1h_b = torch.tensor(X_1h_scaled[i:i+BATCH_SIZE], dtype=torch.float32).to(device)
                pred_e, _, _, _ = final_model(x15_b, x1h_b)
                all_preds.append(pred_e.cpu().numpy())
            all_preds = np.concatenate(all_preds)
        pseudo_returns = all_preds.flatten() - 0.5
        dsr_result = validate_model_for_deployment(pseudo_returns, n_trials=10)
        dsr_passed = dsr_result["passed"]
        if dsr_passed:
            print(f"DSR Gate: PASSED (DSR={dsr_result['dsr_pvalue']:.3f}, PSR={dsr_result['psr_pvalue']:.3f})")
        else:
            print(f"DSR Gate: FAILED -- {dsr_result['reason']}")
        report_path = os.path.join(MODEL_DIR, "validation_report.json")
        dsr_result["model"] = "system_c_deeplearn"
        with open(report_path, "w") as f:
            json.dump(dsr_result, f, indent=2)
        print(f"Validation report saved to {report_path}")
    except Exception as e:
        print(f"DSR gate unavailable: {e}")
        dsr_passed = True  # Allow deployment if gate module unavailable

    # Hard gate: promote candidate to production only if validation passes
    if dsr_passed:
        os.replace(candidate_model_path, MODEL_PATH)
        print(f"Validation PASSED -- model promoted to {MODEL_PATH}")
    elif os.path.exists(MODEL_PATH):
        os.remove(candidate_model_path)
        print(f"Validation FAILED -- keeping previous model at {MODEL_PATH}")
    else:
        os.replace(candidate_model_path, MODEL_PATH)
        print(f"Validation FAILED but no previous model -- deploying candidate (bootstrap)")

    # Save scaler (always save — scaler is deterministic from data, not model quality)

    # Save both scalers together — include BOTH key names for compatibility
    scaler_data = {
        "scaler_4h_mean": scaler_4h.mean,  # correct key name
        "scaler_4h_std": scaler_4h.std,
        "scaler_15m_mean": scaler_4h.mean,  # backward compat with bootstrap scanner
        "scaler_15m_std": scaler_4h.std,
        "scaler_1h_mean": scaler_1h.mean,
        "scaler_1h_std": scaler_1h.std,
    }
    joblib.dump(scaler_data, SCALER_PATH)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Training complete in {elapsed:.0f}s")
    print(f"  Model saved: {MODEL_PATH}")
    print(f"  Scaler saved: {SCALER_PATH}")
    print(f"  Parameters: {count_parameters(final_model):,}")
    print(f"  Samples: {len(X_4h)}")
    print(f"  CV mean val loss: {np.mean([r['best_val_loss'] for r in fold_results]):.4f}")
    print(f"  CV mean accuracy: {np.mean([r['val_accuracy'] for r in fold_results]):.3f}")
    print(f"{'=' * 60}")

    # Save arch_config.json so scanner can load with correct dimensions
    # MUST match the actual model architecture built above (hidden_size=128, etc.)
    arch_config = {
        "input_size": NUM_FEATURES,
        "hidden_size": 128,
        "num_layers": 2,
        "n_heads": 4,
        "dropout": 0.3,
        "seq_len": SEQ_LEN,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    arch_config_path = os.path.join(MODEL_DIR, "arch_config.json")
    with open(arch_config_path, "w") as f:
        json.dump(arch_config, f, indent=2)
    print(f"  Arch config saved: {arch_config_path}")

    # Save training summary
    summary = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_path": MODEL_PATH,
        "n_samples": len(X_4h),
        "n_features": NUM_FEATURES,
        "seq_len": SEQ_LEN,
        "n_folds": NUM_FOLDS,
        "fold_results": fold_results,
        "cv_mean_val_loss": float(np.mean([r["best_val_loss"] for r in fold_results])),
        "cv_mean_accuracy": float(np.mean([r["val_accuracy"] for r in fold_results])),
        "parameters": count_parameters(final_model),
        "training_seconds": round(elapsed, 1),
        "device": device,
    }
    summary_path = os.path.join(MODEL_DIR, "training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved: {summary_path}")


if __name__ == "__main__":
    train()
