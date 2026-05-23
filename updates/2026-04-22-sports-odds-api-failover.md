# Sports Odds API failover (live-monitor)

## What was wrong

- `sports_odds.php` (cron/refresh `action=fetch`) used `file_get_contents` only, so DNS/TLS/timeout and `allow_url_fopen` issues had no cURL-based retry path.
- `sports_scores_settle_lib.php` (`/scores` for pick/bet settlement) also used raw `file_get_contents` only.
- There was no region-taper retry when a transport call returned an empty body (e.g. hard timeout) before giving up for that sport.

## What changed

- New `live-monitor/api/odds_api_fetch.php`: `odds_api_http_get()` (cURL when present, else stream context + `file_get_contents`), and `odds_api_v4_get_odds_raw()` with region-taper **only** when the previous attempt returned no body (us,us2,uk,eu → us,us2 → us).
- `sports_odds.php`: require the helper, use it for fetches, add `candidates_tried` / `region_profile` (and `url` on `http_fail`) in `sport_details`.
- `sports_scores_settle_lib.php`: `require_once` the helper; scores URL uses `odds_api_http_get()`.

## How verified

- Manual review: PHP 5.2–compatible syntax (no `?:`, `??`, `[]`, closures); deploy workflow already uploads `live-monitor/api/*.php` including the new file.

## Related page

- https://findtorontoevents.ca/live-monitor/sports-betting.html — reads odds/DB via `sports_odds.php?action=get` and related endpoints; fetches that populate the cache use `action=fetch` (e.g. `sports-betting-refresh.yml`).
