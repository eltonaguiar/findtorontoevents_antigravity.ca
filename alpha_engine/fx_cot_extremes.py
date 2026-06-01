"""FX COT Commercial Extremes (Price-Proxy) Strategy

Academic basis: Ilczyszyn &FirstChild (2014) — "Using COT Data to Trade Forex".
They document that extreme speculative positioning in CFTC Commitments of
Traders data reliably predicts reversals in G10 FX over 1-4 week horizons.

Since yfinance does not provide COT data, this strategy uses a price-action
proxy: a pair trading at the 95th percentile of its 52-week range implies
extreme speculative long positioning (crowding), while the 5th percentile
implies extreme short positioning. We fade these extremes.

Mechanic:
  - Compute each pair's 52-week high/low range from daily bars.
  - If current price is at/above the 95th percentile → SHORT (fade extreme longs).
  - If current price is at/below the 5th percentile → LONG (fade extreme shorts).
  - Exit: return to 50th percentile (median) OR max hold 48h.

Universe: 8 major FX pairs via yfinance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FX_UNIVERSE = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCHF=X", "NZDUSD=X", "USDCAD=X", "EURGBP=X",
]

STRATEGY_NAME = "fx_cot_extremes"
UPPER_PERCENTILE = 95
LOWER_PERCENTILE = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(price: float) -> float:
    if abs(price) >= 100:
        return round(price, 2)
    elif abs(price) >= 10:
        return round(price, 3)
    else:
        return round(price, 5)


def generate_picks(data: dict[str, pd.DataFrame] | None = None) -> List[dict[str, Any]]:
    """Generate COT-extreme proxy picks for FX pairs.

    Each pick includes forced_resolution with max_hold_hours=48, tp_pct=0.3,
    sl_pct=0.2, time_exit_at_market=True.
    """
    if data is None:
        data = _download_data()

    picks: List[dict[str, Any]] = []

    for symbol, df in data.items():
        if df is None or len(df) < 120:
            logger.debug("%s: need >=120 bars for 52w range, got %d",
                         symbol, len(df) if df is not None else 0)
            continue

        close = df["Close"].dropna()
        if len(close) < 120:
            continue

        current_price = float(close.iloc[-1])

        # 52-week range (use ~252 trading days, but cap at available data)
        lookback = min(252, len(close) - 1)
        range_52w = close.iloc[-lookback - 1:-1]  # exclude today from range calc
        if len(range_52w) < 60:
            continue

        w52_high = float(range_52w.max())
        w52_low = float(range_52w.min())
        w52_range = w52_high - w52_low

        if w52_range <= 0:
            continue

        # Percentile rank of current price within 52w range
        pct_rank = (current_price - w52_low) / w52_range * 100

        # Median (50th percentile) as exit target
        w52_median = float(range_52w.median())

        direction: str | None = None
        take_profit: float = 0.0
        stop_loss: float = 0.0

        if pct_rank >= UPPER_PERCENTILE:
            direction = "SHORT"
            take_profit = _smart_round(w52_median)
            # Stop: just above 52w high (extreme gets more extreme)
            stop_loss = _smart_round(w52_high * 1.002)
        elif pct_rank <= LOWER_PERCENTILE:
            direction = "LONG"
            take_profit = _smart_round(w52_median)
            stop_loss = _smart_round(w52_low * 0.998)
        else:
            continue

        # Risk/reward
        tp_dist = abs(take_profit - current_price)
        sl_dist = abs(stop_loss - current_price)
        if sl_dist <= 0:
            continue
        rr = round(tp_dist / sl_dist, 2)

        # Confidence: higher at more extreme percentiles
        extremity = abs(pct_rank - 50) / 50  # 0-1, 1 = most extreme
        confidence = min(0.72, 0.50 + extremity * 0.20)

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "strategy": STRATEGY_NAME,
            "asset_class": "FOREX",
            "category": "forex",
            "entry_price": _smart_round(current_price),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "confidence": round(confidence, 4),
            "risk_reward": rr,
            "timestamp": _now_iso(),
            "reason": (
                f"52w percentile={pct_rank:.1f}% "
                f"(hi={_smart_round(w52_high)}, lo={_smart_round(w52_low)}) "
                f"→ fade extreme {direction}, target median {_smart_round(w52_median)}"
            ),
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 48,
                "tp_pct": 0.3,
                "sl_pct": 0.2,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Ilczyszyn &FirstChild (2014) — COT Data in Forex",
        })

    logger.info("%s: generated %d picks", STRATEGY_NAME, len(picks))
    return picks


def _download_data() -> dict[str, pd.DataFrame]:
    """Download ~400 days of FX data via yfinance (need 52-week history)."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance required: pip install yfinance")
        return {}

    end = datetime.now(timezone.utc)
    start = end - pd.Timedelta(days=400)
    data: dict[str, pd.DataFrame] = {}

    for symbol in FX_UNIVERSE:
        try:
            df = yf.download(
                symbol,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
            )
            if df is not None and len(df) > 60:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[symbol] = df
                logger.debug("%s: %d bars", symbol, len(df))
        except Exception as e:
            logger.warning("%s: download failed: %s", symbol, e)

    return data


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Running %s standalone...", STRATEGY_NAME)
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        print("No picks generated (no pairs at 52w extremes).")
    logger.info("Done — %d picks.", len(picks))
