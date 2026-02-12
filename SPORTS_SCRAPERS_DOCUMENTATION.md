# Sports Scrapers Documentation

## Overview

Comprehensive sports scrapers for NBA, NHL, NFL, and MLB that fetch:
- **Odds** from multiple bookmakers
- **Team Stats** (standings, records, streaks)
- **Injuries** (daily injury reports)
- **Schedules** (upcoming games and scores)

All data is stored in the MySQL database for analysis and display.

## Files Created

```
live-monitor/api/scrapers/
├── nba_scraper.php          # NBA scraper (518 lines)
├── nhl_scraper.php          # NHL scraper with OTL/points support
├── nfl_scraper.php          # NFL scraper with division/conference
├── mlb_scraper.php          # MLB scraper with pitcher data
├── scraper_controller.php   # Unified controller endpoint
├── cron_scheduler.php       # Automated scheduling script
└── (deploy_scrapers.py in root)  # Deployment script
```

## Database Tables Created

Each sport creates 4 tables:

| Table | Purpose |
|-------|---------|
| `lm_{sport}_odds` | Live odds from bookmakers |
| `lm_{sport}_team_stats` | Standings, records, streaks |
| `lm_{sport}_injuries` | Player injury reports |
| `lm_{sport}_schedule` | Game schedules and scores |

Plus control tables:
- `lm_scraper_log` - Run history
- `lm_cron_log` - Cron execution log

## API Endpoints

### Individual Sport Scrapers

**Base URL:** `/live-monitor/api/scrapers/{sport}_scraper.php`

| Action | Description |
|--------|-------------|
| `?action=scrape` (default) | Run all scrapes for this sport |
| `?action=odds` | Scrape odds only |
| `?action=stats` | Scrape team stats only |
| `?action=injuries` | Scrape injury reports only |
| `?action=schedule` | Scrape schedule only |

**Example:**
```
/live-monitor/api/scrapers/nba_scraper.php?action=scrape
```

### Controller

**Base URL:** `/live-monitor/api/scrapers/scraper_controller.php`

| Action | Description |
|--------|-------------|
| `?action=status` (default) | Check table status and row counts |
| `?action=health` | Check ESPN API health |
| `?action=run&key=livetrader2026&sport=nba` | Run specific scraper (admin) |
| `?action=run&key=livetrader2026&sport=all` | Run all scrapers (admin) |
| `?action=last_run` | View execution history |

## Data Sources

### ESPN APIs (Primary)
- **Standings:** `site.api.espn.com/apis/v2/sports/{sport}/standings`
- **Scoreboard:** `site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard`
- **Lines:** `www.espn.com/{sport}/lines` (HTML scraping)
- **Injuries:** `www.espn.com/{sport}/injuries` (HTML scraping)

### Sport-Specific
- **NBA:** BallDontLie API, NBA.com stats
- **NHL:** ESPN stats (goals for/against, OTL)
- **NFL:** ESPN with division/conference
- **MLB:** ESPN with probable pitchers, run line

## Cron Scheduling

### Manual Run
```bash
php cron_scheduler.php [mode]
```

Modes:
- `auto` - Scrape based on active seasons and game times (default)
- `all` - Scrape all sports
- `stats` - Stats-only refresh
- `nba|nhl|nfl|mlb` - Specific sport only

### Recommended Cron Schedule

```cron
# Odds - Every 5 minutes during game hours
*/5 * * * * php /path/to/cron_scheduler.php auto

# Stats - Every 2 hours
0 */2 * * * php /path/to/cron_scheduler.php stats

# Full refresh - Daily at 6 AM
0 6 * * * php /path/to/cron_scheduler.php all
```

## Response Format

### Success Response
```json
{
  "ok": true,
  "sport": "NBA",
  "data": {
    "odds": {...},
    "stats": [...],
    "injuries": [...],
    "schedule": [...],
    "timestamp": "2026-02-12 20:30:00"
  }
}
```

### Error Response
```json
{
  "ok": false,
  "error": "Unknown action: invalid"
}
```

## Deployment

The scrapers have been deployed via:
```bash
python deploy_scrapers.py
```

This uploads all 6 files to:
```
ftp://ejaguiar1:PASS@ftps2.50webs.com/findtorontoevents.ca/live-monitor/api/scrapers/
```

## Integration with ML Pipeline

The scraped data feeds into the existing ML intelligence system:
1. Odds data → Value bet detection (EV% calculation)
2. Stats → Situation scoring (rest, rankings, form)
3. Injuries → Automated filtering (key player out = higher uncertainty)
4. Schedule → B2B fatigue detection

## Monitoring

Check scraper status:
```
/live-monitor/api/scrapers/scraper_controller.php?action=status
```

Check data source health:
```
/live-monitor/api/scrapers/scraper_controller.php?action=health
```

View logs:
```sql
SELECT * FROM lm_cron_log ORDER BY run_at DESC LIMIT 10;
```

## PHP 5.2 Compatibility

All scrapers are compatible with PHP 5.2 (50webs hosting):
- No short array syntax (`[]`)
- No closures/anonymous functions
- No `__DIR__` constant
- No `http_response_code()`
- Standard MySQL functions (not MySQLi prepared statements)

## Future Enhancements

1. **Real-time odds** - WebSocket connections to sharp books
2. **Line movement alerts** - Track significant line changes
3. **Weather integration** - NFL/MLB weather impact
4. **Sharp money indicators** - Track where wiseguys are betting
5. **Consensus percentages** - Public betting percentages
