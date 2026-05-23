#!/usr/bin/env python3
'''
betway_ca_scraper.py - Scrape Betway Canada (Ontario-licensed) moneyline odds
across multiple sports and inject into lm_sports_odds.

Why this exists:
  Betway is one of the larger ON-licensed sportsbooks but rarely surfaces in
  The Odds API's Canadian feed. Adding it as a direct source bumps the per-
  event book count past the de-vig threshold (>=3), which is the precondition
  for STRONG TAKE picks (EV >= 10%) to appear on the live page.

  Output rows match the shape consumed by sports_odds.php?action=inject_fallback
  and are de-duped on (event_id, bookmaker_key, market, outcome_name).

Strategy:
  Betway's site is JS-rendered. Use Playwright with realistic UA + en-CA
  locale. Loop over sport categories - the page shape is consistent across
  sports so one parser handles all of them.

  This script self-degrades to exit 0 with a warning if Playwright is not
  installed, so it is safe to leave wired into the workflow.

Usage:
    python3 live-monitor/betway_ca_scraper.py --save-json --sports ice-hockey
    python3 live-monitor/betway_ca_scraper.py --inject-api \\
        --sports ice-hockey,basketball,american-football,baseball,soccer
'''

from __future__ import annotations

import argparse
import datetime
import hashlib
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

INJECT_URL_DEFAULT = 'https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=inject_fallback'
BOOKMAKER_KEY = 'betway'
BOOKMAKER_NAME = 'Betway'
# Primary URL: Ontario-licensed storefront (may be geo-blocked in CI)
BETWAY_BASE = 'https://betway.ca/ca-on/en-ca/sports/cat/'
# Fallback: global en-CA URL (betway.com/g/en-ca/sports) — same product family,
# more accessible from non-ON IPs (GitHub Actions runners).
BETWAY_BASE_GLOBAL = 'https://betway.com/g/en-ca/sports/cat/'

# Boost detection: flag any line where scraped odds exceed this multiplier
# versus typical single-team moneyline odds (> 2.5x = likely a promoted superboost).
# These are posted to a separate 'betway_boost' bookmaker_key so the UI can
# flag them as promotional EV picks separate from consensus de-vig.
BOOST_MULTIPLIER_THRESHOLD = 2.5  # e.g. +1400 when market was +425

# Betway URL slug -> The Odds API sport_key (matches values used in lm_sports_odds).
SPORT_MAP = {
    'ice-hockey': 'icehockey_nhl',
    'basketball': 'basketball_nba',
    'american-football': 'americanfootball_nfl',
    'cfl': 'americanfootball_cfl',
    'baseball': 'baseball_mlb',
    'soccer': 'soccer_epl',
    'mma': 'mma_mixed_martial_arts',
    'tennis': 'tennis_atp',
    # Added: PWHL women's hockey (Betway covers Vancouver Goldeneyes, Minnesota Frost, etc.)
    'pwhl': 'icehockey_pwhl',
    # Added: IPL cricket — Betway en-CA covers Chennai Super Kings, KKR, LSG, GT etc.
    'cricket': 'cricket_india_ipl',
}


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


def _coerce_price(raw: Any) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if s == '':
        return 0.0
    if s.startswith('+') or (s.startswith('-') and s[1:].isdigit()):
        return _decimal_from_american(s)
    try:
        v = float(s)
    except (TypeError, ValueError):
        return 0.0
    if 1.01 <= v <= 80.0:
        return round(v, 4)
    if abs(v) >= 100:
        return _decimal_from_american(int(v))
    return 0.0


def _hash_event_id(sport_slug: str, home: str, away: str, commence: str) -> str:
    h = hashlib.md5(f'betway|{sport_slug}|{home}|{away}|{commence}'.encode('utf-8')).hexdigest()[:16]
    return f'betway_{sport_slug}_{h}'


def render_sport_page(sport_slug: str, timeout_ms: int = 30000,
                      verbose: bool = False,
                      base_url: Optional[str] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
    if not _HAS_PW:
        raise RuntimeError('playwright not installed')
    # Try primary URL first; fall back to global en-CA URL if primary returns empty page.
    urls_to_try = [
        (base_url or BETWAY_BASE) + sport_slug,
        BETWAY_BASE_GLOBAL + sport_slug,
    ]
    if base_url and base_url == BETWAY_BASE_GLOBAL:
        urls_to_try = [BETWAY_BASE_GLOBAL + sport_slug, BETWAY_BASE + sport_slug]
    url = urls_to_try[0]
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
                if verbose:
                    print(f'[betway:{sport_slug}] networkidle timeout; continuing', file=sys.stderr)
            # Some sport pages defer odds rendering until a tile is visible; nudge it.
            try:
                page.wait_for_selector('[data-testid*="event"], [data-test*="event"], [class*="event"]',
                                       timeout=8000)
            except Exception:
                pass
            html = page.content()
            embedded = _scan_initial_state(page, verbose)
            # If primary URL returned empty/minimal content, try global fallback.
            if not embedded and len(html) < 5000 and len(urls_to_try) > 1:
                if verbose:
                    print(f'[betway:{sport_slug}] primary URL sparse; trying global URL fallback', file=sys.stderr)
                try:
                    page.goto(urls_to_try[1], wait_until='domcontentloaded', timeout=timeout_ms)
                    page.wait_for_load_state('networkidle', timeout=timeout_ms)
                except Exception:
                    pass
                html = page.content()
                embedded = _scan_initial_state(page, verbose)
            return html, embedded
        finally:
            browser.close()


def _scan_initial_state(page: Any, verbose: bool) -> Optional[Dict[str, Any]]:
    '''Look for a window-level state blob (Redux/__NEXT_DATA__/__APOLLO_STATE__).'''
    candidates = [
        '__NEXT_DATA__',
        '__INITIAL_STATE__',
        '__PRELOADED_STATE__',
        '__APOLLO_STATE__',
        '__REDUX_STATE__',
    ]
    for name in candidates:
        try:
            raw = page.evaluate(
                f"() => {{ try {{ const v = window['{name}']; "
                f"return v ? JSON.stringify(v) : null; }} catch(e) {{ return null; }} }}"
            )
        except Exception:
            raw = None
        if raw:
            try:
                if verbose:
                    print(f'[betway] found window.{name}', file=sys.stderr)
                return json.loads(raw)
            except ValueError:
                continue
    # Fall back to the canonical Next.js script tag.
    try:
        next_raw = page.evaluate(
            "() => document.getElementById('__NEXT_DATA__') ? "
            "document.getElementById('__NEXT_DATA__').textContent : null"
        )
    except Exception:
        next_raw = None
    if next_raw:
        try:
            return json.loads(next_raw)
        except ValueError:
            return None
    return None


def _walk_for_events(node: Any, out: List[Dict[str, Any]], depth: int = 0) -> None:
    if depth > 12 or node is None:
        return
    if isinstance(node, dict):
        candidate_pairs = [
            ('homeTeam', 'awayTeam'),
            ('home_team', 'away_team'),
            ('home', 'away'),
            ('participantOne', 'participantTwo'),
        ]
        for h_key, a_key in candidate_pairs:
            if h_key in node and a_key in node:
                home = node.get(h_key)
                away = node.get(a_key)
                if isinstance(home, dict):
                    home = home.get('name') or home.get('displayName') or home.get('shortName') or ''
                if isinstance(away, dict):
                    away = away.get('name') or away.get('displayName') or away.get('shortName') or ''
                event_id = (
                    node.get('id') or node.get('eventId') or node.get('matchId') or ''
                )
                start = (
                    node.get('startTime') or node.get('commenceTime')
                    or node.get('startDate') or node.get('eventStartTime') or ''
                )
                outcomes: List[Dict[str, Any]] = []
                _collect_outcomes(node, outcomes)
                if home and away and outcomes:
                    out.append({
                        'event_id': str(event_id) if event_id else '',
                        'home_team': str(home),
                        'away_team': str(away),
                        'commence_time': str(start),
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


def _parse_dom_fallback(html: str) -> List[Dict[str, Any]]:
    '''Last-resort regex parse - looks for "Team A vs Team B" pairs followed by
    two/three decimal odds. Brittle, but better than zero rows when the SPA
    state blob is not exposed.'''
    events: List[Dict[str, Any]] = []
    # Strip tags to a flat text stream.
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    # Conservative pattern: TeamA vs TeamB ... 1.95 ... 1.90  (or 3-way with draw).
    pattern = re.compile(
        r'([A-Z][\w\.\- ]{2,40}?)\s+(?:vs|v\.?|@)\s+([A-Z][\w\.\- ]{2,40}?)\s+'
        r'.{0,80}?(\d\.\d{2})\s+(\d\.\d{2})(?:\s+(\d\.\d{2}))?'
    )
    for m in pattern.finditer(text):
        home, away = m.group(1).strip(), m.group(2).strip()
        try:
            p1 = float(m.group(3)); p2 = float(m.group(4))
        except (TypeError, ValueError):
            continue
        outcomes = [
            {'name': home, 'price': round(p1, 4)},
            {'name': away, 'price': round(p2, 4)},
        ]
        if m.group(5):
            try:
                outcomes.append({'name': 'Draw', 'price': round(float(m.group(5)), 4)})
            except (TypeError, ValueError):
                pass
        events.append({
            'event_id': '',
            'home_team': home,
            'away_team': away,
            'commence_time': '',
            'outcomes': outcomes,
        })
    return events


def parse_events(state: Optional[Dict[str, Any]], html: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if state:
        _walk_for_events(state, events)
    if not events and html:
        events = _parse_dom_fallback(html)
    return events


def build_rows(events: List[Dict[str, Any]], sport_slug: str) -> List[Dict[str, Any]]:
    sport_key = SPORT_MAP.get(sport_slug, sport_slug)
    rows: List[Dict[str, Any]] = []
    boost_rows: List[Dict[str, Any]] = []
    seen = set()
    for ev in events:
        home = ev.get('home_team', '')
        away = ev.get('away_team', '')
        commence = (ev.get('commence_time', '') or '').replace('T', ' ').replace('Z', '')[:19]
        eid = ev.get('event_id') or _hash_event_id(sport_slug, home, away, commence)
        for o in ev.get('outcomes', []):
            name = (o.get('name') or '').strip()
            price = float(o.get('price') or 0)
            if price <= 1.01 or not name:
                continue
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
            row = {
                'sport': sport_key,
                'event_id': str(eid),
                'home_team': home,
                'away_team': away,
                'commence_time': commence,
                'bookmaker': BOOKMAKER_NAME,
                'bookmaker_key': BOOKMAKER_KEY,
                'market': 'h2h',
                'outcome_name': outcome_name,
                'outcome_price': round(price, 4),
            }
            rows.append(row)
            # Boost detection: flag lines that are suspiciously high vs typical ML range.
            # A normal ML for a favourite runs 1.20–2.00; anything >3.0 on a non-underdog
            # pick OR >6.0 on any pick that has a "was +X" pattern nearby may be a boost.
            # We emit a second row tagged betway_boost for the UI to surface separately.
            if price > BOOST_MULTIPLIER_THRESHOLD * 2:  # e.g. > 5.0 decimal (~+400)
                boost_row = dict(row)
                boost_row['bookmaker'] = 'Betway Boost'
                boost_row['bookmaker_key'] = 'betway_boost'
                boost_rows.append(boost_row)
    return rows, boost_rows


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
    parser = argparse.ArgumentParser(description='Betway CA scraper (Playwright, multi-sport).')
    parser.add_argument('--save-json', action='store_true')
    parser.add_argument('--inject-api', action='store_true')
    parser.add_argument('--inject-url', default=INJECT_URL_DEFAULT)
    parser.add_argument('--api-key', default=os.environ.get('SPORTS_INJECT_KEY', 'livetrader2026'))
    parser.add_argument('--sports', default='ice-hockey',
                        help='Comma-separated Betway sport slugs (e.g. ice-hockey,basketball,american-football).')
    parser.add_argument('--timeout-ms', type=int, default=30000)
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    print('=' * 64)
    print('Betway CA scraper (Playwright)')
    print('=' * 64)

    if not _HAS_PW:
        print('[betway] playwright not installed; exiting 0 (degraded). '
              'Install with: pip install playwright && python -m playwright install --with-deps chromium',
              file=sys.stderr)
        return 0

    sports = [s.strip() for s in args.sports.split(',') if s.strip()]
    all_rows: List[Dict[str, Any]] = []
    per_sport: Dict[str, Dict[str, int]] = {}

    for slug in sports:
        print(f'[scrape] {slug} -> {BETWAY_BASE}{slug}')
        try:
            html, state = render_sport_page(slug, args.timeout_ms, args.verbose)
        except Exception as e:
            print(f'[betway:{slug}] render failed: {e}', file=sys.stderr)
            per_sport[slug] = {'events': 0, 'rows': 0, 'error': 1}
            continue
        events = parse_events(state, html)
        rows, boost_rows = build_rows(events, slug)
        per_sport[slug] = {'events': len(events), 'rows': len(rows), 'boost_rows': len(boost_rows)}
        all_rows.extend(rows)
        all_rows.extend(boost_rows)  # inject boost lines alongside normal lines
        print(f'         events={len(events)}  rows={len(rows)}  boosts={len(boost_rows)}')
        if boost_rows:
            print(f'[boost] Possible Betway promotional lines detected:')
            for br in boost_rows:
                print(f"  {br['away_team']} @ {br['home_team']} {br['outcome_name']} dec={br['outcome_price']}")
        if args.verbose:
            for r in rows[:5]:
                print(f"           {r['away_team']} @ {r['home_team']}  {r['outcome_name']} dec={r['outcome_price']}")

    result = {
        'ok': True,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'bookmaker_key': BOOKMAKER_KEY,
        'sports_scraped': sports,
        'per_sport': per_sport,
        'rows_generated': len(all_rows),
        'rows': all_rows,
    }

    if args.save_json:
        out_dir = 'live-monitor/backfill'
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(out_dir, f'betway_{stamp}.json')
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f'[save] wrote {out_path}')

    if args.inject_api and all_rows:
        resp = post_inject(all_rows, args.inject_url, args.api_key)
        print(f'[inject] {json.dumps(resp)[:400]}')
    elif args.inject_api:
        print('[inject] no rows to inject; skipping')

    return 0


if __name__ == '__main__':
    sys.exit(main())
