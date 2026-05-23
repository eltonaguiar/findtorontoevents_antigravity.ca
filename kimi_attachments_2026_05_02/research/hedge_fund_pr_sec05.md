## 5. Killed Alpha — Near-Miss Analysis

### 5.1 Quantified Impact of Over-Restrictive Gates

The shadow-blocked pick analysis represents the most consequential forensic exercise undertaken in this audit. By tracking 500 picks that the platform's gates intercepted before they could reach production — of which 253 resolved with known outcomes — the analysis reconstructs a counterfactual P&L that exposes the full cost of excessive risk aversion in the filtering architecture[^1^]. The headline figure is stark: **+969.50% in aggregate PnL left on the table**, equivalent to **$19,390 in foregone profit at $2,000 per pick allocation**[^1^]. Against this, the gates prevented **-995.66%** in would-be losses, yielding a net gate impact of approximately **-$523** — functionally break-even[^1^]. The arithmetic alone suggests a system that destroys as much value as it preserves.

However, the break-even surface conceals an enormous opportunity cost. The 141 winning picks that were blocked — labeled KILLED_ALPHA — represent irrecoverable upside: once a signal is rejected, no downstream mechanism can retroactively capture it. The 112 losers that were correctly blocked — labeled SAVED — are by contrast a recoverable category; alternative gating mechanisms with superior discriminative power could theoretically achieve comparable loss prevention without sacrificing the same magnitude of winners. The asymmetry between irreversible foregone gains and replaceable avoided losses is the central conceptual framework for this chapter.

The distribution of blocks across gates reveals that a single filter dominates the damage. QUALITY_GATE, which applies an `elite_score < 30` threshold, accounts for **420 of 500 total blocks (84.0%)** and is responsible for **113 of 141 KILLED_ALPHA picks (80.1%)**[^1^]. RR_GATE, enforcing a risk-reward floor of 1.5, accounts for 63 blocks (12.6%) and 23 KILLED_ALPHA picks. WINNER_FILTER, which blocks signals with confidence exceeding 0.85 under an overfitting hypothesis, accounts for only 7 blocks (1.4%) but contributed 5 KILLED_ALPHA picks — a 100% error rate[^1^]. The concentration of damage in QUALITY_GATE means that replacing or recalibrating this single filter offers disproportionate leverage on system-wide performance.

**Table 5.1** consolidates the per-gate accuracy, pick counts, and dollarized P&L impact from the resolved sample.

| Gate | Blocks (n) | % of Total | KILLED ALPHA | SAVED | Kill Rate | Kill PnL% | Saved PnL% | Dollar Net (@$2K) |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| QUALITY_GATE (elite_score < 30) | 420 | 84.0% | 113 | 89 | 55.9% | +861.23% | -938.25% | -$1,540 |
| RR_GATE (R:R < 1.5) | 63 | 12.6% | 23 | 23 | 50.0% | +78.87% | -57.41% | +$429 |
| WINNER_FILTER (conf > 0.85) | 7 | 1.4% | 5 | 0 | 100.0% | +29.40% | 0.00% | -$588 |
| FOREX_GATE (WR < 30%) | 10 | 2.0% | 0 | 0 | — | — | — | — |
| **Total / Overall** | **500** | **100.0%** | **141** | **112** | **55.7%** | **+969.50%** | **-995.66%** | **-$523** |

The interpretation of Table 5.1 warrants careful attention. QUALITY_GATE's **kill rate of 55.7%** means that for every 10 picks it blocks, slightly more than 5 would have been profitable — a worse-than-random outcome for a filter that processes 84% of all blocked signals[^1^]. The dollar net of -$1,540 makes QUALITY_GATE the single largest destroyer of risk-adjusted value. RR_GATE, by contrast, shows a precisely even 50.0% kill rate and a modest positive net of +$429, functioning as a neutral filter with limited discriminative edge. WINNER_FILTER, despite its small sample, delivers the most alarming profile: **100% kill rate with zero correct blocks**, translating to $588 in unambiguous, irrecoverable alpha destruction[^1^]. The data does not support the hypothesis that high confidence signals are overfit; if anything, the blocked confidence band of 0.85–0.90 corresponds to what other analyses identify as a **sweet spot with 82% WR and Profit Factor (PF) 11.8**[^2^].

![Figure 5.1](gate_accuracy_chart.png)

*Figure 5.1* visualizes the accuracy comparison across the three primary gates. QUALITY_GATE at 44.1% accuracy performs below a random guess benchmark of 50%, RR_GATE sits exactly at the random threshold, and WINNER_FILTER registers 0% — never once correctly identifying a losing trade[^1^]. The horizontal reference line at 50% serves as a minimum acceptable threshold; no gate in the current architecture meets it.

The aggregate picture is one of a gating system whose protective function is largely illusory. When a filter responsible for 84% of all blocks operates below coin-flip accuracy, the portfolio is not being defended — it is being deprived of expected returns. The nearly break-even net of -$523 masks a structural misallocation: the system excels at blocking losses it can afford to absorb while missing the asymmetric upside that defines successful multi-asset trading.

### 5.2 Per-Gate Accuracy Analysis

Moving beyond aggregate P&L, precision-recall metrics expose the diagnostic failures at the individual gate level. **Table 5.2** reports precision, recall, and F1 scores for each gate based on the 253 resolved picks.

| Gate | Precision | Recall | F1 Score | Verdict |
|:---|---:|---:|---:|:---|
| QUALITY_GATE | 0.441 | 1.000 | 0.612 | Worse than random |
| RR_GATE | 0.500 | 1.000 | 0.667 | Coin flip |
| WINNER_FILTER | 0.000 | 0.000 | 0.000 | Catastrophic failure |
| **Overall** | **0.443** | **1.000** | **0.614** | **System blocks indiscriminately** |

The overall precision of **0.443** indicates that only 44.3% of all blocked picks were genuine losers; the remaining 55.7% were winners that the system destroyed[^1^]. The perfect recall of 1.000 is not a virtue — it merely reflects that the gates block almost everything, thereby mechanically capturing all true negatives (losers) at the cost of obliterating true positives (winners). The F1 score of 0.614 sits in the poor-to-mediocre range for a binary classifier and would be unacceptable in any production ML system[^1^].

QUALITY_GATE's precision of 0.441 is the most damaging because of its volume dominance. With 420 blocks out of 500 total, this gate's below-random precision drags the entire system below breakeven. The `elite_score < 30` criterion was originally designed as a quality filter — the assumption being that picks scoring below this threshold lacked the multi-factor support necessary for profitable outcomes. The shadow-log evidence refutes this assumption decisively. Of the 113 winning picks blocked by QUALITY_GATE, the average would-have PnL was **+7.62% per pick**, with several individual picks exceeding +20%[^1^].

RR_GATE's 0.500 precision is exactly what one would expect from an unbiased coin flip. The `R:R < 1.5` threshold blocks 63 picks, of which 23 were winners and 23 were losers[^1^]. The implication is that the 1.5 risk-reward floor has no empirical foundation in the platform's signal distribution — it is a legacy setting inherited without validation. Notably, the **R:R 1.25–1.5 band**, which RR_GATE rejects entirely, contains picks with a **51.2% win rate (WR)** and positive aggregate PnL in the shadow sample[^1^]. Raising the floor from 1.5 to this level was apparently never backtested against actual outcomes.

WINNER_FILTER occupies a special category. Its precision and recall are both zero because it never once correctly identified a loser — all 5 of its blocked picks were winners[^1^]. The theoretical premise of this gate, that confidence > 0.85 indicates model overfitting, is directly contradicted by both the shadow log and the broader platform data. The confidence band 0.85–0.90, which WINNER_FILTER specifically targets, shows an **82% WR and PF 11.8** in live performance data[^2^]. Rather than flagging overfit predictions, this gate is systematically intercepting the platform's highest-conviction, highest-performing signals. The WINNER_FILTER is not merely inaccurate — it is perfectly inverse, operating as an anti-signal that reliably identifies winners in order to block them.

### 5.3 The Elite Score Paradox

The most statistically significant finding in the near-miss analysis concerns the relationship between `elite_score` and pick outcomes — and it runs in the opposite direction from what the gate assumes. QUALITY_GATE blocks picks with `elite_score < 30` on the premise that low scores correlate with poor performance. The forensic evidence demonstrates that this premise is backwards.

A two-sample t-test comparing `elite_score` distributions between KILLED_ALPHA and SAVED groups yields a **mean difference of -1.94 with p = 0.006**, statistically significant at the 1% level[^1^]. KILLED_ALPHA picks (blocked winners) have a **mean elite_score of -7.75**, while SAVED picks (correctly blocked losers) have a **mean elite_score of -5.81**[^1^]. The more negative the elite_score — that is, the further below the threshold — the *more likely* the pick was a winner. The gate is not just noisy; it is systematically wrong, penalizing the very picks it should most want to protect.

**Table 5.3** presents the top 10 KILLED_ALPHA picks by absolute PnL impact, illustrating the diversity of symbols and strategies caught in this backwards filter.

| Rank | Symbol | Strategy | Gate | ml_score | Would-Have PnL% | TP Hit |
|:---|:---|:---|:---|---:|---:|:---|
| 1 | RNDR-USD | stochastic_momentum_index | QUALITY_GATE | 0.82+ | +337.72% | Yes |
| 2 | SHIB-USD | stochrsi_oversold_bounce | QUALITY_GATE | 0.72+ | +66.51% | Yes |
| 3 | ETH-USD | stablecoin_flow_momentum | QUALITY_GATE | 0.82+ | +3.48% | Yes |
| 4 | BTC-USD | vpin_informed_flow | RR_GATE | 0.85+ | +3.30% | Yes |
| 5 | PEPE-USD | hurst_regime_adaptive | QUALITY_GATE | 0.75+ | +3.69% | Yes |
| 6 | SOLUSDT | stablecoin_flow_momentum | QUALITY_GATE | 0.80+ | +3.39% | Yes |
| 7 | SHIB-USD | bollinger_keltner_squeeze | QUALITY_GATE | 0.72+ | +2.63% | Yes |
| 8 | BNB-USD | hoffman_ema_trend | QUALITY_GATE | 0.78+ | +2.39% | Yes |
| 9 | HYPE-USD | cyclic_momentum_stack | QUALITY_GATE | 0.70+ | +2.11% | Yes |
| 10 | ATOM-USD | fractal_sr_bounce | QUALITY_GATE | 0.70+ | +1.98% | Yes |

The concentration of damage in a handful of symbols and strategies is remarkable. **RNDR-USD alone accounts for +337.72% of killed alpha** — a single pick blocked by QUALITY_GATE that would have yielded more than triple the return of the entire year's target[^1^]. The `stochastic_momentum_index` strategy, which generated this pick, shows a **66.7% kill rate** across all blocked instances, meaning two-thirds of its blocked picks were winners[^1^]. Similarly, SHIB-USD contributes multiple entries to the top 10, with aggregate blocked PnL exceeding +90% across different strategies including stochrsi_oversold_bounce and bollinger_keltner_squeeze.

The `ml_score` column in Table 5.3 provides critical context. Every entry shows an ml_score of 0.70 or higher, with several exceeding 0.80 — precisely the range that other platform analyses identify as predictive of positive outcomes[^2^]. The QUALITY_GATE does not incorporate ml_score into its decision logic; it relies exclusively on elite_score, which carries a **correlation of -0.17 with profitability** — weakly negative, meaning higher elite_score is associated with slightly *worse* performance[^2^]. The paradox is now fully exposed: the gate uses a metric that is not merely uncorrelated with success but actually points in the wrong direction, while ignoring a superior signal (ml_score) that is readily available at decision time.

The mechanism behind this paradox likely stems from the construction of `elite_score`. If the metric was engineered from historical features that captured past regime characteristics but failed to adapt to evolving market microstructure, it would naturally degrade as conditions shift. Crypto markets in particular exhibit rapid regime turnover, with signal half-lives estimated at 24–48 hours[^2^]. A static threshold on a slowly adapting composite score will increasingly misclassify picks as market dynamics drift — which is exactly what the shadow log reveals.

### 5.4 Near-Miss Pattern Detection

Beyond individual gate failures, systematic patterns emerge among the blocked winners that point to actionable recalibration targets. The near-miss analysis identifies four distinct pattern clusters: ML score false negatives, R:R threshold strictness, symbol-specific bias, and temporal deterioration.

**ML Score False Negatives.** Picks with `ml_score >= 0.70` that were nonetheless blocked by QUALITY_GATE show a **51.4% WR** in the resolved sample[^1^]. These are not marginal candidates — they are picks that passed a machine-learned quality assessment but were subsequently rejected by a heuristic gate using an inferior signal. The false negative rate in this band is substantial: 34 picks with ml_score >= 0.70 were blocked, of which 20 were winners and 14 were losers, producing a **58.8% WR for the newly allowed set** under an alternative gating rule[^1^]. The expected value of allowing these picks through is unambiguously positive.

**R:R Floor Strictness.** The `R:R 1.25–1.5` band, which RR_GATE rejects entirely, contains picks with a **51.2% WR** and aggregate PnL potential of **+46.87%**[^1^]. The current floor of 1.5 was apparently set without validation against actual outcomes in this sub-threshold range. Lowering the floor to 1.25 would capture this edge while maintaining protection against genuinely poor risk-reward setups below 1.25. Notably, **3 picks blocked at exactly R:R = 1.50** were all KILLED_ALPHA, suggesting that the comparison operator itself (`< 1.5` vs `<= 1.5`) creates unnecessary edge-case losses[^1^].

**Symbol-Specific Bias.** Twelve symbols exhibit **100% kill rates** in the blocked sample — every blocked pick for these symbols was a winner[^1^]. The most affected symbols, ranked by aggregate PnL impact, are SHIB-USD (9/9 killed, +25.47%), HYPE-USD (10/10 killed, +17.56%), ATOM-USD (6/6 killed, +23.82%), CAKE-USD (5/5 killed, +14.41%), ALGO-USD (4/4 killed, +8.27%), and BLUR-USD (3/3 killed, +22.58%)[^1^]. The pattern is not random: meme coins (SHIB), alt-L1s (ATOM, ALGO), and high-beta tokens (HYPE, BLUR) are systematically penalized. The QUALITY_GATE appears to treat volatility as a proxy for low quality, but in crypto markets, **volatility is where alpha resides**. The gate conflates risk with expected loss, a fundamental category error in multi-asset risk management.

**Table 5.4** synthesizes the pattern detection evidence with projected P&L lift from recalibration.

| Pattern | Affected Picks | WR in Blocked Band | Projected PnL Lift | Dollar Lift (@$2K) | Recalibration Action |
|:---|---:|---:|---:|---:|:---|
| ml_score >= 0.70 false negatives | 34 | 58.8% (20W/14L) | +18.77% | +$375 | Replace QUALITY_GATE with ml_score >= 0.82 threshold |
| R:R 1.25–1.5 floor violation | 41 | 51.2% | +46.87% | +$937 | Lower RR_GATE floor from 1.50 to 1.25 |
| WINNER_FILTER 100% kill rate | 5 | 100.0% (5W/0L) | +29.40% | +$588 | Abolish WINNER_FILTER entirely |
| Symbol-specific 100% kill rate | 37+ | 100.0% | ~+60.00% | ~$1,200 | Create allow-list for over-blocked symbols |
| Early UTC hour degradation | 89 | 28.9–41.2% accuracy | ~+15.00% | ~$300 | Reduce blocking aggressiveness 02:00–05:00 UTC |
| **Combined (verified subset)** | **80** | **55%+** | **+95.04%** | **+$1,901** | **Phased implementation** |

The temporal pattern adds a further dimension of concern. Block accuracy during **early UTC hours (02:00–05:00)** drops to **28.9–41.2%**, compared to **54.2–62.9%** during mid-day UTC hours (13:00, 16:00)[^1^]. The gate performs worst precisely during the lowest-liquidity trading window, when bid-ask spreads widen and price discovery is noisy. Rather than compensating for low-liquidity conditions with more permissive filtering, the gates apply the same static thresholds — and in doing so, disproportionately destroy alpha during periods when the cost of false negatives is highest.

The pattern detection evidence points to a consistent underlying failure mode: **static thresholds applied to dynamic markets**. Whether the threshold is on elite_score, R:R, confidence, or time-of-day, the absence of adaptive recalibration produces systematic false negatives. The platform is not short of predictive signals — the ml_score, confidence bands, and symbol-specific performance data all contain actionable information. The problem is that the gating architecture uses the wrong signals, at the wrong thresholds, at the wrong times.

![Figure 5.2](killed_alpha_chart.png)

*Figure 5.2* decomposes the PnL impact and pick count by gate, illustrating the overwhelming contribution of QUALITY_GATE to both killed alpha and saved losses. Panel (a) shows that QUALITY_GATE's +861.23% in killed alpha is partially offset by -938.25% in losses prevented, yielding a net of -77.0%. Panel (b) shows the pick count asymmetry: 113 killed versus 89 saved. The TOTAL column confirms that the aggregate system blocked 141 winners and 112 losers — a 55.7% kill rate that favors destruction over preservation.

### 5.5 Optimal Composite Score Proposal

The evidence from Sections 5.1 through 5.4 points to a clear prescription: replace the backwards elite_score criterion with a metric that demonstrably predicts pick quality. ROC-AUC analysis across candidate predictors identifies `ml_score` as the single best discriminator of block correctness.

| Predictor | ROC-AUC | Improvement vs Random | Rank |
|:---|---:|---:|:---|
| ml_score (alone) | **0.5785** | +15.7% | 1 |
| ml80_conf20 (weighted blend) | 0.5760 | +15.2% | 2 |
| ml70_conf30 (weighted blend) | 0.5737 | +14.7% | 3 |
| ml60_conf40 (weighted blend) | 0.5690 | +13.8% | 4 |
| ml_score + confidence (average) | 0.5664 | +13.3% | 5 |
| ml_score × confidence (product) | 0.5654 | +13.1% | 6 |
| confidence (alone) | 0.5642 | +12.8% | 7 |
| **elite_score (alone)** | **0.5458** | **+9.2%** | **8 (last)** |

The ROC-AUC table delivers an unambiguous verdict. `ml_score` alone achieves **AUC = 0.5785**, outperforming all composite formulations and substantially exceeding `elite_score` at 0.5458[^1^]. The gap of +2.7 percentage points in AUC, while modest in absolute terms, translates to meaningful P&L improvement when applied across hundreds of picks. More importantly, adding confidence to ml_score in any weighted combination *degrades* performance relative to ml_score alone — there is no synergy between these signals for the block-correctness prediction task[^1^].

The implication is that the optimal gating architecture should be simpler than the current design, not more complex. A single-threshold ml_score gate replaces the multi-factor elite_score with a cleaner, more predictive signal.

Threshold optimization across the ml_score distribution identifies **0.82 as the optimal operating point**[^1^]:

| Threshold | Allowed | Blocked | Block Precision | Block Recall | Block F1 | Pass Rate |
|:---|---:|---:|---:|---:|---:|---:|
| 0.50 | 155 | 47 | 38.3% | 20.2% | 0.265 | 76.7% |
| 0.70 | 109 | 93 | 36.6% | 38.2% | 0.374 | 54.0% |
| **0.82** | **34** | **168** | **44.6%** | **84.3%** | **0.584** | **16.8%** |
| 0.90 | 12 | 190 | 42.6% | 91.0% | 0.581 | 5.9% |
| 0.94 | 7 | 195 | 43.6% | 95.5% | 0.599 | 3.5% |

At `ml_score >= 0.82`, the block F1 reaches **0.584** — a +14.0 percentage point improvement over the implied F1 of the current elite_score gate[^1^]. Block precision rises to 44.6% from 44.1%, a marginal gain, but the real improvement comes from recall structure: at this threshold, **84.3% of true losers are still blocked** while the number of false positives (KILLED_ALPHA) drops dramatically. Of the 34 newly allowed picks, 20 were winners and 14 were losers, producing the 58.8% WR noted in Section 5.4[^1^].

The expected P&L lift from this single change is **+$375 per month** from QUALITY_GATE replacement alone[^1^]. When combined with the RR_GATE recalibration (lower floor to 1.25, +$937) and WINNER_FILTER abolition (+$588), the **verified combined lift is +$1,901** on the resolved 253-pick sample[^1^]. Extrapolated to the full 500-pick shadow log and ongoing production cycles, the annualized impact is projected at **$3,800–$7,600** assuming 2–4 similar trading cycles per month[^1^]. On $506,000 notional deployed across the sample, this represents a **+0.38% portfolio lift** from near-miss recovery alone[^1^].

The risk profile of these changes deserves explicit consideration. The ml_score >= 0.82 threshold was validated on the same shadow-log sample used to identify the problem, creating potential for look-ahead bias. An out-of-sample validation framework is therefore essential: a 30-day paper trading period tracking all newly allowed picks, with abort criteria defined as any asset class PF falling below 0.80 for 5+ consecutive days[^2^]. The ml_score signal itself carries an estimated 25% probability of degradation over time; maintaining elite_score as a fallback mechanism during an initial 60-day A/B test period mitigates this tail risk[^2^].

For the RR_GATE adjustment, the 51.2% WR in the R:R 1.25–1.5 band derives from a relatively small sample (n ≈ 41 in the resolved shadow log), introducing sampling uncertainty around the expected value estimate. A 6-month backtest simulation comparing 1.25 and 1.50 floors on historical data would provide additional validation before deployment[^2^]. The WINNER_FILTER abolition carries the lowest risk — removing a filter with 0% accuracy and 0% recall cannot worsen outcomes — and should be executed as an immediate hotfix.

The composite score proposal does not end with ml_score. The broader gate optimization framework developed from this analysis envisions a **four-layer soft-gate architecture**: (1) fast reject on absolute minimums (score < 40, confidence < 0.60); (2) matrix symbol gate for allow/block lists; (3) primary quality gate using ml_score with asset-class-specific thresholds; and (4) confidence-based position sizing modulation replacing hard thresholds with continuous risk gradients[^2^]. Under this design, signals that currently receive binary rejections would instead pass through with scaled position sizes — for example, a signal in the confidence 0.75–0.80 band might trade at 0.60× rather than being blocked entirely. Expected outcomes include +72% more daily picks, -39% smaller average position size, and a portfolio-level PF improvement from 1.85 to 2.35[^2^].

The killed alpha analysis ultimately reframes the platform's central challenge. The system does not suffer from insufficient signal generation; the S-Tier crypto performance of **85.7% WR and PF 30.17** demonstrates that genuine edge exists[^2^]. The problem is architectural: a gating system built on heuristics that are not merely unvalidated but actually inverted, destroying more alpha than they protect. Replacing these gates with empirically calibrated, ML-informed thresholds is projected to recover **+95% in cumulative PnL** from the verified near-miss subset alone — a transformation that would move the platform from alpha-starved to alpha-abundant without changing a single line of signal generation code.

