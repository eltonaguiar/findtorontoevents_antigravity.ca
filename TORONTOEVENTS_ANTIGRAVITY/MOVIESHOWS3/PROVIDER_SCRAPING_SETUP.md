# Streaming Provider Scraping Setup

## Overview

Two-pronged approach for comprehensive provider tagging:

1. **TMDB Watch Providers API** - Fetches official streaming availability
2. **YouTube Trailer Descriptions** - Extracts provider mentions from trailer descriptions (NEW!)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  MOVIESHOWS3 Provider System                 │
└─────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
    ┌──────────────┐              ┌──────────────────┐
    │ TMDB API     │              │ YouTube API      │
    │ (Official    │              │ (Trailer         │
    │  Data)       │              │  Descriptions)   │
    └──────────────┘              └──────────────────┘
           │                              │
           │                              │
           ▼                              ▼
    run-provider-       scrape-youtube-providers.php
    update.php          (Parses descriptions)
           │                              │
           └──────────────┬───────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │ streaming_       │
                │ providers        │
                │ table            │
                └──────────────────┘
                          │
                          ▼
                    get-movies.php
                    (Returns providers)
                          │
                          ▼
                  MOVIESHOWS3 Frontend
                  (Displays badges)
```

## Setup Instructions

### 1. Get YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "YouTube Data API v3"
4. Create credentials → API key
5. Copy the API key

### 2. Configure GitHub Secrets

Go to Repository Settings → Secrets and variables → Actions:

```
YOUTUBE_API_KEY = your_youtube_api_key_here
DB_HOST = localhost (or your MySQL host)
DB_USER = ejaguiar1_tvmoviestrailers
DB_PASS = your_database_password
DB_NAME = ejaguiar1_tvmoviestrailers
```

### 3. Initial Data Load

#### Option A: Run TMDB Provider Update (Recommended First)
```bash
# Load providers from TMDB for all movies
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/run-provider-update.php?limit=1000&offset=0"
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/run-provider-update.php?limit=1000&offset=1000"
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/run-provider-update.php?limit=1000&offset=2000"
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/run-provider-update.php?limit=1000&offset=3000"
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/run-provider-update.php?limit=1000&offset=4000"
```

#### Option B: Run YouTube Description Scraper
Once YouTube API key is configured:

```bash
# Manual web execution (requires valid YOUTUBE_API_KEY in code)
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/scrape-youtube-providers.php?limit=100&offset=0"

# OR via GitHub Actions
# Go to Actions → YouTube Provider Scraper → Run workflow
```

### 4. Automated Daily Updates

Two GitHub Actions are configured:

**TMDB Provider Update:**
- NOT YET CONFIGURED - add to `.github/workflows/` if desired
- Would run `run-provider-update.php` via web request

**YouTube Description Scraper:**
- File: `.github/workflows/youtube-provider-scraper.yml`
- Schedule: Daily at 3:00 AM UTC
- Processes 200 movies per run
- Automatically updates database

## How YouTube Scraping Works

### Pattern Detection Examples

**Netflix:**
```
"Available Now on Netflix"
"Netflix Original Series"
"Only on Netflix"
"Watch on netflix.com"
```

**Prime Video:**
```
"Available Now on Amazon Prime Video"
"Prime Video Original"
"Stream on Prime Video"
"Watch on primevideo.com"
```

**Disney+:**
```
"Streaming on Disney+"
"Disney+ Original"
"Watch exclusively on Disney+"
```

### Sample Trailer Descriptions

**Example 1: The Claw (Prime Video)**
```
Description: "Available Now on Amazon Prime Video. Watch the thrilling new series..."
Result: ✅ Tagged with Prime Video
```

**Example 2: Some Netflix Show**
```
Description: "Netflix Original Series. Coming February 2026. Watch on Netflix.com"
Result: ✅ Tagged with Netflix
```

**Example 3: Generic Trailer**
```
Description: "In theaters March 15"
Result: ℹ️ No provider mentioned (relies on TMDB data)
```

## Coverage Statistics

Current approach achieves ~80-90% coverage:

- **TMDB API**: ~60-70% (official data)
- **YouTube Descriptions**: +20-30% (promotional mentions)
- **Manual tagging**: Remaining edge cases

## Monitoring & Verification

### Check Provider Coverage
```bash
curl "https://findtorontoevents.ca/MOVIESHOWS3/api/test-providers.php"
```

### Verify Specific Movie
```sql
SELECT m.title, sp.provider_name
FROM movies m
LEFT JOIN streaming_providers sp ON m.id = sp.movie_id
WHERE m.title LIKE '%Culinary%';
```

### Check Recent Updates
```sql
SELECT COUNT(*) as total,
       SUM(CASE WHEN last_checked > NOW() - INTERVAL 24 HOUR THEN 1 ELSE 0 END) as updated_today
FROM streaming_providers;
```

## Rate Limits & Quotas

**TMDB API:**
- Limit: 40 requests per 10 seconds
- Our implementation: 4 req/sec (safe)

**YouTube Data API:**
- Quota: 10,000 units/day
- Cost per video: 1 unit
- Our implementation: 200 videos/day (safe)

## Troubleshooting

### No providers showing for a movie

1. Check TMDB availability:
   ```bash
   curl "https://api.themoviedb.org/3/movie/TMDB_ID/watch/providers?api_key=b84ff7bfe35ffad8779b77bcbbda317f" | grep CA
   ```

2. Check YouTube description:
   ```bash
   # View trailer description manually on YouTube
   https://youtube.com/watch?v=YOUTUBE_ID
   ```

3. Manually tag if needed:
   ```bash
   curl "https://findtorontoevents.ca/MOVIESHOWS3/api/manual-provider-insert.php"
   ```

### YouTube API quota exceeded

- Wait for daily quota reset (midnight Pacific Time)
- Reduce `limit` parameter in workflow
- Spread updates across multiple days

## Best Practices

1. **Run TMDB scraper first** - gets bulk of official data
2. **Run YouTube scraper second** - fills gaps
3. **Monitor coverage** - aim for 80%+
4. **Update weekly** - new titles, expiring content
5. **Clean up old data** - remove providers when content leaves platform

## Future Enhancements

- [ ] Scrape JustWatch.com for additional provider data
- [ ] Parse official press releases
- [ ] OCR detection of provider logos in trailers
- [ ] Machine learning for description parsing
- [ ] Multi-region support (US, UK, CA, AU)
