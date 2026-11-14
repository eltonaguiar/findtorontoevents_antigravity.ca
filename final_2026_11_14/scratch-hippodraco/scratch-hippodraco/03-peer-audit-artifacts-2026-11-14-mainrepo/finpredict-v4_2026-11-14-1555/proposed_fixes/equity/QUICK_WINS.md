# QUICK WINS — EQUITY / ETF / BOND Prediction Pipelines

**Audit Date:** 2026-11-14  
**Scope:** Non-crypto asset classes (EQUITY, ETF, BOND)  
**Status:** All three are `NOT_READY` or `INSUFFICIENT_DATA`. No real-money deployment.

---

## 0. The Numbers (Ground Truth)

| Class | Open Picks | Avg PnL | Intrabar n | Intrabar WR | Intrabar PF | Verdict | Key Blocker |
|-------|------------|---------|------------|-------------|-------------|---------|-------------|
| **EQUITY** | 757 | **-5.22%** | 250 | 59.2% | 0.939 | FAIL | `CLASS_DEMOTED`, MDD=0.9999, SPA p=0.256, single-source |
| **ETF** | 1,722 | **-0.20%** | 45 | 2.2% | 0.022 | INSUFFICIENT_N | `NO_DATA`, 0 strategies with n>=20, no edge |
| **BOND** | 1,293 | **-1.66%** | 26 | 7.7% | 0.391 | INSUFFICIENT_N | `NO_DATA`, 72% underwater, 0 strategies with n>=20 |

Cross-cutting: `dashboard_data.json` is **26 days stale**; `picks_now_live_pnl.json` is **45h old**; `intrabar_gate` is `NO_DATA` or `CLASS_DEMOTED` on 100% of top picks; `db_n=0` for ~90% of top picks.

---

## 1. TOP 3 QUICK WINS (< 1 day each)

### 1.1 Freeze & Purge Stale Open Picks (All Three Classes)

**What to do:**
- Force-close or archive open picks older than **14 days** for EQUITY, ETF, and BOND.
- The backlogs (757 / 1,722 / 1,293) are distorting aggregate PnL and masking true pipeline health.
- EQUITY has picks from **June 6** (~161 days old); ETF and BOND have similar zombie cohorts.

**File / location:**
- `alpha_engine/pick_revalidator.py` — add a hard `max_age_days=14` cutoff for non-crypto classes.
- `alpha_engine/database.py` — run a one-shot SQL `UPDATE at_raw_picks SET status='EXPIRED_FORCE' WHERE asset_class IN ('EQUITY','ETF','BOND') AND age_days > 14 AND status='OPEN'`.

**Expected impact:**
- Removes phantom PnL drag. True class-level PnL will become visible (likely still negative, but honest).
- Reduces resolver load and DB bloat.

**Effort:** 2-4 hours.

---

### 1.2 Fix `dashboard_data.json` Freshness Pipeline

**What to do:**
- `dashboard_data.json` drives the `/audit` HTML and is **26 days stale** (2026-10-19). It still shows ghost picks (ADBE, NVDA, TQQQ, etc.).
- The generator script (`audit_trail/dashboard_generator.py` or equivalent) is either failing silently or not scheduled.
- Run it manually, inspect stderr, fix the breakage (likely a missing data dependency or DB connection), then ensure the hourly cron/GitHub Action that commits it is active.

**File / location:**
- `audit_trail/dashboard_generator.py`
- `.github/workflows/audit-dashboard.yml` (verify the cron still fires and the `[skip ci]` commit path is correct)
- `audit_dashboard/data/dashboard_data.json`

**Expected impact:**
- `/audit` HTML shows real active-pick counts and recent_closed cohorts.
- Eliminates the "ghost pick" confusion that wastes triage time.

**Effort:** 2-6 hours (depends on why it broke).

---

### 1.3 Demote ETF & BOND to `WATCH` with `position_size_pct=0`

**What to do:**
- EQUITY is already correctly demoted: all top picks are `WATCH`, `position_size_pct=0.0`, null TP/SL.
- ETF and BOND are still emitting `STRONG_BUY` picks with non-zero scores but **zero track record** (`db_n=0`, `intrabar_gate=NO_DATA`).
- Apply the same `CLASS_DEMOTED` gate to ETF and BOND in the production scanner until they pass `n>=100` resolved, `WR>=50%`, `PF>=1.5`.

**File / location:**
- `alpha_engine/non_crypto_policy.py` — add `ETF` and `BOND` to the `WATCH_ONLY_CLASSES` set.
- `alpha_engine/scanner.py` — ensure `position_size_pct=0` and `tp=None/sl=None` when `asset_class in ('ETF','BOND')` and `intrabar_gate != 'PASS'`.

**Expected impact:**
- Prevents any downstream system (paper trading, copy-trader, human dashboard) from treating these as actionable signals.
- Stops the bleeding of false confidence.

**Effort:** 1-2 hours.

---

## 2. MEDIUM FIXES (1-3 days)

### 2.1 Hook Non-Crypto Classes into Intrabar Resolution

**What to do:**
- Intrabar truth exists for CRYPTO (`at_signal_outcomes.intrabar_*`) but is **not populated** for EQUITY/ETF/BOND top picks.
- EQUITY has 250 resolved intrabar rows total, yet top picks show `intrabar_fwd_n=null`. This means the resolver is either not running for these asset classes or the symbols are not mapping correctly to the price-feed backend.
- ETF has only 44 resolved trades in history. BOND has 26.
- **Action:** Ensure the universal pick resolver (`audit_trail/universal_pick_resolver.py`) includes EQUITY, ETF, and BOND symbols in its daily run, and that the price feed (Yahoo Finance / FRED / polygon) returns first-touch prices for them.

**File / location:**
- `audit_trail/universal_pick_resolver.py`
- `alpha_engine/equity_price_failover.py` (if equity feed is separate)
- `alpha_engine/bond_data_fred.py` (for bond price feed)

**Expected impact:**
- `intrabar_gate` flips from `NO_DATA` to actual `PASS`/`FAIL` based on real price action.
- Enables honest edge calculation for each pick.

**Effort:** 1-2 days.

---

### 2.2 Backfill 90-Day DB History for ETF & BOND

**What to do:**
- The DB (`at_raw_picks`) has 90 days of data, but `db_n=0` for all top ETF/BOND picks. This means the current strategies (e.g., `etf_scanner`, `bond_duration_rotation`) are **newly emitted** with no historical overlap, or the `strategy` column does not match the lookup key.
- Run `tools/non_crypto_pick_audit.py --backfill 90` to reconcile strategy names and populate `db_n`, `db_wr`, `db_pf` for every active strategy.
- For BOND specifically, verify that `bond_yield_momentum`, `bond_mean_reversion`, etc., are writing to `at_raw_picks` with the correct `asset_class='BOND'` tag.

**File / location:**
- `tools/non_crypto_pick_audit.py`
- `alpha_engine/etf_scanner.py`
- `alpha_engine/bond_yield_curve_inversion.py`

**Expected impact:**
- Top picks will show non-zero `db_n`. Strategies with `n<20` can be identified and killed.
- Provides the data needed for FDR/SPA testing.

**Effort:** 1 day.

---

### 2.3 Kill Single-Source & Sub-20 Strategies

**What to do:**
- EQUITY has exactly **1** strategy with `n>=20`: `MeanReversionBB` (n=200, WR 50%, PF 1.5). Everything else is noise.
- ETF has **0** strategies with `n>=20`. BOND has **0**.
- **Action:** In the scanner / harness, blacklist any ETF/BOND strategy with `n<20`. For EQUITY, allow only `MeanReversionBB` and `unknown` (n=61) to emit until others accumulate 20+ resolved trades.
- This stops the strategy-sprawl that dilutes the tiny sample.

**File / location:**
- `alpha_engine/scanner.py` — add `min_strategy_n=20` for non-crypto classes.
- `alpha_engine/etf_strategy_harness.py`
- `alpha_engine/bond_strategy_harness.py` (or the relevant harness under `tools/kimi_research_2026_05_20/alpha_engine/`)

**Expected impact:**
- Concentrates emission onto the one EQUITY strategy that has a plausible edge.
- Prevents new, untested strategies from polluting the ETF/BOND track records.

**Effort:** 4-8 hours.

---

## 3. LONG-TERM FIXES (1-2 weeks)

### 3.1 Build Non-Crypto Walk-Forward Validator

**What to do:**
- CRYPTO has `walkforward_validator.py` and `forward_validator.py`. Non-crypto has nothing equivalent.
- Build a lightweight per-class walk-forward harness:
  - Train on 60 days, test on 30 days.
  - Require OOS PF >= 1.2 and WR >= 45% before a strategy graduates to production emission.
  - Run weekly, not daily, to avoid overfitting.
- This is the only way to get `forward_wr` and `forward_trades` populated for EQUITY/ETF/BOND.

**File / location:**
- New: `alpha_engine/non_crypto_walkforward.py`
- Consumes: `alpha_engine/database.py` (historical `at_raw_picks`)
- Outputs: JSON per strategy to `audit_dashboard/data/non_crypto_wf_results.json`

**Expected impact:**
- Strategies with in-sample curve-fitting are caught before they emit live picks.
- `forward_wr` becomes a real gate, not a null field.

**Effort:** 1 week.

---

### 3.2 Rehabilitate EQUITY via MeanReversionBB Graduation Path

**What to do:**
- `MeanReversionBB` is the only EQUITY sleeve with n=200, WR 53.9%, PF 1.76 (from `strategy_perf_by_class`).
- It is currently blocked by:
  - `MDD=0.9999` ( registry MDD says ~100% drawdown — likely a data bug or legacy bad pick)
  - `SPA p=0.256` (fails significance)
  - `single_source_ok=false` (only one profitable strategy)
  - `bootstrap_ci` lower bound is negative.
- **Action:**
  1. Fix the MDD calculation: verify if the 0.9999 value is real or an artifact of one catastrophic pick (e.g., a leveraged ETF mis-tagged as EQUITY).
  2. Run a 10,000-iteration paired bootstrap vs. SPY benchmark for the `MeanReversionBB` closed set.
  3. If it passes benchmark-beat + CI lower > 0, graduate it to a standalone `EQUITY_ONLY` scanner with position size capped at 1%.

**File / location:**
- `alpha_engine/benchmark_closed_ledger.py` (reuse existing benchmark harness)
- `alpha_engine/proven_edge_strategies.py` (add `MeanReversionBB` if it passes)
- `alpha_engine/position_sizer.py` (enforce 1% cap for single-source equity)

**Expected impact:**
- EQUITY could become the first non-crypto class to reach `WATCH` → `READY`.
- Even if it only trades 1-2 names per week, it proves the non-crypto stack can work.

**Effort:** 3-5 days.

---

### 3.3 ETF & BOND: Strategy Pivot or Formal Retirement

**What to do:**
- **ETF:** The current intrabar record (n=44, WR 2.2%, PF 0.022) is not a "fixable" pipeline issue — it is a strategy-design catastrophe. The current approaches (`extreme_oversold_bounce`, `hyperopt_connors_rsi2`, etc.) are uniformly unprofitable at first-touch resolution.
- **BOND:** 26 resolved trades, 7.7% WR. Bond markets are carry-dominated and low-vol; intraday TP/SL breakouts are structurally misaligned.
- **Options:**
  - **Option A (Pivot):** Switch ETF to a monthly-regime rotation model (e.g., `etf_vix_regime_rotation.py` + dual momentum) with end-of-month rebalancing instead of intraday TP/SL. Switch BOND to a duration-rotation signal (e.g., yield-curve slope) with weekly holds.
  - **Option B (Retire):** Formally deprecate ETF and BOND live emission. Keep the harnesses in incubator mode until a new signal source is proven.

**File / location:**
- `alpha_engine/etf_strategy_harness.py` (refactor or add `mode='incubator'`)
- `alpha_engine/bond_yield_curve_inversion.py` (pivot to weekly-hold logic)
- `alpha_engine/non_crypto_policy.py` (add `DEPRECATED_CLASSES = ['ETF','BOND']` if retiring)

**Expected impact:**
- Stops wasting compute and DB space on asset classes where the current model architecture is structurally mismatched.
- If pivoted, gives a realistic path to n>=100 within 6 months.

**Effort:** 3-7 days (pivot) or 2 hours (retire).

---

## 4. VERDICT: Are These Classes Salvageable?

### EQUITY — Yes, with focused rehab
- **Salvageable?** **Yes.** It has one strategy (`MeanReversionBB`, n=200, PF 1.76) with a real track record.
- **What it takes:**
  1. Purge stale picks and freeze emission to `WATCH`.
  2. Fix MDD artifact and rerun SPA/bootstrap.
  3. Graduate `MeanReversionBB` as a single-source pilot with 1% position cap.
  4. Require n>=100 and PF>=1.5 before any second strategy is added.
- **Timeline:** 1-2 weeks to pilot readiness; 3 months to multi-source maturity.

### ETF — No, under current architecture
- **Salvageable?** **Only if pivoted.** The current intraday TP/SL model on ETFs is generating 2.2% WR. That is not a tuning problem; it is a model-structure problem.
- **What it takes:**
  1. Immediate retirement of all intraday ETF strategies.
  2. Either (a) adopt a monthly dual-momentum / sector-rotation regime with end-of-month holds, or (b) formally deprecate.
  3. If adopted, run 6 months of paper trades before live emission.
- **Timeline:** 1 week to retire; 2 months to design and backtest a pivot; 6 months to prove.

### BOND — No, under current architecture
- **Salvageable?** **Only if pivoted.** Bonds do not generate enough intraday volatility for TP/SL breakouts. 7.7% WR on 26 trades is conclusive.
- **What it takes:**
  1. Immediate retirement of all intraday bond strategies.
  2. Pivot to a macro-duration-rotation model (e.g., yield-curve slope + Fed policy regime) with weekly or monthly rebalancing.
  3. Use `alpha_engine/bond_yield_curve_inversion.py` as the seed, but refactor for hold-period signals, not intraday scalps.
- **Timeline:** 1 week to retire; 1 month to design pivot; 6 months to prove.

---

## Appendix: Fix Summary Table

| # | Fix | Classes | Effort | File(s) |
|---|-----|---------|--------|---------|
| 1.1 | Purge stale open picks (>14d) | EQUITY, ETF, BOND | <1d | `pick_revalidator.py`, `database.py` |
| 1.2 | Fix `dashboard_data.json` freshness | All | <1d | `dashboard_generator.py`, GHA workflow |
| 1.3 | Demote ETF/BOND to WATCH | ETF, BOND | <1d | `non_crypto_policy.py`, `scanner.py` |
| 2.1 | Hook into intrabar resolver | EQUITY, ETF, BOND | 1-2d | `universal_pick_resolver.py`, price feeders |
| 2.2 | Backfill 90d DB history | ETF, BOND | 1d | `non_crypto_pick_audit.py`, scanners |
| 2.3 | Kill sub-20 strategies | EQUITY, ETF, BOND | <1d | `scanner.py`, harnesses |
| 3.1 | Build walk-forward validator | EQUITY, ETF, BOND | 1wk | New: `non_crypto_walkforward.py` |
| 3.2 | Graduate MeanReversionBB | EQUITY | 3-5d | `benchmark_closed_ledger.py`, `proven_edge_strategies.py` |
| 3.3 | Pivot or retire ETF/BOND | ETF, BOND | 3-7d | Harnesses, `non_crypto_policy.py` |

---

*Prepared by Kilo | 2026-11-14*  
*Based on audit evidence: `evidence_money_ready_verdict.json`, `evidence_intrabar_truth.json`, `evidence_pick_summary_stats.json`, `noncrypto_deep_dive.md`*
