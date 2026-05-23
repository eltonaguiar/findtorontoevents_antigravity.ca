# Prop Firm Classic Strategies + Justin's Methods + System Improvements

**Date:** 2026-03-07
**Status:** Design

## Context

### Current Performance (March 7, 2026)
- 33 systems tracked, 5,621 closed picks, **45% overall WR, PF 0.93** (marginally underwater)
- **Winners:** battleground (60.1% WR, +4015%), kimi_tracking (64% WR, +268%), claude_gainer (56.2% WR)
- **Failures identified:** funding_rate_carry (-181% from ROBOUSDT blowup), baby_strats_forward (42.3% WR, -5349%), alpha_engine (35.4% WR), KIMI (25.8% closed WR)
- **Broken workflow:** ANTIGRAVITY-CLAUDEOPUS (fixed: fear_greed float→dict check)

### Justin's Trading Advice (Expert Prop Firm Trader)
Justin uses 4 core indicators from ChartPrime/J Bravo, trades 5m/15m (tournament) and 1h/4h:
1. **EMA9 candle close crossover** — short when close < EMA9, buy when close > EMA9, hold until signal reverses
2. **RSI on 1h/4h** — higher-timeframe RSI as directional bias filter
3. **Pattern recognition** — double tops, pattern breaks, tweezer bottoms

## New Strategies (8 total)

### Battle-Tested Classics (5)

#### 1. Opening Range Breakout (ORB)
- **Edge:** First 1h after 00:00 UTC defines session range; trade breakout
- **Entry:** Price breaks above range high (BUY) or below range low (SELL) with volume > 1.2x
- **TP/SL:** TP = 1.5x range height, SL = opposite side of range. Min 2:1 R:R
- **Timeframe:** 15m candles, first 4 candles = range (1h window)
- **Max hold:** 16 bars (4h)
- **Expected WR:** 55-65% (documented 60-81% on futures)
- **Symbols:** Top 10 crypto by volume

#### 2. Turtle/Donchian Channel Breakout
- **Edge:** Richard Dennis classic — 20-bar high/low channel breakout
- **Entry:** Close above 20-bar high (BUY) or below 20-bar low (SELL)
- **Exit:** Trailing stop at 10-bar low (longs) or 10-bar high (shorts)
- **Filter:** EMA 8/21/50 must be stacked in trend direction
- **Timeframe:** 1h candles
- **Position sizing:** ATR-based, reduce 50% when ATR > 1.5x average
- **Expected WR:** 40-45% but PF 1.5-2.0 (big winners compensate)
- **Annual returns:** Up to 62.71% on crypto (Gate Research)

#### 3. Inside Bar Breakout
- **Edge:** Consolidation → expansion. Mother bar fully contains child bar
- **Entry:** Break of inside bar high (BUY) or low (SELL) with volume confirmation
- **TP/SL:** TP = 2x inside bar range, SL = opposite side of inside bar
- **Filter:** EMA20 trend direction must align with breakout
- **Timeframe:** 1h candles
- **Expected WR:** 60-75% with trend filter

#### 4. VWAP Mean Reversion
- **Edge:** Price deviates > 2 std dev from VWAP → snaps back
- **Entry:** Touch VWAP lower band (BUY) or upper band (SELL), volume spike confirms
- **TP:** VWAP mean (the center line)
- **SL:** 1.0 ATR beyond entry
- **Timeframe:** 15m candles (intraday)
- **Max hold:** 8 bars (2h)
- **Expected WR:** ~50% but strong PF (1.69 documented)

#### 5. Session Momentum (London/NY Overlap)
- **Edge:** 14:00-20:00 UTC = highest crypto volume window (US market overlap)
- **Entry:** EMA9 > EMA21 + volume > 1.5x avg + RSI 40-70, during session window only
- **TP/SL:** 2x ATR TP, 1x ATR SL
- **Timeframe:** 15m candles
- **Max hold:** 12 bars (3h, must exit by session end)
- **Expected WR:** 55-62% (our own London breakout research: 62%)

### Justin's Methods (3)

#### 6. EMA9 Close Crossover (Justin's Primary)
- **Edge:** Simple trend-following on candle close vs EMA9 — Justin's actual method
- **Entry:** Candle closes above EMA9 → BUY. Candle closes below EMA9 → SELL
- **Exit:** Reverse signal (close crosses back)
- **Filter:** Only trade when EMA9 slope > 5 degrees (avoid chop)
- **Timeframes:** Run on both 15m and 1h (Justin uses 5m/15m for tournament, 1h/4h for daily)
- **Position sizing:** 2% risk per trade
- **Expected WR:** 45-55% (trend-following, wins via R:R not WR)

#### 7. RSI Multi-Timeframe Bias (Justin's Directional Filter)
- **Edge:** Use 1h and 4h RSI to determine directional bias, only trade in that direction on lower TF
- **Entry:** 4h RSI < 40 → only SHORT on 15m. 4h RSI > 60 → only LONG on 15m. Combined with EMA9 close signal.
- **TP/SL:** 2x ATR TP, 1.5x ATR SL
- **Timeframe:** Signal on 15m, bias from 1h/4h
- **Expected WR:** 55-65% (HTF alignment dramatically improves LTF signals)

#### 8. Double Top/Tweezer Pattern Scanner (Justin's Pattern Recognition)
- **Edge:** Classic reversal patterns — double top/bottom, tweezer top/bottom
- **Double top:** Two peaks within 0.5% of each other, neckline break confirms
- **Tweezer:** Two consecutive candles with matching highs (top) or lows (bottom), wick > 40% of bar
- **Entry:** Break of neckline (double top/bottom) or next candle confirmation (tweezer)
- **TP/SL:** TP = pattern height projected, SL = above/below pattern extreme
- **Timeframe:** 1h candles
- **Expected WR:** 55-65% (well-documented reversal patterns)

## System Improvements (Built Into All New Strategies)

### 1. Liquidity Filter (Prevents ROBOUSDT-type Blowups)
```python
MIN_MARKET_CAP = 100_000_000  # $100M minimum
MIN_24H_VOLUME = 5_000_000    # $5M daily volume
```
All strategies skip symbols below these thresholds.

### 2. Auto-Disable Losers
Any strategy with 0% WR after 5+ trades gets auto-disabled in forward testing.

### 3. Wider Crypto Stops (Default)
All new strategies use minimum 1.5x ATR SL (current KIMI uses 1x → 58% SL hit rate).

### 4. Portfolio Circuit Breaker
-5% daily realized loss → halt all new entries for 24 hours.

### 5. Walk-Forward Validation Gate
Nothing goes to paper trading without passing quan_engine anti-overfit checks.

## Architecture

### Files to Create
1. `baby_strategies/prop_firm_classics.py` — 8 strategy classes with shared indicator lib
2. `paper_trading/strategies/prop_firm_classics_pt.py` — Paper trading wrappers
3. `backtest_prop_firm_classics.py` — Multi-symbol backtest runner

### Files to Modify
1. `paper_trading/strategies/__init__.py` — Register 8 new strategies
2. `.github/workflows/baby-strat-forward-paper.yml` — Add path triggers
3. `ml_crypto_predictor/enhanced_models/live_picks_tracker.py` — Already fixed (fear_greed bug)

### Shared Infrastructure
- Reuse `IndicatorCache` pattern from `backtest_hoffman_combos.py`
- Reuse `Signal` dataclass and `simulate_trades()` from existing backtester
- All strategies implement `generate_signals(df, symbol) -> List[Signal]`

## Prop Firm Compliance (All Strategies)

| Rule | Value |
|---|---|
| Max risk per trade | 2% of equity |
| Minimum R:R | 2:1 |
| Max daily drawdown | 5% (circuit breaker) |
| Max total drawdown | 10% |
| Max hold time | Strategy-specific (2h-48h) |
| Liquidity minimum | $100M mcap, $5M daily vol |
| Stop loss minimum | 1.5x ATR |

## Success Criteria

| Metric | Target | Stretch |
|---|---|---|
| Win Rate (avg across 8) | > 50% | > 55% |
| Profit Factor | > 1.3 | > 1.8 |
| Max Drawdown | < 10% | < 7% |
| Sharpe Ratio | > 1.5 | > 2.5 |
| Min trades per strategy (backtest) | 50 | 100 |

## Backtest Plan

1. Test all 8 strategies across 10 symbols × 1000 bars (15m)
2. Run on 3 independent time periods (recent, 2w ago, 1m ago)
3. Require profitable in ≥ 2 of 3 periods to be promoted
4. Document max DD% and avg PnL% for each (per user request)
