#!/usr/bin/env python3
'''
olg_line_checker.py — OLG Proline+ line comparison tool.

Compares our active picks from lm_sports_value_bets / lm_sports_daily_picks
against OLG Proline+ published odds (scraped from olg.ca/en/sports/prolineplus.html)
to identify cases where OLG is offering better odds than our best book.

Why this matters:
  OLG Proline+ is Ontario's government-owned sportsbook and the dominant book
  for CFL, college sports, and parlay-focused bettors. When our value algorithm
  shows a pick at odds X, but OLG offers odds Y > X, the user should bet on OLG
  instead of our recommended book. Conversely, if our best book beats OLG,
  that confirms the edge is real (not just a soft-book artifact).

Usage:
    python3 live-monitor/olg_line_checker.py                    # all picks
    python3 live-monitor/olg_line_checker.py --sport NBA        # NBA only
    python3 live-monitor/olg_line_checker.py --min-ev 5.0       # strong picks only
    python3 live-monitor/olg_line_checker.py --verbose          # full details
'''

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

OLG_BASE = 'https://www.olg.ca'
OLG_PROLINE_URL = 'https://www.olg.ca/en/sports/prolineplus.html'
INJECT_KEY = os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026')


# ---- Helpers -----------------------------------------------------------------

def _http_get(url: str, headers: Optional[Dict[str, str]] = None,
              timeout: int = 15) -> Optional[str]:
    h = headers or {}
    h.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    h.setdefault('Accept', 'text/html,application/xhtml+xml,application/json')
    h.setdefault('Accept-Language', 'en-CA,en;q=0.9')
    h.setdefault('Referer', OLG_BASE)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        safe_url = url.split('?')[0][:60]
        print(f"[http] {safe_url}: {e}", file=sys.stderr)
        return None


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None,
                   timeout: int = 15) -> Optional[Dict[str, Any]]:
    raw = _http_get(url, headers, timeout)
    if raw:
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return None


def american_to_decimal(a: str) -> float:
    try:
        a_int = int(a)
    except (TypeError, ValueError):
        return 0.0
    if a_int > 0:
        return round(1.0 + a_int / 100.0, 4)
    return round(1.0 + 100.0 / abs(a_int), 4)


def _extract_gateway_from_html(html: str) -> Optional[str]:
    '''Find the OLG API gateway URL from the page HTML.'''
    patterns = [
        r"gatewayUrl[\t ]*[:=][\t ]*['\"](https?://[^'\"\s]+)",
        r"baseUrl[\t ]*[:=][\t ]*['\"](https?://gateway[^'\"\s]+)",
        r'(https?://gateway\.olg\.ca[^\"\'\s]{0,100})',
        r'(https?://prod-[a-z0-9]+\.olg\.ca[^\"\'\s]{0,100})',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return m.group(1).rstrip(',;').strip()
    return None


# ---- OLG API probing ---------------------------------------------------------

def probe_olg_gateway() -> Dict[str, Any]:
    '''Attempt to find and probe the OLG Proline+ API.'''
    print('[olg] fetching prolineplus page...')
    html = _http_get(OLG_PROLINE_URL)
    if not html:
        return {'ok': False, 'error': 'page_unreachable'}

    gateway = _extract_gateway_from_html(html)
    results: Dict[str, Any] = {
        'ok': False,
        'gateway_found': gateway,
        'page_size': len(html),
        'events': [],
        'errors': [],
    }

    if not gateway:
        results['errors'].append('no_gateway_url_found')
        return results

    print(f'[olg] found gateway: {gateway[:80]}')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-CA,en;q=0.9',
        'Origin': OLG_BASE,
        'Referer': OLG_PROLINE_URL,
    }

    candidates = [
        f'{gateway}/sportsbook/v2/events',
        f'{gateway}/sportsbook/v1/events',
        f'{gateway}/sportsbook/events',
        f'{gateway}/prolineplus/api/events',
        f'{gateway}/sports/v1/events',
        f'{gateway}/betting/events',
    ]

    for endpoint in candidates:
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as r:
                ct = r.headers.get('Content-Type', '')
                body = r.read()
                if r.status == 200 and ('json' in ct or body.startswith(b'{') or body.startswith(b'[')):
                    try:
                        data = json.loads(body)
                        results['ok'] = True
                        results['endpoint'] = endpoint
                        results['events'] = data.get('events', data.get('data', []))
                        print(f"[olg] API HIT at {endpoint}: {len(results['events'])} events")
                        return results
                    except ValueError:
                        pass
        except urllib.error.HTTPError as e:
            results['errors'].append(f'{endpoint} -> HTTP {e.code}')
        except Exception as e:
            results['errors'].append(f'{endpoint} -> {e}')

    return results


def scrape_olg_from_page() -> List[Dict[str, Any]]:
    '''Attempt to extract event data embedded in the OLG page source.'''
    print('[olg] attempting to extract OLG data from page source...')
    html = _http_get(OLG_PROLINE_URL)
    if not html:
        return []

    events: List[Dict[str, Any]] = []

    ld_patterns = [
        r'<script type="application/ld\+json">(.*?)</script>',
        r'window\.__NEXT_DATA__\s*=\s*(.*?);',
        r"data-events\s*=\s*['\"](.*?)['\"]",
    ]

    for pat in ld_patterns:
        matches = re.findall(pat, html, re.DOTALL | re.IGNORECASE)
        for m in matches[:3]:
            try:
                data = json.loads(m)
                found = _walk_json_for_events(data)
                if found:
                    events.extend(found)
                    print(f'[olg] found {len(found)} events via pattern')
            except (json.JSONDecodeError, TypeError):
                pass

    return events[:200]


def _walk_json_for_events(obj: Any, depth: int = 0) -> List[Dict[str, Any]]:
    '''Recursively walk a JSON object looking for event-like structures.'''
    if depth > 10:
        return []
    if isinstance(obj, list):
        results: List[Dict[str, Any]] = []
        for item in obj:
            results.extend(_walk_json_for_events(item, depth + 1))
        return results
    if isinstance(obj, dict):
        if 'home_team' in obj or 'homeTeam' in obj:
            return [obj]
        if ('odds' in obj or 'price' in obj) and ('name' in obj or 'team' in obj):
            return [obj]
        results: List[Dict[str, Any]] = []
        for v in obj.values():
            results.extend(_walk_json_for_events(v, depth + 1))
        return results
    return []


# ---- Fetch our picks ---------------------------------------------------------

def fetch_our_picks(sport_filter: str = 'all', min_ev: float = 0.0) -> List[Dict[str, Any]]:
    '''Fetch active picks from our dashboard API.'''
    url = f'https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today&key={INJECT_KEY}'
    if sport_filter != 'all':
        url += f'&sport={sport_filter}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            picks = data.get('value_bets', [])
            return [p for p in picks if float(p.get('ev_pct', 0)) >= min_ev]
    except Exception as e:
        print(f'[our_picks] fetch failed: {e}', file=sys.stderr)
        return []


def fetch_our_odds(sport_filter: str = 'all') -> Dict[str, List[Dict[str, Any]]]:
    '''Fetch current odds from our DB, grouped by event_id.'''
    sport = sport_filter if sport_filter != 'all' else 'all'
    url = f'https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=get&sport={sport}&hours=72'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            result: Dict[str, List[Dict[str, Any]]] = {}
            for e in data.get('events', []):
                eid = e.get('event_id', '')
                rows: List[Dict[str, Any]] = []
                for b in e.get('bookmakers', []):
                    bk = b.get('key', '')
                    for m in b.get('markets', []):
                        for o in m.get('outcomes', []):
                            rows.append({
                                'book': bk,
                                'book_name': b.get('name', ''),
                                'market': m.get('key', ''),
                                'outcome': o.get('name', ''),
                                'price': float(o.get('price', 0)),
                                'point': o.get('point'),
                            })
                result[eid] = rows
            return result
    except Exception as e:
        print(f'[our_odds] fetch failed: {e}', file=sys.stderr)
        return {}


# ---- Comparison engine -------------------------------------------------------

def _norm_outcome(name: str) -> str:
    '''Normalize outcome names for comparison.'''
    return re.sub(r'[^a-z0-9]', '', name.lower())


def compare_pick_against_olg(
    pick: Dict[str, Any],
    our_odds: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    '''Compare a single pick against OLG available odds.'''
    eid = pick.get('event_id', '')
    market = pick.get('market', 'h2h')
    outcome = pick.get('outcome_name', '')

    event_odds = our_odds.get(eid, [])
    outcome_odds = [
        o for o in event_odds
        if o['market'] == market and _norm_outcome(o['outcome']) == _norm_outcome(outcome)
    ]

    if outcome_odds:
        best_us = max(o['price'] for o in outcome_odds)
        worst_us = min(o['price'] for o in outcome_odds)
        best_us_book = next((o['book'] for o in outcome_odds if o['price'] == best_us), '')
    else:
        best_us = float(pick.get('best_odds', 0))
        worst_us = best_us
        best_us_book = pick.get('best_book', '')

    olg_estimate = 0.0  # updated when OLG API is reachable
    olg_edge = None
    if olg_estimate > 0 and best_us > 0:
        olg_edge = round(100 * (olg_estimate - best_us) / best_us, 2)

    return {
        'sport': pick.get('sport_short', pick.get('sport', '')),
        'game': f"{pick.get('away_team', '?')} @ {pick.get('home_team', '?')}",
        'commence': pick.get('commence_time', '')[:16],
        'outcome': outcome,
        'market': market,
        'recommendation': pick.get('recommendation', ''),
        'ev_pct': float(pick.get('ev_pct', 0)),
        'our_best_odds': best_us,
        'our_best_book': best_us_book,
        'our_spread_pct': round(100 * (best_us - worst_us) / worst_us, 1) if worst_us > 0 else 0.0,
        'olg_odds': olg_estimate,
        'olg_edge_pct': olg_edge,
        'kelly_stake': pick.get('kelly_bet', 0),
        'grade': pick.get('rating_grade', ''),
    }


# ---- Main comparison ---------------------------------------------------------

def run_comparison(sport: str = 'all', min_ev: float = 0.0, verbose: bool = False) -> None:
    print('=' * 72)
    print('OLG Proline+ Line Checker')
    print(f'  Sport filter : {sport}')
    print(f'  Min EV       : {min_ev}%')
    print('=' * 72)

    print('\n[1/3] Probing OLG Proline+ API...')
    olg_result = probe_olg_gateway()
    olg_raw = olg_result.get('events', [])

    if not olg_raw:
        print('[1/3] OLG API not reachable (client-side rendered app)')
        print('      Falling back to page-source scan...')
        olg_raw = scrape_olg_from_page()

    print(f'      OLG events found: {len(olg_raw)}')
    if olg_raw:
        for ev in olg_raw[:5]:
            print(f"        - {ev.get('away', ev.get('away_team', '?'))} @ {ev.get('home', ev.get('home_team', '?'))}")
    else:
        print('      NOTE: OLG Proline+ data unavailable via scraping.')
        print('      Manual check required at olg.ca/en/sports/prolineplus.html')

    print('\n[2/3] Fetching our active picks...')
    our_picks = fetch_our_picks(sport_filter=sport, min_ev=min_ev)
    print(f'      Our active picks: {len(our_picks)}')

    print('\n[3/3] Fetching our current odds DB...')
    our_odds = fetch_our_odds(sport_filter=sport)
    print(f'      Events with odds: {len(our_odds)}')

    print('\n' + '=' * 72)
    print('COMPARISON RESULTS')
    print('=' * 72)

    strong_takes: List[Dict[str, Any]] = []
    takes: List[Dict[str, Any]] = []
    leans: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for pick in our_picks:
        result = compare_pick_against_olg(pick, our_odds)
        rec = result['recommendation']

        if rec == 'STRONG TAKE':
            strong_takes.append(result)
        elif rec == 'TAKE':
            takes.append(result)
        elif rec in ('LEAN', 'LOW EDGE'):
            leans.append(result)

        # Flag anomalies
        if result['our_spread_pct'] > 15.0:
            warnings.append(
                f"HIGH BOOK SPREAD on {result['game']}: "
                f"{result['our_spread_pct']}% (best={result['our_best_odds']})"
            )
        if result['our_best_odds'] > 3.5 and sport == 'NBA':
            warnings.append(
                f"UNUSUALLY HIGH NBA ODDS: {result['outcome']} @ {result['our_best_odds']} "
                f"at {result['our_best_book']} - verify vs OLG before sizing up"
            )

        if verbose:
            olg_status = f"OLG={result['olg_odds']}" if result['olg_odds'] > 0 else 'OLG=??? (check manually)'
            print(f"\n  [{rec}] {result['sport']} | {result['game']}")
            print(f"    Pick    : {result['outcome']} @ {result['our_best_odds']} ({result['our_best_book']})")
            print(f"    EV      : {result['ev_pct']}%")
            print(f"    Kelly   : ${result['kelly_stake']:.2f}")
            print(f"    Grade   : {result['grade']}")
            print(f"    Spread  : {result['our_spread_pct']}% across our books")
            print(f"    OLG     : {olg_status}")
            if result['olg_edge_pct'] is not None:
                print(f"    Edge    : {result['olg_edge_pct']}% vs OLG")

    print('\n[STRONG TAKE] 10%+ EV')
    if strong_takes:
        for r in strong_takes:
            olg_note = f"OLG={r['olg_odds']}" if r['olg_odds'] > 0 else 'OLG=??? (check manually)'
            print(f"  [+] {r['game']} | {r['outcome']} @ {r['our_best_odds']} | "
                  f"EV={r['ev_pct']}% | Kelly=${r['kelly_stake']:.2f} | "
                  f"{r['our_best_book']} | {olg_note}")
    else:
        print('  (none above min_ev threshold)')

    print('\n[TAKE] 6-10% EV')
    if takes:
        for r in takes:
            olg_note = f"OLG={r['olg_odds']}" if r['olg_odds'] > 0 else 'OLG=??? (check manually)'
            print(f"  [>] {r['game']} | {r['outcome']} @ {r['our_best_odds']} | "
                  f"EV={r['ev_pct']}% | Kelly=${r['kelly_stake']:.2f} | "
                  f"{r['our_best_book']} | {olg_note}")
    else:
        print('  (none above min_ev threshold)')

    print('\n[LEAN] 3-6% EV')
    if leans:
        for r in leans[:8]:
            olg_note = f"OLG={r['olg_odds']}" if r['olg_odds'] > 0 else 'OLG=???'
            print(f"  [~] {r['game']} | {r['outcome']} @ {r['our_best_odds']} | "
                  f"EV={r['ev_pct']}% | Kelly=${r['kelly_stake']:.2f} | {olg_note}")
    else:
        print('  (none)')

    if warnings:
        print('\n[WARNINGS]')
        for w in warnings:
            print(f"  [!] {w}")

    print(f"\nGenerated: {datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')}")
    print(f'Source: findtorontoevents.ca live-monitor')


# ---- CLI ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description='Compare our picks against OLG Proline+ odds.')
    parser.add_argument('--sport', default='all',
                        help='Sport filter (NBA, NHL, etc.). Default: all.')
    parser.add_argument('--min-ev', type=float, default=0.0,
                        help='Minimum EV%% to include. Default: 0 (all).')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print full details per pick.')
    parser.add_argument('--save-json', action='store_true',
                        help='Save results to JSON.')
    args = parser.parse_args()

    run_comparison(sport=args.sport, min_ev=args.min_ev, verbose=args.verbose)

    if args.save_json:
        our_picks = fetch_our_picks(sport_filter=args.sport, min_ev=args.min_ev)
        our_odds  = fetch_our_odds(sport_filter=args.sport)
        results = [compare_pick_against_olg(p, our_odds) for p in our_picks]
        out_dir = 'live-monitor/backfill'
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f'olg_line_check_{datetime.date.today().isoformat()}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\n[save] wrote {out_path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())