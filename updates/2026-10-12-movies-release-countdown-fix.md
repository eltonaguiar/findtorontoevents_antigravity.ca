# Movies release countdown: frozen January date repaired at source

## Root cause

The original React component in the separate
`eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` repository,
`movieshows/src/components/VideoCard.tsx`, calculated release countdowns using:

```typescript
const today = new Date("2026-01-28");
```

The same fixed date was in the deployed
`/MOVIESHOWS/_next/static/chunks/6d9ad93a5abfae37.js` bundle.
On October 12, Toy Story 5 still displayed "In 4 Months". Parsing its
date-only string as UTC also displayed June 18 instead of June 19 in a
North American browser.

## Fix and preservation

With user approval, the original movie source was checked out separately in
the session workspace. Its component now calculates the countdown after
hydration from the viewer's current calendar day and refreshes it every
minute. Calendar-day arithmetic is unaffected by daylight-saving changes.
Malformed dates fail explicitly and are logged.

Past/current release dates say **Released**, not **Streaming Now**; the date
does not prove current streaming availability. Date-only values are formatted
at local noon to avoid the UTC/local one-day shift.

The original movie app was rebuilt, type-checked, and statically exported.
Only movie assets were deployed; the events homepage was not touched.
The 102 original headings were checked against the rebuilt export before
replacement. MovieShows2 retains all four existing enhancement scripts:
scroll-fix, db-connector, ui-minimal, and ms2-enhancer.

The corrected generated MovieShows1 HTML and MovieShows2 app HTML are
preserved in this repository. The original TypeScript change, helper,
regression tests, and source documentation live on the isolated
`fix/movie-release-countdown-oct12` branch in the source checkout.

## Verification

- `TZ=America/Toronto node --experimental-strip-types --test tests/release-date.test.mjs`
  in the original movie source: **7 passed**, including Toy Story 5 in
  October, same-day/tomorrow, future countdown thresholds, DST, invalid dates,
  hydration, and timer cleanup.
- `npm run build` in that source: **passed** Next compilation, TypeScript
  checking, and static export.
- Existing repair tests: **29 passed** across the database configuration and
  legacy routing tests; rating-display regressions: **6 passed**.
- Uploaded 26 rebuilt movie assets per version over FTPS to both
  findtorontoevents.ca and tdotevent.ca before replacing their landing HTML.
  No old hashed assets were deleted.
- Fresh production browser at `/MOVIESHOWS/` showed Toy Story 5 as
  **Jun 19, 2026 / RELEASED**, with no "4 Months" countdown.
- Fresh production browser at `/MOVIESHOWS2/app.html` showed varied TMDB
  ratings after its enhancement-cache version was advanced.

## Remaining limitations

This corrects time calculation, not the January-era static catalogue's
factual descriptions, poster URLs, theatre assertions, or independently
unverified IMDb values. MovieShows2's refreshed database feed is separate.
The user later supplied a valid GoDaddy-specific credential; the same rebuilt
movie assets and rating fixes were deployed there after localhost validation.
Its separate refresh completed with zero errors and 7,901 total titles.
