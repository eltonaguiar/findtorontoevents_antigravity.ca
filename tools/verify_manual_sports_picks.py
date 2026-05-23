#!/usr/bin/env python3
"""
Verify manual tennis/golf/UFC picks against Polymarket.

Parses the curated picks arrays embedded in
live-monitor/sports-betting.html, fuzzy-matches each pick's outcome_name
against active Polymarket markets (Gamma API), and reports gaps between
the bookmaker implied probability (from best_odds) and Polymarket's
last-trade implied probability.

Output: reports/MANUAL_SPORTS_PICKS_VERIFICATION_<UTC>.md (and JSON sidecar).

Read-only. Hits Polymarket public Gamma API only. No writes outside reports/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "live-monitor" / "sports-betting.html"
GAMMA = "https://gamma-api.polymarket.com/events"

POLY_TAGS = {
    "tennis_atp": "tennis",
    "golf_pga": "golf",
    "ufc_mma": "mma",
}


def http_get_json(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": "manual-pick-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def extract_picks_array(html: str, var_name: str) -> list[dict]:
    """Extract a JS array literal `var <var_name> = [ ... ];` and parse it as JSON-like."""
    m = re.search(rf"var\s+{re.escape(var_name)}\s*=\s*(\[.*?\n\]);", html, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    # Convert JS object literal to JSON: quote keys, replace single quotes with double quotes,
    # strip trailing commas, escape inner apostrophes already handled by \'.
    # 1. Replace JS-escaped single quote \' with placeholder
    body = body.replace(r"\'", "")
    # 2. Quote bare keys: `key:` -> `"key":`
    body = re.sub(r"([{,\s])([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
    # 3. Convert single-quoted strings to double-quoted, escaping any inner double quotes
    def sq_to_dq(m):
        s = m.group(1).replace('"', '\\"')
        return '"' + s + '"'
    body = re.sub(r"'((?:[^'\\]|\\.)*)'", sq_to_dq, body)
    # 4. Restore escaped apostrophes as plain '
    body = body.replace("", "'")
    # 5. Remove trailing commas before ] or }
    body = re.sub(r",(\s*[\]}])", r"\1", body)
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        print(f"[parse] {var_name}: JSON decode failed at {e.pos}: {e.msg}", file=sys.stderr)
        print(body[max(0, e.pos - 80):e.pos + 80], file=sys.stderr)
        return []


def fetch_polymarket_events(tag_slug: str) -> list[dict]:
    params = {
        "active": "true",
        "closed": "false",
        "limit": "300",
        "order": "volume",
        "ascending": "false",
        "tag_slug": tag_slug,
    }
    url = f"{GAMMA}?{urllib.parse.urlencode(params)}"
    try:
        data = http_get_json(url)
    except Exception as e:
        print(f"[poly] {tag_slug}: fetch failed: {e}", file=sys.stderr)
        return []
    return data if isinstance(data, list) else data.get("events", [])


def parse_outcome_prices(market: dict) -> list[tuple[str, float]]:
    """Return [(outcome_name, last_price), ...] for a Polymarket market."""
    outcomes = market.get("outcomes")
    prices = market.get("outcomePrices")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except Exception:
            prices = []
    out = []
    if isinstance(outcomes, list) and isinstance(prices, list):
        for name, p in zip(outcomes, prices):
            try:
                out.append((str(name), float(p)))
            except (TypeError, ValueError):
                continue
    return out


def best_match(
    player: str,
    opponent: str | None,
    candidates: list[tuple[dict, dict]],
) -> tuple[dict, dict, float] | None:
    """Find the Polymarket (event, market) whose question best matches the pick.

    Prefers head-to-head markets where both the player and opponent appear; falls
    back to single-name match. Returns (event, market, score) or None when no
    candidate clears 0.65.
    """
    p = player.lower().strip()
    opp = (opponent or "").lower().strip()
    best = None
    best_score = 0.0
    for ev, mkt in candidates:
        question = (mkt.get("question") or "").lower()
        title = (ev.get("title") or "").lower()
        haystack = f"{question} | {title}"
        if not haystack.strip(" |"):
            continue
        score = 0.0
        # Strong: both player and opponent named (h2h match for the right fight)
        if opp and p in haystack and opp in haystack and opp != "field":
            score = 0.97
        elif p in haystack:
            score = 0.85
        else:
            score = difflib.SequenceMatcher(None, p, question or title).ratio()
        # Hard reject: season-long futures / "become champion" / "fight next" markets.
        # These are not comparable to a single-event h2h or single-tournament outright.
        season_noise = (
            "become uf", "become the uf", "become champion", "become the champion",
            "champion in 2026", "champion on dec", "calendar grand slam", "season",
            "fight next", "fight of the year", "tour championship",
            "fighter of the year", "comeback fighter", "knockout of",
            "win the 2026 men's us open", "win the 2026 men's french open",
            "win the 2026 us open", "win the 2026 french open",
            "win the 2026 australian open", "win the 2026 wimbledon",
            "wimbledon winner", "us open winner", "french open winner",
            "australian open winner", "atp finals", "year-end no",
        )
        if any(n in haystack for n in season_noise):
            continue
        if score > best_score:
            best_score = score
            best = (ev, mkt, score)
    if best and best[2] >= 0.7:
        return best
    return None


def flatten_markets(events: list[dict]) -> list[tuple[dict, dict]]:
    out = []
    for ev in events:
        markets = ev.get("markets") or []
        for mkt in markets:
            if mkt.get("closed") or mkt.get("archived"):
                continue
            out.append((ev, mkt))
    return out


def verify_picks(picks: list[dict], poly_markets: list[tuple[dict, dict]]) -> list[dict]:
    rows = []
    for pick in picks:
        decimal_odds = float(pick.get("best_odds") or 0)
        if decimal_odds <= 1.0:
            book_implied = None
        else:
            book_implied = 1.0 / decimal_odds  # raw, not devig'd (single-side)
        player = pick.get("outcome_name") or ""
        # Identify the opponent (whichever of away/home isn't the picked side)
        away = pick.get("away_team") or ""
        home = pick.get("home_team") or ""
        opponent = home if player.lower() == away.lower() else away
        match = best_match(player, opponent, poly_markets)
        poly_prob = None
        poly_source = None
        match_score = None
        if match:
            ev, mkt, score = match
            match_score = round(score, 3)
            poly_source = mkt.get("question") or ev.get("title")
            outcomes = parse_outcome_prices(mkt)
            best_oc = None
            # Prefer an outcome whose name explicitly contains the player name
            # (multi-outcome markets, e.g. "Alcaraz", "Sinner", "Field"). For
            # binary Yes/No markets neither outcome will mention the player —
            # the question text already does — so default to "Yes".
            for name, prob in outcomes:
                if player.lower() in name.lower() or (name.lower() in player.lower() and len(name) >= 3):
                    best_oc = (name, prob)
                    break
            if not best_oc and outcomes:
                yes = next((o for o in outcomes if o[0].lower() == "yes"), None)
                best_oc = yes or outcomes[0]
            if best_oc:
                poly_prob = best_oc[1]
        gap_pp = None
        if book_implied is not None and poly_prob is not None:
            gap_pp = round((poly_prob - book_implied) * 100, 2)
        rows.append({
            "sport": pick.get("sport"),
            "game_date": pick.get("game_date"),
            "matchup": f"{pick.get('away_team')} vs {pick.get('home_team')}",
            "pick": player,
            "american_odds": pick.get("american_odds"),
            "decimal_odds": decimal_odds,
            "book_implied_pct": round(book_implied * 100, 2) if book_implied else None,
            "manual_win_prob_pct": pick.get("win_probability"),
            "manual_ev_pct": pick.get("ev_pct"),
            "polymarket_implied_pct": round(poly_prob * 100, 2) if poly_prob is not None else None,
            "polymarket_market": poly_source,
            "match_score": match_score,
            "poly_minus_book_pp": gap_pp,
            "verdict": _verdict(book_implied, poly_prob, pick.get("win_probability")),
        })
    return rows


def _verdict(book_implied: float | None, poly_prob: float | None, manual_wp: float | None) -> str:
    if book_implied is None:
        return "no_odds"
    if poly_prob is None:
        return "no_polymarket_match"
    gap = (poly_prob - book_implied) * 100
    manual_gap = None
    if manual_wp is not None:
        manual_gap = (float(manual_wp) / 100.0 - book_implied) * 100
    # Confirm: Polymarket agrees with manual edge direction (both positive or both negative gap)
    if manual_gap is not None and ((manual_gap > 0) == (gap > 0)) and abs(gap) >= 2:
        return "polymarket_confirms_edge"
    if abs(gap) >= 5:
        return "polymarket_disagrees_strongly" if (manual_gap or 0) * gap < 0 else "polymarket_alone_signals_edge"
    if abs(gap) >= 2:
        return "soft_signal"
    return "polymarket_neutral"


def render_markdown(rows: list[dict], generated_at: str) -> str:
    out = []
    out.append(f"# Manual Sports Picks Verification — {generated_at}\n")
    out.append("Cross-checks the curated UFC/Tennis/Golf picks in `live-monitor/sports-betting.html` "
               "against Polymarket Gamma API last-trade prices.\n")
    out.append("**Verdicts:**\n")
    out.append("- `polymarket_confirms_edge` — Polymarket gap and manual gap both lean the same way ≥ 2pp.\n")
    out.append("- `polymarket_alone_signals_edge` — Polymarket gap ≥ 5pp but manual model didn't flag it (or no manual prob).\n")
    out.append("- `polymarket_disagrees_strongly` — Polymarket says the opposite of the manual call by ≥ 5pp.\n")
    out.append("- `soft_signal` — small gap (2–5pp).\n")
    out.append("- `polymarket_neutral` — gap < 2pp; no edge vs market.\n")
    out.append("- `no_polymarket_match` — no fuzzy match found on Polymarket.\n\n")

    by_sport: dict[str, list[dict]] = {}
    for r in rows:
        by_sport.setdefault(r["sport"] or "?", []).append(r)
    for sport, items in by_sport.items():
        out.append(f"## {sport}\n")
        out.append("| Date | Matchup | Pick | Odds | Book impl % | Manual WP % | Poly impl % | Poly−Book pp | Verdict | Poly market |")
        out.append("|---|---|---|---|---:|---:|---:|---:|---|---|")
        for r in items:
            out.append("| {date} | {matchup} | {pick} | {odds} | {book} | {wp} | {poly} | {gap} | {verdict} | {src} |".format(
                date=r["game_date"] or "",
                matchup=r["matchup"],
                pick=r["pick"],
                odds=r.get("american_odds") or r.get("decimal_odds") or "",
                book=r["book_implied_pct"] if r["book_implied_pct"] is not None else "—",
                wp=r["manual_win_prob_pct"] if r["manual_win_prob_pct"] is not None else "—",
                poly=r["polymarket_implied_pct"] if r["polymarket_implied_pct"] is not None else "—",
                gap=f"{r['poly_minus_book_pp']:+.1f}" if r["poly_minus_book_pp"] is not None else "—",
                verdict=r["verdict"],
                src=(r["polymarket_market"] or "")[:60],
            ))
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=str(REPO / "reports"))
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--html", default=str(HTML))
    args = ap.parse_args()

    html = Path(args.html).read_text(encoding="utf-8", errors="replace")
    all_picks: list[dict] = []
    for var_name, sport_key in [("ufcPicksData", "ufc_mma"), ("tennisPicksData", "tennis_atp"), ("golfPicksData", "golf_pga")]:
        picks = extract_picks_array(html, var_name)
        for p in picks:
            p.setdefault("sport", sport_key)
        all_picks.extend(picks)
        print(f"[parse] {var_name}: {len(picks)} picks", file=sys.stderr)

    if not all_picks:
        print("No picks parsed; aborting.", file=sys.stderr)
        return 1

    # Fetch one Polymarket bucket per unique sport tag, dedupe overlap.
    sport_to_markets: dict[str, list[tuple[dict, dict]]] = {}
    for sport_key, tag in POLY_TAGS.items():
        if tag in sport_to_markets:
            continue
        events = fetch_polymarket_events(tag)
        sport_to_markets[sport_key] = flatten_markets(events)
        print(f"[poly] {sport_key} ({tag}): {len(events)} events / {len(sport_to_markets[sport_key])} markets", file=sys.stderr)

    rows: list[dict] = []
    for pick in all_picks:
        sport_key = pick.get("sport") or "ufc_mma"
        markets = sport_to_markets.get(sport_key, [])
        rows.extend(verify_picks([pick], markets))

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md = render_markdown(rows, ts)
    if args.stdout:
        sys.stdout.write(md)
        return 0
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"MANUAL_SPORTS_PICKS_VERIFICATION_{ts}.md"
    json_path = out_dir / f"MANUAL_SPORTS_PICKS_VERIFICATION_{ts}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps({"generated_at": ts, "rows": rows}, indent=2), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
