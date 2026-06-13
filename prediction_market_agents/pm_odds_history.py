#!/usr/bin/env python3
"""
pm_odds_history.py — IDEA-H lead/lag prerequisite (DAILY_IDEAS 2026-05-24 build plan)
=====================================================================================
Captures ONE daily odds snapshot per macro prediction market (Kalshi + Polymarket)
into an append-only JSONL so pm_lead_lag_analyzer.py can compute odds-vs-underlying
cross-correlation once >=20 daily points exist per market.

Why this exists: pm_macro_overlay.py (Phase 1, 2026-06-06) fetches the single most
liquid Fed market per platform and discards everything after each run — nothing in
the PM stack persists an odds time series, so the lead/lag analysis specified in
DAILY_IDEAS IDEA-H ("for each PM event with >20 daily data points, compute
(PM_odds[t], underlying_return[t-3..t+3]) correlation") was impossible.

Output: prediction_market_agents/data/pm_odds_history.jsonl
  one row per (snapshot UTC date, platform, market_id); re-runs same day are no-ops.
  Already covered by alpha-engine-live.yml's `git add prediction_market_agents/data/`
  so history accrues across CI runs without new persistence plumbing.

OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule: read-only data capture, emits no picks,
changes no production behavior. Wired as a non-fatal step in alpha-engine-live.yml.
"""

from __future__ import annotations

import json
import logging
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "pm_odds_history.jsonl"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [pm_odds_history] %(message)s")

# NOTE on API schemas (verified live 2026-06-12; pm_macro_overlay.py predates these
# and is broken against them — see PR body):
#   Kalshi v2: market status is 'active' (not 'open'); prices are string-dollar
#     fields (last_price_dollars / yes_bid_dollars); volume is volume_fp.
#   Polymarket: /markets?search= IGNORES the search param; the working endpoint
#     is /public-search?q=... which returns events with nested markets.
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLYMARKET_SEARCH = "https://gamma-api.polymarket.com/public-search"
TIMEOUT = 20

KALSHI_SERIES = ["KXFED", "FOMC", "FEDRATE", "FED"]
POLYMARKET_QUERIES = ["fed+rate+cut", "fed+rate"]
MAX_MARKETS_PER_PLATFORM = 25

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _get(url: str, timeout: int = TIMEOUT) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def _classify_action(text: str) -> str:
    text = (text or "").lower()
    if any(w in text for w in ("cut", "lower", "decrease", "reduce")):
        return "cut"
    if any(w in text for w in ("hike", "raise", "increase")):
        return "hike"
    return "hold"


def _norm_prob(raw: Any) -> Optional[float]:
    try:
        prob = float(raw)
    except (TypeError, ValueError):
        return None
    if prob > 1:
        prob /= 100.0
    if prob <= 0 or prob > 1:
        return None
    return round(prob, 4)


def fetch_kalshi_rows(now: datetime) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for series in KALSHI_SERIES:
        data = _get(f"{KALSHI_API}/markets?series_ticker={series}&limit=20")
        if not data:
            continue
        for m in data.get("markets", []):
            if m.get("status") not in ("active", "open"):
                continue
            ticker = m.get("ticker") or ""
            if not ticker or ticker in seen:
                continue
            # Current API: string-dollar fields. Legacy fallback: cent ints
            # (_norm_prob divides >1 values by 100).
            prob = _norm_prob(m.get("last_price_dollars") or m.get("yes_bid_dollars")
                              or m.get("yes_bid") or m.get("last_price"))
            if prob is None:
                continue
            seen.add(ticker)
            title = (m.get("title") or "") + " " + (m.get("subtitle") or "")
            volume = m.get("volume_fp") or m.get("volume_24h_fp") or m.get("volume") or 0
            try:
                volume = float(volume)
            except (TypeError, ValueError):
                volume = 0.0
            rows.append({
                "date": now.strftime("%Y-%m-%d"),
                "ts": now.isoformat(),
                "platform": "kalshi",
                "market_id": ticker,
                "title": title.strip()[:200],
                "action": _classify_action(title),
                "prob": prob,
                "volume": volume,
            })
            if len(rows) >= MAX_MARKETS_PER_PLATFORM:
                return rows
    return rows


def fetch_polymarket_rows(now: datetime) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for query in POLYMARKET_QUERIES:
        data = _get(f"{POLYMARKET_SEARCH}?q={query}&limit_per_type=10")
        if not data:
            continue
        for ev in data.get("events") or []:
            if ev.get("closed"):
                continue
            for m in ev.get("markets") or []:
                if m.get("closed"):
                    continue
                mid = str(m.get("id") or m.get("conditionId") or "")
                title = m.get("question") or m.get("title") or ev.get("title") or ""
                if not mid or mid in seen:
                    continue
                low = title.lower()
                if not any(w in low for w in ("fed", "fomc", "federal reserve", "rate")):
                    continue
                outcome_prices = m.get("outcomePrices")
                if isinstance(outcome_prices, str):
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except Exception:
                        outcome_prices = None
                prob = None
                if outcome_prices:
                    prob = _norm_prob(outcome_prices[0])
                if prob is None:
                    prob = _norm_prob(m.get("bestBid"))
                if prob is None:
                    continue
                seen.add(mid)
                try:
                    volume = float(m.get("volume") or m.get("volumeNum") or 0)
                except (TypeError, ValueError):
                    volume = 0.0
                rows.append({
                    "date": now.strftime("%Y-%m-%d"),
                    "ts": now.isoformat(),
                    "platform": "polymarket",
                    "market_id": mid,
                    "title": title.strip()[:200],
                    "action": _classify_action(title),
                    "prob": prob,
                    "volume": volume,
                })
                if len(rows) >= MAX_MARKETS_PER_PLATFORM:
                    return rows
    return rows


def load_existing_keys(path: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    if not path.exists():
        return keys
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                keys.add((row.get("date", ""), row.get("platform", ""), str(row.get("market_id", ""))))
            except Exception:
                continue
    return keys


def run() -> int:
    now = datetime.now(timezone.utc)
    rows = fetch_kalshi_rows(now) + fetch_polymarket_rows(now)
    if not rows:
        logger.info("No macro PM markets fetched (APIs down or no open markets) — nothing appended")
        return 0

    existing = load_existing_keys(HISTORY_FILE)
    appended = 0
    with HISTORY_FILE.open("a") as fh:
        for row in rows:
            key = (row["date"], row["platform"], str(row["market_id"]))
            if key in existing:
                continue
            fh.write(json.dumps(row, default=str) + "\n")
            existing.add(key)
            appended += 1

    logger.info("Fetched %d markets, appended %d new daily snapshots to %s",
                len(rows), appended, HISTORY_FILE)
    return appended


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # sidecar must never break the calling workflow
        logger.error("pm_odds_history failed: %s", exc)
        sys.exit(0)
