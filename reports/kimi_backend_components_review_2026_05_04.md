# Kimi Backend + Components Deep Review — 2026-05-04

Scope: `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/` (api/, components/, static/).
Reviewer focus: security, portability into hand-coded `TORONTOEVENTS_ANTIGRAVITY/index.html`, data-pipeline fit.

## Per-file verdict

| File | Verdict |
|---|---|
| `api/user-settings.php` | REJECT for now (depends on missing `users`/`sessions` tables + `db-config.php`). Code is well-written; archive for a future logged-in phase. |
| `api/check-session.php` | REJECT for now (same dependency). Cherry-pick CORS+session pattern. |
| `api/db-schema-user-settings.sql` | REJECT — references nonexistent `users(id)`. No user-account infra exists on 50webs. |
| `components/GearSettingsModal.tsx` | REJECT — no React build pipeline on the live page. Use as design spec only. |
| `components/providerRegistry.md` | ADOPT-AS-IS as documentation reference. |
| `static/gear-settings-integration.js` | ADOPT-WITH-FIXES (see fixes #1–#6). Best ROI artifact in the bundle. |
| `static/gear-settings-integration.css` | ADOPT-AS-IS — fully `fte-` prefixed, zero collisions verified against host page. |

## Security findings (PHP backend)

1. **[P2] CORS allow-list lacks mirror domains.** Only `findtorontoevents.ca` is whitelisted; production also serves `tdotevent.ca` and `torontoevent.net` from the same `index.html` (per CLAUDE.md). Cross-origin XHR from the mirrors will be blocked. Fix: add both to `$allowedOrigins`.
2. **[P1] No CSRF protection on POST.** Cookie-only auth + `Access-Control-Allow-Credentials: true` + permissive `Content-Type: application/json` means a logged-in user visiting an attacker page can have settings overwritten via a `fetch(..., {credentials:'include'})` call from any whitelisted origin (including `http://localhost` — which is in the allow-list and a real risk on dev machines). Fix: require a CSRF token header (`X-CSRF-Token`) bound to the session, or strip `http://localhost*` from production deployments.
3. **[P2] `localhost` in production CORS allow-list.** `http://localhost` and `http://localhost:3000` should be gated behind an env flag, not shipped to prod.
4. **[P3] `JSON_PRETTY_PRINT` on every response** wastes bandwidth; cosmetic.
5. **[P3] `error_log` leaks no PII but no request_id correlation.** Minor.
6. **No SQL injection risk found.** All queries use PDO prepared statements with named params. Session-id regex `^[a-f0-9]{64}$` is properly anchored. Good.
7. **No XSS risk in PHP layer** (JSON-only responses, correct Content-Type).
8. **`SameSite` cookie attribute is not set here** — must be `Lax` or `Strict` on the session-issuing endpoint (not in this bundle, but flag it for whoever ships login).

## Vanilla shim findings (`gear-settings-integration.js`)

**Fix #1 [P0] — Selector list does not match host page gear buttons.** Host has 3 gear buttons (lines 994, 1021, 1029 in `TORONTOEVENTS_ANTIGRAVITY/index.html`). None have `data-testid="config-button"`, `aria-label*="settings"|"config"`, or `title*="settings"|"config"`. The actual attributes are `title="System Configuration (Top Right)"` and `title="Configuration Settings (Always Accessible)"` and `aria-label="Open Settings"` (line 1029 matches `aria-label*="settings" i`, OK). Lines 994/1021 will be missed.

**Fix #2 [P0] — `:has-text()` is a Playwright-only selector.** All four `:has-text(...)` entries throw `SyntaxError` in `querySelector`. The try/catch swallows it silently, so they're dead code. Remove them.

**Fix #3 [P1] — Add real selectors:** `'button[title*="Configuration" i]'`, `'button[title*="System Configuration" i]'`, plus a text-content fallback that iterates `document.querySelectorAll('button')` and matches `textContent.includes('⚙️')` or `'Event System Settings'` (line 995).

**Fix #4 [P1] — Hooks only ONE gear; the page has 3.** Loop and bind all matches, not `break` on first.

**Fix #5 [P1] — `applyMaxEventsFilter` keys on `evt.source`, but `__RAW_EVENTS__` items in this codebase do not currently carry a `source` field** (verified — host code only references `.source` for chip-injection objects, not events; events come from `events.json`). Result: every event falls through `enabledSet.has("unknown")` → returns `false` → **entire grid wipes to zero events** the moment the user toggles a source. P0 production hazard if shipped without a guard. Fix: short-circuit if no event has a `source` field — treat all as enabled until pipeline ships it.

**Fix #6 [P2] — Re-render hook wraps `applyThumbnails` but the host's `applyThumbnails` reads from `window.__RAW_EVENTS__` directly inside its body (multiple call sites, lines 3540/3562/3846/etc.), not from its `events` arg.** Wrapping the function won't actually filter what gets rendered. Need to instead replace `window.__RAW_EVENTS__` itself (or set `window.__FILTERED_EVENTS__` and patch host code to read it).

**Fix #7 [P2] — `init()` is async + auto-runs**, but if `__RAW_EVENTS__` arrives later (it's set inside an async fetch around line 125), the initial filter pass misses it. Need a `MutationObserver` or a "raw events ready" event hook.

## localStorage fallback path

Verified safe: `checkSession()` returns `false` on any non-2xx or network error; `isLoggedIn` stays `false`; `saveSettingsToBackend` and `fetchSettingsFromBackend` early-return on `!isLoggedIn`. `loadSettingsFromLocalStorage` runs synchronously at module load and is the source of truth when offline. **Graceful degradation works.** One nit: `checkSession()` against a non-existent endpoint returns 404 HTML, `res.ok` is false → falls through cleanly. OK.

## CSS conflicts

Verified: every class in `gear-settings-integration.css` is `fte-`-prefixed. Host `index.html` uses Tailwind utility classes + a few semantic classes (`.source-link`, `.source-name`, `.glass-panel`, `.windows-fixer-promo`). **Zero collisions.** `z-index: 9999` on `.fte-modal-backdrop` correctly sits above host `z-[200]` controls.

## Cherry-pick top 5

1. **`gear-settings-integration.css` whole file** — drop-in, zero conflicts.
2. **Modal builder + focus trap + ESC handling** (lines 304–459 of the JS). Accessibility is solid; reuse verbatim.
3. **Tab system + `buildToggle` helper** (lines 706–729). Clean reusable primitive.
4. **`loadSettingsFromLocalStorage` / `saveToLocalStorage` / `deepMerge` trio** (lines 82–134). Defensive parsing pattern.
5. **PHP CORS preflight + `jsonResponse`/`error` helpers** (`user-settings.php` lines 22–61). Reuse as a template when login lands.

## Phase 1 PR — what ships TODAY

**Title:** `feat(homepage): vanilla gear-settings modal (localStorage-only, no backend)`

Scope:
- Add `static/gear-settings.css` (Kimi CSS verbatim).
- Add `static/gear-settings.js` derived from Kimi shim with these deltas:
  - **Strip** `checkSession`, `fetchSettingsFromBackend`, `saveSettingsToBackend`, all `/api/*` calls, `isLoggedIn`/`sessionChecked` state. Header subtitle hard-codes "Settings saved locally on this device".
  - **Replace** selector list with the three real selectors (Fix #3) + iterate-and-bind-all (Fix #4).
  - **Remove** `:has-text()` selectors (Fix #2).
  - **Guard** `applyMaxEventsFilter`: if `events.every(e => !e.source && !e.sourceId)`, return events unchanged (Fix #5). Add a `console.info` so we know when source-field ships.
  - **Replace** the `applyThumbnails` wrapper with `window.__FILTERED_EVENTS__` write + a one-line patch in host `index.html` to prefer `__FILTERED_EVENTS__` over `__RAW_EVENTS__` when present (Fix #6).
  - Defer `init()` until `__RAW_EVENTS__` is observed (Fix #7) — small `Object.defineProperty` setter trap or 250ms poll.
- Two `<script>`/`<link>` tags added to `TORONTOEVENTS_ANTIGRAVITY/index.html` (do NOT edit any auto-generated file).
- FTP-upload via existing deploy pattern (manual, no `deploy_sports_files.sh` for non-sports paths).

Non-goals (defer to Phase 2 once login exists):
- Any PHP file from this bundle.
- DB schema.
- Source-toggle UI being functional (ship the tab read-only with a "Source filtering ships when event-pipeline adds `source` field" notice).
- Calendar export button (`/api/export/calendar` does not exist).

Estimated effort: 2–3 hours including FTP + smoke test.

## Files referenced

- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\api\user-settings.php`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\api\check-session.php`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\api\db-schema-user-settings.sql`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\static\gear-settings-integration.js`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\static\gear-settings-integration.css`
- `c:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\index.html` (lines 994, 1021, 1029 — gear buttons; line 125 — `__RAW_EVENTS__` assignment; lines 3540/3562/4154 — `applyThumbnails` reads `__RAW_EVENTS__` directly)
