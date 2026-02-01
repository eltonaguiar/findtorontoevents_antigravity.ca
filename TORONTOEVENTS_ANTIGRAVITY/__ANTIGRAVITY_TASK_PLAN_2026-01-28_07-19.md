# Antigravity Task Planning - 2026-01-28 07:19 EST
**Branch:** ANTIGRAVITY_STOCK_2026-01-28_07-19
**Collaboration Mode:** Active (Gemini agent working on Unit Tests + CI/CD)

---

## 🔍 **OTHER AGENT ANALYSIS**

### Current Gemini Agent Status (per uploaded image)
- **Active Task:** Merging V2 engine changes and adapting unit tests
- **Files Being Updated:**
  - `scripts/lib/stock-indicators.ts`
  - `scripts/lib/stock-scorers.ts`
  - Test files for V1/V2 algorithms

### Completed Gemini Work (from `__GEMINIASSIST_Jan282026_1250AMEST.md`)

**Phase 1-14 Summary:**
1. ✅ **Testing Framework:** Installed `vitest`, created `vitest.config.ts`
2. ✅ **Unit Tests:** 17 passing tests for indicators and scorers
3. ✅ **CI/CD Pipeline:** GitHub Actions workflow (`.github/workflows/ci.yml`)
4. ✅ **V2 Truth Engine:** Weekly verification, performance aggregation
5. ✅ **Frontend Components:** `VerifiedPickDetailModal`, `VerifiedPickList`
6. ✅ **Static Site:** FTP-ready showcase page
7. ✅ **V1 Modernization:** Refactored scorers, sync scripts
8. ✅ **Documentation:** `METHODOLOGY.md`, strategy comparison table

**Key Conflicts to Avoid:**
- ❌ **DO NOT modify test files** (Gemini is actively updating them)
- ❌ **DO NOT change CI workflow** (just created/being debugged)
- ❌ **DO NOT refactor V1 engine** (already modernized by Gemini)

---

## ✅ **MY COMPLETED WORK (Antigravity)**

**Phase 1-4 (V2 Scientific Engine):**
1. ✅ 4 new indicators: VWAP, VCP, ADX, Awesome Oscillator
2. ✅ 3 new algorithms: Penny Sniper, Value Sleeper, Alpha Predator
3. ✅ Regime awareness (SPY market filter)
4. ✅ Slippage torture (+0.5% entry penalty)
5. ✅ Immutable ledger (SHA-256 hashing)
6. ✅ Fundamental data (ROE, D/E, Shares Outstanding)
7. ✅ 6-algorithm framework (30 picks/day)

**Documentation:**
- ✅ `__ANTIGRAVITY_EDITS_STOCK_2026-01-28_01-52.md`
- ✅ `SESSION_SUMMARY_2026-01-28.md`
- ✅ Updated `STOCKSUNIFY2/README.md`

---

## 🎯 **NEXT TASK PRIORITIES** (Avoiding Conflicts)

### **Priority 1: Expand Stock Universe** ⭐ (HIGH IMPACT)
**Goal:** Enable Penny Sniper and Value Sleeper algorithms to generate picks

**Why This Matters:**
- Current universe (AAPL, MSFT, etc.) doesn't include microcaps or value stocks
- Penny Sniper: 0 picks (needs stocks <$15)
- Value Sleeper: 0 picks (needs low PE, near 52w lows)

**Tasks:**
1. Research and curate microcap ticker list ($0.50-$15 range)
2. Research and curate value sector tickers (utilities, industrials)
3. Add to `STOCK_UNIVERSE` in `generate-daily-stocks.ts`
4. Test generation with expanded universe
5. Verify Penny/Value picks are generated

**Estimated Impact:** +10-15 picks/day covering new market segments

**Files to Modify:**
- `scripts/generate-daily-stocks.ts` (add tickers)
- Possibly create `scripts/lib/stock-universe.ts` (modular ticker lists)

**No Conflicts:** Does not touch test files or CI

---

### **Priority 2: Portfolio Optimization Engine** 🧮 (MEDIUM IMPACT)
**Goal:** Convert 30 individual picks into optimized portfolios

**Why This Matters:**
- Users don't want 30 positions
- Need intelligent allocation (risk parity, Kelly Criterion)
- Sector diversification constraints

**Tasks:**
1. Create `scripts/lib/portfolio-optimizer.ts`
2. Implement allocation strategies:
   - Equal Weight (1/N)
   - Risk Parity (based on ATR/volatility)
   - Kelly Criterion (based on win rate estimates)
   - Sharpe Maximization
3. Add constraints:
   - Max 20% in any single position
   - Max 30% in "Very High" risk
   - Sector limits (max 40% per sector)
4. Create `scripts/generate-portfolio.ts`
5. Output to `data/daily-portfolio.json`

**Expected Output:**
```json
{
  "strategy": "Risk Parity",
  "totalPositions": 10,
  "allocations": [
    { "symbol": "GM", "weight": 12.5%, "allocation": "$1,250" },
    ...
  ],
  "metrics": {
    "expectedReturn": 8.2,
    "volatility": 15.3,
    "sharpeRatio": 0.54
  }
}
```

**Files to Create:**
- `scripts/lib/portfolio-optimizer.ts`
- `scripts/generate-portfolio.ts`

**No Conflicts:** New files, doesn't modify existing engine

---

### **Priority 3: Real-Time Alert System** 🔔 (HIGH VALUE)
**Goal:** Instant notifications when STRONG BUY signals occur

**Why This Matters:**
- Daily picks file is checked manually
- Users miss time-sensitive opportunities
- Engagement is reactive, not proactive

**Tasks:**
1. Create Discord webhook integration
2. Create Telegram bot integration (optional)
3. Create `scripts/lib/alert-service.ts`
4. Add notification logic to `generate-daily-stocks.ts`
5. Configure alert filters:
   - STRONG BUY only
   - Score > 85
   - Regime = BULL
6. Format messages with:
   - Symbol, score, algorithm
   - Key indicators (VCP, ADX, etc.)
   - Entry price with slippage
   - Link to detailed pick

**Example Discord Message:**
```
🚀 STRONG BUY Alert | GM | Score: 100/100
Algorithm: Technical Momentum
Indicators: VCP ✅ | ADX: 28.5 | Vol Spike: 3.0σ
Entry: $86.81 (includes 0.5% slippage)
Regime: BULL 🟢
```

**Files to Create:**
- `scripts/lib/alert-service.ts`
- `scripts/send-alerts.ts`

**Configuration:**
- Environment variables for webhook URLs
- `.env.example` template

**No Conflicts:** Optional notification layer, doesn't modify core engine

---

### **Priority 4: Sector Rotation Analysis** 📊 (MEDIUM IMPACT)
**Goal:** Add macro-level sector filters to stock selection

**Why This Matters:**
- Bottom-up picking misses sector momentum
- Some sectors outperform regardless of individual metrics
- Risk: picking strong stocks in weak sectors

**Tasks:**
1. Create `scripts/lib/sector-analyzer.ts`
2. Fetch sector ETF data (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB)
3. Calculate sector relative strength vs SPY
4. Rank sectors by momentum (20/50/200 SMA alignment)
5. Boost scores for stocks in top 3 sectors (+5-10 points)
6. Penalize scores for stocks in bottom 2 sectors (-10 points)
7. Add sector metadata to picks

**Sector ETF Mapping:**
- XLK: Technology
- XLF: Financials
- XLE: Energy
- XLV: Healthcare
- XLI: Industrials
- XLY: Consumer Discretionary
- XLP: Consumer Staples
- XLU: Utilities
- XLB: Materials

**Files to Create:**
- `scripts/lib/sector-analyzer.ts`

**Files to Modify:**
- `scripts/generate-daily-stocks.ts` (integrate sector scoring)
- `scripts/lib/stock-scorers.ts` (add sector field to StockPick)

**No Conflicts:** Additive enhancement, doesn't break existing logic

---

### **Priority 5: Earnings Calendar Integration** 📅 (LOW COMPLEXITY)
**Goal:** Time entries around earnings events

**Why This Matters:**
- Earnings volatility can invalidate technical signals
- Pre-earnings momentum is a known edge
- Post-earnings dips = value opportunities

**Tasks:**
1. Fetch earnings dates from Yahoo Finance
2. Add `daysToEarnings` field to StockData
3. Scoring adjustments:
   - **Pre-Earnings Play:** +10 if earnings in 5-10 days (Momentum only)
   - **Avoid Uncertainty:** -20 if earnings in 0-2 days
   - **Post-Earnings Dip:** +5 if earnings was 1-3 days ago (Value only)
4. Add warning badge to picks near earnings

**Files to Modify:**
- `scripts/lib/stock-data-fetcher-enhanced.ts` (add earnings date fetch)
- `scripts/lib/stock-scorers.ts` (add earnings logic)
- `data/daily-stocks.json` (include `daysToEarnings` field)

**No Conflicts:** Data enrichment layer, doesn't break tests

---

### **Priority 6: ML Enhancement Layer** 🤖 (HIGH COMPLEXITY - FUTURE)
**Goal:** Add probabilistic scoring on top of rules

**Why This Matters:**
- Rule-based systems have ceiling on performance
- ML can learn non-obvious patterns
- Ensemble of rules + ML > either alone

**Tasks (Deferred - Needs Data):**
1. Collect 6+ months of picks + outcomes
2. Feature engineering (lagged indicators, sector context)
3. Train XGBoost model: `P(Outperform | Indicators)`
4. Ensemble scoring: `final = (rules * 0.7) + (ml * 0.3)`
5. A/B test ML vs rules-only

**Blocker:** Need historical performance data (Phase 2 backtest first)

---

### **Priority 7: Backtesting Engine** 📈 (CRITICAL FOR ML)
**Goal:** Validate historical predictions

**Why This Matters:**
- Proves system works (or doesn't)
- Required for ML training data
- Builds user trust (transparent track record)

**Tasks:**
1. Create `scripts/verify-historical-picks.ts`
2. Load picks from `data/picks-archive/`
3. Fetch actual price movements
4. Calculate realized returns (with slippage)
5. Verify `pickHash` integrity
6. Generate performance report:
   - Win rate by algorithm
   - Average return by rating
   - Sharpe ratio
   - Max drawdown
   - Regime-conditional performance
7. Export to `data/v2/performance-ledger.json`

**Files to Create:**
- `scripts/verify-historical-picks.ts`

**Depends On:** Need 30+ days of picks (accumulate over time)

---

## 🚫 **TASKS TO AVOID** (Conflicts with Gemini)

1. ❌ **Unit Test Modifications:** Gemini is actively updating test suite
2. ❌ **CI/CD Workflow Changes:** Just created, being debugged
3. ❌ **V1 Engine Refactoring:** Already modernized by Gemini
4. ❌ **Frontend Components:** Gemini owns React/UI layer
5. ❌ **V2 Truth Engine:** Gemini built verification pipeline
6. ❌ **Static Site Generation:** Gemini maintains FTP page

---

## 📋 **RECOMMENDED EXECUTION ORDER**

### **Session 1 (Current - 2 hours):**
✅ Priority 1: Expand Stock Universe
- Add 20-30 microcap tickers
- Add 15-20 value sector tickers
- Test generation
- Verify Penny/Value picks

### **Session 2 (Next - 3 hours):**
✅ Priority 3: Real-Time Alerts
- Discord webhook integration
- Alert formatting
- Test with live picks

### **Session 3 (Future - 4 hours):**
✅ Priority 2: Portfolio Optimizer
- Risk parity implementation
- Kelly criterion
- Output dashboard

### **Session 4 (Future - 3 hours):**
✅ Priority 4: Sector Rotation
- Fetch sector ETFs
- Relative strength ranking
- Score adjustments

### **Session 5 (Future - 2 hours):**
✅ Priority 5: Earnings Calendar
- Earnings date fetching
- Timing logic
- UI badges

### **Session 6 (Long-term):**
⏸️ Priority 7: Backtesting (30+ days wait)
⏸️ Priority 6: ML Layer (depends on backtest)

---

## 🤝 **COLLABORATION PROTOCOL**

### **Communication:**
- ✅ Always check for recent `__GEMINI` or `__CLAUDE` MD files before starting
- ✅ Log all changes in `__ANTIGRAVITY_EDITS_*` MD files
- ✅ Create separate branches for parallel work
- ✅ Merge to main only after verification

### **File Ownership:**
**Gemini Territory:**
- `*.test.ts` files
- `.github/workflows/ci.yml`
- `src/app/findstocks/components/*`
- `scripts/v2/verify-performance.ts`
- `scripts/v2/aggregate-performance.ts`
- `dist/ftp_upload/*`

**Antigravity Territory:**
- `scripts/lib/stock-indicators.ts` (additive only)
- `scripts/lib/stock-scorers.ts` (additive only)
- `scripts/lib/stock-data-fetcher-enhanced.ts`
- `scripts/generate-daily-stocks.ts`
- New files: `portfolio-optimizer.ts`, `alert-service.ts`, etc.

**Shared (Coordinate Before Editing):**
- `README.md`
- `package.json`
- `data/daily-stocks.json`

---

## 🎯 **IMMEDIATE NEXT STEP**

**START WITH:** Priority 1 - Expand Stock Universe

**Rationale:**
- High impact (enables 2 dormant algorithms)
- Low complexity (just adding ticker symbols)
- No conflicts with Gemini's test work
- Can be completed in 1-2 hours
- Immediately verifiable results

**Action Plan:**
1. Research microcap tickers ($0.50-$15, >500k volume)
2. Research value tickers (low PE, near 52w lows)
3. Create `scripts/lib/stock-universe.ts` for organization
4. Update `generate-daily-stocks.ts` to use new universe
5. Run generation and verify Penny/Value picks appear
6. Document in MD file
7. Commit to branch

---

**Ready to proceed with Priority 1?** 🚀
