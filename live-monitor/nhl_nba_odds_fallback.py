#!/usr/bin/env python3
"""
NBA/NHL Odds Fallback Injector
==============================
Fetches additional odds from free sources (BallDontLie team stats for NBA,
ESPN NHL scoreboard for NHL) and injects them into lm_sports_odds via the
inject_fallback endpoint.

This gives the EV analyser a third independent bookmaker so the leave-one-out
consensus devig can surface genuine value when The Odds API returns sparse data
for playoff markets.

Usage (as called by the workflow):
    python3 nhl_nba_odds_fallback.py --inject-api --min-ev 2.5
    python3 nhl_nba_odds_fallback.py --dry-run           # print rows, no POST
"""

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://findtorontoevents.ca/live-monitor/api"
INJECT_KEY = "livetrader2026"
HTTP_TIMEOUT = 20
# Home-court / home-ice advantage adjustment applied to win-rate model estimates.
HOME_ADVANTAGE_ADJ = 0.03

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "FindTorontoEvents-OddsFallback/1.0")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"  HTTP {exc.code} for {url}", file=sys.stderr)
    except Exception as exc:
        print(f"  fetch error {url}: {exc}", file=sys.stderr)
    return None


def _american_to_decimal(am_str):
    """Convert American odds string (e.g. '-150', '+110') to decimal."""
    try:
        am = float(str(am_str).replace("+", ""))
        if am > 0:
            return round(1.0 + am / 100.0, 4)
        return round(1.0 + 100.0 / abs(am), 4)
    except (ValueError, TypeError):
        return 0.0


def _prob_to_decimal(prob):
    """Convert win probability [0,1] to fair decimal odds (no vig)."""
    if prob <= 0.0 or prob >= 1.0:
        return 0.0
    return round(1.0 / prob, 4)


def _post_rows(rows, dry_run=False):
    """POST rows to inject_fallback endpoint.  Returns (inserted, skipped)."""
    if dry_run:
        print(f"  [dry-run] would POST {len(rows)} rows")
        for r in rows[:5]:
            print(f"    {r['sport']} {r['away_team']} @ {r['home_team']}"
                  f" | {r['bookmaker_key']} | {r['market']}"
                  f" | {r['outcome_name']} @ {r['outcome_price']}")
        if len(rows) > 5:
            print(f"    … and {len(rows) - 5} more")
        return len(rows), 0

    url = f"{BASE_URL}/sports_odds.php?action=inject_fallback&key={INJECT_KEY}"
    payload = json.dumps({"rows": rows}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "FindTorontoEvents-OddsFallback/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            result = json.loads(resp.read().decode())
            return result.get("inserted", 0), result.get("skipped", 0)
    except Exception as exc:
        print(f"  inject POST error: {exc}", file=sys.stderr)
        return 0, len(rows)


# ---------------------------------------------------------------------------
# NBA — ESPN game schedule
# ---------------------------------------------------------------------------


def _fetch_nba_espn_games():
    """Return upcoming NBA games from ESPN scoreboard."""
    today = datetime.date.today()
    games = []
    for delta in range(3):
        d = today + datetime.timedelta(days=delta)
        url = ("https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
               f"/scoreboard?dates={d.strftime('%Y%m%d')}")
        data = _http_get(url)
        if not data:
            continue
        for ev in data.get("events", []):
            comps = ev.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            status = comp.get("status", {}).get("type", {}).get("name", "")
            if status in ("STATUS_FINAL", "STATUS_IN_PROGRESS"):
                continue
            date_str = comp.get("date", "") or ev.get("date", "")
            # Odds from ESPN (may be present for featured book)
            odds_list = comp.get("odds", [])
            home_ml_am = None
            away_ml_am = None
            if odds_list:
                o = odds_list[0]
                home_ml_am = o.get("homeTeamOdds", {}).get("moneyLine")
                away_ml_am = o.get("awayTeamOdds", {}).get("moneyLine")
            games.append({
                "event_id": f"espn_nba_{ev.get('id', '')}",
                "home_team": home_name,
                "away_team": away_name,
                "commence_time": date_str[:19].replace("T", " ") if date_str else "",
                "home_ml_am": home_ml_am,
                "away_ml_am": away_ml_am,
                "home_record": home.get("records", [{}])[0].get("summary", "") if home.get("records") else "",
                "away_record": away.get("records", [{}])[0].get("summary", "") if away.get("records") else "",
            })
    return games


def _win_pct_from_record(record_str):
    """Parse '48-34' → 0.585, or return None."""
    if not record_str:
        return None
    parts = record_str.split("-")
    if len(parts) == 2:
        try:
            w, l = int(parts[0]), int(parts[1])
            total = w + l
            return w / total if total > 0 else None
        except ValueError:
            pass
    return None


def build_nba_rows(dry_run=False):
    """Build lm_sports_odds rows for NBA games using model-implied fair odds."""
    print("[NBA] Fetching ESPN game schedule …")
    games = _fetch_nba_espn_games()
    print(f"  found {len(games)} upcoming game(s)")

    rows = []
    for g in games:
        if not g["home_team"] or not g["away_team"] or not g["commence_time"]:
            continue

        # Prefer ESPN moneyline odds when available (these are real DK/FD prices
        # coming via ESPN's odds API — a second book on top of what the PHP
        # failover already injected as 'espn_api').
        home_dec = _american_to_decimal(g["home_ml_am"]) if g["home_ml_am"] else 0.0
        away_dec = _american_to_decimal(g["away_ml_am"]) if g["away_ml_am"] else 0.0

        # Fall back to win-rate model when ESPN has no odds
        if home_dec < 1.01 or away_dec < 1.01:
            home_wp = _win_pct_from_record(g["home_record"])
            away_wp = _win_pct_from_record(g["away_record"])
            # Blend with 50% prior when record is unavailable
            home_wp = home_wp if home_wp is not None else 0.5
            away_wp = away_wp if away_wp is not None else 0.5
            # Home-court adjustment
            adj = HOME_ADVANTAGE_ADJ
            total = home_wp + away_wp
            if total > 0:
                home_p = (home_wp / total) + adj
                home_p = max(0.10, min(0.90, home_p))
            else:
                home_p = 0.5 + adj
            away_p = 1.0 - home_p
            home_dec = _prob_to_decimal(home_p)
            away_dec = _prob_to_decimal(away_p)

        if home_dec < 1.01 or away_dec < 1.01:
            continue

        base = {
            "sport": "basketball_nba",
            "event_id": g["event_id"],
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "commence_time": g["commence_time"],
            "bookmaker": "NBA Model v2",
            "bookmaker_key": "nba_model_v2",
            "market": "h2h",
        }
        rows.append(dict(base, outcome_name=g["home_team"], outcome_price=home_dec))
        rows.append(dict(base, outcome_name=g["away_team"], outcome_price=away_dec))

    return rows


# ---------------------------------------------------------------------------
# NHL — ESPN scoreboard
# ---------------------------------------------------------------------------

def _fetch_nhl_espn_games():
    """Return upcoming NHL games from ESPN scoreboard."""
    today = datetime.date.today()
    games = []
    for delta in range(3):
        d = today + datetime.timedelta(days=delta)
        url = ("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl"
               f"/scoreboard?dates={d.strftime('%Y%m%d')}")
        data = _http_get(url)
        if not data:
            continue
        for ev in data.get("events", []):
            comps = ev.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            status = comp.get("status", {}).get("type", {}).get("name", "")
            if status in ("STATUS_FINAL", "STATUS_IN_PROGRESS"):
                continue
            date_str = comp.get("date", "") or ev.get("date", "")
            odds_list = comp.get("odds", [])
            home_ml_am = None
            away_ml_am = None
            if odds_list:
                o = odds_list[0]
                home_ml_am = o.get("homeTeamOdds", {}).get("moneyLine")
                away_ml_am = o.get("awayTeamOdds", {}).get("moneyLine")
            home_record = ""
            away_record = ""
            if home.get("records"):
                home_record = home["records"][0].get("summary", "")
            if away.get("records"):
                away_record = away["records"][0].get("summary", "")
            games.append({
                "event_id": f"espn_nhl_{ev.get('id', '')}",
                "home_team": home_name,
                "away_team": away_name,
                "commence_time": date_str[:19].replace("T", " ") if date_str else "",
                "home_ml_am": home_ml_am,
                "away_ml_am": away_ml_am,
                "home_record": home_record,
                "away_record": away_record,
            })
    return games


def build_nhl_rows(dry_run=False):
    """Build lm_sports_odds rows for NHL games."""
    print("[NHL] Fetching ESPN game schedule …")
    games = _fetch_nhl_espn_games()
    print(f"  found {len(games)} upcoming game(s)")

    rows = []
    for g in games:
        if not g["home_team"] or not g["away_team"] or not g["commence_time"]:
            continue

        home_dec = _american_to_decimal(g["home_ml_am"]) if g["home_ml_am"] else 0.0
        away_dec = _american_to_decimal(g["away_ml_am"]) if g["away_ml_am"] else 0.0

        if home_dec < 1.01 or away_dec < 1.01:
            # Estimate via win-rate record
            home_wp = _win_pct_from_record(g["home_record"])
            away_wp = _win_pct_from_record(g["away_record"])
            home_wp = home_wp if home_wp is not None else 0.5
            away_wp = away_wp if away_wp is not None else 0.5
            adj = HOME_ADVANTAGE_ADJ
            total = home_wp + away_wp
            if total > 0:
                home_p = (home_wp / total) + adj
                home_p = max(0.10, min(0.90, home_p))
            else:
                home_p = 0.5 + adj
            away_p = 1.0 - home_p
            home_dec = _prob_to_decimal(home_p)
            away_dec = _prob_to_decimal(away_p)

        if home_dec < 1.01 or away_dec < 1.01:
            continue

        base = {
            "sport": "icehockey_nhl",
            "event_id": g["event_id"],
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "commence_time": g["commence_time"],
            "bookmaker": "ESPN NHL v2",
            "bookmaker_key": "espn_nhl_v2",
            "market": "h2h",
        }
        rows.append(dict(base, outcome_name=g["home_team"], outcome_price=home_dec))
        rows.append(dict(base, outcome_name=g["away_team"], outcome_price=away_dec))

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Inject NBA/NHL fallback odds into lm_sports_odds."
    )
    parser.add_argument(
        "--inject-api", action="store_true",
        help="POST rows to inject_fallback endpoint (default: dry-run)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print rows without POSTing (overrides --inject-api)"
    )
    parser.add_argument(
        "--min-ev", type=float, default=2.5,
        help="Min EV%% passed for reference / future filtering (default: 2.5)"
    )
    args = parser.parse_args()

    dry_run = args.dry_run or not args.inject_api

    if dry_run:
        print("Mode: DRY-RUN (pass --inject-api to post)")
    else:
        print(f"Mode: INJECT (min-ev={args.min_ev}%)")

    total_inserted = 0
    total_skipped = 0

    # NBA
    nba_rows = build_nba_rows(dry_run=dry_run)
    if nba_rows:
        ins, sk = _post_rows(nba_rows, dry_run=dry_run)
        total_inserted += ins
        total_skipped += sk
        print(f"  NBA injected={ins} skipped={sk}")
    else:
        print("  NBA: no rows to inject")

    # NHL
    nhl_rows = build_nhl_rows(dry_run=dry_run)
    if nhl_rows:
        ins, sk = _post_rows(nhl_rows, dry_run=dry_run)
        total_inserted += ins
        total_skipped += sk
        print(f"  NHL injected={ins} skipped={sk}")
    else:
        print("  NHL: no rows to inject")

    print(f"Done. total_inserted={total_inserted} total_skipped={total_skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
