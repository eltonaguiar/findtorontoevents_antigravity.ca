---
name: verify-remote-site
description: After coding changes, fully verify and test the remote site (findtorontoevents.ca) using Playwright and HTTP fallback—events load, no JS errors, key features present.
---

# Verify Remote Site

Use this skill when the user asks to **verify remote site**, **test the live site**, **confirm findtorontoevents.ca works**, or **run remote verification** after coding changes.

## Root cause: FavCreators path (/fc/ not /favcreators/)

On the host, **any URL path containing the segment "favcreators"** returns **500 Internal Server Error** (including direct requests to static files). The cause is server-side handling (e.g. a global rule, handler, or filter for that folder name) that fails. **We avoid it by deploying the FavCreators app under a different path: /fc/.**

- **FavCreators guest:** `https://findtorontoevents.ca/fc/#/guest` or `https://findtorontoevents.ca/findevents/fc/#/guest`
- **Main site (Toronto Events):** Often at `https://findtorontoevents.ca/findevents/` (or root). For verification, set **REMOTE_BASE** or **VERIFY_REMOTE_URL** to the base that serves the main index (e.g. `https://findtorontoevents.ca/findevents`).
- **Quick Nav / menu:** FavCreators link points to **/fc/#/guest** (not /favcreators/#/guest).

## 1. Run verification

Run:

```bash
npm run verify:remote
```

This:

1. Runs **Playwright** against `https://findtorontoevents.ca` (or `VERIFY_REMOTE_URL`):
   - Homepage 200
   - Events grid visible
   - **Events count > 0** (cards or "N EVENTS FOUND")
   - Filter UI (GLOBAL FEED / search) visible
   - No critical JS errors (SyntaxError, ChunkLoadError, ModSecurity)
   - Main chunk returns JavaScript
   - Quick Nav and key links (e.g. FavCreators → /fc/#/guest)
2. If Playwright fails or is unavailable, runs the **HTTP fallback** (no browser):
   - Index 200 and HTML has `#events-grid` and chunk refs
   - Chunk 200 and body is JS (not HTML/ModSecurity)
   - `events.json` 200 and non-empty events array

## 2. Report result

- **PASS:** All checks passed; report "Remote verification passed."
- **FAIL:** Report the first failing check or error and suggest fixes (e.g. chunk blocked → see fix-toronto-events skill, FIX_SUMMARY.md).

## 3. Optional: different URL

For staging or another base URL:

```bash
VERIFY_REMOTE_URL=https://staging.example.com npm run verify:remote
```

## 4. When local verified passed and ready to deploy: cross-comparison

Run a **cross-comparison** so remote vs local can be checked for missing or outdated content:

1. Ensure the **local server is running** (`python tools/serve_local.py`).
2. Run:

```bash
npm run compare:local-vs-remote
```

This compares:

- **Index:** Chunk script list (remote must have at least the same chunks as local).
- **Main chunk:** Content hash; if different, remote may be outdated.
- **events.json:** Event count; warns if remote has 0 and local has &gt; 0.
- **&lt;title&gt;:** Warns if index.html is out of sync.

**FAIL** = remote missing chunk(s) or remote chunk not valid JS. **WARN** = remote may be outdated or missing data. **OK** = remote in sync. If FAIL or WARN, deploy then re-run `npm run verify:remote`.

Env: **LOCAL_BASE** (default `http://localhost:9000`), **REMOTE_BASE** or **VERIFY_REMOTE_URL** (default `https://findtorontoevents.ca`). If the main site is under findevents, set **REMOTE_BASE=https://findtorontoevents.ca/findevents** (or VERIFY_REMOTE_URL) so index/chunk/events checks hit the correct base.

## 5. FTP / deploy

Verification does **not** use FTP. To deploy first (using FTP env vars), use the project deploy tools and then run `npm run verify:remote`. See `.cursor/rules/ftp-credentials.mdc` for FTP env vars.

## Files

- **Tests:** `tests/verify_remote_site.spec.ts`
- **Runner:** `tools/verify_remote_site.js` (Playwright then fallback)
- **Fallback:** `tools/verify_remote_site_fallback.js` (HTTP-only)
- **Compare:** `tools/compare_local_vs_remote.js` (local vs remote when ready to deploy)
- **Rule:** `.cursor/rules/verify-remote-site.mdc`
