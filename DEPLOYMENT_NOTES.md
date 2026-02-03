# Deployment Notes — Prevent Partial Deployments

**Rule:** Never deploy a page or asset without deploying **all of its dependencies** and **verifying** the result.

## 1. No partial deployments

- **Do not** upload only one file (e.g. `index4.html`) and assume the page will work.
- **Do** identify every resource the page needs (HTML, CSS, JS, JSON, favicon, chunks, etc.) and deploy that **full set**.
- **Do** deploy to every URL path where the page can be served (e.g. domain root and `/findevents/` if both are used).

**Example (index4.html):** The page depends on:
- `index4.html` itself
- `data/menu4.json` (menu fetch)
- `next/events.json`, `events.json`, `data/events.json` (events fetch)
- `next/_next/static/chunks/cd9d6741b3ff3a25.css` (styles)
- `favicon.ico` (icon)

Deploying only `index4.html` causes "Menu fetch 404" and "Could not load events" until the rest are uploaded. Use `tools/deploy_index4.py` which uploads the full set.

## 2. Dependency check before deploy

Before running any deploy script or one-off upload:

1. **List dependencies** of the target page/asset:
   - Inspect the HTML/JS for: `<link href=`, `<script src=`, `fetch(...)`, `src=`, `href=` (data, API, assets).
   - Note whether URLs are absolute (`/path`) or relative (`path` or `./path`); both resolve from the page URL, so the same files must exist at the right remote paths.
2. **Ensure the deploy script (or upload list) includes every dependency.** If the script only uploads one file, either extend the script or run additional uploads so the full set is deployed.
3. **If the page is served from multiple paths** (e.g. `/index4.html` and `/findevents/index4.html`), deploy the **same full set** to both locations (e.g. under domain root and under `findevents/`).

## 3. Verify after deploy (and check for JS errors)

After every deploy:

1. **Run remote verification** so the live site is checked for load, events, and **no JavaScript errors**:
   - **Recommended:** `npm run verify:remote` (runs Playwright tests against the live site, including "no critical JS errors in console").
   - Or: `VERIFY_REMOTE=1 npx playwright test tests/verify_remote_site.spec.ts`
2. **Check:** page loads, no 404s in Network tab, **no SyntaxError / ChunkLoadError in console**, events and styles load.
3. **If anything fails:** fix (e.g. chunk syntax, missing files), redeploy the affected files, and verify again.

Do not consider a deploy "done" until this verification passes. A broken chunk (e.g. `a2ac3a6616d60872.js`) will cause "Uncaught SyntaxError" and break the events page; the Playwright test catches this.

## 3b. Check for JS errors before deploy (optional but recommended)

Before deploying changes that touch the main React chunk or `index.html`:

1. **Local verification:** `npm run verify:local` (runs Playwright against local server; includes `no_js_errors.spec.ts`).
2. **Or** start the local server (`python tools/serve_local.py`), open the page, and confirm the browser console has no SyntaxError or critical errors.
3. **Chunk edits:** If you patched `next/_next/static/chunks/a2ac3a6616d60872.js` (or `_next/static/chunks/...`), ensure braces and parentheses are balanced so the script parses. One missing `}` or `)` can cause "missing ) after argument list" or "Unexpected token" and break the events page after deploy.

## 4. Scripts and references

| Deploy target | Script | What it deploys |
|--------------|--------|------------------|
| Main site (index.html, events, nav) | `tools/deploy_to_ftp.py` | index.html, .htaccess, events.json, next/events.json, next/_next/, FavCreators to /fc/ |
| index4.html (backup landing) | `tools/deploy_index4.py` | index4.html, data/menu4.json, data/events.json, events.json, next/events.json, favicon.ico, next/_next/ (to both root and findevents) |

- **Skill:** `.cursor/skills/deploy-and-fix-remote/SKILL.md` — full workflow: local test → deploy → verify remote.
- **FTP credentials:** `.cursor/rules/ftp-credentials.mdc` — use env vars only.
