/**
 * STOCKSUNIFY2: Technical & Statistical Strategies
 *
 * These strategies focus on "Falsifiability" and "Regime Awareness"
 */

export interface StockData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  avgVolume: number;
  marketCap?: number;
  pe?: number;
  history?: {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[];
}

export interface V2Pick {
  symbol: string;
  name: string;
  score: number;
  rating: "STRONG BUY" | "BUY" | "HOLD" | "SELL";
  algorithm: string;
  timeframe: string;
  risk: "Low" | "Medium" | "High" | "Very High";
  metrics: Record<string, any>;
  v2_hash: string;
}

/**
 * Strategy A: Regime-Aware Reversion (RAR)
 * Uses Market Regime + RSI + Trend Verification
 */
export function scoreRAR(
  data: StockData,
  marketData?: StockData,
): V2Pick | null {
  if (!data.history || data.history.length < 200) return null;

  const prices = data.history.map((h) => h.close);
  const currentPrice = data.price;

  // 1. Regime Check (Is market calm/bullish?)
  // If marketData provided, check if S&P 500 is > 200-day MA
  let isBullishRegime = true;
  if (marketData && marketData.history) {
    const spyPrices = marketData.history.map((h) => h.close);
    const spySMA200 = spyPrices.slice(-200).reduce((a, b) => a + b, 0) / 200;
    isBullishRegime = marketData.price > spySMA200;
  }

  if (!isBullishRegime) return null; // Strategy shuts down in Bear/Storm

  // 2. Trend Verification (Is stock currently in long-term uptrend?)
  const sma200 = prices.slice(-200).reduce((a, b) => a + b, 0) / 200;
  const isUptrend = currentPrice > sma200;
  if (!isUptrend) return null;

  // 3. RSI Overbought/Oversold
  const rsi = calculateRSI(prices, 14);

  // Strategy: Buy high-quality stocks in an uptrend that have a short-term dip
  if (rsi < 40) {
    const score = Math.min(100, Math.max(0, (40 - rsi) * 2 + 60));
    return {
      symbol: data.symbol,
      name: data.name,
      score: Math.round(score),
      rating: score > 80 ? "STRONG BUY" : "BUY",
      algorithm: "Regime-Aware Reversion (V2)",
      timeframe: "7d",
      risk: "Medium",
      metrics: { rsi, sma200, regime: "Bullish" },
      v2_hash: "rar-v2.0.0-alpha",
    };
  }

  return null;
}

/**
 * Strategy B: Volatility-Adjusted Momentum (VAM)
 * Ranks stocks by Return / Ulcer Index
 */
export function scoreVAM(data: StockData): V2Pick | null {
  if (!data.history || data.history.length < 50) return null;

  const prices = data.history.map((h) => h.close).slice(-60); // Last 60 days
  const totalReturn = ((data.price - prices[0]) / prices[0]) * 100;

  // Only care if it's actually going up
  if (totalReturn < 5) return null;

  const ulcerIndex = calculateUlcerIndex(prices);

  // Performance Ratio (Similar to Martin Ratio)
  // We want maximum return with minimum drawdown "duration/depth"
  const scoreVal = (totalReturn / (ulcerIndex + 1)) * 10;
  const score = Math.min(100, Math.max(0, scoreVal + 40));

  if (score > 60) {
    return {
      symbol: data.symbol,
      name: data.name,
      score: Math.round(score),
      rating: score > 85 ? "STRONG BUY" : "BUY",
      algorithm: "Volatility-Adjusted Momentum (V2)",
      timeframe: "1m",
      risk: "Low",
      metrics: {
        ulcerIndex,
        totalReturn,
        martinRatio: totalReturn / ulcerIndex,
      },
      v2_hash: "vam-v2.0.0-alpha",
    };
  }

  return null;
}

/**
 * Utility: RSI Calculation
 */
function calculateRSI(prices: number[], periods: number = 14): number {
  if (prices.length < periods + 1) return 50;

  let gains = 0;
  let losses = 0;

  for (let i = prices.length - periods; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  if (losses === 0) return 100;
  const rs = gains / losses;
  return 100 - 100 / (1 + rs);
}

/**
 * Utility: Z-Score Calculation
 * How many standard deviations a value is from the mean
 */
function calculateZScore(value: number, historicalValues: number[]): number {
  if (historicalValues.length < 2) return 0;
  const mean =
    historicalValues.reduce((a, b) => a + b, 0) / historicalValues.length;
  const variance =
    historicalValues.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) /
    historicalValues.length;
  const stdDev = Math.sqrt(variance);
  if (stdDev === 0) return 0;
  return (value - mean) / stdDev;
}

/**
 * Utility: Volume Z-Score
 * Statistical significance of current volume vs historical
 */
function calculateVolumeZScore(
  currentVolume: number,
  volumeHistory: number[],
): number {
  return calculateZScore(currentVolume, volumeHistory);
}

/**
 * Utility: RSI Z-Score
 * How extreme is current RSI relative to its own history
 */
function calculateRSIZScore(
  prices: number[],
  periods: number = 14,
): { rsi: number; zScore: number } {
  const rsi = calculateRSI(prices, periods);

  // Calculate historical RSI values
  const rsiHistory: number[] = [];
  for (let i = periods + 20; i <= prices.length; i++) {
    rsiHistory.push(calculateRSI(prices.slice(0, i), periods));
  }

  const zScore = calculateZScore(rsi, rsiHistory.slice(-50));
  return { rsi, zScore };
}

/**
 * Utility: ATR (Average True Range) Calculation
 */
function calculateATR(
  history: { high: number; low: number; close: number }[],
  periods: number = 14,
): number {
  if (history.length < periods + 1) return 0;

  const trueRanges: number[] = [];
  for (let i = 1; i < history.length; i++) {
    const high = history[i].high;
    const low = history[i].low;
    const prevClose = history[i - 1].close;
    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low - prevClose),
    );
    trueRanges.push(tr);
  }

  return trueRanges.slice(-periods).reduce((a, b) => a + b, 0) / periods;
}

/**
 * Utility: Ulcer Index Calculation
 * Measures the square root of the mean of squared "Drawdowns from Peak"
 */
function calculateUlcerIndex(prices: number[]): number {
  let maxPrice = 0;
  let sumSquaredDrawdowns = 0;

  for (const price of prices) {
    if (price > maxPrice) {
      maxPrice = price;
    } else {
      const drawdown = ((price - maxPrice) / maxPrice) * 100;
      sumSquaredDrawdowns += Math.pow(drawdown, 2);
    }
  }

  return Math.sqrt(sumSquaredDrawdowns / prices.length);
}

/**
 * Utility: Check Breakout Pattern
 */
function checkBreakout(
  history: { high: number; close: number }[],
  periods: number = 20,
): boolean {
  if (history.length < periods) return false;
  const recentHighs = history.slice(-periods, -1).map((h) => h.high);
  const maxHigh = Math.max(...recentHighs);
  const currentClose = history[history.length - 1].close;
  return currentClose > maxHigh;
}

/**
 * Strategy C: Liquidity-Shielded Penny (LSP)
 * Implements "Slippage Torture" and "Volume Cap" checks
 */
export function scoreLSP(data: StockData): V2Pick | null {
  // 1. Penny Stock Definition: Price < $5
  if (data.price > 5 || data.price < 0.1) return null;

  // 2. Volume Cap Interrogation
  // Never assume we can trade >2% of daily volume
  const maxTradeDollars = data.avgVolume * data.price * 0.02;
  if (maxTradeDollars < 5000) return null; // If we can't trade $5k without moving the market, ignore it

  // 3. Slippage Torture Test
  // Expected return must survive a 3x "Slippage Multiplier" (e.g. 3% penalty)
  const shortTermReturn = data.changePercent;
  const slippagePenalty = 3.0; // 3%
  const tortureAdjustedReturn = shortTermReturn - slippagePenalty;

  if (tortureAdjustedReturn < 1.0) return null; // If it doesn't survive 3% slippage, it's a "Liquidity Mirage"

  // 4. Momentum Check
  if (data.changePercent < 2) return null;

  const score = Math.min(100, Math.max(0, tortureAdjustedReturn * 10 + 50));

  return {
    symbol: data.symbol,
    name: data.name,
    score: Math.round(score),
    rating: score > 80 ? "STRONG BUY" : "BUY",
    algorithm: "Liquidity-Shielded Penny (V2)",
    timeframe: "24h",
    risk: "Very High",
    metrics: {
      avgVolume: data.avgVolume,
      liquidityCap: maxTradeDollars,
      tortureReturn: tortureAdjustedReturn,
    },
    v2_hash: "lsp-v2.0.0-alpha",
  };
}

/**
 * Strategy D: Scientific CAN SLIM (SCS)
 * Traditional growth + Regime filtering + Fundamental Lag protection
 */
export function scoreScientificCANSLIM(
  data: StockData,
  marketData?: StockData,
): V2Pick | null {
  if (!data.history || data.history.length < 200) return null;

  // 1. Regime Guard
  let isBullishRegime = true;
  if (marketData && marketData.history) {
    const spyPrices = marketData.history.map((h) => h.close);
    const spySMA200 = spyPrices.slice(-200).reduce((a, b) => a + b, 0) / 200;
    isBullishRegime = marketData.price > spySMA200;
  }
  if (!isBullishRegime) return null;

  const prices = data.history.map((h) => h.close);
  const sma200 = prices.slice(-200).reduce((a, b) => a + b, 0) / 200;

  // Trend Filter
  if (data.price < sma200) return null;

  // 2. Yearly Return as RS Proxy
  const yearlyReturn = (data.price - prices[0]) / prices[0];

  // 3. Scoring
  let score = 50;
  if (yearlyReturn > 0.4) score += 20;
  if (data.pe && data.pe < 40) score += 10;
  if (data.marketCap && data.marketCap > 1_000_000_000) score += 10;

  // 4. Slippage Penalty
  const adjustedReturn = yearlyReturn * 100 - 1.5;

  if (score > 60) {
    return {
      symbol: data.symbol,
      name: data.name,
      score: Math.round(Math.min(100, score)),
      rating: score > 85 ? "STRONG BUY" : "BUY",
      algorithm: "Scientific CAN SLIM (V2)",
      timeframe: "1y",
      risk: "Medium",
      metrics: { yearlyReturn, pe: data.pe, sma200, adjustedReturn },
      v2_hash: "scs-v2.0.0-alpha",
    };
  }
  return null;
}

/**
 * Strategy E: Institutional Footprint (IF)
 * Based on Research Paper: Volume Z-Score > 2.0 indicates significant institutional entry
 * Combined with trend confirmation
 */
export function scoreInstitutionalFootprint(data: StockData): V2Pick | null {
  if (!data.history || data.history.length < 50) return null;

  const prices = data.history.map((h) => h.close);
  const volumes = data.history.map((h) => h.volume);

  // 1. Volume Z-Score - Institutional activity detection
  const volumeZScore = calculateVolumeZScore(data.volume, volumes.slice(-20));

  // Must have statistically significant volume (> 2.0 sigma)
  if (volumeZScore < 2.0) return null;

  // 2. RSI Z-Score - Extreme momentum detection
  const { rsi, zScore: rsiZScore } = calculateRSIZScore(prices);

  // 3. Trend Confirmation (price > 20 SMA)
  const sma20 = prices.slice(-20).reduce((a, b) => a + b, 0) / 20;
  const isUptrend = data.price > sma20;

  // 4. Breakout Check
  const breakout = checkBreakout(data.history, 20);

  // Score calculation
  let score = 40;

  // Volume significance (max 30 points)
  if (volumeZScore > 3.0) score += 30;
  else if (volumeZScore > 2.5) score += 25;
  else score += 20;

  // Trend bonus (max 20 points)
  if (isUptrend) score += 15;
  if (breakout) score += 5;

  // RSI positioning (max 10 points) - prefer slightly oversold in uptrend
  if (rsi >= 40 && rsi <= 60) score += 10;
  else if (rsi >= 30 && rsi <= 70) score += 5;

  // Market cap quality filter
  if (data.marketCap && data.marketCap > 1_000_000_000) score += 5;

  score = Math.min(100, Math.max(0, score));

  if (score >= 65) {
    return {
      symbol: data.symbol,
      name: data.name,
      score: Math.round(score),
      rating: score > 85 ? "STRONG BUY" : "BUY",
      algorithm: "Institutional Footprint (V2)",
      timeframe: "1w",
      risk:
        data.marketCap && data.marketCap > 10_000_000_000 ? "Low" : "Medium",
      metrics: {
        volumeZScore: Math.round(volumeZScore * 100) / 100,
        rsi,
        rsiZScore: Math.round(rsiZScore * 100) / 100,
        breakout,
        sma20,
      },
      v2_hash: "if-v2.0.0-alpha",
    };
  }

  return null;
}

/**
 * Strategy F: Adversarial Trend (AT)
 * Uses volatility-normalized trend following
 */
export function scoreAdversarialTrend(data: StockData): V2Pick | null {
  if (!data.history || data.history.length < 50) return null;

  const prices = data.history.map((h) => h.close);
  const sma20 = prices.slice(-20).reduce((a, b) => a + b, 0) / 20;
  const sma50 = prices.slice(-50).reduce((a, b) => a + b, 0) / 50;

  // Golden Cross / Trend Alignment
  if (sma20 <= sma50 || data.price <= sma20) return null;

  // Volatility Normalization
  const returns = [];
  for (let i = 1; i < prices.length; i++) {
    returns.push(Math.abs(prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  const avgVolatilty = returns.slice(-20).reduce((a, b) => a + b, 0) / 20;

  const trendStrength = (data.price - sma50) / sma50;
  const scoreVal = (trendStrength / (avgVolatilty + 0.01)) * 5;
  const score = Math.min(100, Math.max(0, scoreVal + 40));

  if (score > 65) {
    return {
      symbol: data.symbol,
      name: data.name,
      score: Math.round(score),
      rating: score > 85 ? "STRONG BUY" : "BUY",
      algorithm: "Adversarial Trend (V2)",
      timeframe: "1m",
      risk: "Medium",
      metrics: { trendStrength, avgVolatilty, signalDensity: scoreVal },
      v2_hash: "at-v2.0.0-alpha",
    };
  }
  return null;
}
