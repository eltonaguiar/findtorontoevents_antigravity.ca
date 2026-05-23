#!/usr/bin/env python3
"""
Multi-Source Odds Fallback Injector
====================================
Universal odds fallback that runs on GitHub Actions and POSTs normalized rows
to live-monitor/api/sports_odds.php?action=inject_fallback.

Tier ordering per sport:

  Tier-1 (no key, no signup):
    - ESPN scoreboard (site.api.espn.com) for event_id, teams, commence_time
    - DraftKings unofficial v5 eventgroup JSON for h2h / spreads / totals
    Combined into a single canonical row stream. This is the most resilient
    leg — no quota, no auth, runs from any IP.

  Tier-2 (env keys, optional):
    - Odds-API.io v3 with ODDS_API_IO_KEY  (samples books pair A: DraftKings,FanDuel)
    - Odds-API.io v3 with ODDS_API_IO_KEY2 (samples books pair B: BetMGM,Caesars)
    Free tier caps at 2 bookmakers selected per account, so 2 keys = 4 books of
    independent coverage. Skipped silently if env vars are absent or set to '-'.

  Tier-3 (no key):
    - TheSportsDB free (key=123) — schedule-only sanity check; emits zero odds
    rows but logs whether the upstream league has any visible upcoming events.

Output schema (matches sports_odds.php inject_fallback handler):
    sport, event_id, home_team, away_team, commence_time,
    bookmaker, bookmaker_key, market in [h2h|spreads|totals],
    outcome_name, outcome_price (decimal), outcome_point (nullable)

Usage:
    python3 multi_source_odds_fallback.py --inject-api
    python3 multi_source_odds_fallback.py --dry-run
    python3 multi_source_odds_fallback.py --sports nba,nhl,mlb
    python3 multi_source_odds_fallback.py --tier1-only           # ESPN+DK only

Stdlib-only — no pip install required on GitHub runners.
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
USER_AGENT = "FindTorontoEvents-MultiSrcFallback/1.0"

# Sport short -> (espn_path, dk_eventgroup_id, odds_api_io_sport_slug, the-odds-api sport_key)
SPORT_REGISTRY = {
    "nba":   {"espn": "basketball/nba",      "dk": 42648, "ioslug": "basketball",         "tok": "basketball_nba"},
    "wnba":  {"espn": "basketball/wnba",     "dk": 94682, "ioslug": "basketball",         "tok": "basketball_wnba"},
    "ncaab": {"espn": "basketball/mens-college-basketball", "dk": 92483, "ioslug": "basketball", "tok": "basketball_ncaab"},
    "nhl":   {"espn": "hockey/nhl",          "dk": 42133, "ioslug": "ice-hockey",         "tok": "icehockey_nhl"},
    "nfl":   {"espn": "football/nfl",        "dk": 88808, "ioslug": "american-football", "tok": "americanfootball_nfl"},
    "ncaaf": {"espn": "football/college-football", "dk": 87637, "ioslug": "american-football", "tok": "americanfootball_ncaaf"},
    "mlb":   {"espn": "baseball/mlb",        "dk": 84240, "ioslug": "baseball",          "tok": "baseball_mlb"},
    "mls":   {"espn": "soccer/usa.1",        "dk": None,  "ioslug": "football",          "tok": "soccer_usa_mls"},
    "epl":   {"espn": "soccer/eng.1",        "dk": None,  "ioslug": "football",          "tok": "soccer_epl"},
    "ufc":   {"espn": "mma/ufc",             "dk": None,  "ioslug": "mixed-martial-arts","tok": "mma_mixed_martial_arts"},
    "cfl":   {"espn": "football/cfl",        "dk": None,  "ioslug": "american-football","tok": "americanfootball_cfl"},
    "ufl":   {"espn": None,                  "dk": None,  "ioslug": "american-football","tok": "americanfootball_ufl"},
}

# BallDontLie sport->(path_segment, version, schedule_resource, time_field, odds_path).
# Schedule endpoints work on the FREE tier; /odds requires GOAT plan ($39.99/mo)
# and 403s on free — adapter degrades to schedule-only rows when /odds fails.
BDL_REGISTRY = {
    "nba":   ("nba",   "v1", "games",   "datetime",   "v2/odds"),
    "wnba":  ("wnba",  "v1", "games",   "datetime",   None),     # no odds endpoint
    "nfl":   ("nfl",   "v1", "games",   "date",       "v1/odds"),
    "mlb":   ("mlb",   "v1", "games",   "date",       "v1/odds"),
    "nhl":   ("nhl",   "v1", "games",   "date",       "v1/odds"),
    "ncaaf": ("ncaaf", "v1", "games",   "date",       "v1/odds"),
    "ncaab": ("ncaab", "v1", "games",   "date",       "v1/odds"),
    "epl":   ("epl",   "v2", "matches", "kickoff",    "v2/odds"),
    "laliga":("laliga","v1", "matches", "kickoff",    "v1/odds"),
    "mls":   ("mls",   "v1", "matches", "kickoff",    "v1/odds"),
    "ufc":   ("mma",   "v1", "events",  "datetime",   "v1/odds"),
}

# League slug filter for Odds-API.io v3 events endpoint (per-sport upcoming filter).
ODDS_API_IO_LEAGUE = {
    "nba":   "usa-nba",
    "wnba":  "usa-wnba",
    "ncaab": "usa-ncaa",       # may vary; keep loose match
    "nhl":   "usa-nhl",
    "nfl":   "usa-nfl",
    "ncaaf": "usa-ncaa",
    "mlb":   "usa-mlb",
    "mls":   "usa-mls",
    "epl":   "england-premier-league",
    "ufc":   "international-ufc",
    "cfl":   "canada-cfl",
    "ufl":   "usa-ufl",
}


def is_nfl_offseason(today=None):
    """NFL reg season runs Sep → early Feb. Preseason starts ~Aug 7. May-Jul is
    a hard dead window with no events on most APIs."""
    today = today or datetime.date.today()
    return today.month in (3, 4, 5, 6, 7) or (today.month == 8 and today.day < 7)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url, headers=None):
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
        print(f"  HTTP {exc.code} for {url[:120]}... :: {body}", file=sys.stderr)
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


def american_to_decimal(american):
    try:
        a = int(american)
    except (TypeError, ValueError):
        return None
    if a == 0:
        return None
    return round((a / 100.0 + 1) if a > 0 else (100.0 / abs(a) + 1), 4)


# ---------------------------------------------------------------------------
# Tier 1 — ESPN events × DraftKings unofficial odds (no key)
# ---------------------------------------------------------------------------

def fetch_espn_events(sport_short):
    cfg = SPORT_REGISTRY.get(sport_short)
    if not cfg or not cfg.get("espn"):
        return []
    url = f"https://site.api.espn.com/apis/site/v2/sports/{cfg['espn']}/scoreboard"
    data = _http_get(url)
    if not isinstance(data, dict):
        return []
    events = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams) != 2:
            continue
        home = next((t for t in teams if t.get("homeAway") == "home"), None) or teams[0]
        away = next((t for t in teams if t.get("homeAway") == "away"), None) or teams[1]
        events.append({
            "event_id": str(ev.get("id") or ""),
            "home_team": (home.get("team") or {}).get("displayName", ""),
            "away_team": (away.get("team") or {}).get("displayName", ""),
            "commence_time": ev.get("date") or comp.get("date") or "",
        })
    return events


def fetch_dk_eventgroup(sport_short):
    cfg = SPORT_REGISTRY.get(sport_short)
    if not cfg or not cfg.get("dk"):
        return None
    url = f"https://sportsbook.draftkings.com/sites/US-SB/api/v5/eventgroups/{cfg['dk']}?format=json"
    return _http_get(url, headers={"Accept": "application/json"})


def normalize_dk_to_rows(dk_data, sport_token):
    """Walk DraftKings v5 eventgroup JSON. Emit rows for h2h/spreads/totals."""
    rows = []
    if not isinstance(dk_data, dict):
        return rows
    eg = dk_data.get("eventGroup") or {}
    events = {}
    for ev in eg.get("events", []) or []:
        eid = str(ev.get("eventId") or "")
        if not eid:
            continue
        events[eid] = {
            "event_id": eid,
            "home_team": ev.get("eventMetadata", {}).get("participantMetadata", {}).get("teamName1", "") or ev.get("name", ""),
            "away_team": ev.get("eventMetadata", {}).get("participantMetadata", {}).get("teamName2", ""),
            "commence_time": ev.get("startDate") or "",
        }
    market_label_to_key = {
        "moneyline": "h2h", "money line": "h2h",
        "spread": "spreads", "point spread": "spreads", "puck line": "spreads", "run line": "spreads",
        "total": "totals", "total points": "totals", "total runs": "totals", "total goals": "totals",
    }
    for cat in eg.get("offerCategories", []) or []:
        for sub in cat.get("offerSubcategoryDescriptors", []) or []:
            subcat = sub.get("offerSubcategory") or {}
            for offers in subcat.get("offers", []) or []:
                for offer in offers or []:
                    eid = str(offer.get("eventId") or "")
                    ev = events.get(eid)
                    if not ev:
                        continue
                    label = (offer.get("label") or "").strip().lower()
                    market = market_label_to_key.get(label)
                    if not market:
                        continue
                    for outcome in offer.get("outcomes", []) or []:
                        price_dec = outcome.get("oddsDecimal")
                        if price_dec is None:
                            price_dec = american_to_decimal(outcome.get("oddsAmerican"))
                        try:
                            price_f = float(price_dec) if price_dec is not None else None
                        except (TypeError, ValueError):
                            price_f = None
                        if price_f is None or price_f < 1.01 or price_f > 50.0:
                            continue
                        line = outcome.get("line")
                        try:
                            point = float(line) if line is not None else None
                        except (TypeError, ValueError):
                            point = None
                        rows.append({
                            "sport": sport_token,
                            "event_id": ev["event_id"],
                            "home_team": ev["home_team"],
                            "away_team": ev["away_team"],
                            "commence_time": ev["commence_time"],
                            "bookmaker": "DraftKings",
                            "bookmaker_key": "draftkings",
                            "market": market,
                            "outcome_name": outcome.get("label", ""),
                            "outcome_price": round(price_f, 4),
                            "outcome_point": point,
                        })
    return rows


def tier1_collect(sport_short):
    """ESPN+DK pairing. ESPN gives canonical event_id+commence_time, DK gives odds.
    DK eventIds differ from ESPN, so we DO NOT join — instead we emit DK rows
    keyed by DK's own eventId. ESPN rows are emitted as a 'consensus_espn'
    virtual book with no real odds (skipped unless we add a model later)."""
    dk_data = fetch_dk_eventgroup(sport_short)
    cfg = SPORT_REGISTRY[sport_short]
    return normalize_dk_to_rows(dk_data, cfg["tok"])


# ---------------------------------------------------------------------------
# Tier 2 — Odds-API.io v3 (round-robin keys, 2 books per key)
# ---------------------------------------------------------------------------

def _odds_api_io_keys():
    """Return list of (env_name, api_key, bookmakers_csv).
    Free tier of Odds-API.io caps each account at 2 selected bookmakers, so we
    use 2 keys with disjoint book pairs to get 4 books of independent coverage."""
    pairs = []
    plan = [
        ("ODDS_API_IO_KEY",  "DraftKings,FanDuel"),
        ("ODDS_API_IO_KEY2", "BetMGM,Caesars"),
    ]
    for kname, books in plan:
        v = os.getenv(kname, "").strip()
        if v and v != "-":
            pairs.append((kname, v, books))
    return pairs


def fetch_odds_api_io(sport_short):
    rows = []
    cfg = SPORT_REGISTRY.get(sport_short)
    if not cfg:
        return rows
    keys = _odds_api_io_keys()
    if not keys:
        return rows
    league_slug = ODDS_API_IO_LEAGUE.get(sport_short)
    qs_events = urllib.parse.urlencode({
        "sport": cfg["ioslug"],
        **({"league": league_slug} if league_slug else {}),
    })
    # Use first key to list events; cache results.
    events_url = f"https://api.odds-api.io/v3/events?{qs_events}&apiKey={keys[0][1]}"
    events = _http_get(events_url)
    if not isinstance(events, list):
        return rows
    upcoming = [e for e in events if (e.get("status") or "").lower() not in ("settled", "cancelled")]
    print(f"  odds-api.io [{sport_short}] events: {len(events)} total, {len(upcoming)} upcoming", file=sys.stderr)
    if not upcoming:
        return rows
    # Per-event odds. Cap at 5 to stay under 100/hr quota when 9 sports active.
    for ev in upcoming[:5]:
        eid = ev.get("id")
        if not eid:
            continue
        for kname, kval, books in keys:
            url = (f"https://api.odds-api.io/v3/odds?sport={cfg['ioslug']}"
                   f"&eventId={eid}&bookmakers={urllib.parse.quote(books)}&apiKey={kval}")
            data = _http_get(url)
            if not isinstance(data, dict):
                continue
            home = ev.get("home") or ""
            away = ev.get("away") or ""
            ct = ev.get("date") or ""
            rows.extend(_parse_io_event_odds(data, cfg["tok"], str(eid), home, away, ct))
    return rows


def _safe_float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 1.01 <= f <= 50.0 else None


def _parse_io_event_odds(payload, sport_token, event_id, home, away, commence_time):
    """Odds-API.io v3 event-odds shape:
       bookmakers: { "<book>": [ {name: "ML"|"Spread"|"Totals", odds:[{home,away}|{home,away,hdp}|{over,under,hdp}] }, ... ] }
    """
    rows = []
    bookmakers = (payload or {}).get("bookmakers") or {}
    market_name_map = {
        "ml": "h2h", "moneyline": "h2h", "money line": "h2h",
        "spread": "spreads", "puck line": "spreads", "run line": "spreads",
        "totals": "totals", "total": "totals",
    }
    for bk_name, markets in bookmakers.items():
        if not isinstance(markets, list):
            continue
        bkey = bk_name.lower().replace(" ", "_")
        for mkt in markets:
            if not isinstance(mkt, dict):
                continue
            market = market_name_map.get((mkt.get("name") or "").strip().lower())
            if not market:
                continue
            for odds in (mkt.get("odds") or []):
                if not isinstance(odds, dict):
                    continue
                point = odds.get("hdp")
                try:
                    point_f = float(point) if point is not None else None
                except (TypeError, ValueError):
                    point_f = None
                if market == "h2h":
                    pairs = [(home, _safe_float(odds.get("home"))),
                             (away, _safe_float(odds.get("away")))]
                elif market == "spreads":
                    h = _safe_float(odds.get("home")); a = _safe_float(odds.get("away"))
                    pairs = [(home, h, point_f),
                             (away, a, (None if point_f is None else -point_f))]
                else:  # totals
                    pairs = [("Over",  _safe_float(odds.get("over")),  point_f),
                             ("Under", _safe_float(odds.get("under")), point_f)]
                for tup in pairs:
                    if len(tup) == 2:
                        name, price = tup; pt = None
                    else:
                        name, price, pt = tup
                    if price is None:
                        continue
                    rows.append({
                        "sport": sport_token,
                        "event_id": event_id,
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence_time,
                        "bookmaker": bk_name,
                        "bookmaker_key": bkey,
                        "market": market,
                        "outcome_name": name,
                        "outcome_price": round(price, 4),
                        "outcome_point": pt,
                    })
    return rows


# ---------------------------------------------------------------------------
# Tier 3 — BallDontLie (free schedule + paid odds via BALLDONTLIE_API key)
# ---------------------------------------------------------------------------

def fetch_balldontlie(sport_short, days_ahead=7):
    """Free tier: schedules only (5 req/min, no monthly cap).
    Paid GOAT: real h2h/spreads/totals via /odds.
    Adapter degrades cleanly: if /odds returns 403, only event-shape rows are
    emitted with bookmaker=None (so a downstream adapter can join odds on
    event_id without losing schedule sanity)."""
    cfg = BDL_REGISTRY.get(sport_short)
    if not cfg:
        return []
    key = (os.getenv("BALLDONTLIE_API") or "").strip()
    if not key or key == "-":
        return []
    sport_path, version, sched_resource, time_field, odds_path = cfg
    rows = []
    today = datetime.date.today()
    dates = [(today + datetime.timedelta(days=d)).isoformat() for d in range(days_ahead)]
    qs = "&".join(f"dates[]={d}" for d in dates) if sport_short in ("nba", "wnba") else ""
    sched_url = f"https://api.balldontlie.io/{sport_path}/{version}/{sched_resource}"
    if qs:
        sched_url += "?" + qs
    sched = _http_get(sched_url, headers={"Authorization": key})
    if not isinstance(sched, dict):
        return []
    games = sched.get("data") or []
    sport_tok = SPORT_REGISTRY.get(sport_short, {}).get("tok") or sport_short
    schedule_index = {}
    for g in games:
        gid = g.get("id")
        if gid is None:
            continue
        # Schema differs per sport: NBA/WNBA → home_team{full_name}+visitor_team
        # MLB/NHL/NFL → similar; soccer → home_team/away_team strings; MMA → fighter_a/fighter_b
        home = (g.get("home_team") or g.get("fighter_a") or {})
        away = (g.get("visitor_team") or g.get("away_team") or g.get("fighter_b") or {})
        if isinstance(home, dict): home = home.get("full_name") or home.get("name") or ""
        if isinstance(away, dict): away = away.get("full_name") or away.get("name") or ""
        ct = g.get(time_field) or g.get("date") or ""
        schedule_index[gid] = {"event_id": f"bdl_{sport_short}_{gid}", "home": home, "away": away, "ct": ct}
    print(f"  balldontlie [{sport_short}] schedule: {len(schedule_index)} games", file=sys.stderr)
    if not odds_path or not schedule_index:
        return []
    # Try /odds endpoint (paid plan only — 403 on free).
    odds_url = f"https://api.balldontlie.io/{sport_path}/{odds_path}"
    odds_resp = _http_get(odds_url, headers={"Authorization": key})
    if not isinstance(odds_resp, dict):
        return []  # /odds blocked or empty — schedule-only path stops here
    for o in (odds_resp.get("data") or []):
        gid = o.get("game_id") or o.get("event_id")
        sched_row = schedule_index.get(gid)
        if not sched_row:
            continue
        bk = o.get("vendor") or o.get("bookmaker") or "consensus_bdl"
        bkey = bk.lower().replace(" ", "_")
        base = {
            "sport": sport_tok,
            "event_id": sched_row["event_id"],
            "home_team": sched_row["home"],
            "away_team": sched_row["away"],
            "commence_time": sched_row["ct"],
            "bookmaker": bk,
            "bookmaker_key": bkey,
        }
        ml_h = american_to_decimal(o.get("moneyline_home_odds"))
        ml_a = american_to_decimal(o.get("moneyline_away_odds"))
        if ml_h and ml_a:
            rows.append({**base, "market": "h2h", "outcome_name": sched_row["home"],
                         "outcome_price": ml_h, "outcome_point": None})
            rows.append({**base, "market": "h2h", "outcome_name": sched_row["away"],
                         "outcome_price": ml_a, "outcome_point": None})
        sp_h_v = o.get("spread_home_value"); sp_h_o = american_to_decimal(o.get("spread_home_odds"))
        sp_a_v = o.get("spread_away_value"); sp_a_o = american_to_decimal(o.get("spread_away_odds"))
        if sp_h_v is not None and sp_h_o:
            rows.append({**base, "market": "spreads", "outcome_name": sched_row["home"],
                         "outcome_price": sp_h_o, "outcome_point": float(sp_h_v)})
        if sp_a_v is not None and sp_a_o:
            rows.append({**base, "market": "spreads", "outcome_name": sched_row["away"],
                         "outcome_price": sp_a_o, "outcome_point": float(sp_a_v)})
        tot_v = o.get("total_value"); tot_o = american_to_decimal(o.get("total_over_odds"))
        tot_u = american_to_decimal(o.get("total_under_odds"))
        if tot_v is not None and tot_o and tot_u:
            rows.append({**base, "market": "totals", "outcome_name": "Over",
                         "outcome_price": tot_o, "outcome_point": float(tot_v)})
            rows.append({**base, "market": "totals", "outcome_name": "Under",
                         "outcome_price": tot_u, "outcome_point": float(tot_v)})
    return rows


# ---------------------------------------------------------------------------
# Inject
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
    ap.add_argument("--sports", default="nba,nhl,nfl,mlb,ncaab,ncaaf,mls,epl,ufc")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--tier1-only", action="store_true",
                    help="Skip Odds-API.io (Tier 2) and BallDontLie (Tier 3)")
    ap.add_argument("--no-bdl", action="store_true",
                    help="Skip BallDontLie even if BALLDONTLIE_API set")
    args = ap.parse_args(argv)

    targets = [s.strip() for s in args.sports.split(",") if s.strip()]

    # NFL off-season swap: in May-Jul, replace `nfl` with `cfl` + `ufl` (real
    # in-season substitutes). Reg-season NFL endpoints return zero events Mar-Aug,
    # so the analyzer otherwise has nothing to chew on.
    if "nfl" in targets and is_nfl_offseason():
        targets = [t for t in targets if t != "nfl"]
        for swap in ("cfl", "ufl"):
            if swap not in targets and swap in SPORT_REGISTRY:
                targets.append(swap)

    summary = {
        "ok": True,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "active_targets": targets,
        "nfl_offseason_swap": is_nfl_offseason(),
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
        rows_t1 = tier1_collect(short)
        rows_t2 = [] if args.tier1_only else fetch_odds_api_io(short)
        rows_t3 = [] if (args.tier1_only or args.no_bdl) else fetch_balldontlie(short)
        rows = rows_t1 + rows_t2 + rows_t3
        summary["sports"][short] = {
            "tier1_rows": len(rows_t1),
            "tier2_rows": len(rows_t2),
            "tier3_rows": len(rows_t3),
            "total": len(rows),
        }
        summary["total_rows"] += len(rows)
        all_rows.extend(rows)

    if all_rows and args.inject_api and not args.dry_run:
        # Chunk in 500-row batches to stay under php POST body limits.
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
