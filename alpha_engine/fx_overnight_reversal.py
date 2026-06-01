"""FX Overnight Reversal Strategy

Academic basis: Breedon & Ranaldo (Journal of Finance, 2013) — "Intraday Patterns
in the Returns and Bid-Ask Spreads of Foreign Exchange". They document a
systematic overnight reversal in G10 FX: currencies that appreciate strongly
during the local trading day tend to reverse the following morning, driven by
inventory imbalances and order-flow exhaustion at the 17:00 ET fixing window.

Mechanic:
  - At ~17:00 ET (daily bar close), measure the absolute 1-day return.
  - If |1d return| > 1.5 × average |1d return| over the trailing 5 days,
    fade the move: positive return → SHORT, negative return → LONG.
  - Exit at next-day 08:00 ET OR max hold 24h (forced_resolution).

Universe: 8 major FX pairs via yfinance daily bars.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FX_UNIVERSE = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCHF=X", "NZDUSD=X", "USDCAD=X", "EURGBP=X",
]

STRATEGY_NAME = "fx_overnight_reversal"


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
    """Generate overnight reversal picks for FX pairs.

    Each pick includes forced_resolution with max_hold_hours=24, tp_pct=0.3,
    sl_pct=0.2, time_exit_at_market=True.
    """
    if data is None:
        data = _download_data()

    picks: List[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol, df in data.items():
        if df is None or len(df) < 10:
            logger.debug("%s: insufficient data (%d bars)", symbol, len(df) if df is not None else 0)
            continue

        close = df["Close"].dropna()
        if len(close) < 6:
            continue

        current_price = float(close.iloc[-1])

        # 1-day return
        ret_1d = float(close.iloc[-1] / close.iloc[-2] - 1) if close.iloc[-2] != 0 else 0.0

        # Average absolute return over trailing 5 days
        abs_returns = close.pct_change().abs().iloc[-6:-1]  # last 5 daily |returns|, excluding today
        if len(abs_returns) < 3:
            continue
        avg_abs_ret = float(abs_returns.mean())

        if avg_abs_ret <= 0:
            continue

        # Signal: |1d return| > 1.5 × avg(|5d returns|)
        if abs(ret_1d) <= 1.5 * avg_abs_ret:
            continue

        # Fade direction: positive return → SHORT, negative → LONG
        direction = "SHORT" if ret_1d > 0 else "LONG"

        # TP/SL from forced_resolution spec
        tp_pct = 0.3 / 100  # 0.3%
        sl_pct = 0.2 / 100  # 0.2%
        if direction == "LONG":
            take_profit = _smart_round(current_price * (1 + tp_pct))
            stop_loss = _smart_round(current_price * (1 - sl_pct))
        else:
            take_profit = _smart_round(current_price * (1 - tp_pct))
            stop_loss = _smart_round(current_price * (1 + sl_pct))

        rr = tp_pct / sl_pct  # 1.5:1

        confidence = min(0.70, 0.50 + abs(ret_1d) / avg_abs_ret * 0.05)

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
            "risk_reward": round(rr, 2),
            "timestamp": _now_iso(),
            "reason": (
                f"|1d ret|={abs(ret_1d)*100:.3f}% > 1.5×avg5d={avg_abs_ret*100:.3f}% "
                f"→ fade {direction}"
            ),
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 24,
                "tp_pct": 0.3,
                "sl_pct": 0.2,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Breedon & Ranaldo (JF 2013)",
        })

    logger.info("%s: generated %d picks", STRATEGY_NAME, len(picks))
    return picks


def _download_data() -> dict[str, pd.DataFrame]:
    """Download ~30 days of daily FX data via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance required: pip install yfinance")
        return {}

    end = datetime.now(timezone.utc)
    start = end - pd.Timedelta(days=30)
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
            if df is not None and len(df) > 5:
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
        print("No picks generated (no extreme overnight moves detected).")
    logger.info("Done — %d picks.", len(picks))
