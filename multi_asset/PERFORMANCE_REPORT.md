# Multi-Asset Forward-Test Portfolio Performance Report

**Generated:** 2026-03-11 18:20 UTC

---

## 1. Portfolio Summary

| Metric | Value |
|--------|-------|
| Total Picks | 55 |
| Active (Open) | 27 |
| Closed | 28 |
| Wins / Losses | 4 / 24 |
| Win Rate (closed) | **14.3%** |
| Avg PnL (closed) | -0.9218% |
| Total PnL (all) | -27.9278% |
| Sharpe Ratio | -0.7797 |
| Sortino Ratio | -0.5704 |
| Profit Factor | 0.0537 |
| Active (awaiting price) | 6 |

## 2. CRITICAL ISSUES

### Win Rate: 14.3% (Target: >50%)

The portfolio launched during a severe market selloff (VIX spiked 39.4%) and immediately
suffered from over-concentration in the `vix_reversal` strategy, which dominated 49% of
all picks with a disastrous 14.8% win rate. The strategy has been **DISABLED** as of March 11.

**Key problems identified:**
- `vix_reversal` fired on every asset simultaneously during the VIX spike, creating massive correlated exposure
- No strategy diversification cap existed -- one strategy could dominate the entire portfolio
- No bounce/mean-reversion strategy was available to capitalize on oversold conditions
- Trend filter (SMA200) blocked entries for legitimate dip-buying opportunities

## 3. Performance by Strategy

| Strategy | Picks | Open | Closed | Wins | Win Rate | Avg PnL% | Sharpe | Status |
|----------|-------|------|--------|------|----------|----------|--------|--------|
| connors_rsi2 | 8 | 8 | 0 | 0 | 0.0% | -0.0844% | -0.236 | **ACTIVE** |
| ema_stack_momentum | 6 | 5 | 1 | 0 | 0.0% | -0.0339% | -0.137 | **ACTIVE** |
| extreme_oversold_bounce | 8 | 8 | 0 | 0 | 0.0% | 0.0332% | 0.854 | **ACTIVE** |
| hyperopt_connors_rsi2 | 2 | 2 | 0 | 0 | 0.0% | 0.0242% | 16.238 | **ACTIVE** |
| macd_divergence | 4 | 4 | 0 | 0 | 0.0% | -0.3386% | -1.153 | **ACTIVE** |
| vix_reversal | 27 | 0 | 27 | 4 | 14.8% | -0.9559% | -0.803 | **DISABLED** |

## 4. Performance by Asset Class

| Asset Class | Picks | Open | Closed | Wins | Win Rate | Avg PnL% | Total PnL% |
|-------------|-------|------|--------|------|----------|----------|------------|
| ETF | 16 | 10 | 6 | 1 | 16.7% | -0.2571% | -3.8562% |
| Forex | 8 | 8 | 0 | 0 | 0.0% | -0.1731% | -1.2115% |
| Futures | 13 | 6 | 7 | 0 | 0.0% | -1.3074% | -14.3818% |
| Penny | 1 | 1 | 0 | 0 | 0.0% | 0.2488% | 0.2488% |
| Stock | 17 | 2 | 15 | 3 | 20.0% | -0.5818% | -8.7271% |

## 5. Active Picks (27 open)

| Symbol | Strategy | Class | Dir | Entry | Current | TP | SL | Conf | PnL% |
|--------|----------|-------|-----|-------|---------|----|----|------|------|
| USDJPY=X | connors_rsi2 | Forex | LONG | 157.9110 | 158.9030 | 162.6483 | 153.9632 | 70% | +0.6282% |
| SOFI | ema_stack_momentum | Penny | SHORT | 18.2900 | 18.2445 | 13.7175 | 21.8633 | 76% | +0.2488% |
| CL=F | ema_stack_momentum | Futures | LONG | 87.6400 | 87.7600 | 94.6512 | 68.0569 | 85% | +0.1369% |
| AUDUSD=X | macd_divergence | Forex | LONG | 0.7140 | 0.7146 | 0.7355 | 0.6962 | 65% | +0.0786% |
| TLT | connors_rsi2 | ETF | LONG | 87.2600 | 87.3250 | 95.9860 | 82.8970 | 95% | +0.0745% |
| XLF | extreme_oversold_bounce | ETF | LONG | 49.4150 | 49.4450 | 51.1445 | 48.4267 | 90% | +0.0607% |
| SPY | hyperopt_connors_rsi2 | ETF | LONG | 674.1500 | 674.3200 | 741.5650 | 640.4425 | 95% | +0.0252% |
| QQQ | hyperopt_connors_rsi2 | ETF | LONG | 605.8600 | 606.0000 | 666.4460 | 575.5670 | 95% | +0.0231% |
| TLT | extreme_oversold_bounce | ETF | LONG | 87.3200 | 87.3250 | 89.1392 | 85.5736 | 90% | +0.0057% |
| USDJPY=X | ema_stack_momentum | Forex | LONG | 158.9250 | 158.9030 | 163.6928 | 155.9724 | 71% | -0.0138% |
| IWM | connors_rsi2 | ETF | LONG | 251.6000 | 251.4500 | 276.7600 | 239.0200 | 95% | -0.0596% |
| NQ=F | connors_rsi2 | Futures | LONG | 24961.7500 | 24944.5000 | 26958.6900 | 23963.2800 | 95% | -0.0691% |
| XLE | ema_stack_momentum | ETF | LONG | 56.6850 | 56.6261 | 62.3535 | 52.2100 | 73% | -0.1039% |
| SPY | connors_rsi2 | ETF | LONG | 675.1900 | 674.3200 | 742.7090 | 641.4305 | 95% | -0.1289% |
| QQQ | connors_rsi2 | ETF | LONG | 607.1300 | 606.0000 | 667.8430 | 576.7735 | 91% | -0.1861% |
| ES=F | connors_rsi2 | Futures | LONG | 6786.0000 | 6766.0000 | 7328.8800 | 6514.5600 | 95% | -0.2947% |
| GBPUSD=X | macd_divergence | Forex | LONG | 1.3454 | 1.3407 | 1.3857 | 1.3117 | 65% | -0.3446% |
| AUDUSD=X | ema_stack_momentum | Forex | LONG | 0.7180 | 0.7146 | 0.7395 | 0.6948 | 68% | -0.4716% |
| EURUSD=X | macd_divergence | Forex | LONG | 1.1636 | 1.1574 | 1.1985 | 1.1345 | 65% | -0.5324% |
| NZDUSD=X | macd_divergence | Forex | LONG | 0.5947 | 0.5914 | 0.6125 | 0.5798 | 65% | -0.5559% |
| YM=F | connors_rsi2 | Futures | LONG | 47687.0000 | 47382.0000 | 51501.9600 | 45779.5200 | 95% | -0.6396% |
| ES=F | extreme_oversold_bounce | Futures | LONG | 6766.0000 | N/A | 6863.1625 | 6630.6800 | 87% | awaiting price |
| YM=F | extreme_oversold_bounce | Futures | LONG | 47382.0000 | N/A | 48803.4600 | 46434.3600 | 87% | awaiting price |
| JPM | extreme_oversold_bounce | Stock | LONG | 286.4850 | N/A | 297.9444 | 279.3229 | 85% | awaiting price |
| V | extreme_oversold_bounce | Stock | LONG | 308.7200 | N/A | 317.4420 | 301.0020 | 82% | awaiting price |
| USDCAD=X | extreme_oversold_bounce | Forex | LONG | 1.3586 | N/A | 1.3648 | 1.3383 | 89% | awaiting price |
| IWM | extreme_oversold_bounce | ETF | LONG | 251.4500 | N/A | 260.2507 | 246.4210 | 88% | awaiting price |

## 6. Closed Picks (28 closed)

| Symbol | Strategy | Class | Dir | Entry | Close | PnL% | Close Reason |
|--------|----------|-------|-----|-------|-------|------|--------------|
| TSLA | vix_reversal | Stock | LONG | 399.2400 | 403.9850 | +1.1885% | Strategy disabled - no hyperopt backing |
| GOOGL | vix_reversal | Stock | LONG | 307.0400 | 307.7600 | +0.2345% | Strategy disabled - no hyperopt backing |
| XLK | vix_reversal | ETF | LONG | 139.7600 | 139.8000 | +0.0286% | Strategy disabled - no hyperopt backing |
| NVDA | vix_reversal | Stock | LONG | 184.7700 | 184.7951 | +0.0136% | Strategy disabled - no hyperopt backing |
| TLT | ema_stack_momentum | ETF | LONG | 88.2800 | 88.3956 | +0.0000% | STOP_LOSS |
| AAPL | vix_reversal | Stock | LONG | 260.8300 | 260.3550 | -0.1821% | Strategy underperforming - removed from portfolio |
| META | vix_reversal | Stock | LONG | 654.0700 | 651.9900 | -0.3180% | Strategy underperforming - removed from portfolio |
| ZN=F | vix_reversal | Futures | LONG | 112.3906 | 111.9844 | -0.3615% | Strategy disabled - no hyperopt backing |
| ZN=F | vix_reversal | Futures | LONG | 112.3906 | 111.9688 | -0.3754% | Strategy underperforming - removed from portfolio |
| AAPL | vix_reversal | Stock | LONG | 260.8300 | 259.8278 | -0.3842% | Strategy disabled - no hyperopt backing |
| META | vix_reversal | Stock | LONG | 654.0700 | 651.1100 | -0.4526% | Strategy disabled - no hyperopt backing |
| GLD | vix_reversal | ETF | LONG | 477.8600 | 475.2550 | -0.5451% | Strategy disabled - no hyperopt backing |
| MSFT | vix_reversal | Stock | LONG | 405.7600 | 403.4600 | -0.5668% | Strategy underperforming - removed from portfolio |
| GLD | vix_reversal | ETF | LONG | 477.8600 | 475.1200 | -0.5734% | Strategy underperforming - removed from portfolio |
| GC=F | vix_reversal | Futures | LONG | 5213.5000 | 5178.0000 | -0.6809% | Strategy disabled - no hyperopt backing |
| MSFT | vix_reversal | Stock | LONG | 405.7600 | 402.9649 | -0.6889% | Strategy disabled - no hyperopt backing |
| GC=F | vix_reversal | Futures | LONG | 5213.5000 | 5174.5000 | -0.7481% | Strategy underperforming - removed from portfolio |
| JPM | vix_reversal | Stock | LONG | 288.7300 | 286.4400 | -0.7931% | Strategy underperforming - removed from portfolio |
| JPM | vix_reversal | Stock | LONG | 288.7300 | 285.9500 | -0.9628% | Strategy disabled - no hyperopt backing |
| AMZN | vix_reversal | Stock | LONG | 214.3300 | 212.1490 | -1.0176% | Strategy underperforming - removed from portfolio |
| XLF | vix_reversal | ETF | LONG | 50.0600 | 49.4700 | -1.1786% | Strategy underperforming - removed from portfolio |
| AMZN | vix_reversal | Stock | LONG | 214.3300 | 211.7500 | -1.2038% | Strategy disabled - no hyperopt backing |
| XLF | vix_reversal | ETF | LONG | 50.0600 | 49.4100 | -1.2984% | Strategy disabled - no hyperopt backing |
| V | vix_reversal | Stock | LONG | 314.4300 | 309.0100 | -1.7237% | Strategy underperforming - removed from portfolio |
| V | vix_reversal | Stock | LONG | 314.4300 | 308.5500 | -1.8701% | Strategy disabled - no hyperopt backing |
| SI=F | vix_reversal | Futures | LONG | 88.5950 | 85.5250 | -3.4652% | Strategy disabled - no hyperopt backing |
| SI=F | vix_reversal | Futures | LONG | 88.5950 | 85.3700 | -3.6402% | Strategy underperforming - removed from portfolio |
| SI=F | vix_reversal | Futures | LONG | 88.5950 | 85.0512 | -4.2440% | STOP_LOSS |

## 7. Root Cause Analysis

### Why performance is poor

1. **`vix_reversal` dominated 49% of all picks (27/55) with 14.8% win rate.**
   The strategy fired on every available asset simultaneously during a single VIX spike event,
   creating 27 correlated LONG positions that all moved against the portfolio. Only
   4/27 closed trades were profitable.

2. **Trend filter blocked dip-buying entries.**
   The SMA(200) trend filter, while designed to avoid buying into downtrends, prevented
   legitimate mean-reversion entries during the selloff. Assets that briefly dipped below
   their 200-day SMA could not be bought even at extreme oversold conditions.

3. **No bounce/mean-reversion strategy existed.**
   The initial strategy set lacked a dedicated extreme-oversold bounce strategy. The
   `connors_rsi2` strategy existed but its SMA(200) requirement was too strict for crash
   conditions. A new `extreme_oversold_bounce` strategy has since been added.

4. **Over-concentration in a single strategy.**
   No cap existed on how many picks a single strategy could generate. `vix_reversal`
   produced 27 picks in one scan cycle, dwarfing all other strategies combined.
   A concentration cap of 30% per strategy has been deployed.

## 8. Fixes Deployed (March 11, 2026)

| # | Fix | Impact |
|---|-----|--------|
| 1 | **Disabled `vix_reversal` strategy** | Eliminates 49% of picks with 14.8% WR; all open vix_reversal positions closed |
| 2 | **Added hyperopt-tuned `bollinger_mr`** | Backtested 73-92% WR across SPY, QQQ, GLD, AMZN, NZDUSD |
| 3 | **Added hyperopt-tuned `connors_rsi2`** | Backtested 67-92% WR; relaxed SMA filter to SMA(150) |
| 4 | **Added hyperopt-tuned `macd_div`** | Backtested 67-83% WR across forex and equity |
| 5 | **Added `extreme_oversold_bounce`** | RSI(2)<5 + price<BB_lower; 3-day max hold; targets quick 1.5-3.5% mean reversion |
| 6 | **Expanded forex pairs** | Added USDCAD, USDCHF, EURJPY to diversify asset class exposure |
| 7 | **Relaxed dedup to 2 strategies/symbol** | Allows connors_rsi2 AND extreme_oversold_bounce on same symbol |
| 8 | **Strategy concentration cap (30%)** | No single strategy can exceed 30% of active portfolio |

## 9. Hyperopt-Proven Strategies (Top Performers)

These strategies were optimized via hyperparameter optimization (hyperopt) on historical data:

| Symbol | Strategy | Backtest WR | Key Parameters | Notes |
|--------|----------|-------------|----------------|-------|
| GLD | connors_rsi2 | **92.0%** | RSI(2)<20, SMA(100) | Gold mean-reversion |
| AMZN | bollinger_mr | **92.3%** | BB(15,1.8), RSI<35 | High-beta bounce |
| NZDUSD | bollinger_mr | **88.2%** | BB(20,2.0), RSI<30 | Forex mean-reversion |
| SPY | connors_rsi2 | **86.7%** | RSI(2)<15, SMA(150) | Index dip-buy |
| QQQ | connors_rsi2 | **83.3%** | RSI(2)<15, SMA(150) | Tech index dip-buy |
| EURUSD | macd_div | **83.3%** | MACD(12,26,9), RSI<40 | Forex divergence |
| SPY | bollinger_mr | **80.0%** | BB(20,1.5), RSI<25 | Tight Bollinger bounce |
| GBPUSD | macd_div | **77.8%** | MACD(12,26,9), RSI<45 | Cable divergence |
| QQQ | bollinger_mr | **76.9%** | BB(15,2.0), RSI<30 | Tech bounce |
| USDJPY | connors_rsi2 | **73.3%** | RSI(2)<10, SMA(200) | Yen carry pullback |
| IWM | bollinger_mr | **73.1%** | BB(20,2.2), RSI<35 | Small-cap bounce |
| AUDUSD | connors_rsi2 | **67.0%** | RSI(2)<10, SMA(100) | AUD dip-buy |

## 10. Questions for External Review

1. **Regime Filter:** Should we add a market regime classifier (bull/bear/chop) that adjusts
   position sizing and strategy activation based on VIX levels, breadth, and trend?

2. **TP/SL Ratios:** Current risk-reward ratios range from 0.3x to 2.0x. Should we enforce a
   minimum 1.5x R:R across all strategies, or does the high win rate of mean-reversion
   strategies justify tighter targets?

3. **Short-Side Strategies:** Only `ema_stack_momentum` generates SHORT signals (1 pick: SOFI).
   Should we add dedicated short strategies (e.g., RSI overbought fade, breakdown short)
   to hedge long exposure during selloffs?

4. **Hold Time Management:** `extreme_oversold_bounce` has a 3-day max hold. Should other
   strategies have maximum hold times? Current `connors_rsi2` and `macd_divergence`
   picks have no exit timer.

5. **Position Sizing:** All picks are currently equal-weighted. Should we implement
   confidence-weighted sizing (e.g., 95% confidence = full size, 65% = half size)?

6. **Asset Class Caps:** Should we cap exposure per asset class (e.g., max 40% in ETFs,
   max 30% in futures) to prevent concentration risk similar to the vix_reversal blowup?

7. **Trailing Stops:** Should profitable positions use trailing stops (e.g., 2x ATR trail)
   instead of fixed TP targets to let winners run?

8. **Overfitting Risk:** Hyperopt strategies show 67-92% backtest WR. What is the expected
   degradation in live trading? Should we apply a haircut (e.g., expect 60-75% live WR)
   and size accordingly?

9. **Crypto Integration:** The multi-asset scanner currently covers futures, stocks, forex,
   ETFs, and penny stocks. Should we integrate crypto pairs (BTC, ETH, SOL) from the
   existing alpha_engine/KIMI systems to further diversify?

10. **Sample Size:** With only 28 closed trades, statistical significance is limited.
    How many closed trades do we need before making further strategy changes? (Suggestion:
    minimum 50 closed trades per strategy before declaring it proven or disabling it.)

---

*Report generated automatically by `multi_asset/gen_report.py`*