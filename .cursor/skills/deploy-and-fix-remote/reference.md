# Deploy and Fix Remote — Reference

## No partial deployments

- **Never** deploy only one file (e.g. a single HTML page) without deploying **all dependencies** (CSS, JS, JSON, favicon, chunks, etc.).
- **Before deploy:** list every resource the page loads; ensure the deploy script (or upload list) includes the full set.
- **After deploy:** verify the URL (no 404s, no console errors); run `npm run verify:remote` for the main site.
- See **DEPLOYMENT_NOTES.md** (workspace root) for examples and script reference.

## FTP credentials (env vars)

| Variable | Purpose |
|----------|--------|
| `FTP_SERVER` or `FTP_HOST` | FTP hostname |
| `FTP_USER` | FTP username |
| `FTP_PASS` | FTP password |
| `FTP_REMOTE_PATH` | Remote path (e.g. `findtorontoevents.ca/findevents`); optional, has default in deploy script |

**Clarify with user if unclear:** Which FTP site? Which remote directory (document root)?

## Commands (order)

| Step | Command | Purpose |
|------|--------|--------|
| 1. Local server | `python tools/serve_local.py` | Serve at http://localhost:9000 (correct MIME for chunks). |
| 2. Local verify | `npm run verify:local` | Playwright: events load, no JS errors. **Must pass before remote deploy.** |
| 3. Deploy | `python tools/deploy_to_ftp.py` | Upload index, .htaccess, events.json, next/_next/ to FTP_REMOTE_PATH. |
| 4. Remote verify | `npm run verify:remote` | Playwright + fallback: events, no JS errors on live site. |

## When remote verify fails

| Symptom | Use | Action |
|--------|-----|--------|
| Events not loading, SyntaxError, no filter bar, chunk 404/blocked | **fix-toronto-events** | Read skill + reference; apply path/chunk/ModSecurity/events.json fixes; redeploy; re-verify. |
| Nav menu wrong (links, labels) | **fix-nav-menu** | Edit nav block only; patch_nav_js.py if chunk must match; redeploy; re-verify. |
| Other | Project .MD | FIX_SUMMARY.md, INDEX_BROKEN_FIX.md, DEPLOYMENT_FIX_FAVCREATORS.md; inspect manually; fix and redeploy. |

## Deploy to both locations

If the host serves from a subdirectory (e.g. findtorontoevents.ca/), deploy the **same set** to:

- FTP root: index.html, .htaccess, events.json, js-proxy if used
- **findtorontoevents.ca/** (or that subdir): index.html, .htaccess, next/_next/, events.json, next/events.json

## Worst case

Events still not loading after fixes → compare with sister project **E:\findtorontoevents.ca** (working events). Align index.html chunk URLs, events.json path, chunk syntax; re-test locally, then redeploy and verify remote.

## Deploy scripts (full set only)

| Target | Script | Includes |
|--------|--------|----------|
| Main site | `tools/deploy_to_ftp.py` | index.html, .htaccess, events.json, next/events.json, next/_next/, FavCreators |
| index4.html | `tools/deploy_index4.py` | index4.html, data/menu4.json, data/events.json, events.json, next/events.json, favicon.ico, next/_next/ (root + findevents) |

## Related skills

| If | Use |
|----|-----|
| Events not loading, SyntaxError, skeleton only | **fix-toronto-events** |
| Nav menu links/labels/structure wrong | **fix-nav-menu** |
| Local-only deploy and test | **deploy-and-fix-local** |
| Verify live site after changes | **verify-remote-site** |
