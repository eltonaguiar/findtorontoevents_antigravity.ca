# Sports Betting Database Verification Guide

## Quick Health Check Commands

### 1. Full Database Verification
```bash
# Run complete verification
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=verify"

# Check specific table
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=table&table=sports_bets"

# Find anomalies
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=anomalies"

# Fix missing indexes (dry run)
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=fix"

# Actually apply fixes
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=fix&execute=1"
```

---

## Expected Database Schema

### Core Tables

#### 1. `sports_bets` - Main betting tracker
| Column | Type | Required |
|--------|------|----------|
| id | INT (PK) | YES |
| sport | VARCHAR(20) | YES |
| bet_type | VARCHAR(50) | YES |
| stake | DECIMAL(10,2) | YES |
| odds | DECIMAL(8,2) | YES |
| ev_percent | DECIMAL(5,2) | YES |
| status | VARCHAR(20) | YES |
| result | VARCHAR(10) | No |
| profit_loss | DECIMAL(10,2) | No |
| created_at | DATETIME | YES |
| settled_at | DATETIME | No |

**Indexes:** sport, status, created_at

#### 2. `lm_sports_odds` - Cached odds from The Odds API
| Column | Type | Required |
|--------|------|----------|
| id | INT (PK) | YES |
| sport | VARCHAR(20) | YES |
| game_date | DATETIME | YES |
| home_team | VARCHAR(100) | YES |
| away_team | VARCHAR(100) | YES |
| bookmaker | VARCHAR(50) | YES |
| created_at | DATETIME | YES |

**Indexes:** sport, game_date

#### 3. Sport-Specific Odds Tables
- `lm_nba_odds` - NBA odds with spread, total
- `lm_nhl_odds` - NHL odds with puck_line, total
- `lm_nfl_odds` - NFL odds with spread, total
- `lm_mlb_odds` - MLB odds with run_line, total

All have: game_date, home_team, away_team, bookmaker, recorded_at

#### 4. Gap-Bridge Module Tables
- `lm_weather_data` - Weather impact scores
- `lm_travel_analysis` - Travel fatigue calculations
- `lm_mlb_analysis` - Pitcher/umpire analysis
- `lm_data_validation` - Validation results
- `lm_referee_stats` - Official tendencies
- `lm_live_odds` - Real-time odds feed
- `lm_line_movement` - Historical line changes
- `lm_nfl_hardened_games` - Cross-validated NFL data

#### 5. Logging Tables
- `lm_cron_log` - Scraper execution history
- `lm_scraper_log` - Individual scraper results

---

## Manual Verification Checklist

### Step 1: Check Table Existence
```sql
-- List all sports betting tables
SHOW TABLES LIKE 'lm_%';
SHOW TABLES LIKE 'sports_%';
```

**Expected:** 20+ tables with `lm_` prefix + `sports_bets`

### Step 2: Verify Row Counts
```sql
-- Core tables should have data
SELECT COUNT(*) FROM sports_bets;
SELECT COUNT(*) FROM lm_sports_odds;
SELECT COUNT(*) FROM lm_nba_odds;
SELECT COUNT(*) FROM lm_nhl_odds;

-- New tables may be empty initially
SELECT COUNT(*) FROM lm_weather_data;
SELECT COUNT(*) FROM lm_mlb_analysis;
SELECT COUNT(*) FROM lm_data_validation;
```

### Step 3: Check for Data Anomalies

#### Negative Stakes (CRITICAL)
```sql
SELECT id, sport, stake, created_at 
FROM sports_bets 
WHERE stake < 0;
-- Expected: 0 rows
```

#### Impossible EV Values (WARNING)
```sql
SELECT id, sport, ev_percent, pick 
FROM sports_bets 
WHERE ev_percent > 100 OR ev_percent < -50;
-- Expected: 0 rows (or review if found)
```

#### NULL Critical Fields (CRITICAL)
```sql
SELECT COUNT(*) 
FROM sports_bets 
WHERE sport IS NULL 
   OR bet_type IS NULL 
   OR stake IS NULL 
   OR odds IS NULL;
-- Expected: 0 rows
```

#### Future Dates (WARNING)
```sql
SELECT COUNT(*) 
FROM lm_sports_odds 
WHERE game_date > DATE_ADD(NOW(), INTERVAL 7 DAY);
-- Expected: 0 rows (or scheduled games only)
```

### Step 4: Check for Duplicates

#### Duplicate Bets
```sql
SELECT game_id, pick, COUNT(*) as cnt
FROM sports_bets
WHERE game_id IS NOT NULL
GROUP BY game_id, pick
HAVING cnt > 1;
-- Expected: 0 rows
```

#### Duplicate Odds Entries
```sql
SELECT home_team, away_team, game_date, COUNT(*) as cnt
FROM lm_sports_odds
WHERE game_date >= CURDATE()
GROUP BY home_team, away_team, game_date
HAVING cnt > 1;
-- Expected: 0 rows
```

### Step 5: Check Referential Integrity

#### Orphan Weather Data
```sql
SELECT COUNT(*) 
FROM lm_weather_data w
LEFT JOIN lm_sports_odds o ON w.game_id = o.id
WHERE o.id IS NULL 
  AND w.recorded_at > DATE_SUB(NOW(), INTERVAL 7 DAY);
-- Expected: 0 rows
```

### Step 6: Check Data Freshness
```sql
-- Last update times
SELECT 
    'sports_bets' as table_name, 
    MAX(created_at) as last_update,
    TIMESTAMPDIFF(HOUR, MAX(created_at), NOW()) as hours_ago
FROM sports_bets
UNION ALL
SELECT 
    'lm_sports_odds', 
    MAX(created_at),
    TIMESTAMPDIFF(HOUR, MAX(created_at), NOW())
FROM lm_sports_odds
UNION ALL
SELECT 
    'lm_nba_odds', 
    MAX(recorded_at),
    TIMESTAMPDIFF(HOUR, MAX(recorded_at), NOW())
FROM lm_nba_odds;
```

**Expected:** Core tables updated within 24 hours

---

## Common Issues & Fixes

### Issue 1: Missing Indexes
```sql
-- Check for slow queries
SHOW INDEX FROM sports_bets;
SHOW INDEX FROM lm_sports_odds;

-- Add missing indexes
CREATE INDEX idx_sport_status ON sports_bets (sport, status);
CREATE INDEX idx_game_date ON lm_sports_odds (game_date);
```

### Issue 2: Duplicate Records
```sql
-- Find exact duplicates
SELECT home_team, away_team, game_date, bookmaker, COUNT(*)
FROM lm_sports_odds
GROUP BY home_team, away_team, game_date, bookmaker
HAVING COUNT(*) > 1;

-- Remove duplicates (keep newest)
DELETE o1 FROM lm_sports_odds o1
INNER JOIN lm_sports_odds o2
WHERE o1.id < o2.id
  AND o1.home_team = o2.home_team
  AND o1.away_team = o2.away_team
  AND o1.game_date = o2.game_date
  AND o1.bookmaker = o2.bookmaker;
```

### Issue 3: Stale Data
```sql
-- Remove old odds (keep 30 days)
DELETE FROM lm_sports_odds 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Archive old bets (keep all for ROI tracking)
-- No deletion needed - historical data valuable
```

### Issue 4: Invalid Data Types
```sql
-- Check for non-numeric odds
SELECT id, odds FROM sports_bets 
WHERE odds REGEXP '[^0-9.-]';

-- Check for invalid dates
SELECT id, game_date FROM lm_sports_odds
WHERE game_date = '0000-00-00' OR game_date IS NULL;
```

---

## Performance Checks

### Table Sizes
```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
    table_rows
FROM information_schema.TABLES
WHERE table_schema = DATABASE()
  AND table_name LIKE 'lm_%' OR table_name LIKE 'sports_%'
ORDER BY size_mb DESC;
```

**Expected:**
- sports_bets: < 1 MB (unless thousands of bets)
- lm_sports_odds: < 10 MB
- Other tables: < 5 MB each

### Slow Query Log
```sql
-- Enable slow query log (if accessible)
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
```

---

## Integration with New Scraper Tables

When deploying the hardened scrapers, new tables will be created automatically:

### Auto-Created Tables
```sql
-- These will be created on first run:
-- lm_data_validation
-- lm_nfl_hardened_games
-- lm_weather_data (if weather module used)
-- lm_travel_analysis (if travel module used)
-- etc.
```

### Verify New Tables
```sql
-- After first scraper run:
SHOW TABLES LIKE 'lm_%';

-- Check for data
SELECT COUNT(*) FROM lm_data_validation;
SELECT COUNT(*) FROM lm_weather_data;
```

---

## Automated Monitoring

### Set Up Cron Job
```bash
# Daily database health check
0 6 * * * curl -s "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/db_verify.php?action=verify" > /var/log/db_health.json
```

### Alert Thresholds
| Metric | Warning | Critical |
|--------|---------|----------|
| Missing tables | Any | Core tables |
| Duplicate bets | > 0 | > 5 |
| Negative stakes | > 0 | Any |
| Stale data (hours) | > 24 | > 72 |
| Data confidence | < 80% | < 60% |

---

## Troubleshooting

### Database Connection Issues
```php
// Check db_config.php exists and has correct credentials
// Located at: live-monitor/api/db_config.php

// Should contain:
$servername = "localhost";
$username = "your_username";
$password = "your_password";
$dbname = "your_database";

// Sports DB (optional, falls back to main)
$sports_servername = "localhost";
$sports_username = "your_username";
$sports_password = "your_password";
$sports_dbname = "sports_db";
```

### Character Set Issues
```sql
-- Ensure UTF-8
ALTER DATABASE your_database CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE sports_bets CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
```

---

## Verification Summary Template

After running verification, report should show:

```json
{
  "summary": {
    "status": "healthy",  // or "warning" or "critical"
    "tables_found": "18/20",
    "critical_issues": 0,
    "warnings": 2
  },
  "checks": {
    "tables": {
      "expected": 20,
      "found": 18,
      "missing": ["lm_mlb_analysis", "lm_referee_stats"]
    },
    "data": {
      "checks": {
        "invalid_sport": 0,
        "missing_odds": 0,
        "duplicate_bets": 0
      }
    }
  }
}
```

---

## Next Steps After Verification

1. ✅ **If Healthy:** Continue with normal operations
2. ⚠️ **If Warnings:** Review flagged items, apply fixes
3. 🚨 **If Critical:** Stop automated betting, investigate issues

### Post-Verification Actions
- [ ] Run `db_verify.php?action=fix&execute=1` if needed
- [ ] Schedule daily verification cron job
- [ ] Document any manual data corrections made
- [ ] Update this guide with any sport-specific issues found

---

## Contact & Support

For database issues:
1. Check this guide first
2. Run verification tool
3. Review error logs in `live-monitor/api/`
4. Check database connection in `db_config.php`

---

*Last Updated: 2026-02-12*
*Verification Tool: db_verify.php*
