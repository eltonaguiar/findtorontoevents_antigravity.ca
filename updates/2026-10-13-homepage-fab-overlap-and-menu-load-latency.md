# 2026-10-13 — Homepage: filter buttons overlapping AI/bell + slow "menu" on initial load

File changed: `TORONTOEVENTS_ANTIGRAVITY/index.html` (live at findtorontoevents.ca and tdotevent.ca)

## What was broken

### 1. Overlapping floating buttons (bottom-right)
Four separate fixed widgets were all anchored to the bottom-right corner:

| Widget | Source | Position |
|---|---|---|
| `#custom-filter-controls` (Near Me / Show Multi-Day / Show TBD / Thumbnails) | index.html | `right:20px; bottom:20px`, about 210×212 px |
| `#fte-ai-btn` (🤖 AI) | `/ai-assistant.js` (deployed, not in git) | `right:24px; bottom:100px` |
| `#fte-mute-btn` (🔔) | `/ai-assistant.js` | `right:30px; bottom:156px` |
| Settings FAB | Next.js markup | `right-6 bottom-6`, 64×64 |

Measured on live: six button-on-button intersections at 1280, 768 and 390 px.

### 2. The "menu" (10 promo tiles) loaded late and looked broken
- `window.__whenReactHydrated__` waits for `__RAW_EVENTS__` **and** an event card heading matching
  `[class*="glass-panel"]:not(.animate-pulse) h2`. Event cards now render their titles as **`<h3>`** (50 h3s and 0 h2s on live).
  As a result, the witness never matched and every visitor waited for the **5-second hard fallback** after `window.load`.
  That one timer gated the promo tiles, the filter buttons and the chip injectors.
  Live timeline (fast network): `load` 1.4 s → tiles and filters **6.5 s**.
- In the meantime, the legacy `/add-promos.js` injected its own FavCreators/Stocks rows. Those rows used inline
  `display:block !important`, and their title wrapper had `max-width:0; opacity:0`. The result was the title-less
  "💎 Open App →" / "📈 Open App →" rows that stayed visible until the 6.5 s mark. `#injected-promos` already renders
  both of those tiles, so the script was redundant.
- `/ai-assistant.js` (530 KB) was a parser-blocking script.

## What changed
1. Witness selector now accepts `h2` **or** `h3` (and the `event-card` / `EventCard` variants). It is still gated on `__RAW_EVENTS__` being non-empty, and the 5 s fallback stays as a safety net.
2. Removed `<script src="/add-promos.js" async>`. The file is left on FTP so cached HTML still gets a 200, and so we can roll back.
3. `<script src="/ai-assistant.js" defer>`. No inline script depends on it running synchronously (checked by the reviewer).
4. Filter stack moved out of the AI/bell column:
   - desktop: `right:120px`
   - ≤640 px: `left:12px`, compact buttons, Near Me panel `width: calc(100vw - 132px)`
   - The filter stack is hidden while the AI chat panel is open (`body:has(#fte-ai-panel.open)`), because the panel (z 100001) would otherwise cover it.

## Verification
The test is a Playwright run against **live assets** (real chunks, ai-assistant.js, events.json), with only `/index.html` swapped for the patched file through `page.route`.

| | Live (before) | Patched |
|---|---|---|
| Menu tiles visible (1280) | 6742 ms | **1431 ms** |
| Menu tiles visible (768 / 390) | 5999 / 5992 ms | **1410 / 1349 ms** |
| Title-less legacy rows shown | yes (~0.8 s → 6.7 s) | **never** |
| Filter-button overlaps (1280/768/390) | 6 / 6 / 6 | **0 / 0 / 0** |
| React #418 count | 1 (pre-existing) | 1 (unchanged) |
| Near Me panel open vs AI/bell | — | no overlap |
| AI panel open → filters hidden; closed → visible | — | ✔ |

The patched run logs two extra 404 console errors. Their cause is **pre-existing data**: some events.json thumbnails carry
relative ROM-site paths (`/sites/default/files/...webp`). Those 404s now fire earlier because thumbnails apply sooner.

## Review
- Plan reviewed by groq `openai/gpt-oss-120b` (APPROVE-WITH-CHANGES) and a rubber-duck review agent (APPROVE-WITH-CHANGES).
  - Accepted: hide the filters while the AI panel is open; verify there are no new #418 errors.
  - Rejected with evidence: scoping the witness to `#events-grid`, because that element does not exist on live, so the
    change would reintroduce the 5 s fallback. The add-promos "globals" concern was also rejected: the script is a
    self-contained IIFE.
- Other reviewers could not run: nvidia, nous, fireworks, aimlapi, cerebras, mistral, gemini and github_models returned
  404/403/timeouts; the codex and grok CLIs have expired auth.

## Backups / rollback
- git tag `backup/homepage-pre-fab-fix-20261013-211121`
- FTP: `/findtorontoevents.ca/_backups/index.html.bak-20261013-211121`, `/tdotevent.ca/_backups/index.html.bak-20261013-211121`
- To roll back, re-upload the backup file to `/<site>/index.html`.

## Phase 2 (not done here)
- `/next/events.json` is **17.5 MB**. Shard or slim it; this is the remaining slow-network cost.
- Decouple the nav tiles from event data so they render on React commit rather than on the first event card. Reserve tile-grid height to avoid CLS.
- Fix relative ROM thumbnail URLs in the scraper output.
- Bring `ai-assistant.js`, `add-promos.js` and `theme-*.js` under git so FAB positions are coordinated in one place.
