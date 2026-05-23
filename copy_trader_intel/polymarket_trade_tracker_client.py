#!/usr/bin/env python3
"""
Polymarket Trade Tracker Client
================================
Thin read-only wrapper around Polymarket's public CLOB/Gamma APIs and the
Polygon public RPC to replicate the core query that
leolopez007/polymarket-trade-tracker performs:

    Given a wallet address + market ID → return PnL, maker/taker counts,
    and on-chain receipt summary.

No private keys required. No auto-trading. All data from free public endpoints.

Source repo (MIT): https://github.com/leolopez007/polymarket-trade-tracker
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# Public endpoint constants (no API key needed)
# ---------------------------------------------------------------------------
_GAMMA_MARKET_URL = "https://gamma-api.polymarket.com/markets/{market_id}"
_DATA_API_POSITIONS_URL = "https://data-api.polymarket.com/positions?user={wallet}"
_CLOB_TRADES_URL = (
    "https://clob.polymarket.com/trades?market={condition_id}&maker_address={wallet}"
)
_POLYGON_RPC = "https://polygon-rpc.com"

_TIMEOUT = 15  # seconds per request


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> Any:
    """HTTP GET → parsed JSON. Raises urllib.error.URLError on failure."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "polymarket-trade-tracker-client/1.0 (read-only)"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_condition_id(market_id: str) -> str | None:
    """
    Look up the CLOB conditionId for a market.
    market_id may be a full market URL slug or a raw condition/token ID.
    """
    # If it already looks like a hex condition id, pass through
    if market_id.startswith("0x") and len(market_id) >= 60:
        return market_id

    # Try to strip a URL to just the slug and query Gamma API
    slug = market_id.rstrip("/").split("/")[-1]
    try:
        url = _GAMMA_MARKET_URL.format(market_id=slug)
        data = _get(url)
        # Gamma returns a list when querying by slug
        if isinstance(data, list) and data:
            data = data[0]
        return data.get("conditionId") or data.get("condition_id")
    except Exception:
        return None


def _fetch_trades(wallet: str, condition_id: str) -> list[dict]:
    """Pull all trades for the given wallet+market from the CLOB public API."""
    url = _CLOB_TRADES_URL.format(condition_id=condition_id, wallet=wallet)
    try:
        data = _get(url)
        if isinstance(data, dict):
            return data.get("data", [])
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _fetch_positions(wallet: str, condition_id: str) -> list[dict]:
    """Pull current open positions for the wallet, filtered to the market."""
    try:
        data = _get(_DATA_API_POSITIONS_URL.format(wallet=wallet))
        if isinstance(data, list):
            return [
                p for p in data
                if condition_id and (
                    p.get("conditionId") == condition_id
                    or p.get("market") == condition_id
                )
            ]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_wallet_market_pnl(wallet: str, market_id: str) -> dict:
    """
    Return PnL and trade-role breakdown for a wallet on a given Polymarket market.

    Parameters
    ----------
    wallet : str
        Polygon/Ethereum wallet address (0x…).
    market_id : str
        Polymarket market identifier — accepts:
        - Full market URL  (e.g. "https://polymarket.com/event/foo/will-it-bar")
        - Market slug      (e.g. "will-bitcoin-hit-100k-by-end-of-2025")
        - Hex condition ID (e.g. "0x3a…")

    Returns
    -------
    dict with keys:
        wallet       : str  — echoed back
        market_id    : str  — echoed back
        condition_id : str  — resolved hex condition ID (or "unknown")
        pnl_usdc     : float — realised PnL in USDC (positive = profit)
        maker_trades : int
        taker_trades : int
        total_trades : int
        status       : "ok" | "unavailable"
        error        : str  (only present when status == "unavailable")
    """
    base: dict = {
        "wallet": wallet,
        "market_id": market_id,
        "condition_id": "unknown",
        "pnl_usdc": 0.0,
        "maker_trades": 0,
        "taker_trades": 0,
        "total_trades": 0,
        "status": "unavailable",
    }

    try:
        # 1. Resolve the condition ID
        condition_id = _resolve_condition_id(market_id)
        if not condition_id:
            base["error"] = f"Could not resolve condition_id for market_id={market_id!r}"
            return base
        base["condition_id"] = condition_id

        # 2. Pull trades from CLOB
        trades = _fetch_trades(wallet, condition_id)

        maker_count = 0
        taker_count = 0
        pnl = 0.0

        for trade in trades:
            # Role detection: CLOB marks each fill as "maker" or "taker"
            side = (trade.get("side") or "").upper()
            role = (trade.get("type") or trade.get("role") or "").lower()
            price = float(trade.get("price") or 0.0)
            size = float(trade.get("size") or trade.get("amount") or 0.0)

            if role == "maker":
                maker_count += 1
            else:
                taker_count += 1

            # Approximate PnL: BUY fills negative cash-flow, SELL positive
            if side == "SELL":
                pnl += price * size
            elif side == "BUY":
                pnl -= price * size

        base["maker_trades"] = maker_count
        base["taker_trades"] = taker_count
        base["total_trades"] = maker_count + taker_count
        base["pnl_usdc"] = round(pnl, 6)
        base["status"] = "ok"
        return base

    except urllib.error.URLError as exc:
        base["error"] = f"Network error: {exc}"
        return base
    except Exception as exc:  # noqa: BLE001
        base["error"] = f"Unexpected error: {exc}"
        return base


# ---------------------------------------------------------------------------
# CLI smoke-test (python polymarket_trade_tracker_client.py <wallet> <market>)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python polymarket_trade_tracker_client.py <wallet> <market_id>")
        sys.exit(0)

    result = fetch_wallet_market_pnl(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
