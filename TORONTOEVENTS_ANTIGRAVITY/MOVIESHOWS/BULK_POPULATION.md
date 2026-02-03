# Bulk Content Population

This script populates the MovieShows database with 200+ movies and TV series per year, starting from 2025/2026 and working backwards to 2020.

## Features

- **200+ items per year** (70% movies, 30% TV series)
- **TMDB integration** for complete metadata
- **Automatic thumbnails** (poster + backdrop)
- **Trailer extraction** (up to 3 per item)
- **Smart filtering** (minimum 10 votes for quality)
- **Rate limiting** to respect API limits

## Usage

```bash
npm run movies:bulk
```

## What It Does

For each year (2026 → 2020):
1. Discovers popular movies sorted by popularity
2. Discovers popular TV series sorted by popularity
3. Fetches full metadata from TMDB
4. Extracts thumbnails (poster + backdrop)
5. Extracts YouTube trailers
6. Adds to database with all metadata

## Expected Results

- **Total items**: ~1,400 (200 × 7 years)
- **Thumbnails**: ~2,800 (2 per item)
- **Trailers**: ~3,000+ (2-3 per item)
- **Runtime**: ~2-3 hours (with rate limiting)

## Progress Tracking

The script shows real-time progress:
```
[45/200] ✓ The Batman (2026)
[46/200] ✓ Stranger Things (2026) [TV]
```

## Year Summary

After each year:
```
2026 Summary:
  Added: 200
  Skipped: 15 (duplicates)
  Errors: 2
```

## Final Summary

After completion:
```
BULK POPULATION COMPLETE
Total Added: 1,385
Total Skipped: 45
Total Errors: 10
Years Processed: 7
Average per Year: 198
```

## Configuration

Edit `scripts/bulk-populate-content.js`:

```javascript
const MOVIES_PER_YEAR = 200;  // Target per year
const START_YEAR = 2026;      // Start year
const END_YEAR = 2020;        // End year
```

## Rate Limiting

- 300ms delay between items
- 2 second pause between years
- Respects TMDB API limits

## Error Handling

- Skips duplicates (409 status)
- Logs errors but continues
- Retries on network issues
- Comprehensive error reporting

## Database Impact

Each item includes:
- Full metadata (title, year, genre, description)
- TMDB and IMDb IDs
- 2 high-quality thumbnails
- 2-3 official trailers
- Source tracking

## Running Specific Years

To populate only specific years, modify the script:

```javascript
// Single year
await populateYear(2026);

// Range
for (let year = 2026; year >= 2024; year--) {
  await populateYear(year);
}
```

## Notes

- Requires TMDB_API_KEY in .env
- Database must be initialized first
- Can be run multiple times (skips duplicates)
- Safe to interrupt and resume
