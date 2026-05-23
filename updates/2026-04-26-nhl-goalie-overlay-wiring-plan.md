# NHL Goalie Overlay — Opt-in Sidecar + Wiring Plan

**Date:** 2026-04-26
**Branch:** `feat/nhl-goalie-scraper`
**Author:** Claude Opus 4.7
**Status:** Phase 1 + Phase 2 LANDED (2026-04-26). Phase 2 wired the JSON feed into `sports_value_analyze_lib.php` (Shin output overlay) + surfaced `goalie_overlay_applied` / `goalie_shift_pp` via `sports_picks.php?action=today` + UI "G" badge in `sports-betting.html`. Phase 3 (A/B cohort analysis) still pending.

## What's in this PR

1. [tools/scrapers/nhl_goalie_scraper.py](tools/scrapers/nhl_goalie_scraper.py) — pulls today's NHL schedule from `api-web.nhle.com` (free, no key) and joins with MoneyPuck's `goalies.csv` (season-to-date GSAx/60, SV%, GP). Writes `live-monitor/data/nhl_goalies_today.json`. Stdlib + standard `urllib` only.
2. This wiring plan doc.

**Inert today.** No PHP code reads the JSON; no production behavior change. Per CLAUDE.md Wire-Up Rule, this PR title says "opt-in" and includes a Wiring Plan with target dates.

## Why ship the data feed first

The full goalie overlay (scoped previously by a Plan subagent) requires modifying `live-monitor/api/sports_value_analyze_lib.php` — but that file is currently being modified in PR #401 (Pinnacle Shin devig). Touching it on a third branch creates a guaranteed rebase conflict.

Splitting the work:
- **Phase 1 (this PR):** Python scraper + JSON output. Independent of `sports_value_analyze_lib.php`.
- **Phase 2 (after PR #401 merges):** new file `live-monitor/api/sports_value_nhl_goalie_lib.php` + 1 require_once + 1 call site in the analyzer. ~80 LoC, clean rebase.
- **Phase 3 (after 2 weeks of Phase 2):** A/B logging columns + cohort analysis.

## Adjustment formula (Phase 2 spec)

Compute `Δ = home.gsax_per60 - away.gsax_per60`. Apply only when both starters are confirmed AND both have `gp >= 10` this season.

```
shift_pp = clamp(Δ * 5.0, -5.0, +5.0)   # 0.5pp per 0.1 GSAx/60 delta, hard cap ±5pp
if home_goalie.rest_days == 0: shift_pp -= 1.0   # B2B penalty
if away_goalie.rest_days == 0: shift_pp += 1.0
p_home_adj = clamp(p_home + shift_pp/100, 0.01, 0.99)
p_away_adj = 1 - p_home_adj    # 2-way; 3-way preserves draw and renormalizes win sides
```

Hard cap ensures a single bad GSAx number can't move EV by more than 5pp.

## Target dates

| Phase | Action | Target date | Self-deletion if missed |
|---|---|---|---|
| Phase 1 (PR #403) | Land scraper + add cron entry | 2026-04-30 | DONE 2026-04-26 |
| Phase 2 | Wire PHP lib + analyzer hook (after PR #401 merges) | 2026-05-09 | DONE 2026-04-26 (`sports_value_nhl_goalie_lib.php` + analyzer hook + UI badge, branch `feat/nhl-goalie-overlay-phase2`) |
| Phase 3 | A/B logging + 60-bet cohort analysis | 2026-06-30 | If win rate < 45% with Wilson lower bound, kill the overlay |

## Operator step (Phase 1)

Add to deploy host crontab:

```
0 17 * * *  cd /home/findtorontoevents.ca && python3 tools/scrapers/nhl_goalie_scraper.py
```

Runs once daily at 13:00 ET (~6 hours before typical NHL puck drop, after most lineups confirm). Scraper exits 0 even on upstream failure so cron stays green.

## Why MoneyPuck + NHL API and not Daily Faceoff

MoneyPuck publishes a clean, dated CSV of season-to-date goalie metrics that's been stable since 2019. Daily Faceoff was the original choice in the Plan subagent's scope but requires HTML scraping and would break on every site redesign. The NHL public API (`api-web.nhle.com/v1/schedule/{date}`) provides confirmed starters when teams release lineups — same data Daily Faceoff sources from. Source consolidation: 2 stable APIs instead of 1 stable + 1 fragile.

Trade-off: NHL API only confirms starters when teams release lineups (typically ~2h pre-game). The 13:00 ET cron may run before lineups confirm; in that case `home_goalie` / `away_goalie` are null and the Phase 2 analyzer hook will fall through to Jensen-only pricing for that game. No regression vs current behavior.

## Test plan

- [ ] `python tools/scrapers/nhl_goalie_scraper.py --stdout` on a non-game day — should output `games: []` cleanly
- [ ] `python tools/scrapers/nhl_goalie_scraper.py --stdout` on a game day — should output ≥1 game with both teams populated
- [ ] When MoneyPuck CSV is unreachable — scraper logs error, writes `errors` field, exits 0
- [ ] Phase 2 dry-run after PR #401 merges: `sports_value_nhl_goalie_lib.php` returns `null` when JSON is missing; analyzer continues with Jensen-only

## Reversibility

- Set `nhl_goalie_overlay_enabled=0` in feature flags (Phase 2): all overlays disabled, but JSON keeps populating.
- Delete `live-monitor/data/nhl_goalies_today.json`: same effect — Phase 2 reader returns null, analyzer falls through.
- Revert this PR: scraper gone, no other production code references it.

## Wire-Up Rule compliance

This PR satisfies the **opt-in sidecar branch** of the Wire-Up Rule:
- PR title says "opt-in" ✅
- Module does not change production behavior ✅ (scraper writes a file no PHP code reads yet)
- Wiring Plan section names target caller file + function + expected date ✅ (Phase 2 target 2026-05-09; if it doesn't land by 2026-05-16, the doc commits to deletion)

## Out of scope (v1)

- Skater-level xG, line matchups, possession metrics
- Live in-game goalie pulls
- Per-period save percentage
- Refs / weather / B2B for skaters
- Other sports (NHL only)

The full Phase 2/3 spec is preserved in [updates/2026-04-26-pinnacle-shin-devig-anchor.md](updates/2026-04-26-pinnacle-shin-devig-anchor.md) "Follow-up #1" — landing here as a sidecar lets us validate the data feed independently before wiring into the analyzer.
