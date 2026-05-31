# Phase-2 Performance Audit — CRYPTO

Source: `ejaguiar1_stocks.trading_picks WHERE category='crypto' AND closed_at IS NOT NULL`, pulled 2026-05-31 (post PR #158 SHIBUSDT resolver + PR #166 EQUITY mistag backfill).

## Class-aggregate

| metric | value | T2 threshold | T1 threshold | verdict |
|---|---|---|---|---|
| n | 4,451 | >=100 | >=100 | PASS |
| WR | 41.43% | >=50% | >=55% | **FAIL** |
| PF | 0.863 | >=1.5 | >=2.0 | **FAIL** |
| avg_pnl | -0.410% | >0 | >0 | **FAIL** |
| MDD (equity-curve proxy, equal-weight) | ~2,211% peak-to-trough | <20% | <10% | **FAIL (extreme)** |

**Class verdict: FAIL all axes except n.** Aggregate WR/PF is consistent with the `money_ready_verdict.json` post-policy-clean view (PF 0.89, WR 37.4%) — the small upward bias here (PF 0.86 → 0.89 raw vs net; WR 41.4 vs 37.4) is the absence of slippage/fee netting on the raw DB read. The DISPUTED CRYPTO banner is justified.

Note: MDD proxy is an equal-weight, order-by-`closed_at` equity curve on per-pick `pnl_pct` values — it overstates real portfolio MDD because it does not normalize by capital allocation per trade. Treat it as directional only; the consistent triple-digit single-strategy MDDs below indicate genuine tail risk regardless of normalization.

## Per-strategy table (n >= 10, sorted by PF desc)

| strategy | n | WR | PF | avg_pnl | MDD% | T2 verdict |
|---|---|---|---|---|---|---|
| ml_enhanced_INJUSDT_1d_B_lightgbm | 25 | 96.00% | 35.64 | 13.86 | 10.0 | thin-n |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 10 | 80.00% | 25.48 | 3.84 | 1.4 | thin-n |
| prediction_market_consensus | 95 | 84.21% | 24.51 | 2.83 | 3.2 | near-T1, thin-n |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 34 | 94.12% | 10.36 | 1.59 | 4.8 | thin-n |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 28 | 50.00% | 6.02 | 9.54 | 37.9 | thin-n + MDD fail |
| multi_period_rsi_confluence_eth | 12 | 66.67% | 4.47 | 11.10 | 32.9 | thin-n + MDD fail |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 39 | 64.10% | 4.34 | 4.12 | 23.0 | thin-n + MDD fail |
| crypto_keltner_compression_expansion_v1 | 21 | 71.43% | 3.09 | 17.07 | 148.9 | thin-n + MDD extreme |
| ml_enhanced_ZKUSDT_4h_D_ensemble_stack | 12 | 75.00% | 2.67 | 1.30 | 6.5 | thin-n |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 34 | 58.82% | 2.33 | 2.66 | 31.8 | thin-n + MDD fail |
| ml_enhanced_INJUSDT | 18 | 72.22% | 2.32 | 0.41 | 5.6 | thin-n |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack | 28 | 82.14% | 2.13 | 0.62 | 15.4 | thin-n |
| copy_hl_lb_None | 279 | 0.72% | 2.13 | 1.50 | 4.0 | **WR fail, n>=100** — degenerate |
| ml_enhanced_ADAUSDT_15m_B_lightgbm | 22 | 63.64% | 1.91 | 0.44 | 4.5 | thin-n |
| keltner_compression_expansion_xrp_v1 | 10 | 70.00% | 1.77 | 5.71 | 70.8 | thin-n + MDD extreme |
| ml_enhanced_STRKUSDT | 24 | 62.50% | 1.67 | 1.17 | 29.6 | thin-n + MDD fail |
| ml_enhanced_XRPUSDT_1d_D_ensemble_stack | 25 | 56.00% | 1.59 | 0.81 | 28.7 | thin-n + MDD fail |
| ml_enhanced_FETUSDT_15m_B_lightgbm | 26 | 73.08% | 1.42 | 0.42 | 17.0 | thin-n |
| claude_ml_moderate_mut | 26 | 46.15% | 1.40 | 0.58 | 24.4 | thin-n + MDD fail |
| (empty strategy) | 301 | 47.51% | 1.37 | 0.93 | 299.8 | **untagged bucket** |
| keltner_compression_expansion_eth_v1 | 21 | 61.90% | 1.28 | 3.21 | 171.6 | thin-n + MDD extreme |
| seasonal_factor_rotation | 13 | 38.46% | 1.25 | 0.19 | 4.5 | thin-n + WR fail |
| crypto_bayesian_regime_transition_momentum_v1 | 30 | 53.33% | 1.16 | 2.65 | 213.5 | thin-n + MDD extreme |
| fractal_sr_bounce | 21 | 38.10% | 1.14 | 0.02 | 1.4 | thin-n + WR fail |
| ml_enhanced_TONUSDT_4h_D_ensemble_stack | 18 | 61.11% | 1.13 | 0.21 | 24.7 | thin-n + MDD fail |
| order_book_imbalance | 11 | 45.45% | 1.11 | 0.09 | 4.5 | thin-n + WR fail |
| luxalgo_confluence | 1,968 | 42.58% | 1.10 | 0.12 | 174.5 | **n>=100, PF/WR/MDD all fail** |
| ml_enhanced_TONUSDT | 23 | 69.57% | 1.07 | 1.32 | 405.3 | thin-n + MDD extreme |
| crypto_soc_orderflow_absorption_a10_v1 | 18 | 44.44% | 1.06 | 0.83 | 101.0 | thin-n + MDD extreme |
| quan_engine_swing | 10 | 50.00% | 1.00 | -0.01 | 9.6 | thin-n + PF fail |
| keltner_compression_expansion_sol_v1 | 22 | 59.09% | 0.91 | -1.62 | 402.8 | thin-n + PF/MDD fail |
| spot_perp_basis_arb | 16 | 50.00% | 0.90 | -0.08 | 5.3 | thin-n + PF fail |
| ml_enhanced_DOGEUSDT_15m_D_ensemble_stack | 28 | 50.00% | 0.71 | -0.19 | 10.4 | thin-n + PF fail |
| ml_enhanced_APEUSDT | 10 | 40.00% | 0.68 | -0.47 | 7.2 | thin-n + PF/WR fail |
| ml_enhanced_POLUSDT_1d_B_lightgbm | 26 | 46.15% | 0.65 | -1.02 | 70.7 | thin-n + all-axis fail |
| ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | 31 | 41.94% | 0.62 | -0.42 | 27.9 | thin-n + all-axis fail |
| ml_enhanced_ZKUSDT | 26 | 50.00% | 0.57 | -1.30 | 45.8 | thin-n + PF/MDD fail |
| ml_enhanced_ALGOUSDT_15m_B_lightgbm | 29 | 48.28% | 0.50 | -1.08 | 39.9 | thin-n + all-axis fail |
| ensemble | 76 | 40.79% | 0.34 | -5.02 | 491.8 | n<100, all-axis fail |
| ml_enhanced_AVAXUSDT_1d_B_lightgbm | 25 | 44.00% | 0.34 | -1.29 | 38.8 | thin-n + all-axis fail |
| drawdown_recovery_rsi_eth | 17 | 41.18% | 0.31 | -9.64 | 190.9 | thin-n + all-axis fail |
| autocorrelation_exploiter | 12 | 25.00% | 0.30 | -1.42 | 22.6 | thin-n + all-axis fail |
| ml_enhanced_HBARUSDT_1d_D_ensemble_stack | 27 | 44.44% | 0.29 | -1.70 | 59.6 | thin-n + all-axis fail |
| ml_enhanced_JTOUSDT_1d_B_lightgbm | 28 | 35.71% | 0.28 | -4.84 | 161.3 | thin-n + all-axis fail |
| cross_sectional_reversal | 11 | 9.09% | 0.26 | -1.89 | 20.4 | thin-n + all-axis fail |
| ml_enhanced_INJUSDT_15m_D_ensemble_stack | 28 | 10.71% | 0.15 | -0.74 | 23.2 | thin-n + all-axis fail |
| ml_enhanced_DYDXUSDT | 27 | 29.63% | 0.12 | -9.52 | 267.4 | thin-n + all-axis fail |
| kalman_filter_trend | 11 | 9.09% | 0.06 | -1.48 | 17.4 | thin-n + all-axis fail |
| ml_enhanced_APEUSDT_1d_D_ensemble_stack | 25 | 36.00% | 0.06 | -24.36 | 641.8 | thin-n + all-axis fail |
| ml_enhanced_TRXUSDT_1d_B_lightgbm | 25 | 12.00% | 0.004 | -63.04 | 1576.6 | catastrophic |
| binance_smart_money | 10 | 0.00% | n/a | n/a | 0.0 | data-quality (pnl NULL) |
| funding_rate_carry | 11 | 36.36% | n/a | n/a | 0.0 | data-quality (pnl NULL) |

## Promotable to T2 (PASS all axes, n >= 100)

**ZERO strategies pass T2 with n>=100.** Only two strategies clear n>=100 at all:
- `luxalgo_confluence` (n=1968) — PF 1.10 / WR 42.6% / MDD 174% → FAIL on all three quality axes.
- `copy_hl_lb_None` (n=279) — PF 2.13 but WR 0.72% → degenerate (skewed by 1-2 fat tails; statistically not a strategy, recommend audit).
- `prediction_market_consensus` (n=95) — closest to T1-quality (WR 84.2%, PF 24.5, MDD 3.2%) but **5 picks short of the n>=100 floor**. Highest-priority candidate for promotion once it crosses 100; flag for active scaling.

## Watchlist (strong metrics but thin sample, near n=100)

Order: closest to graduation first.
1. `prediction_market_consensus` (n=95) — needs 5 more closed picks. **Top promotion candidate.** Watch for source-concentration: top symbol DOGEUSDT 48/95 (50.5%) is borderline HHI fail.
2. `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=39) — PF 4.34 / WR 64% but 100% single-symbol concentration (per-symbol grid strategy, not portfolio-tradable in isolation).
3. `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` (n=34) — PF 10.4 / WR 94% — same single-symbol caveat.
4. `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` (n=28, MDD 15.4%) — only ML-grid strategy with MDD inside T2.
5. `ml_enhanced_INJUSDT_1d_B_lightgbm` (n=25, MDD 10%) — top PF but only on INJUSDT.

**Caveat for the ml_enhanced_* family:** these are per-symbol-per-timeframe grid strategies (top-symbol concentration = 100% by design). The "strategy" is really a symbol bet. Treat the family as an ensemble; a single member graduating to T2 is misleading.

## Dead/retire candidates (catastrophic PF or n>=100 fail)

- `ml_enhanced_TRXUSDT_1d_B_lightgbm` (n=25, PF 0.004, avg_pnl -63%, MDD 1577%) — kill on sight.
- `ml_enhanced_APEUSDT_1d_D_ensemble_stack` (n=25, PF 0.06, avg_pnl -24%, MDD 642%) — kill.
- `ml_enhanced_DYDXUSDT` (no-suffix; n=27, PF 0.12, MDD 267%) — kill (note: distinct from the 15m_D_ensemble_stack variant which is working).
- `kalman_filter_trend`, `cross_sectional_reversal`, `ml_enhanced_INJUSDT_15m_D_ensemble_stack` (PF<0.20, WR<11%) — kill.
- `drawdown_recovery_rsi_eth` (n=17, PF 0.31, 94% ETHUSDT concentration, MDD 191%) — kill.
- `luxalgo_confluence` (n=1968, PF 1.10) — biggest live emitter, sub-T2. Recommend **mutate-before-kill** per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (axes: regime gate, volatility floor, source-confluence). Killing without mutation risks losing the only large-n base.
- `copy_hl_lb_None` (n=279, WR 0.72%) — investigate resolver labelling; PF is real but WR=0.72 across n=279 suggests `status` mislabel or all-pnl-from-1-2 trades. **Audit before kill, do not delete.**

## pf_registry divergences

- DB class-aggregate (this audit): n=4451 / WR=41.4% / PF=0.86 (gross, no slippage).
- pf_registry `by_asset_class_policy_clean_net`: n=334 / WR=37.4% / PF=0.89 (filtered to policy-clean cohort + slippage-netted).
- pf_registry `by_asset_class_raw`: n=1544 / WR=41.4% / PF=1.46 — closely matches DB WR but materially higher PF.

**Divergence on PF magnitude (0.86 DB vs 1.46 raw-registry) is large.** Likely drivers:
1. Registry `raw` view is on `at_raw_picks`, not `trading_picks` — different denominator (loss bucket smaller in raw).
2. Registry winsorizes tail PnL; DB does not (worst observed in DB = -100%, best = +99.97%).
3. Policy-clean cohort (n=334) is a small slice; the broader 4,451-pick DB universe drags PF down because the bulk of luxalgo_confluence and ensemble/ml_enhanced losers are policy-excluded from the clean cohort.

Per-strategy registry view is uninformative for divergence audit: `by_asset_class_strategy_policy_clean_net` lists 48 crypto strategies but **all have `pf: None` and n<10 except `UNKNOWN` (n=36), `battleground_luxalgo` (n=37), `copy_trader_clones/intel` (n=34 each)**. The strategy taxonomy in the registry does not align with the DB `strategy` column (registry uses `at_raw_picks.source_system`-derived names, DB uses pipeline-emitted strategy names). Cross-walk is needed before per-strategy divergence is meaningful — flag as separate follow-up.

## Leftover mistag anomalies (post PR #158 / PR #166)

Suffix-mistag scan: 54 rows where `category != 'crypto'` but symbol has a crypto suffix:
- `category='meme'` × 25 rows — DOGEUSDT (17), SHIBUSDT (7), WIFUSDT (1). **Intentional**, not a mistag — `meme` is a separate class for memecoin-specific pipelines. Confirm with class owner this is desired.
- `category=''` (empty) × 28 rows — ETH (17), BTC (11). **Mistag**, should be backfilled to `crypto`. Low blast-radius (28 picks) but should land before the next per-class audit.
- `category='forex'` × 1 row — BTCUSDT (1). Single stray; safe to manual-fix.

Additionally, the DB has 301 closed CRYPTO picks with `strategy=''` (empty string) — top symbol WIFUSDT (7%), WR 47.5%, PF 1.37, MDD 300%. This is the un-tagged bucket and should be source-traced to its emitter, then either reassigned or excluded from class-aggregate.

## Recommendation

1. **Next graduation candidate**: `prediction_market_consensus`. It is 5 picks short of n>=100 and currently posts T1-grade WR/PF/MDD (84%/24.5/3.2%). **DO NOT promote until n>=100 AND HHI on top symbol drops below 0.40** (currently DOGEUSDT 50.5%). Add a concentration gate before any sizing-up decision; otherwise this is one symbol, not a strategy.

2. **Top kill**: `ml_enhanced_TRXUSDT_1d_B_lightgbm` — avg_pnl -63%, PF 0.004, MDD 1577% on n=25. Then in order: `ml_enhanced_APEUSDT_1d_D_ensemble_stack`, `ml_enhanced_DYDXUSDT` (no-suffix), `kalman_filter_trend`, `ml_enhanced_INJUSDT_15m_D_ensemble_stack`. For `luxalgo_confluence` (n=1968, PF 1.10) — mutate-before-kill via three-axis protocol; killing it removes the largest n base without a replacement.

3. **Data-integrity follow-ups before the next audit**: (a) backfill `category=''` crypto-suffix picks (28 rows) to `'crypto'`; (b) source-trace the 301 closed picks with `strategy=''`; (c) build pf_registry ↔ DB strategy cross-walk so per-strategy divergence audit can run; (d) re-resolve `binance_smart_money` and `funding_rate_carry` (n=10/11, pnl NULL — resolver gap).
