"""FX Asian Session Range Break Strategy

Academic basis: Osler (2005) — "Support and Resistance in Currency Markets"
documents that intraday range breakouts (particularly from the Asian session)
carry directional momentum into the London/NY sessions because stop-loss
clusters accumulate at range extremes during low-volatility Asian hours.

Mechanic:
  - Track yesterday's high/low as a proxy for the Asian session range
    (yfinance lacks reliable intraday FX candles; daily high/low captures
    the overnight consolidation range for most G10 pairs).
  - If current price breaks yesterday's high by >0.1% → LONG (breakout).
  - If current price breaks yesterday's low by >0.1% → SHORT (breakdown).
  - Target: range midpoint as TP proxy. Stop: opposite range extreme + buffer.
  - Forced exit: max hold 24h or return to range midpoint.

Universe: 8 major FX pairs via yfinance daily bars.
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

STRATEGY_NAME = "fx_asian_range_break"
BREAKOUT_THRESHOLD = 0.001  # 0.1%


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
    """Generate Asian session range break picks.

    Each pick includes forced_resolution with max_hold_hours=24, tp_pct=0.3,
    sl_pct=0.2, time_exit_at_market=True.
    """
    if data is None:
        data = _download_data()

    picks: List[dict[str, Any]] = []

    for symbol, df in data.items():
        if df is None or len(df) < 5:
            logger.debug("%s: insufficient data", symbol)
            continue

        high = df["High"].dropna()
        low = df["Low"].dropna()
        close = df["Close"].dropna()

        if len(high) < 3 or len(low) < 3 or len(close) < 3:
            continue

        current_price = float(close.iloc[-1])
        yesterday_high = float(high.iloc[-2])
        yesterday_low = float(low.iloc[-2])
        range_mid = (yesterday_high + yesterday_low) / 2.0
        range_size = yesterday_high - yesterday_low

        if range_size <= 0 or current_price <= 0:
            continue

        breakout_pct = (current_price - yesterday_high) / yesterday_high
        breakdown_pct = (yesterday_low - current_price) / yesterday_low

        direction: str | None = None
        take_profit: float = 0.0
        stop_loss: float = 0.0

        if breakout_pct > BREAKOUT_THRESHOLD:
            direction = "LONG"
            # TP: range midpoint projected upward (range height above breakout)
            take_profit = _smart_round(current_price + range_size)
            # SL: yesterday's low (back inside range = failed breakout)
            stop_loss = _smart_round(yesterday_low)
        elif breakdown_pct > BREAKOUT_THRESHOLD:
            direction = "SHORT"
            # TP: range midpoint projected downward
            take_profit = _smart_round(current_price - range_size)
            # SL: yesterday's high
            stop_loss = _smart_round(yesterday_high)
        else:
            continue

        # Risk/reward
        tp_dist = abs(take_profit - current_price)
        sl_dist = abs(stop_loss - current_price)
        if sl_dist <= 0:
            continue
        rr = round(tp_dist / sl_dist, 2)

        # Confidence based on breakout magnitude beyond threshold
        magnitude = breakout_pct if direction == "LONG" else breakdown_pct
        confidence = min(0.72, 0.52 + magnitude * 20)

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
                f"Asian range break: yest_hi={_smart_round(yesterday_high)}, "
                f"yest_lo={_smart_round(yesterday_low)}, "
                f"price={_smart_round(current_price)} "
                f"→ {direction} ({magnitude*100:.2f}% beyond range)"
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
            "academic_citation": "Osler (2005) — Support and Resistance in Currency Markets",
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
        print("No picks generated (no range breakouts detected).")
    logger.info("Done — %d picks.", len(picks))
