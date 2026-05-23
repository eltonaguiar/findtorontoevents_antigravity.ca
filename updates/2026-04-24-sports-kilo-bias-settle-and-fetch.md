# Sports betting: ESPN soft-line bias, settlement aliases, fetch rotation (2026-04-24)

## Context

Analysis noted (1) **ESPN API fallback** rows (`bookmaker_key=espn_api`) can read as +EV when they are a **single** recreational line, not a sharp consensus, (2) **only MLS** showing when budget rotation alternated half the leagues, (3) **settlement** misses when The Odds API team strings differ from pick strings (e.g. “… FC”).

## Code changes

1. **`sports_value_analyze_lib.php` — `sports_value_quote_usable`**
   - Excludes **`espn_api`** (ESPN scoreboard / synthetic) from consensus and from value-bet math so those lines are not used like multi-book devig.

2. **`sports_odds.php` — `budget_safe`**
   - Every run fetches **NBA + NHL** plus two other sports in a 3-step rotation (was alternating whole league groups, which skipped NBA/NHL for half the daily runs).

3. **`odds_api_fetch.php` — `odds_api_v4_get_odds_raw`**
   - Does not stop on the first **non-empty HTTP** body: tries **region** candidates until a response includes **at least one** event with `bookmakers`, or returns the last body for downstream ESPN failover (keeps `odds_api_get_events_with_failover` behavior).

4. **`sports_scores_settle_lib.php` — `sports_scores_team_aliases`**
   - Strips common club suffixes (`fc`, `sc`, `cf`, `afc`) to match scoreboard short/long names, and adds a `… fc` variant for a pick without suffix.

## Not done here

- **Higher min_ev** for soccer/MLS (would wire `min_ev` in `sports_picks` analyze and/or `sports-betting-refresh` workflow).
- **ML “filter”** for historical tickets — policy change, not a one-line code fix.

## Verify

- After deploy, run a fetch + `action=analyze` and confirm `lm_sports_value_bets` does not use `espn_api` as best book when The Odds API has real books.
- Re-run `settle_by_scores` / `settle_picks` for a case that previously 14d-voided on name mismatch (optional).
