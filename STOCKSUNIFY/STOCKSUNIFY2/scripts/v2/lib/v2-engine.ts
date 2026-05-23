/**
 * STOCKSUNIFY2: Scientific Engine
 *
 * Orchestrates data fetching, strategy execution, and audit logging.
 */

import {
  fetchMultipleStocks,
  fetchStockData,
} from "../../lib/stock-data-fetcher-enhanced";
import {
  scoreRAR,
  scoreVAM,
  scoreLSP,
  scoreScientificCANSLIM,
  scoreAdversarialTrend,
  scoreInstitutionalFootprint,
  V2Pick,
} from "./strategies";

// The "Standard" Scientific Universe - Expanded for comprehensive coverage
const V2_UNIVERSE = [
  // Market Index (Regime Baseline)
  "SPY",

  // Mega-Cap Tech (Quality Growth)
  "AAPL",
  "MSFT",
  "NVDA",
  "AMZN",
  "GOOGL",
  "META",
  "TSLA",
  "AVGO",
  "COST",
  "V",
  "MA",
  "NFLX",
  "AMD",
  "LRCX",

  // Additional Large-Cap Tech
  "CRM",
  "ADBE",
  "ORCL",
  "INTC",
  "QCOM",
  "NOW",
  "SNOW",
  "PANW",

  // Strong Fundamentals (Financials)
  "JPM",
  "UNH",
  "LLY",
  "JNJ",
  "PG",
  "XOM",
  "CAT",
  "GE",
  "BAC",
  "WFC",
  "GS",
  "MS",
  "BLK",
  "AXP",

  // Healthcare
  "ABBV",
  "MRK",
  "PFE",
  "TMO",
  "DHR",
  "ABT",

  // Consumer & Industrial
  "WMT",
  "HD",
  "MCD",
  "NKE",
  "SBUX",
  "TGT",
  "LOW",
  "DE",
  "HON",
  "UPS",
  "RTX",
  "LMT",
  "BA",

  // Energy & Materials
  "CVX",
  "COP",
  "SLB",
  "EOG",
  "LIN",
  "APD",
  "FCX",

  // High Beta / Speculative (Stress Test verification)
  "COIN",
  "MSTR",
  "UPST",
  "AFRM",
  "PLTR",
  "SOFI",
  "HOOD",
  "SQ",

  // EV & Clean Energy
  "RIVN",
  "LCID",
  "F",
  "GM",
  "ENPH",
  "FSLR",

  // Penny / Micro-cap universe for LSP strategy
  "GME",
  "AMC",
  "SNDL",
  "MULN",
  "XELA",
  "HSTO",
  "BB",
  "NAKD",
];

export async function generateScientificPicks(): Promise<{
  picks: V2Pick[];
  regime: any;
}> {
  console.log("📡 Engine: Fetching Market Regime Baseline (SPY)...");
  const spyData = await fetchStockData("SPY");

  let spySMA200 = 0;
  if (spyData?.history && spyData.history.length >= 200) {
    const closes = spyData.history.map((h) => h.close);
    // Calculate SMA200 using the last 200 closing prices
    spySMA200 = closes.slice(-200).reduce((a, b) => a + b, 0) / 200;
  }

  const regime = {
    symbol: "SPY",
    price: spyData?.price || 0,
    sma200: spySMA200,
    status: (spyData?.price || 0) > spySMA200 ? "BULLISH" : "BEARISH",
  };

  console.log("📡 Engine: Fetching Strategic Universe...");
  const allData = await fetchMultipleStocks(V2_UNIVERSE);

  // Filter out SPY from the pool (it's for regime/benchmark only)
  const stockPool = allData.filter((d) => d.symbol !== "SPY");

  const v2Picks: V2Pick[] = [];

  console.log("🔬 Engine: Running Interrogations...");

  for (const data of stockPool) {
    // 1. Run RAR (Regime Aware)
    const rar = scoreRAR(data, spyData || undefined);
    if (rar) v2Picks.push(rar);

    // 2. Run VAM (Volatility Adjusted)
    const vam = scoreVAM(data);
    if (vam) v2Picks.push(vam);

    // 3. Run LSP (Liquidity Shielded)
    const lsp = scoreLSP(data);
    if (lsp) v2Picks.push(lsp);

    // 4. Run SCS (Scientific CAN SLIM)
    const scs = scoreScientificCANSLIM(data, spyData || undefined);
    if (scs) v2Picks.push(scs);

    // 5. Run AT (Adversarial Trend)
    const at = scoreAdversarialTrend(data);
    if (at) v2Picks.push(at);

    // 6. Run IF (Institutional Footprint) - New from Research Paper
    const instFp = scoreInstitutionalFootprint(data);
    if (instFp) v2Picks.push(instFp);
  }

  // Sort by scientific score
  v2Picks.sort((a, b) => b.score - a.score);

  console.log(`✅ Engine: Generated ${v2Picks.length} Scientific Picks`);

  // Return top 20 verified picks and the regime context
  return {
    picks: v2Picks.slice(0, 20),
    regime,
  };
}
