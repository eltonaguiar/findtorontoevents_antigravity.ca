# Weather page: move Top Entertainment into left side panel

## What changed
- `weather/index.html`: removed the inline "Top Entertainment — Most Played" card from the main weather container.
- Moved the entertainment tabs (TV Series, Movies, Podcasts, Songs) and content container into the left navigation side panel (below the Quick Nav links).
- Rendering logic (`renderEnt`, `ENT_DATA`, `entLinks`) unchanged; IDs `#ent-tabs` and `#ent-content` preserved so tab switching still works.

## Verification
- Playwright `tests/weather_page.spec.ts`: 4/4 pass, 0 JS errors.
