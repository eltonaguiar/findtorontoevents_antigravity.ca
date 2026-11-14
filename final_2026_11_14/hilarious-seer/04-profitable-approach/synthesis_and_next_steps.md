# Profitable Approach Synthesis — From Audit to Edge

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Status:** FAIL → Path to MONEY-READY defined

---

## Current State (Verdict: FAIL)

- **All 9 asset classes FAIL** money-ready certification
- **Root cause:** data-quality artifacts, not missing formulas
  - 172-day stale active picks (129/129 frozen)
  - PnL ratio-vs-percent split brain (8 sign-flips, 15 miscalculations)
  - Frozen prices (83% of crypto OPEN picks, 79% of forex)
  - Broken lifecycle (100% REGISTERED, 0% CLOSED/TP/SL in pick_history)
  - Divergent stores (SQLite 129 vs MySQL 90,523 vs dashboard 20)
- **Statistical machinery exists but is unwired:** benchmark_closed_ledger.py, admissibility_pipeline.py, statistical_gates.py, monte_carlo.py — all rigorous, none in the daily production path
- **Prior benchmark result:** 4/67 ledgers pass paired-bootstrap, 9/67 pass MC top-decile; no ledger clears PF>1.5 post-costs with timing significance

---

## The Path to Profitability

### Phase 0: Stop the Bleed (This Week)

**Goal:** Make PnL measurement trustworthy.

1. **Canonical PnL recompute**
   - Run `quick_wins/shared/normalize_pnl_units.py` across all stores (SQLite, MySQL, JSON)
   - Standardize on **decimal ratio** (not percent)
   - Direction-aware: LONG `(cur-entry)/entry`, SHORT `(entry-cur)/entry`
   - Verify: spot-check 50 random rows against Binance/Yahoo live prices

2. **Price refresh + zombie purge**
   - Run `audit_trail/fetch_stock_prices.py` + Binance spot fetchers
   - Update `current_price` for all ACTIVE/OPEN picks
   - Quarantine picks >30 days stale to a `zombie_ledger` (do not delete — audit trail)
   - Resolve TIME_EXIT picks via `universal_pick_resolver.py` with live prices

3. **Fix lifecycle pipeline**
   - Ensure `universal_pick_resolver.py` writes to `audit_trail/data/universal_resolved_picks.json`
   - Wire resolver into `audit-dashboard.yml` hourly cron
   - Fix `sync_all_picks_to_mysql.py` Bug A (null entry_price) and Bug B (`pnl *= 100`)

4. **Store reconciliation**
   - Run `tools/cross_db_consistency.py` and resolve all orphaned keys
   - Make `live_picks.db` the single source of truth for active picks
   - MySQL and dashboard JSON become read-only mirrors

**Success criteria:**
- All ACTIVE picks have `current_price` within 1% of live market price
- `pick_history` has ≥10% CLOSED/TP/SL events (up from 0%)
- PnL sign matches price move for 100% of spot-checked rows
- `db_freshness.json` overall = GREEN

---

### Phase 1: Rigorous Validation (Next 2 Weeks)

**Goal:** Run the rigorous statistical gates on clean data.

1. **Wire `statistical_scoring_framework.py` into the daily path**
   - After `forward_validator.py` runs, call `StrategyCertifier` on each strategy
   - Gate 4 (Money-Ready) becomes the promotion threshold
   - Only strategies passing Gate 4 appear on the dashboard

2. **Add missing gates to `StrategyCertifier`**
   - Port `benchmark_closed_ledger.py::random_entry_mc` as Gate 2b (MC timing)
   - Port `benchmark_closed_ledger.py::paired_bootstrap` as Gate 1b (benchmark comparison)
   - Add purged k-fold CV (from `admissibility_pipeline.py`) to Gate 2
   - Add regime stratification (bull/bear/chop) to Gate 2

3. **Run benchmark on clean cohort**
   - Re-run `python3 -m alpha_engine.benchmark_closed_ledger --picks audit_dashboard/data/dashboard_data.json --fetch BTC-USD SPY --fetch-picks`
   - Target: ≥1 ledger with `pass_95=true` AND MC percentile ≥0.90 AND PF>1.5

4. **Intrabar resolution deep-dive**
   - Run `reresolve_intrabar.py --apply` on all closed trades
   - Exclude `close_approx` and ambiguous rows from WR/PF calculations
   - Re-measure top 5 ledgers with clean intrabar data

**Success criteria:**
- ≥1 `(strategy, asset_class)` ledger passes all 6 gates
- DSR > 0.95 for the passing ledger
- Bootstrap 95% CI lower bound for PF > 1.0
- MC timing percentile ≥ 0.90

---

### Phase 2: Strategy Iteration (Ongoing)

**Goal:** Find and prove edge through controlled experimentation.

1. **Adopt the two-archetype model** (from finpredict-v4 TradingView research)
   - **Grinder pipeline:** Target 70%+ WR, 1.5:1 R:R, high sample size
     - Candidate: `multi_asset_copytrader` (documented 82.1% WR)
     - Filter: only liquid crypto majors (BTC, ETH, SOL, LINK, NEAR, AVAX)
     - Timeframe: 1H entry, 4H direction filter
   - **Sniper pipeline:** Target 45–55% WR, 3:1+ R:R, tight SL
     - Candidate: `st_fear_greed_contrarian` (documented BNBUSDT +21.42%)
     - Filter: RSI < 35, volume spike >2x, Bollinger squeeze < 0.04
     - Timeframe: Daily regime + 4H precision entry

2. **Implement ICT/SMC baby strategy**
   - Add one strategy using fair value gap (FVG) retest + order block invalidation SL
   - Backtest on 2 years of 4H crypto data
   - Run through full 6-gate certification

3. **Add the 8 missing winner symbols**
   - `AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`
   - Check historical resolver data for n≥30 closed trades per symbol
   - If n<30, paper-trade for 90 days to build sample

4. **Heterogeneous stacking** (from finpredict-v4 research)
   - Wire LightGBM + GRU-Attention + Ridge linear model as meta-features
   - Calibrate with `CalibratedClassifierCV(method="isotonic", cv=3)`
   - Clip ensemble outputs to [2nd, 98th] percentile

**Success criteria:**
- ≥1 strategy from each archetype passes Gate 4 on out-of-sample data
- Paper-trading PF > 1.5 for 90 days on at least one strategy
- Kelly-fraction position sizing (0.25x–0.5x full Kelly) applied

---

### Phase 3: Real-Money Deployment (After 90-Day Paper)

**Goal:** Deploy only after statistically proven edge.

1. **Capital lock rules**
   - Max 2% risk per trade
   - Daily loss cap at −5%, monthly at −20%
   - 3 losses in a row → stop for session (grinder rule)
   - No Martingale scaling after losses (sniper rule)

2. **Continuous monitoring**
   - Daily `StrategyCertifier` run on rolling 90-day window
   - If any gate fails for 7 consecutive days, auto-demote to paper
   - Monthly benchmark re-run (paired bootstrap + MC timing)

3. **Regime awareness**
   - `regime_flip_detector.py` labels each day as bull/bear/chop
   - Do not trade grinder strategies in chop regime (WR collapses)
   - Do not trade sniper strategies in strong-trend regime (mean-reversion fails)

**Success criteria:**
- 90-day paper PF > 1.5 post-costs
- Live deployment maintains PF > 1.2 for first 30 days
- No drawdown > 20% from peak

---

## Why This Will Work

The repo already has every statistical tool needed to prove edge:
- `benchmark_closed_ledger.py` — rigorous MC timing + benchmark comparison
- `admissibility_pipeline.py` — purged CV + DSR + PBO + block bootstrap
- `statistical_gates.py` — BH-FDR + Newey-West + power analysis
- `statistical_scoring_framework.py` — complete 6-gate certifier

The only missing ingredient is **clean data + wiring**. Every prior audit concluded the same thing: edge collapses to coin-flip on dirty data. Phase 0 fixes the data. Phase 1 wires the gates. Phase 2 iterates strategies. Phase 3 deploys conservatively.

**People win TradingView contests because they specialize in one pattern, master it, and exploit it in the right asset class at the right time.** We will do the same — but with statistical proof at every step.
