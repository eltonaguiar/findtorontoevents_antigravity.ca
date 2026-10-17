# Weather page: dynamic conditions + nav + side panel (2026-10-17)

## What changed
- `weather/index.html`: made "Will it be sunny?" check day/night-aware (clear nights no longer reported as sunny); daylight-left now shows time until next sunrise at night; jacket verdict emoji/reason adapt to day/night; UV shows "(day max)" at night; season uses Toronto TZ; speech wording adapts; added day/night indicator and real-feel type.
- Added collapsible left navigation panel (hamburger) with links to main site sections, similar to main page quick nav.
- Added collapsible right side panel with 5 upcoming events (from /events.json) and 5 latest news (from /fc/api/news_feed.php), plus links to events and news pages.

## Verification
- Playwright `tests/weather_page.spec.ts`: 4/4 pass, 0 JS errors.
