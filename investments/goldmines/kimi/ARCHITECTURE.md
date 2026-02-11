# KIMI Goldmine Architecture

## Overview

The KIMI Goldmine now uses a **GitHub Actions-powered** architecture that completely eliminates the need for server-side cron jobs, bypassing the 10 cron job limit on shared hosting.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GITHUB ACTIONS                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Collect   │→ │   Process   │→ │   Update    │→ │    Push     │    │
│  │   Stocks    │  │    Merge    │  │    JSON     │  │    to Git   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│  ┌─────────────┐                                                       │
│  │Collect Memes│                                                       │
│  └─────────────┘                                                       │
│  ┌─────────────┐                                                       │
│  │Collect Sport│                                                       │
│  └─────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
                        Raw GitHub JSON Files
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      YOUR WEBSITE (Any Hosting)                         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              kimi-goldmine-client.html                          │   │
│  │                    ↓                                            │   │
│  │         Fetch from GitHub Raw (unlimited requests)              │   │
│  │                    ↓                                            │   │
│  │              Display Dashboard                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  NO CRON JOBS NEEDED!                                                   │
│  NO DATABASE NEEDED!                                                    │
│  NO SERVER-SIDE PROCESSING!                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why This Architecture?

### Problem: Shared Hosting Cron Limits
- Most shared hosts limit cron jobs to 5-10 per account
- We need to collect from 6+ sources every 15 minutes
- That's 576+ cron jobs per day - impossible on shared hosting

### Solution: GitHub Actions
- **2,000 minutes/month** free tier (more than enough)
- **Unlimited** workflow runs for public repos
- Runs every 15 minutes = 2,880 runs/month
- Generates static JSON files
- Website just fetches JSON - no processing needed

## Data Flow

### 1. Collection Phase (GitHub Actions)
```yaml
Every 15 minutes:
  1. Fetch stock picks from findtorontoevents.ca
  2. Fetch meme coins from findtorontoevents.ca
  3. Fetch sports bets from findtorontoevents.ca
  4. Merge and normalize all data
  5. Save unified JSON to repo
  6. Commit and push
```

### 2. Storage Phase (GitHub Repo)
```
data/goldmine/
├── unified_picks.json    # All picks merged
├── stats.json            # Aggregated statistics
├── stock_picks.json      # Raw stock data
├── meme_winners.json     # Raw meme data
└── sports_picks.json     # Raw sports data
```

### 3. Display Phase (Client-Side)
```javascript
// Browser fetches directly from GitHub Raw
fetch('https://raw.githubusercontent.com/.../unified_picks.json')
  .then(renderDashboard)
```

## Files

### Server-Side (Your Website)
Just one file needed:
- `kimi-goldmine-client.html` - Fetches from GitHub, displays dashboard

### GitHub Actions (This Repo)
- `.github/workflows/kimi-goldmine-collector.yml` - Data collection workflow

### Generated Data (In This Repo)
- `data/goldmine/unified_picks.json` - Generated every 15 minutes
- `data/goldmine/stats.json` - Statistics by type/source

## Setup

### 1. Deploy Client Dashboard
Upload just this file to your website:
```
https://findtorontoevents.ca/investments/goldmines/kimi/kimi-goldmine-client.html
```

### 2. Enable GitHub Actions
The workflow file is already in `.github/workflows/`. Just push to GitHub and:
1. Go to Actions tab
2. Enable workflows
3. The first run will happen automatically

### 3. Wait for First Data
The first collection happens within 15 minutes. After that:
```
https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/goldmine/unified_picks.json
```

## GitHub Actions Schedule

| Task | Frequency | Minutes/Month |
|------|-----------|---------------|
| Market Hours Collection | Every 15 min, Mon-Fri 9:30-4PM | ~400 |
| Off-Hours Collection | Every hour | ~200 |
| Total | | ~600 minutes |

**Well under the 2,000 minute free tier limit**

## Benefits

1. **Zero Cron Jobs** - No limits, no setup on shared host
2. **Zero Database** - JSON files only
3. **Zero Server Load** - All processing on GitHub
4. **Unlimited Scaling** - Can add 100 more sources easily
5. **Version History** - Git tracks all data changes
6. **Backup** - Data lives in GitHub, not just your server
7. **Free CDN** - GitHub Raw is served via CDN

## Alternative: Server-Side Database Version

If you prefer the database version with all features:
- Use `kimi-goldmine.html` + `kimi_goldmine_api.php`
- Requires 1 cron job (the 15-minute collector)
- More features (alerts, winners tracking, performance calc)
- More complex setup

## Which Should I Use?

| Feature | GitHub Actions (Client) | Server + Database |
|---------|------------------------|-------------------|
| Setup Complexity | ⭐ Easy | ⭐⭐⭐ Complex |
| Cron Jobs Needed | 0 | 1-2 |
| Database Needed | No | Yes |
| Real-time Updates | ~15 min delay | ~15 min delay |
| Historical Analysis | Limited | Full |
| Winner Tracking | No | Yes |
| Alerts | No | Yes |
| Performance Metrics | Basic | Advanced |
| Best For | Simple monitoring | Full analysis |

## Monitoring

### Check if Actions are Running
1. Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions
2. Look for "KIMI Goldmine Data Collection"
3. Should show recent runs every 15 minutes

### Check Data Freshness
```bash
curl -s https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/goldmine/unified_picks.json | head -5
```

## Troubleshooting

### Dashboard shows "Data Not Available Yet"
- GitHub Actions hasn't run yet
- First run happens within 15 minutes of pushing
- Check Actions tab for status

### Actions are failing
- Check Actions tab for error logs
- Usually API connectivity issues
- Verify source endpoints are accessible

### Data is stale
- Check when Actions last ran
- Verify workflow is enabled
- Check for rate limiting on source APIs

## Future Enhancements

- [ ] Add more data sources (forex, mutual funds)
- [ ] Calculate performance metrics in Actions
- [ ] Generate winner reports
- [ ] Add email/Discord notifications for new picks
- [ ] Historical backtesting
- [ ] Machine learning predictions

## Cost

| Resource | Cost |
|----------|------|
| GitHub Actions | FREE (2,000 min/month) |
| GitHub Storage | FREE (public repo) |
| Website Hosting | No change |
| **Total** | **FREE** |
