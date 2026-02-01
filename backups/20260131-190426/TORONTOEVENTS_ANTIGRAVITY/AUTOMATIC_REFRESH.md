# Automatic Event Refresh System

This project includes an automated system to refresh event data from multiple sources and make it available via GitHub.

## How It Works

### 1. GitHub Actions Workflow

The `.github/workflows/scrape-events.yml` workflow automatically:
- Runs every 6 hours (configurable via cron schedule)
- Scrapes events from all configured sources
- Updates `data/events.json` and `data/metadata.json`
- Commits and pushes changes back to the repository

### 2. Client-Side Data Fetching

The application (`src/lib/data-client.ts`) fetches events directly from GitHub's raw JSON endpoint:
- **Events URL**: `https://raw.githubusercontent.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/main/data/events.json`
- **Metadata URL**: `https://raw.githubusercontent.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/main/data/metadata.json`

### 3. Auto-Refresh

- Events are automatically refreshed every 30 minutes in the browser
- Metadata is refreshed every hour
- No page reload required - data updates seamlessly

## Setup Instructions

### 1. Enable GitHub Actions

1. Go to your repository settings on GitHub
2. Navigate to **Actions** → **General**
3. Under **Workflow permissions**, select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**

### 2. Verify Default Branch

The workflow is configured to use the `main` branch. If your default branch is different:
- Update `.github/workflows/scrape-events.yml` line 18: change `ref: main` to your branch name
- Update `src/lib/data-client.ts` line 4: change `GITHUB_BRANCH` to your branch name

### 3. Manual Trigger

You can manually trigger the workflow:
1. Go to **Actions** tab in GitHub
2. Select **Scrape Events** workflow
3. Click **Run workflow** → **Run workflow**

## Configuration

### Change Refresh Frequency

Edit `.github/workflows/scrape-events.yml`:
```yaml
schedule:
  # Run every 6 hours (current)
  - cron: '0 */6 * * *'
  
  # Examples:
  # Every 3 hours: '0 */3 * * *'
  # Every 12 hours: '0 */12 * * *'
  # Daily at 2 AM: '0 2 * * *'
```

### Change Client-Side Refresh Rate

Edit `src/lib/data-client.ts`:
- Events refresh: Line 67 - change `30 * 60 * 1000` (30 minutes)
- Metadata refresh: Line 103 - change `60 * 60 * 1000` (1 hour)

## Troubleshooting

### Workflow Not Running

1. Check if Actions are enabled in repository settings
2. Verify the cron schedule syntax is correct
3. Check the Actions tab for error messages

### Events Not Updating

1. Verify the GitHub Actions workflow completed successfully
2. Check that `data/events.json` was updated in the repository
3. Clear browser cache and hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
4. Check browser console for fetch errors

### Permission Errors

If the workflow can't push changes:
1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **Read and write permissions**
3. Save changes

## Benefits

✅ **Always Fresh Data**: Events are automatically updated every 6 hours  
✅ **No Manual Intervention**: Fully automated process  
✅ **Fast Loading**: Direct GitHub CDN delivery  
✅ **Version Control**: All changes are tracked in git history  
✅ **Transparent**: See exactly when data was last updated  

## Monitoring

Check the last update time:
- In the app header: "Last updated: [timestamp]"
- In GitHub: View `data/metadata.json` for `lastUpdated` field
- In Actions: View workflow run history
