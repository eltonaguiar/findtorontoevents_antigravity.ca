#!/usr/bin/env python3
"""
Sports Prediction Market Bridge
==============================
Fetches high-liquidity sports markets from Polymarket and exports a compact
signal file that can be consumed by live-monitor/api/sports_picks.php.

This module is additive and does not change the strict crypto-only
alpha_engine/polymarket_signals.py pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
REQUEST_TIMEOUT = 20
ACTIVE_MARKET_LIMIT = 500

MIN_VOLUME_USD = 5000.0
MIN_CONFIDENCE = 0.60

SPORT_KEYWORDS = (
    "nba", "nhl", "nfl", "mlb", "cfl", "mls", "ncaaf", "ncaab",
    "soccer", "premier league", "la liga", "champions league",
    "tennis", "atp", "wta", "golf", "ufc", "mma", "formula 1", "f1",
    "world cup", "super bowl", "stanley cup", "world series", "finals", "playoffs",
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATHS = (
    os.path.join(ROOT, "alpha_engine", "data", "sports_prediction_market_signals.json"),
    os.path.join(ROOT, "live-monitor", "backfill", "sports_prediction_market_signals.json"),
)


def _fetch_json(url: str, params: Dict[str, Any]) -> Any:
    query = urllib.parse.urlencode(params)
    full_url = url + "?" + query
    req = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "SportsPredictionMarketBridge/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_sports_question(question: str) -> bool:
    q = (question or "").lower()
    if not q:
        return False
    for token in SPORT_KEYWORDS:
        if token in q:
            return True
    return False


def _parse_prices(raw: Any) -> List[float]:
    if isinstance(raw, list):
        vals = raw
    elif isinstance(raw, str):
        try:
            vals = json.loads(raw)
        except Exception:
            vals = []
    else:
        vals = []
    out: List[float] = []
    for v in vals:
        try:
            out.append(float(v))
        except Exception:
            continue
    return out


def fetch_sports_signals() -> List[Dict[str, Any]]:
    payload = _fetch_json(
        f"{GAMMA_API_BASE}/markets",
        {
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
            "limit": str(ACTIVE_MARKET_LIMIT),
        },
    )
    if not isinstance(payload, list):
        return []

    signals: List[Dict[str, Any]] = []
    for m in payload:
        if not isinstance(m, dict):
            continue
        question = str(m.get("question") or "")
        if not _is_sports_question(question):
            continue

        try:
            volume = float(m.get("volumeNum", m.get("volume", 0)) or 0)
        except Exception:
            volume = 0.0
        if volume < MIN_VOLUME_USD:
            continue

        prices = _parse_prices(m.get("outcomePrices", []))
        if len(prices) < 2:
            continue

        p_yes = prices[0]
        p_no = prices[1]
        confidence = max(p_yes, p_no)
        if confidence < MIN_CONFIDENCE:
            continue

        signal = {
            "id": str(m.get("id") or ""),
            "source": "polymarket",
            "question": question,
            "confidence": round(confidence, 4),
            "direction": "YES" if p_yes >= p_no else "NO",
            "yes_probability": round(p_yes, 4),
            "no_probability": round(p_no, 4),
            "volume_usd": round(volume, 2),
            "end_date": m.get("endDate"),
        }
        signals.append(signal)

    signals.sort(key=lambda x: (x.get("confidence", 0), x.get("volume_usd", 0)), reverse=True)
    return signals


def save_signals(signals: List[Dict[str, Any]]) -> None:
    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "sports_prediction_market_bridge",
        "count": len(signals),
        "signals": signals,
    }

    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        LOG.info("Wrote %d signals -> %s", len(signals), path)


def main() -> None:
    try:
        signals = fetch_sports_signals()
        save_signals(signals)
        print(json.dumps({"ok": True, "count": len(signals)}))
    except Exception as exc:
        LOG.exception("sports prediction market bridge failed")
        print(json.dumps({"ok": False, "error": str(exc)}))


if __name__ == "__main__":
    main()
