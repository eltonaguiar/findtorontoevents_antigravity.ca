# Local Run Activity Log

**Purpose:** Track all local GPU training runs, quick-guess sessions, and their results.

---

## 2026-03-18

### Session 1: Quick Guess Agent (01:00 - 05:00 UTC)
- **Duration:** ~4 hours
- **Symbols:** 3 active (BTC, ETH, SOL), 27 with dummy fallback models
- **Predictions made:** 2,136
- **Resolved:** 2,136
- **Accuracy:**
  - 5 min: 46% (774 samples)
  - 15 min: 44% (744 samples)
  - 60 min: 23% (618 samples) — auto-contrarian flip active
- **Notes:** Initial accuracy was 54% on 5min but regressed toward mean. BNB/XRP/DOGE had training errors (KeyError) — fixed with DummyClassifier fallback.
- **Auto-contrarian flips active:** BTC 15m, BTC 60m, ETH 60m, SOL 60m

### Session 2: GPU Training Pipeline (Built ~06:00 UTC)
- **Status:** Pipeline created, not yet run (agents building)
- **Files created:**
  - `local_gpu_trainer/train_gru.py` — GRU training script
  - `local_gpu_trainer/run_nightly.py` — Nightly orchestrator
  - `local_gpu_trainer/inference.py` — CPU inference for Alpha Engine
- **Model:** GRU, 2 layers, 64 hidden units, 48h lookback
- **Targets:** 4h and 24h price direction
- **Training data:** 15 symbols x 6 months hourly candles from Binance
- **First training run:** Pending (run `py -3.14 local_gpu_trainer/run_nightly.py`)

---

## Template for Future Entries

```
### Session N: [Type] (HH:MM - HH:MM UTC)
- **Duration:**
- **GPU used:** Yes/No
- **Training time:**
- **Model:** [GRU/Quick Guess/etc]
- **Accuracy before:** X%
- **Accuracy after:** Y%
- **Notes:**
```

---

## Quick Reference

| Metric | Current Value | Target | Trend |
|--------|--------------|--------|-------|
| Quick Guess 5min accuracy | 46% | >55% | Regressing |
| Quick Guess 15min accuracy | 44% | >55% | Regressing |
| GRU 4h accuracy | Not yet trained | >55% | N/A |
| GRU 24h accuracy | Not yet trained | >55% | N/A |
| Symbols active (Quick Guess) | 3/30 real, 27 dummy | 30/30 real | Improving |
| GPU training time | Not yet measured | <30s | N/A |
