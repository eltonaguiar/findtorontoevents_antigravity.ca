"""
GRU-based crypto price direction predictor for Alpha Engine.

Fetches OHLCV data from Binance, engineers features matching the Alpha Engine,
trains a 2-layer GRU, and exports weights for CPU inference in CI.

Usage:
    py -3.14 local_gpu_trainer/train_gru.py

Requirements:
    pip install torch requests numpy pandas
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful torch import
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    log.error("PyTorch not installed. Install: pip install torch")

try:
    import numpy as np
    import pandas as pd
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    log.error("numpy/pandas not installed. Install: pip install numpy pandas")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    log.error("requests not installed. Install: pip install requests")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "LINKUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT",
]

SEQUENCE_LEN = 48          # 48 hourly candles
NUM_FEATURES = 15          # feature count per timestep
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.3
LR = 0.001
EPOCHS = 50
PATIENCE = 7               # early stopping patience
BATCH_SIZE = 256
VAL_SPLIT = 0.20           # chronological 80/20

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "gru_crypto.pt"
LOG_PATH = MODELS_DIR / "training_log.json"

# Binance API mirrors (3+ fallback chain per project rules)
BINANCE_URLS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def _binance_klines(symbol: str, interval: str = "1h", limit: int = 4320) -> list:
    """Fetch klines from Binance with mirror fallback. 4320 = ~6 months of 1h."""
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
    all_klines = []
    end_time = None

    while len(all_klines) < limit:
        p = dict(params)
        if end_time:
            p["endTime"] = end_time

        fetched = False
        for base_url in BINANCE_URLS:
            try:
                resp = requests.get(
                    f"{base_url}/api/v3/klines", params=p, timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if not data:
                        fetched = True
                        break
                    all_klines = data + all_klines
                    end_time = data[0][0] - 1  # before earliest candle
                    fetched = True
                    break
            except Exception:
                continue

        if not fetched:
            log.warning(f"Failed to fetch {symbol} from all Binance mirrors")
            break

        if len(data) < params["limit"]:
            break  # no more data

        time.sleep(0.25)  # rate limit

    return all_klines


def fetch_ohlcv(symbol: str) -> "pd.DataFrame":
    """Fetch ~6 months of 1h OHLCV for a symbol and return a DataFrame."""
    raw = _binance_klines(symbol, "1h", 4320)
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    for col in ["open", "high", "low", "close", "volume", "quote_vol"]:
        df[col] = df[col].astype(float)
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Feature engineering (matches Alpha Engine indicators)
# ---------------------------------------------------------------------------
def engineer_features(df: "pd.DataFrame") -> "np.ndarray":
    """Build 15 features per row from OHLCV. Returns (N, 15) array."""
    c = df["close"].values.astype(np.float64)
    h = df["high"].values.astype(np.float64)
    l = df["low"].values.astype(np.float64)
    o = df["open"].values.astype(np.float64)
    v = df["volume"].values.astype(np.float64)

    n = len(c)
    feats = np.zeros((n, NUM_FEATURES), dtype=np.float32)

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
        feats[:, 1] = (100 - 100 / (1 + rs)) / 100  # normalize to 0-1

    # 3. Bollinger Band position (where price sits in the band)
    window = 20
    if n >= window:
        sma20 = pd.Series(c).rolling(window).mean().values
        std20 = pd.Series(c).rolling(window).std().values
        bb_width = 2 * std20
        bb_pos = np.where(bb_width > 1e-10, (c - (sma20 - std20)) / (bb_width + 1e-10), 0.5)
        feats[:, 2] = np.clip(bb_pos, 0, 1)

    # 4. Volume ratio (current / 20-period SMA)
    if n >= window:
        vol_sma = pd.Series(v).rolling(window).mean().values
        feats[:, 3] = np.clip(v / (vol_sma + 1e-10), 0, 10) / 10

    # 5. ATR(14) normalized by close
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = np.zeros(n)
    if n > 14:
        atr[14] = tr[:14].mean()
        for i in range(15, n):
            atr[i] = (atr[i - 1] * 13 + tr[i - 1]) / 14
        feats[:, 4] = np.clip(atr / (c + 1e-10), 0, 0.2) / 0.2

    # 6. VWAP distance (session = 24h rolling)
    if n >= 24:
        cum_vol = pd.Series(v).rolling(24).sum().values
        cum_vp = pd.Series(v * c).rolling(24).sum().values
        vwap = cum_vp / (cum_vol + 1e-10)
        feats[:, 5] = np.clip((c - vwap) / (c * 0.02 + 1e-10), -1, 1)

    # 7. SMA(9) distance
    if n >= 9:
        sma9 = pd.Series(c).rolling(9).mean().values
        feats[:, 6] = np.clip((c - sma9) / (c * 0.02 + 1e-10), -1, 1)

    # 8. SMA(21) distance
    if n >= 21:
        sma21 = pd.Series(c).rolling(21).mean().values
        feats[:, 7] = np.clip((c - sma21) / (c * 0.04 + 1e-10), -1, 1)

    # 9. SMA(50) distance
    if n >= 50:
        sma50 = pd.Series(c).rolling(50).mean().values
        feats[:, 8] = np.clip((c - sma50) / (c * 0.08 + 1e-10), -1, 1)

    # 10. SMA(200) distance
    if n >= 200:
        sma200 = pd.Series(c).rolling(200).mean().values
        feats[:, 9] = np.clip((c - sma200) / (c * 0.15 + 1e-10), -1, 1)

    # 11. High-low range normalized
    feats[:, 10] = np.clip((h - l) / (c + 1e-10), 0, 0.1) / 0.1

    # 12. Open-close body normalized
    feats[:, 11] = np.clip((c - o) / (c * 0.02 + 1e-10), -1, 1)

    # 13. Upper shadow ratio
    max_oc = np.maximum(o, c)
    feats[:, 12] = np.clip((h - max_oc) / (h - l + 1e-10), 0, 1)

    # 14. Lower shadow ratio
    min_oc = np.minimum(o, c)
    feats[:, 13] = np.clip((min_oc - l) / (h - l + 1e-10), 0, 1)

    # 15. Hour-of-day (cyclical encoding — sin component)
    if "timestamp" in df.columns:
        hours = df["timestamp"].dt.hour.values
        feats[:, 14] = np.sin(2 * np.pi * hours / 24)

    # Replace NaN/inf
    feats = np.nan_to_num(feats, nan=0.0, posinf=1.0, neginf=-1.0)
    return feats


def create_labels(df: "pd.DataFrame") -> "np.ndarray":
    """Create binary labels: [UP in 4h, UP in 24h]. Shape (N, 2)."""
    c = df["close"].values.astype(np.float64)
    n = len(c)
    labels = np.zeros((n, 2), dtype=np.float32)

    # 4h = 4 candles ahead
    for i in range(n - 4):
        labels[i, 0] = 1.0 if c[i + 4] > c[i] else 0.0

    # 24h = 24 candles ahead
    for i in range(n - 24):
        labels[i, 1] = 1.0 if c[i + 24] > c[i] else 0.0

    return labels


# ---------------------------------------------------------------------------
# Dataset & Model
# ---------------------------------------------------------------------------
if HAS_TORCH:
    class CryptoSequenceDataset(Dataset):
        """Sliding window dataset: 48 steps -> direction labels."""

        def __init__(self, features: np.ndarray, labels: np.ndarray, seq_len: int = SEQUENCE_LEN):
            self.seq_len = seq_len
            # Trim so last sequence has valid labels (24h lookahead)
            max_idx = len(features) - 24
            self.features = features
            self.labels = labels
            self.valid_len = max(0, max_idx - seq_len)

        def __len__(self):
            return self.valid_len

        def __getitem__(self, idx):
            x = self.features[idx: idx + self.seq_len]
            y = self.labels[idx + self.seq_len - 1]
            return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

    class GRUDirectionPredictor(nn.Module):
        """2-layer GRU for binary direction prediction (4h + 24h)."""

        def __init__(self, input_size=NUM_FEATURES, hidden_size=HIDDEN_SIZE,
                     num_layers=NUM_LAYERS, dropout=DROPOUT):
            super().__init__()
            self.gru = nn.GRU(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.dropout = nn.Dropout(dropout)
            self.fc = nn.Linear(hidden_size, 2)  # 4h, 24h

        def forward(self, x):
            # x: (batch, seq_len, features)
            out, _ = self.gru(x)
            out = out[:, -1, :]  # last timestep
            out = self.dropout(out)
            out = torch.sigmoid(self.fc(out))
            return out


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def build_dataset(symbols: list = None) -> tuple:
    """Fetch data for all symbols and build combined sequences + labels."""
    if symbols is None:
        symbols = SYMBOLS

    all_features = []
    all_labels = []

    for sym in symbols:
        log.info(f"Fetching {sym}...")
        df = fetch_ohlcv(sym)
        if df.empty or len(df) < SEQUENCE_LEN + 24 + 50:
            log.warning(f"Skipping {sym}: insufficient data ({len(df)} rows)")
            continue

        feats = engineer_features(df)
        labs = create_labels(df)
        all_features.append(feats)
        all_labels.append(labs)
        log.info(f"  {sym}: {len(df)} candles, features shape {feats.shape}")

    if not all_features:
        raise RuntimeError("No data fetched for any symbol")

    return np.concatenate(all_features, axis=0), np.concatenate(all_labels, axis=0)


def train_model(
    features: np.ndarray,
    labels: np.ndarray,
    epochs: int = EPOCHS,
    lr: float = LR,
    patience: int = PATIENCE,
    batch_size: int = BATCH_SIZE,
) -> dict:
    """Train GRU model. Returns metrics dict."""
    if not HAS_TORCH:
        raise RuntimeError("PyTorch not installed")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Training device: {device}")
    if device.type == "cuda":
        log.info(f"GPU: {torch.cuda.get_device_name(0)}")

    # Chronological split (no shuffle)
    n = len(features) - SEQUENCE_LEN - 24
    split_idx = int(n * (1 - VAL_SPLIT))

    train_ds = CryptoSequenceDataset(features[:split_idx + SEQUENCE_LEN + 24], labels[:split_idx + SEQUENCE_LEN + 24])
    val_ds = CryptoSequenceDataset(features[split_idx:], labels[split_idx:])

    log.info(f"Train sequences: {len(train_ds)}, Val sequences: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=(device.type == "cuda"))
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=(device.type == "cuda"))

    model = GRUDirectionPredictor().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss()

    best_val_loss = float("inf")
    best_epoch = 0
    best_state = None
    train_losses = []
    val_losses = []
    val_accuracies = []

    t0 = time.time()

    for epoch in range(1, epochs + 1):
        # --- Train ---
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            preds = model(x_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        train_loss = epoch_loss / max(n_batches, 1)
        train_losses.append(train_loss)

        # --- Validate ---
        model.eval()
        val_loss = 0.0
        correct_4h = 0
        correct_24h = 0
        total = 0
        with torch.no_grad():
            for x_batch, y_batch in val_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                preds = model(x_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * x_batch.size(0)
                pred_dir = (preds > 0.5).float()
                correct_4h += (pred_dir[:, 0] == y_batch[:, 0]).sum().item()
                correct_24h += (pred_dir[:, 1] == y_batch[:, 1]).sum().item()
                total += x_batch.size(0)

        val_loss = val_loss / max(total, 1)
        val_losses.append(val_loss)
        acc_4h = correct_4h / max(total, 1)
        acc_24h = correct_24h / max(total, 1)
        val_accuracies.append({"4h": acc_4h, "24h": acc_24h})

        log.info(
            f"Epoch {epoch:>3}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
            f"Val Acc 4h: {acc_4h:.3f} | Val Acc 24h: {acc_24h:.3f}"
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= patience:
            log.info(f"Early stopping at epoch {epoch} (best was {best_epoch})")
            break

    elapsed = time.time() - t0

    # Restore best model
    if best_state is not None:
        model.load_state_dict(best_state)

    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    save_dict = {
        "model_state_dict": best_state or model.state_dict(),
        "config": {
            "input_size": NUM_FEATURES,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "sequence_len": SEQUENCE_LEN,
        },
        "symbols": SYMBOLS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    torch.save(save_dict, str(MODEL_PATH))
    log.info(f"Model saved to {MODEL_PATH}")

    # Build metrics
    best_acc = val_accuracies[best_epoch - 1] if val_accuracies else {"4h": 0, "24h": 0}
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "symbols": SYMBOLS,
        "epochs_run": epoch,
        "best_epoch": best_epoch,
        "best_val_loss": round(best_val_loss, 5),
        "best_val_acc_4h": round(best_acc["4h"], 4),
        "best_val_acc_24h": round(best_acc["24h"], 4),
        "training_time_sec": round(elapsed, 1),
        "train_losses": [round(x, 5) for x in train_losses],
        "val_losses": [round(x, 5) for x in val_losses],
        "model_path": str(MODEL_PATH),
        "sequence_len": SEQUENCE_LEN,
        "num_features": NUM_FEATURES,
        "hidden_size": HIDDEN_SIZE,
        "num_layers": NUM_LAYERS,
    }

    with open(LOG_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    log.info(f"Training log saved to {LOG_PATH}")

    return metrics


# ---------------------------------------------------------------------------
# Export inference wrapper
# ---------------------------------------------------------------------------
def export_inference_wrapper():
    """Write a lightweight gru_inference.py next to the model file."""
    code = '''"""
Lightweight GRU inference wrapper — loads model on CPU.
Auto-generated by train_gru.py. Do not edit manually.
"""
import os
import json
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

MODELS_DIR = Path(__file__).resolve().parent


class GRUDirectionPredictor(nn.Module):
    """Mirror of training model architecture."""
    def __init__(self, input_size=15, hidden_size=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size, hidden_size=hidden_size,
            num_layers=num_layers, batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 2)

    def forward(self, x):
        out, _ = self.gru(x)
        out = out[:, -1, :]
        out = self.dropout(out)
        return torch.sigmoid(self.fc(out))


_model_cache = {}


def load_model():
    """Load model onto CPU (cached)."""
    if not HAS_TORCH:
        return None
    if "model" in _model_cache:
        return _model_cache["model"]

    model_path = MODELS_DIR / "gru_crypto.pt"
    if not model_path.exists():
        return None

    checkpoint = torch.load(str(model_path), map_location="cpu", weights_only=False)
    cfg = checkpoint.get("config", {})
    model = GRUDirectionPredictor(
        input_size=cfg.get("input_size", 15),
        hidden_size=cfg.get("hidden_size", 64),
        num_layers=cfg.get("num_layers", 2),
        dropout=cfg.get("dropout", 0.3),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    _model_cache["model"] = model
    _model_cache["config"] = cfg
    _model_cache["symbols"] = checkpoint.get("symbols", [])
    return model


def get_training_log():
    """Return training metrics if available."""
    log_path = MODELS_DIR / "training_log.json"
    if log_path.exists():
        with open(log_path) as f:
            return json.load(f)
    return None
'''
    wrapper_path = MODELS_DIR / "gru_inference.py"
    with open(wrapper_path, "w") as f:
        f.write(code)
    log.info(f"Inference wrapper exported to {wrapper_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not (HAS_TORCH and HAS_DEPS and HAS_REQUESTS):
        log.error("Missing dependencies. Install: pip install torch numpy pandas requests")
        sys.exit(1)

    log.info("=" * 60)
    log.info("Alpha Engine — GRU Training Pipeline")
    log.info("=" * 60)

    log.info(f"Symbols: {len(SYMBOLS)}")
    log.info(f"Sequence length: {SEQUENCE_LEN}h")
    log.info(f"Architecture: GRU({NUM_LAYERS} layers, {HIDDEN_SIZE} hidden)")
    log.info(f"Epochs: {EPOCHS}, LR: {LR}, Patience: {PATIENCE}")
    log.info("")

    features, labels = build_dataset()
    log.info(f"Total data: {features.shape[0]} rows, {features.shape[1]} features")

    metrics = train_model(features, labels)

    export_inference_wrapper()

    log.info("")
    log.info("=" * 60)
    log.info("Training Complete")
    log.info(f"  Device:        {metrics['device']}")
    if metrics.get("gpu_name"):
        log.info(f"  GPU:           {metrics['gpu_name']}")
    log.info(f"  Best epoch:    {metrics['best_epoch']}/{metrics['epochs_run']}")
    log.info(f"  Val loss:      {metrics['best_val_loss']}")
    log.info(f"  Val acc (4h):  {metrics['best_val_acc_4h']:.1%}")
    log.info(f"  Val acc (24h): {metrics['best_val_acc_24h']:.1%}")
    log.info(f"  Time:          {metrics['training_time_sec']:.0f}s")
    log.info(f"  Model:         {MODEL_PATH}")
    log.info("=" * 60)

    return metrics


if __name__ == "__main__":
    main()
