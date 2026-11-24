#!/usr/bin/env python3
"""
pm_macro_expansion.py — Kalshi + Polymarket macro contract emitter
==================================================================
Emits high-probability, forward-only, OUTCOME-RESOLVABLE binary-contract
picks for macro/financial prediction markets:

  Kalshi series : KXFEDDECISION, KXGDP, KXCPI, KXDJIA, KXNASDAQ100
  Polymarket    : Fed cut/hike, unemployment, GDP, S&P 500, Treasury yields

Why a separate emitter (vs. pm_macro_overlay.py)
------------------------------------------------
pm_macro_overlay converts PM probabilities into *spot-derived* FOREX/ETF
trades (EURUSD, TLT ...). A binary contract ("Will X happen?") has no spot
price and no meaningful TP/SL — it settles at 1.0 / 0.0. The audit stack
already knows how to settle those (audit_trail/pm_contract_resolver.py), so
this emitter writes CONTRACT picks directly:

    asset_class = "PREDICTION_MARKET"
    market_id, platform, contract_side ("YES"/"NO")
    entry_price = implied probability (0..1)  -> cost of the contract
    resolution_date                          -> when the market settles

They route through pm_contract_resolver (payout 1.0/0.0), never price TP/SL.

All picks are shadow / forward-test only (no sizing). Outputs:
  prediction_market_agents/data/pm_macro_expansion_signals.json   (envelope)
  alpha_engine/data/pm_macro_expansion_picks.json                 (flat list)

Read-only w.r.t. the network except the two public PM APIs. Stdlib only.
"""
from __future__ import annotations

import json
import logging
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
PM_DATA_DIR = ROOT / "prediction_market_agents" / "data"
AE_DATA_DIR = ROOT / "alpha_engine" / "data"
OUTPUT_ENVELOPE = PM_DATA_DIR / "pm_macro_expansion_signals.json"
OUTPUT_MIRROR = AE_DATA_DIR / "pm_macro_expansion_picks.json"

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLYMARKET_SEARCH = "https://gamma-api.polymarket.com/public-search"
TIMEOUT = 20

SOURCE_SYSTEM = "pm_macro_expansion"
STRATEGY = "pm_macro_expansion"

# Only surface genuinely high-probability contracts.
MIN_PROB = 0.65
# Ignore markets whose resolution is further out than this (keep the book tight).
MAX_DAYS_OUT = 400
# Kalshi series -> (human label, asset tag)
KALSHI_SERIES = {
    "KXFEDDECISION": ("Fed FOMC decision", "RATES"),
    "KXGDP": ("US GDP growth", "MACRO"),
    "KXCPI": ("US CPI inflation", "MACRO"),
    "KXDJIA": ("Dow Jones level", "EQUITY"),
    "KXNASDAQ100": ("Nasdaq-100 level", "EQUITY"),
}
# Polymarket /public-search queries -> (human label, asset tag)
POLY_QUERIES = {
    "fed+rate+cut": ("Fed rate cut", "RATES"),
    "fed+rate+hike": ("Fed rate hike", "RATES"),
    "unemployment": ("Unemployment rate", "MACRO"),
    "gdp": ("GDP growth", "MACRO"),
    "s+p+500": ("S&P 500 level", "EQUITY"),
    "treasury+yield": ("Treasury yield", "RATES"),
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

logger = logging.getLogger("pm_macro_expansion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [pm_macro_exp] %(message)s")

def _get(url: str, timeout: int = TIMEOUT) -> Optional[Any]:
    """Fetch JSON from a public endpoint; None on any failure (never raises)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except Exception as exc:  # noqa: BLE001
        logger.warning("GET %s failed: %s", url, exc)
        return None


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse an ISO-ish timestamp to an aware UTC datetime, else None."""
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _kalshi_prob(market: dict) -> Optional[float]:
    """Implied YES probability from Kalshi's string-dollar fields (0..1)."""
    for field in ("last_price_dollars", "yes_bid_dollars", "last_price", "yes_bid"):
        raw = market.get(field)
        if raw in (None, "", 0):
            continue
        try:
            prob = float(raw)
        except (TypeError, ValueError):
            continue
        if prob > 1:  # legacy cent-integer fields
            prob /= 100.0
        if 0.0 < prob < 1.0:
            return prob
    return None


def _poly_prob(market: dict) -> Optional[float]:
    """Implied YES probability from a Polymarket market's outcomePrices."""
    prices = market.get("outcomePrices")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except (ValueError, TypeError):
            return None
    if not isinstance(prices, list) or not prices:
        return None
    try:
        prob = float(prices[0])
    except (TypeError, ValueError):
        return None
    if 0.0 < prob < 1.0:
        return prob
    return None


def _within_window(resolution: Optional[datetime], now: datetime) -> bool:
    if resolution is None:
        return False
    days = (resolution - now).total_seconds() / 86400.0
    return 0.0 < days <= MAX_DAYS_OUT


def _build_contract_pick(
    *,
    platform: str,
    market_id: str,
    market_title: str,
    prob: float,
    resolution: Optional[datetime],
    asset_tag: str,
    symbol: str,
    now: datetime,
) -> dict:
    """Build one standardized, outcome-resolvable binary-contract pick."""
    res_iso = resolution.strftime("%Y-%m-%dT%H:%M:%SZ") if resolution else None
    return {
        "id": f"pm_macro_{platform}_{market_id}_{now.strftime('%Y%m%d%H%M')}",
        "strategy": STRATEGY,
        "source_system": SOURCE_SYSTEM,
        "symbol": symbol,
        "category": "prediction_market",
        "asset_class": "PREDICTION_MARKET",
        "asset_tag": asset_tag,
        "signal_type": "BUY",
        "direction": "LONG",          # LONG == buying the YES contract
        "contract_side": "YES",
        "market_id": str(market_id),
        "platform": platform,
        "market_title": market_title[:180],
        "entry_price": round(prob, 4),  # implied probability == contract cost
        "confidence": round(prob, 4),
        "resolution_date": res_iso,
        "signal_time_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ingest_time_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verification_state": "forward_test_only",
        "bias_controls": ["resolve_by_market_outcome", "no_spot_tp_sl"],
        "forward_test_only": True,
        "sizing_allowed": False,
        "shadow": True,
        "status": "OPEN",
        "reason": (
            f"PM macro contract: {platform} '{market_title[:100]}' YES at "
            f"{prob:.1%} implied, resolves {res_iso or 'n/a'}. "
            f"Settles 1.0/0.0 on market outcome (no spot TP/SL)."
        ),
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_date": now.strftime("%Y-%m-%d"),
    }

def fetch_kalshi_series_picks(now: datetime) -> list[dict]:
    """One high-probability YES contract per nearest upcoming event, per series."""
    picks: list[dict] = []
    for series, (label, asset_tag) in KALSHI_SERIES.items():
        data = _get(
            f"{KALSHI_API}/markets?"
            + urllib.parse.urlencode({"series_ticker": series, "limit": 100,
                                      "status": "open"})
        )
        markets = [m for m in (data or {}).get("markets", [])
                   if isinstance(m, dict) and m.get("status") in ("active", "open")]
        if not markets:
            logger.info("Kalshi %s: no open markets", series)
            continue

        # Group by event, keep events whose close_time is still in the future.
        events: dict[str, list[dict]] = {}
        for m in markets:
            events.setdefault(m.get("event_ticker") or series, []).append(m)

        def _close(ms: list[dict]) -> Optional[datetime]:
            for m in ms:
                dt = _parse_dt(m.get("close_time") or m.get("expiration_time"))
                if dt:
                    return dt
            return None

        upcoming = {ev: ms for ev, ms in events.items()
                    if _within_window(_close(ms), now)}
        if not upcoming:
            logger.info("Kalshi %s: no future-dated events", series)
            continue
        ev = min(upcoming, key=lambda e: _close(upcoming[e]))

        # Emit the single most-likely leg of the nearest event.
        best: Optional[tuple[dict, float]] = None
        for m in upcoming[ev]:
            prob = _kalshi_prob(m)
            if prob is None or prob < MIN_PROB:
                continue
            if best is None or prob > best[1]:
                best = (m, prob)
        if best is None:
            logger.info("Kalshi %s/%s: no leg >= %.0f%%", series, ev, MIN_PROB * 100)
            continue

        market, prob = best
        title = (market.get("title") or market.get("yes_sub_title")
                 or market.get("no_sub_title") or label)
        picks.append(_build_contract_pick(
            platform="kalshi",
            market_id=market.get("ticker") or ev,
            market_title=f"{label}: {title}",
            prob=prob,
            resolution=_close(upcoming[ev]),
            asset_tag=asset_tag,
            symbol=ev,
            now=now,
        ))
        logger.info("Kalshi %s -> %s %.1f%%", ev, title[:50], prob * 100)
    return picks

def fetch_polymarket_picks(now: datetime) -> list[dict]:
    """One high-probability YES contract per query, from the nearest open market."""
    picks: list[dict] = []
    for query, (label, asset_tag) in POLY_QUERIES.items():
        data = _get(
            f"{POLYMARKET_SEARCH}?"
            + urllib.parse.urlencode({"q": query, "limit_per_type": 10})
        )
        best: Optional[tuple[dict, float, datetime]] = None
        for ev in (data or {}).get("events") or []:
            if ev.get("closed"):
                continue
            for m in ev.get("markets") or []:
                if m.get("closed"):
                    continue
                prob = _poly_prob(m)
                if prob is None or prob < MIN_PROB:
                    continue
                res = _parse_dt(m.get("endDate") or m.get("endDateIso") or ev.get("endDate"))
                if not _within_window(res, now):
                    continue
                # Prefer the soonest-resolving eligible market.
                if best is None or res < best[2]:
                    best = (m, prob, res)
        if best is None:
            logger.info("Polymarket %s: no market >= %.0f%% in window", label, MIN_PROB * 100)
            continue
        market, prob, res = best
        title = market.get("question") or market.get("title") or label
        picks.append(_build_contract_pick(
            platform="polymarket",
            market_id=market.get("id") or market.get("conditionId") or market.get("slug") or title,
            market_title=f"{label}: {title}",
            prob=prob,
            resolution=res,
            asset_tag=asset_tag,
            symbol=(market.get("slug") or query).upper()[:40],
            now=now,
        ))
        logger.info("Polymarket %s -> %s %.1f%%", label, str(title)[:50], prob * 100)
    return picks

def generate_picks() -> list[dict]:
    """Collect + de-duplicate Kalshi and Polymarket macro contract picks."""
    now = datetime.now(timezone.utc)
    picks = fetch_kalshi_series_picks(now) + fetch_polymarket_picks(now)

    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for p in picks:
        key = (p["platform"], p["market_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    deduped.sort(key=lambda p: p["confidence"], reverse=True)
    return deduped


def run() -> None:
    """Generate picks and persist both the envelope and the flat mirror."""
    picks = generate_picks()
    now = datetime.now(timezone.utc)
    envelope = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": SOURCE_SYSTEM,
        "status": "ok" if picks else "empty",
        "pick_count": len(picks),
        "picks": picks,
    }
    PM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ENVELOPE.write_text(json.dumps(envelope, indent=2, default=str))
    AE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MIRROR.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Wrote %d picks -> %s (+ mirror %s)",
                len(picks), OUTPUT_ENVELOPE.name, OUTPUT_MIRROR.name)

    for p in picks:
        print(f"  {p['platform']:10s} {p['asset_tag']:7s} "
              f"{p['confidence']:.1%}  {p['market_title'][:70]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
    sys.exit(0)
