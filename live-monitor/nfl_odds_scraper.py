#!/usr/bin/env python3
'''
nfl_odds_scraper.py — NFL fallback scraper (mirrors nba_odds_scraper.py).

Primary data source: nflreadpy (the official successor to nfl_data_py), which
pulls pre-processed .parquet files from the nflverse repository. This gives us
decades of NFL schedules, spreads, totals, and results for free with zero API
credits. Secondary fallback: ESPN NFL scoreboard JSON (already used elsewhere
in the pipeline).

Why this module exists:
  The sports betting dashboard currently shows 0 picks for NFL because the
  Odds API is only queried once per rotation slot (see sports_odds.php
  budget_safe rotation). When NFL is out of rotation, the analyzer has nothing
  to chew on. This script produces ESPN+nflverse-derived fair-odds rows that
  can be injected into lm_sports_odds via the existing
  sports_odds.php?action=inject_fallback endpoint.

Usage:
    python3 live-monitor/nfl_odds_scraper.py                      # preview
    python3 live-monitor/nfl_odds_scraper.py --save-json           # write JSON
    python3 live-monitor/nfl_odds_scraper.py --inject-api          # push into DB
    python3 live-monitor/nfl_odds_scraper.py --min-ev 2.5          # filter EV

Graceful degradation: missing nflreadpy falls back to ESPN-only mode. Missing
ESPN falls back to empty output (still exit 0 in CI).
'''

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

try:
    import nflreadpy as nfl  # type: ignore
    _HAS_NFLREADPY = True
except Exception as _e:
    nfl = None  # type: ignore
    _HAS_NFLREADPY = False
    _NFLREADPY_ERR = str(_e)

ESPN_NFL_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
CANADIAN_BOOKS = ('fanduel', 'draftkings', 'betmgm', 'pointsbet', 'caesars', 'bet365')


# ---- Helpers -----------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; nfl-scraper)'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print(f'[http] {url}: {e}', file=sys.stderr)
        return None


def _american_from_prob(prob: float) -> int:
    '''Convert a fair win probability (0-1) to American odds (no vig added).'''
    p = max(0.02, min(0.98, float(prob)))
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def _decimal_from_american(american: int) -> float:
    '''Convert American odds to decimal (Odds API native format).'''
    a = int(american)
    if a > 0:
        return round(1.0 + a / 100.0, 4)
    return round(1.0 + 100.0 / abs(a), 4)


def _calc_ev_pct(decimal_odds: float, true_prob: float) -> float:
    '''EV% relative to stake 1.0 at the given decimal odds and true probability.'''
    return round(100.0 * (true_prob * (decimal_odds - 1.0) - (1.0 - true_prob)), 2)


# ---- nflreadpy-backed historical / schedule context --------------------------

def load_team_power_ratings(seasons: List[int]) -> Dict[str, Dict[str, float]]:
    '''Compute simple power ratings (points scored / allowed per game) from
    nflreadpy schedule data over the given seasons.

    Returns:
        { team_abbrev: {'pf_pg': float, 'pa_pg': float, 'games': int, 'win_pct': float} }
    '''
    if not _HAS_NFLREADPY:
        return {}
    try:
        games = nfl.load_schedules(seasons=seasons)  # type: ignore[attr-defined]
    except Exception as e:
        print(f'[nflreadpy] load_schedules failed: {e}', file=sys.stderr)
        return {}

    stats: Dict[str, Dict[str, float]] = {}

    # `games` is a polars or pandas DataFrame depending on nflreadpy version.
    to_dict = getattr(games, 'to_dicts', None) or getattr(games, 'to_dict', None)
    if to_dict is None:
        return {}
    try:
        rows = games.to_dicts() if hasattr(games, 'to_dicts') else games.to_dict(orient='records')
    except Exception:
        return {}

    for row in rows:
        home_score = row.get('home_score')
        away_score = row.get('away_score')
        if home_score is None or away_score is None:
            continue
        home = row.get('home_team') or ''
        away = row.get('away_team') or ''
        try:
            hs = float(home_score)
            as_ = float(away_score)
        except (TypeError, ValueError):
            continue
        for team, pf, pa, won in ((home, hs, as_, hs > as_), (away, as_, hs, as_ > hs)):
            if not team:
                continue
            s = stats.setdefault(team, {'pf_pg': 0.0, 'pa_pg': 0.0, 'games': 0.0, 'wins': 0.0})
            s['games'] += 1
            s['pf_pg'] += pf
            s['pa_pg'] += pa
            if won:
                s['wins'] += 1

    # Normalize to per-game averages and win pct.
    out: Dict[str, Dict[str, float]] = {}
    for team, s in stats.items():
        g = max(1.0, s['games'])
        out[team] = {
            'pf_pg': round(s['pf_pg'] / g, 2),
            'pa_pg': round(s['pa_pg'] / g, 2),
            'games': int(s['games']),
            'win_pct': round(s['wins'] / g, 3),
        }
    return out


# ---- ESPN scoreboard ---------------------------------------------------------

def fetch_espn_nfl_events() -> List[Dict[str, Any]]:
    data = _http_get_json(ESPN_NFL_SCOREBOARD)
    if not data:
        return []
    events_out: List[Dict[str, Any]] = []
    for event in data.get('events', []) or []:
        comps = event.get('competitions') or []
        if not comps:
            continue
        comp = comps[0]
        teams = comp.get('competitors') or []
        if len(teams) < 2:
            continue

        def _t(role: str) -> Dict[str, Any]:
            for t in teams:
                if (t.get('homeAway') or '').lower() == role:
                    return t
            return teams[0] if role == 'home' else teams[1]

        home = _t('home')
        away = _t('away')
        status = (event.get('status') or {}).get('type') or {}
        events_out.append({
            'event_id': f"espn_nfl_{event.get('id')}",
            'commence_time': event.get('date', ''),
            'status': status.get('description', ''),
            'status_state': status.get('state', ''),
            'home_team': (home.get('team') or {}).get('displayName', ''),
            'home_abbrev': (home.get('team') or {}).get('abbreviation', ''),
            'away_team': (away.get('team') or {}).get('displayName', ''),
            'away_abbrev': (away.get('team') or {}).get('abbreviation', ''),
            'odds': event.get('odds') or [],
        })
    return events_out


# ---- Fair-odds generation ----------------------------------------------------

def _fair_home_prob(home_abbrev: str, away_abbrev: str,
                    power: Dict[str, Dict[str, float]]) -> float:
    '''Estimate fair home-team win probability using simple ratings +
    a baseline home-field advantage (NFL ~ 2.2 points = ~0.057 in win prob).'''
    hp = power.get(home_abbrev, {})
    ap = power.get(away_abbrev, {})

    # Baseline 50/50 + home-field edge of ~5-6%.
    base = 0.555
    if not hp or not ap:
        return base

    # Points-differential proxy: (pf-pa) per game.
    home_edge = hp.get('pf_pg', 22.0) - hp.get('pa_pg', 22.0)
    away_edge = ap.get('pf_pg', 22.0) - ap.get('pa_pg', 22.0)
    net = home_edge - away_edge  # positive = home favored on power
    # Logistic scaling: every 7 points of net edge adds ~14% win prob.
    scaled = 1.0 / (1.0 + pow(2.718281828, -net / 14.0))
    # Blend with home-field baseline to avoid over-extrapolation on small samples.
    blend = 0.6 * scaled + 0.4 * 0.555
    return max(0.05, min(0.95, blend))


def build_fallback_rows(events: List[Dict[str, Any]],
                        power: Dict[str, Dict[str, float]],
                        min_ev: float) -> List[Dict[str, Any]]:
    '''Produce rows shaped for sports_odds.php?action=inject_fallback.'''
    rows: List[Dict[str, Any]] = []
    for ev in events:
        state = (ev.get('status_state') or '').lower()
        if state in ('post', 'in'):
            continue  # only upcoming games

        home_prob = _fair_home_prob(ev['home_abbrev'], ev['away_abbrev'], power)
        away_prob = 1.0 - home_prob

        home_american = _american_from_prob(home_prob)
        away_american = _american_from_prob(away_prob)
        home_decimal = _decimal_from_american(home_american)
        away_decimal = _decimal_from_american(away_american)

        # Shave ~4% off each side to simulate a book's line (give the analyzer
        # something plausible without claiming zero vig).
        home_decimal = round(home_decimal * 0.96, 4)
        away_decimal = round(away_decimal * 0.96, 4)

        home_ev = _calc_ev_pct(home_decimal, home_prob)
        away_ev = _calc_ev_pct(away_decimal, away_prob)

        # Only emit the side(s) whose EV clears the caller's threshold.
        for name, team, dec, prob, evp in (
            ('home', ev['home_team'], home_decimal, home_prob, home_ev),
            ('away', ev['away_team'], away_decimal, away_prob, away_ev),
        ):
            if abs(evp) < min_ev:
                continue
            rows.append({
                'sport': 'americanfootball_nfl',
                'event_id': ev['event_id'],
                'home_team': ev['home_team'],
                'away_team': ev['away_team'],
                'commence_time': (ev.get('commence_time') or '').replace('T', ' ').replace('Z', '')[:19],
                'bookmaker': 'nflreadpy_fallback',
                'bookmaker_key': 'nflreadpy_fallback',
                'market': 'h2h',
                'outcome_name': team,
                'outcome_price': dec,
                '_meta': {
                    'side': name,
                    'fair_prob': round(prob, 4),
                    'ev_pct': evp,
                    'source': 'nflreadpy+espn',
                    'home_power': power.get(ev['home_abbrev']),
                    'away_power': power.get(ev['away_abbrev']),
                },
            })
    return rows


# ---- Inject-API client -------------------------------------------------------

INJECT_URL_DEFAULT = 'https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=inject_fallback'


def post_inject(rows: List[Dict[str, Any]], url: str, key: str) -> Dict[str, Any]:
    full_url = url + ('&' if '?' in url else '?') + 'key=' + key
    # Strip our private _meta blob before posting — the endpoint doesn't know it.
    payload_rows = [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows]
    body = json.dumps({'rows': payload_rows}).encode('utf-8')
    req = urllib.request.Request(full_url, data=body, method='POST')
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


# ---- CLI ---------------------------------------------------------------------

def _default_seasons(n: int = 2) -> List[int]:
    now = datetime.datetime.utcnow()
    return list(range(now.year - n, now.year + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description='NFL odds fallback scraper (nflreadpy + ESPN).')
    parser.add_argument('--save-json', action='store_true', help='Save predictions to JSON.')
    parser.add_argument('--inject-api', action='store_true',
                        help='POST rows to sports_odds.php?action=inject_fallback.')
    parser.add_argument('--inject-url', default=INJECT_URL_DEFAULT, help='Override inject URL.')
    parser.add_argument('--api-key', default=os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026'))
    parser.add_argument('--min-ev', type=float, default=2.5,
                        help='Minimum EV%% (absolute value) required to emit a row.')
    parser.add_argument('--seasons', default='', help='Override power-rating seasons (e.g. 2023,2024).')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    print('=' * 64)
    print('NFL Odds Scraper — nflreadpy + ESPN fallback')
    print('=' * 64)

    if not _HAS_NFLREADPY:
        print(f'[warn] nflreadpy unavailable ({_NFLREADPY_ERR}). Running ESPN-only.')

    # Step 1: power ratings from nflverse
    if args.seasons.strip():
        try:
            seasons = [int(s) for s in args.seasons.split(',') if s.strip()]
        except ValueError:
            print('[error] --seasons must be integers', file=sys.stderr)
            return 2
    else:
        seasons = _default_seasons(2)
    print(f'[1/3] Loading NFL power ratings (seasons {seasons})...')
    power = load_team_power_ratings(seasons)
    print(f'      teams with ratings: {len(power)}')

    # Step 2: ESPN scoreboard for upcoming games
    print('[2/3] Fetching ESPN NFL scoreboard...')
    events = fetch_espn_nfl_events()
    print(f'      upcoming events: {len(events)}')

    # Step 3: synthesize fair-odds rows
    print(f'[3/3] Building fallback rows (min_ev={args.min_ev})...')
    rows = build_fallback_rows(events, power, args.min_ev)
    print(f'      rows passing EV filter: {len(rows)}')

    if args.verbose:
        for r in rows[:10]:
            meta = r.get('_meta', {})
            print(f"  {r['away_team']} @ {r['home_team']}  pick={r['outcome_name']} "
                  f"dec={r['outcome_price']}  EV={meta.get('ev_pct')}%")

    result = {
        'ok': True,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'events_scanned': len(events),
        'rows_generated': len(rows),
        'min_ev': args.min_ev,
        'seasons': seasons,
        'rows': rows,
    }

    if args.save_json:
        out_dir = 'live-monitor/backfill'
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(out_dir, f'nfl_fallback_{stamp}.json')
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f'[save] wrote {out_path}')

    if args.inject_api and rows:
        resp = post_inject(rows, args.inject_url, args.api_key)
        print(f'[inject] {json.dumps(resp)[:400]}')
    elif args.inject_api:
        print('[inject] no rows to inject; skipping')

    return 0


if __name__ == '__main__':
    sys.exit(main())
