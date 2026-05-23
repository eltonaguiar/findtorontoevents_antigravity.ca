---
name: deploy-and-fix-local
description: Deploy changes and test locally on localhost with Node/Playwright—ensure page is free from JS and other errors; events must load. Use fix-toronto-events if events fail, fix-nav-menu if nav needs fixing; worst case refer to sister project E:\findtorontoevents.ca.
---

# Deploy and Fix Local

Use this skill when the user asks to **deploy and test locally**, **run local verification**, **ensure the page has no JavaScript errors after changes**, or **verify Toronto Events load on localhost** before or after deploying.

**Known issue:** After changes—especially to the **nav menu**—Toronto Events may stop loading properly on the page. Follow the fix steps below and use the referenced skills if needed.

## 1. Workflow overview

1. **Deploy** (if deploying to server: use FTP/env vars; see `.cursor/rules/ftp-credentials.mdc`). For local-only testing, "deploy" means having your latest files saved in the project.
2. **Start the local server** with the correct tool (see §2).
3. **Run Playwright tests** against localhost to confirm: page loads, no JS errors, events load, filter UI visible (§3).
4. **If events or nav fail:** Apply fix-toronto-events or fix-nav-menu (§4). Re-test locally.

## 2. Local server (required)

**Always use:**

```bash
python tools/serve_local.py
```

- Serves at **http://localhost:9000** (and http://127.0.0.1:9000).
- Sets correct MIME for `/next/_next/` (`.js` → `application/javascript`, `.css` → `text/css`) so chunks are parsed as JS—critical for events and React.
- Handles proxy-style URLs if index uses them.

**Do not use** `python -m http.server`—it does not set MIME for `/next/_next/` and can serve PHP source for proxy URLs → SyntaxError → events never load.

Playwright can start the server for you when you run the local tests (§3); otherwise start it manually before testing.

## 3. Run local verification (Playwright)

From project root:

```bash
npm run verify:local
```

This runs Playwright against **http://localhost:9000** with the local webServer (`serve_local.py`) and executes:

- **Events loading:** page loads, events grid visible, event cards (links) present, filter/search UI (GLOBAL FEED or search bar), no critical JS errors (SyntaxError, Unexpected token).
- **No JS errors:** main chunk returns 200 and real JavaScript; console has no SyntaxError, ChunkLoadError, modsecurity, uncaught exceptions (hydration #418 is ignored).

**Alternative (individual specs):**

```bash
npx playwright test events-loading.spec.ts
npx playwright test tests/no_js_errors.spec.ts
```

**Result:**

- **PASS:** Report "Local verification passed. Events load, no JS errors."
- **FAIL:** Identify the first failing check (e.g. SyntaxError in a2ac chunk, no event cards, no filter bar). Then apply §4.

## 4. If events or nav are broken

| Symptom | Use this | Action |
|--------|----------|--------|
| **Events not loading,** skeleton only, no filter bar, **SyntaxError** in `a2ac3a6616d60872.js`, ChunkLoadError, or "denied by modsecurity" | **fix-toronto-events** | Read `.cursor/skills/fix-toronto-events/SKILL.md` and reference.md. Diagnose (Network tab, chunk URL 200 + JS body), then apply fix steps: correct index.html/chunk paths, serve_local.py, chunk syntax fix, events.json, etc. Re-run `npm run verify:local`. |
| **Nav menu** wrong (links, labels, structure, missing/extra items) | **fix-nav-menu** | Read `.cursor/skills/fix-nav-menu/SKILL.md`. Edit only the nav block in index.html; do not change asset URLs or add fallback scripts. Sync chunk via patch_nav_js.py if React renders those links. Re-run local verification. |

**Important:** Nav menu edits can **break events loading** (e.g. accidental change to asset URLs, or chunk syntax error after patching). After any nav change, always re-run local verification; if events fail, use **fix-toronto-events** first (e.g. Fix 1b for chunk syntax), then re-check nav.

## 5. Worst case: events still not loading

If events still do not load after applying fix-toronto-events and fix-nav-menu:

- **Sister project:** Refer to **E:\findtorontoevents.ca** (slightly outdated but with working events functionality).
- Compare: index.html (chunk URLs, base path, events fetch), chunk files under `next/_next/static/chunks/`, `events.json` location and content, and `serve_local.py` behavior. Port any working pattern (e.g. chunk URL shape, events.json path, or minimal nav structure) back into this project and re-test locally.

## 6. Checklist before considering "done"

- [ ] Local server: `python tools/serve_local.py` (or started by Playwright).
- [ ] `npm run verify:local` passes (events load, no JS errors).
- [ ] If you had to fix events: fix-toronto-events steps applied and verified.
- [ ] If you had to fix nav: fix-nav-menu rules followed; asset URLs unchanged; verify:local still passes.
- [ ] Optional: run remote verification after deploying (`npm run verify:remote`) per verify-remote-site skill.

## 7. Files and references

- **Local server:** `tools/serve_local.py`
- **Local tests:** `events-loading.spec.ts`, `tests/no_js_errors.spec.ts`
- **Config:** `playwright.config.ts` (webServer = serve_local.py, baseURL = localhost:9000 for local runs)
- **Skills:** fix-toronto-events, fix-nav-menu, verify-remote-site
- **Reference:** [reference.md](reference.md) in this skill
- **Sister project (working events):** E:\findtorontoevents.ca
