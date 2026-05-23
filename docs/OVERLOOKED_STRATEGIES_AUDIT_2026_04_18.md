# Overlooked Strategies Audit — 2026-04-18

**Author:** Claude Opus 4.7 (1M ctx), task-pool investigator
**Companion docs:** `GITHUB_STRATS.MD`, `KIMI_STRATS.MD`, `ANTIGRAVITY_STRATS.MD`, `CURSOR_STRATS.MD`, `XIAOMI_MIMO_STRATS.MD`
**Baseline:** Post-retraction of `CRYPTO_PLAYBOOK_RETRACTION_2026_04_18.md` — zero approved combos cleared Wilson LB > 50% @ Bonferroni k=4.

> **Important corrigendum.** The task brief references `GITHUB_CLOUDAGENT_STRATS.MD` committed on branch `copilot/research-other-strategies` at SHA `104a741`. **Neither the file nor the SHA exists in this repository.** `git log --all --oneline | grep -i "cloudagent"` returns nothing; branch list has only `copilot/enhance-prediction-strategies`. The closest real artifacts are `GITHUB_STRATS.MD` (2.5 MB, 26k lines, 309 strategies, commit `3c57881d9c`), `ANTIGRAVITY_STRATS.MD` (commit `d2031ef117`), `KIMI_STRATS.MD` (`9f1d9a1fe0`), `XIAOMI_MIMO_STRATS.MD` (`3645e4cca2`), `CURSOR_STRATS.MD` (`ed57b08675`). I treat these five as the aggregated "prior cloud agent output" and build on them.

---

## 1. What prior cloud-agent research already produced

**GITHUB_STRATS.MD** (309 strategies, multi-agent, walk-forward + CPCV specs)
- PART I (100): microstructure (VPIN variants, Kyle's λ, Hasbrouck IS, Amihud, LDINN LSTM, ACD), cross-asset/macro (PMI, 2s10s/5s30s, CDX/iTraxx momentum, term-premium harvesting, Dollar Smile), alt-data, DeFi protocol, on-chain advanced, NFT, crypto deriv, behavioral, market structure, ML.
- PART II (49 equity): factor, stat-arb, PEAD variants, sector rotation, institutional flow, equity microstructure, special situations.
- PART III (40 FI/FX/commodities), IV (40 crypto/DeFi), V (40 options/ML/alt-data), VI (40 macro/sys-portfolio).

**KIMI_STRATS.MD** — 54 institutional strategies (options, rates, macro, DeFi, risk premia).

**ANTIGRAVITY_STRATS.MD** (443 lines, April 18) — the most operational of the set. Key calls:
- "Completely missing": Cu/Au ratio gate, HYG-LQD spread momentum, TIP/TLT real-rate, yield-curve slope (ZN-ZT), VIX term-structure switch, ETF creation/redemption flow, index rebalance front-run, dispersion trading, gamma scalping, GNN crypto correlation, TFT forecasting, MEV-aware entry, tariff NLP, Baltic Dry, FOMC NLP, MOC imbalance, Asian-session → London breakout, spoof-detection alpha, protocol revenue momentum, stablecoin velocity.
- Flagged as "already in universe, just not ratioed": HG=F, GC=F, HYG, LQD, TIP, TLT, ZN=F, ZT=F, VIXY — five P0 wins using only existing data.

**CURSOR_STRATS.MD** — narrower; emphasises that the 347-ID `STRATEGY_FAMILIES` map in `alpha_engine/config.py` has depth-of-implementation gaps rather than name gaps: dispersion/correlation swaps, dealer-gamma/OI maps, pure RL policies, `kimi_*` ML stacks unwired, market-making/liquidity provision, convertible RV, cross-margin contagion, DEX-vs-CEX basis with oracle/vAMM mechanics.

**XIAOMI_MIMO_STRATS.MD** (902 lines) — 40+ additional strategies; overlaps heavily with the above on volatility carry, dispersion, PEAD-variants, stat-arb pairs.

**Net novel from the prior docs (de-duplicated across all five):** ~180 unique strategy archetypes proposed, of which ~40 genuinely fill repo gaps.

---

## 2. Current strategy inventory (master list)

Evidence:
- `alpha_engine/config.py::STRATEGY_FAMILIES` — ~347 IDs across 12 INDICATOR_FAMILIES (momentum, trend, volume, sentiment, on_chain, structure, volatility, carry, regime, mean_reversion, community, earnings).
- `baby_strategies/` — **193 `.py` files** (`ls baby_strategies/*.py | wc -l`). Includes `adaptive_*`, `adx_*`, `autocorr_reversion`, `bb_squeeze_breakout`, `bollinger_mean_reversion`, Connors R2/R3/R4, `corr_*` (hma, kama, vwap, zscore, triple_crown, net_consensus), `dca_rsi_adaptive`, `dema_crossover_momentum`, `donchian_trend_filter`, `dual_momentum_crypto`, `dxy_weekly_drop`, `ehlers_fisher_transform`, `elder_ray_power`, `equity_earnings_drift_pead`, `equity_sector_rotation_momentum`, `equity_vix_regime_momentum`, `fib_rsi_divergence`, `fomc_drift_calendar`, forex `bb_mr`/`carry_momentum_harvest`/`ensemble_4h`/`weekly_open_gap_fill`, funding-rate family (`fr_adx_regime`, `fr_base_reversal`, `fr_full_confluence`, `fr_liquidity_filtered`, `fr_mtf_aligned`, `fr_pullback_entry`, `fr_rsi_divergence`, `fr_volume_spike`, `funding_rate_mean_reversion_v1`), `heikin_ashi_trend_rider`, `hoffman_*`, `hurst_regime_filter`, `ichimoku_cloud_breakout`, `kalman_mean_reversion`, inverse wrappers.
- `alpha_engine/crypto_edge_strategies.py:298/530/771` — `funding_rate_extreme_contrarian`, `oi_price_divergence_v2`, `liquidation_flush_recovery`.
- `quan_engine/strategy_pool.py` — wraps 7 baby_strategies: `overnight_seasonality_btc`, `pairs_spread_btceth`, `liquidity_sweep_reversal`, `consecutive_down_rsi`, `rsi2_bb_squeeze`, `autocorr_reversion`, `volume_profile_deviation`; plus prop families in `quan_engine/prop_strategies.py`.
- `tools/hyro_backtest_extended.py` EXTENDED_STRATEGIES keys: `adx_trend`, `bollinger`, `donchian`, `ema_crossover`, `ema_rsi_filtered`, `false_breakout`, `heikin_ashi`, `keltner`, `macd_trend`, `rsi_volume`, `stochastic`, `supertrend`, `volume_surge_rev`, `vwap`, `williams_r`.
- `tools/hyro_backtest_new_strategies.py` NEW_STRATEGIES: `adx_slope_momentum`, `consolidation_breakout`, `rsi_pullback`, `triple_ema_trend`, `vwap_trend`.
- `genome/` — 13 DNA modules (`dna_engine*`, `dna_confluence_mutations`, `dna_pumpwatch_v2_mutations`, `dna_rapid_fire_mutations`, `dna_signal_engine_mutations`, `dna_strategy_factory`, `dna_winner_mutations`, `evolve_strategies`, `genetic_programmer`, `contrarian_evolver`, `failure_evolver`, `ensemble_evolver`, `audit_ensemble_evolver`).
- `genome/mutation_lab/` — 3 mutators (see §5): `mutator_amplify`, `mutator_invert`, `mutator_hybrid`; plus `antigravity_mutations_v2`, `innovative_mutations`, `kimi_supplemental_mutations`, `mega_crypto_strategies`, `mega_equity_strategies`, `mega_forex_strategies`, `super_mutations`, `trusted_genome_mutations`.
- `ml_battleground/` — `battleground_mutations`, `ensemble_coordinator`, `retrain_on_live`, abc forward-test harness.
- `breakout_arena/` — three approaches: `approach_a_sr_breakout`, `approach_b_ml_breakout`, `approach_c_spike_reverse`.

Total effective coverage: ~600+ unique strategy expressions, ~347 canonical IDs.

---

## 3. Truly novel additions (⭐), partials (🟡), already-done (✅)

Scored 1–5 on **Evidence** (academic/backtest quality), **Difficulty** (1=hour, 5=month), **Edge** (incremental PnL potential over existing book).

| # | Strategy (source doc) | Status | Evidence | Diff | Edge |
|---|---|---|---|---|---|
| 1 | Copper-Gold regime gate (ANTIGRAV 4.4) | ⭐ NOVEL — HG/GC both in universe, no ratio code | 4 | 1 | 4 |
| 2 | HYG-LQD credit-spread momentum (ANTIGRAV 4.5, GITHUB 2.3) | ⭐ NOVEL as spread; both ETFs in universe | 5 | 1 | 4 |
| 3 | TIP/TLT real-rate signal (ANTIGRAV 4.6) | ⭐ NOVEL | 4 | 1 | 3 |
| 4 | 2s10s yield-curve slope (ANTIGRAV 4.2, GITHUB 2.2) | ⭐ NOVEL | 5 | 2 | 4 |
| 5 | VIX term-structure contango/backwardation switch (ANTIGRAV 10.1, 3.1) | ⭐ NOVEL as binary regime | 5 | 2 | 4 |
| 6 | FOMC minutes hawkish/dovish NLP (ANTIGRAV 8.4) | 🟡 have `fomc_drift_calendar`, no NLP | 4 | 3 | 3 |
| 7 | Multi-exchange VPIN (Binance+Bybit+OKX) (ANTIGRAV 6.4) | 🟡 have `vpin_detector` single-venue | 4 | 3 | 3 |
| 8 | Funding settlement 15-min reversion (ANTIGRAV 9.2) | ⭐ NOVEL (have funding, not settlement-timed) | 3 | 1 | 3 |
| 9 | MOC (market-on-close) imbalance (ANTIGRAV 9.3) | ⭐ NOVEL | 4 | 3 | 4 |
| 10 | Asian-range → London-open breakout (ANTIGRAV 9.4) | 🟡 have generic ORB | 3 | 1 | 3 |
| 11 | CTA multi-asset 12m trend across SPY/TLT/GLD/DBC (ANTIGRAV 10.4) | ⭐ NOVEL as cross-asset TF | 5 | 2 | 4 |
| 12 | Correlation-breakdown detector (DCC-GARCH z-score) (ANTIGRAV 10.2) | 🟡 have `correlation_monitor`, not used as signal | 4 | 3 | 3 |
| 13 | Dispersion trade (index IV vs constituent IV) (ALL docs) | ⭐ NOVEL, needs options data | 5 | 5 | 4 |
| 14 | Gamma scalping (long straddle + dynamic delta hedge) (ANTIGRAV 3.3) | ⭐ NOVEL | 5 | 5 | 3 |
| 15 | GEX / dealer-gamma map (CURSOR, ANTIGRAV) | ⭐ NOVEL | 5 | 4 | 4 |
| 16 | Temporal Fusion Transformer multi-horizon (ANTIGRAV 2.1) | ⭐ NOVEL (have LSTM only) | 4 | 4 | 4 |
| 17 | Graph Neural Net crypto token propagation (ANTIGRAV 2.3) | ⭐ NOVEL | 3 | 5 | 4 |
| 18 | Conformal prediction wrapper on existing ML ranker (ANTIGRAV 2.4) | 🟡 have `conformal_sizing`, not on signal | 5 | 2 | 3 |
| 19 | Protocol revenue momentum (Token Terminal, DefiLlama) (ANTIGRAV 5.3) | ⭐ NOVEL (have TVL, not revenue) | 4 | 2 | 4 |
| 20 | Stablecoin velocity (bridge + CEX deposits) (ANTIGRAV 5.2) | 🟡 have supply, not velocity | 3 | 3 | 3 |
| 21 | DEX concentrated-liquidity positioning (Uni V3/V4) (ANTIGRAV 5.1) | ⭐ NOVEL | 3 | 4 | 3 |
| 22 | Spot-perp cross-venue basis w/ credit constraint (CURSOR 4.2–4.3) | 🟡 have basis, not cross-venue w/ borrow cost | 5 | 3 | 4 |
| 23 | Kyle's λ adaptive execution (GITHUB 1.2) | ⭐ NOVEL | 5 | 4 | 3 |
| 24 | Amihud-illiquidity mean reversion (GITHUB 1.4) | ⭐ NOVEL for small-cap sleeve | 5 | 2 | 3 |
| 25 | Flash-crash precursor + recovery (GITHUB 1.7) | ⭐ NOVEL | 4 | 3 | 3 |
| 26 | ETF creation/redemption flow (ANTIGRAV 7.1) | ⭐ NOVEL | 4 | 2 | 3 |
| 27 | Quarter-end window dressing (ANTIGRAV 7.3) | 🟡 have `turn_of_month`, not QE-specific | 3 | 1 | 2 |
| 28 | Dollar-Smile regime (ANTIGRAV 4.3) | 🟡 have `usd_strength_scanner` | 4 | 3 | 3 |
| 29 | Baltic Dry Index momentum (ANTIGRAV 8.2) | ⭐ NOVEL | 3 | 2 | 2 |
| 30 | Tariff-announcement NLP shock absorber (ANTIGRAV 8.1) | ⭐ NOVEL | 3 | 4 | 3 |

---

## 4. Cross-asset transfer opportunities

The repo is siloed: `quan_engine` = crypto perps; `alpha_engine` scanner = equities; `forex_smart_picks.py`+`non_crypto_policy.py` = FX; `multi_asset/` = ETFs. High-conviction transfers:

1. **`quan_engine_scalp` (LONG bias, 2:1 RR, 8-bar hold) → US equities (ES/NQ intraday).** The 8-bar hold on 5m crypto is the 40-min equity equivalent; VWAP+momentum logic survives asset transplant because it keys off microstructure, not token-specific features. Evidence: the live concentration penalty in pick #373 (`source_concentration_penalty: -18`, "edge concentrated in HYPEUSDT, TAOUSDT, TRXUSDT") explicitly tells us the signal isn't crypto-idiosyncratic — it's being amplified by a tiny symbol subset. Equity transplant dilutes concentration risk.
2. **`adx_slope_momentum` (`tools/hyro_backtest_new_strategies.py`) → FX majors (EURUSD, GBPUSD).** ADX slope is regime-agnostic. Currently only backtested on crypto; forex has stronger trending regimes during session overlap.
3. **`corr_vwap_zscore_reversion` (baby_strategies) → ETF pairs (XLK/XLF, IWM/SPY).** Crypto VWAP-reversion logic transplants cleanly; ETF pairs have stationarity that crypto pairs lack.
4. **`fomc_drift_calendar` → crypto (BTC, ETH).** Currently equity-only. BTC has shown clear drift around FOMC since 2021 (spot-ETF flows amplified post-2024).
5. **`funding_rate_extreme_contrarian` (crypto perps) → FX forwards.** Inverted form: when forward points are extreme (carry premium blown out), mean-reversion trade on the forward basis. Pure asset-class transplant.
6. **`equity_earnings_drift_pead` → crypto token unlocks.** PEAD-style drift after scheduled unlock events. Same mechanism (slow-information-diffusion), different event catalyst.
7. **`liquidity_sweep_reversal` (crypto perps) → equity index futures at key VWAP/prior-day-high levels.** Liquidity-grab mechanics are identical at stop clusters.
8. **`dxy_weekly_drop` (forex) → emerging-market equities (EEM, FXI).** EM equities are inverse-DXY; the signal is already latent.

---

## 5. DNA mutation gaps

Evidence: `genome/mutation_lab/` contains **exactly three mutator kinds**:
- `mutator_amplify.py` — parameter perturbation (±PERTURBATION_RANGE) on winners.
- `mutator_invert.py` — "Pure Flip" (BUY↔SELL of losers with WR<30%) + "Loser Inversion" (inferred genes from losers with polarity flip).
- `mutator_hybrid.py` — loser-fix (parameter perturb around losing strategy) + crossbreed (winner × loser gene mix).

What the mutators are iterating on: `targets_path`-driven, but consumers are primarily winner lists in `genome/trusted_genome_picks.md` + per-run JSONs. The existing cadence preferentially mutates the **already-proven**. Per the retraction, this is producing diminishing returns (no combo clears Wilson LB > 50% @ Bonferroni k=4).

**Mutations NEVER tried (gaps):**
1. **Timeframe inversion.** No mutator transplants a 1h strategy onto 5m or 1d. Only parameter-level perturbation. A timeframe-jump would effectively create a new family.
2. **Asset-class transplantation.** `mega_crypto_strategies.py`, `mega_equity_strategies.py`, `mega_forex_strategies.py` exist as **separate** pools. No mutator lifts a genome from one pool and retunes it on the other's data. The cross-asset transfers in §4 are exactly this gap.
3. **Regime-conditional activation.** The `regime_router.py` and `bayesian_regime_reference.py` exist but are **routing**, not **gating**. A regime-conditional mutation would fork one strategy into {regime-A-only, regime-B-only, regime-C-only} variants and score each. Not done.
4. **Ensemble-member dropout / causal masking.** The ensemble evolver (`genome/ensemble_evolver.py`) selects members; it never ablates a member *with controls* to measure marginal attribution. Shapley-style attribution mutations would identify dead weight.
5. **Entry/exit decoupling.** All mutators perturb entry and exit gene jointly. Decoupling — "keep entry, re-evolve exit logic only" — has not been attempted and is the cheapest way to recover losers whose thesis is right but exit is wrong.
6. **Inverse on winners.** `mutator_invert.py` only inverts losers. Inverting winners during regime change (when a winner decays) has never been tested and is a natural hedge.
7. **Horizon extension.** `quan_engine` 8-bar max-hold is hardcoded. No mutator tries 16, 32, 64 bars while holding every other gene fixed.

---

## 6. Top 5 implementation priorities

Ranked by (Evidence × Edge) / Difficulty. All five require **zero new data sources** — everything is already in the universe per `ANTIGRAVITY_STRATS.MD` §11 "Quick Wins".

| Rank | Strategy | Data | Effort | ROI estimate | Why now |
|------|----------|------|--------|--------------|---------|
| 1 | **Copper-Gold regime gate as an overlay filter on all equity/ETF longs** | HG=F, GC=F in universe | 1 day | +3–8% ann. Sharpe uplift | Filters risk-off periods; one of the cleanest growth proxies in macro |
| 2 | **HYG-LQD credit-spread momentum** (widening → defensive, tightening → offensive) | HYG, LQD in universe | 1 day | 56–65% WR, Sharpe 1.5–2.0 (GITHUB 2.3) | Credit leads equity by 2–4 weeks; direct fix for zero approved combos |
| 3 | **VIX term-structure binary switch** (contango=sell vol, backwardation=buy assets) | VIXY + VIX futures curve | 2 days | Sharpe 0.6–1.0 as overlay | Kills whipsaw in regime-transition windows |
| 4 | **CTA 12-month multi-asset trend** on SPY/TLT/GLD/DBC equal-weighted | All in universe | 2 days | Crisis-alpha (+20–40% in 2008/2020/2022) | Only unified cross-asset trend layer; current trend strategies are per-asset siloed |
| 5 | **Regime-conditional mutator** (fork each live strategy into 3 regime-gated variants; use existing `bayesian_regime_reference.py`) | None new | 3–5 days | Unlocks strategies currently killed by averaging across regimes | Directly attacks the Wilson-LB-ceiling problem identified in the retraction |

Priorities 1–4 are pure cross-asset ratio/regime signals using data already loaded. Priority 5 is infrastructure but is the **only one that compounds** across the entire strategy book.

---

## 7. Appendix: strategies to RETIRE

Derived by joining `strategies_agreed` across `alpha_engine/data/closed_picks.json` (4,391 closed picks) and keying on `exit_reason` + `pnl_pct`. Threshold: WR < 30% **and** total PnL < 0 over n ≥ 50 attributions. These are candidates for **removal**, not further mutation (they have been extensively amplified/inverted already; the thesis is broken, not the parameters).

| Strategy | n | WR | Total PnL (%) |
|----------|---|----|--------------:|
| `proven_triple_ema_prop` | 1,616 | **17.2%** | −203.4 |
| `proven_propfirm_cons_prop` | 1,832 | **19.5%** | −214.3 |
| `fear_greed_contrarian` | 3,525 | **28.3%** | −456.2 |

`fear_greed_contrarian` alone contributes −456% cumulative — it is the single largest PnL drag in the consensus engine. The "proven_*" prefix is misleading; these were backtest-winners that have not held up live. Retiring these three alone removes ~6,973 of 4,391 × k attributions (they frequently co-appear in `strategies_agreed`) and should materially lift aggregate Wilson LB without adding a single new edge.

**Also watch (WR 30–40%, negative PnL, n ≥ 100):**
- `proven_stochrsi_prop` (n=224, WR 31.2%, −67.3)
- `corr_hma_trend` (n=920, WR 32.9%, −156.5)
- `ema_momentum_prop` (n=1,572, WR 34.5%, −198.4)
- `ema_aggressive_prop` (n=2,031, WR 35.7%, −249.1)
- `proven_keltner_squeeze_prop` (n=1,187, WR 37.7%, −95.9)

These have Wilson LB < 50% with comfortable margin; they should drop to observe-only pending regime-conditional re-test per Priority 5 above.

---

## Document history

| Date | Change |
|------|--------|
| 2026-04-18 | Initial audit. Corrected missing-doc premise; cross-referenced all five prior STRATS docs; executed 4,391-pick closed-trade retire analysis. |
