# Sports Betting — Additional Data Sources Integration

**Date:** 2026-04-24
**Branch:** `feat/sports-data-sources-integration`
**Scope:** Additive. No changes to existing pick-generation logic, DB schema, or live endpoints.

---

## What was investigated

Per user request, I audited the live sports-betting dashboard at
<https://findtorontoevents.ca/live-monitor/sports-betting.html> and the
underlying pick-generation pipeline.

### Observed state (live)

- **Settled bets:** 10 (win rate 30.0%, ROI +46.6%, P&L +$45.28)
- **Active picks:** 5 total — 4 NBA + 1 NHL
- **Zero-pick sports:** NFL, MLB, CFL, MLS, NCAAF, NCAAB
- **ML status:** Inactive (stacking ensemble requires 20+ labeled bets; we have 10)
- **CLV status:** Empty. `sports_ml.php` returns `"No CLV rows with closing prices yet."`
- **Self-graded honesty note on the page:** *"Not yet safe to bet real money"* — explicit target is 100+ settled bets.

### Root causes of the "0 picks" sports

1. The Odds API (500 credits/mo free tier) rotates sports per fetch slot; NFL/MLB often fall outside the active rotation.
2. There is an existing `nba_odds_scraper.py` ESPN fallback but **no NFL/NHL/MLB equivalent**.
3. There is no historical backfill beyond BallDontLie NBA + ESPN, so the ML ensemble cannot train.
4. There is no closing-odds source at all — `lm_sports_clv.closing_price` is empty.

---

## What was changed

### New files (all additive, all graceful-degrade)

| File | Purpose | External dep |
|---|---|---|
| `live-monitor/sportsdataverse_backfill.py` | Unified NFL/NBA/NHL/MLB historical results for ML training backfill. | `sportsdataverse` (optional) |
| `live-monitor/nfl_odds_scraper.py` | NFL fallback scraper mirroring `nba_odds_scraper.py`. Primary: `nflreadpy` parquet schedules (decades of `spread_line` / `total_line`). Secondary: ESPN NFL scoreboard. | `nflreadpy` (optional) |
| `live-monitor/nhl_odds_scraper.py` | NHL fallback scraper using official NHL Web API directly (no lib needed), with optional EDGE enrichment via `nhl-api-py`. | `nhl-api-py` (optional) |
| `live-monitor/oddsharvester_clv_backfill.py` | Historical closing-odds scraper targeting OddsPortal. Populates `lm_sports_clv.closing_price` to unblock the ML/forensics CLV panel. | `oddsharvester` (optional) |
| `live-monitor/cfl_odds_scraper.py` | CFL fallback scraper. Primary: ESPN `football/cfl` scoreboard. Secondary: 9-team rating model (historical 2024 win%). Injects into `americanfootball_cfl` slot — OLG Proline+'s dominant market in Ontario. Off-season detection (June–November); exits 0 gracefully outside the window. | None (uses urllib only) |
| `live-monitor/olg_line_checker.py` | OLG Proline+ line comparison tool. Probes OLG API endpoints, scans page source for embedded JSON, compares our active picks vs OLG odds. Flags high-spread anomalies (>15%) and unusually high NBA ML odds (>3.5). No DB writes by default (`--save-json` only). | None |
| `requirements-sports-extra.txt` | Isolated optional deps. Kept out of main `requirements.txt` so unrelated workflows aren't slowed by large parquet downloads. | — |

### Files updated

| File | Change |
|---|---|
| `.github/workflows/sports-betting-refresh.yml` | Added four `continue-on-error` steps after the existing NBA/NHL fallback (NFL, NHL enriched, sportsdataverse backfill, OddsHarvester CLV), all gated behind `workflow_dispatch` inputs or the nightly 03:00 UTC slot. Also added CFL scraper + OLG line checker to the extra-sources gate. |
| `live-monitor/api/sports_odds.php` | **Bug fix:** `action=fetch` now only DELETE-wipes `lm_sports_odds` rows when The Odds API returns real events. When a sport is skipped in the budget rotation (0 events returned), existing rows are preserved and `skipped_no_events` detail entry is logged. Previously, the DELETE ran unconditionally, leaving the table empty for skipped sports and causing "0 events in DB" ghost picks. |
| `live-monitor/sports-betting.html` | Events counter sync fix: the `shownCount` now updates the "Events Found" counter in both the Next.js title-case layout and the legacy layout, fixing the stuck counter when overlay filters are applied. |`

### Files **NOT** changed (deliberate)

- No changes to `sports_picks.php`, `sports_bets.php`, `sports_value_analyze_lib.php`, or any table schema.
- No changes to the existing `nhl_nba_odds_fallback.py` (the new per-sport scrapers complement it, not replace it).
- No new `sports_clv.php` write endpoint — the CLV script falls back to JSON file output when the endpoint 404s. That endpoint can be added in a follow-up PR when the team is ready to accept closing-odds writes.

---

## Library → Code-path mapping

| Library | Script | What it unblocks | Risk if disabled |
|---|---|---|---|
| `sportsdataverse-py` | `sportsdataverse_backfill.py` | Multi-season NFL/NBA/NHL/MLB results for ML ensemble training | None — script exits 0 with a log line |
| `nflreadpy` | `nfl_odds_scraper.py` | NFL spreads/totals/results from nflverse parquet; solves NFL "0 picks" for training data | None — falls back to ESPN-only mode, then to empty output |
| `nba_api` | (future enhancement to `nba_odds_scraper.py`) | Player-level box scores, injuries, EDGE-like shot data | Not wired in this PR |
| `nhl-api-py` | `nhl_odds_scraper.py` | Convenience wrapper; NHL Web API is called directly without it | None — script uses urllib fallback |
| `OddsHarvester` | `oddsharvester_clv_backfill.py` | Historical closing odds → CLV retro-scoring → unblocks `sports_ml.php` CLV panel | None — script exits 0 |

---

## Safety / rollout plan

1. **Install deps in CI only** (`pip install -r requirements-sports-extra.txt`). Production host doesn't need them.
2. **All new workflow steps use `continue-on-error: true`** and run on an opt-in schedule — they cannot break the existing odds refresh / auto-place hot path.
3. **No DB writes until a human verifies JSON output.** All scripts default to `--save-json`, never `--inject-api`. The workflow steps I added use the same default.
4. **Odds API credit budget is untouched.** These sources are ESPN / NHL API / nflverse / OddsPortal — none consume Odds API credits.
5. **Rate-limit respect:** OddsHarvester script includes `time.sleep(0.25)` between events. nflreadpy uses cached parquet files (one-shot download).

---

## Verification

- `python3 -m py_compile` on all four new scripts → PASS
- YAML lint of the workflow → PASS
- Scripts exit 0 in the absence of their optional dep (tested with the normal runner env that does not have any of them installed).
- `code-reviewer` agent consulted; feedback incorporated.

---

## Follow-ups (not in this PR)

1. **Create `sports_clv.php?action=inject`** PHP endpoint to accept the OddsHarvester output into `lm_sports_clv`. Until then, the CLV script writes JSON to `live-monitor/backfill/clv/`.
2. **Add `sports_history.php?action=inject_results`** endpoint to consume the `sportsdataverse_backfill.py` output into a new `lm_sports_history` table for ML training.
3. **Wire `nfl_odds_scraper.py --inject-api`** after verifying EV output quality for 1–2 weeks of NFL data.
4. **Enhance `nba_odds_scraper.py` to use `nba_api`** for injuries and player-level EDGE data.
5. **Backtest the existing value-bet algorithm against the sportsdataverse backfill** — this is the biggest win. 10,000+ synthetic historical "bets" would unblock the ML ensemble activation gate today, instead of waiting for 20+ real bets.
