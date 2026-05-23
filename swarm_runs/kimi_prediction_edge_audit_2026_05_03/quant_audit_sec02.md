## 2. Edge Analysis Per Asset Class

### 2.1 The Five-Gate Investability Framework

Any claim that a strategy possesses "edge" is, in quantitative finance, a statistical hypothesis that must survive multiple independent tests. Drawing on Lopez de Prado's sample-size standards [^27^], Bailey & Lopez de Prado's Deflated Sharpe Ratio framework [^49^][^51^], and the Jacquier et al. (2025) closed-form replication model [^21^], this audit evaluates every asset class through five sequential gates. A strategy must clear all five to receive an investable verdict.

**Gate 1 — Profit Factor (PF) > 1.5.** PF, defined as gross profit divided by gross loss, captures the interplay of win rate and reward-to-risk in a single metric. The literature treats PF 1.0–1.2 as breakeven territory after costs, 1.2–1.5 as the minimum deployable threshold, and above 1.5 as strong edge [^43^]. Gate 1 is set at 1.5 rather than the more lenient 1.2 to compensate for the 10–20% degradation that backtested results typically suffer in live markets due to slippage, commissions, and execution variance [^32^].

**Gate 2 — Win Rate (WR) > 50%.** While a sub-50% WR can be profitable with sufficiently high R:R, the psychological and practical challenges of sustained losing streaks—elevated risk of ruin, discipline erosion, and capacity constraints—make 50% a pragmatic floor for any strategy intended for scalable deployment [^33^].

**Gate 3 — Out-of-Sample (OOS) Sharpe > 0.** This is the decisive gate. A strategy with positive in-sample (IS) metrics but negative OOS Sharpe is, by definition, overfitted: it captured noise during training and fails on unseen data. Jacquier, Muhle-Karbe, and Mulligan (2025) demonstrate that the replication ratio—OOS Sharpe divided by IS Sharpe—increases with training-set size and true signal strength, but collapses when model complexity rises or the underlying edge is weak [^21^]. Negative OOS Sharpe is prima facie evidence of curve-fitting.

**Gate 4 — Sample Size n ≥ 100.** The Central Limit theorem establishes ~30 observations as the absolute floor for statistical inference [^27^], yet trading strategy validation demands substantially more. Industry convention holds that 100 trades provide basic reliability, while 200–500 approach institutional grade [^27^]. Strategies with n < 100 lack the statistical power to distinguish edge from random fluctuation.

**Gate 5 — Positive Quarter-Kelly Fraction.** Even a strategy that passes Gates 1–4 can warrant zero allocation if Kelly-optimal sizing turns negative. The Quarter-Kelly fraction must exceed zero for any capital deployment to be mathematically justified [^34^][^42^].

**Table 1: Five-Gate Pass/Fail Matrix**

| Asset Class | Gate 1: PF > 1.5 | Gate 2: WR > 50% | Gate 3: OOS Sharpe > 0 | Gate 4: n ≥ 100 | Gate 5: Q-Kelly > 0 | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Equity | **1.72** ✓ | **53.1%** ✓ | **+3.527** ✓ | 136 ✓ | +5.3% ✓ | **SAFE** |
| ETF | 1.32 ✗ | **52.9%** ✓ | +6.368* ✓ | 45 ✗ | +2.9% ✓ | **CAUTION** |
| Crypto B-Tier | 1.28 ✗ | 45.0% ✗ | −0.242 ✗ | **940** ✓ | +2.4% ✓ | **CAUTION** |
| Crypto A-Tier | 1.58 ✓ | 42.4% ✗ | −0.242 ✗ | 304 ✓ | +4.3% ✓ | **CAUTION** |
| Bond | **1.72** ✓ | 50.0% ✓ | N/A | 20 ✗ | +6.0% ✓ | **CAUTION** |
| Forex | 1.41 ✗ | 21.4% ✗ | **−1.406** ✗ | 195 ✓ | +3.5% ✓ | **DANGEROUS** |
| Commodity | 1.04 ✗ | 21.2% ✗ | **−2.412** ✗ | 143 ✓ | +0.4% ✓ | **DANGEROUS** |
| Crypto S-Tier | **6.80** ✓ | **70.4%** ✓ | −0.242 ✗ | 27 ✗ | +16.5% ✓ | **DANGEROUS** |
| Crypto C-Tier | 0.56 ✗ | 28.1% ✗ | −0.242 ✗ | 224 ✓ | −5.3% ✗ | **DANGEROUS** |
| Futures | N/A | N/A | N/A | 0 ✗ | N/A | **DANGEROUS** |

*ETF OOS Sharpe of 6.368 is flagged as a potential artifact due to only 12 walk-forward folds and high decay (10.8). Source: platform dashboard data, 2026-05-03; academic thresholds from [^21^][^27^][^43^][^49^][^51^].*

Only one asset class—Equity—clears all five gates. Every other asset class fails at least one criterion, and in most cases multiple. The pattern of negative OOS Sharpe across Crypto (aggregate), Forex, and Commodity is the defining signature of overfitting documented by Jacquier et al.: positive IS metrics coupled with negative OOS performance indicate that the in-sample results captured noise, not signal [^21^]. For Forex, the replication ratio is not merely below 50%—it is negative, meaning the strategy actively loses money on unseen data. The same holds for Commodity (−2.412 OOS Sharpe) and Crypto aggregate (−0.242). The "replication ratio" framework from Imperial College and Qube Research & Technologies [^21^] thus provides a rigorous theoretical foundation for what the raw metrics already suggest: these strategies lack genuine predictive power.

---

### 2.2 Equity: The Only SAFE Asset Class

Equity is the single asset class on the Antigravity platform that meets every criterion for genuine statistical edge. With a Profit Factor of 1.72—solidly within the "strong edge" 1.5–2.0 range [^43^]—and a Win Rate of 53.1%, the strategy demonstrates that it wins more often than it loses while also winning more money per win than it loses per loss. The OOS Sharpe of +3.527 is the highest across all asset classes and comfortably exceeds the institutional threshold of +1.5 cited by Dim05 and Dim11. The sample size of 136 closed trades meets the n ≥ 100 minimum, though it remains below the 200-trade institutional-grade threshold.

What distinguishes Equity most sharply from every other asset class is its walk-forward behavior. The platform's 47 walk-forward folds produce an OOS Win Rate of 57.9%—meaning the strategy actually **outperforms** on unseen data relative to its in-sample rate of 53.1%. This is the antithesis of overfitting. A consistency metric of 66.0% and a worst-fold WR of 20.0% further underscore robustness: even in the most adverse fold, the strategy remains profitable. Realized PnL stands at +233.48%, providing substantial absolute confirmation that the statistical edge has translated into actual capital growth.

The Quarter-Kelly fraction of +5.3% supports a meaningful position size without exposing the portfolio to ruin risk. Under half-Kelly sizing, Equity warrants a 25% portfolio allocation—making it the anchor position. This allocation is conservative: it reflects the reality that only one asset class has validated edge, and deploying capital beyond this concentration would mean allocating to strategies with negative or unverified OOS performance. The verdict is unambiguous: **SAFE — Scale**.

---

### 2.3 Crypto Tier Analysis

Cryptocurrency is not a monolithic asset class on this platform. Four distinct tiers operate under different parameters, and collapsing them into a single analysis would obscure critical differences. The aggregate OOS Sharpe for all crypto tiers is −0.242—a definitive overfitting signal that means the combined crypto operation destroys value on unseen data. Yet within this aggregate, each tier tells a different story.

**Table 2: Crypto Tier Breakdown**

| Tier | PF | WR | n | OOS Sharpe | Key Characteristic | Verdict |
|:---|:---:|:---:|:---:|:---:|:---|:---:|
| S-Tier | 6.80 | 70.4% | 27 | −0.242 | Survivorship filter, n=27 statistically meaningless | DANGEROUS |
| A-Tier | 1.58 | 42.4% | 304 | −0.242 | Time-decay confirmed: PF 1.98 (L50) → 1.23 (L100) | CAUTION |
| B-Tier | 1.28 | 45.0% | **940** | −0.242 | Largest sample; marginal positive expectancy at L20 | CAUTION |
| C-Tier | 0.56 | 28.1% | 224 | −0.242 | Active capital destruction; PF below 1.0 | DANGEROUS |
| **Aggregate** | — | 43.0% | **1,495** | **−0.242** | Definitive overfitting across all tiers | **DANGEROUS** |

*Source: platform dashboard data, 2026-05-03. L50/L100 refer to lookback periods (last 50/100 picks). Time-decay data from FOOLPROOF_ACTION_PLAN [^43^].*

**S-Tier (PF 6.80, WR 70.4%, n=27):** These metrics are exceptional on their face—indeed, too exceptional. With only 27 trades, the S-Tier sample falls below even the Central Limit Theorem floor of 30 observations [^27^]. A PF of 6.80 in a sample this small is almost certainly a hot streak, not reproducible edge. As Cryptorobot.ai notes in the context of backtesting, "Profit Factor above 3.0 often signals curve fitting" [^37^]. The S-Tier functions as a survivorship filter: picks that have already passed every other gate by definition look good in hindsight. This is selection bias dressed up as strategy performance. The recommended action is abandon—absorb any structural insights into B-Tier development, but do not allocate capital.

**A-Tier (PF 1.58, WR 42.4%, n=304):** The A-Tier fails Gate 2 (WR below 50%) and Gate 3 (negative OOS Sharpe). More critically, time-decay is confirmed: PF degrades from 1.98 at L50 to 1.23 at L100, approaching breakeven territory [^43^]. This pattern—adverse selection at longer horizons where low-quality picks get caught by mean reversion—indicates that the signal loses predictive power beyond a 50-pick lookback. The trajectory is toward eventual sub-1.2 PF, at which point the tier would fail Gate 1 as well. Monitor only, with a hard halt trigger if PF drops below 1.2.

**B-Tier (PF 1.28, WR 45.0%, n=940):** The B-Tier is the workhorse of the crypto operation. Its sample size of 940 exceeds the 500-trade institutional threshold and provides genuine statistical power. PF of 1.28 sits above the 1.2 minimum deployable threshold [^43^], and positive expectancy at L20 confirms marginal edge. However, the negative aggregate OOS Sharpe means even this best crypto tier degrades on unseen data. The B-Tier is viable only with an R:R 1.5–2.0 overlay (see Section 2.5), which concentrates exposure in the platform's single profitable parameter band. Without that filter, B-Tier allocation should be zero.

**C-Tier (PF 0.56, WR 28.1%, n=224):** This is a value destroyer. A PF below 1.0 means the strategy loses money on every dollar risked; at 0.56, gross losses are nearly double gross profits. The Quarter-Kelly fraction of −5.3% is deeply negative, making any allocation mathematically indefensible. The 68.5% loss rate and confirmed negative expectancy mean C-Tier trading is not merely unprofitable—it is wealth destruction. Zero allocation is mandatory.

---

### 2.4 The Broken Asset Classes

Four asset classes beyond crypto receive DANGEROUS verdicts. Their failures are structural, not cosmetic, and no amount of parameter tuning will salvage them.

**Forex (PF 0.27 post-fix, OOS Sharpe −1.406, WR 21.4%):** The 2026-04-28 resolver "fix" did not improve Forex—it revealed that Forex was never profitable. The pre-fix 0% WR was a measurement artifact (an infinite retry loop in `outcome_resolver.py` that hung all trade outcomes in limbo); the post-fix PF of 0.27 represents the true performance of a broken strategy [^271^]. This PF means the strategy loses \$3.70 for every \$1.00 of gross profit. The OOS Sharpe of −1.406 with n=195+ is definitive evidence of overfitting: with sufficient sample size, the failure cannot be attributed to bad luck. The classic pattern documented by AQR Capital Management—a moving average strategy whose Sharpe dropped from 1.2 in backtesting to −0.2 on new data [^31^]—is replicated here in starker form. Six days of post-fix data are statistically inadequate (45–65 trades at ~46% WR produce a 95% confidence interval of [32%, 60%], indistinguishable from random) [^295^]. The recommended action is **HALT** until June 1, 2026, at minimum, with any reassessment requiring 200+ post-fix trades.

**Commodity (PF 1.04, OOS Sharpe −2.412, WR 21.2%):** Commodity is the worst performer by OOS Sharpe (−2.412) across the entire platform. The in-sample PF of 1.04 sits in "breakeven territory" [^43^], meaning gross profit barely exceeds gross loss; after costs, this is certainly a losing strategy. The 58% flat exit rate—more than half of all "trades" exit at breakeven—is a structural failure mode suggesting the strategy initiates positions then exits indiscriminately, lacking genuine conviction. The specific strategy `cta_commodity_momentum_term` carries a PF of 0.02, which is not merely broken but farcical. Verdict: **ABANDON**.

**Bond (PF 1.72, WR 50.0%, n=20):** Bond metrics appear strong but the sample is critically insufficient. With only 10 closed trades (18–20 total), the data sit below the CLT floor [^27^]. The PF of 1.72 and WR of 50% are statistically meaningless—they could result from 1–2 lucky trades. No OOS Sharpe data is available. Verdict: **CAUTION — Monitor Only**. Require 100+ trades before any confidence assignment.

**Futures (n=2):** Two trades constitute no viable dataset. Trading Futures without any backtested or live track record is equivalent to random betting. Verdict: **HALT** until a minimum viable strategy is developed with 200+ backtested trades and positive OOS Sharpe across 20+ walk-forward folds.

---

### 2.5 The Golden Finding: R:R 1.5–2.0 Band

Among the most consequential discoveries in this audit is the extreme concentration of alpha within a narrow R:R band. Platform-wide shadow data (n=253) reveal that the 1.5–2.0 R:R interval generates a PF of 5.81, a Kelly fraction of +47.2%, and an average PnL of +4.98%. Above 2.0 R:R, the picture inverts catastrophically: PF collapses to 0.35 and the average trade loses −17.88%. This is not a gradual degradation—it is a cliff.

**Table 3: Performance by R:R Band**

| R:R Band | Profit Factor | Kelly f* | Avg PnL per Trade | Implied Win Rate | Quarter-Kelly | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| < 1.5 | 1.01 | −1.6% | −0.12% | ~40% | 0% (BLOCKED) | Unprofitable |
| **1.5 – 2.0** | **5.81** | **+47.2%** | **+4.98%** | **~77%** | **+11.8%** | **SWEET SPOT** |
| > 2.0 | 0.35 | −22.8% | −17.88% | ~12% | 0% (BLOCKED) | Catastrophic |

*Source: shadow data analysis n=253 from FOOLPROOF_ACTION_PLAN. Kelly derived from f* = (p(b+1) − 1) / b where p = PF/(PF+b). Quarter-Kelly represents recommended maximum position size [^201^][^210^].*

The 1.5–2.0 band's profitability is mathematically verifiable. With PF = 5.81 and average R:R of 1.75, the implied win rate is approximately 76.85% (derived from p = 5.81 / (5.81 + 1.75)). Full Kelly computes to 63.6%, making the platform's Quarter-Kelly allocation of 11.8% conservative by roughly 26%—it sits between Quarter- and Eighth-Kelly, a prudent fraction for a multi-asset platform with estimation uncertainty [^201^][^210^]. Monte Carlo simulation of 10,000 paths at this sizing produces a median final equity of 2.564x after one year, with zero paths hitting the 10% drawdown halt threshold.

The catastrophe above 2.0 R:R has four reinforcing causes. First, asymmetric execution: wide stops get hit more frequently than backtests suggest because theoretical R:R rarely matches realized R:R. Second, time decay: longer holding periods increase exposure to gap risk, overnight events, and carry costs. Third, behavioral bias: traders take profits early on winning high-R:R trades (realized R:R far below target) but let losers run to full stop. Fourth, fat-tail risk: wide stops magnify single-event damage [^143^][^230^]. The breakeven analysis is damning: at R:R 2.5, even a PF of 1.0 requires a 28.6% WR, while the platform achieves only ~12%—a gap of 16.6 percentage points that no parameter tweak can close.

**Why lowering the floor to 1.25 was catastrophically wrong.** The FOOLPROOF_ACTION_PLAN originally recommended lowering the R:R floor from 1.5 to 1.25; independent verification corrected this. The 1.25–1.5 band produces a PF of 1.01 and Kelly of −1.6%—essentially breakeven before costs and unprofitable after. Treating this band as tradeable would have routed capital into noise, diluting the 1.5–2.0 alpha with marginal trades. The corrected configuration—hard floor at 1.5, hard ceiling at 2.0—should be implemented immediately with full traffic deployment.

---

### 2.6 Recommended Capital Allocation

The allocation below synthesizes the Five-Gate analysis, crypto tier breakdown, R:R band findings, and Kelly-derived position limits into a single deployable framework. It is deliberately conservative: capital is reserved for proven edge, not distributed in equal portions across broken strategies.

**Table 4: Final Capital Allocation Matrix**

| Asset Class | Five-Gate Status | Quarter-Kelly | Allocation | Rationale |
|:---|:---:|:---:|:---:|:---|
| **Equity** | ALL PASS | +5.3% | **25%** | Only validated edge; OOS Sharpe +3.527; primary alpha source |
| **ETF** | 2/5 FAIL (n, OOS artifact) | +2.9% | **5%** | Test allocation only; 12 folds insufficient; reassess at 20+ folds |
| Crypto B-Tier | 2/5 FAIL (PF, WR, OOS) | +2.4% | **0%** | Halt until aggregate OOS Sharpe turns positive |
| Crypto A-Tier | 3/5 FAIL (WR, OOS) | +4.3% | **0%** | Halt until PF decay stabilizes above 1.5 |
| Forex | 4/5 FAIL | +3.5% | **0%** | HALT until June 1 reassessment; PF 0.27 post-fix |
| Commodity | 4/5 FAIL | +0.4% | **0%** | ABANDON; OOS Sharpe −2.412 irredeemable |
| Bond | 2/5 FAIL (n) | +6.0% | **0%** | Insufficient data; n=20 statistically meaningless |
| Crypto S-Tier | 2/5 FAIL (n, OOS) | +16.5% | **0%** | ABANDON; n=27 is noise, not signal |
| Crypto C-Tier | 4/5 FAIL | −5.3% | **0%** | BLOCKED; negative Kelly = wealth destruction |
| Futures | 5/5 FAIL (no data) | N/A | **0%** | No strategy exists to allocate to |
| **Cash / Reserve** | — | — | **70%** | Dry powder for validated opportunities |

*Source: synthesized from Five-Gate analysis (Section 2.1), Kelly calculations (Dim08), and R:R band findings (Section 2.5). Allocation percentages reflect half-Kelly sizing as industry standard [^35^].*

The 70% cash reserve reflects five factors. First, only one asset class (Equity) has validated edge sufficient for real-money deployment at scale. Second, half-Kelly is the industry standard to reduce drawdown risk—full Kelly can produce 60%+ drawdowns [^35^]. Third, OOS uncertainty in all non-Equity asset classes demands a defensive posture. Fourth, the prevalence of negative OOS Sharpe across three of five asset classes with data suggests systemic overfitting in the platform's strategy development pipeline. Fifth, capital preservation enables rapid redeployment when other asset classes achieve OOS validation.

**Rebalancing triggers** govern when this allocation may be revised. Equity allocation may increase beyond 25% only if OOS Sharpe remains above +2.0 for 90 consecutive days with n exceeding 200. ETF allocation may increase from 5% to 10% if OOS Sharpe stabilizes below 3.0 (the current 6.368 is suspected artifact) with 20+ walk-forward folds and decay below 5.0. Crypto B-Tier may receive a 5% test allocation only if aggregate OOS Sharpe turns positive and holds for 60 days. Forex may be reconsidered on June 1, 2026, contingent on 200+ post-fix trades with PF above 1.2 and OOS Sharpe above zero. Any asset class dropping below its gate thresholds for 14 consecutive days triggers automatic reduction to zero. These are hard rules, not guidelines: the platform's history of deploying strategies with negative OOS Sharpe makes algorithmic discipline essential.
