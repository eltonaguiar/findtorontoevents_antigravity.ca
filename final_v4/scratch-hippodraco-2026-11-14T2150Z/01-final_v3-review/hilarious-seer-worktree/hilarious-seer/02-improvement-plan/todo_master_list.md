# Master Todo List — Improvement Plan

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Status:** Synthesis of all peer work, ready for implementation

---

## A. GENERAL FIXES (Cross-Cutting, All Asset Classes)

### A1 — PnL Unit Contract [P0]
- [ ] Standardize ALL PnL writes to **decimal ratio** (not percent)
- [ ] Fix `mercury2/scanner.py:481-483` — remove `* 100`
- [ ] Fix `sync_all_picks_to_mysql.py:660-661,858-859` — remove `pnl *= 100` heuristic
- [ ] Fix `dashboard/generate_dashboard.py:24` — add `%` sign at display layer only
- [ ] Add CI assertion: `|pnl| > 100` triggers build fail unless `unit` field declared
- [ ] Run `quick_wins/shared/normalize_pnl_units.py` migration across SQLite + MySQL + JSON
- [ ] Spot-check 50 random rows vs live Binance/Yahoo prices
- [ ] **Owner:** backend/data integrity
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** none

### A2 — Price Freshness Pipeline [P0]
- [ ] Wire `alpha_engine/universal_price_enricher.py` into `audit-dashboard.yml` hourly cron
- [ ] Fix `fetch_stock_prices.py` 60s timeout → 300s or non-fatal
- [ ] Label `UNQUOTED` when feed fails; never fabricate `0%`
- [ ] Fix forex cache (`data/forex_rate_cache/`) — 161d stale
- [ ] Fix commodity cache (`data/commodity_price_cache/`) — 161d stale
- [ ] Fix equity cache (`data/equity_quote_cache/`) — empty except `.gitkeep`
- [ ] Add hard TTL: dashboard build FAILS (not warns) when feed > 24h stale
- [ ] **Owner:** infra/pipeline
- [ ] **ETA:** 5 days
- [ ] **Blocked by:** none

### A3 — Zombie Drain + Dedup [P0]
- [ ] Quarantine picks >30 days stale to `zombie_ledger` (never delete)
- [ ] Dedup composite key: `(symbol, strategy, direction, entry_time, entry_price)`
- [ ] Resolve TIME_EXIT picks via `universal_pick_resolver.py` with live prices
- [ ] Fix resolver output persistence (`audit_trail/data/universal_resolved_picks.json`)
- [ ] Ensure `pick_history` has ≥10% CLOSED/TP/SL events (up from 0%)
- [ ] **Owner:** backend/data integrity
- [ ] **ETA:** 5 days
- [ ] **Blocked by:** A2 (need live prices first)

### A4 — Store Reconciliation [P0]
- [ ] Make `live_picks.db` single source of truth for active picks
- [ ] MySQL and dashboard JSON become read-only mirrors
- [ ] Run `tools/cross_db_consistency.py` and resolve orphaned keys
- [ ] Publish one canonical cohort definition per class as row-level query
- [ ] Every rate carries `{cohort_id, n, filter_hash}`
- [ ] CI fails when two live files disagree on same `cohort_id`
- [ ] **Owner:** backend/data integrity
- [ ] **ETA:** 5 days
- [ ] **Blocked by:** A1, A3

### A5 — Exit Taxonomy Fix [P1]
- [ ] Adopt `docs/DATA_CONTRACT.md` from finpredict-v2 as canonical
- [ ] Add CI assertion: `resolution_method` + `exit_reason` populated for ≥95% of closed rows
- [ ] Add `stop_loss_initial` + `stop_loss_at_exit` fields for trailing-stop rows
- [ ] Investigate B4: 79% of ETF SL rows, 66% of EQUITY SL rows exited inside the stop
- [ ] **Owner:** backend/resolver
- [ ] **ETA:** 7 days
- [ ] **Blocked by:** A3

### A6 — Trial Count Registry [P1]
- [ ] Pre-register every forward test with trial ID
- [ ] Registry increments on every run
- [ ] Pass threshold: |t| ≥ 3.5 (or BH-FDR q=0.10 across actual count)
- [ ] Never use 1.96 without multiplicity correction
- [ ] **Owner:** stats/validation
- [ ] **ETA:** 5 days
- [ ] **Blocked by:** none

### A7 — Cost Gate Enforcement [P1]
- [ ] Implement `tools/per_class_cost_gate.py` (started today)
- [ ] Wire into `tools/hc_gates_python.py`
- [ ] Enforce by default with fail-open on missing evidence
- [ ] Retroactive simulation: verify −617.5pp → +238.3pp claim
- [ ] **Owner:** backend/gatekeeping
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** none

### A8 — Verdict Registry [P1]
- [ ] Every verdict file carries `evidence_hash` + `generated_at`
- [ ] Consumer refuses to act on stale hash
- [ ] CI greps for `VALIDATED`/`PROVEN` and fails without matching registry entry
- [ ] **Owner:** infra/ci
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** none

---

## B. GITHUB ACTIONS FIXES

### B1 — Alpha Engine Workflow Repair [P0]
- [ ] Fix alpha engine workflow (9 cancelled + 1 failure of last 10 runs)
- [ ] Add `concurrency:` blocks to prevent cancel-cascade
- [ ] Add `timeout-minutes:` to all 360 workflow files
- [ ] Stagger cron schedules to avoid collision
- [ ] **Owner:** infra/ci
- [ ] **ETA:** 5 days
- [ ] **Blocked by:** none

### B2 — Horizon Harness CI Gate [P1]
- [ ] Ship `pi_horizon_validation.py` as CI gate (exit code 1 on failure)
- [ ] Gate criteria: n≥60, 95% CI excludes 50%, PF>1.05, win-majority ≥66% of windows
- [ ] Multiple-testing-adjusted, capital-adjusted
- [ ] **Owner:** ci/validation
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** A1, A2, A3

### B3 — Freshness Guardian Extension [P1]
- [ ] Extend `tools/db_freshness_check.py` to cover:
  - `fetch_prices.php` (currently 404 since 2026-04-29)
  - `signal_outcomes` resolution (~80d stale)
  - `hilarious-seer` crypto dataset (172d stale)
- [ ] Hard fail on TTL exceed, not just warn
- [ ] **Owner:** ci/monitoring
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** none

### B4 — PnL Unit Sanity Gate [P1]
- [ ] CI gate fails when mixed PnL units detected in same store
- [ ] Reject `|pnl| > 100` unless `unit` field declared
- [ ] Run on every commit to `alpha_engine/data/` or `audit_dashboard/data/`
- [ ] **Owner:** ci/data-quality
- [ ] **ETA:** 2 days
- [ ] **Blocked by:** A1

### B5 — Conflict Marker Safety [P2]
- [ ] Verify `.github/scripts/assert_no_conflict_markers.sh` runs on all PRs
- [ ] Add to pre-commit hooks
- [ ] **Owner:** ci/safety
- [ ] **ETA:** 1 day
- [ ] **Blocked by:** none

---

## C. ASSET-CLASS-SPECIFIC FIXES

### CRYPTO
- [ ] **C1:** Route `kimi_riseoftheclaw` through intrabar resolver (resolves +727.3pp leak) [P0]
- [ ] **C2:** Kill CRYPTO SWING emission (n=243, PF 0.457, −328.6pp) [P0]
- [ ] **C3:** Forward-test POSITION horizon only, frozen rules, n≥100, gate PF≥1.3, WR≥55% [P1]
- [ ] **C4:** Restate ITERATION-005 vs buy-and-hold benchmark (paired bootstrap) [P1]
- [ ] **C5:** Add survivorship-adjusted universe (include delisted coins) [P1]
- [ ] **C6:** Add taker-cost stress (0.15%, 0.2% scenarios) [P1]
- [ ] **C7:** Reduce single-source concentration (94–98% luxalgo) [P2]
- [ ] **Owner:** strategy/crypto
- [ ] **ETA:** 2–8 weeks
- [ ] **Blocked by:** A1, A2, A3, B1

### EQUITY
- [ ] **E1:** Freeze H10 RSI(2) parameters, start clean forward OOS (90 days / 30 round trips) [P1]
- [ ] **E2:** Report Sharpe with and without best day (+11.20% on 2025-04-09) [P1]
- [ ] **E3:** 2-day-lag test: confirm Sharpe ≥ 1.0 with realistic execution lag [P1]
- [ ] **E4:** Risk-matched benchmark comparison (not raw Sharpe) [P1]
- [ ] **E5:** Build fundamental factor backtest (Piotroski + value + quality, 10+ year history) [P2]
- [ ] **E6:** Market-neutral long/short construction [P2]
- [ ] **Owner:** strategy/equity
- [ ] **ETA:** 4–12 weeks
- [ ] **Blocked by:** A1, A2, A3

### ETF
- [ ] **T1:** Build 10+ year ETF price database (50 ETFs) [P2]
- [ ] **T2:** Implement risk-parity trend backtest [P2]
- [ ] **T3:** Add cost model + regime filter (SPY > 200d SMA) [P2]
- [ ] **T4:** Walk-forward analysis (10-fold) [P2]
- [ ] **Owner:** strategy/etf
- [ ] **ETA:** 8–16 weeks
- [ ] **Blocked by:** A1, A2

### FOREX
- [ ] **F1:** Fix price feed (Frankfurter/OANDA) [P2]
- [ ] **F2:** Purge 11 frozen phantoms [P2]
- [ ] **F3:** Enable PR#6 call sites [P2]
- [ ] **F4:** Build carry feed (FRED/ECB rates) [P2]
- [ ] **F5:** Backtest carry + trend overlay [P3]
- [ ] **Owner:** strategy/forex
- [ ] **ETA:** 12–20 weeks
- [ ] **Blocked by:** A1, A2

### BONDS
- [ ] **B1:** Wire FRED/yfinance for Treasury ETF prices [P2]
- [ ] **B2:** Backfill 5+ years of TLT/IEF/SHY/TBT prices [P2]
- [ ] **B3:** Backtest duration trend [P3]
- [ ] **Owner:** strategy/bonds
- [ ] **ETA:** 12–20 weeks
- [ ] **Blocked by:** A1, A2

### FUTURES / COMMODITIES
- [ ] **X1:** Procure real futures data feed (CME/ICE/Bloomberg) [P3]
- [ ] **X2:** Build roll handling + continuous contracts [P3]
- [ ] **X3:** Build contango/backwardation model [P3]
- [ ] **X4:** Backtest CTA trend [P3]
- [ ] **X5:** Remove from BLOCKED_ASSET_CLASSES only after X1–X4 complete [P3]
- [ ] **Owner:** strategy/futures
- [ ] **ETA:** 20–40 weeks
- [ ] **Blocked by:** A1, A2, real feed procurement

### MUTUAL FUNDS
- [ ] **M1:** Keep `NOT_BUILT` label on dashboard [P0]
- [ ] **M2:** Do NOT build live pick class (monthly NAV incompatible) [P0]
- [ ] **M3:** If desired: monthly tactical-rotation research only (not live picks) [P3]
- [ ] **Owner:** strategy/mutual_funds
- [ ] **ETA:** N/A (do not build)
- [ ] **Blocked by:** structural incompatibility

---

## D. BACKTEST / SIMULATION REQUIREMENTS

### D1 — CRYPTO Stop Fill Replay [P0]
- [ ] Replay 3,500 closed CRYPTO rows with gap-aware fill
- [ ] Measure planned vs realized stop levels per system
- [ ] Verify breakeven claim (−617.5pp → +238.3pp is retroactive simulation, not forward)
- [ ] Output: `stop_fill_replay_crypto.json` (childlike-airport already produced this)
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 3 days
- [ ] **Blocked by:** A2, A3

### D2 — CRYPTO ITERATION-005 Benchmark Restatement [P1]
- [ ] Re-run trend strategy vs buy-and-hold benchmark (same 10 assets)
- [ ] Paired bootstrap: 10,000 resamples of (trade − B&H) pairs
- [ ] Random-entry MC timing test (same-asset, direction-aware, window-matched)
- [ ] Report: pass_95, MC percentile, excess Sharpe, maxDD vs B&H
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 1 week
- [ ] **Blocked by:** A1, A2, A3

### D3 — EQUITY H10 Clean Forward OOS [P1]
- [ ] Freeze H10 parameters in a file (timestamped, signed)
- [ ] Run for 90 calendar days or 30 round trips (whichever comes first)
- [ ] Daily log: entry, exit, PnL, benchmark (SPY total return)
- [ ] Report: Sharpe, PF, WR, DSR, benchmark excess, best-day sensitivity
- [ ] Kill condition: fails any gate → EQUITY is beta, stop emitting
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 90 days (waiting period)
- [ ] **Blocked by:** A1, A2, A3

### D4 — ETF Multi-Asset Trend Backtest [P2]
- [ ] 10+ year history, 20–50 ETFs, risk-parity weighting
- [ ] Cost model: 0.05% commission + ETF spread
- [ ] Regime filter: SPY > 200d SMA
- [ ] Walk-forward: 10-fold, purged CV
- [ ] Benchmark: risk-matched portfolio (not B&H)
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 4 weeks
- [ ] **Blocked by:** A1, A2

### D5 — VWAP Mean Reversion Re-Test [P3]
- [ ] Re-run with correct annualization (daily → annual, not bar → annual)
- [ ] Real PBO gate (CSCV, not the inverted one)
- [ ] Intrabar stops (not close-only)
- [ ] Report: corrected Sharpe, PF, PBO, DSR
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 2 weeks
- [ ] **Blocked by:** A1, A2

### D6 — 683-Strategy Bonferroni Screen [P2]
- [ ] Run Bonferroni correction across all 683 strategies in zoo
- [ ] Report: how many survive at α=0.05/683, α=0.01/683
- [ ] Identify false positive rate
- [ ] **Owner:** simulation/validation
- [ ] **ETA:** 1 week
- [ ] **Blocked by:** A1, A3

---

## E. MACHINE LEARNING FIXES

### E1 — Gatekeeper Leakage Fix [P1]
- [ ] Confirm leakage mask default=ON in production
- [ ] Run retrain on clean data (post-A1, A2, A3)
- [ ] Bundle parity tests: old bundle vs new bundle on same holdout
- [ ] A/B sleeve behavior validation
- [ ] Test environment mutation checks
- [ ] **Owner:** ml/gatekeeper
- [ ] **ETA:** 2 weeks
- [ ] **Blocked by:** A1, A2, A3

### E2 — Confidence Calibration [P2]
- [ ] Add `CalibratedClassifierCV(method="isotonic", cv=3)` to `crypto_ml_edge` pipeline
- [ ] Clip ensemble outputs to [2nd, 98th] percentile of training-set predictions
- [ ] Report calibration curves before/after
- [ ] **Owner:** ml/calibration
- [ ] **ETA:** 1 week
- [ ] **Blocked by:** none

### E3 — Heterogeneous Stacking [P2]
- [ ] Wire LightGBM + GRU-Attention + Ridge linear model as meta-features
- [ ] Existing in `ml_battleground/` but not wired together
- [ ] Cross-validation to prevent leakage
- [ ] **Owner:** ml/ensemble
- [ ] **ETA:** 3 weeks
- [ ] **Blocked by:** none

---

## Dependency Graph

```
A1 (PnL units) ──┬──► A3 (zombies) ──┬──► C1-C7 (crypto)
                 │                    ├──► E1-E3 (ML)
                 │                    └──► D1-D6 (simulations)
                 │
A2 (freshness) ──┤──► A3 ──► A4 (reconciliation)
                 │
B1 (GHA alpha) ──┘

A5 (exit taxonomy) ──► D1, D5
A6 (trial registry) ──► D2-D6
A7 (cost gate) ──► ALL asset classes
A8 (verdict registry) ──► B2

B2 (harness gate) ──► ALL asset classes
B3 (freshness guardian) ──► A2
B4 (PnL sanity) ──► A1

C1-C2 (crypto fixes) ──► D1
C3-C4 (crypto forward) ──► D2, D3
E1 (gatekeeper) ──► C4, D2
```

---

## 90-Day Sprint Priority

| Week | Focus | Tasks |
|------|-------|-------|
| 1 | A1, A2, B1 | PnL units, price freshness, alpha engine CI |
| 2 | A3, A4, B3 | Zombie drain, store reconciliation, freshness guardian |
| 3 | A5, B2, B4 | Exit taxonomy, horizon harness gate, PnL sanity CI |
| 4 | C1, C2, D1 | CRYPTO stop fill fix, kill SWING, replay simulation |
| 5 | C3, D2 | CRYPTO POSITION forward test begins, ITERATION-005 benchmark restatement |
| 6–8 | E1, E2, E3 | Gatekeeper retrain, calibration, stacking |
| 9–12 | E1, D3 | EQUITY H10 forward OOS, waiting period |
| 13 | Review | StrategyCertifier on all live classes; decision: scale or wind down |

---

## Resource Estimates

| Category | Tasks | Dev Weeks | Total |
|----------|-------|-----------|-------|
| General fixes (A1–A8) | 8 | 3 weeks | 24 dev-weeks |
| GHA fixes (B1–B5) | 5 | 1 week | 5 dev-weeks |
| Asset-class fixes (C1–X5) | 25 | varies | ~40 dev-weeks |
| Simulations (D1–D6) | 6 | 2 weeks | 12 dev-weeks |
| ML fixes (E1–E3) | 3 | 2 weeks | 6 dev-weeks |
| **Total** | **47** | | **~87 dev-weeks** |

With 2 developers: ~44 weeks (11 months)
With 3 developers: ~29 weeks (7 months)
With 4 developers: ~22 weeks (5.5 months)

**Critical path:** A1 → A2 → A3 → A4 → C1/C2 → D1 → C3 → D2 (9 weeks to first CRYPTO forward result)
