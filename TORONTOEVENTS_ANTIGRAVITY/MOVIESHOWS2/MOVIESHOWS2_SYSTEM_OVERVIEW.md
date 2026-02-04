# MovieShows2 - Movie/TV Database System Overview

> **For AI Coders:** This document describes the MovieShows2 subsystem to avoid conflicts.
> Last updated: 2026-02-04

---

## Architecture

The system uses a **MySQL database** on 50webs.com shared hosting, with PHP scripts deployed via FTP. A GitHub Actions workflow automates daily data pulls from TMDB (The Movie Database) API.

### Database

- **Host:** `localhost` (scripts run on the 50webs server)
- **Database:** `ejaguiar1_tvmoviestrailers`
- **User:** `ejaguiar1_tvmoviestrailers`
- **Password:** stored in GitHub secret `EJAGUIAR1_TVMOVIESTRAILERS`
- **Current size:** 4,278 titles (2,184 movies + 2,094 TV shows), 2,614 trailers

### Key Tables

| Table | Purpose |
|-------|---------|
| `movies` | Core content (title, type, genre, description, release_year, imdb_rating, imdb_id, **tmdb_id**, runtime) |
| `trailers` | YouTube trailer links (movie_id FK, **youtube_id**, title, priority, is_active) |
| `thumbnails` | Poster images (movie_id FK, url, is_primary) |
| `sync_log` | History of data pulls (sync_type, status, items_processed, error_message) |
| `content_sources` | Source tracking (movie_id FK, source, source_data JSON) |
| `user_queues` | User watchlists |
| `user_preferences` | User settings |
| `shared_playlists` / `playlist_items` | Shared playlists |

### Deduplication

- Movies/TV shows are deduplicated by `tmdb_id` (unique per TMDB entry)
- Trailers are deduplicated by `youtube_id` (no duplicate YouTube URLs)
- Both checks happen in-memory (pre-loaded sets) AND via DB query (race condition protection)

---

## Files Created (DO NOT MODIFY existing files)

All new files are under `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/`:

### PHP Scripts (deployed to FTP)

| File | URL | Purpose |
|------|-----|---------|
| `fetch_new_content.php` | `/movieshows2/fetch_new_content.php` | Main TMDB fetch script. Requires `?key=AUTH_KEY`. Supports `&type=`, `&pages=`, `&mode=` params |
| `admin_search.php` | `/movieshows2/admin_search.php` | Search TMDB API, cross-reference with local DB. Returns JSON with `in_database` flag |
| `admin_add_single.php` | `/movieshows2/admin_add_single.php` | Add a single title by TMDB ID. Requires `?key=AUTH_KEY&tmdb_id=N&type=movie|tv` |
| `admin_fetch_year.php` | `/movieshows2/admin_fetch_year.php` | Fetch content for a specific year. Requires `?key=AUTH_KEY&year=YYYY` |
| `log/index.php` | `/movieshows2/log/` | Sync log dashboard (HTML page showing stats, sync history, content by year) |
| `log/api_status.php` | `/movieshows2/log/api_status.php` | JSON API returning database stats, recent syncs, yearly breakdown |

### Frontend

| File | URL | Purpose |
|------|-----|---------|
| `admin.html` | `/movieshows2/admin.html` | Admin panel with 3 tabs: Search & Add, Year Analysis, Bulk Fetch |

### Tests

| File | Purpose |
|------|---------|
| `tests/movieshows2-admin.spec.js` | 38 Playwright tests (log page, API, admin UI, security, dedup) |
| `tests/playwright.config.js` | Playwright config for these tests |

### Deployment

| File | Purpose |
|------|---------|
| `tools/deploy_movieshows2.py` | FTP deployment script for movieshows2 files only |
| `.github/workflows/fetch-movies.yml` | GitHub Actions: daily TMDB fetch at 6:00 AM UTC |

---

## API Keys & Secrets

| Key | Source | Used In |
|-----|--------|---------|
| TMDB API Key | `b84ff7bfe35ffad8779b77bcbbda317f` | fetch_new_content.php, admin_search.php, admin_add_single.php, admin_fetch_year.php |
| TMDB Read Token | Bearer token (JWT) | Same scripts (Authorization header for curl requests) |
| Auth Key | `ms2_sync_2024_findto` | Required query param `?key=` for write operations |

### GitHub Secrets Required

| Secret | Value |
|--------|-------|
| `FTP_HOST` | `ftps2.50webs.com` |
| `FTP_USER` | `ejaguiar1` |
| `FTP_PASS` | FTP password from `.env` |
| `EJAGUIAR1_TVMOVIESTRAILERS` | Database password |

---

## PHP Compatibility Notes

The 50webs hosting runs an **older PHP version** (pre-5.4). Key constraints:

- **DO NOT** use `http_response_code()` - use `header('HTTP/1.1 403 Forbidden')` instead
- **DO NOT** use short array syntax `[]` - use `array()` instead
- **DO NOT** use `finally` blocks
- Use `curl` (CURLOPT_*) for HTTP requests, not `file_get_contents` with stream contexts
- SSL verification must be disabled (`CURLOPT_SSL_VERIFYPEER => false`)

---

## Workflow: How Data Gets Fetched

1. GitHub Actions triggers `fetch-movies.yml` (daily or manual)
2. Workflow runs `tools/deploy_movieshows2.py` to upload latest PHP scripts via FTP
3. Workflow calls `fetch_new_content.php?key=AUTH_KEY&type=both&pages=3&mode=trending` via curl
4. PHP script:
   - Connects to MySQL database
   - Pre-loads all existing `tmdb_id`s and `youtube_id`s into memory
   - Fetches trending/discover content from TMDB API
   - Skips any item whose `tmdb_id` already exists (dedup)
   - Inserts new movies/TV shows with trailers and thumbnails
   - Logs results to `sync_log` table
5. Workflow calls `log/api_status.php` to verify the database state

---

## Admin Panel Features

### Tab 1: Search & Add
- Search bar queries TMDB multi/movie/tv endpoints
- Results show poster, title, year, rating, type badge
- Each result shows "In Database" or "Missing" badge
- "Add" button for missing items (calls `admin_add_single.php`)

### Tab 2: Year Analysis
- Grid of year cards (2000-2027) with movie/TV counts
- Color-coded gap indicators: red (low), yellow (moderate), green (good)
- Click a year card to open fetch panel for that year
- Fetch panel calls `admin_fetch_year.php`

### Tab 3: Bulk Fetch
- Mode: Trending This Week or Discover (Current Year)
- Type: Both, Movies, TV Shows
- Pages: 1-10
- Calls `fetch_new_content.php`

---

## Running Tests

```bash
npx playwright test --config="TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/tests/playwright.config.js" --reporter=list
```

All 38 tests should pass. Tests run against the live site at `https://findtorontoevents.ca`.

---

## Important: What NOT to Change

- **Do not modify** any files in `MOVIESHOWS2/api/` (existing `db-config.php`, `get-movies.php`, `queue.php`)
- **Do not modify** `MOVIESHOWS2/index.html`, `app.html`, `play.html` (existing frontend)
- **Do not modify** `MOVIESHOWS2/init-database.php`, `verify-database.php` (existing DB scripts)
- **Do not modify** any files in `MOVIESHOWS/` or `MOVIESHOWS3/` directories
- The `movies` table schema is shared across all MOVIESHOWS variants - schema changes affect everything
