# Fix: findtorontoevents.ca/weather — all weather display & forecast items missing

**Date:** 2026-10-19
**Symptom (user report):** "on findtorontoevents.ca/weather all items seem to be missing in
terms of the weather display and forecast" — the page showed the jacket-verdict skeleton with
every card empty (`--°`, `Loading…`, 0 forecast days, 0 hourly items), or a blank content area.

## Root cause (three failure paths, all reproduced in a real browser)

All three were confirmed with headless-Chromium probes against the live page before fixing:

1. **Any failed fetch wiped an already-good render.** `loadWeather()` did
   `#content.style.display='none'` on *every* call, including the 10-minute auto-refresh. A
   single network blip (or the API being briefly unreachable) hid the whole weather display and
   forecast and never restored them.

2. **A partial API payload produced a visible empty skeleton.** `render()` flipped
   `#content` visible as its *first* statement, then computed. A 200 response missing
   `daily`/`hourly` (or with a `null` `uv_index_max`, whose `.toFixed(1)` threw) made `render()`
   throw *after* the flip → every card stayed at its placeholder, and the error was written into
   the already-hidden `#loading` box, so the user saw an empty page with no error and no retry.
   This is the exact "everything missing" report.

3. **No timeout, no retry.** A single `fetch(url)` with no `AbortController` and one attempt —
   one transient error was fatal.

Two adjacent bugs found during the fix:

4. **Auto-refresh reverted a looked-up location to Toronto.** The 10-min `setInterval` called
   `loadWeather(LAT, LON, …)` with the *default* `LAT`/`LON`, which are never updated after a
   postal/geolocation lookup — so every refresh silently showed Toronto data under a mismatched
   area label.

5. **The decorative background ate clicks.** `#bg-container` / `.bg-layer` are purely visual but
   lacked `pointer-events:none`, so they intercepted pointer events over the loading box — a real
   user's tap on the (new) Retry button would have been swallowed.

## Changes (`weather/index.html`)

- **Publish only on success.** Moved the `#loading`/`#content` flip to the **end** of a fully
  successful `render()`. The page is never shown as an empty skeleton.
- **Payload shape guard.** `render()` now throws (before any DOM write) if `current`/`daily`/
  `hourly`/their `time` arrays are missing → routes to the error path instead of a half-render.
- **`uv_index_max` null guard** — `null.toFixed()` no longer throws mid-render.
- **Refresh keeps last data.** `loadWeather()` tracks `_wxRendered`; a failed *refresh* keeps the
  last good data on screen and shows a `#wx-stale` notice ("Couldn't refresh weather … showing
  the last update") with a Retry button, instead of wiping.
- **Timeout + retries.** `_wxFetchForecast()` wraps the fetch in an `AbortController` 10s timeout
  and 3 attempts with 500ms/1500ms backoff. Render/validation errors are *not* retried (they
  surface immediately to the error path).
- **Visible error + Retry.** On initial failure, `_wxShowFatal()` shows the error and a real
  `#wx-retry` button (`window.retryWeather()` replays the last request). The area label is
  committed only on success, so a failed lookup keeps label + data consistent.
- **Auto-refresh uses current coords.** `setInterval` now refreshes `_lastLat`/`_lastLon`.
- **Background click-through.** Added `pointer-events:none` to `#bg-container` and `.bg-layer`.

## Verification

- **New regression tests** added to `tests/weather_page.spec.ts`:
  - *failed refresh KEEPS last good data (no wipe) + shows stale notice*
  - *initial fetch failure shows a VISIBLE error + Retry button, and Retry recovers*
  - *partial API payload shows an error, never an empty skeleton*
  (Route matchers use a **regex**, not a glob — the built forecast URL contains
  `&timezone=America/Toronto`, and a Playwright glob `*` does not cross `/`.)
- **Local:** full weather spec 9/9 pass against the clean build.
- **Live:** deployed via `python3 tools/deploy_to_ftp.py --weather-only` (scoped to
  `/weather/`, `/jacket/`, `/doineedajacket/` only), then `VERIFY_REMOTE=1` full spec 9/9 pass
  against `https://findtorontoevents.ca/weather/`. Confirmed the deployed page carries the fix
  markers (`_wxFetchForecast`, `_wxShowFatal`, `_lastLat,_lastLon`, bg `pointer-events`).

## Note on the git working tree

`weather/index.html` in the working tree was **entangled with another session's uncommitted
restructure** (the embedded player moved into a right-side panel + a live-radio widget). To avoid
committing or deploying that WIP, the deployed artifact was built as **live + only this fix**
(no foreign restructure). The other session's uncommitted working-tree version was preserved
(restored after staging), so their work is not lost. The committed `weather/index.html` is the
verified-live clean build.
