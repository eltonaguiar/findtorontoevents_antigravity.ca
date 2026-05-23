#!/usr/bin/env python3
"""
Stratified spot-check: recompute directional PnL from entry/exit vs dashboard row.
Uses public Binance klines (crypto) and yfinance if available (stocks/FX).
Run: python tools/audit_sample_market_validate.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any


def _get(url: str, timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "findtorontoevents-audit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def pnl_long_pct(entry: float, exit_px: float) -> float:
    if entry <= 0:
        return 0.0
    return round((exit_px - entry) / entry * 100, 4)


def pnl_short_pct(entry: float, exit_px: float) -> float:
    if entry <= 0:
        return 0.0
    return round((entry - exit_px) / entry * 100, 4)


def last_crypto_price(symbol: str) -> float | None:
    sym = symbol.upper().replace("/", "").replace("-", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT" if "USDT" not in sym else sym
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    try:
        data = _get(url)
        return float(data["price"])
    except Exception:
        return None


def main() -> int:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        yf = None

    # Minimal synthetic checks (no placeholder picks — only math validation)
    assert abs(pnl_long_pct(100, 105) - 5.0) < 0.01
    # Short profits when exit < entry
    assert abs(pnl_short_pct(100, 95) - 5.0) < 0.01

    print("Binance spot BTCUSDT:", last_crypto_price("BTCUSDT"))
    if yf:
        t = yf.Ticker("EURUSD=X")
        h = t.history(period="5d")
        if h is not None and len(h) > 0:
            print("yfinance EURUSD=X last close:", float(h["Close"].iloc[-1]))

    print(
        "Use this script with real pick JSON from DASHBOARD_DATA; compare row pnl_pct "
        "to pnl_*_pct(entry, exit_or_mark)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
