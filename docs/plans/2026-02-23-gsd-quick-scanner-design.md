# GSD Quick Scanner — Design Document

**Date:** 2026-02-23
**Goal:** Get the Crypto ML Edge Engine generating viable picks within 5 hours by aggregating proven, battle-tested strategies — no ML training required.
**Deadline:** 10:00 PM EST tonight

## Problem

The full GSD Crypto ML Edge Engine requires trained ML models that pass a DSR > 0.95 gate. No models pass yet, so `active_picks.json` has zero picks and the dashboard is empty. Meanwhile, 3 proven strategies in `alpha_engine/` are generating real signals RIGHT NOW but aren't wired into the Edge Engine pipeline.

## Solution

Build `crypto_ml_edge/quick_scanner.py` — an aggregator that:
1. Calls 3 proven strategies from `alpha_engine/`
2. Normalizes their output into the existing `active_picks.json` schema
3. Enriches each pick with EST timestamps and full audit trail
4. Feeds into the existing dashboard, Discord, and TP/SL tracking pipeline

## Architecture

```
crypto_ml_edge/quick_scanner.py
    ├── call alpha_engine/connors_rsi2.generate_signals()
    │   └── 8 symbols: SPY, QQQ, IWM, GLD, TLT, BTC-USD, ETH-USD, SOL-USD
    │   └── 75.7% WR proven (Connors & Alvarez 2008)
    │
    ├── call alpha_engine/funding_rate_scanner.run_scan()
    │   └── 10 Binance perps: BTC, ETH, SOL, BNB, AVAX, LINK, DOGE, XRP, ADA, MATIC
    │   └── 71% WR on negative funding carry
    │
    ├── call alpha_engine/vix_spike_reversal.generate_signals()
    │   └── VIX spike (SPY), extreme level (SPY), crypto fear capitulation (BTC/ETH/SOL)
    │   └── 72% WR, HIGHEST CONVICTION in current F&G=14 regime
    │
    ├── normalize_to_edge_pick() — convert each strategy's dict → active_picks.json pick format
    ├── add_audit_trail() — strategy name, reasons, academic source, market regime, EST timestamp
    ├── assign_tier() — HIGH (conf >= 0.75 & RR >= 2.0), MEDIUM (conf >= 0.65), WATCH (rest)
    ├── deduplicate() — same symbol + same direction within 24h = skip
    │
    └── merge into crypto_ml_edge/data/active_picks.json
        └── existing track_picks() handles TP/SL closure
        └── existing dashboard reads this file
        └── existing Discord notification fires
```

## Pick Schema (Extended)

Each pick in `active_picks.json` `picks[]` array:

```json
{
  "id": "connors_rsi2::BTCUSD::2026-02-23T22:30",
  "pair": "BTCUSDT",
  "symbol_display": "BTC-USD",
  "timeframe": "1d",
  "direction": "long",
  "confidence": 0.80,
  "tier": "HIGH",
  "entry_price": 96500.00,
  "tp_price": 98430.00,
  "sl_price": 95535.00,
  "position_size_usd": 500.00,
  "position_size_pct": 0.05,
  "risk_reward_ratio": 2.0,
  "max_hold_bars": 48,
  "signal_time": "2026-02-23T22:30:00Z",
  "signal_time_est": "2026-02-23 05:30:00 PM EST",
  "source": "quick_engine",
  "status": "active",
  "bars_held": 0,
  "audit": {
    "strategy_id": "connors_rsi2",
    "strategy_name": "Connors RSI-2 Mean Reversion",
    "reasons": [
      "RSI-2 = 3.2 (EXTREME OVERSOLD, threshold < 5)",
      "Connors RSI = 8.1 (below 10 buy threshold)",
      "Price above 200-day SMA (trend filter: BULL)"
    ],
    "academic_source": "Connors & Alvarez (2008) — 75.7% WR on SPY backtest",
    "market_regime": "extreme_fear",
    "fear_greed_index": 14,
    "strategy_indicators": {
      "rsi2": 3.2,
      "connors_rsi": 8.1,
      "atr14": 965.0,
      "sma200": 92000.0
    },
    "confidence_factors": [
      "Base confidence: 0.73",
      "CRSI < 10 bonus: +0.07",
      "Above 200 SMA: no penalty"
    ]
  }
}
```

## Current Market Regime (Research)

As of Feb 23, 2026:
- **Crypto Fear & Greed: 14** (Extreme Fear — near FTX/COVID lows)
- **BTC: ~$96K** (down from $126K ATH, -24%)
- **VIX: ~19** (moderate, not spiking)
- **Funding rates: near zero** (+0.004%/8h avg — low yield environment)

**Strategy effectiveness in current regime:**
| Strategy | Current Signal Strength | Notes |
|---|---|---|
| VIX/Fear Contrarian | HIGHEST | F&G=14, every historical extreme fear → recovery |
| Connors RSI-2 | MODERATE | Works if RSI-2 < 5 fires on BTC/ETH; trend filter important |
| Funding Rate Carry | LOW | Near-zero rates in fear regime; few exploitable anomalies |

## Dashboard Updates

Extend `crypto_ml_edge/dashboard/index.html` to:
1. Show **tier badges** (HIGH=green, MEDIUM=yellow, WATCH=gray) per pick
2. Show **EST timestamps** prominently (not just UTC)
3. Add expandable **"Why this pick?"** audit panel per pick showing:
   - Strategy name and academic source
   - Bullet-point reasons
   - Key indicator values
   - Confidence breakdown
4. Add **"Last Scan"** indicator with EST time in the header
5. Show **strategy breakdown** count (e.g., "2 RSI-2, 1 Funding, 3 Fear/Greed")
6. Show **market regime** badge in header

## Discord Notification Updates

Extend each pick line in the embed to show:
- Strategy name
- First reason as one-liner
- Tier badge emoji (HIGH=green circle, MEDIUM=yellow, WATCH=white)

## Workflow Changes

Update `.github/workflows/crypto-ml-edge.yml`:
- Cron: `*/30 * * * *` (every 30 minutes)
- Add `quick_scanner.py` call BEFORE the ML scanner
- Quick scanner writes picks → ML scanner runs (no-ops if no models) → track_picks closes any TP/SL
- Same commit + deploy steps

## Deduplication Rules

- Pick ID format: `{strategy_id}::{pair}::{date}` (one pick per strategy per pair per day)
- If a pick already exists in `active_picks.json` with same ID and status=active, skip
- Closed picks are never overwritten

## Position Sizing

- Capital base: $10,000 (simulated)
- Per-pick max: 5% ($500)
- Use `compute_position_size()` from `crypto_ml_edge/risk.py` when ATR is available
- Fallback: fixed 3% for strategies without ATR data (funding rate)

## File Changes

| File | Action |
|---|---|
| `crypto_ml_edge/quick_scanner.py` | **CREATE** — Main aggregator |
| `crypto_ml_edge/dashboard/index.html` | **EDIT** — Add tier badges, audit panel, EST timestamps, strategy breakdown |
| `crypto_ml_edge/discord_notify.py` | **EDIT** — Add strategy name + reason to pick lines |
| `.github/workflows/crypto-ml-edge.yml` | **EDIT** — 30-min cron, add quick_scanner step |
| `crypto_ml_edge/scanner.py` | **EDIT** — Make track_picks() handle new audit field gracefully |

## Success Criteria

1. Running `quick_scanner.py` produces real picks in `active_picks.json` within minutes
2. Dashboard at `/edge/` shows picks with audit trail and EST timestamps
3. Discord notification fires with strategy names and dashboard link
4. GitHub Actions runs every 30 min, commits new picks, deploys dashboard
5. TP/SL tracking works — picks close automatically when targets hit
