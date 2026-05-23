# Toronto event discovery — coverage and Phase 2 supplements

## UnifiedTorontoScraper inventory (production path)

These sources are registered in [`tools/scrapers/unified_scraper.py`](../tools/scrapers/unified_scraper.py) `UnifiedTorontoScraper.__init__` in order:

| Area | Sources |
|------|---------|
| Official / City | Nathan Phillips Square, Sankofa Square, City of Toronto, Sofia Adel Giudice Notion |
| Ticketing / platforms | Eventbrite, Ticketmaster, Meetup |
| Media / listings | BlogTO, NOW Toronto, toronto.com |
| Major venues / culture | Harbourfront Centre, Major Venues (ROM, AGO, TIFF, Bentway, Evergreen), Toronto Public Library |
| Community | Unity Maps, Toronto Events Weekly, Creative Code Sheet, Light Morning Calendar, American Arenas |
| Large venues (Scrapling) | Scotiabank Arena, Massey Hall, Casa Loma, TO Live, U of T Events, Toronto Botanical Garden, BMO Field, Rogers Centre |
| Dating / singles | Dating Events, Fatsoma, Get Thursday, Manual Curated |
| High volume / festivals | Major Festivals, Mirvish, Songkick, Resident Advisor, Toronto Zoo, Luma |
| Tourism / calendars | ToDo Canada, Toronto.ca calendar, Destination Toronto |

API keys optional for: Ticketmaster (`TICKETMAST_CONSUMER_KEY`), Songkick (`SONGKICK_API_KEY`), Luma (`LUMA_API_KEY`).

## Gap scan (diagnostic)

[`tools/scan_event_gaps.py`](../tools/scan_event_gaps.py) compares a **live baseline** (`https://findtorontoevents.ca/events.json` with fallback to `/next/events.json`) to the unified scraper output (and optional supplements). It does **not** sync to production; it writes `reports/event_gaps_*.json`.

## Experimental supplements (gap scan only)

[`tools/scrapers/experimental_supplement.py`](../tools/scrapers/experimental_supplement.py) is **not** part of the default unified scraper. It runs only when:

```text
python tools/scan_event_gaps.py --include-experimental
```

| Mechanism | Purpose | Configuration |
|-----------|---------|----------------|
| RSS | Keyword-filtered items from a public feed (default: BlogTO FeedBurner) | `EXPERIMENTAL_RSS_URL` overrides default URL |
| iCal | Minimal VEVENT parsing from a calendar URL | `EXPERIMENTAL_ICAL_URL` must be set or this path returns nothing |

Items are tagged with source names like `Experimental RSS (feeds.feedburner.com)` so reviewers can ignore or promote them.

## Suggested future sources (not implemented)

Prioritize stable **APIs**, **official iCal/RSS**, and **permission to crawl** before fragile HTML:

- **Ticketing:** Showpass, Dice, AXS (Toronto listings) — evaluate TOS and robots.txt.
- **Institutions:** U of T / TMU / OCAD public event APIs or `.ics` where offered.
- **Open data:** City of Toronto CKAN / tabular event datasets (hostname and APIs change; validate before wiring to production).
- **Social:** Facebook / Google Events — usually auth-heavy; separate spike with compliance review.

Any new source should return the same event-shaped dicts as other scrapers and pass `python tools/validate_php52.py` only for PHP; Python scrapers follow existing patterns in `tools/scrapers/`.
