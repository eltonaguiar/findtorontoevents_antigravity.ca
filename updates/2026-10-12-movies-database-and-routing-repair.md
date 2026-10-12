# Movies database, refresh, and version-one routing repair

## What was broken

- MovieShows2 and MovieShows3 used stale hardcoded database passwords on
  findtorontoevents.ca and tdotevent.ca. The supplied local credential succeeded
  against localhost, while the deployed password returned MySQL error 1045.
- The MovieShows3 refresh's embedded TMDB key returned HTTP 401 / TMDB error 7.
  The existing local TMDB environment credential returned HTTP 200.
- PHP 5.2.17 on 50webs does not support `__DIR__`. The MovieShows1 PHP wrapper
  therefore treated its existing HTML as missing and redirected to MovieShows2.
- The refresh log used `JSON_PRETTY_PRINT` and the two-argument `json_encode`
  interface, which are unavailable on PHP 5.2. The failed initial refresh left an
  empty log instead of a usable record.

## Changes

- Both movie database configs now use paired
  `EJAGUIAR1_TVMOVIESTRAILERS_USER` / `EJAGUIAR1_TVMOVIESTRAILERS_PASS`
  environment settings first, then host-local private configuration.
- Private configuration can live at `movies-db-private.php` outside the web
  root. 50webs' virtual FTP root does not map to the PHP filesystem parent, so
  the deployed installation uses `.movies-db-private/credentials.php` in each
  domain, protected by `.htaccess` containing `Deny from all`. HTTP denial was
  verified before credentials were uploaded, and the files have mode 0600.
- No replacement passwords or API keys are written to Git. Both private
  credential locations are ignored. The private PHP file returns an array with
  `username`, `password`, and `tmdb_api_key`.
- The refresh uses `TMDB_API_KEY` from PHP's environment or the private file.
  Missing credentials and connection failures are explicitly logged without
  printing secrets.
- MovieShows2's DB diagnostic now uses the same configuration rather than
  retrying stale credentials. Deployment preserves private credential files,
  ships the directory denial rule, and checks actual populated API payloads
  instead of treating a landing-page HTTP 200 as database health.
- The refresh log uses the PHP-5.2-compatible JSON call when pretty printing is
  unavailable and reports persistence failures explicitly.
- MovieShows1 uses `dirname(__FILE__)`, restoring its own original app at
  `/MOVIESHOWS/` without replacing its HTML or bundled assets.

## Verification

- `PHP_BINARY=<session PHP CLI> python3 -m pytest tests/test_movies_db_config.py tests/test_movies_legacy_wrapper.py -q`:
  **29 passed**. Credential tests cover priority, incomplete environment
  settings, invalid/missing private settings, protected-directory loading,
  secret-safe connection errors, TMDB credentials, and legacy JSON logging.
  Wrapper tests cover the PHP-5.2-compatible path and HTML/toast injection.
- PHP CLI `-n -l` checks passed for the edited database configs, diagnostic,
  refresh, and MovieShows1 wrapper. The deployment YAML parsed and its embedded
  Python scripts compiled.
- All four MovieShows2/MovieShows3 APIs on the two 50webs domains returned HTTP
  200, `success: true`, and 4,848 playable titles before refresh.
- Both private directory access checks returned HTTP 403. All temporary
  diagnostic probes were removed; initial credential probes were additionally
  checked for HTTP 404 after deletion.
- Both MovieShows1 domain-root routes now return HTTP 200 at their own URL with
  the original `/MOVIESHOWS/_next/` assets and injected upgrade toast, rather
  than an HTTP 302 to MovieShows2.
- After refresh, all four APIs returned **4,904 playable titles**. HTTP access
  to both `credentials.php` and the directory's `.htaccess` returned 403 on
  both domains. A browser check of MovieShows1 retained its own URL and found
  nine original Next.js script assets plus the upgrade-toast script.

## Database refresh

The existing authenticated MovieShows3 importer ran once successfully with
`type=both`, `pages=3`, `mode=trending`. It did not reset or rebuild the DB.

| Measurement | Before | After |
|---|---:|---:|
| Total titles | 7,841 | 7,899 |
| Movies | 4,074 | 4,107 |
| TV shows | 3,767 | 3,792 |
| Active, nonempty trailers | 7,173 | 7,229 |

TMDB returned 120 candidates: 33 movies and 25 TV shows were added, 62 existing
entries were skipped, and there were zero errors. The persisted pull log
records success at 2026-10-12 02:49:10 server time. The last movie insertion
advanced from 2026-04-13 to that timestamp.

## Routing history and remaining scope

- The original MovieShows1 HTML still exists. MovieShows2 shares the original
  base Next.js app but adds its database/UI enhancements; MovieShows3 is a
  separate implementation. These were not replaced with one site during this
  repair.
- The surviving February backup history shows the MovieShows2 enterprise
  landing first linked to MovieShows1, then to `play.html` on February 3.
  By February 11, its index had become the current `app.html` redirect.
  `index_enterprise_landing.html` still exists live, but is a marketing/demo
  page, not an independently verified alternative Film Vault app.
- The main repository's May 23 history reset limits earlier history. Evidence
  came from the retained `findtorontoevents_antigravity.ca_FEB162026backup`
  repository and `MOVIESHOWS2_CURSORNOSCROLLINGBUG` source overview.
- GoDaddy/torontoevent.net is a separate database host. The initial existing
  credentials failed with 1045. The user subsequently added an explicitly
  labeled GoDaddy movies section to the local credential file; that new
  credential succeeded against localhost with 7,841 movies and 7,234 trailers.
  It was installed as mode-0600 private configuration outside `public_html`,
  and both movie APIs were repaired. The same source and display fixes were
  deployed there. Its separate refresh added 33 movies and 27 TV shows,
  skipped 60 duplicates, and completed with zero errors: **7,901 total titles**.
  No GoDaddy password or TMDB key was committed.
- The legacy `imdb_rating` DB field is populated by TMDB `vote_average` in
  the importer; its name does not establish independently verified IMDb data.
  The uniform-10.0 display report is being investigated separately.

## Operational follow-up

Merge only the listed repair files and tests, together with this document.
The shared worktree contains unrelated edits and commits; no broad staging,
reset, or push is appropriate. Deployments from older repository revisions
can restore stale config files until the repair is merged.
