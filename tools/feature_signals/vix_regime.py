#!/usr/bin/env python3
"""VIX regime feature signal.

Rule:
  VIX9D < VIX  → risk-on  → LONG SPY
  VIX9D > VIX  → risk-off → LONG TLT

Data: yfinance (^VIX, ^VIX9D, VXV)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SYMBOLS = {"VIX": "^VIX", "VIX9D": "^VIX9D", "VXV": "VXV"}
TRADE_MAP = {
    "risk_on": {"symbol": "SPY", "label": "S&P 500"},
    "risk_off": {"symbol": "TLT", "label": "20+ Year Treasuries"},
}


def _download_latest(ticker: str) -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def fetch_vix_data() -> dict[str, float | None]:
    return {k: _download_latest(v) for k, v in SYMBOLS.items()}


def emit_picks() -> list[dict[str, Any]]:
    data = fetch_vix_data()
    vix = data.get("VIX")
    vix9d = data.get("VIX9D")
    vxv = data.get("VXV")
    if vix is None or vix9d is None:
        return []

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    if vix9d < vix:
        regime = "risk_on"
        thesis = (
            f"VIX9D ({vix9d:.2f}) < VIX ({vix:.2f}) — short-term vol "
            "compressed vs spot; market pricing near-term calm. Risk-on."
        )
    elif vix9d > vix:
        regime = "risk_off"
        thesis = (
            f"VIX9D ({vix9d:.2f}) > VIX ({vix:.2f}) — short-term vol "
            "elevated; fear accelerating. Risk-off."
        )
    else:
        return []

    trade = TRADE_MAP[regime]
    sym = trade["symbol"]
    price = _download_latest(sym)
    if price is None:
        return []

    direction = "LONG"
    tp = round(price * 1.04, 2)
    sl = round(price * 0.975, 2)

    return [{
        "id": f"feature_vix_regime::{sym}::{date_str}",
        "symbol": sym,
        "direction": direction,
        "entry_price": round(price, 2),
        "take_profit": tp,
        "stop_loss": sl,
        "status": "OPEN",
        "confidence": 0.68,
        "reason": thesis,
        "category": "etf",
        "asset_class": "ETF",
        "feature_raw": {
            "VIX": vix,
            "VIX9D": vix9d,
            "VXV": vxv,
            "regime": regime,
        },
    }]


if __name__ == "__main__":
    import pprint
    pprint.pprint(emit_picks())
