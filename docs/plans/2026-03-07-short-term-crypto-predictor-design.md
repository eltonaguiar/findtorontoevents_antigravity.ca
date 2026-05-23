# Short-Term Crypto Predictor — Design

## Overview
Extend `claude_gainer_ml` with 1h/4h prediction modes. Reuses the existing
feedback loop (TP/SL tracker + self-improver + online retraining + drift detection)
and adds 10 features from `crypto_ml_edge` (funding rates, Fear & Greed, ATR, S/R).

## Approach
**Approach A: Extend Claude Gainer ML** — chosen because it already has the full
self-learning pipeline. `crypto_ml_edge` has better features but no feedback loop.

## Architecture
```
Binance 1h/4h klines + Funding Rates + F&G API
    → Feature Engine (30 original + 10 new = 40 features)
    → RF + XGBoost ensemble inference
    → TP/SL computation (ATR-based, per timeframe)
    → Picks → MySQL now_history + JSON files
    → Self-improver loop (retrains from resolved picks)
```

## New Features (from crypto_ml_edge)
1. `funding_rate` — live Binance futures funding
2. `funding_zscore` — 20-period z-score of funding rate
3. `funding_momentum` — 3-bar change in funding
4. `fear_greed_current` — live F&G index (0-100)
5. `fear_greed_7d_avg` — 7-day F&G average
6. `fear_greed_momentum` — F&G current - 7d avg
7. `atr_pct` — ATR(14) as % of close
8. `vol_percentile` — volume rank in 90-bar window
9. `sr_dist_high` — distance from 20-bar swing high
10. `sr_dist_low` — distance from 20-bar swing low

## Timeframe Configs
| TF | TP (ATR×) | SL (ATR×) | Max Hold | Label |
|----|-----------|-----------|----------|-------|
| 1h | 2.5×      | 1.5×      | 12 bars  | +1.5% |
| 4h | 3.5×      | 2.0×      | 8 bars   | +3.0% |

## Self-Learning Loop
1. TP/SL Tracker: resolves open picks against live prices each scan
2. Online Learning: resolved picks → labeled rows → training data
3. Auto-Retrain: at 10+ new samples OR 7 days since last train
4. Drift Detection: rolling 20-pick precision <40% → alert + force retrain
5. Adaptive Threshold: confidence threshold adjusts from recent accuracy

## Integration
- MySQL: `now_history` table, `source = 'CLAUDE_GAINER_ST'`
- JSON: `claude_gainer_ml/tracker/short_term_picks.json`
- Audit: auto-loaded via `JSON_PICK_SOURCES`
- Discord: #fresh-picks via freshpicks_notify
- Actions: `claude-gainer-short-term.yml` every 30 min

## Pairs
Top 20 USDT by volume (smaller set — ML inference is slower than rule-based)

## Files
- `claude_gainer_ml/short_term_scanner.py` — main scanner
- `.github/workflows/claude-gainer-short-term.yml` — automation
