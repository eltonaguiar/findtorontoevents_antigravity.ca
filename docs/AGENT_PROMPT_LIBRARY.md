# Agent Prompt Library: findtorontoevents_antigravity.ca
## World-Class Prediction System — Strategic Improvement Plan

---

## SECTION 1: IMMEDIATE PRIORITY — MySQL Edge Extraction Prompt

### Prompt 1A: Database Edge Scanner (Run This First)

```
I need you to connect to and analyze two MySQL databases on mysql.50webs.com:
- Database 1: ejaguiar1_stocks — contains historical stock/asset data
- Database 2: ejaguiar1_backtests — contains backtest results and strategy performance

Your mission: Extract statistical edge per asset class with extreme rigor.

STEP 1: Schema Discovery
- List ALL tables in both databases
- Show column names, types, and row counts for each table
- Identify which tables contain: trades/picks, strategies, asset classes, performance metrics
- Identify primary keys and relationships between tables

STEP 2: Data Quality Audit
- Count total picks/trades per asset class (CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND)
- Count wins/losses/flat per asset class
- Identify NULL values, duplicate entries, ghost rows
- Check date ranges per asset class (earliest pick, latest pick)
- Flag any data integrity issues

STEP 3: Statistical Edge Calculation (Per Asset Class)
For each asset class with n >= 30 trades, calculate:
- Win Rate = wins / (wins + losses)
- Profit Factor = (sum of winning trade profits) / abs(sum of losing trade losses)
- Average Win = mean of all winning trades
- Average Loss = mean of all losing trades
- W/L Ratio = Average Win / abs(Average Loss)
- Expectancy = (Win% * Avg Win) - (Loss% * abs(Avg Loss))
- Sharpe Ratio (per-trade): mean(pnl) / std(pnl)
- Max Drawdown: maximum peak-to-trough decline
- Median Trade: median of all trade PnLs
- Skewness of trade returns

STEP 4: Per-Strategy Breakdown
- Group by strategy_name/system
- Calculate PF, WR, n for each strategy within each asset class
- Rank strategies by PF within each class
- Identify strategies with n >= 30 AND PF > 1.5 (potential winners)
- Identify strategies with n >= 30 AND PF < 1.0 (candidates for inversion)

STEP 5: Confidence Interval Analysis
For each asset class and top strategy:
- Calculate 95% confidence interval for Win Rate
- Calculate 95% confidence interval for Profit Factor
- Use bootstrapping (1000 resamples) if parametric methods are uncertain
- Report: "We can be 95% confident the true PF is in range [X, Y]"

STEP 6: Time Decay Analysis
- Calculate rolling 7-day PF and WR per asset class
- Calculate rolling 30-day PF and WR per asset class
- Flag any asset class where 30d PF < 1.0 but all-time PF > 1.0 (decay warning)
- Flag any asset class where 30d PF > all-time PF (improving trend)

STEP 7: The "Invert Losers" Analysis
For strategies with WR between 35-45% (consistently wrong):
- Calculate what PF/WR would be if EVERY signal were inverted (BUY→SELL, SELL→BUY)
- If inverted PF > 1.5 AND inverted WR > 50%, flag as "INVERSION CANDIDATE"
- These are contrarian goldmines — the strategy is reliably wrong

STEP 8: Output Format
Generate two files:
1. edge_report_mysql.md — Full markdown report with all tables
2. edge_per_class.json — Machine-readable JSON for downstream use

Format for edge_per_class.json:
{
  "generated_at": "ISO timestamp",
  "total_trades": N,
  "asset_classes": {
    "EQUITY": {
      "n_trades": N, "wins": N, "losses": N, "win_rate": 0.XX,
      "profit_factor": X.XX, "sharpe": X.XX, "max_dd": 0.XX,
      "expectancy": X.XX, "confidence_95_pf": [X.XX, X.XX],
      "strategies": [...],
      "rolling_7d_pf": X.XX, "rolling_30d_pf": X.XX,
      "status": "T1/T2/T3/NO_EDGE/INSUFFICIENT_DATA"
    },
    ...
  }
}
```

### Prompt 1B: Deep Strategy Autopsy

```
Using the ejaguiar1_backtests database, perform forensic analysis on strategy performance.

For EACH strategy with n >= 20 trades:

1. Pick Distribution: Histogram of PnL per trade (identify bimodal distributions)
2. Concentration Risk: Is >20% of total PnL from a single symbol?
3. Regime Performance: Split trades by market regime (if regime data exists)
4. Day-of-Week Effect: WR by Monday/Tuesday/Wednesday/Thursday/Friday
5. Hour-of-Day Effect: WR by trading hour (for intraday strategies)
6. Streak Analysis: Longest win streak, longest loss streak, serial correlation
7. Drawdown Profile: Time spent in drawdown, recovery time distribution
8. Fat Tail Analysis: Count of trades >3 sigma from mean (outlier risk)

Flag strategies with:
- High WR but low PF (many small wins, few huge losses = dangerous)
- Low WR but high PF (few big wins, many small losses = viable with sizing)
- Serial correlation > 0.3 (trending performance, regime-dependent)
- Outlier rate > 5% (unstable, single trade can destroy month)

Output: strategy_autopsy.json with per-strategy health scores (0-100)
```

---

## SECTION 2: Per-Asset-Class Improvement Prompts

> **Source:** CRYPTO, EQUITY, and FOREX statistics below reflect verified data from `audit_dashboard/data/dashboard_data.json` (2026-05-16T03:55Z edge analysis).

### Prompt 2A: CRYPTO Confidence Recalibration (Critical — Your #1 Problem)

```
PROBLEM STATEMENT: CRYPTO shows PF 0.70 with 18% volume, stable but volume-capped by quan_engine drag. Confidence >= 0.90 produces low WR, while confidence 0.50-0.60 produces higher WR. This is ML calibration inversion — the model is confidently wrong.

TASK: Fix the CRYPTO prediction pipeline.

1. In the codebase, locate:
   - alpha_engine/score_booster._calibrate_confidence()
   - The upstream ML model that generates confidence scores for crypto
   - Any calibration curves (reliability diagrams) in the code

2. Implement these fixes:
   a) Isotonic Regression calibration: Fit isotonic regression on validation set to map raw confidence → calibrated probability
   b) Platt Scaling: Logistic calibration as fallback
   c) Temperature Scaling: Learn a temperature parameter T to sharpen/soften softmax outputs
   d) Per-regime calibration: Fit separate calibration curves for trending vs ranging markets

3. For crypto specifically, implement the INVERSION LAYER:
   - If confidence > 0.85: set effective_score = raw_score - 12 (existing penalty — keep)
   - If confidence < 0.60: set effective_score = raw_score + 3 (existing reward — keep)
   - BUT ALSO: Flip the direction for confidence > 0.85 (if model says BUY with 90% confidence, treat as SELL signal with reduced size)
   - Document: "crypto_high_confidence_inversion = True"

4. Add a calibration monitoring job that runs daily:
   - Bin predictions by confidence decile (0-10%, 10-20%, ..., 90-100%)
   - Calculate actual WR per bin
   - If actual WR < predicted WR for 3 consecutive bins: TRIGGER_ALERT
   - Auto-disable any bin where WR < 20% for 7+ days

5. After calibration, recalculate:
   - Expected WR per confidence band
   - Expected PF per confidence band
   - New threshold for "tradeable" signals

ACCEPTANCE CRITERIA:
- WR for confidence >= 0.80 must be >= 55%
- WR for confidence 0.50-0.60 must be >= 50%
- Calibration curve (actual WR vs predicted confidence) must be monotonic increasing
- Test on 30-day holdout before deploying
```

### Prompt 2B: EQUITY — Scale What Works

```
PROBLEM STATEMENT: EQUITY shows PF 1.974, WR 54.0%, n=252 — this is a genuine T2 edge. But the recent panel may differ. We need to scale this systematically.

TASK: Build an EQUITY edge amplification system.

1. From the database, extract EQUITY trades with score >= 50 AND trust >= 7.
   Calculate the PF/WR for this filtered subset. Is it higher than the overall 1.974?

2. Implement EQUITY-specific filters:
   a) Pre-market gap filter: Skip if overnight gap > 3% ( earnings risk )
   b) Earnings window filter: No new positions 3 days before/after earnings
   c) Sector rotation overlay: Track relative strength of XLK vs XLU vs XLE
   d) VIX regime filter: Reduce position size by 50% if VIX > 25
   e) Market breadth filter: Only trade if NYSE advance-decline line is positive

3. Implement "Smart Conviction Stack" for EQUITY:
   - Score 50-59: Paper trade only (1x size)
   - Score 60-69: 0.5% portfolio allocation
   - Score 70-79: 1.0% portfolio allocation
   - Score 80-89: 1.5% portfolio allocation (max without exception)
   - Score 90+: 2.0% portfolio allocation (requires human approval)

4. Add EQUITY-specific strategy DNA:
   - Volatility Contraction Breakout (your top strategy per audit)
   - Mean Reversion after earnings gap
   - Sector momentum rotation
   - Overnight gap fade

5. Edge validation requirement:
   - Must produce PF > 1.5 on 90-day rolling window
   - Must produce WR > 50% on 30-day rolling window
   - If either fails for 14 consecutive days: PAUSE new trades, investigate

6. Output: equity_edge_v2.py — standalone module that can be imported and called
```

### Prompt 2C: FOREX — Mutation Protocol (Your Worst Performer)

```
PROBLEM STATEMENT: FOREX shows PF 0.27, worst asset class, LONG blocked until 2026-05-22. Losers are far bigger than winners. Classic "death by a thousand cuts with occasional catastrophe."

TASK: Full FOREX strategy mutation.

1. From database, analyze FOREX trade distribution:
   - What is the average win? Average loss? (expect loss > win)
   - Which currency pairs are the worst? (likely JPY crosses)
   - Which time of day produces best/worst results?
   - What is the holding period distribution? (too long = swap cost drain)

2. Implement FOREX Mutation Protocol:
   a) DIRECTION FLIP: Since PF 0.27 means inverted would be PF 1/0.27 ≈ 3.70, test a 30-day pilot where ALL signals are inverted
   b) SYNTAX-LIMITED PAIRS: Only trade EURUSD, GBPUSD, USDJPY (most liquid, lowest spread)
   c) SESSION FILTER: Only trade during London-NY overlap (8am-12pm EST) for highest liquidity
   d) SWAP AWARENESS: Exit all positions before 5pm EST to avoid overnight swap costs
   e) CARRY FILTER: Only go LONG pairs with positive carry, SHORT pairs with negative carry

3. Add COT (Commitment of Traders) data overlay:
   - Load COT data for each currency
   - If commercial traders are net LONG > 70%: bias signals LONG
   - If commercial traders are net SHORT > 70%: bias signals SHORT
   - If commercials are neutral (30-70%): no bias, use technical signals only

4. Risk limits (strict):
   - Max 0.5% risk per trade (tighter than other asset classes)
   - Max 2 concurrent FOREX positions
   - Hard stop at 1% loss per trade
   - Daily loss limit: 2% of FOREX allocation (then stop for the day)

5. Mutation evaluation framework:
   - Run original + mutated strategy side by side for 30 days
   - Compare PF, WR, avg trade duration, swap costs
   - If mutated version PF > 1.2 after 30 days: deploy
   - If still PF < 1.0 after 30 days: kill FOREX trading entirely

6. Output: forex_mutation_v2.py with A/B testing harness
```

### Prompt 2D: COMMODITY — Clean the COT Artifact

```
PROBLEM STATEMENT: COMMODITY shows PF 2.48, WR 61.2% — looks amazing BUT audit says this is "inflated by CT=F COT dedup artifact." COT-dedup guard is active but awaiting 100 clean picks.

TASK: Produce clean COMMODITY edge without COT contamination.

1. Database analysis:
   - Separate CT=F (Cotton) trades from non-COT commodity trades
   - Calculate PF/WR for: GC=F (Gold), CL=F (Oil), ZW=F (Wheat), ZS=F (Soybeans), HG=F (Copper)
   - Calculate PF/WR for CT=F alone
   - Confirm: Is CT=F responsible for the headline 2.48 PF?

2. Implement COT-dedup filter:
   - If a signal is generated within 24h of a COT report release for the SAME symbol: DEDUPLICATE
   - Only keep the FIRST signal after COT release
   - Mark all deduped signals in database with flag "cot_dedup_excluded"

3. Build clean COMMODITY strategies:
   a) Seasonality Strategy: Load 10-year seasonal patterns per commodity
      - Long Gold in January (historical strength)
      - Short NatGas in October (shoulder season)
      - Use seasonal percentile ranks as signal modifiers
   
   b) COT Commercial Positioning (CLEAN):
      - If commercials are net long > 65% of recent range: LONG bias
      - If commercials are net short > 65% of recent range: SHORT bias
      - Only update once per week (after COT Friday release)
      - No intraday COT signals
   
   c) Roll Yield Capture:
      - If futures curve is in backwardation: LONG (positive carry)
      - If futures curve is in contango: SHORT (or avoid LONG)
      - Only apply to holding periods > 5 days

4. Clean validation gate:
   - Must have 100 clean picks (no COT dedup) before claiming any tier
   - Target after clean: PF > 1.5, WR > 55%, MDD < 15%
   - If clean PF < 1.2 after 100 picks: COMMODITY goes to PAPER ONLY

5. Output: commodity_clean_v2.py with COT dedup guard + seasonal overlay
```

### Prompt 2E: ETF — Sector Rotation Momentum

```
PROBLEM STATEMENT: ETF shows PF 1.33, WR 57.4%, n=108 — charter floor met (n>=100) but below T2 threshold of PF 1.5. Need to lift PF to 1.5 for T2 status.

TASK: ETF edge amplification through sector rotation.

1. From database:
   - Which ETFs are traded? (SPY, QQQ, IWM, sector ETFs?)
   - What is PF/WR per individual ETF?
   - Which strategy is used? (audit says rs-breakout-scout)
   - What is the average holding period?

2. Implement ETF-Specific Edge:
   a) Relative Strength Rotation:
      - Calculate 20-day momentum for all 11 sector ETFs
      - Go LONG the top 3 sectors by momentum
      - Go SHORT the bottom 3 sectors (if shorting allowed)
      - Rebalance weekly
   
   b) Flow-Based Signal:
      - Track daily ETF flow data (if available via ICI or ETF.com)
      - If inflows > $500M into sector over 5 days: LONG signal
      - If outflows > $300M: avoid or SHORT
   
   c) Macro Regime Overlay:
      - Rising rates environment: Underweight TLT, overweight XLF
      - Falling rates: Overweight TLT, underweight XLF
      - High inflation: Overweight XLE, XLB
      - Low inflation: Overweight XLK, XLY

3. Score the regime alignment:
   - If signal DIRECTION matches macro regime: +10 points to score
   - If signal OPPOSES macro regime: -5 points
   - If neutral regime: no adjustment

4. Target to achieve T2:
   - Need PF lift from 1.33 → 1.50 (13% improvement)
   - WR already 57.4% (above 50% threshold)
   - MDD must stay < 20%
   - Action: Filter to Score >= 60 only, add regime overlay
   - Expected: PF 1.5-1.7, WR 58-62%

5. Output: etf_sector_rotation_v2.py
```

### Prompt 2F: BOND — Accumulation Mode with Strict Gates

```
PROBLEM STATEMENT: BOND shows PF 0.66, WR 54.5%, n=11 — far below any meaningful threshold. Need to accumulate 100+ picks before claiming edge.

TASK: BOND scanner + paper-only accumulator.

1. DO NOT trade bonds with real money until:
   - n >= 100 closed picks
   - PF > 1.2
   - WR > 50%
   - All achieved on paper trading

2. Implement BOND signal generator:
   a) Yield Curve Slope:
      - Calculate 10Y-2Y Treasury spread
      - If spread > 100bp (steepening): LONG TLT (rates falling)
      - If spread < 0bp (inverted): SHORT TLT or LONG SHY (rates rising)
      - If spread 0-50bp: no signal (uncertain regime)
   
   b) Credit Spread Signal:
      - Calculate HYG spread over Treasuries
      - If spread widening > 20bp in 5 days: risk-off, avoid corporate bonds
      - If spread tightening: risk-on, LONG HYG/LQD
   
   c) Rate Expectation:
      - Fed Funds futures implied probability of rate change
      - If > 70% chance of CUT: LONG TLT
      - If > 70% chance of HIKE: SHORT TLT
      - Otherwise: no directional bias

3. Paper trading accumulator:
   - Generate 3-5 BOND signals per week
   - Track in separate paper_portfolio table
   - Calculate rolling PF/WR after each 10-trade milestone
   - At n=50: preliminary review
   - At n=100: full statistical evaluation
   - Only if PF > 1.2 AND WR > 50%: enable small live trades (0.25% size)

4. Output: bond_accumulator_v2.py — paper-only, no real money wiring
```

---

## SECTION 3: System-Wide Improvement Prompts

### Prompt 3A: DNA Mutation Engine

```
Build a Strategy DNA Mutation Engine that automatically evolves strategies.

CONCEPT: Every strategy has "DNA" — a set of parameters, filters, and rules.
When a strategy underperforms, we mutate its DNA rather than killing it.

1. DNA Representation:
Each strategy's DNA is a JSON object:
{
  "strategy_id": "uuid",
  "parent_id": "uuid or null",
  "generation": 1,
  "chromosomes": {
    "entry_trigger": {"type": "rsi_cross", "params": {"period": 14, "level": 30}},
    "exit_trigger": {"type": "atr_stop", "params": {"mult": 2.0}},
    "filter_regime": {"type": "trend", "params": {"ma_fast": 10, "ma_slow": 50}},
    "filter_volatility": {"type": "atr_percentile", "params": {"window": 20, "min": 30, "max": 80}},
    "position_size": {"type": "kelly_half", "params": {"cap": 0.02}},
    "max_holding": {"type": "fixed", "params": {"days": 5}}
  },
  "fitness_score": 0.0,
  "birth_date": "2026-05-16",
  "status": "active"
}

2. Mutation Operators:
   a) POINT_MUTATION: Randomly change one parameter (e.g., RSI 14→21)
   b) CROSSOVER: Combine chromosomes from two parent strategies
   c) INVERSION: Flip the direction of a strategy (BUY↔SELL)
   d) FILTER_ADD: Add a new filter chromosome
   e) FILTER_REMOVE: Remove a filter that reduces fitness
   f) REGIME_SWITCH: Create per-regime variants (trending vs ranging)

3. Fitness Function:
   fitness = (PF * 0.4) + (WR * 100 * 0.3) + (sharpe * 10 * 0.2) + (1/max(1,MDD*10) * 0.1)
   Minimum n=20 for fitness evaluation
   Penalty: -0.5 if rolling 7d WR drops >20% below baseline

4. Evolution Loop (runs weekly):
   - Evaluate fitness of all active strategies
   - Kill strategies with fitness < 0.5 (generational death)
   - Clone top 20% strategies with POINT_MUTATION
   - Create CROSSOVER children from top 40% pairs
   - If any strategy has WR 35-45%: create INVERSION variant
   - Place new mutants in PAPER_TRADING sandbox
   - After 30 days / 20 trades: promote to LIVE if fitness > 0.7
   - Track lineage: every mutant knows its parent

5. Output: dna_mutation_engine.py with:
   - StrategyDNA class (serialize/deserialize DNA)
   - MutationEngine class (apply operators)
   - FitnessEvaluator class (calculate fitness)
   - EvolutionLoop class (weekly run)
   - LineageTracker class (parent-child relationships)
```

### Prompt 3B: Strategy Inversion Layer

```
Build an automatic "Invert the Losers" system.

PROBLEM: Many strategies have 35-45% WR — they are reliably WRONG. Instead of deleting them, we can INVERT them to get 55-65% WR.

1. Inversion Detection (runs daily):
For each strategy with n >= 20:
   - Calculate actual WR over last 60 trades
   - If 35% <= WR <= 45%: FLAG as "inversion_candidate"
   - If 25% <= WR <= 35%: FLAG as "strong_inversion_candidate" (65-75% inverted WR)
   - Calculate hypothetical inverted PF/WR
   - If inverted_PF >= 1.3 AND inverted_WR >= 55%: AUTO-CREATE inversion

2. Inverted Strategy Creation:
Original: "buy_when_rsi_below_30"
Inverted: "sell_when_rsi_below_30" (BUY → SELL, vice versa)

Original exit: "sell_when_rsi_above_70"
Inverted exit: "buy_when_rsi_above_70"

But keep:
- Same position sizing (Kelly)
- Same stop losses
- Same filters (volatility, regime)
- Different name: "INV_buy_when_rsi_below_30"

3. A/B Test Framework:
   - Run original AND inverted simultaneously
   - But with REDUCED size (0.25% each instead of 0.5%)
   - Track both for 30 days / 20 trades minimum
   - At evaluation: keep the winner, kill the loser

4. Safety Guard:
   - Never run inverted strategy at full size until it proves itself
   - Max 5 inverted strategies active at any time
   - If inverted strategy WR drops below 50% for 14 days: KILL immediately
   - Log every inversion decision with full reasoning

5. Output: inversion_layer.py + inverted_strategies table in database
```

### Prompt 3C: Swarm Research Agents (Per Asset Class)

```
Create a Swarm Research System that deploys specialized research agents per asset class.

ARCHITECTURE:
```
                    Swarm Orchestrator
                         |
     +----------+--------+--------+----------+
     |          |        |        |          |
  Crypto    Equity   Forex   Commodity   Bond/ETF
 Research  Research Research Research   Research
  Agent     Agent    Agent    Agent     Agent
```

1. Swarm Orchestrator (swarm_orchestrator.py):
   - Daily: deploys all 5 research agents
   - Collects findings from each agent
   - Cross-validates (e.g., if both equity and forex agree on USD direction, boost confidence)
   - Generates unified daily research report
   - Updates alpha_engine with new signals

2. Each Research Agent has these tools:
   a) Technical Analysis Tool: Compute all indicators, identify patterns
   b) Fundamental Scraper: Scrape earnings, macro data, COT reports
   c) Sentiment Analyzer: Analyze social media, news sentiment
   d) Correlation Engine: Cross-asset correlation, lead-lag analysis
   e) Regime Detector: HMM-based market state classification
   f) Backtest Runner: Test new ideas on historical data
   g) Report Generator: Markdown report with actionable signals

3. Crypto Research Agent (agents/crypto_researcher.py):
   - Runs: continuous (24/7)
   - Inputs: Price data, funding rates, open interest, social sentiment
   - Output: LONG/SHORT/NEUTRAL + confidence + reasoning
   - Special: Tracks Bitcoin dominance, altcoin season index, exchange flows

4. Equity Research Agent (agents/equity_researcher.py):
   - Runs: Before market open (8:00 AM EST), after close (5:00 PM EST)
   - Inputs: Earnings calendar, pre-market movers, sector performance
   - Output: Pre-market bias, intraday levels, post-market review
   - Special: Earnings surprise predictor, sector rotation tracker

5. Forex Research Agent (agents/forex_researcher.py):
   - Runs: 4x daily (London open, London-NY overlap, NY afternoon, Asia open)
   - Inputs: COT data (weekly), economic calendar, central bank speeches
   - Output: Session bias, key levels, carry trade signals
   - Special: Interest rate differential tracker, COT commercial positioning

6. Commodity Research Agent (agents/commodity_researcher.py):
   - Runs: Daily (after market close)
   - Inputs: Inventory reports, weather data, COT, seasonal patterns
   - Output: Supply/demand imbalance score, directional bias
   - Special: Seasonal percentile rank, weather impact model

7. Bond/ETF Research Agent (agents/bond_etf_researcher.py):
   - Runs: Daily (after Treasury close)
   - Inputs: Yield curve, Fed policy, flow data, credit spreads
   - Output: Rate direction bias, sector ETF rotation signals
   - Special: Yield curve slope predictor, credit cycle position

8. Each agent produces:
```json
{
  "agent": "crypto_researcher",
  "timestamp": "2026-05-16T12:00:00Z",
  "asset_class": "CRYPTO",
  "signal": {
    "direction": "LONG",
    "symbol": "BTC-USD",
    "confidence": 0.65,
    "entry_price": 103500,
    "stop_loss": 101430,
    "take_profit": 107640,
    "timeframe": "5d",
    "reasoning": "Funding rate negative (shorts pay longs), RSI 32 oversold, exchange outflows increasing"
  },
  "regime": "mean_reverting",
  "risk_level": "medium"
}
```

9. Swarm Consensus:
   - If 3+ agents agree on DIRECTION: boost confidence by +0.15
   - If 2 agents agree: no boost
   - If agents disagree: reduce confidence by -0.10, flag "MIXED_SIGNALS"
   - If agent contradicts its own 7-day baseline: REDUCE weight by 50%

10. Output: swarm/ directory with 5 agent files + orchestrator + consensus engine
```

### Prompt 3D: The "Necromancer" — Save Failing Strategies

```
Build a "Necromancer" system that resurrects failing strategies instead of deleting them.

CONCEPT: When a strategy drops below threshold, don't kill it — diagnose WHY and fix it.

1. Diagnosis Pipeline (triggered when strategy PF < 1.0 for 14 days):
   a) Regime Check: Is the strategy failing in ALL regimes or just one?
   b) Asset Check: Is it failing on ALL symbols or just specific ones?
   c) Time Check: Is it failing recently or consistently?
   d) Correlation Check: Is another strategy stealing its edge (dilution)?
   e) Parameter Check: Have optimal parameters drifted?

2. Treatment Options:
   If failing ONLY in trending regime → ADD counter-trend filter
   If failing ONLY on specific symbols → REMOVE those symbols from universe
   If failing recently but historically good → REDUCE size by 50% (don't kill)
   If edge stolen by newer strategy → MERGE with the newer strategy
   If parameters drifted → RE-OPTIMIZE on recent data only

3. The "Phoenix Protocol":
   - Quarantine failing strategy (stop new trades, keep existing)
   - Run diagnosis
   - Apply treatment
   - Paper trade treated version for 20 trades
   - If treated PF > 1.3: RE-LAUNCH as "StrategyName_v2"
   - If treatment fails: FINAL KILL, but save DNA for future crossover

4. Output: necromancer.py + strategy_quarantine table in DB
```

### Prompt 3E: Multi-Timeframe Confluence Engine

```
Build a Multi-Timeframe Confluence (MTF) engine that requires agreement across timeframes before generating a signal.

PROBLEM: Many signals fail because they align with 1h trend but oppose the daily trend. Require multiple timeframes to agree.

1. Timeframe Hierarchy:
   - PRIMARY (entry timeframe): 1h or 4h
   - SECONDARY (trend confirmation): Daily
   - TERTIARY (macro context): Weekly

2. Confluence Scoring:
   For a LONG signal to trigger:
   - PRIMARY: Must show BUY signal (e.g., RSI cross, MA cross)
   - SECONDARY: Daily trend must be UP or NEUTRAL (not DOWN)
   - TERTIARY: Weekly trend must not be strongly DOWN
   
   Scoring:
   - All 3 agree (UP/UP/UP): Score +30, full size
   - 2 of 3 agree (UP/UP/FLAT): Score +15, half size
   - 1 of 3 agree (UP/FLAT/DOWN): Score -10, NO TRADE
   - 0 of 3 agree: Score -30, opposite signal considered

3. Asset-class specific timeframes:
   - CRYPTO: 4h / 1d / 3d (faster, 24/7)
   - EQUITY: 1h / 1d / 1w (standard)
   - FOREX: 4h / 1d / 1w (standard)
   - COMMODITY: 1d / 1w / 1M (slower, fundamentals-driven)
   - ETF: 1d / 1w / 1M (long-term)
   - BOND: 1d / 1w / 1M (very long-term)

4. Implementation:
   - Compute signals on all 3 timeframes independently
   - Store in mtf_signals table
   - Confluence scorer reads all 3, outputs final signal + score
   - Backtest: Does MTF filtering improve PF? (expect +0.2 to +0.5 PF lift)

5. Output: mtf_confluence_engine.py
```

### Prompt 3F: Adaptive Risk Manager (Kelly + CPPI Hybrid)

```
Build an Adaptive Risk Manager that dynamically adjusts position size based on:
1. Kelly criterion (proven edge)
2. CPPI (Constant Proportion Portfolio Insurance) — protects floor
3. Current drawdown level
4. Correlation heatmap

POSITION SIZE FORMULA:
final_size = min(
  kelly_half * edge_score,              # Kelly-derived size
  cppi_max_exposure,                     # CPPI cap
  drawdown_reduced_size,                 # Smaller when in DD
  correlation_adjusted_size              # Smaller when correlated
)

1. Kelly Half:
   kelly = (WR * W/L_ratio - (1-WR)) / W/L_ratio
   size = kelly * 0.5 * (score / 100)   # Score-weighted Kelly
   
2. CPPI Floor:
   floor = portfolio_value * 0.90       # 10% max loss allowed
   cushion = portfolio_value - floor
   cppi_exposure = cushion * multiplier  # multiplier = 3-5
   
3. Drawdown Reduction:
   if current_DD < 5%:  dd_factor = 1.0  (full size)
   if current_DD < 10%: dd_factor = 0.75 (75% size)
   if current_DD < 15%: dd_factor = 0.50 (50% size)
   if current_DD > 20%: dd_factor = 0.0  (STOP all new trades)
   
4. Correlation Adjustment:
   Count currently open positions in same asset class
   if 0 open: corr_factor = 1.0
   if 1 open: corr_factor = 0.8
   if 2 open: corr_factor = 0.6
   if 3+ open: corr_factor = 0.4
   
   Also check cross-asset correlation:
   If BTC and ETH positions both open: corr_factor *= 0.7 (high correlation)

FINAL FORMULA:
position_size = kelly_size * dd_factor * corr_factor
if portfolio_exposure + position_size > cppi_exposure:
  position_size = cppi_exposure - portfolio_exposure  # Hard CPPI cap

5. Output: adaptive_risk_manager.py with real-time portfolio tracking
```

---

## SECTION 4: GitHub Actions Integration Prompts

### Prompt 4A: Efficient CI/CD for Research Agents

```
Design GitHub Actions workflows for the swarm research agents that are efficient and don't duplicate existing jobs.

REQUIREMENTS:
- Add to existing workflows, don't create new ones
- Share Python environment between jobs (use cache)
- Only run when relevant code changes
- Use conditional logic to skip expensive steps

PROPOSED WORKFLOW STRUCTURE:

.github/workflows/
├── audit_main.yml          ← EXISTING (your current main workflow)
├── audit_v2_research.yml   ← NEW (lightweight, adds research triggers)
└── audit_v2_deploy.yml     ← NEW (deploys v2 dashboard, depends on main)

The audit_v2_research.yml triggers:
- On schedule: Every 6 hours (aligned with your existing data refresh)
- On dispatch: Manual trigger
- On push: Only if swarm/ or agents/ directory changes

Key efficiency features:
1. Job dependency: v2_research needs: [your_existing_data_job]
2. Python env: Use actions/setup-python with cache: 'pip'
3. Shared venv: Cache .venv between runs (key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }})
4. Conditional steps: Use if: steps.changed-files.outputs.swarm == 'true'
5. Artifact passing: Pass research output as artifact to deploy job
6. Matrix strategy: Run 5 agents in parallel (5 jobs, not sequential)

Estimated cost: Adds ~2 minutes to existing workflow (agents run in parallel)
```

### Prompt 4B: Automated Edge Monitoring Alert

```
Create a monitoring job that runs every 6 hours and alerts when edge degrades.

ALERT CONDITIONS:
1. CRITICAL (Slack/Email): Any asset class rolling 7d PF < 0.8
2. WARNING (Slack): Any asset class rolling 30d PF < 1.0
3. INFO (Dashboard): Any strategy rolling 7d WR >20% below its all-time baseline
4. OPPORTUNITY: Any strategy with 35-45% WR (inversion candidate detected)

AUTO-ACTIONS:
- CRITICAL: Pause new trades in that asset class, alert team
- WARNING: Reduce position size by 50%, add to watchlist
- INFO: Log only, show on dashboard
- OPPORTUNITY: Auto-create inverted strategy in paper sandbox

Output: edge_monitor.py + GitHub Actions job
```

---

## SECTION 5: Complete Strategic Roadmap

### Phase 1: Foundation (Week 1-2)
1. Run Prompt 1A (MySQL edge extraction) → Get ground truth
2. Run Prompt 1B (Strategy autopsy) → Know what you have
3. Fix CRYPTO confidence calibration (Prompt 2A) → Your biggest leak

### Phase 2: Amplify Winners (Week 3-4)
4. Scale EQUITY (Prompt 2B) → Only class with real T2 edge
5. Clean COMMODITY (Prompt 2D) → Remove COT artifact
6. Enhance ETF (Prompt 2E) → Push to T2 threshold

### Phase 3: Fix or Kill Losers (Week 5-6)
7. FOREX mutation (Prompt 2C) → Invert or kill
8. BOND accumulator (Prompt 2F) → Paper only, 100-pick target
9. Deploy inversion layer (Prompt 3B) → Harvest contrarian alpha

### Phase 4: Evolve (Week 7-8)
10. DNA mutation engine (Prompt 3A) → Automated strategy evolution
11. Necromancer (Prompt 3D) → Save salvageable strategies
12. MTF confluence (Prompt 3E) → Multi-timeframe filtering

### Phase 5: Swarm Intelligence (Week 9-10)
13. Deploy 5 research agents (Prompt 3C) → Per-asset-class research
14. Adaptive risk manager (Prompt 3F) → Kelly + CPPI hybrid sizing
15. Launch /audit/v2 dashboard → Full integration

### Phase 6: Optimize (Ongoing)
16. Weekly: Run edge monitoring (Prompt 4B)
17. Weekly: Evolution loop (DNA mutation)
18. Monthly: Full statistical review per asset class
19. Quarterly: Re-evaluate all tier assignments

---

## SUMMARY: Which Prompts to Run When

| Priority | Prompt | When | Expected Impact |
|----------|--------|------|-----------------|
| 🔴 CRITICAL | 1A (MySQL Edge) | TODAY | Ground truth — know where you stand |
| 🔴 CRITICAL | 2A (CRYPTO Calib) | This week | Fix PF 0.70 volume cap from quan_engine drag |
| 🟠 HIGH | 2B (EQUITY Scale) | Week 2 | Lock in T2 edge, systematic sizing |
| 🟠 HIGH | 2D (COMM Clean) | Week 2 | Real 2.48 PF or artifact? |
| 🟠 HIGH | 3B (Inversion) | Week 3 | Free alpha from reliably wrong strategies |
| 🟡 MEDIUM | 3A (DNA Mutation) | Week 5 | Automated strategy evolution |
| 🟡 MEDIUM | 3C (Swarm Agents) | Week 7 | Multi-agent research per class |
| 🟢 LATER | 2C (FOREX Fix) | Week 5-6 | Only if mutation works |
| 🟢 LATER | 2F (BOND Accum) | Ongoing | Paper trade to 100 picks |
| 🟢 LATER | 3D (Necromancer) | Week 7+ | Save salvageable strategies |
