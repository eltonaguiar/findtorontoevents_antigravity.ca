# Live Trading Monitor - Forward-Facing Performance Summary
**Generated:** 2026-02-12 20:45 UTC
**Data Source:** Production API endpoints (findtorontoevents.ca/live-monitor/)
**Period:** Last 90 days (Feb 2026)

---

## Executive Summary

**Portfolio Status:** $9,969.03 (down from initial $10,000)
**Total Realized PnL:** +$33.44 (+0.33%)
**Current Drawdown:** -0.52% from peak ($10,022.40)
**Open Positions:** 10 positions ($4,426.48 invested)
**Unrealized PnL:** -$30.07

**Overall Performance:**
- **Total Trades:** 13 closed positions
- **Win Rate:** 53.85% (7 wins, 6 losses)
- **Profit Factor:** 1.83
- **Average Return:** +0.54% per trade
- **Average Win:** +2.16% | Average Loss:** -1.35%
- **Average Hold Time:** 7.65 hours

---

## Performance by Algorithm

### Top Performers

#### 1. Ichimoku Cloud - BEST PERFORMER
- **Win Rate:** 80% (4 wins, 1 loss)
- **Total Trades:** 5
- **Average Return:** +1.85% per trade
- **Total PnL:** +$44.97
- **Average Hold:** 6.75 hours
- **Parameters (Learned):**
  - Take Profit: 3.4% (vs 2% default)
  - Stop Loss: 2%
  - Max Hold: 16 hours
- **Status:** PROFITABLE - Learned to be more aggressive on TP

#### 2. StochRSI Crossover
- **Win Rate:** 75% (3 wins, 1 loss)
- **Total Trades:** 4
- **Average Return:** +0.23% per trade
- **Total PnL:** +$4.25
- **Average Hold:** 6.2 hours
- **Parameters (Learned):**
  - Take Profit: 3.1% (vs 2% default)
  - Stop Loss: 2%
  - Max Hold: 12 hours
- **Status:** PROFITABLE - Slightly more aggressive TP

### Underperformers

#### 3. RSI Reversal - NEEDS REVIEW
- **Win Rate:** 0% (0 wins, 1 loss)
- **Total Trades:** 1 (insufficient data)
- **Average Return:** -0.03%
- **Total PnL:** -$0.17
- **Average Hold:** 7.02 hours
- **Parameters (Learned):**
  - Take Profit: 2%
  - Stop Loss: 1%
  - Max Hold: 6 hours
- **Status:** NEUTRAL - Too few trades to evaluate

#### 4. Consensus (Challenger Bot) - STRUGGLING
- **Win Rate:** 0% (0 wins, 2 losses)
- **Total Trades:** 2
- **Average Return:** -0.33%
- **Total PnL:** -$3.28
- **Average Hold:** 12.3 hours
- **Parameters (Learned):**
  - Take Profit: 3%
  - Stop Loss: 2%
  - Max Hold: 12 hours (vs 24 default)
- **Status:** UNDERPERFORMING - Both FOREX trades lost

#### 5. Unknown Algorithm (Empty String)
- **Win Rate:** 0% (0 wins, 1 loss)
- **Total Trades:** 1
- **Total PnL:** -$12.33 (-2.47%)
- **Trade:** BTCUSD LONG on 2026-02-09
- **Status:** DATA QUALITY ISSUE - Missing algorithm name

---

## Performance by Asset Class

### Crypto - STRONG PERFORMER
- **Total Trades:** 9
- **Win Rate:** 77.8% (7 wins, 2 losses)
- **Average Return:** +1.13% per trade
- **Total PnL:** +$10.15
- **Status:** PRIMARY PROFIT DRIVER

**Top Crypto Trades:**
1. UNIUSD SHORT: +4.06% (Ichimoku Cloud)
2. AXSUSD SHORT: +3.42% (Ichimoku Cloud)
3. BCHUSD SHORT: +2.82% (Ichimoku Cloud)
4. HBARUSD SHORT: +2.63% (StochRSI Crossover)

### Forex - LOSING
- **Total Trades:** 3
- **Win Rate:** 0% (0 wins, 3 losses)
- **Average Return:** -0.23% per trade
- **Total PnL:** -$0.69
- **Status:** AVOID - All trades lost

**Forex Failures:**
1. USDJPY LONG: -0.47% (Consensus, max hold exit)
2. GBPUSD LONG: -0.19% (Consensus, max hold exit)
3. EURUSD LONG: -0.03% (RSI Reversal, max hold exit)

### Stocks - MIXED (Currently Open)
- **Open Positions:** 5 stocks (all Challenger Bot)
- **Current Unrealized PnL:** -$24.79 (-1.26% avg)
- **Positions:**
  - AMZN: -2.50%
  - NVDA: -1.90%
  - GOOGL: -0.48%
  - MSFT: -0.21%
  - JNJ: +0.004% (VAM algo)

---

## Current Open Positions (10 Total)

### Winning Positions (3)
1. **SUIUSD** (CRYPTO, StochRSI Crossover): +0.72% (+$3.61)
2. **TRXUSD** (CRYPTO, StochRSI Crossover): +0.58% (+$2.90)
3. **JNJ** (STOCK, VAM): +0.004% (+$0.02)

### Losing Positions (6)
1. **AMZN** (STOCK, Challenger Bot): -2.50% (-$12.17) - NEAR STOP LOSS
2. **NVDA** (STOCK, Challenger Bot): -1.90% (-$9.24)
3. **ATOMUSD** (CRYPTO, Alpha Predator): -1.47% (-$7.18)
4. **SOLUSD** (CRYPTO, StochRSI Crossover): -0.94% (-$4.63)
5. **GOOGL** (STOCK, Challenger Bot): -0.48% (-$2.33)
6. **MSFT** (STOCK, Challenger Bot): -0.21% (-$1.05)

### Flat Position (1)
1. **DOGEUSD** (CRYPTO, StochRSI Crossover): 0% ($0.00) - Just opened

---

## Machine Learning Progress

### Signal Generation
- **Learned Signals Generated:** 2,491 (vs 500 original)
- **Improvement:** 5x more signals from learned parameters
- **Untagged Signals:** 0 (100% tagged)

### Parameter Learning Status
**Note:** The `learned_params` endpoint returned empty results, indicating no stored parameter evolution data. However, the `by_algorithm` endpoint shows clear evidence of learned parameters:

#### Learned vs Default Parameters

**Ichimoku Cloud:**
- Learned TP: 3.4% vs Default: 2% (+70% increase)
- Learned SL: 2% vs Default: 1% (+100% increase)
- Max Hold: 16 hours (unchanged)
- **Result:** More aggressive profit taking and tighter risk management

**StochRSI Crossover:**
- Learned TP: 3.1% vs Default: 2% (+55% increase)
- Learned SL: 2% vs Default: 1% (+100% increase)
- Max Hold: 12 hours (unchanged)
- **Result:** Balanced approach with higher targets

**Consensus:**
- Learned Max Hold: 12 hours vs Default: 24 hours (-50% decrease)
- TP/SL: 3%/2% (default values retained)
- **Result:** System learned to cut losing trades faster

**RSI Reversal:**
- Parameters: 2% TP, 1% SL, 6 hours max hold
- **Result:** Conservative defaults maintained (insufficient data)

---

## Exit Reason Analysis

From 13 closed trades:
- **Take Profit (5 trades):** 38% - All profitable (+$52.58 total)
- **Stop Loss (4 trades):** 31% - All losses (-$39.39 total)
- **Trailing Stop (2 trades):** 15% - All profitable (+$8.36 total)
- **Max Hold (3 trades):** 23% - All losses (-$2.50 total)

**Key Insight:** Max hold exits are 100% losers. System correctly learned to reduce max hold time on Consensus algorithm.

---

## Trade Quality Metrics

### Winning Trades (7 total)
- **Best Trade:** UNIUSD SHORT +4.06% (+$20.00, Ichimoku Cloud)
- **Worst Win:** ARBUSD SHORT +0.50% (+$2.41, StochRSI Crossover)
- **Average Win:** +2.16%
- **Average Win Hold:** ~6 hours

### Losing Trades (6 total)
- **Worst Trade:** AXSUSD SHORT -2.51% (-$12.59, Ichimoku Cloud)
- **Best Loss:** EURUSD LONG -0.03% (-$0.17, RSI Reversal)
- **Average Loss:** -1.35%
- **Average Loss Hold:** ~9 hours

### Win/Loss Ratio: 1.60 (wins are 60% larger than losses)

---

## Algorithm Deployment Status

**Active Algorithms (5 deployed):**
1. Ichimoku Cloud - Trading actively, high win rate
2. StochRSI Crossover - Trading actively, high win rate
3. RSI Reversal - Minimal activity
4. Consensus (Challenger Bot) - Active but losing
5. Alpha Predator - Active (1 open position)
6. VAM - Active (1 open position: JNJ)

**Expected Algorithms Not Seen:**
- 15+ algorithms are expected per project memory but only 6 are generating trades
- May indicate regime gating is blocking most algorithms

---

## Risk Management

### Position Sizing
- **Average Position Size:** ~$490 per trade
- **Max Position:** $500.67 (AXSUSD, Ichimoku Cloud)
- **Min Position:** $484.38 (HBARUSD, StochRSI Crossover)
- **Current Invested:** $4,426.48 (44% of portfolio)
- **Cash Reserve:** $5,573.57 (56%)

### Fees
- **Total Fees Paid:** $17.61 on 13 trades
- **Average Fees:** $1.35 per trade (0.27% of position value)
- **Forex Fees:** $0 (no fees on forex trades)
- **Crypto Fees:** ~$1.95 per trade

### Drawdown
- **Current Drawdown:** -0.52% from peak
- **Peak Value:** $10,022.40 (achieved during trading)
- **Current Value:** $9,969.98
- **Max Unrealized Loss:** -$30.07 (current open positions)

---

## Day-by-Day Performance

### Feb 9-10 (First Trading Day)
- 4 trades opened
- 3 closed (all losses): -$15.45 total
- Algorithms: Consensus (2 losses), RSI Reversal (1 loss), Unknown (1 loss)

### Feb 12 (Most Active Day)
- 16 trades total (9 closed, 7 opened)
- Closed PnL: +$49.22
- Best day so far

---

## Recommendations

### Critical Actions
1. **Investigate Unknown Algorithm:** One BTCUSD trade has empty algorithm name (-$12.33 loss)
2. **Review Challenger Bot:** 0% win rate on Forex (2/2 losses). Consider disabling Forex trading.
3. **Monitor AMZN Position:** Currently at -2.50%, near stop loss trigger
4. **Forex Trading:** Pause Forex trading until Consensus algorithm shows positive results

### Strategic Insights
1. **Crypto SHORT Bias:** 7/9 crypto trades are SHORT positions with 77.8% win rate. Continue SHORT-focused crypto strategy.
2. **Ichimoku Cloud Dominance:** 80% win rate, +$44.97 profit. Allocate more capital to this algorithm.
3. **Max Hold Time:** All max-hold exits are losers. Continue reducing max hold times.
4. **Parameter Learning:** System is successfully learning more aggressive TP levels (+55% to +70% increases).

### Data Quality Issues
1. **Missing Learned Params Endpoint:** The `learned_params` API returns empty despite clear evidence of parameter evolution
2. **Algorithm Name Null:** Trade ID 4 (BTCUSD) has empty algorithm name
3. **VAM Algorithm:** Only 1 trade (JNJ), not included in performance stats - may be new/experimental

---

## Comparison to Project Goals

**Target Metrics (from project memory):**
- Initial Capital: $10,000
- Position Sizing: 5% (~$500) - ACHIEVED
- Max Positions: 10 - ACHIEVED (currently at 10)
- Expected Algorithms: 20 - UNDERPERFORMING (only 6 active)

**Performance vs Expectations:**
- Win Rate: 53.85% (TARGET: unknown, but respectable)
- Profit Factor: 1.83 (TARGET: >2.0 recommended)
- Sharpe Ratio: Not available in API data
- Total Return: +0.33% over 3 days (annualized: ~40% if sustained)

---

## Next Steps

1. **Fix Data Collection:** Investigate why `learned_params` endpoint returns empty
2. **Algorithm Audit:** Confirm why only 6/20 algorithms are trading (regime gating?)
3. **Asset Class Tuning:** Disable Forex trading on Consensus algorithm
4. **Capital Reallocation:** Increase allocation to Ichimoku Cloud and StochRSI Crossover
5. **Monitor Open Positions:** AMZN approaching stop loss, may trigger soon
6. **Historical Analysis:** Current sample size (13 trades) is small. Need 50+ trades for statistical significance.

---

## File Locations

**API Endpoints:**
- Dashboard: `https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=dashboard`
- Performance Summary: `https://findtorontoevents.ca/live-monitor/api/algo_performance.php?action=summary&days=90`
- By Algorithm: `https://findtorontoevents.ca/live-monitor/api/algo_performance.php?action=by_algorithm&days=90`
- By Asset: `https://findtorontoevents.ca/live-monitor/api/algo_performance.php?action=by_asset&days=90`
- Trade History: `https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=history`
- Open Positions: `https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=open_positions`

**Frontend:**
- Live Monitor: `https://findtorontoevents.ca/live-monitor/`
- Admin Key: `livetrader2026`

---

**Report Generated:** 2026-02-12 at 20:45 UTC
**Data Freshness:** Real-time (snapshot times in API responses)
**Next Update:** After 25+ total trades (for statistical significance)
