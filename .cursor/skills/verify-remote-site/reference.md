# Verify Remote Site — Reference

## Commands

| Command | Purpose |
|--------|--------|
| `npm run verify:remote` | Full verification (Playwright then HTTP fallback). |
| `npm run verify:remote:fallback` | HTTP-only checks (no Playwright). |
| `npm run verify:remote:playwright` | Playwright only; set `VERIFY_REMOTE=1` first on Windows. |
| `npm run compare:local-vs-remote` | Cross-compare local vs remote (when local passed, ready to deploy). |

## Environment

- `VERIFY_REMOTE_URL` — Base URL (default https://findtorontoevents.ca).
- `VERIFY_REMOTE` — Set by runner to skip local webServer when running remote spec.
- FTP vars — Not used by verification; see ftp-credentials for deploy.

## Root cause (FavCreators 500)

Path segment **"favcreators"** on the host triggers server-side handling that returns 500. We deploy the app under **/fc/** instead; nav links use **/fc/#/guest**.

## Checks (Playwright)

1. Homepage 200
2. Events grid visible (after React load)
3. Events count > 0 (cards or "N EVENTS FOUND")
4. Filter UI (GLOBAL FEED or search bar)
5. No critical JS errors
6. Main chunk returns JS (not HTML/ModSecurity)
7. Quick Nav opens, FavCreators link present (href contains **fc**, points to /fc/#/guest)

## Checks (fallback)

1. Index 200, HTML has `#events-grid` and chunk refs
2. Chunk 200, body is JS
3. events.json 200, valid JSON, non-empty events
