# Surface 1 — findtorontoevents.ca audit

**Date:** 2026-05-04 05:26 UTC
**Probe:** `tmp/surface1_events_audit.js` (Playwright headless, 1440x900)
**Artifacts:** `tmp/surface1_artifacts/{summary,chips,gear,tabular,console,pageerrors,netfail,after_scroll,selector_probe}.json`
**Live page sha (PR #778):** 91f7579cdd67 (~10 min before run)

## TL;DR

Live oscillation fix from PR #778 is **partially effective** — `[FILTERS]` still fires 46× per page load (down from 48 baseline; not down to 1× as targeted). Three confirmed live bugs. Counter logic is actually correct; prior audit's "0 cards visible" finding was a **selector-false-negative** in the prior probe (the new probe confirms cards render). **However, Today/Tomorrow/This Week genuinely return counter=0** — this is a real production gap (zero events surfaced for the most useful filters).

## Confirmed live bugs

### BUG-1 (P0 / critical) — Today / Tomorrow / This Week show 0 events
- **Repro:** load `https://findtorontoevents.ca/`, click `🔥 Today` chip → counter = `0`. Same for Tomorrow + This Week.
- **Console evidence:** `[FILTERS] Shown: 0 Hidden: 50`
- **Root cause hypothesis:** date-window comparator in `applyFilters` (line 3450, `TORONTOEVENTS_ANTIGRAVITY/index.html`) treats `event.date` as future-only or compares the wrong field. With 11,290 events in `events.json` it is statistically impossible for "This Week" to be empty. Likely a TZ off-by-one or `Date.parse` failure on the bulk source (Toronto Public Library, 6,396 records, ~56% of corpus).
- **User impact:** the highest-intent filter shows nothing; bounces users to "All Dates" or away.

### BUG-2 (P1 / high) — `applyFilters` still fires 46× on initial load
- **Repro:** `tmp/surface1_artifacts/console.json` — count of `[FILTERS]` lines = 46.
- **Status vs PR #778:** marginal change (48→46). Mutex retry queue from PR #773 is firing on no-op DOM state. Likely cause: a MutationObserver triggered by lazy-load batches re-arming the queue.
- **User impact:** wasted CPU; counter flicker; risk of regression to the 195↔196 oscillation under slow networks.

### BUG-3 (P1 / high) — Tabular view click does not render a `<table>`
- **Repro:** click any element with text "Tabular" → `tables = 0, divGrids = 1`.
- **Note:** tabular-view PR `feat/tabular-view-enhancement-2026-05-04` (333 LOC) targets a div-grid structure (`role="grid"`), not a `<table>`. The probe found `divGrids: 1`, so the view IS rendering, but as div-grid. **Selector update needed in tests + likely UX clarity needed for users expecting an HTML table.** Sortable headers / CSV export not validated by this probe.

## Validated / refuted prior findings

| Prior finding (`reports/eventsite_inspection_2026_05_04.md`) | Status |
|---|---|
| All 6 chips return 0 visible cards | **REFUTED** — selector `.group:not([style*="display: none"]) [class*="event-card"]` was stale. New probe with `.group` finds 18–67 cards visible across chips. Counter accuracy OK on `All Dates`/`This Month`/`Next Month`. |
| Today/Tomorrow/This Week counter=0 | **CONFIRMED** — and counter is truthful, not a probe artefact. (Promoted to BUG-1 above.) |
| `applyFilters` fires 20× | **PARTIALLY CONFIRMED** — now 46× initial. Still oscillating. |
| Gear panel not detected | **REFUTED** — bottom-right gear opens; 15 fixed/absolute panels detected post-click. After scroll, 33 still visible (no "blur/disappear"). Need user-perceptual repro to nail down the "blurs on scroll" complaint. |
| Tabular view table not visible | **CONFIRMED** as written — but the PR uses a div-grid (`role="grid"`), so the test selector should be updated rather than treated as a regression. |

## Network / errors

- 1 React #418 hydration error (pre-existing, non-blocking minified bundle).
- 9 net failures (ad blocker + PostHog 127.0.0.1 dev telemetry — noise).

## Feature design

See `reports/surface1_max3_per_source_design.md` for the gear-icon "Max 3 events per day per source" toggle (Eventbrite-exempt). Wires into `applyFilters` line 3450 + persists via existing `toronto-events-settings` localStorage key (line 3370). Key risk: cap interplay with counter-update ordering can re-trigger the oscillation (BUG-2) if cap is applied after counter recompute.

## More-sources recommendation

8 priorities listed (TIFF Bell Lightbox P0, Bandsintown P0, City of Toronto Open Data P1, indie cinemas P1, theatre P1, sports P2, festival expansion P2, Harbourfront re-scrape). See design doc.

## Standing recommendation

**Ship-today:** investigate + fix BUG-1 (Today/Tomorrow/This Week date comparator). This is the highest-leverage user-visible defect.
**This-week:** BUG-2 oscillation root cause (MutationObserver re-arm), tabular-view test-selector update + CSV/sort validation, ship the Max-3-per-source feature behind the gear toggle (default OFF; opt-in).
**Next-sprint:** TIFF + Bandsintown + Toronto Open Data integrations; user-prefs API endpoint for cross-device persistence.
