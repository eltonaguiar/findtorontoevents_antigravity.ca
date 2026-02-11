# KIMI Goldmine System

## Overview

The **KIMI Goldmine** is a centralized tracking system that aggregates predictions from all Antigravity prediction sources (stocks, crypto, forex, mutual funds, sports betting) to ensure no winning algorithm or hidden gem is ever lost or forgotten.

## Philosophy

> "We don't just make picks - we discover which pick sources are actually goldmines."

## Database Tables

All tables prefixed with `KIMI_GOLDMINE_`:

| Table | Purpose |
|-------|---------|
| `KIMI_GOLDMINE_PICKS` | Every prediction from every source |
| `KIMI_GOLDMINE_PERFORMANCE` | Aggregated metrics by source/period |
| `KIMI_GOLDMINE_WINNERS` | Exceptional performers that met criteria |
| `KIMI_GOLDMINE_SOURCES` | Metadata for all prediction sources |
| `KIMI_GOLDMINE_ALERTS` | Notifications for significant events |
| `KIMI_GOLDMINE_DAILY_SNAPSHOT` | Historical daily status records |

## Files

| File | Purpose |
|------|---------|
| `kimi_goldmine_schema.php` | Database setup - run this first |
| `kimi_goldmine_collector.php` | Data collection from all sources |
| `kimi_goldmine_api.php` | API endpoint for dashboard |
| `kimi-goldmine.html` | Main dashboard frontend |
| `README.md` | This file |

## Installation

### Step 1: Create Database Tables

```bash
php kimi_goldmine_schema.php
```

Or visit in browser:
```
https://yourdomain.com/investments/goldmines/kimi/kimi_goldmine_schema.php
```

### Step 2: Set Up Automated Collection

Add to cron (runs every 15 minutes):
```bash
*/15 * * * * curl -s "https://yourdomain.com/investments/goldmines/kimi/kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026" > /dev/null
```

Daily performance calculation (runs at 6 AM):
```bash
0 6 * * * curl -s "https://yourdomain.com/investments/goldmines/kimi/kimi_goldmine_collector.php?action=calculate_performance&key=goldmine2026" > /dev/null
```

Price updates (every 30 minutes during market hours):
```bash
*/30 9-16 * * 1-5 curl -s "https://yourdomain.com/investments/goldmines/kimi/kimi_goldmine_collector.php?action=update_prices&key=goldmine2026" > /dev/null
```

### Step 3: Access Dashboard

```
https://yourdomain.com/investments/goldmines/kimi/kimi-goldmine.html
```

## API Endpoints

### Collector API (`kimi_goldmine_collector.php`)

| Action | Purpose | Parameters |
|--------|---------|------------|
| `collect` | Import picks from sources | `source=all\|stock\|crypto\|meme\|forex\|fund\|sports` |
| `update_prices` | Refresh current prices | - |
| `resolve` | Check exits, resolve completed | - |
| `calculate_performance` | Recalculate all metrics | - |
| `find_winners` | Surface new winners | - |
| `status` | Get collection status | - |

### Dashboard API (`kimi_goldmine_api.php`)

| Action | Purpose |
|--------|---------|
| `dashboard` | Main dashboard data |
| `picks` | List all picks (with filters) |
| `winners` | List discovered winners |
| `performance` | Performance metrics |
| `sources` | All prediction sources |
| `alerts` | System alerts |
| `goldmines` | Goldmine-worthy sources |
| `pick_detail` | Single pick details |
| `source_detail` | Source with history |

## Goldmine Criteria

A source achieves **Goldmine Status** when:

1. ✅ Minimum 10 resolved picks (statistical significance)
2. ✅ Win rate of 55% or higher
3. ✅ Average return of 10% or higher
4. ✅ Sharpe ratio of 1.0 or higher
5. ✅ Consistent performance across market conditions

## Tracked Sources

### Stocks
- Alpha Forge Ultimate
- God-Mode Standard
- Piotroski F-Score
- Technical Momentum
- CAN SLIM
- Penny Stock Scanner

### Crypto
- Crypto Winners
- Meme Coin Scanner (7-factor scoring)

### Forex
- Forex Signals

### Mutual Funds
- Fund Selections

### Sports Betting
- Value Bet Finder (+EV detection)
- Line Shopping

### Alpha Engine (Python)
- ML Ranker
- Quality Compounders

## Winner Categories

| Category | Criteria |
|----------|----------|
| **Mega Winner** | 50%+ return |
| **Quick Hit** | 20%+ return, fast exit |
| **Consistent Performer** | Multiple wins in a row |
| **Comeback Kid** | Recovered from drawdown |
| **Hidden Gem** | 10%+ return, under-the-radar |

## Dashboard Sections

1. **Dashboard** - Overview stats, top performers, recent activity
2. **All Picks** - Complete list with filtering
3. **Winners** - Discovered exceptional performers
4. **Goldmines** - Sources meeting goldmine criteria
5. **Sources** - All prediction sources with metadata
6. **Performance** - Detailed metrics by period
7. **Alerts** - System notifications

## Security

- Admin key required for collection actions: `goldmine2026`
- Change this key in production!
- Dashboard is read-only (no key required for API reads)

## Troubleshooting

### No data showing
1. Run schema setup: `kimi_goldmine_schema.php`
2. Run collector: `kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026`
3. Check database permissions

### Prices not updating
1. Ensure price API keys are configured
2. Check `update_prices` cron job is running
3. Verify database connection

### Sources not appearing
1. Check `KIMI_GOLDMINE_SOURCES` table has data
2. Run schema setup to populate default sources
3. Verify source `is_active = 1`

## Future Enhancements

- [ ] Machine learning model to predict which picks will become winners
- [ ] Email/Discord alerts for new goldmines discovered
- [ ] Export to Excel/CSV for analysis
- [ ] Integration with broker APIs for auto-trading goldmine picks
- [ ] Backtesting engine to validate goldmine criteria
- [ ] Social features (follow top performing sources)

## Support

For questions or issues, check the main analysis document:
`KIMI_STOCKS_ANALYSIS_2026_Feb10.md`
