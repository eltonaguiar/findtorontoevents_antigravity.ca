# PHP 5.2 gate for MOVIESHOWS3, plus four auth/preflight fixes (2026-11-26)

## Why

50webs (`findtorontoevents.ca`) runs **PHP 5.2.17** and the MOVIESHOWS3 scripts call
`error_reporting(0)` / `ini_set('display_errors','0')`. A construct from a newer PHP
therefore does not raise an error anyone can see — the request dies as an **empty
HTTP 500**. A single `http_response_code()` call cost three deploy cycles to find
(see `updates/2026-11-26-movieshows3-refresh-green.md`).

## Audit result

Nine PHP files ship from `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/`. Four used
`http_response_code()`, all in auth or CORS-preflight branches:

| File | Line | Version needed | Effect on 50webs |
|---|---|---|---|
| `api/add-movies-batch.php` | 20 | 5.4 (403) | auth failure returned an empty 500 instead of JSON |
| `api/check-session.php` | 11 | 5.4 (204) | every OPTIONS preflight failed |
| `api/get-movies.php` | 18 | 5.4 (204) | OPTIONS preflight failed (GET still worked) |
| `log/api_status.php` | 17 | 5.4 (204) | OPTIONS preflight failed (GET still worked) |

No short arrays, `??`, closures, traits, arrow functions or 7.x/8.x syntax were found.
`api/db-config.php` and `api/tmdb-ratings.php` were clean.

## Changes

1. **`tools/php52_compat_lint.py`** — scans a tree for constructs newer than 5.2 with a
   curated rule list, strips comments first (so prose like "no ?? operator" is not a
   false positive), honours a `// php52-allow:` escape hatch, and exits non-zero on any
   finding. `http_response_code()` is accepted when the file guards it with
   `function_exists('http_response_code')`.
2. **`tests/test_php52_compat_lint.py`** — 7 tests, including `test_repository_tree_is_clean`,
   which fails the build if the shipped tree ever regresses.
3. **`.github/workflows/php52-compat-lint.yml`** — runs the scan and the tests on PRs and
   pushes that touch `MOVIESHOWS3/**/*.php`.
4. **The four PHP fixes** — guard the call and also send the raw status line, so the same
   file behaves correctly on 5.2 and on 7+/8:
   ```php
   if (function_exists('http_response_code')) { http_response_code(403); }
   header('HTTP/1.1 403 Forbidden');
   ```

## Verification

- `python3 tools/php52_compat_lint.py` → `9 file(s) scanned, 0 finding(s)`.
- `python3 -m pytest tests/test_php52_compat_lint.py -q` → 7 passed.
- `php -l` clean on all four edited files.
- Before the fix the same scan reported exactly those four findings.
