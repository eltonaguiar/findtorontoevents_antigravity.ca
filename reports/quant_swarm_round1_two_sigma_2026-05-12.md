# Two Sigma Lens — Round 1 Quant Swarm (2026-05-12)

ML-systematic. Alt-data. Ensembles. Drift-aware. Caveman.

## 1. Per-class keep / kill / rebuild

- **CRYPTO** — KEEP filtered (PF 1.36 post-resolver-v2). KILL `quan_engine` MATIC 100%-WR ghost + `alpha_engine_fast` (PF 0.62) + `kimi_signal_tracking` (decayed 30.4%). REBUILD per-symbol ensemble with funding/OI/onchain alt-data; 20K stale joblibs from 2026-03-28 are dead weight.
- **EQUITY** — KEEP T2-candidate (PF 1.41 / WR 52.7%). Gatekeeper holdout +16.16pp. REBUILD with PEAD + earnings-drift + analyst-revision alt-data; current top-features are all in-system (`strat_fwd_wr`, `forward_wr`) — pure autocorrelation, no real alpha.
- **COMMODITY** — KEEP (PF 1.78 / WR 46.9%, n=750). REBUILD around COT extremes (cot_paper_pilot) + carry/momo a la Miffre 2010; cotton/coffee 53yr COT is the genuine alt-data edge.
- **BOND** — KEEP (PF 1.72), n=18 too thin. REBUILD as TLT/IEF spread-z + DGS10-DGS2 FRED macro pair-trades per v3b spec.
- **FOREX** — KILL emissions until mutate-protocol done (PF 0.27 unfiltered; but gatekeeper +16.86pp on filtered subset — strong residual signal exists). REBUILD with carry + DXY regime gate.
- **FUTURES / ETF / MEMECOIN / PENNY** — KILL routing. Sub-floor, no path.

## 2. Hidden-insight queries

- **Low-score-high-PnL:** gatekeeper top-20 features are ALL endogenous (`strat_fwd_wr`, `age_hours`, `sl_dist_pct`, `rr_ratio`). Zero macro, zero microstructure, zero sentiment, zero cross-sectional rank. Missing: VIX-regime, DXY-regime, sector-relative-strength, COT-z, funding-skew, order-flow-imbalance, news-sentiment surprise. The model can't see WHY a trade works — only that the strategy worked last time. That is **momentum-on-strategy-WR**, not alpha. Add the 7 alt-data features and re-train; expect AUC 0.59 → 0.65+.
- **High-score-low-PnL:** CRYPTO holdout −16.67pp. Residual signal = `direction` (importance 0.0201, near-bottom). Gatekeeper has learned the LONG-bias of 7 source systems but CRYPTO regime since Apr inverts on red-BTC-4h. Stratify training by `btc_4h_regime`; fit per-regime calibrators.
- **Dormant top strategies:** `enhanced_ml_crypto_v3` workflow silently skipping retrain on feature-count mismatch since 2026-03-28 (44d stale). Drift diagnostic = feature-schema diff vs current `at_raw_picks`. Likely 1-2 columns added downstream; auto-bisect and rebuild baseline.

## 3. First builds (Two Sigma stack)

Priority order. NO deep models yet — n=3500 labeled rows after noise filter is laughably thin for LSTMs/transformers.

1. **Stacked LightGBM + XGBoost + CatBoost ensemble**, per-asset-class submodel, isotonic-calibrated. Replace single-LGBM gatekeeper. Expected lift: AUC +0.03-0.05, WR +3-5pp at fixed selection rate.
2. **Purged-CPCV** (López de Prado AFML ch.7) replacing 12-fold WF — current setup ignores embargo, label-leakage near class boundaries. Expected: drops apparent lift 2-3pp but kills the in-sample optimism that produces 42% BT vs 11% live.
3. **Meta-labeling** (Triple-Barrier): primary model = existing strategies, meta = LightGBM predicts P(strategy correct). Expected +5-8pp precision at 30% recall.
4. **Drift monitors** (PSI/KS on top-10 features, 24h window) auto-gate when PSI>0.25.

## 4. ML reality fix — 32.6% accuracy + CRYPTO inversion

32.6% with precision 11.5 / recall 84.4 is **class-imbalance pathology**, not anti-edge. Model predicts WIN almost always; the 11% base rate kills accuracy. Fix:

- Threshold-tune on **expected-value** not accuracy; use cost-sensitive loss (`scale_pos_weight = (1-base_wr)/base_wr`).
- Per-class calibrators (Platt/isotonic) — CRYPTO inversion vanishes when calibrated per regime.
- Hard-rule: if per-class holdout-lift < 0 over rolling 500 picks, **auto-disable** that class from gatekeeper output (don't invert — disable; inversion is a bet on stationarity we haven't earned).

## 5. THE ONE THING — Day 1

**Ship Purged-CPCV + embargo on all training. Today.**

42% backtest vs 11% live = ~31pp leakage. Until that gap closes, every model claim, every "Tier 2 candidate," every per-class lift number is in-sample optimism. CPCV is 4 hours of work. Nothing else matters until the OOS gap is < 5pp. No real-money sizing, no v3b rollout, no ensemble work — CPCV first.

## NFA — research surface only.
