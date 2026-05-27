# Remaining Items — EAGLE Session 2026-05-27
**Model:** opencode / deepseek-v4-flash-free  
**Timestamp:** 2026-05-27 02:17 EST  
**Source:** End-to-end pipeline audit — items deferred from Quick Wins

---

## Sprint 1 (Data Integrity — Blocks Everything)

These P0 issues make ALL dashboard metrics untrustworthy. Fix order matters: each unlocks the next.

### 1. Fix signal_outcomes Resolver (82 days stale)
- **Incident:** `signal_outcomes` table last populated ~March 4 2026. Outcome resolver pipeline dead.
- **Impact:** ALL forward-WR metrics unverifiable. Every "WR 80%" claim has no outcome data backing it.
- **Fix:** Already partially wired in `.github/workflows/outcome-resolver.yml` (May 25). Monitor next 7 days for data flow. If still 0 rows, the `active_picks_sync.py --apply` step needs debugging.
- **Priority:** P0 — unlocks everything else

### 2. PnL Reconciliation (38.97% mismatch)
- **Incident:** 38.97% of sampled closed picks show mismatch between `pnl_pct` and actual price movement.
- **Impact:** ~10K corrupt rows. ALL cohort WR/PF stats are suspect for classes where these rows cluster.
- **Fix:** Cross-reference `trading_picks.pnl_pct` with `(exit_price - entry_price) / entry_price` for every row where both prices exist. Flag mismatches > 5%.
- **Priority:** P0 — gate before any real-money claim

### 3. WON Label Backfill (2,531 contradicted rows)
- **Incident:** 2,531 rows with `status='WON'` but `pnl_pct < 0`, avg pnl = -41.13%.
- **Impact:** Skews every WON/LOST cohort analysis. 2,531 winning trades that lost money.
- **Fix:** `.github/workflows/won-pnl-contradiction-backfill.yml` already created. Trigger via GitHub UI with `apply=true`.
- **Priority:** P0

### 4. Ghost Row Dedup (56,559 rows)
- **Incident:** 56,559 duplicate rows in `trading_picks`. Top cohort: 20,474 identical MATICUSDT entries.
- **Impact:** Inflates n counts by 2-10x per symbol. WR/PF denominators are wrong.
- **Fix:** `DELETE FROM trading_picks WHERE (asset_class, strategy, symbol, entry_time) GROUP BY HAVING COUNT(*) > 1` — keep the row with the earliest `created_at`.
- **Priority:** P0

### 5. Trust Score Backfill (99.99% NULL)
- **Incident:** `trust_score` is NULL on 99.99% of closed picks.
- **Impact:** High Conviction overlay (which filters by trust_score) is unverified on nearly all closed picks. HC tab could be showing random subset.
- **Fix:** Compute trust_score retroactively: `trust_score = min(1, max(0, (forward_wr - 0.35) / 0.40))` for every closed pick with forward_wr data. For picks without fwd_wr, leave NULL (honest).
- **Priority:** P0

### 6. Unfreeze Forward Validator (29.2M open, 270h frozen)
- **Incident:** `forward_validator` has 29.2M open positions and has been frozen for 270 hours.
- **Impact:** No picks are being resolved. TP/SL hits are not recorded. The entire closed-pick ledger is stopped.
- **Fix:** Kill the frozen process, restart with `--max-open 50000`, add a watchdog cron that restarts if frozen > 1h.
- **Priority:** P0

---

## Sprint 2 (Pipeline Hygiene)

### 7. FOREX M-007 Hard Disable Assessment
- **Status:** FOREX hard-disabled (M-007 in quality_gates.py line 8216) until carry-factor rehab achieves PF>1.0 / WR>45% / n>30.
- **Reality:** `cta_replicator` FOREX cohort shows PF 2.51 standalone (n=109). The disable is blanket — it kills the one working FOREX strategy.
- **Action:** Lift M-007 for `cta_replicator` FOREX only. Keep hard-disable for all other FOREX sources.
- **File:** `audit_trail/quality_gates.py` line 8216

### 8. ETF VIX-Regime Wiring (H-037)
- **Status:** ETF VIX carry backtest shows PF 2.05→3.22 on 11-year SPDR data. NOT wired to production.
- **Action:** Wire `etf_vix_carry` from `reports/H-037*` into `proven_research_strategies.py`. Gate with VIX < 25 (same as ETF quality gate). Start at EXPERIMENTAL tier.
- **File:** `alpha_engine/proven_research_strategies.py`

### 9. BOND Scanner Activation
- **Status:** BOND n=11, PF 0.66, sizing_allowed=false. The `bond_scanner.py` exists but is not in production cron.
- **Action:** Add `bond_scanner.py` to `.github/workflows/production-scanner.yml` as a nightly step. Set TLT/IEF/SHY as initial universe. Gate: min n=30 before any BOND pick appears on dashboard.
- **Priority:** Low — BOND is 100% deferred by every 90-day plan

### 10. PENNY_MEME Research Pipeline
- **Status:** MEMECOIN PF 0.499 / WR 15.7% (n=1869). PENNY_STOCK WR 6.76% / PF 0.19 (n=148). Full quarantine recommended.
- **Action:** No production picks. Create a research-only pipeline that:
  - Collects penny/meme picks into a separate `research_picks` table
  - Runs the same gates but output goes to a `/research` dashboard tab
  - Purpose: gather n>500 clean sample before re-evaluating
- **Priority:** Low per SUPREME_PLAN priority tier

---

## Sprint 3 (Strategy Expansion)

### 11. Mean-Reversion Production Wrapper
- **Problem:** 30+ mean-reversion strategies in `baby_strategies/` but only 3 are wired to production (`proven_vwap_mean_reversion`, `bollinger_mean_reversion_survivor`, `keltner_mean_reversion_survivor`).
- **Action:** Create `alpha_engine/mean_reversion_engine.py` that:
  - Wraps Connors R3, Keltner MR, Bollinger MR, VWAP MR, Williams %R
  - Applies ADX < 25 gate from Quick Win #4
  - Emits single consolidated pick per symbol per cycle (not 5 competing picks)
  - Writes to a single `mean_reversion_consensus` strategy name for tracking

### 12. BTC/ETH Pairs Spread (Sharpe 3.77)
- **Problem:** `pairs_spread_btceth.py` exists in `baby_strategies/` with documented Sharpe 3.77 (Tadi 2025 research). Not in production.
- **Action:** Wire to production as a standalone strategy. Use cointegration z-score ±2 entry, TP at z-score 0, SL at z-score ±3. Start at 0.5x EXPERIMENTAL.
- **Risk:** The Tadi 2025 research used different period. Need our own cointegration test on 2023-2026 data.

### 13. EQUITY PEAD Shadow → Probation
- **Status:** `equity_pead_strategy.py` in SHADOW mode (EQUITY_PEAD_ENABLED=0). Pooled OOS WR=53.2% n=1,964 from forward signal research.
- **Action:** Flip to PROBATION (default ON for 45 large-cap symbols, monitor 30 days). Gate: TP=+6%, SL=-3%, RR=2.0, hold=30 days.
- **File:** `alpha_engine/equity_pead_strategy.py`

### 14. COMMODITY Seasonality Extension
- **Action:** Add grain harvest cycles (ZC/ZW/ZS), energy winter draws (NG), metals seasonals as additive criteria to existing COT commercial extremes (PF 1.60). Target: lift COMMODITY WR from 54.5% to 58%+.
- **File:** `alpha_engine/commodity_strategy_harness.py`

---

## Sprint 4 (Institutional Readiness)

### 15. Two-Stage Gate Implementation (from SUPREME_PLAN)
- **Stage 1 — Paper-trustworthy (Day 90):** PF > 1.3 / WR > 48% / Sharpe > 1.0 / MDD < 25%
- **Stage 2 — Institutional pilot:** PF > 1.5 / WR > 50% / Sharpe > 1.5 / MDD < 20% held 6 consecutive months
- **Action:** Wire these thresholds into `audit_trail/money_ready_verdict.py` as hard gates (not just dashboard badges)

### 16. Transaction Cost & Slippage Modeling
- **Problem:** No transaction cost or slippage modeled anywhere. Backtests are fiction for crypto-perps, pennies, microcaps.
- **Action:** Add `cost_per_trade = 0.001` (10bps) for CRYPTO, `0.002` for EQUITY, `0.0005` for FOREX/FUTURES. Deduct from pnl_pct at pick creation time in `production_scanner.py`.

### 17. Portfolio-Level Correlation Caps
- **Problem:** No correlation-aware position sizing. Two LONG CRYPTO picks from different strategies on the same symbol are treated as independent.
- **Action:** Add a portfolio correlation matrix (rolling 30d) that caps net exposure to correlated pairs at 40% of total.

---

## Database Migration Plan

```sql
-- Step 1: Create roadmap_items table (Quick Win #8)
CREATE TABLE roadmap_items (...);

-- Step 2: Migrate incidents from 18 INCIDENT_<CLASS> tables
INSERT INTO roadmap_items (item_type, severity, asset_class, title, description, component, reporter, sprint, status, created_at)
SELECT 'incident', 'P0', asset_class, title, description, component, reporter, 'Sprint 1', 'backlog', created_at
FROM incident_stocks UNION ALL ...;

-- Step 3: Migrate enhancements from 18 ENHANCEMENT_<CLASS> tables
INSERT INTO roadmap_items (item_type, severity, asset_class, title, description, component, reporter, sprint, status, created_at)
SELECT 'enhancement', 'HIGH', asset_class, title, description, component, reporter, 'Sprint 2', 'backlog', created_at
FROM enhancement_stocks UNION ALL ...;

-- Step 4: Drop old per-class tables (after 30-day migration verification)
```

---

## Per-Asset-Class: Top Recommended Strategy

| Asset Class | Top Strategy | Current PF/n | Target PF | Path |
|-------------|-------------|-------------|-----------|------|
| **CRYPTO** | Funding Rate Carry (Sharpe 8.19) + ADX-gated Connors R3 | 1.36 / 8,122 | >1.5 | Fix confidence inversion → wire ADX gate → isolate funding_carry |
| **EQUITY** | `stocks_rsi2_pullback` (88.9% WR) + PEAD shadow | 1.57 / 420 | >2.0 | Promote PEAD to probation → keep rsi2_pullback as anchor |
| **FOREX** | `cta_replicator` SHORT (PF 2.51 standalone, 93% USDJPY) | -0.27 / 5,069 | >1.5 | Lift M-007 for cta_replicator only → fix TP/SL asymmetry |
| **COMMODITY** | COT commercial extremes (PF 1.60) + CT=F (66.7% WR) | 1.42 / 354 | >1.8 | Rehab CT=F → add seasonality → fix filter-survival gap |
| **ETF** | Sector rotation + VIX regime (backtest PF 2.05→3.22) | 1.48 / 106 | >2.0 | Wire VIX regime to prod → wait for n>200 |
| **BOND** | Deferred (n=11, PF 0.66) | 0.66 / 11 | N/A | Activate scanner → gather n>30 → re-evaluate |
| **FUTURES** | Dead (n=0) | 0.00 / 0 | N/A | Separate from COMMODITY misclassification → rebuild universe |
| **PENNY_MEME** | Quarantined (PF 0.499 / WR 15.7%) | 0.50 / 2,017 | N/A | Research-only pipeline → kill if n>500 confirms WR<20% |
