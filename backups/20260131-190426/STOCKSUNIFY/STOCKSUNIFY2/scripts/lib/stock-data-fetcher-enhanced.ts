/**
 * Enhanced Stock Data Fetcher
 * Uses multiple API sources with fallbacks
 *
 * Priority:
 * 1. Yahoo Finance (free, no key)
 * 2. Polygon.io (premium data)
 * 3. Twelve Data (good free tier)
 * 4. Finnhub (real-time data)
 * 5. Tiingo (backup)
 */

import { STOCK_API_KEYS, API_PRIORITY } from "./stock-api-keys";

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
  high52Week?: number;
  low52Week?: number;
  history?: {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[];
}

/**
 * Fetch stock data from Yahoo Finance (primary, free)
 */
async function fetchFromYahoo(symbol: string): Promise<StockData | null> {
  try {
    const quoteUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1y`;
    const infoUrl = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${symbol}?modules=summaryProfile,financialData,defaultKeyStatistics`;

    const [quoteResponse, infoResponse] = await Promise.all([
      fetch(quoteUrl),
      fetch(infoUrl).catch(() => null),
    ]);

    if (!quoteResponse.ok) {
      return null;
    }

    const quoteData = await quoteResponse.json();
    const result = quoteData.chart?.result?.[0];
    if (!result) return null;

    const meta = result.meta || {};
    const timestamps = result.timestamp || [];
    const closes = result.indicators?.quote?.[0]?.close || [];
    const volumes = result.indicators?.quote?.[0]?.volume || [];
    const highs = result.indicators?.quote?.[0]?.high || [];
    const lows = result.indicators?.quote?.[0]?.low || [];
    const opens = result.indicators?.quote?.[0]?.open || [];

    const currentPrice = meta.regularMarketPrice || meta.previousClose || 0;
    const previousClose = meta.previousClose || currentPrice;
    const change = currentPrice - previousClose;
    const changePercent = previousClose ? (change / previousClose) * 100 : 0;

    const recentVolumes = volumes.slice(-50).filter((v: number) => v > 0);
    const avgVolume =
      recentVolumes.length > 0
        ? recentVolumes.reduce((a: number, b: number) => a + b, 0) /
          recentVolumes.length
        : meta.regularMarketVolume || 0;

    const history = timestamps
      .map((ts: number, i: number) => ({
        date: new Date(ts * 1000).toISOString().split("T")[0],
        open: opens[i] || 0,
        high: highs[i] || 0,
        low: lows[i] || 0,
        close: closes[i] || 0,
        volume: volumes[i] || 0,
      }))
      .filter((h: any) => h.close > 0);

    let marketCap, pe, high52Week, low52Week;
    if (infoResponse?.ok) {
      try {
        const infoData = await infoResponse.json();
        const summary = infoData.quoteSummary?.result?.[0];
        if (summary) {
          marketCap =
            summary.summaryProfile?.marketCap ||
            summary.defaultKeyStatistics?.marketCap?.raw;
          pe = summary.defaultKeyStatistics?.trailingPE?.raw;
          high52Week = summary.defaultKeyStatistics?.fiftyTwoWeekHigh?.raw;
          low52Week = summary.defaultKeyStatistics?.fiftyTwoWeekLow?.raw;
        }
      } catch (e) {
        // Ignore
      }
    }

    return {
      symbol: symbol.toUpperCase(),
      name: meta.longName || meta.shortName || symbol,
      price: currentPrice,
      change,
      changePercent,
      volume: meta.regularMarketVolume || 0,
      avgVolume,
      marketCap,
      pe,
      high52Week,
      low52Week,
      history,
    };
  } catch (error) {
    return null;
  }
}

/**
 * Fetch stock data from Polygon.io
 */
async function fetchFromPolygon(symbol: string): Promise<StockData | null> {
  try {
    const apiKey = STOCK_API_KEYS.POLYGON;
    if (!apiKey) return null;

    // Get current quote
    const quoteUrl = `https://api.polygon.io/v2/aggs/ticker/${symbol}/prev?adjusted=true&apikey=${apiKey}`;
    const quoteResponse = await fetch(quoteUrl);

    if (!quoteResponse.ok) return null;

    const quoteData = await quoteResponse.json();
    if (!quoteData.results || quoteData.results.length === 0) return null;

    const prev = quoteData.results[0];
    const price = prev.c; // Close price
    const volume = prev.v;

    // Get historical data (last year)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(startDate.getFullYear() - 1);

    const historyUrl = `https://api.polygon.io/v2/aggs/ticker/${symbol}/range/1/day/${startDate.toISOString().split("T")[0]}/${endDate.toISOString().split("T")[0]}?adjusted=true&sort=asc&apikey=${apiKey}`;
    const historyResponse = await fetch(historyUrl);

    let history: any[] = [];
    if (historyResponse.ok) {
      const historyData = await historyResponse.json();
      if (historyData.results) {
        history = historyData.results.map((r: any) => ({
          date: new Date(r.t).toISOString().split("T")[0],
          open: r.o,
          high: r.h,
          low: r.l,
          close: r.c,
          volume: r.v,
        }));
      }
    }

    // Get company info
    const tickerUrl = `https://api.polygon.io/v3/reference/tickers/${symbol}?apikey=${apiKey}`;
    const tickerResponse = await fetch(tickerUrl);
    let name = symbol;
    let marketCap: number | undefined;

    if (tickerResponse.ok) {
      const tickerData = await tickerResponse.json();
      if (tickerData.results) {
        name = tickerData.results.name || symbol;
        marketCap = tickerData.results.market_cap;
      }
    }

    const previousClose =
      history.length > 0 ? history[history.length - 1].close : price;
    const change = price - previousClose;
    const changePercent = previousClose ? (change / previousClose) * 100 : 0;

    const recentVolumes = history
      .slice(-50)
      .map((h: any) => h.volume)
      .filter((v: number) => v > 0);
    const avgVolume =
      recentVolumes.length > 0
        ? recentVolumes.reduce((a: number, b: number) => a + b, 0) /
          recentVolumes.length
        : volume;

    return {
      symbol: symbol.toUpperCase(),
      name,
      price,
      change,
      changePercent,
      volume,
      avgVolume,
      marketCap,
      history,
    };
  } catch (error) {
    return null;
  }
}

/**
 * Fetch stock data from Finnhub
 */
async function fetchFromFinnhub(symbol: string): Promise<StockData | null> {
  try {
    const apiKey = STOCK_API_KEYS.FINNHUB;
    if (!apiKey) return null;

    // Get quote
    const quoteUrl = `https://finnhub.io/api/v1/quote?symbol=${symbol}&token=${apiKey}`;
    const quoteResponse = await fetch(quoteUrl);

    if (!quoteResponse.ok) return null;

    const quoteData = await quoteResponse.json();
    if (!quoteData.c) return null; // No current price

    const price = quoteData.c;
    const previousClose = quoteData.pc || price;
    const change = price - previousClose;
    const changePercent = previousClose ? (change / previousClose) * 100 : 0;
    const high = quoteData.h;
    const low = quoteData.l;
    const volume = quoteData.v || 0;

    // Get company profile (try new key if first fails)
    let profileUrl = `https://finnhub.io/api/v1/stock/profile2?symbol=${symbol}&token=${apiKey}`;
    let profileResponse = await fetch(profileUrl);

    // Try new Finnhub key if first fails
    if (!profileResponse.ok && STOCK_API_KEYS.FINNHUB_NEW) {
      profileUrl = `https://finnhub.io/api/v1/stock/profile2?symbol=${symbol}&token=${STOCK_API_KEYS.FINNHUB_NEW}`;
      profileResponse = await fetch(profileUrl);
    }

    let name = symbol;
    let marketCap: number | undefined;

    if (profileResponse.ok) {
      const profileData = await profileResponse.json();
      if (profileData.name) {
        name = profileData.name;
        marketCap = profileData.marketCapitalization;
      }
    }

    // Get historical data (candles)
    const endTime = Math.floor(Date.now() / 1000);
    const startTime = endTime - 365 * 24 * 60 * 60; // 1 year ago

    const candlesUrl = `https://finnhub.io/api/v1/stock/candle?symbol=${symbol}&resolution=D&from=${startTime}&to=${endTime}&token=${apiKey}`;
    const candlesResponse = await fetch(candlesUrl);

    let history: any[] = [];
    if (candlesResponse.ok) {
      const candlesData = await candlesResponse.json();
      if (candlesData.s === "ok" && candlesData.c) {
        history = candlesData.c.map((close: number, i: number) => ({
          date: new Date(candlesData.t[i] * 1000).toISOString().split("T")[0],
          open: candlesData.o[i],
          high: candlesData.h[i],
          low: candlesData.l[i],
          close,
          volume: candlesData.v[i],
        }));
      }
    }

    const recentVolumes = history
      .slice(-50)
      .map((h: any) => h.volume)
      .filter((v: number) => v > 0);
    const avgVolume =
      recentVolumes.length > 0
        ? recentVolumes.reduce((a: number, b: number) => a + b, 0) /
          recentVolumes.length
        : volume;

    return {
      symbol: symbol.toUpperCase(),
      name,
      price,
      change,
      changePercent,
      volume,
      avgVolume,
      marketCap,
      high52Week: high,
      low52Week: low,
      history,
    };
  } catch (error) {
    return null;
  }
}

/**
 * Fetch stock data from Twelve Data
 */
async function fetchFromTwelveData(symbol: string): Promise<StockData | null> {
  try {
    const apiKey = STOCK_API_KEYS.TWELVE_DATA;
    if (!apiKey) return null;

    // Get real-time quote
    const quoteUrl = `https://api.twelvedata.com/price?symbol=${symbol}&apikey=${apiKey}`;
    const quoteResponse = await fetch(quoteUrl);

    if (!quoteResponse.ok) return null;

    const quoteData = await quoteResponse.json();
    if (quoteData.status === "error" || !quoteData.price) return null;

    const price = parseFloat(quoteData.price);

    // Get time series (historical data)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(startDate.getFullYear() - 1);

    const historyUrl = `https://api.twelvedata.com/time_series?symbol=${symbol}&interval=1day&start_date=${startDate.toISOString().split("T")[0]}&end_date=${endDate.toISOString().split("T")[0]}&apikey=${apiKey}`;
    const historyResponse = await fetch(historyUrl);

    let history: any[] = [];
    let previousClose = price;
    let avgVolume = 0;

    if (historyResponse.ok) {
      const historyData = await historyResponse.json();
      if (historyData.values && Array.isArray(historyData.values)) {
        history = historyData.values
          .map((v: any) => ({
            date: v.datetime.split(" ")[0],
            open: parseFloat(v.open),
            high: parseFloat(v.high),
            low: parseFloat(v.low),
            close: parseFloat(v.close),
            volume: parseFloat(v.volume) || 0,
          }))
          .reverse(); // Reverse to chronological order

        if (history.length > 0) {
          previousClose = history[history.length - 1].close;
        }

        const recentVolumes = history
          .slice(-50)
          .map((h: any) => h.volume)
          .filter((v: number) => v > 0);
        avgVolume =
          recentVolumes.length > 0
            ? recentVolumes.reduce((a: number, b: number) => a + b, 0) /
              recentVolumes.length
            : 0;
      }
    }

    // Get company profile
    const profileUrl = `https://api.twelvedata.com/profile?symbol=${symbol}&apikey=${apiKey}`;
    const profileResponse = await fetch(profileUrl);

    let name = symbol;
    let marketCap: number | undefined;

    if (profileResponse.ok) {
      const profileData = await profileResponse.json();
      if (profileData.name) {
        name = profileData.name;
        marketCap = profileData.market_cap
          ? parseFloat(profileData.market_cap)
          : undefined;
      }
    }

    const change = price - previousClose;
    const changePercent = previousClose ? (change / previousClose) * 100 : 0;

    return {
      symbol: symbol.toUpperCase(),
      name,
      price,
      change,
      changePercent,
      volume: 0, // Twelve Data doesn't provide current volume in price endpoint
      avgVolume,
      marketCap,
      history,
    };
  } catch (error) {
    return null;
  }
}

/**
 * Main fetch function with fallbacks
 */
export async function fetchStockData(
  symbol: string,
): Promise<StockData | null> {
  // Try APIs in priority order
  for (const api of API_PRIORITY) {
    try {
      let data: StockData | null = null;

      switch (api) {
        case "YAHOO_FINANCE":
          data = await fetchFromYahoo(symbol);
          break;
        case "POLYGON":
          data = await fetchFromPolygon(symbol);
          break;
        case "TWELVE_DATA":
          data = await fetchFromTwelveData(symbol);
          break;
        case "FINNHUB":
          data = await fetchFromFinnhub(symbol);
          break;
        default:
          continue;
      }

      if (data) {
        console.log(`✅ Fetched ${symbol} from ${api}`);
        return data;
      }
    } catch (error) {
      console.warn(`⚠️  ${api} failed for ${symbol}, trying next...`);
      continue;
    }
  }

  console.error(`❌ All APIs failed for ${symbol}`);
  return null;
}

export async function fetchMultipleStocks(
  symbols: string[],
): Promise<StockData[]> {
  const results: StockData[] = [];

  // Fetch in batches to avoid rate limiting
  const batchSize = 5;
  for (let i = 0; i < symbols.length; i += batchSize) {
    const batch = symbols.slice(i, i + batchSize);
    const batchResults = await Promise.all(
      batch.map((symbol) => fetchStockData(symbol)),
    );

    results.push(...batchResults.filter((r): r is StockData => r !== null));

    // Small delay between batches to respect rate limits
    if (i + batchSize < symbols.length) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  return results;
}
