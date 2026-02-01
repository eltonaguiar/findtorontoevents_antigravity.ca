# Toronto Events App - Sprint Plan (Jan 2026)

## Priority 1: Data Quality & Filtering
- [ ] **Fix Dating Events Scraper**
    - Audit `source-eventbrite.ts`: Verify `organizers` URL scraping.
    - Test individual organizer URLs (e.g. Toronto Dating Hub) to see if they yield JSON-LD or need a different parser.
    - Ensure `categorizeEvent` correctly tags them as 'Dating'.
- [ ] **Enhanced Categorization**
    - Update `categorizeEvent` in `utils.ts`:
        - Add 'Construction' category (keywords: forklift, scissor lift, training, etc).
        - Refine 'Tech' and 'Dating' keywords.
- [ ] **Filtering & Defaults**
    - Update `EventFeed.tsx`:
        - Hide 'Construction' category by default.
        - Hide 'Sold Out' events by default (add settings toggle).

## Priority 2: Timezone & DateTime
- [ ] **Fix Timezone Display**
    - The raw data might be being parsed as UTC and then displayed as local, causing shifts.
    - Verify `normalizeDate` in `utils.ts`.
    - Ensure strictly `America/Toronto` handling.

## Priority 3: UI/UX Improvements
- [ ] **Preview Panel Overhaul**
    - Fix "See Tickets" / Heart overlap.
    - Implement Split View: Data on left, Iframe on right (or top/bottom).
- [ ] **Settings Panel**
    - Add Gear Icon.
    - Category toggles (Show/Hide Construction, etc).
    - Sort preferences.

## Priority 4: Advanced Features
- [ ] AI Chat / Search Bar improvements.
