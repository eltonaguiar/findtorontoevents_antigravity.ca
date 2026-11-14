# Crypto Deep Dive Audit Report

**Audit Date:** 2026-11-14T15:52:38Z  
**Dashboard URL:** https://findtorontoevents.ca/audit  
**Dashboard Data Generated At:** 2026-11-14T14:30:07.135931+00:00  
**Binance Prices Fetched At:** 2026-11-14T15:52:38Z  
**Auditor:** Kilo  

---

## Executive Summary

- **Total Active Picks (all asset classes):** 20
- **Crypto Active Picks:** 3 (15% of active book)
- **All Crypto Picks Are SHORT direction** (bearish bias aligned with dashboard's "htf_bias": "BEAR")
- **Live vs Stale Verdict:** 2 picks are genuinely live (price has moved), 1 pick's current_price is stale (unchanged from entry). However, **all 3 dashboard `current_price` values are stale relative to live Binance prices**.
- **PnL Accuracy:** Dashboard understates PnL on all 3 picks when compared to live Binance prices.
- **Forward Validation:** None of the 3 active crypto picks have forward-validated track records (`forward_validated=false`, `forward_trades=0`).

---

## 1. Active Crypto Picks — Full Detail

### Pick 1: NEARUSDT SHORT

| Field | Dashboard Claim | Live Verification | Discrepancy |
|-------|----------------|-------------------|-------------|
| **Symbol** | NEARUSDT | NEARUSDT | — |
| **Direction** | SHORT | SHORT | — |
| **Entry Price** | 3.324 | 3.324 | — |
| **Claimed Current Price** | 3.233 | **3.209** (Binance) | **-0.024** (dashboard is stale) |
| **Claimed PnL %** | 2.74% | **3.46%** (calculated from live) | **+0.72pp** dashboard under-reports |
| **Timestamp** | 2026-11-14T13:10:05Z | 2026-11-14T13:10:05Z | — |
| **Claimed Age** | 1.3h | 1.33h (vs generated_at 14:30:07Z) | Accurate |
| **Verified Age (now)** | — | 2.71h (vs 15:52:38Z) | Dashboard is ~1.4h stale |
| **Data Source** | tsmom_strategy / tsmom_volscaled | — | — |
| **Agreeing Systems** | alpha_engine, inverse_mutations | — | 2 systems |
| **Total Source Systems** | 7 | — | — |
| **Edge (forward_wr)** | 0% | — | NO DATA |
| **FWD WR %** | 0% | — | NO DATA |
| **FWD N** | 0 | — | NO DATA |
| **sym_dir_fwd_wr** | 50.0% | — | n=82, pf=1.366 |
| **Trust Score** | 3 (LOW) | — | WATCH tier |
| **Track Level** | none | — | — |
| **Status** | OPEN | — | — |
| **Conflict** | Has direction conflict (resolved SHORT) | — | — |
| **Antigravity Safe** | false | — | Paper only |

**Notes:**  
- `_backfilled: true` — this pick was backfilled, not real-time emitted.
- `_dup_cross: true` — cross-feed duplicate detected.
- `_emitter_registry_would_block: true` — registry gate would block this emitter but `enforce_block: false`.

---

### Pick 2: XRPUSDT SHORT

| Field | Dashboard Claim | Live Verification | Discrepancy |
|-------|----------------|-------------------|-------------|
| **Symbol** | XRPUSDT | XRPUSDT | — |
| **Direction** | SHORT | SHORT | — |
| **Entry Price** | 0.9842 | 0.9842 | — |
| **Claimed Current Price** | 0.9842 | **0.9698** (Binance) | **-0.0144** (dashboard is stale) |
| **Claimed PnL %** | 0.0% | **1.46%** (calculated from live) | **+1.46pp** dashboard shows flat |
| **Timestamp** | 2026-11-14T13:53:28Z | 2026-11-14T13:53:28Z | — |
| **Claimed Age** | 0.6h | 0.61h (vs generated_at 14:30:07Z) | Accurate |
| **Verified Age (now)** | — | 1.98h (vs 15:52:38Z) | Dashboard is ~1.4h stale |
| **Data Source** | kalshi_signal_agent / kalshi_mtf_consensus | — | — |
| **Agreeing Systems** | alpha_engine (prediction_market_consensus) | — | 1 system |
| **Total Source Systems** | 9 | — | — |
| **Edge (forward_wr)** | 0% | — | NO DATA |
| **FWD WR %** | 0% | — | NO DATA |
| **FWD N** | 0 | — | NO DATA |
| **sym_dir_fwd_wr** | 51.7% | — | n=60, pf=1.687 |
| **Trust Score** | 4 (LOW) | — | WATCH tier |
| **Track Level** | none | — | — |
| **Status** | OPEN | — | — |
| **Type Label** | PM Kalshi | — | — |
| **Antigravity Safe** | false | — | Paper only |

**Notes:**  
- `research_cohort: verified_alpha` — assigned to verified-alpha cohort.
- `_verified_alpha_bonus: 6` — received verified alpha bonus in scoring.
- `_phase1_dz_shadow_reject` is NOT present (unlike BTC).
- `_backfilled: true` — backfilled pick.

---

### Pick 3: BTCUSDT SHORT

| Field | Dashboard Claim | Live Verification | Discrepancy |
|-------|----------------|-------------------|-------------|
| **Symbol** | BTCUSDT | BTCUSDT | — |
| **Direction** | SHORT | SHORT | — |
| **Entry Price** | 66300.0 | 66300.0 | — |
| **Claimed Current Price** | 66300.0 | **65658.01** (Binance) | **-641.99** (dashboard is stale) |
| **Claimed PnL %** | 0.0% | **0.97%** (calculated from live) | **+0.97pp** dashboard shows flat |
| **Timestamp** | 2026-11-14T13:53:28Z | 2026-11-14T13:53:28Z | — |
| **Claimed Age** | 0.6h | 0.61h (vs generated_at 14:30:07Z) | Accurate |
| **Verified Age (now)** | — | 1.98h (vs 15:52:38Z) | Dashboard is ~1.4h stale |
| **Data Source** | kalshi_signal_agent / kalshi_mtf_consensus | — | — |
| **Agreeing Systems** | genetic_programmer, mape_evolver, mutation_lab, forward_signals, contrarian_consensus | — | 5 systems |
| **Total Source Systems** | 13 | — | — |
| **Edge (forward_wr)** | 0% | — | NO DATA |
| **FWD WR %** | 0% | — | NO DATA |
| **FWD N** | 0 | — | NO DATA |
| **sym_dir_fwd_wr** | 39.1% | — | n=46, pf=0.718 |
| **Trust Score** | 4 (LOW) | — | WATCH tier |
| **Track Level** | none | — | — |
| **Status** | OPEN | — | — |
| **Type Label** | PM Kalshi | — | — |
| **Antigravity Safe** | false | — | Paper only |
| **Technical Verdict** | STRONG SELL | — | 0/3 BUY timeframes |

**Notes:**  
- `_phase1_dz_shadow_reject: "confidence=0.673 in dead zone [0.65, 0.75)"` — this pick was shadow-rejected in phase 1 for confidence dead-zone.
- `_opposing_killed: true` — an opposing direction pick was killed.
- `_backfilled: true` — backfilled pick.
- `technical_alignment: false` but `strong: true` — contradictory flags.

---

## 2. Live Binance Prices vs Dashboard Prices

| Symbol | Dashboard Current | Binance Live | Delta (USDT) | Delta % |
|--------|-------------------|--------------|--------------|---------|
| NEARUSDT | 3.233 | **3.209** | -0.024 | -0.74% |
| XRPUSDT | 0.9842 | **0.9698** | -0.0144 | -1.46% |
| BTCUSDT | 66300.0 | **65658.01** | -641.99 | -0.97% |

**Observation:** All 3 dashboard `current_price` values are **stale** and higher than live prices. For SHORT positions, this means the dashboard **understates profitable PnL**. NEAR is closest to live, while XRP and BTC are completely flat (equal to entry price in dashboard).

---

## 3. Calculated PnL from Live Prices

| Symbol | Direction | Entry | Live Price | Calc PnL % | Claimed PnL % | Discrepancy |
|--------|-----------|-------|------------|------------|---------------|-------------|
| NEARUSDT | SHORT | 3.324 | 3.209 | **3.46%** | 2.74% | +0.72pp |
| XRPUSDT | SHORT | 0.9842 | 0.9698 | **1.46%** | 0.00% | +1.46pp |
| BTCUSDT | SHORT | 66300.0 | 65658.01 | **0.97%** | 0.00% | +0.97pp |

---

## 4. Timestamp Freshness Audit

| Symbol | Signal Timestamp | Dashboard Age Claim | Age vs generated_at (14:30:07Z) | Age vs Now (15:52:38Z) | Accuracy |
|--------|------------------|---------------------|----------------------------------|------------------------|----------|
| NEARUSDT | 13:10:05Z | 1.3h | 1.33h | 2.71h | **Accurate relative to generated_at** |
| XRPUSDT | 13:53:28Z | 0.6h | 0.61h | 1.98h | **Accurate relative to generated_at** |
| BTCUSDT | 13:53:28Z | 0.6h | 0.61h | 1.98h | **Accurate relative to generated_at** |

**Conclusion:** The `age_hours` field is computed correctly relative to `generated_at` (dashboard generation time), not wall-clock now. The dashboard data itself is **~1h 22m stale** at time of audit. The HTML has a `<meta http-equiv="refresh" content="300">` (5-minute auto-refresh), but the underlying JSON data updates on an hourly cron, so the effective staleness is ~1-2 hours.

---

## 5. Flat / Null / Zero PnL Count

| Symbol | Claimed PnL % | Category |
|--------|---------------|----------|
| NEARUSDT | 2.74% | Non-zero |
| XRPUSDT | 0.0% | **Flat / Zero** |
| BTCUSDT | 0.0% | **Flat / Zero** |

- **2 out of 3 crypto active picks (66.7%) show 0.0% PnL** in the dashboard.
- **All 3 picks show non-zero PnL when recalculated from live Binance prices.**
- No picks show `null` PnL.

---

## 6. Metrics Per Pick — Edge, Track, FWD WR%, FWD N

| Symbol | forward_wr | forward_trades | forward_validated | forward_status | track_level | sym_track_total | sym_dir_fwd_wr | sym_dir_fwd_n | sym_dir_fwd_pf |
|--------|------------|----------------|-------------------|----------------|-------------|-----------------|----------------|---------------|----------------|
| NEARUSDT | 0% | 0 | **false** | NO_DATA | none | 0 | 50.0% | 82 | 1.366 |
| XRPUSDT | 0% | 0 | **false** | NO_DATA | none | 0 | 51.7% | 60 | 1.687 |
| BTCUSDT | 0% | 0 | **false** | NO_DATA | none | 0 | 39.1% | 46 | 0.718 |

**Key Findings:**
- **Zero forward-tracked trades** for any active crypto pick. The `forward_wr` and `forward_trades` fields are all 0.
- `forward_status` for all 3: `"NO_DATA: no closed picks found for this system/strategy"`
- The only forward-looking metrics available are `sym_dir_fwd_wr` (symbol+direction forward win rate from `at_signal_outcomes.intrabar`), which ranges from 39.1% (BTC) to 51.7% (XRP).
- **No pick has a track_level above "none"**.

---

## 7. Data Sources Audit

### NEARUSDT
- **Primary Source:** `tsmom_strategy` → `tsmom_volscaled`
- **Agreeing Systems:** `alpha_engine/luxalgo_confluence`, `inverse_mutations/inverse_luxalgo_confluence`
- **Total Contributing Systems:** 7 (`alpha_engine`, `copy_trader_clones`, `inverse_mutations`, `luxalgo_filters`, `super_signals`, `trusted_genome`, `tsmom_strategy`)
- **Source Type:** TSMOM (time-series momentum) strategy with vol-scaling
- **Research Cohort:** None assigned
- **Real vs Cached:** The `tsmom_strategy` is a real system. However, `_backfilled: true` indicates this specific pick instance was backfilled into the dataset, not emitted live.

### XRPUSDT
- **Primary Source:** `kalshi_signal_agent` → `kalshi_mtf_consensus`
- **Agreeing Systems:** `alpha_engine/prediction_market_consensus`
- **Total Contributing Systems:** 9
- **Source Type:** Kalshi prediction-market multi-timeframe consensus
- **Research Cohort:** `verified_alpha`
- **Real vs Cached:** Kalshi is a real prediction market, but the signal agent reads cached/consolidated Kalshi data. The `kalshi_mtf_consensus` strategy has **zero forward-tracked trades** (`forward_trades=0`), so its historical performance is unverified.

### BTCUSDT
- **Primary Source:** `kalshi_signal_agent` → `kalshi_mtf_consensus`
- **Agreeing Systems:** `genetic_programmer`, `mape_evolver`, `mutation_lab`, `forward_signals`, `contrarian_consensus`
- **Total Contributing Systems:** 13 (most crowded)
- **Source Type:** Kalshi prediction-market consensus + 5 agreeing systems
- **Research Cohort:** `verified_alpha`
- **Real vs Cached:** Same as XRP — Kalshi-based, but no forward validation. The high system count (13) creates "crowded_consensus_unproven" penalty (+2 only, minimal).

**Source Verdict:**
- All 3 picks come from **real source systems** (tsmom_strategy, kalshi_signal_agent), but:
  - **None have forward-validated track records** for their specific strategy.
  - All 3 are `_backfilled: true`, meaning they were not live-emitted but rather reconstructed/backfilled.
  - Kalshi signals have no closed-pick history in the system's forward tracker.

---

## 8. Crypto RSI5070 Forward Tracking Data

**File:** `audit_dashboard/data/crypto_rsi5070_us_forward_status.json`

| Metric | Value |
|--------|-------|
| **Condition** | CRYPTO AND Wilder RSI(14,1h) in [50,70] AND US session |
| **Generated At** | 2026-11-12T18:18:47Z (~2 days old) |
| **Status** | SHADOW_TRACKING |
| **N** | 430 |
| **N Gate** | 150 (passed) |
| **WR %** | 42.6% |
| **WR % Last 30d** | 53.1% (n=49) |
| **Avg PnL %** | 0.2934% |
| **Gross PF** | 1.271 |
| **Net PF** | 1.113 |
| **Net CI LB** | 0.9164 |
| **IS Net PF** | 1.079 |
| **OOS Net PF** | 1.146 |
| **IS/OOS Split** | 2026-08-05 |
| **Top Symbol** | JUPUSDT (5.1%) |
| **Promotable** | false |

**Gates:**
- net_ci_lb_gt_1.15: **FAIL** (0.9164 < 1.15)
- n_eff_ge_80: PASS
- n_ge_150: PASS
- oos_net_pf_ge_1.0: PASS
- concentration_lt_0.35: PASS

**Failing Gates:** `["net_ci_lb_gt_1.15"]`

**Verdict:** Below promotion bar. Net PF 1.11 with CI lower bound 0.92 means the edge is **not statistically distinguishable from 1.0** at standard confidence. The condition is forward-shadow only and should **never be sized**.

**Relevance to Active Picks:** None of the 3 active picks use the `crypto_rsi5070_us` condition directly. The active picks use `tsmom_volscaled` and `kalshi_mtf_consensus` strategies. The RSI5070 data provides context that **no CRYPTO condition in the system currently meets the promotion bar**.

---

## 9. Live vs Stale Summary

### Genuinely Live Picks
A pick is "genuinely live" if:
1. It has a real, non-backfilled signal timestamp within the last few hours.
2. Its `current_price` reflects market movement (not flat at entry).
3. It has forward-validation data or a verified track record.

| Pick | Signal Fresh (<3h) | Price Moved (dashboard) | Price Moved (live) | Forward Validated | Verdict |
|------|---------------------|------------------------|--------------------|-------------------|---------|
| NEARUSDT SHORT | Yes (2.7h) | Yes (3.233 ≠ 3.324) | Yes (3.209 ≠ 3.324) | **No** | **Live but unvalidated** |
| XRPUSDT SHORT | Yes (2.0h) | **No** (0.9842 = 0.9842) | Yes (0.9698 ≠ 0.9842) | **No** | **Stale price, unvalidated** |
| BTCUSDT SHORT | Yes (2.0h) | **No** (66300 = 66300) | Yes (65658 ≠ 66300) | **No** | **Stale price, unvalidated** |

### Stale Indicators Summary
- **Dashboard current_price stale:** 2 out of 3 picks show flat prices (XRP, BTC). NEAR's price is also stale relative to live Binance.
- **Data generation staleness:** Dashboard JSON generated at 14:30:07Z, viewed at 15:52:38Z = **1h 22m lag**.
- **Backfilled picks:** All 3 picks have `_backfilled: true`.
- **Zero forward trades:** All 3 picks have no forward-tracked history.
- **RSI5070 data age:** 2 days old (2026-11-12).

### Final Tally
- **Genuinely live + validated:** 0
- **Live signals but unvalidated + stale prices:** 3
- **Stale / flat / null PnL (dashboard view):** 2 out of 3
- **Stale / flat / null PnL (reality):** 0 out of 3 (all moved favorably for SHORTs)

---

## 10. Risk Flags

1. **All crypto picks are SHORT** in a market that may be oversold (RSI at entry: NEAR 19.9, XRP 30.7, BTC 24.6). These are extremely low RSI values, suggesting potential mean-reversion risk against SHORT positions.
2. **No forward validation** — all strategies show `NO_DATA` for closed picks.
3. **Dashboard price staleness** — traders relying on dashboard PnL would see flat/understated profits.
4. **Crowded consensus** — BTC pick has 13 contributing systems, which historically correlates with lower edge (per `crowded_consensus_unproven` penalty).
5. **Emitter registry would block** — all 3 picks have `_emitter_registry_would_block: true` for their (asset_class, strategy) pair.
6. **Trust tier WATCH** — all 3 picks have trust_score ≤ 4, placing them in the lowest trust tier.
7. **Dead zone confidence** — BTC at 0.673 confidence falls in the `[0.65, 0.75)` dead zone and received a phase-1 shadow reject.

---

## Appendix: Raw JSON Snippets

### NEARUSDT Active Pick (abridged)
```json
{
  "symbol": "NEARUSDT",
  "direction": "SHORT",
  "entry_price": 3.324,
  "current_price": 3.233,
  "pnl_pct": 2.74,
  "timestamp": "2026-11-14T13:10:05.727789+00:00",
  "age_hours": 1.3,
  "strategy": "tsmom_volscaled",
  "source_system": "tsmom_strategy",
  "forward_wr": 0,
  "forward_trades": 0,
  "forward_validated": false,
  "trust_score": 3,
  "trust_label": "LOW",
  "track_level": "none",
  "sym_dir_fwd_wr": 50.0,
  "sym_dir_fwd_n": 82,
  "_backfilled": true
}
```

### XRPUSDT Active Pick (abridged)
```json
{
  "symbol": "XRPUSDT",
  "direction": "SHORT",
  "entry_price": 0.9842,
  "current_price": 0.9842,
  "pnl_pct": 0.0,
  "timestamp": "2026-11-14T13:53:28.525051+00:00",
  "age_hours": 0.6,
  "strategy": "kalshi_mtf_consensus",
  "source_system": "pm_kalshi_signals",
  "forward_wr": 0,
  "forward_trades": 0,
  "forward_validated": false,
  "trust_score": 4,
  "trust_label": "LOW",
  "track_level": "none",
  "sym_dir_fwd_wr": 51.7,
  "sym_dir_fwd_n": 60,
  "_backfilled": true
}
```

### BTCUSDT Active Pick (abridged)
```json
{
  "symbol": "BTCUSDT",
  "direction": "SHORT",
  "entry_price": 66300.0,
  "current_price": 66300.0,
  "pnl_pct": 0.0,
  "timestamp": "2026-11-14T13:53:28.525051+00:00",
  "age_hours": 0.6,
  "strategy": "kalshi_mtf_consensus",
  "source_system": "pm_kalshi_signals",
  "forward_wr": 0,
  "forward_trades": 0,
  "forward_validated": false,
  "trust_score": 4,
  "trust_label": "LOW",
  "track_level": "none",
  "sym_dir_fwd_wr": 39.1,
  "sym_dir_fwd_n": 46,
  "_backfilled": true,
  "_phase1_dz_shadow_reject": "confidence=0.673 in dead zone [0.65, 0.75)"
}
```

---

*End of Report*
