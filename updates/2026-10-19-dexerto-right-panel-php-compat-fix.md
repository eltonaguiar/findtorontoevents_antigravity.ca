# Fix: Dexerto News Right Panel showed "unavailable" on live site

## Date
2026-10-19

## What was broken
The new `🎮 Dexerto News` section in the weather page right panel
(`weather/index.html`) displayed only "Dexerto news unavailable" on the live
site (`https://findtorontoevents.ca/weather/`), even after deployment.

Root cause: the endpoint `weather/api/dexerto_news.php` was failing with PHP
**parse errors** on the production server because it is running a legacy PHP
version that does not support:

1. `const` array declarations in the `array(...)` shorthand form at that scope
   (the original T_CONST error on the live server), and
2. anonymous functions / closures (the later "unexpected T_FUNCTION,
   expecting ')'" error at the `array_map(function ($it) {` call).

Because the endpoint returned a PHP error page instead of valid JSON, the
client-side `loadSideDexerto()` fetch hit the `.catch()` branch and painted the
"Dexerto news unavailable" fallback. The fallback to Google News never got a
chance to run since the script died at parse time.

## What changed
In `weather/api/dexerto_news.php`:

- Replaced the `const DEXERTO_FEEDS = array(...)` declaration with a classic
  `$DEXERTO_FEEDS = array(...)` variable (works on all PHP versions).
- Removed both `array_map(function ($it) { ... }, ...)` closures and replaced
  them with plain `foreach` loops that tag each item with
  `$it['source'] = 'dexerto';` — fully compatible with legacy PHP.

## Deployment
Deployed `weather/api/dexerto_news.php` and `weather/index.html` to
`findtorontoevents.ca/weather/` via `tools/deploy_to_ftp.py --weather-only`.

## How it was verified
1. **Endpoint** — `curl https://findtorontoevents.ca/weather/api/dexerto_news.php`
   now returns `HTTP 200` with valid JSON: `{"ok":true,"fetched_at":...,"items":[...]}`
   containing 6 real Dexerto articles (title/url/date/source), e.g.
   *"GTA 6 devs tried a million weapon wheel alternatives…"* with
   `source:"dexerto"` and URLs under `dexerto.com`.
2. **Playwright (live remote)** — added `tests/dexerto_right_panel.spec.ts`
   and ran it against the live site:
   `VERIFY_REMOTE=1 npx playwright test tests/dexerto_right_panel.spec.ts --project="Desktop Chrome"`.
   Result: **1 passed**. The test asserts `#side-dexerto li a` count > 0,
   no `.side-empty` fallback state, and the first link points to
   `dexerto.com`.

## Files touched
- `weather/api/dexerto_news.php` — legacy PHP compat fix (no closures, no
  `const` array).
- `tests/dexerto_right_panel.spec.ts` — new Playwright verification spec.
- `playwright.config.ts` — added the new spec to `testMatch`.
