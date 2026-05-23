"""
CPU inference module for Alpha Engine integration.

Loads the trained GRU model and predicts price direction.
Gracefully returns None if PyTorch is not installed or no model exists.

Usage:
    from local_gpu_trainer.inference import predict_direction
    result = predict_direction("BTCUSDT", horizon="4h")
    # Returns: {"direction": "UP", "probability": 0.72, "confidence": 0.72}
    # Returns None if model unavailable
"""

import sys
import os
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Graceful imports — entire module is a no-op without torch
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import numpy as np
    import pandas as pd
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

MODELS_DIR = Path(__file__).resolve().parent / "models"

# ---------------------------------------------------------------------------
# Lazy model loading
# ---------------------------------------------------------------------------
_cache = {}


def _load_model():
    """Load GRU model onto CPU (cached). Returns None on failure."""
    if not HAS_TORCH:
        return None
    if "model" in _cache:
        return _cache["model"]

    model_path = MODELS_DIR / "gru_crypto.pt"
    if not model_path.exists():
        return None

    try:
        # Import model class from the generated wrapper
        sys.path.insert(0, str(MODELS_DIR))
        from gru_inference import GRUDirectionPredictor, load_model
        model = load_model()
        if model is not None:
            _cache["model"] = model

            checkpoint = torch.load(str(model_path), map_location="cpu", weights_only=False)
            _cache["config"] = checkpoint.get("config", {})
            _cache["symbols"] = checkpoint.get("symbols", [])

        return model
    except Exception as e:
        log.debug(f"GRU model load failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Feature engineering (must match train_gru.py exactly)
# ---------------------------------------------------------------------------
BINANCE_URLS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


def _fetch_recent_ohlcv(symbol: str, limit: int = 100) -> "pd.DataFrame":
    """Fetch recent 1h candles for inference. Only needs ~100 candles."""
    if not HAS_REQUESTS:
        return pd.DataFrame()

    # Normalize symbol
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    params = {"symbol": sym, "interval": "1h", "limit": limit}

    for base_url in BINANCE_URLS:
        try:
            resp = requests.get(f"{base_url}/api/v3/klines", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    df = pd.DataFrame(data, columns=[
                        "open_time", "open", "high", "low", "close", "volume",
                        "close_time", "quote_vol", "trades", "taker_buy_base",
                        "taker_buy_quote", "ignore",
                    ])
                    for col in ["open", "high", "low", "close", "volume", "quote_vol"]:
                        df[col] = df[col].astype(float)
                    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
                    df = df.sort_values("timestamp").reset_index(drop=True)
                    return df
        except Exception:
            continue

    return pd.DataFrame()


def _engineer_features(df: "pd.DataFrame") -> "np.ndarray":
    """Build 15 features per row — mirrors train_gru.engineer_features."""
    c = df["close"].values.astype(np.float64)
    h = df["high"].values.astype(np.float64)
    l = df["low"].values.astype(np.float64)
    o = df["open"].values.astype(np.float64)
    v = df["volume"].values.astype(np.float64)

    n = len(c)
    feats = np.zeros((n, 15), dtype=np.float32)

    # 1. Log returns
    feats[1:, 0] = np.diff(np.log(np.maximum(c, 1e-10)))

    # 2. RSI(14)
    delta = np.diff(c)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)
    if n > 14:
        avg_gain[14] = gain[:14].mean()
        avg_loss[14] = loss[:14].mean()
        for i in range(15, n):
            avg_gain[i] = (avg_gain[i - 1] * 13 + gain[i - 1]) / 14
            avg_loss[i] = (avg_loss[i - 1] * 13 + loss[i - 1]) / 14
        rs = np.divide(avg_gain, avg_loss + 1e-10)
        feats[:, 1] = (100 - 100 / (1 + rs)) / 100

    # 3. BB position
    window = 20
    if n >= window:
        sma20 = pd.Series(c).rolling(window).mean().values
        std20 = pd.Series(c).rolling(window).std().values
        bb_width = 2 * std20
        feats[:, 2] = np.clip(np.where(bb_width > 1e-10, (c - (sma20 - std20)) / (bb_width + 1e-10), 0.5), 0, 1)

    # 4. Volume ratio
    if n >= window:
        vol_sma = pd.Series(v).rolling(window).mean().values
        feats[:, 3] = np.clip(v / (vol_sma + 1e-10), 0, 10) / 10

    # 5. ATR(14) normalized
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = np.zeros(n)
    if n > 14:
        atr[14] = tr[:14].mean()
        for i in range(15, n):
            atr[i] = (atr[i - 1] * 13 + tr[i - 1]) / 14
        feats[:, 4] = np.clip(atr / (c + 1e-10), 0, 0.2) / 0.2

    # 6. VWAP distance
    if n >= 24:
        cum_vol = pd.Series(v).rolling(24).sum().values
        cum_vp = pd.Series(v * c).rolling(24).sum().values
        vwap = cum_vp / (cum_vol + 1e-10)
        feats[:, 5] = np.clip((c - vwap) / (c * 0.02 + 1e-10), -1, 1)

    # 7-10. SMA distances
    for idx, period in [(6, 9), (7, 21), (8, 50)]:
        if n >= period:
            sma = pd.Series(c).rolling(period).mean().values
            scale = 0.02 if period <= 21 else 0.08
            feats[:, idx] = np.clip((c - sma) / (c * scale + 1e-10), -1, 1)
    if n >= 200:
        sma200 = pd.Series(c).rolling(200).mean().values
        feats[:, 9] = np.clip((c - sma200) / (c * 0.15 + 1e-10), -1, 1)

    # 11. Range
    feats[:, 10] = np.clip((h - l) / (c + 1e-10), 0, 0.1) / 0.1

    # 12. Body
    feats[:, 11] = np.clip((c - o) / (c * 0.02 + 1e-10), -1, 1)

    # 13-14. Shadow ratios
    feats[:, 12] = np.clip((h - np.maximum(o, c)) / (h - l + 1e-10), 0, 1)
    feats[:, 13] = np.clip((np.minimum(o, c) - l) / (h - l + 1e-10), 0, 1)

    # 15. Hour cyclical
    if "timestamp" in df.columns:
        feats[:, 14] = np.sin(2 * np.pi * df["timestamp"].dt.hour.values / 24)

    return np.nan_to_num(feats, nan=0.0, posinf=1.0, neginf=-1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def predict_direction(symbol: str, horizon: str = "4h") -> dict:
    """
    Predict price direction using trained GRU model.

    Args:
        symbol: Trading pair (e.g. "BTCUSDT", "BTC-USD", "BTC")
        horizon: "4h" or "24h"

    Returns:
        {"direction": "UP"/"DOWN", "probability": 0.0-1.0, "confidence": 0.0-1.0}
        Returns None if model unavailable or prediction fails.
    """
    if not (HAS_TORCH and HAS_DEPS and HAS_REQUESTS):
        return None

    model = _load_model()
    if model is None:
        return None

    try:
        seq_len = _cache.get("config", {}).get("sequence_len", 48)

        # Fetch recent data (need seq_len + warmup for indicators)
        df = _fetch_recent_ohlcv(symbol, limit=max(seq_len + 210, 260))
        if df.empty or len(df) < seq_len + 50:
            return None

        features = _engineer_features(df)

        # Take last seq_len rows as input sequence
        seq = features[-seq_len:]
        x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)  # (1, seq_len, 15)

        with torch.no_grad():
            pred = model(x)  # (1, 2) — [4h_prob, 24h_prob]

        idx = 0 if horizon == "4h" else 1
        prob = float(pred[0, idx].item())

        direction = "UP" if prob > 0.5 else "DOWN"
        confidence = abs(prob - 0.5) * 2  # 0.5 -> 0.0, 1.0 -> 1.0

        return {
            "direction": direction,
            "probability": round(prob, 4),
            "confidence": round(confidence, 4),
            "horizon": horizon,
            "symbol": symbol.upper(),
            "model": "gru_v1",
        }

    except Exception as e:
        log.debug(f"GRU prediction failed for {symbol}: {e}")
        return None


def get_model_info() -> dict:
    """Return model metadata and training metrics. None if unavailable."""
    if not HAS_TORCH:
        return None

    log_path = MODELS_DIR / "training_log.json"
    if log_path.exists():
        try:
            with open(log_path) as f:
                return json.load(f)
        except Exception:
            pass

    return None
