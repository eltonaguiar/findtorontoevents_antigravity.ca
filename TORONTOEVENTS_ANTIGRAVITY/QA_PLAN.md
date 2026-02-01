# Toronto Events QA Skyrocket Plan 🚀

This plan outlines the strategy to achieve 99.9% reliability and data quality for the Toronto Event Aggregator.

## 1. Data Integrity & Validation
- **Keyword-Based Multi-Day Tagging**: Every event title and description will be scanned for keywords like "multiple dates", "recurring", "series", "check availability", and "weekly". These will be moved to the "Multi-Day" section automatically.
- **Started Event Filtering**: By default, the UI will hide events that have already started (based on the current timestamp in Toronto). A "Show Ongoing" toggle will allow users to opt-in.
- **Detailed Enrichment**: The scraper will spend more time on detail pages to extract:
  - Exact start/end times.
  - Sales status (Closed/Ended).
  - High-resolution images.
  - Price ranges (capturing both min and max).

## 2. Automated Quality Gates
- **Score-Based Thresholds**: Events with missing images, very short descriptions (<50 chars), or unverified locations will be marked as "Review Needed" and hidden by default.
- **Double-Pass Scraping**: 
  - **Pass 1**: Rapid list scraping to find new URLs.
  - **Pass 2**: Deep inspection of the 50 most imminent events to ensure timing is perfect.

## 3. Automation & Monitoring
- **GitHub Action Cron Job**: Automate scraping and deployment Every 6 hours to ensure data never goes stale.
- **Metadata Versioning**: Save `metadata.json` with the last successful scrape time and event counts to track scraper health.

## 4. Manual Verification Tools
- **Internal Dashboard**: A dedicated hidden route (or local script) to flag events that have broken links or "TBD" prices for manual cleanup.

## 5. UI/UX Polish
- **Explicit Pricing**: Every event card must show a price or "Free". If price is undetermined, it will show "Check Tickets" with a warning.
- **Price preferences**: Users can save their price range and filter settings across sessions.
