# Fix: Add Thursday Dating Events Scraper

## Problem

**findtorontoevents.ca** was missing dating events from **getthursday.com/toronto/**, a major dating/singles events platform.

### Root Causes

1. **No Thursday Scraper Existed**: The codebase had scrapers for Eventbrite dating categories, 25dates.com, and Fatsoma, but no scraper for Thursday's Toronto page
2. **Fatsoma Scraper Ineffective**: The existing `fatsoma_scraper.py` was attempting to scrape Fatsoma's global discover page but finding 0 Toronto events due to:
   - Wrong pagination logic
   - Incorrect regex patterns for Toronto location filtering
   - The scraper was looking for Thursday events on the wrong platform

## Impact

- Users searching for dating events on findtorontoevents.ca were missing **10+ major dating events** from Thursday
- Thursday is described as "The Biggest IRL Dating Brand in the World" and operates globally
- Events included notable dating experiences like:
  - First Dates: Theatre Experience
  - AI Matchbox Dating
  - Thursday Sunrise Forgives
  - LGBTQ+ events (Bangarang)
  - Summer Yacht Party

## Solution

Created a new dedicated scraper: `tools/scrapers/thursday_scraper.py`

### Key Features

1. **Correct CSS Selectors**: Thursday uses BEM-style classes:
   - Event cards: `.events-grid-flexible-columns__card`
   - Event URLs: `card-link` attribute on `.card__wrapper`
   - Titles: `.card__heading a.heading-link`
   - Dates: `.meta--date`
   - Venues: `.meta--location`
   - Images: `.card__media--image`

2. **Date Parsing**: Handles Thursday's date format:
   - Input: "Sat 25th April 2026 at 6:30 pm"
   - Converts to ISO-8601 UTC (accounting for EDT offset)

3. **Dating Category Tagging**:
   - Forces "Dating" category for all events
   - Auto-tags with relevant keywords (LGBTQ+, Singles, Dating, etc.)
   - Appends "Singles" tag by default

4. **Fallback Parser**: Works with both:
   - BeautifulSoup (recommended)
   - Scrapling (for TLS fingerprinting)

### Files Changed

1. **Created**: `tools/scrapers/thursday_scraper.py` (393 lines)
   - Full scraper implementation with date parsing, location enhancement, and categorization

2. **Modified**: `tools/scrapers/unified_scraper.py`
   - Added `GetThursdayScraper` import
   - Added `GetThursdayScraper()` instance to scrapers list
   - Scraped alongside other dating sources (Eventbrite, Fatsoma, 25dates)

## Test Results

```
[Thursday] Scraping Thursday Toronto events...
[Thursday] Found 12 unique events
  ✓ First Dates: Theatre Experience I Second City
  ✓ Thursday | Sunrise Forgives | Toronto
  ✓ Thursday Presents: The Chase Run Club | Toronto
  ✓ AI Matchbox Dating (35+) | Track & Field | Toronto
  ✓ Thursday | Isabelle's | Toronto
  ✓ Thursday | Cassius | Toronto
  ✓ Thursday | Track & Field (2 Events In 1) | Toronto
  ✓ Thursday | Bangarang (LGBTQ+) | Toronto
  ✓ AI Matchbox Dating (25 – 35) | Sand Trap | Toronto
  ✓ Thursday | Summer Yacht Party | Toronto
[Thursday] Total Thursday dating events: 10
```

Successfully scraped **10 dating events** from Thursday's Toronto page with proper:
- Titles, URLs, dates, venues, images
- Dating category classification
- Singles/LGBTQ+ tags where applicable
- ISO-8601 date formatting

## Integration

The scraper is now part of the unified scraping pipeline:

```python
# In unified_scraper.py's __init__ method
self.scrapers = [
    # ... other scrapers ...
    DatingEventsScraper(),      # Eventbrite dating categories
    FatsomaScraper(),           # Fatsoma dating events
    GetThursdayScraper(),       # Thursday dating events (NEW)
    # ... more scrapers ...
]
```

## Deployment

After merging this PR:
1. Run the unified scraper to regenerate `events.json` with Thursday events included
2. Deploy `events.json` to the live site
3. Thursday events will now appear in the Dating category on findtorontoevents.ca

## Technical Notes

### Why Thursday Scraper Succeeded Where Fatsoma Failed

1. **Direct URL Targeting**: Thursday scraper hits the specific Toronto page (`/toronto/`) rather than a global discover page
2. **BEM Class Names**: Thursday uses structured BEM (`.card__heading`, `.meta--date`) vs Fatsoma's generic class names
3. **card-link Attribute**: Thursday stores event URLs in a data attribute, not in standard `<a>` tags
4. **Single-Page Scrape**: Thursday displays all upcoming events on one page (no pagination needed)

### Date Parsing Edge Cases

The date parser handles:
- Ordinal suffixes (25th, 1st, 3rd)
- Time conversion (7:00 pm → 23:00 UTC)
- EDT offset adjustment (+4 hours)
- Noon UTC fallback for date-only parsing

### Future Improvements

1. Add pagination support if Thursday adds more events than fit on one page
2. Fetch detail pages for enhanced descriptions
3. Extract price information from detail pages
4. Add regex pattern for event age ranges (e.g., "AI Matchbox Dating (35+)")

## Verification

To verify this fix works:
1. Run: `python tools/scrapers/thursday_scraper.py`
2. Should output 10+ Thursday events with valid dates, titles, URLs
3. Run: `python tools/scrape_and_sync_events.py --output events.json`
4. Check `events.json` contains Thursday-sourced events with `source: "Thursday"`
5. Deploy and verify events appear on findtorontoevents.ca under Dating category