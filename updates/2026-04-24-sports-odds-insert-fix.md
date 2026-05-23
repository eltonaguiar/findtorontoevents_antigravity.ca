# Sports odds fetch: 0 `odds_rows` fix (2026-04-24)

## Symptom

- `sports_odds.php?action=get&hours=48` returned **0 events** (empty `lm_sports_odds` for upcoming games).
- `action=fetch` reported **events_cached** (e.g. 12–24) but **odds_rows: 0** for every sport, so `sports_picks` / value logic had no NBA/NHL lines.
- `sports_picks?action=today` showed only stale MLS lines from an old `lm_sports_daily_picks` date.

## Root cause

1. **Duplicate `INSERT`:** Re-fetching the same events re-ran `INSERT` into `lm_sports_odds` without clearing, so many hosts hit **unique / duplicate** failures (silent), leaving **odds_rows: 0**. Fixed with **`DELETE` upcoming rows per sport** before insert, plus `sport_details` diagnostics.
2. **Empty `bookmakers` from The Odds API:** The API sometimes (or in certain shapes) returns **event shells with `bookmakers: []`**. The code **returned that payload immediately** and **never** fell through to the ESPN/secondary chain, so the DB had nothing to store. Fixed in `odds_api_get_events_with_failover`: if no event has any bookmakers, treat as miss and **fall through** to `odds_api_events_from_espn` (and existing NBA model fallback for NBA). Also unwraps a top-level `{"data":[...]}` JSON wrapper if the API ever returns it.

## Fix (PHP 5.2–safe, `live-monitor/api/sports_odds.php`)

1. **Before** inserting rows for a sport, `DELETE` upcoming odds for that `sport` where `commence_time >= NOW()` so each fetch replaces the snapshot.
2. **`sports_odds_norm_team()`** for API team fields; normalize `outcome` `name` if it is ever an array.
3. On failed `INSERT`, increment **`insert_failures`** and store **`first_mysql_error`** (and **`first_event_bookmakers`** when 0 rows) in **`sport_details`** in the JSON response for debugging.

## After deploy: validate

```bash
curl -s "https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=fetch&key=livetrader2026&budget_safe=1" | head -c 2000
# Expect odds_rows > 0, sport_details[].odds_rows > 0 for NBA/NHL when games exist.

curl -s "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=analyze&key=livetrader2026&min_ev=4" | head -c 1500
curl -s "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=daily_picks&key=livetrader2026" | head -c 1500
```

Or trigger: **Actions → “Sports Betting Odds Refresh & Auto-Settle” → Run workflow**.
