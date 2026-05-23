# Sports Betting Failover APIs — Implementation Report

**Date:** 2026-04-23  
**Author:** Antigravity  
**Status:** Deployed to feature branch → PR

---

## Problem

The sports betting live monitor at `findtorontoevents.ca/live-monitor/sports-betting.html` relied on a **single data source** (ESPN) for all team intelligence, injury reports, schedule data, and standings across NBA, NHL, NFL, and MLB. This created a critical single point of failure — if ESPN changed their API structure, rate-limited requests, or went down temporarily, the entire intelligence pipeline would fail silently.

## Solution

Implemented a **multi-source failover architecture** with 7+ free API sources organized in cascading chains per sport and data type.

### Architecture (3-tier cascade)

```
┌─────────────────────────────────────────────────┐
│  Tier 1: PHP Failover Proxy (server-side)       │
│  sports_failover_proxy.php                      │
│  Cascades: ESPN → NHL API → MLB API → NBA CDN   │
│            → BallDontLie → TheSportsDB          │
├─────────────────────────────────────────────────┤
│  Tier 2: Client-Side Direct APIs                │
│  sports-failover.js                             │
│  Falls back to direct CORS-enabled API calls    │
├─────────────────────────────────────────────────┤
│  Tier 3: SessionStorage Cache                   │
│  5-minute TTL stale cache as last resort        │
└─────────────────────────────────────────────────┘
```

### Failover Sources Per Sport

| Sport | Source 1 (Primary) | Source 2 | Source 3 | Source 4 |
|-------|-------------------|----------|----------|----------|
| **NBA** | ESPN v2 API | NBA CDN (`cdn.nba.com`) | BallDontLie API | TheSportsDB |
| **NHL** | ESPN v2 API | NHL Web API (`api-web.nhle.com`) | TheSportsDB | — |
| **NFL** | ESPN v2 API | TheSportsDB | — | — |
| **MLB** | ESPN v2 API | MLB Stats API (`statsapi.mlb.com`) | TheSportsDB | — |

All sources are **free tier / no-auth** (or use free API keys included in config).

## Files Changed

### New Files

| File | Description |
|------|-------------|
| `live-monitor/api/sports_failover_config.php` | Failover chain definitions for all sports × data types |
| `live-monitor/api/sports_failover_proxy.php` | Unified proxy with parsers for 8 different API formats |
| `live-monitor/sports-failover.js` | Client-side failover wrapper with cache + health panel |

### Modified Files

| File | Changes |
|------|---------|
| `live-monitor/sports-betting.html` | Added failover JS include; updated documentation (known flaws, roadmap Phase 6, benchmark table) |
| `live-monitor/sports-betting.js` | `fetchSportStats()` now tries failover proxy first; added `fetchSportStatsDirect()` as backward-compatible fallback |

## Verification

### Health Check Endpoint
```
GET /live-monitor/api/sports_failover_proxy.php?action=health
```
Returns per-source latency and status for all configured failover chains.

### Source Listing
```
GET /live-monitor/api/sports_failover_proxy.php?action=sources
```
Lists all configured failover sources (with API keys masked).

### Manual Fetch
```
GET /live-monitor/api/sports_failover_proxy.php?sport=NBA&type=standings
GET /live-monitor/api/sports_failover_proxy.php?sport=NHL&type=standings
GET /live-monitor/api/sports_failover_proxy.php?sport=MLB&type=scoreboard
```

### UI Health Panel
Navigate to **System Analysis** tab → scroll to "🔄 Failover API Health" panel.

## Backward Compatibility

- If `sports-failover.js` fails to load, `sports-betting.js` falls back to original direct PHP endpoint calls
- Existing `nba_stats.php`, `nhl_stats.php`, etc. remain untouched and functional
- The failover proxy is a new endpoint — no existing APIs are modified
- SessionStorage cache provides a final safety net even if all APIs fail

## Known Limitations

1. **TheSportsDB** provides team metadata but not live standings (no W-L records)
2. **BallDontLie** free tier is limited in data — primarily team rosters, not full stats
3. **Injury failover** currently ESPN-only — no free alternatives discovered for structured injury data
4. **Client-side direct API calls** may be blocked by CORS on some APIs (ESPN CORS headers are permissive; MLB/NHL less so)
5. Health check uses HEAD requests which some APIs don't support — may show false negatives
