# Database Enhancement Plan

## Goal
Populate the database with **100 movies + 100 TV shows per year** from 2027 back to 2015.

## Current Status
- Database: `ejaguiar1_tvmoviestrailers` at `mysql.50webs.com`
- Credentials: username=`ejaguiar1_tvmoviestrailers`, password=`virus2016`
- Backup available at: `C:\Users\zerou\Downloads\movies_asof2026_feb_03_715pmEST.sql`

## Files Created

### 1. `populate_tmdb.php`
PHP script that runs on the server to populate the database using TMDB API.

**Features:**
- Inspects current database state
- Fetches movies/TV shows from TMDB API
- Prevents duplicates (checks tmdb_id)
- Supports incremental population (only adds what's missing)
- Rate limiting to respect API limits

**Usage:**

```bash
# Inspect database
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=inspect

# Populate specific year and type
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=YOUR_KEY&year=2027&type=movie&limit=100

# Populate all years (2015-2027) automatically
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate_all&api_key=YOUR_KEY
```

### 2. `populate_db.js` (Local Node.js script)
Node.js script for local database operations (requires remote MySQL access).

**Note:** This requires remote MySQL access which may not be enabled on 50webs.com. The PHP script is recommended instead.

## Implementation Steps

### Step 1: Get TMDB API Key
1. Go to https://www.themoviedb.org/
2. Create an account or log in
3. Go to Settings → API
4. Request an API key (free for non-commercial use)
5. Copy your API key

### Step 2: Upload PHP Script to Server
Upload `populate_tmdb.php` to your server at:
```
/public_html/MOVIESHOWS/populate_tmdb.php
```

You can use FTP or the file manager in your hosting control panel.

### Step 3: Inspect Current Database
Visit:
```
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=inspect
```

This will show you:
- Total records
- Count by year and type
- Sample records

### Step 4: Populate Database

#### Option A: Populate All Years at Once (Recommended)
```
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate_all&api_key=YOUR_TMDB_API_KEY
```

This will automatically populate 100 movies + 100 TV shows for each year from 2027 to 2015.

**Warning:** This may take 10-30 minutes depending on server speed and API rate limits.

#### Option B: Populate Year by Year
For more control, populate each year individually:

```bash
# 2027 Movies
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=YOUR_KEY&year=2027&type=movie&limit=100

# 2027 TV Shows
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=YOUR_KEY&year=2027&type=tv&limit=100

# 2026 Movies
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=YOUR_KEY&year=2026&type=movie&limit=100

# 2026 TV Shows
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=populate&api_key=YOUR_KEY&year=2026&type=tv&limit=100

# ... continue for each year down to 2015
```

### Step 5: Verify Results
After population, run the inspect command again:
```
https://findtorontoevents.ca/MOVIESHOWS/populate_tmdb.php?action=inspect
```

You should see approximately:
- **2,600 total records** (13 years × 200 items per year)
- 100 movies per year from 2015-2027
- 100 TV shows per year from 2015-2027

## Database Schema

The `movies` table structure:
```sql
CREATE TABLE `movies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `type` enum('movie','tv') DEFAULT 'movie',
  `genre` varchar(255) DEFAULT NULL,
  `description` text,
  `release_year` int DEFAULT NULL,
  `imdb_rating` decimal(3,1) DEFAULT NULL,
  `imdb_id` varchar(20) DEFAULT NULL,
  `tmdb_id` int DEFAULT NULL,
  `runtime` int DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_release_year` (`release_year`),
  KEY `idx_imdb_id` (`imdb_id`),
  KEY `idx_tmdb_id` (`tmdb_id`)
);
```

## Troubleshooting

### Issue: "Access denied" error
- Verify the database credentials in `populate_tmdb.php`
- Ensure the script is uploaded to the correct location on the server

### Issue: "API key required" error
- Make sure you're passing the `api_key` parameter in the URL
- Verify your TMDB API key is valid

### Issue: Script times out
- Use Option B (year by year) instead of populate_all
- Reduce the `limit` parameter (e.g., `limit=50`)
- Contact your hosting provider about PHP execution time limits

### Issue: Duplicate entries
- The script automatically checks for duplicates using `tmdb_id`
- If you see duplicates, they may have different `tmdb_id` values
- You can run a cleanup query if needed

## Expected Timeline

- **Inspect database:** < 1 second
- **Populate single year (200 items):** 2-5 minutes
- **Populate all years (2,600 items):** 20-60 minutes

## Next Steps After Population

1. Verify the data quality
2. Update your frontend to display the new movies/shows
3. Consider adding more metadata (posters, trailers, cast, etc.)
4. Set up regular updates to keep the database current

## Notes

- The script uses TMDB's "discover" endpoint to get popular movies/shows
- Items are sorted by popularity (most popular first)
- The script respects TMDB's rate limits with 250ms delays between requests
- All data is stored in UTF-8 encoding
- The script is idempotent (safe to run multiple times)
