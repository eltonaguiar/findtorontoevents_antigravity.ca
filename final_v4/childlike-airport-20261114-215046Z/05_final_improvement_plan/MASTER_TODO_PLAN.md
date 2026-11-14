# 05 — Final Improvement Plan (Master TODOs)

**Principle:** integrity → reproduce (net, benchmark-relative, statistically controlled) → paper → gated live.

## 1. General Fixes
- [ ] **G-01 (P0)** Canonical PnL recompute/reconcile (units, sign/calc, reject null/zero entry, remove `%*100`).
- [ ] **G-02 (P0)** Pricing/realism & marks (remove hardcoded prices; restore feeds; gap-aware conservative fills).
- [ ] **G-03 (P0)** Lifecycle/provenance (resolve zombies/EXPIRED bias, terminal states, `resolution_method`/lineage).
- [ ] **G-04 (P0)** Unify sources & sync (bond/ETF/JSON↔DB), de-dup, freshness SLA.
- [ ] **G-05 (P0)** Cross-ledger reconciliation with canonical cohorts & published diffs.
- [ ] **G-06 (P0)** Per-asset-class cost model (fees/spread/slippage/funding/roll/borrow), gross & net.
- [ ] **G-07 (P1)** Regime coverage; leakage-safe labels/features (embargo/purge).
- [ ] **G-08 (P1)** Multiple-testing/stats (CSCV/PBO, DSR effective-N, BH/Bonferroni, fixed windows, MIN_WINDOWS).
- [ ] **G-09 (P1)** Benchmark-relative & carry-vs-alpha reporting.
- [ ] **G-10 (P1)** Risk/concentration controls (vol target/caps, kill-switches, source gates).
- [ ] **G-11 (P1)** Observability & reproducibility (drift/staleness/fill parity, configs/seeds/hashes).
- [ ] **G-12 (P2)** Wire `MUTUAL_FUND` class + validated allocation plumbing.

## 2. GitHub Actions / CI Fixes
- [ ] **CI-01 (P0)** Triage/fix failing workflows (perms/secrets/timeouts/deps/paths).
- [ ] **CI-02 (P0)** Fix mass cancellations (concurrency/cancel-in-progress, split jobs, timeouts).
- [ ] **CI-03 (P0)** Freshness & integrity gates (TTL fail-build, audit-trail/schema/unit checks).
- [ ] **CI-04 (P1)** Harness validation gates (seeded smoke, PnL/sync/resolver tests, PBO/DSR checks).
- [ ] **CI-05 (P1)** Deterministic envs & artifact integrity before deploy.
- [ ] **CI-06 (P1)** Loop/trigger safety (`[skip ci]`, no broad generator globs) + alerting.
- [ ] **CI-07 (P1)** API/secret/rate-limit hygiene (backoff/retry, quotas).

## 3. Asset-Class-Specific
| Class | TODOs | Gate |
|---|---|---|
| **Crypto** | CR-01 VWAP-MR core (BTC,ETH,SOL,XRP,ADA); CR-02 >730d reval (PBO<0.3); CR-03 Vol-Targeted TSMOM; CR-04 reproduce mega_mutation; CR-05 MR+trend ensemble; fix fill realism | Net OOS+benchmark, PBO/DSR/MDD/n, paper |
| **Stocks/ETFs** | EQ-01 reproduce Variant C net; EQ-02 Faber TAA/QVM; ET-01 sync; ET-02 low-fee costed universe | Net risk-adjusted OOS vs benchmark |
| **Mutual Funds** | MF-01 wire `MUTUAL_FUND`; MF-02 validated allocation (ranker/holdings); MF-03 $0-min/no-load/ER≤0.20% subset; MF-04 next-NAV/constraints; MF-05 NAV walk-forward | Net-of-fee OOS+paper |
| **Bonds** | BD-01 sync; BD-02 Vol-Targeted Bond Trend (rate/regime, carry/costs) | Robust across regimes |
| **Forex** | FX-01 net-of-spread/roll momentum; FX-02 `fx_kill_switch`; FX-03 contamination/timestamps/allowlist | Survives costs, capped MDD |
| **Commodities/Futures** | CM-01 fix 98.4% zero-PnL/marks/roll (blocker); CM-02 diversified trend; CM-03 vol/regime | Correct marks + net diversified OOS |

## 4. Backtest/Simulation per Proposed Fix
| Fix/Algo | Simulation | Acceptance |
|---|---|---|
| PnL/unit/sync (G-01/02/04) | Deterministic recompute & reconciliation | 0 sign/calc mismatches; tests pass |
| Gap-aware/fill realism (B06) | Gap/intrabar replay naive vs conservative | No better-than-gap; consistent labels |
| Per-class cost gate | With/without counterfactual | Suppresses negative-expectancy classes |
| VWAP-MR core (CR-01/02) | >730d 4h walk-forward, core-only, cost stress 20/30/50bps, CSCV/PBO | PF≥1.2–1.5, Sharpe≥1.0, MDD<15–20%, **PBO<0.3**, DSR>0.95, stable |
| Vol-Targeted TSMOM (CR-03) | 7y+ diversified, bear/subperiods, funding/costs, bootstrap CI, benchmark | Robust net edge, CI>0, controlled MDD |
| MR+TSMOM ensemble (CR-05) | Risk-balanced/regime blend OOS | Better risk-adjusted than components |
| mega_mutation (CR-04) | Independent reimpl, path-verified TP/SL, full costs | Persists OOS net-of-cost else reject |
| Variant C (EQ-01) | Raw walk-forward, net costs, expanded universe | Gates met, stable |
| Faber TAA/QVM (EQ-02/ET) | Long-history costed vs risk-matched benchmark | Net outperformance, controlled MDD |
| MF low-fee allocation (MF-02..05) | NAV walk-forward, next-NAV, ER/constraints, overlay vs buy-hold | Net-of-fee acceptable MDD; overlay justified |
| Bond trend (BD-02) | Rate-regime stress | Robust across regimes |
| FX momentum (FX-01/02) | Spread/roll-inclusive + kill-switch | Survives costs, capped MDD |
| Commodity trend post-fix (CM-01..03) | Roll/margin-aware on corrected series | Net positive, reconciles to marks |
| Harness/stats fixes (G-08, CI-04) | Fixed windows, MIN_WINDOWS, BH/Bonferroni, DSR effective-N, PBO checks | No false-positive pass; reproducible |

## Milestones
**M1** P0+CI green+reconciliation → **M2** ≥1 crypto + ≥1 non-crypto/MF pass strict OOS sim → **M3** paper forward → **M4** gated live (capped risk, kill-switches).
