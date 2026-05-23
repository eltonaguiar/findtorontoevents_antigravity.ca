/**
 * Stock Scoring Algorithms
 * 
 * Implements CAN SLIM Growth and Technical Momentum scoring
 */

import { StockData } from "./stock-data-fetcher-enhanced";
import {
  getEMA,
  calculateRSI,
  calculateMACD,
  calculateADX,
  calculateVolumeRatio,
  calculateRSRating,
  isStage2Uptrend,
  getPriceVs52WHigh,
} from "./stock-indicators";

export interface StockPick {
  symbol: string;
  name: string;
  score: number;
  rating: "STRONG BUY" | "BUY" | "HOLD" | "SELL";
  algorithm: string;
  timeframe: string;
  risk: "Low" | "Medium" | "High" | "Very High";
  metrics?: Record<string, any>;
}

/**
 * CAN SLIM Growth Screener
 * 
 * Based on William O'Neil's methodology:
 * - RS Rating (40 pts) - relaxed from 90 to 75+
 * - Stage-2 Uptrend (30 pts)
 * - Price vs 52W High (20 pts)
 * - RSI momentum (10 pts)
 * - Volume bonus
 * 
 * RELAXED: RS Rating threshold lowered from 90 to 75 to generate more picks
 */
export function scoreCANSLIM(data: StockData, marketData?: StockData): StockPick | null {
  if (!data.history || data.history.length < 200) return null;
  
  const prices = data.history.map((h) => h.close);
  const currentPrice = data.price;
  
  // Calculate RS Rating (relaxed threshold: 75+ instead of 90+)
  let rsRating = 50;
  if (marketData && marketData.history) {
    const marketPrices = marketData.history.map((h) => h.close);
    rsRating = calculateRSRating(prices, marketPrices);
  } else {
    // Fallback: use 12-month return as proxy
    const yearlyReturn = (currentPrice - prices[0]) / prices[0];
    if (yearlyReturn > 0.4) rsRating = 85;
    else if (yearlyReturn > 0.2) rsRating = 75;
    else if (yearlyReturn > 0.1) rsRating = 65;
    else rsRating = 50;
  }
  
  // RELAXED: Accept RS Rating >= 75 (was 90)
  if (rsRating < 75) return null;
  
  // Stage-2 Uptrend check
  const stage2 = isStage2Uptrend(prices);
  if (!stage2) return null;
  
  // Price vs 52-week high
  const priceVs52W = getPriceVs52WHigh(currentPrice, data.high52Week);
  
  // RSI
  const rsi = calculateRSI(prices, 14);
  
  // Volume bonus
  const volumes = data.history.map((h) => h.volume);
  const volumeRatio = calculateVolumeRatio(volumes, 20);
  
  // Scoring
  let score = 0;
  
  // RS Rating (40 pts) - relaxed scoring
  if (rsRating >= 90) score += 40;
  else if (rsRating >= 85) score += 35;
  else if (rsRating >= 80) score += 30;
  else if (rsRating >= 75) score += 25; // RELAXED: was 20
  
  // Stage-2 Uptrend (30 pts)
  if (stage2) score += 30;
  
  // Price vs 52W High (20 pts)
  if (priceVs52W >= 95) score += 20;
  else if (priceVs52W >= 90) score += 18;
  else if (priceVs52W >= 85) score += 15;
  else if (priceVs52W >= 80) score += 12;
  else if (priceVs52W >= 75) score += 10;
  
  // RSI momentum (10 pts)
  if (rsi >= 50 && rsi <= 70) score += 10; // Healthy momentum
  else if (rsi >= 45 && rsi < 50) score += 7;
  else if (rsi >= 70 && rsi < 75) score += 5;
  
  // Volume bonus (up to 10 pts)
  if (volumeRatio >= 1.5) score += 10;
  else if (volumeRatio >= 1.2) score += 7;
  else if (volumeRatio >= 1.0) score += 5;
  
  // Determine rating
  let rating: "STRONG BUY" | "BUY" | "HOLD" | "SELL";
  if (score >= 80) rating = "STRONG BUY";
  else if (score >= 60) rating = "BUY";
  else if (score >= 40) rating = "HOLD";
  else rating = "SELL";
  
  // RELAXED: Lower threshold from 50 to 30 to generate more picks
  if (score < 30) return null;
  
  return {
    symbol: data.symbol,
    name: data.name,
    score: Math.round(Math.min(100, score)),
    rating,
    algorithm: "CAN SLIM Growth",
    timeframe: "3m-1y",
    risk: data.price < 5 ? "High" : "Medium",
    metrics: {
      rsRating: Math.round(rsRating),
      stage2,
      priceVs52W: Math.round(priceVs52W * 10) / 10,
      rsi: Math.round(rsi * 10) / 10,
      volumeRatio: Math.round(volumeRatio * 100) / 100,
    },
  };
}

/**
 * Technical Momentum Screener
 * 
 * ENHANCED with:
 * - EMA(50,200) trend filter (bullish cross required)
 * - ADX > 20 strength filter
 * - Volume > 1.5x 20-day average
 * - RSI/MACD signals
 * 
 * Timeframes: 24h, 3d, 7d
 */
export function scoreTechnicalMomentum(
  data: StockData,
  timeframe: "24h" | "3d" | "7d" = "24h"
): StockPick | null {
  if (!data.history || data.history.length < 200) return null;
  
  const prices = data.history.map((h) => h.close);
  const highs = data.history.map((h) => h.high);
  const lows = data.history.map((h) => h.low);
  const volumes = data.history.map((h) => h.volume);
  const currentPrice = data.price;
  
  // ENHANCED: EMA(50,200) trend filter
  const ema50 = getEMA(prices, 50);
  const ema200 = getEMA(prices, 200);
  
  if (!ema50 || !ema200) return null;
  
  // Require bullish EMA cross: EMA50 > EMA200 and price > EMA50
  if (ema50 <= ema200 || currentPrice <= ema50) return null;
  
  // ENHANCED: ADX > 20 strength filter
  const adx = calculateADX(highs, lows, prices, 14);
  if (!adx || adx < 20) return null; // Require ADX >= 20 for trend strength
  
  // ENHANCED: Volume > 1.5x 20-day average
  const volumeRatio = calculateVolumeRatio(volumes, 20);
  if (volumeRatio < 1.5) return null; // Require volume surge
  
  // Calculate indicators
  const rsi = calculateRSI(prices, 14);
  const macd = calculateMACD(prices, 12, 26, 9);
  
  // Scoring based on timeframe
  let score = 0;
  
  if (timeframe === "24h") {
    // 24-hour: Volume surge (40 pts), RSI extremes (30 pts), Breakout (30 pts)
    
    // Volume surge (40 pts)
    if (volumeRatio >= 2.5) score += 40;
    else if (volumeRatio >= 2.0) score += 35;
    else if (volumeRatio >= 1.5) score += 30; // Minimum threshold met
    
    // RSI extremes (30 pts)
    if (rsi < 30) score += 30; // Oversold bounce
    else if (rsi >= 50 && rsi <= 70) score += 25; // Healthy momentum
    else if (rsi >= 45 && rsi < 50) score += 20;
    else if (rsi >= 70 && rsi < 75) score += 15; // Overbought but still strong
    
    // Breakout (30 pts) - price near 20-day high
    const high20 = Math.max(...prices.slice(-20));
    const priceVsHigh20 = (currentPrice / high20) * 100;
    if (priceVsHigh20 >= 98) score += 30;
    else if (priceVsHigh20 >= 95) score += 25;
    else if (priceVsHigh20 >= 92) score += 20;
    
  } else if (timeframe === "3d") {
    // 3-day: Volume (30 pts), Breakout (30 pts), RSI momentum (25 pts), Volatility (15 pts)
    
    // Volume (30 pts)
    if (volumeRatio >= 2.0) score += 30;
    else if (volumeRatio >= 1.5) score += 25;
    
    // Breakout (30 pts)
    const high20 = Math.max(...prices.slice(-20));
    const priceVsHigh20 = (currentPrice / high20) * 100;
    if (priceVsHigh20 >= 95) score += 30;
    else if (priceVsHigh20 >= 90) score += 25;
    else if (priceVsHigh20 >= 85) score += 20;
    
    // RSI momentum (25 pts)
    if (rsi >= 50 && rsi <= 70) score += 25;
    else if (rsi >= 45 && rsi < 50) score += 20;
    else if (rsi >= 70 && rsi < 75) score += 18;
    else if (rsi < 30) score += 15; // Oversold bounce potential
    
    // Volatility/ATR-style (15 pts) - using ADX as proxy
    if (adx >= 30) score += 15;
    else if (adx >= 25) score += 12;
    else if (adx >= 20) score += 10;
    
  } else if (timeframe === "7d") {
    // 7-day: Bollinger Squeeze (30 pts), RSI extremes (25 pts), Volume (25 pts), Institutional (20 pts)
    
    // Bollinger Squeeze proxy (30 pts) - low volatility before move
    // Use recent price range vs longer-term range
    const recentRange = Math.max(...prices.slice(-10)) - Math.min(...prices.slice(-10));
    const longerRange = Math.max(...prices.slice(-30)) - Math.min(...prices.slice(-30));
    const squeezeRatio = recentRange / (longerRange + 0.001);
    if (squeezeRatio < 0.5 && adx >= 20) score += 30; // Low vol + trend = squeeze breakout
    else if (squeezeRatio < 0.7) score += 20;
    
    // RSI extremes (25 pts)
    if (rsi >= 50 && rsi <= 70) score += 25;
    else if (rsi >= 45 && rsi < 50) score += 20;
    else if (rsi < 30) score += 18;
    
    // Volume (25 pts)
    if (volumeRatio >= 1.8) score += 25;
    else if (volumeRatio >= 1.5) score += 20;
    
    // Institutional-style proxy (20 pts) - size + volume
    const marketCap = data.marketCap || 0;
    const isLargeCap = marketCap > 1_000_000_000;
    if (isLargeCap && volumeRatio >= 1.5) score += 20;
    else if (isLargeCap && volumeRatio >= 1.2) score += 15;
    else if (volumeRatio >= 1.5) score += 12;
  }
  
  // MACD bonus (up to 10 pts)
  if (macd && macd.histogram > 0 && macd.macd > macd.signal) {
    score += 10;
  }
  
  // Determine rating
  let rating: "STRONG BUY" | "BUY" | "HOLD" | "SELL";
  if (score >= 75) rating = "STRONG BUY";
  else if (score >= 50) rating = "BUY";
  else if (score >= 30) rating = "HOLD";
  else rating = "SELL";
  
  // RELAXED: Lower threshold from 45 to 35 to generate more picks
  if (score < 35) return null;
  
  return {
    symbol: data.symbol,
    name: data.name,
    score: Math.round(Math.min(100, score)),
    rating,
    algorithm: "Technical Momentum",
    timeframe,
    risk: data.price < 5 ? "Very High" : data.price < 10 ? "High" : "Medium",
    metrics: {
      ema50: Math.round(ema50 * 100) / 100,
      ema200: Math.round(ema200 * 100) / 100,
      adx: Math.round(adx * 10) / 10,
      volumeRatio: Math.round(volumeRatio * 100) / 100,
      rsi: Math.round(rsi * 10) / 10,
      macdHistogram: macd ? Math.round(macd.histogram * 100) / 100 : null,
    },
  };
}

/**
 * Composite Rating Engine (Medium-term: 1m, 3m)
 * Kept as-is for now
 */
export function scoreComposite(data: StockData): StockPick | null {
  if (!data.history || data.history.length < 50) return null;
  
  const prices = data.history.map((h) => h.close);
  const volumes = data.history.map((h) => h.volume);
  const currentPrice = data.price;
  
  // Technical (40 pts)
  const sma20 = prices.slice(-20).reduce((a, b) => a + b, 0) / 20;
  const sma50 = prices.length >= 50 ? prices.slice(-50).reduce((a, b) => a + b, 0) / 50 : sma20;
  const rsi = calculateRSI(prices, 14);
  
  let technicalScore = 0;
  if (currentPrice > sma20 && sma20 > sma50) technicalScore = 40;
  else if (currentPrice > sma20) technicalScore = 30;
  else if (currentPrice > sma50) technicalScore = 20;
  
  if (rsi >= 50 && rsi <= 70) technicalScore += 5;
  
  // Volume (20 pts)
  const volumeRatio = calculateVolumeRatio(volumes, 20);
  let volumeScore = 0;
  if (volumeRatio >= 1.5) volumeScore = 20;
  else if (volumeRatio >= 1.2) volumeScore = 15;
  else if (volumeRatio >= 1.0) volumeScore = 10;
  
  // Fundamental (20 pts)
  let fundamentalScore = 0;
  if (data.pe && data.pe > 0 && data.pe < 30) fundamentalScore += 10;
  if (data.marketCap && data.marketCap > 1_000_000_000) fundamentalScore += 10;
  
  // Regime Adjustment (20 pts)
  let regimeScore = 20; // Default neutral
  
  const totalScore = technicalScore + volumeScore + fundamentalScore + regimeScore;
  
  let rating: "STRONG BUY" | "BUY" | "HOLD" | "SELL";
  if (totalScore >= 80) rating = "STRONG BUY";
  else if (totalScore >= 60) rating = "BUY";
  else if (totalScore >= 40) rating = "HOLD";
  else rating = "SELL";
  
  if (totalScore < 50) return null;
  
  return {
    symbol: data.symbol,
    name: data.name,
    score: Math.round(Math.min(100, totalScore)),
    rating,
    algorithm: "Composite Rating",
    timeframe: "1m-3m",
    risk: data.price < 5 ? "High" : "Medium",
    metrics: {
      technicalScore,
      volumeScore,
      fundamentalScore,
      regimeScore,
    },
  };
}
