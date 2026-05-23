# Local GPU Training Pipeline — Alpha Engine

Trains a GRU deep learning model locally on your GPU, exports weights for CPU inference in CI.

## Quick Start

```bash
# Install dependencies
pip install torch numpy pandas requests

# Run training (auto-detects GPU)
py -3.14 local_gpu_trainer/run_nightly.py

# Run training + push weights to GitHub
py -3.14 local_gpu_trainer/run_nightly.py --push
```

## Schedule Nightly Training (Windows Task Scheduler)

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task > Name: "Alpha GRU Training"
3. Trigger: Daily, 12:00 AM
4. Action: Start a program
   - Program: `py`
   - Arguments: `-3.14 local_gpu_trainer/run_nightly.py --push`
   - Start in: `E:\findtorontoevents_antigravity.ca`
5. Finish. The task runs during off-hours when your GPU is free.

## Architecture

```
Input:  48 hourly candles x 15 features
Model:  GRU(2 layers, 64 hidden) -> Dropout(0.3) -> Linear(2)
Output: P(UP) for 4h and 24h horizons
Loss:   Binary Cross-Entropy
```

### 15 Features (matches Alpha Engine indicators)

| # | Feature | Range |
|---|---------|-------|
| 1 | Log returns | unbounded |
| 2 | RSI(14) | 0-1 |
| 3 | Bollinger Band position | 0-1 |
| 4 | Volume ratio (vs 20-SMA) | 0-1 |
| 5 | ATR(14) normalized | 0-1 |
| 6 | VWAP distance | -1 to 1 |
| 7 | SMA(9) distance | -1 to 1 |
| 8 | SMA(21) distance | -1 to 1 |
| 9 | SMA(50) distance | -1 to 1 |
| 10 | SMA(200) distance | -1 to 1 |
| 11 | High-low range | 0-1 |
| 12 | Open-close body | -1 to 1 |
| 13 | Upper shadow ratio | 0-1 |
| 14 | Lower shadow ratio | 0-1 |
| 15 | Hour-of-day (sin) | -1 to 1 |

## Tuning Parameters

Edit constants at the top of `train_gru.py`:

| Parameter | Default | Notes |
|-----------|---------|-------|
| `SEQUENCE_LEN` | 48 | Input window (hours). Try 24-96. |
| `HIDDEN_SIZE` | 64 | GRU hidden units. Try 32-128. |
| `NUM_LAYERS` | 2 | GRU depth. 1-3 is reasonable. |
| `DROPOUT` | 0.3 | Regularization. 0.1-0.5. |
| `LR` | 0.001 | Learning rate. Try 0.0005-0.002. |
| `EPOCHS` | 50 | Max epochs (early stopping). |
| `PATIENCE` | 7 | Stop after N epochs without improvement. |
| `BATCH_SIZE` | 256 | Reduce if GPU runs out of memory. |

## Adding/Removing Symbols

Edit the `SYMBOLS` list in `train_gru.py`:

```python
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", ...
]
```

## How It Integrates

The Alpha Engine's `forward_validator.py` imports `predict_direction()` from `local_gpu_trainer/inference.py`. When a trained model exists:

- Fetches recent 1h candles for the signal's symbol
- Runs GRU inference on CPU (no GPU needed)
- If confidence > 60%, adds +5 (agree) or -5 (disagree) to `elite_score`
- Prediction is stored in `signal['gru_prediction']`

If PyTorch is not installed or no model file exists, the integration silently does nothing.

## File Structure

```
local_gpu_trainer/
  train_gru.py          # Training script (run on GPU)
  inference.py          # CPU inference for Alpha Engine
  run_nightly.py        # Nightly orchestrator
  models/
    gru_crypto.pt       # Trained model weights (generated)
    gru_inference.py    # Lightweight loader (auto-generated)
    training_log.json   # Metrics from last training run (generated)
```
