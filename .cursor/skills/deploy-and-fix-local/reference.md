# Deploy and Fix Local — Reference

## Commands

| Command | Purpose |
|--------|--------|
| `python tools/serve_local.py` | Start local server at http://localhost:9000 (correct MIME for chunks). |
| `npm run verify:local` | Run full local verification (events + no JS errors) with Playwright; starts server if needed. |
| `npx playwright test events-loading.spec.ts` | Events loading and filter UI tests only. |
| `npx playwright test tests/no_js_errors.spec.ts` | No JS errors + chunk returns real JS. |

## Environment

- **BASE_URL** — Override base URL for tests (default http://localhost:9000).
- **CI** — When set, Playwright does not reuse an existing server.
- FTP vars — For deploy to server; see `.cursor/rules/ftp-credentials.mdc`. Not used by local verification.

## Local verification checks (Playwright)

1. **Events loading:** Page loads, `#events-grid` visible, event cards (links) in grid, filter UI (GLOBAL FEED or search placeholder).
2. **No critical JS errors:** No SyntaxError, Unexpected token, ChunkLoadError, "denied by modsecurity", uncaught ReferenceError/TypeError. Main chunk (`/next/_next/static/chunks/a2ac3a6616d60872.js`) returns 200 and body starts with `(globalThis.TURBOPACK...`.
3. Hydration mismatch (React #418) is ignored in no_js_errors spec.

## When to use other skills

| If | Use |
|----|-----|
| Events not loading, SyntaxError, skeleton only, no filter bar | **fix-toronto-events** |
| Nav menu links/labels/structure wrong | **fix-nav-menu** |
| After deploy: verify live site | **verify-remote-site** |

## Known issue

**Nav menu changes** can break Toronto Events loading (e.g. chunk syntax after patch, or accidental asset URL change). After any nav edit, run `npm run verify:local`; if events fail, apply fix-toronto-events then re-check nav.

## Worst case

If events still do not load after fixes: compare with sister project **E:\findtorontoevents.ca** (working events). Align index.html chunk URLs, events.json path, and chunk syntax; re-test locally.
