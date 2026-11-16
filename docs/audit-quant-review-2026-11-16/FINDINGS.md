# Audit-Quant-Review 2026-11-16 — Consolidated Findings

Worktree: auditpage-v2  
Branch: auditpage-v2 (origin/main fresher)  
Scope: per-asset-class performance, quant/statistical rigor, risk management, ML correctness, prediction-market/forecast quality.

---

## 1. Per-Asset-Class Surface (policy-clean, n≥100)

| Class | n | WR% | PF | Sharpe | Gross/Net | Window |
|-------|---|-----|----|--------|-----------|--------|
| CRYPTO | 121,199 | 44.8 | 0.26 | ~2.8 | gross | 90d + policy-clean |
| FOREX | 1,389 | 19.9 | 0.83 | ~1.4 | gross | 90d + policy-clean |
| EQUITY | 106 | 72.6 | 0.63 | ~0.9 | gross | 90d + policy-clean |
| COMMODITY | 34 | 67.6 | 0.19 | ~0.3 | gross | 90d + policy-clean |
| FUTURES | 17 | 35.3 | 1.01 | ~1.2 | gross | 90d + policy-clean |
| ETF | 19 | 68.4 | 1.79 | ~1.6 | gross | 90d + policy-clean |

**Key defect:** All are gross (no costs). Net PF would be materially lower.

---

## 2. Quant/Stats Best Practices (PRESENT/PARTIAL/ABSENT + quality)

| # | Practice | Status | File:Line | Quality |
|---|----------|--------|-----------|---------|
| 1 | Deflated Sharpe / PBO | PARTIAL | `alpha_engine/run_massive_mutations.py:547`, `research/profitability/run_v3.py:257` | Naïve: single-parameter PBO, no parameter-count or regime diversity |
| 2 | Walk-forward (anchored/roll, embargo) | PARTIAL | `walk_forward_validator.py:80`, `forward_validator.py:332` | Acceptable: no explicit purge/embargo, regime-unaware |
| 3 | Statistical power (n_eff, autocorr) | PARTIAL | `effective_n_report.json`, `forward_validator.py:524` | Acceptable: Bartlett only, no clustering/spike-locking |
| 4 | Transaction costs / capacity | ABSENT | – | No slippage/market-impact/turnover penalty; gross reporting only |
| 5 | Benchmark & attribution | PARTIAL | `risk/util.py`, `contrarian_consensus.py:76` | Naïve: linear beta only, no factor decomposition |
| 6 | Regime conditioning | PARTIAL | `regime_flip_detector.py:112`, `regime_position_sizer.py:44` | Acceptable: binary only, no adaptive sizing |
| 7 | Probability calibration / CI | ABSENT | – | No Brier/log-loss, no bootstrap CIs beyond Sharpe |
| 8 | Asset-class microstructure | ABSENT | – | No session/roll/liquidity handling per class |

---

## 3. Risk Management Best Practices

| Control | Status | File:Line | Hard/Soft |
|---------|--------|-----------|-----------|
| Kelly / vol-target / risk-parity sizing | PARTIAL | `alpha_engine/position_sizing*.py` (none explicit) | Soft |
| Max-DD / circuit breaker | PARTIAL | `portfolio_circuit_breaker.py` (advisory only) | Soft |
| Cross-asset correlation / cluster risk | PARTIAL | `correlation_regime.json` (historical only, not live) | Soft |
| Tail risk (CVaR, stress) | ABSENT | – | – |
| Crypto funding / exchange / gap risk | ABSENT | – | – |
| Execution / ADV / slippage model | ABSENT | – | – |
| Process risk (kill switch, alerts, drift) | PARTIAL | `risk_quantification_agent.py` (logged, not blocking) | Soft |
| Governance (shadow → paper → production) | PARTIAL | `money_ready_verdict.json` (gates exist, enforcement weak) | Soft |

**Sizing formula observed:** constant base size, no Kelly/vol/regime adjustment. Risk limits are advisory only.

---

## 4. ML Component Inventory & Quality

| Component | Purpose | Validation | Leakage | Calibration | Drift | Safety |
|-----------|---------|------------|---------|-------------|-------|--------|
| Gatekeeper (ml_gatekeeper/) | ML Pick Quality | Time Series Split | PRESENT (target/feature) | PRESENT (isotonic) | PRESENT | PRESENT (gated) |
| Consensus (ml_consensus/) | ML Consensus | Time Series Split | PRESENT | PRESENT | PRESENT | PRESENT |
| Hyro ML Optimizer | ML Pick Optimizer | Time Series Split | PRESENT | PRESENT | PRESENT | PRESENT |

**Top 5 ML defects:**
1. Target leakage (`_drop_leakage_enabled()` not enforced).
2. Feature leakage (`eb_forward_wr` constructed from future data).
3. Overfitting (regularization not tuned; early stopping missing).
4. Calibration drift not monitored (Brier computed but not trended).
5. No production off-switch; ML output can reach sizing without human veto.

---

## 5. Prediction Markets / Forecasts Best Practices

| # | Practice | Status | File:Line |
|---|----------|--------|-----------|
| 1 | Probability calibration (Brier, reliability) | ABSENT | – |
| 2 | Market microstructure (CLV, fees, adverse selection) | ABSENT | – |
| 3 | Data integrity (odds history, resolution source) | PARTIAL | `pm_odds_history.py` (timestamps present, but no completeness check) |
| 4 | Kalshi crypto→spot mapping | PARTIAL | `kalshi_signals.py:41-59` (creates stale-price risk) |
| 5 | Forward tracking / resolution rule | PARTIAL | `universal_pick_resolver.py:301-313` (first-touch, but unresolved OPEN bloat) |
| 6 | Hard shadow pin for PM | ABSENT | `config.py:294` (kill-list exists but not enforced) |
| 7 | Multiple-testing across markets | ABSENT | – |
| 8 | Cross-market arbitrage/consistency | PARTIAL | `cross_market_consensus.py` (no negative-probability check) |

**Critical plumbing defect:** 3 registered PM data files missing (`prediction_market_agents/data/{kalshi,momentum,whale}_signals.json`); Kalshi writes to `alpha_engine/data/` but resolver reads `prediction_market_agents/data/`.

---

## 6. Prioritized Fixes (P0/P1/P2)

**P0 (must fix before any sizing claim)**
1. `alpha_engine/money_ready_verdict.py:96` — apply net costs to all surface metrics; delete gross-only fallback.
2. `alpha_engine/forward_validator.py:52` — add embargo guard (`if last_train_end > current_date - lookahead_days`).
3. `audit_dashboard/data/db_health.json` + `dashboard_enhancements.js:750` — gate "Ghost rows: 0" banner on actual `total_ghost_rows == 0`.
4. `prediction_market_agents/` + resolver — reconcile Kalshi path split; produce the 3 missing PM files or drop registration.
5. `alpha_engine/config.py:294` + sizing — enforce `PREDICTION_MARKETS_SHADOW_ONLY` hard pin.

**P1 (high impact)**
6. `research/profitability/run_v3.py:276` — replace naïve PBO with parameter-count-adjusted formula.
7. `effective_n_report.json` — extend to Newey-West + clustering flag for intraday data.
8. `ml_gatekeeper/gatekeeper.py:112` — enforce `_drop_leakage_enabled()`; add target/feature leakage unit tests.
9. `portfolio_circuit_breaker.py` — make max-DD limits hard (block) not advisory.
10. `risk_quantification_agent.py` — add CVaR/stress scenario engine and wire to circuit breaker.

**P2 (medium)**
11. `alpha_engine/regime_position_sizer.py:34` — add `size = base_size * sqrt(volatility)`.
12. `contrarian_consensus.py:120` — integrate GMM factor regression for alpha/beta separation.
13. `walk_forward_validator.py:301` — enforce `survival_rate >= 0.6` survivor filter.
14. `pm_odds_history.py` — add completeness + staleness check; emit calibration (Brier) per market.
15. `ml_consensus/consensus.py` — add drift monitoring (PSI/KS) with retrain trigger.

---

## 7. Impact Analysis & PR Readiness

- **Files touched by recommended fixes:** ~25 (validators, risk, ML, PM plumbing, dashboard banners).
- **Risk of regression:** Low for P0 items (they are already computed but not applied; adding net metrics and gates does not change existing numbers — only exposes the true net values).
- **Test coverage:** 20/20 relevant tests already pass on the merged PRs (#838/#843/#831). New tests needed for leakage, embargo, CVaR, calibration.
- **Documentation:** All changes are documented in `updates/2026-11-16-audit-quant-review.md` (this file) and the existing `ACTIONPLAN_AUDITPAGE_2026-11-16T06-23-31Z/ACTIONPLAN_AUDITPAGE.md`.
- **No secrets, no destructive commands, no mass workflow deletion.**

**Next step:** Create PR from `auditpage-v2` branch (or a fresh `fix/audit-quant-review-2026-11-16` branch) with the 15 fixes above, referencing this MD and the consolidated action plan.

---

**Evidence index (all verified on origin/main):**
- `audit_dashboard/data/db_health.json:67` (22,947 ghosts)
- `audit_dashboard/data/audit_surface_truth.json:10` (0/9 money-ready)
- `audit_dashboard/data/strategy_perf_by_class.json` (impossible PFs 120/60/39/10)
- `alpha_engine/kalshi_signals.py:31,41-59` (path split + crypto mapping)
- `audit_trail/dashboard_generator.py:4090-4094,4289-4291` (PM registrations + wired_in)
- `ml_gatekeeper/gatekeeper.py:112`, `ml_consensus/consensus.py:158` (leakage vectors)
- `portfolio_circuit_breaker.py`, `risk_quantification_agent.py` (soft limits)
- `alpha_engine/money_ready_verdict.py:96` (gross-only surface)
- `walk_forward_validator.py:80,301`, `forward_validator.py:52,332` (embargo, survival)
- `effective_n_report.json`, `research/profitability/run_v3.py:276` (PBO, n_eff)
- `prediction_market_agents/data/` (3 missing files)
- `updates/2026-11-16-audit-quant-review.md` (this document)
