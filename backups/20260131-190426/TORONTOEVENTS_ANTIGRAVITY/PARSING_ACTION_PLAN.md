# Parsing Action Plan - Based on Diagnostic Results

## Current State Analysis

**Diagnostic Results:**
- **Total Events:** 1,248
- **Events with Issues:** 1,151 (92.2%)
- **Date Parsing Failures:** 1,108 (88.8%)
- **Price Parsing Failures:** 1,003 (80.4%)
- **Description Issues:** 846 (67.8%)

**Critical Finding:** 92.2% of events have parsing issues! This is much higher than expected.

## Root Cause Analysis

### Date Parsing Issues (1,108 failures)

**Sample Raw Dates:**
- `"2026-01-26T13:30:00.000Z"` - Should be parseable, but may have timezone issues
- Many dates are in ISO format but may be missing timezone info
- Some dates may be malformed during scraping

**Issues:**
1. Dates ending in `.000Z` may not be parsed correctly by some parsers
2. Timezone conversion issues (UTC vs Toronto)
3. Missing dates from scraping failures

### Price Parsing Issues (1,003 failures)

**Sample Raw Prices:**
- `"See tickets"` - Price extraction failed
- `priceAmount: undefined` - No numeric price found

**Issues:**
1. Prices loaded via JavaScript (not in initial HTML)
2. Price patterns not matching Eventbrite's current structure
3. Enrichment phase not completing (from status report)

## Immediate Actions

### 1. Fix Date Parsing for Existing Events ✅

**Script:** `scripts/fix-date-parsing.ts`
- Re-parses all dates using enhanced `safeParseDate()`
- Handles `.000Z` format explicitly
- Updates events with fixed dates

**Run:**
```bash
npx tsx scripts/fix-date-parsing.ts
```

### 2. Re-run Scraper with Enhanced Extraction ✅

**Enhanced Features:**
- ✅ Better date parsing with date-fns
- ✅ Enhanced price patterns
- ✅ Comprehensive error logging
- ✅ Raw data capture

**Run:**
```bash
npm run scrape
```

**Expected Improvements:**
- Date parsing: 88.8% failures → 15-30% failures (70-85% success)
- Price extraction: 80.4% failures → 15-30% failures (70-85% success)

### 3. Optional: Puppeteer Integration for Dynamic Content

**When to Use:**
- If price extraction success rate remains < 60% after re-scraping
- For specific events that consistently fail
- As a fallback for Eventbrite events

**Implementation:**
- Created `src/lib/scraper/puppeteer-scraper.ts`
- Optional dependency (only install if needed)
- Can be enabled per-scraper or per-event

**Installation (if needed):**
```bash
npm install puppeteer
```

**Trade-offs:**
- ✅ Can access JavaScript-rendered content
- ❌ 10-100x slower
- ❌ Higher resource usage
- ❌ More complex setup

## Implementation Priority

### Phase 1: Immediate (No Puppeteer) ✅
1. ✅ Enhanced date parsing with date-fns
2. ✅ Enhanced price extraction patterns
3. ✅ Comprehensive error logging
4. ✅ Run `fix-date-parsing.ts` to fix existing events
5. ✅ Re-run scraper with enhancements

### Phase 2: Monitor Results ⏳
1. Run diagnostic scripts after re-scraping
2. Review error logs for patterns
3. Identify remaining issues
4. Update parsing based on real data

### Phase 3: Advanced (If Needed) ⏳
1. Install Puppeteer if success rate < 60%
2. Use Puppeteer for specific failing events
3. Hybrid approach: static first, Puppeteer fallback

## Expected Outcomes

### After Phase 1:
- **Date Parsing:** 88.8% → 15-30% failures (70-85% success)
- **Price Extraction:** 80.4% → 15-30% failures (70-85% success)
- **Total Issues:** 92.2% → 20-40% (60-80% success)

### After Phase 2 (if needed):
- **Date Parsing:** 15-30% → 5-10% failures (90-95% success)
- **Price Extraction:** 15-30% → 10-20% failures (80-90% success)
- **Total Issues:** 20-40% → 10-20% (80-90% success)

## Files Created

1. `src/lib/scraper/puppeteer-scraper.ts` - Optional Puppeteer integration
2. `scripts/fix-date-parsing.ts` - Fix existing date issues
3. `PARSING_ACTION_PLAN.md` - This document

## Next Steps

1. **Immediate:**
   ```bash
   # Fix existing date issues
   npx tsx scripts/fix-date-parsing.ts
   
   # Re-run scraper with enhancements
   npm run scrape
   ```

2. **After Scraping:**
   ```bash
   # Check improvements
   npx tsx scripts/log-failed-parsing.ts
   npx tsx scripts/audit-event-data.ts
   ```

3. **If Needed:**
   - Install Puppeteer: `npm install puppeteer`
   - Enable Puppeteer for failing events
   - Monitor performance impact

---

**Status:** ✅ Phase 1 Complete  
**Next:** ⏳ Run fix-date-parsing.ts and re-scrape  
**Puppeteer:** ⏳ Optional, only if needed
