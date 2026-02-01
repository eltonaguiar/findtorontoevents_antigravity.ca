# Why https://findtorontoevents.ca/index.html Is Broken – Diagnosis & Fix Steps

Use this when the live page shows skeleton content, no events, no filters, or JS errors.

---

## 1. What “broken” usually means

| What you see | Likely cause |
|--------------|----------------|
| Page loads but **no event cards** (only skeleton placeholders or blank grid) | React app didn’t run → JS chunks failed to load (404, block, or wrong path). |
| **No filter bar** (no search, no GLOBAL FEED, no date/price/category) | Same: React never hydrated. |
| **Console: SyntaxError: Unexpected token '('** in a chunk (e.g. `a2ac3a6616d60872.js`) | Browser got HTML or “denied by modsecurity” instead of JavaScript. |
| **Console: “Preloaded but not used”** for a CSS/JS file | Preload URL and real `<link>`/`<script>` don’t match, or **`sw.js`** stripped `?v=` so the fetched URL didn't match the preload URL. |
| **Layout looks wrong or unstyled** | Main CSS chunk failed (same path/block issues as JS). |
| **Page loads, filters work, but no event cards** | Events JSON not loaded → `getAssetPrefix()` threw in a lazy chunk, or `/next/events.json` / `/events.json` not served. See [§ Events not loading](#events-not-loading). |

Root cause is almost always: **chunk URLs in the live `index.html` don’t match where the server actually serves the files**, or the server/WAF blocks those requests.

---

## 2. Diagnose (do this first)

### Step A – Open the live page and DevTools

1. Open **https://findtorontoevents.ca/** (prefer this over `/index.html` so cache/redirects match normal visitors).
2. Open **DevTools** (F12) → **Console** tab. Reload the page.
3. Note any **red errors**, especially:
   - `SyntaxError: Unexpected token '('` in a file like `a2ac3a6616d60872.js`
   - `ChunkLoadError` or `Loading chunk X failed`
   - `Failed to load resource` (then check Network for that URL).

### Step B – Check the main JS chunk in Network

1. DevTools → **Network** tab. Reload.
2. In the filter/list, find the request for **`a2ac3a6616d60872.js`** (or the file named in the SyntaxError).
3. Click it and check:

   | Check | Expected | If wrong |
   |-------|----------|----------|
   | **Request URL** | `https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=...` | If it’s `.../**_next/**/...` (single `_next`, no `next/`), the live HTML has the wrong path. |
   | **Status** | **200** | 404 = file not at that path on server, or path in HTML wrong. |
   | **Response body** | Starts with `(globalThis.TURBOPACK...` (real JS) | If it’s HTML or “denied by modsecurity”, server/WAF is blocking or returning an error page. |

### Step C – Compare with the live HTML

1. On the live site, **View Page Source** (Ctrl+U or right‑click → View Page Source).
2. Search for `_next` or `a2ac3a6616d60872`.
3. Check:
   - Do script/link URLs use **`/next/_next/static/chunks/...`** (with `next/` before `_next`)?
   - Is the first query parameter **`?v=...`** (question mark), not **`&v=...`** (ampersand)?
   - Does the **version** in every chunk URL match what the server serves? (e.g. if Network shows `?v=20260131-185045`, **all** chunk/CSS URLs in the HTML must use that same `?v=20260131-185045`; a mismatch causes 404 → SyntaxError and “preloaded but not used”.)

If the **live** source has `/_next/` (no `next/`), `&v=`, or a different `?v=...` than the server, the deployed `index.html` is wrong or stale.

---

## 3. Fix steps (in order)

### Fix 1 – Deploy the correct `index.html`

The repo’s `index.html` already uses the right URLs:

- Base path: **`/next/_next/static/chunks/...`**
- Query: **`?v=20260131-v3`** (e.g. `...js?v=20260131-v3`)

**Do this:**

1. From your project (e.g. `e:\findtorontoevents.ca`), upload **`index.html`** to the **document root** of the live server (overwriting the existing one).
2. Use FTP/SFTP/cPanel/whatever you normally use for findtorontoevents.ca.
3. After upload, **hard-refresh** the site (Ctrl+Shift+R) or test in an incognito window so the browser doesn’t use an old cached HTML.

If the live server’s **document root** is different (e.g. a `public_html` or `www` subfolder), upload `index.html` there so that the site is served from that root.

### Fix 2 – Ensure chunks exist at `/next/_next/` on the server

The browser will request e.g.:

`https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=20260131-v3`

So on the server you must have:

- `next/_next/static/chunks/a2ac3a6616d60872.js`
- (and the same for the other chunk filenames in `index.html`)

**Do this:**

1. In your project, the built chunks live under **`next/_next/static/chunks/`** (and **`next/_next/static/media/`** for fonts, etc.).
2. Upload that **entire `next/`** folder (or at least `next/_next/`) to the live server so that the path from the site root is **`next/_next/...`**.
3. If you use a script (e.g. `tools/copy_to_next_path.py`), run it so the server has the same structure as in the repo.

Verify: open in a browser (or with curl):

`https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=20260131-v3`

You should get **200** and JavaScript that starts with `(globalThis.TURBOPACK...`.

### Fix 2b – Service worker (`sw.js`) stripping `?v=`

If you see **SyntaxError** in a chunk and/or **"Preloaded but not used"** for the main CSS, and the server returns valid JS when you open the chunk URL directly, the cause is often **`sw.js`**. An older `sw.js` stripped query parameters from `/_next/` and `/next/_next/` requests, so:

- The browser requested `a2ac3a6616d60872.js?v=20260201` but the SW fetched `a2ac3a6616d60872.js` (no `?v=`). A cached 404/HTML for the unversioned URL could be served → **SyntaxError**.
- The preload was for `cd9d6741b3ff3a25.css?v=20260201` and the stylesheet link used the same URL, but the SW fetched the unversioned URL, so the browser didn't match preload to the applied stylesheet → **"Preloaded but not used"**.

**Do this:** Deploy the updated **`sw.js`** that no longer strips `?v=` (it just passes through `fetch(event.request)`). Then hard-refresh or use an incognito window so the new SW takes over. Optionally unregister the old SW (DevTools → Application → Service Workers → Unregister) before testing.

### Fix 3 – Stop ModSecurity (or WAF) from blocking JS/CSS

If Step B showed **Status 200** but the **response body** was “denied by modsecurity” (or similar), the server is blocking the request.

**Do this:**

1. Add (or keep) **`.htaccess`** in the directories that serve the chunks, so ModSecurity doesn’t apply to them. Per `FIX_SUMMARY.md`, the important ones are:
   - `next/_next/.htaccess`
   - `next/_next/static/chunks/.htaccess`
2. Use the same `.htaccess` content you used when the site was working (disable or whitelist ModSecurity for those paths). If you have `tools/upload_next_htaccess.py`, use it to upload these files.
3. Restart or reload the web server if required by your host.

### Events not loading

If the page and filters render but **no event cards** appear, the app is failing to load events from `getAssetPrefix() + "/events.json"` (e.g. `/next/events.json`). Common causes:

1. **`getAssetPrefix()` throws** when called from a lazy-loaded chunk (`document.currentScript` is null). The repo fix: `next/_next/static/chunks/dde2c8e6322d1671.js` is patched to return `window.__NEXT_ASSET_PREFIX__` or `"/next"` instead of throwing. Ensure this patched chunk is deployed; after a rebuild from source you may need to re-apply the patch or set `window.__NEXT_ASSET_PREFIX__ = "/next"` in `index.html` (already set).
2. **Server doesn’t serve events JSON** – Ensure both `/events.json` and `/next/events.json` return **200** and `application/json`. Locally, `tools/serve_local.py` serves both; on the live server, have `events.json` at the site root and a copy at `next/events.json`.

**Local check:** Open http://127.0.0.1:9000/ and http://127.0.0.1:9000/next/events.json – both should return JSON. Restart the local server after changing `serve_local.py`.

### Fix 4 – Use the canonical URL

Prefer **https://findtorontoevents.ca/** instead of **https://findtorontoevents.ca/index.html** for testing and sharing. Some setups cache or redirect differently for `/` vs `/index.html`. The fixes above apply to both; using `/` avoids unnecessary differences.

### If deploy is correct but you still see errors

If you’ve confirmed:

- Live **View Source** uses `/next/_next/static/chunks/...` and the chunk URL returns **200** with body starting with `(globalThis.TURBOPACK...` (e.g. with curl or DevTools → Network → click the chunk → Response),

then the server and paths are correct. The remaining cause is usually **cache**:

1. **Hard refresh:** Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac).
2. **Incognito/private window:** Open the site in a private window to avoid cached HTML/JS.
3. **Cache-bust:** Ensure every asset URL in `index.html` uses the same `?v=YYYYMMDD-...` (including the CSS **preload** link). If the stylesheet has `?v=20260131-185045` but the preload doesn’t, you get “Preloaded but not used” and possible stale loads. After changing `?v=`, re-upload `index.html` and hard-refresh again.

---

## 4. Quick checklist after fixing

- [ ] Live **View Source** shows `/next/_next/static/chunks/...` and `?v=...` for all chunk URLs.
- [ ] **Network**: request to `a2ac3a6616d60872.js` is **200** and response is JavaScript starting with `(globalThis.TURBOPACK...`.
- [ ] **Console**: no SyntaxError or ChunkLoadError.
- [ ] Page shows **event cards** and the **filter bar** (search, GLOBAL FEED, date/price, etc.).

---

## 5. Reference

- **Break-fix / debugging:** `BREAK_FIX.MD`
- **What breaks events loading (rules for editing HTML):** `FIX_SUMMARY.md` (section “WHAT BREAKS EVENTS LOADING”)
