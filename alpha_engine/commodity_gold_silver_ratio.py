"""Gold/Silver Ratio Mean Reversion Strategy
=============================================
Academic citation: Erb & Harvey (FAJ 2006)
"The Tactical and Strategic Value of Commodity Futures"

Logic:
  The Gold/Silver ratio mean-reverts over time. When the ratio deviates
  significantly from its historical midpoint (~70), a pairs trade captures
  the convergence.

Entry:
  ratio > 80 (gold expensive vs silver) → LONG SI=F, SHORT GC=F
  ratio < 60 (gold cheap vs silver)     → LONG GC=F, SHORT SI=F

Exit:
  Ratio returns to 70 (midpoint)  OR  max hold 168h (7 days)

Universe: GC=F (gold), SI=F (silver)

DEFAULT-OFF. Set env COMMODITY_GOLD_SILVER_RATIO_ENABLED=1 to emit picks.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_gold_silver_ratio_reversion"
ACADEMIC_CITATION = "Erb-Harvey (FAJ 2006)"

RATIO_UPPER = 80.0
RATIO_LOWER = 60.0
RATIO_MIDPOINT = 70.0
FETCH_PERIOD = "6mo"
SMA_LOOKBACK = 60
TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 168


def _enabled() -> bool:
    return os.environ.get("COMMODITY_GOLD_SILVER_RATIO_ENABLED", "0") == "1"


def _fetch_pair_data() -> Optional[dict[str, Any]]:
    """Fetch Gold and Silver price data via yfinance."""
    try:
        import yfinance as yf
        gc = yf.download("GC=F", period=FETCH_PERIOD, interval="1d",
                         auto_adjust=True, progress=False)
        si = yf.download("SI=F", period=FETCH_PERIOD, interval="1d",
                         auto_adjust=True, progress=False)
        if gc is None or gc.empty or si is None or si.empty:
            return None
        for df in (gc, si):
            if hasattr(df.columns, "get_level_values"):
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception:
                    pass
        gc_close = gc["Close"].dropna().astype(float)
        si_close = si["Close"].dropna().astype(float)

        aligned = gc_close.index.intersection(si_close.index)
        if len(aligned) < SMA_LOOKBACK + 5:
            return None
        gc_close = gc_close.loc[aligned]
        si_close = si_close.loc[aligned]

        ratio = gc_close / si_close
        ratio_sma = ratio.rolling(SMA_LOOKBACK).mean()
        ratio_std = ratio.rolling(SMA_LOOKBACK).std()

        last_ratio = float(ratio.iloc[-1])
        last_sma = float(ratio_sma.iloc[-1])
        last_std = float(ratio_std.iloc[-1])
        last_gc = float(gc_close.iloc[-1])
        last_si = float(si_close.iloc[-1])

        if last_si <= 0 or last_std <= 0:
            return None

        return {
            "ratio": last_ratio,
            "ratio_sma": last_sma,
            "ratio_std": last_std,
            "gc_price": last_gc,
            "si_price": last_si,
        }
    except Exception as e:
        logger.warning("Pair data fetch failed: %s", e)
        return None


def generate_picks(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Generate Gold/Silver ratio mean-reversion picks."""
    if not _enabled():
        logger.info("commodity_gold_silver_ratio disabled (set COMMODITY_GOLD_SILVER_RATIO_ENABLED=1)")
        return []

    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()

    data = _fetch_pair_data()
    if data is None:
        logger.warning("No pair data — cannot compute ratio")
        return []

    ratio = data["ratio"]
    z_score = (ratio - data["ratio_sma"]) / data["ratio_std"] if data["ratio_std"] > 0 else 0.0
    picks: list[dict[str, Any]] = []

    if ratio > RATIO_UPPER:
        confidence = round(min(0.80, 0.55 + abs(z_score) * 0.05), 4)
        si_px = round(data["si_price"], 4)
        picks.append({
            "symbol": "SI=F",
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": si_px,
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Gold/Silver ratio at {ratio:.1f} (>{RATIO_UPPER}). "
                f"Gold expensive vs silver (z={z_score:.2f}). LONG silver, "
                f"SHORT gold — expect ratio to revert to {RATIO_MIDPOINT}."
            ),
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
                "pair_leg": "LONG",
                "ratio": round(ratio, 4),
                "ratio_sma_60d": round(data["ratio_sma"], 4),
                "ratio_z_score": round(z_score, 4),
                "gc_price": round(data["gc_price"], 4),
                "si_price": round(data["si_price"], 4),
                "exit_target": f"ratio_revert_to_{RATIO_MIDPOINT}",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })
        gc_px = round(data["gc_price"], 4)
        picks.append({
            "symbol": "GC=F",
            "direction": "SHORT",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": gc_px,
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Gold/Silver ratio at {ratio:.1f} (>{RATIO_UPPER}). "
                f"Gold expensive vs silver (z={z_score:.2f}). SHORT gold leg "
                f"of pairs trade — expect ratio to revert to {RATIO_MIDPOINT}."
            ),
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
                "pair_leg": "SHORT",
                "ratio": round(ratio, 4),
                "ratio_sma_60d": round(data["ratio_sma"], 4),
                "ratio_z_score": round(z_score, 4),
                "gc_price": round(data["gc_price"], 4),
                "si_price": round(data["si_price"], 4),
                "exit_target": f"ratio_revert_to_{RATIO_MIDPOINT}",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })

    elif ratio < RATIO_LOWER:
        confidence = round(min(0.80, 0.55 + abs(z_score) * 0.05), 4)
        gc_px = round(data["gc_price"], 4)
        si_px = round(data["si_price"], 4)
        picks.append({
            "symbol": "GC=F",
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": gc_px,
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Gold/Silver ratio at {ratio:.1f} (<{RATIO_LOWER}). "
                f"Gold cheap vs silver (z={z_score:.2f}). LONG gold, "
                f"SHORT silver — expect ratio to revert to {RATIO_MIDPOINT}."
            ),
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
                "pair_leg": "LONG",
                "ratio": round(ratio, 4),
                "ratio_sma_60d": round(data["ratio_sma"], 4),
                "ratio_z_score": round(z_score, 4),
                "gc_price": round(data["gc_price"], 4),
                "si_price": round(data["si_price"], 4),
                "exit_target": f"ratio_revert_to_{RATIO_MIDPOINT}",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })
        picks.append({
            "symbol": "SI=F",
            "direction": "SHORT",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": si_px,
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Gold/Silver ratio at {ratio:.1f} (<{RATIO_LOWER}). "
                f"Gold cheap vs silver (z={z_score:.2f}). SHORT silver leg "
                f"of pairs trade — expect ratio to revert to {RATIO_MIDPOINT}."
            ),
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
                "pair_leg": "SHORT",
                "ratio": round(ratio, 4),
                "ratio_sma_60d": round(data["ratio_sma"], 4),
                "ratio_z_score": round(z_score, 4),
                "gc_price": round(data["gc_price"], 4),
                "si_price": round(data["si_price"], 4),
                "exit_target": f"ratio_revert_to_{RATIO_MIDPOINT}",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })
    else:
        logger.info("Gold/Silver ratio at %.1f — within neutral zone [%d, %d], no signal",
                     ratio, RATIO_LOWER, RATIO_UPPER)

    logger.info("Gold/Silver Ratio: ratio=%.1f, %d picks generated", ratio, len(picks))
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Running Gold/Silver Ratio strategy (standalone)...")
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        logger.info("No picks generated (disabled or ratio in neutral zone)")
        print("[]")
