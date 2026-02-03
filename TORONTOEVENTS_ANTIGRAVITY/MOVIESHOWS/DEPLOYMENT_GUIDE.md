# MovieShows Database Deployment Guide

## Files Created

### Database Schema
- `database/schema.sql` - Complete database schema with 5 tables

### PHP API Endpoints
- `MOVIESHOWS/api/db-config.php` - Database configuration
- `MOVIESHOWS/api/movies.php` - Movies CRUD API
- `MOVIESHOWS/api/trailers.php` - Trailers management API
- `MOVIESHOWS/database/init-db.php` - Database initialization script

### Content Scripts
- `scripts/add-specific-movies.js` - Add the 13 requested movies
- `scripts/scrape-cineplex.js` - Scrape Cineplex Toronto
- `scripts/discover-trailers.js` - YouTube trailer discovery
- `scripts/deploy-movieshows-db.js` - FTP deployment script

### NPM Scripts Added
```bash
npm run movies:add        # Add specific movies
npm run movies:scrape     # Scrape Cineplex
npm run movies:discover   # Discover trailers
npm run movies:update     # Full update (scrape + discover)
npm run movies:deploy     # Deploy to FTP
```

## Manual Deployment Steps

Since FTP deployment requires credentials, you can manually upload these files:

### Upload to `/findtorontoevents.ca/MOVIESHOWS/`:

1. **API Directory** (`/api/`):
   - `db-config.php`
   - `movies.php`
   - `trailers.php`

2. **Database Directory** (`/database/`):
   - `init-db.php`
   - `schema.sql`

3. **Root**:
   - `DATABASE_README.md`

## After Deployment

1. **Initialize Database**:
   Visit: `https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php`
   
   This will create all tables and verify the setup.

2. **Test API**:
   Visit: `https://findtorontoevents.ca/MOVIESHOWS/api/movies.php`
   
   Should return: `{"movies":[],"count":0}`

3. **Add Movies**:
   ```bash
   npm run movies:add
   ```

4. **Scrape Cineplex**:
   ```bash
   npm run movies:scrape
   ```

5. **Discover Trailers** (requires YouTube API key):
   ```bash
   npm run movies:discover
   ```

## Database Configuration

Update `MOVIESHOWS/api/db-config.php` if needed:
- `DB_HOST` - Database host (default: localhost)
- `DB_NAME` - ejaguiar1_tvmoviestrailers
- `DB_USER` - ejaguiar1_tvmoviestrailers
- `DB_PASS` - tvmoviestrailers1

## Next Steps

After database is initialized and API is working:

1. Update MovieShows frontend to use the API
2. Implement trailer failover in the player
3. Add thumbnail fallback system
4. Test multi-trailer support
