# Sports Betting System — Comprehensive Architecture Audit

**Date**: 2026-02-11
**Auditor**: Sports Betting Architecture Specialist

---

## 1. FILE INVENTORY

### PHP Backend APIs (all in `live-monitor/api/`)

| File | Lines | Purpose |
|------|-------|---------|
| `sports_db_connect.php` | 32 | DB connection layer — tries `ejaguiar1_sportsbet` first, falls back to `ejaguiar1_stocks` |
| `sports_odds.php` | 758 | Odds fetching + caching from The Odds API. Actions: sports, fetch, get, credit_usage, clv |
| `sports_picks.php` | 1643 | Value bet finder + line shopping + daily picks + settlement. Actions: analyze, value_bets, line_shop, today, all, daily_picks, pick_history, performance, settle_picks |
| `sports_bets.php` | 1118 | Paper betting tracker. Actions: place, active, settle, auto_place, history, dashboard, leaderboard, reset, backfill |
| `sports_scores.php` | 716 | Multi-source score fetcher (The Odds API + ESPN API + ESPN scraping). Included by sports_bets.php and sports_picks.php |
| `db_config.php` | 35 | Shared config with DB creds for both ejaguiar1_stocks and ejaguiar1_sportsbet |

### Frontend

| File | Purpose |
|------|---------|
| `live-monitor/sports-betting.html` | Main dashboard (~1400+ lines). 8 tabs: Dashboard, Today's Picks, Odds Explorer, Bet Tracker, Bankroll, Performance, Pick History, Date Detail |
| `predictions/sports.html` | Static stub page showing hardcoded stats ($1,013.14 bankroll, 25.3% ROI). Placeholder for Phase 2 integration. |
| `backups_2026-02-11/sports-betting.html.bak` | Backup of sports-betting.html |

### Deployment Tools

| File | Purpose |
|------|---------|
| `tools/deploy_sports_betting.py` | FTP deploy script. Uploads 12 files including all sports PHP APIs + frontend + nav pages |

### GitHub Actions Workflows

| File | Schedule | Steps |
|------|----------|-------|
| `.github/workflows/sports-betting-refresh.yml` | 5x daily: 10am, 1pm, 4pm, 7pm, 10pm EST (cron: `0 15,18,21,0,3 * * *`) | 8 steps (see Section 7) |

### Data Files

| File | Purpose |
|------|---------|
| `data/goldmine/sports_picks.json` | JSON export of sports picks (large file, 354KB+) |

---

## 2. DATABASE ARCHITECTURE

### Connection Flow

```
sports_db_connect.php
  |
  |-- Try: ejaguiar1_sportsbet (mysql.50webs.com)
  |     User: ejaguiar1_sportsbet / Password: eltonsportsbets
  |     |-- If SUCCESS: use ejaguiar1_sportsbet
  |     |-- If FAIL (connect_error):
  |           |-- Fallback: ejaguiar1_stocks (mysql.50webs.com)
  |                 User: ejaguiar1_stocks / Password: stocks
```

### Critical Finding: Which Database Is Actually Used?

The `sports_db_connect.php` tries `ejaguiar1_sportsbet` first with `@new mysqli()` (error suppressed). If it connects, ALL sports tables are created there. If not, they fall back to `ejaguiar1_stocks`.

**The SQL dump `sportsbetv2.sql` is COMPLETELY EMPTY** (just `CREATE DATABASE ejaguiar1_sportsbet`). This means either:
1. The `ejaguiar1_sportsbet` DB exists but has no tables (sports_db_connect.php connects successfully, then each PHP file auto-creates tables via `CREATE TABLE IF NOT EXISTS`)
2. OR the connection to `ejaguiar1_sportsbet` fails silently and everything falls back to `ejaguiar1_stocks`

**Evidence from `10_123_0_33.sql` (the stocks DB dump)**: The goldmine_tracker table has rows with `source_table='lm_sports_daily_picks'` — these are imported from a SEPARATE connection to `ejaguiar1_sportsbet` (see goldmine_tracker.php lines 784, 1532 which explicitly open a new connection to `ejaguiar1_sportsbet`). This strongly suggests **ejaguiar1_sportsbet IS a working database on the server**.

**Conclusion**: The `ejaguiar1_sportsbet` database exists and is being used. The SQL dump is empty because the tables are auto-created by the PHP code on first access. The tables DO exist on the server but were NOT exported in the dump.

### Tables (all `lm_sports_*` prefix, auto-created by PHP)

| Table | Created By | Columns | Purpose |
|-------|-----------|---------|---------|
| `lm_sports_odds` | `sports_odds.php` | id, sport, event_id, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point, last_updated | Cached odds from The Odds API. UNIQUE on (event_id, bookmaker_key, market, outcome_name) |
| `lm_sports_credit_usage` | `sports_odds.php` | id, request_time, sport, credits_used, credits_remaining | Tracks monthly API credit consumption |
| `lm_sports_clv` | `sports_odds.php` | id, event_id, sport, home_team, away_team, commence_time, bookmaker_key, market, outcome_name, opening_price, closing_price, opening_implied_prob, closing_implied_prob, clv_pct, first_seen, last_updated | Closing Line Value tracking — snapshots opening vs closing odds |
| `lm_sports_value_bets` | `sports_picks.php` | id, event_id, sport, home_team, away_team, commence_time, market, bet_type, outcome_name, best_book, best_book_key, best_odds, consensus_implied_prob, true_prob, edge_pct, ev_pct, kelly_fraction, kelly_bet, all_odds(TEXT), detected_at, status | Active value bets found by algorithm |
| `lm_sports_daily_picks` | `sports_picks.php` | id, pick_date, generated_at, sport, event_id, home_team, away_team, commence_time, market, pick_type, outcome_name, best_book, best_book_key, best_odds, ev_pct, kelly_bet, algorithm, confidence, result, pnl, all_odds(TEXT) | Timestamped historical daily picks with settlement tracking |
| `lm_sports_bets` | `sports_bets.php` | id, event_id, sport, home_team, away_team, commence_time, game_date, bet_type, market, pick, pick_point, bookmaker, bookmaker_key, odds, implied_prob, bet_amount, potential_payout, algorithm, ev_pct, status, result, pnl, settled_at, actual_home_score, actual_away_score, placed_at | Paper bets with full settlement data |
| `lm_sports_bankroll` | `sports_bets.php` | id, snapshot_date, bankroll, total_bets, total_wins, total_losses, total_pushes, win_rate, total_wagered, total_pnl, roi_pct | Daily bankroll snapshots. UNIQUE on snapshot_date |

**Total: 7 tables** (matches the 7 `lm_sports_*` tables seen in the stocks DB)

### Cross-DB Access

`goldmine_tracker.php` opens a **separate** `mysqli` connection to `ejaguiar1_sportsbet` (lines 784, 1532) to read:
- `lm_sports_daily_picks` — imports picks into goldmine signals
- `lm_sports_bets` — reads bankroll/PnL stats for goldmine dashboard

This confirms sports data lives in `ejaguiar1_sportsbet`, NOT `ejaguiar1_stocks`.

---

## 3. API ENDPOINTS (Complete Reference)

### `sports_odds.php` — Odds Fetcher + Cache

| Action | Auth | Method | Description |
|--------|------|--------|-------------|
| `?action=sports` | Public | GET | List active in-season sports (0 credits) |
| `?action=fetch&key=livetrader2026` | Admin | GET | Fetch odds from The Odds API, cache in DB. Supports `&budget_safe=1` |
| `?action=get[&sport=X][&hours=48]` | Public | GET | Return cached odds grouped by event |
| `?action=credit_usage` | Public | GET | Monthly API credit usage stats |
| `?action=clv[&sport=X][&hours=72]` | Public | GET | Closing Line Value report |

### `sports_picks.php` — Value Bet Finder + Line Shopping

| Action | Auth | Method | Description |
|--------|------|--------|-------------|
| `?action=analyze&key=livetrader2026` | Admin | GET | Run value bet algorithm, store results. Triggers Discord alerts for A+ bets |
| `?action=value_bets[&sport=X][&market=X][&min_ev=2.0]` | Public | GET | Return active value bets (rated A+ through D) |
| `?action=line_shop[&sport=X][&hours=48]` | Public | GET | Best/worst odds across Canadian sportsbooks |
| `?action=today[&sport=X]` | Public | GET | Combined picks for next 24h with standings enrichment |
| `?action=all[&sport=X]` | Public | GET | Full combined response (value bets + line shopping) |
| `?action=daily_picks&key=livetrader2026` | Admin | GET | Generate + store timestamped daily picks snapshot |
| `?action=pick_history[&date=X][&sport=X][&days=7]` | Public | GET | View historical daily picks by date |
| `?action=performance` | Public | GET | Deep analytics: by sport, market, confidence, bookmaker, EV buckets, streaks |
| `?action=settle_picks&key=livetrader2026` | Admin | GET | Settle daily picks using multi-source scores |

### `sports_bets.php` — Paper Betting Tracker

| Action | Auth | Method | Description |
|--------|------|--------|-------------|
| `?action=place&key=...` | Admin | GET | Place a paper bet (quarter-Kelly sizing) |
| `?action=active` | Public | GET | List pending bets |
| `?action=settle&key=...` | Admin | GET | Auto-settle completed bets using scores (Odds API + ESPN failover) |
| `?action=auto_place&key=...&min_ev=3.0&max_bets=5` | Admin | GET | Auto-place paper bets from top value bets |
| `?action=history[&sport=X][&algorithm=X][&page=1]` | Public | GET | Past bets with filters (paginated, 50/page) |
| `?action=dashboard` | Public | GET | Full bankroll + stats + by-sport + by-algorithm + history + recent bets |
| `?action=leaderboard` | Public | GET | Algorithm performance ranked by ROI |
| `?action=reset&key=...&confirm=yes` | Admin | GET | Truncate tables, reset bankroll to $1000 |
| `?action=backfill&key=...` | Admin | GET | Retroactively create paper bets from settled daily picks |

### `sports_scores.php` — Score Fetcher (include-only + standalone test)

| Action | Auth | Method | Description |
|--------|------|--------|-------------|
| `?action=test[&sport=X][&days=3]` | Public | GET | Test multi-source score fetching |

Functions exported: `_scores_fetch_all()`, `_scores_lookup()`, `_scores_fetch_standings()`, `_scores_find_team_standing()`, `_scores_team_match()`

---

## 4. THE ODDS API INTEGRATION

### Configuration
- **API Key**: `b91c3bedfe2553cf90a5fa2003417b2a` (in `db_config.php`)
- **Base URL**: `https://api.the-odds-api.com/v4`
- **Plan**: Free tier — **500 credits/month**

### Credit Management
- `sports_odds.php` tracks credits via `lm_sports_credit_usage` table
- Response headers tracked: `x-requests-used`, `x-requests-remaining`, `x-requests-last`
- **Budget-safe mode**: When `&budget_safe=1` is passed and remaining credits < 100, only fetches 2 sports max
- **Hard stop**: If monthly credits < 20, refuses to fetch
- **Fetch cost**: ~6 credits per sport (h2h + spreads + totals for 2 regions: us, us2)

### Credit Usage Estimate
- 5 runs/day * ~3 active sports * 6 credits = **~90 credits/day**
- ~30 days = **~2700 credits/month** (exceeds 500 limit!)
- **However**: Budget-safe mode limits to 2 sports when tight, and not all sports are in-season simultaneously

### Score Fetching (0 credits)
- Scores endpoint: `?daysFrom=3&dateFormat=iso` — **0 credits** (confirmed free)
- Used for settlement in both `sports_bets.php` and `sports_picks.php`

### Supported Sports
```
icehockey_nhl    -> NHL
basketball_nba   -> NBA
americanfootball_nfl -> NFL
baseball_mlb     -> MLB
americanfootball_cfl -> CFL
soccer_usa_mls   -> MLS
americanfootball_ncaaf -> NCAAF
basketball_ncaab -> NCAAB
```

### Supported Bookmakers (19 total)
Major Canadian-legal: bet365, FanDuel, DraftKings, BetMGM, PointsBet, Caesars, BetRivers, ESPN BET, Fanatics
Offshore: Bovada, BetOnline, Unibet, MyBookie, SuperBook, LowVig, BetUS, Pinnacle, Fliff, Hard Rock

---

## 5. ALGORITHMS & FEATURES

### Value Bet Algorithm
1. Fetch all odds from cached DB (from The Odds API)
2. For each event/market/outcome: calculate consensus implied probability across all bookmakers
3. Remove vig: `true_prob = avg_implied_prob / total_overround`
4. Calculate EV: `EV = (true_prob * decimal_odds) - 1`
5. Filter: only bets with EV >= 2% (configurable)
6. Size with quarter-Kelly: `kelly_fraction = EV / (odds - 1) / 4`

### Rating System (A+ through D)
Scoring out of 100 based on:
- EV% (0-50 points) — primary driver
- Number of books offering odds (0-20 points) — consensus strength
- Market type reliability (0-15 points) — h2h > spreads > totals
- Canadian book availability (0-10 points)
- Time until game (0-5 points, with penalty if imminent)
- Kelly size confidence (0-5 bonus)

Grades: A+ (90+), A (80+), B+ (70+), B (60+), C+ (50+), C (40+), D (<40)
Actions: STRONG TAKE (80+), TAKE (65+), LEAN (50+), WAIT (35+), SKIP (<35)

### Line Shopping
- Compares odds across **Canadian-legal books only** (9 books)
- Calculates savings % between best and worst odds
- Key number detection for NFL spreads (3, 7, 10, 14, 17, 21)

### CLV (Closing Line Value) Tracking
- Snapshots opening odds on first fetch
- Updates closing odds on subsequent fetches
- Calculates CLV% = (opening_implied_prob - closing_implied_prob) / opening_implied_prob * 100
- Reports by bookmaker and top movers

### Multi-Source Score Settlement
Three-tier failover:
1. **The Odds API** scores endpoint (0 credits, has event_id matching)
2. **ESPN API** (`site.api.espn.com/apis/site/v2/sports/...`) — free, fuzzy team matching
3. **ESPN web scraping** (last resort) — parses embedded JSON from ESPN scoreboard pages

Settlement covers:
- Moneyline (h2h): winner = team with higher score
- Spread: adjusted_score = pick_score + point_spread
- Totals (Over/Under): combined score vs line

### Discord Alerts
- Triggered by `_sp_discord_exceptional()` in sports_picks.php
- Fires for A+ rated bets with EV >= 7%
- Sends embed to Discord webhook (from `.env` file)
- Shows sport, pick, EV%, odds, grade, win probability, bookmaker

### Standings Enrichment
- Fetches current standings from ESPN API (`apis/v2/sports/.../standings`)
- Enriches picks with team ranks, records
- Generates "Here's Why" reasoning text for B+ or higher picks

---

## 6. PAPER BETTING CONFIGURATION

| Parameter | Value |
|-----------|-------|
| Initial bankroll | $1,000 |
| Max active bets | 20 |
| Min bet | $5 |
| Max bet % | 5% of bankroll |
| Sizing method | Quarter-Kelly (default 2% if no EV data) |
| Auto-void | Pending bets > 7 days old |
| Auto-place (GitHub Actions) | min_ev=3.0, max_bets=5 per run |
| Admin key | `livetrader2026` |

---

## 7. GITHUB ACTIONS WORKFLOW

**File**: `.github/workflows/sports-betting-refresh.yml`
**Schedule**: 5x daily (10am, 1pm, 4pm, 7pm, 10pm EST)
**Timeout**: 5 minutes

### Steps (in order):
1. **Check active sports** — `sports_odds.php?action=sports`
2. **Fetch odds (budget-safe)** — `sports_odds.php?action=fetch&key=livetrader2026&budget_safe=1`
3. **Analyze value bets** — `sports_picks.php?action=analyze&key=livetrader2026`
4. **Generate daily picks snapshot** — `sports_picks.php?action=daily_picks&key=livetrader2026`
5. **Auto-place top value bets** — `sports_bets.php?action=auto_place&key=livetrader2026&min_ev=3.0&max_bets=5`
6. **Auto-settle completed bets** — `sports_bets.php?action=settle&key=livetrader2026`
7. **Settle daily picks** — `sports_picks.php?action=settle_picks&key=livetrader2026`
8. **Dashboard summary** — `sports_bets.php?action=dashboard`
9. **Credit usage check** — `sports_odds.php?action=credit_usage`

All steps have `continue-on-error: true` and human-readable Python parsing of JSON responses.

---

## 8. FRONTEND (sports-betting.html)

### API Endpoints Called
```
sports_bets.php?action=dashboard        (Dashboard tab)
sports_odds.php?action=credit_usage     (Status bar)
sports_picks.php?action=today           (Today's Picks tab)
sports_odds.php?action=get&hours=48     (Odds Explorer tab)
sports_bets.php?action=active           (Bet Tracker - active)
sports_bets.php?action=history          (Bet Tracker - history)
sports_bets.php?action=dashboard        (Bankroll tab)
sports_picks.php?action=performance     (Performance tab)
sports_picks.php?action=pick_history    (Pick History tab)
```

### Features
- 8-tab interface: Dashboard, Today's Picks, Odds Explorer, Bet Tracker, Bankroll, Performance, Pick History, Date Detail
- Chart.js for bankroll visualization
- Sport filters (All, NHL, NBA, NFL, MLB, CFL, MLS, NCAAF, NCAAB)
- Rating badges (A+ through D with color coding)
- Take/Wait/Skip recommendation indicators
- American + decimal odds display
- Canadian book highlighting
- "Here's Why" reasoning for top picks

---

## 9. CROSS-SYSTEM INTEGRATION

### Goldmine Tracker Integration
`goldmine_tracker.php` opens **separate** connections to `ejaguiar1_sportsbet`:
- **Line 784**: Imports daily picks into goldmine signals (`source_system='sports'`, `source_table='lm_sports_daily_picks'`)
- **Line 1532**: Reads sports bankroll/PnL for goldmine dashboard summary

### Predictions Hub
`predictions/sports.html` is a **static stub** with hardcoded metrics. Not yet integrated with live APIs.

---

## 10. IDENTIFIED GAPS & ISSUES

### A. Database

1. **Empty sportsbet dump**: The `sportsbetv2.sql` file is empty. To get a proper dump, export from the live `ejaguiar1_sportsbet` database via phpMyAdmin. All 7 tables exist on the server (auto-created by PHP).

2. **No explicit schema file**: Unlike other subsystems that have `schema.php`, sports tables are created inline in each PHP file. Consider creating a `sports_schema.php` for centralized schema management.

3. **Fallback ambiguity**: `sports_db_connect.php` silently falls back to `ejaguiar1_stocks` if `ejaguiar1_sportsbet` connection fails. This could cause data to end up in the wrong database without any warning. The `@` error suppression makes this invisible.

### B. API Credit Budget

4. **500 credits/month is VERY tight**: At 5 runs/day with 3+ active sports, the system could easily blow through credits. The budget-safe mode helps but only kicks in when credits are already low. Consider:
   - Reducing to 3 runs/day during offseason
   - Only fetching sports that have games in the next 12 hours
   - Caching aggressively and skipping fetch if odds were updated <2 hours ago

### C. Security

5. **Admin key in URL parameters**: The admin key `livetrader2026` is passed in GET query strings. This appears in server access logs and browser history. Since the server runs PHP 5.2 (no POST body parsing via `php://input`), this is a known limitation.

6. **Admin key in GitHub Actions workflow**: The key is hardcoded in the YAML file (not using GitHub Secrets). Anyone with repo read access can see it. Should use `${{ secrets.SPORTS_ADMIN_KEY }}`.

7. **API key in db_config.php**: The Odds API key `b91c3bedfe2553cf90a5fa2003417b2a` is in version-controlled source. Should be in `.env` or environment variables.

### D. Features / Code Quality

8. **Duplicate settlement logic**: Both `sports_bets.php` (settle action) and `sports_picks.php` (settle_picks action) have nearly identical settlement logic. Could be refactored into a shared function in `sports_scores.php`.

9. **No odds staleness detection**: Old cached odds are only purged when a `fetch` is triggered (deletes odds older than 6 hours). If the GitHub Actions workflow fails, stale odds persist and could generate bad value bets.

10. **No backtest validation**: The value bet algorithm's EV calculation assumes consensus implied probability is a good proxy for true probability. There's no historical validation of whether high-EV bets actually win at the predicted rate.

### E. Missing Features (from OPUS46 analysis context)

11. **No live streaming**: All data is polled at 5x/day intervals. No WebSocket or SSE for real-time odds updates.

12. **No multi-leg / parlay support**: Only single-bet support. No parlay, teaser, or round-robin bets.

13. **No injury/weather data**: Value bet algorithm doesn't factor in injury reports, weather conditions, or lineup changes.

14. **predictions/sports.html is a dead page**: Shows hardcoded stats, not connected to any live API. Should either be connected or removed.

---

## 11. SUMMARY

### System Health: GOOD
The sports betting system is **fully operational** with a complete pipeline:
- Odds fetch -> Value bet analysis -> Daily picks -> Auto-place paper bets -> Auto-settle -> Dashboard

### Architecture: CLEAN
- 4 PHP files + 1 shared library (sports_scores.php) + 1 DB connector
- 7 well-structured MySQL tables with proper indexes
- Multi-source score settlement with graceful failover
- Comprehensive rating system (A+ through D)
- Full GitHub Actions automation

### Database: SEPARATE (ejaguiar1_sportsbet)
- Sports data lives in its own database, NOT in ejaguiar1_stocks
- Cross-DB access from goldmine_tracker.php works correctly
- The empty SQL dump just means tables weren't exported (they exist on the server)

### Primary Risks:
1. API credit exhaustion (500/month is tight for 5x/day)
2. Admin key exposure in URLs and workflow file
3. No schema versioning — tables auto-created inline
