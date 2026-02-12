# Live Trading Performance Analysis

**Date**: February 12, 2026 (20:34 UTC)
**Data Source**: Production APIs at findtorontoevents.ca
**Period**: 30-day rolling window (with live trading active since Feb 9, 2026)

---

## Data Collection Summary

| # | Endpoint | Status | File |
|---|----------|--------|------|
| 1 | algo_performance summary (30d) | OK | algo_summary.json |
| 2 | algo_performance by_algorithm (30d) | OK | algo_by_algorithm.json |
| 3 | algo_performance by_asset (30d) | OK | algo_by_asset.json |
| 4 | algo_performance trades (200) | OK | closed_trades.json |
| 5 | algo_performance learned_params | OK (empty) | learned_params.json |
| 6 | live_trade history (200) | OK | live_history.json |
| 7 | live_trade dashboard | OK | live_dashboard.json |
| 8 | live_trade positions | OK | open_positions.json |
| 9 | consensus_performance dashboard | **500 Error** | consensus_dashboard.json |
| 10 | daily_picks all | OK | daily_picks.json |
| 11 | advanced_stats leaderboard | **500 Error** | leaderboard.json |
| 12 | advanced_stats algorithm_report | **500 Error** | algo_report.json |

**Note**: 3 endpoints returned HTTP 500. The consensus_performance and advanced_stats APIs on `/fc/portfolio2/` appear to have server-side issues. Analysis below is based on the 9 working endpoints.

---

## Portfolio Overview

| Metric | Value |
|--------|-------|
| Portfolio Value | $9,980.19 (starting $10,000) |
| Cash Available | $5,091.57 |
| Invested Capital | $4,921.59 |
| Open Positions | 10 |
| Unrealized P&L | -$32.97 |
| Realized P&L Today | +$61.36 |
| Cumulative Realized P&L | +$45.58 |
| Peak Value | $10,022.40 |
| Current Drawdown | 0.42% |
| Trading Since | February 9, 2026 (4 days) |

---

## Top 5 Performing Algorithms by Win Rate

| Rank | Algorithm | Win Rate | Trades | Wins | Losses | Avg Return |
|------|-----------|----------|--------|------|--------|------------|
| 1 | **StochRSI Crossover** | **100.0%** | 3 | 3 | 0 | +1.13% |
| 2 | **Ichimoku Cloud** | **80.0%** | 5 | 4 | 1 | +1.85% |
| 3 | -- | -- | -- | -- | -- | -- |
| 4 | Consensus | 0.0% | 2 | 0 | 2 | -0.33% |
| 5 | RSI Reversal | 0.0% | 1 | 0 | 1 | -0.03% |

**Analysis**: Only 4 named algorithms have completed trades so far. StochRSI Crossover has a perfect record (3/3 wins), while Ichimoku Cloud is the volume leader with 5 trades at 80% win rate. The unnamed algorithm (trade #4, BTCUSD) and Consensus both had 0% win rates but with very small sample sizes.

---

## Top 5 by Profit Factor

Profit Factor = Gross Wins / Gross Losses (higher is better; > 1.0 is profitable)

| Rank | Algorithm | Profit Factor | Gross Wins | Gross Losses | Net P&L |
|------|-----------|--------------|------------|--------------|---------|
| 1 | **StochRSI Crossover** | **Infinite** (0 losses) | +$16.39 | $0 | +$16.39 |
| 2 | **Ichimoku Cloud** | **4.57** | +$57.56 | -$12.59 | +$44.97 |
| 3 | **Overall Portfolio** | **2.61** | +$73.95 | -$28.37 | +$45.58 |
| 4 | RSI Reversal | 0.00 | $0 | -$0.17 | -$0.17 |
| 5 | Consensus | 0.00 | $0 | -$3.28 | -$3.28 |

**Analysis**: The portfolio-level profit factor of 2.61 is strong. StochRSI Crossover has infinite PF (no losses), while Ichimoku Cloud's 4.57 PF is excellent. Both losing algorithms (RSI Reversal, Consensus) have had very few trades -- too early to draw conclusions.

---

## Top 5 by Sharpe Ratio (Estimated)

Since we have limited trade history (12 closed trades over 4 days), we compute an approximate Sharpe from per-trade returns.

**Per-trade returns** (sorted):
- StochRSI Crossover: +0.26%, +0.50%, +2.63% -- Mean: +1.13%, StdDev: 1.29%
- Ichimoku Cloud: -2.51%, +1.45%, +2.82%, +3.42%, +4.06% -- Mean: +1.85%, StdDev: 2.55%
- Consensus: -0.47%, -0.19% -- Mean: -0.33%, StdDev: 0.20%
- RSI Reversal: -0.03% -- Mean: -0.03% (1 trade, no variance)

| Rank | Algorithm | Approx Sharpe (per-trade) | Interpretation |
|------|-----------|--------------------------|----------------|
| 1 | **StochRSI Crossover** | **0.87** | Good risk-adjusted returns |
| 2 | **Ichimoku Cloud** | **0.72** | Acceptable, higher variance |
| 3 | **Overall Portfolio** | **0.57** | Positive but dragged by losers |
| 4 | RSI Reversal | N/A (1 trade) | Insufficient data |
| 5 | Consensus | -1.65 | Negative -- consistently losing |

**Note**: True Sharpe requires annualization and risk-free rate. These are approximate per-trade Sharpe ratios for relative ranking only. With only 4 days of data, treat these as directional indicators, not statistically significant measures.

---

## Worst 5 Algorithms (Need Improvement)

| Rank | Algorithm | Issue | Details |
|------|-----------|-------|---------|
| 1 | **Unnamed ("" algo)** | -2.47% on only trade | BTCUSD LONG hit stop_loss. No algorithm name recorded -- data integrity issue. |
| 2 | **Consensus** | 0% win rate (0/2) | Both FOREX trades (USDJPY, GBPUSD) hit max_hold. Avg loss -0.33%. Learned hold of 12h may be too short. |
| 3 | **RSI Reversal** | 0% win rate (0/1) | EURUSD LONG hit max_hold at -0.03%. Learned hold of 6h (vs original 12h) too aggressive. |
| 4 | **Challenger Bot** | No closed trades yet | 4 open STOCK positions (AMZN -2.49%, NVDA -1.79%, GOOGL -0.36%, MSFT +0.05%). All underwater except MSFT. |
| 5 | **Alpha Predator** | No closed trades yet | 1 open position (ATOMUSD -1.22%). Early days but currently losing. |

**Analysis**: The biggest concern is that 3 algorithms that attempted forex trades all lost. The Challenger Bot has 4 stock positions open with a 72-hour max hold window, so the jury is still out, but the aggregate unrealized is -$22.39 across those 4 positions.

---

## Learned vs Original Parameters Comparison

The `learned_params` endpoint returned empty (no stored parameter comparisons), but we can extract learned vs original from the closed trades data:

| Algorithm | Param | Original | Learned | Change | Impact |
|-----------|-------|----------|---------|--------|--------|
| **StochRSI Crossover** | TP | 2% | 3% | +50% | Allowed winners to run further; all 3 trades won |
| **StochRSI Crossover** | SL | 1% | 2% | +100% | Wider stop prevented premature exits |
| **StochRSI Crossover** | Hold | 12h | 12h | No change | -- |
| **Ichimoku Cloud** | TP | 2% | 3.0-3.6% | +50-80% | Higher targets captured larger moves (avg +1.85%) |
| **Ichimoku Cloud** | SL | 1% | 2% | +100% | Wider stop; 1 loss hit SL at -2.51% |
| **Ichimoku Cloud** | Hold | 16h | 16h | No change | -- |
| **Consensus** | TP | 3% | 3% | No change | -- |
| **Consensus** | SL | 2% | 2% | No change | -- |
| **Consensus** | Hold | 24h | 12h | **-50%** | Reduced hold caused max_hold exits before targets |
| **RSI Reversal** | TP | 2% | 2% | No change | -- |
| **RSI Reversal** | SL | 1% | 1% | No change | -- |
| **RSI Reversal** | Hold | 12h | 6h | **-50%** | Too aggressive; exited at max_hold before TP/SL |

### Which Algos Improved Most from Learning

1. **StochRSI Crossover** -- Learned parameters (wider TP 3%, wider SL 2%) produced 100% win rate vs the original tighter parameters. The wider TP allowed trailing stops and take profits to capture 0.26% to 2.63% gains. This is the **best improvement from parameter learning**.

2. **Ichimoku Cloud** -- Learned TP of 3.0-3.6% (vs original 2%) captured substantially larger moves. 4 of 5 trades won with average +1.85% return. The wider SL of 2% gave positions room to breathe. **Second-best improvement**.

3. **Consensus** -- Learning **hurt performance**. Reducing max hold from 24h to 12h caused both trades to exit at max_hold with small losses. The original 24h hold would have given more time for the positions to recover.

4. **RSI Reversal** -- Learning **hurt performance**. Reducing hold from 12h to 6h caused max_hold exit before the position had a chance to move. The original parameters would have been better.

---

## Asset Class Performance Comparison: Stock vs Crypto vs Forex

### Closed Trades by Asset Class

| Asset Class | Trades | Wins | Win Rate | Avg Return | Total P&L | Best Trade | Worst Trade |
|-------------|--------|------|----------|------------|-----------|------------|-------------|
| **CRYPTO** | 8 | 7 | **87.5%** | +1.58% | +$60.37 | +4.06% (UNIUSD) | -2.51% (AXSUSD) |
| **FOREX** | 3 | 0 | **0.0%** | -0.23% | -$3.45 | -0.03% (EURUSD) | -0.47% (USDJPY) |
| **STOCK** | 1 | 0 | **0.0%** | -2.47% | -$12.33 | -- | -2.47% (BTCUSD*) |

*Note: The BTCUSD trade (#4) is classified as CRYPTO in the live_history but logged as a stock trade entry with no algorithm name. This is likely a data recording issue.

### Open Positions by Asset Class

| Asset Class | Positions | Invested | Unrealized P&L | Avg Unrealized % |
|-------------|-----------|----------|-----------------|------------------|
| **CRYPTO** | 5 | ~$2,484 | -$11.53 | -0.47% |
| **STOCK** | 5 | ~$2,443 | -$21.44 | -0.88% |
| **FOREX** | 0 | $0 | -- | -- |

### Key Findings by Asset Class

**CRYPTO (Best Performer)**:
- Dominates with 87.5% win rate on closed trades
- All 7 wins were SHORT positions on altcoins (SHIB, BCH, UNI, HBAR, AXS, ARB)
- Currently bearish crypto market is ideal for the SHORT bias
- Average hold time: 8.1 hours -- well-suited for intraday crypto volatility
- Algorithms StochRSI Crossover and Ichimoku Cloud are particularly effective on crypto

**FOREX (Worst Performer)**:
- 0% win rate across 3 trades (all LONG positions)
- All 3 exited via max_hold -- positions never reached TP or SL targets
- Average loss small (-0.23%) suggesting low volatility / ranging conditions
- FOREX may need different parameters: wider hold periods, or avoid during low-vol conditions
- No new FOREX positions currently open

**STOCKS (Insufficient Data on Closed, Mixed on Open)**:
- Only 1 closed trade (unnamed algo, BTCUSD logged as stock -- likely error)
- 5 open positions via Challenger Bot + VAM, all LONG
- Challenger Bot positions (AMZN, NVDA, GOOGL, MSFT) have 72h max hold, so more time needed
- VAM just opened JNJ, currently +0.20%

---

## Detailed Trade Log (All 12 Closed Trades)

| # | Symbol | Algo | Direction | Entry | Exit | P&L % | P&L $ | Exit Reason | Hold |
|---|--------|------|-----------|-------|------|-------|-------|-------------|------|
| 1 | UNIUSD | Ichimoku | SHORT | $3.351 | $3.202 | **+4.06%** | +$20.00 | take_profit | 3.3h |
| 2 | AXSUSD | Ichimoku | SHORT | $1.470 | $1.414 | **+3.42%** | +$16.69 | take_profit | 7.5h |
| 3 | BCHUSD | Ichimoku | SHORT | $511.00 | $494.60 | **+2.82%** | +$13.77 | take_profit | 11.9h |
| 4 | HBARUSD | StochRSI | SHORT | $0.0957 | $0.0928 | **+2.63%** | +$12.72 | take_profit | 4.6h |
| 5 | UNIUSD | Ichimoku | SHORT | $3.464 | $3.400 | **+1.45%** | +$7.10 | trailing_stop | 8.6h |
| 6 | ARBUSD | StochRSI | SHORT | $0.112 | $0.111 | **+0.50%** | +$2.41 | trailing_stop | 7.2h |
| 7 | SHIBUSD | StochRSI | SHORT | $6.08e-6 | $6.04e-6 | **+0.26%** | +$1.26 | trailing_stop | 12.0h |
| 8 | EURUSD | RSI Rev. | LONG | $1.1913 | $1.1909 | -0.03% | -$0.17 | max_hold | 7.0h |
| 9 | GBPUSD | Consensus | LONG | $1.3693 | $1.3667 | -0.19% | -$0.95 | max_hold | 12.2h |
| 10 | USDJPY | Consensus | LONG | $155.86 | $155.14 | -0.47% | -$2.33 | max_hold | 12.4h |
| 11 | BTCUSD | (unnamed) | LONG | $70,460 | $69,001 | -2.47% | -$12.33 | stop_loss | 9.3h |
| 12 | AXSUSD | Ichimoku | SHORT | $1.374 | $1.403 | -2.51% | -$12.59 | stop_loss | 2.5h |

---

## Signal Generation Volume

| Source | Signals (30d) |
|--------|---------------|
| Learned Parameters | 2,479 |
| Original Parameters | 500 |
| Untagged | 0 |
| **Total** | **2,979** |

The system is generating ~100 signals/day. With only 12 executed trades, the signal-to-trade conversion rate is approximately 0.4%, suggesting very aggressive filtering or position limits are in effect.

---

## Key Improvement Recommendations

### 1. Fix FOREX Strategy (Critical)
- **Problem**: 0% win rate across all 3 FOREX trades. All hit max_hold.
- **Root Cause**: Consensus algo learned hold reduced from 24h to 12h, but FOREX needs longer hold periods due to lower volatility. RSI Reversal learned hold reduced from 12h to 6h, also too aggressive.
- **Recommendation**: Revert FOREX hold parameters to originals (24h for Consensus, 12h for RSI Reversal), or increase them further. Consider adding volatility-based dynamic hold periods for FOREX.

### 2. Fix Unnamed Algorithm Data Issue (High)
- **Problem**: Trade #4 (BTCUSD) has an empty algorithm name and signal_id=0.
- **Root Cause**: Likely a manual test trade or a signal that bypassed the algorithm tagging system.
- **Recommendation**: Add validation in `live_trade.php` to reject trades with empty algorithm names. Investigate if this was a one-time issue or systematic.

### 3. Expand Crypto SHORT Strategy (Medium)
- **Problem**: 87.5% win rate on crypto SHORTs is excellent but the system only trades ~8 crypto positions per day.
- **Recommendation**: Increase position limits for crypto or reduce the signal filtering threshold for StochRSI Crossover and Ichimoku Cloud on crypto assets. The current bearish market is favorable for SHORT strategies.

### 4. Monitor Challenger Bot Stock Positions (Medium)
- **Problem**: 4 LONG stock positions are collectively underwater (-$22.39 unrealized).
- **Context**: These have 72h max hold, so only ~17h into the trade. Still within normal parameters.
- **Recommendation**: No immediate action needed. Monitor whether these recover before the 72h window. If the 72h window consistently results in max_hold exits, consider adjusting.

### 5. Populate Learned Parameters Table (Low)
- **Problem**: The `learned_params` endpoint returns empty, even though trades clearly use learned parameters.
- **Root Cause**: The algo_performance system stores learned params per-trade but may not aggregate them into the learned_params action response.
- **Recommendation**: Fix the `learned_params` action in `algo_performance.php` to return the aggregated learned parameter sets from closed trade data.

### 6. Fix 500 Errors on Advanced Stats APIs (High)
- **Problem**: 3 endpoints returning HTTP 500:
  - `consensus_performance.php?action=dashboard`
  - `advanced_stats.php?action=leaderboard`
  - `advanced_stats.php?action=algorithm_report`
- **Recommendation**: Check server error logs for these endpoints. Likely a PHP syntax error or database connection issue in the `/fc/portfolio2/api/` path.

### 7. Improve Risk Management for Learning (Medium)
- **Problem**: The learning system correctly widened TP/SL for crypto (beneficial) but incorrectly shortened hold times for FOREX (harmful).
- **Recommendation**: Add asset-class-specific floors for hold periods. FOREX minimum hold should be 12h. Crypto can stay at current learned values. Consider separate learning pools per asset class.

### 8. Add More Algorithm Coverage (Low)
- **Problem**: Only 4 named algorithms have generated closed trades. The system has 20 algorithms, but 16 haven't produced closed positions yet.
- **Context**: System just launched Feb 9, 2026 (4 days ago). Challenger Bot, VAM, and Alpha Predator have open positions.
- **Recommendation**: Monitor over the next 1-2 weeks. If algorithms like MACD Divergence, Bollinger Bounce, VWAP, etc. aren't generating signals, investigate their regime gates.

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Closed Trades | 12 |
| Win Rate | 58.3% (7W / 5L) |
| Profit Factor | 2.61 |
| Total Realized P&L | +$45.58 |
| Average Win | +2.16% (+$10.56) |
| Average Loss | -1.13% (-$5.67) |
| Best Trade | UNIUSD SHORT +4.06% (+$20.00) |
| Worst Trade | AXSUSD SHORT -2.51% (-$12.59) |
| Average Hold Time | 8.2 hours |
| Win/Loss Ratio (avg $) | 1.86:1 |
| Signal Generation Rate | ~100/day |
| Trade Execution Rate | ~3/day |
| Portfolio Return (4 days) | -0.20% (unrealized drag) |
| Realized-only Return | +0.46% |

**Overall Assessment**: The live trading system is net profitable after 4 days of operation. Crypto SHORT strategies are the clear winners. FOREX is the weakest link. The learning system has been beneficial for crypto parameters but harmful for FOREX hold times. The portfolio is well-managed with appropriate position sizing (~$500/trade, 5% of capital). Drawdown is minimal at 0.42%. The system needs more time to generate statistically significant results, but early signs are promising for crypto-focused strategies.

---

*Analysis generated February 12, 2026. Data collected from production APIs.*
