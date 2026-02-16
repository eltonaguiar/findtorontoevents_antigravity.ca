# Streaming Providers Setup Guide

## Overview
This system stores streaming platform availability in the database and serves it via API, eliminating client-side TMDB API calls.

## Installation Steps

### 1. Create Database Tables
```bash
mysql -u ejaguiar1_tvmoviestrailers -p ejaguiar1_tvmoviestrailers < migrations/001_create_streaming_providers.sql
```

This creates:
- `streaming_providers` - Current provider availability
- `streaming_provider_history` - Tracks when titles join/leave platforms

### 2. Initial Provider Data Load
Run the provider update job to populate initial data:

```bash
cd TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3
php jobs/update-streaming-providers.php --all
```

Expected output:
```
[INFO] Starting streaming provider update job at 2026-02-15 14:30:00
[INFO] Found 320 movies to update
[FETCH] The Wrecking Crew (TMDB: 123456, Type: movie)... OK (3 providers)
...
[SUMMARY]
  Movies processed: 320
  Providers added: 856
  Providers removed: 0
  Errors: 0
  Completed at 2026-02-15 14:45:00
```

### 3. Setup Cron Job
Add to crontab to update providers daily at 2:00 AM:

```bash
crontab -e
```

Add line:
```
0 2 * * * /usr/bin/php /path/to/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/jobs/update-streaming-providers.php >> /var/log/provider-updates.log 2>&1
```

### 4. Test API Response
Verify providers are returned:

```bash
curl https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php | jq '.movies[0].providers'
```

Expected output:
```json
[
  {
    "id": "9",
    "name": "Prime Video",
    "logo": "https://image.tmdb.org/t/p/original/emthp39XA2YScoYL1p0sdbAH2WA.jpg"
  },
  {
    "id": "8",
    "name": "Netflix",
    "logo": "https://image.tmdb.org/t/p/original/t2yyOv40HZeVlLjYsCsPHnWLk4W.jpg"
  }
]
```

## Update Job Options

### Update All Movies
```bash
php jobs/update-streaming-providers.php --all
```

### Update Specific Movie
```bash
php jobs/update-streaming-providers.php --movie-id=123
```

### Update Movies Not Checked in 30 Days
```bash
php jobs/update-streaming-providers.php --days=30
```

## How It Works

### Data Flow
```
TMDB Watch Providers API
        ↓
update-streaming-providers.php (cron job)
        ↓
streaming_providers table
        ↓
get-movies.php API
        ↓
MOVIESHOWS3 frontend (filter pills, badges)
```

### Provider Tracking
- **Added**: When a title appears on a new platform → logged to `streaming_provider_history` with action='added'
- **Removed**: When a title leaves a platform → `is_active=0` + history log with action='removed'
- **Last Checked**: Timestamp updated on every provider check

### Supported Providers (Canada)
| ID  | Name         | Priority |
|-----|--------------|----------|
| 8   | Netflix      | 1        |
| 9   | Prime Video  | 2        |
| 337 | Disney+      | 3        |
| 15  | Hulu         | 4        |
| 350 | Apple TV+    | 5        |
| 1899| Max          | 6        |
| 531 | Paramount+   | 7        |
| 386 | Peacock      | 8        |
| 230 | Crave        | 9        |
| 73  | Tubi         | 10       |

## Monitoring

### Check Provider Coverage
```sql
SELECT
    COUNT(DISTINCT movie_id) as titles_with_providers,
    COUNT(*) as total_provider_associations,
    AVG(providers_per_title) as avg_providers_per_title
FROM (
    SELECT movie_id, COUNT(*) as providers_per_title
    FROM streaming_providers
    WHERE is_active = 1
    GROUP BY movie_id
) t;
```

### View Recent Provider Changes
```sql
SELECT
    m.title,
    sph.provider_name,
    sph.action,
    sph.timestamp
FROM streaming_provider_history sph
JOIN movies m ON sph.movie_id = m.id
ORDER BY sph.timestamp DESC
LIMIT 20;
```

### Check Provider Distribution
```sql
SELECT
    provider_name,
    COUNT(*) as title_count
FROM streaming_providers
WHERE is_active = 1
GROUP BY provider_name
ORDER BY title_count DESC;
```

## Troubleshooting

### No Providers Returned
1. Check database tables exist:
   ```sql
   SHOW TABLES LIKE 'streaming%';
   ```

2. Verify provider data:
   ```sql
   SELECT COUNT(*) FROM streaming_providers WHERE is_active = 1;
   ```

3. Check API response:
   ```bash
   curl https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/get-movies.php
   ```

### TMDB Rate Limiting
The job includes built-in rate limiting (250ms delay between requests = ~4 req/sec).

If you hit rate limits, reduce batch size or increase delay in `update-streaming-providers.php`:
```php
usleep(500000); // Increase from 250000 to 500000 (0.5s delay)
```

### Update Job Errors
Check logs:
```bash
tail -f /var/log/provider-updates.log
```

Common errors:
- **"No TMDB ID"** - Movie missing `tmdb_id`, cannot fetch providers
- **"No CA data"** - Title not available in Canada
- **"FAILED"** - Network error or TMDB API down

## Performance

- **Initial load** (~320 movies): ~2-3 minutes
- **Daily updates** (7-day refresh): ~30-60 seconds
- **API response**: +5ms per request (due to JOIN)
- **Database size**: ~50 bytes per provider association

## Migration from Client-Side

The frontend previously fetched providers client-side from TMDB. Now:

### Before (Client-Side)
```javascript
// Fetch from TMDB for each movie
fetch('https://api.themoviedb.org/3/movie/123/watch/providers?api_key=...')
```

### After (Server-Side)
```javascript
// Providers included in get-movies.php response
movie._providers = movie.providers || [];
```

Benefits:
- ✅ Faster page loads (no TMDB API calls)
- ✅ No TMDB API key exposure
- ✅ Offline/cached provider data
- ✅ Historical tracking
- ✅ Server-side filtering capability
