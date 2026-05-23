#!/usr/bin/env python3
"""
Commodity Seasonal Planting/Harvest Strategy
============================================
Top-1 candidate from edge research synthesis:
  - Refs: reports/edge_research_synthesis_2026_05_12.md
  - Refs: reports/asset_class_research_COMMODITY_2026_05_12_0438Z.md
          reports/asset_class_research_COMMODITY_2026_05_12_0442Z.md (Grok)

Thesis:
  Grain futures exhibit reliable seasonal price pressure driven by USDA
  crop progress reports:
    - 2 weeks PRE-PLANTING peak  -> LONG (depressed pre-plant price)
    - 2 weeks PRE-HARVEST peak   -> SHORT (oversupply pressure)
  Exit: 30 days after entry OR reverse signal.

Symbols: ZC=F Corn, ZW=F Wheat, ZS=F Soy, CT=F Cotton.

Expected (research): PF 2.2, COMMODITY already PF 3.77 above T2 — lock the lead.

DEFAULT-OFF. Set env COMMODITY_SEASONAL_ENABLED=1 to emit picks. Soak first.
Read-only data ingest; no live trading wired here.

Per-crop allowlist (post-backtest tightening):
  Ref: reports/backtest_commodity_seasonal_2026_05_12_0542Z.md (5y backtest)
    ZW Wheat:    PASS PF 1.76
    CT Cotton:   PASS PF 1.59
    ZS Soybeans: WARN PF 1.06
    ZC Corn:     FAIL PF 0.78
  Env COMMODITY_SEASONAL_CROPS (comma-separated crop keys) gates which
  crops emit picks. Default "WHEAT,COTTON" (PASS only). "ALL" enables all
  four. E.g. "WHEAT" enables only wheat.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

LOG = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_seasonal_planting_harvest"
ASSET_CLASS = "COMMODITY"

# Futures symbol map (Yahoo continuous-front-month codes)
CROP_TO_SYMBOL: dict[str, str] = {
    "CORN": "ZC=F",
    "WHEAT": "ZW=F",
    "SOYBEANS": "ZS=F",
    "COTTON": "CT=F",
}

# Historical peak weeks (ISO week-of-year) for US crops.
# Sources: USDA NASS Crop Progress historical aggregates.
#   planting_peak: week when % planted hits ~50% nationally
#   harvest_peak:  week when % harvested hits ~50% nationally
PEAK_WEEKS: dict[str, dict[str, int]] = {
    "CORN":     {"planting_peak": 19, "harvest_peak": 41},  # mid-May / mid-Oct
    "SOYBEANS": {"planting_peak": 22, "harvest_peak": 41},  # late-May / mid-Oct
    "WHEAT":    {"planting_peak": 17, "harvest_peak": 27},  # late-Apr / early-Jul (winter wheat harvest)
    "COTTON":   {"planting_peak": 20, "harvest_peak": 43},  # mid-May / late-Oct
}

# Risk knobs
ATR_TP_MULT = 1.2
ATR_SL_MULT = 1.0
HOLD_DAYS = 30
CONF_FLOOR = 0.55
CONF_CEIL = 0.75
PRE_PEAK_WINDOW_WEEKS = 2  # "in 2 weeks before peak"


def _enabled() -> bool:
    return os.environ.get("COMMODITY_SEASONAL_ENABLED", "0") == "1"


def _get_enabled_crops() -> set[str]:
    """Per-crop allowlist from env COMMODITY_SEASONAL_CROPS.

    Default: {"WHEAT", "COTTON"} (only PASS crops per
    reports/backtest_commodity_seasonal_2026_05_12_0542Z.md).
    "ALL": every key in CROP_TO_SYMBOL.
    Otherwise: comma-separated crop keys (case-insensitive), filtered to
    those present in CROP_TO_SYMBOL.
    """
    raw = os.environ.get("COMMODITY_SEASONAL_CROPS", "WHEAT,COTTON").strip()
    if not raw:
        return {"WHEAT", "COTTON"}
    if raw.upper() == "ALL":
        return set(CROP_TO_SYMBOL.keys())
    parts = {p.strip().upper() for p in raw.split(",") if p.strip()}
    return {c for c in parts if c in CROP_TO_SYMBOL}


def _iso_week(dt: datetime) -> int:
    return dt.isocalendar().week


def detect_window(crop: str, now: datetime | None = None) -> str | None:
    """Return 'LONG' if in pre-planting window, 'SHORT' if pre-harvest, else None."""
    crop = crop.upper()
    if crop not in PEAK_WEEKS:
        return None
    now = now or datetime.now(timezone.utc)
    wk = _iso_week(now)
    peaks = PEAK_WEEKS[crop]
    plant_lo = peaks["planting_peak"] - PRE_PEAK_WINDOW_WEEKS
    plant_hi = peaks["planting_peak"]
    harv_lo = peaks["harvest_peak"] - PRE_PEAK_WINDOW_WEEKS
    harv_hi = peaks["harvest_peak"]
    if plant_lo <= wk < plant_hi:
        return "LONG"
    if harv_lo <= wk < harv_hi:
        return "SHORT"
    return None


def _fetch_price_atr(symbol: str) -> tuple[float, float] | None:
    """Return (last_close, atr14). Graceful on missing yfinance."""
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        LOG.warning("yfinance unavailable; cannot price %s", symbol)
        return None
    try:
        df = yf.download(symbol, period="3mo", interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "get_level_values"):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                pass
        df = df.dropna(subset=["Close"])
        if df.empty:
            return None
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        close = df["Close"].astype(float)
        prev_close = close.shift(1)
        tr = (high - low).combine((high - prev_close).abs(), max).combine(
            (low - prev_close).abs(), max
        )
        atr14 = float(tr.rolling(14).mean().iloc[-1])
        last_close = float(close.iloc[-1])
        if not (atr14 > 0) or not (last_close > 0):
            return None
        return last_close, atr14
    except Exception as e:  # noqa: BLE001
        LOG.warning("price fetch failed %s: %s", symbol, e)
        return None


def _confidence_for(crop: str, direction: str, now: datetime) -> float:
    """Calibrated 0.55-0.75 based on closeness to peak (closer = higher)."""
    peaks = PEAK_WEEKS[crop]
    peak = peaks["planting_peak"] if direction == "LONG" else peaks["harvest_peak"]
    wk = _iso_week(now)
    dist = max(0, peak - wk)  # 0..PRE_PEAK_WINDOW_WEEKS-1
    if PRE_PEAK_WINDOW_WEEKS <= 1:
        frac = 1.0
    else:
        frac = 1.0 - (dist / float(PRE_PEAK_WINDOW_WEEKS))
    frac = max(0.0, min(1.0, frac))
    return round(CONF_FLOOR + frac * (CONF_CEIL - CONF_FLOOR), 4)


def build_pick(crop: str, direction: str, price: float, atr: float,
               now: datetime) -> dict[str, Any]:
    symbol = CROP_TO_SYMBOL[crop]
    if direction == "LONG":
        take_profit = round(price + ATR_TP_MULT * atr, 4)
        stop_loss = round(price - ATR_SL_MULT * atr, 4)
    else:
        take_profit = round(price - ATR_TP_MULT * atr, 4)
        stop_loss = round(price + ATR_SL_MULT * atr, 4)
    return {
        "strategy": STRATEGY_NAME,
        "asset_class": ASSET_CLASS,
        "symbol": symbol,
        "crop": crop,
        "direction": direction,
        "entry_price": round(price, 4),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": _confidence_for(crop, direction, now),
        "hold_days": HOLD_DAYS,
        "atr14": round(atr, 4),
        "generated_utc": now.isoformat(),
        "source": "usda_seasonal",
    }


def generate_picks(now: datetime | None = None) -> list[dict[str, Any]]:
    """Return list of pick dicts. DEFAULT-OFF: empty unless env flag set."""
    if not _enabled():
        LOG.info("commodity_seasonal disabled (set COMMODITY_SEASONAL_ENABLED=1)")
        return []
    now = now or datetime.now(timezone.utc)
    enabled_crops = _get_enabled_crops()
    picks: list[dict[str, Any]] = []
    for crop in CROP_TO_SYMBOL:
        if crop not in enabled_crops:
            continue
        direction = detect_window(crop, now)
        if direction is None:
            continue
        symbol = CROP_TO_SYMBOL[crop]
        priced = _fetch_price_atr(symbol)
        if priced is None:
            LOG.warning("skip %s (%s): no price/atr", crop, symbol)
            continue
        price, atr = priced
        picks.append(build_pick(crop, direction, price, atr, now))
    return picks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = generate_picks()
    import json as _json
    print(_json.dumps(out, indent=2))
