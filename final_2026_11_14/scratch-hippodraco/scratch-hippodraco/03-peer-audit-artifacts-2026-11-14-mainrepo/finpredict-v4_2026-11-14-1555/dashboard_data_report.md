# Prediction System Dashboard Data Audit Report

**Audited:** 2026-11-14T15:48Z  
**Data path:** `/home/eaguiar2015/wt-audit-prediction-system/audit_dashboard/data/`  
**Auditor:** Kilo (automated audit)

---

## 1. Executive Summary

**No asset class is money-ready.** All classes fail the honest intrabar-truth gate or have insufficient sample size. The dashboard shows significant metric inflation versus raw DB figures in several classes, and the production pipeline is suffering from severe resolution backlogs and stale signal-outcome tables.

| Verdict Count | Classes |
|---------------|---------|
| NOT_READY | CRYPTO, EQUITY, FOREX |
| WATCH | COMMODITY |
| INSUFFICIENT_DATA | BOND, ETF, FUTURES, MEME, PENNY_STOCK |
| **MONEY_READY** | **0** |

---

## 2. Per-Asset-Class Summary Table

### 2.1 Active Picks (as of latest dashboard payload)

| Asset Class | Top-25 Picks | Live PnL Panel (n_open) | Avg Live PnL % | n_pos | n_neg | Stale (>24h) | Zero-PnL |
|-------------|--------------|------------------------|----------------|-------|-------|--------------|----------|
| BOND | 8 | 1,313 | -1.93% | 319 | 975 | 0 | 0 |
| COMMODITY | 0 | 4 | +4.80% | 3 | 1 | 0 | 0 |
| CRYPTO | 0* | 0** | — | — | — | 0 | 0 |
| EQUITY | 5 | 767 | -5.99% | 184 | 578 | 0 | 0 |
| ETF | 5 | 1,730 | -0.40% | 884 | 833 | 0 | 0 |
| FOREX | 7 | 547 | +0.26% | 245 | 295 | 0 | 0 |
| FUTURES | 0 | 0** | — | — | — | 0 | 0 |

\* CRYPTO appears in `picks_now["all"]` (n=1) but not in the curated top-25.  
\** Live PnL panel (`picks_now_live_pnl.json`) does not currently list CRYPTO or FUTURES rows; the 4,361 open picks are concentrated in BOND, ETF, EQUITY, and FOREX.

### 2.2 Honest Intrabar-Truth Performance (closed picks)

| Asset Class | n | WR % | PF | Avg PnL % | Verdict |
|-------------|---|------|----|-----------|---------|
| CRYPTO | 3,705 | 35.9 | 0.92 | -0.103 | FAIL |
| EQUITY | 250 | 59.2 | 0.939 | -0.074 | FAIL |
| FOREX | 612 | 32.2 | 0.66 | -0.105 | FAIL |
| COMMODITY | 229 | 40.2 | 1.026 | +0.027 | FAIL |
| FUTURES | 52 | 42.3 | 1.094 | +0.079 | INSUFFICIENT_N |
| ETF | 45 | 2.2 | 0.022 | -2.332 | INSUFFICIENT_N |
| BOND | 26 | 7.7 | 0.391 | -0.334 | INSUFFICIENT_N |
| MEMECOIN | 102 | 29.4 | 0.661 | -0.343 | FAIL |

### 2.3 Recent Closed Performance — DB Raw (last 14 days)

| Asset Class | n_decisive | Wins | Losses | WR % | PF | Mean PnL % | n_active | Top-Source Share |
|-------------|------------|------|--------|------|----|------------|----------|------------------|
| CRYPTO | 1,384 | 609 | 775 | 44.0 | 1.031 | +0.04 | 11 | 99.6% |
| EQUITY | 17 | 6 | 11 | 35.3 | 1.007 | +0.02 | 43 | 100% |
| FOREX | 159 | 11 | 148 | 6.9 | 0.087 | -0.47 | 9 | 100% |
| ETF | 47 | 12 | 35 | 25.5 | 0.621 | -0.83 | 9 | 100% |
| FUTURES | 189 | 79 | 110 | 41.8 | 1.376 | +0.37 | 9 | 100% |

### 2.4 Policy-Clean Net Registry (full history)

| Asset Class | n | PF |
|-------------|---|----|
| CRYPTO | 21,988 | 0.259 |
| EQUITY | 461 | 0.702 |
| FOREX | 438 | 0.834 |
| COMMODITY | 14 | 0.172 |
| ETF | 15 | 1.836 |
| FUTURES | 13 | 0.857 |
| BOND | 1 | 0.0 |
| MEME | 10 | 0.023 |

---

## 3. Frozen / Stale Data Issues

### 3.1 Resolution Pipeline Backlog
- **`picks_now_track_record.json`** tracks **4,820 symbol-days**; only **301 resolved** (6.2% resolution rate).
- **4,220 picks (87.6%)** are in the `10d+ (TIME_EXIT due)` maturity bucket — they have aged past the intended holding period without resolution.
- Cumulative tracked PnL: **-718.4%** across 4820 symbol-days.
- Track-record WR: **14.3%** (43 won / 258 lost).

### 3.2 Stale Signal-Outcomes Table
- **`at_signal_outcomes`** (the intrabar-truth source) has not resolved since **2026-03-04**.
- Staleness: **115,782 minutes (~80 days)**.
- Status: **RED** in `db_freshness.json`.
- This means the "honest" intrabar figures above are historical and have not been refreshed for ~80 days.

### 3.3 Dead Asset Classes (no recent closures)
| Asset Class | Days Since Last Close | Note |
|-------------|----------------------|------|
| FUTURES | 245.7 | Last closed 2026-03-13 |
| PENNY_STOCK | 247.6 | Last closed 2026-03-11 |
| BOND | 4.0 | Last closed 2026-11-10 (but only n=1 in policy-clean) |

### 3.4 DB Bloat & Ghost Rows
- **Ghost rows:** 22,947 duplicate/negligible-pnl rows. Top cohorts are MEMECOIN `meta_strategy` duplicates (e.g., DOGEUSDT 3,569 rows with identical pnl).
- **Open bloat:** `trading_picks` has **90,523 open rows** but only **21 active** per the DB health check.
- **PnL sign mismatch:** 0.54% of sampled rows have contradictory sign (green tier, but non-zero).
- **Naive magnitude mismatch:** 27% of sampled rows differ materially from raw computed PnL.

### 3.5 Null / Stuck Fields
- In `picks_now.json` (top-25 curated list), **100% of picks have null `pnl_pct`**, `exit_price`, `closed_at`, `tp_hit`, and `sl_hit`. This is expected for a daily-generated "scored" pick list, but it means the dashboard surface has **no live profitability data** for these curated picks.
- In `picks_now_live_pnl.json`, **44 picks show exactly 0% PnL** (stuck at breakeven), out of 4,361 priced.

### 3.6 HyroTrader Picks
- All 7 hyrotrader picks are **pending_entry** with null `entry_price`, `stop_loss`, `take_profit`, `opened_at`, `closed_at`, and `pnl_pct`.
- Account snapshot is stale (last session 2026-04-08, equity $4,929 of $5,000 start).

---

## 4. Dashboard vs Raw DB Discrepancies

### 4.1 CRYPTO — Massive Dashboard Inflation
| Metric | Dashboard recent_closed | DB raw 90d | Delta |
|--------|------------------------|------------|-------|
| n | 2,129 | 2,001 | +6% |
| WR % | 51.57 | 39.38 | **+12.2 pp** |
| PF | 1.801 | 0.371 | **+4.9x** |
| Mean PnL % | +0.54 | -4.60 | **+5.14 pp** |

- The dashboard "Smart Picks" cohort (n=337, WR=78.9%, PF=9.69) is **91.7% sourced from `claude_gainer_st`**, which has only **3 closed rows** in the raw DB. This is a single-strategy track record masquerading as a portfolio.
- **63.9% of EXPIRED rows are counted as WON** when intraday drift was positive, inflating WR.
- **1,864 duplicate groups** exist in CRYPTO 90d raw data — count-inflation risk.

### 4.2 EQUITY — Dashboard Filters Out Winners
| Metric | Dashboard recent_closed | DB raw 90d | Delta |
|--------|------------------------|------------|-------|
| n | 567 | 8,249 | -93% |
| WR % | 37.39 | 66.69 | **-29.3 pp** |
| PF | 0.704 | 5.555 | **-7.9x** |
| Mean PnL % | -0.72 | +4.94 | **-5.66 pp** |

- The dashboard's curated cohort is **heavily filtered** and ends up with a losing profile, while the raw DB shows strong performance. This suggests the dashboard filter logic is inverted or capturing a specific losing subset.

### 4.3 FOREX — Extreme Raw Outliers
| Metric | Dashboard recent_closed | DB raw 90d | Delta |
|--------|------------------------|------------|-------|
| n | 516 | 6,051 | -91% |
| WR % | 45.54 | 83.28 | **-37.7 pp** |
| PF | 2.02 | 0.108 | **-18.7x** |
| Mean PnL % | +0.41 | -5.07 | **-5.48 pp** |

- Raw DB shows many small wins (83% WR) but **massive aggregate losses** (-5.07% mean), indicating a "death by a thousand cuts + occasional catastrophic loss" pattern. The dashboard cohort avoids this by filtering.

### 4.4 FUTURES — Outlier-Driven Raw Metrics
| Metric | Dashboard recent_closed | DB raw 90d | Delta |
|--------|------------------------|------------|-------|
| n | 14 | 2,681 | -99% |
| WR % | 7.14 | 50.0 | **-42.9 pp** |
| PF | 0.582 | 131.6 | **+226x** |
| Mean PnL % | -0.44 | +371.2 | **+371.6 pp** |

- Raw DB PF of 131.6 and mean +371% are driven by **one or two extreme winning trades**, not a repeatable edge. The tiny dashboard cohort (n=14) is more representative of typical performance.

### 4.5 Live PnL Panel vs DB Active Count
- `picks_now_live_pnl.json`: **4,361 open picks** priced.
- `db_health.json` (`trading_picks`): **90,523 open rows**, of which only **21 are marked active**.
- This 4,000x gap indicates the "active" definition differs wildly between the pricing view and the DB health harness, making operational monitoring unreliable.

---

## 5. Money-Ready Gate Status (per `money_ready_verdict.json`)

| Asset Class | Verdict | PF | WR % | MDD | CVaR 95% | Expectancy | Policy Frozen |
|-------------|---------|----|------|-----|----------|------------|---------------|
| CRYPTO | NOT_READY | 0.92 | 35.87 | 100.1% | -96.1 | -0.059 | No |
| EQUITY | NOT_READY | 0.94 | 59.20 | 100.0% | -5.31 | +0.008 | No |
| FOREX | NOT_READY | 0.66 | 32.19 | 82.1% | -5.87 | -0.002 | **Yes** |
| COMMODITY | WATCH | 1.03 | 40.17 | 19.8% | -3.66 | -0.004 | **Yes** |
| ETF | INSUFFICIENT_DATA | 0.02 | 2.22 | — | — | — | No |
| BOND | INSUFFICIENT_DATA | 0.0 | 0.0 | — | — | — | **Yes** |
| FUTURES | INSUFFICIENT_DATA | 1.09 | 42.31 | 16.7% | -4.77 | +0.010 | **Yes** |
| MEME | INSUFFICIENT_DATA | 0.02 | 10.0 | 49.4% | -13.85 | -0.066 | No |

**Key gate failures:**
- **CRYPTO:** PF < 1.0, WR < 50%, expectancy negative, MDD ~100%, bootstrap CI excludes zero.
- **EQUITY:** PF < 1.0, MDD ~100%, SPA fails (p=0.256), single-source concentration.
- **FOREX:** PF < 1.0, WR < 50%, DSR near zero, expectancy negative, policy frozen.
- **COMMODITY:** PF barely above 1.0, expectancy negative, DSR = 0, policy frozen.

---

## 6. Alarming Outliers & Red Flags

1. **CRYPTO Smart-Picks PF 9.69 is fabricated by a single source.** 91.7% of the cohort comes from `claude_gainer_st` (only 3 raw DB rows). This is not a portfolio — it is one strategy's backtested track record pasted onto the dashboard.

2. **Intrabar truth has not updated in 80 days.** The `at_signal_outcomes` table (source of honest first-touch performance) is stale since 2026-03-04. Any "honest" metric relying on this table is frozen in time.

3. **Track-record resolution rate is 6.2%.** Of 4,820 tracked symbol-days, only 301 have resolved. The remaining 4,220 are stuck in `TIME_EXIT due` limbo, making the forward-test effectively a black hole.

4. **EQUITY dashboard filter inverts performance.** Raw DB 90d shows WR 66.7% / PF 5.6 / mean +4.9%, while the dashboard shows WR 37.4% / PF 0.7 / mean -0.7%. The filter is capturing losers and discarding winners.

5. **Top sleeves report impossible stats.** `GainerPredictor1hStrategy` (CRYPTO) shows WR 97.96% / PF 120.0 on n=49. `ADX Trend Confirmation` shows WR 97.18% / PF 56.7 on n=213. These are almost certainly overfitted or data-leaked.

6. **22,947 ghost rows** in the DB, dominated by MEMECOIN duplicate re-emissions, indicate the deduplication and flicker-filter pipeline is failing for high-volume strategies.

---

## 7. Recommendations

1. **Do not allocate capital** to any asset class based on current dashboard figures. The system-wide verdict is **NOT money-ready**.
2. **Fix `at_signal_outcomes` refresh.** 80 days of stale intrabar data makes honest auditing impossible.
3. **Resolve the 4,220 TIME_EXIT backlogged picks.** The forward-test pipeline is choked; without resolution, track-record WR/PF are meaningless.
4. **Audit CRYPTO Smart-Picks filtering.** Remove single-source concentration and EXPIRED-mislabeled-WON counting.
5. **Investigate EQUITY dashboard filter inversion.** Determine why the curated cohort underperforms the raw DB by such a wide margin.
6. **Reconcile "active" definitions.** Align `picks_now_live_pnl` (4,361 open), `trading_picks` (90,523 open / 21 active), and `picks_now` (25 top picks) so operators have a single source of truth.

---

*Report generated by automated audit. All figures sourced directly from the JSON payloads in `audit_dashboard/data/`.*
