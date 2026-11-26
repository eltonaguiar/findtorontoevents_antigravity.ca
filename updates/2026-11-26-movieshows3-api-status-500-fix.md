# MOVIESHOWS3 `log/api_status.php` HTTP 500 — root cause and fix (2026-11-26)

## What was broken

`https://findtorontoevents.ca/MOVIESHOWS3/log/api_status.php` and the same path on
`https://torontoevent.net` both returned **HTTP 500** with a body like:

```json
{"success":false,"error":"SQLSTATE[28000] [1045] Access denied for user
 'ejaguiar1_tvmoviestrailers'@'localhost' (using password: YES)","timestamp":"..."}
```

This broke the movie database refresh: `tools/run_movies_refresh.py` calls
`api_status.php` first to take a pre-refresh snapshot, so `kimi-fetch-movies.yml` and
`fetch-movies.yml` aborted before doing any TMDB work. They failed on cloud runners too —
it was never a runner problem.

## Why it was deployment drift, not a code or DB fault

- `/MOVIESHOWS3/api/get-movies.php` returned **200** with 7,427 rows, and
  `/MOVIESHOWS3/log/pull_log.json` returned **200** — the database and the shared
  credentials were healthy.
- Both scripts include the same `MOVIESHOWS3/api/db-config.php`. Its `getDbConnection()`
  catches the `PDOException` and returns `null`, so `api_status.php` can only print
  `{"error":"DB connection failed"}` on a bad login — it cannot emit a raw SQLSTATE.
- The live response was a raw SQLSTATE, which only the `catch (Exception $e)` block
  (echoing `$e->getMessage()`) can produce.
- Direct confirmation: the live file was **2,068 bytes** while the repo copy is
  **3,044 bytes** — a different, older file was deployed.

So an old copy of `api_status.php` that built PDO inline with stale credentials had been
sitting on the host.

## What changed

1. `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/log/api_status.php`
   - The catch block no longer returns `$e->getMessage()` to the caller. It logs the
     detail with `error_log()` and returns a generic `Database query failed`.
   - Reason: the raw message leaked the SQLSTATE and the database user name to any
     public caller.
2. `.github/workflows/deploy-movieshows3-hotfix.yml`
   - Added `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/log/api_status.php` to **both** deploy
     lists (50webs → `findtorontoevents.ca/MOVIESHOWS3/log`, GoDaddy →
     `MOVIESHOWS3/log`). The workflow previously shipped only `index.html`, `.htaccess`
     and the `api/` files, which is why the stale log file was never replaced.

## How it was verified

- `php -l` on the edited file: no syntax errors.
- The workflow YAML parses (`yaml.safe_load`).
- Deployed to 50webs via FTP (backup of the old file kept at
  `/tmp/rollback_api_status/50webs.php` before overwrite):
  `https://findtorontoevents.ca/MOVIESHOWS3/log/api_status.php` → **HTTP 200**,
  `{"success":true,"total_records":8147,...}`.
- `torontoevent.net` still returned 500 afterwards: its FTP account (GoDaddy) rejected
  every stored credential pair, so it is deployed through the workflow's GitHub secrets
  instead of locally.

## Follow-up

- After this workflow is dispatched, `/MOVIESHOWS3/log/api_status.php` on both hosts is
  replaced by the repo version. Re-run `kimi-fetch-movies.yml` to confirm the refresh
  completes.
