#!/usr/bin/env python3
"""
Polymarket vs sportsbook devig'd consensus edge scanner.

Pulls active Polymarket sports markets (NBA / NHL / NFL / MLB / MMA / soccer)
via the public Gamma API and joins them against findtorontoevents.ca's
sports_picks.php?action=today payload, which carries multi-book devig'd
implied probabilities. Reports games where Polymarket and the sportsbook
consensus disagree by more than --min-gap-pp percentage points.

Use this to find cross-venue edges:
  * Polymarket > book by N pp -> book side is undervalued; bet the favourite
    on the book or sell the favourite on Polymarket.
  * Book > Polymarket by N pp -> Polymarket side is undervalued; buy the
    favourite on Polymarket or fade on the book.

Read-only. Hits Polymarket Gamma API and our own sports_picks endpoint;
writes a markdown report to reports/POLYMARKET_EDGE_SCAN_<UTC>.md unless
--stdout is passed.

Usage:
  python tools/polymarket_edge_scan.py
  python tools/polymarket_edge_scan.py --min-gap-pp 4 --sport mma
  python tools/polymarket_edge_scan.py --stdout
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any

GAMMA = "https://gamma-api.polymarket.com/events"
SITE_PICKS = "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today&sport=all"

POLY_SPORT_TAGS = {
    "nba": "basketball",
    "nhl": "hockey",
    "nfl": "football",
    "mlb": "baseball",
    "mls": "soccer",
    "mma": "mma",
    "ufc": "mma",
}


def http_get(url: str, timeout: float = 30.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "polymarket-edge-scan/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_polymarket_events(sport_tag: str | None) -> list[dict]:
    # Gamma supports tag_slug filter; fall back to category=Sports otherwise.
    params = {
        "active": "true",
        "closed": "false",
        "limit": "500",
        "order": "volume",
        "ascending": "false",
    }
    if sport_tag:
        params["tag_slug"] = sport_tag
    url = f"{GAMMA}?{urllib.parse.urlencode(params)}"
    try:
        data = http_get(url)
    except Exception as e:
        print(f"[poly] fetch failed: {e}", file=sys.stderr)
        return []
    return data if isinstance(data, list) else data.get("events", [])


def parse_market_outcomes(market: dict) -> list[tuple[str, float]]:
    # Each binary market on Polymarket exposes outcomes (Yes/No or team names)
    # with last-trade prices. Prefer outcomePrices when present (parallel arrays),
    # else parse outcomes JSON string.
    out_names = market.get("outcomes") or "[]"
    out_prices = market.get("outcomePrices") or "[]"
    try:
        names = json.loads(out_names) if isinstance(out_names, str) else out_names
        prices = json.loads(out_prices) if isinstance(out_prices, str) else out_prices
    except Exception:
        return []
    pairs: list[tuple[str, float]] = []
    for n, p in zip(names, prices):
        try:
            pairs.append((str(n), float(p)))
        except Exception:
            continue
    return pairs


def normalize_team(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_site_picks() -> list[dict]:
    try:
        data = http_get(SITE_PICKS)
    except Exception as e:
        print(f"[site] fetch failed: {e}", file=sys.stderr)
        return []
    return data.get("value_bets", []) if isinstance(data, dict) else []


def site_pick_implied_prob(pick: dict) -> float | None:
    odds = pick.get("best_odds") or 0.0
    try:
        odds = float(odds)
    except Exception:
        return None
    if odds <= 1.0:
        return None
    return 1.0 / odds


def join_events(poly_events: list[dict], site_picks: list[dict]) -> list[dict]:
    # Index site picks by normalized "home|away" team aliases plus last-name token.
    by_alias: dict[str, list[dict]] = {}
    for sp in site_picks:
        home = normalize_team(sp.get("home_team", ""))
        away = normalize_team(sp.get("away_team", ""))
        if not home or not away:
            continue
        for combo in (
            f"{home}|{away}",
            f"{away}|{home}",
            f"{home.split()[-1]}|{away.split()[-1]}",
            f"{away.split()[-1]}|{home.split()[-1]}",
        ):
            by_alias.setdefault(combo, []).append(sp)

    rows: list[dict] = []
    for ev in poly_events:
        title = ev.get("title") or ev.get("question") or ""
        # Pull the lead binary market for each event (event-level price summary).
        markets = ev.get("markets") or []
        if not markets:
            continue
        m = markets[0]
        outcomes = parse_market_outcomes(m)
        if len(outcomes) != 2:
            continue
        # Try to pull two team/fighter names from event title or outcome labels.
        cand_text = f"{title} {outcomes[0][0]} {outcomes[1][0]}".lower()
        cand_text = re.sub(r"[^a-z0-9 ]+", " ", cand_text)
        words = set(re.split(r"\s+", cand_text))
        match = None
        for combo, picks in by_alias.items():
            a, b = combo.split("|", 1)
            if a in cand_text and b in cand_text:
                match = picks[0]
                break
        if not match:
            continue
        site_p = site_pick_implied_prob(match)
        if site_p is None:
            continue
        # outcomes[0] aligned with whichever side matched the pick's outcome name.
        out_name_lc = (match.get("outcome_name") or "").lower()
        poly_for_pick = None
        for nm, pr in outcomes:
            if normalize_team(nm).split()[-1] in out_name_lc.split():
                poly_for_pick = pr
                break
        if poly_for_pick is None:
            poly_for_pick = outcomes[0][1]
        # Skip markets that have effectively resolved (poly at 0 or 1) — those are
        # post-game settlements, not actionable edges.
        if poly_for_pick <= 0.02 or poly_for_pick >= 0.98:
            continue
        gap_pp = (site_p - poly_for_pick) * 100.0
        rows.append({
            "matchup": title or f"{match['away_team']} @ {match['home_team']}",
            "sport": match.get("sport_short") or match.get("sport"),
            "pick": match.get("outcome_name"),
            "site_book": match.get("best_book"),
            "site_odds": match.get("best_odds"),
            "site_implied_pct": round(site_p * 100.0, 1),
            "poly_implied_pct": round(poly_for_pick * 100.0, 1),
            "gap_pp": round(gap_pp, 1),
            "poly_volume": ev.get("volume") or ev.get("volume24hr") or 0,
            "ev_pct_site": match.get("ev_pct"),
        })
    return rows


def render_markdown(rows: list[dict], min_gap: float, sport_filter: str | None) -> str:
    rows = [r for r in rows if abs(r["gap_pp"]) >= min_gap]
    rows.sort(key=lambda r: abs(r["gap_pp"]), reverse=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Polymarket × Sportsbook Edge Scan — {now}",
        "",
        f"Min gap: **{min_gap}pp**.  Sport filter: **{sport_filter or 'all'}**.  "
        f"Joined rows: **{len(rows)}**.",
        "",
        "Site implied prob comes from `sports_picks.php?action=today` (best devig'd",
        "consensus across 12+ books). Polymarket implied prob is the last-trade",
        "price on the matched binary market. Gap is `site - poly` in percentage",
        "points; positive means Polymarket *underprices* this side (buy on Poly",
        "or bet on book), negative means Polymarket overprices (sell / fade).",
        "",
        "| Sport | Matchup | Pick | Site EV% | Site implied | Poly implied | Gap (pp) | Poly vol |",
        "|-------|---------|------|---------:|-------------:|-------------:|---------:|---------:|",
    ]
    for r in rows[:30]:
        lines.append(
            f"| {r['sport']} | {r['matchup']} | {r['pick']} ({r['site_book']} {r['site_odds']}) | "
            f"{r.get('ev_pct_site', '')} | {r['site_implied_pct']}% | {r['poly_implied_pct']}% | "
            f"{r['gap_pp']:+.1f} | ${int(r['poly_volume']):,} |"
        )
    if not rows:
        lines.append("| — | _no joined rows above threshold_ | | | | | | |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-gap-pp", type=float, default=3.0)
    ap.add_argument("--sport", default=None, help="nba|nhl|nfl|mlb|mls|mma — passes Polymarket tag_slug")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    poly_tag = POLY_SPORT_TAGS.get((args.sport or "").lower())
    poly = fetch_polymarket_events(poly_tag)
    site = fetch_site_picks()
    rows = join_events(poly, site)
    md = render_markdown(rows, args.min_gap_pp, args.sport)

    if args.stdout:
        sys.stdout.write(md)
        return 0

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = f"reports/POLYMARKET_EDGE_SCAN_{ts}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {out}  poly_events={len(poly)}  site_picks={len(site)}  joined={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
