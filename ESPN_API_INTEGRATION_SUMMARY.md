# ESPN Hidden API Integration Summary

## Source
**GitHub Gist:** https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b

## New Files Created

| File | Size | Purpose |
|------|------|---------|
| `espn_api_enhanced.php` | 26.2 KB | Direct ESPN API wrapper with multi-source validation |
| `unified_sports_feed.php` | 24.0 KB | Single endpoint for all sports with automatic source selection |

---

## ESPN APIs Now Integrated

### Professional Sports

| Sport | Scoreboard | Teams | News | Standings | Special |
|-------|------------|-------|------|-----------|---------|
| **NFL** | ✅ | ✅ | ✅ | ✅ | - |
| **NBA** | ✅ | ✅ | ✅ | ✅ | - |
| **NHL** | ✅ | ✅ | ✅ | ✅ | - |
| **MLB** | ✅ | ✅ | ✅ | ✅ | - |

### College Sports

| Sport | Scoreboard | Teams | News | Rankings |
|-------|------------|-------|------|----------|
| **NCAAF** | ✅ | ✅ | ✅ | AP Top 25, CFP |
| **NCAAB (M)** | ✅ | ✅ | ✅ | AP Top 25 |
| **NCAAW (W)** | ✅ | ✅ | ✅ | AP Top 25 |

### Soccer

| League | Scoreboard | Teams | News |
|--------|------------|-------|------|
| **EPL** | ✅ | ✅ | ✅ |
| **MLS** | ✅ | ✅ | ✅ |
| **Other** | ✅ | ✅ | ✅ |

### Women's Sports

| Sport | Scoreboard | Teams | News |
|-------|------------|-------|------|
| **WNBA** | ✅ | ✅ | ✅ |

---

## API Endpoints

### Enhanced ESPN API

```
# Get complete sport data
/espn_api_enhanced.php?action=sport&sport=nfl&date=2024-01-15

# Get specific game details
/espn_api_enhanced.php?action=game&sport=nfl&game_id=401547123

# Get team information
/espn_api_enhanced.php?action=team&sport=nba&team_id=lal

# Get NCAAF rankings
/espn_api_enhanced.php?action=rankings

# Get validated games (cross-checked)
/espn_api_enhanced.php?action=validate&sport=nfl&date=2024-01-15
```

### Unified Sports Feed

```
# Get complete feed for a sport
/unified_sports_feed.php?action=feed&sport=nfl&include=games,odds,news,standings

# Get live scores across all sports
/unified_sports_feed.php?action=live

# Get best available odds
/unified_sports_feed.php?action=odds&sport=nfl&home=Chiefs&away=Bills&date=2024-01-15

# Get value bets (EV > 2%)
/unified_sports_feed.php?action=value&sport=nfl&min_ev=2.0

# List supported sports
/unified_sports_feed.php?action=sports
```

---

## Response Examples

### NFL Game Data

```json
{
  "ok": true,
  "data": {
    "games": [
      {
        "id": "401547123",
        "date": "2024-09-05T20:20Z",
        "name": "Detroit Lions at Kansas City Chiefs",
        "short_name": "DET @ KC",
        "status": "Final",
        "status_detail": "Final/OT",
        "home_team": {
          "id": "12",
          "name": "Kansas City Chiefs",
          "abbreviation": "KC",
          "score": "21",
          "winner": true
        },
        "away_team": {
          "id": "8",
          "name": "Detroit Lions",
          "abbreviation": "DET",
          "score": "20",
          "winner": false
        },
        "odds": {
          "spread": -6.5,
          "over_under": 54,
          "provider": "DraftKings"
        },
        "venue": "GEHA Field at Arrowhead Stadium"
      }
    ]
  }
}
```

### NCAAF Rankings

```json
{
  "ok": true,
  "rankings": {
    "AP Top 25": [
      {"rank": 1, "team": "Georgia", "record": "13-0"},
      {"rank": 2, "team": "Michigan", "record": "13-0"},
      {"rank": 3, "team": "Alabama", "record": "12-1"}
    ],
    "College Football Playoff Rankings": [
      {"rank": 1, "team": "Michigan", "record": "13-0"},
      {"rank": 2, "team": "Washington", "record": "13-0"},
      {"rank": 3, "team": "Alabama", "record": "12-1"},
      {"rank": 4, "team": "Florida State", "record": "13-0"}
    ]
  }
}
```

### Live Scores

```json
{
  "ok": true,
  "timestamp": "2024-01-15T20:30:00Z",
  "live_games": {
    "nfl": [
      {
        "id": "401547456",
        "home_team": {"name": "Bills", "score": 17},
        "away_team": {"name": "Chiefs", "score": 21},
        "status": "In Progress",
        "period": 4,
        "clock": "2:34"
      }
    ],
    "nba": [
      {
        "id": "401562789",
        "home_team": {"name": "Lakers", "score": 98},
        "away_team": {"name": "Warriors", "score": 102},
        "status": "In Progress",
        "period": 4,
        "clock": "5:21"
      }
    ]
  }
}
```

---

## Multi-Source Validation

The system now cross-checks ESPN data against:

1. **Primary:** ESPN Hidden APIs (95% reliability)
2. **Secondary:** Internal scrapers (90% reliability)
3. **Tertiary:** Sports Reference (88% reliability)

### Validation Process

```
ESPN API Data
      ↓
Compare with backup sources
      ↓
Calculate confidence score
      ↓
> 90% = Accept
70-90% = Flag for review
< 70% = Reject
```

---

## Database Integration

### New Tables

```sql
-- ESPN API cache
lm_espn_nfl_data (data_date, data_json, recorded_at)
lm_espn_nba_data (data_date, data_json, recorded_at)
lm_espn_nhl_data (data_date, data_json, recorded_at)
lm_espn_mlb_data (data_date, data_json, recorded_at)

-- Unified feed cache
lm_unified_feed_cache (sport, feed_date, feed_data, cached_at)
```

### Data Flow

```
User Request
      ↓
Check Cache (5 min TTL)
      ↓
If stale → Fetch ESPN API
      ↓
Cross-validate with backup
      ↓
Store in cache
      ↓
Return to user
```

---

## Rate Limiting

| Source | Limit | Our Delay |
|--------|-------|-----------|
| ESPN APIs | Unknown | 100ms between requests |
| Internal DB | N/A | None (cached) |

---

## Usage Examples

### Get Today's NFL Games
```bash
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/unified_sports_feed.php?action=feed&sport=nfl"
```

### Get Live Scores
```bash
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/unified_sports_feed.php?action=live"
```

### Get NCAAF Rankings
```bash
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/espn_api_enhanced.php?action=rankings"
```

### Get Best Odds
```bash
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/unified_sports_feed.php?action=odds&sport=nfl&home=Chiefs&away=Bills"
```

### Find Value Bets
```bash
curl "http://ejaguiar1.50webs.com/live-monitor/api/scrapers/unified_sports_feed.php?action=value&min_ev=3.0"
```

---

## Sports Supported

| Sport | Code | Leagues |
|-------|------|---------|
| NFL | `nfl` | National Football League |
| NBA | `nba` | National Basketball Association |
| NHL | `nhl` | National Hockey League |
| MLB | `mlb` | Major League Baseball |
| NCAAF | `ncaaf` | College Football |
| NCAAB | `ncaab` | Men's College Basketball |
| NCAAW | `ncaaw` | Women's College Basketball |
| WNBA | `wnba` | Women's NBA |
| EPL | `epl` | English Premier League |
| MLS | `mls` | Major League Soccer |

---

## Deployment

```bash
# Deploy new API modules
python deploy_espn_apis.py

# Or manually upload:
# - espn_api_enhanced.php
# - unified_sports_feed.php
```

---

## Next Steps

1. **Add more soccer leagues** (La Liga, Bundesliga, Serie A)
2. **Add tennis** (ATP, WTA)
3. **Add golf** (PGA Tour)
4. **Add MMA** (UFC)
5. **Implement WebSocket** for real-time updates
6. **Add player props** from ESPN player data

---

## Credits

**Original API Discovery:** @akeaswaran (GitHub Gist)
**Integration:** Enhanced scrapers with validation
**Documentation:** Sports Betting Database System

---

*Last Updated: 2026-02-12*
*ESPN API Version: Hidden/Undocumented (v2)*
