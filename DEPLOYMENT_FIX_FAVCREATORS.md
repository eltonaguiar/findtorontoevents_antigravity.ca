# FavCreators Link Fix - Deployment Instructions

## Issue
The main menu link for "Fav creators" was going to `/favcreators/` or `/favcreators/#/guest`. **The host returns 500 for `/favcreators/`**, so the correct working URL is **`/fc/#/guest`**.

## Fix Applied
The JavaScript chunk file is patched by `tools/patch_nav_js.py`. The file `next/_next/static/chunks/a2ac3a6616d60872.js` must contain:
- ✅ Correct URL: `href:"/fc/#/guest"` (1 occurrence)
- ❌ Wrong URLs: `href:"/favcreators/"` or `href:"/favcreators/#/guest"` (0 occurrences)

## Files Fixed
The following files are updated by `tools/patch_nav_js.py` and are ready for deployment:
1. `next/_next/static/chunks/a2ac3a6616d60872.js` (primary file)
2. Mirrors under `_next/`, `next/`, `TORONTOEVENTS_ANTIGRAVITY/`, `DEPLOY/` as configured in the script

## Deployment Steps
1. Run `python tools/patch_nav_js.py` to ensure chunk uses `/fc/#/guest` (it replaces both `/favcreators/` and `/favcreators/#/guest`).
2. Upload the fixed `next/_next/static/chunks/a2ac3a6616d60872.js` (and mirrors) to the server.
3. Ensure **index.html** is deployed (it includes a client-side fix that rewrites any link containing "favcreators" to `/fc/#/guest` and intercepts clicks).
4. Clear any CDN/server cache for JavaScript files.
5. Verify: https://findtorontoevents.ca/fc/#/guest should load; https://findtorontoevents.ca/favcreators/#/guest returns 500.

## Verification
After deployment, run:
```bash
npx playwright test tests/inspect_favcreators_link.spec.ts
```

The test should show the FAVCREATORS link pointing to `/fc/#/guest` (not `/favcreators/#/guest`).

## Tools
- `tools/patch_nav_js.py` – Replaces `href:"/favcreators/"` and `href:"/favcreators/#/guest"` with `href:"/fc/#/guest"` in the nav chunk.
- `tools/fix_favcreators_url.py` – Fixes chunk files to use `/fc/#/guest`.
- `tools/verify_fix.py` – Verifies the chunk uses `/fc/#/guest`.
