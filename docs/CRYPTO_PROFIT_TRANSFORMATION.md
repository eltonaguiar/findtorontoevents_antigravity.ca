# Crypto Prediction System: Profit Transformation Plan

**Date:** 2026-03-24
**Analyst:** Quantitative Trading Advisor
**Data basis:** 558 closed picks (alpha_engine), 1927 scored picks (IC analysis), 65 paper trades

---

## Current State Diagnosis

The system is not break-even — it is actively losing money. The paper portfolio shows -5.42% ($1000 to $946) over 8 days. The headline 41.9% WR with a 1.19 profit factor comes from backfilled picks inflating the numbers. Live forward performance is worse.

**Critical findings from the data:**

| Metric | Value | Verdict |
|--------|-------|---------|
| Paper trading PnL | -$54.22 (-5.42%) | **Losing money** |
| Paper profit factor | 0.75 | **Below 1.0 = net loser** |
| Paper expectancy/trade | -$0.92 | **Negative edge** |
| Closed picks WON/LOST | 201W / 255L | 44.1% WR system-wide |
| Scoring Spearman (WR) | 0.003 | **Effectively random** |
| Scoring Spearman (PnL) | 0.224 | Weak but present |
| Feature health | 1 alive, 4 weak, 27 dead | **ML cannot work** |
| ML model status | force_retrain (no model) | **Offline** |
| ENJ single trade | -$96.17 (99% of account) | **Position sizing failure** |
| LONG WR (paper) | 34.7% | **Catastrophic** |
| SHORT WR (paper) | 62.5% | Actually working |
| Decile test verdict | BROKEN | Score does not predict outcomes |
| Anti-predictive components | 7 of 21 scoring components | **Scoring hurts performance** |

---

## The Three Root Causes (in order of severity)

### Root Cause 1: The Scoring System Is Anti-Predictive

This is the single biggest problem. Seven of twenty-one scoring components have **negative** information coefficients — they are actively ranking bad picks higher:

| Component | IC | Mean Weight | Impact |
|-----------|-----|------------|--------|
| ml_score | -0.194 | 3.81 pts | **Worst offender** |
| source_system | -0.181 | 14.70 pts | Highest-weighted anti-signal |
| confidence | -0.140 | 0.64 pts | Overconfident picks lose more |
| risk_reward | -0.127 | 3.49 pts | Higher R:R = more losses |
| age_freshness | -0.076 | -1.38 pts | Mild negative |
| leverage_safety | -0.054 | 6.67 pts | Mild negative |
| proven_strategy_bonus | -0.003 | 0.27 pts | Near zero |

Meanwhile, the **only four predictive components** are underweighted:

| Component | IC | Mean Weight |
|-----------|-----|------------|
| regime_bonus | +0.190 | 4.27 pts |
| strategy_track_record | +0.173 | 0.05 pts (!!!) |
| forward_wr | +0.165 | 5.22 pts |
| technical_alignment | +0.160 | -1.11 pts (negative avg!) |

The composite score `source_system` carries 14.7 points on average and is anti-predictive at IC=-0.18. This single component is doing more damage than any other factor in the system.

### Root Cause 2: The System Takes Too Many Trades With No Edge

The decile test shows the scoring is BROKEN — Q1 WR (33.6%) vs Q4 WR (35.2%) is a 1.6% spread. Random would produce larger separation. The system emits picks that a coin flip would match.

With 60+ strategies, most have fewer than 20 trades. Of the 26 strategies in IC analysis, only 7 are predictive. But the system gives equal or near-equal weight to all of them.

### Root Cause 3: Position Sizing Ignores Catastrophic Risk

The ENJ trade lost $96.17 — that was 98.7% of the account on a single position. Despite having Kelly sizing and circuit breakers deployed, one trade consumed the account. This suggests the safeguards are either not wired into the paper trading pipeline or their limits are far too high.

---

## 8 Prioritized Recommendations

### PRIORITY 1 (Highest Leverage — Do These First)

---

#### Recommendation 1: Flip Anti-Predictive Scoring Weights to Zero or Negative

**Timeline:** Quick win (1 day)
**Expected impact:** +5-8% WR improvement, scoring Spearman from 0.003 to 0.15+
**Files to change:** `alpha_engine/smart_picks_engine.py` (function `score_pick`, lines 345-370), `alpha_engine/meta_consensus_scorer.py`

**What to do:**

In `smart_picks_engine.py`, the scoring formula at line 345 uses regime (25%), elite/quality (35%), freshness (15%), tp_upside (15%), htf_alignment (10%). The IC data proves this allocation is wrong.

Concrete changes:
1. **Zero out `source_system` contribution.** It has IC=-0.18 with the highest mean weight (14.7 pts). It is the single most damaging input. In `meta_consensus_scorer.py`, find where source_system adds to the score and set its weight to 0.
2. **Zero out `ml_score` contribution.** IC=-0.19. The ML model is offline anyway (force_retrain status with no data). Any residual ml_score influence is pure noise.
3. **Zero out `confidence` as a scoring input.** IC=-0.14. The data shows higher-confidence picks actually lose more. The strong signal filter already uses confidence as a filter gate (0.60-0.70 sweet spot), which is correct — just stop using it as a ranking signal.
4. **Double the weight of `strategy_track_record`.** IC=+0.173 but current mean contribution is only 0.05 points. This is the second-best predictor and it has almost zero influence.
5. **Increase `regime_bonus` weight.** IC=+0.190, the best single predictor. Keep it as the dominant factor.

New approximate allocation: regime_bonus 35%, strategy_track_record 25%, forward_wr 20%, technical_alignment 20%. Everything else at 0.

**What could go wrong:** If the IC measurements are noisy due to small sample sizes for some strategies, zeroing source_system could remove a useful signal for those specific strategies. Mitigation: monitor WR for 48 hours after the change.

---

#### Recommendation 2: Hard-Kill the Worst 10 Strategies Immediately

**Timeline:** Quick win (1 day)
**Expected impact:** +3-5% WR by removing negative-expectancy noise
**Files to change:** `alpha_engine/production_scanner.py` (wherever strategies are registered/enabled)

**What to do:**

The IC analysis identifies these strategies as actively destructive (anti-predictive with negative PnL):

| Strategy | IC | Avg PnL | WR | Trades | Action |
|----------|-----|---------|-----|--------|--------|
| crypto_soc_orderflow_absorption_a06_v1 | -0.491 | -0.04 | 40% | 10 | **KILL** |
| crypto_soc_orderflow_absorption_a02_v1 | -0.350 | -0.54 | 18.8% | 16 | **KILL** |
| atr_regime_rsi | -0.213 | -0.29 | 25% | 28 | **KILL** |
| crypto_soc_orderflow_absorption_a07_v1 | -0.200 | -0.44 | 26.3% | 19 | **KILL** |
| crypto_mtf_ema_slope_alignment_v1 | -0.163 | -0.49 | 21.4% | 14 | **KILL** |
| crypto_soc_orderflow_absorption_a03_v1 | -0.116 | -0.24 | 33.3% | 15 | **KILL** |
| winner_pattern_precursor | +0.035 | -1.67 | 10.4% | 48 | **KILL** |
| hl_funding_fade | +0.026 | -4.29 | 20% | 20 | **KILL** |
| claude_gainer_ml | 0.000 | -2.71 | 10% | 10 | **KILL** |
| macd_rsi_confluence | 0.000 | 0.00 | 0% | 10 | **KILL** |

That is 10 strategies producing 196 trades with overwhelmingly negative PnL. Killing them does not violate the "mutate before kill" rule because these have been given 10-48 trades each and their track records are clear.

Also: `multi_period_rsi_confluence_xrp` (WR 7.7%, 13 trades) should be killed.

**What could go wrong:** Reducing the strategy count reduces trade volume, which means fewer opportunities. But trades with negative expectancy are worse than no trades.

---

#### Recommendation 3: Cap Position Size at 2% of Account (Hard Enforcement)

**Timeline:** Quick win (2 hours)
**Expected impact:** Prevents catastrophic single-trade blowups; converts -5.42% drawdown trajectory into survivable -1% to -2% range
**Files to change:** Paper trading allocation logic (wherever position_size is calculated for the paper portfolio)

**What to do:**

The ENJ trade used 98.7% of the $1,000 account ($987.04 position). This means either:
- Kelly sizing calculated an absurdly high allocation (possible if confidence was very high and the model had no track record data), or
- The paper trading pipeline bypasses the Kelly/VaR modules entirely

Add a **hard cap** as the very last line before any trade is placed:
```python
MAX_POSITION_PCT = 0.02  # 2% of account, non-negotiable
position_size = min(position_size, account_balance * MAX_POSITION_PCT)
```

This is a circuit breaker, not an optimization. Even if Kelly says 50%, the answer is 2%.

For a $1,000 account, this means max $20 per trade. With a -5% stop loss, max risk per trade = $1 (0.1% of account). This is conservative but it means the system can survive 50 consecutive losses.

**What could go wrong:** With $20 per position, the absolute dollar profits will be tiny. This is correct — the system should not be sizing up until it has a proven positive expectancy over 100+ trades.

---

### PRIORITY 2 (Structural Fixes — Next 3-5 Days)

---

#### Recommendation 4: Fix the Feature Pipeline (18 of 32 Features Dead)

**Timeline:** Structural fix (3-5 days)
**Expected impact:** Enables ML retraining, which is a prerequisite for any ML-driven improvement
**Files to change:** `alpha_engine/feature_populator.py`, `alpha_engine/meta_consensus_scorer.py`

**What to do:**

The feature health report shows 27 dead features (only 1 alive). The most critical dead features are:

- `strategy_encoded` — 0 samples. This is trivially derivable from the pick's strategy name.
- `strategy_win_rate` — 0 samples. Must be computed from closed_picks.json.
- `strategy_sharpe` — 0 samples. Same source.
- `hour_utc` — 0 samples. Trivially derivable from pick timestamp.
- `regime_encoded` — 98% zero. The regime detector is apparently not wiring data into picks.
- `rsi_at_entry` — 66% missing. Should come from the technical analysis done at pick time.
- `volume_ratio` — 62% missing. Same.

The model_comparison.json shows `force_retrain` status with the note "39 features aligned." This suggests someone recently wired the feature populator. Verify it is actually populating by checking the next batch of picks after the scanner runs.

Priority order for feature fixes:
1. `strategy_win_rate` and `strategy_sharpe` (compute from closed_picks, highest IC potential)
2. `regime_encoded` (fix the wiring from fast_regime_detector)
3. `strategy_encoded` (simple label encoding)
4. `hour_utc` / time features (trivial to add)

Do NOT fix interaction features (`rsi_x_regime`, `vol_ratio_x_regime`, etc.) until the base features work.

**What could go wrong:** Fixing features does not fix the model if the model architecture is wrong. The meta_consensus_scorer's heuristic scoring should be the baseline, and the ML model should only be promoted when it demonstrably beats the heuristic on held-out data.

---

#### Recommendation 5: Eliminate Shorts and Forex Until They Work in Paper

**Timeline:** Quick win (1 day) for the block; structural fix (1-2 weeks) to make them work
**Expected impact:** Removes known negative-EV trade categories

**What to do:**

Paper trading shows:
- LONG trades: 34.7% WR, -$69.37 total PnL (net loser)
- SHORT trades: 62.5% WR, +$15.15 total PnL (net winner!)

This contradicts the known system metric of 14.8% short WR. The discrepancy likely comes from the paper trading using a different strategy mix than the backtested shorts. The paper portfolio's shorts are working because they are from the `st_fear_greed_contrarian` strategy (IC=+0.081, 604 trades, positive avg_pnl).

For the alpha_engine closed picks: SELL signals number 58 out of 558 total. Without a per-direction WR breakdown in closed_picks.json, the known system-wide short WR of 14.8% from the audit suggests the non-paper shorts are terrible.

**Action:** In `production_scanner.py` and `smart_picks_engine.py`, add a direction filter:
- Block all SHORT signals except from strategies with >30 closed short trades and >40% WR on shorts
- Block ALL forex picks (0% WR on closed trades per the known metrics)
- Block all equity picks until at least 20 closed equity trades show >45% WR

**What could go wrong:** If the market enters a sustained downtrend, having no short capability means the system will bleed on longs. Mitigation: keep shorts from proven strategies (identified above) and add a global "bear mode" flag that loosens the short filter when BTC is below its 50-day EMA.

---

#### Recommendation 6: Concentrate on Proven Winners Only (Top 5 Strategies)

**Timeline:** Structural fix (3-5 days)
**Expected impact:** +8-12% WR by allocating capital only to strategies with demonstrated edge
**Files to change:** `alpha_engine/production_scanner.py`, strategy selection logic

**What to do:**

From IC analysis, only these strategies have both positive IC and positive avg_pnl:

| Strategy | IC | Avg PnL | WR | Trades |
|----------|-----|---------|-----|--------|
| strong consensus | +0.191 | +7.25% | 45.5% | 11 |
| crypto_bayesian_regime_transition_momentum_v1 | +0.117 | +0.29% | 58.8% | 34 |
| st_fear_greed_contrarian | +0.081 | +0.21% | 27.6% | 604 |
| vwap_deviation_reversion_xrp_v1 | +0.330 | +0.63% | 41.7% | 12 |
| funding_momentum | -0.067 | +0.19% | 58.3% | 108 |

`funding_momentum` has negative IC but positive PnL/WR — its scoring is anti-predictive (higher-scored picks do worse) but the strategy itself finds winners. This means the strategy works but the scoring is ranking its picks incorrectly.

**Action:**
1. Create a whitelist of strategies allowed to produce active picks
2. Start with the top 5 above
3. Any new strategy must pass walk-forward validation with >45% WR on 20+ trades before joining the whitelist
4. Allocate proportionally to strategy IC: strong_consensus gets the largest allocation

**What could go wrong:** Low trade volume. With only 5 strategies, the system might produce 2-5 picks per day instead of 20+. This is acceptable — fewer high-quality trades beats more random ones. The Pareto principle applies: a few strategies will generate all the profits.

---

### PRIORITY 3 (Medium-Term Structural Improvements — 1-2 Weeks)

---

#### Recommendation 7: Rebuild the Decile Scoring From Scratch Using Only IC-Positive Components

**Timeline:** Structural fix (1-2 weeks)
**Expected impact:** Scoring Spearman from 0.003 to 0.20+, which enables meaningful pick filtering
**Files to change:** `alpha_engine/smart_picks_engine.py`, `alpha_engine/meta_consensus_scorer.py`

**What to do:**

The current decile test is BROKEN: Q1 WR 33.6% vs Q4 WR 35.2% (1.6% spread). The scoring system cannot distinguish good picks from bad ones. The score has 21 components, of which 10 are zero_variance (contributing nothing) and 7 are anti-predictive (actively harmful).

Build a new scoring function using ONLY these inputs:
1. **regime_bonus** (IC=+0.190) — Is the trade direction aligned with the current regime?
2. **strategy_track_record** (IC=+0.173) — How has this specific strategy performed historically?
3. **forward_wr** (IC=+0.165) — Forward walk-forward win rate
4. **technical_alignment** (IC=+0.160) — Do higher-timeframe indicators confirm?

Score = `w1*regime_bonus + w2*strategy_track_record + w3*forward_wr + w4*technical_alignment`

Initial weights proportional to IC: `[0.276, 0.252, 0.240, 0.232]`

Then re-run the decile test. The target is:
- Q4 WR > Q1 WR by at least 10 percentage points
- Spearman(score, WR) > 0.15
- Monotonic increase in PnL from decile 1 to decile 10

Only when these targets are met should the scoring system be used for pick filtering. Until then, use the whitelist approach from Recommendation 6.

**What could go wrong:** Overfitting the scoring weights to the 1927-pick sample. Mitigation: use the walk-forward validator to test the scoring on held-out data. Split the 1927 picks into train (first 1400) and test (last 527) chronologically. If the decile separation holds on the test set, the scoring is valid.

---

#### Recommendation 8: Implement Per-Strategy Adaptive Stop-Loss Based on Historical MFE/MAE

**Timeline:** Structural fix (1-2 weeks)
**Expected impact:** +2-4% WR improvement by reducing premature stop-outs
**Files to change:** `alpha_engine/smart_picks_engine.py` (TP/SL calculation), strategy modules

**What to do:**

The closed picks data shows:
- Average MFE (maximum favorable excursion): 0.30% — picks move in the right direction by this much on average before reversing
- Average MAE (maximum adverse excursion): -0.19% — picks move against the trader by this much on average

The strong signal filter sets fixed stop distances (1.5-3% optimal). But the actual price behavior shows much tighter movement. If stops are set at 2% but the average MAE is only 0.19%, the stops are 10x wider than needed. Conversely, if TPs are set at 3-4% but the average MFE is only 0.30%, the TPs are 10-13x more ambitious than what typically happens.

**Action:**
1. For each strategy with >20 closed picks, compute the 75th percentile MAE and MFE
2. Set the stop-loss at 1.5x the 75th percentile MAE (gives the trade room to breathe without being too wide)
3. Set the take-profit at 0.8x the 75th percentile MFE (captures most of the typical move)
4. This means R:R will be determined by actual price behavior, not by theoretical targets

Example: If a strategy's 75th percentile MAE is 0.5% and MFE is 1.2%, set SL at 0.75% and TP at 0.96%. This gives R:R of 1.28, which is lower than the current minimum of 1.5 in the strong signal filter. The R:R filter threshold should be lowered to 1.0 for strategies where the data supports it.

**Important caveat:** The MFE/MAE data has 54.5% missing values. This analysis can only be done for strategies where the data exists. The feature populator fix (Recommendation 4) will help populate this data going forward.

**What could go wrong:** Tighter stops mean more stop-outs if the market is volatile. The 75th percentile approach accounts for this, but regime-dependent adjustment is better (wider stops in high-vol regimes, tighter in low-vol).

---

## Implementation Priority Matrix

| # | Recommendation | Time | WR Impact | Difficulty | Dependencies |
|---|---------------|------|-----------|------------|--------------|
| 1 | Flip anti-predictive scoring weights | 1 day | +5-8% | Low | None |
| 2 | Kill worst 10 strategies | 1 day | +3-5% | Low | None |
| 3 | Hard cap position size at 2% | 2 hours | Prevents blowup | Low | None |
| 4 | Fix feature pipeline | 3-5 days | Enables ML | Medium | None |
| 5 | Block shorts/forex (except proven) | 1 day | +2-3% | Low | None |
| 6 | Concentrate on top 5 strategies | 3-5 days | +8-12% | Medium | #2 |
| 7 | Rebuild scoring from IC-positive only | 1-2 weeks | +5-10% | High | #1, #4 |
| 8 | Adaptive SL/TP from MFE/MAE | 1-2 weeks | +2-4% | High | #4 |

**Do recommendations 1, 2, and 3 today.** They require minimal code changes and address the three highest-impact problems. Together they should shift the system from -5% to roughly break-even.

Then do 5 and 6 this week. Then 4, 7, 8 next week.

---

## Realistic Expectations

Even with all 8 recommendations implemented perfectly, this system will not become a money printer. Here is what is realistic:

- **Week 1 (recommendations 1-3, 5):** System stops actively losing money. Paper portfolio stabilizes around break-even. WR improves from 41% to ~48-50%.
- **Week 2-3 (recommendations 4, 6, 7):** Scoring becomes weakly predictive (Spearman 0.10-0.20). Top-decile picks show 55%+ WR. System produces 3-8 high-conviction trades per day instead of 20+ mediocre ones.
- **Month 2+ (recommendation 8, ML retraining):** With clean features and validated scoring, the ML model can retrain on real data. If it achieves IC>0.15 on held-out data, it can be promoted. Target: 52-58% WR with 1.5+ profit factor on live paper trades.

The fundamental truth: a system with 60+ strategies and broken scoring is worse than a system with 5 strategies and no scoring at all. Simplify first, then add complexity only when each addition demonstrably improves out-of-sample performance.

---

## Appendix: Key File Locations

| File | Purpose |
|------|---------|
| `alpha_engine/smart_picks_engine.py` | Main scoring function (lines 294-370) |
| `alpha_engine/meta_consensus_scorer.py` | Meta-learner scoring + training (line 808+) |
| `alpha_engine/strong_signal_filter.py` | 5-filter quality gate |
| `alpha_engine/production_scanner.py` | Strategy registration/execution |
| `alpha_engine/data/ic_weights.json` | Component IC analysis (source of truth) |
| `alpha_engine/data/decile_test.json` | Scoring effectiveness test |
| `alpha_engine/data/feature_health_report.json` | Feature pipeline health |
| `alpha_engine/data/closed_picks.json` | 558 closed trade records |
| `alpha_engine/data/paper_trade_analysis.json` | Paper portfolio results |
| `alpha_engine/data/model_comparison.json` | ML model status |
| `alpha_engine/data/score_pnl_history.json` | Score-PnL correlation tracking |
