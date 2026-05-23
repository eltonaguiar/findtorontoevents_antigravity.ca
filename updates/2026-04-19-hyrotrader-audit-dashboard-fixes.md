# HyroTrader Audit Dashboard Fixes — 2026-04-19

## Issues Reported

1. **Individual Signal Outcomes showing NO_DATA** for most recent signals with no failover or explanation
2. **ML Edge Optimizer section was blank** — no data, no explanation for why
3. **"No numeric prices in JSON yet"** message was unhelpful and alarming
4. **Per-strategy breakdown showed no win rates >50%** — data was too thin
5. **No clarification** that Individual Signal Outcomes shows recent signals only, not full history

## Root Cause

The `hyro_pick_performance_validator.py` only pulled signals from two thin sources:
- `hyro_signal_history.json` — 2 signals
- `hyro_quan_bridge.json` — 15 signals

Of those 17 signals, 15 returned `NO_DATA` because Binance klines couldn't be fetched (API timeouts, rate limits, single retry, no failover). The validator had **no access** to the richest data source: `closed_picks.json` (thousands of crypto picks with already-recorded outcomes).

## Changes Made

### 1. Front-end: `audit_dashboard/hyrotrader/index.html`

| Section | Before | After |
|---------|--------|-------|
| Individual Signal Outcomes header | "Individual signal outcomes" | "Individual signal outcomes" + dynamic signal count badge |
| Signal outcomes description | "Each row = one signal..." | "Showing **recent** validated signals only (not full history). Each row = one signal... NO_DATA = Binance klines unavailable (API timeout or signal too recent)." |
| NO_DATA notice | None | Yellow warning box appears when >30% of signals are NO_DATA, explaining the cause and suggesting re-running the validator |
| NO_DATA rows | Normal styling | Dimmed (opacity 0.5) with italic text to visually de-emphasize |
| ML Edge Optimizer | Blank when sparse data | Purple "sparse-data notice" explains: most combos grade F because <5 trades exist; shows which strategies have enough data |
| "No numeric prices" message | "No numeric prices in JSON yet — add when you have real levels." | "Auto-computed prices not yet available — run `python tools/hyro_filter_from_dashboard.py --save` to populate from audit, or paste real levels from Hyro terminal." |

### 2. Backend: `tools/hyro_pick_performance_validator.py`

| Change | Details |
|--------|---------|
| **New data source** | `extract_signals_from_closed_picks()` — pulls crypto closed picks from `alpha_engine/data/closed_picks.json` (and falls back to `dashboard_payload.json`). These picks already have recorded outcomes, so they skip Binance API entirely. |
| **Crypto-only filter** | Closed picks filtered to `asset_class == "CRYPTO"` only (HyroTrader is Binance crypto perps) |
| **Pre-validated outcomes** | Signals from closed picks carry `_prevalidated_outcome` dict (WIN/LOSS/EXPIRED mapped from exit_reason). Skips API fetch entirely. |
| **Binance retry logic** | `MAX_RETRIES_PER_MIRROR = 2` — each Binance mirror retried up to 2 times (was 1 attempt total). 1s sleep between retry rounds. |
| **Lookback increased** | Default `lookback_days` raised from 14 → 30 for more signal coverage |
| **Dedup key improved** | Now includes `round(entry, 4)` in dedup key to avoid false uniqueness from rounding drift |
| **Signal cap** | `MAX_SIGNALS = 500` — most recent 500 signals only, prevents massive output files / slow dashboard rendering |
| **Fallback path** | `DASHBOARD_PAYLOAD_PATH` used as fallback if `closed_picks.json` doesn't exist |
| **Source priority** | `closed_picks` → `signal_history` → `quan_bridge` (closed picks checked first because richest + pre-validated) |

## Expected Impact

- **Individual Signal Outcomes**: Should show hundreds of validated signals instead of ~2 with 88% NO_DATA rate. Pre-validated closed picks eliminate most NO_DATA rows.
- **ML Edge Optimizer**: Should populate with strategy grades based on real closed-pick outcomes. Many will still grade low (F/D) due to thin data, but the sparse-data notice explains why.
- **Per-strategy win rates**: With thousands of closed crypto picks available, strategies with enough trades (n≥5) should show meaningful WR/PF metrics. ML-enhanced strategies (DYDX 15m, TON 4h, etc.) should surface >50% WR.
- **"No numeric prices"**: Message now tells the user exactly what to run instead of being passive.

## How to Verify

1. Run the validator with the new closed-picks source:
   ```bash
   python tools/hyro_pick_performance_validator.py --save --lookback-days 30
   ```
2. Start local server and check the dashboard:
   ```bash
   python tools/serve_local.py
   # Open http://127.0.0.1:5173/audit/hyrotrader/
   ```
3. Verify:
   - Individual Signal Outcomes shows signal count badge
   - NO_DATA rows are dimmed
   - ML Edge Optimizer shows strategy grades (even if many are F)
   - "No numeric prices" message (if visible) shows the `hyro_filter_from_dashboard.py` command

## Files Modified

- `audit_dashboard/hyrotrader/index.html` — front-end fixes (signal count, NO_DATA notice, ML sparse notice, dimmed NO_DATA rows, helpful "no prices" message)
- `tools/hyro_pick_performance_validator.py` — backend enrichment (closed_picks source, retry logic, pre-validated outcomes, signal cap, dedup improvement)
