# Prediction System Dashboard Metrics & Sources Audit
**Audited at:** 2026-11-14 15:53 UTC  
**Target:** https://findtorontoevents.ca/audit  
**Auditor:** Kilo  

---

## Executive Summary

| Category | Verdict |
|----------|---------|
| **Dashboard page freshness** | LIVE (built ~1.5h ago) |
| **Active picks table** | **EMPTY (0 picks)** — CRITICAL |
| **Primary pick generator (Alpha Engine)** | **DEAD (9 cancelled + 1 failure in last 10 runs)** |
| **Most sidecar JSONs** | **STALE (45–80+ hours old)** |
| **DB freshness check** | **EXTREMELY STALE (175 days old)** |
| **picks_now_live_pnl** | STALE (~45h old, separate tracker) |
| **HyroTrader panel** | STALE (~46h old, mostly empty) |
| **Filter permutations (Smart/VA/HC/Money Ready)** | EMPTY — all return no data |

**Bottom line:** The dashboard HTML is regenerated hourly, but the upstream pipelines that feed it picks and metrics are either broken, cancelled, or orphaned. The dashboard is a **freshly-painted facade over an empty data warehouse**.

---

## 1. Dashboard Generated Timestamp vs Current UTC

- **Live `dashboard_data.json` generated_at:** `2026-11-14T14:30:07Z`
- **Current UTC:** `2026-11-14T15:53:49Z`
- **Age:** **~1.4 hours old**
- **Verdict:** The dashboard build pipeline (`audit-dashboard.yml`) is running on schedule (hourly at :10). One run is currently `in_progress` (started 15:14). The HTML/JSON shell is **LIVE**.
- **BUT:** The build is packaging whatever upstream data exists. Because upstream is broken, the output is an empty active-picks table.

---

## 2. `hourly_update_last_run.json`

- **Path:** `audit_dashboard/data/hourly_update_last_run.json`
- **last_run:** `2026-11-12T19:22:01Z`
- **Age:** **44.6 hours old**
- **Verdict:** **STALE**. Whatever process writes this file has not run in ~2 days. This is a red flag that the "hourly update" concept is not being honored.

---

## 3. `db_freshness.json`

- **Path:** `audit_dashboard/data/db_freshness.json`
- **generated_at:** `2026-05-23T18:29:59Z`
- **Age:** **4,197 hours (~175 days) old**
- **overall:** `RED`
- **live_picks:** GREEN (but timestamp `2026-05-23 17:47:39` — May)
- **resolver_outputs:** GREEN (but timestamp `2026-05-23 17:53:12` — May)
- **signal_outcomes:** `RED` — `115,782 minutes stale` (~80 days), last resolved `2026-03-04`
- **backtests:** `YELLOW` — schema error (`no timestamp column`)
- **Verdict:** **EXTREMELY STALE / UNRELIABLE**. This file appears abandoned. The green statuses are based on timestamps from May 2026. Do not trust this file.

---

## 4. `feature_signals_latest.json`

- **Path:** `audit_dashboard/data/feature_signals_latest.json`
- **generated_at:** `2026-11-11T08:30:23Z`
- **Age:** **79.5 hours old**
- **Content:** 19 picks across 8 sleeves (commodity_momentum, commodity_term_cot, equity_momentum_quality, forex_carry_momentum, etf_sector_rotation, bond_duration_momentum)
- **Verdict:** **STALE**. Nearly 3 days old. The feature-signals pipeline is either not running or not committing. All picks have `forward_validated: false`.

---

## 5. Active Picks Metrics Columns

The live `dashboard_data.json` shows:

```
n_active_picks: 0
closed_picks count: 0
asset_class_health: None
smart_picks: None
high_conviction: None
money_ready: None
```

Because there are **zero active picks** on the live dashboard, every metric column is **EMPTY**:

| Metric | Status | Notes |
|--------|--------|-------|
| edge | EMPTY | No picks to compute edge on |
| track | EMPTY | No picks to show track record for |
| FWD WR% | EMPTY | No forward-tested picks |
| FWD N | EMPTY | No forward-trade count |
| score | EMPTY | No scored picks |
| trust | EMPTY | No trust-tier assignments |
| confidence | EMPTY | No confidence values |

**Local discrepancy:** `alpha_engine/data/active_picks.json` (in repo) contains **99 picks** with `copy_trader_intel` (50), `multi_asset_copytrader` (10), `bond_scanner` (6), etc. These picks exist in the repo but **do not reach the live dashboard**. This indicates a breakage between the alpha-engine output and the dashboard-generator input, or the dashboard generator is filtering them all out.

**hf_stats.by_asset_class** does show non-zero `n` values (CRYPTO 1,153, EQUITY 287, ETF 164, etc.), but `wr=None` and `pf=None` for every class. This suggests the high-frequency stats panel has row counts but no computed performance metrics.

---

## 6. Data Source Claims

### 6.1 Kalshi / Polymarket ("Prediction Market Consensus")
- **Code exists:** `alpha_engine/kalshi_signals.py`, `alpha_engine/polymarket_signals.py`, `prediction_market_agents/orchestrator.py`
- **GHA execution:** `audit-dashboard.yml` runs these hourly with `|| echo "...failed (non-fatal)"` — failures are **silent**.
- **Live evidence:** `verified_alpha.active_count = 2` (extremely low). The dashboard shows 0 active picks total. Prediction-market signals are either failing or producing signals that get filtered out.
- **Verdict:** Code runs, but output is **NOT reaching the dashboard** in actionable form. Likely **STALE/EMPTY**.

### 6.2 Copy Trader
- **Workflow:** `copy-trader-intelligence.yml` runs every 45 minutes.
- **Local evidence:** 50 of 99 local active picks are from `copy_trader_intel`.
- **Live evidence:** 0 active picks on dashboard. The copy-trader pipeline runs but its picks are **orphaned** — they exist in `alpha_engine/data/active_picks.json` but the dashboard generator does not surface them.
- **Verdict:** Pipeline **LIVE** but output **NOT REACHING DASHBOARD**.

### 6.3 Claude Gainer
- **Workflow:** `claude-gainer-ml-live.yml` runs every 30 minutes.
- **Recent runs:** Last 3 runs **succeeded** (15:48, 15:18, 14:48).
- **Output path:** `claude_gainer_ml/tracker/claude_live_picks.json` and `updates/data/`
- **Live evidence:** Not visible in dashboard active picks (0 total). The gainer picks are either not merged into the dashboard payload or filtered out.
- **Verdict:** Scanner **LIVE**, but output **ORPHANED** from dashboard.

### 6.4 Grok / Mercury (AI Tournament)
- **Workflow:** `ai-tournament-pipeline.yml` runs daily at 12:00 UTC.
- **Gate:** `if: ${{ vars.AI_TOURNAMENT_PIPELINE_ENABLED == 'true' }}` — this is **off by default** unless the repo variable is set.
- **Live evidence:** `predictions_leaderboard` has 222 entries, suggesting historical data exists. But active picks from tournament = 0.
- **Verdict:** Pipeline status **UNKNOWN** (gated by variable). Historical data **STALE**, not driving live picks.

### 6.5 Alpha Engine (Primary Scanner)
- **Workflow:** `alpha-engine-live.yml` runs every 2 hours.
- **Last 10 runs:**
  - `2026-11-14T15:05` — **failure**
  - `2026-11-14T14:05` — **cancelled**
  - `2026-11-14T12:08` — **cancelled**
  - `2026-11-14T10:06` — **cancelled**
  - `2026-11-14T08:07` — **cancelled**
  - `2026-11-14T06:10` — **cancelled**
  - `2026-11-14T04:07` — **cancelled**
  - `2026-11-14T02:09` — **cancelled**
  - `2026-11-14T00:17` — **cancelled**
  - `2026-11-13T22:06` — **cancelled**
- **Verdict:** **DEAD / BROKEN**. The primary pick generator has been cancelling or failing for ~24+ hours. This is the root cause of the empty active-picks table.

---

## 7. Filter Permutations

The dashboard advertises four filter surfaces:
- Smart Picks
- Verified Alpha
- High Conviction
- Money Ready

**Live data:**
- `smart_picks: None`
- `verified_alpha.active_count: 2` (not surfaced as active picks)
- `high_conviction: None`
- `money_ready: None`

**Verdict:** These are **not UI overlays on the same stale dataset** — they are **empty because the underlying dataset is empty**. With 0 active picks, no filter can return results. The filters are real gates, but there is nothing to gate.

---

## 8. HyroTrader Panel (`/audit/hyrotrader`)

- **hyro_quan_bridge.json generated_at:** `2026-11-12T18:12:50Z` (~45.8 hours old)
- **hyrotrader_picks.json:** 7 picks (static challenge config + manual action log)
- **Live page state:**
  - QuanEngine panel: "Loading..." (Table 1)
  - Live playbook signals (Table 2): "Not loaded yet"
  - Trade journal: "No journal trades logged yet"
  - Signal Strength & Performance: All stats show "—"
  - ML Edge Optimizer: All stats show "—"
- **Page note:** "Table 1 (QuanEngine bridge) is generated server-side by GitHub Actions (hourly). The refresh button re-reads the latest file — it does NOT regenerate the bridge."
- **Verdict:** **STALE / EMPTY**. The bridge JSON is 2 days old. All dynamic panels show loading spinners or empty dashes. No live Binance candles are being fetched on load (the "Refresh live checks" button is present but unclicked). The only real content is the static challenge parameter documentation.

---

## 9. `picks_now_live_pnl.json`

- **Path:** `audit_dashboard/data/picks_now_live_pnl.json`
- **generated_at:** `2026-11-12T18:57:19Z` (~45 hours old)
- **Source:** `picks_now_tracker (ejaguiar1_stocks), prices via yfinance/Binance`
- **n_open:** 4,310
- **Asset class breakdown:**
  - BOND: 1,293 (avg PnL -1.66%)
  - ETF: 1,722 (avg PnL -0.2%)
  - FOREX: 534 (avg PnL +0.26%)
  - EQUITY: 757 (avg PnL -5.22%)
  - COMMODITY: 4 (avg PnL +3.57%)
- **Verdict:** **STALE**. This is a separate tracker (not the alpha engine). It has ~4,300 open picks, but:
  1. The data is 2 days old.
  2. There is **zero CRYPTO** — this is a traditional-finance tracker (bonds, ETFs, forex, equities).
  3. Prices are from Nov 12. Any "live PnL" is not live.
  4. The picks are mostly `STRONG_BUY` / `WATCH` directions with uniform scores (e.g., many BOND picks have `score: 75.0`), suggesting a scoring model that does not differentiate much.

---

## Root Cause Analysis

```
Alpha Engine (primary scanner)
    ↓  Runs every 2h
    ↓  Last 24h: 9 cancelled + 1 failure
    ↓  [BROKEN]
alpha_engine/data/active_picks.json (local repo has 99 picks from prior runs)
    ↓  Not picked up by dashboard generator, or filtered out
    ↓  [ORPHANED]
Audit Dashboard Generator (runs hourly)
    ↓  Receives 0 active picks
    ↓  Produces dashboard_data.json with n_active_picks=0
    ↓  [LIVE BUILD, EMPTY CONTENT]
Live Site (/audit)
    ↓  Serves fresh HTML + empty JSON
    ↓  [FRESH SHELL, EMPTY DATA]
```

The dashboard is **honest** about being empty (it shows 0 picks, not fabricated ones), but it is **not useful** as a decision-making tool right now because the upstream pick generators are down.

---

## Recommendations

1. **Fix Alpha Engine cancellations immediately.** The last 10 runs are all cancelled or failed. Investigate whether this is a concurrency issue, timeout, or code error. The `cancel-in-progress: true` setting may be causing cascading cancels.

2. **Verify dashboard generator input.** Even with 99 local active picks, the dashboard shows 0. Check `audit_trail/dashboard_generator.py` for a filter that is zeroing out the active picks table.

3. **Restore DB freshness monitoring.** `db_freshness.json` is 175 days old and should either be deleted or revived.

4. **Surface pipeline failures loudly.** Many steps use `|| echo "...non-fatal"` which masks failures. Consider failing the dashboard build if critical upstream steps (alpha engine, resolver) are broken.

5. **Separate concerns.** `picks_now_live_pnl.json` tracks a completely different universe (bonds/ETFs) from the alpha engine (crypto-focused). Clarify on the dashboard which tracker each panel belongs to.

6. **HyroTrader bridge.** The QuanBridge JSON is 2 days old. If the hourly GHA step is failing, surface that error instead of showing "Loading..." forever.

---

*Report generated by Kilo on 2026-11-14T15:53Z.*
