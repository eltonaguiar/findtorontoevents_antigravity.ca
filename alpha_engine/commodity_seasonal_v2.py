"""Improved Commodity Seasonal Pattern Strategy (v2)
=====================================================
Academic citation: Gorton, Hayashi & Rouwenhorst (JBF 2013)
"The Fundamentals of Commodity Futures Returns"

Logic:
  Each commodity has seasonal strong/weak months driven by supply/demand
  cycles. Uses 5-year average monthly returns to determine seasonal bias
  per commodity. Only trades in historically strong months when momentum
  confirms the seasonal direction.

Entry:
  In historically strong month AND 1m momentum > 0 → LONG

Exit:
  End of month  OR  max hold 168h (7 days)

Universe: GC=F, SI=F, CL=F, NG=F, HG=F, ZC=F

DEFAULT-OFF. Set env COMMODITY_SEASONAL_V2_ENABLED=1 to emit picks.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_seasonal_v2"
ACADEMIC_CITATION = "Gorton-Hayashi-Rouwenhorst (JBF 2013)"

COMMODITY_UNIVERSE: dict[str, dict[str, str]] = {
    "GC=F": {"name": "Gold", "sector": "precious_metals"},
    "SI=F": {"name": "Silver", "sector": "precious_metals"},
    "CL=F": {"name": "WTI Crude Oil", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "sector": "energy"},
    "HG=F": {"name": "Copper", "sector": "industrial_metals"},
    "ZC=F": {"name": "Corn", "sector": "agriculture"},
}

FETCH_PERIOD_5Y = "5y"
FETCH_PERIOD_3MO = "3mo"
MOMENTUM_WINDOW = 21
TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 168
MIN_STRONG_MONTHS = 3
STRONG_MONTH_THRESHOLD_PCT = 0.5


def _enabled() -> bool:
    return os.environ.get("COMMODITY_SEASONAL_V2_ENABLED", "0") == "1"


def _compute_avg_monthly_returns(symbol: str) -> Optional[dict[int, float]]:
    """Compute average monthly returns over 5 years for *symbol* via yfinance."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=FETCH_PERIOD_5Y, interval="1mo",
                         auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 24:
            return None
        if hasattr(df.columns, "get_level_values"):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                pass
        close = df["Close"].dropna().astype(float)
        if len(close) < 24:
            return None

        returns = close.pct_change().dropna()
        monthly_avg: dict[int, list[float]] = {}
        for dt, ret in returns.items():
            m = dt.month
            monthly_avg.setdefault(m, []).append(float(ret))

        avg_returns = {}
        for m, rets in monthly_avg.items():
            if rets:
                avg_returns[m] = float(np.mean(rets))
        return avg_returns
    except Exception as e:
        logger.warning("5y monthly data fetch failed for %s: %s", symbol, e)
        return None


def _fetch_current_momentum(symbol: str) -> Optional[float]:
    """Fetch 1-month momentum for *symbol* via yfinance."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=FETCH_PERIOD_3MO, interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "get_level_values"):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                pass
        close = df["Close"].dropna().astype(float)
        if len(close) < MOMENTUM_WINDOW + 5:
            return None
        last = float(close.iloc[-1])
        lookback = float(close.iloc[-MOMENTUM_WINDOW])
        if lookback <= 0:
            return None
        return (last - lookback) / lookback
    except Exception as e:
        logger.warning("Momentum fetch failed for %s: %s", symbol, e)
        return None


def _get_strong_months(avg_returns: dict[int, float]) -> set[int]:
    """Return months where average return exceeds threshold."""
    strong = set()
    for m, avg_ret in avg_returns.items():
        if avg_ret > STRONG_MONTH_THRESHOLD_PCT / 100.0:
            strong.add(m)
    return strong


def generate_picks(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Generate improved seasonal picks."""
    if not _enabled():
        logger.info("commodity_seasonal_v2 disabled (set COMMODITY_SEASONAL_V2_ENABLED=1)")
        return []

    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    current_month = now.month
    picks: list[dict[str, Any]] = []

    for symbol, meta in COMMODITY_UNIVERSE.items():
        avg_returns = _compute_avg_monthly_returns(symbol)
        if avg_returns is None:
            logger.warning("Skipping %s — no 5y monthly data", symbol)
            continue

        strong_months = _get_strong_months(avg_returns)
        if not strong_months:
            logger.info("%s: no strong months found (threshold=%.3f%%)",
                        symbol, STRONG_MONTH_THRESHOLD_PCT)
            continue

        if current_month not in strong_months:
            logger.info("%s: month %d not in strong months %s — skip",
                        symbol, current_month, sorted(strong_months))
            continue

        momentum = _fetch_current_momentum(symbol)
        if momentum is None:
            logger.warning("Skipping %s — no momentum data", symbol)
            continue

        if momentum <= 0:
            logger.info("%s: in strong month %d but momentum %.4f <= 0 — skip",
                        symbol, current_month, momentum)
            continue

        month_avg_ret = avg_returns.get(current_month, 0.0)
        confidence = round(min(0.78, 0.55 + abs(month_avg_ret) * 5 + abs(momentum) * 2), 4)

        picks.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Seasonal v2 LONG: {meta['name']} in historically strong month "
                f"({current_month}) with avg monthly return "
                f"{month_avg_ret*100:+.2f}% and 1m momentum "
                f"{momentum*100:+.2f}%. Gorton-Hayashi-Rouwenhorst "
                f"commodity futures returns."
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
                "current_month": current_month,
                "avg_monthly_return": round(month_avg_ret, 6),
                "momentum_1m": round(momentum, 6),
                "strong_months": sorted(strong_months),
                "all_monthly_returns": {str(k): round(v, 6) for k, v in avg_returns.items()},
                "exit_condition": "end_of_month_or_max_hold",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })

    logger.info("Seasonal v2: %d picks generated from %d symbols (month=%d)",
                len(picks), len(COMMODITY_UNIVERSE), current_month)
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Running Seasonal v2 strategy (standalone)...")
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        logger.info("No picks generated (disabled, not strong month, or momentum <= 0)")
        print("[]")
