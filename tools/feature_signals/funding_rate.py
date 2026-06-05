#!/usr/bin/env python3
"""Funding-rate mean-reversion feature signal.

Rule:
  lastFundingRate > +0.1% per 8h  → SHORT  (overleveraged longs)
  lastFundingRate < -0.1% per 8h  → LONG   (overleveraged shorts)

Fetches Binance USD-M premiumIndex (no API key).
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

BINANCE_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex"
THRESHOLD = 0.001  # 0.1%
TOP_N = 5


def _http_get_json(url: str, timeout: int = 20) -> Any:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "feature-signals/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def fetch_funding_rates() -> list[dict[str, Any]]:
    data = _http_get_json(BINANCE_PREMIUM_INDEX)
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        try:
            rate = float(row.get("lastFundingRate", 0))
            if abs(rate) >= THRESHOLD:
                out.append({
                    "symbol": str(row.get("symbol", "")),
                    "mark_price": float(row.get("markPrice", 0)),
                    "index_price": float(row.get("indexPrice", 0)),
                    "last_funding_rate": rate,
                })
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: abs(x["last_funding_rate"]), reverse=True)
    return out


def emit_picks(max_picks: int = TOP_N) -> list[dict[str, Any]]:
    raw = fetch_funding_rates()
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    for r in raw[:max_picks]:
        sym = r["symbol"]
        rate = r["last_funding_rate"]
        entry = r["mark_price"]
        if entry <= 0:
            continue
        direction = "SHORT" if rate > 0 else "LONG"
        # Crypto perp targets / stops
        tp_mult = 1.03 if direction == "LONG" else 0.97
        sl_mult = 0.98 if direction == "LONG" else 1.02
        picks.append({
            "id": f"feature_funding_mr::{sym}::{date_str}",
            "symbol": sym,
            "direction": direction,
            "entry_price": round(entry, 8),
            "take_profit": round(entry * tp_mult, 8),
            "stop_loss": round(entry * sl_mult, 8),
            "status": "OPEN",
            "confidence": round(min(0.85, 0.60 + abs(rate) * 50), 3),
            "reason": (
                f"Funding mean-reversion: {sym} 8h funding rate "
                f"{rate*100:+.3f}% (>0.1%) → {direction}. "
                "Extreme funding implies overleveraged crowd; fade it."
            ),
            "category": "crypto",
            "asset_class": "CRYPTO",
            "feature_raw": {"lastFundingRate": rate, "markPrice": entry},
        })
    return picks


if __name__ == "__main__":
    import pprint
    pprint.pprint(emit_picks())
