# 2026-04-26 — Mercury sports-betting feedback (PR 1 of 4)

## Source

Mercury "Sports Betting System Analysis & Strategy" report (April 2026), reviewed against:

- Live URL: https://findtorontoevents.ca/live-monitor/sports-betting.html
- Database extract: `ejaguiar1_sportsbet.zip` (this repo)

## Scope

This PR delivers **Phase 0 (foundations) + Phase 1 items 1–3 (odds history, steam-move detector, arbitrage scanner) + Phase 1 item 5 (WNBA filter)** from the integration plan agreed in the prior analysis PR. Phases 2–4 are deferred to PR 2–4 because they depend on paid-API authorization (Odds API paid tier, Prediction Hunt Dev key, OpenWeatherMap) and on the freshness of the Polymarket whale list — both flagged as open questions in the plan.

## What changed

### Schema (`live-monitor/sql/sports_plan_migrations_v2.sql` — new)

10 `CREATE TABLE IF NOT EXISTS` blocks (idempotent, MyISAM to match the rest of the schema):

- `lm_sports_odds_history` — rolling odds snapshots, 30-day prune cadence (Phase 1.1)
- `lm_sports_steam_moves` — coordinated line-move detections (Phase 1.2)
- `lm_sports_arbs` — two-leg arbitrage opportunities (Phase 1.3)
- `lm_predmarket_quotes`, `lm_predmarket_ev_signals` — Prediction Hunt persistence (Phase 1.4 / 2.6, schema only)
- `lm_event_weather` — OpenWeatherMap snapshots (Phase 2.7, schema only)
- `lm_nhl_goalie_starts` — NHL situational input (Phase 2.8, schema only)
- `lm_esports_odds` — CS2/LoL pilot table (Phase 2.9, schema only)
- `lm_polymarket_wallets`, `lm_polymarket_positions` — whale tracker (Phase 2.10, schema only)

Tables for Phase 2 ship as schema only so subsequent PRs can add producers without a second migration round trip against the live DB.

### Producers / scanners (PHP, all PHP 5.2 compatible)

- `live-monitor/api/sports_odds.php` — every successful `INSERT IGNORE INTO lm_sports_odds` is now mirrored to `lm_sports_odds_history` with `snapshot_at = NOW()`. Failures are silent so the primary write path is never blocked.
- `live-monitor/api/sports_steam_detector.php` (new) — CLI/web entrypoint. Reads the last `2 * window_minutes` from history, groups by `(event_id, market, outcome_name)`, compares each book's earliest "old" sample to its latest "new" sample, and writes a `lm_sports_steam_moves` row when ≥3 books move ≥0.05 in decimal odds (or ≥0.5 pts for spreads/totals) in the same direction. Duplicate suppression: skips emission if the same `(event, market, outcome, direction)` already has a row inside the window.
- `live-monitor/api/sports_arb_scanner.php` (new) — CLI/web entrypoint. Iterates current `lm_sports_odds` rows grouped by `(event_id, market, abs(point))`, finds the best price per outcome across books, and emits a `lm_sports_arbs` row for every 2-outcome pair where `1/odds_a + 1/odds_b < 1.0 - fees_pct` and `net_edge ≥ 0.5%`. Reuses `sports_value_quote_usable()` from the existing analyzer to filter out exchange/outlier prices. Existing `open` rows are refreshed on re-detection and auto-closed when the scan no longer finds them.

### Read APIs (PHP)

- `live-monitor/api/sports_steam.php` (new) — JSON read for the UI tab. Filters: `hours`, `sport`, `limit`.
- `live-monitor/api/sports_arb.php` (new) — JSON read with computed stake-share-percent per leg. Filters: `status`, `hours`, `sport`, `limit`.

### UI (`live-monitor/sports-betting.html`)

- New tabs **⚡ Arbitrage** and **🔥 Steam Moves** (between Odds Comparison and My Bets).
- New **WNBA** sport-filter button.
- Footer disclaimer expanded to clarify arbs/steam are display-only and the platform remains paper-only.
- `switchTab()` matcher generalized to handle multiple emoji-labeled tabs (`nba_nhl`, `arbs`, `steam`).
- New `fetchArbs()` / `fetchSteam()` JS handlers; auto-refresh inherits from the existing 5-min `setInterval`.

### Sport list (`live-monitor/api/sports_odds.php`)

- Added `basketball_wnba` (short=`WNBA`) to `$SPORT_TARGETS` so the existing odds-fetch cron picks it up automatically once The Odds API key is enabled.
- Added the `WNBA` LIKE branch to the `?action=get` filter.

### Config (`live-monitor/api/db_config.php`)

- Two new env-only slots (no committed values): `PREDICTION_HUNT_API_KEY`, `OPENWEATHER_API_KEY`. PR 2/3 wires the consumers.

## What's NOT in this PR (deferred per plan)

- **Phase 1 item 4 (Prediction Hunt free tier)** — schema is ready; the `predhunt_fetch.php` consumer + UI cross-reference column ship in PR 2.
- **Phase 2 items 6–10** — schema-only here; consumers ship in PR 3 and PR 4.
- **Phase 3** (RLM, Dixon-Coles, promotions) and **Phase 4** (ML activation, real-money) — out of scope.

## Verification

- `php -l` clean on all new/modified PHP files (`db_config.php`, `sports_odds.php`, `sports_steam_detector.php`, `sports_steam.php`, `sports_arb_scanner.php`, `sports_arb.php`).
- HTML script-tag balance preserved (6 open / 6 close `<script>` tags, including 1 deferred external Chart.js).
- SQL parsed: 10 `CREATE TABLE IF NOT EXISTS` blocks, each terminated by `) ENGINE=MyISAM`. No `DROP`, no `ALTER`, no destructive statements.
- All `IF NOT EXISTS`, so re-running on the live `ejaguiar1_sportsbet` DB is safe even if a partial earlier apply happened.

## Deployment notes (for the host operator)

1. Backup `ejaguiar1_sportsbet` before applying the migration (per repo policy):
   `mysqldump --opt ejaguiar1_sportsbet > backups/ejaguiar1_sportsbet_$(date +%F).sql`
2. Apply the migration:
   `mysql ejaguiar1_sportsbet < live-monitor/sql/sports_plan_migrations_v2.sql`
3. The history table is auto-populated by the existing odds cron — no other producer cron needed for PR 1.
4. Add two cron entries (or extend the existing `goldmine_maintenance.php` schedule):
   - Steam detector: `*/5 * * * *  curl -fsSL "https://findtorontoevents.ca/live-monitor/api/sports_steam_detector.php?key=livetrader2026&window=15" >/dev/null`
   - Arb scanner:    `*/5 * * * *  curl -fsSL "https://findtorontoevents.ca/live-monitor/api/sports_arb_scanner.php?key=livetrader2026" >/dev/null`
5. Optional history-prune cron (recommended after 30 days of growth):
   `15 4 * * *  mysql ejaguiar1_sportsbet -e "DELETE FROM lm_sports_odds_history WHERE snapshot_at < NOW() - INTERVAL 30 DAY"`

## Risk / rollback

- All changes are additive. To roll back: drop the 10 new tables, revert the four touched files (`sports_odds.php`, `sports-betting.html`, `db_config.php`, no schema removal needed for the `_v2.sql` file). The existing paper-bet tracker is unaffected because the new history mirror uses `@$sports_mysqli->query(...)` so any failure on the new table is silent.
- No new external API dependency in PR 1 (Odds API paid-tier is **not** activated; the existing 2-3h refresh continues to feed history at the same cadence).
