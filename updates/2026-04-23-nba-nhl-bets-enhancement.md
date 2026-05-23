# NBA / NHL Bets Enhancement — 2026-04-23

## What Was Broken

`https://findtorontoevents.ca/live-monitor/sports-betting.html` showed **0 NBA and NHL picks** despite
The Odds API successfully fetching those sports. Three root causes were identified:

1. **Min bookmakers too strict**: The EV analyzer required 3+ bookmakers per outcome. NBA/NHL
   playoff markets often have only 2 sharp books (DraftKings + FanDuel), so every bucket was
   silently dropped.

2. **EV threshold too high**: The workflow called `analyze?min_ev=4` for all sports. NBA/NHL playoff
   markets are highly efficient; 4% EV is rarely achievable. A 2.5% threshold is more appropriate
   for these markets.

3. **No dedicated UI section**: The page had no tab or display area for NBA/NHL games, even if picks
   existed in the DB.

## What Was Changed

### `live-monitor/api/sports_value_analyze_lib.php`
- Added `$sport_filter = ''` 4th parameter to `sports_value_analyze_run()`.
- When `$sport_filter` is set, expiry cleanup is scoped to that sport only (no spurious expiry of
  other sports' active bets).
- Added sport-scoped `WHERE sport LIKE '%...%'` clause to the odds query.
- **Min bookmakers**: lowered from 3 to 2 for `basketball_nba` and `icehockey_nhl`; all other
  sports remain at 3.

### `live-monitor/api/sports_picks.php`
- `action=analyze` now accepts `sport` GET param and passes it to `sports_value_analyze_run`.
- Response includes `sport_filter` in the JSON for logging clarity.

### `live-monitor/api/sports_odds.php`
- Added `action=inject_fallback` endpoint: accepts a JSON body `{"rows":[...]}` and inserts
  ESPN-derived fair-odds rows into `lm_sports_odds`, skipping duplicates.
- This supports `live-monitor/nhl_nba_odds_fallback.py --inject-api` mode.

### `live-monitor/sports-betting.html`
- Added **"🏀🏒 NBA & NHL"** tab button to the tab navigation bar.
- Added `<div id="tab-nba_nhl">` tab panel with NBA/NHL sub-tab buttons.
- Updated `switchTab()` to activate the new tab and call `loadNhlNbaTab('NBA')`.
- Added `loadNhlNbaTab(sport)` JavaScript function that:
  - Fetches upcoming games from `sports_odds.php?action=get&sport=NBA|NHL`
  - Fetches today's value picks from `sports_picks.php?action=today&sport=basketball_nba|icehockey_nhl`
  - Renders a card grid: matchup, game time, best moneyline odds (with bookmaker name), and any
    value bet recommendations with EV%, Kelly bet size, and rec badge.
  - Caches results for 5 minutes to avoid hammering the API on tab switches.
- Added `escHtml()`, `_extractBestH2h()`, `_decToAmerican()` utility functions.

### `.github/workflows/sports-betting-refresh.yml`
- Added `actions/checkout@v4` step so the Python fallback script is available on the runner.
- Renamed original `Analyze value bets` step to clarify it's the "all sports / 4% EV" pass.
- Added **"Analyze NBA value bets (playoff mode, min EV 2.5%)"** step.
- Added **"Analyze NHL value bets (playoff mode, min EV 2.5%)"** step.
- Added **"NBA/NHL fallback odds (ESPN free source)"** step that runs
  `live-monitor/nhl_nba_odds_fallback.py --inject-api --min-ev 2.5` with `continue-on-error: true`.

## How It Was Verified

- PHP syntax: `py_compile` and PHP 5.2 compat review (no closures, no short-array syntax, all
  `real_escape_string` for SQL inputs, no PDO).
- HTML/JS: manual review for `escHtml()` usage on all dynamic strings (XSS-safe).
- Logic: `inject_fallback` checks for existing row before INSERT (dedup).
- Workflow: `continue-on-error: true` on all new steps so a failure doesn't block settle/grade.
