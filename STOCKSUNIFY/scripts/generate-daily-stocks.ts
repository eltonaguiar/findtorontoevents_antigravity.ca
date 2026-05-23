#!/usr/bin/env tsx
/**
 * Daily Stock Picks Generator
 *
 * This script generates daily stock picks by combining multiple algorithms:
 * - CAN SLIM Growth Screener (long-term)
 * - Technical Momentum (short-term)
 * - Composite Rating (medium-term)
 *
 * Output: data/daily-stocks.json
 */

import * as fs from "fs";
import * as path from "path";
// Use enhanced fetcher with multi-API fallbacks (Yahoo, Polygon, Twelve Data, Finnhub)
import { fetchMultipleStocks } from "./lib/stock-data-fetcher-enhanced";
import {
  scoreCANSLIM,
  scoreTechnicalMomentum,
  scoreComposite,
} from "./lib/stock-scorers";
import type { StockPick } from "./lib/stock-scorers";

// EXPANDED stock universe to generate more picks
// Mix of large cap, mid cap, growth, value, and momentum stocks
const STOCK_UNIVERSE = [
  // Large Cap Tech
  "AAPL",
  "MSFT",
  "GOOGL",
  "GOOG",
  "AMZN",
  "NVDA",
  "META",
  "TSLA",
  "NFLX",
  // Growth Stocks
  "AMD",
  "INTC",
  "CRM",
  "ADBE",
  "PYPL",
  "NOW",
  "SNOW",
  "PLTR",
  "DOCN",
  "NET",
  "CRWD",
  "ZS",
  "PANW",
  "DDOG",
  "MDB",
  "OKTA",
  // Financials
  "JPM",
  "BAC",
  "GS",
  "MS",
  "V",
  "MA",
  "AXP",
  "WFC",
  "C",
  "BLK",
  "SCHW",
  // Consumer
  "WMT",
  "TGT",
  "HD",
  "LOW",
  "NKE",
  "SBUX",
  "MCD",
  "COST",
  "TJX",
  "ROST",
  // Energy
  "XOM",
  "CVX",
  "SLB",
  "COP",
  "EOG",
  "MPC",
  "VLO",
  // Healthcare
  "JNJ",
  "PFE",
  "UNH",
  "ABBV",
  "TMO",
  "ABT",
  "LLY",
  "MRK",
  "BMY",
  // Industrials
  "BA",
  "CAT",
  "GE",
  "HON",
  "RTX",
  "LMT",
  "NOC",
  // Communication Services
  "DIS",
  "CMCSA",
  "VZ",
  "T",
  "NFLX",
  "GOOGL",
  "META",
  // Materials
  "LIN",
  "APD",
  "ECL",
  "SHW",
  "DD",
  // Real Estate
  "AMT",
  "PLD",
  "EQIX",
  "PSA",
  // Utilities
  "NEE",
  "DUK",
  "SO",
  "D",
  // Penny/Momentum (for short-term screener)
  "GME",
  "AMC",
  "BB",
  "SNDL",
  "NAKD",
  // Additional momentum plays
  "RIVN",
  "LCID",
  "F",
  "GM",
  "RBLX",
  "HOOD",
  "SOFI",
  "AFRM",
  "UPST",
  "OPEN",
  // Crypto-related
  "COIN",
  "MSTR",
  "SQ",
  "PYPL",
  // Biotech/Pharma momentum
  "MRNA",
  "BNTX",
  "NVAX",
  "GILD",
  "REGN",
  // Semiconductor momentum
  "AVGO",
  "QCOM",
  "TXN",
  "MU",
  "LRCX",
  "AMAT",
  "KLAC",
  // Cloud/SaaS
  "WDAY",
  "VEEV",
  "TEAM",
  "ZM",
  "FTNT",
  "SPLK",
];

async function generateStockPicks(): Promise<StockPick[]> {
  console.log("📊 Fetching stock data...");
  const stockData = await fetchMultipleStocks(STOCK_UNIVERSE);
  console.log(`✅ Fetched data for ${stockData.length} stocks`);

  const picks: StockPick[] = [];
  const algorithmStats: Record<string, number> = {};

  // 1. CAN SLIM Growth Screener (Long-term: 3m, 6m, 1y)
  console.log("\n🔍 Running CAN SLIM Growth Screener (Long-term)...");
  for (const data of stockData) {
    const score = scoreCANSLIM(data);
    if (score && score.score >= 30) {
      // RELAXED: Lower threshold from 40 to 30 to generate more picks (goal: 5-20 picks/day)
      picks.push(score);
      algorithmStats[score.algorithm] =
        (algorithmStats[score.algorithm] || 0) + 1;
      console.log(
        `  ✓ ${score.symbol}: ${score.score}/100 (${score.rating}) - ${score.timeframe}`,
      );
    }
  }

  // 2. Technical Momentum - All Timeframes
  const momentumTimeframes: Array<"24h" | "3d" | "7d"> = ["24h", "3d", "7d"];
  for (const timeframe of momentumTimeframes) {
    console.log(`\n🔍 Running Technical Momentum Screener (${timeframe})...`);
    for (const data of stockData) {
      const score = scoreTechnicalMomentum(data, timeframe);
      if (score && score.score >= 35) {
        // RELAXED: Lower threshold from 45 to 35 to generate more trades (goal: 20+ trades/day)
        picks.push(score);
        algorithmStats[`Technical Momentum (${timeframe})`] =
          (algorithmStats[`Technical Momentum (${timeframe})`] || 0) + 1;
        console.log(
          `  ✓ ${score.symbol}: ${score.score}/100 (${score.rating})`,
        );
      }
    }
  }

  // 3. Composite Rating Engine (Medium-term: 1m, 3m)
  console.log("\n🔍 Running Composite Rating Engine (Medium-term)...");
  for (const data of stockData) {
    const score = scoreComposite(data);
    if (score && score.score >= 50) {
      // Keep threshold for quality
      picks.push(score);
      algorithmStats[score.algorithm] =
        (algorithmStats[score.algorithm] || 0) + 1;
      console.log(`  ✓ ${score.symbol}: ${score.score}/100 (${score.rating})`);
    }
  }

  // Print algorithm statistics
  console.log("\n📊 Algorithm Statistics:");
  for (const [algorithm, count] of Object.entries(algorithmStats)) {
    console.log(`  • ${algorithm}: ${count} picks`);
  }

  // Group picks by algorithm for better organization
  const picksByAlgorithm = new Map<string, StockPick[]>();
  for (const pick of picks) {
    const key = pick.algorithm;
    if (!picksByAlgorithm.has(key)) {
      picksByAlgorithm.set(key, []);
    }
    picksByAlgorithm.get(key)!.push(pick);
  }

  // Sort each algorithm's picks by score
  for (const [algorithm, algorithmPicks] of picksByAlgorithm.entries()) {
    algorithmPicks.sort((a, b) => b.score - a.score);
  }

  // Combine picks: prioritize STRONG BUY, then BUY, sorted by score
  const strongBuys = picks
    .filter((p) => p.rating === "STRONG BUY")
    .sort((a, b) => b.score - a.score);
  const buys = picks
    .filter((p) => p.rating === "BUY")
    .sort((a, b) => b.score - a.score);
  const holds = picks
    .filter((p) => p.rating === "HOLD")
    .sort((a, b) => b.score - a.score);

  // Remove duplicates (same symbol + algorithm) - keep highest score
  const uniquePicks = new Map<string, StockPick>();
  for (const pick of picks) {
    const key = `${pick.symbol}-${pick.algorithm}-${pick.timeframe}`;
    const existing = uniquePicks.get(key);
    if (!existing || pick.score > existing.score) {
      uniquePicks.set(key, pick);
    }
  }

  const finalPicks = Array.from(uniquePicks.values());

  // Sort by rating priority (STRONG BUY > BUY > HOLD) then by score
  finalPicks.sort((a, b) => {
    const ratingOrder = { "STRONG BUY": 3, BUY: 2, HOLD: 1, SELL: 0 };
    const ratingDiff = ratingOrder[b.rating] - ratingOrder[a.rating];
    if (ratingDiff !== 0) return ratingDiff;
    return b.score - a.score;
  });

  // Return top picks (increased limit to show more variety)
  return finalPicks.slice(0, 30);
}

async function main() {
  console.log("📈 Generating daily stock picks...\n");

  try {
    const stocks = await generateStockPicks();
    const lastUpdated = new Date().toISOString();

    // Stamp each pick with prediction timestamp for retroactive analysis
    const stampedStocks = stocks.map((s) => ({
      ...s,
      pickedAt: lastUpdated,
    }));

    const output = {
      lastUpdated,
      totalPicks: stampedStocks.length,
      stocks: stampedStocks,
    };

    // Ensure data directory exists
    const dataDir = path.join(process.cwd(), "data");
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    // Archive today's picks by date (YYYY-MM-DD) for historical backtest
    const archiveDir = path.join(dataDir, "picks-archive");
    if (!fs.existsSync(archiveDir)) {
      fs.mkdirSync(archiveDir, { recursive: true });
    }
    const dateKey = lastUpdated.slice(0, 10); // YYYY-MM-DD
    const archivePath = path.join(archiveDir, `${dateKey}.json`);
    fs.writeFileSync(
      archivePath,
      JSON.stringify(
        {
          lastUpdated,
          totalPicks: stampedStocks.length,
          stocks: stampedStocks,
        },
        null,
        2,
      ),
    );
    console.log(`📁 Archived to ${archivePath}`);

    // Write to data/daily-stocks.json
    const outputPath = path.join(dataDir, "daily-stocks.json");
    fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));

    console.log(`\n✅ Generated ${stampedStocks.length} stock picks`);
    console.log(`📁 Saved to: ${outputPath}`);

    // Also write to public/data for web access
    const publicDataDir = path.join(process.cwd(), "public", "data");
    if (!fs.existsSync(publicDataDir)) {
      fs.mkdirSync(publicDataDir, { recursive: true });
    }
    const publicOutputPath = path.join(publicDataDir, "daily-stocks.json");
    fs.writeFileSync(publicOutputPath, JSON.stringify(output, null, 2));
    console.log(`📁 Also saved to: ${publicOutputPath}`);
    console.log(`📅 All picks stamped with pickedAt: ${lastUpdated}`);

    // Print detailed summary
    console.log("\n📊 Summary:");
    console.log(`  • Total Picks: ${stampedStocks.length}`);
    console.log(
      `  • STRONG BUY: ${stampedStocks.filter((s) => s.rating === "STRONG BUY").length}`,
    );
    console.log(
      `  • BUY: ${stampedStocks.filter((s) => s.rating === "BUY").length}`,
    );
    console.log(
      `  • HOLD: ${stampedStocks.filter((s) => s.rating === "HOLD").length}`,
    );

    // Group by algorithm
    const byAlgorithm = new Map<string, StockPick[]>();
    for (const stock of stampedStocks) {
      const key = stock.algorithm;
      if (!byAlgorithm.has(key)) {
        byAlgorithm.set(key, []);
      }
      byAlgorithm.get(key)!.push(stock);
    }

    console.log("\n📈 Picks by Algorithm:");
    for (const [algorithm, algorithmStocks] of byAlgorithm.entries()) {
      console.log(`  • ${algorithm}: ${algorithmStocks.length} picks`);
      const topPick = algorithmStocks[0];
      if (topPick) {
        console.log(
          `    Top: ${topPick.symbol} (${topPick.score}/100, ${topPick.rating})`,
        );
      }
    }

    console.log(
      `\n🏆 Top Overall Pick: ${stampedStocks[0]?.symbol} (${stampedStocks[0]?.score}/100, ${stampedStocks[0]?.rating})`,
    );
  } catch (error) {
    console.error("❌ Error generating stock picks:", error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { generateStockPicks };
