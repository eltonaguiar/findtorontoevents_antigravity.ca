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

**Key defects:**
- All are gross (no costs). Net PF would be materially lower.
- `strategy_perf_by_class.json` contains a **PF=999 / ∞ zero-loss sentinel** (356 cells with PF≥999 and zero losses); `pf_ok=true` on CHEAP_STOCKS is the same sentinel, not a pass. Do not quote sleeve PFs (e.g. ADX 60, equity RSI-reversal 57) as class edge.
- Some class `wr_ok` flags use a **40% floor**, not the 50% money-ready bar — a green WR flag is not a pass.
- `db_health.json` (12:48Z) records 22,947 ghost rows, **278 null resolved pnl**, and a **27% magnitude mismatch**; the live footer still said 5/5 because the checker is non-fatal (`|| echo`) and had not rerun.

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
| Fractional Kelly sizing | PRESENT | `alpha_engine/kelly_position_sizer.py:80-118` (quarter-Kelly, cap 25%) | Soft (env-flag gated) |
| Continuous Kelly | PRESENT | `kelly_position_sizer.py:121-149` (mu/sigma^2) | Unused in production path |
| Volatility targeting | PRESENT | `kelly_position_sizer.py:272-303`, `regime_position_sizer.py:324-348` | Soft (scaling) |
| Risk-parity / HRP | ABSENT | – | – |
| Max-DD / circuit breaker | PRESENT | `alpha_engine/portfolio_circuit_breaker.py:50-73` (YELLOW -10 / RED -20 / HALT -30); root `portfolio_circuit_breaker.py:207` calls flatten | Hard on new entries, **soft on existing** (`_flatten_all_positions` is a log-only stub, root `portfolio_circuit_breaker.py:209-213`) |
| Time-based stop / cooldown | PRESENT | `portfolio_circuit_breaker.py:60`, `circuit_breaker_aggregator.py:128` | Hard |
| Recovery rules | PRESENT | `drawdown_circuit_breaker.py:163-173` | Hard |
| Cross-asset correlation (live) | PARTIAL | `correlation_regime.json` (30d class-level only) | Advisory |
| Cluster / crowded-trade penalty | PARTIAL | `regime_position_sizer.py:372-408` | Advisory |
| Beta netting | ABSENT | – | – |
| CVaR / Expected Shortfall | PRESENT | `risk_quantification_agent.py:424-426`, `risk_management/portfolio_kelly_var.py:144-161` | Advisory (not enforced in hot path) |
| Stress tests / scenario analysis | PRESENT | `risk_adjusted_analysis.py:268-366` | Advisory |
| Skew / kurtosis / gap risk | PRESENT | `risk_adjusted_analysis.py:353-366` | Advisory |
| Liquidity / ADV impact | ABSENT | – | – |
| Gross/net exposure limits | PARTIAL | `risk_management/portfolio_kelly_var.py:22-23` (quarter-Kelly, 10% max/1% min, 2% VaR) | Advisory |
| Crypto funding / stablecoin / weekend gap | ABSENT | – | – |
| Slippage model | PRESENT | `risk_adjusted_analysis.py:53-54` (0.05% + 0.03%) | Advisory |
| Order sizing vs ADV | ABSENT | – | – |
| Kill switch (manual override) | PARTIAL | `RISK_FRAMEWORK.md:224-265` (spec only) | Not implemented |
| Alerts / incident postmortems | PARTIAL | `risk_quantification_agent.py:828-897` | Advisory |
| Model drift monitoring | PRESENT | `circuit_breaker_aggregator.py:234-250` (KS ratio) | Hard (T3/T4) |
| Governance (shadow → paper → production) | PRESENT | `paper_trading/strategy_promotion_pipeline.py`, `portfolio_manager.py:142-155` | Hard |
| NFA / compliance notes | PARTIAL | `RISK_FRAMEWORK.md:271-390` | Spec only |

**Sizing math verdict:** fractional Kelly, continuous Kelly, vol-target and portfolio-Kelly+VaR are **formulaically correct** (quarter-Kelly for safety; CORRECT `f*=(p*b-q)/b`; portfolio VaR clip [1%,10%]; regime multipliers BULL 1.75x / CHOP 0.5x). The gap is **enforcement and integration**, not formula errors.

**Top risk defects:**
1. **P0** — root `portfolio_circuit_breaker.py:209-213` `_flatten_all_positions()` only logs; breaker blocks new entries but leaves existing risk on when triggered.
2. **P1** — `alpha_engine/drawdown_circuit_breaker.py:245-252` returns FALSE when state is >2h old, silently allowing trading during an unresolved drawdown.
3. **P1** — no live per-pick correlation gate; `correlation_regime.json` is 30d class-level only.
4. **P2** — `risk_management/portfolio_kelly_var` computes but is not called in the hot path (`production_scanner.py:6007-6016` is observability-only).
5. **P2** — crypto funding-rate / stablecoin-depeg / weekend-gap guards absent (`kelly_position_sizer.py:39-64` only zeroes FOREX).

---

## 4. ML Component Inventory & Quality

| Component | Purpose | Validation | Leakage | Calibration | Drift | Safety |
|-----------|---------|------------|---------|-------------|-------|--------|
| Gatekeeper (ml_gatekeeper/) | ML Pick Quality | Time Series Split | **MASKED by default** (`gatekeeper.py:92-101` indices 5,6,19,30; applied `:195`) | PRESENT (isotonic) | PRESENT | PRESENT (gated) |
| Consensus (ml_consensus/) | ML Consensus | Time Series Split | **Review**: `consensus.py:134` uses `strat_fwd_wr`/`forward_wr` in the score | PRESENT | PRESENT | PRESENT |
| Hyro ML Optimizer | ML Pick Optimizer | Time Series Split | inherits gatekeeper masking | PRESENT | PRESENT | PRESENT |

**ML assessment (verified on origin/main):**
1. Target/feature leakage masking is **ON by default** (`ml_gatekeeper/gatekeeper.py:95` `_drop_leakage_enabled()`; `_LEAKAGE_FEATURE_INDICES=(5,6,19,30)` at `:92`; applied at `:195`). The opt-out is `ML_GATE_DROP_LEAKAGE=0`. This is a **strength**, not a defect.
2. **Residual review item:** `ml_consensus/consensus.py:134` builds the consensus score from `strat_fwd_wr`/`forward_wr` (forward-looking performance). Not a training-leak (it is an aggregation weight), but it means the score chases past forward WR — document or gate it.
3. **Calibration:** Brier/ECE computed in `alpha_engine/prediction_market_signals.py:1806` (research tracker) and `tools/brier_reliability_stub.py`; the live ML path should emit a reliability curve, not just a scalar. **Correction:** `alpha_engine/score_booster.py::_calibrate_confidence` is a **hardcoded score penalty, not a probability calibrator** (it does not rewrite `confidence`); the live "ML calibration" text is a static 2026-05-15 measurement; `ml_trading_enabled=false` (`alpha_engine/data/ml_health_status.json`) and the gainer model is ~175 days old (trained 2026-05-25). Treat live ML calibration as stale/research-only.
4. **Drift:** `ml_gatekeeper/models/drift_baseline.json` + `circuit_breaker_aggregator.py:234-250` KS ratio exist; retrain trigger wiring should be confirmed end-to-end.
5. **Safety:** ML output is gated by `ml_gatekeeper` before sizing; no direct sizing path found.

---

## 5. Prediction Markets / Forecasts Best Practices

| # | Practice | Status | File:Line |
|---|----------|--------|-----------|
| 1 | Probability calibration (Brier/ECE) | PARTIAL | `alpha_engine/prediction_market_signals.py:1806` (SignalQualityTracker, research class); `tools/brier_reliability_stub.py:214` (stale 2026-04-06, Brier 0.293, skill -0.175, ECE 0.193 on 2,968 pairs); **no reliability curves or log-loss in live PM path** |
| 2 | Market microstructure (CLV, fees, depth, fill prob) | ABSENT | only virtual Kelly on `PM_BANKROLL=100` (`polymarket_btc_updown_agent.py:42,192`) |
| 3 | Data integrity | PARTIAL | `pm_odds_history.py:305` (dedup, timestamps, volume); no cancelled/null-market flagging, no timezone canonicalization |
| 4 | Signal construction | PARTIAL | `kalshi_signal_agent.py:53` (KXBTC→BTCUSDT), `pm_lead_lag_analyzer.py:208` (LEADING); **no documented look-ahead/stale guard** for Kalshi→spot mapping |
| 5 | Risk sizing | PARTIAL | `pm_macro_overlay.py:309` forward_test_only=True, `btc_updown` DRY_RUN=true; **no hard pin in consensus merge** (`orchestrator.py:392`, `prediction_market_agents/orchestrator.py:48` MIN_MERGE_CONFIDENCE). `isVerifiedAlphaPick`/`_is_verified_alpha_pick` still returned true for Polymarket/Kalshi/`copy_pm_` sources on main (display fix pending deploy). |
| 6 | Forward tracking / resolution rule | PRESENT | `universal_pick_resolver.py:666` (intrabar first-touch, SL-wins-ties, `MAX_HOLD_HOURS_BY_CLASS`, TIME_EXIT fallback) |
| 7 | Multiple testing | PARTIAL | `forward_validator.py:333` (White's Reality Check + DSR); no family-wise/FDR in PM cross-market |
| 8 | Arbitrage / consistency | PARTIAL | `cross_market_consensus.py:229`, `pm_macro_overlay.py:334` (>=70% gate); **no negative-probability / impossible-odds guard** |

**PM top defects:**
1. **P0** — `SignalQualityTracker.record_resolution` exists but is never called from the resolver/orchestrator, so Brier/ECE are never computed on live resolved PM picks; the only stub is stale and shows negative skill.
2. **P0** — no hard shadow/paper pin at the consensus merge (`orchestrator.py:392`).
3. **P1** — Kalshi crypto→spot mapping lacks a timestamp-alignment / look-ahead guard (`kalshi_signal_agent.py:424`).
4. **P1** — no closing-line benchmark or CLOB depth snapshot (`pm_odds_history.py:337`, lead-lag `:179`).
5. **P2** — no negative-probability / impossible-odds guard (`cross_market_consensus.py:229`).

---

## 6. Prioritized Fixes (P0/P1/P2)

**P0 (must fix before any sizing claim)**
1. `alpha_engine/money_ready_verdict.py:676-690` — net slippage deduction exists but **fails open to gross** when the import is unavailable (`:683-690`); make net mandatory for all surface metrics and remove the gross fallback.
2. `walk_forward_validator.py:134-165` (`create_windows`, `train_end` at `:165`) — no purge/embargo between train and test windows; add an embargo gap.
3. root `portfolio_circuit_breaker.py:209-213` — implement real `_flatten_all_positions()` (close positions, cancel orders); breaker currently leaves existing risk on.
4. `audit_dashboard/data/db_health.json` + `dashboard_enhancements.js:750` — gate "Ghost rows: 0" banner on actual `total_ghost_rows == 0`.
5. `prediction_market_agents/orchestrator.py:392` + `prediction_market_consensus.py:670` — hard `PREDICTION_MARKETS_SHADOW_ONLY` / forward_test_only pin at the merge; wire `SignalQualityTracker.record_resolution` into `universal_pick_resolver.py:666,1403`.
6. `prediction_market_agents/` + resolver — reconcile Kalshi path split; produce the 3 missing PM files or drop registration.

**P1 (high impact)**
7. `alpha_engine/drawdown_circuit_breaker.py:245-252` — stale (>2h) state must recompute, not return FALSE.
8. `research/profitability/run_v3.py:276` — replace naïve PBO with parameter-count-adjusted formula.
9. `effective_n_report.json` — extend to Newey-West + clustering flag for intraday data.
10. `ml_consensus/consensus.py:134` — `strat_fwd_wr`/`forward_wr` weighting is forward-looking; document or gate. Add a leakage unit test locking `ml_gatekeeper/gatekeeper.py:92-101,195` masking.
11. `kalshi_signal_agent.py:424` — timestamp-alignment / look-ahead guard before emitting spot-mapped signals.
12. `production_scanner.py:5937-5940` — wire `PortfolioKellyVaR.size_position()` into the hot path.

**P2 (medium)**
13. `alpha_engine/regime_position_sizer.py:34` — add `size = base_size * sqrt(volatility)`.
14. `contrarian_consensus.py:120` — integrate GMM factor regression for alpha/beta separation.
15. `walk_forward_validator.py:301` — enforce `survival_rate >= 0.6` survivor filter.
16. `pm_odds_history.py:337` + lead-lag `:179` — completeness/staleness check, closing-line benchmark, CLOB depth snapshot, per-market Brier.
17. `ml_consensus/consensus.py` — add drift monitoring (PSI/KS) with retrain trigger.
18. `cross_market_consensus.py:229` — negative-probability / impossible-odds guard + cross-market arbitrage check.
19. `real_money_tracker.py:229-239` — per-pick live correlation gate (reject |r|>0.7).
20. `kelly_position_sizer.py:352-400` — crypto funding-rate cap, stablecoin whitelist, weekend-gap size reduction.

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

---

## 10. Peer feedback incorporated (auditpage-v4, 2026-11-16T17:34Z)

Source: `ACTIONPLAN_AUDITPAGE/2026-11-16T1734Z_auditpage-v4/FINDINGS.md` on origin/main. Items merged into this report:

1. **Live page lags main.** PR #843 (audit truth layer) is merged on main (`9842be43e98`) but not yet deployed; live `/audit/` still shows the old "5/5 checks pass" and pre-#843 wording. Do not treat live as post-#843 until the next `audit-dashboard.yml` deploy.
2. **PF 999 / ∞ sentinel.** 356 cells in `strategy_perf_by_class.json` have PF≥999 with zero losses; `pf_ok=true` on CHEAP_STOCKS is the same sentinel. Not a pass.
3. **WR floor mismatch.** Some `wr_ok` flags use 40%, not the 50% money-ready bar.
4. **Walk-forward Sharpe outlier.** BOND `oos_sharpe = -65.632` (`alpha_engine/data/walkforward_results.json::by_class.BOND.oos_sharpe`); peer display fix renders `|Sharpe|>5` as `n/a`.
5. **ML calibration is not a calibrator.** `score_booster._calibrate_confidence` is a hardcoded penalty; live ML Health is ~175 days stale; `ml_trading_enabled=false`.
6. **Verified-Alpha badge leakage.** `isVerifiedAlphaPick` / `_is_verified_alpha_pick` returned true for Polymarket/Kalshi/`copy_pm_` sources on main.
7. **Gate quality.** DSR is not ≥0.95 on any class; `wf_oos_ok` can pass when both IS and OOS PF < 1; the ghost-row workflow step is non-fatal (`|| echo`), so a red ghost tier does not stop deploy.
8. **Ledger hygiene.** `db_health.json` records 278 null resolved pnl and a 27% magnitude mismatch alongside the 22,947 ghosts.

## 11. Review checklist for the final plan agent

- [ ] Net-of-cost metrics mandatory (`money_ready_verdict.py:676-690` fail-open removed).
- [ ] Walk-forward embargo (`walk_forward_validator.py:134-165`).
- [ ] Circuit-breaker flatten implemented (root `portfolio_circuit_breaker.py:209-213`).
- [ ] Stale drawdown state recomputes (`drawdown_circuit_breaker.py:245-252`).
- [ ] Ghost-row checker made fatal; `db_health.json` regenerated.
- [ ] PM shadow pin hard-enforced at merge; `record_resolution` wired.
- [ ] PF 999 / ∞ sentinel removed from cards and gates.
- [ ] ML calibration rebuilt as a real probability calibrator; stale 2026-05-15 text removed.
- [ ] Verified-Alpha badge excludes PM/Kalshi/copy_pm.
- [ ] DSR/WFE gates enforced, not displayed.
