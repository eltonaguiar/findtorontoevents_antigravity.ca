# Movies rating display: ten perfect scores on the initial MS2 feed

## Evidence and root cause

Investigated read-only on 2026-10-12. The reported symptom **reproduces on MOVIESHOWS2**, but is not a numeric parsing/clamping bug:

- Public `get-movies.php` on **both findtorontoevents.ca and tdotevent.ca**, for **both MOVIESHOWS2 and MOVIESHOWS3**, returned 4,904 trailer-bearing records, 83 distinct numeric ratings, range 0.0–10.0, **10 records at 10.0**, and 128 at 0.0. The library is not uniformly rated 10.
- MS2's API put those ten perfect-score records first. A fresh Chromium visit to `/MOVIESHOWS2/` redirected to `app.html` and rendered exactly ten `IMDb 10.0` badges. Titles matched the API's first ten, beginning with Firefly Wedding, Love You Teacher, and Born to Bowl.
- MS3's API and rendered page already showed varied scores. Its first ten API ratings were `7.8, 7.2, 7.7, 7.9, 7.0, 10.0, 7.0, 8.2, 8.2, 6.3`; its visible badges had 16 distinct values in the 20 collected badges. No MS3 HTML display fix was justified.

Exact **pre-change** source lines (quoted verbatim):

`TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/api/get-movies.php:47`

```php
        ORDER BY m.imdb_rating DESC, m.created_at DESC
```

`TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js:5192`

```js
        const initialMovies = filteredMovies.slice(0, 10);
```

These two operations select every perfect-score outlier as the initial feed. Ratings are preserved, not converted to 10:

`TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js:4034`

```js
            rating: String(m.imdb_rating || m.rating || ''),
```

A separate attribution error is at `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js:4285`:

```js
        const rating = movie.rating ? `IMDb ${movie.rating}` : "TBD";
```

The refresh stores **TMDB `vote_average`** in the legacy database column `m.imdb_rating`. That name does **not** establish independent IMDb verification.

### V1 static source

After the parent's PHP wrapper repair, a fresh `/MOVIESHOWS/` visit rendered 101 static rating badges with 18 distinct strings including TBD, and no 10.0. The original tracked `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS/index.html:1` contains, for example, the verbatim fragment `IMDb <!-- -->8.5`.

The public V1 bundle `/MOVIESHOWS/_next/static/chunks/691b76dbc7390d6f.js:1` contains data module **37448**, whose literal JSON starts `{"version":"1.0","updated":"2026-01-28","movies":`. Its 101 literal `rating` strings span 7.2–9.2 plus TBD. The renderer in `/MOVIESHOWS/_next/static/chunks/6d9ad93a5abfae37.js:1` consumes it through `var j=e.i(37448)` and `let S=(a=[...z.movies]`, and renders `children:["IMDb ",e.rating]`.

Thus V1 uses a bundled January static dataset, not the refreshed database. This investigation does not verify those static values against IMDb. **No V1 or hashed bundle changes were made.**

## Surgical changes

- MS2 `api/get-movies.php`: order the default discovery feed by `m.created_at DESC, m.id DESC`, as a newest-added library view rather than a perfect-score leaderboard.
- MS2 `api/movies.php`: add allowlisted, opt-in `sort=newest` to list pagination. Keep the existing rating-descending default for top-rated/category callers.
- MS2 `scroll-fix.js`: request that matching ordering for background pages; label database scores **TMDB**, and use generic **Rating** for unattributed static fallback records. Keep actual numeric values, including genuine 10.0, unchanged.
- Both MS2 and MS3 `api/get-movies.php`: add backwards-compatible response metadata `rating_source: "TMDB"` and `rating_scale: 10`. Existing per-movie `imdb_rating` remains the legacy compatibility key.
- Add `tests/test_movies_rating_display.js`: exercise the actual SQL against an in-memory SQLite fixture, actual JS mapper/badge expressions, provenance contract, pagination ordering, and actual slide DOM in Chromium.

The ratings agent did not alter database configuration, refresh scripts,
API-status logging, wrappers, `.htaccess`, hashed bundles, or generated
dashboard files. The deploy owner subsequently rebuilt the separate original
movie application for its release-countdown fix, preserved the four existing
MS2 enhancements, and bumped `app.html`'s scroll-fix cache key.

## Validation

- **Red:** `node --test tests/test_movies_rating_display.js` initially reported 1 pass / 3 expected failures: perfect-score-first ordering, false IMDb label, and missing source metadata. The pagination regression separately failed before its fix.
- **Green:** `node --test tests/test_movies_rating_display.js` — **6/6 passed**, including real slide DOM badges `TMDB 6.4`, `TMDB 7.2`, `TMDB 8.1`, `TMDB 10.0`, and `TBD`. The SQL fixture retains all ten original perfect-score records.
- `node --check TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js` — **passed**.
- Editor Problems check for the four edited production files and test — **no diagnostics**.
- Fresh Chromium production-page verification with **local request interception only** (patched JS and the live MS3 newest-ordered API data substituted for MS2's API) loaded all 4,904 records and rendered `TMDB 7.8, 7.2, 7.7, 7.9, 7.0, 10.0, 7.0, 8.2, 8.2, 6.3`. Badge values matched the public input exactly. All non-GET requests were blocked. **This was not a deployment.**
- `python3 tools/validate_php52.py TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/api/get-movies.php TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/api/movies.php TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php` — **failed on three pre-existing OPTIONS-path `http_response_code(204)` calls** at original lines 14, 15, and 17, respectively. None was introduced or changed by this patch. PHP CLI is unavailable, so native `php -l` was not run.

Reproduce the API distribution without writes:

```bash
curl -fsSL -A 'Mozilla/5.0' https://findtorontoevents.ca/MOVIESHOWS2/api/get-movies.php |
python3 -c 'import json,sys; d=json.load(sys.stdin); r=d["movies"]; v=[float(m["imdb_rating"]) for m in r if m.get("imdb_rating") is not None]; print("count",len(r),"range",min(v),max(v),"distinct",len(set(v)),"tens",v.count(10),"first10",[m.get("imdb_rating") for m in r[:10]])'
```

## Deployment and remaining questions

The deploy owner uploaded the **four production files together** over FTPS to
findtorontoevents.ca and tdotevent.ca. `movies.php` and `scroll-fix.js` agree on
newest ordering for background pages. Both live APIs returned `rating_source:
"TMDB"` with first-ten values `9.0, 6.3, 8.2, 8.2, 7.0, 10.0, 7.0, 7.9, 7.7,
7.2`. Native PHP CLI syntax checks passed for all three edited PHP APIs.

The deployed app now references `scroll-fix.js?v=20261012-ratings`. A fresh
browser visit without request interception rendered **TMDB 9.0, TMDB 6.3,
TMDB 8.2, TMDB 8.2, TMDB 7.0, TMDB 10.0, TMDB 7.0, TMDB 7.9, TMDB 7.7,
TMDB 7.2**. This is actual production verification, not a mocked preview.

Open data-quality questions: the API exposes no TMDB vote count, so the statistical strength of the ten 10.0 records cannot be assessed here; zero values may represent unrated titles. These are not grounds to fabricate replacement ratings. V1's independently unverified static dataset remains a separate freshness/attribution issue, and the pre-existing PHP 5.2 OPTIONS incompatibilities remain outside this rating patch.
