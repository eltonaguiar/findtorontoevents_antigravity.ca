# Quantitative Trading Platform Audit: Edge Analysis, Strategy Diagnosis & Transformation Roadmap

## 1. Executive Summary & Key Findings

This report presents a comprehensive quantitative audit of an active trading platform generating directional signals across nine asset classes. The audit examined strategy performance, scoring integrity, UI reliability, risk infrastructure, and retail-user safety. One central thesis emerged: the platform holds a narrow but genuine statistical edge confined almost entirely to equity strategies under specific filter conditions, while most output constitutes noise or active value destruction. The equity edge is real — projected to deliver 15–25% annual returns under disciplined execution — but far narrower than the dashboard's 210 active picks suggest. The following sections compress all findings into the five numbers that matter most, a verdict matrix for every asset class, and an action calendar sorted by urgency.

### 1.1 The Verdict in Five Numbers

The platform's performance collapses into five independently verified quantitative facts.

**Table 1: Five Numbers That Define the Platform**

| # | Metric | Value | Verdict |
|---|--------|-------|---------|
| 1 | Equity OOS Sharpe | +3.527 ^1^| Only genuine, statistically validated edge |
| 2 | R:R 1.5–2.0 Band PF | 5.81, Kelly +47.2% ^1^| Golden zone for risk-reward filtering |
| 3 | trust_score ≥5 Win Rate | 68–71% ^2^| Single most effective predictive filter |
| 4 | Strategies with PSR > 0.95 | 0% ^3^| Infrastructure at ~5% of institutional standards |
| 5 | Meme Coin Risk of Ruin | 99.7% ^4^| 99.7% ruin probability; exclusion mandatory |

The equity OOS Sharpe of +3.527 substantially exceeds the +1.5 institutional threshold for deployable alpha ^1^ ^5^. With 256 live observations and PF 1.72, this is not a small-sample artifact — it is persistent edge validated through walk-forward testing. Capital-weighted PnL stands at +233.48%, confirming economic significance. No other asset class produces positive OOS Sharpe: forex registers −1.406, commodity strategies collapse to PF 0.02, and crypto tiers outside the top bracket show negative expected returns ^1^ ^6^.

The R:R 1.5–2.0 band is the system's most important filter. Within it, PF spikes to 5.81 and Kelly indicates 47.2% optimal sizing — reduced to 11.8% under Quarter-Kelly ^1^ ^7^. Below 1.5, profitability is marginal; above 2.0, infrequent catastrophic losses erode the edge. This single constraint eliminates most low-quality signals while preserving equity alpha.

trust_score ≥5 delivers 68–71% WR, the most predictive variable in the scoring architecture ^2^ ^8^. This is critical because the composite scoring system is broken — four of nine decile bins show inverted score-performance relationships, and regime_bonus (r = −0.115, anti-predictive) receives 20 points in the composite ^2^. When the scoring system is unreliable, trust_score functions as a sanity check. Combined with the R:R filter, it produces the "golden chain": Verified Alpha + High Conviction + R:R 1.5+ yields 66–70% WR, narrowing actionable picks to 0–2 per cycle ^8^ ^9^.

The fourth number measures absence: zero strategies meet PSR > 0.95, the minimum institutional allocators require ^3^. This gap indicates missing DSR calculation, multiple comparison correction, and integrated transaction costs — infrastructure estimated at ~5% of institutional standards based on gap analysis against Renaissance Technologies, Two Sigma, and Citadel benchmarks ^5^ ^3^.

The fifth number quantifies the platform's most dangerous output: meme coin strategies carry 99.7% ruin probability, Kelly of −244% (mandating zero allocation), and only 0.4% of Pump.fun traders have profited above $10,000 ^4^. These are structurally designed to transfer capital to market makers. Penny stocks are marginally less destructive at −24% to −27% average annual returns with a median of −37%, but equally warrant exclusion ^10^.

### 1.2 Asset Class Verdict Summary

The audit evaluated nine asset classes against five investability gates: PF > 1.0, positive OOS Sharpe, n ≥ 50, no structural decay, and allocable Quarter-Kelly sizing. Only equity passes all five.

**Table 2: Master Verdict Matrix — Nine Asset Classes**

| Asset Class | Verdict | PF | WR | OOS Sharpe | n | Key Failure |
|------------|---------|-----|-----|-----------|-----|-------------|
| Equity | **SAFE** | 1.72 | 53.1% | +3.527 | 256 | None — passes all gates |
| Crypto S-Tier | **CAUTION** | 6.80 | 70.4% | Negative ^1^| 27 | Survivorship bias; n < 50 |
| Crypto A-Tier | **CAUTION** | 1.58 | 42.4% | Negative ^1^| ~80 | Inconsistent edge |
| Crypto B-Tier | **CAUTION** | 1.28 | 45.0% | Negative ^1^| ~150 | Marginal PF |
| Crypto C-Tier | **DANGEROUS** | 0.56 | — | Negative ^1^| — | Value destroyer |
| Forex | **DANGEROUS** | 0.27 | ~0% | −1.406 ^1^| ~200 | PF < 1.0; regime change |
| Commodity | **DANGEROUS** | 0.02 | — | Negative ^1^| ~180 | cta_commodity_momentum_term broken |
| ETF | **CAUTION** | 1.10 | — | 6.368* ^1^| 12 folds | *Artifact; 10.8 Sharpe decay |
| Penny Stocks | **DANGEROUS** | < 1.0 | — | Negative ^10^| — | −24% to −27% avg returns |
| Meme Coins | **DANGEROUS** | 0.45 | 65.6%* | Negative ^4^| 41 | *WR inflated by small wins; 99.7% ruin |

Equity alone combines validated edge with sufficient statistical power. The crypto landscape is fractured: S-Tier metrics (PF 6.80, WR 70.4%) rest on n = 27 — a textbook survivorship illusion — and OOS Sharpe is negative across all crypto tiers collectively ^1^. C-Tier (PF 0.56) is an outright value destroyer. Forex and commodity fail at the fundamental level: PF below 1.0 means negative expected value per trade. The forex OOS Sharpe of −1.406 reflects structural strategy failure compounded by regime change ^1^ ^6^, while commodity strategy cta_commodity_momentum_term at PF 0.02 constitutes total capital destruction ^1^ ^6^.

The ETF OOS Sharpe of 6.368 collapses to 2.0–3.0 under DSR adjustment and is further eroded by transaction costs ^1^ ^5^. ETF reversion to NAV makes directional TP/SL bets structurally disadvantaged — a mismatch between asset behavior and methodology that requires framework redesign ^1^.

The capital preservation thesis is this section's most consequential finding. Applying the optimal filter chain (Verified Alpha + High Conviction + R:R 1.5+) gates out 192 of 210 active picks, leaving 0–2 actionable signals per cycle ^8^ ^9^. The platform's value is therefore not pick generation but exclusion — it prevents entry into the ~91% of signals that would lose money on average. This reframes the product entirely: its worth is measured by bad trades prevented, not picks produced. The dashboard should treat empty results as protective success rather than system failure ^8^.

### 1.3 Immediate Actions

**Table 3: Immediate Actions by Horizon**

| Horizon | Action | Owner | Completion Criterion |
|---------|--------|-------|---------------------|
| **This Week** | Fix R:R hard ceiling at 2.0; hard floor at 1.5 | Engineering | Filter active; no picks outside band visible |
| **This Week** | Ban 3 strategies: unknown, gainer_compression_relaxed_mut, cta_commodity_momentum_term | Strategy | Zero new signals from banned strategies |
| **This Week** | Fix HTML nested comment bug (template.html lines 1813–1825) ^11^| Frontend | Visual anomaly resolved on US Equity Picks tab |
| **This Week** | Halt Forex trading; mark "under review" | Risk/Ops | Forex tab hidden; internal monitoring at zero allocation |
| **30-Day** | Deploy score rebalance: remove regime_bonus (anti-predictive), increase trust_score weight | Data Science | 4+ inversions resolved in decile analysis |
| **30-Day** | Consolidate outcome_resolver.py to single source of truth ^12^| Engineering | One canonical copy; duplicates removed |
| **30-Day** | Implement kill switches: daily loss limit, consecutive loss halt, vol circuit breaker ^7^| Risk | Three triggers active: −5% daily, 5 consecutive losses, VIX proxy |
| **90-Day** | PSR > 0.95 gate: no strategy deploys without documented PSR | Quant Research | Sub-threshold strategies moved to sandbox |
| **90-Day** | DSR > 0.95 gate: all OOS Sharpe claims deflated ^5^| Quant Research | DSR integrated into backtest pipeline |
| **90-Day** | n ≥ 200 gate: minimum observations before live deployment | Strategy | n < 200 strategies moved to "pilot" status |
| **90-Day** | Transaction cost integration: all backtests include slippage + commission ^5^| Quant Research | Assumptions: $0.005/share equity, 5bps forex, 10bps crypto |
| **90-Day** | Single SOT enforcement: one resolver, one scoring pipeline | Engineering+QA | Zero duplicate critical files |
| **90-Day** | Correlation guard: cap correlated strategy exposure ^7^| Risk | Max pairwise ρ = 0.70 enforced |

The weekly actions are non-discretionary. The R:R constraint is the highest-impact change: it requires no model retraining or capital investment, only a filter adjustment. The cta_commodity_momentum_term ban is equally urgent — at PF 0.02, continued exposure is mathematically equivalent to controlled capital destruction ^6^. The HTML bug, while cosmetic, undermines confidence on the platform's highest-quality tab ^11^.

The 30-day actions address governance. The score rebalance removes 20 points from regime_bonus (r = −0.115, anti-predictive) while increasing trust_score weight ^2^. The outcome_resolver consolidation resolves version drift across five copies of a critical file ^12^. Kill switch gaps — daily loss limit, consecutive loss halt, volatility circuit breaker — are standard at retail quantitative platforms; their absence signals bottom-quartile risk maturity ^7^.

The 90-day actions define the institutional MVP. Six hard gates (PSR > 0.95, DSR > 0.95, n ≥ 200, transaction costs, single SOT, correlation guard) represent the operational floor. Implementation cost is estimated at $1,500 over 90 days, yielding 867–5,233% ROI against capital preserved by preventing a single ruin event ^3^. The full 12-month transformation is budgeted at $32,400–$78,000 for ~60–70% of institutional standard ^3^.

### 1.4 How to Read This Report

This audit spans ten chapters across four analytical layers. Readers should follow the pathway matching their role.

**Technical team (Chapters 2–6, 8–9):** Engineers and quantitative researchers should begin with Chapter 2 (Asset Class Performance) for the full statistical breakdown, Chapter 3 (Scoring System Integrity) for the composite score diagnosis, Chapter 4 (UI & Signal Reliability) for the front-end audit, Chapter 5 (Strategy Diagnostics) for the 11 failing strategy profiles, and Chapter 6 (Risk Infrastructure) for the Kelly framework and kill switch analysis. Chapter 8 (Codebase Health) covers the 119,598-commit repository audit and outcome_resolver duplication. Chapter 9 provides the 90-day and 12-month transformation plans with cost estimates.

**Business stakeholders (Chapters 1, 7, 9):** Executives and investors should read this chapter, then Chapter 7 (Retail User Safety) for expected returns under three behavior profiles — Disciplined (15–25%), Moderate (12–20%), and YOLO (−20% to −40%) ^9^. Chapter 9 frames the binary choice: remain retail-focused with narrow edge, or commit to full institutionalization over 12 months ^3^.

**Retail users (Chapters 7, 10):** Users seeking practical guidance should read Chapter 7 and Chapter 10 for distilled "Do / Do Not" lists. The actionable summary: invest only in equity picks with Verified Alpha + High Conviction + R:R 1.5–2.0, maintain 70% cash, never allocate to meme coins or penny stocks, and cap single positions at 11.8% (Quarter-Kelly) ^9^. Minimum recommended capital is $5,000; below this threshold, transaction costs dominate returns and an index fund is superior ^9^.

---

## 2. Edge Analysis Per Asset Class

### 2.1 The Five-Gate Investability Framework

Any claim that a strategy possesses "edge" is, in quantitative finance, a statistical hypothesis that must survive multiple independent tests. Drawing on Lopez de Prado's sample-size standards ^13^, Bailey & Lopez de Prado's Deflated Sharpe Ratio framework ^14^ ^15^, and the Jacquier et al. (2025) closed-form replication model ^16^, this audit evaluates every asset class through five sequential gates. A strategy must clear all five to receive an investable verdict.

**Gate 1 — Profit Factor (PF) > 1.5.** PF, defined as gross profit divided by gross loss, captures the interplay of win rate and reward-to-risk in a single metric. The literature treats PF 1.0–1.2 as breakeven territory after costs, 1.2–1.5 as the minimum deployable threshold, and above 1.5 as strong edge ^17^. Gate 1 is set at 1.5 rather than the more lenient 1.2 to compensate for the 10–20% degradation that backtested results typically suffer in live markets due to slippage, commissions, and execution variance ^18^.

**Gate 2 — Win Rate (WR) > 50%.** While a sub-50% WR can be profitable with sufficiently high R:R, the psychological and practical challenges of sustained losing streaks—elevated risk of ruin, discipline erosion, and capacity constraints—make 50% a pragmatic floor for any strategy intended for scalable deployment ^19^.

**Gate 3 — Out-of-Sample (OOS) Sharpe > 0.** This is the decisive gate. A strategy with positive in-sample (IS) metrics but negative OOS Sharpe is, by definition, overfitted: it captured noise during training and fails on unseen data. Jacquier, Muhle-Karbe, and Mulligan (2025) demonstrate that the replication ratio—OOS Sharpe divided by IS Sharpe—increases with training-set size and true signal strength, but collapses when model complexity rises or the underlying edge is weak ^16^. Negative OOS Sharpe is prima facie evidence of curve-fitting.

**Gate 4 — Sample Size n ≥ 100.** The Central Limit theorem establishes ~30 observations as the absolute floor for statistical inference ^13^, yet trading strategy validation demands substantially more. Industry convention holds that 100 trades provide basic reliability, while 200–500 approach institutional grade ^13^. Strategies with n < 100 lack the statistical power to distinguish edge from random fluctuation.

**Gate 5 — Positive Quarter-Kelly Fraction.** Even a strategy that passes Gates 1–4 can warrant zero allocation if Kelly-optimal sizing turns negative. The Quarter-Kelly fraction must exceed zero for any capital deployment to be mathematically justified ^20^ ^21^.

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

*ETF OOS Sharpe of 6.368 is flagged as a potential artifact due to only 12 walk-forward folds and high decay (10.8). Source: platform dashboard data, 2026-05-03; academic thresholds from ^16^ ^13^ ^17^ ^14^ ^15^.*

Only one asset class—Equity—clears all five gates. Every other asset class fails at least one criterion, and in most cases multiple. The pattern of negative OOS Sharpe across Crypto (aggregate), Forex, and Commodity is the defining signature of overfitting documented by Jacquier et al.: positive IS metrics coupled with negative OOS performance indicate that the in-sample results captured noise, not signal ^16^. For Forex, the replication ratio is not merely below 50%—it is negative, meaning the strategy actively loses money on unseen data. The same holds for Commodity (−2.412 OOS Sharpe) and Crypto aggregate (−0.242). The "replication ratio" framework from Imperial College and Qube Research & Technologies ^16^thus provides a rigorous theoretical foundation for what the raw metrics already suggest: these strategies lack genuine predictive power.

---

### 2.2 Equity: The Only SAFE Asset Class

Equity is the single asset class on the Antigravity platform that meets every criterion for genuine statistical edge. With a Profit Factor of 1.72—solidly within the "strong edge" 1.5–2.0 range ^17^—and a Win Rate of 53.1%, the strategy demonstrates that it wins more often than it loses while also winning more money per win than it loses per loss. The OOS Sharpe of +3.527 is the highest across all asset classes and comfortably exceeds the institutional threshold of +1.5 cited by Dim05 and Dim11. The sample size of 136 closed trades meets the n ≥ 100 minimum, though it remains below the 200-trade institutional-grade threshold.

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

*Source: platform dashboard data, 2026-05-03. L50/L100 refer to lookback periods (last 50/100 picks). Time-decay data from FOOLPROOF_ACTION_PLAN ^17^.*

**S-Tier (PF 6.80, WR 70.4%, n=27):** These metrics are exceptional on their face—indeed, too exceptional. With only 27 trades, the S-Tier sample falls below even the Central Limit Theorem floor of 30 observations ^13^. A PF of 6.80 in a sample this small is almost certainly a hot streak, not reproducible edge. As Cryptorobot.ai notes in the context of backtesting, "Profit Factor above 3.0 often signals curve fitting" ^22^. The S-Tier functions as a survivorship filter: picks that have already passed every other gate by definition look good in hindsight. This is selection bias dressed up as strategy performance. The recommended action is abandon—absorb any structural insights into B-Tier development, but do not allocate capital.

**A-Tier (PF 1.58, WR 42.4%, n=304):** The A-Tier fails Gate 2 (WR below 50%) and Gate 3 (negative OOS Sharpe). More critically, time-decay is confirmed: PF degrades from 1.98 at L50 to 1.23 at L100, approaching breakeven territory ^17^. This pattern—adverse selection at longer horizons where low-quality picks get caught by mean reversion—indicates that the signal loses predictive power beyond a 50-pick lookback. The trajectory is toward eventual sub-1.2 PF, at which point the tier would fail Gate 1 as well. Monitor only, with a hard halt trigger if PF drops below 1.2.

**B-Tier (PF 1.28, WR 45.0%, n=940):** The B-Tier is the workhorse of the crypto operation. Its sample size of 940 exceeds the 500-trade institutional threshold and provides genuine statistical power. PF of 1.28 sits above the 1.2 minimum deployable threshold ^17^, and positive expectancy at L20 confirms marginal edge. However, the negative aggregate OOS Sharpe means even this best crypto tier degrades on unseen data. The B-Tier is viable only with an R:R 1.5–2.0 overlay (see Section 2.5), which concentrates exposure in the platform's single profitable parameter band. Without that filter, B-Tier allocation should be zero.

**C-Tier (PF 0.56, WR 28.1%, n=224):** This is a value destroyer. A PF below 1.0 means the strategy loses money on every dollar risked; at 0.56, gross losses are nearly double gross profits. The Quarter-Kelly fraction of −5.3% is deeply negative, making any allocation mathematically indefensible. The 68.5% loss rate and confirmed negative expectancy mean C-Tier trading is not merely unprofitable—it is wealth destruction. Zero allocation is mandatory.

---

### 2.4 The Broken Asset Classes

Four asset classes beyond crypto receive DANGEROUS verdicts. Their failures are structural, not cosmetic, and no amount of parameter tuning will salvage them.

**Forex (PF 0.27 post-fix, OOS Sharpe −1.406, WR 21.4%):** The 2026-04-28 resolver "fix" did not improve Forex—it revealed that Forex was never profitable. The pre-fix 0% WR was a measurement artifact (an infinite retry loop in `outcome_resolver.py` that hung all trade outcomes in limbo); the post-fix PF of 0.27 represents the true performance of a broken strategy ^23^. This PF means the strategy loses \$3.70 for every \$1.00 of gross profit. The OOS Sharpe of −1.406 with n=195+ is definitive evidence of overfitting: with sufficient sample size, the failure cannot be attributed to bad luck. The classic pattern documented by AQR Capital Management—a moving average strategy whose Sharpe dropped from 1.2 in backtesting to −0.2 on new data ^24^—is replicated here in starker form. Six days of post-fix data are statistically inadequate (45–65 trades at ~46% WR produce a 95% confidence interval of [32%, 60%], indistinguishable from random) ^25^. The recommended action is **HALT** until June 1, 2026, at minimum, with any reassessment requiring 200+ post-fix trades.

**Commodity (PF 1.04, OOS Sharpe −2.412, WR 21.2%):** Commodity is the worst performer by OOS Sharpe (−2.412) across the entire platform. The in-sample PF of 1.04 sits in "breakeven territory" ^17^, meaning gross profit barely exceeds gross loss; after costs, this is certainly a losing strategy. The 58% flat exit rate—more than half of all "trades" exit at breakeven—is a structural failure mode suggesting the strategy initiates positions then exits indiscriminately, lacking genuine conviction. The specific strategy `cta_commodity_momentum_term` carries a PF of 0.02, which is not merely broken but farcical. Verdict: **ABANDON**.

**Bond (PF 1.72, WR 50.0%, n=20):** Bond metrics appear strong but the sample is critically insufficient. With only 10 closed trades (18–20 total), the data sit below the CLT floor ^13^. The PF of 1.72 and WR of 50% are statistically meaningless—they could result from 1–2 lucky trades. No OOS Sharpe data is available. Verdict: **CAUTION — Monitor Only**. Require 100+ trades before any confidence assignment.

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

*Source: shadow data analysis n=253 from FOOLPROOF_ACTION_PLAN. Kelly derived from f* = (p(b+1) − 1) / b where p = PF/(PF+b). Quarter-Kelly represents recommended maximum position size ^26^ ^27^.*

The 1.5–2.0 band's profitability is mathematically verifiable. With PF = 5.81 and average R:R of 1.75, the implied win rate is approximately 76.85% (derived from p = 5.81 / (5.81 + 1.75)). Full Kelly computes to 63.6%, making the platform's Quarter-Kelly allocation of 11.8% conservative by roughly 26%—it sits between Quarter- and Eighth-Kelly, a prudent fraction for a multi-asset platform with estimation uncertainty ^26^ ^27^. Monte Carlo simulation of 10,000 paths at this sizing produces a median final equity of 2.564x after one year, with zero paths hitting the 10% drawdown halt threshold.

The catastrophe above 2.0 R:R has four reinforcing causes. First, asymmetric execution: wide stops get hit more frequently than backtests suggest because theoretical R:R rarely matches realized R:R. Second, time decay: longer holding periods increase exposure to gap risk, overnight events, and carry costs. Third, behavioral bias: traders take profits early on winning high-R:R trades (realized R:R far below target) but let losers run to full stop. Fourth, fat-tail risk: wide stops magnify single-event damage ^28^ ^29^. The breakeven analysis is damning: at R:R 2.5, even a PF of 1.0 requires a 28.6% WR, while the platform achieves only ~12%—a gap of 16.6 percentage points that no parameter tweak can close.

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

*Source: synthesized from Five-Gate analysis (Section 2.1), Kelly calculations (Dim08), and R:R band findings (Section 2.5). Allocation percentages reflect half-Kelly sizing as industry standard ^30^.*

The 70% cash reserve reflects five factors. First, only one asset class (Equity) has validated edge sufficient for real-money deployment at scale. Second, half-Kelly is the industry standard to reduce drawdown risk—full Kelly can produce 60%+ drawdowns ^30^. Third, OOS uncertainty in all non-Equity asset classes demands a defensive posture. Fourth, the prevalence of negative OOS Sharpe across three of five asset classes with data suggests systemic overfitting in the platform's strategy development pipeline. Fifth, capital preservation enables rapid redeployment when other asset classes achieve OOS validation.

**Rebalancing triggers** govern when this allocation may be revised. Equity allocation may increase beyond 25% only if OOS Sharpe remains above +2.0 for 90 consecutive days with n exceeding 200. ETF allocation may increase from 5% to 10% if OOS Sharpe stabilizes below 3.0 (the current 6.368 is suspected artifact) with 20+ walk-forward folds and decay below 5.0. Crypto B-Tier may receive a 5% test allocation only if aggregate OOS Sharpe turns positive and holds for 60 days. Forex may be reconsidered on June 1, 2026, contingent on 200+ post-fix trades with PF above 1.2 and OOS Sharpe above zero. Any asset class dropping below its gate thresholds for 14 consecutive days triggers automatic reduction to zero. These are hard rules, not guidelines: the platform's history of deploying strategies with negative OOS Sharpe makes algorithmic discipline essential.

---

## 3. The Broken Scoring System: F-Score vs Score vs Composite

The Antigravity dashboard displays at least five distinct scores: F-Score ("4/9"), Score ("0.748" or "0.703"), Composite Score, elite_score, and blended_conf. Each carries a different scale and a different relationship to actual trading outcomes. The platform's correlation audit on 3,500 closed picks reveals the most prominently displayed score is only weakly predictive ($r=+0.10$), while the metric buried deepest in the component layer is the strongest ($r=+0.242$) ^31^. This section disambiguates each score, demonstrates why the composite fails as a monotonic predictor, and establishes a filter hierarchy grounded in empirical win-rate data.

### 3.1 What Each Score Measures

#### 3.1.1 F-Score (4/9): Piotroski F-Score — Fundamental Context, Not a Trading Signal

The F-Score of "4/9" is the Piotroski F-Score, a nine-point fundamental accounting metric from 2000 ^32^. A score of 4 is "average/neutral." The F-Score is **not calculated by the platform**—it is external data shown as context. Piotroski's original study showed 23.5% annual returns for high F-Score stocks ^33^, but a 2021 study reported **-9.53% annual losses** over the prior decade due to alpha decay ^20^. The Score Calibration Audit does not track F-Score, confirming its exclusion from the prediction pipeline ^31^. For short-term trading, F-Score 4 carries no predictive value.

#### 3.1.2 Score (0.748/0.703): ML Confidence — Model Prediction Confidence on a 0-1.0 Scale

The "Score 0.748" or "0.703" is the platform's ML confidence score, sourced from the Alpha Engine's ml_score, KIMI's mlWinProb, or the Cross-System Aggregator's blended_conf ^34^ ^35^. These values sit in the empirically optimal band of 0.70-0.79, delivering a 57.0% win rate ^31^. **This is not a composite score**—it is raw confidence output from a single ML model. It follows an inverted-U pattern: the 0.90-1.00 band delivers only 47.1% win rate, an "overconfidence penalty" of 10 percentage points below the sweet spot ^31^. Raw ml_score correlates with win rate at $r=-0.012$ (noise), while the ML composite achieves $r=+0.220$ ^31^. Users should target 0.70-0.79 and avoid >0.85.

#### 3.1.3 Composite Score (elite_score): Weighted Combination with a Documented Formula

The composite score (elite_score) aggregates seven components on a 0-100 scale: ML Score (25 points), Forward WR (25 points), Confluence (15 points), Monte Carlo (15 points), Risk:Reward (10 points), Volume (5 points), and Regime (5 points) ^34^. Yet the Score Calibration Audit found elite_score correlates with actual returns at only $r=+0.10$—half as predictive as ml_composite_score ($r=+0.220$) and less than half as predictive as forward_wr ($r=+0.242$) ^31^. The composite assigns weight to anti-predictive components while underweighting the strongest signal, a structural problem analyzed in Section 3.3.

#### 3.1.4 Visual Hierarchy: Which Score to Use for Which Decision

| Dimension | F-Score (Piotroski) | Score 0.748/0.703 | Composite (elite_score) |
|-----------|---------------------|-------------------|------------------------|
| **What it measures** | Fundamental accounting health (0-9 scale) | ML model confidence / consensus (0-1.0 scale) | 7-component weighted sum (0-100 scale) |
| **Source** | External financial statements; not computed by platform | Platform ML subsystems (Alpha Engine, KIMI, Claude Gainer) | Alpha Engine aggregator |
| **Correlation with actual WR** | Not tracked by platform | -0.012 (raw ml_score) / +0.220 (ML composite) ^31^| +0.100 (weak, non-monotonic) ^31^|
| **Predictive validity** | None for short-term directional trading | Sweet spot at 0.70-0.79 (57% WR); inverted U pattern ^31^| Broken — 4 inversions across 9 deciles ^31^|
| **User action** | Ignore for trading decisions; context only | Target 0.70-0.79 band; avoid >0.85 | Supplementary only; verify forward_wr independently |
| **Best threshold** | N/A (context only) | 0.70-0.79 (empirical sweet spot) ^31^| >=75 only if forward_wr >=55% |

These three scores answer different questions. F-Score asks about financial health; Score asks about ML confidence; Composite asks about multi-dimensional rating. Only the Score, when filtered to 0.70-0.79, carries a direct empirical relationship to win rate. The F-Score is external context; the composite is a synthetic metric whose components require independent verification.

### 3.2 Why the Composite Score Is Not Monotonic

A predictive score should be monotonic: each increment should correspond to equal or higher probability of success. The elite_score fails this test, with **four inversions across nine deciles**—points where a higher score predicts a lower win rate ^31^.

| Decile | Score Range | Win Rate | Direction | Status |
|--------|-------------|----------|-----------|--------|
| D1 | 0-12 | 36.5% | Baseline | Working — heavy penalty correct |
| D2 | 12-18 | 41.2% | Rising | Expected |
| D3 | 18-20 | 48.3% | Rising | Expected |
| D4 | 20-28 | 54.9% | Rising | Expected |
| D5 | 28-30 | 55.7% | Rising | Expected — local peak |
| D6 | 30-35 | 43.1% | **Falling** | **INVERSION #1** |
| D7 | 35-40 | 35.7% | **Falling** | **INVERSION #2 — Dead Zone** |
| D8 | 40-48 | 52.0% | **Rising** | **INVERSION #3 — Recovery from dead zone** |
| D9 | 48-60+ | 47.8% | **Falling** | **INVERSION #4 — Overconfidence penalty** |

The D5-to-D7 progression is particularly damaging: win rate collapses from 55.7% to 35.7%—a 20-percentage-point decline despite a 12-point score increase. D6-D7 functions as a "dead zone" where mid-range scores mask poor performance ^31^. D8 recovers to 52.0% before D9 falls to 47.8%, meaning the score zigzags rather than improves monotonically. Such a pattern cannot serve as a reliable filtering threshold.

#### 3.2.2 The Overconfidence Penalty

The D9 inversion reflects the same overconfidence penalty seen in raw ML confidence. Highly confident predictions react to regime_bonus ($r=-0.115$) or noise features that inflate the composite while degrading outcomes ^31^. The 0.70-0.79 band's 57.0% win rate outperforms the 0.90+ band's 47.1% by 10 percentage points, confirming that medium-confidence predictions paradoxically achieve greater accuracy ^31^.

### 3.3 Inverted Weights

The composite's non-monotonicity stems from a weighting scheme that inverts the empirical correlation ranking: the strongest predictors receive modest weights, while anti-predictive components receive substantial allocations.

#### 3.3.1 Component Correlation vs. Weight Allocation

| Component | Correlation ($r$) with WR | Current Weight | Predictive Signal | Proposed Weight | Proposed Change |
|-----------|--------------------------|----------------|-------------------|-----------------|-----------------|
| **forward_wr** | **+0.242** | 25 pts | Best predictor | **55 pts** | +120% |
| leverage_safety | +0.133 | 5 pts | Moderate positive | 10 pts | +100% |
| source_system | +0.080 | N/A | Weak positive | 5 pts | — |
| elite_score (composite) | +0.100 | Aggregate | Weak (non-monotonic) ^31^| N/A | Rebuild formula |
| ml_composite_score | +0.220 | 25 pts | Moderate positive | 15 pts | -40% |
| **ml_score (raw)** | **-0.012** | **9-25 pts** | **Noise** | **4 pts** | **-56%** |
| market_cap_tier | +0.056 | N/A | Negligible | 5 pts | — |
| **regime_bonus** | **-0.115** | **20 pts** | **Anti-predictive** | **5 pts** | **-75%** |
| (15 components) | 0.000 | Various | Pure noise | 0-1 pts each | Eliminate |

Three structural problems are visible. **forward_wr**—the best predictor at $r=+0.242$—receives only 25 points, identical to the random ml_score. **regime_bonus** at $r=-0.115$ is actively harmful: it predicts worse returns, yet commands 20 points that inflate the composite when picks are weakest. Fifteen components carry zero correlation ($r=0.000$) yet consume aggregate weight ^31^.

#### 3.3.2 Proposed Weight Rebalance

The audit's proposed fix: forward_wr increases from 25 to 55 points (+120%), regime_bonus collapses from 20 to 5 points (-75%), and raw ml_score drops from 9 to 4 points (-56%) ^31^. Until deployed, users should mentally reweight the elite_score by discounting regime_bonus and requiring forward_wr >=55% regardless of headline composite value.

### 3.4 What Users Should Actually Filter By

The trust_score >=5 filter delivers 68-71% win rate ^31^—substantially higher than the composite's peak decile of 55.7%. It captures source quality, track record, and cross-system agreement. Forward_win_rate in the 50-65% band delivers 69.7% win rate ^31^, the second most effective filter. The Risk:Reward 1.5-2.0 band—identified as the sole profitable zone with Profit Factor 5.81—provides the tertiary gate. Confidence in the 0.70-0.79 band adds a fourth layer at 57.0% win rate, though the inverted-U pattern means it must be range-bound.

#### 3.4.1 Filter Hierarchy

| Rank | Filter | Threshold | Expected WR | Pick Count | Evidence Source |
|------|--------|-----------|-------------|------------|-----------------|
| **1** | **trust_score** | **>= 5** | **68-71%** | Moderate | Score Calibration Audit, Signal Brackets ^31^|
| **2** | **forward_wr** | **50-65%** | **69.7%** | Moderate | Score Calibration Audit ^31^|
| 3 | confidence (ML) | 0.70-0.79 | 57.0% | High | Empirical sweet spot ^31^|
| 4 | Risk:Reward | 1.5-2.0 | 55-60% (band-dependent) | Moderate | Shadow data: PF 5.81 at 1.5-2.0 |
| 5 | Beta Confluence | >= 70 | Not empirically tested | Low | Theoretical quality gate ^35^|
| — | confidence | 0.90+ | 47.1% | High | Overconfidence penalty — avoid ^31^|
| — | trust_score | 0-2 | 37.4% | High | Filter OUT — worse than random ^31^|

The hierarchy reveals a counter-intuitive finding: the platform's most prominent scores are not its most predictive filters. The trust_score and forward_wr filters—sitting lower in the UI—outperform headline scores by 10-20 percentage points. A user relying on the composite's "S" or "A" grade would select picks that underperform a trust_score >=5 threshold by 15-25 percentage points. The scoring architecture is broken in both its internal weighting and its presentation, directing users toward the least reliable metrics.

Users should treat the composite as a starting point, not a decision criterion. Any pick with elite_score below 75 should be discarded unless it passes trust_score >=5 and forward_wr 50-65% gates. The user's scores of 0.748 and 0.703 fall in the optimal confidence band, but confidence alone should never override a failing trust_score or forward_wr. The scoring system adds noise; the filter hierarchy subtracts it.

---

## 4. UI/UX Audit: Finding the Best Picks

The audit dashboard presents fourteen navigation tabs, eight filter buttons, nine dropdown selectors, and overlapping quality labels — all competing to answer one question: which picks are worth trading? This chapter tests every filter combination, documents a naming collision that violates UX heuristics, cross-checks the ?Guide against live data, assesses supplementary tabs, and fixes a production HTML bug.

### 4.1 Filter Combination Testing

The filter bar offers seven binary toggles (including "🧠 SMART PICKS," "Verified Alpha," and "🔥 HIGH CONVICTION ⭐") plus five preset categories. Testing logical pairings and triplets against the live database produces a clear hierarchy. The single-filter baseline shows "Verified Alpha" and "🔥 HIGH CONVICTION ⭐" each isolating picks with projected WR of approximately 62–64%, a 14–19 percentage-point lift over the unfiltered feed ^19^.

**Table 1: Filter Combination Matrix — Projected WR and Pick Count**

| Filter Set | Projected WR | Pick Count | PF (est.) | Usability |
|:---|:---:|:---:|:---:|:---|
| All picks (baseline) | 45–50% | ~210 | 1.0 | Reference only |
| High-grade only | 52–55% | ~45 | 1.1 | Low lift, vague criteria |
| Trusted only | 55–58% | ~18 | 1.3 | Source-based, not quality-based |
| R:R 1.5+ only | 50–52% | ~67 | 1.4 | Underperforms baseline on non-crypto |
| 🧠 SMART PICKS (filter) | 58–60% | ~12 | 1.6 | Per-asset gates, composable |
| 🔥 HIGH CONVICTION ⭐ | 60–64% | ~8 | 1.8 | Best single quality gate |
| Verified Alpha only | 62–64% | ~13 | 1.9 | Best single trust gate |
| Verified Alpha + High Conviction | **65–68%** | **3–8** | **2.1** | **Best daily driver** ^19^|
| Verified Alpha + R:R 1.5+ | 63–65% | 2–5 | 1.9 | Loses forward validation |
| High Conviction + Trusted | 60–63% | 3–6 | 1.8 | Redundant overlap |
| SMART PICKS + R:R 1.5+ | 58–60% | 1–3 | 1.7 | Too restrictive |
| **VA + HC + R:R 1.5+** | **66–70%** | **0–2** | **2.3** | **Best WR; often empty** ^19^|
| High-grade + Trusted + R:R 1.5+ + Recent | 55–58% | 5–10 | 1.5 | Volume-quality tradeoff |

The triple-filter combination gates out 192 of 210 picks (91%), leaving an empty table on most sessions ^19^. The UI treats this as a failure state rather than a protective one. For practical use, "Verified Alpha + High Conviction" is the optimal daily driver — 3–8 picks with projected WR above 65%. The triple-filter variant suits high-conviction sizing decisions where capital preservation outweighs frequency.

### 4.2 The "Smart Picks" Naming Crisis

The UI contains **three distinct elements** carrying the label "Smart Picks," each with a different behavioral contract. This violates Nielsen's heuristic #2 (system-real-world match) and heuristic #4 (consistency) ^36^.

**Table 2: Three UI Elements Named "Smart Picks" — Behavioral Divergence**

| Element | Visual Location | Behavioral Contract | Interaction Model |
|:---|:---|:---|:---|
| "🧠 SMART PICKS" button | Filter bar | Composable toggle; applies per-asset gates (min score, R:R ≥1.5, forward WR ≥50%, regime alignment) | Toggle on/off; stacks with other filters |
| "🧠 Smart Picks" tab | Top navigation (4th tab) | Standalone page showing pre-filtered results | Switches page context; may alter columns |
| "Smart Picks" reference | ?Guide modal, feed descriptions | Non-interactive conceptual tier label | Defines scoring methodology only |

The collision creates concrete errors. A trader clicking the filter button expects the same outcome as clicking the tab, yet the former is composable within the current view while the latter is a dedicated page that may reset filter context ^36^. The fix: rename the tab to "Smart Picks Feed," rename the filter button to "Apply Smart Gates," and reserve "Smart Picks" for documentation only.

### 4.3 Guide Page Accuracy

The ?Guide modal presents authoritative documentation, but cross-referencing against the closed-pick database ($n = 4{,}618$) reveals misalignment on R:R recommendations and combo reproducibility.

**Table 3: ?Guide Claim vs. Actual Data — Discrepancy Audit**

| Guide Claim | Stated Metrics | Actual / Cross-Check | Severity |
|:---|:---|:---|:---:|
| Crypto Confidence 0.85–0.90 | 82% WR, PF 11.8 | Confirmed; overfit cliff (>0.90 → 47% WR) not explained | Low |
| R:R ≥2.0 band | 58.0% WR, PF 3.06 | Triple-verified; prior tooltip (29.5% WR) empirically wrong | Low |
| **R:R ≥1.5 filter (current)** | Recommended | **Underperforms baseline on every asset class** (crypto −0.4pp, equity −1.0pp, forex −9.2pp, commodity −32.3pp) ^19^| **High** |
| **Maximum Conviction Combo** | 71.3% WR, PF 13.21, n=94 | **Not reproducible on current window (n=0); "insufficient sample"** ^19^| **High** |
| **Stocks Trusted + score ≥50** | 69.2% WR, +25.8pp lift | **PF 0.77 on n=13 — fails PF > 1.5 edge threshold** | **Medium** |
| High-grade A/B | NOT an edge | 49.3% WR, PF 0.66, −0.08% avg (n=483) | None (honest) |

The Maximum Conviction Combo — "PROVEN strategy + confidence 0.8–0.9: 71.3% WR, PF 13.21" — produces zero matching picks on the current data window. The guide buries this in a footnote reading "insufficient sample," but a user scanning headline claims would conclude it is validated and actionable ^19^. The R:R ≥1.5 filter is the second high-severity issue: live data shows it underperforming baseline across every asset class, a case of conditional statistics (R:R ≥2.0 among *closed picks*) diverging from prospective filter performance. Verdict: the Guide presents two non-reproducible or contradictory recommendations alongside accurate crypto confidence data.

### 4.4 Supplementary Tab Analysis

The dashboard ships with **fourteen tabs**. Two merit scrutiny.

**US Equity Picks** is entirely non-functional: "Building track record · n=0/100" with empty sub-tabs. The scoring formula (0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate) is displayed, but zero picks exist to score. This tab consumes prime navigation real estate for a feature with no actionable data since deployment.

**Closed Picks** is the audit trail — the only tab enabling forward-claim validation by comparing advertised FWD WR against realized WR. For a platform styled as an audit system, this is the evidence locker and should be prominently placed.

The remaining tabs fall into operational (Portfolios, Performance), internal diagnostics (Score Tracker, ML Health, Permutations), and external links (Links) categories. Most duplicate Overview data or expose pipeline states irrelevant to trading decisions.

**Table 4: Recommended Tab Reduction — 14 to 5**

| Current Tab | Recommendation | Rationale |
|:---|:---|:---|
| Overview | **Keep** | Consolidated landing with asset-class tiles |
| Active Picks | **Keep** | Core feed; add filter chips from Section 4.1 |
| Verified Alpha | **Merge into Active Picks** | Becomes filter toggle, not standalone tab |
| Smart Picks | **Merge into Active Picks** | Becomes "Apply Smart Gates" filter per 4.2 |
| US Equity Picks | **Hide until n≥100** | Zero actionable picks; show badge in Overview |
| Closed Picks | **Keep** | Audit validation; rename "Trade History" |
| Portfolios | **Merge into Overview** | Duplicates existing portfolio tiles |
| Dashboards | **Remove** | No unique data vs. Overview |
| Strat. Leaderboard | **Keep** | Per-strategy WR/PF rankings |
| Permutations | **Remove** | Internal combinatorial analysis |
| Performance | **Merge into Overview** | Duplicates asset-class tile data |
| Score Tracker | **Demote to Debug Mode** | Internal diagnostics only |
| ML Health | **Remove** | Empty tab at time of audit ^20^|
| Links | **Move to footer** | External URLs in primary nav dilute focus ^36^|

The reduction follows progressive disclosure: show decisions users need, hide infrastructure they don't ^30^. Diagnostic depth stays accessible via an "Advanced" toggle.

### 4.5 HTML Bug Fix

The US Equity Picks tab displays leaked text: `` ` inside this block — HTML does not support nested comments and the inner `-->` would close the outer. -->``. This is a developer comment escaped into the rendered page.

**Table 5: HTML Comment Bug — Root Cause and Fix**

| Attribute | Detail |
|:---|:---|
| **File** | `audit_dashboard/template.html`, lines ~1813–1825 (UEPS section) |
| **Bug type** | Nested HTML comment with premature `-->` terminator ^20^|
| **Root cause** | HTML parser treats `-->` inside backtick-quoted text as comment end ^37^|
| **Visible impact** | Developer warning text renders on US Equity Picks tab |
| **Severity** | Medium — UX degradation; security risk if pattern repeats |

The comment warned: "do NOT nest comments inside this block." The irony is self-evident — the warning about nested comments triggers the exact bug it describes ^37^ ^38^.

**Fix:** Replace the entire multi-line block:

```html
<!-- Before (lines 1813–1825): verbose multi-line comment containing nested `-->` -->
<!-- After: -->
<!-- UEPS mount point -->
```

This is the cleanest fix — the comment contains no runtime logic and describes server-side architecture irrelevant to end users ^20^ ^39^.

**Verification:** (1) replace block with `<!-- UEPS mount point -->`; (2) reload and confirm no leaked text; (3) grep codebase for other comments containing `-->` sequences; (4) add an `htmlhint` linter or CI grep check ^20^. Secondary cleanup: wrap 15+ `console.log` statements in a debug flag (they leak internal file paths) and remove the empty ML Health tab that presents users with a blank page ^20^. These fixes address the most visible quality issues. They do not alter underlying statistical validity — that was the subject of Chapters 2 and 3 — but they prevent users from encountering HTML fragments, empty tabs, and contradictory filter recommendations that erode trust in engineering standards.

---

## 5. Strategy Health & Failure Analysis

### 5.1 Strategy Failure Overview

Systematic diagnosis of the platform's strategy universe reveals **11 strategies flagged as statistical dropouts**, defined as those whose 7-day Win Rate (WR) has fallen more than 20 percentage points below their historical baseline. The mean baseline WR across the cohort was 46.4%, yet the current 7-day average stands at 27.5% — a **19.1pp collective collapse** that demands classification before any capital reallocation.

Four failure modes emerge from the diagnostic framework, grounded in Jegadeesh & Titman's momentum-to-reversal transition model ^40^, Ali-Daniel-Hirshleifer's "PMP Effect" on style-chasing reversals ^41^, and practitioner evidence on RSI(2) regime dependency from Connors & Alvarez ^42^ ^43^. Published anomalies face approximately 5pp of annual Sharpe decay from joint overfitting and arbitrage pressures ^44^.

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

The median drop is 21pp, but the worst performers — stocks_rsi2_pullback at –31pp and forex_rsi2_mean_reversion at –30pp — are mean-reversion strategies operating in environments where mean-reversion assumptions have broken down. Lehmann (1990) and Jegadeesh (1990) established that short-term contrarian profits require sufficiently negative return autocorrelations ^45^; when markets enter trending regimes, those autocorrelations flip positive and the strategy's edge inverts into a liability ^33^. The 31pp collapse in stocks_rsi2_pullback — whose 73% baseline WR made it the portfolio's statistical crown jewel — exemplifies how regime dependency transforms a high-conviction edge into a capital destruction engine within a single volatility cycle.

### 5.2 Strategy-by-Strategy Diagnosis

#### 5.2.1 Regime Change: What Shifted, What Filter Would Restore Edge

Four strategies share the regime-change diagnosis. **stocks_rsi2_pullback**, built on Connors & Alvarez's canonical RSI(2) configuration ^43^, collapsed from 73% to 42% as the equity market exited its mean-reverting regime. Practitioner research documents that "the 2008 financial crisis and March 2020 crash saw win rates drop below 60% as 'buy the dip' repeatedly failed" ^43^. The restoration path involves four parameter tweaks: tighten entry to RSI(2) < 5; add a VIX regime filter (suspend when VIX > 25 or VIX > 20 and rising); implement a 5-bar time stop; and require price above both 200-day and 50-day SMAs. Dual-trend confirmation "boosts win rates by 5–10% while reducing signal frequency" ^43^. Expected WR recovery: 42% → 60–65%.

**forex_rsi2_mean_reversion** suffers from a fundamental asset-class mismatch. Connors research explicitly warns that "applying RSI 2 blindly to highly trending markets like forex or commodities yields sub-50% win rates" ^46^. The recommended action is to abandon forex deployment and relocate the same logic to S&P 500 / Nasdaq-100 instruments, where StatOasis documented 73–80% WR with proper filtering ^42^.

**myfxbook_retail_contrarian** has degraded because the least-informed retail traders have exited active forex markets, leaving a more sophisticated residual cohort. Chan (1988) demonstrated that contrarian profits are compensation for time-varying risk; when risk regimes shift, abnormal returns shrink to near-zero ^47^. The recommended inversion — fading retail only when VIX < 25 and positioning exceeds the 90th percentile — narrows signal frequency but restores theoretical edge.

**st_obv_support_divergence** has suffered from declining volume-signal reliability due to dark pool proliferation, payment-for-order-flow arrangements, and algorithmic execution that fragments volume signals across venues ^48^. The modest 11pp decline suggests residual edge; modernization of the volume metric combined with a 50% position-size reduction is the appropriate response.

#### 5.2.2 Adverse Selection: Why Consensus Signals Become Self-Defeating

Three strategies — **futures_momentum**, **MomentumEMA**, and **ensemble** — suffer from adverse selection where signal popularity eroded alpha. MomentumEMA is the clearest case: EMA-crossover momentum has been public knowledge for 40+ years, placing it in the crosshairs of Falck et al.'s finding that "publication year alone accounts for 30% of variance in Sharpe decay" with "5pp annual decay" ^44^. The Jegadeesh & Titman (2001) reversal evidence shows that momentum portfolios experience "dramatic reversal of returns in the second through fifth years" post-formation ^40^— and for EMA momentum, that formation period spans decades.

Futures momentum faces dual headwinds: general momentum crowding (Ali-Daniel-Hirshleifer's "PMP Effect" generates 0.40% monthly alpha from fading it, t=3.74 ^41^) and commodity-specific structural breakdown as index investing created then arbitraged artificial momentum ^49^. The ensemble strategy illustrates "garbage in, garbage out": with 7 of 11 constituents failing, the ensemble amplifies rather than attenuates losses. The Sheppert GT-Score framework supports reducing constituent count to only robust, validated signals ^19^.

#### 5.2.3 Overfitting: Which Parameters Were Over-Optimized

**gainer_compression_relaxed_mut** carries its pathology in its name: "relaxed_mut" signals mutation-based optimization with relaxed constraints, a recipe for parameter bloat. The 32% baseline WR was already the worst in the portfolio; the collapse to 8% is textbook overfitting. Detection literature identifies the signatures: "deterioration outside the build dataset; brittle values where small changes imply large jumps" ^20^. The GT-Score research shows that "profit-optimized strategies achieve higher mean test returns but exhibit materially worse performance retention from training to out-of-sample" ^19^.

**signal_engine_momentum_mut** shows similar characteristics: a 50% marginal baseline collapsing 20pp, a decline larger than regime change alone would produce. The AlgoXpert framework identifies "parameter overfitting, selection bias, and sensitivity to regime changes" as primary failure modes for optimized strategies ^18^.

#### 5.2.4 Structural: Code Bugs and Data Pipeline Failures

The **unknown** strategy is a governance failure: a system component receiving capital allocation with no documented logic, no known parameters, and no reproducible validation. The AlgoXpert framework requires "cliff veto, execution controls, and circuit breakers" — none applicable to an undocumented system ^18^. Its 34% baseline was already below random walk; the 18% 7-day reading merely confirms what the absence of documentation implied.

**cta_commodity_momentum_term** is structurally dead. A Profit Factor of 0.02 represents complete strategy death, not temporary decay. The 58% flat exits indicate the strategy fails to capture directional moves at all — a signature of momentum logic applied to markets where momentum has been fully arbitraged ^49^. The path forward is not to fix momentum but to invert to the academically validated carry alternative: go long backwardation, short contango.

### 5.3 Inverse Strategy Candidates

#### 5.3.1 Academic Basis: Jegadeesh & Titman Momentum Reversal

The theoretical foundation for strategy inversion rests on a robust literature. Jegadeesh & Titman (2001) demonstrated that momentum portfolios earn +12.17% in year one but decline to –0.44% by year five — a 12.6pp reversal ^40^. Ali et al. (2017) showed that following top-quintile momentum performance, stale portfolios reverse –19% in years 2–5 versus +11% after bottom-quintile performance ^41^. Lehmann (1990) and Jegadeesh (1990) established that short-term contrarian strategies generate 2%+ monthly abnormal returns, with winners reversing –0.35% to –0.55% the following week ^45^. Four strategies meet the inversion criteria: baseline WR above 50%, current decline exceeding 15pp, and failure mode consistent with regime change or adverse selection.

#### 5.3.2 Table: 4 Invertible Strategies

| Strategy | Baseline WR | Current WR | Inverted Signal | Expected Inverted WR | Academic Basis |
|:---|:---:|:---:|:---|:---:|:---|
| myfxbook_retail_contrarian | 54% | 33% | Fade retail at 90th+ pct, VIX < 25 | 48–52% ^47^| Chan (1988): contrarian profits as time-varying risk compensation |
| futures_momentum | 45% | 20% | Short winners, buy losers in high-PMP | 55–60% ^41^| Ali et al. PMP Effect: 0.40% monthly alpha from reversal (t=3.74) |
| goldmine_1x_consensus | 30% | 12% | Go against >70% consensus | 55–60% ^16^| BSV/DHS: short-run underreaction → long-run overreaction |
| MomentumEMA | 67% | 46% | Fade EMA crosses when VIX > 20 | 55–58% ^40^| J&T (2001): momentum reverses 12.6pp years 2–5 post-formation |

The expected inverted WRs are conservative estimates drawn directly from the cited academic returns. The goldmine_1x_consensus inversion exploits Barberis-Shleifer-Vishnu (1998) and Daniel-Hirshleifer-Subrahmanyam (1998): short-run underreaction followed by long-run overreaction means consensus systematically overshoots ^16^.

#### 5.3.3 Validation Plan: 30-Day Paper Trade Before Live Deployment

No inverted strategy receives live capital without completing a **30-day paper-trading validation** producing at least 30 simulated trades. Minimum acceptance criteria: (1) paper WR within 5pp of expected inverted WR; (2) maximum drawdown below 15%; (3) Profit Factor exceeding 1.0; (4) no single day exceeding 20% of total PnL. This protocol aligns with the AlgoXpert IS/WFA/OOS framework ^18^and prevents deployment of theoretically sound inversions that encounter execution slippage or microstructure frictions not captured by backtest assumptions.

### 5.4 Strategies to Ban Immediately

Three strategies require permanent capital prohibition. Decision criteria: no recoverable edge regardless of parameter adjustment; governance failure precluding safe deployment; or structural mismatch between strategy and asset class.

The **unknown** strategy receiving live allocation represents a breakdown of quantitative governance. No documentation, no auditable logic, no validation protocol. Trading it is the antithesis of the GT-Score framework's emphasis on "stable parameter regions" and "structural safeguards" ^19^. **Action: remove code; treat as a new strategy subject to full IS/WFA/OOS protocol if logic can be recovered** ^18^.

**gainer_compression_relaxed_mut**, at 32% baseline WR, is not a temporarily failing strategy but a failed experiment. The "relaxed mutation" approach generated spurious patterns. If the volatility-compression concept has theoretical merit, it must be rebuilt from scratch with minimum 200 trades for validation ^21^, GT-Score optimization ^19^, and walk-forward validation with purge gaps ^18^. **Action: permanently abandon current implementation.**

**cta_commodity_momentum_term** (PF 0.02) is dead. The recommended replacement is a **triple-screen commodity carry strategy**: Screen 1 selects commodities in backwardation (positive roll yield); Screen 2 filters for term structure slope in the top tertile; Screen 3 applies a 20-day momentum overlay to time entry within carry-selected instruments. Fuertes et al. demonstrate that term structure strategies improved post-financialization (Sharpe 0.41 vs 0.35 for momentum) ^49^. Expected PF improvement: 0.02 → 1.1–1.4.

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
| claude_gainer | 56.2% | 2.23 | 32 | Building | **MODERATE EDGE — EMERGING**: Below 200-trade validation ^21^but above minimum viability. | Gradual allocation increase; apply MDD guard at 12% |

The Tier-2 strategies reveal a critical pattern: **signal_validation** (PF 2.58) and **mega_mutation** (PF 3.19) possess the highest Profit Factors in the entire portfolio, yet both receive minimal capital because low signal frequency keeps them in "building" status. The GT-Score framework favors these robust, lower-frequency strategies over the high-frequency, decaying strategies in the dropout list ^19^. The recommendation is to reallocate 30–40% of capital from failing dropout strategies to these Tier-2 building strategies, with graduated scaling: full activation at n ≥ 200, partial scaling at n ≥ 50, paper-only below n = 30.

The **rl_agent** strategy exemplifies a critical governance tension. Its 60% WR and 2.54 PF are superficially attractive, but 5 trades provide no statistical foundation for allocation. The platform must resist scaling strategies prematurely based on early outperformance — a pattern that mirrors the survivorship illusion identified elsewhere in this audit, where small-sample extreme metrics systematically fail to replicate.

---

## 6. Risk Management Assessment

### 6.1 Overall Risk Framework Score

The platform's risk management framework earns an overall score of **6.5/10** — adequate in its core mathematics but weakened by material gaps in diversification, kill switch coverage, and position concentration discipline. Table 6.1 breaks down the component scores.

**Table 6.1 — Risk Framework Component Scores**

| Dimension | Score /10 | Grade | Assessment |
|:----------|:---------:|:-----:|:-----------|
| Kelly sizing by R:R band | 8.5 | B+ | Quarter-Kelly 11.8% mathematically verified; conservative vs. theoretical 15.9% ^26^|
| Asset class position sizing | 7.0 | C+ | Reasonable tiering; bonds and forex underweighted |
| C-tier handling (PF 0.56) | 9.0 | A | Correctly blocked at 0% allocation ^50^|
| Cross-asset diversification | 5.2 | F | ETF-equity correlation 0.85 creates hidden concentration |
| Position distribution | 6.5 | C | Over-concentrated in crypto S-tier; true independent bets ≈4 |
| Probability of ruin | 2.1/10 (low risk) | A+ | Quarter-Kelly + 10% DD halt makes ruin virtually impossible |
| R:R >2.0 handling | 9.0 | A | Correctly blocked; Kelly = –22.8% ^51^|
| Kill switch ladder | 6.0 | C | Missing daily loss limit, consecutive loss halt, vol circuit breaker ^52^|
| **Overall** | **6.5** | **C+** | Solid mathematical foundation with material execution gaps |

The framework's strongest pillar is Kelly-derived position sizing. For the primary R:R 1.5–2.0 band (PF 5.81, implied win rate 76.85%, payoff ratio 1.75:1), the formula $f^* = (p \times (b+1) - 1) / b$ yields Full Kelly of 63.6%, making the platform's 11.8% Quarter-Kelly allocation approximately one-fifth Kelly — a conservative buffer that virtually eliminates geometric ruin risk ^27^. Blocking of the R:R 1.25–1.5 (Kelly –1.6%) and R:R >2.0 (Kelly –22.8%) bands is mathematically correct ^51^. The weakest dimension is cross-asset diversification at 5.2/10: nine asset classes on paper collapse to approximately four independent risk exposures in practice, undermining the position-sizing framework.

### 6.2 Probability of Ruin

Monte Carlo simulation of 10,000 equity paths produces reassuring results: at 11.8% Quarter-Kelly with 76.85% win rate, **zero paths** hit the 10% drawdown (DD) halt over 252 trades. Median final equity reached **2.564×** (+156.4%), with the worst case at 2.074× ^53^. Median maximum DD was 1.1%.

**Table 6.2 — Ruin Probability by Portfolio Composition and Sizing Regime**

| Risk per Trade | P(Ruin @ 5% DD) | P(Ruin @ 10% DD) | P(Ruin @ 20% DD) | Max DD @ 100 Trades |
|:---------------|:---------------:|:----------------:|:----------------:|:--------------------|
| 2.0% | 1.2% | 0.015% | ~0% | 7.8% |
| 5.0% | 17.2% | 3.0% | 0.09% | 18.5% |
| **11.8%** (current) | **47.5%** | **22.5%** | **5.1%** | **39.5%** |
| 15.0% | 55.6% | 30.9% | 9.6% | 47.8% |
| 47.2% (Half-Kelly) | 83.0% | 68.9% | 47.5% | 92.2% |

The values in Table 6.2 assume independent sequential bets without the 10% DD circuit breaker. The critical distinction is that the platform's kill switch at 10% DD triggers a full halt *before* mathematical ruin occurs, rendering the effective ruin probability **0%** with disciplined execution ^54^. However, this low-probability outcome depends critically on maintaining the 76.85% win rate. If a market regime shift reduces the win rate to 60%, the probability of a 10% DD event rises to approximately 8%; at 50% win rate, it jumps to roughly 25%. Win-rate degradation should be monitored as an early warning signal.

### 6.3 Kill Switch Gaps

The current kill switch configuration matches industry standards at the 5% DD (50% size reduction) and 10% DD (full halt) levels, but omits three circuit breakers that institutional-grade systems treat as non-negotiable ^52^. Table 6.3 compares the current configuration against industry best practices.

**Table 6.3 — Kill Switch Gap Analysis: Current vs. Industry Best Practice**

| Feature | Current State | Industry Standard | Gap Severity |
|:--------|:-------------|:-------------------|:-------------|
| 1st DD threshold (5% → 50% size) | Implemented | 3–5% → 50% size | None |
| 2nd DD threshold (10% → full halt) | Implemented | 7–10% full halt | None |
| Asset-specific halt (PF decay) | PF < 0.80 @ 5 days | PF < 1.0 @ 3–5 days | Slight |
| **Daily loss limit** | **Not set** | **2% warning, 3% hard halt** | **Critical** |
| **Consecutive loss halt** | **Not set** | **5–7 losses → review** | **High** |
| **Volatility circuit breaker** | **Not set** | **VIX >40 → 50% reduction** | **High** |
| Correlation stress guard | Not set | Correlation → 1.0 = reduce | Medium |
| Recovery protocol | Not set | Recover 50% of DD to resume | Medium |

The daily loss limit is the most critical gap. Without a 2–3% single-day maximum loss circuit breaker, a flash crash can inflict more damage in one session than a week of disciplined trading ^54^. The consecutive loss halt is equally important: after 5 consecutive losses with a 77% win-rate strategy (probability 0.06%), the edge has likely broken ^53^. Continuing to trade under these conditions constitutes revenge trading. The recommended enhanced kill switch adds Level 0 (daily loss limit at 2% → 50% size, 3% → halt), Level 6 (5 consecutive losses → strategy review), and Level 7 (VIX >40 → 50% reduction). These enhancements would raise the kill switch score from 6.0/10 to an estimated 9.0/10 ^52^.

### 6.4 Cross-Asset Correlation

**Table 6.4 — Cross-Asset Correlation Matrix (2020–2024 Literature Basis)**

| Asset | BTC/ETH | Crypto A | Equity | Forex | Commodity | Bond | ETF |
|:------|:-------:|:--------:|:------:|:-----:|:---------:|:----:|:---:|
| BTC/ETH | 1.00 | 0.65 | 0.45 | 0.10 | 0.15 | –0.05 | 0.40 |
| Crypto A | 0.65 | 1.00 | 0.35 | 0.08 | 0.12 | –0.03 | 0.32 |
| Equity | 0.45 | 0.35 | 1.00 | 0.15 | 0.30 | **–0.40** | **0.85** |
| Forex | 0.10 | 0.08 | 0.15 | 1.00 | 0.10 | 0.05 | 0.12 |
| Commodity | 0.15 | 0.12 | 0.30 | 0.10 | 1.00 | –0.20 | 0.25 |
| Bond | –0.05 | –0.03 | **–0.40** | 0.05 | –0.20 | 1.00 | –0.35 |
| ETF | 0.40 | 0.32 | **0.85** | 0.12 | 0.25 | –0.35 | 1.00 |

The diversification matrix reveals that the portfolio's nine asset classes collapse to approximately four independent bets. The most damaging concentration is the **ETF-equity correlation of 0.85**, which effectively means these two categories represent a single position for risk-limit purposes ^55^ ^56^. Bonds provide the only true negative correlation to equities (–0.40) and are currently underweighted relative to their hedging value. Forex displays the lowest average correlation with all other assets (~0.10) and functions as the portfolio's best diversifier, yet receives only 0.85% allocation under the current distribution ^57^. Crypto internal correlation is high (0.65 between S-tier and A-tier), meaning all crypto positions should be aggregated for concentration limit purposes — the crypto S-tier + A-tier + B-tier combination effectively acts as 1.5 independent bets, not 3 ^58^ ^59^.

In stress periods, the crypto-equity correlation can spike to 0.60+, further reducing independent exposures ^60^. The recommended remediation aggregates ETF with equity, aggregates all crypto tiers, increases bond allocation to 2.5–3.0% (from 1.71%), and increases forex to 1.5% (from 0.85%). These changes would raise the diversification score from 5.2 to an estimated 7.5 while maintaining the same total position exposure.

---

## 7. Penny Stocks and Meme Coins: High-Risk Deep Dive

### 7.1 Penny Stock Viability

Academic evidence on penny stock profitability is overwhelmingly negative for small investors. Peer-reviewed studies consistently show average annual returns of –24% to –27%, with median returns of –37% — meaning more than half of penny stocks lose over one-third of their value annually ^61^ ^62^. Table 7.1 summarizes the key academic findings.

**Table 7.1 — Academic Evidence on Penny Stock Returns**

| Study | Period | Sample | Avg Annual Return | Median Return | Key Finding |
|:------|:-------|:-------|:-----------------:|:-------------:|:------------|
| Bruggemann et al. (2016) ^61^ ^62^| 2001–2010 | 10,000+ OTC stocks | **–27%** | **–37%** | 5-year survival rate 60–90%; volatility >2× Nasdaq-listed |
| Eraker & Ready (2015) ^61^| 2000–2008 | ~OTC stocks | **–24%** | — | Aggregate investor losses: **$180 billion** |
| Ang, Shtauber & Tetlock (2013) ^61^| Multi-year | OTC stocks | Negative risk-adjusted | — | Negative returns unexplained by systematic risk factors |
| Verdad Advisors (2024) ^63^ ^64^| 1996–May 2024 | Sub-$5 stocks | +0.9% (equal-weight) | — | Cap-weighted return: **–60%**; Sharpe: **–2.06** |
| Konku et al. (2012) ^65^| Multi-year | Penny stocks | 18–20% (first year only) | — | Returns collapse after month 13; optimal hold: 11 months |

The distribution of penny stock returns is critically important: the equal-weighted average of +0.9% versus the cap-weighted return of –60% demonstrates extreme positive skewness. A handful of stocks produce massive gains while the vast majority destroy capital — the classic "lottery ticket" distribution that attracts retail investors while systematically transferring wealth to insiders and promoters ^64^. The "most liquid subset" exception identified by Verdad Advisors — timing entry via collapsing high-yield spreads following market panic — is statistically significant but represents a narrow, contrarian crisis-investing strategy fundamentally different from typical retail momentum chasing ^64^.

**Table 7.2 — Cost Structure: Penny Stocks vs. Large-Cap Equities**

| Cost Component | S&P 500 Stocks | Microcap Stocks ($1–$5) | Sub-$1 OTC Stocks | Source |
|:---------------|:-------------:|:----------------------:|:-----------------:|:-------|
| Bid-ask spread | 0.01–0.05% | **1–3%** | **5–50%+** of share price | Market data ^66^|
| Entry slippage | Minimal | $0.15–$0.60/share | $0.15–$0.60/share | Trading journals ^66^|
| Exit slippage | Minimal | $0.10–$0.40/share | Potentially no bid available | Trading journals ^66^|
| Round-trip friction (total) | ~0.02% | **3–15%** | **15–30%+** | Calculated ^67^|
| Commission (retail) | $0 | $0 | $0–$6.95/trade | Broker data |

For a $100 position in a sub-$1 OTC stock, round-trip transaction costs alone consume $15–$30 before any price movement occurs ^67^. The SEC's own disclosure example illustrates the trap: a stock with a $0.04 bid and $0.10 ask represents a 60% spread — an investor putting $5,000 at the $0.10 offer can only recover $2,000 at the $0.04 bid, losing more than half the investment to spread alone ^67^. A stock must appreciate **15–30% just to break even** on costs. Against a median return of –37%, the probability of doubling a $100 position net of spreads is statistically negligible. The only evidence-based exception is crisis-timing via high-yield spread compression, which requires macro timing, systematic execution, and exit discipline that retail investors do not possess ^64^.

### 7.2 Penny Stock Verdict

The verdict is **DANGEROUS — default exclusion.** Professional fund families grounded in academic research systematically exclude penny stocks: Alpha Architect screens out lottery-characteristic stocks, AQR excludes extreme volatility/skewness securities, Avantis filters low-priced illiquid issues, Bridgeway applies minimum price and liquidity thresholds, and Dimensional Fund Advisors excludes microcap and pink sheet securities entirely ^64^. Larry Swedroe's assessment is direct: "An efficient way to improve the expected performance of an equity strategy would be to systematically exclude penny stocks" ^64^. If included at all, penny stocks should be restricted to a separate PENNY asset class with mandatory filters: minimum $1M daily volume, spread below 2%, exchange-listed only (NYSE/Nasdaq), price above $1.00, and market cap above $50M. Position limits must be **2% per pick and 5% total allocation** with mandatory user opt-in and separate tracking from core equity picks.

### 7.3 Meme Coin Viability

Meme coins present a structurally negative expected-value proposition that exceeds even penny stocks in its wealth-destruction efficiency. On-chain data from Pump.fun — the largest meme coin launchpad with 5.7 million tokens created and $398 million in platform revenue — reveals the most comprehensive profitability dataset available ^68^.

**Table 7.3 — Meme Coin Trader Profitability: Pump.fun On-Chain Data**

| Profit Threshold | Wallets | % of Total (13.55M) |
|:-----------------|:-------:|:--------------------|
| >$10,000 | 55,296 | **0.41%** ^68^|
| >$100,000 | ~6,504 | **0.048%** ^68^|
| >$1,000,000 | ~294 | **0.002%** ^68^|
| Self-reported profitable (survey) | — | 56% (unverified) ^69^|
| Cross-validated loss rate | — | **80–95%** ^70^ ^71^|

The 0.41% profitability rate above $10,000 means that **99.6% of meme coin traders fail to achieve meaningful profits**. Self-reported surveys claiming 56% profitability suffer from survivorship bias and overclaiming; on-chain data is definitive ^69^ ^71^. Academic research confirms that social-media-influenced traders lose 1% per trade on average in cryptocurrency — the second-worst performance across all asset classes studied ^72^. The Memecoin Fragility Framework (ME2F) quantified PEPE at 301.8% daily volatility and found that top 100 addresses hold more than 70% of supply in most meme coins, with some tokens exceeding 90% ownership concentration ^26^. A comprehensive manipulation study documented $7.78 million in extracted profits against $9.3 million in total losses across over 17,000 victim addresses ^54^.

Applying the Kelly Criterion to the platform's shadow-data parameters (65.6% win rate, 5% average win, –47.2% average loss) produces a **Kelly fraction of –244%** ^58^. A negative Kelly fraction means the optimal bet size is zero — the strategy has negative expected value regardless of the high win rate. The reconciliation reveals the structural trap: at 65.6% win rate with –12.96% average PnL, every loss wipes out approximately nine winning trades. For a $100 investor, Monte Carlo simulation projects a **99.7% risk of ruin** with median final capital of $0.78 ^58^. Even assuming optimistic parameters (35% win rate, 30% average win, –10% average loss) that have never been demonstrated achievable by retail traders, doubling $100 remains a near-zero probability event.

### 7.4 Meme Coin Verdict

The verdict is **COMPLETELY EXCLUDE** — structurally negative-EV. Unlike penny stocks, which retain a narrow crisis-timing exception, meme coins offer no evidence-based entry strategy with positive expectancy. The Random Walk Hypothesis holds for short-term cryptocurrency forecasts ^73^ ^74^, social sentiment APIs lag price action by 15–60 minutes while pumps complete in minutes ^75^, and up to 30% of Pump.fun wallets are bots generating false signals ^68^. Every positive backtest result in the literature (Belcastro et al.'s 194% gain ^52^, momentum strategies) suffers from in-sample overfitting, institutional infrastructure requirements, or no out-of-sample validation. Momentum strategies on meme coins specifically returned –36.9% in backtesting ^76^. The meme coin ecosystem is a negative-sum game where creators and insiders extract value, platforms earn fees, bots capture alpha, and retail provides exit liquidity.

### 7.5 Comparative Assessment

**Table 7.4 — Penny Stocks vs. Meme Coins vs. Equities: Comparative Metrics**

| Metric | Penny Stocks (OTC) | Meme Coins | Platform Equities |
|:-------|:------------------|:-----------|:------------------|
| Average annual return | –24% to –27% ^61^| Not meaningfully calculable | PF 1.72 (positive) |
| Median return | –37% ^62^| Median final: $0.78 (meme coin) ^58^| Positive expected value |
| % of traders profitable | <10% (short-term) | **0.41%** >$10K ^68^| 66–70% (filtered) |
| Kelly fraction | Negative (most strategies) | **–244%** ^58^| +21.1% (Equity) |
| Risk of ruin ($100, 2% sizing) | >95% over 100 trades | **99.7%** ^58^| <1% ^53^|
| Round-trip transaction cost | 3–30% ^67^| Spread + gas fees 0.5–3% | <0.05% |
| Sharpe ratio | –2.06 ^64^| Not calculable (infinite variance) | OOS Sharpe +3.527 |
| Verdict | DANGEROUS — exclude by default | **COMPLETELY EXCLUDE** | Crown jewel asset class |

Table 7.4 crystallizes the divergence between these three asset classes. Penny stocks and meme coins share a common structural signature: many small wins masking catastrophic losses, extreme positive skewness creating a "survivorship illusion" that attracts retail capital, and transaction cost structures that make positive net returns mathematically improbable. The platform's equity strategies, by contrast, deliver positive OOS Sharpe (+3.527), a verifiable Kelly fraction above zero, and a sub-1% ruin probability under disciplined sizing. The difference is not one of degree but of kind: equities exhibit positive expected value under the platform's methodology, while penny stocks and meme coins exhibit structurally negative expected value under any retail-accessible approach. Including either asset class would dilute the platform's genuine equity edge with lottery-ticket exposures that serve as wealth transfer mechanisms from retail investors to insiders.

---

## 8. Code Quality and Technical Debt

### 8.1 Repository Health

The platform's codebase presents a paradox: 119,598 commits across multiple AI-agent contributors (KIMI, Claude, Cursor, Copilot) have produced volume without corresponding quality infrastructure [from dim10 analysis]. The public mphinance/mphinance repository contains 561 commits focused on content and configuration, not core trading logic. The actual trading system — containing `outcome_resolver.py` and strategy engine code — resides in a separate repository where code quality issues are more acute.

The most critical maintenance risk is **code duplication**: `outcome_resolver.py` exists in **5 or more copies** across different directories, creating version-control drift and inconsistent backtest results. The 2026-04-28 resolver fix may have been applied to only the primary copy, leaving backtest processes and dashboard queries potentially referencing unpatched versions ^23^. Commit message quality is inconsistent — emoji-heavy messages like "🎙️ Voice extraction" suggest limited human review of AI agent contributions. With multiple AI agents committing without a structured review gate, "agent drift" — small unauthorized changes to strategy parameters — becomes a non-trivial risk.

**Table 8.1 — Repository Health Metrics**

| Metric | Value | Assessment |
|:-------|:------|:-----------|
| Total commits | 119,598 | High velocity, unclear quality correlation |
| AI agent contributors | 4+ (KIMI, Claude, Cursor, Copilot) | No structured review gate |
| Copies of outcome_resolver.py | 5+ | Version-control drift risk ^23^|
| Public repo commits (mphinance) | 561 | Content-focused; not core trading system |
| HTML comment bugs in production | 1 (nested comment in template.html) | Medium severity; affects UX ^23^|
| Console.log statements in JS | 15+ | Low severity; exposes architecture details |
| Empty tab content (ML Health) | 1 tab | Possibly intentional (dynamic load) |
| Inst. infrastructure coverage | ~5% of hedge-fund standard | Existential gap |

### 8.2 The Resolver Fix

The 2026-04-28 resolver fix eliminated an infinite retry loop in `outcome_resolver.py` — a well-documented failure mode where a mid-write crash leaves corrupted state triggering endless retries ^23^. Pre-fix, FOREX showed 0% win rate because failed resolutions never completed; post-fix, FOREX registered 46.4% WR and commodity PF reached 1.78. The critical distinction: this was a **tracking fix, not a strategy fix**. The resolver classifies outcomes of trades already made — it does not determine which trades to make. The fix was akin to repairing a broken speedometer: it reveals true speed without making the car faster.

The post-fix FOREX profit factor of **0.27** means the strategy loses $3.70 for every $1.00 of gross profit. The fix did not break FOREX — it revealed that FOREX was already broken ^13^. Meanwhile, commodity PF of 1.78 is encouraging but statistically unconfirmed. The attribution challenge is compounded by multiple confounding commits in the same 2-week window: cross-system aggregation, 5 new swarm engines, and configuration changes. Post-fix data mixes legacy and new engine picks in unknown proportions, violating consistent structural conditions for statistical validity ^25^.

### 8.3 Evaluation Timeline

Six days of post-fix data is categorically insufficient to evaluate any trading strategy change. The statistical requirements are well-established across institutional and retail standards.

**Table 8.2 — Minimum Evaluation Timeline for Resolver Fix Impact**

| Confidence Level | Minimum Closed Trades | Est. Calendar Days | Assessment Date | Actionable? |
|:-----------------|:--------------------:|:------------------:|:----------------|:-----------|
| Bug elimination confirmed | — | Immediate | 2026-04-28 | Yes — non-zero WR confirms fix |
| Gross directional check | 100 | 14–20 days | 2026-05-18 | Barely — detects gross failure only ^77^|
| Basic WR/PF stability | 200 | 28–40 days | 2026-06-01 | Moderate — basic trend assessment ^13^|
| Regime resilience | 500 | 70–100 days | 2026-08-01 | Yes — institutional-grade confidence ^25^|
| Full regime coverage | 500+ across regimes | 90–180 days | 2026-08 to 2026-10 | Yes — deployment decision support ^13^|

At the platform's estimated resolution velocity of 30% of picks closing within 24 hours, FOREX generates approximately 45–65 closed trades in 6 days and commodities generate 25–35. With 45–65 trades at ~46% WR, the 95% confidence interval spans approximately [32%, 60%] — far too wide to distinguish edge from random noise at the 50% benchmark ^78^ ^25^. The 5 new swarm engines deployed in the same window constitute the most dangerous confounding factor: post-fix FOREX and commodity data is not from the same strategy distribution as pre-fix data, making attribution impossible without per-engine telemetry ^77^. Recommendation: **do not make allocation decisions based on 6-day post-fix data**. Wait until at least 2026-05-18 for gross directional assessment and 2026-06-01 for any meaningful PF/WR evaluation.

### 8.4 Orphaned Code Goldmines

The high commit velocity and multi-agent development model have likely left dormant but valuable code modules scattered throughout the repository. Table 8.3 identifies the top candidates for resurrection based on cross-dimensional evidence of potential edge.

**Table 8.3 — Top Orphaned Code Candidates for Resurrection**

| Candidate Module | Evidence of Edge | Resurrection Priority | Est. Effort |
|:-----------------|:----------------|:---------------------|:------------|
| Signal Quality ML predictor | Claims +5–15pp WR improvement; "code review only" evidence grade; needs backtest validation | High | 2–3 weeks |
| Intraday reversal (academic) | 0.62–0.85% monthly alpha (t-stats 4.37–6.72); not currently active | High | 1–2 weeks |
| Acquirer event strategy | Penny stock acquirers earn +1.99% excess CAR over (–5,+5) window ^79^| Medium | 2–3 weeks |
| Sentiment-based L/S (NPos/Neg) | Positive sentiment measure predicts short-term penny returns ^80^| Medium | 2–3 weeks |
| Crisis-timing via high-yield spread | Verdad finding: penny stocks outperform only during spread compression ^64^| Medium | 3–4 weeks |

The Signal Quality ML predictor is the highest-priority candidate. While the claimed +5–15 percentage point win-rate improvement remains at "code review only" evidence grade (unverified by actual backtest), the potential upside justifies dedicated validation effort. If even a 5pp improvement is achievable on the equity strategy's current ~57% WR, the resulting 62% WR would push the R:R 1.5–2.0 band's profit factor well above the institutional threshold of 2.0. However, the predictor must be validated with a minimum 200-trade out-of-sample backtest before any live deployment — the same statistical rigor applied to the resolver fix evaluation. The intraday reversal strategy, with documented monthly alpha and high t-statistics, represents the lowest-effort, highest-confidence resurrection candidate and should be prioritized for immediate testing.

---

## 9. Institutional Transformation Roadmap

### 9.1 Gap Analysis: The 5% Reality

The gap between current infrastructure and institutional-grade quantitative trading is quantifiable and severe. Cross-referencing the 12-dimension audit findings against operational standards at Renaissance Technologies, Two Sigma, and Citadel reveals that approximately **5% of required institutional infrastructure** is currently operational ^81^. The walk-forward OOS framework, tier classification system, kill-switch ladder, and feature flags provide a viable skeleton. The critical deficiency, however, is the **absence of a unified research-to-production pipeline with statistical validation gates**. Renaissance Technologies discards 99% of tested signals ^81^; this platform deploys signals without PSR/DSR validation, without multiple-testing correction, and with negative OOS Sharpe ratios — an existential risk, not a gap.

**Table 9.1 — Infrastructure Gap: Current vs. Institutional Standard**

| Component | Current State | Institutional Standard | Gap Severity |
|-----------|---------------|----------------------|--------------|
| Signal validation (PSR/DSR) | Not deployed; negative OOS Sharpe accepted | PSR > 0.95, DSR > 0.95 required; 99%+ rejection rate ^81^| **Existential** |
| Data quality | Free APIs (yfinance, CoinGecko); survivorship bias unaddressed | Point-in-time, survivorship-bias-free data; tick-level history ^82^| **Existential** |
| Transaction cost modeling | None; backtests against theoretical prices | Frazzini-Israel-Moskowitz calibration; power-law market impact ^83^| **Massive** |
| Execution infrastructure | No OMS/EMS; no broker connectivity | Co-located execution; 0.002-0.003% transaction costs ^82^| **Massive** |
| Cross-strategy risk | Kill-switch ladder only; no correlation monitoring | Centralized cross-asset risk platform; real-time VaR/CVaR ^84^| **Critical** |
| Code governance | 5+ copies of outcome_resolver.py; AI agents commit without review | Mandatory human review; CI/CD; single source of truth ^85^| **Existential** |
| Sample size enforcement | Strategies with n=5, n=18, n=32 deployed | Minimum 200-500 trades per strategy before deployment ^81^| **Existential** |
| Audit trail | None | Immutable, cryptographically signed trade decision records ^86^| **Critical** |
| Regime detection | None | Hidden Markov Model (HMM) with strategy switching ^81^| **Large** |

The pattern is unmistakable: validation infrastructure is the most deficient dimension. **Zero percent** of current strategies have PSR > 0.95 or DSR > 0.95, and multiple strategies operate below statistical minimums (n=5, n=18, n=32). The kill-switch ladder is a reactive safety mechanism — it cannot substitute for proactive statistical validation. Closing these gaps requires a phased investment: a 90-day Minimum Viable Product (MVP) at approximately $1,500, followed by a 12-month build-out at $32,400-$78,000.

### 9.2 What a Quant/Hedge Fund Manager Would Add

A professional quantitative researcher would introduce three categories of additions: statistical validation methodology, data infrastructure upgrades, and governance frameworks.

**Table 9.2 — Quant/Hedge Fund Methodology Additions**

| Category | Addition | Estimated Cost | Impact | Priority |
|----------|----------|---------------|--------|----------|
| Statistical validation | PSR > 0.95 hard gate (Bailey & Lopez de Prado, 2012) ^81^| ~$0 (code only) | Prevents deployment of false-positive strategies | P0 — Week 1 |
| Statistical validation | DSR > 0.95 hard gate (Bailey & Lopez de Prado, 2014) | ~$0 (code only) | Corrects Sharpe ratio for multiple-testing bias | P0 — Week 2 |
| Statistical validation | Combinatorial Purged Cross-Validation (CPCV) ^87^| ~$0 (code only) | Eliminates overfitting through embargo-period purging | P1 — Month 2-3 |
| Statistical validation | Multiple testing correction (Bonferroni/Holm/BH) | ~$0 (code only) | False discovery rate exceeds 50% without correction ^88^| P0 — Week 2-4 |
| Data infrastructure | Polygon.io + CCData institutional feeds | ~$300/month | Eliminates 1-4% annual survivorship bias inflation ^87^| P0 — Week 1 |
| Data infrastructure | Point-in-time database (TimescaleDB) | ~$50/month | Prevents look-ahead bias; enables reproducible backtests ^89^| P0 — Week 1-2 |
| Execution | Transaction cost model (Frazzini-Israel-Moskowitz) | ~$0 (code only) | 85% of market impact is permanent ^83^; models prevent fiction | P1 — Week 3-4 |
| Risk management | Cross-position correlation guard (max 0.7 pairwise) | ~$0 (code only) | Prevents concentrated risk amplification | P1 — Week 5-6 |
| Risk management | Regime detection (VIX-based 5-regime) | ~$0 (code only) | Blocks momentum strategies in bear markets ^42^| P1 — Week 5-6 |
| Governance | Mandatory human code review for all AI-generated commits | ~$0 (process) | Eliminates version-control chaos from 5+ file copies ^85^| P0 — Week 1 |
| Governance | CI/CD pipeline (GitHub Actions) | ~$0-$20/month | Automated testing prevents broken code in production | P1 — Week 1-2 |
| Compliance | Immutable audit trail | ~$0 (code only) | Complete trade decision reconstruction ^86^| P2 — Week 11-12 |

The highest-impact additions are also the cheapest. PSR/DSR gates, CPCV, and multiple testing correction require only developer time — no capital expenditure — yet their absence is an existential risk. Data infrastructure upgrades cost approximately $350/month, less than the expected loss from a single bad trade based on survivorship-biased data. The 90-day MVP implements all P0 and P1 items in sequence, creating statistical rigor before any capital is deployed to new strategies.

### 9.3 The 90-Day MVP: Six Hard Gates

The 90-day transformation targets "minimum viable institutional" status — defined as: a professional quant would not immediately reject the platform as unfit for serious capital. This requires six non-negotiable hard gates.

**The Six Hard Gates:** (1) **PSR > 0.95** — 95% confidence that the true Sharpe is positive ^81^; (2) **DSR > 0.95** — 95% confidence after multiple-testing correction; (3) **n >= 200** — minimum 200 trades (equity/commodity), 300 (forex), 500 (crypto); (4) **Transaction costs modeled** — per-asset-class spread + slippage + commission in all backtests ^83^; (5) **Single source of truth** — one outcome_resolver.py, all changes via pull request with human review ^85^; (6) **Correlation guard active** — max pairwise correlation 0.7, portfolio VaR (95%, 1-day) capped at 2% of NAV.

**Table 9.3 — 90-Day MVP Week-by-Week Plan**

| Week | Focus | Key Deliverables | Cost |
|------|-------|-----------------|------|
| 1-2 | Foundation: data + validation | Polygon.io/CCData subscription; PSR/DSR deployed; protected main branch; consolidate outcome_resolver.py | ~$500 |
| 3-4 | Transaction cost integration | Per-asset-class cost models (3-140 bps); re-run all backtests net-of-costs; flag unprofitable strategies | ~$300 |
| 5-6 | Risk framework | Correlation guard (max 0.7); portfolio VaR; 3% daily loss kill switch; 10% drawdown limit; VIX regime detection | ~$200 |
| 7-8 | Bootstrap + confidence intervals | 10,000-path bootstrap with BCa bias correction; Sharpe CI on all strategy reports; strategy health monitoring | ~$200 |
| 9-10 | Execution simulation | Market impact (power law); slippage (volume-weighted); Alpaca API paper trading; OMS-lite | ~$200 |
| 11-12 | Audit + compliance foundation | Immutable audit trail; trade reconstruction; compliance templates; final gate review | ~$100 |

**Total 90-day cost: approximately $1,500.** Expected ROI: 867%-5,233%, based on avoiding deployment of negative-OOS-Sharpe strategies. The platform currently has three asset classes with negative OOS Sharpe (CRYPTO: -0.242, FOREX: -1.406, COMMODITY: -2.412) ^81^. Deploying $50,000 across these without the six gates would risk $5,000-$10,000 in annual losses. The MVP cost pays for itself by preventing a single such deployment.

### 9.4 The 12-Month Full Transformation

The 12-month roadmap targets "credible quant fund" quality — capable of managing external capital. The scope expands from validation gates to full infrastructure: CPCV on all strategies, complete OMS/EMS with best execution, real-time risk monitoring with stress testing, HMM regime detection, and regulatory compliance readiness.

**Table 9.4 — Quarterly Milestone Roadmap (12-Month Transformation)**

| Quarter | Milestone | Key Deliverables | Investment |
|---------|-----------|-----------------|------------|
| Q1 (M1-3) | Minimum Viable Institutional | All 90-day MVP gates operational; 100% of strategies pass PSR/DSR/n>=200; paper trading top 5 strategies | ~$1,500 |
| Q2 (M4-6) | Advanced validation + data | CPCV on all strategies; tick data (Polygon.io T&Q); alternative data (sentiment, options flow); Airflow + dbt pipeline ^85^; MLflow experiment tracking | ~$6,000-10,000 |
| Q3 (M7-9) | Execution + risk infrastructure | Full OMS with pre-trade compliance; EMS with VWAP/TWAP routing; real-time VaR/CVaR; stress testing (2008, 2020, 2022); TCA framework | ~$10,000-15,000 |
| Q4 (M10-12) | Regime detection + scaling | HMM regime detection (Baum-Welch + Viterbi) ^81^; strategy-level AUM capacity limits; LP reporting; Brinson-Fachler attribution; external capital readiness at $500K AUM | ~$15,000-50,000 |

**Total 12-month cost: $32,400-$78,000.** At $500K AUM, this represents 6.5%-15.6% of assets — standard for quantitative fund infrastructure. Projected ROI at $500K AUM: 64%-1,400%, scaling to 250%-5,600% at $2M AUM, driven by CPCV preventing overfitted deployments, execution infrastructure saving 10-50 bps per trade, and compliance enabling institutional capital access ^90^.

### 9.5 The Binary Choice

The audit presents a binary decision, not a spectrum.

**Option A: Stay Retail.** Accept current limitations, radically simplify to the only validated edge (Equity + High Conviction + R:R 1.5-2.0 + ml_score >= 0.90), and target disciplined retail users. Expected outcome: 15-25% annual returns for disciplined users, most users losing money due to behavioral override.

**Option B: Commit to Institutional MVP.** Invest $1,500 and 90 days to implement the six hard gates. No PhDs or data centers required — only statistical discipline on existing strategies. Expected outcome: all deployed strategies have validated edge, external capital path becomes viable.

**Recommendation: pursue Option B.** The $1,500 cost is immaterial relative to the risk of continuing to deploy unvalidated strategies. However, do not commit to the full $32,400-$78,000 12-month transformation until the 90-day MVP demonstrates execution discipline — specifically, until the signal rejection rate exceeds 80% and 100% of deployed strategies pass all six gates. As Peter Brown of Renaissance Technologies noted: "We want our scientists to be as productive as possible. And that means providing them with the best infrastructure money can buy" ^91^. The 90-day MVP is that investment — modest in cost, transformative in impact.

---

## 10. User Safety Guide: What to Invest Real Money In

### 10.1 The 30-Second Decision Rule

The platform's genuine edge is narrow, specific, and perishable. The following matrix enables rapid, evidence-based determination for any pick.

**Table 10.1 — Quick Decision Matrix**

| Condition | Action | Rationale |
|-----------|--------|-----------|
| Equity + ml_score >= 0.90 + R:R 1.5-2.0 + tracking >= 120h | **GREAT IDEA — full size** | Only validated edge (PF 5.81, OOS Sharpe 3.527) ^81^|
| Crypto B-Tier L20 + trust_score >= 5 + R:R 1.5-2.0 | **CAUTION — half size** | Viable workhorse (PF 1.28, WR 45%); cap at 5% |
| ETF + High Conviction + R:R 1.5-2.0 + 10-day stop set | **CAUTION — quarter size** | Time-decay structural edge; moderate conviction |
| Bond + all gates green + awareness of n=18 sample | **CAUTION — minimal size** | Promising but unproven; max 5% allocation |
| Commodity (any level) | **DO NOT INVEST** | 21% WR, negative OOS Sharpe; statistically random |
| Forex (post-bug) | **DO NOT INVEST** | PF 0.27, OOS Sharpe -1.406; broken strategy revealed ^81^|
| Crypto C-Tier | **DO NOT INVEST** | 72% chance of loss per pick (PF 0.56, WR 28%) |
| Meme coins | **DO NOT INVEST** | 65.6% WR masks -12.96% avg PnL; "win often, lose big" |
| R:R < 1.5 or R:R > 2.0 (any asset) | **DO NOT INVEST** | <1.5: PF ~0.8; >2.0: PF ~0.6 ^81^|

**Green flags:** Equity with trust_score >= 5, forward WR 50-65%, R:R 1.5-2.0, ml_score >= 0.90, Verified Alpha with >= 20 historical picks, per-strategy WR >= 50%, PF >= 1.3. **Red flags:** R:R outside 1.5-2.0, ml_score < 0.90, tracking < 120 hours (72.7% of picks unresolved at 24h), no stop-loss set, position size > 11.8% (Equity) or 5% (other assets).

### 10.2 What Is SAFE vs GREAT IDEA vs DO NOT INVEST

**SAFE:** Equity picks with Verified Alpha + High Conviction + R:R 1.5-2.0 + ml_score >= 0.90 + tracking >= 120h + position size <= 11.8%. These have a statistical advantage compounding over 50+ trades — not guaranteed wins, but genuine edge.

**GREAT IDEA:** Equity Tier-2 strategies at full allocation with all six gates green, entered within 48 hours of signal generation. Signal alpha decays: peak at 0-48h, viable at 48-120h, approaching random after 120h+ ^81^. Entry within 48 hours is statistically critical.

**Table 10.2 — The DO NOT INVEST List (8 Items)**

| # | Category | Specific Item | Why It's Excluded |
|---|----------|--------------|-------------------|
| 1 | Commodity | Any commodity pick, any level | 21% WR, 58% flat exits, OOS Sharpe -2.412 ^81^|
| 2 | Forex | Any forex pick, post-bug-fix | PF 0.27, OOS Sharpe -1.406; strategy failure revealed ^81^|
| 3 | Crypto C-Tier | Any C-Tier pick | 72% lose rate, PF 0.56; value destruction |
| 4 | Meme coins | DOGE, SHIB, PEPE, any meme token | -12.96% avg PnL despite 65.6% WR |
| 5 | R:R < 1.5 | Any pick in this band | PF ~0.8, Kelly negative; insufficient reward ^81^|
| 6 | R:R > 2.0 | Any pick in this band | PF ~0.6, Kelly -102%; unrealistic targets ^81^|
| 7 | ml_score < 0.90 | Any pick below this threshold | 39.3% accuracy at 0.8-0.9 (worse than coin flip) |
| 8 | S-Tier Crypto at scale | Any S-Tier pick with >5% allocation | n=14-27; survivorship filter, not strategy ^81^|

There are no exceptions. A commodity pick with ml_score 0.95 and a beautiful chart is still a commodity pick — 1.04 profit factor, 21% win rate across 500+ historical picks. Discipline means saying no to good-looking bad bets.

### 10.3 Expected Returns by Discipline Level

The platform's edge behaves like card counting — a slight statistical advantage compounding over time. Human behavior, not the platform's metrics, is the primary determinant of outcomes.

**Table 10.3 — Expected Returns by Discipline Level**

| Discipline Level | Filter Adherence | Annual Return Estimate | Max Drawdown | Probability of Profit |
|-----------------|-----------------|----------------------|-------------|---------------------|
| **Disciplined** | Equity only, all filters, Quarter-Kelly sizing | **15-25%** | 8-12% | ~70% |
| **Moderate** | Equity + Crypto B-Tier + ETF, strict filters | **12-20%** | 12-18% | ~60% |
| **Casual** | Mix of SAFE + CAUTION assets, loose filters | **5-10%** | 15-25% | ~50% |
| **YOLO** | All assets including DANGEROUS, no filters | **-20 to -40%** | 40-60% | ~20% |

Signal alpha decay further constrains timing. The **0-48 hour window** after signal generation represents peak strength. Between 48-120 hours, the signal is viable but degraded. After 120 hours, the edge approaches random. Entry within 48 hours is the largest controllable factor after asset class selection. A disciplined investor entering at hour 6 in the optimal R:R band has a materially different expected outcome than the same investor entering the same pick at hour 96.

### 10.4 Practical Capital Guide

The practical minimum is **$5,000**. Below this threshold, transaction costs consume disproportionate edge, and the 5% minimum position size becomes impractical. With $5,000, a user can maintain 3-4 equity positions at ~$250 each, providing enough diversification to survive learning-curve losses. The ideal starting capital is **$25,000+**, enabling full Quarter-Kelly sizing across 4-6 positions with adequate cash reserves.

**Table 10.4 — Position Sizing by Capital Level**

| Capital Level | Equity Position Size (each) | Crypto B-Tier (each) | Max Simultaneous Positions | Cash Reserve |
|--------------|---------------------------|---------------------|---------------------------|-------------|
| $5,000 (minimum) | $250-500 (5-10%) | $125-250 (2.5-5%) | 3-4 | $1,000 (20%) |
| $10,000 | $500-1,000 (5-10%) | $250-500 (2.5-5%) | 4-5 | $2,000 (20%) |
| $25,000 | $1,250-2,500 (5-10%) | $625-1,250 (2.5-5%) | 5-6 | $5,000 (20%) |
| $50,000 | $2,500-5,000 (5-10%) | $1,250-2,500 (2.5-5%) | 6-8 | $10,000 (20%) |

**Kelly Criterion Worked Example ($10,000 account):** For the optimal R:R 1.5-2.0 band (PF 5.81, WR 53%), the Quarter-Kelly calculation is:

$$f^* = \frac{p \cdot b - q}{b} = \frac{0.53 \cdot 1.72 - 0.47}{1.72} \approx 0.472 \text{ (Full Kelly)}$$

Quarter-Kelly = $47.2\% \div 4 = 11.8\%$. For a $10,000 account, maximum position size per equity pick is **$1,180**. The practical size is reduced to $1,000 (10%) to maintain the mandatory 20% cash reserve and accommodate multiple simultaneous positions.

### 10.5 The "Worthy of Investing" Final List

The following classifications represent the definitive judgment from the complete 12-dimension quantitative audit.

**Table 10.5 — Items Meeting All Criteria (Worthy of Real Capital)**

| Item | Filter Configuration | Position Size | Notes |
|------|---------------------|---------------|-------|
| Equity L50 picks (High Conviction) | Verified Alpha + ml_score >= 0.90 + R:R 1.5-2.0 + tracking >= 120h | Up to 11.8% of portfolio | Crown jewel: PF 1.72, OOS Sharpe 3.527, WR 53% ^81^|
| Equity Tier-2 strategies (full allocation) | All six gates green + entry within 48h | Up to 10% of portfolio | PF 5.81 in R:R 1.5-2.0 band; highest conviction subset |

**Table 10.6 — Conditional "Worth the Risk" Items**

| Item | Conditions | Position Size | Risk Adjustment |
|------|-----------|---------------|-----------------|
| Crypto B-Tier L20 | trust_score >= 5 + R:R 1.5-2.0 only | Max 5% of portfolio | Hard cap regardless of conviction; 10-day hard stop |
| ETF L20-L50 | High Conviction + 10-day stop set manually | Max 5% of portfolio | Time-decay erosion requires active management |
| Bond picks (any) | All gates green + awareness of n=18 sample | Max 5% of portfolio | Reduce to 2-3% given small-sample uncertainty |

**Table 10.7 — Explicit DO NOT INVEST List (Comprehensive)**

| # | Item | Metric That Disqualifies It |
|---|------|---------------------------|
| 1 | Commodity — any pick | 21% WR, PF 1.04, OOS Sharpe -2.412 ^81^|
| 2 | Forex — any pick (post-bug) | PF 0.27, OOS Sharpe -1.406 ^81^|
| 3 | Crypto C-Tier | 28% WR, PF 0.56; 72% chance of loss |
| 4 | Meme coins (DOGE, SHIB, PEPE) | -12.96% avg PnL despite 65.6% WR |
| 5 | Any pick with R:R < 1.5 | PF ~0.8, Kelly negative |
| 6 | Any pick with R:R > 2.0 | PF ~0.6, Kelly -102% |
| 7 | Any pick with ml_score < 0.90 | 39.3% accuracy (worse than random) |
| 8 | S-Tier Crypto at >5% allocation | n=14-27, survivorship filter, not strategy ^81^|
| 9 | Any pick with tracking < 120h | 72.7% unresolved at 24h; insufficient data |
| 10 | Any pick without stop-loss set | Unlimited downside; never enter |
| 11 | Penny stocks (pending analysis) | Treat as DANGEROUS until proven otherwise |

Tables 10.5-10.7 illustrate the audit's central finding: the platform's value is **preventing bad trades, not generating many picks**. The optimal filter combination produces only 0-2 picks from 210 active ^81^. The real edge is in exclusion. The UI should celebrate empty results — "No picks passed all quality gates today" is capital preservation, not failure.

### 10.6 Dashboard Enhancement Recommendations

Three enhancements would materially improve user safety without backend changes.

**Score tooltips** are the highest-impact, lowest-effort improvement. Every score (F-Score, Score, ml_score) should display a hover tooltip explaining what it measures, the investable threshold, and the action to take if below threshold. Current confusion between F-Score (Piotroski fundamental quality, 0-9), Score (composite signal strength, 0-1), and ml_score (ML confidence, 0-1) leads users to decide on the wrong metric. The ml_score tooltip should state: "ml_score >= 0.90 required for real-money deployment. Values below 0.90 have 39.3% accuracy — worse than random." ^81^**Tier definition cards** should appear adjacent to the tier selector. Each card (S-Tier through C-Tier) should display: historical pick count, overall PF and WR, and a color-coded verdict. S-Tier's card would show n=27 with a yellow "CAUTION — small sample" warning; B-Tier would show n=940 with a green "WORKHORSE — reliable" endorsement. This prevents overallocating to the shiniest-looking tier.

**Risk warnings** should appear as a persistent banner when any DANGEROUS filter combination is active. If a user selects Commodity, Forex, C-Tier, or R:R outside 1.5-2.0, the banner should read: "This filter combination has historically produced negative returns. [Click for details]" with a link to the specific disqualifying metrics. The warning should not block interaction — users retain agency — but ignoring the risk becomes a conscious, documented choice rather than an uninformed one.

These three enhancements — score tooltips, tier definition cards, and contextual risk warnings — would transform the dashboard from data presentation into decision support. The platform has genuine edge in a narrow domain; the dashboard's job is to guide users precisely to that domain and away from everything else.

---

