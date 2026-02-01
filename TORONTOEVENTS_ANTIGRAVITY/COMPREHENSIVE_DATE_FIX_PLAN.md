# Comprehensive Date Extraction Fix Plan

**Date:** January 27, 2026  
**Priority:** CRITICAL - Invalid dates are NOT acceptable

## Problem Statement

1. **Fatsoma events have wrong dates**
2. **Invalid dates are appearing in the database**
3. **Only acceptable reason for missing date: Source page explicitly shows "TBD"**

## Root Cause Analysis

### Current Issues:
1. **Fatsoma Scraper**: Uses `new Date().toISOString()` as fallback (line 51) - this is WRONG
2. **Insufficient Detail Page Fetching**: Not all scrapers fetch detail pages when date extraction fails
3. **Weak Validation**: Events with invalid dates are not being rejected
4. **No TBD Detection**: No explicit check for "TBD" or "To Be Determined" dates

## Solution: Universal Date Extraction Strategy

### Phase 1: Enhanced Date Extraction Function
Create a robust date extraction function that:
1. Tries JSON-LD first (most reliable)
2. Falls back to HTML selectors
3. Checks for "TBD" explicitly
4. Returns null only if TBD is found, otherwise throws error

### Phase 2: Update ALL Scrapers
For each scraper:
1. **Remove all `new Date().toISOString()` fallbacks** - these are WRONG
2. **Always fetch detail page** if listing page date extraction fails
3. **Use enhanced extraction function** with TBD detection
4. **Reject events** without valid dates (unless TBD)

### Phase 3: Validation & Testing
1. Audit all events in database
2. Fix existing invalid dates
3. Add validation to prevent future invalid dates

## Implementation Plan

### Step 1: Create Enhanced Date Extraction Utility
- Function: `extractDateFromPage(url: string, checkTBD: boolean = true)`
- Returns: `{ date: string | null, isTBD: boolean }`
- Throws error if date cannot be extracted and not TBD

### Step 2: Update Each Scraper (Priority Order)
1. ✅ **Fatsoma** - CRITICAL (reported issue)
2. ✅ **AllEvents.in** - Already enhanced, verify
3. ✅ **CitySwoon** - Already enhanced, verify
4. **Eventbrite** - Check date extraction
5. **Thursday** - Check date extraction
6. **Toronto Dating Hub** - Check date extraction
7. **25Dates** - Check date extraction
8. **Waterworks** - Check date extraction
9. **BlogTO** - Check date extraction
10. **Narcity** - Check date extraction
11. **Showpass** - Check date extraction
12. **Meetup** - Check date extraction
13. **Toronto** - Check date extraction

### Step 3: Database Cleanup
- Scan all events for invalid dates
- Fix or remove events with invalid dates
- Mark TBD events appropriately

## Success Criteria

✅ **Zero invalid dates** in database (unless explicitly TBD)  
✅ **All scrapers** fetch detail pages when needed  
✅ **TBD detection** works correctly  
✅ **No fallback to current date** - only TBD or valid date
