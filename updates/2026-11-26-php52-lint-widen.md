# PHP 5.2 gate widened to every 50webs tree (2026-11-26)

## Why

The first version of the gate only watched `MOVIESHOWS3/`. But 50webs serves
**PHP 5.2.17 for the whole host** — `x-powered-by: PHP/5.2.17` on
`/MOVIESHOWS3/log/api_status.php` *and* on `/fc/events-api/setup_tables.php` — and
there are no per-directory PHP handlers (`.htaccess` scan). Any PHP that deploys
there can hit the same silent empty HTTP 500.

## What deploys to 50webs

| Local tree | Remote path | Files |
|---|---|---|
| `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3` | `findtorontoevents.ca/MOVIESHOWS3` | 10 |
| `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2` | `findtorontoevents.ca/movieshows2` | 6 |
| `favcreators/docs` | `findtorontoevents.ca/fc` | 90 |

(`tools/deploy_movieshows2.py` REMOTE_BASE and `tools/deploy_to_ftp.py`, which
uploads `favcreators/docs` as `/fc/`.)

## Changes

1. **`MOVIESHOWS2`: 2 real hits fixed** — `api/get-movies.php:15` and
   `api/movies.php:16` called `http_response_code(204)` for OPTIONS preflight.
   Both now use the guarded form plus the raw status line, matching MOVIESHOWS3.
   `php -l` clean on both.
2. **The scanner is now string-aware.** Stripping comments alone left a false
   positive class: markdown like `'**Note:** ...'` inside a PHP string tripped the
   power-operator rule. 30 of the 67 reported `/fc` hits were exactly that. String
   literals are blanked now, keeping byte offsets and line numbers intact.
   The `function_exists('http_response_code')` guard is consequently matched
   against the **raw** source, since the guard text itself lives in a string.
3. **Baselines.** `tools/php52_baseline.json` records per-file/per-rule counts of
   accepted violations; only findings beyond those counts fail the build. `--write-baseline`
   regenerates it. This lets the gate cover `/fc` today instead of after a
   90-file rewrite. The `/fc` tree has **27 hits across 13 file/rule keys**
   (short arrays, `??`, closures, `http_response_code`) — real work, not blocking.
4. **Workflow** now covers all three trees and the baseline file, both on PR and
   on push to main.

## Verification

- `python3 tools/php52_compat_lint.py` → `105 file(s) scanned, 0 new finding(s), 27 baselined`, exit 0.
- Without the baseline the same scan reports 27 (was 67 before string-awareness).
- `python3 -m pytest tests/test_php52_compat_lint.py -q` → **11 passed**, including
  `test_movieshows_trees_are_clean`, `test_full_repository_scan_passes_with_baseline`,
  `test_strings_are_not_code`, and a pair of tests proving the baseline suppresses
  known findings but still fails on a new one in the same file.

## Follow-up audit: deployed vs repo

`tools/php52_drift_check.py` byte-compares every deployed `.php` on 50webs against
the repo. Result: **94 identical, 3 drifted, 209 live-only orphans, 3 repo-only** —
all of the drift is in `movieshows2/api` (`db-config.php`, `movies.php`,
`sync-providers.php`) and `movieshows2/api/get-movies.php` is **not deployed at
all**, so that PHP 5.2 fix lives only in git. Full report:
`reports/50webs_php_drift_2026-11-26.md`.
