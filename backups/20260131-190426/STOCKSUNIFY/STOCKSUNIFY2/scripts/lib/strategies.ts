/**
 * STOCKSUNIFY2: Technical & Statistical Strategies
 * 
 * These strategies focus on "Falsifiability" and "Regime Awareness"
 */

import { StockData } from './stock-data-fetcher-enhanced';

export interface V2Pick {
    symbol: string;
    name: string;
    score: number;
    rating: 'STRONG BUY' | 'BUY' | 'HOLD' | 'SELL';
    algorithm: string;
    timeframe: string;
    risk: 'Low' | 'Medium' | 'High' | 'Very High';
    metrics: Record<string, any>;
    v2_hash: string;
}

/**
 * Strategy A: Regime-Aware Reversion (RAR)
 */
export function scoreRAR(data: StockData, marketData?: StockData): V2Pick | null {
    if (!data.history || data.history.length < 200) return null;

    const prices = data.history.map(h => h.close);
    const currentPrice = data.price;

    let isBullishRegime = true;
    if (marketData && marketData.history) {
        const spyPrices = marketData.history.map(h => h.close);
        const spySMA200 = spyPrices.slice(-200).reduce((a, b) => a + b, 0) / 200;
        isBullishRegime = marketData.price > spySMA200;
    }

    if (!isBullishRegime) return null;

    const sma200 = prices.slice(-200).reduce((a, b) => a + b, 0) / 200;
    if (currentPrice < sma200) return null;

    const rsi = calculateRSI(prices, 14);
    if (rsi < 40) {
        const score = Math.min(100, Math.max(0, (40 - rsi) * 2 + 60));
        return {
            symbol: data.symbol,
            name: data.name,
            score: Math.round(score),
            rating: score > 80 ? 'STRONG BUY' : 'BUY',
            algorithm: 'Regime-Aware Reversion (V2)',
            timeframe: '7d',
            risk: 'Medium',
            metrics: { rsi, sma200, regime: 'Bullish' },
            v2_hash: 'rar-v2.0.0-beta'
        };
    }
    return null;
}

/**
 * Strategy B: Volatility-Adjusted Momentum (VAM)
 */
export function scoreVAM(data: StockData): V2Pick | null {
    if (!data.history || data.history.length < 50) return null;

    const prices = data.history.map(h => h.close).slice(-60);
    const totalReturn = (data.price - prices[0]) / prices[0] * 100;
    if (totalReturn < 5) return null;

    const ulcerIndex = calculateUlcerIndex(prices);
    const scoreVal = (totalReturn / (ulcerIndex + 1)) * 10;
    const score = Math.min(100, Math.max(0, scoreVal + 40));

    if (score > 60) {
        return {
            symbol: data.symbol,
            name: data.name,
            score: Math.round(score),
            rating: score > 85 ? 'STRONG BUY' : 'BUY',
            algorithm: 'Volatility-Adjusted Momentum (V2)',
            timeframe: '1m',
            risk: 'Low',
            metrics: { ulcerIndex, totalReturn, martinRatio: totalReturn / (ulcerIndex + 0.001) },
            v2_hash: 'vam-v2.0.0-beta'
        };
    }
    return null;
}

/**
 * Strategy C: Liquidity-Shielded Penny (LSP)
 */
export function scoreLSP(data: StockData): V2Pick | null {
    if (data.price > 5 || data.price < 0.1) return null;

    const maxTradeDollars = data.avgVolume * data.price * 0.02;
    if (maxTradeDollars < 5000) return null;

    const tortureReturn = data.changePercent - 3.0; // 3% slippage stress
    if (tortureReturn < 1.0) return null;

    const score = Math.min(100, Math.max(0, (tortureReturn * 10) + 50));

    return {
        symbol: data.symbol,
        name: data.name,
        score: Math.round(score),
        rating: score > 80 ? 'STRONG BUY' : 'BUY',
        algorithm: 'Liquidity-Shielded Penny (V2)',
        timeframe: '24h',
        risk: 'Very High',
        metrics: { liquidityCap: maxTradeDollars, tortureReturn },
        v2_hash: 'lsp-v2.0.0-beta'
    };
}

/**
 * Strategy D: Scientific CAN SLIM (SCS)
 */
export function scoreScientificCANSLIM(data: StockData, marketData?: StockData): V2Pick | null {
    if (!data.history || data.history.length < 200) return null;

    let isBullishRegime = true;
    if (marketData && marketData.history) {
        const spySMA200 = marketData.history.slice(-200).reduce((a, b) => a + b, 0) / 200;
        isBullishRegime = marketData.price > spySMA200;
    }
    if (!isBullishRegime) return null;

    const prices = data.history.map(h => h.close);
    const sma200 = prices.slice(-200).reduce((a, b) => a + b, 0) / 200;
    if (data.price < sma200) return null;

    const yearlyReturn = (data.price - prices[0]) / prices[0];
    let score = 50;
    if (yearlyReturn > 0.40) score += 20;
    if (data.pe && data.pe < 40) score += 10;
    if (data.marketCap && data.marketCap > 1_000_000_000) score += 10;

    if (score > 60) {
        return {
            symbol: data.symbol,
            name: data.name,
            score: Math.round(Math.min(100, score)),
            rating: score > 85 ? 'STRONG BUY' : 'BUY',
            algorithm: 'Scientific CAN SLIM (V2)',
            timeframe: '1y',
            risk: 'Medium',
            metrics: { yearlyReturn, pe: data.pe, sma200 },
            v2_hash: 'scs-v2.0.0-beta'
        };
    }
    return null;
}

/**
 * Strategy E: Adversarial Trend (AT)
 */
export function scoreAdversarialTrend(data: StockData): V2Pick | null {
    if (!data.history || data.history.length < 50) return null;

    const prices = data.history.map(h => h.close);
    const sma20 = prices.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const sma50 = prices.slice(-50).reduce((a, b) => a + b, 0) / 50;

    if (sma20 <= sma50 || data.price <= sma20) return null;

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
            rating: score > 85 ? 'STRONG BUY' : 'BUY',
            algorithm: 'Adversarial Trend (V2)',
            timeframe: '1m',
            risk: 'Medium',
            metrics: { trendStrength, avgVolatilty },
            v2_hash: 'at-v2.0.0-beta'
        };
    }
    return null;
}

function calculateRSI(prices: number[], periods: number = 14): number {
    if (prices.length < periods + 1) return 50;
    let gains = 0; let losses = 0;
    for (let i = prices.length - periods; i < prices.length; i++) {
        const diff = prices[i] - prices[i - 1];
        if (diff >= 0) gains += diff; else losses -= diff;
    }
    if (losses === 0) return 100;
    const rs = gains / losses;
    return 100 - (100 / (1 + rs));
}

function calculateUlcerIndex(prices: number[]): number {
    let maxPrice = 0; let sumSquaredDrawdowns = 0;
    for (const price of prices) {
        if (price > maxPrice) maxPrice = price;
        else {
            const drawdown = (price - maxPrice) / maxPrice * 100;
            sumSquaredDrawdowns += Math.pow(drawdown, 2);
        }
    }
    return Math.sqrt(sumSquaredDrawdowns / prices.length);
}
