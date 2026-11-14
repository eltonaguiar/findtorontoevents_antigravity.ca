# Non-Crypto Asset Class Deep Dive Audit
**Date:** 2026-11-14  
**Auditor:** Kilo  
**Sources:** `picks_now.json`, `picks_now_live_pnl.json`, `dashboard_data.json`, `intrabar_truth_by_class.json`, `strategy_perf_by_class.json`, live dashboard HTML

---

## Executive Summary

All five non-crypto asset classes (EQUITY, ETF, BOND, COMMODITY, FUTURES) are **currently non-viable for real-money deployment**. None meet the system's own money-ready criteria (n>=100, WR>=50%, PF>=1.5, DSR verified). The health ranges from "emitting but bleeding" (BOND, ETF) to "completely dead" (COMMODITY, FUTURES).

| Class | Status | Live Picks | Avg PnL | Intrabar Verdict | Age of Newest |
|-------|--------|------------|---------|------------------|---------------|
| **EQUITY** | STALE / REHAB | 757 | **-5.22%** | FAIL (n=249, WR 59%, PF 0.93) | ~2.4 days |
| **ETF** | STALE / REHAB | 1722 | **-0.20%** | INSUFFICIENT_N (n=44, WR 2.3%, PF 0.02) | ~1.9 days |
| **BOND** | EMITTING / POOR | 1293 | **-1.66%** | INSUFFICIENT_N (n=26, WR 7.7%, PF 0.39) | ~1.9 days |
| **COMMODITY** | **DEAD** | 4 | **+3.57%** | FAIL (n=229, WR 40%, PF 1.03) | **~156 days** |
| **FUTURES** | **DEAD / BLOCKED** | 0 | N/A | INSUFFICIENT_N (n=52, WR 42%, PF 1.09) | **No live picks** |

---

## 1. Data Source Freshness

| File | Generated | Age (as of 2026-11-14) |
|------|-----------|------------------------|
| `picks_now.json` | 2026-11-12 18:04 UTC | ~2 days |
| `picks_now_live_pnl.json` | 2026-11-12 18:57 UTC | ~2 days |
| `intrabar_truth_by_class.json` | 2026-11-12 18:14 UTC | ~2 days |
| `strategy_perf_by_class.json` | 2026-11-12 13:45 UTC | ~2 days |
| `dashboard_data.json` | **2026-10-19 19:40 UTC** | **~26 days (STALE)** |

> **Critical Finding:** The main `dashboard_data.json` (which drives the /audit HTML active-picks table) is **26 days old**. The "active picks" shown in that file are ghosts from October 19. The live system actually consumes `picks_now_live_pnl.json` for pricing, but the dashboard UI may still reference stale counts.

---

## 2. EQUITY

### Active Pick Count
- **picks_now_live_pnl.json:** 757 open picks
- **picks_now.json (top-ranked):** 10 picks (5 in `picks`, 5 duplicated in `trending`)
- **dashboard_data.json (stale):** 2 picks (ADBE, NVDA from Oct 19)

### Top Picks (from picks_now.json)
All equity picks are demoted to **WATCH** direction with `position_size_pct: 0.0` and **null TP/SL**.

| Symbol | Direction | Score | Generated | Notes |
|--------|-----------|-------|-----------|-------|
| GOOGL | WATCH | 72.5 | Nov 12 18:04 | intrabar_gate: CLASS_DEMOTED |
| PLTR | WATCH | 69.5 | Nov 12 18:04 | intrabar_gate: CLASS_DEMOTED |
| TTWO | WATCH | 67.5 | Nov 12 18:04 | intrabar_gate: CLASS_DEMOTED |
| MU | WATCH | 58.0 | Nov 12 18:04 | intrabar_gate: CLASS_DEMOTED |
| NFLX | WATCH | 42.5 | Nov 12 18:04 | No TP/SL |

### Timestamp Audit
- **Newest:** 2026-11-12 06:11 UTC (~2.4 days old)
- **Oldest:** 2026-06-06 04:53 UTC (~161 days old)
- **Verdict:** Mix of very recent and ancient picks. The WATCH demotion means **none are actually tradeable**.

### PnL Check (picks_now_live_pnl.json)
- **Average PnL:** -5.22%
- **Positive / Negative:** 176 / 534
- **Most picks are deeply underwater.**

### Metrics: Edge, Track, Forward
- `intrabar_fwd_n`: **null** for all top picks
- `intrabar_fwd_wr_pct`: **null**
- `intrabar_gate`: `CLASS_DEMOTED` or `NO_DATA`
- `db_n` (database history): 0 for most (GOOGL has 7, WR 14.3%)
- `forward_wr`: 0 in dashboard_data.json
- `forward_trades`: 0
- `strat_fwd_wr`: null

### Intrabar Truth
```json
{
  "n": 249,
  "wr_pct": 59.0,
  "pf": 0.934,
  "avg_pnl_pct": -0.0806,
  "verdict": "FAIL"
}
```
> High WR (59%) but PF < 1.0 and negative avg PnL = **asymmetric losses** (wins small, losses large).

### Strategy Performance (top 5)
| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| MeanReversionBB | 191 | 53.9% | 1.76 | +0.70% |
| stocks_rsi2_pullback | 81 | 46.9% | 1.22 | +0.31% |
| MomentumEMA | 65 | 23.1% | 0.45 | -0.85% |
| unknown | 61 | 49.2% | 1.82 | +0.76% |
| Dividend Aristocrats | 14 | 35.7% | 0.97 | -0.04% |

**EQUITY Verdict:** STALE / REHAB. Picks exist but are demoted to WATCH, net negative PnL, no forward-validated edge, massive stale backlog.

---

## 3. ETF

### Active Pick Count
- **picks_now_live_pnl.json:** 1722 open picks
- **picks_now.json (top-ranked):** 5 picks
- **dashboard_data.json (stale):** 9 picks (TQQQ, QQQ, VLUE, USO, XLE, XLK, XRT, XLV, EFA from Oct 16-19)

### Top Picks (from picks_now.json)
| Symbol | Direction | Score | Generated |
|--------|-----------|-------|-----------|
| BITO | STRONG_BUY | 95.0 | Nov 12 18:04 |
| IBIT | STRONG_BUY | 90.0 | Nov 12 18:04 |
| HDV | STRONG_BUY | 87.5 | Nov 12 18:04 |
| SCHD | STRONG_BUY | 82.5 | Nov 12 18:04 |
| SDY | STRONG_BUY | 82.5 | Nov 12 18:04 |

> Note: BITO and IBIT are Bitcoin ETFs. They are technically ETFs but behave like crypto proxies.

### Timestamp Audit
- **Newest:** 2026-11-12 18:08 UTC (~1.9 days old)
- **Oldest:** 2026-06-06 04:53 UTC (~161 days old)

### PnL Check
- **Average PnL:** -0.20%
- **Positive / Negative:** 920 / 797
- Near break-even on aggregate, but 1722 picks is an enormous, unmanaged backlog.

### Metrics: Edge, Track, Forward
- `db_n`: 0 for all top picks
- `intrabar_fwd_n`: null
- `intrabar_gate`: NO_DATA
- No forward-validation data available.

### Intrabar Truth
```json
{
  "n": 44,
  "wr_pct": 2.3,
  "pf": 0.022,
  "avg_pnl_pct": -2.3613,
  "verdict": "INSUFFICIENT_N"
}
```
> Catastrophic. Only 44 resolved trades, 2.3% WR. This is the worst intrabar-verified class.

### Strategy Performance (all)
| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| extreme_oversold_bounce | 10 | 0.0% | 0.00 | -3.10% |
| hyperopt_connors_rsi2 | 4 | 0.0% | 0.00 | -3.29% |
| etf_rsi2_pullback | 3 | 66.7% | 24.51 | +15.67% |
| regime_mild_bull | 2 | 100% | 999 | +2.12% |
| vix_reversal | 2 | 0.0% | 0.00 | -0.01% |

**ETF Verdict:** STALE / REHAB. Large volume of picks but essentially no proven edge. Intrabar record is near-total loss.

---

## 4. BOND

### Active Pick Count
- **picks_now_live_pnl.json:** 1293 open picks
- **picks_now.json (top-ranked):** 9 picks
- **dashboard_data.json (stale):** 0 picks (bond emission restarted after this file was built)

### Top Picks (from picks_now.json)
| Symbol | Direction | Score | Generated |
|--------|-----------|-------|-----------|
| WIP | STRONG_BUY | 90.0 | Nov 12 18:04 |
| TIP | STRONG_BUY | 84.0 | Nov 12 18:04 |
| SCHP | STRONG_BUY | 84.0 | Nov 12 18:04 |
| PFFA | STRONG_BUY | 82.5 | Nov 12 18:04 |
| PFFD | STRONG_BUY | 76.5 | Nov 12 18:04 |
| PFXF | STRONG_BUY | 76.5 | Nov 12 18:04 |
| PFF | STRONG_BUY | 76.5 | Nov 12 18:04 |
| SPSB | STRONG_BUY | 75.0 | Nov 12 18:04 |
| SPIB | STRONG_BUY | 75.0 | Nov 12 18:04 |

### Timestamp Audit
- **Newest:** 2026-11-12 18:08 UTC (~1.9 days old)
- **Oldest:** 2026-06-18 20:38 UTC (~148 days old)
- The user mentioned "4 days ago" — this refers to the Nov 9/10 cohort still present in the backlog. Newest picks are indeed ~2 days old.

### PnL Check
- **Average PnL:** -1.66%
- **Positive / Negative:** 350 / 936
- **72% of bond picks are underwater.**

### Metrics: Edge, Track, Forward
- `db_n`: **0** for all top picks (no historical track record)
- `dbf_active`: false for all
- `dbf_staleness_days`: 999.0 (no data)
- `intrabar_fwd_n`: null
- `intrabar_gate`: NO_DATA
- `tp_sl_quality_score`: 0.0 for many (WIP, TIP, SCHP, PFFD, PFF, SPSB, SPIB)

### Intrabar Truth
```json
{
  "n": 26,
  "wr_pct": 7.7,
  "pf": 0.391,
  "avg_pnl_pct": -0.3342,
  "verdict": "INSUFFICIENT_N"
}
```
> Only 26 resolved trades. 7.7% WR is abysmal.

### Strategy Performance
| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| bond_yield_momentum | 5 | 0.0% | 0.00 | -0.48% |
| futures_momentum | 5 | 80.0% | 717.24 | +2.02% |
| bond_mean_reversion | 3 | 0.0% | 0.00 | -0.61% |
| bond_yield_curve_slope | 3 | 0.0% | 0.00 | -0.83% |

> n=3-5 per strategy. No statistically meaningful edge.

**BOND Verdict:** EMITTING but POOR. Restarted emission (per 2026-05-31 data integrity repair) but no track record, most picks show 0% database history, and aggregate PnL is negative.

---

## 5. COMMODITY

### Active Pick Count
- **picks_now_live_pnl.json:** **4** open picks
- **picks_now.json (top-ranked):** 0 picks
- **dashboard_data.json (stale):** 2 picks (GC=F, PA=F from Oct 19)

### The 4 Live Commodity Picks
| Symbol | Direction | Entry | Generated | Current | PnL | Age |
|--------|-----------|-------|-----------|---------|-----|-----|
| ZM=F | STRONG_BUY | 303.50 | Jun 11 07:41 | 324.10 | **+6.79%** | ~156 days |
| ZS=F | STRONG_BUY | 1124.25 | Jun 11 07:41 | 1220.25 | **+8.54%** | ~156 days |
| ZS=F | STRONG_BUY | 1119.50 | Jun 10 07:30 | 1220.25 | **+9.00%** | ~157 days |
| LE=F | STRONG_BUY | 248.025 | Jun 10 07:30 | 223.15 | **-10.03%** | ~157 days |

### Timestamp Audit
- **Newest:** 2026-06-11 07:41 UTC (~156 days old)
- **Oldest:** 2026-06-10 07:30 UTC (~157 days old)
- **Verdict:** All commodity picks are **5+ months old**. No new commodity emission since June 2026.

### PnL Check
- **Average PnL:** +3.57% (skewed by two large ZS=F winners and one LE=F loser)
- **Positive / Negative:** 3 / 1

### Metrics: Edge, Track, Forward
- No forward metrics populated for commodity picks in top-level files.
- `intrabar_gate` not applicable (no recent picks).

### Intrabar Truth
```json
{
  "n": 229,
  "wr_pct": 40.2,
  "pf": 1.026,
  "avg_pnl_pct": 0.027,
  "verdict": "FAIL"
}
```
> Nearly break-even on aggregate (PF 1.026), but n<1000 and verdict FAIL.

### Strategy Performance
| Strategy | n | WR | PF | Avg PnL |
|----------|---|----|----|---------|
| futures_momentum | 681 | 37.3% | 0.25 | -0.72% |
| cta_cross_asset_tsmom | 96 | 19.8% | 0.28 | -1.49% |
| cta_commodity_momentum_term | 52 | 40.4% | 0.28 | -0.42% |
| cta_golden_cross_200 | 24 | 83.3% | 10.87 | +3.83% |
| combined_confidence | 10 | 40.0% | 1.01 | +0.03% |

**COMMODITY Verdict:** DEAD. Only 4 active picks, all ancient. The system has stopped emitting commodity signals. The CT=F DSR=1.0 claim was **falsified on 2026-05-13** (6.33x over-emission artifact).

---

## 6. FUTURES

### Active Pick Count
- **picks_now_live_pnl.json:** **0** open picks
- **picks_now.json (top-ranked):** 0 picks
- **dashboard_data.json (stale):** 1 pick (YM=F from Oct 19)

### The "1 Futures Active Pick" Mystery
The user asked about "1 futures active pick." This refers to **YM=F** in the 26-day-stale `dashboard_data.json`:
- Symbol: YM=F (Dow Jones futures)
- Direction: LONG
- Generated: 2026-10-19 18:13 UTC
- PnL: +0.08%
- Strategy: futures_connors_rsi2
- edge: 100.0 (but track=2, so meaningless)

**This pick is a ghost.** The file it lives in is stale, and the live pricing tracker (`picks_now_live_pnl.json`) shows **zero** futures picks.

### Timestamp Audit
- **No live timestamps.** The only record is 26 days old.

### PnL Check
- N/A (no live picks)

### Metrics
- `forward_wr`: 100.0 (but based on n=2)
- `forward_trades`: 2
- `forward_validated`: False

### Intrabar Truth
```json
{
  "n": 52,
  "wr_pct": 42.3,
  "pf": 1.094,
  "avg_pnl_pct": 0.0791,
  "verdict": "INSUFFICIENT_N"
}
```

### HTML Dashboard Declares FUTURES "BLOCKED"
> "Futures remain BLOCKED... 6.3% WR on n=17 with 76% LOST-exit rate. Kill list pending."

**FUTURES Verdict:** DEAD / BLOCKED. Zero live emission. The sole "active" pick is a stale artifact. Module officially blocked per system policy.

---

## 7. Cross-Cutting Findings

### Most Non-Crypto Picks Show 0%, Flat, or Null PnL
- **BOND:** 72% of picks are negative. Many show 0.0% (e.g., SHV, SGOV) because they are cash-like instruments.
- **EQUITY:** WATCH picks have **null TP/SL** and **0% position_size**. They are not real trades.
- **ETF:** Near break-even aggregate (-0.2%) but huge dispersion.
- **COMMODITY:** Only 4 picks, two big winners, one big loser.

### Edge / Track / Forward Metrics Are Empty
Across all non-crypto top picks in `picks_now.json`:
- `intrabar_fwd_n`: **null** (100% of picks)
- `intrabar_fwd_wr_pct`: **null** (100%)
- `intrabar_gate`: `NO_DATA` or `CLASS_DEMOTED`
- `db_n`: 0 for ~90% of picks
- `dbf_active`: false for all

This means **there is no forward-validated track record** for any non-crypto pick currently being emitted. The system cannot compute edge because it lacks resolved trade history.

### Data Source Mismatch
- `dashboard_data.json` (used by HTML UI) is **26 days stale**.
- `picks_now_live_pnl.json` (used by pricing tracker) is **2 days fresh**.
- The dashboard may display contradictory counts depending on which data layer is rendered.

---

## 8. Asset Class Vitality Matrix

| Asset Class | Alive? | Stale? | Dead? | Key Evidence |
|-------------|--------|--------|-------|--------------|
| **EQUITY** | Partially | YES | No | Recent emission (Nov 12) but all WATCH, net -5.22% PnL, no edge data |
| **ETF** | Partially | YES | No | Recent emission (Nov 12) but intrabar WR 2.3%, n=44, no proven edge |
| **BOND** | YES | Partially | No | Active emission, 1293 picks, but avg -1.66%, no track record, n=26 intrabar |
| **COMMODITY** | **NO** | **YES** | **YES** | 4 picks, all 156+ days old, no emission since June |
| **FUTURES** | **NO** | **YES** | **YES** | 0 live picks, module BLOCKED, only stale artifact in old JSON |

---

## 9. Recommendations

1. **Do not size** on any non-crypto asset class. None pass the system's own money-ready gates.
2. **Purge stale picks.** BOND (1293), ETF (1722), and EQUITY (757) have massive backlogs of old, unresolved picks that distort aggregate PnL.
3. **Fix dashboard_data.json freshness.** The 26-day lag means the /audit HTML is showing ghost picks.
4. **FUTURES:** Either formally retire the module or develop a re-emission plan. Current state is BLOCKED with zero activity.
5. **COMMODITY:** If re-emission is desired, start from scratch. The 4 zombie picks from June should be closed/ignored.
6. **Forward validation:** Non-crypto classes need n>=100 resolved trades before any edge metrics can be trusted. Currently all are below this threshold.

---

*End of Report*
