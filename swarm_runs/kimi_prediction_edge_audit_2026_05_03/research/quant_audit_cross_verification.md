# Phase 4: Cross-Verification Results

## High Confidence Findings (Confirmed by 2+ agents, independent sources)

### HC-1: Only Equity Has Genuine Statistical Edge
- **Dim01** (Asset Edge): Equity passes all 5 gates (PF 1.72, OOS Sharpe +3.527, n=136+)
- **Dim05** (Backtesting): OOS Sharpe +3.527 exceeds Dim05's institutional threshold of +1.5
- **Dim08** (Risk): Equity Quarter-Kelly at 5.3%, consistent with PF 1.72
- **Dim11** (Safety Guide): Rates Equity as only SAFE asset class
- **Status:** CONFIRMED — Equity is the crown jewel

### HC-2: R:R 1.5-2.0 Band is the Only Profitable Zone
- **Dim01**: Confirms PF 5.81, Kelly +47.2% in this band
- **Dim08**: Mathematically verifies Quarter-Kelly 11.8% for this band, 0% for others
- **Dim03**: UI analysis confirms R:R 1.5+ filter produces best risk-adjusted picks
- **Status:** CONFIRMED — Hard floor at 1.5, hard ceiling at 2.0

### HC-3: Composite Scoring System is Fundamentally Broken
- **Dim02**: Score Calibration Audit shows r=+0.10 for composite, regime_bonus is anti-predictive (r=-0.115)
- **Dim03**: UI shows confusing multiple score displays without explanation
- **Dim12**: Hedge fund gap analysis flags "no validated scoring" as existential gap
- **Status:** CONFIRMED — Score needs repair before it can be trusted

### HC-4: Meme Coins Should Be Excluded
- **Dim07**: 99.7% risk of ruin, 0.4% of Pump.fun traders profitable, Kelly = -244%
- **Dim06**: Similar structural pattern — small wins, catastrophic losses
- **Dim08**: Risk analysis says 0% allocation mathematically required
- **Status:** CONFIRMED — Exclude from quantitative system entirely

### HC-5: Penny Stocks Are Wealth Destruction for Most
- **Dim06**: Average returns -24% to -27% annually, median -37%
- **Dim08**: Quarter-Kelly gives near-zero allocation even with best-case assumptions
- **Dim12**: Professional firms (AQR, Dimensional) systematically exclude them
- **Status:** CONFIRMED — If included, maximum 5% allocation with strict filters

### HC-6: The HTML Nested Comment Bug Exists in US Equity Picks Tab
- **Dim09**: Found exact location (template.html lines 1813-1825), root cause identified
- **Dim03**: UI investigation confirms "weird text" visible on US Equity Picks tab
- **Status:** CONFIRMED — Fix: replace with simple `<!-- UEPS mount point -->`

### HC-7: 6 Days Is Insufficient to Assess Resolver Fix Impact
- **Dim10**: Statistical minimum is 200-500 trades; at current velocity needs 3-8 weeks
- **Dim05**: Institutional validation requires 90+ days for regime coverage
- **Status:** CONFIRMED — Wait until June 1 for meaningful PF/WR evaluation

### HC-8: Verified Alpha + High Conviction is Optimal UI Path
- **Dim03**: Triple-filter (Verified Alpha + High Conviction + R:R 1.5+) gives 66-70% WR
- **Dim01**: Confirms these picks come from safest asset classes
- **Dim11**: Safety guide recommends this exact filter chain
- **Status:** CONFIRMED — Best daily driver: Verified Alpha + High Conviction

---

## Medium Confidence Findings (Single authoritative source)

### MC-1: ETF OOS Sharpe 6.368 is Artifact of Tiny Sample
- **Dim01**: Flags as suspicious with only 12 folds and 10.8 decay
- **Dim05**: Deflated Sharpe Ratio would reduce this to 2.0-3.0 range
- **Status:** LIKELY TRUE — But needs DSR calculation to confirm

### MC-2: Four Strategies Are Profitably Invertible
- **Dim04**: myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA
- Academic basis: momentum reversal literature (Jegadeesh & Titman, Hong & Stein)
- **Status:** PLAUSIBLE — But needs paper trading before live deployment

### MC-3: Platform Has ~5% of Institutional Infrastructure
- **Dim12**: Gap analysis against Renaissance/Two Sigma/Citadel standards
- **Status:** REASONABLE ESTIMATE — Based on publicly available information

### MC-4: ml_score >= 0.90 is Optimal Threshold
- **Action Plan**: Claims 66.7% accuracy at 0.9+ vs 39.3% at 0.8-0.9
- **Dim02**: But Score Calibration Audit shows 0.70-0.79 is actual sweet spot (57% WR)
- **Status:** CONFLICT — See Conflict Zone C-1 below

---

## Low Confidence Findings (Weak sourcing or single unverified claim)

### LC-1: Signal Quality ML Predictor Improves WR by 5-15pp
- **Action Plan**: Claims +5-15pp WR improvement
- **Dim12**: Notes this is "code review only" evidence grade
- **Status:** UNVERIFIED — Needs actual backtest

### LC-2: CEF NAV Discount Strategy (17.3% annual, Sharpe 1.86)
- **Action Plan**: Cites "CUNY paper"
- **Status:** UNVERIFIED — Cannot locate original paper

---

## Conflict Zones

### C-1: Optimal ml_score Threshold
- **Action Plan says**: ml_score >= 0.90 (66.7% accuracy)
- **Dim02 says**: Confidence 0.70-0.79 is sweet spot (57% WR), 0.90+ WORSE (47% WR)
- **Analysis**: These may be measuring DIFFERENT scores. Action Plan refers to "ml_score" (gating threshold), Dim02 refers to "confidence" (display score). The platform has multiple score types and they behave differently at different thresholds.
- **Resolution**: BOTH may be correct for their respective score types. Users should filter by trust_score >= 5 (68-71% WR) rather than any ml_score threshold.

### C-2: Forex Verdict (HALT vs MONITOR)
- **Dim01 says**: DANGEROUS — PF 0.27, OOS Sharpe -1.406 → HALT
- **Action Plan says**: TRUE WR ~49% post-bug-fix, PF 3.59 from "trusted filter" → T3 candidate
- **Analysis**: These use DIFFERENT data slices. PF 0.27 is overall; PF 3.59 is from a specific "trusted" subset. The trusted filter may have selection bias.
- **Resolution**: The Dim10 finding that 6 days is insufficient applies here. HALT for now, reassess June 1 with 30+ days of post-fix data.

### C-3: Crypto S-Tier (SCALE vs ABANDON)
- **Dim01 says**: DANGEROUS — n=27, negative OOS Sharpe → ABANDON
- **Action Plan says**: Exceptional metrics, scale with on-chain data
- **Analysis**: The metrics ARE exceptional (PF 6.80, WR 70.4%) but n=27 is statistically meaningless. OOS Sharpe is negative for ALL crypto tiers collectively.
- **Resolution**: CAUTION — Don't abandon the strategy but don't scale either. Require n>=50 before any allocation increase. Current allocation should be minimal.
