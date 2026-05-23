# Surface 1 — "Max 3 events per day per source" — Design Doc

**Date:** 2026-05-04
**Surface:** findtorontoevents.ca homepage gear-icon settings panel
**Status:** Design only — read-only on production code

## Where to wire

`TORONTOEVENTS_ANTIGRAVITY/index.html`:
- **Settings persistence pattern** to mirror: line 3370 (`localStorage.setItem('toronto-events-settings', JSON.stringify(s))`) and line 5939 (`fte_os_sections`). Reuse the `toronto-events-settings` key — add `s.maxThreePerSourcePerDay = boolean`.
- **Gear panel surgery:** the bottom-right gear button at line 1029 (`aria-label="Open Settings"`) opens a panel rendered as a fixed/absolute container (audit detected 15 fixed panels post-click). Add the toggle inside that panel near the existing `showThumbnails`/`showMultiDay`/`showTBD` toggle row (lines ~3349–3372) — same `<button>` pattern with `.classList.toggle('active')`.
- **applyFilters integration:** line 3450 `function applyFilters()` — add a pre-filter step that consults `__RAW_EVENTS__` and tags any event beyond cap-3 with `data-cap-hidden="1"`. Then the existing visibility branch hides that card alongside other hidden categories. Do this BEFORE the date-window filter so cap counts reflect what user would see.

## Algorithm

```
if (s.maxThreePerSourcePerDay) {
  const buckets = new Map();  // key = `${YYYY-MM-DD}|${source}`
  const sorted = [...events].sort((a,b) =>
      (a.date || '').localeCompare(b.date || '') ||
      (a.title || '').localeCompare(b.title || ''));
  for (const e of sorted) {
    const src = (e.source || '').toLowerCase();
    if (src.includes('eventbrite')) { e._capPass = true; continue; }
    const key = `${e.date}|${src}`;
    const n = (buckets.get(key) || 0) + 1;
    buckets.set(key, n);
    e._capPass = n <= 3;
  }
}
```

## Persistence

- **Anonymous:** `toronto-events-settings.maxThreePerSourcePerDay` in localStorage (existing key).
- **Logged-in:** no `/api/user_prefs.php` endpoint exists today (grep found none). Fallback = localStorage only. Future PR: when auth ships, POST to `/api/user_prefs` with `{key: 'maxThreePerSourcePerDay', value: bool}` and merge on load.
- **Sync across tabs:** `window.addEventListener('storage', e => { if (e.key === 'toronto-events-settings') applyFilters(); })`.

## UI

Toggle button matching `multiDayBtn` style (line 3349). Label: "📊 Limit to 3 events per source per day". Tooltip (`title` attr): "Eventbrite is exempt — keeps full coverage of major source."

## Risks

- **Tie-breaking:** If a source has 100 events on one day, sort by `date` ascending then `title` ascending for determinism (above). Risk: alphabetical bias hides "Z..." events; acceptable trade-off for stable UX.
- **Toronto Public Library (6,396 events, 56% of corpus)** dominates today's view; cap-3 on TPL daily is the primary value driver — verify post-cap counter still ≥ ~80 events/day for healthy density.
- **Counter mismatch:** counter span at line 5113-area must be updated AFTER cap pre-filter, not before, or the user-visible count will diverge from card count (existing oscillation bug class).
- **Multi-day events** (`endDate > startDate`) — apply cap on `startDate` only to avoid double-counting.

---

## Phase 3 — More Toronto event source recommendations

**Already integrated** (from `events.json`, 11,290 total):
Toronto Public Library 6,396 · NOW Toronto 2,239 · Eventbrite 679 · Meetup 527 · ToDoCanada 438 · ROM 433 · Dating Events 281 · Toronto Botanical Garden 50 · Major Toronto Festivals 39 · Nathan Phillips Square 30 · AGO 21 · Massey Hall 19 · Toronto.ca Calendar 19 · Harbourfront Centre 16 · Sankofa Square 13 · Roy Thomson Hall 12 · Scotiabank Arena 9 · The Bentway 8 · CitySwoon 5 · TO Live 5 · Toronto Zoo 4 · 25dates.com 3.

**Recommended additions** (priority · approach):
1. **TIFF Bell Lightbox** (P0 · scrape `tiff.net/calendar` JSON-LD) — major film/cultural; missing.
2. **Bandsintown API** (P0 · public API key, geo=Toronto) — concerts, dense feed, ethical.
3. **City of Toronto Open Data — Festivals & Events** (P1 · CKAN JSON, CC-BY) — official calendar.
4. **Hot Docs / TIFF Lightbox / Paradise Theatre / Royal Cinema** (P1 · RSS or scrape) — independent cinema.
5. **Soulpepper / Tarragon / Crow's / Factory / Canadian Stage** (P1 · per-venue scrape) — theatre niche.
6. **Toronto FC / Raptors / Maple Leafs / Blue Jays** (P2 · official schedule JSON) — sports already partial.
7. **Luminato, TJF, Caribana, TIFF, Pride, NXNE** (P2 · already partial under "Major Toronto Festivals" — expand).
8. **TodoCanada** already integrated (438). **Harbourfront** already integrated (16) but under-scraped — re-run.

Skip: Facebook Events (TOS), private Discord/IG event pages (ethical/legal).
