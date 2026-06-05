#!/usr/bin/env python3
"""Crude-oil futures term-structure feature signal.

Rule:
  Contango     (front < back, spread > +5%)  → SHORT CL=F
  Backwardation (front > back, spread < -5%) → LONG  CL=F

We use CL=F as the front-month proxy and dynamically resolve the
~6-month-out NYMEX contract (e.g. CLZ26.NYM).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FRONT_TICKER = "CL=F"
SPREAD_PCT_THRESHOLD = 0.05  # 5%
# NYMEX WTI month codes
MONTH_CODES = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]


def _download_latest(ticker: str) -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _six_month_contract() -> str | None:
    """Return a yfinance ticker for the NYMEX crude contract ~6 months out."""
    now = datetime.now(timezone.utc)
    # Target ~6 months ahead
    target_month = now.month + 6
    target_year = now.year
    if target_month > 12:
        target_month -= 12
        target_year += 1
    code = MONTH_CODES[target_month - 1]
    short_year = str(target_year)[-2:]
    return f"CL{code}{short_year}.NYM"


def _try_back_contract() -> tuple[str, float] | None:
    """Try the 6-month contract and fall back to adjacent months if needed."""
    primary = _six_month_contract()
    if primary:
        price = _download_latest(primary)
        if price is not None:
            return primary, price
    # Fallback: try +/- 1 month
    now = datetime.now(timezone.utc)
    for delta in (-1, 1, -2, 2):
        m = now.month + 6 + delta
        y = now.year
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        code = MONTH_CODES[m - 1]
        short_year = str(y)[-2:]
        tick = f"CL{code}{short_year}.NYM"
        price = _download_latest(tick)
        if price is not None:
            return tick, price
    return None


def fetch_term_structure() -> dict[str, Any]:
    front_price = _download_latest(FRONT_TICKER)
    back = _try_back_contract()
    if front_price is None or back is None:
        return {"error": "Failed to fetch front or back month price"}
    back_ticker, back_price = back
    spread = (back_price - front_price) / front_price
    return {
        "front_ticker": FRONT_TICKER,
        "front_price": front_price,
        "back_ticker": back_ticker,
        "back_price": back_price,
        "spread_pct": spread,
    }


def emit_picks() -> list[dict[str, Any]]:
    ts = fetch_term_structure()
    if "error" in ts:
        return []
    spread = ts["spread_pct"]
    if abs(spread) < SPREAD_PCT_THRESHOLD:
        return []

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    if spread > 0:
        direction = "SHORT"
        thesis = (
            f"Crude contango {spread*100:.1f}% ({ts['front_ticker']} {ts['front_price']:.2f} "
            f"vs {ts['back_ticker']} {ts['back_price']:.2f}). "
            "Near-term supply surplus / storage incentive — fade crude."
        )
    else:
        direction = "LONG"
        thesis = (
            f"Crude backwardation {abs(spread)*100:.1f}% ({ts['front_ticker']} {ts['front_price']:.2f} "
            f"vs {ts['back_ticker']} {ts['back_price']:.2f}). "
            "Near-term scarcity / tightness — buy crude."
        )

    entry = ts["front_price"]
    tp_mult = 1.06 if direction == "LONG" else 0.94
    sl_mult = 0.96 if direction == "LONG" else 1.04

    return [{
        "id": f"feature_term_structure::CL=F::{date_str}",
        "symbol": "CL=F",
        "direction": direction,
        "entry_price": round(entry, 2),
        "take_profit": round(entry * tp_mult, 2),
        "stop_loss": round(entry * sl_mult, 2),
        "status": "OPEN",
        "confidence": round(min(0.80, 0.60 + abs(spread) * 2), 3),
        "reason": thesis,
        "category": "commodity",
        "asset_class": "COMMODITY",
        "feature_raw": ts,
    }]


if __name__ == "__main__":
    import pprint
    pprint.pprint(emit_picks())
