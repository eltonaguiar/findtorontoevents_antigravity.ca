# Audit Quant Review — Remaining Items (prioritized)

Consolidated from `docs/audit-quant-review-2026-11-16/FINDINGS.md` after rounds 1-4
(#853, #858, #863, #870). Items here are **not yet executed**.

## P0 — correctness / truthfulness

1. **`record_resolution` wiring (PM calibration).**
   `alpha_engine/prediction_market_signals.py::SignalQualityTracker.record_resolution`
   is never called, so Brier/ECE are never computed on live resolved PM picks.
   Blocker: the resolver carries picks, not markets — a market→pick mapping
   (`market_id`, `predicted_prob`, `actual_outcome`) must be designed first.

2. **Promotion gates are displayed, not enforced.**
   `money_ready_verdict` exposes `dsr_ok` / `wf_oos_ok` / `fdr_ok` as shadow
   fields. DSR is not ≥0.95 on any class and `wf_oos_ok` can still pass when
   in-sample PF < 1. Decide which gates are hard and wire them into the verdict.

3. **PF 999 / ∞ sentinel in gates.**
   #853 fixed the *display*; some gate paths still read the sentinel as a pass
   (`pf_ok=true` on CHEAP_STOCKS; 356 cells with PF≥999 and zero losses).

## P1 — statistical rigor

4. **Walk-forward embargo.** No purge gap between train and test windows
   (`walk_forward_validator.py::create_windows`, `alpha_engine/walk_forward_validator.py`).
5. **`PortfolioKellyVaR` hot-path wiring.** Computed in
   `risk_management/portfolio_kelly_var.py` but not called by
   `alpha_engine/production_scanner.py` before `save_active_picks`.
6. **PBO formula.** `research/profitability/run_v3.py` uses a single-parameter
   PBO; needs parameter-count / regime diversity / effective-trials adjustment.
7. **n_eff.** `effective_n_report.json` uses Bartlett with `L=floor(n^0.25)`;
   add Ljung-Box lag selection and an intraday clustering flag.

## P2 — risk / ML / PM hygiene

8. **Regime-aware sizing.** `alpha_engine/regime_position_sizer.py` is
   regime-blind; add `size = base * sqrt(volatility)`.
9. **Alpha/beta separation.** `alpha_engine/contrarian_consensus.py` uses a
   linear beta only; add a factor (GMM) decomposition.
10. **Survival filter.** Enforce `survival_rate >= 0.6` on walk-forward survivors.
11. **PM microstructure.** No closing-line value benchmark, CLOB depth, or fill
    probability (`pm_odds_history.py`, `pm_lead_lag_analyzer.py`).
12. **ML drift.** `ml_consensus` has no PSI/KS drift monitor with a retrain
    trigger; calibration is a hardcoded penalty, not a probability calibrator.
13. **Crypto-specific guards.** No funding-rate cap, stablecoin whitelist, or
    weekend-gap size reduction (`alpha_engine/kelly_position_sizer.py`).
14. **Verified-Alpha badge.** `isVerifiedAlphaPick` / `_is_verified_alpha_pick`
    still return true for Polymarket/Kalshi/`copy_pm_` sources on main.
15. **Walk-forward Sharpe outlier.** `|Sharpe| > 5` (e.g. BOND -65.6) should
    render `n/a`, not a number.

## Executed so far (for context)

- #853: drawdown stale-state fail-safe; PF sentinel display `n/a`; net-pnl fail-safe.
- #858: PM ingest rejection fixed; hard shadow pin in both merge paths.
- #863: impossible-probability guard; walk-forward OOS profitability gate.
- #870: circuit-breaker auto-flatten hook.
