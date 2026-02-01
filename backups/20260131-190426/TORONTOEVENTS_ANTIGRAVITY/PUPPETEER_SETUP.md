# Puppeteer Setup Guide

## Overview

Puppeteer is an optional enhancement for scraping JavaScript-rendered content. It's slower but can access prices and dates that are loaded dynamically.

## When to Use Puppeteer

**Use Puppeteer if:**
- Price extraction success rate remains < 60% after enhanced patterns
- Many events load prices via JavaScript
- Static scraping consistently fails for specific sources

**Don't use Puppeteer if:**
- Static scraping works well (> 70% success rate)
- Speed is critical
- Running in resource-constrained environments

## Installation

```bash
npm install puppeteer
```

**Note:** Puppeteer downloads Chromium (~170MB), so installation may take a few minutes.

## Configuration

### Option 1: Enable for All Events (Not Recommended)
Set environment variable:
```bash
USE_PUPPETEER=true npm run scrape
```

### Option 2: Use Selectively (Recommended)
The code automatically uses Puppeteer only for events that failed price extraction:
- Events with `price === 'See tickets'`
- Events with `priceAmount === undefined`

### Option 3: Manual Usage
```typescript
import { extractPriceWithPuppeteer } from './src/lib/scraper/puppeteer-scraper';

const priceData = await extractPriceWithPuppeteer(eventUrl);
```

## Performance Impact

**Static Scraping:**
- Speed: ~100-500ms per event
- Success Rate: 70-85% (with enhanced patterns)

**Puppeteer Scraping:**
- Speed: ~2-5 seconds per event (10-50x slower)
- Success Rate: 85-95% (can access JS-rendered content)

**Recommendation:** Use Puppeteer selectively for events that fail static extraction.

## Files

- `src/lib/scraper/puppeteer-scraper.ts` - Puppeteer utilities
- `src/lib/scraper/detail-scraper.ts` - Optional Puppeteer support
- `src/lib/scraper/source-eventbrite.ts` - Automatic Puppeteer fallback

## Testing

```bash
# Test Puppeteer availability
node -e "console.log(require('./src/lib/scraper/puppeteer-scraper').isPuppeteerAvailable())"

# Run scraper with Puppeteer enabled
USE_PUPPETEER=true npm run scrape
```

---

**Status:** ✅ Optional Enhancement Ready  
**Installation:** ⏳ Manual (only if needed)  
**Default:** ❌ Disabled (use static scraping first)
