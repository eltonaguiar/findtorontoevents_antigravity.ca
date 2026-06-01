"""Commodity Inventory Report Fade Strategy
============================================
Academic citation: Anderson, Kellogg & Salant (AER 2018)
"The Welfare Effects of Nudges: A Case Study of Energy Use Social Comparisons"

Logic:
  After large price moves (>2σ of 20d volatility), fade the direction if volume
  is elevated (proxy for inventory report shock). Inventory reports cause
  sharp, temporary dislocations that revert within days.

Entry:
  |1d return| > 2 × 20d rolling std  AND  volume > 2x 20d avg volume
  → fade the move (if price dropped, go LONG; if price rose, go SHORT)

Exit:
  Return to 20d SMA  OR  max hold 168h (7 days)

Universe: GC=F, SI=F, CL=F, NG=F, HG=F, ZC=F

DEFAULT-OFF. Set env COMMODITY_INVENTORY_REPORT_ENABLED=1 to emit picks.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_inventory_report_fade"
ACADEMIC_CITATION = "Anderson-Kellogg-Salant (AER 2018)"

COMMODITY_UNIVERSE: dict[str, dict[str, str]] = {
    "GC=F": {"name": "Gold", "sector": "precious_metals"},
    "SI=F": {"name": "Silver", "sector": "precious_metals"},
    "CL=F": {"name": "WTI Crude Oil", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "sector": "energy"},
    "HG=F": {"name": "Copper", "sector": "industrial_metals"},
    "ZC=F": {"name": "Corn", "sector": "agriculture"},
}

FETCH_PERIOD = "3mo"
VOL_LOOKBACK = 20
VOL_THRESHOLD_SIGMA = 2.0
VOLUME_MULT_THRESHOLD = 2.0
TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 168


def _enabled() -> bool:
    return os.environ.get("COMMODITY_INVENTORY_REPORT_ENABLED", "0") == "1"


def _fetch_data(symbol: str) -> Optional[dict[str, Any]]:
    """Fetch OHLCV data for *symbol* via yfinance. Returns summary dict or None."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=FETCH_PERIOD, interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "get_level_values"):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                pass
        df = df.dropna(subset=["Close"])
        if len(df) < VOL_LOOKBACK + 5:
            return None

        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)

        last_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        daily_return = (last_close - prev_close) / prev_close

        rolling_std = float(close.pct_change().rolling(VOL_LOOKBACK).std().iloc[-1])
        avg_volume = float(volume.rolling(VOL_LOOKBACK).mean().iloc[-1])
        last_volume = float(volume.iloc[-1])
        sma_20 = float(close.rolling(VOL_LOOKBACK).mean().iloc[-1])

        if rolling_std <= 0 or avg_volume <= 0:
            return None

        return {
            "last_close": last_close,
            "prev_close": prev_close,
            "daily_return": daily_return,
            "rolling_std": rolling_std,
            "last_volume": last_volume,
            "avg_volume": avg_volume,
            "sma_20": sma_20,
        }
    except Exception as e:
        logger.warning("Data fetch failed for %s: %s", symbol, e)
        return None


def generate_picks(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Generate inventory report fade picks."""
    if not _enabled():
        logger.info("commodity_inventory_report disabled (set COMMODITY_INVENTORY_REPORT_ENABLED=1)")
        return []

    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    picks: list[dict[str, Any]] = []

    for symbol, meta in COMMODITY_UNIVERSE.items():
        data = _fetch_data(symbol)
        if data is None:
            logger.warning("Skipping %s — no data", symbol)
            continue

        abs_ret = abs(data["daily_return"])
        vol_threshold = VOL_THRESHOLD_SIGMA * data["rolling_std"]
        volume_ratio = data["last_volume"] / data["avg_volume"]

        if abs_ret < vol_threshold:
            logger.debug("%s: |ret|=%.4f < threshold=%.4f — no signal",
                         symbol, abs_ret, vol_threshold)
            continue

        if volume_ratio < VOLUME_MULT_THRESHOLD:
            logger.debug("%s: vol_ratio=%.2f < %.1f — volume not elevated",
                         symbol, volume_ratio, VOLUME_MULT_THRESHOLD)
            continue

        if data["daily_return"] < 0:
            direction = "LONG"
            reason = (
                f"Inventory Report Fade LONG: {meta['name']} dropped "
                f"{data['daily_return']*100:.2f}% (>2σ={vol_threshold*100:.2f}%) "
                f"on {volume_ratio:.1f}x avg volume. Fading the move — target "
                f"20d SMA {data['sma_20']:.2f}."
            )
        else:
            direction = "SHORT"
            reason = (
                f"Inventory Report Fade SHORT: {meta['name']} surged "
                f"{data['daily_return']*100:.2f}% (>2σ={vol_threshold*100:.2f}%) "
                f"on {volume_ratio:.1f}x avg volume. Fading the move — target "
                f"20d SMA {data['sma_20']:.2f}."
            )

        confidence = round(min(0.78, 0.55 + (abs_ret / vol_threshold - 1.0) * 0.1
                               + (volume_ratio / VOLUME_MULT_THRESHOLD - 1.0) * 0.05), 4)

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": reason,
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": ACADEMIC_CITATION,
            "extra": {
                "daily_return": round(data["daily_return"], 6),
                "rolling_std_20d": round(data["rolling_std"], 6),
                "vol_threshold_sigma": VOL_THRESHOLD_SIGMA,
                "volume_ratio": round(volume_ratio, 2),
                "sma_20": round(data["sma_20"], 4),
                "last_close": round(data["last_close"], 4),
                "exit_target": "20d_SMA_or_max_hold",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })

    logger.info("Inventory Report Fade: %d picks generated from %d symbols",
                len(picks), len(COMMODITY_UNIVERSE))
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Running Inventory Report Fade strategy (standalone)...")
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        logger.info("No picks generated (disabled or no signals)")
        print("[]")
