# Weather Page Testing Protocol (findtorontoevents.ca/weather/)

## Preconditions
- Local server running: `python3 tools/serve_local.py` (port 5173) OR Playwright webServer auto-start.
- For remote: `VERIFY_REMOTE=1`.

## Test Suite
- `tests/weather_page.spec.ts` — 4 tests:
  1. Page loads, jacket verdict, no JS errors, core cards present.
  2. `/jacket/` redirects to `/weather/`.
  3. `/doineedajacket/` redirects to `/weather/`.
  4. Postal code lookup updates area label.

## Manual Checks
- Skins: click each skin; background updates; persisted in localStorage.
- Background FX: apply each filter; canvas filtered.
- Scenes: apply each scene; body background animates; weather particles remain.
- Layouts: apply each layout; background reframed.
- Collapse: per-section Hide/Show; "Hide optional sections" hides all optional cards.
- Last updated: shows ET (Toronto) timestamp, not stale.
- Quick links: open AccuWeather/Weather.com/Windy etc.
- Weather map: Windy iframe loads.
- Live cameras: YouTube streams load; no unavailable video.
- Player: music videos load, Top Songs Spotify embed loads, radio plays.

## Commands
- Local: `npx playwright test tests/weather_page.spec.ts --project="Desktop Chrome"`
- Remote: `VERIFY_REMOTE=1 npx playwright test tests/weather_page.spec.ts --project="Desktop Chrome"`

## Pass Criteria
- 4/4 tests pass.
- 0 JS errors (pageerror/console error excluding favicon/#418).
- No large empty boxes; player frame hidden until load.
- Last updated visible and accurate.
