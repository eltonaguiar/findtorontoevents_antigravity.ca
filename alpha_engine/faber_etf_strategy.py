"""Faber 10-month tactical MA (ETF) — top-1 academic consensus strategy.

Logic:
  if Price > SMA(Price, 10-months) then LONG else CASH.
  Monthly resolution; check at month-end or daily with monthly data.

Symbols (Academic Benchmark):
  SPY (US Equity), QQQ (Nasdaq), IWM (Small Cap), EEM (Emerging), GLD (Gold), TLT (Long Bonds).

Refs:
  - Mebane Faber (2007) "A Quantitative Approach to Tactical Asset Allocation"
  - reports/peer_claude-ORIGINAL_HUNT_FINAL_SYNTHESIS_2026-05-31.md

Wiring:
  - Part of the Tier-2 fresh build wave.
  - Frequency: Daily check (uses monthly bars).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

SYMBOLS = ["SPY", "QQQ", "IWM", "EEM", "GLD", "TLT"]
LOOKBACK_MONTHS = 10

def fetch_monthly_data(symbol: str) -> Optional[list[float]]:
    """Fetch monthly close prices for the last 18 months via yfinance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="18mo", interval="1mo")
        if df.empty:
            return None
        return df["Close"].tolist()
    except Exception as e:
        logger.error(f"Error fetching monthly data for {symbol}: {e}")
        return None

def compute_faber_signal(prices: list[float]) -> str:
    """Returns 'LONG' if current price > 10mo SMA, else 'CASH'."""
    if len(prices) < LOOKBACK_MONTHS:
        return "CASH"
    
    current_price = prices[-1]
    sma = np.mean(prices[-LOOKBACK_MONTHS:])
    
    if current_price > sma:
        return "LONG"
    return "CASH"

def generate_faber_picks() -> list[dict[str, Any]]:
    """Generate Faber 10mo MA picks for the benchmark ETF universe."""
    picks = []
    now = datetime.now(timezone.utc)
    
    for symbol in SYMBOLS:
        prices = fetch_monthly_data(symbol)
        if not prices:
            continue
            
        signal = compute_faber_signal(prices)
        if signal == "LONG":
            current_price = prices[-1]
            picks.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": "faber_10mo_ma",
                "asset_class": "ETF",
                "category": "etf",
                "entry_price": round(current_price, 4),
                "confidence": 0.75,
                "generated_at": now.isoformat(),
                "reason": f"Price ({current_price:.2f}) above {LOOKBACK_MONTHS}mo SMA ({np.mean(prices[-LOOKBACK_MONTHS:]):.2f})",
                "timeframe": "1mo",
                "source": "alpha_engine",
                "source_system": "faber_10mo_ma"
            })
            
    return picks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    picks = generate_faber_picks()
    import json
    print(json.dumps(picks, indent=2))
