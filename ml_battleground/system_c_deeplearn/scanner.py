"""
System C Scanner: "The Neural Net"
GRU-Attention model inference -> ATR-based TP/SL -> forward validation -> save picks.

Loads trained model, feeds 200 bars of 4h (primary) + 1h (secondary) per pair,
entry threshold: probability > 0.65, R:R gate >= 1.5.

Falls back to "no signals" if model not yet trained (no fake data).

Run: python -m ml_battleground.system_c_deeplearn.scanner
"""
import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import joblib
except ImportError:
    joblib = None

from shared.data_fetcher import (
    fetch_single, fetch_fear_greed, fetch_funding_rates,
    fetch_btc_price, fetch_fear_greed_history, fear_greed_persistence, PAIRS,
)
from shared.indicators import atr, rsi, ema
from shared.risk_manager import can_open_trade, calculate_drawdown, position_size, should_trade
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed
from shared.performance import compute_stats
from shared.discord_notify import send_system_status, send_pick_alert, send_pick_exit
from shared.market_health import check_market_health, apply_health_gate, MarketHealth, dynamic_sl_multiplier
from shared.trade_filters import adaptive_threshold, atr_percentile_filter, volume_confirmation, reversal_confirmation
from shared.strategy_health import filter_signals_by_health
from shared.symbol_lock import filter_signals_by_lock
from shared.revision_marker import check_revision
from shared.meta_labeler import filter_signals_batch as meta_label_filter
from shared.external_signals import fetch_external_signals, apply_external_confluence_batch, log_external_signals_summary
from shared.feature_snapshot import snapshot_from_array

VERSION = "1.0.0"
SYSTEM_NAME = "system_c_deeplearn"
SYSTEM_LABEL = "The Neural Net"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EST = timezone(timedelta(hours=-5))
SCAN_FREQUENCY = "Every 30 minutes"
SCAN_STATE_PATH = os.path.join(DATA_DIR, "last_scan_state.json")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "gru_attention.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.joblib")

# Load architecture config if present (set by bootstrap training)
def _load_arch_config():
    cfg_path = os.path.join(MODEL_DIR, "arch_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f)
    return {}

_ARCH_CFG = _load_arch_config()

# Thresholds
ENTRY_THRESHOLD = 0.65      # minimum entry probability
MIN_RR = 1.5                # minimum risk-reward ratio
SEQ_LEN = _ARCH_CFG.get("seq_len", 200)  # sequence length for model input
NUM_FEATURES = 25  # was 24 — added fractional differentiation (Lopez de Prado AFML Ch.5)
# Feature names matching build_features_for_inference column order (Design 3E)
_FEATURE_NAMES = [
    "open_norm", "high_norm", "low_norm", "close_norm", "volume_norm",  # 0-4
    "rsi_14", "macd_hist", "bb_pctb", "vol_ratio_20", "atr_norm",       # 5-9
    "hour_sin", "hour_cos", "btc_return", "fear_greed", "funding_rate", "price_ema200",  # 10-15
    "log_return", "lag_3", "lag_5", "lag_10", "lag_20",                  # 16-20
    "fib_position", "dist_fib_618", "vol_zscore",                        # 21-23
    "close_fracdiff",                                                     # 24
]


def load_model():
    """
    Load trained GRU-Attention model and feature scalers.
    Returns (model, scaler_15m, scaler_1h) or (None, None, None) if not available.
    """
    if not TORCH_AVAILABLE:
        print("[System C] PyTorch not available. Model inference skipped.")
        return None, None, None

    if joblib is None:
        print("[System C] joblib not available. Model loading skipped.")
        return None, None, None

    if not os.path.exists(MODEL_PATH):
        print(f"[System C] Model not trained yet: {MODEL_PATH} not found.")
        print("[System C] Run: python -m ml_battleground.system_c_deeplearn.train_model")
        return None, None, None

    if not os.path.exists(SCALER_PATH):
        print(f"[System C] Scaler not found: {SCALER_PATH}")
        return None, None, None

    try:
        from system_c_deeplearn.model_arch import GRUAttentionModel

        # Load scaler data
        scaler_data = joblib.load(SCALER_PATH)

        class SimpleScaler:
            def __init__(self, mean, std):
                self.mean = np.asarray(mean, dtype=np.float32)
                self.std = np.asarray(std, dtype=np.float32)
                self.n_features = len(self.mean)

            def transform(self, X):
                # Handle feature count mismatch: truncate or pad
                n_cols = X.shape[1] if X.ndim > 1 else len(X)
                if n_cols > self.n_features:
                    X = X[:, :self.n_features]
                elif n_cols < self.n_features:
                    # Pad with zeros (shouldn't happen but be safe)
                    pad = np.zeros((X.shape[0], self.n_features - n_cols), dtype=np.float32)
                    X = np.hstack([X, pad])
                return ((X - self.mean) / (self.std + 1e-10)).astype(np.float32)

        # CRITICAL FIX: Use scaler_4h if available, fall back to scaler_15m for compat
        # Old bug: scaler_15m (trained on 15m data) was applied to 4h data,
        # meaning the model received adversarially scaled inputs → random predictions
        if "scaler_4h_mean" in scaler_data:
            scaler_primary = SimpleScaler(scaler_data["scaler_4h_mean"], scaler_data["scaler_4h_std"])
            print("[System C] Using scaler_4h (correct match for 4h data)")
        else:
            scaler_primary = SimpleScaler(scaler_data["scaler_15m_mean"], scaler_data["scaler_15m_std"])
            print("[System C] WARNING: scaler_4h not found, using scaler_15m (model needs retraining!)")
        scaler_1h = SimpleScaler(scaler_data["scaler_1h_mean"], scaler_data["scaler_1h_std"])

        # Load model — use arch_config input_size (the TRAINED feature count),
        # NOT NUM_FEATURES (which may have been updated for future retraining).
        trained_input_size = _ARCH_CFG.get("input_size", NUM_FEATURES)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = GRUAttentionModel(
            input_size=trained_input_size,
            hidden_size=_ARCH_CFG.get("hidden_size", 128),
            num_layers=_ARCH_CFG.get("num_layers", 2),
            n_heads=_ARCH_CFG.get("n_heads", 4),
            dropout=_ARCH_CFG.get("dropout", 0.3),
        )
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
        model.to(device)
        model.eval()

        print(f"[System C] Model loaded from {MODEL_PATH} (device={device}, input_size={trained_input_size})")
        return model, scaler_primary, scaler_1h

    except Exception as e:
        import traceback
        print(f"[System C] Error loading model: {e}")
        traceback.print_exc()
        return None, None, None


def build_features_for_inference(df, fear_greed_val, funding_rate, btc_returns=None):
    """
    Build feature matrix (n, 25) for a single pair DataFrame.
    Must match train_model.build_features_for_df exactly (same 25 features).
    """
    from shared.indicators import rsi as calc_rsi, macd as calc_macd
    from shared.indicators import bollinger_bands as calc_bb, atr as calc_atr, ema as calc_ema

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    opn = df["Open"]
    volume = df["Volume"]
    n = len(df)

    # Rolling means for normalization
    close_rm200 = close.rolling(200, min_periods=50).mean()
    vol_rm200 = volume.rolling(200, min_periods=50).mean()
    close_rm200 = close_rm200.replace(0, np.nan).fillna(close.mean())
    vol_rm200 = vol_rm200.replace(0, np.nan).fillna(volume.mean())

    # OHLCV normalized
    f_open = (opn / close_rm200).values
    f_high = (high / close_rm200).values
    f_low = (low / close_rm200).values
    f_close = (close / close_rm200).values
    f_volume = (volume / vol_rm200).values

    # RSI(14) / 100
    rsi_vals = calc_rsi(close, 14).values / 100.0

    # MACD histogram normalized by close
    _, _, macd_hist = calc_macd(close)
    f_macd = (macd_hist / close.replace(0, np.nan)).fillna(0).values

    # Bollinger %B
    _, _, _, _, pctb = calc_bb(close)
    f_bb = pctb.fillna(0.5).clip(-0.5, 1.5).values

    # Volume ratio vs 20-bar MA
    vol_ma20 = volume.rolling(20, min_periods=5).mean().replace(0, np.nan).fillna(volume.mean())
    f_vol_ratio = (volume / vol_ma20).fillna(1.0).values

    # ATR normalized by close
    atr_vals = calc_atr(high, low, close, 14)
    f_atr = (atr_vals / close.replace(0, np.nan)).fillna(0.02).values

    # Hour sin/cos
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

    # Fear & Greed (constant)
    f_fg = np.full(n, fear_greed_val)

    # Funding rate (constant)
    f_funding = np.full(n, funding_rate)

    # Price vs EMA(200)
    ema200 = calc_ema(close, 200)
    f_price_ema = (close / ema200.replace(0, np.nan)).fillna(1.0).values

    # === NEW RESEARCH-BACKED FEATURES (16-23) — must match train_model ===

    # 16: Log return (1-bar) — stationary representation
    f_log_ret = np.log(close / close.shift(1)).fillna(0).values

    # 17-20: Lagged returns at multiple windows
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

    # 23: Volume z-score (20-bar)
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

    features = np.column_stack([
        f_open, f_high, f_low, f_close, f_volume,          # 0-4
        rsi_vals, f_macd, f_bb, f_vol_ratio, f_atr,        # 5-9
        f_hour_sin, f_hour_cos, f_btc_ret, f_fg, f_funding, f_price_ema,  # 10-15
        f_log_ret, f_lag_3, f_lag_5, f_lag_10, f_lag_20,   # 16-20
        f_fib_position, f_dist_fib_618, f_vol_zscore,      # 21-23
        f_close_ffd,                                         # 24: fracdiff (AFML Ch.5)
    ])

    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def run_inference(model, scaler_primary, scaler_1h, df_primary, df_1h,
                  fear_greed_val, funding_rate, btc_ret_primary, btc_ret_1h):
    """
    Run model inference on a single pair.
    df_primary: 4h data.
    scaler_primary: scaler for primary timeframe (4h if available, 15m fallback).
    Returns (entry_prob, tp_dist, sl_dist, attn_weights) or None on failure.
    """
    if model is None:
        return None

    try:
        # Build features (always builds full 25-feature matrix)
        feat_primary = build_features_for_inference(df_primary, fear_greed_val, funding_rate, btc_ret_primary)
        feat_1h = build_features_for_inference(df_1h, fear_greed_val, funding_rate, btc_ret_1h)

        # Truncate features to match trained model's input_size
        # (model may have been trained on 16 features, scanner builds 24)
        trained_input_size = _ARCH_CFG.get("input_size", NUM_FEATURES)
        if feat_primary.shape[1] > trained_input_size:
            feat_primary = feat_primary[:, :trained_input_size]
            feat_1h = feat_1h[:, :trained_input_size]

        # Take last SEQ_LEN bars
        if len(feat_primary) < SEQ_LEN or len(feat_1h) < SEQ_LEN:
            return None

        seq_primary = feat_primary[-SEQ_LEN:]
        seq_1h = feat_1h[-SEQ_LEN:]

        # Scale primary timeframe data
        seq_primary_scaled = scaler_primary.transform(seq_primary)
        seq_1h_scaled = scaler_1h.transform(seq_1h)

        # Convert to tensors
        device = next(model.parameters()).device
        x_primary = torch.tensor(seq_primary_scaled, dtype=torch.float32).unsqueeze(0).to(device)
        x_1h = torch.tensor(seq_1h_scaled, dtype=torch.float32).unsqueeze(0).to(device)

        # Inference
        with torch.no_grad():
            entry_prob, tp_dist, sl_dist, attn_weights = model(x_primary, x_1h)

        return (
            float(entry_prob.cpu().item()),
            float(tp_dist.cpu().item()),
            float(sl_dist.cpu().item()),
            attn_weights.cpu().numpy() if attn_weights is not None else None,
            seq_primary[-1],  # last row of feature vector for snapshot (Design 3E)
        )

    except Exception as e:
        print(f"[System C] Inference error: {e}")
        return None


def calibrate_confidence(raw_prob: float, temperature: float = 2.5) -> float:
    """
    Calibrate overconfident neural net probabilities using temperature scaling.

    Problem: untrained/overfit/bootstrap model outputs 84-93% on losing trades.
    Old T=2.0 barely compressed: 0.90 → 0.8967 (useless).
    T=3.5 over-suppressed: 0.93 → 0.68 (blocked all trades during bootstrap).

    T=2.5 (fast-learn balance): 0.93 → 0.73, 0.85 → 0.64, 0.70 → 0.56
    Compresses overconfidence while still allowing enough signals for data collection.

    Hard cap at 0.75 — no bootstrap model should claim > 75% confidence.
    """
    import math
    raw_prob = max(0.001, min(0.999, raw_prob))
    logit = math.log(raw_prob / (1.0 - raw_prob))
    scaled_logit = logit / temperature
    calibrated = 1.0 / (1.0 + math.exp(-scaled_logit))

    # Hard cap: bootstrap model max 75% confidence
    return min(calibrated, 0.75)


def _check_candle_gate(reference_df) -> bool:
    """Returns True if a new 1h candle has closed since last scan.

    Uses BTCUSDT 1h as the reference candle clock. If the latest candle
    close timestamp matches the stored one, skip the scan to avoid
    computing features on incomplete (mid-candle) data.
    """
    if reference_df is None or len(reference_df) == 0:
        return True  # No data = let it try
    latest_close = str(reference_df.index[-1])
    if os.path.exists(SCAN_STATE_PATH):
        try:
            with open(SCAN_STATE_PATH) as f:
                state = json.load(f)
            if state.get("last_candle_close") == latest_close:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    # Update state
    os.makedirs(os.path.dirname(SCAN_STATE_PATH), exist_ok=True)
    with open(SCAN_STATE_PATH, 'w') as f:
        json.dump({"last_candle_close": latest_close}, f)
    return True


def scan():
    """Main scan cycle for System C."""
    now = datetime.now(timezone.utc)
    print(f"\n{'=' * 60}")
    print(f"[System C] The Neural Net v{VERSION} -- Scan at {now.isoformat()}")
    print(f"{'=' * 60}")

    # Check for revision reset (archives pre-revision data, resets tracking)
    from pathlib import Path
    check_revision(SYSTEM_NAME, Path(DATA_DIR))

    # Load model
    model, scaler_primary, scaler_1h = load_model()
    if model is None:
        print("[System C] No trained model available. Writing empty state and exiting.")
        # Still validate existing picks and write dashboard
        active = load_active(DATA_DIR)
        closed = load_closed(DATA_DIR)
        if active:
            active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR)
            if newly_closed:
                closed.extend(newly_closed)
                save_picks(active, newly_closed, DATA_DIR)
                for pick in newly_closed:
                    send_pick_exit(SYSTEM_LABEL, pick)
        stats = compute_stats(closed)
        _write_dashboard_data(active, closed, stats, model_loaded=False)
        _send_status(active, closed, stats)
        return

    # Load existing state
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    # Validate existing picks first
    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR)
    if newly_closed:
        print(f"  Closed {len(newly_closed)} picks:")
        for p in newly_closed:
            pnl = p.get("net_pnl_pct", 0)
            print(f"    {p['symbol']} -> {p.get('exit_reason', '?')} ({pnl:+.2f}%)")
            send_pick_exit(SYSTEM_LABEL, p)

    # Check risk budget
    stats = compute_stats(closed + [p for p in newly_closed])
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed + newly_closed, stats)
        _send_status(active, closed + newly_closed, stats)
        return

    # Drawdown halt gate (8% DD = stop trading until recovery)
    ok_to_trade, halt_reason = should_trade(equity_curve)
    if not ok_to_trade:
        print(f"  {halt_reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed + newly_closed, stats)
        _send_status(active, closed + newly_closed, stats)
        return

    # --- Circuit Breaker: reduce size on cold streaks (never fully halt — fast-learn mode) ---
    # Full pausing prevented System C from collecting data needed to improve.
    # risk_manager.py handles micro-positions (0.1% on 0/5 streaks, 0.25% on <30% WR)
    all_closed_so_far = closed + [p for p in newly_closed]
    circuit_breaker_reduce = False

    if len(all_closed_so_far) >= 5:
        last_5 = all_closed_so_far[-5:]
        wins_last_5 = sum(1 for t in last_5 if t.get("net_pnl_pct", 0) > 0)
        if wins_last_5 == 0:
            circuit_breaker_reduce = True
            print(f"  *** FAST-LEARN: 0/5 wins — micro-positions only (0.1% via risk_manager) ***")

    if not circuit_breaker_reduce and len(all_closed_so_far) >= 10:
        last_10 = all_closed_so_far[-10:]
        wins_last_10 = sum(1 for t in last_10 if t.get("net_pnl_pct", 0) > 0)
        wr_last_10 = wins_last_10 / len(last_10)
        if wr_last_10 < 0.25:
            circuit_breaker_reduce = True
            print(f"  *** FAST-LEARN: {wr_last_10:.0%} WR over last 10 — capped at 0.25% position ***")

    # Fetch market context
    print("\n  Fetching market context...")
    fear_greed = fetch_fear_greed()
    fear_greed_val = fear_greed / 100.0
    funding_rates = fetch_funding_rates()

    # Fetch BTC data for BTC return feature
    # Primary: 4h (best signal-to-noise), Secondary: 1h
    # 15m removed — too noisy for crypto, destroys profitability via transaction costs
    btc_4h = fetch_single("BTCUSDT", "4h", SEQ_LEN + 50)
    btc_1h = fetch_single("BTCUSDT", "1h", SEQ_LEN + 50)

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate(btc_1h):
        print(f"  Skipping scan: no new 1h candle closed since last scan")
        all_closed = closed + newly_closed
        save_picks(active, newly_closed, DATA_DIR)
        stats = compute_stats(all_closed)
        _write_dashboard_data(active, all_closed, stats, model_loaded=(model is not None))
        _send_status(active, all_closed, stats)
        print(f"[System C] Scan complete (no new candle).")
        return

    btc_ret_4h_series = btc_4h["Close"].pct_change().fillna(0) if btc_4h is not None else None
    btc_ret_1h_series = btc_1h["Close"].pct_change().fillna(0) if btc_1h is not None else None

    # --- Market Health Gate ---
    health, health_details = check_market_health(fear_greed, btc_1h, funding_rates)
    print(f"  Market Health: {health.value} | F&G={fear_greed}, BTC trend={health_details.get('btc_trend','?')}, "
          f"BTC 24h={health_details.get('btc_24h_change','?')}%, volatility={health_details.get('volatility','?')}")

    # BTC trend context (for logging/awareness)
    if btc_1h is not None and len(btc_1h) >= 200:
        btc_close = btc_1h["Close"].values
        btc_sma50 = float(np.mean(btc_close[-50:]))
        btc_sma200 = float(np.mean(btc_close[-200:]))
        btc_now = float(btc_close[-1])
        if btc_now > btc_sma50 and btc_now > btc_sma200:
            btc_trend = "BULLISH"
        elif btc_now < btc_sma200:
            btc_trend = "BEARISH"
        else:
            btc_trend = "NEUTRAL"
        print(f"  BTC trend: {btc_trend} (${btc_now:.0f} | SMA50=${btc_sma50:.0f} | SMA200=${btc_sma200:.0f})")

    if health == MarketHealth.PANIC:
        print(f"  *** PANIC MODE: scanning for SELL-only opportunities ***")

    # --- F&G 3-Day Persistence (R008: Wong, Sharpe 1.3) ---
    fg_history = fetch_fear_greed_history(7)
    fg_persist = fear_greed_persistence(fg_history)
    if fg_persist["persistent"]:
        print(f"  F&G PERSISTENT: {fg_persist['direction']} ({fg_persist['fear_days']}d fear, {fg_persist['greed_days']}d greed)")

    # --- F&G Directional Filter (HARD BLOCK — same logic as System A/B) ---
    fg_direction = None
    fg_confidence_boost = 0.0
    if fear_greed < 15:
        # P0 BOUNCE DETECTOR: F&G < 15 = capitulation bottom 70-80% of historical cases
        fg_direction = None
        print(f"  F&G BOUNCE ZONE: F&G={fear_greed} < 15, extreme capitulation — bounce detector active (no forced SELL)")
    elif fear_greed < 25:
        fg_direction = "SELL"
        print(f"  F&G HARD BLOCK: SELL only (F&G={fear_greed} < 25, extreme fear — no BUYs)")
    elif fear_greed > 85:
        fg_direction = "BUY"
        print(f"  F&G HARD BLOCK: BUY only (F&G={fear_greed} > 85, parabolic greed — no SHORTs)")
    elif fg_persist["persistent"] and fg_persist["direction"] == "SELL" and fear_greed <= 35:
        fg_direction = "SELL"
        fg_confidence_boost = 0.10
        print(f"  F&G PERSISTENT FEAR: SELL only ({fg_persist['fear_days']}d consecutive fear, F&G={fear_greed})")
    elif fg_persist["persistent"] and fg_persist["direction"] == "BUY" and fear_greed >= 75:
        fg_direction = "BUY"
        fg_confidence_boost = 0.10
        print(f"  F&G PERSISTENT GREED: BUY only ({fg_persist['greed_days']}d consecutive greed, F&G={fear_greed})")
    else:
        print(f"  F&G: {fear_greed} (no directional filter)")

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    ext_signals = fetch_external_signals()
    log_external_signals_summary(ext_signals)

    # Scan all pairs
    print(f"\n  Scanning {len(PAIRS)} pairs (threshold={ENTRY_THRESHOLD}, R:R>={MIN_RR})...")
    new_signals = []
    active_symbols = {p["symbol"] for p in active}
    scan_results = []

    for pair in PAIRS:
        if pair in active_symbols:
            continue

        # Fetch both timeframes: 4h (primary) + 1h (secondary)
        df_4h = fetch_single(pair, "4h", SEQ_LEN + 50)
        df_1h = fetch_single(pair, "1h", SEQ_LEN + 50)

        if df_4h is None or df_1h is None:
            continue
        if len(df_4h) < SEQ_LEN or len(df_1h) < SEQ_LEN:
            continue

        funding = funding_rates.get(pair, 0.0)

        # --- Research-backed pre-trade filters ---
        # ATR percentile filter (Wilder 1978)
        atr_check = atr(df_1h["High"], df_1h["Low"], df_1h["Close"], 14)
        if len(atr_check) >= 50 and not atr_percentile_filter(atr_check.values):
            continue

        # Volume confirmation gate
        vol_col = "volume" if "volume" in df_1h.columns else "Volume"
        vol_ok, vol_ratio = volume_confirmation(df_1h[vol_col].values)
        if not vol_ok:
            continue

        # Align BTC returns to pair's index
        btc_r_4h = None
        btc_r_1h = None
        if btc_ret_4h_series is not None:
            btc_r_4h = btc_ret_4h_series.reindex(df_4h.index, method="nearest").fillna(0)
        if btc_ret_1h_series is not None:
            btc_r_1h = btc_ret_1h_series.reindex(df_1h.index, method="nearest").fillna(0)

        # Run inference
        result = run_inference(
            model, scaler_primary, scaler_1h,
            df_4h, df_1h,
            fear_greed_val, funding,
            btc_r_4h, btc_r_1h,
        )

        if result is None:
            continue

        raw_prob, tp_dist_atr, sl_dist_atr, attn_weights, _last_feat_row = result

        # Calibrate overconfident neural net output (temperature scaling)
        # T=2.5: moderate compression (0.93→0.73, 0.85→0.64, 0.70→0.56)
        # Balances between raw overconfidence and over-suppression (T=3.5 blocked everything)
        entry_prob = calibrate_confidence(raw_prob, temperature=2.5)

        # Current price and ATR
        current_price = float(df_1h["Close"].iloc[-1])
        atr_1h = atr(df_1h["High"], df_1h["Low"], df_1h["Close"], 14)
        atr_now = float(atr_1h.iloc[-1]) if len(atr_1h) > 0 else current_price * 0.02
        rsi_val = float(rsi(df_1h["Close"], 14).iloc[-1]) if len(df_1h) > 14 else 50.0

        scan_results.append({
            "pair": pair,
            "entry_prob": entry_prob,
            "tp_dist_atr": tp_dist_atr,
            "sl_dist_atr": sl_dist_atr,
        })

        # Entry gate — slightly raised threshold during bootstrap (< 30 closed trades)
        # With T=2.5 calibration: raw 0.93 → 0.73, raw 0.85 → 0.64
        # Bootstrap threshold 0.55 lets more signals through for fast data collection
        # while still filtering out low-confidence noise (raw < ~0.75)
        n_closed_total = len(closed) + len(newly_closed)
        effective_threshold = 0.55 if n_closed_total < 30 else ENTRY_THRESHOLD
        if entry_prob < effective_threshold:
            continue

        # Determine signal direction using RSI + trend (mean-reversion logic)
        # RSI < 30 + price below EMA200 = OVERSOLD = BUY (bounce play)
        # RSI > 70 + price above EMA200 = OVERBOUGHT = SELL (fade play)
        # Otherwise: trust the model's own directional prediction
        ema_200 = ema(df_1h["Close"], 200)
        ema_200_val = float(ema_200.iloc[-1]) if len(ema_200) >= 200 else current_price
        price_below_ema200 = current_price < ema_200_val * 0.99
        price_above_ema200 = current_price > ema_200_val * 1.01

        if rsi_val < 30 and price_below_ema200:
            # Oversold bounce — mean reversion BUY
            signal_direction = "BUY"
        elif rsi_val > 70 and price_above_ema200:
            # Overbought fade — mean reversion SELL
            signal_direction = "SELL"
        else:
            # Model confidence not extreme: use model's own prediction
            # entry_prob > 0.5 from the GRU = bullish prediction (BUY)
            # entry_prob < 0.5 = bearish prediction (SELL)
            # Since we already gated on entry_prob >= ENTRY_THRESHOLD (0.65),
            # the model is confident in a move — default to BUY for long bias
            # unless RSI is elevated (> 60) suggesting overbought lean
            if rsi_val > 60:
                signal_direction = "SELL"
            else:
                signal_direction = "BUY"

        # Reversal confirmation: price action must confirm signal direction (Elder 1993)
        close_col = "close" if "close" in df_1h.columns else "Close"
        high_col = "high" if "high" in df_1h.columns else "High"
        low_col = "low" if "low" in df_1h.columns else "Low"
        rev_ok, rev_reason = reversal_confirmation(
            df_1h[close_col].values, df_1h[high_col].values, df_1h[low_col].values,
            signal_type=signal_direction,
        )
        if not rev_ok:
            print(f"    [filtered] {pair}: reversal not confirmed ({rev_reason})")
            continue

        # Apply F&G directional filter
        if fg_direction and signal_direction != fg_direction:
            continue

        # Clamp model SL to minimum 2.0x ATR (was 1.5x — too tight for 4h crypto)
        sl_dist_atr = max(sl_dist_atr, 2.0)

        # TP capped at 2.0x ATR (was ~4.0x effective; 37.8% trades expired)
        tp_dist_atr = max(tp_dist_atr, sl_dist_atr * 1.33)
        tp_dist_atr = min(tp_dist_atr, 2.0)

        # Convert TP/SL from ATR units to price
        if signal_direction == "BUY":
            tp_price = current_price + tp_dist_atr * atr_now
            sl_price = current_price - sl_dist_atr * atr_now
        else:  # SELL
            tp_price = current_price - tp_dist_atr * atr_now
            sl_price = current_price + sl_dist_atr * atr_now

        # --- Dynamic SL widening during volatility spikes ---
        if len(df_1h) >= 60:
            high_col = "high" if "high" in df_1h.columns else "High"
            low_col = "low" if "low" in df_1h.columns else "Low"
            ranges = (df_1h[high_col] - df_1h[low_col]).values[-60:]
            current_range = float(ranges[-1])
            median_range = float(np.median(ranges[:-1]))
            if median_range > 0 and current_range / median_range > 2.0:
                old_sl = sl_price
                sl_dist = abs(current_price - sl_price)
                if signal_direction == "BUY":
                    sl_price = current_price - sl_dist * 1.5
                else:
                    sl_price = current_price + sl_dist * 1.5
                print(f"  [volatility] Widening SL for {pair}: {old_sl:.4g} -> {sl_price:.4g}")

        # Dynamic SL widening based on market health (WARNING/CAUTION = wider SL)
        health_sl_mult = dynamic_sl_multiplier(health, base_mult=1.0)
        if health_sl_mult > 1.0:
            old_sl = sl_price
            sl_dist = abs(current_price - sl_price)
            if signal_direction == "BUY":
                sl_price = current_price - sl_dist * health_sl_mult
            else:
                sl_price = current_price + sl_dist * health_sl_mult
            print(f"  [health={health.value}] Widening SL for {pair}: {old_sl:.4g} -> {sl_price:.4g} ({health_sl_mult:.1f}x)")

        # --- Minimum SL floor: never closer than 1.5% ---
        sl_dist_abs = abs(current_price - sl_price)
        if current_price > 0 and sl_dist_abs / current_price < 0.015:
            if signal_direction == "BUY":
                sl_price = current_price * (1 - 0.015)
            else:
                sl_price = current_price * (1 + 0.015)
            print(f"  [SL floor] {pair}: SL widened to 1.5% minimum")

        # R:R gate
        if signal_direction == "BUY":
            risk = current_price - sl_price
            reward = tp_price - current_price
        else:
            risk = sl_price - current_price
            reward = current_price - tp_price
        rr = reward / risk if risk > 0 else 0

        if rr < MIN_RR:
            continue

        # Check transaction cost viability
        cost = round_trip_cost(pair)
        tp_dist_pct = reward / current_price
        sl_dist_pct = risk / current_price
        # 3x cost rule: gross reward must exceed 3x round_trip_cost (min 30 bps)
        min_reward = max(cost * 3, 0.003)
        gross_reward_pct = tp_dist_pct
        if gross_reward_pct < min_reward:
            continue  # not enough reward to cover costs

        # --- Expected return pre-filter (Kimi/Lopez de Prado) ---
        expected_return = entry_prob * tp_dist_pct - (1 - entry_prob) * sl_dist_pct - cost
        if expected_return < min_reward:
            print(f"    [filtered] {pair}: E[R]={expected_return:.4f} < min {min_reward:.4f} (3x cost rule)")
            continue

        # Adaptive threshold: cost-aware breakeven (Kissell 2020)
        min_conf = adaptive_threshold(tp_dist_pct, sl_dist_pct, cost)
        # Hard confidence floor: never open below effective entry threshold
        effective_min = max(min_conf, effective_threshold)
        if entry_prob < effective_min:
            continue

        # Position sizing
        wr = stats.get("win_rate", 0.5) if stats.get("trades", 0) > 10 else 0.5
        avg_win = stats.get("avg_win_pct", 2.0)
        avg_loss = abs(stats.get("avg_loss_pct", -1.5))
        pos_size = position_size(wr, avg_win, avg_loss, confidence=entry_prob,
                                recent_trades=all_closed_so_far)

        # Circuit breaker: cap position size to minimum 0.25% if recent WR < 25%
        if circuit_breaker_reduce:
            pos_size = min(pos_size, 0.0025)

        signal = {
            "symbol": pair,
            "signal_type": signal_direction,
            "entry_price": round(current_price, 8),
            "take_profit": round(tp_price, 8),
            "stop_loss": round(sl_price, 8),
            "risk_reward": round(rr, 2),
            "confidence": round(entry_prob, 4),
            "ml_score": round(entry_prob, 4),
            "raw_confidence": round(raw_prob, 4),
            "tp_dist_atr": round(tp_dist_atr, 3),
            "sl_dist_atr": round(sl_dist_atr, 3),
            "atr_value": round(atr_now, 8),
            "rsi_value": round(rsi_val, 2),
            "position_size_pct": round(pos_size * 100, 2),
            "features": snapshot_from_array(_last_feat_row, _FEATURE_NAMES),
            "strategy": "gru_attention",
            "tp_sl_method": "neural_net",
            "timeframe": "4h",
            "timestamp": now.isoformat(),
            "system": SYSTEM_NAME,
            "market_health": health.value,
            "version": VERSION,
            "fear_greed": fear_greed,
            "funding_rate": funding,
            "transaction_cost_pct": round(cost * 100, 3),
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "pick_reason": (
                f"GRU-Attention neural net entry probability {entry_prob:.2f} "
                f"(threshold {ENTRY_THRESHOLD}) | R:R {rr:.1f} (min {MIN_RR}) "
                f"| TP={tp_dist_atr:.2f}x ATR, SL={sl_dist_atr:.2f}x ATR "
                f"| RSI={rsi_val:.1f} | F&G={fear_greed} | Funding={funding:.4f}"
            ),
        }

        # Calculate initial unrealized P&L from latest close
        signal["current_price"] = current_price
        if signal["signal_type"] == "BUY":
            signal["unrealized_pnl_pct"] = round((current_price - signal["entry_price"]) / signal["entry_price"] * 100, 4)
        else:
            signal["unrealized_pnl_pct"] = round((signal["entry_price"] - current_price) / signal["entry_price"] * 100, 4)

        new_signals.append(signal)
        active_symbols.add(pair)
        time.sleep(0.1)  # rate limit

    # --- Meta-Labeler Quality Gate (Lopez de Prado M2) ---
    all_closed = closed + newly_closed
    if new_signals:
        new_signals = meta_label_filter(new_signals, all_closed, SYSTEM_NAME)

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    if new_signals:
        new_signals = apply_external_confluence_batch(new_signals, ext_signals)

    # Apply market health gate to filter/adjust signals
    raw_count = len(new_signals)
    new_signals = apply_health_gate(health, new_signals)
    if raw_count > 0 and len(new_signals) < raw_count:
        print(f"  Health gate ({health.value}): {raw_count} -> {len(new_signals)} signals")

    # --- Strategy Health Gate: disable consistently losing strategies ---
    new_signals = filter_signals_by_health(new_signals, all_closed)

    # --- Cross-System Symbol Lock: prevent conflicting positions ---
    new_signals = filter_signals_by_lock(new_signals, SYSTEM_NAME)

    # Sort by entry probability, take top N that fit risk budget
    new_signals.sort(key=lambda s: s["confidence"], reverse=True)

    added = 0
    for sig in new_signals:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            break
        active.append(sig)
        added += 1
        print(
            f"  NEW: {sig['symbol']} BUY @ {sig['entry_price']:.6g} | "
            f"prob={sig['confidence']:.3f} R:R={sig['risk_reward']:.1f} "
            f"TP={sig['tp_dist_atr']:.1f}xATR SL={sig['sl_dist_atr']:.1f}xATR"
        )
        send_pick_alert(SYSTEM_LABEL, sig)

    # Summary
    all_closed = closed + newly_closed
    stats = compute_stats(all_closed)
    print(f"\n  Results: {len(PAIRS)} scanned, {added} new picks, "
          f"{len(active)} active, {len(all_closed)} closed")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} "
          f"Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    if scan_results:
        probs = [r["entry_prob"] for r in scan_results]
        print(f"  Model output: mean_prob={np.mean(probs):.3f} "
              f"max_prob={np.max(probs):.3f} "
              f"above_threshold={sum(1 for p in probs if p >= ENTRY_THRESHOLD)}")

    # Save everything
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, all_closed, stats, scan_results=scan_results)
    _send_status(active, all_closed, stats)

    # Check DSR validation status
    _dsr_validated = False
    try:
        _vr_path = os.path.join(os.path.dirname(__file__), "models", "validation_report.json")
        if os.path.exists(_vr_path):
            with open(_vr_path) as _vf:
                _dsr_validated = bool(json.load(_vf).get("passed", False))
    except Exception:
        pass

    # Write scan summary for debugging
    scan_summary = {
        "timestamp": now.isoformat(),
        "market_health": health.value,
        "fear_greed": fear_greed,
        "active_count": len(active),
        "closed_count": len(all_closed),
        "new_picks": added,
        "newly_closed": len(newly_closed),
        "win_rate": stats.get("win_rate", 0),
        "sharpe": stats.get("sharpe", 0),
        "drawdown": round(dd, 4),
        "dsr_validated": _dsr_validated,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    print(f"\n[System C] Scan complete.\n")


def _write_dashboard_data(active: list, closed: list, stats: dict,
                          model_loaded: bool = True,
                          scan_results: Optional[list] = None):
    """Write JSON data for dashboard consumption."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # System C uses a single strategy (GRU-Attention) so inception is system-level
    STRATEGY_INCEPTION = {
        "gru_attention": {"inception": "2026-02-23T18:00:00Z", "last_code_update": "2026-02-24T20:00:00Z"},
    }

    # Enrich closed trades with strategy inception metadata
    for trade in closed:
        strat = trade.get("strategy", "")
        if strat in STRATEGY_INCEPTION:
            trade["strategy_inception"] = STRATEGY_INCEPTION[strat]["inception"]
            trade["strategy_last_code_update"] = STRATEGY_INCEPTION[strat]["last_code_update"]

    dashboard_data = {
        "system": SYSTEM_LABEL,
        "system_name": SYSTEM_NAME,
        "version": VERSION,
        "scan_frequency": SCAN_FREQUENCY,
        "inception_date": "2026-02-23T18:00:00Z",
        "last_code_update": "2026-02-24T20:00:00Z",
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "model_loaded": model_loaded,
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "entry_threshold": ENTRY_THRESHOLD,
        "min_rr": MIN_RR,
        "strategy_breakdown": {
            strat: {**meta, "trades": sum(1 for t in closed if t.get("strategy") == strat),
                    "wins": sum(1 for t in closed if t.get("strategy") == strat and (t.get("net_pnl_pct", 0) > 0)),
                    "total_pnl": round(sum(t.get("net_pnl_pct", 0) for t in closed if t.get("strategy") == strat), 4)}
            for strat, meta in STRATEGY_INCEPTION.items()
            if any(t.get("strategy") == strat for t in closed)
        },
    }

    if scan_results:
        dashboard_data["scan_heatmap"] = [
            {
                "pair": r["pair"],
                "entry_prob": round(r["entry_prob"], 4),
                "tp_dist_atr": round(r["tp_dist_atr"], 3),
                "sl_dist_atr": round(r["sl_dist_atr"], 3),
            }
            for r in scan_results
        ]

    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


def _send_status(active: list, closed: list, stats: dict):
    """Send Discord status notification."""
    from shared.validator import passes_validation_gate

    gate = passes_validation_gate(closed)

    send_system_status(
        system_name=SYSTEM_NAME,
        system_label=SYSTEM_LABEL,
        version=VERSION,
        active_picks=active,
        closed_picks=closed,
        stats=stats,
        validation_gate=gate,
    )


if __name__ == "__main__":
    scan()
