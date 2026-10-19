# Weather Page — Reset Look Button + Goodreads Self-Dev Books (2026-10-18)

## Problems

1. **Unrecoverable bad theme.** A user clicked the **Glass** skin; the glassy translucent
   cards blended the text into the live weather background and they couldn't read the page
   anymore. The chosen theme (plus FX filter, scene, layout, extras-visibility and player
   size) is cached in `localStorage` (`weather-theme`, `weather-fx`, `weather-scene`,
   `weather-layout`, `weather-hide-extras`, `weather-player-size`), so the unreadable look
   came back on every visit with **no way to reset**.
2. **Weak books widget.** The right panel's "Self-Dev Books" pulled the 5 newest
   Open-Library self-help books — random low-quality titles, not actual top books.

## Changes — `weather/index.html`

### Reset look (recovery button)

- New fixed button `#look-reset` ("↺ Reset look") under the side-panel toggle
  (`top:66px; right:14px; z-index:300`). Deliberately **high-contrast** (solid `#fff`
  background, `#111` text, 2px dark border) so it stays readable on *any* theme —
  including the broken Glass state that triggered this bug.
- Second "🔄 Reset look & feel to default" button inside the Skins & Themes card, and a
  "🔄 Reset" button in the left nav-panel theme switcher.
- Delegated click handler (own `<script>` block): removes all six `weather-*` keys from
  `localStorage`, then `location.reload()` so every subsystem re-initializes to defaults
  (Auto theme, no FX, no scene, full layout, extras visible, medium player).
- Note: after reload the page re-caches the default values (e.g. `weather-theme='auto'`),
  so "reset" = keys back to defaults, not keys absent.

### Goodreads top self-development books

- Replaced the Open-Library "newest first" query with a curated `GOODREADS_SELFDEV` list
  of 24 all-time top self-development books (Atomic Habits, 7 Habits, Deep Work, Can't
  Hurt Me, …). Goodreads has no public API and blocks scraping, so the ranking is curated
  in-code; **covers and links resolve live** from Open Library (`search.json` by
  title+author → `cover_i`), falling back to a Goodreads search link.
- **Dynamic:** a Fisher-Yates shuffle picks 5 of the 24 on every page load, and the
  widget re-rotates every 15 minutes (`setInterval(loadSideBooks, 900000)`).
- Section retitled "📚 Top Self-Dev Books"; "more →" now points to Goodreads.

## Tests — `tests/weather_page.spec.ts`

- New: `reset look button clears cached bad theme (glass) and restores defaults` — seeds
  `weather-theme=glass`, reloads, asserts `body.theme-glass`, clicks `#look-reset`,
  asserts theme key is back to `auto`, Glass class gone, Auto button active.
- New: `self-dev books widget renders rotated Goodreads picks` — waits for
  `#side-books li a`, asserts 5 books render.
- Hardened 2 pre-existing flaky spots: `networkidle` → `domcontentloaded` (the Windy map
  iframe keeps network alive, making `networkidle` unreliable) and a longer initial wait
  for the Open-Meteo verdict fetch under parallel workers.

## Verification

```
npx playwright test tests/weather_page.spec.ts --project="Desktop Chrome" --workers=2
→ 6 passed (37.8s)
```

All inline `<script>` blocks also pass `node --check`.

## Deploy

```
python tools/deploy_to_ftp.py --weather-only
```
