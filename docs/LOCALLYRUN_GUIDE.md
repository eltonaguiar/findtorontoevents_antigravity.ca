# Local Run Guide — GPU Training & Local Scanning

**Last Updated:** 2026-03-18 06:00 UTC

## Overview

This guide covers everything that runs LOCALLY on your machine (not on GitHub Actions). Two main systems:

1. **GPU Training Pipeline** — Trains deep learning models (GRU) on your GPU overnight
2. **Quick Guess ML Agent** — Runs predictions every 60 seconds locally

---

## 1. GPU Training Pipeline

### What It Does
Trains a GRU (Gated Recurrent Unit) neural network on your local GPU using 6 months of hourly crypto candles. The trained model predicts price direction (UP/DOWN) for the next 4h and 24h.

### Files
| File | Purpose |
|------|---------|
| `local_gpu_trainer/train_gru.py` | Main training script — fetches data, trains GRU, saves model |
| `local_gpu_trainer/run_nightly.py` | Nightly orchestrator — runs training + pushes to GitHub |
| `local_gpu_trainer/inference.py` | CPU inference — loads model and makes predictions |
| `local_gpu_trainer/models/gru_crypto.pt` | Trained model weights (~1MB) |
| `local_gpu_trainer/models/training_log.json` | Training metrics (loss, accuracy, time) |
| `local_gpu_trainer/README.md` | Quick reference |

### How to Run

**Manual training:**
```bash
cd e:/findtorontoevents_antigravity.ca
py -3.14 local_gpu_trainer/run_nightly.py
```

**Schedule nightly (Windows Task Scheduler):**
1. Open Task Scheduler → Create Basic Task
2. Name: "Alpha Engine GPU Training"
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
   - Program: `C:\Users\zerou\AppData\Local\Programs\Python\Python314\python.exe`
   - Arguments: `local_gpu_trainer/run_nightly.py`
   - Start in: `E:\findtorontoevents_antigravity.ca`
5. Check "Run whether user is logged on or not"

### How to Tweak

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `LEARNING_RATE` | train_gru.py | 0.001 | Lower = stable but slow. Higher = fast but unstable |
| `HIDDEN_SIZE` | train_gru.py | 64 | Model capacity. 32=light, 128=heavy |
| `SEQ_LENGTH` | train_gru.py | 48 | Hours of lookback. 24=1day, 72=3days |
| `NUM_EPOCHS` | train_gru.py | 50 | Max training iterations (early stopping active) |
| `SYMBOLS` | train_gru.py | 15 cryptos | Add/remove from the list |
| `DROPOUT` | train_gru.py | 0.3 | Regularization. Higher = less overfitting |

### GPU Impact
- Training: 5-10 seconds, ~100-200MB GPU RAM
- Zero impact on gaming or other GPU tasks
- Model inference runs on CPU (no GPU needed for predictions)

### How It Connects to Alpha Engine
The trained model is loaded by `local_gpu_trainer/inference.py`. The Alpha Engine's `forward_validator.py` calls it:
- If GRU agrees with pick direction: +5 elite_score
- If GRU disagrees: -5 elite_score
- If model not available: silently skipped (no impact)

---

## 2. Quick Guess ML Agent

### What It Does
Makes short-term price predictions (1m to 1 week) for 30 crypto symbols using GradientBoosting. Learns from outcomes and retrains every 20 minutes.

### Files
| File | Purpose |
|------|---------|
| `parallel_agent/quick_guess_agent.py` | The agent — fetches data, trains, predicts |
| `parallel_agent/run_local.py` | Local continuous runner (predict every 60s) |
| `parallel_agent/data/guess_history.json` | All predictions + outcomes |
| `parallel_agent/data/guess_stats.json` | Accuracy stats by symbol/horizon |
| `parallel_agent/data/guess_models.pkl` | Persisted models |
| `parallel_agent/data/latest_predictions.json` | Latest predictions for Alpha Engine |

### How to Run

**Start continuous local scanning:**
```bash
cd e:/findtorontoevents_antigravity.ca
py -3.14 parallel_agent/run_local.py
```
Press Ctrl+C to stop (saves state automatically).

**Run single cycle (test):**
```bash
py -3.14 -c "
from parallel_agent.quick_guess_agent import QuickGuessAgent
agent = QuickGuessAgent()
agent.train()
preds = agent.predict_all()
for p in preds[:10]:
    d = 'UP' if p['prob_up'] > 0.55 else ('DN' if p['prob_up'] < 0.45 else '--')
    print(f'{p[\"symbol\"]:>12} +{p[\"horizon\"]:>5}m {d} {p[\"prob_up\"]:.1%}')
"
```

### How to Tweak

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `SYMBOLS` | quick_guess_agent.py line 30 | 30 cryptos | Add/remove symbols |
| `HORIZONS` | quick_guess_agent.py line 43 | [1,3,5,15,60,240,4320,10080] | Prediction timeframes in minutes |
| `MIN_SAMPLES_TRAIN` | quick_guess_agent.py line 52 | 20 | Min data points before training |
| `RETRAIN_INTERVAL` | quick_guess_agent.py line 50 | 20 min | How often to retrain |

### Current Performance (as of Mar 18)
| Horizon | Accuracy | Samples |
|---------|----------|---------|
| 5 min | 46% | 774 |
| 15 min | 44% | 744 |
| 60 min | 23% (auto-flipped) | 618 |

### Auto-Contrarian Feature
When a symbol+horizon is consistently wrong (<40% accuracy on 20+ samples), the agent automatically FLIPS its prediction. A consistently wrong model is just as useful as a consistently right one.

---

## 3. GitHub Actions (Remote)

These run automatically — no local action needed:

| Workflow | Frequency | What It Does |
|----------|-----------|-------------|
| `alpha-engine-live.yml` | Every 10 min | Full scanner + ML training + pick generation |
| `quick-guess-ml.yml` | Every 10 min | Quick guess predictions (remote backup) |
| `kimi-feb172026-live.yml` | Every 30 min | KIMI scanner (re-enabled) |
| `claude-gainer-tracker.yml` | Every ~8h | Claude Gainer ML training |

---

## 4. Recommended Daily Routine

| Time (EST) | Activity | How |
|-----------|----------|-----|
| **2:00 AM** | GPU training (auto) | Scheduled via Task Scheduler |
| **Morning** | Check results | Open `local_gpu_trainer/models/training_log.json` |
| **Anytime** | Start local scanner | `py -3.14 parallel_agent/run_local.py` |
| **Anytime** | Check predictions | Open `parallel_agent/data/latest_predictions.json` |
| **Anytime** | Check portfolio | Open `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/` |

---

## 5. Troubleshooting

| Issue | Fix |
|-------|-----|
| `No module named 'torch'` | `py -3.14 -m pip install torch` |
| `No module named 'pandas'` | `py -3.14 -m pip install pandas scikit-learn` |
| GPU not detected | Check `py -3.14 -c "import torch; print(torch.cuda.is_available())"` |
| Quick guess stuck | Delete `parallel_agent/data/guess_models.pkl` and restart |
| Training too slow | Reduce `NUM_EPOCHS` or `SEQ_LENGTH` |
| Bad predictions | Check `training_log.json` — if val_loss increasing, model is overfitting. Increase DROPOUT. |
