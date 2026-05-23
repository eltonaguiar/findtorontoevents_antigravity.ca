/**
 * Technical Indicators Library
 * 
 * Provides EMA, ADX, RSI, MACD, and volume calculations for stock scoring
 */

export interface PriceHistory {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Calculate EMA (Exponential Moving Average)
 */
export function calculateEMA(prices: number[], period: number): number[] {
  if (prices.length < period) return [];
  
  const multiplier = 2 / (period + 1);
  const ema: number[] = [];
  
  // Seed with SMA
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += prices[i];
    ema[i] = 0; // placeholder
  }
  ema[period - 1] = sum / period;
  
  // Calculate EMA from period onward
  for (let i = period; i < prices.length; i++) {
    ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1];
  }
  
  return ema;
}

/**
 * Get the latest EMA value
 */
export function getEMA(prices: number[], period: number): number | null {
  const ema = calculateEMA(prices, period);
  return ema.length > 0 ? ema[ema.length - 1] : null;
}

/**
 * Calculate RSI (Relative Strength Index)
 */
export function calculateRSI(prices: number[], period: number = 14): number {
  if (prices.length < period + 1) return 50;
  
  let gains = 0;
  let losses = 0;
  
  for (let i = prices.length - period; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) {
      gains += diff;
    } else {
      losses -= diff;
    }
  }
  
  if (losses === 0) return 100;
  const rs = gains / losses;
  return 100 - (100 / (1 + rs));
}

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 * Returns: { macd: number, signal: number, histogram: number }
 */
export function calculateMACD(
  prices: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): { macd: number; signal: number; histogram: number } | null {
  if (prices.length < slowPeriod + signalPeriod) return null;
  
  const fastEMA = calculateEMA(prices, fastPeriod);
  const slowEMA = calculateEMA(prices, slowPeriod);
  
  if (fastEMA.length === 0 || slowEMA.length === 0) return null;
  
  // Calculate MACD line
  const macdLine: number[] = [];
  const minLength = Math.min(fastEMA.length, slowEMA.length);
  const offset = Math.abs(fastEMA.length - slowEMA.length);
  
  for (let i = 0; i < minLength; i++) {
    const fastIdx = fastEMA.length > slowEMA.length ? i + offset : i;
    const slowIdx = slowEMA.length > fastEMA.length ? i + offset : i;
    macdLine.push(fastEMA[fastIdx] - slowEMA[slowIdx]);
  }
  
  if (macdLine.length < signalPeriod) return null;
  
  // Calculate signal line (EMA of MACD)
  const signalEMA = calculateEMA(macdLine, signalPeriod);
  if (signalEMA.length === 0) return null;
  
  const macd = macdLine[macdLine.length - 1];
  const signal = signalEMA[signalEMA.length - 1];
  const histogram = macd - signal;
  
  return { macd, signal, histogram };
}

/**
 * Calculate ADX (Average Directional Index)
 * Uses Wilder's smoothing method
 */
export function calculateADX(
  highs: number[],
  lows: number[],
  closes: number[],
  period: number = 14
): number | null {
  if (highs.length < period + 2 || lows.length < period + 2 || closes.length < period + 2) {
    return null;
  }
  
  // Calculate True Range, +DM, -DM
  const tr: number[] = [];
  const plusDM: number[] = [];
  const minusDM: number[] = [];
  
  for (let i = 1; i < closes.length; i++) {
    const hl = highs[i] - lows[i];
    const hc = Math.abs(highs[i] - closes[i - 1]);
    const lc = Math.abs(lows[i] - closes[i - 1]);
    tr.push(Math.max(hl, Math.max(hc, lc)));
    
    const upMove = highs[i] - highs[i - 1];
    const downMove = lows[i - 1] - lows[i];
    
    if (upMove > downMove && upMove > 0) {
      plusDM.push(upMove);
    } else {
      plusDM.push(0);
    }
    
    if (downMove > upMove && downMove > 0) {
      minusDM.push(downMove);
    } else {
      minusDM.push(0);
    }
  }
  
  if (tr.length < period) return null;
  
  // Wilder's smoothing for ATR, +DM, -DM
  let atrSum = 0;
  let pdmSum = 0;
  let mdmSum = 0;
  
  for (let i = 0; i < period; i++) {
    atrSum += tr[i];
    pdmSum += plusDM[i];
    mdmSum += minusDM[i];
  }
  
  // Calculate smoothed values
  const smoothedATR: number[] = [atrSum / period];
  const smoothedPDM: number[] = [pdmSum / period];
  const smoothedMDM: number[] = [mdmSum / period];
  
  for (let i = period; i < tr.length; i++) {
    smoothedATR.push((smoothedATR[smoothedATR.length - 1] * (period - 1) + tr[i]) / period);
    smoothedPDM.push((smoothedPDM[smoothedPDM.length - 1] * (period - 1) + plusDM[i]) / period);
    smoothedMDM.push((smoothedMDM[smoothedMDM.length - 1] * (period - 1) + minusDM[i]) / period);
  }
  
  // Calculate +DI and -DI
  const plusDI: number[] = [];
  const minusDI: number[] = [];
  
  for (let i = 0; i < smoothedATR.length; i++) {
    if (smoothedATR[i] === 0) {
      plusDI.push(0);
      minusDI.push(0);
    } else {
      plusDI.push((smoothedPDM[i] / smoothedATR[i]) * 100);
      minusDI.push((smoothedMDM[i] / smoothedATR[i]) * 100);
    }
  }
  
  // Calculate DX
  const dx: number[] = [];
  for (let i = 0; i < plusDI.length; i++) {
    const diSum = plusDI[i] + minusDI[i];
    if (diSum === 0) {
      dx.push(0);
    } else {
      dx.push((Math.abs(plusDI[i] - minusDI[i]) / diSum) * 100);
    }
  }
  
  if (dx.length < period) return null;
  
  // Calculate ADX (smoothed DX)
  let adxSum = 0;
  for (let i = 0; i < period; i++) {
    adxSum += dx[i];
  }
  let adx = adxSum / period;
  
  for (let i = period; i < dx.length; i++) {
    adx = (adx * (period - 1) + dx[i]) / period;
  }
  
  return adx;
}

/**
 * Calculate volume ratio (current vs N-day average)
 */
export function calculateVolumeRatio(volumes: number[], days: number = 20): number {
  if (volumes.length < days) return 1;
  
  const recentVolumes = volumes.slice(-days);
  const avgVolume = recentVolumes.reduce((a, b) => a + b, 0) / recentVolumes.length;
  
  if (avgVolume === 0) return 1;
  return volumes[volumes.length - 1] / avgVolume;
}

/**
 * Calculate Relative Strength Rating (RS Rating)
 * Compares stock's 12-month performance vs market (S&P 500 proxy)
 */
export function calculateRSRating(
  stockPrices: number[],
  marketPrices: number[],
  months: number = 12
): number {
  if (stockPrices.length < 20 || marketPrices.length < 20) return 50;
  
  // Use last ~252 trading days (12 months)
  const lookback = Math.min(252, Math.min(stockPrices.length, marketPrices.length));
  const stockReturn = (stockPrices[stockPrices.length - 1] - stockPrices[stockPrices.length - lookback]) / stockPrices[stockPrices.length - lookback];
  const marketReturn = (marketPrices[marketPrices.length - 1] - marketPrices[marketPrices.length - lookback]) / marketPrices[marketPrices.length - lookback];
  
  // RS Rating: 0-100 scale (50 = market performance)
  // If stock outperforms market by 2x, RS Rating = 75+
  const relativePerformance = stockReturn / (marketReturn + 0.001);
  
  // Convert to 0-100 scale (simplified)
  // Top 1% stocks get 99, top 10% get 90+, etc.
  let rsRating = 50;
  if (relativePerformance > 2.0) rsRating = 95;
  else if (relativePerformance > 1.5) rsRating = 85;
  else if (relativePerformance > 1.2) rsRating = 75;
  else if (relativePerformance > 1.0) rsRating = 65;
  else if (relativePerformance > 0.8) rsRating = 55;
  else if (relativePerformance > 0.5) rsRating = 45;
  else rsRating = 35;
  
  return Math.min(100, Math.max(0, rsRating));
}

/**
 * Check if price is in Stage-2 uptrend (Minervini style)
 * Stage 2: Price above rising 30-week MA (150-day SMA), with base formation
 */
export function isStage2Uptrend(prices: number[]): boolean {
  if (prices.length < 150) return false;
  
  const sma150 = prices.slice(-150).reduce((a, b) => a + b, 0) / 150;
  const sma150Prev = prices.slice(-151, -1).reduce((a, b) => a + b, 0) / 150;
  const currentPrice = prices[prices.length - 1];
  
  // Price above rising MA
  return currentPrice > sma150 && sma150 > sma150Prev;
}

/**
 * Calculate price vs 52-week high percentage
 */
export function getPriceVs52WHigh(currentPrice: number, high52Week?: number): number {
  if (!high52Week || high52Week === 0) return 0;
  return (currentPrice / high52Week) * 100;
}
