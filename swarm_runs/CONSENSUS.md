# Asset-Class Methodology Consensus (DeepSeek + xAI)

Briefing: `swarm_runs/briefing_asset_class_audit.md`
Source probes: `swarm_runs/20260503T132558Z/probe.{deepseek,xai}.json`

Confidence: DeepSeek=MEDIUM; xAI=MEDIUM

## Q1 — Best statistically-proven approach per class

### EQUITY

| field | DeepSeek | xAI |
|---|---|---|
| approach | Factor-mimicking portfolio (Fama-French 5-factor + momentum) with daily rebalancing and volatility scaling | Factor-based momentum with volatility adjustment |
| edge_mechanism | Systematic capture of size, value, profitability, investment, and momentum premia documented over 60+ years; microstructure edge from limit-order book imbalance at 1-min frequency | Mispricing from behavioral biases in momentum and low-vol factors |
| test | Deflated Sharpe Ratio (DSR) with n>=200 trades; Wilson 50% LB on WR > 55% | Wilson LB on WR >50% and PSR on PF >1.5 |
| min_n | 200 | 100 |
| external_benchmark | AQR Equity Market Neutral fund; Ken French data library | AQR Momentum Fund (AMOMX) and Renaissance Medallion factor studies |
| kill_rule | If DSR < 0.5 or rolling 3-month PF < 1.0 over 100 trades, halt and mutate factor weights | Abandon if PF <1.0 or WR <45% over n=200 trades |

### CRYPTO

| field | DeepSeek | xAI |
|---|---|---|
| approach | Regime-switching momentum + basis trade (perpetual futures basis vs spot) with volatility gating | Sentiment-driven contrarian with on-chain volume filter |
| edge_mechanism | Microstructure: persistent basis deviations due to retail flow asymmetry; sentiment regime captured by fear-greed index (proven 4.22 PF on 96 trades) | Overreaction to social sentiment spikes, validated by on-chain liquidity shifts |
| test | Wilson 50% LB on WR > 60% with n>=50; PSR > 2.0 | Wilson LB on WR >55% and SPA on PF >2.0 |
| min_n | 50 | 150 |
| external_benchmark | Hyperliquid HLP index; CoinDesk Trend Indicator | Hyperliquid HLP and BitMEX funding rate arbitrage studies |
| kill_rule | If basis spread < 0.1% for 30 consecutive days or WR drops below 50% on 50-trade rolling window | Abandon if PF <1.5 or WR <50% over n=300 trades |

### FOREX

| field | DeepSeek | xAI |
|---|---|---|
| approach | Carry-to-volatility ratio (G10 pairs only) with trend filter from COT commercial positioning | Carry trade with interest rate differential and volatility gate |
| edge_mechanism | Term-structure: interest rate differentials predict 60% of 3-month moves; COT commercial hedging flows reveal smart-money positioning | Term-structure edge from persistent rate differentials, filtered by low-vol regimes |
| test | Wilson 50% LB on WR > 55% with n>=200; SPA p-value < 0.05 vs random entry | Wilson LB on WR >50% and DSR on PF >1.5 |
| min_n | 200 | 100 |
| external_benchmark | MyFXBook verified public track records; Deutsche Bank FX Factor indices | MyFXBook verified carry strategies and Barclays FX Carry Index |
| kill_rule | If rolling 6-month Sharpe < 0.0 or WR < 45% over 100 trades, abandon G10 and switch to EM carry only | Abandon if PF <1.0 or WR <45% over n=200 trades |

### COMMODITY

| field | DeepSeek | xAI |
|---|---|---|
| approach | Term-structure roll yield (backwardation/contango) + COT commercial net positioning | Trend-following with CFTC COT commercial positioning filter |
| edge_mechanism | Commodity futures term structure predicts 70% of spot returns over 1-month horizon; commercial hedgers have information advantage over speculators | Microstructure edge from commercial hedger signals anticipating supply/demand shifts |
| test | Wilson 50% LB on WR > 55% with n>=100; DSR > 1.0 | Wilson LB on WR >50% and PSR on PF >1.5 |
| min_n | 100 | 50 |
| external_benchmark | DBMF (iMGP DBi Managed Futures); KMLM (KFA Mount Lucas) | DBMF (iMGP DBi Managed Futures Strategy ETF) |
| kill_rule | If 3-month rolling PF < 1.2 or WR < 50% over 50 trades, freeze allocation | Abandon if PF <1.2 or WR <45% over n=100 trades |

### ETF

| field | DeepSeek | xAI |
|---|---|---|
| approach | Sector rotation based on relative strength (12-month momentum) with volatility parity weighting | Mean-reversion on sector rotation with liquidity filter |
| edge_mechanism | Cross-sectional momentum across 10 US sectors persists 3-12 months; volatility parity reduces drawdowns by 40% vs equal weight | Mispricing from overreaction in sector flows, corrected by high-volume mean reversion |
| test | Wilson 50% LB on WR > 55% with n>=100; PSR > 1.5 | Wilson LB on WR >55% and PSR on PF >1.5 |
| min_n | 100 | 100 |
| external_benchmark | Renaissance Institutional Equities (RIEF) factor literature; SPY sector rotation indices | Invesco S&P 500 Equal Weight ETF (RSP) rotation studies |
| kill_rule | If n < 100 after 6 months or rolling PF < 1.0 over 50 trades, merge into EQUITY class | Abandon if PF <1.2 or WR <50% over n=150 trades |

### BOND

| field | DeepSeek | xAI |
|---|---|---|
| approach | No defensible approach with current data (n=18). Recommend merge into ETF class or wait for n>=100 | Yield curve steepness arbitrage with duration hedge |
| edge_mechanism | N/A - insufficient sample | Term-structure edge from mispriced yield curve expectations, hedged for rate risk |
| test | N/A - cannot statistically validate | Wilson LB on WR >55% and DSR on PF >1.5 |
| min_n | 100 | 50 |
| external_benchmark | Bloomberg Barclays US Aggregate Bond Index | PIMCO Active Bond ETF (BOND) and Bloomberg Barclays studies |
| kill_rule | If n < 100 after 12 months, permanently merge into ETF class | Abandon if PF <1.2 or WR <50% over n=100 trades |

## Q2 — 30/60/90d rescue plan

### 30d

**DeepSeek**
- Kill or mutate top-3 FOREX draggers (forex_rsi2_mean_reversion, forex_carry_momentum) and CRYPTO quan_engine :: gate=All three strategies paused; mutation logs written
- Implement hard volume cap: no strategy >15% of asset-class volume :: gate=Dashboard shows concentration <15% for all classes
- Re-run forward-edge audit with correct promotion-log timestamps :: gate=Forward labels match actual promotion dates; n>=10 per strategy

**xAI**
- FOREX: Mutate forex_rsi2_mean_reversion and forex_carry_momentum via inverse polarity and symbol rotation :: gate=PF >0.5 or WR >48% on mutated variants, n>=50
- CRYPTO: Isolate quan_engine and unknown, cap volume at 5% each, reallocate to atr_percentile_gate :: gate=Class PF >1.3, top-2 strategies <15% volume

### 60d

**DeepSeek**
- Deploy FOREX rescue: inverse polarity on forex_rsi2_mean_reversion + symbol rotation to AUD/JPY, NZD/USD only :: gate=30-day forward WR > 50%, PF > 1.2 on mutated strategy
- CRYPTO cleanup: remove 'unknown' source trades; reclassify to correct strategy tags :: gate=Unknown source count < 10; CRYPTO class WR > 48%
- Implement kill-switch automation: auto-halt any strategy with 20-trade rolling PF < 0.5 :: gate=No strategy runs with PF < 0.5 for >24 hours

**xAI**
- FOREX: Deploy carry trade with rate differential focus on high-yield pairs :: gate=PF >1.0, WR >50%, n>=100
- CRYPTO: Stress-test mega_mutation_macd_rsi_m048 on forward picks :: gate=PF >5.0, WR >80%, n>=30

### 90d

**DeepSeek**
- FOREX class re-evaluation: if PF > 1.2 and WR > 50% over 200 trades, promote to T2 :: gate=FOREX class health shows 'stable' status
- CRYPTO class: if WR > 50% and PF > 1.5 over 1000 trades, target T1 :: gate=CRYPTO class health shows 'T1 candidate'
- Full system audit: compare live vs backtest performance; document all overrides :: gate=Live/backtest correlation > 0.7 for all active strategies

**xAI**
- FOREX: Full portfolio rebalance, kill non-performing mutations :: gate=Class PF >1.5, WR >50%
- CRYPTO: Promote T1 strategies to 60% volume share :: gate=Class PF >1.8, MDD <15%

## Risk register (union)

- [DS/high] Mutation creates new losers faster than old ones are killed -> mitigation: Mandatory 20-trade paper period before live deployment
- [DS/med] Concentration shifts to one strategy after killing draggers -> mitigation: Hard 15% volume cap enforced at execution layer
- [DS/high] Forward-edge audit labels are inaccurate due to missing promotion log -> mitigation: Manual timestamp reconstruction; accept 'approximate' label
- [DS/med] CRYPTO 'unknown' source hides a genuine T1 strategy being misclassified -> mitigation: Trace each unknown trade to source API; reclassify within 7 days
- [DS/low] Resolver-v2 noise filter thresholds are too aggressive, removing real signals -> mitigation: Backtest with 0.05bp and 2bp thresholds; compare PF distributions
- [XA/med] Mutation fails to lift FOREX PF due to structural market shift -> mitigation: Diversify signal sources with external API sentiment data
- [XA/low] CRYPTO volume cap on losers causes liquidity mismatch -> mitigation: Gradual reallocation over 14 days
- [XA/med] Data integrity issues in forward-only audit -> mitigation: Cross-verify with promotion-log once available
- [XA/high] Regulatory clampdown on FOREX/CRYPTO pairs -> mitigation: Prepare fallback symbol lists on compliant exchanges
- [XA/high] Overfitting during mutation testing -> mitigation: Enforce out-of-sample validation, n>=50

## Do not optimize

- [DS] Surviving 5/100 random seeds in walk-forward optimization
- [DS] P-hacking strategy-symbol pairs until one shows significance
- [DS] Adding more strategies to dilute poor performers (diversification fallacy)
- [DS] Using in-sample Wilson LB without out-of-sample forward test
- [DS] Optimizing for max PF on <50 trades (overfit trap)
- [DS] Ignoring after-cost net edge in favor of gross PF
- [XA] Walk-forward optimization without out-of-sample holdout
- [XA] Strategy-symbol pairs cherry-picked for historical fit
- [XA] Random seed survival (e.g., 5/100 passing by luck)
- [XA] Overweighting small-n strategies despite high PF
- [XA] Ignoring concentration risk for temporary PF boost

## Exit ramps

**DeepSeek:** Abandon FOREX class entirely if after 90 days: (a) PF < 1.0 on 200+ trades, (b) WR < 45%, (c) no single strategy passes forward-edge audit. Reallocate capital to CRYPTO and EQUITY. For CRYPTO: if class WR < 40% after removing quan_engine and unknown, freeze all CRYPTO strategies and divert to EQUITY/COMMODITY only.

**xAI:** Abandon FOREX if PF <0.5 after 90d rescue (n>=500); abandon CRYPTO if PF <1.2 after 90d despite T1 strategy dominance (n>=1000); continue rescue if PF shows consistent upward trend even if below T2

## Caveats
- DeepSeek: Cannot verify promotion-log timestamps from briefing; forward-edge audit labels are approximate. BOND and ETF have insufficient n for statistical validation. SPORTS and FUTURES have zero data - excluded. Resolver-v2 noise filter thresholds assumed correct but not independently verified.
- xAI: Forward-only edge audit lacks promotion-log for precise validation; BOND and ETF sample sizes are thin, reducing statistical reliability
