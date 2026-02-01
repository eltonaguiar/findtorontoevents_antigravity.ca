# Fix Toronto Events – Reference

Read these project files when you need full detail. Paths are relative to the workspace root (`e:\findtorontoevents_antigravity.ca` or `E:\findtorontoevents.ca`).

## Primary Fix docs (repo root)

| File | Use when |
|------|----------|
| **FIX_SUMMARY.md** | Rules for editing index.html, what breaks events, 3-layer fix (WAF, data sync, hydration), SyntaxError diagnosis, verification, "0 events", hydration #418, "Today" filter, MutationObserver. |
| **INDEX_BROKEN_FIX.md** | Step-by-step diagnosis (DevTools, Network, View Source), fix steps in order (deploy index, chunks at next/_next/, ModSecurity, events.json, sw.js, canonical URL), checklist. |
| **WHAT_FIXED_IT.md** | Timeline of fixes, key insight (server uses /next/_next/; .htaccess in subdirs bypass ModSecurity). |
| **FIX_STATUS.md** | Current status, path vs rewrite, recommended next steps. |
| **FINAL_FIX_SUMMARY.md** | Root cause (ModSecurity blocking JS), options (host whitelist, server config, alternate dir). |
| **DEPLOYMENT_FIX_SUMMARY.md** | Incorrect asset paths, upload steps, FTP notes. |
| **DEPLOYMENT_FIX_FAVCREATORS.md** | FavCreators link fix, deployment steps, verification (Playwright test), tools (patch_nav_js.py, etc.). |

## TORONTOEVENTS_ANTIGRAVITY (data/parsing fixes)

- **COMPREHENSIVE_DATE_FIX_PLAN.md**, **DATE_*_COMPLETE.md**, **DATA_PARSING_FIXES.md**, **PRICING_*_FIXES.md**, **EMERGENCY_FIX_COMPLETE.md**, etc. – Use when fixing date/time parsing, invalid data, or pricing in the app or build.

## Key tools (tools/)

- **copy_to_next_path.py** – Copy `_next/` to `next/_next/` so server paths match.
- **upload_next_htaccess.py** – Upload .htaccess to `_next/`, `next/_next/`, `next/_next/static/chunks/` to bypass ModSecurity.
- **patch_nav_js.py** – Fix FavCreators (and other nav) URLs in chunk files.
- **serve_local.py** – **Use this for local testing.** Mimics js-proxy-v2.php so chunk URLs return real JS/CSS. Do NOT use `python -m http.server` (it would serve PHP source → SyntaxError → events never load).
- **shift_event_dates.py** – Shift event dates for testing (e.g. `--min-today`).
- **fix_html_paths.py**, **deploy_fix.py**, **ftp_backup_and_upload.py** – Deployment and path fixes.

## Local testing (127.0.0.1:9000)

- **Always run:** `python tools/serve_local.py` from the project root.
- **Do not run:** `python -m http.server` – chunk URLs point to js-proxy-v2.php; without the mimic you get PHP source instead of JS → SyntaxError → React never loads → events never load.

## Quick paths (live server)

- Chunk base: **/next/_next/static/chunks/** (e.g. `a2ac3a6616d60872.js?v=...`).
- Events JSON: **/events.json**, **/next/events.json**, **/data/events.json** (sync same file to all).

---

## Debugging / fix notes (faster next time)

Use these when the same issues recur. Full steps in [SKILL.md](SKILL.md) §7.

| Issue | Cause | Fix |
|-------|--------|-----|
| **Local: events not loading, SyntaxError** | `python -m http.server` serves PHP source for `/js-proxy-v2.php?file=...` → browser gets PHP, not JS. | Use **`python tools/serve_local.py`** only (mimics proxy, serves real JS). |
| **Live: proxy times out** | `js-proxy-v2.php?file=...` times out or fails on host. | Use **direct chunk URLs** (`/next/_next/static/chunks/xxx.js`). Root .htaccess: comment out proxy rewrite; add `RewriteRule ^next/_next/ - [L]`. Deploy ModSecurity bypass .htaccess in `next/_next/` and `next/_next/static/chunks/`. |
| **Live: getAssetPrefix() throws E784** | Scripts loaded via proxy → `document.currentScript.src` has no `/_next/`. | Patch **dde2c8e6322d1671.js**: when pathname has no `/_next/`, return `window.__NEXT_ASSET_PREFIX__ \|\| "/next"`. Redeploy chunk. |
| **Live: still broken after deploy** | Host may serve from **findtorontoevents.ca/** subdir. | Deploy **same set** to both FTP root and **findtorontoevents.ca/**: index.html, .htaccess, chunks, events.json, next/events.json. |
| **Events fetch broken** | Complex tryFetch/clone can break app's response handling. | Use simple rewrite: any `events.json` request → single fetch to `/next/events.json` (match sister project). |
