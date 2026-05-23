# Strategy harvest synthesis (2026-05-19)

Generated: 2026-05-19T22:38:32.919781+00:00

## Source: TOP10_STRATEGIES_PER_ASSET_CLASS_2026-05-19.md

# Top 10 strategies per asset class (pf_registry)

**Generated:** 2026-05-19T22:34Z  
**Registry snapshot:** `2026-05-19T20:58:20Z`  
**Canonical view:** `by_asset_class_policy_clean_net`  
**Ranking:** `by_asset_class_strategy` sorted by profit_factor (prefer n≥5).

## Codebase configuration spec (for meta-prompts / debate)

| Knob | Value / path |
|------|----------------|
| PF source | `audit_dashboard/data/pf_registry.json` |
| Dedup key | strategy(source_system\|strategy), symbol, direction, trade_date, entry~2p |
| Emitter gate | `alpha_engine/emitter_whitelist.py` — `EMITTER_REGISTRY_GATE=1`, enforce off by default |
| Hardcoded toxic pairs | quan_engine/CRYPTO; cta_replicator/COMMODITY; multi_asset_copytrader/FOREX,EQUITY |
| Harness | `tools/edge_stability_harness.py` — 11/11 daily-bar causal **KILLED** |
| Quarantine | `audit_dashboard/data/quarantine_manifest.json` size_caps + blocked pairs |
| Strategy families | `alpha_engine/config.py` → `STRATEGY_FAMILIES` |

### Class size caps (quarantine_manifest)

- **CRYPTO:** max_risk 10% — Per Grok 2026-05-12 rescue plan + ML inversion -16.67pp on CRYPTO holdout
- **EQUITY:** max_risk 25% — T2 candidate; PF 1.41 / WR 52.7% on n=421
- **COMMODITY:** max_risk 25% — CT=F factor-beta sleeve (not alpha); CTA-crowding cap per AQR R3 review
- **ETF:** max_risk 20% — Borderline T2; emission audit pending
- **FOREX:** max_risk 0% — Sub-floor PF 0.27 / WR 45.6% on n=1169; class-blocked per hedge_fund_sprint until SHORT-only rehab clears
- **BOND:** max_risk 20% — Quality-T2 (PF 1.72) but n=18 sub-floor; ramping post-FRED fix

## CRYPTO

**Class policy_clean_net:** n=1127 | PF=0.659 | WR=44.3656% | MDD=1.0

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 96.8 | 60.545 | — | — |
| 2 | `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 19 | 89.5 | 58.819 | — | — |
| 3 | `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 96.4 | 41.520 | — | — |
| 4 | `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 56.8 | 9.427 | — | — |
| 5 | `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 61.7 | 3.943 | — | — |
| 6 | `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 29 | 89.7 | 3.771 | — | — |
| 7 | `drawdown_recovery_rsi_eth` | 9 | 55.6 | 3.322 | — | — |
| 8 | `st_atr_vol_breakout` | 7 | 57.1 | 3.296 | — | — |
| 9 | `proven_vwap_mean_reversion` | 5 | 60.0 | 3.094 | — | — |
| 10 | `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 56.8 | 2.120 | — | — |

**Rescue candidates (CRYPTO):** `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`, `ml_enhanced_INJUSDT_1d_B_lightgbm`, `ml_enhanced_FETUSDT_1d_B_lightgbm`

## EQUITY

**Class policy_clean_net:** n=5 | PF=0.253 | WR=20.0% | MDD=0.129189

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `multi_asset_copytrader` | 47 | 36.2 | 0.912 | — | — |
| 2 | `stocks_rsi2_pullback` | 2 | 50.0 | 0.750 | — | — |
| 3 | `auto_dna_mutation` | 1 | 0.0 | 0.000 | — | — |
| 4 | `regime_terminal` | 1 | 0.0 | 0.000 | — | — |
| 5 | `copy_trader_intel` | 1 | 100.0 | — | — | — |
| 6 | `futures_connors_rsi2` | 1 | 100.0 | — | — | — |

**Rescue candidates (EQUITY):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.

## COMMODITY

**Class policy_clean_net:** n=55 | PF=1.424 | WR=54.5455% | MDD=0.52391

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `multi_asset_cot` | 58 | 58.6 | 1.598 | — | — |
| 2 | `multi_asset_copytrader` | 64 | 46.9 | 1.124 | — | — |
| 3 | `cta_replicator` | 68 | 14.7 | 0.283 | — | — |
| 4 | `combined_confidence_strategy` | 6 | 16.7 | 0.256 | — | — |
| 5 | `cot_positioning` | 1 | 0.0 | 0.000 | — | — |

**Rescue candidates (COMMODITY):** `multi_asset_cot`

## ETF

**Class policy_clean_net:** n=2 | PF=11.995 | WR=50.0% | MDD=0.0204

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `etf_all_strategies` | 1 | 0.0 | 0.000 | — | — |
| 2 | `etf_scanner` | 1 | 100.0 | — | — | — |

**Rescue candidates (ETF):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.

## FOREX

**Class policy_clean_net:** n=148 | PF=1.491 | WR=56.0811% | MDD=0.043379

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `cta_replicator` | 109 | 64.2 | 2.514 | — | — |
| 2 | `combined_confidence_strategy` | 15 | 46.7 | 1.057 | — | — |
| 3 | `alpha_engine` | 43 | 27.9 | 0.594 | — | — |
| 4 | `multi_asset_scanner` | 15 | 26.7 | 0.306 | — | — |
| 5 | `multi_asset_copytrader` | 325 | 11.1 | 0.160 | — | — |
| 6 | `prediction_market_agents` | 1 | 0.0 | 0.000 | — | — |

**Rescue candidates (FOREX):** `cta_replicator`

## BOND

**Class policy_clean_net:** n=5 | PF=0.000 | WR=0.0% | MDD=0.479416

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|

## Cloud debate (`20260519T223418Z`)

### deepseek-deepseek-chat__meta_debate.md

# deepseek:deepseek-chat

elapsed=19.38s ok=True

# Meta-Debate: Top-10 Strategies Per Asset Class (v1)

## A) Per Asset Class Debate (Ranks 1-3)

### CRYPTO rank 1: `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`
**Prosecutor:** PF 60.545 on n=31 is a textbook overfit artifact — 96.8% WR with 15m data on a single symbol screams data leakage from ensemble stacking on identical timestamps. The 11/11 daily-bar harness killed all ML-enhanced families for causal violation; this is the poster child for quarantine.

**Defense:** Rescue via intraday re-registration with strict temporal split — isolate the 15m slice to a shadow harness that enforces `EMITTER_WHITELIST_ENFORCE=1` for this strategy only. The ensemble stack can be decomposed into base learners; test each independently with walk-forward validation on n≥100 fresh ticks.

**Judge:** VERDICT **SHADOW** — test: Run 30-day intraday shadow with `EMITTER_WHITELIST_ENFORCE=1` for this strategy only; rescue if PF≥2.0 on n≥100 with no daily-bar causal leakage.

### CRYPTO rank 2: `ml_enhanced_BNBUSDT_15m_B_lightgbm`
**Prosecutor:** Same family as rank 1 — 89.5% WR on n=19 is statistically meaningless. The `B_lightgbm` variant shares feature engineering with the killed ensemble family. Registry shows `quan_engine/CRYPTO` as hardcoded toxic pair; this strategy is a vector for systemic contamination.

**Defense:** Mutation: replace LightGBM with XGBoost on the same feature set, add a volatility filter that kills trades during regime shifts (VIX > 25 for crypto proxy). Re-register as `xgboost_BNBUSDT_15m_B_volfilter` — new family, no causal baggage.

**Judge:** VERDICT **KILL** — test: If mutation cannot achieve PF≥1.5 on n≥50 within 30 days with 0 daily-bar overlap, permanently quarantine.

### CRYPTO rank 3: `ml_enhanced_INJUSDT_1d_B_lightgbm`
**Prosecutor:** 96.4% WR on n=28 with daily data is impossible without lookahead — the `1d` frequency means each trade is a full day prediction. The `B_lightgbm` suffix ties it to the killed family. Registry shows `pf_registry.json` dedup key would catch this if it were live; it's paper-only and should stay killed.

**Defense:** Isolate the daily slice as a regime-dependent strategy — only trade when INJUSDT is in a confirmed trend (ADX > 25). The 1d frequency actually reduces overfitting risk vs 15m. Re-register as `regime_trend_INJUSDT_1d` with `EMITTER_WHITELIST_ENFORCE=1` and a 20-trade minimum before any capital allocation.

**Judge:** VERDICT **SHADOW** — test: 30-day shadow with enforced whitelist; rescue if PF≥1.8 on n≥30 with no consecutive losing streaks >3.

### EQUITY rank 1: `multi_asset_copytrader`
**Prosecutor:** PF 0.912 on n=47 with 36.2% WR is below the 1.0 threshold — this strategy is destroying capital. The `multi_asset_copytrader` family is flagged as hardcoded toxic for EQUITY in `quan_engine/CRYPTO; cta_replicator/COMMODITY; multi_asset_copytrader/FOREX,EQUITY`. It's a known drag.

**Defense:** The copytrader can be rescued by restricting to SHORT-only signals during bear regimes (200-day MA below). The 0.912 PF is close to breakeven; a simple regime filter could push it above 1.2. Mutation: add `regime_terminal` as a gate — only copy trades when regime is confirmed bearish.

**Judge:** VERDICT **KILL** — test: If SHORT-only mutation cannot achieve PF≥1.2 on n≥30 within 30 days, permanently quarantine. Current form is toxic.

### EQUITY rank 2: `stocks_rsi2_pullback`
**Prosecutor:** n=2 is below the n≥5 minimum for any meaningful analysis. PF 0.750 on 2 trades is noise. The RSI2 strategy family is known for overfitting in equities (see AQR R3 review). This should be killed until n≥100.

**Defense:** The RSI2 pullback is a classic mean-reversion strategy that works in liquid equities. Rescue by expanding to the top 100 S&P 500 stocks by volume, not just the 2 tested. Re-register as `stocks_rsi2_pullback_v2` with `EMITTER_WHITELIST_ENFORCE=1` and a minimum of 50 symbols.

**Judge:** VERDICT **KILL** — test: If expanded version cannot achieve PF≥1.3 on n≥100 within 30 days, permanently quarantine. Current n=2 is insufficient.

### EQUITY rank 3: `auto_dna_mutation`
**Prosecutor:** n=1 with 0% WR and PF=0.000 — this is a failed experiment. The `auto_dna_mutation` family is a genetic algorithm that produces non-reproducible results. It should be killed and the family removed from `STRATEGY_FAMILIES` in `alpha_engine/config.py`.

**Defense:** The DNA mutation framework is designed for exploration, not production. Rescue by fixing the random seed and running 1000+ iterations with a fitness function that penalizes overfitting. The 0% WR on 1 trade is meaningless — the framework needs n≥100 to converge.

**Judge:** VERDICT **KILL** — test: If fixed-seed version cannot achieve PF≥1.0 on n≥100 within 30 days, permanently quarantine. Current form is non-reproducible.

### COMMODITY rank 1: `multi_asset_cot`
**Prosecutor:** PF 1.598 on n=58 with 58.6% WR is respectable but the COT (Commitment of Traders) data has a known 3-day reporting lag that creates a stale signal problem. The `cta_replicator` family is flagged as hardcoded toxic for COMMODITY. This strategy shares COT features with the killed family.

**Defense:** The COT strategy is fundamentally different from CTA replication — it's a positioning-based mean reversion, not a trend-following CTA. Rescue by adding a freshness filter: only trade if COT data is <5 days old. Re-register as `cot_positioning_v2` with `EMITTER_WHITELIST_ENFORCE=1`.

**Judge:** VERDICT **RESCUE** — test: 30-day live with freshness filter; rescue if PF≥1.3 on n≥30 with no stale data trades.

### COMMODITY rank 2: `multi_asset_copytrader`
**Prosecutor:** PF 1.124 on n=64 with 46.9% WR is barely above breakeven. The copytrader family is flagged as toxic for EQUITY and FOREX; it's likely toxic for COMMODITY too. The 1.124 PF is within the noise range for n=64.

**Defense:** The copytrader can be rescued by restricting to only copying trades from the `multi_asset_cot` strategy (rank 1). This creates a meta-strategy that only trades when COT signals align with copytrader signals. Mutation: add `cot_positioning` as a required co-signal.

**Judge:** VERDICT **SHADOW** — test: 30-day shadow with COT co-signal filter; rescue if PF≥1.3 on n≥30.

### COMMODITY rank 3: `cta_replicator`
**Prosecutor:** PF 0.283 on n=68 with 14.7% WR is catastrophic. This is the exact strategy family flagged as hardcoded toxic for COMMODITY in `quan_engine/CRYPTO; cta_replicator/COMMODITY`. It should be immediately killed and the family removed from all COMMODITY trading.

**Defense:** The CTA replicator can be rescued by inverting the signals — the 14.7% WR means it's consistently wrong, so flipping the sign would give 85.3% WR. Mutation: create `cta_replicator_inverse` that takes the opposite position of the original.

**Judge:** VERDICT **KILL** — test: If inverse version cannot achieve PF≥1.5 on n≥50 within 30 days, permanently quarantine. Original is toxic.

### ETF rank 1: `
### openrouter-inclusionai-ring-2-6-1t__meta_debate.md

# openrouter:inclusionai/ring-2.6-1t

elapsed=17.49s ok=True

# Meta-debate: Top-10 Strategies per Asset Class (v1) — Full Adjudication

> **Registry snapshot:** `2026-05-19T20:58:20Z` | **Canonical view:** `by_asset_class_policy_clean_net`  
> **Harness status:** `tools/edge_stability_harness.py` — 11/11 daily-bar causal **KILLED**  
> **Emitter gate:** `EMITTER_WHITELIST_ENFORCE=0` (shadow)

---

## A) Per-Class Debate — Ranks 1–3

### CRYPTO rank 1: `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`

**Prosecutor:** PF=60.545 on n=31 is a textbook overfit signature — no daily-bar strategy sustains PF>10 outside of microstructure regimes. The 11/11 harness killed all causal daily-bar hypotheses; this 15m ensemble likely shares the same causal leakage path through orderbook imbalance features. Quarantine manifest caps CRYPTO at 10% max_risk for exactly this reason. **Kill.**

**Defense:** DYDX USDT perpetual has structural microstructure edge (funding rate arbitrage, liquidation cascades) that *is* the alpha, not a statistical artifact. The ensemble_stack architecture (vs. single LightGBM) provides built-in model diversification. Rescue via: (1) isolate to perp-specific feature set only, (2) apply purged walk-forward CV with embargo=5d, (3) re-register under `alpha_engine/config.py::STRATEGY_FAMILIES` as a new sub-family `DYDX_PERP_MICRO` — not recycling the killed ML family.

**Judge:** VERDICT **SHADOW** — test: run `tools/edge_stability_harness.py` with `timeframe=15m symbol=DYDXUSDT regime_filter=vol_target` for 30 trading days; acceptance: PF≥3.0 AND n≥30 AND max_drawdown<8% AND no causal feature importance above 0.15 in SHAP audit. Fails any → hard kill.

---

### CRYPTO rank 2: `ml_enhanced_BNBUSDT_15m_B_lightgbm`

**Prosecutor:** PF=58.819 on n=19 — fewer than 3 weeks of 15m trades. BNB has extreme correlation to BTC regime; this is regime-snooping, not alpha. Hardcoded toxic pair `quan_engine/CRYPTO` applies. The 11/11 harness kill confirms the entire ML-enhanced family is contaminated. **Kill.**


### openrouter-qwen-qwen3-6-max-preview__meta_debate.md

# openrouter:qwen/qwen3.6-max-preview

elapsed=163.19s ok=False

openrouter error: IncompleteRead(4147 bytes read)


### xai-grok-3-latest__meta_debate.md

# xai:grok-3-latest

elapsed=22.97s ok=True

**A) Per asset class debate blocks (ranks 1–3 only)**

### CRYPTO rank 1: `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`
Prosecutor: n=31 with PF=60.545 is statistically invalid under 11/11 daily-bar kill; small-sample bias and CRYPTO toxic pair flag require permanent quarantine.  
Defense: Slice to 15m only, mutate ensemble weights, then intraday re-register under `alpha_engine/emitter_whitelist.py` without touching killed families.  
Judge: VERDICT SHADOW — test: 30-day paper run, target n≥100 clean, PF≥1.8, harness efficiency ≥0.65.

### CRYPTO rank 2: `ml_enhanced_BNBUSDT_15m_B_lightgbm`
Prosecutor: PF=58.819 on n=19 violates registry size caps and daily-bar causal kill; no rescue path exists without recycling.  
Defense: Isolate BNBUSDT 15m slice and apply lightgbm hyper-parameter mutation only.  
Judge: VERDICT KILL — test: none; remains in `quarantine_manifest.json`.

### CRYPTO rank 3: `ml_enhanced_INJUSDT_1d_B_lightgbm`
Prosecutor: 1d bar already killed by harness; PF=41.52 is spurious.  
Defense: Drop to 4h/1h intraday re-registration only.  
Judge: VERDICT SHADOW — test: 30-day paper, n≥80, PF≥1.6 on clean holdout.

### EQUITY rank 1: `multi_asset_copytrader`
Prosecutor: PF=0.912 on n=47 fails PF≥1.2 and EQUITY max_risk 25% policy; toxic pair flag active.  
Defense: Mutation to equity-only slice with new hypothesis required.  
Judge: VERDICT KILL — test: none.

### EQUITY rank 2: `stocks_rsi2_pullback`
Prosecutor: n=2 renders any metric meaningless under registry rules.  
Defense: Requires entirely new hypothesis.  
Judge: VERDICT KILL.

### EQUITY rank 3: `auto_dna_mutation`
Prosecutor: n=1, PF=0.000; zero information.  
Defense: Not salvageable.  
Judge: VERDICT KILL.

### COMMODITY rank 1: `multi_asset_cot`
Prosecutor: PF=1.598 on n=58 passes basic threshold but remains CT=F factor-beta sleeve per AQR review.  
Defense: Keep as sleeve only, cap at 25% risk, no alpha claim.  
Judge: VERDICT SHADOW — test: 30-day paper, PF≥1.4, n≥100.

### COMMODITY rank 2: `multi_asset_copytrader`
Prosecutor: PF=1.124 below rescue bar and toxic pair flag.  
Defense: Not viable without new hypothesis.  
Judge: VERDICT KILL.

### COMMODITY rank 3: `cta_replicator`
Prosecutor: PF=0.283 on n=68; class-blocked.  
Defense: Irredeemable.  
Judge: VERDICT KILL.

### ETF rank 1: `etf_all_strategies`
Prosecutor: n=1, PF=0.000; emission audit pending.  
Defense: Requires new hypothesis.  
Judge: VERDICT KILL.

### ETF rank 2: `etf_scanner`
Prosecutor: n=1, insufficient.  
Defense: Not salvageable.  
Judge: VERDICT KILL.

### FOREX rank 1: `cta_replicator`
Prosecutor: PF=2.514 on n=109 but FOREX max_risk=0% and SHORT-only rehab not yet cleared.  
Defense: Isolate SHORT-only slice and re-register after hedge_fund_sprint sign-off.  
Judge: VERDICT SHADOW — test: 30-day paper, PF≥1.5, WR≥52%, n≥150.

### FOREX rank 2: `combined_confidence_strategy`
Prosecutor: PF=1.057 borderline and n=15 too low.  
Defense: Needs mutation + larger n.  
Judge: VERDICT KILL.

### FOREX rank 3: `alpha_engine`
Prosecutor: PF=0.594, toxic.  
Defense: Not viable.  
Judge: VERDICT KILL.

### BOND rank 1: `bond_scanner`
Prosecutor: n=4, PF=0.000; sub-floor.  
Defense: Requires new hypothesis post-FRED fix.  
Judge: VERDICT KILL.

### BOND rank 2: `cta_replicator`
Prosecutor: n=1, zero value.  
Defense: Not salvageable.  
Judge: VERDICT KILL.

**B) Meta-prompt recommendations**

| meta_id | when_to_use | inject_variables | success_signal |
|---------|-------------|------------------|----------------|
| META_DEBATE_PER_CLASS_v1 | cloud rescue debate | `pf_registry.json`, class, rank, n, PF | Judge verdict + 30-day test defined |
| STRATEGY_HARVEST_EXECUTE_v1 | local P0 wire | `quarantine_manifest.json`, strategy, slice | wire_targets emitted, acceptance tests pass |
| EDGE_STABILITY_RETEST_v1 | post-mutation harness | `tools/edge_stability_harness.py`, 30-day window | harness efficiency ≥0.65, n≥100 clean |
| EMITTER_WHITELIST_FLIP_v1 | enforce=1 decision | `alpha_engine/emitter_whitelist.py`, class | no toxic pair violations, PF≥1.5 |
| CROSS_CLASS_SYNTHESIS_v1 | weekly registry review | all class policy_clean_net rows | updated rescue candidates + flip flags |

**C) Cross-class synthesis**

| Class | Best rescue strategy (from table) | Worst drag strategy | Flip enforce whitelist? (Y/N + why) |
|-------|-----------------------------------|---------------------|-------------------------------------|
| CRYPTO | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | `ml_enhanced_BNBUSDT_15m_B_lightgbm` | Y — after 30-day shadow PF≥1.8 |
| EQUITY | none | `multi_asset_copytrader` | N — no candidates meet bar |
| COMMODITY | `multi_asset_cot` | `cta_replicator` | N — sleeve only, keep enforce=0 |
| ETF | none | `etf_all_strategies` | N — emission audit pending |
| FOREX | `cta_replicator` | `multi_asset_copytrader` | Y — SHORT-only slice after rehab |
| BOND | none | `bond_scanner` | N — n too low |

**D) Top 5 information-gain questions**

1. Does `ml_enhanced_INJUSDT_1d_B_lightgbm` retain PF>1.6 when restricted to 4h bars only on the next 30-day out-of-sample window?
2. What is the exact n threshold at which `multi_asset_cot` COMMODITY sleeve transitions from factor-beta to alpha under AQR R3 crowding metric?
3. Can `cta_replicator` FOREX SHORT-only mutation clear PF≥1.5 and WR≥52% after hedge_fund_sprint rehab on n≥150?
4. How much does `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` PF degrade when ensemble weights are frozen versus re-optimized daily?
5. What is the incremental PF lift, if any, when `bond_scanner` is re-run post-FRED fix on n≥50 BOND instruments?


## Local execute (`20260519T223720Z`)

### ollama-mistral-nemo-latest__strategy_harvest.md

# ollama:mistral-nemo:latest

elapsed=14.17s ok=True

Based on the provided adjudication, here are the deliverables:

### 1) Per-class action table

| Class | Strategy to SIZE UP | Strategy to CAP/KILL | hypothesis_id | wire_target file:function | 7-day command |
|-------|----------------------|----------------------|---------------|---------------------------|---------------|
| CRYPTO | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | `ml_enhanced_BNBUSDT_15m_B_lightgbm` | HYP_CRYPTO_DYDX_ENSEMBLE | `tools/edge_stability_harness.py`:DYDXUSDT, 15m, ensemble_stack | `python tools/edge_stability_harness.py --timeframe=15m --symbol=DYDXUSDT --regime_filter=vol_target` |
| FOREX | `cta_replicator` (SHORT-only) | None | HYP_FOREX_CTA_SHORT | `tools/edge_stability_harness.py`:CTA, SHORT-only, FOREX | `python tools/edge_stability_harness.py --timeframe=daily --symbol=EURUSD --regime_filter=cta_short` |
| COMMODITY | `multi_asset_cot` | `cta_replicator` | HYP_COMMOD_COT | `tools/edge_stability_harness.py`:COMMOD, COT, daily | `python tools/edge_stability_harness.py --timeframe=daily --symbol=GOLD --regime_filter=cot` |
| ETF | None | `etf_all_strategies` | HYP_ETF_ALL_STRATS | `tools/emitter_audit.py`:ETF, all_strats | `python tools/emitter_audit.py --class=ETF --strategy=all_strats` |

### 2) Three P0 PRs (smallest diff)

1. **Title:** Implement DYDXUSDT ensemble_stack harness
   - Files: `tools/edge_stability_harness.py`, `alpha_engine/config.py`
   - Acceptance test: PF≥3.0, n≥30, max_drawdown<8% after 30-day shadow trading.
   - Class rescued: CRYPTO

2. **

### ollama-qwen2-5-coder-14b-instruct-q4-k-m__strategy_harvest.md

# ollama:qwen2.5-coder:14b-instruct-q4_K_M

elapsed=26.23s ok=True

## Per-class Action Table

| Class | Strategy to SIZE UP | Strategy to CAP/KILL | hypothesis_id | wire_target file:function | 7-day command |
|-------|----------------------|----------------------|---------------|---------------------------|---------------|
| CRYPTO | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | `ml_enhanced_BNBUSDT_15m_B_lightgbm` | crypto_hypothesis_01 | `alpha_engine/config.py::STRATEGY_FAMILIES` | `tools/edge_stability_harness.py --timeframe=15m --symbol=DYDXUSDT --regime_filter=vol_target` |
| EQUITY | none | `multi_asset_copytrader` | equity_hypothesis_02 | `alpha_engine/emitter_whitelist.py::CLASS_BLOCKED` | `audit_trail/strategy_audit.py --class=EQUITY --strategy=multi_asset_copytrader` |
| COMMODITY | `multi_asset_cot` | `cta_replicator` | commodity_hypothesis_03 | `alpha_engine/config.py::STRATEGY_FAMILIES` | `tools/edge_stability_harness.py --timeframe=daily --symbol=COMMODITY --regime_filter=factor_beta` |
| ETF | none | `etf_all_strategies` | etf_hypothesis_04 | `audit_trail/emission_audit.py::EMISSION_AUDIT_PENDING` | `audit_trail/strategy_audit.py --class=ETF --strategy=etf_all_strategies` |
| FOREX | `cta_replicator` | `multi_asset_copytrader` | forex_hypothesis_05 | `alpha_engine/config.py::STRATEGY_FAMILIES` | `tools/edge_stability_harness.py --timeframe=daily --symbol=FOREX --regime_filter=hedge_fund_sprint` |
| BOND | none | `bond_scanner` | bond_hypothesis_06 | `audit_trail/emission_audit.py::EMISSION_AUDIT_PENDING` | `audit_trail/strategy_audit.py --class=BOND --strategy=bond_scanner` |

## Three P0 PRs

### 1) CRYPTO: Shadow Test for DYDXUSDT Ensemble Stack
**Title:** Implement shadow test for `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`
**Files:** 
- `alpha_engine/config.py`
- `tools/edge_stability_harness.py`
- `.github/workflows/audit-dashboard.yml`

**Acceptance Test:** PF≥3.0 AND n≥30 AND max_drawdown<8% AND no causal feature importance above 0.15 in SHAP audit.

### 2) COMMODITY: Register `multi_asset_cot` as Best Rescue Strategy
**Title:** Register `multi_asset_cot` as best rescue strategy for COMMODITY class
**Files:** 
- `alpha_engine/config.py`
- `audit_trail/strategy_audit.py`

**Acceptance Test:** PF≥1.5 AND n≥30 AND max_drawdown<8%.

### 3) FOREX: Implement SHORT-only Slice for CTA Replicator
**Title:** Implement SHORT-only slice for `cta_replicator` in FOREX class
**Files:** 
- `alpha_engine/config.py`
- `tools/edge_stability_harness.py`

**Acceptance Test:** PF≥1.5 AND WR≥52% AND n≥150.

## Meta-prompt Calibration

| Meta-prompt | Run on Ollama 14B | Run on Cloud Ring/DeepSeek |
|-------------|------------------|----------------------------|
| META_DEBATE_PER_CLASS_v1 | Yes | No |
| STRATEGY_HARVEST_EXECUTE_v1 | No | Yes |
| EDGE_STABILITY_RETEST_v1 | Yes | No |
| EMITTER_WHITELIST_FLIP_v1 | No | Yes |
| CROSS_CLASS_SYNTHESIS_v1 | No | Yes |

## Honest Freeze List

- **Classes to STOP new emissions for 90 days:**
  - EQUITY
  - ETF
  - BOND

- **Classes to CONTINUE paper harvest:**

### ollama-qwen3-14b__strategy_harvest.md

# ollama:qwen3:14b

elapsed=21.88s ok=True

### **1) Per-Class Action Table**

| Class     | Strategy to SIZE UP                                      | Strategy to CAP/KILL                                 | hypothesis_id                          | wire_target file:function                                      | 7-day command                                                                 |
|-----------|----------------------------------------------------------|-------------------------------------------------------|----------------------------------------|------------------------------------------------------------------|-------------------------------------------------------------------------------|
| **CRYPTO** | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`              | `ml_enhanced_BNBUSDT_15m_B_lightgbm`                  | `DYDX_PERP_MICRO`                      | `alpha_engine/emitter_whitelist.py::add_strategy_family`         | Run `tools/edge_stability_harness.py` with `timeframe=15m symbol=DYDXUSDT`     |
| **COMMODITY** | `multi_asset_cot`                                       | `cta_replicator`                                     | `COMMODITY_COT_MICRO`                  | `audit_trail/strategy_slicing.py::sleeve_commodity_cot`           | Apply purged walk-forward CV with `embargo=5d` and re-register under `COMMODITY_COT_MICRO` |
| **FOREX**  | `cta_replicator` (SHORT-only mutation)                   | `multi_asset_copytrader`                                | `FOREX_SHORT_ONLY`                     | `


## How to proceed next (operator)

1. `python tools/build_top10_strategies_per_class.py` after each dashboard deploy
2. Flip `EMITTER_WHITELIST_ENFORCE=1` only for classes where Judge verdict=RESCUE on rank1-3
3. Pre-register tick/intraday hypotheses (CRYPTO) — not daily-bar killed families
4. Re-run: `python tools/strategy_harvest_round.py --phase all`
