# Kimi Gear Settings Integration — Review (2026-05-04)

**Reviewer:** Claude Opus 4.7 (1M)
**Source:** `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/`
**Target surface:** `TORONTOEVENTS_ANTIGRAVITY/index.html` (4,845-line hand-coded HTML; the live findtorontoevents.ca / tdotevent.ca / torontoevent.net homepage)

---

## 1. Verdict: **Adopt the vanilla shim with modifications. Reject the React `.tsx`. Defer the PHP backend.**

| Asset | Verdict | Why |
|---|---|---|
| `components/GearSettingsModal.tsx` (629 lines React) | **Reject for this surface** | The live homepage is hand-coded HTML with no React build pipeline, no JSX transformer, no bundler. The Next.js app at `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` only builds the embedded event-grid widget; it does NOT produce `index.html`. Mounting a `.tsx` here would require either (a) introducing esbuild/Vite to this repo (out of scope) or (b) hand-transpiling — pointless when the vanilla shim already exists and is feature-equivalent. Keep the `.tsx` as a reference design only. |
| `static/gear-settings-integration.js` (931 lines vanilla) | **Adopt with modifications** | Pure DOM, no framework deps, plug-and-play with the existing `<script defer>` model. Hooks `window.applyThumbnails` which already exists at `index.html:4274`. |
| `static/gear-settings-integration.css` | Adopt as-is | Self-scoped under `.fte-modal-*` — no collision risk with existing `.glass-panel` / Tailwind utility classes. |
| `api/user-settings.php` + `check-session.php` | **Defer (Phase 2)** | 50webs hosts static files only; there is no PHP runtime, no MySQL, no `sessions` table, and no auth/login UI on this site today. Shipping the backend would be dead code. |
| `api/db-schema-user-settings.sql` | Defer | Same reason. |

---

## 2. Selector / Mount-point Fixes (CRITICAL)

Kimi's auto-detect selector list (`[data-testid="config-button"]`, `button[aria-label*="settings"]`, `button[title*="settings"]`, `button[title*="config"]`, `button:has-text("⚙️")`) **will partially match but bind to the wrong element** on the live page.

The live page has **three** ⚙️ buttons:

| # | Location | `index.html` line | Selector hit |
|---|---|---|---|
| A | Sidebar drawer "Event System Settings" | 994–995 | `button:has-text("Settings")` — hidden in mega-menu |
| B | **Top-right fixed `#top-right-controls`** with `title="System Configuration (Top Right)"` | 1021–1028 | `button[title*="config"]` (case-sensitive issue: title is "Configuration" capital C — `[title*="config"]` only matches lowercase in CSS attribute selectors by default; `i` flag needed) |
| C | Bottom-right fixed pulse button with `aria-label="Open Settings"` | 1029–1038 | `button[aria-label*="settings"]` — partial match (capital S) |

**Required fixes in `gear-settings-integration.js` selector array:**

```js
// Replace the existing selector list with:
'#top-right-controls button',                       // primary: top-right gear (line 1021)
'[title*="Configuration" i]',                       // case-insensitive
'[aria-label*="Settings" i]',                       // case-insensitive
'[data-testid="config-button"]',                    // future-proof
'button[title*="System Configuration"]',
```

Note: CSS `:has-text()` is NOT a real CSS selector (it is Playwright-only). The shim must implement this in JS via `Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('⚙️'))`. Confirm Kimi's shim does that (lines ~200-300 of integration.js); if it relies on `querySelector(':has-text(...)')` it will throw `SyntaxError: invalid selector` in all browsers.

**Recommendation:** bind to BOTH the top-right (B) and bottom-right (C) buttons so users get the modal from either location. Do NOT auto-create a fourth gear button (Kimi's fallback) — would clash visually with the existing trio.

**`__RAW_EVENTS__` wiring is fine** — it is populated at `index.html:125` (`window.__RAW_EVENTS__ = events`) and `applyThumbnails()` is defined at line 4274. Kimi's documented wrap pattern works.

---

## 3. `data-source` Field — Blocking Gap

`grep "source" TORONTOEVENTS_ANTIGRAVITY/index.html` returns zero hits where each event object carries a `source` / `sourceId` field. The events come from `events-cache` (line 54-77) but the per-event source provenance is **not currently exposed on the event object**. Without this, Kimi's filter degrades to bucketing every event under `"unknown"` and the max-3-per-source limit collapses to a global max-3-per-day cap.

**Pre-req PR (must land BEFORE the gear PR):** ensure the upstream events feed (`events.json` / scraper output) carries a `source` string per event, and the cache layer preserves it onto `__RAW_EVENTS__`. Until then, ship the gear modal in **read-only "preview" mode** — toggles work, persist, but the filter is no-op.

---

## 4. Security Review

### `user-settings.php`
- **SQL injection:** Properly parameterized (PDO `:uid`, `:json`, `:sid`). PASS.
- **Session fixation / hijack:** Uses cookie `session_id` with `^[a-f0-9]{64}$` regex check — reasonable. Assumes session cookie is set `HttpOnly; Secure; SameSite=Strict` by the auth flow. **No CSRF token on POST.** Because the endpoint relies on cookie auth and `Access-Control-Allow-Credentials: true`, an attacker on a non-allowlisted origin cannot read responses, but they CAN issue a same-site forged POST (e.g. via image/form on findtorontoevents.ca itself if XSS exists, or a sibling subdomain). Mitigation: enforce `SameSite=Strict` on the session cookie AND add a CSRF double-submit token. Settings tampering is low-impact (just hides events) but the pattern leaks into future sensitive endpoints.
- **CORS:** Whitelist is correct. PASS.
- **Validation:** `validateSettings()` clamps int range, validates booleans, filters `enabledSources` to strings. `enabledSources` is unbounded in array length — add `count($raw['enabledSources']) <= 50` to prevent JSON bloat DoS. The settings JSON column should also have a server-side length cap (`LENGTH(settings_json) < 4096`).
- **JSON parse blind spot:** `filter_var($v, FILTER_VALIDATE_BOOLEAN)` returns `false` for invalid input silently — fine for booleans but be aware non-bool inputs are coerced to `false` rather than rejected.
- **Error leakage:** `error_log` is server-side only; client gets generic "Internal server error". PASS.

### `check-session.php`
- Same parameterization — PASS.
- Identical CORS — PASS.
- Returns `loggedIn:false` rather than 401 for invalid session — correct (this is an idempotent probe).

### `gear-settings-integration.js` (XSS)
- **Mostly safe:** Uses `createElement` + `appendChild(document.createTextNode(...))` for user-controllable text. Source names from `DEFAULT_SOURCES` are hardcoded constants → safe.
- **Risk vector:** Lines 290-300 use `svg.innerHTML = paths[name]` with hardcoded SVG path strings. Safe because `paths[name]` is a closed dictionary controlled by the script. PASS.
- **localStorage trust:** `loadSettingsFromLocalStorage()` does `JSON.parse(raw)` and `deepMerge` — if a malicious extension or other script stores `{ "sources": [{"name": "<img onerror=...>", ...}]}` and the modal renders source names via `textContent` (it does, via createTextNode), no XSS. PASS.
- **No prototype pollution check** in `deepMerge` — a crafted `__proto__` key in localStorage would pollute. Add: `if (key === '__proto__' || key === 'constructor') continue;` to deepMerge. Low-severity (attacker needs prior localStorage write) but cheap fix.

### Backend payload trust
- Backend `validateSettings` does NOT validate that `enabledSources` IDs are in the known whitelist — a logged-in attacker could store arbitrary strings (e.g. 1MB of garbage if length cap not added). Recommend: intersect `enabledSources` with a server-side allowlist of the 12 known source IDs before persisting.

**Overall:** No critical (P0/P1) security holes. Three medium-severity hardening items: CSRF on POST, `enabledSources` allowlist + length cap, deepMerge prototype guard.

---

## 5. Proposed PR

**Branch:** `feat/gear-settings-modal-phase1`
**Title:** `feat(homepage): ship gear settings modal (max-N-per-source + Eventbrite exemption, localStorage-only)`

### Files in PR

| Action | Path | Notes |
|---|---|---|
| ADD | `TORONTOEVENTS_ANTIGRAVITY/static/gear-settings-integration.js` | Vanilla shim, with modifications (selectors below, prototype-pollution guard, no PHP fetch) |
| ADD | `TORONTOEVENTS_ANTIGRAVITY/static/gear-settings-integration.css` | As-is |
| EDIT | `TORONTOEVENTS_ANTIGRAVITY/index.html` | Two lines: `<link>` in `<head>`, `<script defer>` before `</body>`. Bind shim to existing `#top-right-controls button` — do not inject a 4th gear |
| ADD | `updates/2026-05-04-gear-settings-modal-phase1.md` | "What's New" entry |
| OMIT | `api/*.php`, `*.sql`, `components/*.tsx` | Phase 2 / never |

### Required code changes to Kimi's shim before merge

1. **Selector list rewrite** (Section 2 above) — bind to `#top-right-controls button` and the bottom-right pulse button; remove `:has-text()` pseudo-selector (invalid CSS).
2. **Disable backend sync entirely** for Phase 1: comment out `checkSession()`, `fetchSettingsFromBackend()`, `saveSettingsToBackend()` calls so the shim never hits `/api/`. Saves a 404 round-trip on every page load.
3. **`deepMerge` prototype guard:**
   ```js
   for (const key in source) {
     if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
     // ...
   }
   ```
4. **Fallback for missing `source` field:** when `evt.source` is undefined, treat the event as exempt (don't filter it out). This prevents the modal from hiding the entire grid until the upstream `source` field PR lands.
5. **Remove `auto-create gear button` fallback** — three gears already exist; a fourth would damage UX.
6. **Cache-bust:** `?v=20260504` not `?v=1`.

### Wiring-rule compliance

CLAUDE.md "Wire-Up Rule" applies to Python integration modules; this is a frontend feature with a direct user-visible caller (the gear button click handler) — compliant. Modal's filter mutates `window.__FILTERED_EVENTS__` which `applyThumbnails` already reads (per Kimi's pattern at line 81 of the guide).

---

## 6. Phasing

### Ship-this-week (Phase 1) — localStorage only
- Modal renders, opens from existing top-right gear (line 1021)
- **Display tab:** max-N-per-source slider (1-10), Eventbrite exemption toggle, source badge toggle
- **Sources tab:** enable/disable each of the 12 sources (no-op until `source` field lands upstream — show banner: "Per-source filtering activates once event provenance ships")
- **Persistence:** localStorage only (`fte_gear_settings`)
- **NO backend, NO login, NO calendar export, NO dedup, NO group-by-date**

### Phase 2 (defer 2-4 weeks)
- Upstream `source` field on every event in `__RAW_EVENTS__` (separate PR — events pipeline)
- Activate per-source filter
- `deduplicate` toggle (needs a fingerprint function — title+date normalization)

### Phase 3 (defer indefinitely until login exists)
- PHP backend (`user-settings.php`, `check-session.php`)
- Account-bound persistence
- Gate: requires (a) PHP-capable host or migration off 50webs, (b) auth/login UI, (c) `users` + `sessions` tables, (d) CSRF token + `enabledSources` server-side allowlist (Section 4)

### Phase 4 (nice-to-have)
- Calendar export tab (iCal / Google) — useful but orthogonal to the core "fewer events per source" pain point that motivated this work

---

## Key Findings Summary

1. The React `.tsx` is unusable on this surface — the live page is not a React app. Vanilla shim is the only path.
2. The shim's auto-detect selectors will mis-bind on the live page (3 existing gears + `:has-text()` is invalid CSS). Six-line selector rewrite required.
3. **Blocking pre-req:** events do not currently carry a `source` field on `__RAW_EVENTS__`. Without it, the marquee feature (max-N-per-source) is a no-op. Ship the modal anyway in Phase 1 with a "coming soon" banner on the Sources tab; land the `source` field in a separate events-pipeline PR for Phase 2.
4. **Defer the PHP backend** — 50webs is static-only, no `users`/`sessions` tables, no login UI. Phase 1 should be 100% localStorage. Saves a guaranteed 404 round-trip on every page load.
5. Security: no P0/P1 holes in the PHP. Three medium hardening items for whenever the backend ships (CSRF, allowlist+length-cap, prototype guard).
6. Two-line edit to `TORONTOEVENTS_ANTIGRAVITY/index.html` (the canonical edit point per CLAUDE.md), then FTP-upload via the documented credentials path.

**Files referenced:**
- `c:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\index.html` (lines 125, 994-995, 1021-1038, 4274)
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\GEAR_INTEGRATION_GUIDE.md`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\static\gear-settings-integration.js`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\api\user-settings.php`
- `c:\findtorontoevents_antigravity.ca\reports\kimi_swarm_archive_2026_05_04\findtorontoevents_swarm\api\check-session.php`
