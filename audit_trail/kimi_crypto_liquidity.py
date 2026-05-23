"""
Kimi Agent (High-Score Asset Picks) — live crypto liquidity enrichment.

Uses Binance USDT-M 24h ticker (quote volume in USDT, free API, no keys).
Feeds quality_gates score adjustments; does not invent volumes when API fails.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Mapping, MutableMapping, Tuple

logger = logging.getLogger(__name__)

BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"


def fetch_binance_24h_maps(timeout: float = 15.0) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return (symbol -> quote_volume_usd, symbol -> price_change_pct).

    Empty dicts on failure.
    """
    try:
        import urllib.request

        req = urllib.request.Request(
            BINANCE_24H_URL,
            headers={"User-Agent": "FindTorontoEvents-Audit/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.warning("kimi_liquidity: Binance 24h fetch failed: %s", exc)
        return {}, {}

    qv: Dict[str, float] = {}
    pc: Dict[str, float] = {}
    if not isinstance(raw, list):
        return {}, {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").upper().strip()
        if not sym.endswith("USDT"):
            continue
        try:
            qv[sym] = float(row.get("quoteVolume") or 0.0)
            pc[sym] = float(row.get("priceChangePercent") or 0.0)
        except (TypeError, ValueError):
            continue
    return qv, pc


def enrich_picks_with_binance_24h(
    picks: List[MutableMapping[str, Any]],
    quote_map: Mapping[str, float] | None = None,
    pct_map: Mapping[str, float] | None = None,
) -> int:
    """Attach quote_volume_24h and price_change_pct_24h to CRYPTO USDT picks.

    If maps are None, fetches once from Binance. Returns count enriched.
    """
    if quote_map is None or pct_map is None:
        quote_map, pct_map = fetch_binance_24h_maps()
    if not quote_map:
        return 0

    n = 0
    for pick in picks:
        if not isinstance(pick, MutableMapping):
            continue
        ac = str(pick.get("asset_class") or "CRYPTO").upper()
        if ac != "CRYPTO":
            continue
        sym = str(pick.get("symbol") or "").upper().strip()
        if not sym.endswith("USDT"):
            continue
        q = quote_map.get(sym)
        if q is not None and q > 0:
            pick["quote_volume_24h"] = round(q, 2)
            n += 1
        p = pct_map.get(sym)
        if p is not None:
            pick["price_change_pct_24h"] = round(p, 4)
    return n


def kimi_score_adjust_liquidity(quote_vol_usd: float) -> Tuple[int, str]:
    """Score delta from 24h USDT quote volume (Kimi tier thresholds, 2026-04-08).

    Returns (delta, penalty_label) for pick["_penalties"].
    """
    qv = float(quote_vol_usd)
    if qv < 3_000_000:
        return -28, "kimi_liquidity(<$3M):-28"
    if qv < 10_000_000:
        return -10, "kimi_liquidity_tier5($3-10M):-10"
    if qv < 30_000_000:
        return -5, "kimi_liquidity_tier4($10-30M):-5"
    if qv < 100_000_000:
        return 2, "kimi_liquidity_tier3:+2"
    if qv < 500_000_000:
        return 4, "kimi_liquidity_tier2:+4"
    return 6, "kimi_liquidity_tier1:+6"
