# Break-Fix: Debugging Events Loading on findtorontoevents.ca

**Use this guide when events don’t load, filters don’t work, or you see JS errors after editing the site (especially `index.html`).**

---

## 1. Quick diagnosis

| Symptom | Likely cause | Go to |
|--------|----------------|-------|
| **SyntaxError: Unexpected token '('** in a chunk file (e.g. `a2ac3a6616d60872.js`) | Server returned non-JS (404 HTML, ModSecurity block, or wrong path) | [§2](#2-syntaxerror-unexpected-token) |
| **“Preloaded but not used”** for a CSS/JS URL | Preload URL and real `<link>`/`<script>` don’t match (path or query) | [§3](#3-preload-not-used) |
| **Events show but no filters** (no search, no GLOBAL FEED, no date/price filters) | React app didn’t load or hydration was broken (e.g. fallback script rewrote DOM) | [§4](#4-events-but-no-filters) |
| **Blank or skeleton grid only** | Chunks 404/blocked or React never ran | [§2](#2-syntaxerror-unexpected-token) |
| **MutationObserver error in `web-client-content-script.js`** | Browser extension, not site code | [§5](#5-extension-errors) |

---

## 2. SyntaxError: Unexpected token '('

**What it means:** The browser requested a JS chunk but got something that isn’t JavaScript (e.g. HTML error page or “denied by modsecurity”). The engine tries to parse it as JS and fails.

**Debug steps:**

1. **Network tab**
   - DevTools → **Network** → reload.
   - Find the request for the chunk in the error (e.g. `a2ac3a6616d60872.js`).
   - Check:
     - **Request URL** – must match where the server actually serves the file (see below).
     - **Status** – should be **200**.
     - **Response** – must be JavaScript (e.g. starts with `(globalThis.TURBOPACK...`), not HTML or a short message.

2. **Path**
   - **Live site (findtorontoevents.ca):** Chunks are under **`/next/_next/static/chunks/`**.
   - In `index.html`, every asset URL must use that base: **`/next/_next/`** (not `/_next/`).
   - If the HTML uses `/_next/...`, the server returns 404 HTML → SyntaxError.

3. **Query string**
   - First query parameter must use **`?`** (e.g. `?v=20260131-v3`), not **`&`** (e.g. `file.js&v=...`).
   - Wrong: `href="/next/_next/static/chunks/file.css&v=20260131-v3"`  
   - Right: `href="/next/_next/static/chunks/file.css?v=20260131-v3"`

4. **ModSecurity / WAF**
   - If the response body is “denied by modsecurity” or similar, the server/WAF is blocking the request.
   - Ensure `.htaccess` (or equivalent) under the directory that serves the chunks disables or whitelists ModSecurity for those JS/CSS requests (see `FIX_SUMMARY.md`).

**Fix:** Update `index.html` so all chunk URLs use **`/next/_next/`** and **`?v=...`**. Re-upload and hard-refresh. Do not reformat or minify the whole file in a way that changes these URLs.

---

## 3. Preload not used

**What it means:** A `<link rel="preload" href="...">` points to a different URL than the actual `<link rel="stylesheet">` or `<script src="...">` that loads the resource, or the real load failed.

**Debug steps:**

1. In `index.html`, compare:
   - The **preload** `href` (e.g. for the main CSS or main JS).
   - The **stylesheet** `href` or **script** `src` for the same file.
2. They must be **identical** (path + query). Often the preload had `/next/_next/...` and the stylesheet had `/_next/...`, or one had `?v=...` and the other had `&v=...`.

**Fix:** Make preload and the real tag use the same URL: **`/next/_next/static/chunks/...`** and **`?v=...`**.

---

## 4. Events but no filters

**What it means:** The events grid has content (e.g. from a static fallback or skeleton) but the React app didn’t hydrate, so the filter bar (search, GLOBAL FEED, date/price/category) never appears.

**Common causes:**

1. **Fallback script** – A script fetches `events.json` and injects HTML into the events grid. That **replaces the DOM** React expects, so hydration fails.  
   **Fix:** Remove any script that writes event HTML into the grid. The site must rely only on the React app for events and filters.

2. **Chunk load failure** – One or more JS chunks failed (404, block, wrong path/query). React never runs.  
   **Fix:** Same as [§2](#2-syntaxerror-unexpected-token): fix paths and query strings, ensure chunks return 200 and real JS.

**Check:** Open Network tab; every `_next` chunk request should be 200 and return JavaScript. If any chunk fails or returns HTML, fix that first.

---

## 5. Extension errors

**MutationObserver / `web-client-content-script.js`:**  
This comes from a **browser extension** (e.g. Cursor, dev tools), not from findtorontoevents.ca. You can’t fix it in site code.

**What to do:** Disable extensions for the site, or test in a clean/incognito profile, to avoid noise when debugging.

---

## 6. Checklist before editing index.html

- [ ] I will **not** change any `href` or `src` that points to `_next` (must stay **`/next/_next/`** and **`?v=...`**).
- [ ] I will **not** add a script that fetches `events.json` and writes HTML into the events grid.
- [ ] I will **not** reformat or minify the whole file; I will edit only the specific block (e.g. nav links).
- [ ] For menu/nav/footer: I will only change `<a href="...">` and link text; no global replace on `/_next/` or `?`/`&`.

---

## 7. Verification after a fix

1. **Live:** Open https://findtorontoevents.ca/ (or your live URL).
2. **Network:** DevTools → Network → reload. Click `a2ac3a6616d60872.js`:
   - URL: `https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js?v=...`
   - Status: **200**
   - Response: starts with `(globalThis.TURBOPACK...`
3. **Console:** No red SyntaxError or ChunkLoadError.
4. **UI:** Filter bar (search, GLOBAL FEED, date/price/category) and event cards appear and work.

---

## 8. Reference

- **Full rules and “what broke” table:** `FIX_SUMMARY.md` (section **WHAT BREAKS EVENTS LOADING**).
- **Source repo (Toronto Events Antigravity):** [github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY).
