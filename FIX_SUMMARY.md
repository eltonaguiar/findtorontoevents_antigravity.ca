# What Fixed findtorontoevents.ca

---

## ⚠️ WHAT BREAKS EVENTS LOADING (Read Before Editing index.html)

**Events and filters only work when the React app loads.** The React app loads only when every chunk URL in `index.html` returns the real JavaScript/CSS file. Small edits to `index.html` (e.g. updating the menu, adding a link, reformatting, or “fixing” HTML) have repeatedly broken loading because they changed asset URLs or structure. **AI agents and humans:** follow the rules below whenever you touch `index.html`.

### What Actually Broke (Exact Failures)

| What broke | How it broke | Result |
|------------|--------------|--------|
| **Asset path** | URLs were `/_next/static/chunks/...` but the **live server** serves files from **`/next/_next/static/chunks/...`**. A 404 returns HTML; the browser parses that as JS → **SyntaxError: Unexpected token '('**. | React never runs, no events, no filters. |
| **Query string** | First query parameter used **`&`** instead of **`?`** (e.g. `href=".../file.css&v=20260131-v3&v=..."`). The server treats `file.css&v=...` as the filename → 404 or wrong file. | Chunks fail to load or wrong/cached file. |
| **Preload mismatch** | Preload link pointed to one URL (e.g. `/next/_next/...`) and the real `<link rel="stylesheet">` or script to another (e.g. `/_next/...`) or had wrong query. | Warning: “preloaded but not used”; CSS/JS can fail. |
| **Fallback script** | A script injected event HTML into the events grid from `events.json`. That **replaced the DOM** React was about to hydrate. | React could not attach; filters and interactivity never worked. |
| **Reformat / minify** | Reformatting or “cleaning” HTML sometimes changed `?v=...` to `&v=...`, or stripped the `next` segment from paths, or altered the order of attributes. | Same as path/query breakage above. |

### Rules When Editing index.html (Menu, Links, Content, Anything)

1. **Do not change any asset URL.**
   - Every `href` or `src` that points to `_next` must stay exactly as-is:
   - **Live site:** base path is **`/next/_next/`** (e.g. `/next/_next/static/chunks/a2ac3a6616d60872.js?v=20260131-v3`).
   - First query parameter must use **`?`** (e.g. `?v=20260131-v3`), never **`&`** (e.g. `&v=...`).
   - Do not “fix” or “normalize” these URLs when updating menu, nav, or footer.

2. **Do not add a “fallback” or “backup” script** that fetches `events.json` and writes HTML into the events grid (or any container React hydrates). It will break hydration and remove filters/features.

3. **Do not reformat or minify the whole file** unless you are certain no `/_next/` or `/next/_next/` URL and no `?v=` in asset URLs is changed. Prefer editing only the specific line or block (e.g. the nav list) for menu/link changes.

4. **Menu/nav/footer link changes:** Only edit the `<a href="...">` and link text inside the existing nav/footer. Do not do a global find-replace on `/_next/` or on `?`/`&` in the file.

5. **After any edit:** Confirm in the built HTML that:
   - All chunk URLs still start with **`/next/_next/`** (on the live server).
   - Every asset URL uses **`?v=...`** for the first query param, not `&v=...`.

### Why “Simple” Changes Keep Breaking It

- **Single file:** All critical URLs live in one file (`index.html`). A small edit (e.g. add FavCreators link) often involves opening the whole file; automated tools or agents then “tidy” or “fix” the rest (paths, query strings, or add fallbacks).
- **Fragile URLs:** The site works only when every chunk request hits the correct path and gets real JS/CSS. One wrong URL (or one fallback script) is enough to break events and filters.
- **Copy-paste / find-replace:** Replacing `/_next/` with something else, or `?v=` with `&v=`, or inserting a fallback “so events show if JS fails” has happened repeatedly; it always breaks the real app.

### Quick Check After Edits

- **Live site:** Open DevTools → Network, reload, and check the request for `a2ac3a6616d60872.js`:
  - URL should be `https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=...`
  - Status 200, response body starts with `(globalThis.TURBOPACK...`
- If you see **SyntaxError: Unexpected token '('** or **preload not used**, compare asset URLs in `index.html` to the rules above.

---

## ✅ Site is Now Working!

The site is successfully loading events. Console shows:
- ✅ "Successfully loaded 1084 events from FTP fallback"
- ✅ "EventFeed Display events: 953"
- ✅ JavaScript files loading correctly (38,924 bytes - valid content)

## The Fix (Based on FTP File Timestamps - Converted to Eastern Time)

### Critical Changes (2026-01-31 3:32 PM - 3:40 PM EST)

1. **Copied `_next/` to `next/_next/`** (3:32-3:33 PM EST)
   - **What**: Copied all static assets to `next/_next/static/chunks/` directory
   - **Why**: Server HTML was requesting files from `/next/_next/...` paths
   - **Tool**: `tools/copy_to_next_path.py`

2. **Added `.htaccess` files in subdirectories** (3:33-3:35 PM EST)
   - **What**: Created `.htaccess` files in:
     - `_next/.htaccess`
     - `next/_next/.htaccess`  
     - `next/_next/static/chunks/.htaccess`
   - **Why**: Bypass ModSecurity blocking for JavaScript files
   - **Content**: Disabled ModSecurity rules for those directories
   - **Tool**: `tools/upload_next_htaccess.py`

3. **Updated root `.htaccess`** (3:40 PM EST)
   - **What**: Added rewrite rule to route JS files through PHP proxy
   - **Why**: Additional layer of protection (though subdirectory `.htaccess` files were the main fix)

4. **Uploaded `events.json`** (3:39 PM EST)
   - **What**: Made events data available at root and `data/` directory
   - **Why**: Fallback data source when GitHub isn't accessible

## Root Cause

The server's **ModSecurity** was blocking JavaScript files at `/next/_next/...` paths, returning "denied by modsecurity" (21 bytes) instead of actual JavaScript (38KB). This caused:
1. JavaScript syntax errors (browser tried to execute "denied by modsecurity" as code)
2. React never initialized
3. EventFeed component never mounted
4. No events displayed

## The Solution

By copying files to `next/_next/` AND adding `.htaccess` files in those directories to disable ModSecurity, the files became accessible. The `.htaccess` files in subdirectories take precedence and allow the files to be served correctly.

## Files That Fixed It

Based on modification times (Eastern Time), these were the critical fixes:

1. **`next/_next/.htaccess`** (3:33 PM EST) - **PRIMARY FIX**
   - Disabled ModSecurity for `next/_next/` directory
   - Allowed JavaScript files to be served

2. **`next/_next/static/chunks/.htaccess`** (3:35 PM EST) - **SECONDARY FIX**
   - Additional ModSecurity bypass for chunks directory

3. **Files in `next/_next/static/chunks/`** (3:32-3:33 PM EST)
   - All JavaScript files copied to match server's expected paths

## Verification

- ✅ JavaScript files return 38,924 bytes (correct size)
- ✅ Files contain valid JavaScript code (not "denied by modsecurity")
- ✅ Events loading: 1084 events loaded, 953 displayed
- ✅ EventFeed component rendering correctly
- ✅ No more syntax errors in console

## Key Takeaway

The `.htaccess` files in subdirectories (`next/_next/.htaccess`) were the **primary fix**. They allowed ModSecurity to serve the JavaScript files correctly, which enabled React to initialize and the EventFeed component to render.

---

## Full UI (Filters, Search, GLOBAL FEED) = React App Must Load

The **filter bar** (search, "GLOBAL FEED" / "MY EVENTS", date filters, price limit, categories, hidden-event toggles) is **not** in the static HTML. It is rendered by the **React app** when the client-side JS loads and hydrates. Any script that rewrites the events grid (e.g. a static fallback that injects HTML) will break React’s DOM and prevent filters from working, so the events fallback was removed; the site relies entirely on the React app for events and filters.

- **If you see event cards but NO filter bar** (no search, no date/price/category filters): the React app is not loading. You are either seeing skeleton cards or an old static fallback.
- **Fix:** Ensure `/_next/static/chunks/*.js` (or `/next/_next/static/chunks/*.js` if your server uses that path) are served correctly:
  - Return **200** and **JavaScript** content (not HTML, not "denied by modsecurity").
  - Check **Browser Console** for red errors (e.g. SyntaxError, ChunkLoadError).
  - Check **Network** tab: chunk requests must succeed and return valid JS.
- **Reference:** tdotevent.ca shows the full UI because its React app loads; same app, same code.

---

## MutationObserver error in `web-client-content-script.js`

If you see: **"Uncaught TypeError: Failed to execute 'observe' on 'MutationObserver': parameter 1 is not of type 'Node'"** in `web-client-content-script.js`:

- This comes from a **browser extension** (e.g. Cursor or another IDE/dev extension), not from findtorontoevents.ca.
- The extension is trying to observe a DOM node that does not exist yet or is not a valid Node.
- **You cannot fix this in the site code.** To reduce interference: disable extensions on the site, use a clean browser profile, or test in an incognito window with extensions off.

---

## "a2ac3a6616d60872.js:14 Uncaught SyntaxError: Unexpected token '('"

This error means **the browser did not receive real JavaScript** for that chunk. The file on disk (in `_next/static/chunks/a2ac3a6616d60872.js`) is valid JS; the server is returning something else for the request.

**Typical causes:**

1. **Wrong response body** – The URL for the chunk returns HTML (e.g. a 404 page), "denied by modsecurity", or another short text/HTML response. The engine parses that as JS and fails (e.g. at "line 14" of that HTML).
2. **Path mismatch** – `index.html` asks for `/_next/static/chunks/a2ac3a6616d60872.js`, but on the server the file lives under `next/_next/static/chunks/`. The server then returns a 404 HTML page for `/_next/...`, which causes the SyntaxError.
3. **ModSecurity / WAF** – The server or WAF blocks the request and returns a block message instead of the JS file.

**What to do:**

1. **Network tab** – Open DevTools → Network, reload, click the request for `a2ac3a6616d60872.js`. Check:
   - **Status**: should be 200.
   - **Response**: should be JavaScript (starts with `(globalThis.TURBOPACK...`), not HTML or a short message.
2. **Path** – If your site is configured to serve chunks from `next/_next/`, ensure `index.html` (and any inline script that references chunks) uses the same base path (e.g. `/next/_next/static/chunks/...`). If the server only has `_next/` at the document root, ensure the server is serving those files for `/_next/...` (no `next/` prefix).
3. **ModSecurity** – If the response is "denied by modsecurity" or similar, add or keep `.htaccess` (or equivalent) under the directory that serves the chunks so that ModSecurity does not block those JS requests (see "Files That Fixed It" above).

Once the chunk URL returns the actual JS file (200 + correct body), the SyntaxError and the resulting React/filter issues go away.
