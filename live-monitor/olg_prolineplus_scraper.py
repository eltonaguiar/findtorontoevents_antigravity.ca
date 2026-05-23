#!/usr/bin/env python3
'''
olg_prolineplus_scraper.py - Scrape OLG ProLine+ (Ontario government sportsbook)
moneyline odds and inject into lm_sports_odds.

Why this exists:
  OLG ProLine+ is a mandatory Ontario book that The Odds API does not surface.
  Without it, lm_sports_odds often has < 3 books per event and the de-vig step
  in sports_value_analyze_lib.php silently drops the event - which is the main
  reason "STRONG TAKE" picks (EV >= 10%) are rare on the live page.

  Output rows are de-duped by (event_id, bookmaker_key, market, outcome_name)
  inside sports_odds.php?action=inject_fallback so re-runs are idempotent.

Strategy:
  OLG's site is a Next.js client-rendered SPA. urllib gets an empty shell
  (confirmed by the failing gateway probe in olg_line_checker.py). We render
  the page in headless Chromium via Playwright, wait for hydration, and
  read either window.__NEXT_DATA__ or the DOM.

  This script self-degrades to exit 0 with a warning if Playwright is not
  installed, so it is safe to leave wired into the workflow even when the
  optional dep install partially fails.

Usage:
    python3 live-monitor/olg_prolineplus_scraper.py --save-json
    python3 live-monitor/olg_prolineplus_scraper.py --inject-api
    python3 live-monitor/olg_prolineplus_scraper.py --save-json --inject-api --verbose
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
from typing import Any, Dict, List, Optional, Tuple

try:
    from playwright.sync_api import sync_playwright  # type: ignore
    _HAS_PW = True
except Exception:
    sync_playwright = None  # type: ignore
    _HAS_PW = False

OLG_PROLINE_URL = 'https://www.olg.ca/en/sports/prolineplus.html'
INJECT_URL_DEFAULT = 'https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=inject_fallback'
BOOKMAKER_KEY = 'olg_prolineplus'
BOOKMAKER_NAME = 'OLG ProLine+'

# OLG sport-name -> The Odds API sport_key mapping (matches values used
# elsewhere in lm_sports_odds, e.g. 'icehockey_nhl', 'basketball_nba').
SPORT_MAP = {
    'hockey': 'icehockey_nhl',
    'ice hockey': 'icehockey_nhl',
    'nhl': 'icehockey_nhl',
    'basketball': 'basketball_nba',
    'nba': 'basketball_nba',
    'football': 'americanfootball_nfl',
    'nfl': 'americanfootball_nfl',
    'cfl': 'americanfootball_cfl',
    'baseball': 'baseball_mlb',
    'mlb': 'baseball_mlb',
    'soccer': 'soccer_epl',
    'mls': 'soccer_usa_mls',
    'ufc': 'mma_mixed_martial_arts',
    'mma': 'mma_mixed_martial_arts',
}


def _normalize_sport(label: str) -> str:
    if not label:
        return 'other'
    k = label.strip().lower()
    if k in SPORT_MAP:
        return SPORT_MAP[k]
    for token, sport_key in SPORT_MAP.items():
        if token in k:
            return sport_key
    return 'other'


def _decimal_from_american(a: Any) -> float:
    try:
        v = int(str(a).replace('+', '').strip())
    except (TypeError, ValueError):
        return 0.0
    if v == 0:
        return 0.0
    if v > 0:
        return round(1.0 + v / 100.0, 4)
    return round(1.0 + 100.0 / abs(v), 4)


def _is_decimal_odds(s: str) -> bool:
    try:
        return 1.01 <= float(s) <= 80.0
    except (TypeError, ValueError):
        return False


def _coerce_price(raw: Any) -> float:
    '''OLG can show decimal (1.95) or american (+150 / -120). Detect both.'''
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if s == '':
        return 0.0
    if s.startswith('+') or s.startswith('-') or (s.lstrip('-').isdigit() and abs(int(s)) >= 100):
        return _decimal_from_american(s)
    if _is_decimal_odds(s):
        return round(float(s), 4)
    return 0.0


def render_page(url: str, timeout_ms: int = 30000, verbose: bool = False) -> Tuple[str, Optional[Dict[str, Any]]]:
    '''Return (html, next_data_dict_or_none) after Playwright renders the page.'''
    if not _HAS_PW:
        raise RuntimeError('playwright not installed')
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled'],
        )
        try:
            ctx = browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                locale='en-CA',
                timezone_id='America/Toronto',
                viewport={'width': 1366, 'height': 900},
            )
            page = ctx.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=timeout_ms)
            except Exception:
                # networkidle can timeout on heavy SPAs; the DOM is usually
                # already populated by then. Fall through.
                if verbose:
                    print('[olg] networkidle wait timed out; continuing', file=sys.stderr)
            html = page.content()
            try:
                next_data_raw = page.evaluate(
                    "() => document.getElementById('__NEXT_DATA__') ? "
                    "document.getElementById('__NEXT_DATA__').textContent : null"
                )
            except Exception:
                next_data_raw = None
            next_data = None
            if next_data_raw:
                try:
                    next_data = json.loads(next_data_raw)
                except ValueError:
                    next_data = None
            return html, next_data
        finally:
            browser.close()


def _walk_for_events(node: Any, out: List[Dict[str, Any]], depth: int = 0) -> None:
    '''Walk arbitrary JSON looking for objects that look like sportsbook events.'''
    if depth > 12 or node is None:
        return
    if isinstance(node, dict):
        # Heuristic: an event has team/competitor names and a list of outcomes/markets.
        candidate_names = [
            ('homeTeam', 'awayTeam'),
            ('home_team', 'away_team'),
            ('home', 'away'),
            ('participant1', 'participant2'),
        ]
        for h_key, a_key in candidate_names:
            if h_key in node and a_key in node:
                home = node.get(h_key)
                away = node.get(a_key)
                if isinstance(home, dict):
                    home = home.get('name') or home.get('displayName') or home.get('shortName') or ''
                if isinstance(away, dict):
                    away = away.get('name') or away.get('displayName') or away.get('shortName') or ''
                event_id = (
                    node.get('id') or node.get('eventId') or node.get('matchId')
                    or node.get('competitionId') or ''
                )
                start = (
                    node.get('startTime') or node.get('commenceTime')
                    or node.get('startDate') or node.get('eventStartTime') or ''
                )
                sport = (
                    node.get('sport') or node.get('sportName')
                    or node.get('category') or node.get('league') or ''
                )
                # Find moneyline-shaped outcomes anywhere under this node.
                outcomes: List[Dict[str, Any]] = []
                _collect_outcomes(node, outcomes)
                if home and away and outcomes:
                    out.append({
                        'event_id': str(event_id) if event_id else f'olg_{home}_{away}_{start}',
                        'home_team': str(home),
                        'away_team': str(away),
                        'commence_time': str(start),
                        'sport_label': str(sport),
                        'outcomes': outcomes,
                    })
                break
        for v in node.values():
            _walk_for_events(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _walk_for_events(v, out, depth + 1)


def _collect_outcomes(node: Any, out: List[Dict[str, Any]], depth: int = 0) -> None:
    if depth > 8 or node is None:
        return
    if isinstance(node, dict):
        name_keys = ('name', 'outcomeName', 'displayName', 'selectionName', 'label')
        price_keys = ('price', 'odds', 'decimalOdds', 'americanOdds', 'displayOdds')
        name_v = next((node[k] for k in name_keys if k in node and isinstance(node[k], (str, int, float))), None)
        price_v = next((node[k] for k in price_keys if k in node), None)
        if name_v is not None and price_v is not None:
            price = _coerce_price(price_v)
            if price > 0:
                out.append({'name': str(name_v), 'price': price})
        for v in node.values():
            _collect_outcomes(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _collect_outcomes(v, out, depth + 1)


def parse_events(next_data: Optional[Dict[str, Any]], html: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if next_data:
        _walk_for_events(next_data, events)
    if not events and html:
        # Fallback: try to find any embedded JSON blobs in the HTML.
        for m in re.finditer(r'>(\{.{200,200000}?\})<', html):
            blob = m.group(1)
            try:
                data = json.loads(blob)
            except (ValueError, json.JSONDecodeError):
                continue
            _walk_for_events(data, events)
            if events:
                break
    return events


def build_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for ev in events:
        sport_key = _normalize_sport(ev.get('sport_label', ''))
        home = ev.get('home_team', '')
        away = ev.get('away_team', '')
        commence = (ev.get('commence_time', '') or '').replace('T', ' ').replace('Z', '')[:19]
        eid = str(ev.get('event_id', ''))
        # Restrict to h2h (moneyline) outcomes that match a team name.
        for o in ev.get('outcomes', []):
            name = (o.get('name') or '').strip()
            price = float(o.get('price') or 0)
            if price <= 1.01 or not name:
                continue
            # Must match a side (home/away or draw for soccer).
            is_home = name.lower() == home.lower() or home.lower() in name.lower()
            is_away = name.lower() == away.lower() or away.lower() in name.lower()
            is_draw = name.lower() in ('draw', 'tie', 'x')
            if not (is_home or is_away or is_draw):
                continue
            outcome_name = home if is_home else (away if is_away else 'Draw')
            dedup = (eid, outcome_name)
            if dedup in seen:
                continue
            seen.add(dedup)
            rows.append({
                'sport': sport_key,
                'event_id': eid,
                'home_team': home,
                'away_team': away,
                'commence_time': commence,
                'bookmaker': BOOKMAKER_NAME,
                'bookmaker_key': BOOKMAKER_KEY,
                'market': 'h2h',
                'outcome_name': outcome_name,
                'outcome_price': round(price, 4),
            })
    return rows


def post_inject(rows: List[Dict[str, Any]], url: str, key: str) -> Dict[str, Any]:
    full_url = url + ('&' if '?' in url else '?') + 'key=' + key
    body = json.dumps({'rows': rows}).encode('utf-8')
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


def main() -> int:
    parser = argparse.ArgumentParser(description='OLG ProLine+ scraper (Playwright).')
    parser.add_argument('--save-json', action='store_true')
    parser.add_argument('--inject-api', action='store_true',
                        help='POST rows to sports_odds.php?action=inject_fallback.')
    parser.add_argument('--inject-url', default=INJECT_URL_DEFAULT)
    parser.add_argument('--api-key', default=os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026'))
    parser.add_argument('--url', default=OLG_PROLINE_URL)
    parser.add_argument('--timeout-ms', type=int, default=30000)
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    print('=' * 64)
    print('OLG ProLine+ scraper (Playwright)')
    print('=' * 64)

    if not _HAS_PW:
        print('[olg] playwright not installed; exiting 0 (degraded). '
              'Install with: pip install playwright && python -m playwright install --with-deps chromium',
              file=sys.stderr)
        return 0

    print(f'[1/3] Rendering {args.url}...')
    try:
        html, next_data = render_page(args.url, args.timeout_ms, args.verbose)
    except Exception as e:
        print(f'[olg] render failed: {e}', file=sys.stderr)
        return 0
    print(f'      html_size={len(html)}  next_data={"yes" if next_data else "no"}')

    print('[2/3] Parsing events...')
    events = parse_events(next_data, html)
    print(f'      events: {len(events)}')

    print('[3/3] Building inject rows...')
    rows = build_rows(events)
    print(f'      rows: {len(rows)}')

    if args.verbose:
        for r in rows[:10]:
            print(f"  {r['sport']}  {r['away_team']} @ {r['home_team']}  {r['outcome_name']} dec={r['outcome_price']}")

    result = {
        'ok': True,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'source': args.url,
        'bookmaker_key': BOOKMAKER_KEY,
        'events_parsed': len(events),
        'rows_generated': len(rows),
        'rows': rows,
    }

    if args.save_json:
        out_dir = 'live-monitor/backfill'
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(out_dir, f'olg_prolineplus_{stamp}.json')
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
