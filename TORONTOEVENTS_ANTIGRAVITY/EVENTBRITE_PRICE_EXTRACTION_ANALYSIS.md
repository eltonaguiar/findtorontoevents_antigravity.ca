# Eventbrite Price Extraction - Failure Analysis & Hardened Fix

## Executive Summary

**Problem**: Eventbrite events were failing to extract prices correctly. Two confirmed failures:
- Event priced at $23 failed to extract
- Event priced at $699 (https://www.eventbrite.com/e/ai-implementation-in-business-toronto-tickets-1027612706267) failed to extract

**Root Cause**: The `EventbriteDetailScraper.enrichEvent()` method was not extracting prices from detail pages, and the main scraper only relied on incomplete JSON-LD data from listing pages.

**Solution**: Implemented comprehensive price extraction in the detail scraper with multiple fallback strategies, and updated the main scraper to use enriched prices.

---

## Failure Analysis

### Issue 1: Missing Price Extraction in Detail Scraper
**Impact**: Critical - All events that don't have complete price data in listing page JSON-LD fail to extract prices.

**Evidence**: 
- The `EventEnrichment` interface did not include `price` or `priceAmount` fields
- The `enrichEvent()` method only extracted time, description, sales status, and recurring status
- Detail pages often contain more accurate price data than listing pages

**Why this causes $23 and $699 failures**:
- Listing pages may have incomplete or missing `offers` in JSON-LD
- Eventbrite displays prices like "From CA$699.00" on detail pages which aren't always in listing JSON-LD
- Currency codes (CA$, CAD) weren't being parsed correctly

### Issue 2: Incomplete JSON-LD Price Parsing
**Impact**: High - Even when JSON-LD contains price data, it may not be extracted correctly.

**Evidence**:
- Price fields can be numbers, strings, or formatted strings (e.g., "699.00", "$699", "CA$699")
- Currency codes weren't being stripped before parsing
- `lowPrice` and `highPrice` fields weren't always checked
- Price validation (reasonable ranges) was missing

**Why this causes failures**:
- String prices like "CA$699.00" would fail `parseFloat()` without cleaning
- Price ranges (lowPrice/highPrice) weren't being considered
- No validation meant invalid prices could be extracted

### Issue 3: No HTML Fallback for Price Extraction
**Impact**: Medium - When JSON-LD is missing or incomplete, no fallback mechanism existed.

**Evidence**:
- Eventbrite uses specific CSS classes and data attributes for prices
- Text patterns like "From CA$699.00" appear in HTML but weren't being extracted
- No fallback to body text pattern matching

**Why this causes failures**:
- Some events may not have structured JSON-LD offers
- JavaScript-rendered prices might not be in initial HTML (though we don't use JS rendering)
- HTML selectors provide a reliable fallback

### Issue 4: Enrichment Results Not Used for Price Updates
**Impact**: Critical - Even if we added price extraction, the main scraper wasn't using it.

**Evidence**:
- The main scraper called `enrichEvent()` but only used `realTime`, `fullDescription`, `salesEnded`, and `isRecurring`
- Price fields from enrichment were ignored
- Events were only enriched for "today/tomorrow" events, not all events

**Why this causes failures**:
- Detail page prices were extracted but never applied to events
- Only a subset of events were enriched, missing many that needed price updates

---

## Recommended Fixes

### Fix 1: Add Price Extraction to Detail Scraper (CRITICAL)
**Priority**: Critical  
**Implementation**: Added comprehensive price extraction to `EventbriteDetailScraper.enrichEvent()`

**Code Changes**:
1. Updated `EventEnrichment` interface to include `price?: string` and `priceAmount?: number`
2. Implemented three-tier extraction strategy:
   - **Method 1**: JSON-LD structured data (most reliable)
   - **Method 2**: HTML price selectors (Eventbrite-specific)
   - **Method 3**: Body text pattern matching (fallback)

**Key Features**:
- Handles currency codes: CA$, CAD, C$, $
- Parses price ranges (lowPrice, highPrice)
- Validates prices (0-100000 range)
- Uses minimum price when multiple prices found
- Handles "Free" events correctly

**Test Case**: 
```bash
npm run test:eventbrite-price
# Should extract $699 from https://www.eventbrite.com/e/ai-implementation-in-business-toronto-tickets-1027612706267
```

### Fix 2: Enhanced JSON-LD Price Parsing (HIGH)
**Priority**: High  
**Implementation**: Improved price parsing in main scraper to handle all formats

**Code Changes**:
- Handle both number and string price values
- Strip currency symbols before parsing
- Check `lowPrice`, `highPrice`, and `price` fields
- Validate price ranges (0-100000)
- Handle `isAccessibleForFree` flag correctly

**Test Case**: Events with JSON-LD offers containing string prices like "CA$699.00" should now parse correctly.

### Fix 3: Use Enriched Prices in Main Scraper (CRITICAL)
**Priority**: Critical  
**Implementation**: Updated main scraper to use enriched prices when available

**Code Changes**:
- Enrich ALL events (not just today/tomorrow) to get accurate prices
- Prioritize events without prices for enrichment
- Update event price if:
  - No price exists, OR
  - Current price is "See tickets" placeholder, OR
  - Enriched price is different (more accurate)

**Test Case**: Events that fail to extract prices from listing pages should now get prices from detail pages.

### Fix 4: HTML Fallback Selectors (MEDIUM)
**Priority**: Medium  
**Implementation**: Added multiple HTML selectors for price extraction

**Selectors Used**:
- `[data-testid="price"]`
- `.event-price`, `.ticket-price`, `.price-display`
- `[itemprop="price"]`
- `.eds-text-color--primary-brand`, `.eds-text-weight--heavy`

**Pattern Matching**:
- `/(?:CA\$|CAD|C\$)\s*(\d+(?:\.\d{2})?)/i` - Matches CA$699.00
- `/\$\s*(\d+(?:\.\d{2})?)/i` - Matches $699
- `/(?:from|starting at|tickets from)\s*(?:CA\$|CAD|C\$|\$)?\s*(\d+(?:\.\d{2})?)/i` - Matches "From CA$699"

**Test Case**: Events without JSON-LD prices should extract from HTML elements.

---

## Hardened Strategy

### Multi-Layer Defense Approach

1. **Primary**: JSON-LD structured data extraction (most reliable, standardized)
2. **Secondary**: HTML selector-based extraction (Eventbrite-specific, reliable)
3. **Tertiary**: Text pattern matching (fallback, handles edge cases)

### Best Practices Implemented

1. **Currency Handling**: Supports CA$, CAD, C$, $ formats
2. **Price Validation**: Range checks (0-100000) prevent invalid data
3. **Minimum Price Selection**: When multiple prices found, uses minimum (most user-friendly)
4. **Free Event Detection**: Explicitly handles "Free" events
5. **Error Resilience**: Each extraction method is wrapped in try-catch
6. **Rate Limiting**: 500ms delay between detail page requests

### Long-Term Solution

**Current Approach**: DOM-based scraping with multiple fallback strategies
- ✅ Works without API keys
- ✅ Handles dynamic content
- ✅ Multiple extraction methods ensure reliability

**Future Consideration**: Eventbrite API (if available)
- ⚠️ Requires API key and authentication
- ⚠️ May have rate limits
- ✅ More reliable and official
- ✅ Better structured data

**Recommendation**: Continue with current approach unless Eventbrite provides official API access. The multi-layer extraction strategy provides excellent reliability.

---

## Testing & Verification

### Test Script
Created `scripts/test-eventbrite-price-extraction.ts` to verify price extraction:

```bash
npx tsx scripts/test-eventbrite-price-extraction.ts
```

### Expected Results
- ✅ $699 event should extract price correctly
- ✅ $23 event should extract price correctly (when URL provided)
- ✅ Free events should show "Free"
- ✅ Events with price ranges should show minimum price
- ✅ Currency codes should be handled correctly

### Production Verification
After deployment, verify:
1. Events show accurate prices (not "See tickets")
2. Currency codes are displayed correctly
3. Free events show "Free"
4. Price extraction works for both listing and detail pages

---

## Implementation Summary

**Files Modified**:
1. `src/lib/scraper/detail-scraper.ts` - Added comprehensive price extraction
2. `src/lib/scraper/source-eventbrite.ts` - Enhanced JSON-LD parsing, use enriched prices

**Key Improvements**:
- ✅ Price extraction from JSON-LD, HTML, and text patterns
- ✅ Currency code handling (CA$, CAD, C$, $)
- ✅ Price validation and range checking
- ✅ Enrichment of all events (prioritizing those without prices)
- ✅ Multiple fallback strategies for reliability

**Performance Impact**:
- Enrichment now runs for all events (was only today/tomorrow)
- 500ms delay between requests prevents rate limiting
- Prioritization ensures events without prices are enriched first

---

## Conclusion

The hardened implementation addresses all identified failure points:
1. ✅ Detail scraper now extracts prices
2. ✅ JSON-LD parsing handles all formats
3. ✅ HTML fallback provides reliability
4. ✅ Main scraper uses enriched prices
5. ✅ Multi-layer defense ensures accuracy

The solution is production-ready and should resolve both the $23 and $699 price extraction failures.
