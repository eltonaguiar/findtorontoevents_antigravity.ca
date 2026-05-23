# Kimi Swarm Enhancement Proposals — Live-State Review

> **Date:** 2026-05-04
> **Source proposal:** `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/enhancement_proposals.md` (676 lines, dated 2026-04-26, v0.5.2 target)
> **Live surface:** `TORONTOEVENTS_ANTIGRAVITY/index.html` (6,178 lines, hand-coded vanilla JS — NOT the Next.js EventCard subset)
> **Reviewer:** Claude Opus 4.7 (1M)
> **Mode:** read-only; no git, no commits

---

## 0. Architecture compatibility caveat (READ FIRST)

The proposal document was authored against a **hypothetical React/Next.js stack** with TypeScript components, Postgres/Supabase, JWT auth, and `/api/*` REST endpoints. **None of that exists in the live homepage.** Per `CLAUDE.md`:

> `TORONTOEVENTS_ANTIGRAVITY/index.html` IS the live findtorontoevents.ca homepage — it is NOT auto-generated, NOT a wrapper around the React app, NOT a "shell." 4,845 (now 6,178) lines of hand-coded HTML... the imperative `applyThumbnails()` injector pulls from `window.__RAW_EVENTS__`.

Every `*.tsx` filepath, `interface Foo {}`, `POST /api/user/settings`, and `CREATE TABLE` block in the proposal must be re-read as **"vanilla JS IIFE + localStorage + static `events.json`"**. Server-side persistence and JWT/auth flows are out-of-scope unless the agent also brings up the Next.js subapp at `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` (separate repo, builds the embedded grid only — does **not** own settings UI). The pragmatic path is **localStorage-only** for v1; sign-in sync is a later concern.

A live multi-source overlay already exists and reads from PHP at `/fc/api/events_get_sources.php?all=1` (`index.html:2219`). That is the only "backend" endpoint in play today.

---

## 1. Per-enhancement status

### F1. Gear Settings Modal — **PARTIAL**

- A "⚙️ Event System Settings" button exists at `index.html:994-995` (sidebar) and a top-right config button at `index.html:1021-1028` plus a bottom-right floating gear at `index.html:1029-1038`. **None of them open a modal** — they are visual placeholders with no `addEventListener('click', …)` wired.
- A localStorage settings store is already live: key `toronto-events-settings`, currently holding `{ showThumbnails: bool }` only (`index.html:3154`, `:3368-3370`). The persistence shape proposed by Kimi (anonymous → localStorage) is **already the right pattern** — just extend the existing key.
- "Show Multi-Day Events" / "Show TBD Events" / "Show Thumbnails" toggles already exist as floating chips (`index.html:3349-3372`). These are the de-facto "Display" tab today.
- **Fits hand-coded architecture:** YES, trivially. Build a vanilla `<dialog>` or absolute-positioned div, no React.
- **TS/JWT/DB schema in proposal §1.3-1.4: OUT-OF-SCOPE** for v1.

### F2. Smart Deduplication — **PARTIAL (server-side, not in homepage)**

- The multi-source loader at `index.html:2208-2330+` already **collapses duplicates upstream**: `events_get_sources.php?all=1` returns one canonical event per ID with a `sources[]` array (`:2289` "🎫 N Sources" badge). Dedup is done on the server, not in JS.
- The Jaro-Winkler fingerprint scheme proposed by Kimi is **redundant** for events that flow through that PHP endpoint. It would only help for events that bypass `/fc/api/events_get_sources.php` (i.e., raw `__RAW_EVENTS__` from `events.json`).
- Title-match heuristic in `findEventByTitle` at `:2253-2269` is a 70%-word-overlap matcher — already a (weaker) form of fuzzy dedup.
- **Fits architecture:** YES on server side (PHP), N/A on homepage.

### F3. Calendar Export (iCal + Google Calendar) — **NOT-STARTED**

- Zero references to `BEGIN:VCALENDAR`, `text/calendar`, `.ics`, or `google.com/calendar/render` in `index.html`. (`google.com/calendar` matches at `:1827, :3537, :3856` etc. are all about literal "Toronto Calendar" copy / code comments — not export.)
- **Fits architecture:** YES — pure client-side .ics builder against `window.__RAW_EVENTS__` is ~80 lines of JS. No backend needed for personal-use export. Google Calendar "Add to Calendar" links are URL-only.
- Proposal §3.3 `/api/export/calendar` endpoint is **OUT-OF-SCOPE** (no Node API server). Use a pure client-side `Blob` download.

### F4. Source Toggles & Provider Registry — **PARTIAL (display-only)**

- Multi-source data is already loaded and badge-displayed (`index.html:2287-2306`).
- No per-source enable/disable toggle exists anywhere.
- The "Provider Registry DB table" (`provider_registry`) in proposal §schema is **OUT-OF-SCOPE** in this repo; if it exists it lives in the PHP `/fc/api/` backend.
- **Fits architecture:** PARTIAL. Filter-by-source at the homepage layer can be done in vanilla JS by reading `event.source` / `event.sources[]` and adding a hidden-source set in localStorage.

### F5. 15 New Toronto Data Sources — **OUT-OF-SCOPE for the homepage repo**

- The homepage consumes a single, pre-merged `events.json`. Source ingestion happens elsewhere (`*_scraper.py` modules per `CLAUDE.md`, plus the PHP multi-source endpoint). Adding sources is a backend/scraper PR, not an `index.html` PR.
- **Fits architecture:** N/A — wrong repo surface. Belongs in the scraper modules.

### F6. Notification Preferences — **OUT-OF-SCOPE**

- Requires Web Push, service workers, server cron, email service, auth. None present. Proposal already labels P3/deferred to v0.7.0.

### F7. Weather-Aware Outdoor Filtering — **OUT-OF-SCOPE**

- Requires a `venue_type` field that does not exist in `events.json` today. Proposal already labels P3/deferred to v0.8.0.

### F8. Data Quality Dashboard (mentioned in exec summary) — **DONE elsewhere**

- The audit dashboard at `audit_dashboard/template.html` already covers data-quality reporting for the alpha engine. Events-side gap reporting is in `tools/scan_event_gaps.py` per `CLAUDE.md`. A homepage-embedded dashboard duplicates existing surfaces.

| # | Feature | Status | Architecture fit |
|---|---|---|---|
| F1 | Gear Settings Modal | PARTIAL | YES (vanilla) |
| F2 | Smart Dedup | PARTIAL (server) | N/A on homepage |
| F3 | Calendar Export | NOT-STARTED | YES (client-only) |
| F4 | Source Toggles + Registry | PARTIAL | PARTIAL |
| F5 | 15 New Sources | OUT-OF-SCOPE here | wrong repo |
| F6 | Notifications | OUT-OF-SCOPE | needs auth/server |
| F7 | Weather-aware | OUT-OF-SCOPE | needs venue tags |
| F8 | Data-quality dashboard | DONE elsewhere | duplicates audit |

---

## 2. Top-3 enhancements ranked by value/effort

### #1 — Calendar Export (.ics) — highest value/effort ratio

- **Value:** users have asked for "add to calendar" since v0.3; satisfies a real ongoing user request; zero backend dependency; works immediately for anonymous visitors.
- **Effort:** ~1 day. Pure client-side `Blob` of `text/calendar` MIME built from `window.__RAW_EVENTS__`. Per-card "Add to Google Calendar" link is a URL template.
- **PR title:** `feat(homepage): per-card iCal export and Google Calendar add link`
- **Branch:** `feat/homepage-calendar-export`
- **File edits:**
  - `TORONTOEVENTS_ANTIGRAVITY/index.html` near line ~3340 (alongside the existing floating-chip controls): add an "📅 Export filtered to .ics" floating chip that builds a VCALENDAR from the currently-rendered cards (read from `window.__RAW_EVENTS__` filtered by the same predicates `applyFilters()` uses).
  - In the multi-source panel template at `:2295-2306`, append one extra `<a>` per event: `https://www.google.com/calendar/render?action=TEMPLATE&text=...&dates=...&location=...`.
  - No new files, no React, no API.
- **Risk:** low — touches additive JS only; localStorage untouched; no impact on existing filter pipeline.

### #2 — Wire the existing gear button to a real settings panel (extend localStorage)

- **Value:** unlocks every other feature on this list (max-per-source, source toggles, dedup-on/off, calendar export config) by giving them a UI home. Three gear buttons exist today and **none are wired** — looks broken to users.
- **Effort:** ~2 days. Vanilla `<dialog>` element + section-list. Reuse `toronto-events-settings` localStorage key already in flight at `:3154, :3368-3370`.
- **PR title:** `feat(homepage): wire gear button to settings panel with display/sources/export tabs`
- **Branch:** `feat/homepage-settings-panel`
- **File edits:**
  - `TORONTOEVENTS_ANTIGRAVITY/index.html` `:994-995` and `:1021-1038`: add `id="open-settings-panel"` and a click handler.
  - Insert a new `<dialog id="settings-panel">` block near `:1038` with three sections: Display (mirrors the floating chips: showThumbnails, showMultiDay, showTBD), Sources (checkbox-per-source from `Object.values(multiSourceEvents).flatMap(e=>e.sources)`), Export (links to the .ics from PR #1).
  - Extend the localStorage shape: `{ showThumbnails, hiddenSources: [], maxPerSource: 3, exemptEventbrite: true }`.
- **Risk:** low — additive; existing chips keep working; no DOM the React grid relies on is touched.

### #3 — Max-N-per-source cap with Eventbrite exemption (homepage filter)

- **Value:** addresses the real complaint that Eventbrite dominates the feed. Easy to demo. Pairs naturally with PR #2 (uses the same panel).
- **Effort:** ~1 day. Insert a per-source counter inside `applyFilters()` (lookup the source via `eventData.source` or `eventData.sources[0].source_name` from the multi-source map at `:2213`).
- **PR title:** `feat(homepage): cap N events per source per day with Eventbrite exemption`
- **Branch:** `feat/homepage-max-per-source`
- **File edits:**
  - `TORONTOEVENTS_ANTIGRAVITY/index.html` inside `applyFilters()` (near `:3350` where filter chips are wired): add a sort-stable pre-pass that decrements a per-`(date, source)` counter and hides cards once `>= maxPerSource` (default 3); skip the cap when `source === 'Eventbrite'` and `exemptEventbrite === true`.
  - Settings live in the same localStorage key as PR #2.
- **Risk:** medium — interacts with the existing multi-day / TBD / past-event filter chains; needs Playwright validation that totals on the chip counter at `:4129` (`window.__RAW_EVENTS__.length`) update correctly.

---

## 3. Toronto data sources — rank to integrate first

**Caveat:** these belong in the scraper repo / PHP backend, NOT in `index.html`. The ranking below is for whoever owns ingestion. Rank = `(events/week) ÷ (integration days) × quality`, breaking ties by feasibility.

| Rank | Source | Type | Est. events/wk | Days | Q | Score | Why first 5 |
|---|---|---|---|---|---|---|---|
| 1 | **Ticketmaster Discovery API** | API | 300 | 2 | 88 | 13,200 | Generous 5k/day quota; covers concerts+sports+theatre; closes the biggest gap vs Eventbrite |
| 2 | **Toronto Open Data (CKAN)** | API | 60 | 1 | 65 | 3,900 | Zero auth, no rate limit, civic events nobody else has |
| 3 | **Bandsintown** | API | 180 | 1.5 | 75 | 9,000 | Already free-tier; pure music gap-filler |
| 4 | **Sports leagues (Jays/Raptors/Leafs/TFC)** | API | 40 | 2 | 90 | 1,800 | Highest data quality; aligns with Goal #2 (sports betting picks) — same data feeds both |
| 5 | **BlogTO RSS** | RSS | 50 | 0.5 | 60 | 6,000 | Cheapest integration; food+nightlife coverage missing from API sources |

Deferred:
- Songkick (#13 in proposal) → duplicative with Bandsintown.
- AGO/ROM/Harbourfront/TIFF → low volume; keep for phase 2.
- Meetup → OAuth2 friction + post-2023 API restrictions; not worth it.
- Facebook Events → ToS-violating scrape; do not integrate.
- TPL / Now Toronto → low events/week; phase 3.

---

## 4. Compatibility notes — proposals that assumed React/Next.js

Every section below in the original proposal needs an "**adapt to vanilla JS**" caveat before it ships:

- §1.3 `GearSettingsModal.tsx` + `interface GearSettingsModalProps` → vanilla `<dialog>` + plain `addEventListener`. No TypeScript anywhere in `TORONTOEVENTS_ANTIGRAVITY/index.html`.
- §1.4 `POST /api/user/settings` JWT round-trip → defer; localStorage is sufficient for v1. Re-introduce only when sign-in lands (`Sign In` mega-menu link exists at `:1029` but auth backend status is unknown to this review).
- §2.4 `lib/deduplicate.ts` → already done server-side at `/fc/api/events_get_sources.php?all=1`; do not re-implement in browser JS.
- §3.3 `/api/export/calendar` → use a pure client-side `Blob([icsText], {type:'text/calendar'})` + `URL.createObjectURL` download. No server needed.
- §4 `provider_registry` Postgres schema → out of scope here; if useful, lives in the PHP `/fc/api/` backend.
- §"Database Schema Changes" entire section → drop. Not applicable to the homepage repo.
- §"Implementation Roadmap" Phase 1-4 → re-budget. Realistically ~5 dev-days for PRs #1-#3 above. Sprint estimates of 6-8 weeks assume the React/SQL stack that does not exist here.

---

*End of review.*
