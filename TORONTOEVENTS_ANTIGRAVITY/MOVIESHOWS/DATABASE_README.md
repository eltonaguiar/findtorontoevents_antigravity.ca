# MovieShows Database Setup

## Quick Start

### 1. Initialize Database
```bash
php MOVIESHOWS/database/init-db.php
```

This will:
- Test database connection
- Create all required tables
- Insert initial content sources

### 2. Add Specific Movies
```bash
npm run movies:add
```

Adds the 13 requested movies: The Housemaid, Zootopia, The Wrecking Crew, The Plague, Iron Lung, Fallout, Wonderman, Anaconda, Greenland 2, The Rip, Shelter, Shrinking, Beauty

### 3. Scrape Cineplex Toronto
```bash
npm run movies:scrape
```

Scrapes currently playing movies from Cineplex Toronto theatres

### 4. Discover Trailers
```bash
npm run movies:discover
```

Discovers YouTube trailers for all movies (requires YOUTUBE_API_KEY in .env)

### 5. Full Update
```bash
npm run movies:update
```

Runs both scraping and trailer discovery

## API Endpoints

All endpoints are located at `/MOVIESHOWS/api/`

### Movies
- `GET /api/movies.php` - Get all movies
- `GET /api/movies.php?id=X` - Get specific movie
- `POST /api/movies.php` - Create movie
- `PUT /api/movies.php?id=X` - Update movie
- `DELETE /api/movies.php?id=X` - Delete movie

### Trailers
- `GET /api/trailers.php?movie_id=X` - Get trailers for movie
- `POST /api/trailers.php` - Add trailer
- `PUT /api/trailers.php?id=X` - Update trailer
- `DELETE /api/trailers.php?id=X` - Deactivate trailer

## Database Schema

### Tables
- `movies` - Movie/TV series information
- `trailers` - Multiple trailers per movie with priority
- `thumbnails` - Multiple thumbnail sources with fallback
- `content_sources` - Track content sources
- `sync_log` - Synchronization history

## Environment Variables

Add to `.env`:
```
YOUTUBE_API_KEY=your_youtube_api_key_here
```

## Deployment

Files to deploy to `/findtorontoevents.ca/MOVIESHOWS`:
- `api/db-config.php`
- `api/movies.php`
- `api/trailers.php`
- `database/init-db.php`
- `database/schema.sql`
