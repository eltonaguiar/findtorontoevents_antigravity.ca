---
name: deploy-and-fix-remote
description: Checks FTP credentials and deploys to the remote site; clarifies which FTP site and directory if unclear. Tests locally first (serve_local + Playwright), then deploys remotely and verifies; if remote fails uses fix-toronto-events, fix-nav-menu, and project .MD docs until fixed. Events must load with no JS errors; worst case refer to sister project E:\findtorontoevents.ca.
---

# Deploy and Fix Remote

Use this skill when the user asks to **deploy to the remote site**, **deploy and verify live**, **push changes to findtorontoevents.ca**, or **deploy and fix until the remote site works**.

**Known issue:** After changes—especially to the **nav menu**—Toronto Events may stop loading on the page. Use fix-toronto-events if events fail, fix-nav-menu if the nav needs fixing. Events must load with no JavaScript syntax errors.

## 1. Clarify FTP target (if unclear)

Before deploying, ensure you know **which FTP site** and **which remote directory** to use.

- **Env vars** (see `.cursor/rules/ftp-credentials.mdc`):
  - `FTP_SERVER` or `FTP_HOST` — FTP hostname
  - `FTP_USER` — FTP username
  - `FTP_PASS` — FTP password
  - `FTP_REMOTE_PATH` — remote path (e.g. `findtorontoevents.ca/findevents` or site root)

**If unclear:** Ask the user explicitly:
- "Which FTP site should I deploy to? (e.g. findtorontoevents.ca)"
- "Which remote directory is the document root? (e.g. FTP root, or `findtorontoevents.ca/findevents`)"

Default in project tools is often **`findtorontoevents.ca/findevents`** (site under a subfolder). Confirm before running deploy.

## 2. Check FTP credentials

Before any FTP deploy:

1. **Verify** that `FTP_SERVER` (or `FTP_HOST`), `FTP_USER`, and `FTP_PASS` are set (or will be set by the user).
2. **Remind** the user to set them if not set: e.g. `set FTP_SERVER=... FTP_USER=... FTP_PASS=...` (Windows) or `export FTP_SERVER=...` (Unix), or load from `.env` if the script supports it.
3. **Do not** hardcode credentials in scripts or in chat.

If credentials are missing and the user cannot provide them, stop at "credentials required" and do not attempt FTP upload.

## 2.5 No partial deployments (required)

**Never deploy a single page or asset without deploying all of its dependencies and verifying the result.**

1. **Identify dependencies** before deploy: inspect the page/HTML for every resource it loads (CSS, JS, JSON, favicon, chunks, API endpoints). List absolute and relative URLs.
2. **Deploy the full set:** use a script that uploads every dependency (e.g. `deploy_index4.py` for index4.html + menu + events + CSS + favicon), or run additional uploads so nothing is missing.
3. **If the page is served from multiple paths** (e.g. root and `/findevents/`), deploy the same full set to both locations.
4. **Verify after deploy:** load the URL, check Network tab for 404s and console for errors; run `npm run verify:remote` for the main site. Do not consider deploy "done" until verification passes.

See **DEPLOYMENT_NOTES.md** (workspace root) for examples and script reference.

## 3. Workflow overview

1. **Test locally first** — Ensure the page is free from errors (JS and other) on localhost before deploying remotely (§4).
2. **Deploy remotely** — Upload using project deploy tools with the confirmed FTP target (§5).
3. **Verify remote** — Run remote verification; if it fails, diagnose and fix (§6).
4. **Fix until working** — Use fix-toronto-events, fix-nav-menu, and project .MD docs; inspect manually until the remote site works (§6).

Events must still load properly with no JavaScript syntax errors after deploy.

## 4. Test locally first (required)

Before deploying to the remote site:

1. **Start local server:**
   ```bash
   python tools/serve_local.py
   ```
   Serves at **http://localhost:9000** with correct MIME for `/next/_next/` (critical for events).

2. **Run local verification:**
   ```bash
   npm run verify:local
   ```
   Playwright runs against localhost: events grid, filter UI, no SyntaxError/ChunkLoadError, chunk returns real JS.

3. **If local fails:**
   - **Events not loading, SyntaxError, skeleton only, no filter bar** → Use **fix-toronto-events** (read `.cursor/skills/fix-toronto-events/SKILL.md` and reference); fix then re-run `npm run verify:local`.
   - **Nav menu wrong (links, labels, structure)** → Use **fix-nav-menu** (read `.cursor/skills/fix-nav-menu/SKILL.md`); do not change asset URLs; re-run local verification.

**Do not proceed to remote deploy until local verification passes.**

## 5. Deploy remotely

With credentials set and `FTP_REMOTE_PATH` clarified (or default):

```bash
python tools/deploy_to_ftp.py
```

This uploads to `FTP_REMOTE_PATH`: index.html, .htaccess, events.json, next/_next/ (and FavCreators to /fc/ as applicable). Other tools (e.g. deploy_htaccess.py, upload_next_htaccess.py) may be needed for specific fixes; see fix-toronto-events and project .MD docs.

**Deploy to both locations if the host serves from a subdir:** FTP root and **findtorontoevents.ca/** (or the subdir the host uses)—same set: index.html, .htaccess, chunks, events.json. See fix-toronto-events skill §7 "Deploy to both locations."

## 6. Verify remote and fix until working

After deploy:

```bash
npm run verify:remote
```

- **PASS:** Report "Remote verification passed. Events load, no JS errors."
- **FAIL:** Diagnose and fix:
  1. **Events not loading, SyntaxError, no filter bar, chunk 404/blocked** → Use **fix-toronto-events**. Read `.cursor/skills/fix-toronto-events/SKILL.md` and reference.md; apply fix steps (paths, chunks, ModSecurity, events.json, chunk syntax). Redeploy affected files, then re-run `npm run verify:remote`.
  2. **Nav menu wrong** → Use **fix-nav-menu**. Edit only nav block; sync chunk via patch_nav_js.py if needed; redeploy chunk and index; re-verify.
  3. **Other** → Check project Fix docs: **FIX_SUMMARY.md**, **INDEX_BROKEN_FIX.md**, **DEPLOYMENT_FIX_FAVCREATORS.md**, **FIX_STATUS.md** (workspace root). Inspect manually (View Source, Network tab, chunk URL 200 + JS body) and apply fixes; redeploy and re-verify.

Repeat until remote verification passes. Events must load with no JS syntax errors.

## 7. Worst case: events still not loading

If events still do not load after applying fix-toronto-events, fix-nav-menu, and project .MD fixes:

- **Sister project:** Refer to **E:\findtorontoevents.ca** (slightly outdated but working events).
- Compare: index.html (chunk URLs, base path, events fetch), `next/_next/static/chunks/`, events.json location, serve_local behavior. Port any working pattern back into this project, re-test locally, then redeploy and verify remote.

## 8. Checklist before "done"

- [ ] FTP target clarified (site + directory); credentials checked (env vars, no hardcoding).
- [ ] **No partial deploy:** dependencies of the page/asset identified; full set deployed (see §2.5, DEPLOYMENT_NOTES.md).
- [ ] Local: `python tools/serve_local.py`; `npm run verify:local` **passed** (events load, no JS errors).
- [ ] Remote deploy: `python tools/deploy_to_ftp.py` (or e.g. `deploy_index4.py` for index4 + deps); all dependencies included.
- [ ] **Post-deploy verification:** `npm run verify:remote` **passed** (or manual check: page loads, no 404s, no console errors).
- [ ] Events loading on remote with no JavaScript syntax errors.
- [ ] If events or nav were fixed: fix-toronto-events / fix-nav-menu rules followed; asset URLs unchanged.

## 9. Files and references

- **No partial deployments:** `DEPLOYMENT_NOTES.md` (root) — dependency check, full set deploy, verify after.
- **FTP rule:** `.cursor/rules/ftp-credentials.mdc`
- **Deploy:** `tools/deploy_to_ftp.py` (main site); `tools/deploy_index4.py` (index4 + all deps)
- **Local server:** `tools/serve_local.py`
- **Local verify:** `npm run verify:local` (events-loading.spec.ts, tests/no_js_errors.spec.ts)
- **Remote verify:** `npm run verify:remote` (tools/verify_remote_site.js)
- **Skills:** fix-toronto-events, fix-nav-menu, verify-remote-site, deploy-and-fix-local
- **Fix docs (root):** FIX_SUMMARY.md, INDEX_BROKEN_FIX.md, DEPLOYMENT_FIX_FAVCREATORS.md, FIX_STATUS.md
- **Reference:** [reference.md](reference.md) in this skill
- **Sister project (working events):** E:\findtorontoevents.ca
