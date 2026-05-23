# PR: Additional Failover APIs for Sports Betting Monitor

**Date:** 2026-04-22  
**Author:** Roo (AI Assistant)  
**Status:** Ready for Review  
**Target:** `main` branch  

## Summary

This PR introduces a comprehensive failover system for the sports betting monitor at `https://findtorontoevents.ca/live-monitor/sports-betting.html`. The system provides multiple fallback data sources when the primary The Odds API is unavailable, rate-limited, or returns empty data.

## Problem Statement

The current sports betting implementation relies solely on The Odds API (500 credits/month free tier). When this API is:
- Rate limited (monthly quota exceeded)
- Temporarily down
- Returning empty data for specific sports

The system has no fallback, resulting in:
- Empty odds tables
- No new picks being generated
- Users seeing "No odds data available" messages

## Solution

Implemented a 4-tier failover architecture:

### Tier 1: Primary API
- **The Odds API** (`sports_odds.php?action=fetch`)
- Full odds data with 9+ bookmakers
- Real-time updates

### Tier 2: Failover APIs (NEW)
- **ESPN API** (free, no rate limits) - NBA, NHL, NFL, MLB scoreboards
- **BallDontLie API** (free tier) - NBA games and scores
- **Database Cache** - Last 6 hours of cached odds

### Tier 3: Health Monitoring (NEW)
- Real-time health checks for all data sources
- Automatic failover activation
- Credit usage monitoring with alerts

### Tier 4: Cache Management (NEW)
- Cache warming when credits are low
- Stale data cleanup
- Cache statistics and monitoring

## Files Added

### 1. `live-monitor/api/sports_odds_failover.php`
Multi-source odds failover API with automatic source selection.

**Endpoints:**
- `?action=status` - Check health of all failover sources
- `?action=get&source=auto` - Auto-select best available source
- `?action=get&source=espn` - Force ESPN API
- `?action=get&source=balldontlie` - Force BallDontLie API
- `?action=get&source=cache` - Force database cache

**Features:**
- Fuzzy team name matching
- Cache age tracking
- Source availability detection
- Response format compatible with primary API

### 2. `live-monitor/api/sports_scores_failover.php`
Multi-source game scores and settlement API.

**Endpoints:**
- `?action=status` - Check scores source health
- `?action=get_scores` - Fetch game scores
- `?action=settle_pending&key=livetrader2026` - Auto-grade pending bets

**Features:**
- ESPN scoreboard integration
- BallDontLie game results
- Automatic bet settlement from scores
- Pending bet matching by event_id or team names

### 3. `live-monitor/api/sports_health.php`
Comprehensive health monitoring API.

**Endpoints:**
- `?action=ping` - Quick connectivity test
- `?action=full` - Complete system health check
- `?action=db` - Database health only
- `?action=apis` - External API status only
- `?action=credits` - Credit usage status
- `?action=pending` - Pending bets status

**Health Checks:**
- Database connectivity and table status
- The Odds API latency and availability
- ESPN API availability (4 sports)
- BallDontLie API availability
- Monthly credit usage (500 limit)
- Stale pending bets (14+ days)

**Response includes:**
```json
{
  "status": "healthy|warning|degraded|critical",
  "issues": ["list of problems"],
  "recommendations": {
    "primary_api": "use_primary|use_failover",
    "failover_chain": "espn|balldontlie|cache_only",
    "settlement": "run_settlement|ok"
  }
}
```

### 4. `live-monitor/api/sports_cache.php`
Cache management and warming API.

**Endpoints:**
- `?action=stats` - Cache statistics
- `?action=warm&key=livetrader2026` - Warm cache from primary API
- `?action=clear_stale&hours=24` - Remove stale entries
- `?action=clear_all&key=livetrader2026` - Clear all odds (DANGER)

**Features:**
- Credit-aware warming (stops at 480/500 credits)
- UPSERT operations (update existing, insert new)
- Stale data cleanup (configurable age)
- Detailed statistics per table

### 5. `live-monitor/sports-betting-failover.js`
Client-side failover integration.

**Features:**
- Automatic failover chain execution
- Health check on page load
- Visual status indicators (live/cached/failover)
- User notification banners for failover activation
- Cache pre-warming when credits low
- Retry logic with exponential backoff

**Failover Chain:**
1. Try primary API (15s timeout)
2. Try failover auto-select (ESPN → BallDontLie → Cache)
3. Show appropriate UI indicators
4. Log all failover events to console

## Files Modified

### `live-monitor/sports-betting.html`
Added script include for failover client:
```html
<script src="sports-failover.js"></script>
<script src="sports-betting-failover.js"></script>  <!-- NEW -->
<script src="sports-betting.js"></script>
```

## Testing

### Manual Test Checklist

1. **Health Check**
   ```bash
   curl "https://findtorontoevents.ca/live-monitor/api/sports_health.php?action=full"
   ```
   - Verify all components return `ok: true`
   - Check credit usage percentage
   - Confirm no critical issues

2. **Failover Odds**
   ```bash
   # Test auto failover
   curl "https://findtorontoevents.ca/live-monitor/api/sports_odds_failover.php?action=get&source=auto&sport=NBA"
   
   # Test ESPN specifically
   curl "https://findtorontoevents.ca/live-monitor/api/sports_odds_failover.php?action=get&source=espn&sport=NBA"
   
   # Test cache fallback
   curl "https://findtorontoevents.ca/live-monitor/api/sports_odds_failover.php?action=get&source=cache&sport=all"
   ```

3. **Failover Scores**
   ```bash
   curl "https://findtorontoevents.ca/live-monitor/api/sports_scores_failover.php?action=get_scores&source=auto&days=3"
   ```

4. **Cache Management**
   ```bash
   # View stats
   curl "https://findtorontoevents.ca/live-monitor/api/sports_cache.php?action=stats"
   
   # Warm cache (requires key)
   curl "https://findtorontoevents.ca/live-monitor/api/sports_cache.php?action=warm&key=livetrader2026"
   ```

5. **Browser Integration**
   - Load sports-betting.html
   - Open DevTools Network tab
   - Verify `sports-betting-failover.js` loads
   - Check console for "[Failover]" log messages
   - Confirm health check runs on load

### Expected Behavior

| Scenario | Expected Result |
|----------|-----------------|
| Primary API works | Data from The Odds API, green "live" indicator |
| Primary API fails | Automatic failover to ESPN/BallDontLie, yellow "cached" indicator |
| All APIs fail | Falls back to database cache, shows "(cached)" indicator |
| Credits > 90% | Console warning, cache warming initiated |
| Credits exhausted | Automatic failover activation, no primary API calls |

## Security Considerations

- All admin endpoints (`warm`, `clear_all`, `settle_pending`) require `key=livetrader2026`
- Database queries use parameterized escaping
- No sensitive data exposed in health checks
- SSL verification disabled for external APIs (hosting requirement)

## Performance Impact

- **Health checks:** 5s timeout, non-blocking
- **Failover chain:** 15s timeout per attempt, max 3 attempts
- **Cache warming:** 60s timeout, runs in background
- **Database:** Indexed queries on `last_updated`, `event_id`

## Rollback Plan

If issues occur:
1. Remove `<script src="sports-betting-failover.js">` from HTML
2. Original `fetchOdds()` function remains untouched as fallback
3. API files can be deleted without affecting existing functionality

## Future Enhancements

- WebSocket integration for real-time odds updates
- Additional sports sources (Yahoo Sports, CBS Sports)
- Machine learning-based source quality scoring
- User preference for data source selection
- Historical failover success rate analytics

## Documentation

- API documentation embedded in PHP files
- Client-side JSDoc comments
- Console logging for debugging
- Health dashboard in System Analysis tab (existing)

---

**Testing completed:** All 4 new APIs tested locally, client integration verified  
**Ready for deployment:** Yes  
**Breaking changes:** None (additive only)