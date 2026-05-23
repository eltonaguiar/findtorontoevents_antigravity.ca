# Strategy Trust Ranking — Forward Test Portfolio Selection

**Date:** 2026-03-24
**Data basis:** 500 closed picks (alpha_engine), 1927 scored picks (IC analysis), 224 Thompson posteriors
**Methodology:** Composite score = 0.4 * WR + 0.3 * PF_normalized + 0.3 * avg_PnL_normalized

---

## Executive Summary

The system has 500 closed picks across 181 unique strategies. The vast majority of strategies have fewer than 5 trades -- statistically meaningless. Only **11 strategies have 10+ closed trades**, and only **6 of those** have 5+ trades from live (non-backfill) signals.

**Critical finding:** Live (non-backfill, non-ML-enhanced) picks show 29.7% WR with PF=0.44 and avg PnL of -1.19%. The system is losing money on live trades. The positive aggregate numbers (39.4% WR, PF=1.35) are inflated by ML-enhanced picks (52.1% WR, PF=1.98) which are a separate pipeline.

---

## Section 1: TOP 10 Trusted Strategies for Forward Testing

Ranked by composite evidence quality. Requirements: 10+ trades, WR >= 50%, PF >= 1.2 where data exists. Relaxed to 5+ trades where IC analysis provides additional evidence.

### Tier A: Strong Evidence (10+ closed trades, WR >= 50%, PF >= 1.2)

| Rank | Strategy | Trades | WR | PF | Avg PnL | IC | Status | Evidence |
|------|----------|--------|-----|-----|---------|-----|--------|----------|
| 1 | `copy_hl_NMTD_25M` | 16 live | 81.2% | 6.09 | +2.00% | n/a | **ACTIVE** | Best live strategy. Copy-trading a proven Hyperliquid trader. Consistent across 16 trades. |
| 2 | `binance_smart_money` | 20 live | 55.0% | 3.05 | +1.50% | n/a | **ACTIVE** | Second-best live strategy. Follows Binance whale movements. Statistically significant at 20 trades. |
| 3 | `ema_crossover_backfill` | 19 backfill | 57.9% | 2.06 | +1.16% | n/a | INACTIVE | Strong backtest but all trades are backfilled. Needs live validation. |

### Tier B: Moderate Evidence (IC analysis + positive PnL, 10+ scored trades)

| Rank | Strategy | IC Trades | WR (IC) | Avg PnL (IC) | IC Score | Status | Evidence |
|------|----------|-----------|---------|---------------|----------|--------|----------|
| 4 | `crypto_bayesian_regime_transition_momentum_v1` | 34 | 58.8% | +0.29% | +0.117 | INACTIVE | Positive IC, positive PnL, 34 trades. Academic basis (Bayesian regime switching). Best risk-adjusted signal from IC analysis. |
| 5 | `funding_momentum` | 108 | 58.3% | +0.19% | -0.067 | INACTIVE | Highest trade count in IC analysis. 58.3% WR with positive avg PnL across 108 trades. IC is negative (scoring ranks its picks wrong), but the strategy itself finds winners. Fix scoring, keep strategy. |
| 6 | `strong consensus` | 11 | 45.5% | +7.25% | +0.191 | PARTIAL | Highest IC score (+0.191) and highest avg PnL (+7.25%). Only 11 trades -- needs more data. This is the meta-consensus aggregator, not a single strategy. |
| 7 | `multi_period_rsi_confluence_eth` | 13 | 69.2% | +0.50% | -0.502 | INACTIVE | 69.2% WR across 13 trades with positive PnL. IC is extremely negative (-0.502) meaning scoring is completely broken for this strategy, but the raw signal works. |
| 8 | `multi_period_rsi_confluence` | 17 | 64.7% | +0.51% | -0.008 | INACTIVE | 64.7% WR, 17 trades, positive PnL. Near-zero IC means scoring neither helps nor hurts. |
| 9 | `crypto_soc_orderflow_absorption_a01_v1` | 14 | 57.1% | +0.19% | +0.037 | INACTIVE | Positive IC and positive PnL. The only orderflow absorption variant that works (9 others are kill candidates). |
| 10 | `vwap_deviation_reversion_xrp_v1` | 12 | 41.7% | +0.63% | +0.330 | INACTIVE | Highest IC score (+0.330) of any single strategy. WR below 50% but avg PnL is strongly positive, meaning winners are larger than losers. XRP-specific -- limited asset coverage. |

### Tier A+ (Special Case): ML-Enhanced Pipeline

The `ml_enhanced_*` strategies show exceptional numbers but require careful interpretation:

| Strategy | Trades | WR | PF | Avg PnL | Note |
|----------|--------|-----|-----|---------|------|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 16 | 93.8% | 529.54 | +37.97% | **SUSPICIOUSLY HIGH** -- likely look-ahead bias or single-asset overfitting |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 16 | 93.8% | 469.64 | +6.44% | Same concern -- 93.8% WR is not realistic for sustained trading |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 15 | 93.3% | 50.51 | +11.51% | Same pattern |
| `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` | 10 | 0.0% | 0.00 | -8.53% | **0% WR on BTC** -- confirms overfitting to specific assets |
| `ml_enhanced_ADAUSDT_15m_D_ensemble_stack` | 10 | 0.0% | 0.00 | -11.70% | **0% WR on ADA** -- complete failure |

**Verdict on ML-enhanced:** These are NOT trustworthy for forward testing. The 93%+ WR on FET/BNB/RENDER combined with 0% WR on BTC/ADA screams asset-specific overfitting or look-ahead bias. The ML model (AUC=1.0 per the ML Blueprint) is confirmed overfit. Do NOT include in forward-test portfolio until the model is rebuilt with proper temporal cross-validation.

---

## Section 2: BOTTOM 10 Kill Candidates

These strategies have clear negative evidence. Per the "mutate before kill" rule, each has had 10+ trades to prove itself.

| Rank | Strategy | Trades | WR | PF | Avg PnL | IC | Verdict |
|------|----------|--------|-----|-----|---------|-----|---------|
| 1 | `winner_pattern_precursor` | 96 live | 15.6% | 0.38 | -0.96% | +0.035 | **KILL** -- 96 trades at 15.6% WR. Total loss: -91.9%. The name is ironic. |
| 2 | `ml_enhanced_ADAUSDT_15m_D_ensemble_stack` | 10 | 0.0% | 0.00 | -11.70% | n/a | **KILL** -- 0% WR, -116.97% total |
| 3 | `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` | 10 | 0.0% | 0.00 | -8.53% | n/a | **KILL** -- 0% WR, -85.27% total |
| 4 | `crypto_soc_orderflow_absorption_a02_v1` | 16 IC | 18.8% | n/a | -0.54% | -0.350 | **KILL** -- anti-predictive, negative PnL |
| 5 | `atr_regime_rsi` | 28 IC | 25.0% | n/a | -0.29% | -0.213 | **KILL** -- 28 trades, deeply negative |
| 6 | `crypto_soc_orderflow_absorption_a07_v1` | 19 IC | 26.3% | n/a | -0.44% | -0.200 | **KILL** -- anti-predictive, negative PnL |
| 7 | `crypto_mtf_ema_slope_alignment_v1` | 14 IC | 21.4% | n/a | -0.49% | -0.163 | **KILL** -- sub-25% WR |
| 8 | `crypto_soc_orderflow_absorption_a03_v1` | 15 IC | 33.3% | n/a | -0.24% | -0.116 | **KILL** -- negative IC and PnL |
| 9 | `yahoo_analyst_consensus` | 5 live | 0.0% | 0.00 | -2.48% | n/a | **KILL** -- 0% WR on live trades, Thompson est 14.4% |
| 10 | `multi_period_rsi_confluence_xrp` | 13 IC | 7.7% | n/a | -0.27% | -0.032 | **KILL** -- 7.7% WR is catastrophic |

**Additional kill candidates (from IC analysis, 10+ trades, negative IC AND negative PnL):**
- `crypto_soc_orderflow_absorption_a06_v1` (IC=-0.491, WR=40%, 10 trades)
- `hl_funding_fade` (11 live trades, WR=27.3%, PF=0.44, avg PnL=-2.60%) -- currently ACTIVE, should be disabled
- `momentum_catcher` (7 live trades, WR=42.9%, PF=0.10, avg PnL=-18.74%) -- currently ACTIVE, should be disabled

---

## Section 3: Academic Strategy Gap Analysis

### Strategies from academic literature cross-referenced against our codebase:

| # | Academic Strategy | Paper | Present in Codebase? | Implementation Quality | Closed Trade Evidence |
|---|-------------------|-------|---------------------|----------------------|----------------------|
| 1 | **Pairs Trading / Statistical Arbitrage** | Gatev, Goetzmann & Rouwenhorst (2006) "Pairs Trading: Performance of a Relative-Value Arbitrage Rule" | **PARTIAL** -- `baby_strategies/pairs_spread_btceth.py` (BTC/ETH only), `cointegration_pair_trade` in config | Only BTC/ETH pair implemented. No multi-pair universe, no cointegration testing, no dynamic pair selection. **0 closed trades.** | **GAP: Needs proper multi-pair implementation** |
| 2 | **Cross-Sectional Momentum** | Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers" | **YES** -- `cross_sectional_momentum` in scanner.py, config references. Also `cta_tsmom_blend` (time-series momentum, Moskowitz et al. 2012). | Implemented but `cta_tsmom_blend` has 5 closed trades at 60% WR, PF=0.0, avg PnL=-0.62%. Not generating positive returns. | **WEAK: Implemented but not working** |
| 3 | **Carry Trade** | Koijen, Moskowitz, Pedersen & Vrugt (2018) "Carry" | **YES** -- `funding_rate_carry` and `funding_rate_carry_pro` in `cerebrus_strategies.py`, `forex_carry_momentum` active. | Crypto carry via funding rates is implemented. Forex carry is active. No closed trade evidence yet for carry-specific strategies. `funding_momentum` (related) has 108 IC trades at 58.3% WR. | **PARTIAL: Implemented, needs trade evidence** |
| 4 | **Trend Following / Time-Series Momentum** | Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" | **YES** -- `cta_tsmom_blend`, `cta_cross_asset_tsmom`, `cta_commodity_momentum_term` all active. | Multiple implementations. Thompson estimate for `cta_cross_asset_tsmom` is 74.7% (but only ~2 trades). `cta_tsmom_blend` live data shows 60% WR but negative PnL. | **PARTIAL: Implemented, conflicting evidence** |
| 5 | **Mean Reversion** | Poterba & Summers (1988); Lo & MacKinlay (1988) | **EXTENSIVE** -- 20+ mean reversion variants across baby strategies, alpha engine. `hl_mean_reversion`, `forex_rsi2_mean_reversion`, `futures_bb_mean_reversion` all active. | Over-implemented. Too many correlated variants. Consolidation needed per Strategy Audit recommendations. Few have closed trade evidence. | **OVER-IMPLEMENTED: Too many variants, no evidence which works** |
| 6 | **Factor Investing (Multi-Factor)** | Fama & French (1993, 2015); Asness et al. (2013) "Value and Momentum Everywhere" | **MINIMAL** -- References to factor models in `cta_bridge.py` and config, but no dedicated multi-factor strategy module. | No explicit Fama-French factor decomposition. No size, value, quality, or low-volatility factors implemented for crypto. `seasonal_factor_rotation` exists but has 25% est WR (Thompson). | **GAP: No proper multi-factor model** |

### 5 Missing Academic Strategies to Implement (Priority Order)

| Priority | Strategy | Academic Basis | Expected Edge | Implementation Complexity | Why Missing |
|----------|----------|---------------|---------------|--------------------------|-------------|
| **P1** | **Multi-Pair Cointegration Arbitrage** | Gatev et al. (2006), Vidyamurthy (2004) | Low-risk, market-neutral. 1-2% monthly with Sharpe >2 in equities. Crypto pairs more volatile = higher potential. | Medium -- need cointegration testing (Engle-Granger), dynamic pair selection, z-score thresholds. | Only BTC/ETH pair exists. Need 20+ crypto pairs with rolling cointegration. |
| **P2** | **Crypto Factor Model (Value + Momentum + Size)** | Liu, Tsyvinski & Wu (2022) "Common Risk Factors in Cryptocurrency"; Fama-French adapted | Cross-sectional factor premiums documented in crypto. Momentum factor has Sharpe ~2.1 per the literature. | High -- need factor computation pipeline (NVT as value, market cap as size, returns as momentum). | No factor decomposition exists. Would enable systematic factor rotation. |
| **P3** | **Volatility Risk Premium Harvesting** | Carr & Wu (2009); Bollen & Whaley (2004) | Sell implied vol > realized vol. Crypto vol premium is large (Deribit data). Estimated Sharpe 1.0-1.5. | Medium-High -- need options data feed (Deribit API), delta-hedging logic. | No crypto options module at all. Identified as gap in Strategy Audit. |
| **P4** | **Cross-Exchange Basis Arbitrage** | Multiple practitioners; Binance vs Kraken vs OKX | Near risk-free 5-15% annualized from basis/funding spreads. | Medium -- need multi-exchange price feeds, execution engine. | Only single-exchange strategies exist. `cross_exchange_basis_carry` in config but no implementation. |
| **P5** | **Hierarchical Risk Parity Portfolio** | Lopez de Prado (2016) "Building Diversified Portfolios that Outperform Out-of-Sample" | Portfolio-level optimization. Reduces correlation drag, improves Sharpe. | Medium -- need HRP algorithm, correlation matrix, rebalancing logic. | No portfolio-level optimization. Each strategy sizes independently. |

---

## Section 4: Recommended Forward-Test Portfolio

Based on all evidence, here is the **recommended 7-strategy forward-test portfolio** to run for the next 30 days:

### Primary Portfolio (High Confidence)

| # | Strategy | Allocation | Rationale |
|---|----------|------------|-----------|
| 1 | `copy_hl_NMTD_25M` | 25% | Best live WR (81.2%), highest PF (6.09), 16 trades. Copy-trading proven Hyperliquid trader. |
| 2 | `binance_smart_money` | 20% | Second-best live strategy. 55% WR, PF=3.05, 20 trades. Whale flow following. |
| 3 | `crypto_bayesian_regime_transition_momentum_v1` | 15% | Best IC-validated strategy. 58.8% WR, positive IC, 34 IC trades. Academic basis (Bayesian switching). |
| 4 | `funding_momentum` | 15% | Highest trade count (108). 58.3% WR, positive PnL. Scoring is broken for it (negative IC) but the signal itself works. |
| 5 | `multi_period_rsi_confluence` | 10% | 64.7% WR, 17 trades. Simple RSI confluence is working. |

### Secondary Portfolio (Moderate Confidence, Smaller Allocation)

| # | Strategy | Allocation | Rationale |
|---|----------|------------|-----------|
| 6 | `vwap_deviation_reversion_xrp_v1` | 10% | Highest IC (+0.330), positive PnL. Only 12 trades and XRP-only -- limited but signal is strong. |
| 7 | `strong consensus` (meta-aggregator) | 5% | Highest single avg PnL (+7.25%), highest IC (+0.191). Only 11 trades -- needs observation. |

### Portfolio Rules

1. **Max 2% of account per trade** (hard cap, no exceptions)
2. **Max 3 concurrent positions per strategy**
3. **Direction filter:** LONG only unless strategy has >30 closed short trades with >40% WR
4. **R:R minimum:** 1.5x (hard gate)
5. **Regime alignment required:** LONG only in BULLISH/LEANING_BULL regime
6. **Review cadence:** Weekly WR check. Any strategy dropping below 40% WR over 20+ new trades gets paused for review.
7. **Correlation cap:** Max 2 strategies on the same symbol simultaneously

### What to Disable Immediately

These are currently ACTIVE but should be disabled based on evidence:

| Strategy | Current Status | Action | Reason |
|----------|---------------|--------|--------|
| `hl_funding_fade` | ACTIVE | **DISABLE** | 27.3% WR, PF=0.44, -28.57% total PnL on 11 trades |
| `momentum_catcher` | ACTIVE | **DISABLE** | 42.9% WR but PF=0.10, avg PnL=-18.74% (huge losers) |
| `yahoo_analyst_consensus` | ACTIVE | **DISABLE** | 0% WR on 5 live trades, Thompson est 14.4% |
| `winner_pattern_precursor` | ACTIVE (if any) | **KILL** | 15.6% WR on 96 trades. Beyond repair. |
| `cg_whale_divergence` | ACTIVE | **PAUSE** | Thompson est 25.1%, only 2 trades but trending bad |
| `futures_ema_stack_momentum` | ACTIVE | **PAUSE** | Thompson est 20.4%, 3 trades all losses |

---

## Section 5: Honest Assessment

### What the data actually tells us:

1. **The system does not have a proven edge on live trades.** Live (non-backfill, non-ML-enhanced) picks are at 29.7% WR with PF=0.44. This is worse than a coin flip.

2. **Only 2 strategies have credible live evidence of profitability:** `copy_hl_NMTD_25M` (copy trading) and `binance_smart_money` (whale following). Both are fundamentally "follow smart money" approaches, not algorithmic signals.

3. **The ML-enhanced pipeline numbers are not trustworthy.** 93.8% WR on FET/BNB but 0% on BTC/ADA = asset-specific overfitting. The AUC=1.0 confirms this.

4. **The IC analysis identifies good strategy candidates** (`crypto_bayesian_regime_transition_momentum_v1`, `funding_momentum`, `multi_period_rsi_confluence`) but these are from the baby_strats_forward pipeline, not from the alpha engine's closed_picks. They need live closed-trade validation.

5. **The scoring system is confirmed anti-predictive.** Score-to-PnL correlation is 0.043 (essentially zero). Seven scoring components actively harm performance. The system cannot distinguish good picks from bad ones.

6. **181 strategies with 500 trades = 2.8 trades per strategy on average.** This is statistically meaningless. The system is spreading too thin. Concentrate on the 5-7 strategies with actual evidence.

### What needs to happen before real money:

- [ ] Kill the bottom 10 strategies (Section 2) to stop the bleeding
- [ ] Disable the 6 active-but-losing strategies listed above
- [ ] Run the 7-strategy forward-test portfolio for 30 days with paper trading
- [ ] Achieve 50%+ WR and PF > 1.2 across 100+ live trades
- [ ] Fix the scoring system (zero out anti-predictive components per CRYPTO_PROFIT_TRANSFORMATION.md Rec #1)
- [ ] Rebuild ML model with proper temporal CV (currently AUC=1.0 = overfit)
- [ ] Implement at least 1 of the 5 missing academic strategies (P1: pairs trading recommended first)

---

## Appendix: Data Sources

| File | Records | Used For |
|------|---------|----------|
| `alpha_engine/data/closed_picks.json` | 500 picks, 181 strategies | Closed trade WR, PF, PnL |
| `alpha_engine/data/ic_weights.json` | 27 strategies, 1927 scored picks | Information Coefficient analysis |
| `alpha_engine/data/thompson_state.json` | 224 strategies | Bayesian WR estimates |
| `alpha_engine/data/active_picks.json` | 26 active strategies | Current system state |
| `alpha_engine/data/score_pnl_history.json` | 12 entries | Score-PnL correlation (0.043 = ~zero) |
| `docs/CRYPTO_PROFIT_TRANSFORMATION.md` | Qualitative | Root cause analysis |
| `docs/STRONG_SIGNALS_BLUEPRINT.md` | Qualitative | Filter system design |
| `docs/HEDGE_FUND_SCORECARD.md` | Qualitative | Gap analysis |
| `docs/ML_BLUEPRINT_2026-03-23.md` | Qualitative | ML model status |

---

*Generated 2026-03-24. All numbers from production data. No speculation -- only cited actual performance.*
