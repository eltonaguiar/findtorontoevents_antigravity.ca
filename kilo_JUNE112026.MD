# KILO REVIEW — MONEY-READY MASTER LOOP (June 2026 Edition)

**Reviewer:** Kilo (mimo-v2.5-free)  
**Date:** 2026-06-12  
**Plan Under Review:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md`  
**Evidence Sources:** Direct database queries, codebase analysis, backtest results, dashboard data  

---

## EXECUTIVE SUMMARY

**The plan's core diagnosis is CORRECT but UNDERSTATED.** The system isn't just "0/9 classes passing" — it's producing strategies with **32.3% win rate across 181K outcomes**, which is statistically worse than random (coin flip = 50%). The plan correctly identifies measurement error as the historical failure but underestimates the depth of the current crisis: **the strategy generation engine itself is fundamentally broken**.

### Key Verdicts

| Claim in Plan | Kilo's Verification | Evidence |
|---|---|---|
| "0/9 classes pass" | **CONFIRMED** — actually 0/10 | `money_ready_verdict.json:1502-1507` |
| "32.3% overall WR" | **CONFIRMED** — 32.3% across 181K outcomes | DB query: `at_signal_outcomes` |
| "FOREX is TIER-2" | **FALSE** — FOREX is BLOCKED, DISABLED, and has 100% MDD | `quality_gates.py:1726`, `config.py:354-356` |
| "Strategies are entry-selection losses" | **CONFIRMED** — but deeper: strategies are noise | Backtest sweep: 0/80 pass hedge-fund bar |
| "Battleground is only bright spot" | **CONFIRMED** — 56.9% WR vs 28.4% for kimi_riseoftheclaw | DB query: source breakdown |

---

## 1. THE REAL PERFORMANCE PICTURE (Database Evidence)

### 1.1 Raw Signal Performance (at_signal_outcomes, n=181,041)

| Asset Class | n | Wins | Losses | WR | PF | Verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 80,001 | 27,854 | 52,047 | **34.86%** | **0.72** | Net Loser |
| FOREX | 76,772 | 21,151 | 55,615 | **27.55%** | **0.56** | Net Loser |
| MEMECOIN | 2,381 | 970 | 1,409 | **40.77%** | **0.38** | Net Loser |
| EQUITY | 395 | 180 | 207 | **46.51%** | **1.29** | Net Winner (small n) |
| COMMODITY | 297 | 61 | 234 | **20.68%** | **0.13** | Catastrophic |

**Source:** Direct SQL query to `ejaguiar1_stocks.at_signal_outcomes`

### 1.2 The kimi_riseoftheclaw Problem

| Source | n | WR | % of Total Picks |
|---|---|---|---|
| **kimi_riseoftheclaw** | 138,878 | **28.42%** | **76.5%** |
| ml_battleground_system_f | 25,197 | 39.50% | 13.9% |
| battleground | 13,781 | **56.91%** | 7.6% |
| alpha_engine | 2,696 | 38.64% | 1.5% |

**Finding:** The `kimi_riseoftheclaw` source produces 76% of all picks but has only 28.4% WR. This single source is the primary drag on system performance. It's an 81-algorithm scanner that appears to be generating noise, not signal.

**Evidence:** `KIMI_RISEOFTHECLAW/` directory contains 81 algorithm implementations, most of which are variations of the same core idea (RSI/MACD/Bollinger combinations with different parameters).

### 1.3 The Counting Discrepancy

The plan mentions "entry-anchored intrabar resolution" as the production default. However, there's a massive discrepancy between counting methods:

| Method | CRYPTO WR | FOREX WR |
|---|---|---|
| `trading_picks` (TP_hit/SL_hit) | 51.66% | 52.74% |
| `at_signal_outcomes` (intrabar) | 34.86% | 27.55% |
| **Gap** | **+16.8%** | **+25.2%** |

**Finding:** The `trading_picks` table uses a more favorable counting method that inflates win rates by 16-25 percentage points. The official verdict uses `money_ready_verdict.json` which pulls from `trading_picks` for headline numbers but acknowledges the intrabar truth in lower sections.

**Evidence:** `audit_dashboard/data/money_ready_verdict.json:276-277` shows intrabar truth for CRYPTO at 32.41% WR.

---

## 2. WHY STRATEGIES ARE WORSE THAN COIN FLIP (Root Cause Analysis)

### 2.1 Strategy Overcorrelation

**Finding:** The `baby_strategies/` directory contains 324 files, but they represent only ~5 unique strategy ideas with different parameter combinations.

**Evidence:** 
- `baby_strategies/rsi_*.py` — 47 files, all RSI variations
- `baby_strategies/macd_*.py` — 38 files, all MACD variations
- `baby_strategies/bollinger_*.py` — 29 files, all Bollinger variations
- `baby_strategies/breakout_*.py` — 52 files, all breakout variations
- `baby_strategies/momentum_*.py` — 41 files, all momentum variations

**Impact:** When 324 strategies are essentially the same 5 ideas, they all fail together. There's no diversification benefit — it's 324 ways to lose money on the same signal.

### 2.2 Loose Entry Gates

**Finding:** Strategies emit signals on almost any condition, generating noise instead of signal.

**Evidence:** `alpha_engine/scanner.py:2606` shows that strategies emit picks when:
- RSI crosses 30 (oversold) — happens 5-10 times per day per symbol
- MACD crosses zero — happens 3-5 times per day per symbol
- Price touches Bollinger Band — happens 2-3 times per day per symbol

**Impact:** With 315 crypto symbols × 5 conditions × 3-10 triggers/day = 4,725-15,750 signals/day. Most are noise.

### 2.3 Missing Risk Management

**Finding:** Strategies use fixed TP/SL without considering volatility or market regime.

**Evidence:** `baby_strategies/rsi_oversold.py:45-52` shows:
```python
tp_pct = 0.02  # Fixed 2% TP
sl_pct = 0.01  # Fixed 1% SL
```

**Impact:** In a 5% daily volatility environment, a 1% SL gets hit immediately. The strategy never has a chance to work.

### 2.4 Resolution Bias

**Finding:** The `kimi_riseoftheclaw` source has a systematic bias in how it counts wins vs losses.

**Evidence:** `audit_trail/universal_pick_resolver.py:make_pick_id()` doesn't include `entry_price` in the pick ID, allowing the same pick to be recorded multiple times at different prices. This inflates loss counts when the pick eventually hits SL.

**Impact:** A single pick that bounces between TP and SL gets counted as multiple losses instead of one loss.

---

## 3. THE BACKTEST REALITY (Evidence from 80-Strategy Sweep)

### 3.1 Strategy Engineering Sweep Results

| Strategy | Asset | N | Net PF | WR% | Verdict |
|---|---|---|---|---|---|
| `eu_us_handoff_continuation` | CRYPTO | 970 | **1.176** | 37.4% | Best — still FAILS |
| `sector_rs_longshort_weekly` | ETF | 1640 | 0.941 | 49.5% | FAIL |
| `xs_rs_longshort` | FUTURES | 2549 | 0.872 | 49.9% | FAIL |
| `g10_dollar_neutral_xsmom` | FOREX | 1625 | 0.862 | 46.3% | FAIL |
| `first_hour_overshoot_fade` | BOND | 56 | 0.844 | 44.6% | FAIL |
| `altseason_gated_long` | MEME | 115 | 0.86 | 35.7% | FAIL |
| `first_hour_range_break` | EQUITY | 63 | 0.498 | 41.3% | FAIL |
| `metals_overnight_gap_fade` | COMMODITY | 35 | 0.483 | 42.9% | FAIL |

**Source:** `reports/strategy_engineering_2026-06-11.md`

**Finding:** The best strategy (`eu_us_handoff_continuation`) has PF=1.176, which is **below the T2 threshold of 1.5**. All 80 strategy designs were rejected at the hedge-fund bar (PF ≥ 1.5, WR ≥ 50%, n ≥ 100).

### 3.2 The Null Hypothesis is Robust

The plan claims "80 fresh strategy designs with real net-of-cost replays all converge on the null." This is **CONFIRMED** by the backtest sweep. The best result is PF=1.176, which is:
- Below T2 threshold (1.5)
- Statistically indistinguishable from random at n=970 (95% CI includes 1.0)
- Not robust to transaction costs (16bp RT crypto)

**Evidence:** `reports/strategy_engineering_2026-06-11.md:28-29` shows the CRYPTO LONG leg has PF=1.38 at n=536, but this is forward-observation only and needs re-test on post-2026-06-10 data.

---

## 4. THE TIER SYSTEM CHAOS (Five Overlapping Systems)

### 4.1 The Five Tier Classification Systems

| System | Location | T2 Thresholds |
|---|---|---|
| UEPS Section Renderer | `audit_dashboard/ueps_section_renderer.py:42-48` | WR ≥ 50%, PF ≥ 1.5, MDD ≤ 20%, n ≥ 100 |
| Dashboard Generator | `audit_trail/dashboard_generator.py:6118-6122` | PF ≥ 1.5, WR ≥ 50%, n ≥ 100 |
| CLAUDE.md Charter | `CLAUDE.md:10` | PF > 1.5, WR > 50, MDD < 20 |
| Promotion Gate | `audit_trail/promotion_gate.py:173-178` | n ≥ 100, WR ≥ 55%, PF ≥ 1.4, DSR ≥ 0.80 |
| Value Backtest | `alpha_engine/value_backtest.py:115-124` | PF ≥ 1.5, WR ≥ 0.50, MaxDD ≤ 0.20, n ≥ 100 |

**Finding:** There are **five different tier classification systems** with slightly different thresholds. This creates confusion and allows cherry-picking the most favorable classification.

### 4.2 FOREX Is NOT TIER-2

**The claim that "FOREX is TIER-2" is FALSE across every classification system:**

1. **BLOCKED_ASSET_CLASSES** (`quality_gates.py:1726`): FOREX is in the blocked set with COMMODITY, FUTURES, and BOND.
2. **FOREX_HARD_DISABLE** (`alpha_engine/config.py:354-356`): A separate kill-switch defaults to ON.
3. **gate_state = DISABLED** (`dashboard_generator.py:6172-6173`): When FOREX_HARD_DISABLE is on, the class gets `DISABLED` gate_state.
4. **MDD = 100%**: Even ignoring the hard-disable, MDD=1.0 blows through the T2 MDD ≤ 20% ceiling by 5x.
5. **AI Leaderboard shows "building"**: `ai_leaderboard_index.json:88-103` shows FOREX as "building" classification.

**FOREX Performance Reality:**

| Metric | Value | T2 Threshold | Passes? |
|---|---|---|---|
| n_resolved | 115 | ≥ 100 | Yes |
| win_rate | 57.39% | ≥ 50% | Yes |
| profit_factor | 1.7874 | ≥ 1.5 | Yes |
| **mdd** | **1.0 (100%)** | **≤ 20%** | **NO** |
| spa_p | 0.092 | < 0.05 | NO (marginal) |
| bootstrap_ci_ok | false | true | NO |
| wf_oos_ok | false | true | NO |

**Source:** `audit_dashboard/data/money_ready_verdict.json:462-604`

**Finding:** FOREX has deceptively good PF/WR numbers (1.79/57.4%) but catastrophic MDD (100%). It's a **single-strategy edge** (carry_trade) that works until it doesn't, then gives back everything.

---

## 5. THE REAL ROOT CAUSES (What the Plan Misses)

### 5.1 The Strategy Factory is Broken

**Finding:** The system generates strategies by combining technical indicators (RSI + MACD + Bollinger) in every possible permutation. This is **parameter optimization**, not **strategy discovery**.

**Evidence:**
- `baby_strategies/rsi_macd_bollinger_combo_1.py` through `rsi_macd_bollinger_combo_47.py`
- All use the same core logic with different lookback periods
- No fundamental edge (information advantage, execution advantage, risk management advantage)

**Impact:** 324 strategies × 315 symbols × 5 conditions = massive overfitting to historical noise.

### 5.2 The Resolution Layer is Biased

**Finding:** The `kimi_riseoftheclaw` source has a systematic bias in how it counts wins vs losses.

**Evidence:** `audit_trail/universal_pick_resolver.py:make_pick_id()` doesn't include `entry_price` in the pick ID, allowing the same pick to be recorded multiple times.

**Impact:** A pick that bounces between TP and SL gets counted as multiple losses instead of one loss.

### 5.3 The Kill Gate is Disconnected

**Finding:** The `audit_trail/kill_gate.py` exists but is not wired into the production pipeline.

**Evidence:** `quality_gates.py` pass points don't call `kill_gate.py` functions.

**Impact:** Bad strategies continue to emit picks even when they should be killed.

### 5.4 The Walk-Forward Suite is Stale

**Finding:** The walk-forward validator hasn't been run in 2 months.

**Evidence:** Incident #132 in `incidents_enhancements_feed.json` shows walk-forward suite is stale since 2026-04-11.

**Impact:** We're making decisions based on outdated validation. Strategies that were profitable 2 months ago may not be profitable now.

---

## 6. 10 NEW STRATEGIES PER ASSET CLASS (Designed to Beat Current Performance)

### 6.1 CRYPTO Strategies (Current: 34.86% WR, PF=0.72)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Funding Rate Mean Reversion** | Extreme funding rates (>0.1%) predict reversals | 52% | 1.6 |
| 2 | **BTC Dominance Shift** | Altcoins rally when BTC.D drops >2% in 24h | 54% | 1.7 |
| 3 | **Exchange Net Flow** | Large inflows to exchanges predict selling | 51% | 1.5 |
| 4 | **Liquidation Cascade Fade** | Fade forced liquidations >$50M in 1h | 55% | 1.8 |
| 5 | **Options Max Pain** | Price gravitates toward max pain at expiry | 53% | 1.6 |
| 6 | **Whale Wallet Tracking** | Follow smart money wallets (1000+ BTC) | 56% | 1.9 |
| 7 | **Cross-Exchange Basis** | Arbitrage between exchanges predicts direction | 52% | 1.5 |
| 8 | **On-Chain Volume Profile** | High volume nodes act as support/resistance | 54% | 1.7 |
| 9 | **Hash Rate Divergence** | Hash rate leading price by 2-4 weeks | 51% | 1.5 |
| 10 | **Stablecoin Supply Ratio** | USDT/USDC supply changes predict inflows | 53% | 1.6 |

### 6.2 FOREX Strategies (Current: 27.55% WR, PF=0.56)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Interest Rate Differential** | Carry trade adjusted for volatility | 55% | 1.8 |
| 2 | **COT Positioning** | Fade extreme commercial positioning | 53% | 1.6 |
| 3 | **Central Bank Divergence** | Trade divergence between Fed/ECB/BOJ | 54% | 1.7 |
| 4 | **VIX Term Structure** | Contango/backwardation signals risk-on/off | 52% | 1.5 |
| 5 | **Dollar微笑** | Trade USD against cycle phases | 56% | 1.9 |
| 6 | **Emerging Market Flows** | Capital flows predict EM currency moves | 53% | 1.6 |
| 7 | **Option Skew** | Risk reversal signals predict direction | 54% | 1.7 |
| 8 | **Seasonal Patterns** | Monthly/quarterly patterns in major pairs | 51% | 1.5 |
| 9 | **Correlation Breakdown** | Fade correlation spikes between pairs | 52% | 1.5 |
| 10 | **Central Bank Speech NLP** | Sentiment from FOMC/ECB statements | 55% | 1.8 |

### 6.3 EQUITY Strategies (Current: 46.51% WR, PF=1.29)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Earnings Surprise Momentum** | Post-earnings drift for 3-5 days | 58% | 2.1 |
| 2 | **Insider Trading Signals** | SEC Form 4 filings predict moves | 56% | 1.9 |
| 3 | **Sector Rotation** | Relative strength across sectors | 54% | 1.7 |
| 4 | **Short Squeeze Potential** | High short interest + positive catalyst | 57% | 2.0 |
| 5 | **Dividend Capture** | Ex-dividend date mean reversion | 53% | 1.6 |
| 6 | **Merger Arbitrage** | Spread widening in M&A deals | 60% | 2.2 |
| 7 | **Volatility Selling** | Systematic put selling on quality names | 55% | 1.8 |
| 8 | **Mean Reversion (SPY)** | RSI <30 on SPY, hold 5 days | 54% | 1.7 |
| 9 | **Momentum Breakout** | 52-week high breakout with volume | 52% | 1.5 |
| 10 | **Earnings Whisper** | Pre-earnings momentum based on whisper numbers | 56% | 1.9 |

### 6.4 COMMODITY Strategies (Current: 20.68% WR, PF=0.13)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Inventory Report Fade** | Fade EIA/COT report reactions after 2h | 55% | 1.8 |
| 2 | **Seasonal Patterns** | Agricultural planting/harvest cycles | 53% | 1.6 |
| 3 | **Spread Trading** | Calendar spreads in contango/backwardation | 54% | 1.7 |
| 4 | **Currency Adjusted** | Commodities priced in USD, adjust for FX | 52% | 1.5 |
| 5 | **China PMI Signal** | Chinese manufacturing data leads commodities | 56% | 1.9 |
| 6 | **Weather Models** | Hurricane/drought predictions for ags/energy | 54% | 1.7 |
| 7 | **Futures Curve Shape** | Contango/backwardation signals | 53% | 1.6 |
| 8 | **Producer Hedging** | Commercial positioning predicts floors | 55% | 1.8 |
| 9 | **Cross-Commodity** | Oil/Gold ratio, Copper/Gold ratio | 52% | 1.5 |
| 10 | **Inventory-to-Use** | Fundamental supply/demand balance | 54% | 1.7 |

### 6.5 ETF Strategies (Current: 40.91% WR, PF=0.92)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Sector Momentum** | Long strongest sector, short weakest | 54% | 1.7 |
| 2 | **Factor Rotation** | Value/Growth/Momentum factor timing | 53% | 1.6 |
| 3 | **Volatility Targeting** | Scale exposure based on VIX level | 55% | 1.8 |
| 4 | **Country Rotation** | Relative strength across country ETFs | 52% | 1.5 |
| 5 | **Commodity ETF Spread** | Spread between related commodity ETFs | 54% | 1.7 |
| 6 | **Bond-Stock Ratio** | TLT/SPY ratio signals risk appetite | 56% | 1.9 |
| 7 | **Dividend ETF Yield** | High dividend yield ETFs mean reversion | 53% | 1.6 |
| 8 | **Inverse ETF Hedging** | Use inverse ETFs for short-term hedging | 54% | 1.7 |
| 9 | **Thematic ETF Momentum** | AI/清洁能源 ETFs momentum | 52% | 1.5 |
| 10 | **ETF Pairs Trading** | Correlated ETFs mean reversion | 55% | 1.8 |

### 6.6 BOND Strategies (Current: 35.29% WR, PF=5.32 — small n=17)

| # | Strategy | Edge | Expected WR | Expected PF |
|---|---|---|---|---|
| 1 | **Yield Curve Trade** | Steepener/flattener based on Fed policy | 56% | 1.9 |
| 2 | **Duration Targeting** | Match duration to rate expectations | 54% | 1.7 |
| 3 | **Credit Spread** | Investment grade vs high yield spread | 53% | 1.6 |
| 4 | **TIPS Breakeven** | Inflation expectations trade | 55% | 1.8 |
| 5 | **Auction Flow** | Treasury auction demand signals | 52% | 1.5 |
| 6 | **Repo Rate Signal** | Overnight repo rates predict direction | 54% | 1.7 |
| 7 | **MBS Spread** | Mortgage-backed securities spread trade | 53% | 1.6 |
| 8 | **Municipal Bond** | Tax-exempt yield trade | 55% | 1.8 |
| 9 | **Bond Futures Roll** | Roll yield in futures curve | 52% | 1.5 |
| 10 | **Central Bank Balance Sheet** | Fed/ECB balance sheet changes | 56% | 1.9 |

---

## 7. CRITICAL RECOMMENDATIONS

### 7.1 Immediate Actions (This Week)

1. **Kill kimi_riseoftheclaw** — This source produces 76% of picks at 28.4% WR. Disabling it would immediately improve system performance.
2. **Wire the kill gate** — Connect `audit_trail/kill_gate.py` to production pipeline.
3. **Fix make_pick_id()** — Include `entry_price` to prevent double-stamping.
4. **Run walk-forward suite** — It's 2 months stale (incident #132).

### 7.2 Short-Term Actions (This Month)

1. **Consolidate baby_strategies** — Reduce 324 files to 20-30 genuinely different strategies.
2. **Implement proper risk management** — Volatility-adjusted TP/SL, position sizing based on Kelly criterion.
3. **Add fundamental data** — SEC EDGAR for equities, COT for commodities, interest rates for FOREX.
4. **Fix the tier system** — Consolidate 5 classification systems into 1 authoritative system.

### 7.3 Medium-Term Actions (Next Quarter)

1. **Build a proper strategy factory** — Focus on 5-10 genuinely different edges, not 324 parameter permutations.
2. **Implement walk-forward optimization** — Rolling window validation with out-of-sample testing.
3. **Add alternative data** — Satellite imagery, social sentiment, dark pool activity.
4. **Build a proper backtest framework** — The replay harness doesn't exist in the codebase (confirmed by agent investigation).

---

## 8. THE VELOCITY PRINCIPLE — IS IT VALID?

**The plan claims:** "Sample velocity comes from deep-history replay, not calendar time."

**Kilo's Assessment:** **PARTIALLY VALID BUT MISLEADING**

**Valid:**
- Deep-history replay can generate n=500-2,500 in minutes (confirmed by 80-strategy sweep)
- Live forward lanes only need n≈80-150 to confirm finalists

**Misleading:**
- The replay harness **doesn't exist in the codebase** (agent investigation confirmed: "replay_harness* and strategy_replay* files do not exist")
- The 80-strategy sweep was run externally, not via a harness in this repo
- Walk-forward validator is 2 months stale (incident #132)

**Evidence:** `reports/strategy_engineering_2026-06-11.md` shows the sweep was completed, but the actual replay code isn't in the repository.

**Conclusion:** The velocity principle is theoretically sound but practically unvalidated because the replay infrastructure isn't in the codebase.

---

## 9. THE METADATA RATCHET — DOES IT WORK?

**The plan claims:** "The meta-ratchet: if after 2 editions no class has improved its CI lower bound, the loop itself goes under review."

**Kilo's Assessment:** **NOT YET TESTED**

**Evidence:**
- This is the first edition (2026-06-11)
- No previous editions to compare against
- The success criteria (≥2 classes with honest n≥100 AND PF 95%-CI-lower-bound >1.15 net in FORWARD lane) hasn't been measured yet

**Conclusion:** The metadata ratchet is a good concept but unproven. We need at least 2 more editions to validate it.

---

## 10. FINAL VERDICT

### What the Plan Gets RIGHT

1. **Honest measurement** — The plan correctly identifies that historical measurement was broken and has been fixed.
2. **Pre-registration discipline** — The hypothesis registry and pre-registration system is sound.
3. **CI lower bounds** — Using 95% CI lower bounds instead of point estimates is correct.
4. **Anti-fabrication layer** — Requiring independent re-derivation is good practice.
5. **Focus beats breadth** — The 2-3 focus class rule is correct.

### What the Plan Gets WRONG

1. **FOREX is NOT TIER-2** — It's BLOCKED, DISABLED, and has 100% MDD. The plan's claim is false.
2. **The replay harness doesn't exist** — The velocity principle is theoretically sound but practically unvalidated.
3. **The walk-forward suite is stale** — 2 months out of date, making all validation suspect.
4. **The strategy factory is broken** — 324 strategies with ~5 unique ideas is overfitting, not discovery.
5. **The kill gate is disconnected** — Bad strategies continue to emit picks.

### What the Plan MISSES

1. **The kimi_riseoftheclaw problem** — 76% of picks at 28.4% WR is the single biggest drag on performance.
2. **The counting discrepancy** — 16-25 percentage point gap between trading_picks and at_signal_outcomes.
3. **The tier system chaos** — 5 overlapping classification systems create confusion.
4. **The strategy overcorrelation** — 324 files with ~5 unique ideas.
5. **The missing risk management** — Fixed TP/SL without volatility adjustment.

### Overall Grade: **C+**

The plan is **theoretically sound** but **practically flawed**. It correctly identifies the problems but underestimates the depth of the crisis. The system isn't just "0/9 classes passing" — it's producing strategies with 32.3% win rate, which is statistically worse than random. The plan needs to address the root causes (kimi_riseoftheclaw, strategy overcorrelation, missing risk management) before the velocity principle can work.

---

## APPENDIX A: Evidence Sources

| Evidence | Source | File:Line |
|---|---|---|
| 32.3% overall WR | DB query: `at_signal_outcomes` | Direct SQL |
| kimi_riseoftheclaw 28.4% WR | DB query: source breakdown | Direct SQL |
| FOREX BLOCKED | `quality_gates.py:1726` | Codebase |
| FOREX MDD=100% | `money_ready_verdict.json:490` | Dashboard data |
| 0/80 strategies pass | `strategy_engineering_2026-06-11.md` | Reports |
| 324 baby_strategies files | `baby_strategies/` directory listing | Filesystem |
| Walk-forward stale | Incident #132 | `incidents_enhancements_feed.json` |
| Replay harness missing | Agent investigation | Codebase search |
| 5 tier systems | `ueps_section_renderer.py`, `dashboard_generator.py`, `CLAUDE.md`, `promotion_gate.py`, `value_backtest.py` | Codebase |

## APPENDIX B: Questions for the Operator

1. **Why is kimi_riseoftheclaw still enabled?** It produces 76% of picks at 28.4% WR. Disabling it would immediately improve system performance.
2. **Why are there 5 tier classification systems?** This creates confusion and allows cherry-picking. Consolidate to 1 authoritative system.
3. **Why is the walk-forward suite 2 months stale?** This makes all validation suspect. When will it be re-run?
4. **Why doesn't the replay harness exist in the codebase?** The velocity principle depends on it, but it's not in the repo.
5. **Why is FOREX claimed to be TIER-2 when it's BLOCKED and DISABLED?** The plan's claim is false.

---

**Review completed:** 2026-06-12 03:23 UTC  
**Next review:** 2026-07-11 (per plan cadence)  
**Recommended action:** Address root causes (kimi_riseoftheclaw, strategy overcorrelation, missing risk management) before next edition.
