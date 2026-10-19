# WEATHER_FREEBUFF.MD — full Playwright QA of `https://findtorontoevents.ca/weather/`

**Run:** 2026-10-18 ~09:15–09:30 UTC · **Tool:** Playwright + headless Chromium (Node 22, `playwright` from repo `node_modules`)
**Targets:** live production `https://findtorontoevents.ca/weather/` (byte-identical to repo `weather/index.html`, 100,331 B — verified)
**Viewports:** desktop 1440×900 and mobile 390×844 · **Screenshots:** `/tmp/weather-shots/desktop.png`, `/tmp/weather-shots/mobile.png`
**Artifacts:** suite committed at `tools/qa/weather_page_playwright_check.js` (copy of `/tmp/weather_freebuff_test.js`), raw JSON `/tmp/weather_results3.json`, diagnostic probes `/tmp/weather_diag.js`, `/tmp/weather_bisect.js`, `/tmp/weather_fixtest.js`

---

## 1. Verdict

**38 PASS · 3 INFO · 2 FAIL · 0 WARN** across 43 assertions.

The weather page is in good shape: it loads in **~470 ms**, produces **zero JS/console errors**, **zero failed requests**, has a complete a11y baseline (`lang`, viewport meta, `h1`, alt coverage, labelled buttons/links), and every interactive widget works (nav drawer, side panel, entertainment tabs, media player tabs, audio button, extras collapse, postal-code location change).

Two real defects, both root-caused and reproduced:

| # | Severity | Defect |
|---|---|---|
| **F1** | **High (mobile UX)** | Horizontal page overflow at 390 px — `document.scrollWidth` = **1807 px** vs 390 px viewport. The hourly strip is the cause; a **one-line CSS fix is proven** (§3). |
| **F2** | Medium (a11y) | The nav drawer keeps `aria-hidden="true"` **while it is open**, hiding its whole subtree (Quick Nav + Top Entertainment + theme buttons) from screen readers. |

Plus three informational observations (§4) that are design choices, not bugs.

---

## 2. Test matrix (live run, 2026-10-18 09:2x UTC)

### 2.1 Load, health, data

| Check | Result | Evidence |
|---|---|---|
| `page_load` | PASS | HTTP 200 in 466 ms |
| `page_title` | PASS | `Toronto Weather \| findtorontoevents.ca` |
| `page_js_errors` | PASS | none |
| `console_errors` | PASS | none |
| `failed_requests` | PASS | none (0× ≥400, 0 requestfailed across 23 resources) |
| `body_rendered` | PASS | 5,256 chars of visible text |
| `last_updated_stamp` | INFO | `Oct 18, 5:15 AM ET (Toronto)` — refresh cadence is per-load, values live |

### 2.2 Weather widgets

| Check | Result | Evidence |
|---|---|---|
| `current_temperature` | PASS | `5°C` |
| `feels_like` | PASS | `Feels like 2°C (cold)` |
| `condition_text` | PASS | `🌙 Clear sky` |
| `humidity` | PASS | `70%` |
| `cloud_cover` | PASS | `Crystal-clear skies — great stargazing.` |
| `wind_gust` | PASS | `32 km/h` |
| `daylight_widget` | PASS | `13h 14m of daylight left` |
| `area_label` | PASS | `Area: Toronto, ON, Canada` |
| `hourly_forecast_rendered` | PASS | **24** hour cells |
| `daily_forecast_rendered` | PASS | **7** day cards |
| `rain_probability_bar` | INFO | `0%` — bar correctly renders empty ("Dry") |

### 2.3 Interactions

| Check | Result | Evidence |
|---|---|---|
| `entertainment_tabs_present` | PASS | 4 tabs (`TV / Movies / Pods / Songs`) — they live **inside the left nav drawer** |
| `ent_tab_0..3_click` | PASS ×4 | each click leaves exactly 1 `.ent-tab.active` and repopulates `#ent-content` (6.6–7.7 KB of markup) |
| `player_tabs_present` | PASS | 4 tabs |
| `player_tab_0..2_click` | PASS ×3 | tab 0/1 → `player-video` visible; tab 2 → `player-songs` visible; no page errors |
| `audio_button_click` | PASS | clicked, no page error |
| `extras_toggle_clickable` | PASS | `Hide optional sections` → `Show optional sections` → restored |
| `nav_toggle_opens` | PASS | `transform: matrix(1,0,0,1,0,0)` (open) |
| `nav_close_works` | PASS | `transform: matrix(1,0,0,1,-290,0)` (closed); overlay `.open` removed |
| `nav_aria_hidden_while_open` | **FAIL** | `aria-hidden="true"` while `open=true` → **F2** |
| `postal_lookup` | PASS | `Area: Toronto, ON, Canada` → `Area: Postal code M5V 2T6, Canada`, temp re-rendered `5°C`, 0 page errors |

### 2.4 Responsive + a11y

| Check | Result | Evidence |
|---|---|---|
| `mobile_no_horizontal_overflow` | **FAIL** | `scrollWidth 1807` vs `innerWidth 390` → **F1** |
| `mobile_nav_opens` | PASS | drawer visible at 390 px |
| `mobile_js_errors` | PASS | none |
| `html_lang` | PASS | `en` |
| `viewport_meta` | PASS | present |
| `h1_present` | PASS | `🌤️ Toronto Weather` |
| `images_alt_coverage` | PASS | 0/2 images missing `alt` |
| `buttons_without_label` | PASS | 0 unlabelled buttons |
| `links_without_text` | PASS | 0 empty links |
| `perf_timing` | INFO | DCL 239 ms · load 463 ms · 23 resources · 21 third-party |

---

## 3. F1 (High) — mobile horizontal overflow, root-caused with a proven one-liner

### Symptom
At a 390 px viewport the document scrolls sideways: `document.documentElement.scrollWidth = 1807`.

### Root cause (measured in-browser)
- `.grid{display:grid;grid-template-columns:1fr 1fr}` collapses to a single `1fr` track under the `max-width:700px` media query — **confirmed applied** (`matchMedia('(max-width:700px)') === true`, computed `grid-template-columns: "1786px"`).
- A `1fr` track has an automatic minimum of `min-width:auto`, so it grows to its widest item's **min-content**.
- The widest item is the first `.card.span2` ("🕐 Next 24 Hours"): its min-content is **1786 px**, driven entirely by `#hourly` (`min-content 1744 px` = 24 hour cells ≈ 72 px each). Measured per-card min-content: hourly **1786**, 7-day 182, weather cards 152/142 — nothing else is close.
- Net effect: `.hourly`'s `overflow-x:auto` never engages (`scrollWidth == clientWidth == 1744`), so the *page* scrolls instead of the strip, and `body{overflow-x:hidden}` then **clips** it — on a phone the right-hand side of the page is simply unreachable.

### Fix (verified live in the page, read-only injection)
Adding `.grid > *{min-width:0}` collapses the track and restores the intended strip scrolling:

| Metric | Before | After |
|---|---|---|
| `grid-template-columns` | `1786px` | `348px` |
| hourly card width | 1786 px | 348 px |
| `#hourly` clientWidth / scrollWidth | 1744 / 1744 (**no internal scroll**) | 306 / 1744 (**scrolls, as designed**) |
| `document.scrollWidth` @390 | **1807** | **390** ✅ |

```css
/* weather/index.html — add next to the .grid rule (line ~67) */
.grid > *{min-width:0}
```
(`.hourly{min-width:0}` alone is not sufficient — the bound applies to the grid *item*, i.e. the `.card`.)

---

## 4. F2 (Medium) — drawer stays `aria-hidden="true"` while open

`<aside id="nav-panel" aria-hidden="true">` is static markup; `openNav()`/`closeNav()` only toggle the `open` class (weather/index.html L1396-1397), so the open drawer — Quick Nav links, **Top Entertainment** tabs and content, and all 12 theme buttons — is announced as hidden to assistive tech. The `#side-panel` (right drawer, L629) has the same static `aria-hidden="true"`.

```js
// weather/index.html L1396-1397 — suggested fix
function openNav(){var n=document.getElementById('nav-panel');n.classList.add('open');n.setAttribute('aria-hidden','false');document.getElementById('nav-overlay').classList.add('open');}
function closeNav(){var n=document.getElementById('nav-panel');n.classList.remove('open');n.setAttribute('aria-hidden','true');document.getElementById('nav-overlay').classList.remove('open');}
// …same pattern for openSide()/closeSide()
```

---

## 5. Informational observations (design choices, not defects)

1. **Entertainment tabs are buried in the nav drawer.** `#ent-tabs` ("Top Entertainment — Most Played") lives inside `#nav-panel`, so on any viewport a user must open the ☰ drawer to reach TV/Movies/Pods/Songs. All four tabs work correctly once opened (§2.3); flagging only because the module reads like it belongs on the page.
2. **Player tab semantics.** Of the 4 `#player-tabs`, tab 0 and tab 1 both resolve to the same visible pane (`player-video`); `player-radio` never became visible in this run — either it is gated behind a station load or it is a duplicate target worth a second look.
3. **Third-party surface.** 21 of 23 resources are third-party: `api.open-meteo.com` (forecast), `geocoding-api.open-meteo.com` + `api.zippopotam.us` + `nominatim.openstreetmap.org` (location), `openlibrary.org`, `hacker-news.firebaseio.com`, `api.piped.private.coffee` (media search), plus outbound links to AccuWeather/YouTube/Spotify/EarthCam/SomaFM. All responded OK on this run — no CORS or blocked-request noise — but this page has no offline/degraded mode if any of them dies.
4. **Data freshness.** The `#last-updated` stamp (`Oct 18, 5:15 AM ET`) tracks the data itself, not the page build; a re-render picked up new values within one reload, so the metric is genuinely dynamic (no static-prose problem like the `/audit` one fixed earlier today).

---

## 6. Repro

```bash
node tools/qa/weather_page_playwright_check.js "https://findtorontoevents.ca/weather/" /tmp/weather-shots > results.json
# targeted diagnostics:
node /tmp/weather_diag.js       # drawer/overlay/tab geometry + mobile wide-element list
node /tmp/weather_bisect.js     # per-card min-content widths
node /tmp/weather_fixtest.js    # before/after proof of the `.grid > *{min-width:0}` fix
```

### Test-harness errata (so nobody re-files these as bugs)
Two checks in the first iteration reported false FAILs and were corrected before this report:
- `nav_close_works` originally asserted `display:none`/`width===0` for the closed drawer — the drawer's closed state is `transform:translateX(-100%)`, so the old assertion could never pass. Re-measured via the `open` class / transform: **open and close both work** (including overlay-click dismissal).
- The entertainment tabs timed out in the first pass because they sit inside the closed drawer (`x = -266`); opening the drawer first yields 4/4 PASS. The player tabs similarly need the drawer closed (it overlays at `z-index:400`).

---

## 7. Recommended next actions

1. **Ship the F1 one-liner** (`.grid > *{min-width:0}`) — mobile usability, one line, verified.
2. **Ship the F2 `aria-hidden` toggle** for `#nav-panel` and `#side-panel`.
3. Decide whether Top Entertainment deserves a slot on the page rather than only in the drawer.
4. Add a small degraded-mode notice (or cached fallback) for the 8 third-party APIs this page depends on.

*NFA — QA report only; no production files were modified by this test pass.*
