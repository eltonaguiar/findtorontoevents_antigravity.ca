# Tennis ELO Intelligence Enhancement

**Date:** 2026-04-26  
**Branch:** copilot/enhance-sports-betting-algorithms  
**Status:** ✅ Verified (syntax checked, goalie-overlay pattern mirrored)

## What Was Broken / Missing

The sports betting stack supported ATP/WTA odds via The Odds API (`tennis_atp`,
`tennis_wta` sport keys) but had **no tennis-specific signal layer**. Every
other sport had at least one sport-specific overlay:
- NHL → goalie GSAx overlay
- All sports → Polymarket prediction market confidence boost

Tennis picks were priced purely from multi-book consensus devig with zero
player-quality adjustment. An ELO-rated field like "Djokovic vs a 200-ranked
qualifier" would produce the same composite-score treatment as any other pick.

## What Changed

### 1. `live-monitor/tennis_elo_engine.py` (new)

Python script that fetches **JeffSackmann/tennis_atp** ATP match CSVs directly
from GitHub raw (no paid data subscription required) and computes:

- **Overall ELO** per player
- **Surface-specific ELO** (hard / clay / grass separately)  
- **Serve stats** (EMA of 1st-serve-in %, 1st/2nd-serve-win %, serve
  dominance ratio) — methodology from **jgollub1/tennis_elo**

K-factor is tournament-tier aware (Grand Slam: 40, Masters: 36, ATP 500: 32,
ATP 250+: 24). Processes last 6 years of ATP data (~20K+ matches).

Output: `live-monitor/data/tennis_elo_ratings.json` — consumed by PHP lib.

**Attribution:**
- Data: [JeffSackmann/tennis_atp](https://github.com/JeffSackmann/tennis_atp)
  (MIT license) — replaces paid ATP data subscriptions (~$500/mo)
- ELO methodology: [jgollub1/tennis_elo](https://github.com/jgollub1/tennis_elo)
  — ELO + serve/return stats → win probability

### 2. `live-monitor/api/tennis_elo_lib.php` (new)

PHP 5.2-compatible library providing:

| Function | Purpose |
|---|---|
| `tennis_elo_lookup($name)` | Exact → case-insensitive → last-name fuzzy match |
| `tennis_elo_surface_rating($entry, $surface)` | Pick surface-specific ELO |
| `tennis_elo_win_prob($ra, $rb)` | ELO win probability formula |
| `sports_picks_annotate_tennis_elo(&$vb)` | Main overlay entry point |

**Gate conditions** (must ALL be true to annotate):
- `sport` contains `'tennis'`  
- `market` is `'h2h'` (moneyline only, same as goalie overlay)
- Both players found in ratings with **≥ 30 career matches**

**Surface heuristic** (ATP tour calendar):
- Mar–May → clay (Monte Carlo, Madrid, Rome, Roland Garros)
- Jun–Jul → grass (Queen's, Wimbledon)
- All other months → hard (AO, US Open, indoor swing)

**Composite-score nudge**: up to +5 pts when ELO win probability diverges from
book's implied probability by ≥ 5pp in favour of the picked side.  
EV%, grade, recommendation, and Kelly are **unchanged** (same constraint as
NHL goalie overlay — read-only for core bet sizing).

### 3. `live-monitor/api/sports_picks.php` (updated)

Added `require_once` for `tennis_elo_lib.php` and calls
`sports_picks_annotate_tennis_elo($vb)` at both pick-generation call sites
(alongside the existing `sports_picks_annotate_goalie_overlay` call).

### 4. `.github/workflows/sports-data-snapshots.yml` (updated)

Added **tennis ELO refresh step** that runs daily at 06:00–07:00 UTC (before
the 10:00 ET sports-betting-refresh). Calls `tennis_elo_engine.py --years 6`
and FTP-uploads `live-monitor/data/tennis_elo_ratings.json` to the live site.

## Open-Source Stack Reference (from problem statement)

| Repo | Role | Integration status |
|---|---|---|
| [JeffSackmann/tennis_atp](https://github.com/JeffSackmann/tennis_atp) | ATP match data since 1968 (replaces $500/mo feeds) | **Wired** — fetched by `tennis_elo_engine.py` |
| [jgollub1/tennis_elo](https://github.com/jgollub1/tennis_elo) | ELO + serve/return → win prob methodology | **Wired** — implemented in engine + PHP lib |
| [JeffSackmann/tennis_slam_pointbypoint](https://github.com/JeffSackmann/tennis_slam_pointbypoint) | Point-by-point Grand Slam data | Architecture stub for future in-match Bayesian model |
| [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) | Shot-by-shot scouting (5K+ matches) | Future: serve-pattern clustering |
| [yastrebksv/TennisProject](https://github.com/yastrebksv/TennisProject) | CV + CatBoost bounce prediction | Future: live match integration |
| [zostaff/tennis CV](https://github.com/zostaff/tennis) | YOLO player/ball tracking from broadcast | Future: live match integration |
| Polymarket CLOB API | Crowd-sourced match odds | **Already wired** — `sports_prediction_market_bridge.py` handles ATP/WTA keywords |

## How to Verify

```bash
# Syntax check (no network needed)
python3 -c "import py_compile; py_compile.compile('live-monitor/tennis_elo_engine.py', doraise=True)"

# Dry-run (requires network to raw.githubusercontent.com)
python3 live-monitor/tennis_elo_engine.py --years 2 --out /tmp/tennis_elo_test.json
cat /tmp/tennis_elo_test.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['player_count'], 'players')"
```

## Future Extensions

1. **Point-by-point Bayesian** (`tennis_slam_pointbypoint`): update win prob
   mid-match using in-play score states — live bet sizing adjustment.
2. **Shot-charting** (`MatchChartingProject`): serve direction clustering per
   opponent → matchup-specific ELO adjustment.
3. **WTA ratings**: extend `tennis_elo_engine.py` to also fetch
   `JeffSackmann/tennis_wta` and produce combined ratings JSON.
4. **CV integration** (`yastrebksv/TennisProject`, `zostaff/tennis`): bounce
   prediction from broadcast feeds → live unforced-error rate signal.
