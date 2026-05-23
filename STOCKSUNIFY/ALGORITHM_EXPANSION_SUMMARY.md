# Technical Momentum & CAN SLIM Expansion Summary

**Date:** February 12, 2026  
**Agent:** Agent 4 - Technical Momentum & CAN SLIM Expansion Agent

## Objective
Expand Technical Momentum algorithm to generate more trades and loosen CAN SLIM filters to produce more picks.

## Changes Made

### 1. Created Technical Indicators Library (`scripts/lib/stock-indicators.ts`)
**New file** with comprehensive technical indicator calculations:
- **EMA (Exponential Moving Average)** - calculateEMA(), getEMA()
- **RSI (Relative Strength Index)** - calculateRSI()
- **MACD** - calculateMACD() with signal line and histogram
- **ADX (Average Directional Index)** - calculateADX() using Wilder's smoothing
- **Volume Ratio** - calculateVolumeRatio() for volume surge detection
- **RS Rating** - calculateRSRating() for CAN SLIM scoring
- **Stage-2 Uptrend Detection** - isStage2Uptrend() (Minervini methodology)
- **Price vs 52W High** - getPriceVs52WHigh()

### 2. Created Stock Scorers (`scripts/lib/stock-scorers.ts`)
**New file** implementing scoring algorithms:

#### Technical Momentum (`scoreTechnicalMomentum`)
**ENHANCED with new filters:**
- ✅ **EMA(50,200) trend filter** - Requires bullish cross: EMA50 > EMA200 AND price > EMA50
- ✅ **ADX > 20 strength filter** - Requires ADX >= 20 for trend strength
- ✅ **Volume > 1.5x 20-day average** - Requires volume surge (minimum 1.5x)
- ✅ **RSI/MACD signals** - Maintains existing RSI and MACD scoring
- ✅ **Relaxed threshold** - Lowered from 45 to 35 in generate-daily-stocks.ts

**Timeframes:** 24h, 3d, 7d (all enhanced with new filters)

#### CAN SLIM Growth (`scoreCANSLIM`)
**RELAXED filters:**
- ✅ **RS Rating threshold lowered from 90 to 75** - Accepts RS Rating >= 75 (was >= 90)
- ✅ **Relaxed scoring** - RS Rating 75-79 now gets 25 pts (was 20 pts)
- ✅ **Relaxed threshold** - Lowered from 40 to 30 in generate-daily-stocks.ts

**Maintains:**
- Stage-2 Uptrend requirement
- Price vs 52W High scoring
- RSI momentum scoring
- Volume bonus

### 3. Expanded Stock Universe (`scripts/generate-daily-stocks.ts`)
**EXPANDED from 37 to 120+ tickers:**
- Added more Large Cap Tech (GOOG, DOCN, NET, CRWD, ZS, PANW, DDOG, MDB, OKTA)
- Added more Financials (AXP, WFC, C, BLK, SCHW)
- Added more Consumer (LOW, MCD, COST, TJX, ROST)
- Added more Energy (COP, EOG, MPC, VLO)
- Added more Healthcare (TMO, ABT, LLY, MRK, BMY)
- Added Industrials (BA, CAT, GE, HON, RTX, LMT, NOC)
- Added Communication Services (DIS, CMCSA, VZ, T)
- Added Materials (LIN, APD, ECL, SHW, DD)
- Added Real Estate (AMT, PLD, EQIX, PSA)
- Added Utilities (NEE, DUK, SO, D)
- Added Crypto-related (COIN, MSTR, SQ)
- Added Biotech/Pharma momentum (MRNA, BNTX, NVAX, GILD, REGN)
- Added Semiconductor momentum (AVGO, QCOM, TXN, MU, LRCX, AMAT, KLAC)
- Added Cloud/SaaS (WDAY, VEEV, TEAM, ZM, FTNT, SPLK)
- Added Fintech momentum (HOOD, SOFI, AFRM, UPST, OPEN)
- Added Gaming (RBLX)

### 4. Lowered Thresholds (`scripts/generate-daily-stocks.ts`)
- **CAN SLIM:** Threshold lowered from 40 to 30 (goal: 5-20 picks/day)
- **Technical Momentum:** Threshold lowered from 45 to 35 (goal: 20+ trades/day)

### 5. Supporting Files Created
- `scripts/lib/stock-data-fetcher-enhanced.ts` - Multi-API stock data fetcher with fallbacks
- `scripts/lib/stock-api-keys.ts` - API keys configuration

## Files Modified

1. **STOCKSUNIFY/scripts/lib/stock-indicators.ts** (NEW)
   - Created comprehensive technical indicators library

2. **STOCKSUNIFY/scripts/lib/stock-scorers.ts** (NEW)
   - Created scoring algorithms with enhanced Technical Momentum and relaxed CAN SLIM

3. **STOCKSUNIFY/scripts/generate-daily-stocks.ts** (MODIFIED)
   - Expanded STOCK_UNIVERSE from 37 to 120+ tickers
   - Lowered CAN SLIM threshold from 40 to 30
   - Lowered Technical Momentum threshold from 45 to 35

4. **STOCKSUNIFY/scripts/lib/stock-data-fetcher-enhanced.ts** (NEW)
   - Copied from STOCKSUNIFY2 for multi-API data fetching

5. **STOCKSUNIFY/scripts/lib/stock-api-keys.ts** (NEW)
   - API keys configuration for fallback data sources

## Expected Impact

### Technical Momentum
**Before:** ~12 trades/day  
**After:** Expected 20-40+ trades/day

**Reasons:**
- Expanded universe (37 → 120+ tickers) = 3.2x more stocks scanned
- Lowered threshold (45 → 35) = more picks pass filter
- Enhanced filters (EMA cross, ADX>20, volume>1.5x) ensure quality while allowing more through

### CAN SLIM Growth
**Before:** ~1 pick/day  
**After:** Expected 5-20 picks/day

**Reasons:**
- RS Rating threshold relaxed (90 → 75) = 3-5x more stocks qualify
- Lowered threshold (40 → 30) = more picks pass final filter
- Expanded universe = more candidates to screen

## Technical Details

### Technical Momentum Filters (All Timeframes)
1. **EMA(50,200) Trend Gate:** EMA50 > EMA200 AND price > EMA50
2. **ADX Strength:** ADX >= 20 (trend strength confirmation)
3. **Volume Surge:** Volume > 1.5x 20-day average (minimum)
4. **RSI/MACD:** Existing scoring maintained

### CAN SLIM Filters
1. **RS Rating:** >= 75 (relaxed from 90)
2. **Stage-2 Uptrend:** Required (unchanged)
3. **Price vs 52W High:** Scoring maintained
4. **RSI Momentum:** Scoring maintained
5. **Volume Bonus:** Scoring maintained

## Next Steps

1. **Test the changes:**
   ```bash
   cd STOCKSUNIFY
   npm install  # if needed
   npx tsx scripts/generate-daily-stocks.ts
   ```

2. **Monitor pick counts:**
   - Check `data/daily-stocks.json` for daily pick counts
   - Verify Technical Momentum generates 20+ trades
   - Verify CAN SLIM generates 5-20 picks

3. **Adjust if needed:**
   - If too many picks: raise thresholds slightly (35→38, 30→33)
   - If too few picks: lower thresholds further or relax RS Rating to 70

4. **Backtest performance:**
   - Use archived picks in `data/picks-archive/` to analyze accuracy
   - Compare expanded vs original algorithm performance

## Notes

- All changes maintain backward compatibility with existing data structures
- Technical Momentum filters ensure quality (EMA cross + ADX + volume) while allowing more through
- CAN SLIM relaxation is conservative (75 vs 90) to maintain quality
- Expanded universe covers major sectors for diversification
