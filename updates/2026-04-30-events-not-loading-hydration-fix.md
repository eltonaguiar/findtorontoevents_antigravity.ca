# 2026-04-30 — "No Events Loaded" empty state on mobile (Samsung S25 Ultra report)

## What users saw

On findtorontoevents.ca homepage, mobile users hit the React empty-state banner:

> ⚠️ **No Events Loaded**
> Unable to load events. This could be due to:
> • Network connectivity issues
> • CORS blocking the GitHub fetch
> • Events.json file not accessible
> Check browser console (F12) for detailed error messages.

Reported on a Samsung Galaxy S25 Ultra. Reproduced via Playwright with the
S25 Ultra UA + viewport, but only intermittently — desktop and iPhone profiles
showed cards rendering despite the same React #418 hydration warning.

## Root cause

The React `useEventsFromGitHub` hook in `next/_next/static/chunks/afe53b3593ec888c.js`
does `Promise.any(...)` across **four** parallel event-source fetches:

```js
let r = [
  { url: `${origin}/events.json?t=...`,                     name: "Local Root" },
  { url: `${origin}/TORONTOEVENTS_ANTIGRAVITY/events.json`, name: "Local Subdir" },
  { url: `${origin}/data/events.json?t=...`,                name: "Local Data Folder" },
  { url: githubRawUrl,                                      name: "GitHub" },
];
return await Promise.any(r.map(e => f(e.url, e.name)));
```

Every one of those URLs gets caught by the homepage `window.fetch` interceptor in
`TORONTOEVENTS_ANTIGRAVITY/index.html` and rerouted to `/next/events.json`. So
**every page load fired four simultaneous 16 MB downloads** (~64 MB total per
page). The interceptor used `response.clone()` so both the interceptor and the
React caller could parse the body — but on slower mobile networks the
clone/original body reads can race, leaving the React caller with a partially
consumed body. When `response.json()` returns `[]` or throws, the React hook
sets `events: []` → `0 === e.length` → the banner above renders.

Static infra was healthy throughout: `events.json` returned 200 with 16 MB and
6 950 future-dated events, all Next.js chunks returned 200, and three mirror
hosts served identical content. The break was purely in the client fan-out.

## What changed

`TORONTOEVENTS_ANTIGRAVITY/index.html`, lines 46-122 — the fetch interceptor:

- **Coalesce**: a single `loadEventsText()` call fires once per page load. All
  subsequent `fetch(...events.json...)` requests resolve from the cached text.
- **Source-of-truth as text**, not as a Response: avoids `response.clone()` /
  body-sharing races entirely.
- **Synthesize a fresh `Response` per caller** from the cached text, so each
  React data-source path gets its own untouched body to parse.
- **Fallback chain preserved**: `/next/events.json` → `/events.json` →
  `/data/events.json` → GitHub raw, same order as before, but executed once.
- **`window.__RAW_EVENTS__`** still populated for the legacy `applyThumbnails()`
  imperative injector elsewhere on the page.
- Past-event filtering removed from the interceptor (it only mutated the global,
  not React's data, so it was effectively dead code; React filters past events
  itself once `now` is set client-side).

## Verification

Pre-deploy (Playwright with S25 Ultra UA + 412×915 viewport, real network to
production /next/events.json):

| Metric                              | Before patch | After patch |
|-------------------------------------|--------------|-------------|
| `events.json` HTTP requests / load  | 4            | **1**       |
| Bytes downloaded for events / load  | ~64 MB       | **~16 MB**  |
| `[Data Source] Success` lines       | 4 (all 10864)| 4 (all 10864) |
| `glass-panel` cards rendered        | 56           | 56          |
| `card-thumbnail` images injected    | 47           | 47          |
| `"No Events Loaded"` banner visible | sometimes    | never       |
| `window.__RAW_EVENTS__.length`      | 6796 (pre-filtered) | **10864** (full, parity with React) |

Post-deploy validation steps:
1. `gh run watch` the `deploy-fte-index` workflow until it succeeds.
2. Re-run `.tmp_research/check_s25_ultra.mjs https://findtorontoevents.ca/` and
   confirm `Total requests to events.json: 1` + no "No Events Loaded" text.

## What this does NOT fix

- **Minified React error #418 (hydration mismatch)**: the Next.js `EventFeed`
  component computes a different filtered count when `now=undefined` at SSR
  vs. `now=Date.now()` at CSR. The error logs to console but auto-recovers and
  doesn't affect rendering. Fix lives in the separate Next.js source repo
  `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` — wrap `now` in `useEffect` /
  `suppressHydrationWarning`. Not blocking.
- **The `[DIAGNOSTIC] Data exists but NO cards rendered` console alarm**: the
  alarm uses selector `[class*="event-card"]` but cards render with class
  `glass-panel` — false positive. Removed in this same patch (the diagnostic
  block was rewritten as part of the coalesce refactor).
