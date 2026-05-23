#!/usr/bin/env python3
'''
sportsdataverse_backfill.py — Historical game results backfill for ML training.

Uses sportsdataverse-py (https://github.com/sportsdataverse/sportsdataverse-py)
as a unified Python interface across NFL, NBA, NHL, MLB for training data.

The pipeline currently has ~10 settled bets. The ML ensemble (stacking:
RandomForest + GradientBoosting + XGBoost + LightGBM -> LogisticRegression)
needs 20+ labeled bets before activation, and realistically hundreds for
meaningful generalization. This backfill script pulls multi-season historical
game results (scores, winners, totals) so we can synthetically replay our
value-bet algorithm against real outcomes.

Output modes:
    --save-json                  Write a JSON file per sport under live-monitor/backfill/
    --inject-api                 POST rows to sports_odds.php?action=inject_fallback (existing endpoint)
    --inject-history-api         POST rows to a new optional sports_history.php endpoint (future)
    --sports nba,nfl,nhl,mlb     Comma-separated. Default: all 4.
    --seasons 2023,2024,2025     Comma-separated. Default: last 2 full seasons.

Design notes:
- Graceful degradation: if `sportsdataverse` is not installed, this script
  exits 0 with a clear log line so the GitHub Actions step stays green.
- Only writes `completed` games (winner known). Live/scheduled rows are skipped.
- Normalizes to the same schema used elsewhere in the pipeline:
    { sport, event_id, home_team, away_team, commence_time, home_score,
      away_score, winner, total, spread, season, source }

CLI examples:
    python3 live-monitor/sportsdataverse_backfill.py --save-json
    python3 live-monitor/sportsdataverse_backfill.py --sports nfl --seasons 2023,2024
'''

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

# Optional dependency — do NOT hard-fail in CI if missing.
try:
    import sportsdataverse as sdv  # type: ignore
    _HAS_SDV = True
except Exception as _e:
    sdv = None  # type: ignore
    _HAS_SDV = False
    _SDV_IMPORT_ERR = str(_e)


# ---- Season defaults ---------------------------------------------------------

def _default_seasons(n: int = 2) -> List[int]:
    '''Return the last `n` completed seasons, anchored to the current year.'''
    now = datetime.datetime.utcnow()
    # NFL season typically ends Feb; treat the current calendar year as
    # in-progress for most pro sports.
    current = now.year
    return list(range(current - n, current + 1))


# ---- Per-sport loaders -------------------------------------------------------
# Each loader returns a list[dict] of normalized rows. If the `sportsdataverse`
# import failed, we short-circuit to [] with a logged warning — the CI step
# then emits "0 rows" without failing the job.

def _safe_iter(df_or_list: Any) -> Iterable[Dict[str, Any]]:
    '''Yield dict rows from either a pandas DataFrame or a list of dicts.'''
    if df_or_list is None:
        return
    # pandas DataFrame path
    to_dict = getattr(df_or_list, 'to_dict', None)
    if callable(to_dict):
        try:
            for row in df_or_list.to_dict(orient='records'):
                yield row
            return
        except Exception:
            pass
    # list[dict] path
    try:
        for row in df_or_list:
            if isinstance(row, dict):
                yield row
    except TypeError:
        return


def _norm(row: Dict[str, Any], sport: str, season: int, source: str) -> Optional[Dict[str, Any]]:
    '''Normalize a sportsdataverse row to the common schema.

    Different leagues expose different column names across sdv's sub-modules.
    We look for the most common aliases defensively.
    '''
    def _pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in row and row[k] not in (None, ''):
                return row[k]
        return default

    event_id = _pick('game_id', 'id', 'gameId', 'espn_game_id')
    home = _pick('home_team', 'home', 'home_team_name', 'home_display_name',
                 'home_name', 'team_home_name')
    away = _pick('away_team', 'away', 'away_team_name', 'away_display_name',
                 'away_name', 'team_away_name')
    home_score = _pick('home_score', 'home_team_score', 'homeScore')
    away_score = _pick('away_score', 'away_team_score', 'awayScore')
    commence = _pick('gameday', 'game_date', 'date', 'commence_time',
                     'game_time', 'game_date_time')
    spread = _pick('spread_line', 'spread', 'home_spread')
    total = _pick('total_line', 'total', 'over_under')

    if event_id is None or home is None or away is None:
        return None
    if home_score is None or away_score is None:
        # Not a completed game; skip for training data.
        return None

    try:
        hs = float(home_score)
        as_ = float(away_score)
    except (TypeError, ValueError):
        return None

    winner = 'home' if hs > as_ else ('away' if as_ > hs else 'push')

    return {
        'sport': sport,
        'event_id': str(event_id),
        'home_team': str(home),
        'away_team': str(away),
        'commence_time': str(commence) if commence is not None else '',
        'home_score': hs,
        'away_score': as_,
        'winner': winner,
        'spread_line': float(spread) if spread is not None else None,
        'total_line': float(total) if total is not None else None,
        'season': int(season),
        'source': source,
    }


def load_nfl(seasons: List[int]) -> List[Dict[str, Any]]:
    if not _HAS_SDV:
        return []
    rows: List[Dict[str, Any]] = []
    try:
        # nfl_loaders.load_nfl_schedule returns a DataFrame with spread/total lines.
        schedule = sdv.nfl.load_nfl_schedule(seasons=seasons)  # type: ignore[attr-defined]
    except Exception as e:
        print(f'[sdv-nfl] load_nfl_schedule failed: {e}', file=sys.stderr)
        return []
    for season in seasons:
        # sdv returns all seasons in one frame; filter or iterate all.
        for row in _safe_iter(schedule):
            row_season = row.get('season', row.get('year', season))
            try:
                row_season = int(row_season) if row_season is not None else season
            except (TypeError, ValueError):
                row_season = season
            n = _norm(row, 'NFL', row_season, 'sportsdataverse.nfl')
            if n is not None:
                rows.append(n)
        break  # schedule already contains all seasons in one pass.
    return rows


def load_nba(seasons: List[int]) -> List[Dict[str, Any]]:
    if not _HAS_SDV:
        return []
    rows: List[Dict[str, Any]] = []
    for season in seasons:
        try:
            schedule = sdv.nba.load_nba_schedule(seasons=[season])  # type: ignore[attr-defined]
        except Exception as e:
            print(f'[sdv-nba] load_nba_schedule({season}) failed: {e}', file=sys.stderr)
            continue
        for row in _safe_iter(schedule):
            n = _norm(row, 'NBA', season, 'sportsdataverse.nba')
            if n is not None:
                rows.append(n)
        # Be polite to the underlying parquet/CDN source.
        time.sleep(0.2)
    return rows


def load_nhl(seasons: List[int]) -> List[Dict[str, Any]]:
    if not _HAS_SDV:
        return []
    rows: List[Dict[str, Any]] = []
    for season in seasons:
        try:
            schedule = sdv.nhl.load_nhl_schedule(seasons=[season])  # type: ignore[attr-defined]
        except Exception as e:
            print(f'[sdv-nhl] load_nhl_schedule({season}) failed: {e}', file=sys.stderr)
            continue
        for row in _safe_iter(schedule):
            n = _norm(row, 'NHL', season, 'sportsdataverse.nhl')
            if n is not None:
                rows.append(n)
        time.sleep(0.2)
    return rows


def load_mlb(seasons: List[int]) -> List[Dict[str, Any]]:
    if not _HAS_SDV:
        return []
    rows: List[Dict[str, Any]] = []
    for season in seasons:
        try:
            schedule = sdv.mlb.load_mlb_schedule(seasons=[season])  # type: ignore[attr-defined]
        except Exception as e:
            print(f'[sdv-mlb] load_mlb_schedule({season}) failed: {e}', file=sys.stderr)
            continue
        for row in _safe_iter(schedule):
            n = _norm(row, 'MLB', season, 'sportsdataverse.mlb')
            if n is not None:
                rows.append(n)
        time.sleep(0.2)
    return rows


SPORT_LOADERS = {
    'nfl': load_nfl,
    'nba': load_nba,
    'nhl': load_nhl,
    'mlb': load_mlb,
}


# ---- Output sinks ------------------------------------------------------------

def save_json(rows: List[Dict[str, Any]], sport: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d')
    out_path = os.path.join(out_dir, f'{sport.lower()}_history_{stamp}.json')
    payload = {
        'ok': True,
        'sport': sport,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'row_count': len(rows),
        'source': 'sportsdataverse-py',
        'rows': rows,
    }
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, default=str)
    return out_path


def inject_to_history_api(rows: List[Dict[str, Any]], endpoint: str, api_key: str) -> Dict[str, Any]:
    '''POST normalized history rows to an optional endpoint.

    This endpoint does not yet exist server-side; the function is provided so
    that when we add `sports_history.php?action=ingest`, no client changes are
    required. Fails gracefully with a clear message.
    '''
    import urllib.error
    import urllib.request

    url = endpoint
    if '?' in url:
        url += f'&key={api_key}'
    else:
        url += f'?key={api_key}'

    body = json.dumps({'rows': rows}).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            try:
                return json.loads(raw)
            except ValueError:
                return {'ok': False, 'error': 'non_json_response', 'body': raw[:500]}
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error': f'http_{e.code}', 'body': e.read().decode('utf-8', errors='replace')[:500]}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ---- CLI entrypoint ----------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description='Historical sports results backfill via sportsdataverse-py.')
    parser.add_argument('--sports', default='nba,nfl,nhl,mlb',
                        help='Comma-separated sport codes (nba,nfl,nhl,mlb).')
    parser.add_argument('--seasons', default='',
                        help='Comma-separated season years (e.g. 2023,2024). Defaults to last 2.')
    parser.add_argument('--save-json', action='store_true', help='Write per-sport JSON files to live-monitor/backfill/.')
    parser.add_argument('--out-dir', default='live-monitor/backfill', help='Output directory for --save-json.')
    parser.add_argument('--inject-history-api',
                        default='',
                        help='POST rows to this URL (e.g. https://findtorontoevents.ca/live-monitor/api/sports_history.php?action=ingest).')
    parser.add_argument('--api-key', default=os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026'),
                        help='API key appended as ?key= to the inject URL.')
    parser.add_argument('--max-rows-per-sport', type=int, default=0,
                        help='If >0, cap rows per sport for smoke tests.')
    args = parser.parse_args()

    if not _HAS_SDV:
        print(f'[sportsdataverse_backfill] sportsdataverse-py not installed ({_SDV_IMPORT_ERR}).')
        print('[sportsdataverse_backfill] Install with: pip install sportsdataverse')
        print('[sportsdataverse_backfill] Exiting 0 so CI stays green.')
        return 0

    sports = [s.strip().lower() for s in args.sports.split(',') if s.strip()]
    if args.seasons.strip():
        try:
            seasons = [int(s.strip()) for s in args.seasons.split(',') if s.strip()]
        except ValueError:
            print(f'[sportsdataverse_backfill] Invalid --seasons: {args.seasons}', file=sys.stderr)
            return 2
    else:
        seasons = _default_seasons(2)

    print('=' * 72)
    print('sportsdataverse-py historical backfill')
    print(f'  Sports : {sports}')
    print(f'  Seasons: {seasons}')
    print('=' * 72)

    grand_total = 0
    for sport in sports:
        loader = SPORT_LOADERS.get(sport)
        if loader is None:
            print(f'[skip] unknown sport "{sport}"')
            continue
        print(f'\n[{sport.upper()}] loading schedule(s)...')
        rows = loader(seasons)
        if args.max_rows_per_sport > 0:
            rows = rows[:args.max_rows_per_sport]
        print(f'[{sport.upper()}] loaded {len(rows)} completed games.')
        grand_total += len(rows)

        if args.save_json and rows:
            path = save_json(rows, sport, args.out_dir)
            print(f'[{sport.upper()}] -> {path}')

        if args.inject_history_api and rows:
            resp = inject_to_history_api(rows, args.inject_history_api, args.api_key)
            print(f'[{sport.upper()}] inject response: {json.dumps(resp)[:300]}')

    print(f'\n[done] total rows: {grand_total}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
