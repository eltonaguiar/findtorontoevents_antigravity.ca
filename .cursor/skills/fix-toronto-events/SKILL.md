---
name: fix-toronto-events
description: Diagnoses and fixes findtorontoevents.ca / Toronto events site when events do not load, React does not run, or chunks fail. Uses project Fix docs (FIX_SUMMARY.md, INDEX_BROKEN_FIX.md, etc.). Use when the user reports events not loading, SyntaxError in a2ac3a6616d60872.js, ModSecurity blocking JS, index.html broken, no filters, skeleton only, or asks to fix Toronto events.
---

# Fix Toronto Events

Use this skill when the Toronto events site (findtorontoevents.ca or findtorontoevents_antigravity.ca) shows: no events, no filter bar, skeleton only, JS SyntaxError, or "denied by modsecurity". **First read the project Fix docs** (see [reference.md](reference.md)) for full detail; below is the condensed workflow.

## 1. Diagnose (do this first)

| Symptom | Likely cause |
|--------|----------------|
| **SyntaxError: Unexpected token '('** or **Unexpected token '}'** in `a2ac3a6616d60872.js` (line 27) | (A) Chunk URL returned HTML or "denied by modsecurity" (path wrong or WAF blocking), or (B) chunk file has invalid JS (bad bracket sequence from patch). **Fast fix:** Copy `E:\findtorontoevents.ca\_next\static\chunks\a2ac3a6616d60872.js` over `next/_next/static/chunks/a2ac3a6616d60872.js`, then run `python tools/patch_nav_js.py` and `python tools/verify_events_loading.py`. |
| **No filter bar** (no search, GLOBAL FEED, date/price) | React did not load; chunks failed or hydration broke. |
| **Skeleton / blank grid only** | Chunks 404 or blocked; React never ran. |
| **"Preloaded but not used"** | Preload and real `<link>`/`<script>` URL mismatch, or `sw.js` stripped `?v=`. |
| **Events show but 0 cards** (JSON loads in console) | Data has only past dates; filter shows "upcoming" only. Refresh `events.json` or run `tools/shift_event_dates.py --min-today`. |
| **React error #418** (hydration) | Server-rendered HTML does not match client; common with static export. Often acceptable in dev; fix by ensuring same data/server render if needed. |

**Checks:** DevTools → Network → request for `a2ac3a6616d60872.js`:
- **URL** must be `/next/_next/static/chunks/a2ac3a6616d60872.js` (and `?v=...` on live).
- **Status** 200, **Response** starts with `(globalThis.TURBOPACK...` (real JS). If body is HTML or "denied by modsecurity", fix path and/or ModSecurity. If body is JS but still SyntaxError, the chunk file may have a syntax error (see §3 Fix 1b).

## 2. Rules when editing index.html

**Do not:** change any asset URL, add a fallback script that injects event HTML into the grid, or reformat/minify the whole file.

- Asset base path on live: **`/next/_next/`** (e.g. `/next/_next/static/chunks/a2ac3a6616d60872.js?v=20260131-v3`).
- First query param must be **`?v=...`**, never **`&v=...`**.
- For menu/nav/footer: edit only the specific `<a href="...">` and text; no global replace on `/_next/` or `?`/`&`.

After any edit, confirm in built HTML: all chunk URLs start with `/next/_next/` and use `?v=...`.

## 3. Fix steps (in order)

### Fix 1 – Deploy correct index.html and chunks

**1a – Paths and deploy**

- Upload **index.html** from project root to site document root. Chunk paths in HTML must be **`/next/_next/static/chunks/...`** and use **`?v=...`** as first query param.
- Ensure chunks exist at **next/_next/static/chunks/** on the server. Use `tools/copy_to_next_path.py` if needed.
- Verify: open the chunk URL in the browser → 200 and response body starts with `(globalThis.TURBOPACK...`.

**1b – Chunk syntax error (Unexpected token '(' or '}' in real JS)**

If the chunk returns 200 and valid-looking JS but the browser reports **SyntaxError** (e.g. **Unexpected token '('** at column ~11400 or **Unexpected token '}'** at line 27), the chunk file may have an invalid bracket sequence from patching.

- **Fastest fix (recommended):** Use the **sister project** as source of truth. Copy the working chunk from `E:\findtorontoevents.ca\_next\static\chunks\a2ac3a6616d60872.js` over `next/_next/static/chunks/a2ac3a6616d60872.js`, then run `python tools/patch_nav_js.py`. The patch applies nav customizations (NETWORK details, Data Management at bottom, FAVCREATORS link, etc.) and runs acorn; if acorn fails it does not report success. Then run `python tools/verify_events_loading.py` – it must exit 0.
- **Check:** Run `npx acorn --ecma2020 next/_next/static/chunks/a2ac3a6616d60872.js`. If it reports "Unexpected token", fix the chunk (see fast fix above or manual fixes below).
- **Manual fix (if no sister copy):** After the FAVCREATORS link, the closing sequence must be **three** `]})` then a comma (close link, close div, close details). Correct pattern: `" FAVCREATORS"]})]})]}),` (not `]})]})]})],`). Nav end must be exactly **four** `]})` then `}`: `"]})]})]})]})}e.s"` (not `"]})]})]})})]})}e.s"`). See Fix 1c.
- **Prevent:** Always run `python tools/verify_events_loading.py` after any chunk or patch change; do not declare done until it exits 0.

**1c – Uncaught SyntaxError: Unexpected token '}' (line 27)**  
If the browser reports **Unexpected token '}'** at line 27 in `a2ac3a6616d60872.js`, there is an extra `}` in the nav. Check: (1) Nav end: ensure it is exactly **four** `]})` then `}`: `"]})]})]})]})}e.s"` — **not** `"]})]})]})})]})}e.s"` (patch script §8c fixes that). (2) Run `python tools/verify_events_loading.py`; it must **exit 0** before passing. Do not report done until the syntax check passes.

### Fix 2 – ModSecurity / WAF

If the chunk request returns 200 but body is "denied by modsecurity":

- Add/keep **`.htaccess`** in: `next/_next/.htaccess`, `next/_next/static/chunks/.htaccess` (disable or whitelist ModSecurity for those dirs).
- Use `tools/upload_next_htaccess.py` to deploy.
- Optional: root `.htaccess` can route chunk requests through a PHP proxy (e.g. `js-proxy.php`) as failover.

### Fix 3 – Data and events.json

- Sync **events.json** to: **`/events.json`**, **`/next/events.json`**, **`/data/events.json`** so the app finds it regardless of base path.
- In **index.html**, the events fetch interceptor should try, in order: `/next/events.json`, then `/events.json`, then `/data/events.json` (fallback if one path fails).
- If filters work but 0 cards and console shows events loaded: events may all be in the past; update `events.json` or run `tools/shift_event_dates.py --min-today` for testing.

### Fix 4 – Service worker and preload

- If "Preloaded but not used" or SyntaxError despite valid JS when opening chunk URL directly: deploy updated **sw.js** that does not strip `?v=` from `/_next/` or `/next/_next/` requests. Hard-refresh or incognito; optionally unregister old SW in DevTools → Application → Service Workers.

### Fix 5 – FavCreators link

- Menu link should go to **`/fc/#/guest`** (host returns 500 for `/favcreators/`). Patch with `tools/patch_nav_js.py` and deploy the fixed `next/_next/static/chunks/a2ac3a6616d60872.js`. See DEPLOYMENT_FIX_FAVCREATORS.md. After patching, re-verify chunk syntax (Fix 1b).

## 4. Local testing (127.0.0.1:9000)

- **Run:** `python tools/serve_local.py` from project root.
- **Why:** `serve_local.py` (1) serves real JS/CSS for `/js-proxy-v2.php?file=...` if index used that, (2) sets correct MIME for **`/next/_next/`** requests (`.js` → `application/javascript`, `.css` → `text/css`) so the browser parses chunks as JS, (3) serves `/fc/` and FavCreators docs.
- **Do not** use `python -m http.server` – it does not set MIME for `/next/_next/` and would serve PHP source for any proxy URL → SyntaxError or wrong type → events never load.

## 5. Verification checklist

- [ ] View Source: chunk URLs are `/next/_next/static/chunks/...` and `?v=...`.
- [ ] Network: `a2ac3a6616d60872.js` → 200, response is JS starting with `(globalThis.TURBOPACK...`.
- [ ] Console: no SyntaxError or ChunkLoadError.
- [ ] Page: event cards and filter bar (search, GLOBAL FEED, date/price) visible and working.

## 5b. **Before declaring done** (mandatory for agents)

After any change to **index.html**, **next/_next/static/chunks/a2ac3a6616d60872.js**, **patch_nav_js.py**, or nav/menu logic, **do not tell the user you are done** until:

1. **Syntax check (required):** Run `python tools/verify_events_loading.py`. It runs `npx acorn` on the nav chunk. **If acorn fails, you have not passed** – fix the chunk (see Fix 1b and nav closing sequence below) and re-run until acorn exits 0. Never report "done" or "patch successful" if the chunk has a syntax error.
2. **Events load locally (recommended):** Start `python tools/serve_local.py`, then run `npx playwright test events-loading.spec.ts`. All tests should pass.

**Syntax check is mandatory – no exceptions.** Run `python tools/verify_events_loading.py` after any chunk/patch change. It must **exit 0** (acorn parses the nav chunk). If it fails, **you have not passed** – fix the chunk and re-run until the script exits 0. Never report "done", "patch successful", or "complete" if the chunk has a syntax error (e.g. **Unexpected token '}'** or **Unexpected token '('** at line 27).

**Nav chunk closing:** At the end of the nav (after "Build: 2026-01-29-parallel-fix") the closing sequence must be **four** `]})` then `}`: `"]})]})]})]})}e.s"`. It must **not** be `"]})]})]})})]})}e.s"` (extra `})` causes **Unexpected token '}'** in browser). After patching, run `python tools/verify_events_loading.py` and fix until it passes.

## 6. Project references

Read these from the **workspace root** when you need full detail:

- **FIX_SUMMARY.md** – Full rules for index.html, 3-layer fix (WAF, data sync, hydration), SyntaxError, "0 events", hydration #418, "Today" filter.
- **INDEX_BROKEN_FIX.md** – Step-by-step diagnosis and fix (DevTools, Network, View Source, deploy order).
- **WHAT_FIXED_IT.md**, **FIX_STATUS.md**, **DEPLOYMENT_FIX_SUMMARY.md** – Timeline and deployment notes.
- **DEPLOYMENT_FIX_FAVCREATORS.md** – FavCreators link fix and verification.

For a full index of Fix docs and tools, see [reference.md](reference.md) in this skill.

---

## 7. Debugging / fix notes (faster next time)

Use these when the same issues recur.

### Nav chunk SyntaxError (Unexpected token at line 27) – fastest fix

1. **Copy working chunk from sister project:**  
   Copy `E:\findtorontoevents.ca\_next\static\chunks\a2ac3a6616d60872.js` to `next/_next/static/chunks/a2ac3a6616d60872.js` (overwrite).
2. **Re-apply nav customizations:**  
   Run `python tools/patch_nav_js.py` from project root. The script applies NETWORK (details, expanded), Data Management (collapsible, at bottom), FAVCREATORS link, 2XKO, etc., and runs `npx acorn` at the end; it will not report "Patch successful" if the chunk has a syntax error.
3. **Verify:**  
   Run `python tools/verify_events_loading.py`. It must exit 0 (acorn parses the chunk). Do not declare done until it passes.
4. **If sister project is unavailable:**  
   Fix bracket sequence manually (Fix 1b/1c): FAVCREATORS close = `]})]})]}),`; nav end = exactly four `]})` then `}`: `"]})]})]})]})}e.s"`. Run acorn with `npx acorn --ecma2020 next/_next/static/chunks/a2ac3a6616d60872.js` to get error position (line:column).

### Local: events not loading, SyntaxError, skeleton only

- **Root cause:** (1) Using `python -m http.server`: it does not set `Content-Type: application/javascript` for `.js` under `/next/_next/`, and would serve PHP source for `/js-proxy-v2.php?file=...` if used → browser gets non-JS → SyntaxError → React never runs. (2) Or the nav chunk has a syntax error (extra `]`) from patching – see Fix 1b.
- **Fix:** Always use **`python tools/serve_local.py`**. It serves `/next/_next/` with correct MIME and handles proxy-style URLs. If SyntaxError persists with serve_local, use the **fastest fix** above (copy sister chunk + run `patch_nav_js.py`) or verify with `npx acorn --ecma2020 next/_next/static/chunks/a2ac3a6616d60872.js` and apply Fix 1b/1c.

### Live: proxy (js-proxy-v2.php) times out or fails

- **Symptom:** Chunk requests to `/js-proxy-v2.php?file=...` time out or return error; events/site broken.
- **Fix:** Switch to **direct chunk URLs** and serve from disk:
  1. In **index.html**: use direct URLs (`/next/_next/static/chunks/xxx.js`) for all script/link chunk tags; remove any fetch/XHR interceptor that rewrites to the proxy.
  2. In **root .htaccess**: comment out the rewrite that sends `next/_next/static/chunks/*.js` to js-proxy-v2.php. Add **pass-through** for `next/_next/`: `RewriteRule ^next/_next/ - [L]` so requests are served from `next/_next/` on disk (no rewrite to `_next/`).
  3. Deploy **ModSecurity bypass** .htaccess to `next/_next/` and `next/_next/static/chunks/` (and same under `findtorontoevents.ca/`) so JS is not blocked.
  4. Deploy **index.html** and **.htaccess** to both FTP root and **findtorontoevents.ca/**.

### Live: getAssetPrefix() throws (E784) when using proxy

- **Symptom:** Scripts load via `js-proxy-v2.php`; `document.currentScript.src` does not contain `/_next/`, so **dde2c8e6322d1671.js** throws "Expected document.currentScript src to contain '/_next/'".
- **Fix:** Patch **next/_next/static/chunks/dde2c8e6322d1671.js**: when `pathname.indexOf("/_next/") === -1`, return `window.__NEXT_ASSET_PREFIX__ || "/next"` instead of throwing. Then redeploy that chunk (and mirrors) to the server.

### Deploy to both locations

- Host may serve from **findtorontoevents.ca/** subdirectory. Deploy the same set to **both**:
  - FTP root: `index.html`, `.htaccess`, `js-proxy-v2.php`, `events.json`
  - **findtorontoevents.ca/**: `index.html`, `.htaccess`, `js-proxy-v2.php`, `next/_next/` (chunks + .htaccess), `events.json`, `next/events.json`.

### Events fetch in index.html

- Intercept any `events.json` request and resolve to one URL; try fallbacks only if the first response is not ok (e.g. try `/next/events.json`, then `/events.json`, then `/data/events.json`). Do not consume or clone the response body before the app reads it; return the fetch promise so the app receives the response.
