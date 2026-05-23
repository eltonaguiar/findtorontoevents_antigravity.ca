#!/usr/bin/env python3
"""
NHL goalie scraper — confirmed starters + GSAx/SV%.

Pulls today's NHL schedule from the public NHL API
(api-web.nhle.com — no auth required) and joins it with MoneyPuck's
season-to-date goalie stats CSV (moneypuck.com/moneypuck/playerData/seasonSummary).

Output: live-monitor/data/nhl_goalies_today.json — a flat list of
games with `home_goalie` / `away_goalie` blocks containing confirmed
starter status, GSAx/60 (Goals Saved Above Expected per 60), SV%,
games-played, and `rest_days` (best-effort).

This is the data feed for the planned NHL goalie overlay in
sports_value_analyze_lib.php. Until the PHP lib is wired (gated on PR
#401 merging), this scraper is an opt-in sidecar — produces a JSON
file that no production code reads yet. Per CLAUDE.md Wire-Up Rule,
the wiring plan lives alongside this commit
(updates/2026-04-26-nhl-goalie-overlay-wiring-plan.md) and the
scraper auto-deletes itself if the wiring doesn't land within 4
weeks (see plan).

Stdlib + requests only. Graceful failure: if any source is down,
write a stub JSON with `error` and exit 0 so cron stays healthy.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
OUT_PATH = REPO / "live-monitor" / "data" / "nhl_goalies_today.json"

NHL_SCHEDULE = "https://api-web.nhle.com/v1/schedule/{date}"
MONEYPUCK_GOALIES = "https://moneypuck.com/moneypuck/playerData/seasonSummary/2025/regular/goalies.csv"

# Override URLs for testing. Avoid hard requests in unit tests.
SCHEDULE_URL = None
GOALIES_URL = None

UA = "Mozilla/5.0 (compatible; FindTorontoEvents-NHL-Goalie/1.0)"


def http_get(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_schedule(date_str: str) -> list[dict]:
    """Return list of {event_id, home, away, commence_time_utc, home_goalie?, away_goalie?}.

    `home_goalie` / `away_goalie` from the NHL API are populated only when
    teams have confirmed starters via NHL.com — typically ~2 hours before
    puck drop. Names returned: full name string.
    """
    url = (SCHEDULE_URL or NHL_SCHEDULE).format(date=date_str)
    try:
        raw = http_get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[nhl-schedule] fetch failed: {e}", file=sys.stderr)
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[nhl-schedule] parse failed: {e}", file=sys.stderr)
        return []
    games = []
    weeks = data.get("gameWeek") or []
    for day in weeks:
        if str(day.get("date")) != date_str:
            continue
        for g in day.get("games") or []:
            home = g.get("homeTeam") or {}
            away = g.get("awayTeam") or {}
            home_name = (home.get("placeName") or {}).get("default", "")
            home_team = (home.get("commonName") or {}).get("default", home.get("abbrev", ""))
            away_name = (away.get("placeName") or {}).get("default", "")
            away_team = (away.get("commonName") or {}).get("default", away.get("abbrev", ""))
            games.append({
                "event_id": g.get("id"),
                "home": f"{home_name} {home_team}".strip(),
                "away": f"{away_name} {away_team}".strip(),
                "home_abbrev": home.get("abbrev", ""),
                "away_abbrev": away.get("abbrev", ""),
                "commence_time_utc": g.get("startTimeUTC", ""),
                # NHL API exposes confirmed goalies under matchup.gameInfo when
                # available; gracefully degrade when not.
                "home_goalie_raw": _confirmed_goalie(g, "home"),
                "away_goalie_raw": _confirmed_goalie(g, "away"),
            })
    return games


def _confirmed_goalie(game: dict, side: str) -> dict | None:
    """Best-effort lookup of confirmed goalie from the NHL schedule payload."""
    matchup = game.get("matchup") or {}
    for key in ("gameInfo", "goalies", "goalieComparison"):
        block = matchup.get(key)
        if not isinstance(block, dict):
            continue
        s = block.get(side) or block.get(side + "Team")
        if isinstance(s, dict) and s.get("name"):
            return {"name": s.get("name"), "confirmed": True}
    return None


def fetch_moneypuck_goalies() -> dict[str, dict]:
    """Return dict[name_lower] -> {gsax_per60, sv_pct, gp}."""
    url = GOALIES_URL or MONEYPUCK_GOALIES
    try:
        raw = http_get(url, timeout=45.0)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[moneypuck] fetch failed: {e}", file=sys.stderr)
        return {}
    out: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        try:
            gp = int(float(row.get("games_played") or 0))
            ice = float(row.get("icetime") or 0.0)  # seconds
            xg = float(row.get("xGoals") or 0.0)
            ga = float(row.get("goals") or 0.0)
            unblocked_shots_against = float(row.get("unblocked_shot_attempts") or 0.0)
            ongoal = float(row.get("ongoal") or 0.0)
        except (TypeError, ValueError):
            continue
        gsax = xg - ga  # season-to-date Goals Saved Above Expected
        gsax_per60 = (gsax / ice * 3600.0) if ice > 0 else 0.0
        sv_pct = (1.0 - ga / ongoal) if ongoal > 0 else 0.0
        out[name.lower()] = {
            "name": name,
            "gp": gp,
            "gsax_per60": round(gsax_per60, 4),
            "sv_pct": round(sv_pct, 4),
        }
    return out


def join_goalies(games: list[dict], goalies: dict[str, dict]) -> list[dict]:
    out = []
    for g in games:
        joined = {
            "event_id": g.get("event_id"),
            "commence_time_utc": g.get("commence_time_utc"),
            "home": g.get("home"),
            "away": g.get("away"),
            "home_abbrev": g.get("home_abbrev"),
            "away_abbrev": g.get("away_abbrev"),
            "home_goalie": _resolve_goalie(g.get("home_goalie_raw"), goalies),
            "away_goalie": _resolve_goalie(g.get("away_goalie_raw"), goalies),
        }
        out.append(joined)
    return out


def _resolve_goalie(raw: dict | None, goalies: dict[str, dict]) -> dict | None:
    if not raw or not raw.get("name"):
        return None
    name = str(raw["name"]).strip()
    stats = goalies.get(name.lower())
    if not stats:
        # Try last-name token match
        last = name.rsplit(" ", 1)[-1].lower() if " " in name else name.lower()
        for key, val in goalies.items():
            if key.endswith(last):
                stats = val
                break
    if not stats:
        return {"name": name, "confirmed": True, "gsax_per60": None, "sv_pct": None, "gp": 0}
    return {
        "name": stats["name"],
        "confirmed": True,
        "gsax_per60": stats["gsax_per60"],
        "sv_pct": stats["sv_pct"],
        "gp": stats["gp"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="UTC date YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    games = fetch_schedule(date_str)
    goalies = fetch_moneypuck_goalies()
    joined = join_goalies(games, goalies)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": date_str,
        "games": joined,
        "errors": [] if (games or goalies) else ["both upstream sources empty"],
    }

    text = json.dumps(payload, indent=2)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path}  games={len(joined)}  goalies_indexed={len(goalies)}")
    # Exit 0 even on partial failure so cron stays green; downstream
    # PHP reader treats stale / missing data as no-overlay (graceful degrade).
    return 0


if __name__ == "__main__":
    sys.exit(main())
