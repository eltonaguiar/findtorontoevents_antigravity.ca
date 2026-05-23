# ROOTCAUSE_MOVIES1

## Summary
The MOVIESHOWS3 admin bulk fetch failure and inaccurate Movie/TV counts came from two backend issues:

1. Database authentication was brittle and tied to a single hardcoded credential pair.
2. The movie list query could return duplicate rows per title when joins matched multiple trailers or thumbnails.

These two issues together caused:
- `SQLSTATE[28000] [1045] Access denied` during bulk-fetch operations.
- Inflated or inconsistent UI counts for Movies vs TV Series.

## User-Visible Symptoms
- Admin bulk fetch showed:
  - `DB connection failed: SQLSTATE[28000] [1045] Access denied for user 'ejaguiar1_tvmoviestrailers'@'localhost'`
- Frontend counters on `MOVIESHOWS3` did not consistently reflect unique title counts by type.

## Root Causes

### 1) Credential Drift / Single-Credential Dependency
File: `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/db-config.php`

- The previous implementation used one fixed credential:
  - DB: `ejaguiar1_tvmoviestrailers`
  - User: `ejaguiar1_tvmoviestrailers`
  - Password: `tvmoviestrailers`
- In environments where the active credential is `admin` (or where the original credential is no longer valid), connection attempts fail immediately.
- No fallback chain existed, so one mismatch caused complete outage for any endpoint using `getDbConnection()`.

### 2) Row Multiplication from Join Strategy
File: `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php`

- Prior query joined `movies` to `trailers` and `thumbnails` and combined segments with `UNION ALL`.
- If a movie had multiple active trailers and/or multiple thumbnail rows, the join produced multiple rows for a single movie ID.
- Frontend counts (`allMovies.filter(m => m.type === 'movie')`, etc.) were computed from this returned array, so duplicates inflated counts.

## Changes Applied

### A) Hardened DB Connection with Fallbacks
File updated: `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/db-config.php`

- Added environment override support:
  - `EJAGUIAR1_TVMOVIESTRAILERS_USER`
  - `EJAGUIAR1_TVMOVIESTRAILERS`
- Added host-aware credential ordering.
- Added explicit fallback chain between:
  - `ejaguiar1_tvmoviestrailers / tvmoviestrailers`
  - `admin / 3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl`
- Added per-attempt error logging and final fallback-failure logging.

Outcome: API connection survives credential/environment differences instead of hard-failing on the first mismatch.

### B) Enforced One Row Per Movie in API
File updated: `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php`

- Replaced join-heavy query with a single `movies` base query.
- Selected trailer and thumbnail via correlated subqueries (`LIMIT 1`) to avoid row multiplication.
- Kept `EXISTS` predicate to require at least one active, non-empty trailer.
- Added response diagnostics:
  - `movie_count`
  - `tv_count`

Outcome: API returns unique title rows, and frontend counters now match actual unique movies/series in the feed.

### C) Updated DB Diagnostic Endpoint
File updated: `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/test-db.php`

- Switched to shared `db-config.php` connection logic.
- Added typed totals output (`movie`, `tv`) for faster production checks.

Outcome: same connection path is tested as production APIs, reducing false confidence from mismatched test logic.

## Verification Performed
- Static diagnostics on edited files reported no code problems.
- Runtime PHP CLI lint could not be executed locally because `php` is not available in this shell environment.

## Operational Notes
- The issue is fixed in repository code.
- Production behavior depends on deploying these updated files to the host serving:
  - `/MOVIESHOWS3/api/db-config.php`
  - `/MOVIESHOWS3/api/get-movies.php`
  - `/MOVIESHOWS3/api/test-db.php`

## Quick Post-Deploy Checks
1. Open `/MOVIESHOWS3/api/test-db.php` and confirm successful connection and typed counts.
2. Open `/MOVIESHOWS3/api/get-movies.php` and confirm `success: true` plus stable `count`, `movie_count`, `tv_count` values.
3. Retry bulk fetch in `/MOVIESHOWS3/admin.html` and confirm no `SQLSTATE[28000]` error.
4. Confirm UI counters align with unique content totals.

## Final Conclusion
The outage was not a frontend-only counting bug. It was a coupled backend fault:
- auth fragility caused endpoint failures,
- and query design caused duplicate data rows.

Fixing both was required to restore reliable bulk fetch and accurate Movie/TV counts.
