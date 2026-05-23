#!/usr/bin/env python3
"""
Highlightly Tier-3 Odds Fallback Injector
==========================================
Adapter for highlightly.net (Sports API). Pulls upcoming matches + odds across
all major sports and POSTs normalized rows to:

    live-monitor/api/sports_odds.php?action=inject_fallback

Mirrors the canonical pattern in `multi_source_odds_fallback.py` (stdlib-only,
same row schema, same inject endpoint + key, dry-run argparse).

Highlightly specifics
---------------------
* Auth header   : `x-rapidapi-key: <HIGHLIGHTLY_DOT_NET>`
                  (the only header that gets past the 403 gate; "Invalid request
                  token" 401 means the key is wrong, not the header.)
* Base URL      : `https://<sport>.highlightly.net/`
                  Confirmed-resolvable subdomains as of 2026-05-04:
                    soccer, basketball, baseball, hockey, american-football,
                    rugby, cricket, handball
                  Tennis / MMA / golf / boxing do NOT resolve as subdomains
                  on the current Highlightly cluster; they are skipped here
                  and should be picked up by a separate adapter when the
                  vendor exposes them (their docs page advertises 9 sports).
* Endpoints used:
    GET /matches?date=YYYY-MM-DD     -> upcoming fixture list
    GET /odds?matchId=<id>           -> per-match odds (h2h / spreads / totals)
* Free quota    : 100 req/day. We HARD-cap at 80/run by default to leave a
                  retry margin.

Sport priority (ordered) — burns the 80-req budget on the highest-value
North-American books first, then EPL/UFC/etc. fall through if budget remains.

Usage
-----
    python3 highlightly_odds_fallback.py --dry-run
    python3 highlightly_odds_fallback.py --inject-api
    python3 highlightly_odds_fallback.py --sports nba,nhl,mlb --max-requests 40
"""

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://findtorontoevents.ca/live-monitor/api"
INJECT_KEY = "livetrader2026"
HTTP_TIMEOUT = 20
USER_AGENT = "FindTorontoEvents-Highlightly/1.0"

# Priority order for budget-bounded sport iteration.
PRIORITY = ["nba", "nhl", "nfl", "mlb", "mls", "epl", "ufc", "golf", "tennis", "cricket"]

# sport_short -> (highlightly_subdomain, sport_token, league filter)
SPORT_REGISTRY = {
    "nba":     {"sub": "basketball",        "tok": "basketball_nba",        "league": "NBA"},
    "nhl":     {"sub": "hockey",            "tok": "icehockey_nhl",         "league": "NHL"},
    "nfl":     {"sub": "american-football", "tok": "americanfootball_nfl",  "league": "NFL"},
    "mlb":     {"sub": "baseball",          "tok": "baseball_mlb",          "league": "MLB"},
    "mls":     {"sub": "soccer",            "tok": "soccer_usa_mls",        "league": "MLS"},
    "epl":     {"sub": "soccer",            "tok": "soccer_epl",            "league": "Premier League"},
    "cricket": {"sub": "cricket",           "tok": "cricket",               "league": None},
    # Sports below not currently exposed as Highlightly subdomains; included so
    # CLI accepts them but adapter degrades to a logged skip rather than crash.
    "ufc":     {"sub": None, "tok": "mma_mixed_martial_arts", "league": None},
    "golf":    {"sub": None, "tok": "golf",                   "league": None},
    "tennis":  {"sub": None, "tok": "tennis",                 "league": None},
}


# ---------------------------------------------------------------------------
# HTTP helpers (counted against budget)
# ---------------------------------------------------------------------------

class Budget:
    def __init__(self, cap):
        self.cap = cap
        self.used = 0
    def can_spend(self, n=1):
        return self.used + n <= self.cap
    def spend(self, n=1):
        self.used += n


def _http_get(url, headers, budget):
    if not budget.can_spend(1):
        return None
    budget.spend(1)
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:200]
        except Exception:
            pass
        print(f"  HTTP {exc.code} {url[:120]} :: {body}", file=sys.stderr)
    except Exception as exc:
        print(f"  fetch error {url[:120]}: {exc}", file=sys.stderr)
    return None


def _http_post_json(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:400]
        except Exception:
            pass
        print(f"  POST HTTP {exc.code} :: {body}", file=sys.stderr)
    except Exception as exc:
        print(f"  POST error: {exc}", file=sys.stderr)
    return None


def _safe_decimal(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 4) if 1.01 <= f <= 50.0 else None


# ---------------------------------------------------------------------------
# Highlightly per-sport collection
# ---------------------------------------------------------------------------

def _list_matches(sub, league, headers, budget, days_ahead=4):
    """Return [{id, home, away, ct, league}]. Costs up to `days_ahead` requests
    (one per date). Skips remaining dates if budget exhausted."""
    out = []
    today = datetime.date.today()
    for d in range(days_ahead):
        if not budget.can_spend(1):
            break
        date_str = (today + datetime.timedelta(days=d)).isoformat()
        qs = urllib.parse.urlencode({"date": date_str, "limit": 50})
        url = f"https://{sub}.highlightly.net/matches?{qs}"
        data = _http_get(url, headers, budget)
        if not isinstance(data, (dict, list)):
            continue
        items = data if isinstance(data, list) else (data.get("data") or data.get("matches") or [])
        for m in items:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("id") or m.get("matchId") or "")
            if not mid:
                continue
            lg = (m.get("league") or {})
            lg_name = lg.get("name") if isinstance(lg, dict) else (lg or "")
            if league and lg_name and league.lower() not in str(lg_name).lower():
                continue  # filter by league name
            home = m.get("homeTeam") or m.get("home") or {}
            away = m.get("awayTeam") or m.get("away") or {}
            if isinstance(home, dict):
                home = home.get("name") or home.get("displayName") or ""
            if isinstance(away, dict):
                away = away.get("name") or away.get("displayName") or ""
            ct = m.get("date") or m.get("datetime") or m.get("kickoff") or ""
            out.append({"id": mid, "home": home, "away": away, "ct": ct, "league": lg_name})
    return out


def _normalize_odds_payload(payload, sport_tok, match):
    """Highlightly /odds shape varies slightly by sport but typically returns
        { bookmakers: [ { name, markets: [ { name|key, outcomes: [ {name, price, point} ] } ] } ] }
    or a flat list. Tolerate both."""
    rows = []
    if not isinstance(payload, (dict, list)):
        return rows
    bks = payload.get("bookmakers") if isinstance(payload, dict) else payload
    if not isinstance(bks, list):
        bks = (payload.get("data") if isinstance(payload, dict) else None) or []
        if not isinstance(bks, list):
            return rows
    market_map = {
        "h2h": "h2h", "moneyline": "h2h", "money line": "h2h", "match winner": "h2h",
        "1x2": "h2h", "ml": "h2h",
        "spread": "spreads", "spreads": "spreads", "handicap": "spreads",
        "puck line": "spreads", "run line": "spreads", "asian handicap": "spreads",
        "totals": "totals", "total": "totals", "over/under": "totals", "ou": "totals",
    }
    for bk in bks:
        if not isinstance(bk, dict):
            continue
        bk_name = bk.get("name") or bk.get("bookmaker") or "Highlightly"
        bk_key = (bk.get("key") or bk_name).lower().replace(" ", "_")
        for mkt in (bk.get("markets") or bk.get("bets") or []):
            if not isinstance(mkt, dict):
                continue
            raw = (mkt.get("name") or mkt.get("key") or "").strip().lower()
            market = market_map.get(raw)
            if not market:
                continue
            for oc in (mkt.get("outcomes") or mkt.get("values") or []):
                if not isinstance(oc, dict):
                    continue
                price = _safe_decimal(oc.get("price") or oc.get("odd") or oc.get("decimal"))
                if price is None:
                    continue
                point = oc.get("point") or oc.get("handicap") or oc.get("line")
                try:
                    pt = float(point) if point is not None else None
                except (TypeError, ValueError):
                    pt = None
                rows.append({
                    "sport": sport_tok,
                    "event_id": f"hl_{match['id']}",
                    "home_team": match["home"],
                    "away_team": match["away"],
                    "commence_time": match["ct"],
                    "bookmaker": bk_name,
                    "bookmaker_key": bk_key,
                    "market": market,
                    "outcome_name": oc.get("name") or oc.get("label") or "",
                    "outcome_price": price,
                    "outcome_point": pt,
                })
    return rows


def fetch_highlightly(sport_short, headers, budget, max_matches=4):
    cfg = SPORT_REGISTRY.get(sport_short)
    if not cfg or not cfg.get("sub"):
        print(f"  highlightly [{sport_short}] no subdomain — skipped", file=sys.stderr)
        return []
    sub, tok, league = cfg["sub"], cfg["tok"], cfg.get("league")
    matches = _list_matches(sub, league, headers, budget)
    print(f"  highlightly [{sport_short}] matches: {len(matches)} (budget {budget.used}/{budget.cap})",
          file=sys.stderr)
    rows = []
    for m in matches[:max_matches]:
        if not budget.can_spend(1):
            break
        url = f"https://{sub}.highlightly.net/odds?matchId={urllib.parse.quote(m['id'])}"
        data = _http_get(url, headers, budget)
        if data is None:
            continue
        rows.extend(_normalize_odds_payload(data, tok, m))
    return rows


# ---------------------------------------------------------------------------
# Inject + main
# ---------------------------------------------------------------------------

def post_inject(rows, base_url):
    if not rows:
        return None
    url = f"{base_url}/sports_odds.php?action=inject_fallback&key={INJECT_KEY}"
    return _http_post_json(url, {"rows": rows})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject-api", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sports", default=",".join(PRIORITY))
    ap.add_argument("--max-requests", type=int, default=80,
                    help="Hard cap requests per run (free tier is 100/day, default 80 leaves a retry buffer)")
    ap.add_argument("--max-matches-per-sport", type=int, default=4)
    ap.add_argument("--base-url", default=BASE_URL)
    args = ap.parse_args(argv)

    key = (os.getenv("HIGHLIGHTLY_DOT_NET") or "").strip()
    if not key or key == "-":
        print(json.dumps({"ok": True, "skipped": "HIGHLIGHTLY_DOT_NET unset"}))
        return 0

    headers = {"x-rapidapi-key": key, "Accept": "application/json"}
    budget = Budget(max(1, args.max_requests))

    requested = [s.strip().lower() for s in args.sports.split(",") if s.strip()]
    # Order requested sports by global priority.
    targets = [s for s in PRIORITY if s in requested] + [s for s in requested if s not in PRIORITY]

    summary = {
        "ok": True,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "max_requests": args.max_requests,
        "active_targets": targets,
        "sports": {},
        "total_rows": 0,
        "posted": 0,
        "errors": [],
    }

    all_rows = []
    for short in targets:
        if short not in SPORT_REGISTRY:
            summary["errors"].append(f"unknown sport: {short}")
            continue
        if not budget.can_spend(1):
            summary["sports"][short] = {"skipped": "budget_exhausted"}
            continue
        rows = fetch_highlightly(short, headers, budget, max_matches=args.max_matches_per_sport)
        summary["sports"][short] = {
            "rows": len(rows),
            "requests_so_far": budget.used,
        }
        summary["total_rows"] += len(rows)
        all_rows.extend(rows)

    summary["requests_used"] = budget.used

    if all_rows and args.inject_api and not args.dry_run:
        for i in range(0, len(all_rows), 500):
            batch = all_rows[i:i + 500]
            r = post_inject(batch, args.base_url)
            if r and r.get("ok"):
                summary["posted"] += int(r.get("inserted") or len(batch))
            else:
                summary["errors"].append((r or {}).get("error", "post_failed"))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
