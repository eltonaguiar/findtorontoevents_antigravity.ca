"""Ingest settled Kalshi/Polymarket markets into `data/pm_market_outcomes.json`.

The resolver (`audit_trail/pm_contract_resolver.py`) can only settle a binary
contract once it knows the market outcome. Nothing produced that feed, so the
contract branch had no outcomes to read. This module is the producer:

  * Polymarket Gamma API — `GET /markets?closed=true`, winner read from
    `outcomes` + `outcomePrices` (a settled contract prices at 1.0 / 0.0).
  * Kalshi Trade API — `GET /markets?status=settled`, winner read from `result`.
  * Existing local file is merged, never overwritten with fewer outcomes.

Output contract consumed by `load_market_outcomes`:
    {"generated_at": "...", "markets": [
        {"market_id": "...", "ticker": "...", "outcome": "YES"|"NO",
         "end_date": "...", "source": "polymarket"|"kalshi"}, ...]}

Usage:
    python -m audit_trail.pm_outcome_ingest              # live fetch + merge
    python -m audit_trail.pm_outcome_ingest --local-only # merge local files only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "pm_market_outcomes.json"

POLYMARKET_URL = "https://gamma-api.polymarket.com/markets"
KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"

_REQUEST_TIMEOUT = 20
_SETTLED_PRICE = 0.99


def _json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, params: Optional[Dict[str, str]] = None) -> Any:
    """Minimal GET helper (no retries — callers fail open)."""
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    request = urllib.request.Request(
        url + query, headers={"User-Agent": "audit-pm-outcome-ingest/1.0"}
    )
    with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


# ── Polymarket ─────────────────────────────────────────────────────────────
def parse_polymarket(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn settled Gamma market objects into outcome records."""
    out: List[Dict[str, Any]] = []
    for market in records or []:
        if not isinstance(market, dict):
            continue
        market_id = market.get("id") or market.get("conditionId")
        if not market_id:
            continue
        outcomes = [str(o).strip().upper() for o in _json_list(market.get("outcomes"))]
        prices = [_float(p) for p in _json_list(market.get("outcomePrices"))]

        winner: Optional[str] = None
        if outcomes and len(outcomes) == len(prices):
            best = max(range(len(prices)), key=lambda i: prices[i])
            if prices[best] >= _SETTLED_PRICE:
                winner = outcomes[best]
        if winner is None:
            explicit = market.get("winner") or market.get("resolvedOutcome")
            if isinstance(explicit, str) and explicit.strip():
                winner = explicit.strip().upper()
        if winner not in {"YES", "NO"}:
            continue

        out.append(
            {
                "market_id": str(market_id),
                "ticker": str(market_id),
                "outcome": winner,
                "end_date": market.get("endDate") or market.get("end_date") or "",
                "source": "polymarket",
            }
        )
    return out


def fetch_polymarket_settled(limit: int = 500) -> List[Dict[str, Any]]:
    payload = fetch_json(
        POLYMARKET_URL,
        {"closed": "true", "limit": str(limit), "order": "volumeNum", "ascending": "false"},
    )
    records = payload if isinstance(payload, list) else payload.get("markets") or []
    return parse_polymarket(records)


# ── Kalshi ─────────────────────────────────────────────────────────────────
def parse_kalshi(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for market in records or []:
        if not isinstance(market, dict):
            continue
        ticker = market.get("ticker") or market.get("market_ticker")
        result = str(market.get("result") or "").strip().upper()
        if not ticker or result not in {"YES", "NO"}:
            continue
        out.append(
            {
                "market_id": str(ticker),
                "ticker": str(ticker),
                "outcome": result,
                "end_date": market.get("close_time") or market.get("expiration_time") or "",
                "source": "kalshi",
            }
        )
    return out


def fetch_kalshi_settled(limit: int = 1000) -> List[Dict[str, Any]]:
    payload = fetch_json(KALSHI_URL, {"status": "settled", "limit": str(limit)})
    records = payload.get("markets") if isinstance(payload, dict) else payload
    return parse_kalshi(records or [])


# ── write / merge ──────────────────────────────────────────────────────────
def _load_existing(out_path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    markets = payload.get("markets") if isinstance(payload, dict) else payload
    return [m for m in (markets or []) if isinstance(m, dict)]


def _dedupe(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        key = str(rec.get("market_id") or rec.get("ticker") or "").strip()
        if key:
            merged[key] = rec
    return list(merged.values())


def write_atomic(out_path: Path, records: List[Dict[str, Any]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": _utc_now(), "markets": records}
    fd, tmp = tempfile.mkstemp(dir=str(out_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1)
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def ingest(
    out_path: Optional[Path] = None,
    *,
    polymarket_fetcher: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    kalshi_fetcher: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    local_only: bool = False,
) -> Dict[str, Any]:
    """Fetch settled markets, merge with the existing file, write atomically."""
    out_path = Path(out_path) if out_path else DEFAULT_OUT
    existing = _load_existing(out_path)
    errors: List[str] = []
    fetched: List[Dict[str, Any]] = []

    if not local_only:
        for name, fetcher in (
            ("polymarket", polymarket_fetcher or fetch_polymarket_settled),
            ("kalshi", kalshi_fetcher or fetch_kalshi_settled),
        ):
            try:
                fetched.extend(fetcher() or [])
            except Exception as exc:  # fail open: the dashboard must still build
                errors.append("%s: %s" % (name, exc))

    merged = _dedupe(existing + fetched)
    write_atomic(out_path, merged)
    return {
        "out": str(out_path),
        "existing": len(existing),
        "fetched": len(fetched),
        "total": len(merged),
        "errors": errors,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args(argv)
    result = ingest(Path(args.out), local_only=args.local_only)
    print(
        "[pm-outcome-ingest] existing=%d fetched=%d total=%d -> %s"
        % (result["existing"], result["fetched"], result["total"], result["out"])
    )
    for err in result["errors"]:
        print("[pm-outcome-ingest] fetch failed (non-fatal): %s" % err, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
