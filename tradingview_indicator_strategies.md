# TradingView Built-In Indicator Strategies - Comprehensive Research

## Executive Summary

This document presents 40+ technical indicator-based strategies derived from TradingView's built-in indicator library. The strategies are organized by indicator category and include detailed entry/exit conditions, timeframes, asset classes, and rationale.

---

## Table of Contents

1. [Moving Average Strategies](#1-moving-average-strategies)
2. [Oscillator Strategies](#2-oscillator-strategies)
3. [Volatility Indicator Strategies](#3-volatility-indicator-strategies)
4. [Volume Indicator Strategies](#4-volume-indicator-strategies)
5. [Trend Indicator Strategies](#5-trend-indicator-strategies)
6. [Momentum Indicator Strategies](#6-momentum-indicator-strategies)
7. [Multi-Indicator Confirmation Systems](#7-multi-indicator-confirmation-systems)
8. [Original Indicator Combinations](#8-original-indicator-combinations)

---

## 1. Moving Average Strategies

### Strategy 1: EMA 20/50 Golden Cross
**Indicators:** EMA(20), EMA(50)

**Entry Conditions:**
- Long: EMA(20) crosses above EMA(50)
- Short: EMA(20) crosses below EMA(50)

**Exit Conditions:**
- Long Exit: EMA(20) crosses below EMA(50)
- Short Exit: EMA(20) crosses above EMA(50)

**Timeframe:** Daily, 4H

**Asset Class:** Stocks, Forex, Crypto

**Rationale:** The golden cross is a classic trend-following signal that identifies when short-term momentum aligns with longer-term trend direction.

---

### Strategy 2: Triple EMA Trend Following
**Indicators:** EMA(9), EMA(21), EMA(200)

**Entry Conditions:**
- Long: Price > EMA(200), EMA(9) crosses above EMA(21)
- Short: Price < EMA(200), EMA(9) crosses below EMA(21)

**Exit Conditions:**
- Long Exit: EMA(9) crosses below EMA(21) OR price closes below EMA(200)
- Short Exit: EMA(9) crosses above EMA(21) OR price closes above EMA(200)

**Timeframe:** 1H, 4H, Daily

**Asset Class:** All asset classes

**Rationale:** The 200 EMA acts as a trend filter, while the 9/21 cross provides entry timing within the established trend direction.

---

### Strategy 3: EMA + MACD + RSI Combo
**Indicators:** EMA(20/50), MACD(12/26/9), RSI(14)

**Entry Conditions:**
- Long: EMA(20) > EMA(50), MACD line > Signal line, RSI > 50
- Short: EMA(20) < EMA(50), MACD line < Signal line, RSI < 50

**Exit Conditions:**
- Long Exit: RSI > 75 (overbought) OR MACD bearish crossover
- Short Exit: RSI < 25 (oversold) OR MACD bullish crossover

**Timeframe:** 15m, 1H, 4H

**Asset Class:** Forex, Crypto, Stocks

**Rationale:** Combines trend direction (EMA), momentum (MACD), and strength (RSI) for high-probability entries.

---

### Strategy 4: VWAP Mean Reversion
**Indicators:** VWAP, RSI(14)

**Entry Conditions:**
- Long: RSI < 30 (oversold) AND price < VWAP
- Short: RSI > 70 (overbought) AND price > VWAP

**Exit Conditions:**
- Long Exit: Price returns to VWAP OR RSI crosses above 50
- Short Exit: Price returns to VWAP OR RSI crosses below 50

**Timeframe:** 5m, 15m (intraday)

**Asset Class:** Stocks, Futures

**Rationale:** VWAP represents the average price weighted by volume; mean reversion to this level is statistically probable when combined with RSI extremes.

---

### Strategy 5: WMA Trend Strength
**Indicators:** WMA(50), WMA(200)

**Entry Conditions:**
- Long: WMA(50) crosses above WMA(200) AND price > both MAs
- Short: WMA(50) crosses below WMA(200) AND price < both MAs

**Exit Conditions:**
- Long Exit: Price closes below WMA(50)
- Short Exit: Price closes above WMA(50)

**Timeframe:** Daily, Weekly

**Asset Class:** Stocks, Indices

**Rationale:** Weighted Moving Average gives more importance to recent prices, making it more responsive than SMA for trend detection.

---

### Strategy 6: SMA 50/200 Golden/Death Cross
**Indicators:** SMA(50), SMA(200)

**Entry Conditions:**
- Long: SMA(50) crosses above SMA(200) - Golden Cross
- Short: SMA(50) crosses below SMA(200) - Death Cross

**Exit Conditions:**
- Long Exit: SMA(50) crosses below SMA(100)
- Short Exit: SMA(50) crosses above SMA(100)

**Timeframe:** Daily, Weekly

**Asset Class:** Stocks, Indices, ETFs

**Rationale:** The most basic and widely-followed trend signal; institutional traders often use this for long-term positioning.

---

## 2. Oscillator Strategies

### Strategy 7: RSI Overbought/Oversold
**Indicators:** RSI(14)

**Entry Conditions:**
- Long: RSI crosses above 30 from below
- Short: RSI crosses below 70 from above

**Exit Conditions:**
- Long Exit: RSI crosses above 70
- Short Exit: RSI crosses below 30

**Timeframe:** 1H, 4H, Daily

**Asset Class:** All asset classes

**Rationale:** RSI identifies extreme price conditions where reversals are statistically more likely.

---

### Strategy 8: MACD Histogram Reversal
**Indicators:** MACD(12/26/9)

**Entry Conditions:**
- Long: MACD histogram turns positive (crosses above zero)
- Short: MACD histogram turns negative (crosses below zero)

**Exit Conditions:**
- Long Exit: MACD line crosses below signal line
- Short Exit: MACD line crosses above signal line

**Timeframe:** 15m, 1H, 4H

**Asset Class:** Forex, Crypto, Stocks

**Rationale:** MACD histogram shows momentum acceleration; zero cross indicates shift in momentum direction.

---

### Strategy 9: Stochastic Crossover
**Indicators:** Stochastic(14,3,3)

**Entry Conditions:**
- Long: %K crosses above %D below 20 level
- Short: %K crosses below %D above 80 level

**Exit Conditions:**
- Long Exit: %K crosses above 80
- Short Exit: %K crosses below 20

**Timeframe:** 5m, 15m, 1H

**Asset Class:** Forex, Crypto

**Rationale:** Stochastic identifies overbought/oversold conditions; crossovers in extreme zones signal high-probability reversals.

---

### Strategy 10: CCI Extreme Reversal
**Indicators:** CCI(20)

**Entry Conditions:**
- Long: CCI crosses above -100 from below
- Short: CCI crosses below +100 from above

**Exit Conditions:**
- Long Exit: CCI crosses above +100
- Short Exit: CCI crosses below -100

**Timeframe:** 1H, 4H

**Asset Class:** Commodities, Forex

**Rationale:** CCI measures price deviation from statistical mean; extreme readings indicate unsustainable price moves.

---

### Strategy 11: RSI + MACD Multi-Timeframe
**Indicators:** RSI(14) on Daily, MACD(12/26/9) on 4H

**Entry Conditions:**
- Long: Daily RSI < 40 (oversold) AND 4H MACD bullish crossover
- Short: Daily RSI > 60 (overbought) AND 4H MACD bearish crossover

**Exit Conditions:**
- Long Exit: Daily RSI > 70 OR 4H MACD bearish crossover
- Short Exit: Daily RSI < 30 OR 4H MACD bullish crossover

**Timeframe:** 4H (execution), Daily (trend)

**Asset Class:** Forex, Crypto, Stocks

**Rationale:** Higher timeframe RSI establishes trend context; lower timeframe MACD provides precise entry timing.

---

### Strategy 12: Stochastic RSI (SRSI)
**Indicators:** Stochastic RSI(14,14,3,3)

**Entry Conditions:**
- Long: SRSI %K crosses above %D below 0.20
- Short: SRSI %K crosses below %D above 0.80

**Exit Conditions:**
- Long Exit: SRSI %K crosses above 0.80
- Short Exit: SRSI %K crosses below 0.20

**Timeframe:** 15m, 1H

**Asset Class:** Crypto, Forex

**Rationale:** SRSI is more sensitive than standard RSI, providing earlier signals in volatile markets.

---

## 3. Volatility Indicator Strategies

### Strategy 13: Bollinger Bands Squeeze Breakout
**Indicators:** Bollinger Bands(20,2), MACD(12/26/9)

**Entry Conditions:**
- Long: BB width < 10% of 20-period average (squeeze) AND price closes above upper band AND MACD > Signal
- Short: BB width < 10% of 20-period average (squeeze) AND price closes below lower band AND MACD < Signal

**Exit Conditions:**
- Long Exit: Price touches middle band (20 SMA)
- Short Exit: Price touches middle band (20 SMA)

**Timeframe:** 1H, 4H, Daily

**Asset Class:** Stocks, Forex, Crypto

**Rationale:** Volatility contraction (squeeze) typically precedes significant expansion; MACD confirms breakout direction.

---

### Strategy 14: Bollinger Bands Mean Reversion
**Indicators:** Bollinger Bands(20,2), RSI(14)

**Entry Conditions:**
- Long: Price touches lower band AND RSI < 30
- Short: Price touches upper band AND RSI > 70

**Exit Conditions:**
- Long Exit: Price reaches middle band OR RSI > 50
- Short Exit: Price reaches middle band OR RSI < 50

**Timeframe:** 15m, 1H

**Asset Class:** Forex, Range-bound stocks

**Rationale:** Price tends to revert to mean (middle band) after touching extremes, especially when RSI confirms overextension.

---

### Strategy 15: Keltner Channel Breakout
**Indicators:** Keltner Channels(20,1.5), EMA(200)

**Entry Conditions:**
- Long: Price closes above upper KC AND price > EMA(200)
- Short: Price closes below lower KC AND price < EMA(200)

**Exit Conditions:**
- Long Exit: Price closes below middle line
- Short Exit: Price closes above middle line

**Timeframe:** 4H, Daily

**Asset Class:** Crypto, Commodities

**Rationale:** Keltner Channels use ATR (actual volatility) rather than standard deviation; breakouts signal genuine momentum.

---

### Strategy 16: Keltner Channel Pullback
**Indicators:** Keltner Channels(20,1.5)

**Entry Conditions:**
- Long: Middle line slope > 0 AND price pulls back to middle line
- Short: Middle line slope < 0 AND price pulls back to middle line

**Exit Conditions:**
- Long Exit: Price reaches upper band
- Short Exit: Price reaches lower band

**Timeframe:** 1H, 4H

**Asset Class:** Trending stocks, Forex

**Rationale:** In established trends, price oscillates between middle line and outer bands; middle line acts as dynamic support/resistance.

---

### Strategy 17: ATR Trailing Stop
**Indicators:** ATR(14), SMA(20)

**Entry Conditions:**
- Long: Price crosses above SMA(20) + (2 × ATR)
- Short: Price crosses below SMA(20) - (2 × ATR)

**Exit Conditions:**
- Long Exit: Price closes below trailing stop (highest high - 2×ATR)
- Short Exit: Price closes above trailing stop (lowest low + 2×ATR)

**Timeframe:** 1H, 4H, Daily

**Asset Class:** All asset classes

**Rationale:** ATR-based stops adapt to market volatility, preventing premature exits in volatile conditions while protecting profits.

---

### Strategy 18: Bollinger %B Reversal
**Indicators:** Bollinger Bands %B(20,2)

**Entry Conditions:**
- Long: %B crosses above 0.20 from below
- Short: %B crosses below 0.80 from above

**Exit Conditions:**
- Long Exit: %B crosses above 0.80
- Short Exit: %B crosses below 0.20

**Timeframe:** 15m, 1H

**Asset Class:** Forex, Crypto

**Rationale:** %B quantifies price position within bands; extreme readings indicate overextension with mean reversion likely.

---

## 4. Volume Indicator Strategies

### Strategy 19: OBV Trend Confirmation
**Indicators:** OBV, EMA(50)

**Entry Conditions:**
- Long: OBV making higher highs AND price > EMA(50)
- Short: OBV making lower lows AND price < EMA(50)

**Exit Conditions:**
- Long Exit: OBV divergence (price higher high, OBV lower high)
- Short Exit: OBV divergence (price lower low, OBV higher low)

**Timeframe:** Daily, 4H

**Asset Class:** Stocks, Crypto

**Rationale:** OBV accumulates volume on up days and subtracts on down days; trend confirmation requires volume support.

---

### Strategy 20: VWAP Institutional Strategy
**Indicators:** VWAP, Volume(20)

**Entry Conditions:**
- Long: Price crosses above VWAP AND volume > 1.5× average
- Short: Price crosses below VWAP AND volume > 1.5× average

**Exit Conditions:**
- Long Exit: Price crosses below VWAP
- Short Exit: Price crosses above VWAP

**Timeframe:** 5m, 15m (intraday)

**Asset Class:** Stocks, Futures

**Rationale:** VWAP represents institutional average execution price; breaks with volume indicate institutional accumulation/distribution.

---

### Strategy 21: Volume Profile POC Rejection
**Indicators:** Volume Profile (Point of Control), Price

**Entry Conditions:**
- Long: Price tests POC from above AND bounces with increased volume
- Short: Price tests POC from below AND rejects with increased volume

**Exit Conditions:**
- Long Exit: Price breaks below Value Area Low
- Short Exit: Price breaks above Value Area High

**Timeframe:** 15m, 1H, 4H

**Asset Class:** Futures, Stocks

**Rationale:** Point of Control represents highest volume node; acts as strong support/resistance with rejection signaling continuation.

---

### Strategy 22: Chaikin Money Flow Divergence
**Indicators:** CMF(20), Price

**Entry Conditions:**
- Long: Price makes lower low AND CMF makes higher low (bullish divergence)
- Short: Price makes higher high AND CMF makes lower high (bearish divergence)

**Exit Conditions:**
- Long Exit: CMF crosses below zero
- Short Exit: CMF crosses above zero

**Timeframe:** 1H, 4H, Daily

**Asset Class:** Stocks, Crypto

**Rationale:** CMF measures buying/selling pressure; divergences indicate weakening trend momentum before price reflects it.

---

### Strategy 23: Volume + RSI Breakout
**Indicators:** Volume(20), RSI(14)

**Entry Conditions:**
- Long: Volume > 2× average AND RSI crosses above 50
- Short: Volume > 2× average AND RSI crosses below 50

**Exit Conditions:**
- Long Exit: RSI crosses below 60
- Short Exit: RSI crosses above 40

**Timeframe:** 15m, 1H

**Asset Class:** Crypto, Momentum stocks

**Rationale:** High volume breakouts with RSI confirmation indicate genuine momentum rather than low-volume false breaks.

---

## 5. Trend Indicator Strategies

### Strategy 24: ADX Trend Strength Filter
**Indicators:** ADX(14), +DI, -DI, EMA(50)

**Entry Conditions:**
- Long: ADX > 25 AND +DI > -DI AND price > EMA(50)
- Short: ADX > 25 AND -DI > +DI AND price < EMA(50)

**Exit Conditions:**
- Long Exit: ADX < 20 OR -DI crosses above +DI
- Short Exit: ADX < 20 OR +DI crosses above -DI

**Timeframe:** 4H, Daily

**Asset Class:** Forex, Commodities, Indices

**Rationale:** ADX > 25 indicates strong trend; DI crossovers identify direction. Avoids choppy markets.

---

### Strategy 25: Parabolic SAR Trend Following
**Indicators:** Parabolic SAR(0.02, 0.2), EMA(200)

**Entry Conditions:**
- Long: SAR flips below price AND price > EMA(200)
- Short: SAR flips above price AND price < EMA(200)

**Exit Conditions:**
- Long Exit: SAR flips above price
- Short Exit: SAR flips below price

**Timeframe:** 1H, 4H, Daily

**Asset Class:** Trending markets, Commodities

**Rationale:** Parabolic SAR provides trailing stop mechanism; EMA(200) ensures trades align with major trend.

---

### Strategy 26: Ichimoku Cloud Breakout
**Indicators:** Ichimoku Cloud (9,26,52)

**Entry Conditions:**
- Long: Price crosses above cloud AND Tenkan crosses above Kijun
- Short: Price crosses below cloud AND Tenkan crosses below Kijun

**Exit Conditions:**
- Long Exit: Price crosses below Tenkan OR into cloud
- Short Exit: Price crosses above Tenkan OR into cloud

**Timeframe:** 4H, Daily

**Asset Class:** Forex, Crypto, Indices

**Rationale:** Ichimoku provides complete trend system; cloud acts as support/resistance, crosses provide timing.

---

### Strategy 27: Supertrend ADX Combo
**Indicators:** Supertrend(10,3), ADX(14)

**Entry Conditions:**
- Long: Supertrend turns bullish AND ADX > 25
- Short: Supertrend turns bearish AND ADX > 25

**Exit Conditions:**
- Long Exit: Supertrend turns bearish
- Short Exit: Supertrend turns bullish

**Timeframe:** 1H, 4H

**Asset Class:** All asset classes

**Rationale:** Supertrend provides clear trend signals; ADX filter eliminates weak trend whipsaws.

---

### Strategy 28: ADX + DMI Crossover
**Indicators:** ADX(14), +DI(14), -DI(14)

**Entry Conditions:**
- Long: +DI crosses above -DI AND ADX > 20
- Short: -DI crosses above +DI AND ADX > 20

**Exit Conditions:**
- Long Exit: ADX < 15 (trend exhaustion)
- Short Exit: ADX < 15 (trend exhaustion)

**Timeframe:** Daily, 4H

**Asset Class:** Forex, Stocks

**Rationale:** DI crossovers identify trend direction changes; ADX threshold ensures sufficient trend strength.

---

## 6. Momentum Indicator Strategies

### Strategy 29: Momentum Divergence
**Indicators:** Momentum(10), Price

**Entry Conditions:**
- Long: Price makes lower low AND Momentum makes higher low
- Short: Price makes higher high AND Momentum makes lower high

**Exit Conditions:**
- Long Exit: Momentum crosses below zero
- Short Exit: Momentum crosses above zero

**Timeframe:** 1H, 4H

**Asset Class:** All asset classes

**Rationale:** Momentum measures rate of price change; divergences indicate weakening trend before price reflects it.

---

### Strategy 30: Rate of Change (ROC) Breakout
**Indicators:** ROC(12), SMA(200)

**Entry Conditions:**
- Long: ROC crosses above zero AND price > SMA(200)
- Short: ROC crosses below zero AND price < SMA(200)

**Exit Conditions:**
- Long Exit: ROC crosses below zero
- Short Exit: ROC crosses above zero

**Timeframe:** Daily

**Asset Class:** Stocks, Indices

**Rationale:** ROC measures percentage price change; zero cross with trend filter captures momentum shifts.

---

### Strategy 31: Williams %R Extreme
**Indicators:** Williams %R(14)

**Entry Conditions:**
- Long: %R crosses above -80 from below
- Short: %R crosses below -20 from above

**Exit Conditions:**
- Long Exit: %R crosses above -20
- Short Exit: %R crosses below -80

**Timeframe:** 15m, 1H

**Asset Class:** Forex, Crypto

**Rationale:** Williams %R identifies overbought (> -20) and oversold (< -80) conditions for reversal trading.

---

### Strategy 32: Awesome Oscillator Saucer
**Indicators:** Awesome Oscillator (AO)

**Entry Conditions:**
- Long: AO forms saucer pattern (3 bars: negative, less negative, positive)
- Short: AO forms inverted saucer (3 bars: positive, less positive, negative)

**Exit Conditions:**
- Long Exit: AO crosses below zero
- Short Exit: AO crosses above zero

**Timeframe:** 1H, 4H

**Asset Class:** Stocks, Commodities

**Rationale:** AO saucer patterns indicate momentum acceleration after brief consolidation within trend.

---

## 7. Multi-Indicator Confirmation Systems

### Strategy 33: Triple Confirmation System
**Indicators:** EMA(50), RSI(14), MACD(12/26/9)

**Entry Conditions:**
- Long: Price > EMA(50) AND RSI > 50 AND MACD > Signal
- Short: Price < EMA(50) AND RSI < 50 AND MACD < Signal

**Exit Conditions:**
- Long Exit: 2 of 3 indicators turn bearish
- Short Exit: 2 of 3 indicators turn bullish

**Timeframe:** 4H, Daily

**Asset Class:** All asset classes

**Rationale:** Requiring 3 independent indicator confirmations significantly reduces false signals.

---

### Strategy 34: Multi-Timeframe Trend Confirmator
**Indicators:** EMA(200), SMA(50/200), RSI(14), MACD(12/26/9), ADX(14), Supertrend

**Entry Conditions:**
- Long: Score > +2 on both higher TF (4H) AND mid TF (1H)
- Short: Score < -2 on both higher TF (4H) AND mid TF (1H)

**Exit Conditions:**
- Long Exit: Score drops below +2 on higher TF
- Short Exit: Score rises above -2 on higher TF

**Timeframe:** 1H (execution), 4H (confirmation)

**Asset Class:** Forex, Crypto, Stocks

**Rationale:** Composite scoring across multiple indicators and timeframes ensures high-probability setups.

---

### Strategy 35: Multi-Indicator Reversal Strategy
**Indicators:** RSI(14), MACD(12/26/9), Williams %R(14), Bollinger Bands(20,2), Volume(20)

**Entry Conditions:**
- Long: At least 2 of 4 indicators show oversold (RSI<30, %R<-80, price<lower BB, MACD turning up)
- Short: At least 2 of 4 indicators show overbought (RSI>70, %R>-20, price>upper BB, MACD turning down)

**Exit Conditions:**
- Long Exit: Opposite signal appears
- Short Exit: Opposite signal appears

**Timeframe:** 1H

**Asset Class:** Stocks (mean-reverting), ETFs

**Rationale:** Multiple indicator confluence at extremes identifies high-probability reversal points.

---

### Strategy 36: 5-Indicator Momentum System
**Indicators:** EMA(9/21), RSI(14), MACD(12/26/9), Volume(20), ATR(14)

**Entry Conditions:**
- Long: EMA(9)>EMA(21), RSI 40-70, MACD bullish, Volume > 1.2× avg, ATR expanding
- Short: EMA(9)<EMA(21), RSI 30-60, MACD bearish, Volume > 1.2× avg, ATR expanding

**Exit Conditions:**
- Long Exit: RSI > 75 OR trailing stop at 1.5× ATR
- Short Exit: RSI < 25 OR trailing stop at 1.5× ATR

**Timeframe:** 5m, 15m (day trading)

**Asset Class:** Futures, Stocks

**Rationale:** Combines trend, momentum, volume, and volatility for comprehensive day trading system.

---

### Strategy 37: GKD Modular System
**Indicators:** Baseline (HMA), Volatility (ATR), Confirmation 1 (Fisher), Confirmation 2 (uf2018), Continuation (Coppock)

**Entry Conditions:**
- Long: All 5 components align bullish
- Short: All 5 components align bearish

**Exit Conditions:**
- Long Exit: Baseline turns bearish OR 2+ components disagree
- Short Exit: Baseline turns bullish OR 2+ components disagree

**Timeframe:** 1H, 4H

**Asset Class:** All asset classes

**Rationale:** Modular system allows customization; multiple confirmation layers reduce false signals.

---

## 8. Original Indicator Combinations

### Strategy 38: VWAP + Keltner Mean Reversion
**Indicators:** VWAP, Keltner Channels(20,2), RSI(14)

**Entry Conditions:**
- Long: Price < VWAP AND price touches lower KC AND RSI < 35
- Short: Price > VWAP AND price touches upper KC AND RSI > 65

**Exit Conditions:**
- Long Exit: Price returns to VWAP
- Short Exit: Price returns to VWAP

**Timeframe:** 15m, 1H

**Asset Class:** Futures, Forex

**Rationale:** Combines institutional reference (VWAP) with volatility bands (KC) and momentum (RSI) for high-probability mean reversion.

---

### Strategy 39: ATR Bands + Stochastic Reversal
**Indicators:** ATR Bands (Keltner 21,2.5), Stochastic RSI(14,14,3,3)

**Entry Conditions:**
- Long: Wick crosses lower band AND SRSI %K < 20 AND candle body closes inside bands
- Short: Wick crosses upper band AND SRSI %K > 80 AND candle body closes inside bands

**Exit Conditions:**
- Long Exit: Price reaches middle band OR SRSI > 50
- Short Exit: Price reaches middle band OR SRSI < 50

**Timeframe:** 5m, 15m

**Asset Class:** Crypto, Forex

**Rationale:** Wick rejection at ATR bands with SRSI extreme identifies pivot points with minimal retracement.

---

### Strategy 40: OBV + Supertrend Trend Following
**Indicators:** OBV(20), Supertrend(10,3), ADX(14)

**Entry Conditions:**
- Long: OBV rising AND Supertrend bullish AND ADX > 25
- Short: OBV falling AND Supertrend bearish AND ADX > 25

**Exit Conditions:**
- Long Exit: OBV divergence OR Supertrend flip
- Short Exit: OBV divergence OR Supertrend flip

**Timeframe:** 1H, 4H

**Asset Class:** Stocks, Crypto

**Rationale:** Volume trend (OBV) confirms price trend (Supertrend); ADX ensures trend strength.

---

### Strategy 41: Ichimoku + Volume Profile Confluence
**Indicators:** Ichimoku Cloud(9,26,52), Volume Profile POC

**Entry Conditions:**
- Long: Price above cloud AND Tenkan > Kijun AND price bounces from POC
- Short: Price below cloud AND Tenkan < Kijun AND price rejects at POC

**Exit Conditions:**
- Long Exit: Price enters cloud OR breaks below POC
- Short Exit: Price enters cloud OR breaks above POC

**Timeframe:** 4H, Daily

**Asset Class:** Forex, Indices

**Rationale:** Combines trend direction (Ichimoku) with key volume level (POC) for support/resistance confirmation.

---

### Strategy 42: Williams %R + CCI Momentum
**Indicators:** Williams %R(14), CCI(20), EMA(50)

**Entry Conditions:**
- Long: %R crosses above -80 AND CCI crosses above -100 AND price > EMA(50)
- Short: %R crosses below -20 AND CCI crosses below +100 AND price < EMA(50)

**Exit Conditions:**
- Long Exit: %R crosses above -20 OR CCI crosses above +100
- Short Exit: %R crosses below -80 OR CCI crosses below -100

**Timeframe:** 1H, 4H

**Asset Class:** Commodities, Forex

**Rationale:** Dual oscillator confirmation with trend filter; %R and CCI measure different aspects of momentum.

---

### Strategy 43: Bollinger + Keltner Squeeze
**Indicators:** Bollinger Bands(20,2), Keltner Channels(20,1.5)

**Entry Conditions:**
- Long: BB inside KC (squeeze) AND price breaks above both upper bands
- Short: BB inside KC (squeeze) AND price breaks below both lower bands

**Exit Conditions:**
- Long Exit: Price closes below KC middle line
- Short Exit: Price closes above KC middle line

**Timeframe:** 4H, Daily

**Asset Class:** Stocks, Crypto

**Rationale:** When BB squeeze inside KC, volatility compression is extreme; breakout signals significant move.

---

### Strategy 44: Parabolic SAR + RSI Trend
**Indicators:** Parabolic SAR(0.02,0.2), RSI(14), Volume(20)

**Entry Conditions:**
- Long: SAR flips below price AND RSI > 50 AND volume > average
- Short: SAR flips above price AND RSI < 50 AND volume > average

**Exit Conditions:**
- Long Exit: SAR flips above price OR RSI < 40
- Short Exit: SAR flips below price OR RSI > 60

**Timeframe:** 1H, 4H

**Asset Class:** Trending stocks, Commodities

**Rationale:** SAR provides trend direction and trailing stop; RSI confirms momentum; volume validates move.

---

### Strategy 45: Momentum + ROC Divergence System
**Indicators:** Momentum(10), ROC(12), MACD(12/26/9)

**Entry Conditions:**
- Long: Momentum divergence AND ROC turning up AND MACD histogram increasing
- Short: Momentum divergence AND ROC turning down AND MACD histogram decreasing

**Exit Conditions:**
- Long Exit: Momentum crosses below zero
- Short Exit: Momentum crosses above zero

**Timeframe:** 4H, Daily

**Asset Class:** All asset classes

**Rationale:** Multiple momentum indicators confirming divergence provides stronger reversal signal than single indicator.

---

## Strategy Summary Table

| # | Strategy | Primary Indicators | Best Timeframe | Asset Class | Strategy Type |
|---|----------|-------------------|----------------|-------------|---------------|
| 1 | EMA Golden Cross | EMA(20/50) | Daily | All | Trend Following |
| 2 | Triple EMA | EMA(9/21/200) | 1H-4H | All | Trend Following |
| 3 | EMA+MACD+RSI | EMA, MACD, RSI | 15m-4H | All | Multi-Indicator |
| 4 | VWAP Mean Reversion | VWAP, RSI | 5m-15m | Stocks | Mean Reversion |
| 5 | WMA Trend | WMA(50/200) | Daily | Stocks | Trend Following |
| 6 | SMA Golden Cross | SMA(50/200) | Daily-W | Stocks | Trend Following |
| 7 | RSI Extremes | RSI(14) | 1H-Daily | All | Mean Reversion |
| 8 | MACD Histogram | MACD | 15m-4H | All | Momentum |
| 9 | Stochastic Cross | Stoch(14,3,3) | 5m-1H | Forex | Mean Reversion |
| 10 | CCI Reversal | CCI(20) | 1H-4H | Commodities | Mean Reversion |
| 11 | RSI+MACD MTF | RSI(D), MACD(4H) | 4H | All | Multi-Timeframe |
| 12 | Stochastic RSI | SRSI | 15m-1H | Crypto | Mean Reversion |
| 13 | BB Squeeze | BB, MACD | 1H-Daily | All | Breakout |
| 14 | BB Mean Reversion | BB, RSI | 15m-1H | Forex | Mean Reversion |
| 15 | KC Breakout | KC, EMA(200) | 4H-Daily | Crypto | Breakout |
| 16 | KC Pullback | KC | 1H-4H | Stocks | Trend Following |
| 17 | ATR Trailing | ATR, SMA | 1H-Daily | All | Trend Following |
| 18 | Bollinger %B | %B | 15m-1H | Forex | Mean Reversion |
| 19 | OBV Trend | OBV, EMA | 4H-Daily | Stocks | Trend Following |
| 20 | VWAP Volume | VWAP, Volume | 5m-15m | Stocks | Breakout |
| 21 | Volume Profile POC | Volume Profile | 15m-4H | Futures | Support/Resistance |
| 22 | CMF Divergence | CMF | 1H-Daily | Stocks | Divergence |
| 23 | Volume+RSI | Volume, RSI | 15m-1H | Crypto | Breakout |
| 24 | ADX Filter | ADX, DI, EMA | 4H-Daily | Forex | Trend Following |
| 25 | Parabolic SAR | SAR, EMA | 1H-Daily | Commodities | Trend Following |
| 26 | Ichimoku Cloud | Ichimoku | 4H-Daily | Forex | Trend Following |
| 27 | Supertrend ADX | Supertrend, ADX | 1H-4H | All | Trend Following |
| 28 | ADX+DMI | ADX, DI | Daily | Forex | Trend Following |
| 29 | Momentum Divergence | Momentum | 1H-4H | All | Divergence |
| 30 | ROC Breakout | ROC, SMA | Daily | Stocks | Momentum |
| 31 | Williams %R | %R | 15m-1H | Forex | Mean Reversion |
| 32 | Awesome Oscillator | AO | 1H-4H | Stocks | Momentum |
| 33 | Triple Confirmation | EMA, RSI, MACD | 4H-Daily | All | Multi-Indicator |
| 34 | MTF Confirmator | 6 indicators | 1H-4H | All | Multi-Timeframe |
| 35 | Multi-Reversal | 5 indicators | 1H | Stocks | Mean Reversion |
| 36 | 5-Indicator System | 5 indicators | 5m-15m | Futures | Day Trading |
| 37 | GKD Modular | 5 components | 1H-4H | All | Modular System |
| 38 | VWAP+KC | VWAP, KC, RSI | 15m-1H | Futures | Mean Reversion |
| 39 | ATR+SRSI | ATR Bands, SRSI | 5m-15m | Crypto | Reversal |
| 40 | OBV+Supertrend | OBV, Supertrend | 1H-4H | Stocks | Trend Following |
| 41 | Ichimoku+VP | Ichimoku, VP | 4H-Daily | Forex | Trend Following |
| 42 | %R+CCI | %R, CCI, EMA | 1H-4H | Commodities | Momentum |
| 43 | BB+KC Squeeze | BB, KC | 4H-Daily | Stocks | Breakout |
| 44 | SAR+RSI | SAR, RSI, Volume | 1H-4H | Stocks | Trend Following |
| 45 | Momentum+ROC | Momentum, ROC | 4H-Daily | All | Divergence |

---

## Key Insights

### Most Effective Indicator Combinations

1. **Trend + Momentum + Volume**: EMA + MACD + Volume provides comprehensive analysis
2. **Volatility + Oscillator**: Bollinger Bands + RSI captures mean reversion opportunities
3. **Multi-Timeframe**: Higher TF trend + Lower TF entry timing improves win rates
4. **Trend Strength Filter**: ADX > 25 eliminates choppy market false signals

### Built-in Strategy Templates on TradingView

1. **EMA Cross Strategy**: Basic moving average crossover
2. **RSI Strategy**: Overbought/oversold with adjustable levels
3. **MACD Strategy**: Histogram and line crossover signals
4. **Bollinger Bands Strategy**: Band squeeze and breakout detection
5. **Supertrend Strategy**: ATR-based trend following
6. **Ichimoku Strategy**: Complete cloud-based system

### Best Practices

1. **Always use trend filters** (EMA 200 or ADX) to avoid counter-trend trades
2. **Combine 2-3 non-correlated indicators** for confirmation
3. **Use volume indicators** to validate price breakouts
4. **Adjust parameters** based on asset volatility
5. **Backtest extensively** before live trading

---

*Research compiled from TradingView's built-in indicator library and community strategies. For educational purposes only.*
