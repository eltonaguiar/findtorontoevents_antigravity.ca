## 5. Strategy Health & Failure Analysis

### 5.1 Strategy Failure Overview

Systematic diagnosis of the platform's strategy universe reveals **11 strategies flagged as statistical dropouts**, defined as those whose 7-day Win Rate (WR) has fallen more than 20 percentage points below their historical baseline. The mean baseline WR across the cohort was 46.4%, yet the current 7-day average stands at 27.5% — a **19.1pp collective collapse** that demands classification before any capital reallocation.

Four failure modes emerge from the diagnostic framework, grounded in Jegadeesh & Titman's momentum-to-reversal transition model [^22^], Ali-Daniel-Hirshleifer's "PMP Effect" on style-chasing reversals [^23^], and practitioner evidence on RSI(2) regime dependency from Connors & Alvarez [^38^][^45^]. Published anomalies face approximately 5pp of annual Sharpe decay from joint overfitting and arbitrage pressures [^41^].

#### 5.1.1 Table: 11 Failing Strategies

| Strategy | 7d WR | Baseline WR | Drop (pp) | Failure Category | Invertible |
|:---|:---:|:---:|:---:|:---|:---:|
| myfxbook_retail_contrarian | 33% | 54% | –21 | Regime change + adverse selection | Yes |
| forex_rsi2_mean_reversion | 19% | 49% | –30 | Regime change + wrong asset class | No |
| stocks_rsi2_pullback | 42% | 73% | –31 | Regime change (bear/trendless) | Maybe |
| futures_momentum | 20% | 45% | –25 | Adverse selection + regime change | Yes |
| ensemble | 30% | 41% | –11 | Composition decay (GIGO) | No |
| goldmine_1x_consensus | 12% | 30% | –18 | Overfitting + crowding | Yes |
| st_obv_support_divergence | 46% | 57% | –11 | Regime change (volume reliability) | No |
| unknown | 18% | 34% | –16 | Unknown / data quality | No |
| gainer_compression_relaxed_mut | 8% | 32% | –24 | Overfitting (parameter bloat) | Maybe |
| MomentumEMA | 46% | 67% | –21 | Adverse selection + crowding | Yes |
| signal_engine_momentum_mut | 30% | 50% | –20 | Overfitting + regime dependency | Maybe |

The median drop is 21pp, but the worst performers — stocks_rsi2_pullback at –31pp and forex_rsi2_mean_reversion at –30pp — are mean-reversion strategies operating in environments where mean-reversion assumptions have broken down. Lehmann (1990) and Jegadeesh (1990) established that short-term contrarian profits require sufficiently negative return autocorrelations [^26^]; when markets enter trending regimes, those autocorrelations flip positive and the strategy's edge inverts into a liability [^28^]. The 31pp collapse in stocks_rsi2_pullback — whose 73% baseline WR made it the portfolio's statistical crown jewel — exemplifies how regime dependency transforms a high-conviction edge into a capital destruction engine within a single volatility cycle.

### 5.2 Strategy-by-Strategy Diagnosis

#### 5.2.1 Regime Change: What Shifted, What Filter Would Restore Edge

Four strategies share the regime-change diagnosis. **stocks_rsi2_pullback**, built on Connors & Alvarez's canonical RSI(2) configuration [^45^], collapsed from 73% to 42% as the equity market exited its mean-reverting regime. Practitioner research documents that "the 2008 financial crisis and March 2020 crash saw win rates drop below 60% as 'buy the dip' repeatedly failed" [^45^]. The restoration path involves four parameter tweaks: tighten entry to RSI(2) < 5; add a VIX regime filter (suspend when VIX > 25 or VIX > 20 and rising); implement a 5-bar time stop; and require price above both 200-day and 50-day SMAs. Dual-trend confirmation "boosts win rates by 5–10% while reducing signal frequency" [^45^]. Expected WR recovery: 42% → 60–65%.

**forex_rsi2_mean_reversion** suffers from a fundamental asset-class mismatch. Connors research explicitly warns that "applying RSI 2 blindly to highly trending markets like forex or commodities yields sub-50% win rates" [^44^]. The recommended action is to abandon forex deployment and relocate the same logic to S&P 500 / Nasdaq-100 instruments, where StatOasis documented 73–80% WR with proper filtering [^38^].

**myfxbook_retail_contrarian** has degraded because the least-informed retail traders have exited active forex markets, leaving a more sophisticated residual cohort. Chan (1988) demonstrated that contrarian profits are compensation for time-varying risk; when risk regimes shift, abnormal returns shrink to near-zero [^24^]. The recommended inversion — fading retail only when VIX < 25 and positioning exceeds the 90th percentile — narrows signal frequency but restores theoretical edge.

**st_obv_support_divergence** has suffered from declining volume-signal reliability due to dark pool proliferation, payment-for-order-flow arrangements, and algorithmic execution that fragments volume signals across venues [^39^]. The modest 11pp decline suggests residual edge; modernization of the volume metric combined with a 50% position-size reduction is the appropriate response.

#### 5.2.2 Adverse Selection: Why Consensus Signals Become Self-Defeating

Three strategies — **futures_momentum**, **MomentumEMA**, and **ensemble** — suffer from adverse selection where signal popularity eroded alpha. MomentumEMA is the clearest case: EMA-crossover momentum has been public knowledge for 40+ years, placing it in the crosshairs of Falck et al.'s finding that "publication year alone accounts for 30% of variance in Sharpe decay" with "5pp annual decay" [^41^]. The Jegadeesh & Titman (2001) reversal evidence shows that momentum portfolios experience "dramatic reversal of returns in the second through fifth years" post-formation [^22^] — and for EMA momentum, that formation period spans decades.

Futures momentum faces dual headwinds: general momentum crowding (Ali-Daniel-Hirshleifer's "PMP Effect" generates 0.40% monthly alpha from fading it, t=3.74 [^23^]) and commodity-specific structural breakdown as index investing created then arbitraged artificial momentum [^52^]. The ensemble strategy illustrates "garbage in, garbage out": with 7 of 11 constituents failing, the ensemble amplifies rather than attenuates losses. The Sheppert GT-Score framework supports reducing constituent count to only robust, validated signals [^33^].

#### 5.2.3 Overfitting: Which Parameters Were Over-Optimized

**gainer_compression_relaxed_mut** carries its pathology in its name: "relaxed_mut" signals mutation-based optimization with relaxed constraints, a recipe for parameter bloat. The 32% baseline WR was already the worst in the portfolio; the collapse to 8% is textbook overfitting. Detection literature identifies the signatures: "deterioration outside the build dataset; brittle values where small changes imply large jumps" [^34^]. The GT-Score research shows that "profit-optimized strategies achieve higher mean test returns but exhibit materially worse performance retention from training to out-of-sample" [^33^].

**signal_engine_momentum_mut** shows similar characteristics: a 50% marginal baseline collapsing 20pp, a decline larger than regime change alone would produce. The AlgoXpert framework identifies "parameter overfitting, selection bias, and sensitivity to regime changes" as primary failure modes for optimized strategies [^32^].

#### 5.2.4 Structural: Code Bugs and Data Pipeline Failures

The **unknown** strategy is a governance failure: a system component receiving capital allocation with no documented logic, no known parameters, and no reproducible validation. The AlgoXpert framework requires "cliff veto, execution controls, and circuit breakers" — none applicable to an undocumented system [^32^]. Its 34% baseline was already below random walk; the 18% 7-day reading merely confirms what the absence of documentation implied.

**cta_commodity_momentum_term** is structurally dead. A Profit Factor of 0.02 represents complete strategy death, not temporary decay. The 58% flat exits indicate the strategy fails to capture directional moves at all — a signature of momentum logic applied to markets where momentum has been fully arbitraged [^52^]. The path forward is not to fix momentum but to invert to the academically validated carry alternative: go long backwardation, short contango.

### 5.3 Inverse Strategy Candidates

#### 5.3.1 Academic Basis: Jegadeesh & Titman Momentum Reversal

The theoretical foundation for strategy inversion rests on a robust literature. Jegadeesh & Titman (2001) demonstrated that momentum portfolios earn +12.17% in year one but decline to –0.44% by year five — a 12.6pp reversal [^22^]. Ali et al. (2017) showed that following top-quintile momentum performance, stale portfolios reverse –19% in years 2–5 versus +11% after bottom-quintile performance [^23^]. Lehmann (1990) and Jegadeesh (1990) established that short-term contrarian strategies generate 2%+ monthly abnormal returns, with winners reversing –0.35% to –0.55% the following week [^26^]. Four strategies meet the inversion criteria: baseline WR above 50%, current decline exceeding 15pp, and failure mode consistent with regime change or adverse selection.

#### 5.3.2 Table: 4 Invertible Strategies

| Strategy | Baseline WR | Current WR | Inverted Signal | Expected Inverted WR | Academic Basis |
|:---|:---:|:---:|:---|:---:|:---|
| myfxbook_retail_contrarian | 54% | 33% | Fade retail at 90th+ pct, VIX < 25 | 48–52% [^24^] | Chan (1988): contrarian profits as time-varying risk compensation |
| futures_momentum | 45% | 20% | Short winners, buy losers in high-PMP | 55–60% [^23^] | Ali et al. PMP Effect: 0.40% monthly alpha from reversal (t=3.74) |
| goldmine_1x_consensus | 30% | 12% | Go against >70% consensus | 55–60% [^21^] | BSV/DHS: short-run underreaction → long-run overreaction |
| MomentumEMA | 67% | 46% | Fade EMA crosses when VIX > 20 | 55–58% [^22^] | J&T (2001): momentum reverses 12.6pp years 2–5 post-formation |

The expected inverted WRs are conservative estimates drawn directly from the cited academic returns. The goldmine_1x_consensus inversion exploits Barberis-Shleifer-Vishnu (1998) and Daniel-Hirshleifer-Subrahmanyam (1998): short-run underreaction followed by long-run overreaction means consensus systematically overshoots [^21^].

#### 5.3.3 Validation Plan: 30-Day Paper Trade Before Live Deployment

No inverted strategy receives live capital without completing a **30-day paper-trading validation** producing at least 30 simulated trades. Minimum acceptance criteria: (1) paper WR within 5pp of expected inverted WR; (2) maximum drawdown below 15%; (3) Profit Factor exceeding 1.0; (4) no single day exceeding 20% of total PnL. This protocol aligns with the AlgoXpert IS/WFA/OOS framework [^32^] and prevents deployment of theoretically sound inversions that encounter execution slippage or microstructure frictions not captured by backtest assumptions.

### 5.4 Strategies to Ban Immediately

Three strategies require permanent capital prohibition. Decision criteria: no recoverable edge regardless of parameter adjustment; governance failure precluding safe deployment; or structural mismatch between strategy and asset class.

The **unknown** strategy receiving live allocation represents a breakdown of quantitative governance. No documentation, no auditable logic, no validation protocol. Trading it is the antithesis of the GT-Score framework's emphasis on "stable parameter regions" and "structural safeguards" [^33^]. **Action: remove code; treat as a new strategy subject to full IS/WFA/OOS protocol if logic can be recovered** [^32^].

**gainer_compression_relaxed_mut**, at 32% baseline WR, is not a temporarily failing strategy but a failed experiment. The "relaxed mutation" approach generated spurious patterns. If the volatility-compression concept has theoretical merit, it must be rebuilt from scratch with minimum 200 trades for validation [^42^], GT-Score optimization [^33^], and walk-forward validation with purge gaps [^32^]. **Action: permanently abandon current implementation.**

**cta_commodity_momentum_term** (PF 0.02) is dead. The recommended replacement is a **triple-screen commodity carry strategy**: Screen 1 selects commodities in backwardation (positive roll yield); Screen 2 filters for term structure slope in the top tertile; Screen 3 applies a 20-day momentum overlay to time entry within carry-selected instruments. Fuertes et al. demonstrate that term structure strategies improved post-financialization (Sharpe 0.41 vs 0.35 for momentum) [^52^]. Expected PF improvement: 0.02 → 1.1–1.4.

#### 5.4.4 Table: 3 Banned Strategies

| Strategy | Baseline WR | 7d WR | PF | Ban Rationale | Replacement Action |
|:---|:---:|:---:|:---:|:---|:---|
| unknown | 34% | 18% | < 0.5 | No documentation; governance failure; below-random baseline | Code removal; full protocol if logic recovered |
| gainer_compression_relaxed_mut | 32% | 8% | < 0.3 | Overfitted to noise; worst baseline in portfolio | Permanent abandon; rebuild with GT-Score if concept valid |
| cta_commodity_momentum_term | N/A | N/A | 0.02 | Structural death; 58% flat exits; momentum arbitraged | Deploy triple-screen carry replacement |

Removing these three strategies improves portfolio average WR by approximately 5pp through elimination of negative-expectancy allocations. The ban is irreversible: no future parameter tweak or regime shift can rehabilitate strategies whose edge was either never real or has been permanently arbitraged.

### 5.5 Hidden Edge: Underallocated Tier-2 Strategies

While 11 strategies decay, four Tier-2 strategies with strong historical metrics are starved for capital due to low pick counts or "building" status labels.

#### 5.5.1–5.5.4 Table: 4 Tier-2 Hidden Edge Strategies

| Strategy | WR | PF | n | Status | Hidden Edge Assessment | Recommended Action |
|:---|:---:|:---:|:---:|:---|:---|:---|
| signal_validation | 63.0% | 2.58 | 184 | Building | **STRONG EDGE — UNDERUTILIZED**: Highest PF in portfolio. 184 trades provide statistical significance. Low pick count suggests overly strict validation criteria. | Relax threshold 15–20%; expect 2× signal frequency at >55% WR |
| mega_mutation | 67.9% | 3.19 | 78 | Building | **VERY STRONG EDGE**: Exceptional PF of 3.19. 78 trades limit confidence but ratio is compelling. | Increase position sizing 2×; apply MDD guard at 15% |
| rl_agent | 60.0% | 2.54 | 5 | Building | **TOO EARLY**: 5 trades insufficient for statistical conclusion; variance dominates signal. | Paper trade only; require n ≥ 30 before allocation |
| claude_gainer | 56.2% | 2.23 | 32 | Building | **MODERATE EDGE — EMERGING**: Below 200-trade validation [^42^] but above minimum viability. | Gradual allocation increase; apply MDD guard at 12% |

The Tier-2 strategies reveal a critical pattern: **signal_validation** (PF 2.58) and **mega_mutation** (PF 3.19) possess the highest Profit Factors in the entire portfolio, yet both receive minimal capital because low signal frequency keeps them in "building" status. The GT-Score framework favors these robust, lower-frequency strategies over the high-frequency, decaying strategies in the dropout list [^33^]. The recommendation is to reallocate 30–40% of capital from failing dropout strategies to these Tier-2 building strategies, with graduated scaling: full activation at n ≥ 200, partial scaling at n ≥ 50, paper-only below n = 30.

The **rl_agent** strategy exemplifies a critical governance tension. Its 60% WR and 2.54 PF are superficially attractive, but 5 trades provide no statistical foundation for allocation. The platform must resist scaling strategies prematurely based on early outperformance — a pattern that mirrors the survivorship illusion identified elsewhere in this audit, where small-sample extreme metrics systematically fail to replicate.

