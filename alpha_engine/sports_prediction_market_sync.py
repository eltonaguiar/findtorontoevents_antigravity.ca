#!/usr/bin/env python3
"""
sports_prediction_market_sync.py
================================
Fetches live sports prediction-market probabilities from Polymarket's
public Gamma API and writes a JSON signal file consumed by
live-monitor/api/sports_picks.php (sports_pm_load_signals).

No API key is required — Polymarket Gamma data is public-read.
The script is safe to run in CI (exits 0 on network failure).

Usage:
    python3 alpha_engine/sports_prediction_market_sync.py
    python3 alpha_engine/sports_prediction_market_sync.py --output backfill/sports_prediction_market_signals.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

POLYMARKET_GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
DEFAULT_OUTPUT_PATHS = [
    "backfill/sports_prediction_market_signals.json",
    "alpha_engine/data/sports_prediction_market_signals.json",
]

SPORTS_KEYWORDS = [
    "nba", "nhl", "nfl", "mlb", "ufc", "mma", "tennis", "soccer",
    "basketball", "hockey", "football", "baseball", "premier league",
    "champions league", "epl", "la liga", "bundesliga", "serie a",
]


def _http_get_json(url: str, timeout: int = 20) -> Optional[List[Dict[str, Any]]]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sports-pm-sync)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print(f"[pm-sync] HTTP error: {e}", file=sys.stderr)
        return None


def _is_sports_event(ev: Dict[str, Any]) -> bool:
    title = (ev.get("title") or "").lower()
    if any(kw in title for kw in SPORTS_KEYWORDS):
        return True
    for tag in ev.get("tags", []):
        label = (tag.get("label") or "").lower()
        slug = (tag.get("slug") or "").lower()
        if label in ("sports", "nba", "nhl", "nfl", "mlb", "soccer", "tennis", "ufc", "mma"):
            return True
        if slug in ("sports", "nba", "nhl", "nfl", "mlb", "soccer", "tennis", "ufc", "mma"):
            return True
    return False


def _extract_moneyline_market(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the 'cleanest' moneyline market from an event.

    We prefer markets whose question exactly matches the event title
    (e.g. 'Thunder vs. Suns') and whose outcomes are the two team names.
    We skip spread, total, and prop markets.
    """
    markets: List[Dict[str, Any]] = ev.get("markets", [])
    if not markets:
        return None

    title = ev.get("title", "")
    candidates = []
    for m in markets:
        q = m.get("question", "")
        outcomes = m.get("outcomes", [])
        if not outcomes or len(outcomes) < 2:
            continue
        # Skip obvious non-moneyline markets
        skip_tokens = ("spread", "total", "over/under", "o/u", "1h", "1st half",
                       "exact score", "most sixes", "toss", "first blood",
                       "by ko", "by tko", "by submission")
        q_lower = q.lower()
        if any(t in q_lower for t in skip_tokens):
            continue
        # Score by closeness to event title
        score = 0
        if q.strip() == title.strip():
            score += 10
        elif q.strip().lower() == title.strip().lower():
            score += 9
        # Prefer binary outcomes that look like team names (not Yes/No)
        if not all(o.lower() in ("yes", "no") for o in outcomes):
            score += 5
        # Prefer higher liquidity
        score += float(m.get("liquidity", 0)) / 1_000_000.0
        candidates.append((score, m))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _team_names_from_event(ev: Dict[str, Any]) -> tuple:
    """Try to extract home/away team names from event metadata."""
    teams = ev.get("teams", [])
    if teams and len(teams) >= 2:
        return str(teams[0].get("name", teams[0])), str(teams[1].get("name", teams[1]))
    title = ev.get("title", "")
    # Common separators: " vs ", " vs. ", " @ ", " at "
    for sep in (" vs ", " vs. ", " @ ", " at "):
        if sep in title:
            parts = title.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return "", ""


def _build_signal(ev: Dict[str, Any], market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a signal dict matching the format expected by sports_picks.php."""
    ltp = market.get("lastTradePrice")
    if ltp is None:
        return None
    ltp = float(ltp)
    if not (0.01 <= ltp <= 0.99):
        return None

    outcomes = market.get("outcomes", [])
    if not outcomes:
        return None

    home, away = _team_names_from_event(ev)
    # For binary team markets, lastTradePrice corresponds to outcomes[0]
    favoured = outcomes[0] if outcomes else ""
    # Build a descriptive question string for PHP fuzzy matching
    if home and away:
        question = f"Will {favoured} beat {away if favoured.lower() == home.lower() else home}?"
    else:
        question = market.get("question", ev.get("title", ""))

    volume = ev.get("volume") or market.get("volume") or 0
    if isinstance(volume, str):
        try:
            volume = float(volume)
        except ValueError:
            volume = 0.0

    return {
        "question": question,
        "confidence": round(ltp, 4),
        "volume_usd": round(float(volume), 2),
        "source": "polymarket",
        "event_title": ev.get("title", ""),
        "home_team": home,
        "away_team": away,
        "favoured_outcome": favoured,
        "market_question": market.get("question", ""),
        "outcomes": outcomes,
        "last_trade_price": ltp,
        "best_bid": market.get("bestBid"),
        "best_ask": market.get("bestAsk"),
        "spread": market.get("spread"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_polymarket_sports_signals(limit: int = 500) -> List[Dict[str, Any]]:
    """Fetch sports-tagged events from Polymarket and convert to signals."""
    url = (
        f"{POLYMARKET_GAMMA_EVENTS}?active=true&closed=false"
        f"&limit={limit}&offset=0&order=liquidity&ascending=false"
    )
    events = _http_get_json(url)
    if not events:
        return []

    signals: List[Dict[str, Any]] = []
    for ev in events:
        if not _is_sports_event(ev):
            continue
        market = _extract_moneyline_market(ev)
        if not market:
            continue
        sig = _build_signal(ev, market)
        if sig:
            signals.append(sig)

    return signals


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Polymarket sports signals to JSON")
    parser.add_argument("--output", nargs="+", default=None,
                        help="One or more output JSON paths (default: auto-detected)")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--min-confidence", type=float, default=0.05,
                        help="Minimum confidence (lastTradePrice) to include")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    out_paths = args.output or DEFAULT_OUTPUT_PATHS

    print(f"[pm-sync] Fetching up to {args.limit} Polymarket events...")
    signals = fetch_polymarket_sports_signals(limit=args.limit)
    # Filter out very low-confidence signals (often resolved or stale)
    signals = [s for s in signals if args.min_confidence <= s["confidence"] <= (1.0 - args.min_confidence)]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket_gamma_api",
        "signal_count": len(signals),
        "signals": signals,
    }

    if args.verbose:
        for s in signals[:10]:
            print(f"  {s['event_title'][:60]:<60} conf={s['confidence']:.3f} vol=${s['volume_usd']:,.0f}")

    for p in out_paths:
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"[pm-sync] Wrote {len(signals)} signals to {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
