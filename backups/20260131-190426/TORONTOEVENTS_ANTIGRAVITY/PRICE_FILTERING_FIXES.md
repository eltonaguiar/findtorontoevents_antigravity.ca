# Price Filtering Fixes - Summary

## Problem Identified

The event "Toronto Marriage-Minded Singles - One-on-One" (https://www.eventbrite.ca/e/toronto-marriage-minded-singles-one-on-one-tickets-1981517745919) shows as $606 on Eventbrite but was appearing in filtered results for "events under $120" because:

1. **Price not extracted**: Event had `"price": "See tickets"` with no `priceAmount`
2. **Short description**: Description was too short and didn't include price information
3. **Filter gap**: Filters only checked `priceAmount`, not descriptions when price was missing

## Fixes Implemented

### 1. Enhanced Price Extraction (`src/lib/scraper/detail-scraper.ts`)
- ✅ Added better patterns to extract prices from descriptions
- ✅ Now catches prices in context like "Regular price for this service is $449"
- ✅ Extracts prices over $100 from description text as fallback

### 2. Enhanced Eventbrite Scraper (`src/lib/scraper/source-eventbrite.ts`)
- ✅ Added post-enrichment price extraction from descriptions
- ✅ Re-checks expensive events after enrichment and marks them as CANCELLED
- ✅ Extracts prices from description text when JSON-LD doesn't have them

### 3. Enhanced Quality Filter (`src/lib/quality/score.ts`)
- ✅ Now checks descriptions for high prices when `priceAmount` is undefined
- ✅ Rejects events with prices > $150 mentioned in description text
- ✅ Prevents expensive events from slipping through

### 4. Enhanced Frontend Filter (`src/components/EventFeed.tsx`)
- ✅ Checks descriptions for high prices when filtering
- ✅ Filters out events with prices > maxPrice even if `priceAmount` is undefined
- ✅ Multiple pattern matching for price detection

### 5. Visual Warning (`src/components/EventCard.tsx`)
- ✅ Added warning icon (⚠️) for events showing "See tickets"
- ✅ Color coding: Yellow for "See tickets", Orange for expensive events
- ✅ Alerts users that price may not be available

### 6. Main Scraper Safety (`src/lib/scraper/index.ts`)
- ✅ Re-checks existing events for expensive prices
- ✅ Prunes expensive events even if they were previously in the data

## Test Results

Testing the specific event URL:
- ✅ Price extraction works: Found $674.21 (with fees/taxes, close to $606)
- ✅ Event would be filtered by quality filter (> $150)
- ✅ Event would be filtered by frontend filter (> $120)

## Scripts Created

1. **`scripts/test-price-extraction.ts`** - Test price extraction for a specific URL
2. **`scripts/check-expensive-events.ts`** - Check current data for expensive events
3. **`scripts/re-enrich-expensive-events.ts`** - Re-enrich events with missing prices

## Next Steps

### Immediate Fix for Current Data

Run the re-enrichment script to update existing events:

```bash
npx tsx scripts/re-enrich-expensive-events.ts
```

This will:
- Check all Eventbrite events with "See tickets" or missing prices
- Extract prices from detail pages
- Mark expensive events (> $120) as CANCELLED
- Update the events.json file

### Future Prevention

1. **Enhanced scraping**: Price extraction now happens during scraping
2. **Multiple checks**: Filters at scraper level, quality level, and frontend level
3. **Visual warnings**: Users see warnings for "See tickets" events
4. **Automatic filtering**: Expensive events are automatically filtered out

## Verification

After running the re-enrichment script, verify:

```bash
npx tsx scripts/check-expensive-events.ts
```

This should show 0 expensive events (or only events that are legitimately expensive but within your threshold).

## Filter Thresholds

- **Quality Filter**: Rejects events > $150 (in `shouldIncludeEvent`)
- **Frontend Filter**: Hides events > maxPrice (default $120) when `showExpensive` is false
- **Visual Warning**: Shows ⚠️ for "See tickets" events

---

**The fixes ensure that expensive events are properly flagged and filtered at multiple levels to prevent misleading users.**
