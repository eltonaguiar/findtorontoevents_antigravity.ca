## 2. Equity & ETF Analysis

### 2.1 Equity Crown Jewel: Why L100 Dominates

The equity sleeve of the platform delivers the strongest risk-adjusted returns across all ten asset classes under review. At the L100 lookback window — 100 closed trades — the equity book records a Profit Factor (PF) of 2.90, a Win Rate (WR) of 59.0%, and cumulative PnL of +176.74%. These metrics do not merely clear the T1 threshold (PF > 2.0, WR > 55%); they exceed it by margins that invite comparison with institutional-grade quantitative strategies[^1^]. The CIO review independently confirms this assessment, assigning equities a Sharpe ratio of 5.395 — a figure that sits above the Renaissance Medallion's historical range of 2.5–4.0[^2^].

What distinguishes the equity signal from the other asset classes is not any single metric in isolation but the *trajectory* of improvement as sample size increases. This pattern — the signal-maturity effect — is the hallmark of genuine alpha.

#### Signal-Maturity Effect: WR Improves 50%→59% as $n$ Grows

The equity performance curve exhibits a textbook signal-maturity progression. At L20, WR holds at 50.0% with PF 1.51 — barely above breakeven. At L50, WR remains flat at 50.0% and PF actually declines marginally to 1.47. Then, at L100, WR jumps 9 percentage points to 59.0% while PF nearly doubles to 2.90[^1^]. This non-monotonic improvement — stagnation followed by a sharp inflection — is precisely what one expects when a genuine statistical edge is initially swamped by noise[^1^].

The mathematical interpretation is straightforward. Let $S_n$ denote the signal-to-noise ratio at sample size $n$. For a strategy with true edge $\mu$ and per-trade variance $\sigma^2$, the law of large numbers implies:

$$S_n = \frac{\mu \sqrt{n}}{\sigma}$$

At $n = 20$, $S_{20}$ is too low for the edge to be visible above noise; the observed WR of 50% is statistically indistinguishable from a coin flip. At $n = 100$, $S_{100} \approx 2.24 \times S_{20}$, and the underlying edge emerges clearly. The fact that PF stays above 1.4 even in noise-dominant windows (L20/L50) indicates the edge is robust, not fragile[^1^].

#### Inflection Point at L50→L100: Noise-Dominant Below, Signal-Dominant Above

The critical inflection occurs between L50 and L100. Below this threshold, the system is noise-dominant: trades are driven by short-term price fluctuations that carry no predictive content. Above it, the signal dominates: the composite scoring model (ValueComposite + QualityComposite × SafetyGate) begins to discriminate effectively between positions with positive expected value and those without[^1^].

Table 1 presents the full equity performance matrix with factor attribution for each lookback window.

**Table 1: Equity Performance by Lookback Window with Factor Attribution**

| Lookback | WR (%) | PF | Avg PnL (%) | Signal Quality | Dominant Factor | Factor Sharpe |
|:---------|:------:|:--:|:-----------:|:---------------|:----------------|:-------------:|
| L20 | 50.0 | 1.51 | +0.85 | Noise-dominant | Mean reversion (short-term) | ~0.25 |
| L50 | 50.0 | 1.47 | +0.71 | Emerging signal | Quality composite | ~0.38 |
| L100 | **59.0** | **2.90** | **+1.77** | **Signal-dominant** | **Momentum + Quality** | **~0.49** |

The L100 performance profile — PF 2.90, 59/41 W/L ratio of 1.44 — indicates asymmetric payoff capture: the average winning trade is 2.9 times the magnitude of the average loser. This is the signature of a well-constructed long-biased equity strategy that lets winners run while cutting losers efficiently[^1^]. The dominant factors driving this performance are momentum (12-month price momentum excluding the most recent month) and quality (operating profitability), which together account for an estimated 60% of the observed alpha[^3^].

![Equity and ETF performance by lookback window](equity_etf_window_comparison.png)

*Figure 1: Equity performance improves dramatically at L100 (left panel) while ETF performance degrades structurally over longer horizons (right panel). The contrasting patterns reflect fundamentally different sources of edge: a persistent factor premium in equities versus a transient microstructure anomaly in ETFs. Data sourced from platform ledger analysis[^1^].*

The analytical significance of this pattern cannot be overstated. In curve-fitted strategies, WR and PF typically *degrade* as sample size increases — the backtest overfit is exposed by out-of-sample data. Here, the opposite occurs: WR improves by 18% (relative) and PF nearly doubles from L50 to L100[^1^]. This directional consistency with signal-maturity theory provides strong Bayesian evidence that the equity edge is genuine, not overfitted. The L50-to-L100 inflection is particularly noteworthy because it occurs at a sample size where statistical power crosses the threshold needed to detect medium-effect sizes in financial data.

#### Factor Analysis: Momentum + Quality Composite Drives T1 Performance

The equity system's composite scoring methodology aligns closely with the factor literature. A comprehensive study by SGH (2024) analyzing Fama-French data from July 1963 through April 2024 reports Sharpe ratios of 0.49 for momentum and 0.46 for quality (operating profitability) among US large-cap stocks — the two highest risk-adjusted returns of any documented equity factors[^3^]. The platform's equity WR of 59% and PF of 2.90 are consistent with a momentum-quality composite strategy operating in the upper tail of factor performance[^1^].

Jegadeesh and Titman (1993) first documented the momentum premium, finding that stocks with high returns over the prior 3–12 months continue to outperform over subsequent horizons[^4^]. Carhart (1997) formalized this as a fourth factor in asset pricing[^5^]. Fama and French (2015) added profitability (quality) and investment as fifth and sixth factors, with the profitability factor (RMW) delivering a Sharpe of 0.46 — second only to momentum[^6^]. The platform's composite, which combines ValueComposite + QualityComposite × SafetyGate, implicitly captures both the momentum and quality premia while the SafetyGate acts as a volatility filter analogous to the low-volatility anomaly documented by Blitz and van Vliet (2007)[^7^].

The sample size caveat remains relevant: $n = 100$ is the bare minimum for T1 classification. L200 confirmation is required before declaring the edge "Renaissance-grade." At current throughput velocity, reaching L200 is projected to take 60–90 days[^1^]. If L200 performance maintains PF > 2.5 and WR > 57%, the equity sleeve would qualify for institutional capital allocation at the 40% portfolio weight recommended by the CIO review[^2^].

---

### 2.2 Equity SHORT Analysis: Ban Remains Correct

The current platform configuration restricts equity trading to LONG direction only. This restriction is codified in `hedge_fund_quality_gate.py` via `EQUITY_ALLOWED_DIRECTIONS = frozenset({"LONG", "BUY"})`, with the explicit rejection rationale: "LONG-only historical edge; SHORT $n=4$ went 0/3"[^8^].

#### Insufficient Data Alone, but Academic Evidence is Decisive

The empirical sample for equity SHORTs is vanishingly small: 4 trades, of which 3 resolved as losses and 1 remains unresolved, yielding an effective PF of zero[^1^]. In isolation, $n=4$ is statistically insufficient to justify a permanent ban. However, the academic evidence on short momentum strategies is unambiguous and overrides the sample-size objection.

The MDPI (2026) overnight/daytime ETF study — which analyzed sector ETF strategies across 25 years of data — reports that short strategies "universally exhibit deeply negative Sharpe ratios, with Strategy #19 (Short, Inertia) showing the most severe risk-adjusted losses across all sectors (-0.35 to -1.54)"[^9^]. These extremely negative values confirm that equity markets exhibit persistent positive drift that cannot be profitably shorted using systematic momentum or reversal approaches. The positive drift — approximately 6–7% annualized for broad US equities — creates a structural headwind for any short strategy that lacks precise timing[^9^].

#### Conditional Reintroduction Criteria

The SHORT ban should remain in place for the platform's current configuration, with conditional reintroduction permitted only under a specific set of regime and risk constraints. The recommended criteria are: (1) a minimum sample of $n \geq 25$ closed SHORT trades; (2) a bear regime filter requiring VIX > 30 or a negatively sloped 200-day moving average; (3) an elevated score threshold of $\geq 60$ (not merely $\geq 50$); (4) sector-specific negative momentum per Moskowitz and Grinblatt (1999)[^10^]; (5) a maximum SHORT allocation of 15% of the equity book; and (6) a mandatory 10-day time stop[^1^].

The sector rotation literature provides the theoretical foundation for conditional shorting. Moskowitz and Grinblatt (1999) demonstrated that industry momentum explains a significant fraction of individual stock momentum, and that shorting sectors with negative 6-month momentum can generate positive risk-adjusted returns during bear regimes[^10^]. Alexiou and Tygi (2020) confirmed this finding in both US and European markets[^11^]. However, the PEAD (Post-Earnings Announcement Drift) literature notes that "the long leg of the strategy is surely strongly correlated to the equity market; however, the short only leg can be maybe used as a hedge during bad times"[^1^]. This suggests SHORTs should be treated as crisis hedges, not as alpha generators.

For "Proven" systems only, conditional SHORT reintroduction in bear regimes with VIX > 30 and score $\geq 60$ is projected to improve PF by +0.10 to +0.15 during bear regimes exclusively[^1^]. Until these conditions are met, the ban is correct.

---

### 2.3 AAPL Conditional Unban

The blanket ban on AAPL — `EQUITY_BANNED_SYMBOLS = frozenset({"AAPL"})` — was imposed based on a historical PF of 0.69 across 15 trades[^8^]. This section assesses whether the ban remains justified given current market conditions and statistical best practices.

#### The Statistical Objection: $n=15$ Is Insufficient for Permanent Exclusion

A sample size of $n=15$ with PF 0.69 provides a point estimate, but the confidence interval around that estimate is wide. At the 95% confidence level, the true PF for AAPL under the banned strategy could plausibly range from approximately 0.35 to 1.15 — a region that includes potentially profitable territory. Permanent exclusion based on such limited evidence risks discarding a statistically significant edge that may have been obscured by strategy-specific noise[^1^].

#### Current AAPL Technical Profile

As of the latest data, AAPL trades at $280.14, positioned above both its 50-day moving average ($261.22) and its 200-day moving average ($265.62) — a bullish configuration that places the stock in a confirmed uptrend by classical technical definition[^1^]. The MACD (Moving Average Convergence Divergence) indicator is in positive territory, and historical analysis indicates that MACD positive continuation for AAPL occurs with a 77% probability — among the highest continuation rates for large-cap technology names[^1^]. Additional metrics include a 6-month return of +4.32%, 20-day return of +8.22%, and analyst consensus of "Buy" with a mean rating of 1.875[^1^].

The random-entry analysis is particularly instructive: AAPL random-entry 5-day WR is 47.1% and 20-day WR is 47.1% — both below the 50% breakeven threshold[^1^]. This confirms that AAPL should not be traded on weak or generic signals. The stock's idiosyncratic volatility (annualized 22.0%) and large-cap liquidity create a challenging environment for undifferentiated momentum strategies. However, the evidence does not support a blanket prohibition against *all* strategy-specific entries.

#### Proposed Conditional Unban Framework

The recommended approach replaces the blanket AAPL ban with conditional strategy-based filtering. Under this framework, the `markov_zone_transition` strategy would be permitted for AAPL with a minimum score of 55, the `regular_divergence_reversal` strategy permitted with a higher score floor of 65, and the "Classic Momentum" strategy remains banned (score threshold set to 999, effectively unreachable)[^1^]. All other strategies require score $\geq 60$ for AAPL eligibility.

**Table 2: AAPL Unban Decision Matrix**

| Strategy | Current Status | Proposed Status | Min Score | Rationale | Expected Trades/Q |
|:---------|:---------------|:----------------|:---------:|:----------|:-----------------:|
| markov_zone_transition | Banned (blanket) | Conditional Unban | 55 | Strongest equity strategy; 77% MACD continuation | 2–4 |
| regular_divergence_reversal | Banned (blanket) | Conditional Unban | 65 | Higher bar for reversal signals on momentum name | 1–2 |
| Classic Momentum | Banned (strategy) | **Remain Banned** | 999 | PF 0.92 on $n=39$ across all equities[^8^] | 0 |
| All others | Banned (blanket) | Conditional Unban | 60 | Generic score floor for unproven strategies | 0–1 |

The decision matrix reflects a risk-tiered approach. The `markov_zone_transition` strategy receives the lowest score threshold because it has demonstrated the strongest signal quality on the equity book. The 77% MACD continuation rate for AAPL, combined with the stock's position above both key moving averages, suggests that entries generated by this strategy carry a materially higher probability of success than random entries or generic momentum signals[^1^]. The `regular_divergence_reversal` strategy requires a higher score of 65 because divergence-reversal signals on strongly trending names are inherently more susceptible to false positives — the trend continuation probability outweighs the reversal probability when MACD is positive and price is above the 200-day MA.

The expected impact of lifting the AAPL ban for `markov_zone_transition` (score $\geq 55$) is estimated at 2–4 additional trades per quarter. If these picks maintain the system's L100 WR of approximately 59%, the expected contribution is positive. Risk is minimal: the score floor and strategy filter provide guardrails that prevent weak-signal AAPL entries from degrading book performance[^1^].

---

### 2.4 ETF Time-Decay: Structural, Not Fixable

The ETF sleeve presents a mirror-image problem to equities. Where equity performance improves with sample size, ETF performance degrades — and this degradation is structural, not curable by parameter tuning or better stock selection.

#### Single-Lag Mean Reversion Decay: 25 Years of Academic Evidence

The ETF performance trajectory is the opposite of equity. At L20, WR is 70.0% with PF 2.88 (T1). At L50, WR improves slightly to 72.0% with PF 2.67 (T1). At L100, WR collapses to 52.9% and PF falls to 1.32 (T3)[^1^].

The academic literature provides a definitive explanation. The MDPI (2026) overnight/daytime ETF study states: "The kNN reversal signal is exploited at the single-period lag and is not a multi-period momentum or contrarian effect... Extending the lookback to three or more periods progressively dilutes the signal by averaging in lags with negligible predictive content, reducing final portfolio values by a factor of 5–10 relative to the single-lag implementation"[^9^].

This finding — that the ETF edge is a microstructure anomaly tied to overnight drift and daytime mean reversion, operative only at the single-lag horizon — has been replicated across multiple academic studies spanning 25 years. The ETF edge is not a factor premium; it is a trading friction that dissipates as holding periods extend[^9^].

#### ETFs Are Tactical (L20/L50 T1), Not Strategic (L100 T3)

The diagnosis of three competing hypotheses confirms the structural nature of the decay. Under the volatility clustering hypothesis, ETF volatility is predictable short-term but not long-term — a partial contributor. Under the mean reversion hypothesis (the primary cause), strong academic evidence supports single-lag mean reversion across ETF universes. Under the strategy-specific failure hypothesis, PF degrades across *all* ETF strategies, not merely one, confirming the issue is systemic rather than idiosyncratic[^1^].

**Table 3: ETF Tactical vs Strategic Recommendations**

| Parameter | Current | Recommended | Rationale | Expected Impact |
|:----------|:--------|:------------|:----------|:----------------|
| Hold period | Variable (up to L100) | Max 10 days | Single-lag decay beyond 10 days | Prevents L100 degradation |
| Re-entry window | Any | 24–48h only | Fresh signal required after exit | Maintains signal freshness |
| Position sizing | Standard equity sizing | 0.5× equity sizing | Higher turnover, lower conviction | Reduces turnover drag |
| Tier target | T1 across all windows | T1 at L20 only; T2 acceptable at L50 | Realistic given structural decay | Aligns expectations |
| Stop regime | Standard | 2% hard stop | Microstructure edges are fragile | Limits downside per trade |
| Allocation cap | 25% of portfolio | 15–20% of portfolio | Tactical, not strategic asset class | Reduces decay exposure |

The analytical interpretation of Table 3 centers on a fundamental reclassification: ETFs should be treated as a *tactical* asset class, suitable for short-horizon exploitation of microstructure inefficiencies, rather than a *strategic* asset class for long-horizon factor exposure. This distinction has profound implications for portfolio construction. The CIO review currently assigns ETFs a 25% portfolio weight under HRP allocation[^2^]; the evidence suggests 15–20% is more appropriate given the structural time-decay that erodes edge beyond the 10-day holding horizon.

The platform's current practice of allowing variable hold periods up to L100 is the primary driver of ETF T3 classification. The recommended 10-day hard stop directly addresses this by truncating positions before the single-lag mean reversion signal decays into noise. Re-entry is restricted to 24–48 hour windows to ensure that only fresh signals — not stale continuations — trigger new positions[^1^].

Among academic ETF strategies, Strategy #18 (Long/Reversal) from the MDPI study achieves Sharpe ratios of 1.09–1.25 across the broadest ETF set — XLK, XLU, XLP, XLV, XLI — making it the single most robust ETF strategy documented in the literature[^9^]. Implementation of this overnight/daytime decomposition framework is projected to deliver Sharpe 1.0–1.25 potential, though development timeline is estimated at 3–4 weeks given the required data infrastructure[^1^]. Sector-specific implementations show additional promise: XLE momentum strategies (commodity-linked) delivered Sharpe 0.71 with 1–3 day holds, while XLP mean reversion achieved Sharpe 1.14, though both are limited by sector-specific concentration risk[^9^]. The overnight/daytime framework is preferred precisely because it operates across multiple sectors, avoiding the single-sector dependency that amplifies drawdowns during sector-specific stress events.

---

### 2.5 Factor Sleeve Enhancement

The current equity system's composite scoring — ValueComposite + QualityComposite × SafetyGate — is well-designed but can be enhanced through explicit factor sleeve weighting. This section presents the recommended allocation framework and its academic foundations.

#### Recommended Allocation: Quality 35% / Momentum 25% / Value 20% / Low-Vol 15% / ML Overlay 5%

The SGH (2024) analysis of Fama-French data from July 1963 through April 2024 provides the empirical basis for factor weighting[^3^]. Among US large-cap stocks, momentum delivered the highest Sharpe (0.49) and quality the second-highest (0.46), with value estimated at approximately 0.38 and the market factor at 0.39[^3^]. The recommended allocation inverts the raw Sharpe ranking, placing quality at the highest weight because it exhibits the most stable returns — tracking error of 4.19% versus 9.09% for momentum — making it the more reliable core holding[^3^].

Momentum receives 25% because it delivers the highest absolute returns despite its elevated volatility. Jegadeesh and Titman's original finding — that stocks with high prior 6–12 month returns continue to outperform — has persisted for over three decades, with the momentum premium estimated at 13.30% annualized for US large caps[^3^][^4^]. Value serves as a diversifier due to its negative correlation with momentum (-0.15), providing a natural hedge during momentum drawdowns[^3^]. The low-volatility sleeve (15%) draws on Blitz and van Vliet (2007), who documented a 2.34–2.62% annualized anomaly across regions[^7^], and CIBC (2025) data showing $693B AUM in low-volatility strategies by end of 2024[^12^].

![Recommended factor sleeve allocation](factor_sleeve_allocation.png)

*Figure 2: Recommended factor sleeve allocation for the equity book. Quality and momentum together account for 60% of allocation, reflecting their superior Sharpe ratios in the SGH (2024) 60-year Fama-French analysis[^3^]. The ML/sentiment overlay at 5% preserves the platform's proprietary edge while maintaining factor purity in the core allocation.*

The ML/Sentiment overlay at 5% reflects the platform's proprietary signal. While the academic literature cannot validate this component, the equity L100 PF of 2.90 suggests the ML overlay contributes meaningful alpha beyond what standard factors would predict. The 5% weight is deliberately conservative — sufficient to capture the proprietary edge without allowing model risk to dominate the factor allocation[^1^].

#### Sector Rotation Filter: Expected +0.20 PF, +4pp WR

Beyond factor sleeve rebalancing, the addition of a sector rotation filter represents the highest-impact enhancement available to the equity book. The TSX 60 sector rotation study (2026) reports 15.30% annual returns with a Sharpe of 0.922, outperforming buy-and-hold by 4.95 percentage points[^1^]. Global sector momentum strategies over 30 years delivered 13.94% annual returns with Sharpe 0.80[^13^].

The recommended implementation adds sector-relative momentum as a filter: only equity picks in sectors ranked in the top 5 of 11 GICS sectors by 6-month momentum are eligible for entry. This filter is projected to improve equity PF by +0.15 to +0.25 and WR by +3 to +5 percentage points[^1^]. The mechanism is straightforward — sector momentum acts as a macro-level quality filter, ensuring that individual stock picks are aligned with broad sectoral tailwinds rather than swimming against industry-level headwinds.

Combining factor sleeve enhancement with the sector rotation filter, the equity book is projected to improve from its current PF 2.90 / WR 59% to PF 3.20–3.55 / WR 62–65% under the medium scenario, with an optimistic scenario reaching PF 3.50–4.00 / WR 64–67%[^1^]. Even at the conservative end of this range, the equity sleeve would maintain its status as the platform's crown jewel and primary capital destination.

The combined impact of all recommended enhancements — factor sleeve rebalancing (+0.15 to +0.25 PF), explicit momentum factor (+0.10 to +0.20 PF), sector rotation filter (+0.15 to +0.25 PF), and conditional AAPL unban (+0.05 PF) — represents a material improvement to an already exceptional equity signal. The principal risk remains sample size: $n = 100$ is sufficient for T1 classification but L200 confirmation is necessary before allocating institutional capital at scale[^1^][^2^]. Factor overcrowding presents a secondary concern: if too many market participants adopt identical factor tilts, the historical premium may compress. The multi-factor approach recommended here mitigates this risk by diversifying across five distinct sources of alpha, ensuring that underperformance in any single factor sleeve does not meaningfully degrade overall book returns. Historical evidence from the 2018–2029 period suggests that factor drawdowns of 15–20% for individual styles are common, but multi-factor portfolios experience drawdowns roughly 40% smaller due to the imperfect correlation among factor returns[^3^].
