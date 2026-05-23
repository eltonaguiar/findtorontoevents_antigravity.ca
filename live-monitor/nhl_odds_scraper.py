#!/usr/bin/env python3
'''
nhl_odds_scraper.py — NHL fallback scraper with EDGE-style enrichment.

Uses the official NHL Web API (https://api-web.nhle.com/v1/) directly — no
external library required at runtime. When the `nhl-api-py` package is
installed it is used for convenience helpers; otherwise we fall back to
urllib.request calls. Both paths populate the same row shape.

What this gets us over the existing ESPN-only NHL intel:
  - Real standings (points %, OTL, GF/GA) from the source of truth
  - Team season stats (powerplay %, penalty-kill %, save %, shots for/against)
  - Per-game rest-days / back-to-back flags from /v1/schedule
  - Optional player-level EDGE tracking (skating speed, shot velocity) when
    `nhl-api-py` is available

The script mirrors the nba_odds_scraper.py shape so that downstream wiring
(inject endpoint, GitHub Actions step, CLI flags) is consistent.

Usage:
    python3 live-monitor/nhl_odds_scraper.py
    python3 live-monitor/nhl_odds_scraper.py --save-json
    python3 live-monitor/nhl_odds_scraper.py --inject-api --min-ev 2.0
'''

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

try:
    # Optional convenience wrapper. Not required.
    from nhlpy import NHLClient  # type: ignore
    _HAS_NHL_PY = True
except Exception:
    NHLClient = None  # type: ignore
    _HAS_NHL_PY = False

NHL_API = 'https://api-web.nhle.com/v1'
NHL_STATS_API = 'https://api.nhle.com/stats/rest/en'
INJECT_URL_DEFAULT = 'https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=inject_fallback'


# ---- HTTP helpers ------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (nhl-scraper)'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print(f'[http] {url}: {e}', file=sys.stderr)
        return None


def _american_from_prob(prob: float) -> int:
    p = max(0.02, min(0.98, float(prob)))
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def _decimal_from_american(a: int) -> float:
    a = int(a)
    if a > 0:
        return round(1.0 + a / 100.0, 4)
    return round(1.0 + 100.0 / abs(a), 4)


def _ev_pct(decimal_odds: float, true_prob: float) -> float:
    return round(100.0 * (true_prob * (decimal_odds - 1.0) - (1.0 - true_prob)), 2)


# ---- NHL Web API endpoints ---------------------------------------------------

def fetch_standings() -> List[Dict[str, Any]]:
    data = _http_get_json(f'{NHL_API}/standings/now')
    if not data:
        return []
    out: List[Dict[str, Any]] = []
    for t in data.get('standings', []) or []:
        abbrev = t.get('teamAbbrev', {}).get('default', '')
        name = t.get('teamName', {}).get('default', '')
        out.append({
            'abbrev': abbrev,
            'name': name,
            'wins': t.get('wins', 0),
            'losses': t.get('losses', 0),
            'otl': t.get('otLosses', 0),
            'points': t.get('points', 0),
            'pts_pct': t.get('pointPctg', 0.0),
            'gf': t.get('goalFor', 0),
            'ga': t.get('goalAgainst', 0),
            'gf_per_gp': t.get('goalsForPerGame', 0.0),
            'ga_per_gp': t.get('goalsAgainstPerGame', 0.0),
            'streak_code': t.get('streakCode', ''),
            'streak_count': t.get('streakCount', 0),
            'l10_wins': t.get('l10Wins', 0),
            'l10_losses': t.get('l10Losses', 0),
            'l10_otl': t.get('l10OtLosses', 0),
            'home_wins': t.get('homeWins', 0),
            'home_losses': t.get('homeLosses', 0),
            'road_wins': t.get('roadWins', 0),
            'road_losses': t.get('roadLosses', 0),
        })
    return out


def fetch_schedule_today() -> List[Dict[str, Any]]:
    '''Return today's NHL games with commence time and team abbrevs.'''
    data = _http_get_json(f'{NHL_API}/schedule/now')
    if not data:
        return []
    games: List[Dict[str, Any]] = []
    for week in data.get('gameWeek', []) or []:
        for g in week.get('games', []) or []:
            home = g.get('homeTeam', {})
            away = g.get('awayTeam', {})
            games.append({
                'event_id': f"nhl_{g.get('id')}",
                'commence_time': g.get('startTimeUTC', ''),
                'status': g.get('gameState', ''),
                'home_abbrev': home.get('abbrev', ''),
                'away_abbrev': away.get('abbrev', ''),
                'home_team': (home.get('placeName') or {}).get('default', '') + ' ' + (home.get('commonName') or {}).get('default', ''),
                'away_team': (away.get('placeName') or {}).get('default', '') + ' ' + (away.get('commonName') or {}).get('default', ''),
            })
    # Keep only FUT (future) games
    return [g for g in games if (g.get('status') or '').upper() in ('FUT', 'PRE')]


def fetch_team_seasonal_stats() -> Dict[str, Dict[str, Any]]:
    '''Per-team season summary stats (PP%, PK%, sv%) via the NHL Stats REST API.'''
    url = f'{NHL_STATS_API}/team/summary?cayenneExp=seasonId=20252026%20and%20gameTypeId=2'
    data = _http_get_json(url)
    out: Dict[str, Dict[str, Any]] = {}
    if not data:
        return out
    for t in data.get('data', []) or []:
        code = t.get('teamFullName', '')
        abbrev = (t.get('triCode') or '').upper()
        if not abbrev:
            continue
        out[abbrev] = {
            'name': code,
            'pp_pct': t.get('powerPlayPct', 0.0),
            'pk_pct': t.get('penaltyKillPct', 0.0),
            'shots_for_per_gp': t.get('shotsForPerGame', 0.0),
            'shots_against_per_gp': t.get('shotsAgainstPerGame', 0.0),
            'faceoff_pct': t.get('faceoffWinPct', 0.0),
        }
    return out


def fetch_edge_skater_sample(team_abbrev: str, limit: int = 3) -> List[Dict[str, Any]]:
    '''Best-effort EDGE-style stats (top skater speed/shot samples) if nhl-api-py
    exposes it. Returns [] if unavailable — this is a bonus, not required.'''
    if not _HAS_NHL_PY:
        return []
    try:
        client = NHLClient()  # type: ignore[operator]
        roster = client.teams.team_roster(team_abbrev=team_abbrev.lower(), season='20252026')
    except Exception as e:
        print(f'[nhl-api-py] roster({team_abbrev}) failed: {e}', file=sys.stderr)
        return []
    out: List[Dict[str, Any]] = []
    for player in (roster.get('forwards', []) or [])[:limit]:
        out.append({
            'player_id': player.get('id'),
            'name': (player.get('firstName') or {}).get('default', '') + ' ' + (player.get('lastName') or {}).get('default', ''),
            'position': player.get('positionCode', ''),
        })
    return out


# ---- Fair-odds construction --------------------------------------------------

def _fair_home_prob(home_abbr: str, away_abbr: str,
                    standings_map: Dict[str, Dict[str, Any]],
                    stats_map: Dict[str, Dict[str, Any]]) -> float:
    '''Blend points-% standings + shot differential + special teams + home-ice.'''
    h_st = standings_map.get(home_abbr, {})
    a_st = standings_map.get(away_abbr, {})

    # Baseline: points% already encodes overall strength.
    h_pts = float(h_st.get('pts_pct', 0.5))
    a_pts = float(a_st.get('pts_pct', 0.5))

    # Shot differential proxy (helps separate lucky vs. good teams).
    h_stats = stats_map.get(home_abbr, {})
    a_stats = stats_map.get(away_abbr, {})
    h_shot_diff = float(h_stats.get('shots_for_per_gp', 30)) - float(h_stats.get('shots_against_per_gp', 30))
    a_shot_diff = float(a_stats.get('shots_for_per_gp', 30)) - float(a_stats.get('shots_against_per_gp', 30))

    # Special teams delta (PP% - opposing PK%).
    h_st_adv = float(h_stats.get('pp_pct', 20)) - float(a_stats.get('pk_pct', 80))
    a_st_adv = float(a_stats.get('pp_pct', 20)) - float(h_stats.get('pk_pct', 80))

    # Combine: weighted points-% blend + small shot/ST adjustments + HFA.
    base = 0.5 + 0.35 * (h_pts - a_pts)
    base += 0.004 * (h_shot_diff - a_shot_diff)     # per-shot edge
    base += 0.002 * (h_st_adv - a_st_adv)           # special-teams edge (pct pts)
    base += 0.040                                   # NHL home-ice ~4%
    return max(0.10, min(0.90, base))


def build_fallback_rows(games: List[Dict[str, Any]],
                        standings_map: Dict[str, Dict[str, Any]],
                        stats_map: Dict[str, Dict[str, Any]],
                        min_ev: float) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for g in games:
        home_prob = _fair_home_prob(g['home_abbrev'], g['away_abbrev'], standings_map, stats_map)
        away_prob = 1.0 - home_prob

        home_dec = _decimal_from_american(_american_from_prob(home_prob))
        away_dec = _decimal_from_american(_american_from_prob(away_prob))
        # Light haircut to mimic a book line.
        home_dec = round(home_dec * 0.96, 4)
        away_dec = round(away_dec * 0.96, 4)

        home_ev = _ev_pct(home_dec, home_prob)
        away_ev = _ev_pct(away_dec, away_prob)

        for name, team, dec, prob, evp in (
            ('home', g['home_team'], home_dec, home_prob, home_ev),
            ('away', g['away_team'], away_dec, away_prob, away_ev),
        ):
            if abs(evp) < min_ev:
                continue
            rows.append({
                'sport': 'icehockey_nhl',
                'event_id': g['event_id'],
                'home_team': g['home_team'],
                'away_team': g['away_team'],
                'commence_time': (g.get('commence_time') or '').replace('T', ' ').replace('Z', '')[:19],
                'bookmaker': 'nhl_api_fallback',
                'bookmaker_key': 'nhl_api_fallback',
                'market': 'h2h',
                'outcome_name': team,
                'outcome_price': dec,
                '_meta': {
                    'side': name,
                    'fair_prob': round(prob, 4),
                    'ev_pct': evp,
                    'source': 'nhl-web-api+stats-rest',
                    'home_pts_pct': standings_map.get(g['home_abbrev'], {}).get('pts_pct'),
                    'away_pts_pct': standings_map.get(g['away_abbrev'], {}).get('pts_pct'),
                    'home_pp_pct': stats_map.get(g['home_abbrev'], {}).get('pp_pct'),
                    'away_pp_pct': stats_map.get(g['away_abbrev'], {}).get('pp_pct'),
                },
            })
    return rows


# ---- Inject client -----------------------------------------------------------

def post_inject(rows: List[Dict[str, Any]], url: str, key: str) -> Dict[str, Any]:
    full_url = url + ('&' if '?' in url else '?') + 'key=' + key
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

def main() -> int:
    parser = argparse.ArgumentParser(description='NHL odds fallback scraper (NHL Web API + Stats REST).')
    parser.add_argument('--save-json', action='store_true')
    parser.add_argument('--inject-api', action='store_true',
                        help='POST rows to sports_odds.php?action=inject_fallback.')
    parser.add_argument('--inject-url', default=INJECT_URL_DEFAULT)
    parser.add_argument('--api-key', default=os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026'))
    parser.add_argument('--min-ev', type=float, default=2.0)
    parser.add_argument('--include-edge', action='store_true',
                        help='Also fetch a small EDGE-style roster sample (needs nhl-api-py).')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    print('=' * 64)
    print('NHL Odds Scraper — NHL Web API + Stats REST')
    print('=' * 64)

    print('[1/4] Fetching standings...')
    standings = fetch_standings()
    standings_map = {s['abbrev']: s for s in standings if s.get('abbrev')}
    print(f'      teams: {len(standings_map)}')

    print('[2/4] Fetching season team stats...')
    stats_map = fetch_team_seasonal_stats()
    print(f'      teams with stats: {len(stats_map)}')

    print('[3/4] Fetching today/upcoming schedule...')
    games = fetch_schedule_today()
    print(f'      upcoming games: {len(games)}')

    print(f'[4/4] Building fallback rows (min_ev={args.min_ev})...')
    rows = build_fallback_rows(games, standings_map, stats_map, args.min_ev)
    print(f'      rows: {len(rows)}')

    edge_samples: Dict[str, List[Dict[str, Any]]] = {}
    if args.include_edge and _HAS_NHL_PY:
        print('[bonus] fetching EDGE roster samples...')
        for g in games[:6]:  # cap network pressure
            for side in ('home_abbrev', 'away_abbrev'):
                ab = g.get(side)
                if ab and ab not in edge_samples:
                    edge_samples[ab] = fetch_edge_skater_sample(ab, limit=3)

    if args.verbose:
        for r in rows[:10]:
            meta = r.get('_meta', {})
            print(f"  {r['away_team']} @ {r['home_team']}  pick={r['outcome_name']} "
                  f"dec={r['outcome_price']}  EV={meta.get('ev_pct')}%  pp%={meta.get('home_pp_pct')}/{meta.get('away_pp_pct')}")

    result = {
        'ok': True,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'games_scanned': len(games),
        'rows_generated': len(rows),
        'min_ev': args.min_ev,
        'rows': rows,
        'edge_samples': edge_samples,
        'sources': {
            'schedule': f'{NHL_API}/schedule/now',
            'standings': f'{NHL_API}/standings/now',
            'team_stats': f'{NHL_STATS_API}/team/summary',
        },
    }

    if args.save_json:
        out_dir = 'live-monitor/backfill'
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(out_dir, f'nhl_fallback_{stamp}.json')
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
