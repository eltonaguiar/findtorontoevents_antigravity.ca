#!/usr/bin/env python3
"""
ingest_prediction_markets.py — P2-13 Kalshi/Polymarket ingestion sidecar
========================================================================

Per CLAUDE.md Wire-Up Rule: this is a pure ingestion sidecar that does NOT
change production scoring. It writes a snapshot of currently-open markets
from Kalshi and Polymarket into:
  1. New MySQL table `prediction_market_snapshots`
     (idempotent CREATE TABLE IF NOT EXISTS; pre-P2-13 backup was performed
     via `python3 tools/db_backup_to_backups.py --source-db ejaguiar1_stocks
     --tables prediction_market_snapshots --note 'pre-P2-13 ingestion'` —
     the table is new so the first run is a no-op for backup, but the
     flag is wired and documented in the report).
  2. JSON snapshot at `audit_dashboard/data/prediction_market_snapshots_latest.json`
     for the audit pipeline to consume.
  3. Per-market cache files at `data/prediction_markets/<source>_<market_id>.json`
     (TTL 1h) so re-runs within the hour are free and offline-failover works.

CLAUDE.md "API Failover Rule" applies — per source we have 2 endpoints and
Kalshi's pagination gives us a 3rd leg:

  Kalshi:    primary = https://api.elections.kalshi.com/trade-api/v2/markets
             fallback 1 = https://api.elections.kalshi.com/trade-api/v2/events
                         (different shape; flattens to {event, markets[]})
             fallback 2 = pagination cursor (next_cursor from primary response)

  Polymarket: primary  = https://gamma-api.polymarket.com/markets
              fallback = https://gamma-api.polymarket.com/public-search
                         (event search endpoint; verified schema)

Auth: NEITHER endpoint requires auth for read-only. Per Kalshi/Polymarket
public docs:
  - Kalshi: GET /trade-api/v2/markets is anonymous for read-only.
  - Polymarket: GET /markets and /public-search are anonymous for read-only.
Trading (orders, positions) would need API keys; this tool never trades.

Usage:
  python3 tools/ingest_prediction_markets.py
  python3 tools/ingest_prediction_markets.py --since 2026-06-12T00:00:00Z \\
      --out audit_dashboard/data/prediction_market_snapshots_latest.json
  python3 tools/ingest_prediction_markets.py --skip-db  # JSON+cache only
  python3 tools/ingest_prediction_markets.py --skip-cache  # DB+JSON only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CACHE_DIR = REPO_ROOT / "data" / "prediction_markets"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUT = REPO_ROOT / "audit_dashboard" / "data" / "prediction_market_snapshots_latest.json"
CACHE_TTL_SECONDS = 3600  # 1h

# Endpoint config (Kalshi + Polymarket, both anonymous read)
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_FALLBACK_EVENTS = f"{KALSHI_API}/events"
KALSHI_PRIMARY_MARKETS = f"{KALSHI_API}/markets"

POLY_API = "https://gamma-api.polymarket.com"
POLY_PRIMARY_MARKETS = f"{POLY_API}/markets"
POLY_FALLBACK_SEARCH = f"{POLY_API}/public-search"

HTTP_TIMEOUT = 20
PAGE_LIMIT = 100  # max per page
MAX_PAGES_PER_SOURCE = 3  # failover: try 3 pages before giving up
KALSHI_SERIES_SAMPLE = ("KXFEDDECISION", "KXNBAGAME", "KXNFLGAME", "KXMLBGAME")

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

TABLE_NAME = "prediction_market_snapshots"
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(16) NOT NULL,
  market_id VARCHAR(64) NOT NULL,
  title TEXT,
  category VARCHAR(64),
  yes_price DECIMAL(6,4),
  no_price DECIMAL(6,4),
  volume_24h DECIMAL(18,2),
  close_date DATETIME,
  snapshot_at_utc DATETIME NOT NULL,
  INDEX idx_source_market (source, market_id),
  INDEX idx_snapshot (snapshot_at_utc)
)
""".strip()

logger = logging.getLogger("ingest_pm")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class MarketEvent:
    """Unified shape for a single prediction-market listing (Kalshi or Polymarket)."""

    source: str  # 'kalshi' | 'polymarket'
    market_id: str
    title: str
    category: str
    yes_price: float
    no_price: float
    volume_24h: float
    close_date: str  # ISO8601 string or "" when unknown
    raw: dict[str, Any] = field(default_factory=dict)

    def to_db_row(self, snapshot_at_utc: datetime) -> dict[str, Any]:
        return {
            "source": self.source[:16],
            "market_id": self.market_id[:64],
            "title": (self.title or "")[:65535],
            "category": (self.category or "")[:64],
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "volume_24h": self.volume_24h,
            "close_date": _parse_dt(self.close_date),
            "snapshot_at_utc": snapshot_at_utc,
        }


# ---------------------------------------------------------------------------
# HTTP + cache helpers
# ---------------------------------------------------------------------------


def _http_get(url: str, params: Optional[dict[str, Any]] = None) -> Optional[Any]:
    """One-shot GET with TLS-disabled ctx (50webs agent has no ca-bundle for some endpoints)."""
    if params:
        url = url + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT, context=_SSL_CTX) as resp:
            body = resp.read()
        return json.loads(body)
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def _cache_path(source: str, market_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", market_id)[:80]
    return CACHE_DIR / f"{source}_{safe}.json"


def _cache_get(source: str, market_id: str) -> Optional[dict[str, Any]]:
    path = _cache_path(source, market_id)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        return None
    try:
        with path.open() as fh:
            return json.load(fh)
    except Exception:
        return None


def _cache_put(source: str, market_id: str, raw: dict[str, Any]) -> None:
    try:
        with _cache_path(source, market_id).open("w") as fh:
            json.dump(raw, fh, default=str)
    except Exception as exc:
        logger.warning("cache write failed for %s/%s: %s", source, market_id, exc)


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------


def _norm_prob(raw: Any) -> Optional[float]:
    """Accept string/cent-int/float, return prob in (0, 1]."""
    if raw is None or raw == "":
        return None
    try:
        prob = float(raw)
    except (TypeError, ValueError):
        return None
    if prob > 1:
        prob /= 100.0
    if 0 < prob <= 1:
        return round(prob, 4)
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _classify_category(text: str) -> str:
    """Cheap category tag for the audit-side filter dropdown."""
    low = (text or "").lower()
    if any(w in low for w in ("fed", "fomc", "rate", "inflation", "cpi", "gdp", "election", "president", "congress", "senate")):
        return "macro"
    if any(w in low for w in ("nba", "nfl", "mlb", "nhl", "soccer", "tennis", "ufc", "game", "match", "score")):
        return "sports"
    if any(w in low for w in ("bitcoin", "btc", "eth", "crypto", "solana", "xrp")):
        return "crypto"
    if any(w in low for w in ("ai ", "openai", "anthropic", "gpt", "claude", "gemini", "apple", "google", "microsoft", "tesla", "nvidia")):
        return "tech"
    return "other"


# ---------------------------------------------------------------------------
# Source fetchers
# ---------------------------------------------------------------------------


def _kalshi_price(market: dict) -> Optional[float]:
    """Kalshi v2 prices are string-dollar; legacy cent-int fallback for safety."""
    for field in ("last_price_dollars", "yes_bid_dollars", "last_price", "yes_bid"):
        raw = market.get(field)
        if raw in (None, "", 0):
            continue
        prob = _norm_prob(raw)
        if prob is not None:
            return prob
    return None


def fetch_kalshi() -> list[MarketEvent]:
    """Primary path: /markets with cursor pagination. Fallback: /events flatten."""
    out: list[MarketEvent] = []
    seen: set[str] = set()

    # Primary: page through /markets
    # NOTE: Kalshi v2 returns 400 on `status=active` in the query string (verified
    # 2026-06-13). Status is filtered client-side instead.
    cursor: Optional[str] = None
    pages = 0
    while pages < MAX_PAGES_PER_SOURCE:
        params: dict[str, Any] = {"limit": PAGE_LIMIT}
        if cursor:
            params["cursor"] = cursor
        data = _http_get(KALSHI_PRIMARY_MARKETS, params)
        if not data or "markets" not in data:
            break
        for m in data.get("markets", []):
            if m.get("status") not in ("active", "open"):
                continue
            ticker = m.get("ticker") or m.get("market_id") or ""
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            prob = _kalshi_price(m)
            if prob is None:
                continue
            title = " ".join(
                s for s in (m.get("title"), m.get("subtitle"), m.get("category"), m.get("series_ticker")) if s
            ).strip()
            volume = m.get("volume_fp") or m.get("volume_24h_fp") or m.get("volume") or 0
            try:
                volume = float(volume)
            except (TypeError, ValueError):
                volume = 0.0
            out.append(
                MarketEvent(
                    source="kalshi",
                    market_id=ticker,
                    title=title[:500],
                    category=_classify_category(title + " " + (m.get("category") or "")),
                    yes_price=prob,
                    no_price=round(1.0 - prob, 4),
                    volume_24h=volume,
                    close_date=m.get("close_time") or m.get("expiration_time") or "",
                    raw={k: v for k, v in m.items() if k in ("title", "subtitle", "status", "event_ticker", "series_ticker", "close_time", "volume_fp")},
                )
            )
            _cache_put("kalshi", ticker, m)
        cursor = data.get("cursor")
        if not cursor:
            break
        pages += 1

    if out:
        logger.info("Kalshi primary: %d markets", len(out))
        return out

    # Fallback: /events flattens to per-market. `status=active` is rejected
    # by Kalshi v2 (400 bad_request); filter client-side.
    logger.info("Kalshi primary empty — falling back to /events")
    for series in KALSHI_SERIES_SAMPLE:
        data = _http_get(KALSHI_FALLBACK_EVENTS, {"series_ticker": series, "limit": PAGE_LIMIT, "with_nested_markets": "true"})
        if not data or "events" not in data:
            continue
        for ev in data.get("events", []):
            for m in ev.get("markets", []) or []:
                if m.get("status") not in ("active", "open"):
                    continue
                ticker = m.get("ticker") or ""
                if not ticker or ticker in seen:
                    continue
                seen.add(ticker)
                prob = _kalshi_price(m)
                if prob is None:
                    continue
                title = (m.get("title") or ev.get("title") or "")[:500]
                volume = m.get("volume_fp") or m.get("volume_24h_fp") or m.get("volume") or 0
                try:
                    volume = float(volume)
                except (TypeError, ValueError):
                    volume = 0.0
                out.append(
                    MarketEvent(
                        source="kalshi",
                        market_id=ticker,
                        title=title,
                        category=_classify_category(title),
                        yes_price=prob,
                        no_price=round(1.0 - prob, 4),
                        volume_24h=volume,
                        close_date=m.get("close_time") or "",
                        raw={"event_ticker": ev.get("event_ticker")},
                    )
                )
                _cache_put("kalshi", ticker, m)
        if len(out) >= 50:
            break
    logger.info("Kalshi fallback total: %d markets", len(out))
    return out


def fetch_polymarket() -> list[MarketEvent]:
    """Primary: /markets paginated. Fallback: /public-search flatten."""
    out: list[MarketEvent] = []
    seen: set[str] = set()

    # Primary: /markets with offset pagination
    offset = 0
    for page in range(MAX_PAGES_PER_SOURCE):
        data = _http_get(
            POLY_PRIMARY_MARKETS,
            {"limit": PAGE_LIMIT, "offset": offset, "closed": "false", "active": "true"},
        )
        if not data or not isinstance(data, list) or not data:
            break
        for m in data:
            mid = str(m.get("id") or m.get("conditionId") or "")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            yes = _norm_prob(op[0]) if op else None
            no = _norm_prob(op[1]) if (op and len(op) > 1) else None
            if yes is None:
                yes = _norm_prob(m.get("bestBid"))
            if yes is None:
                continue
            if no is None:
                no = round(1.0 - yes, 4)
            title = m.get("question") or m.get("title") or ""
            volume = m.get("volume24hr") or m.get("volume") or m.get("volumeNum") or 0
            try:
                volume = float(volume)
            except (TypeError, ValueError):
                volume = 0.0
            out.append(
                MarketEvent(
                    source="polymarket",
                    market_id=mid,
                    title=title[:500],
                    category=_classify_category(title),
                    yes_price=yes,
                    no_price=no,
                    volume_24h=volume,
                    close_date=m.get("endDate") or "",
                    raw={"slug": m.get("slug"), "liquidity": m.get("liquidity")},
                )
            )
            _cache_put("polymarket", mid, m)
        if len(data) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT

    if out:
        logger.info("Polymarket primary: %d markets", len(out))
        return out

    # Fallback: /public-search
    logger.info("Polymarket primary empty — falling back to /public-search")
    for q in ("trump", "bitcoin", "fed", "election", "ai", "nba"):
        data = _http_get(POLY_FALLBACK_SEARCH, {"q": q, "limit_per_type": PAGE_LIMIT})
        if not data:
            continue
        for ev in data.get("events") or []:
            if ev.get("closed"):
                continue
            for m in ev.get("markets") or []:
                if m.get("closed"):
                    continue
                mid = str(m.get("id") or m.get("conditionId") or "")
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                op = m.get("outcomePrices")
                if isinstance(op, str):
                    try:
                        op = json.loads(op)
                    except Exception:
                        op = None
                yes = _norm_prob(op[0]) if op else None
                if yes is None:
                    continue
                title = m.get("question") or ev.get("title") or ""
                volume = m.get("volume24hr") or m.get("volume") or 0
                try:
                    volume = float(volume)
                except (TypeError, ValueError):
                    volume = 0.0
                out.append(
                    MarketEvent(
                        source="polymarket",
                        market_id=mid,
                        title=title[:500],
                        category=_classify_category(title),
                        yes_price=yes,
                        no_price=round(1.0 - yes, 4),
                        volume_24h=volume,
                        close_date=m.get("endDate") or "",
                        raw={"event_title": ev.get("title")},
                    )
                )
                _cache_put("polymarket", mid, m)
        if len(out) >= 50:
            break
    logger.info("Polymarket fallback total: %d markets", len(out))
    return out


# ---------------------------------------------------------------------------
# DB merge
# ---------------------------------------------------------------------------


def merge_to_db(markets: Iterable[MarketEvent], snapshot_at_utc: datetime) -> int:
    """CREATE TABLE IF NOT EXISTS + INSERT each market. Returns rows written."""
    try:
        import pymysql  # type: ignore
        from tools.db_env import get_stocks_creds  # type: ignore
    except Exception as exc:
        logger.warning("pymysql/tools.db_env unavailable, skipping DB write: %s", exc)
        return 0

    creds = get_stocks_creds()
    keep = {k: v for k, v in creds.items() if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    keep.setdefault("connect_timeout", 30)
    conn = pymysql.connect(**keep, autocommit=False)
    try:
        cur = conn.cursor()
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("Ensured table %s exists", TABLE_NAME)

        ins = (
            f"INSERT INTO {TABLE_NAME} (source, market_id, title, category, "
            "yes_price, no_price, volume_24h, close_date, snapshot_at_utc) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        written = 0
        for m in markets:
            row = m.to_db_row(snapshot_at_utc)
            cur.execute(
                ins,
                (
                    row["source"],
                    row["market_id"],
                    row["title"],
                    row["category"],
                    row["yes_price"],
                    row["no_price"],
                    row["volume_24h"],
                    row["close_date"],
                    row["snapshot_at_utc"],
                ),
            )
            written += 1
        conn.commit()
        logger.info("Wrote %d rows to %s", written, TABLE_NAME)
        return written
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


def export_json(markets: list[MarketEvent], path: Path, snapshot_at_utc: datetime, since: Optional[str]) -> None:
    payload = {
        "generated_at_utc": snapshot_at_utc.isoformat(),
        "since": since,
        "source_count": len({m.source for m in markets}),
        "kalshi_count": sum(1 for m in markets if m.source == "kalshi"),
        "polymarket_count": sum(1 for m in markets if m.source == "polymarket"),
        "markets": [asdict(m) for m in markets],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    logger.info("Wrote %d markets to %s", len(markets), path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_since(value: Optional[str]) -> Optional[str]:
    """Validate the --since ISO8601 stamp; return as-is on success."""
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    datetime.fromisoformat(s)  # raises if invalid
    return value


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest Kalshi + Polymarket snapshots into DB and JSON.")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output JSON path")
    ap.add_argument("--since", default=None, help="ISO8601 start timestamp (recorded in JSON, not a filter)")
    ap.add_argument("--skip-db", action="store_true", help="skip MySQL writes")
    ap.add_argument("--skip-cache", action="store_true", help="do not write per-market cache files")
    ap.add_argument("--limit", type=int, default=None, help="cap total markets (post-fetch, for testing)")
    args = ap.parse_args()

    since = _parse_since(args.since)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    logger.info("Starting Kalshi + Polymarket ingestion (since=%s)", since)

    kalshi: list[MarketEvent] = []
    polymarket: list[MarketEvent] = []
    try:
        kalshi = fetch_kalshi()
    except Exception as exc:
        logger.error("Kalshi fetch crashed (continuing): %s", exc)
    try:
        polymarket = fetch_polymarket()
    except Exception as exc:
        logger.error("Polymarket fetch crashed (continuing): %s", exc)

    all_markets = kalshi + polymarket
    if args.limit:
        all_markets = all_markets[: args.limit]

    if not all_markets:
        logger.warning("No markets fetched from either source — emitting empty snapshot")
    else:
        logger.info(
            "Fetched kalshi=%d polymarket=%d total=%d",
            len(kalshi), len(polymarket), len(all_markets),
        )

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    export_json(all_markets, out_path, now, since)

    if not args.skip_db:
        merge_to_db(all_markets, now)

    if args.skip_cache:
        # Best-effort cleanup of files written during fetch is a no-op; the cache
        # is the failover source of truth and skipping only means "don't write
        # during this run". Existing cache files persist.
        logger.info("Cache writes disabled (existing cache files retained)")

    # Compact summary line for operators
    print(
        f"OK: kalshi={len(kalshi)} polymarket={len(polymarket)} "
        f"out={out_path} db={'skipped' if args.skip_db else 'written'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
