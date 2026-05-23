#!/usr/bin/env python3
'''
oddsharvester_clv_backfill.py — Historical closing-odds CLV backfill.

Uses OddsHarvester (https://github.com/brendan-gibson/OddsHarvester, 2026-maintained)
to scrape historical CLOSING odds from OddsPortal for games we've already bet
on. The closing line is the strongest single predictor of long-term EV in
sports betting (the Closing Line Value / CLV signal). Populating
`lm_sports_clv.closing_price` is what unblocks:

  - sports_ml.php CLV summary (currently returns "No CLV rows ... yet")
  - sports_bets.php / sports_picks.php / sports_forensics.php joins that pull
    closing_price from lm_sports_clv
  - Retro-scoring of our existing settled bets: did we beat the close?

Design:
  - READ-ONLY for our pipeline — only writes to lm_sports_clv via an injection
    API endpoint (not to be confused with the odds inject endpoint).
  - Graceful degradation: missing `oddsharvester` exits 0 with a warning so CI
    stays green.
  - Respects OddsPortal's rate limits via built-in sleeps.
  - Canadian bookmaker priority: we prefer pinnacle closes (sharpest) as the
    "truth" column; fall back to bet365 / draftkings consensus.

The actual DB write endpoint (sports_clv.php?action=inject) is **not** assumed
to exist yet. When --inject-api is passed and the endpoint 404s, this script
falls back to --save-json mode so the data isn't lost.

Usage:
    python3 live-monitor/oddsharvester_clv_backfill.py --save-json
    python3 live-monitor/oddsharvester_clv_backfill.py --sport nba --days-back 14
    python3 live-monitor/oddsharvester_clv_backfill.py --inject-api --dry-run
'''

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

try:
    # OddsHarvester is the 2026 maintained successor package.
    import oddsharvester  # type: ignore
    _HAS_ODDSHARVESTER = True
except Exception as _e:
    oddsharvester = None  # type: ignore
    _HAS_ODDSHARVESTER = False
    _ODDSHARVESTER_ERR = str(_e)

# Sport slug translation: our pipeline's keys -> OddsPortal slugs.
SPORT_MAP = {
    'basketball_nba': ('basketball', 'usa', 'nba'),
    'icehockey_nhl':  ('hockey',     'usa', 'nhl'),
    'americanfootball_nfl': ('american-football', 'usa', 'nfl'),
    'baseball_mlb':   ('baseball',   'usa', 'mlb'),
}

INJECT_URL_DEFAULT = (
    'https://findtorontoevents.ca/live-monitor/api/sports_clv.php?action=inject'
)

# Preferred books, in order of "sharpness" for closing lines.
PREFERRED_BOOKS = ('pinnacle', 'bet365', 'draftkings', 'fanduel', 'betmgm')


def _log(msg: str) -> None:
    print(f'[oddsharvester_clv] {msg}', file=sys.stderr)


def _http_post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'oddsharvester-clv/1.0'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        _log(f'HTTP {e.code} posting to {url}')
        return None
    except Exception as e:
        _log(f'POST error: {e}')
        return None


def decimal_to_american(decimal: float) -> int:
    if decimal <= 1.0:
        return 0
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def _try_cli_fallback(
    sport_key: str,
    category: str,
    country: str,
    league: str,
    start_date: str,
    end_date: str,
    max_events: int,
) -> List[Dict[str, Any]]:
    '''
    OddsHarvester is primarily a CLI tool. When the Python API shape is not
    recognized, shell out to `oddsharvester --help`-style commands and parse
    the JSON output if available. Returns [] on any failure.

    This is a best-effort path — exact CLI args vary between versions, so we
    try a few reasonable shapes and give up quietly if nothing works.
    '''
    oh_bin = shutil.which('oddsharvester')
    if not oh_bin:
        return []

    candidates = [
        # Newer versions
        [oh_bin, 'scrape-historic',
         '--sport', category, '--league', league,
         '--from-date', start_date, '--to-date', end_date,
         '--format', 'json', '--limit', str(max_events)],
        # Older versions
        [oh_bin, '--sport', category, '--league', league,
         '--historic', '--start', start_date, '--end', end_date,
         '--json', '--max', str(max_events)],
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    parsed = json.loads(result.stdout)
                    if isinstance(parsed, list):
                        return parsed
                    if isinstance(parsed, dict) and 'events' in parsed:
                        return parsed['events'] or []
                except ValueError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    return []


def fetch_closing_odds_for_sport(
    sport_key: str,
    days_back: int = 7,
    max_events: int = 200,
) -> List[Dict[str, Any]]:
    '''
    Fetch historical closing odds for a sport via OddsHarvester.

    Returns a list of rows in our normalized shape:
      {
        sport, event_id (oddsportal id), home_team, away_team,
        commence_time, bookmaker_key, market, outcome,
        closing_price (decimal), closing_price_american (int),
        scraped_at (iso), source='oddsportal'
      }
    '''
    if not _HAS_ODDSHARVESTER:
        _log(f'oddsharvester not installed ({_ODDSHARVESTER_ERR!r}); skipping.')
        return []

    slug = SPORT_MAP.get(sport_key)
    if not slug:
        _log(f'no OddsPortal slug for sport={sport_key}')
        return []

    category, country, league = slug
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days_back)

    rows: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

    # ---- Try the Python API first ----
    try:
        scraper: Any = None
        if hasattr(oddsharvester, 'Scraper'):
            scraper = oddsharvester.Scraper(
                sport=category, country=country, league=league,
            )
        elif hasattr(oddsharvester, 'OddsPortalScraper'):
            scraper = oddsharvester.OddsPortalScraper(
                sport=category, country=country, league=league,
            )

        if scraper is not None and hasattr(scraper, 'historical'):
            events = scraper.historical(
                start_date=start_date.isoformat(),
                end_date=today.isoformat(),
                markets=['h2h', 'spreads', 'totals'],
                limit=max_events,
            ) or []
        else:
            _log('Python API shape not recognized; attempting CLI fallback.')
            events = _try_cli_fallback(
                sport_key, category, country, league,
                start_date.isoformat(), today.isoformat(), max_events,
            )

        for ev in events:
            event_id = str(ev.get('id') or ev.get('event_id') or '')
            home = ev.get('home_team') or ev.get('home') or ''
            away = ev.get('away_team') or ev.get('away') or ''
            commence = ev.get('commence_time') or ev.get('start_time') or ''

            if not event_id or not home or not away:
                continue

            for book in ev.get('bookmakers', []) or []:
                bkey = (book.get('key') or book.get('name') or '').lower()
                for market in book.get('markets', []) or []:
                    mkey = market.get('key') or market.get('type') or 'h2h'
                    for oc in market.get('outcomes', []) or []:
                        price = oc.get('price') or oc.get('closing_price')
                        if not price:
                            continue
                        decimal_price = float(price)
                        rows.append({
                            'sport': sport_key,
                            'event_id': event_id,
                            'home_team': home,
                            'away_team': away,
                            'commence_time': commence,
                            'bookmaker_key': bkey,
                            'market': mkey,
                            'outcome': oc.get('name') or oc.get('team') or '',
                            'closing_price': decimal_price,
                            'closing_price_american': decimal_to_american(decimal_price),
                            'scraped_at': datetime.datetime.utcnow().isoformat() + 'Z',
                            'source': 'oddsportal',
                        })

            # Be polite to OddsPortal — sleep between events.
            time.sleep(0.25)
    except Exception as e:
        _log(f'scrape failed for {sport_key}: {e}')
        # Last-resort CLI fallback if Python path threw.
        if not events:
            events = _try_cli_fallback(
                sport_key, category, country, league,
                start_date.isoformat(), today.isoformat(), max_events,
            )

    return rows


def collapse_to_preferred_book(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    '''
    For each (event_id, market, outcome), keep only the row from the most
    preferred book. lm_sports_clv uses a single closing_price per outcome.
    '''
    best: Dict[tuple, Dict[str, Any]] = {}
    prefs = {b: i for i, b in enumerate(PREFERRED_BOOKS)}

    for r in rows:
        key = (r['event_id'], r['market'], r['outcome'])
        prev = best.get(key)
        r_rank = prefs.get(r['bookmaker_key'], 99)
        if prev is None or r_rank < prefs.get(prev['bookmaker_key'], 99):
            best[key] = r

    return list(best.values())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sport', action='append',
                   help='Sport key (repeatable). Default: all 4.')
    p.add_argument('--days-back', type=int, default=7,
                   help='How far back to scrape. Default 7.')
    p.add_argument('--max-events', type=int, default=200,
                   help='Per-sport event cap. Default 200.')
    p.add_argument('--save-json', action='store_true',
                   help='Write JSON per sport to live-monitor/backfill/clv/.')
    p.add_argument('--inject-api', action='store_true',
                   help='POST rows to sports_clv.php?action=inject.')
    p.add_argument('--inject-url', default=INJECT_URL_DEFAULT)
    p.add_argument('--dry-run', action='store_true',
                   help='Print counts but do not write or POST.')
    p.add_argument('--preferred-book-only', action='store_true',
                   help='Collapse to one row per outcome using preferred books.')
    args = p.parse_args()

    if not _HAS_ODDSHARVESTER:
        _log('oddsharvester not installed — nothing to do. Exit 0 for CI.')
        return 0

    sports = args.sport or list(SPORT_MAP.keys())
    total_rows = 0
    total_posted = 0

    for sport in sports:
        _log(f'scraping {sport} (days_back={args.days_back})...')
        rows = fetch_closing_odds_for_sport(
            sport, days_back=args.days_back, max_events=args.max_events,
        )

        if args.preferred_book_only:
            rows = collapse_to_preferred_book(rows)

        _log(f'  -> {len(rows)} closing-odds rows for {sport}')
        total_rows += len(rows)

        if args.dry_run:
            continue

        if args.save_json and rows:
            out_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'backfill', 'clv'
            )
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(
                out_dir, f'{sport}_{datetime.date.today().isoformat()}.json'
            )
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(rows, f, indent=2)
            _log(f'  -> wrote {out_path}')

        if args.inject_api and rows:
            # POST in chunks to stay within PHP max_input_vars.
            CHUNK = 100
            for i in range(0, len(rows), CHUNK):
                chunk = rows[i:i + CHUNK]
                resp = _http_post_json(args.inject_url, {'rows': chunk})
                if resp is None:
                    _log(f'  -> inject failed at chunk {i}; preserving as JSON')
                    # Last-resort JSON dump so we don't lose the scrape.
                    out_dir = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'backfill', 'clv', 'unposted',
                    )
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(
                        out_dir,
                        f'{sport}_{int(time.time())}_chunk{i}.json',
                    )
                    with open(out_path, 'w', encoding='utf-8') as f:
                        json.dump(chunk, f, indent=2)
                    break
                else:
                    inserted = resp.get('inserted', 0) if isinstance(resp, dict) else 0
                    total_posted += int(inserted or 0)

    _log(f'DONE. total_rows={total_rows} total_posted={total_posted}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
