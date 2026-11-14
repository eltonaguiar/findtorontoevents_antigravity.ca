# Improvement Plan — Todos (final_v3, 2026-11-14)

**Scope:** All asset classes (stocks, crypto, forex, bonds, ETFs, mutual funds)  
**Decision rule:** No real-money allocation until ≥1 asset class passes all gates with benchmark-relative net expectancy CI excluding zero, DSR ≥0.95 (cumulative trial count), PBO ≤0.10, and ≥100 clean forward closes over ≥3 distinct months.

---

## A. General Fixes (all classes)

| # | Todo | Owner | Acceptance Test | Priority |
|---|---|---|---|---|
| G-1 | Canonical PnL unit contract: explicit quote timestamp/source/status and exit price/time/method for every trade; missing/stale quotes must NOT become zero PnL | Data eng | `after_cost_net_per_trade` non-null for ≥95% of closed rows; zero-PnL frozen picks = 0 | P0 |
| G-2 | Make all outcomes terminal and auditable: EXPIRED/TIME exits kept in denominator; prevent EXPIRED→WON relabeling | Data eng | 0 EXPIRED→WON mislabels in CI gate test | P0 |
| G-3 | Deduplicate emissions by economic trade identity; clustered inference for overlapping/re-emitted trades | Data eng | Dedup hash coverage ≥95% of closed rows | P0 |
| G-4 | Reconcile `money_ready_verdict`, `pf_registry`, `recent_closed`, `at_raw_picks` at row level; canonicalize asset-class labels | Data eng | Row counts + inclusion rules published; cohort divergence explained | P0 |
| G-5 | Implement SubQ (subquery) coverage comparison across strategy options before recommending any class | Quant eng | SubQ report with coverage matrix + recommendation | P0 |
| G-6 | Per-class cost gate: validate `tools/per_class_cost_gate.py` index built from closed rows + `tools/data/transaction_costs.json` | Quant eng | Gate passes/fails deterministically for known classes; ETF/COMMODITY correctly blocked | P0 |
| G-7 | Add `resolution_method` field required on every closed pick; backfill for existing 3,500 rows | Data eng | 100% of closed rows have non-null `resolution_method` | P0 |
| G-8 | Block pseudo-picks: no synthetic/replay rows mixed with realized forward trades; distinct cohorts | Data eng | CI gate rejects synthetic/replay mixing | P0 |

---

## B. GitHub Actions Fixes

| # | Todo | Workflow | Acceptance Test | Priority |
|---|---|---|---|---|
| GA-1 | Fix `audit-hourly-update.yml` — ensure it produces `after_cost_net_per_trade` non-null (uses fixed `dashboard_generator.py`) | `audit-hourly-update.yml` | Hourly run populates after-cost field for ≥95% of rows | P0 |
| # | Fix `daily-price-refresh.yml` — `fetch_prices.php` returns HTTP 404 since 2026-04-29; yfinance replacement also failing | `daily-price-refresh.yml` / `daily-prices-yf-refresh.yml` | Both workflows green; price freshness <48h for all active symbols | P0 |
| GA-3 | Fix `db-freshness-guardian.yml` — `at_signal_outcomes` RED (~80 days stale), n_resolved_today=0 | `db-freshness-guardian.yml` | `at_signal_outcomes` GREEN (<360 min stale) | P0 |
| GA-4 | Fix `CI Tests` — currently failing | `ci-tests.yml` | CI green on main | P0 |
| GA-5 | Add per-class cost gate as CI gate (G1-G7 from finpredict-v2 framework) | `ci-tests.yml` + `audit-dashboard.yml` | Gate fails hard on quote honesty, metric liveness, dedup/identity | P0 |
| GA-6 | Add multiple-testing correction as CI gate (Benjamini-Hochberg + Bonferroni across strategy family) | `ci-tests.yml` | Gate rejects strategies with FDR q > 0.10 | P1 |
| GA-7 | Add PBO/SPA gate as CI gate (requires ≥2 strategies with n≥20, ≥5 for PBO power) | `ci-tests.yml` | Gate enforces PBO ≤0.10, SPA p ≤0.10 | P1 |
| GA-8 | Fix `audit-drift-telemetry.yml` — monitor for drift between `money_ready_verdict` and `pf_registry` cohorts | `audit-drift-telemetry.yml` | Alert on cohort divergence >5% | P1 |
| GA-9 | Disable/fix 30 failing workflows; 11 cancelled; 20 never-run | All | 0 failure/cancelled in critical path; never-run workflows either scheduled or removed | P1 |
| GA-10 | Add stale-workflow audit as CI gate | `gha-stale-workflows-audit.yml` | No active workflow with >30 days since last successful run | P1 |

---

## C. Asset-Class-Specific Fixes

### C-1. CRYPTO (Official: n=3,705, WR 35.87%, PF 0.920 — NOT_READY)

| # | Todo | Acceptance Test |
|---|---|---|
| C-1 | Reconcile ledgers: official intrabar (n=3,705) vs policy-clean registry (n=22,055, WR 42.09%, PF 0.258) | Published row counts + inclusion rules |
| C-2 | Remove re-emission duplicates; test delisted/survivorship-safe universe | Dedup hash coverage ≥95% |
| C-3 | Include taker fees, funding, quote freshness, capital constraints in backtest | Cost-adjusted PF < 1.0 correctly flags |
| C-4 | Test daily 50/200-day time-series trend, long/flat, volatility-targeted on frozen liquid universe | Benchmark-relative net expectancy CI excludes zero |
| C-5 | Compare against equal-weight buy-and-hold and cash in bull and bear windows | Excess-of-benchmark Sharpe > 0 |
| C-6 | **Do not use rejected VWAP or mega_mutation claims as proof** | VWAP/mega_mutation excluded from candidate set |

### C-2. EQUITY/STOCKS (Official: n=250, WR 59.20%, PF 0.939 — NOT_READY; WR >50% but PF <1.0)

| # | Todo | Acceptance Test |
|---|---|---|
| C-7 | Reconcile class names and entry/exit ledger | Class labels canonical |
| C-8 | Include delisted names, dividends, split adjustments, turnover costs | Survivorship-safe universe |
| C-9 | Monthly sector-neutral quality/value/momentum ranking on fixed large-liquid universe | Benchmark: SPY/sector + risk-matched passive |
| C-10 | Do NOT attribute deepAI Variant C results to Faber TAA (different rule, different window) | Hypothesis records separate rules |
| C-11 | Use mutual fund top-10 holdings (`fund_holdings_deriver.py`) as equity screen universe | Derivation pipeline runs without error |

### C-3. ETF (Official: n=45, WR 2.22%, PF 0.022 — INSUFFICIENT_DATA; registry n=19, WR 68.42%, PF 1.788 — cohort mismatch blocker)

| # | Todo | Acceptance Test |
|---|---|---|
| C-12 | Explain ETF/BOND cohort mismatch (registry PF 1.788 vs official PF 0.022) | Root cause documented |
| C-13 | Correct ETF/BOND taxonomy; include distributions, expense ratios, spreads, leveraged-product decay | Taxonomy unit test passes |
| C-14 | Monthly tactical allocation across unleveraged, liquid equity/rates/commodity ETFs | Benchmark: risk-matched static allocation |
| C-15 | Compare to static allocation benchmark, not only zero | Excess-of-benchmark net expectancy > 0 |

### C-4. FOREX (Official: n=612, WR 32.19%, PF 0.660 — NOT_READY; raw 14-day: 11/148, PF 0.087)

| # | Todo | Acceptance Test |
|---|---|---|
| C-15 | Timestamp/quote integrity; normalize pair direction | Pair direction canonical |
| C-16 | Acquire historical policy-rate/forward-point and swap data | Rate data coverage ≥95% |
| C-17 | Include spread, rollover, crisis gaps in cost model | Cost model covers all three |
| C-18 | Test diversified G10 carry basket with slow trend/risk-off overlay | Benchmark: passive carry basket |
| C-19 | Do NOT infer edge from one-pair Sharpe | Multi-pair test required |

### C-5. COMMODITY (Official: n=229, WR 40.17%, PF 1.026 — WATCH; registry n=14, WR 14.29%, PF 0.172)

| # | Todo | Acceptance Test |
|---|---|---|
| C-20 | Reconcile labels and ledgers; use real listed contracts, point-in-time contract chains | Contract identity test passes |
| C-21 | Back-adjustment and explicit roll cost | Roll cost modeled |
| C-22 | Cross-market time-series trend + separate term-structure carry test | Two distinct hypotheses tested |
| C-23 | Keep blocked if current signals use crypto proxies | Proxy gate enforced |

### C-6. FUTURES (Official: n=52, WR 42.31%, PF 1.094 — INSUFFICIENT_DATA; registry n=13, WR 30.77%, PF 1.009)

| # | Todo | Acceptance Test |
|---|---|---|
| C-23 | Real feed, contract/expiry identity, continuous-series construction | Contract chain integrity test |
| C-24 | Roll schedule, margin and liquidity-aware sizing | Roll model documented |
| C-25 | CTA-style diversified time-series trend across declared futures universe | Benchmark: same-market buy-and-hold + cash |
| C-26 | Keep blocked if using proxy prices | Proxy gate enforced |

### C-7. BOND (Official: n=1; intrabar subfield n=26, WR 7.69%, PF 0.392 — INSUFFICIENT_DATA)

| # | Todo | Acceptance Test |
|---|---|---|
| C-27 | Separate cash bonds from bond ETFs | Taxonomy split |
| C-28 | Acquire yield, duration, coupon/distribution, reliable mark data | Data coverage ≥95% |
| C-29 | Duration-managed trend/carry using Treasury yield-curve and total-return data | Benchmark: duration-matched |
| C-30 | Keep `INSUFFICIENT_DATA` until then | Gate enforced |

### C-8. MUTUAL_FUND (NOT_BUILT — no live class, no clean realized cohort)

| # | Todo | Acceptance Test |
|---|---|---|
| C-31 | Add MUTUAL_FUND class to `alpha_engine/asset_class.py` + `ml_gatekeeper ASSET_CLASS_MAP` | Class recognized in pipeline |
| C-32 | Do NOT add stub scanner to create fake coverage | No fake picks emitted |
| C-33 | Monthly NAV tactical allocation research only; no intraday pick signal | Signal frequency = monthly |
| C-34 | Build universe, NAV history, fees, separate benchmark | Universe ≥30 funds, NAV history ≥5y |
| C-35 | **Focus on low-fee subset**: sub-$50M AUM, sub-0.20% ER index funds, $0 min initial (see Focus Decision §I) | Low-fee filter produces ≥5 candidates |
| C-36 | Hard gates from `mutual_fund_ranker.py`: ER ≤0.50% index / ≤0.75% active, no load/12b-1/redemption fee, AUM ≥$100M, age ≥5y, min initial ≤$3,000 | Ranker enforces all gates |

### C-9. MEME/PENNY_STOCK (n=10/n=1, insufficient — blocked)

| # | Todo | Acceptance Test |
|---|---|---|
| C-37 | Maintain no-size/blocked status | Blocked gate enforced |
| C-38 | Require price integrity, liquidity, sample size, pre-registered thesis before any search | Pre-registration required |

---

## D. Backtesting / Simulation Fixes (per proposed algorithm)

| # | Algorithm Fix | Asset Class | Acceptance Test | Priority |
|---|---|---|---|---|
| D-1 | Fix horizon harness: enforce `MIN_WINDOWS=4`, implement multiple-testing adjustment (Benjamini-Hochberg + Bonferroni), fixed 60-day calendar intervals (not gap-based), net PnL for execution costs, require valid `resolution_method` | All | Harness enforces all checks; 0 false passes on known-bad data | P0 |
| D-2 | Fix gap-fill pricing in `universal_pick_resolver.py` (already done today — verify CI coverage) | All | CI test covers gap-down SL understatement + gap-up TP overstatement | P0 |
| D-3 | Fix per-class cost gate integration in `hc_gates_python.py` (already done today — verify ETF/COMMODITY blocked) | ETF, COMMODITY | Gate blocks picks when class avg PnL < 3x cost | P0 |
| D-4 | Fix after-cost net per-trade fallback in `dashboard_generator.py` (already done today — verify non-null) | All | `after_cost_net_per_trade` non-null ≥95% | P0 |
| D-5 | Add SubQ comparison: run each candidate strategy through SubQ for coverage/comparison before recommendation | All | SubQ report exists for each candidate | P0 |
| D-6 | Add walk-forward with purged/embargoed windows; compare excess return vs risk-matched benchmark | All | WF windows purged/embargoed; benchmark-relative test | P1 |
| D-7 | Add block-bootstrap confidence interval on net expectancy | All | CI excludes zero for any "passing" candidate | P1 |
| D-8 | Add DSR calculation with cumulative trial count (not just within-run) | All | DSR ≥0.95 required for pass | P1 |
| D-9 | Add PBO calculation (requires ≥2 strategies n≥20, ≥5 for power) | All | PBO ≤0.10 required for pass | P1 |
| D-10 | Add SPA test (White's Reality Check / Hansen SPA) | All | SPA p ≤0.10 required for pass | P1 |

---

## E. Evidence & Documentation

| # | Todo | Acceptance Test |
|---|---|---|
| E-1 | Publish `final_v3/quant-audit-2026-11-14/09_evidence/EVIDENCE_INDEX.md` with all data sources, timestamps, validation limits | Evidence index complete |
| E-2 | Label all peer-reported backtest metrics as claims, not live results | All peer metrics labeled |
| E-3 | Keep denominators separate across `money_ready_verdict`, `pf_registry`, `recent_closed`, `at_raw_picks` | No cross-cohort merging without reconciliation |

---
