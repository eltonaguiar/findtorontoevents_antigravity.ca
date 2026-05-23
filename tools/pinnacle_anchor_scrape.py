"""Pinnacle moneyline anchor scraper.

Fetches currently-posted full-game moneyline odds for NBA, NHL, MLB, NFL from
Pinnacle's public unauthenticated Arcadia API and writes a snapshot JSON.

Pinnacle is the sharpest book in the market (lowest vig, highest limits, sharps
welcome). Even though Ontario bettors can't wager there, the no-vig Pinnacle
line is the closest thing to "true probability" available and is ideal as an
anchor inside our value-bet analyzer (devig of soft-book consensus is biased
toward those books' shading).

Endpoints used (verified 2026-04-25, no auth required):
    GET https://guest.api.arcadia.pinnacle.com/0.1/leagues/{league_id}/matchups?brandId=0
    GET https://guest.api.arcadia.pinnacle.com/0.1/leagues/{league_id}/markets/straight

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ARCADIA_BASE = "https://guest.api.arcadia.pinnacle.com/0.1"
USER_AGENT = "Mozilla/5.0 (compatible; pinnacle-anchor-scrape/1.0)"

# league_id verified live on 2026-04-25
LEAGUES = {
    "nba": {"sport_id": 4, "league_id": 487, "name": "NBA"},
    "nhl": {"sport_id": 19, "league_id": 1456, "name": "NHL"},
    "mlb": {"sport_id": 3, "league_id": 246, "name": "MLB"},
    "nfl": {"sport_id": 15, "league_id": 889, "name": "NFL"},
}


def _get_json(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def american_to_decimal(price: int) -> float:
    """Convert American odds to decimal odds."""
    if price is None:
        return None
    if price >= 100:
        return round(1.0 + price / 100.0, 6)
    if price <= -100:
        return round(1.0 + 100.0 / abs(price), 6)
    # Pinnacle should never quote between -99..+99; treat as invalid.
    return None


def two_way_devig(home_dec: float, away_dec: float):
    """Return (devig_home_implied, devig_away_implied) using simple proportional method."""
    if not home_dec or not away_dec or home_dec <= 1 or away_dec <= 1:
        return None, None
    h = 1.0 / home_dec
    a = 1.0 / away_dec
    s = h + a
    if s <= 0:
        return None, None
    return round(h / s, 6), round(a / s, 6)


def fetch_league(league_key: str):
    """Return list of normalized event dicts for a league key (nba/nhl/mlb/nfl)."""
    cfg = LEAGUES[league_key]
    league_id = cfg["league_id"]
    matchups = _get_json(f"{ARCADIA_BASE}/leagues/{league_id}/matchups?brandId=0")
    markets = _get_json(f"{ARCADIA_BASE}/leagues/{league_id}/markets/straight")

    # Build matchup index: only "real" head-to-head fixtures (parent==None, 2 participants).
    matchup_idx = {}
    for m in matchups:
        if m.get("parent") is not None or m.get("parentId") is not None:
            continue
        parts = m.get("participants") or []
        if len(parts) != 2:
            continue
        home = next((p for p in parts if p.get("alignment") == "home"), None)
        away = next((p for p in parts if p.get("alignment") == "away"), None)
        if not home or not away:
            continue
        # Pull commence_time from period 0 cutoffAt
        commence = None
        for per in m.get("periods", []):
            if per.get("period") == 0:
                commence = per.get("cutoffAt")
                break
        if not commence:
            commence = m.get("startTime")
        matchup_idx[m["id"]] = {
            "home": home.get("name"),
            "away": away.get("name"),
            "commence_time_utc": commence,
        }

    events = []
    for mk in markets:
        if mk.get("type") != "moneyline":
            continue
        if mk.get("period") != 0:
            continue  # full-game only
        mid = mk.get("matchupId")
        meta = matchup_idx.get(mid)
        if not meta:
            continue
        prices = mk.get("prices") or []
        if len(prices) != 2:
            # Skip 3-way (draw) or futures-style markets; we only anchor 2-way.
            continue
        # Match price.participantId to participant by checking matchups payload
        # Pinnacle orders prices in the same order as participants list (home, away usually)
        # but we cannot rely on alignment via participantId here without the full participant
        # mapping. Their convention: prices[0] corresponds to the first participant in
        # matchup.participants (order==0), prices[1] to order==1. We cross-check by
        # re-reading the matchup record.
        matchup_full = next((m for m in matchups if m["id"] == mid), None)
        if not matchup_full:
            continue
        parts = matchup_full.get("participants") or []
        # order field
        ordered = sorted(parts, key=lambda p: p.get("order", 0))
        if len(ordered) != 2:
            continue
        # Map price.participantId -> alignment via the participantId field.
        # Pinnacle's matchup participants do not always carry an id field exposed here;
        # when absent, fall back to order-based mapping.
        align_by_pid = {}
        for p in ordered:
            pid = p.get("id")
            if pid is not None:
                align_by_pid[pid] = p.get("alignment")
        home_price = away_price = None
        if align_by_pid:
            for pr in prices:
                a = align_by_pid.get(pr.get("participantId"))
                if a == "home":
                    home_price = pr.get("price")
                elif a == "away":
                    away_price = pr.get("price")
        if home_price is None or away_price is None:
            # Fallback: order-based — first price = ordered[0], second = ordered[1]
            first_align = ordered[0].get("alignment")
            if first_align == "home":
                home_price, away_price = prices[0].get("price"), prices[1].get("price")
            else:
                away_price, home_price = prices[0].get("price"), prices[1].get("price")

        home_dec = american_to_decimal(home_price)
        away_dec = american_to_decimal(away_price)
        dh, da = two_way_devig(home_dec, away_dec)
        events.append({
            "sport": league_key.upper(),
            "home": meta["home"],
            "away": meta["away"],
            "commence_time_utc": meta["commence_time_utc"],
            "home_decimal": home_dec,
            "away_decimal": away_dec,
            "devig_home_implied": dh,
            "devig_away_implied": da,
        })
    return events


def main():
    ap = argparse.ArgumentParser(description="Pinnacle moneyline anchor scraper")
    ap.add_argument("--stdout", action="store_true", help="Print JSON to stdout instead of writing file")
    ap.add_argument("--sport", choices=list(LEAGUES.keys()), help="Filter to a single sport")
    args = ap.parse_args()

    sports = [args.sport] if args.sport else list(LEAGUES.keys())
    all_events = []
    sports_with_data = []
    try:
        for s in sports:
            try:
                ev = fetch_league(s)
            except urllib.error.HTTPError as he:
                # 401/403/404 on a single league shouldn't kill the whole run
                print(f"[pinnacle] league {s} http error: {he.code}", file=sys.stderr)
                continue
            if ev:
                sports_with_data.append(s)
            all_events.extend(ev)
    except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
        print(f"[pinnacle] api unreachable: {e}", file=sys.stderr)
        sys.exit(0)

    now = datetime.now(timezone.utc)
    snapshot = {
        "snapshot_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(all_events),
        "events": all_events,
    }

    if args.stdout:
        print(json.dumps(snapshot, indent=2))
        print(f"[pinnacle] stdout-only  events={len(all_events)}  sports={sports_with_data}", file=sys.stderr)
        return

    # Resolve repo root from this file location: <repo>/tools/pinnacle_anchor_scrape.py
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo_root, "data", "pinnacle_snapshots")
    os.makedirs(out_dir, exist_ok=True)
    fname = now.strftime("%Y%m%dT%H%MZ") + ".json"
    out_path = os.path.join(out_dir, fname)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    print(f"[pinnacle] wrote {out_path}  events={len(all_events)}  sports={sports_with_data}")


if __name__ == "__main__":
    main()
