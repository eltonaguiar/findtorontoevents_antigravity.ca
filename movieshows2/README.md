# Movie/TV Series Auto-Fetch System

This system automatically fetches new movies and TV series from TMDB API and stores them in the database.

## Components

### 1. Log Viewer (`movieshows2/log/index.php`)
- Displays database statistics (total records, movies, TV series)
- Shows records by year and type
- Lists recent additions
- Shows pull history from automated fetches
- Access at: `https://findtorontoevents.ca/movieshows2/log`

### 2. Fetch Script (`movieshows2/fetch_new_content.php`)
- Fetches 20 new movies + 20 new TV series from current year
- Checks for duplicates before inserting
- Logs all operations to `pull_log.json`
- Uses TMDB API for data

### 3. GitHub Actions Workflow (`.github/workflows/kimi-fetch-movies.yml`)
- Runs daily at 6 AM UTC
- Can be triggered manually
- Fetches new content using PHP script
- Deploys files to FTP server
- Commits pull log back to repository

## Setup Instructions

### Required GitHub Secrets

Add these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

1. **EJAGUIAR1_TVMOVIESTRAILERS**: `virus2016`
   - Database password

2. **TMDB_API_KEY**: `b84ff7bfe35ffad8779b77bcbbda317f`
   - TMDB API key for fetching movie/TV data

3. **FTP_SERVER**: Your FTP server address
   - Example: `ftp.findtorontoevents.ca`

4. **FTP_USERNAME**: Your FTP username
   - Example: `your_ftp_user`

5. **FTP_PASSWORD**: Your FTP password
   - Your FTP account password

### Database Configuration

The system connects to:
- **Host**: `mysql.50webs.com`
- **Database**: `ejaguiar1_tvmoviestrailers`
- **Username**: `ejaguiar1_tvmoviestrailers`
- **Password**: From environment variable or default

### Manual Deployment

If you need to deploy manually:

```bash
cd movieshows2
php fetch_new_content.php
```

Then upload the files to your server via FTP to the `public_html/movieshows2/` directory.

### Testing the Workflow

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "Kimi Fetch Movies/TV" workflow
4. Click "Run workflow" button
5. Check the logs to see the fetch results

## File Structure

```
movieshows2/
├── log/
│   ├── index.php          # Log viewer page
│   └── pull_log.json      # Fetch history (auto-generated)
└── fetch_new_content.php  # Fetch script
```

## How It Works

1. **GitHub Actions** triggers the workflow (daily or manually)
2. **PHP Script** connects to TMDB API and fetches new movies/TV series
3. **Database** receives new records (checks for duplicates)
4. **Log File** records the operation (success/failure, counts)
5. **FTP Deploy** uploads files to web server
6. **Git Commit** saves the pull log back to repository

## Monitoring

- View logs at: `https://findtorontoevents.ca/movieshows2/log`
- Check GitHub Actions for workflow execution status
- Review `pull_log.json` for detailed fetch history

## Notes

- The system fetches only from the current year to get the latest content
- Duplicates are automatically skipped based on TMDB ID
- Rate limiting is implemented (250ms delay between API calls)
- Maximum 5 pages per type to avoid excessive API usage
