# GitHub Data Integration for FTP Deployment

## Overview

The application is configured to pull event data **directly from GitHub** at runtime, ensuring the FTP-deployed site always shows the latest events without requiring a rebuild.

## How It Works

### 1. Client-Side Data Fetching

The app uses `src/lib/data-client.ts` to fetch data from GitHub:

- **Events URL**: `https://raw.githubusercontent.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/main/data/events.json`
- **Metadata URL**: `https://raw.githubusercontent.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/main/data/metadata.json`

### 2. Automatic Refresh

- Events refresh every **30 minutes** automatically
- Metadata refreshes every **1 hour** automatically
- No page reload required - data updates seamlessly

### 3. Deployment Process

When deploying to FTP:

1. **Build the app** (HTML/JS/CSS)
2. **Optionally fetch latest data** from GitHub as fallback
3. **Upload to FTP**:
   - `index.html` (main site)
   - `index3.html` (versioned)
   - `events.json` (fallback - primary source is GitHub)
   - `metadata.json` (fallback - primary source is GitHub)
   - All static assets

## Deployment Commands

### Standard Deployment (Uses GitHub at Runtime)
```bash
npm run build:sftp
npm run deploy:sftp
```

### Deployment with GitHub Data Fetch (Includes Fallback Files)
```bash
npm run deploy:sftp:github
```

This will:
1. Fetch latest `events.json` and `metadata.json` from GitHub
2. Build the app
3. Upload everything to FTP (including data files as fallback)

## Data Flow

```
GitHub Actions (every 6h)
  ↓
Updates data/events.json in GitHub
  ↓
Client App (on load + every 30min)
  ↓
Fetches from GitHub raw JSON
  ↓
Displays latest events
```

## Fallback Strategy

The app tries to fetch from GitHub first. If that fails:
1. It will attempt to use local/fallback files if available
2. Shows loading state while fetching
3. Gracefully handles errors

## Configuration

### GitHub Repository
- **Repo**: `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY`
- **Branch**: `main` (default)
- **Data Path**: `/data/events.json` and `/data/metadata.json`

### Update Branch Name

If your default branch is different, update:
1. `src/lib/data-client.ts` - Line 8-10
2. `scripts/fetch-github-data.ts` - Line 6
3. `.github/workflows/scrape-events.yml` - Line 18

## Benefits

✅ **Always Fresh**: Data is always up-to-date from GitHub  
✅ **No Rebuild Needed**: Update events without rebuilding the app  
✅ **Fast CDN**: GitHub raw JSON is served via CDN  
✅ **Version Control**: All data changes are tracked in git  
✅ **Automatic**: GitHub Actions updates data every 6 hours  

## Verification

To verify the setup is working:

1. **Check Network Tab**: Open browser DevTools → Network
2. **Look for requests to**: `raw.githubusercontent.com/.../events.json`
3. **Check Response**: Should return latest events array
4. **Verify Auto-Refresh**: Wait 30 minutes, check if new data loads

## Troubleshooting

### Events Not Loading

1. Check GitHub URL is accessible: Visit the raw URL directly
2. Check browser console for CORS or fetch errors
3. Verify branch name is correct
4. Check if GitHub Actions workflow ran successfully

### Stale Data

1. Verify GitHub Actions workflow is enabled
2. Check last commit time in GitHub
3. Force refresh: Clear browser cache (Ctrl+Shift+R)
4. Check network tab for cache headers

### Deployment Issues

1. Ensure `npm run build:sftp` completes successfully
2. Check FTP credentials are correct
3. Verify files are uploaded (check FTP file listing)
4. Check browser console for 404 errors on assets
