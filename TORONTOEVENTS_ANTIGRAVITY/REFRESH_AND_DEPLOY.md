# Refresh Events Database and Deploy

## Complete Process

To refresh the events database, sync to GitHub, and deploy to FTP site, you have two options:

### Option 1: Complete Refresh (Recommended)
Runs scraper, then syncs and deploys:
```bash
npm run refresh:all
```

**Note:** This takes 10-15 minutes because the scraper needs to:
- Fetch events from multiple sources (Eventbrite, AllEvents.in, Thursday, etc.)
- Visit individual event pages for enrichment
- Rate limit requests to avoid IP bans

### Option 2: Sync and Deploy Only
Use this if you've already run the scraper:
```bash
npm run sync:deploy
```

This will:
1. Check for changes in `data/events.json` and `data/metadata.json`
2. Commit and push to GitHub (if changes detected)
3. Build Next.js app
4. Deploy to FTP site

## Manual Steps

If you prefer to run steps individually:

### 1. Refresh Events Database
```bash
npm run scrape
```

### 2. Commit and Push to GitHub
```bash
git add data/events.json data/metadata.json
git commit -m "chore: refresh events database - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
git push
```

### 3. Build and Deploy to FTP
```bash
npm run deploy:sftp
```

## What Gets Deployed

The deployment script (`scripts/deploy-simple.ts`) uploads:
- `index.html` (main app) and `index3.html` (legacy)
- `_next/` directory (Next.js build chunks)
- `events.json` and `metadata.json` (from `data/` folder)
- Public assets (favicon, ads.txt, etc.)
- WINDOWSFIXER page (if exists)
- Error pages (404, _not-found)

## FTP Configuration

The FTP credentials are configured in `scripts/deploy-simple.ts`:
- Host: `ftps2.50webs.com`
- Remote Path: `/findtorontoevents.ca`

## GitHub Sync

The script automatically:
- Checks for changes in `data/events.json` and `data/metadata.json`
- Only commits if changes are detected
- Uses commit message: `chore: refresh events database - [timestamp]`
- Pushes to the `main` branch

## Troubleshooting

### Scraper Takes Too Long
This is normal - the scraper processes hundreds of events. Don't interrupt it.

### Git Push Fails
- Ensure you have write access to the repository
- Check your Git credentials are configured
- Verify you're on the correct branch

### FTP Deployment Fails
- Check FTP credentials in `scripts/deploy-simple.ts`
- Verify network connection
- Check if FTP server is accessible

### No Changes Detected
If Git reports no changes:
- The scraper may not have found new events
- Events may have already been up to date
- Check `data/metadata.json` for last updated timestamp

---

**Quick Command:** `npm run refresh:all` (complete process)  
**After Scraper:** `npm run sync:deploy` (sync and deploy only)
