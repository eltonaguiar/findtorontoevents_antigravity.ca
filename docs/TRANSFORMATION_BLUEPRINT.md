# Alpha Engine Transformation Blueprint

**Date:** 2026-03-24
**Status:** DRAFT -- All numbers sourced from verified audit data
**Baseline period:** March 2026 only (1 month of paper trading)

---

## Reality Check: Where We Actually Are

| Metric | Current Value | Honest Assessment |
|--------|--------------|-------------------|
| Win Rate | 32.6% on 1,965 closed trades | Losing on 2 out of 3 trades |
| Profit Factor | 1.09 | Barely above breakeven; fees would destroy this live |
| Sharpe (ann.) | 0.59 | Below minimum institutional threshold (1.0) |
| Sortino (ann.) | 1.42 | Inflated by FET outlier skewing upside |
| Max Drawdown | 625.7% cumulative | Catastrophic; portfolio would have been wiped multiple times |
| Expectancy | +0.094% per trade | Requires 1000+ trades/month to compound meaningfully |
| VaR (95%) | -3.20% | On any given trade, 5% chance of losing 3.2%+ |
| CVaR (95%) | -5.25% | When it's bad, average loss is 5.25% |
| FET concentration | 237% of total PnL | System is NOT profitable; one lucky trade masks everything |
| Return without FET | Deeply negative | The actual system edge is negative |
| ML model | Broken (AUC=1.0) | Overfitting so severe it memorized the training set |
| Smart Picks | 0% WR (1 batch) | The "smart" selection layer adds no value |
| Live trading | ZERO | No real-money validation of any claim |
| Data history | 1 month | Statistically insufficient for most conclusions |

**Bottom line:** Strip out FET, and this system loses money. The 32.6% WR with 1.09 PF means the average winner is roughly 2x the average loser, but that ratio is entirely carried by tail events. This is not a trading system yet. It is a research platform that found one promising signal source (copy traders) buried under 1000+ noise strategies.

---

## What Actually Has Edge (Verified)

| Signal Source | Win Rate | Sample Size | Confidence |
|--------------|----------|-------------|------------|
| Copy trader direct (copy_hl_*) | 52.2% | 23 active | Low (n < 30) |
| Top 5 traders + score >= 70 | 75.4% | 69 closed | Moderate (n > 30, but 1 month) |
| Confidence 0.75-0.80 bucket | 79.2% | 125 trades | Moderate |
| Late NY session (21-24 UTC) | 50.9% | Unknown | Low (session effect, not causal) |
| Scoring IC after zeroing | Spearman 0.616 | Full dataset | High (significant improvement from 0.003) |

**Only 4 of 21 scoring components predict winners:** regime_bonus, track_record, forward_wr, technical_alignment. The other 17 are noise or anti-predictive.

---

## Phase 1: Stop the Bleeding (Days 1-3)

**Goal:** Reduce loss rate from 67.4% to < 60% by cutting the worst sources of negative expectancy.

### 1.1 Raise minimum score threshold from 50 to 70

The A/B test data proves score >= 70 delivers 75.4% WR vs 32.6% system-wide. This is the single highest-impact change.

**Files to modify:**
- `alpha_engine/confluence_pipeline.py` line 27: change `min_score=50.0` to `min_score=70.0`
- `alpha_engine/confluence_pipeline.py` line 792: change `min_score=40.0` to `min_score=70.0`
- `alpha_engine/ab_test_portfolios.py` line 330 (Portfolio F): change `"min_score": 50` to `"min_score": 70`
- `alpha_engine/config.py`: add `MIN_ELITE_SCORE = 70` as a centralized constant

**Expected impact:** Cuts ~60% of picks, but the eliminated picks have < 25% WR. Net effect: fewer trades, much higher WR. Confidence: HIGH (based on 69 closed picks at this threshold).

**Success criteria:** WR on new picks >= 50% over next 100 picks
**Abort criteria:** If WR drops below 40% on 50+ picks at score >= 70, the scoring model is broken and needs full rebuild

### 1.2 Cap FET/single-symbol concentration at 20% of portfolio PnL

237% concentration in one symbol means the portfolio is a single-asset bet dressed up as a system.

**Files to modify:**
- `alpha_engine/config.py`: add `MAX_SYMBOL_PNL_CONCENTRATION = 0.20` (20% max of total PnL from any one symbol)
- `alpha_engine/config.py` line 67: change `MAX_PICKS_PER_SYMBOL = 2` to `MAX_PICKS_PER_SYMBOL = 1`
- `alpha_engine/production_scanner.py`: add concentration check before accepting new picks -- if symbol already has > 20% of open PnL, block new entries

**Expected impact:** Forces diversification. Will reduce headline return but creates a real portfolio instead of a single-bet illusion. Confidence: HIGH (mechanical, not model-dependent).

**Success criteria:** No single symbol exceeds 25% of total PnL over a rolling 7-day window
**Abort criteria:** N/A -- this is a risk management rule, not a performance optimization

### 1.3 Reduce MAX_ACTIVE_PICKS from 10 to 5

With 32.6% WR, more picks = more losers. Concentrate capital on highest-conviction signals only until WR improves.

**Files to modify:**
- `alpha_engine/production_scanner.py` line 214: change `MAX_ACTIVE_PICKS = 10` to `MAX_ACTIVE_PICKS = 5`
- `alpha_engine/config.py` line 65: change `MAX_OPEN_PICKS = 20` to `MAX_OPEN_PICKS = 5`

**Expected impact:** Combined with score >= 70 filter, this ensures only top-tier signals get through. Reduces noise exposure by 50%. Confidence: MODERATE (trade-off between selectivity and sample size).

**Success criteria:** Average pick score > 75 across first 50 picks
**Abort criteria:** If system generates < 2 picks per week, loosen to MAX_ACTIVE_PICKS = 8

### 1.4 Tighten crypto stop loss from -8% to -5%

Current crypto SL of -8% (`config.py` line 95) is too wide. At 32.6% WR, the average loser needs to be much smaller than the average winner. VaR of -3.20% suggests most losses cluster around 3%.

**Files to modify:**
- `alpha_engine/config.py` line 95: change `(-0.08, 0.15, 7)` to `(-0.05, 0.10, 5)` for crypto
- `alpha_engine/config.py` line 96: change `(-0.15, 0.35, 3)` to `(-0.08, 0.20, 3)` for meme

**Expected impact:** Cuts average loss size by ~35%. Will increase the number of stop-outs (lowering WR by 2-3pp) but dramatically improves PF. Confidence: MODERATE (requires CVaR to validate new SL placement).

**Success criteria:** Average loss < 4% over next 200 closed trades
**Abort criteria:** If PF drops below 1.0 (tighter stops creating more losers without improving expectancy), revert to -6% SL

### 1.5 Disable all strategies not sourced from copy traders

The data is unambiguous: copy trader picks at 52.2% WR vs system-generated at ~28%. Until internal strategies prove themselves in forward test, they should not contribute to the main portfolio.

**Files to modify:**
- `alpha_engine/production_scanner.py`: add source filter -- only accept picks where `source` contains "copy" or `strategy` starts with "copy_hl"
- Keep internal strategies running in shadow mode (A/B test portfolios G and H) for continued data collection

**Expected impact:** Eliminates the ~70% of picks that come from unproven internal strategies. Confidence: HIGH (copy trader superiority is verified across multiple metrics).

**Success criteria:** All active picks sourced from copy traders for 14 days
**Abort criteria:** If copy trader pick flow drops below 3 picks per week, selectively re-enable top-3 internal strategies by forward WR

### Phase 1 Combined Targets

| Metric | Current | Phase 1 Target | Basis |
|--------|---------|----------------|-------|
| Win Rate | 32.6% | > 45% | Score >= 70 bucket shows 75.4% WR; being conservative |
| Profit Factor | 1.09 | > 1.3 | Tighter stops + higher WR = better R:R |
| Max Active Picks | 10-20 | 5 | Concentration on highest conviction |
| FET Concentration | 237% | < 25% | Mechanical cap |

---

## Phase 2: Prove the Edge (Days 4-14)

**Goal:** Build statistically meaningful forward-test evidence that the copy-trader-centric system has a real edge.

### 2.1 Run dedicated A/B test: Copy Trader Golden Filter vs Control

The existing A/B framework (8 portfolios A-H) already tests this. Focus ALL attention on Portfolio A ("Golden Filter": top 5 traders, score >= 70, MTF gate, 3%/2% TP/SL).

**Files to modify:**
- `alpha_engine/ab_test_portfolios.py`: no code changes needed; the framework exists
- `.github/workflows/alpha-engine-live.yml`: ensure ab_test_portfolios.py runs every cycle

**Minimum sample sizes for statistical significance:**
- To distinguish 50% WR from 40% WR with 80% power and alpha=0.05: **n = 199 per group** (chi-squared test)
- To distinguish PF 1.3 from PF 1.0 at same power: **n = ~150 per group** (bootstrap)
- At current generation rate (~60 picks/week for golden filter): **3-4 weeks minimum**
- **Do not draw conclusions before 100 picks per portfolio.** Anything less is noise.

**Success criteria:** Portfolio A WR > 55% on 100+ closed picks with PF > 1.3
**Abort criteria:** If Portfolio A WR < 40% at 100 picks, the copy trader edge claim is falsified

### 2.2 Validate the 4 predictive scoring components in isolation

The IC analysis identified regime_bonus, track_record, forward_wr, and technical_alignment as the only predictive components. Build a stripped-down scorer using ONLY these 4.

**Files to modify:**
- `alpha_engine/elite_scorer.py`: create function `compute_minimal_score()` using only the 4 validated components
  - regime_bonus: 0-20 pts (IC = +0.19)
  - forward_wr + track_record: 0-40 pts (IC = +0.17)
  - technical_alignment: -30 to +5 pts (IC = +0.16)
  - Total range: -30 to 65 pts, normalize to 0-100
- Run this in parallel with current scorer in A/B Portfolio clone

**Expected impact:** Cleaner signal. The current 21-component scorer dilutes the 4 real signals with 17 noise/anti-predictive components. Even with zeroing, interaction effects may persist. Confidence: MODERATE (IC analysis is solid but IC != causation).

**Success criteria:** Minimal scorer Spearman correlation with PnL > 0.5 on 200+ picks
**Abort criteria:** If correlation < 0.3, the IC analysis may have been overfit to the specific month

### 2.3 Fix the ML model

AUC = 1.0 means the model memorized the training data. This is a data leakage or insufficient hold-out problem.

**Files to modify:**
- `alpha_engine/data/meta_learner_model.json`: delete and retrain from scratch
- Whatever file trains the model (likely `alpha_engine/ensemble/meta_learner.py` or `alpha_engine/pattern_predictor.py`):
  - Implement proper time-series cross-validation (no future data leakage)
  - Use walk-forward validation with minimum 200-pick test windows
  - Target features: only the 4 IC-validated components + entry hour + symbol category
  - Regularize aggressively: max_depth=3, min_samples_leaf=50, max_features=0.5

**Expected impact:** A properly trained model should achieve AUC of 0.55-0.65 on out-of-sample data (not 1.0, not 0.5). This is realistic for financial ML. Confidence: MODERATE (depends on available training data size, which is currently only 1,965 trades from 1 month).

**Success criteria:** Out-of-sample AUC between 0.55 and 0.70 on walk-forward test
**Abort criteria:** If OOS AUC < 0.52 after proper CV, the feature set is insufficient -- revert to rule-based scoring only

### 2.4 Time-of-day filter: restrict entries to 21-24 UTC

Late NY session shows 50.9% WR vs system average of 32.6%. This is an 18pp improvement worth testing.

**Files to modify:**
- `alpha_engine/production_scanner.py`: add entry time gate -- only accept picks generated during 21:00-23:59 UTC
- Alternative: add time_bonus to `alpha_engine/elite_scorer.py` for 21-24 UTC entries (+10 pts)

**Expected impact:** Reduces pick volume by ~75% (only 3 hours of 24). Combined with copy trader filter, may generate only 1-2 picks per day. Confidence: LOW (time-of-day effects are notoriously unstable and may be coincidental in 1-month sample).

**Success criteria:** WR during 21-24 UTC > 48% on 50+ picks
**Abort criteria:** If WR during this window is < 42% on 50+ picks, the session effect is spurious -- remove the filter

### 2.5 Confidence bucket optimization

The 0.75-0.80 confidence bucket shows 79.2% WR on 125 trades. This is the strongest single signal in the dataset.

**Files to modify:**
- `alpha_engine/production_scanner.py`: add confidence floor of 0.72 for all picks
- `alpha_engine/elite_scorer.py`: weight confidence bucket 0.75-0.80 with a bonus (but note: confidence itself was ZEROED as anti-predictive at IC level, so this bucket effect may be an artifact)

**Expected impact:** If the 0.75-0.80 bucket effect is real, this alone could lift WR to > 60%. But confidence was zeroed in IC analysis (IC = -0.14), meaning across all buckets, higher confidence predicts WORSE outcomes. The 0.75-0.80 sweet spot may be a statistical fluke in 125 trades. Confidence: LOW.

**Success criteria:** Picks in 0.72-0.82 confidence range maintain > 60% WR on 100+ new picks
**Abort criteria:** If WR in this bucket drops below 50% on 75+ picks, the effect is not real

### Phase 2 Combined Targets

| Metric | Phase 1 Target | Phase 2 Target | Basis |
|--------|----------------|----------------|-------|
| Win Rate | > 45% | > 50% | Copy trader + golden filter proven |
| Profit Factor | > 1.3 | > 1.5 | Better picks + tighter risk |
| Sharpe (ann.) | Not measured | > 0.8 | Need 14 days of daily returns |
| OOS AUC | Broken (1.0) | 0.55-0.65 | Properly cross-validated ML |
| Score-PnL Spearman | 0.616 | > 0.5 sustained | Forward validation of IC fix |

---

## Phase 3: Scale What Works (Days 15-30)

**Goal:** Expand proven strategies and prepare for live trading.

### 3.1 Expand copy trader scraper coverage

Currently scraping 10+ exchanges. The constraint is not breadth but QUALITY filtering.

**Files to modify:**
- `copy_trader_intel/consensus_pick_builder.py`: raise minimum trader WR threshold from current to 60%
- `copy_trader_intel/trusted_trader_tracker.py`: implement trader-level scoring -- only copy from traders with > 55% WR on 30+ closed trades
- `copy_trader_intel/main.py`: add trader-level forward WR tracking (currently only pick-level)

**Expected impact:** More high-quality picks from the proven copy trader pipeline. Could increase pick volume by 2-3x while maintaining WR > 50%. Confidence: MODERATE (depends on scraper reliability and trader consistency).

**Success criteria:** Copy trader pick volume > 10/week with WR > 50% sustained
**Abort criteria:** If expanding coverage dilutes WR below 45%, tighten trader filters

### 3.2 Begin live trading with minimal capital

**Prerequisites (all must be met):**
- Phase 2 Portfolio A has 100+ closed picks with WR > 50% and PF > 1.3
- Score-PnL Spearman > 0.4 sustained for 14 days
- No single symbol > 25% of PnL
- Kill switch (`alpha_engine/kill_switch.py`) tested and functional

**Live trading parameters:**
- Starting capital: $500 (disposable amount)
- Position size: 2% of capital per trade ($10)
- Max open positions: 3
- Exchange: one of {Binance, Bybit} via API
- Only copy trader golden filter picks (Portfolio A config)
- Manual execution initially (review each pick before entering)

**Files to modify:**
- New file: `alpha_engine/live_executor.py` -- reads from `data/active_picks.json`, generates order instructions (NOT auto-execute)
- `alpha_engine/config.py`: add `LIVE_MODE = False` flag (default off)
- `alpha_engine/config.py`: add `LIVE_CAPITAL = 500.0`, `LIVE_MAX_RISK_PER_TRADE = 0.02`

**Expected impact:** Real market validation of paper trading results. Expect 5-15% WR degradation from paper to live (slippage, fills, psychology). If paper WR is 55%, expect live WR of 45-50%. Confidence: LOW (paper-to-live translation is the graveyard of trading systems).

**Success criteria:** Live WR > 42% on 30+ trades, live PF > 1.1
**Abort criteria:** If live WR < 35% on 20+ trades OR live drawdown exceeds 15% of $500 ($75), halt live trading and diagnose

### 3.3 Strategy tournament: let internal strategies compete for allocation

Instead of disabling all internal strategies, run them in paper mode and promote the top 3 to live allocation.

**Files to modify:**
- `alpha_engine/tournament_engine.py`: ensure it ranks strategies by forward WR (not backtest WR)
- `alpha_engine/strategy_priority.py`: implement automatic promotion/demotion based on rolling 50-trade WR
  - Promote to live allocation: forward WR > 50% on 50+ trades
  - Demote to shadow: forward WR < 40% on 50+ trades
  - Probation: 30-50 trades, no allocation

**Expected impact:** Identifies which of the 1000+ strategies actually work in forward test. Most will fail. If even 5-10 survive with WR > 50%, that expands the alpha source beyond copy traders. Confidence: LOW (1000+ strategies tested, 405 killed, and the system still shows 32.6% WR -- the surviving strategies may not be better, just less tested).

**Success criteria:** At least 3 internal strategies achieve WR > 48% on 50+ forward trades
**Abort criteria:** If zero strategies achieve WR > 45% after 30 days, the internal strategy approach is fundamentally broken -- pivot entirely to copy trader alpha

### Phase 3 Combined Targets

| Metric | Phase 2 Target | Phase 3 Target | Basis |
|--------|----------------|----------------|-------|
| Win Rate (paper) | > 50% | > 52% | Sustained, not momentary |
| Win Rate (live) | N/A | > 42% | Paper-to-live degradation |
| Profit Factor | > 1.5 | > 1.5 sustained | 30-day rolling |
| Sharpe (ann.) | > 0.8 | > 1.0 | Multi-week daily returns |
| Live trades | 0 | 30+ | Minimum for significance |
| Live capital at risk | $0 | $500 max | Disposable amount |

---

## Phase 4: Institutional Readiness (Days 31-90)

**Goal:** Build verifiable track record, but be honest about what "institutional" means at this scale.

**Hard prerequisite:** Phase 3 live trading must show WR > 42% and PF > 1.1 on 30+ trades. If it does not, Phase 4 does not begin. Instead, return to Phase 2 and re-validate.

### 4.1 Multi-month track record

**What is needed:**
- 90 consecutive days of tracked live performance
- Minimum 200 live trades closed
- Auditable trade log with entry time, exit time, entry price, exit price, fees, slippage
- Daily NAV calculation (net of fees)

**Files to modify:**
- `alpha_engine/data/`: new SQLite table for live trade log (entry_time, exit_time, symbol, direction, entry_price, exit_price, fees, pnl_usd, pnl_pct)
- `alpha_engine/production_scanner.py`: write live trade outcomes to this table
- New file: `alpha_engine/track_record_report.py` -- generates daily/weekly/monthly performance report

**Success criteria at Day 90:**

| Metric | Target | Realistic? |
|--------|--------|-----------|
| Win Rate | > 50% | MAYBE -- if copy trader alpha holds up |
| Profit Factor | > 1.5 | MAYBE -- requires consistent R:R |
| Sharpe (ann.) | > 1.0 | UNLIKELY in 90 days -- need 1.5+ for institutional |
| Max Drawdown | < 15% | Achievable with proper sizing |
| Total Return | > 10% | $50 on $500 -- modest but real |

**Abort criteria:** If at Day 60 the Sharpe is below 0.5 or total return is negative, the system does not have institutional-grade edge. Pivot to research mode.

### 4.2 Third-party verification

At $500 capital, no institutional investor will care. This phase is about building the PROCESS for eventual scaling.

**Options (ranked by credibility):**
1. **Exchange API trade history export** -- proves trades happened at claimed prices
2. **Broker statement** -- if using a regulated broker
3. **Third-party tracking service** -- MyFXBook, Collective2, or similar
4. **GitHub commit history** -- picks committed before resolution (already happening)

**Files to modify:**
- `alpha_engine/audit_sync.py`: add export function for standardized trade log (CSV/JSON)
- Document the verification process

### 4.3 Capacity analysis

At $500, capacity is not a constraint. But for planning:

**Copy trader picks:** Limited by scraper coverage and trader activity. Current rate ~15-30 picks/week. At $10/trade, weekly capital deployed = $150-300. This scales linearly to ~$10K before market impact matters (crypto majors).

**Internal strategies:** If any survive Phase 3 tournament, capacity depends on the asset and timeframe. Most crypto strategies on 4H+ timeframes can absorb $10K-50K before moving the market on mid-cap altcoins.

**Realistic scaling path:**
- Month 1-3: $500 (proving ground)
- Month 4-6: $2,000 (if Month 1-3 profitable)
- Month 7-12: $5,000-10,000 (if Month 4-6 profitable)
- Year 2: $25,000-50,000 (if Year 1 profitable)
- "Institutional" ($1M+): 2-3 years minimum of consistent returns

### Phase 4 Combined Targets

| Metric | Phase 3 Target | Phase 4 Target (Day 90) | Honest Probability |
|--------|----------------|------------------------|-------------------|
| Win Rate (live) | > 42% | > 50% | 30% -- most paper edges evaporate live |
| Profit Factor | > 1.5 | > 1.5 sustained | 25% -- need consistent R:R over 200+ trades |
| Sharpe (ann.) | > 1.0 | > 1.5 | 10% -- 90 days is too short and edge is unproven |
| Max Drawdown | N/A | < 15% | 50% -- achievable with discipline |
| Live trades closed | 30+ | 200+ | 60% -- depends on pick flow |
| Capital | $500 | $500-2000 | 70% -- scale only if profitable |

---

## Key Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| `alpha_engine/config.py` | Risk params, position sizing, universe | 1 |
| `alpha_engine/production_scanner.py` | Main scanner, pick caps, enrichment | 1, 2 |
| `alpha_engine/elite_scorer.py` | Scoring model (IC-calibrated) | 1, 2 |
| `alpha_engine/confluence_pipeline.py` | Min score threshold, pipeline filters | 1 |
| `alpha_engine/ab_test_portfolios.py` | A/B test framework (8 portfolios) | 2 |
| `alpha_engine/forward_validator.py` | Forward test engine, kill switch | 2, 3 |
| `alpha_engine/kill_switch.py` | Emergency halt conditions | 3 |
| `alpha_engine/tournament_engine.py` | Strategy ranking/promotion | 3 |
| `alpha_engine/strategy_priority.py` | Tier system (ELITE/PROVEN/EXPERIMENTAL) | 3 |
| `copy_trader_intel/main.py` | Copy trader scraping orchestrator | 3 |
| `copy_trader_intel/consensus_pick_builder.py` | Multi-source consensus picks | 3 |
| `copy_trader_intel/trusted_trader_tracker.py` | Trader-level quality tracking | 3 |
| `alpha_engine/ensemble/meta_learner.py` | ML model training | 2 |
| `alpha_engine/auto_dna_mutator.py` | Strategy mutation engine | 3 |
| `alpha_engine/crypto_risk_gates.py` | LOW_CONFIDENCE_STRATEGIES, gate checks | 1, 2 |

---

## What This Blueprint Does NOT Promise

1. **70%+ WR on the overall system.** The best verified bucket (score >= 70, top 5 traders) shows 75.4% WR, but that is on 69 picks in one month. Regression to the mean is virtually guaranteed. A realistic sustained target is 50-55%.

2. **"Institutional-grade" performance in 90 days.** Institutional investors require 2-3 years of audited track record with Sharpe > 1.5. At $500 capital and 1 month of data, we are at least 24 months away from that bar.

3. **That the copy trader edge will persist.** Copy trader alpha depends on (a) the traders continuing to be profitable, (b) the scrapers continuing to work, (c) the market regime remaining similar. Any of these can fail.

4. **That internal strategies will ever work.** 1,000+ strategies tested, 405 killed, system WR of 32.6%. The hypothesis that more strategies = more alpha has been empirically falsified. Quality > quantity.

5. **That ML will add value.** With 1,965 trades in 1 month, the dataset is too small and too short for robust ML. A properly regularized model will likely show AUC of 0.55-0.60 -- a modest improvement that may not survive regime change.

---

## Decision Framework: When to Pivot

| Condition | Action |
|-----------|--------|
| Phase 1 WR < 40% after 100 picks | Scoring model is broken. Rebuild from scratch using only copy trader data. |
| Phase 2 Portfolio A WR < 45% at 100 picks | Copy trader golden filter does not generalize. Test wider trader pool (Portfolio F). |
| Phase 2 OOS AUC < 0.52 | ML adds no value. Abandon ML, use pure rule-based scoring. |
| Phase 3 live WR < 35% on 20 trades | Paper-to-live gap is fatal. Diagnose execution issues before continuing. |
| Phase 3 live drawdown > 15% | Risk management failure. Halt, reduce size to $1/trade, diagnose. |
| Phase 4 Sharpe < 0.5 at Day 60 | System does not have institutional-grade edge. Continue as research project, not trading system. |
| Copy trader scrapers break for > 7 days | Primary alpha source offline. Pause live trading until restored. |

---

## Execution Priority (If You Can Only Do 3 Things)

1. **Raise min_score to 70** -- highest-impact, lowest-effort change. One line in `confluence_pipeline.py`.
2. **Restrict to copy trader picks only** -- eliminates 70% of losing trades. Filter in `production_scanner.py`.
3. **Cap MAX_PICKS_PER_SYMBOL to 1** -- prevents FET-style concentration. One line in `config.py`.

Everything else is optimization on top of these three changes.
