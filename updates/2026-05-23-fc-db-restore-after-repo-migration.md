# FavCreators DB restore after repo migration (2026-05-23)

## What was broken

After porting/restoring the repo to a single `main` branch, `https://findtorontoevents.ca/fc/#/guest` showed:

> Database: Not connected — Database connection failed: Access denied for user 'ejaguiar1_favcreators'@'localhost' (using password: YES)

`/fc/api/status.php` returned the same access-denied error. `/fc/api/db_test.php` also had PHP 5.2 parse errors (`?:` and `[]`).

Several GitHub Actions workflows failed with the same class of problem for `ejaguiar1_stocks` (wrong/missing `MYSQL_PASSWORD` secret).

## Root cause

1. **Server:** `/fc/api/.env` was missing after the migration — no deployed MySQL password for FavCreators.
2. **Diagnostics:** `db_test.php` used PHP 5.3+ syntax incompatible with production PHP 5.2.17.
3. **CI:** GitHub secrets (`MYSQL_PASSWORD`, `FINDTORONTOEVENTS_DB_CREDENTIALS`, etc.) did not match passwords in `/home/eaguiar2015/dbpasses.txt`.

## What changed

1. Deployed `findtorontoevents.ca/fc/api/.env` via FTP with credentials from `dbpasses.txt` (`favcreators1234560`).
2. Fixed `favcreators/docs/api/db_test.php` for PHP 5.2 (`?:` → full ternary, `[]` → `array()`).
3. Updated GitHub secrets from `dbpasses.txt` (via `printf`, **no trailing newline** — `echo` breaks MySQL auth):
   - `FINDTORONTOEVENTS_DB_CREDENTIALS` (all 10 DBs)
   - `MYSQL_PASSWORD` / `DB_PASS_STOCKS` → `stocks1234560`
   - `DB_PASSWORD` → `favcreators1234560`
   - `TORONTOEVENT_DB_PASS` → `events1234560`

## Verification

```bash
curl -sS https://findtorontoevents.ca/fc/api/status.php
# {"ok":true,"db":"connected",...}

curl -sS https://findtorontoevents.ca/fc/api/db_test.php
# {"ok":true,"connect_err":null,...}

curl -sS https://findtorontoevents.ca/fc/api/get_all_creators_with_accounts.php | head -c 80
# {"ok":true,"count":113,...}
```

Homepage, `/audit/`, and `/fc/` all return HTTP 200.

## Follow-ups (not blocking FC guest)

- **Deploy Rise of the Claw Dashboard:** GitHub Pages not enabled on repo (404).
- **Claude's Test - Portfolio Manager:** intermittent git push conflict during auto-commit.
- Re-run **MySQL Trading Picks Sync** after secret update to confirm stocks DB access from CI.
