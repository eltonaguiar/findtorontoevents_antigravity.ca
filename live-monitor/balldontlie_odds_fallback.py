#!/usr/bin/env python3
"""
BALLDONTLIE Tier-3 Odds + Schedule Fallback
============================================
Companion to ``multi_source_odds_fallback.py`` (Tier-1 ESPN+DK / Tier-2
Odds-API.io). This script is a *standalone* Tier-3 leg that uses the
BallDontLie v1 API to inject schedule and (where available) odds rows for
six leagues:

    NBA, WNBA, NFL, MLB, NHL, MMA

API base:  https://api.balldontlie.io/v1/
Auth:      Authorization: Bearer ${BALLDONTLIE_API_KEY}
Free tier: 60 req/min; schedules are free, /v1/odds is only on paid plans.

Schedule-only fallback note
---------------------------
On the free tier the ``/v1/odds`` endpoint typically responds 401/403/404 and
this adapter degrades to *schedule-only* sanity rows: the schedule rows are
emitted with ``bookmaker=None`` and zero outcome rows so the analyzer can
detect missing-event drift versus Tier-1/2 sources without false-positive
odds. If the operator upgrades to a paid tier, the same script begins
emitting real h2h/spreads/totals rows on the next run.

Schema (matches ``sports_odds.php?action=inject_fallback``):
    sport, event_id, home_team, away_team, commence_time,
    bookmaker, bookmaker_key, market in [h2h|spreads|totals],
    outcome_name, outcome_price (decimal), outcome_point (nullable)

Skip-if-no-key:
    If ``BALLDONTLIE_API_KEY`` is unset or ``-``, the script prints a
    ``{"skipped": true}`` summary and exits 0 — no exception.

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
BDL_BASE = "https://api.balldontlie.io/v1"
INJECT_KEY = "livetrader2026"
HTTP_TIMEOUT = 20
USER_AGENT = "FindTorontoEvents-BallDontLieFallback/1.0"

# sport_short -> (bdl_path_segment, schedule_resource, time_field, sport_token).
# sport_token mirrors the canonical the-odds-api keys used in PHP analyzer.
BDL_SPORTS = {
    "nba":  ("nba",  "games",  "datetime", "basketball_nba"),
    "wnba": ("wnba", "games",  "datetime", "basketball_wnba"),
    "nfl":  ("nfl",  "games",  "date",     "americanfootball_nfl"),
    "mlb":  ("mlb",  "games",  "date",     "baseball_mlb"),
    "nhl":  ("nhl",  "games",  "date",     "icehockey_nhl"),
    "mma":  ("mma",  "fights", "datetime", "mma_mixed_martial_arts"),
}


# ---------------------------------------------------------------------------
# HTTP helpers (mirrored from multi_source_odds_fallback.py)
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
# Schedule fetch (free tier)
# ---------------------------------------------------------------------------

def fetch_schedule(sport_short, api_key, days_ahead=7):
    cfg = BDL_SPORTS.get(sport_short)
    if not cfg:
        return []
    sport_path, sched_resource, time_field, sport_tok = cfg
    headers = {"Authorization": f"Bearer {api_key}"}

    today = datetime.date.today()
    base_url = f"{BDL_BASE}/{sport_path}/{sched_resource}" if sport_path != "nba" \
               else f"{BDL_BASE}/{sched_resource}"
    # NBA lives at /v1/games (no /nba/ segment). All others at /v1/<sport>/<resource>.

    if sport_short in ("nba", "wnba"):
        # date-array param works on NBA/WNBA games
        params = "&".join(f"dates[]={(today + datetime.timedelta(days=d)).isoformat()}"
                          for d in range(days_ahead))
        params += "&per_page=100"
        url = f"{base_url}?{params}"
    else:
        # Default to upcoming season filter; schema varies, keep loose
        season = today.year if today.month >= 8 else today.year - 1
        url = f"{base_url}?seasons[]={season}&per_page=100"

    resp = _http_get(url, headers=headers)
    if not isinstance(resp, dict):
        return []

    events = []
    for g in (resp.get("data") or []):
        gid = g.get("id")
        if gid is None:
            continue
        # Schema differs per sport: NBA/WNBA → home_team{full_name}+visitor_team
        # NHL/MLB/NFL → home_team/visitor_team objects; MMA → fighter_a/fighter_b.
        home = g.get("home_team") or g.get("fighter_a") or {}
        away = g.get("visitor_team") or g.get("away_team") or g.get("fighter_b") or {}
        if isinstance(home, dict):
            home = home.get("full_name") or home.get("name") or home.get("display_name") or ""
        if isinstance(away, dict):
            away = away.get("full_name") or away.get("name") or away.get("display_name") or ""
        ct = g.get(time_field) or g.get("date") or g.get("datetime") or ""
        # Filter past games when commence_time parseable
        events.append({
            "event_id": f"bdl_{sport_short}_{gid}",
            "home_team": home,
            "away_team": away,
            "commence_time": ct,
            "sport_token": sport_tok,
        })
    return events


# ---------------------------------------------------------------------------
# Odds fetch (paid tier — degrades silently to no-op on free)
# ---------------------------------------------------------------------------

def fetch_odds(sport_short, schedule_index, api_key):
    """Try /v1/odds endpoint. If it 401/403/404s (free tier), return []."""
    cfg = BDL_SPORTS.get(sport_short)
    if not cfg or not schedule_index:
        return []
    sport_path, _, _, sport_tok = cfg
    headers = {"Authorization": f"Bearer {api_key}"}
    # Try sport-scoped odds endpoint; BallDontLie hosts /v1/odds and /v2/odds
    # depending on plan tier; we probe the v1 namespace.
    url = f"{BDL_BASE}/{sport_path}/odds" if sport_path != "nba" \
          else f"{BDL_BASE}/odds"
    resp = _http_get(url, headers=headers)
    if not isinstance(resp, dict):
        return []
    rows = []
    for o in (resp.get("data") or []):
        gid = o.get("game_id") or o.get("event_id") or o.get("fight_id")
        ev = schedule_index.get(gid) or schedule_index.get(f"bdl_{sport_short}_{gid}")
        if not ev:
            continue
        bk = o.get("vendor") or o.get("bookmaker") or "consensus_bdl"
        bkey = bk.lower().replace(" ", "_")
        base = {
            "sport": sport_tok,
            "event_id": ev["event_id"],
            "home_team": ev["home_team"],
            "away_team": ev["away_team"],
            "commence_time": ev["commence_time"],
            "bookmaker": bk,
            "bookmaker_key": bkey,
        }
        ml_h = american_to_decimal(o.get("moneyline_home_odds"))
        ml_a = american_to_decimal(o.get("moneyline_away_odds"))
        if ml_h and ml_a:
            rows.append({**base, "market": "h2h", "outcome_name": ev["home_team"],
                         "outcome_price": ml_h, "outcome_point": None})
            rows.append({**base, "market": "h2h", "outcome_name": ev["away_team"],
                         "outcome_price": ml_a, "outcome_point": None})
        sp_h_v = o.get("spread_home_value"); sp_h_o = american_to_decimal(o.get("spread_home_odds"))
        sp_a_v = o.get("spread_away_value"); sp_a_o = american_to_decimal(o.get("spread_away_odds"))
        if sp_h_v is not None and sp_h_o:
            rows.append({**base, "market": "spreads", "outcome_name": ev["home_team"],
                         "outcome_price": sp_h_o, "outcome_point": float(sp_h_v)})
        if sp_a_v is not None and sp_a_o:
            rows.append({**base, "market": "spreads", "outcome_name": ev["away_team"],
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
    ap.add_argument("--sports", default="nba,wnba,nfl,mlb,nhl,mma")
    ap.add_argument("--base-url", default=BASE_URL)
    args = ap.parse_args(argv)

    api_key = (os.getenv("BALLDONTLIE_API_KEY") or "").strip()
    if not api_key or api_key == "-":
        print(json.dumps({
            "ok": True,
            "skipped": True,
            "reason": "BALLDONTLIE_API_KEY env var unset or '-'",
        }, indent=2))
        return 0

    targets = [s.strip() for s in args.sports.split(",") if s.strip()]
    summary = {
        "ok": True,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "active_targets": targets,
        "sports": {},
        "total_schedule_rows": 0,
        "total_odds_rows": 0,
        "posted": 0,
        "errors": [],
        "samples": [],
    }

    all_odds_rows = []
    for short in targets:
        if short not in BDL_SPORTS:
            summary["errors"].append(f"unknown sport: {short}")
            continue
        sched = fetch_schedule(short, api_key)
        sched_index = {ev["event_id"]: ev for ev in sched}
        odds_rows = fetch_odds(short, sched_index, api_key)
        summary["sports"][short] = {
            "schedule_rows": len(sched),
            "odds_rows": len(odds_rows),
        }
        summary["total_schedule_rows"] += len(sched)
        summary["total_odds_rows"] += len(odds_rows)
        all_odds_rows.extend(odds_rows)
        if sched and len(summary["samples"]) < 3:
            summary["samples"].append({"sport": short, "sample_event": sched[0]})

    if all_odds_rows and args.inject_api and not args.dry_run:
        # Chunk in 500-row batches to stay under php POST body limits.
        for i in range(0, len(all_odds_rows), 500):
            batch = all_odds_rows[i:i + 500]
            r = post_inject(batch, args.base_url)
            if r and r.get("ok"):
                summary["posted"] += int(r.get("inserted") or len(batch))
            else:
                summary["errors"].append((r or {}).get("error", "post_failed"))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
