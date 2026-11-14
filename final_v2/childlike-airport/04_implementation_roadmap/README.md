# 04 — Implementation Roadmap

**Date:** 2026-11-14 | **Principle:** remediate integrity → validate → paper → gated live. No aggregate profitability claims until fixed.

## Phase 0 — Preconditions (blockers)
- [ ] **PnL & data integrity fix** (see `05_data_quality_remediation`): correct `sync_all_picks_to_mysql.py` (null/zero entry, `pnl *= 100` heuristic), fix 98.4% futures/commodity zero-P/L, repair sign/calc mismatches, remove hardcoded `expected_2026_prices` in `price_realism_check.py`.
- [ ] **Source-of-truth unification:** sync `alpha_engine/data/active_picks_bond.json`, `active_picks_etf.json`, and other unsynced feeds; resolve 172d-stale `data/live_picks.db` snapshot; define canonical pick store.
- [ ] **Zombie/expiry hygiene:** resolve/close EXPIRED zombies (78.6% active_raw symptom), stop emitting unresolved zero-P/L rows.
- [ ] **Audit trail & ops:** populate `data/audit_trail.db` logging; stabilize 7 failing workflows and dashboard cancellations.
- [ ] **Regime coverage:** restore regime computation/attachment (currently ~0.25%) — required for VWAP gating and sizing.

## Phase 1 — Validate & Reproduce (no live risk)
- [ ] **Crypto VWAP-MR (core):** reproduce v11/v12 on **exchange data >730d** (Binance/OKX/Coinbase 4h) for BTC,ETH,SOL,XRP,ADA; target **PBO<0.3**, n↑; stress costs 20/30/50bps RT.
- [ ] **Crypto TSMOM:** implement ITERATION-005 spec (50d+200d SMA, 20% vol target, 0.1%/side, 10 crypto, 7.4y-equivalent history) and independently reproduce Sharpe/PF/MDD/CI.
- [ ] **Equity/ETF Variant C:** reproduce deepAI walk-forward (PF 1.26, n=237, p<0.0013) OOS; expand sample/universe.
- [ ] **mega_mutation_macd_rsi / ema_momentum:** independent OOS reproduction with leakage/cost checks.
- [ ] Apply `06_statistical_validation_framework` gates to every candidate; publish pass/fail.

## Phase 2 — Paper / Shadow Deployment
- [ ] Deploy **VWAP-MR core (BTC,ETH,SOL,XRP,ADA)** in shadow: regime-gated, 40% sizing cap, MR-compatible regimes only, real-time marks, cost tracking.
- [ ] Deploy **Vol-Targeted TSMOM** in shadow (diversified basket) with vol targeting and drawdown controls.
- [ ] Monitor: realized PF/Sharpe/MDD, slippage vs model, regime distribution, signal/fill parity, drift.
- [ ] Run for statistically meaningful window (predefined trade/time count) before promotion.

## Phase 3 — Asset-Class Build-Out (parallel, gated)
- [ ] **Stocks/ETFs:** implement & OOS-test **Faber TAA** and/or promote validated Variant C.
- [ ] **Bonds:** build **Vol-Targeted Bond Trend** (rate/regime aware); sync bond picks.
- [ ] **Mutual Funds:** add `MUTUAL_FUND` to `alpha_engine/asset_class.py` and `ml_gatekeeper/gatekeeper.py` ASSET_CLASS_MAP; wire `mutual_fund_ranker.py`; EOD/NAV execution model.
- [ ] **Forex:** implement **FX Momentum** + wire/enable `fx_kill_switch.py`; realistic spread/rollover.
- [ ] **Commodities:** fix futures zero-P/L/pricing; implement **Commodity Trend Following** with roll/margin modeling.

## Phase 4 — Controlled Live (only after gates)
- [ ] Promote strategies that clear strict gates (PF≥1.5 target, Sharpe≥1.0, MDD<20%, PBO<0.3, DSR>0.95, sufficient n) in paper.
- [ ] Start with capped risk (small capital, hard kill-switches, per-strategy and portfolio drawdown limits).
- [ ] Continuous audit: reconcile live PnL to marks, detect drift/regime breaks, auto-degrade on breach.

## Ownership / Sequencing Notes
- **Do first:** Phase 0 (integrity) — without it, Phase 1 metrics are untrustworthy.
- **Crypto can lead** Phases 1–2 (best evidence: TSMOM + VWAP-MR core).
- **Document each promotion** with reproducible artifacts and gate checklist.
