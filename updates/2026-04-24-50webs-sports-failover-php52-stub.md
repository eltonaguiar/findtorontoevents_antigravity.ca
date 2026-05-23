# 50webs: stop deploying PHP-7 sports failover; PHP-5.2 stubs (2026-04-24)

## Problem

- **findtorontoevents.ca (50webs)** reports **PHP 5.2.17** for `live-monitor/api/`.
- **`sports_failover_proxy.php`** (merged via **#342**) uses **PHP 7+** (`??`) and **PHP 5.4+** (short `[]`, closures). On 5.2 it fails at parse time (e.g. `unexpected '?'` on line 22) — any direct HTTP hit returns a **white-screen** parse error.
- **torontoevent.net (GoDaddy)** runs **PHP 8.3+**; the same file works there.

The deploy workflow was uploading **all** `live-monitor/api/*.php` to **both** hosts, so 50webs received a file its runtime could not load.

## Change

File: [`.github/workflows/torontoevent-deploy-live-monitor.yml`](../.github/workflows/torontoevent-deploy-live-monitor.yml), step **“Deploy live-monitor/api/ to findtorontoevents.ca (50webs)”**

1. **Skip** in the 50webs loop: `sports_failover_proxy.php`, `sports_failover_config.php` (repo copies require PHP 5.4+ / 7+).
2. **Upload generated stubs** to the same paths:
   - `sports_failover_proxy.php` — minimal PHP 5.2: `header('HTTP/1.1 503 Service Unavailable')` + `json_encode` + message pointing to `https://torontoevent.net/.../sports_failover_proxy.php`. **503** makes `sports-failover.js` reject tier 1 so **tier 2 (direct APIs)** runs; 200+`{ok:false}` would incorrectly be treated as success by older JS.
   - `sports_failover_config.php` — `<?php $FAILOVER_CHAINS = array();` only (nothing on 50webs `require_once`s it except the old proxy; the stub proxy does not load the config).
3. **Client:** `sports-failover.js` rejects tier 1 when the JSON body has `ok: false` (defense in depth for any 200+error response).

The **first** deploy step (torontoevent.net) is unchanged: full repo PHP files, including the real proxy and config.

## What we did *not* do

- No rewrite of `sports_failover_proxy.php` to PHP 5.2 in-tree (option 2); the canonical implementation stays on PHP 8.
- No separate `*_guard.php` entrypoint (option 3); the stub is enough.

## Verification (after the workflow runs on `main`)

- `https://findtorontoevents.ca/live-monitor/api/sports_failover_proxy.php` — HTTP 200, JSON, `ok: false` and an `error` string (no parse error).
- `https://torontoevent.net/live-monitor/api/sports_failover_proxy.php?...` — still runs the real proxy (e.g. missing `sport` → structured JSON as before).

## Related docs

- [2026-04-23-sports-failover-deploy.md](2026-04-23-sports-failover-deploy.md) — corrected: there is no valid GitHub “issue/PR #350” for the ESPN follow-up; open a new issue when scoped.
- [2026-04-23-sports-secret-audit.md](2026-04-23-sports-secret-audit.md) — 50webs runtime note updated to “fixed by stub + skip”.
