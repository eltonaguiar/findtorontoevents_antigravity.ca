---
name: fix-toronto-events
description: Diagnoses and fixes findtorontoevents.ca / Toronto events site when events do not load, React does not run, or chunks fail. Uses project Fix docs (FIX_SUMMARY.md, INDEX_BROKEN_FIX.md, etc.). Use when the user reports events not loading, SyntaxError in a2ac3a6616d60872.js, ModSecurity blocking JS, index.html broken, no filters, skeleton only, or asks to fix Toronto events.
---

# Fix Toronto Events

Use this skill when the Toronto events site (findtorontoevents.ca or findtorontoevents_antigravity.ca) shows: no events, no filter bar, skeleton only, JS SyntaxError, or "denied by modsecurity". **First read the project Fix docs** (see [reference.md](reference.md)) for full detail; below is the condensed workflow.

## 1. Diagnose (do this first)

| Symptom | Likely cause |
|--------|----------------|
| **SyntaxError: Unexpected token '('** in `a2ac3a6616d60872.js` | Chunk URL returned HTML or "denied by modsecurity" (path wrong or WAF blocking). |
| **No filter bar** (no search, GLOBAL FEED, date/price) | React did not load; chunks failed or hydration broke. |
| **Skeleton / blank grid only** | Chunks 404 or blocked; React never ran. |
| **"Preloaded but not used"** | Preload and real `<link>`/`<script>` URL mismatch, or `sw.js` stripped `?v=`. |
| **Events show but 0 cards** (JSON loads in console) | Data has only past dates; filter shows "upcoming" only. Refresh `events.json` or run `tools/shift_event_dates.py`. |

**Checks:** DevTools → Network → request for `a2ac3a6616d60872.js`:
- **URL** must be `/next/_next/static/chunks/a2ac3a6616d60872.js?v=...` (live server uses `next/_next/`).
- **Status** 200, **Response** starts with `(globalThis.TURBOPACK...` (real JS). If body is HTML or "denied by modsecurity", fix path and/or ModSecurity.

## 2. Rules when editing index.html

**Do not:** change any asset URL, add a fallback script that injects event HTML into the grid, or reformat/minify the whole file.

- Asset base path on live: **`/next/_next/`** (e.g. `/next/_next/static/chunks/a2ac3a6616d60872.js?v=20260131-v3`).
- First query param must be **`?v=...`**, never **`&v=...`**.
- For menu/nav/footer: edit only the specific `<a href="...">` and text; no global replace on `/_next/` or `?`/`&`.

After any edit, confirm in built HTML: all chunk URLs start with `/next/_next/` and use `?v=...`.

## 3. Fix steps (in order)

### Fix 1 – Deploy correct index.html and chunks

- Upload **index.html** from project root to site document root (paths must be `/next/_next/static/chunks/...` and `?v=...`).
- Ensure chunks exist at **next/_next/static/chunks/** on the server. Use `tools/copy_to_next_path.py` if needed.
- Verify: open `https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=...` → 200 and body starts with `(globalThis.TURBOPACK...`.

### Fix 2 – ModSecurity / WAF

If the chunk request returns 200 but body is "denied by modsecurity":

- Add/keep **`.htaccess`** in: `next/_next/.htaccess`, `next/_next/static/chunks/.htaccess` (disable or whitelist ModSecurity for those dirs).
- Use `tools/upload_next_htaccess.py` to deploy.
- Optional: root `.htaccess` can route chunk requests through a PHP proxy (e.g. `js-proxy.php`) as failover.

### Fix 3 – Data and events.json

- Sync **events.json** to: `/events.json`, `/next/events.json`, `/data/events.json` so the app finds it regardless of base path.
- If filters work but 0 cards and console shows events loaded: events may all be in the past; update `events.json` or use `tools/shift_event_dates.py --min-today` for testing.

### Fix 4 – Service worker and preload

- If "Preloaded but not used" or SyntaxError despite valid JS when opening chunk URL directly: deploy updated **sw.js** that does not strip `?v=` from `/_next/` or `/next/_next/` requests. Hard-refresh or incognito; optionally unregister old SW in DevTools → Application → Service Workers.

### FavCreators link

- If menu link should go to `/favcreators/#/guest`: patch chunk with `tools/patch_nav_js.py` and deploy the fixed `next/_next/static/chunks/a2ac3a6616d60872.js`. See DEPLOYMENT_FIX_FAVCREATORS.md.

## 4. Local testing (127.0.0.1:9000)

- **Run:** `python tools/serve_local.py` from project root (mimics js-proxy-v2.php so chunk URLs return JS).
- **Do not** use `python -m http.server` – it serves PHP source for proxy URLs → SyntaxError → events never load.

## 5. Verification checklist

- [ ] View Source: chunk URLs are `/next/_next/static/chunks/...` and `?v=...`.
- [ ] Network: `a2ac3a6616d60872.js` → 200, response is JS starting with `(globalThis.TURBOPACK...`.
- [ ] Console: no SyntaxError or ChunkLoadError.
- [ ] Page: event cards and filter bar (search, GLOBAL FEED, date/price) visible and working.

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

### Local: events not loading, SyntaxError, skeleton only

- **Root cause:** Chunk URLs in index may point to `js-proxy-v2.php?file=...`. With `python -m http.server`, that URL returns **PHP source**, not JS → SyntaxError → React never runs.
- **Fix:** Always use **`python tools/serve_local.py`** (it mimics the proxy and serves real JS for `/js-proxy-v2.php?file=...`). Never use `python -m http.server` for this project.

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

- Keep it simple (match sister project): intercept any `events.json` request and do a **single** fetch to `/next/events.json`. No multi-source tryFetch loop; avoid consuming the response body before the app reads it.
