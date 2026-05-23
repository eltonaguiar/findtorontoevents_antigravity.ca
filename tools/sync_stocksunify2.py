#!/usr/bin/env python3
"""Pull STOCKSUNIFY2 daily-stocks.json and emit the standard active-picks schema.

STOCKSUNIFY2 is the sibling repo `eltonaguiar/STOCKSUNIFY2` that runs
multiple equity algorithms (Volatility-Adjusted Momentum, Adversarial Trend,
Replicator, etc.) and writes a daily picks file to `data/daily-stocks.json`.

This script:
1. Fetches `data/daily-stocks.json` from STOCKSUNIFY2 main.
2. Normalizes each pick to our active-picks schema:
     symbol, direction, strategy, source, asset_class, entry_price,
     stop_loss, score, confidence, generated_at, pick_type, holding_horizon,
     timeframe, category.
3. Atomically writes `audit_dashboard/data/stocksunify2_active_picks.json`.

Wired by .github/workflows/stocksunify2-pull.yml (daily 13:05 UTC).
Registered in audit_trail/dashboard_generator.py JSON_PICK_SOURCES.

Rollback:
    Set env STOCKSUNIFY2_SYNC_DISABLED=1 in workflow to skip writes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "stocksunify2_active_picks.json"
SOURCE_URL = "https://raw.githubusercontent.com/eltonaguiar/STOCKSUNIFY2/main/data/daily-stocks.json"

# Alias short-form algorithm slugs so leaderboard rows for STOCKSUNIFY2
# don't mix with the SAME algorithm name on a different exchange.
_ALG_PREFIX = "stocksunify2_"


def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _normalize(pick: dict) -> dict | None:
    symbol = (pick.get("symbol") or "").upper().strip()
    if not symbol:
        return None
    algorithm = pick.get("algorithm") or "unknown"
    rating = (pick.get("rating") or "").upper().strip()
    if rating in ("STRONG SELL", "SELL"):
        direction = "SELL"
    else:
        direction = "BUY"
    score = float(pick.get("score") or 0)
    entry_price = float(pick.get("entryPrice") or pick.get("price") or 0)
    sim_entry = float(pick.get("simulatedEntryPrice") or 0)
    stop_loss = float(pick.get("stopLoss") or 0)
    picked_at = pick.get("pickedAt") or pick.get("lastUpdated")

    return {
        "symbol": symbol,
        "direction": direction,
        "strategy": _ALG_PREFIX + _slugify(algorithm),
        "source": "stocksunify2",
        "source_system": "stocksunify2",
        "asset_class": "EQUITY",
        "category": "stock",
        "pick_type": "long_term_value",
        "holding_horizon": "long",
        "timeframe": pick.get("timeframe") or "1m",
        "entry_price": entry_price,
        "simulated_entry_price": sim_entry or entry_price,
        "stop_loss": stop_loss,
        "score": score,
        "confidence": min(score / 100.0, 1.0) if score else 0.0,
        "rating": rating,
        "risk": pick.get("risk"),
        "pick_hash": pick.get("pickHash"),
        "indicators": pick.get("indicators") or {},
        "all_algorithms": pick.get("allAlgorithms") or [algorithm],
        "generated_at": picked_at or datetime.now(timezone.utc).isoformat(),
    }


def _fetch() -> dict:
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "stocksunify2-sync"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.loads(fh.read().decode("utf-8"))


def main() -> int:
    if os.environ.get("STOCKSUNIFY2_SYNC_DISABLED", "0") == "1":
        print("[stocksunify2_sync] disabled via STOCKSUNIFY2_SYNC_DISABLED=1")
        return 0
    try:
        raw = _fetch()
    except Exception as exc:
        print(f"[stocksunify2_sync] fetch failed: {exc}", file=sys.stderr)
        return 1
    stocks = raw.get("stocks") or raw.get("picks") or []
    picks = [p for p in (_normalize(s) for s in stocks) if p]
    out = {
        "scanner": "stocksunify2",
        "source_repo": "eltonaguiar/STOCKSUNIFY2",
        "generated_at": raw.get("lastUpdated") or datetime.now(timezone.utc).isoformat(),
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "active_picks": picks,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2), encoding="utf-8")
    tmp.replace(OUT_PATH)
    print(f"[stocksunify2_sync] wrote {len(picks)} picks to {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
