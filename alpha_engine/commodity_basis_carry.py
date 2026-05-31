"""Commodity Basis Carry Strategy — Erb & Harvey / Gorton & Rouwenhorst.

Academic basis: Erb & Harvey (FAJ 2006) "The Tactical and Strategic Value of
Commodity Futures" + Gorton & Rouwenhorst (FAJ 2006) "Facts and Fantasies
about Commodity Futures".  Both papers document that the futures basis
(backwardation vs contango) predicts cross-sectional commodity returns.

Logic:
  - Compute basis proxy for each commodity: current price / 6-month SMA.
    When price > SMA the market is in backwardation (tight supply, upward-
    sloping spot curve); when price < SMA it is in contango (glut).
  - Rank all 6 commodities by basis proxy (most backwardated first).
  - Long top-3 (strongest backwardation = best carry).
  - Short bottom-3 (deepest contango = negative carry).
  - Monthly rebalance (1st trading day of each month).

Proxy rationale: yfinance continuous futures (=F) do not expose separate
front/back month contracts reliably.  Erb-Harvey show that the spot-to-
futures roll yield is closely approximated by the deviation of spot from
its intermediate SMA — a standard practitioner shortcut.

Symbols: CL=F (crude), NG=F (natgas), GC=F (gold), ZC=F (corn),
         HG=F (copper), SI=F (silver)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_basis_carry"
ACADEMIC_CITATION = "Erb-Harvey (FAJ 2006)"

COMMODITY_UNIVERSE: dict[str, dict[str, str]] = {
    "CL=F": {"name": "WTI Crude Oil", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "sector": "energy"},
    "GC=F": {"name": "Gold", "sector": "precious_metals"},
    "ZC=F": {"name": "Corn", "sector": "agriculture"},
    "HG=F": {"name": "Copper", "sector": "industrial_metals"},
    "SI=F": {"name": "Silver", "sector": "precious_metals"},
}

SMA_LOOKBACK_DAYS = 126  # ~6 months of trading days
FETCH_PERIOD = "1y"       # enough history for 6m SMA
TOP_N = 3
BOTTOM_N = 3

TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 720  # 30 days


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_rebalance_day() -> bool:
    """Return True if today is within first 3 trading days of the month.

    This gives a ~3-day window so that weekends/holidays don't skip
    a monthly rebalance.
    """
    now = datetime.now(timezone.utc)
    return now.day <= 3


def _fetch_price_and_sma(symbol: str) -> Optional[tuple[float, float]]:
    """Fetch latest close and 6-month SMA for *symbol* via yfinance.

    Returns (latest_close, sma_6m) or None on failure.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=FETCH_PERIOD)
        if hist.empty or len(hist) < SMA_LOOKBACK_DAYS:
            logger.warning(
                "Insufficient data for %s (%d rows, need %d)",
                symbol, len(hist), SMA_LOOKBACK_DAYS,
            )
            return None
        close = hist["Close"].dropna()
        if len(close) < SMA_LOOKBACK_DAYS:
            return None
        latest = float(close.iloc[-1])
        sma_val = float(close.iloc[-SMA_LOOKBACK_DAYS:].mean())
        if sma_val <= 0 or latest <= 0:
            return None
        return latest, sma_val
    except Exception as e:
        logger.error("Data fetch failed for %s: %s", symbol, e)
        return None


def _basis_proxy(price: float, sma_6m: float) -> float:
    """Compute basis proxy = (price - sma) / sma.

    Positive → backwardation (price above SMA → tight supply / roll yield).
    Negative → contango (price below SMA → glut / negative carry).
    """
    return (price - sma_6m) / sma_6m


def generate_commodity_basis_carry_picks() -> list[dict[str, Any]]:
    """Generate commodity basis-carry picks.

    Returns LONG picks for top-3 most-backwardated commodities and
    SHORT picks for bottom-3 most-contangoed commodities.
    Only fires on the first few days of each month (rebalance window).

    Returns ``[]`` outside the rebalance window or on data failure.
    """
    if not _is_rebalance_day():
        logger.info(
            "Not a rebalance day (day=%d, need <=3) — no picks",
            datetime.now(timezone.utc).day,
        )
        return []

    rankings: list[dict[str, Any]] = []

    for symbol, meta in COMMODITY_UNIVERSE.items():
        result = _fetch_price_and_sma(symbol)
        if result is None:
            logger.warning("Skipping %s — no data", symbol)
            continue
        price, sma_val = result
        basis = _basis_proxy(price, sma_val)
        rankings.append({
            "symbol": symbol,
            "name": meta["name"],
            "sector": meta["sector"],
            "price": price,
            "sma_6m": sma_val,
            "basis": basis,
        })

    if len(rankings) < 4:
        logger.warning(
            "Only %d commodities with data — need at least 4, skipping",
            len(rankings),
        )
        return []

    rankings.sort(key=lambda x: x["basis"], reverse=True)

    logger.info("Basis rankings (most backwardated → most contango):")
    for i, r in enumerate(rankings):
        logger.info(
            "  %d. %s  basis=%+.4f  price=%.2f  sma=%.2f",
            i + 1, r["symbol"], r["basis"], r["price"], r["sma_6m"],
        )

    top = rankings[:TOP_N]
    bottom = rankings[-BOTTOM_N:]

    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for r in top:
        confidence = round(min(0.76, 0.60 + abs(r["basis"]) * 2), 2)
        picks.append({
            "symbol": r["symbol"],
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "reason": (
                f"Basis carry LONG: {r['name']} in backwardation "
                f"(basis={r['basis']:+.4f}, price={r['price']:.2f} > "
                f"SMA6m={r['sma_6m']:.2f}). "
                f"Top-{TOP_N} carry rank — Erb-Harvey roll yield premium."
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
                "basis_proxy": round(r["basis"], 6),
                "price": round(r["price"], 4),
                "sma_6m": round(r["sma_6m"], 4),
                "sector": r["sector"],
                "rank": rankings.index(r) + 1,
                "universe_size": len(rankings),
                "rebalance": "monthly",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
            "timestamp": now.isoformat(),
        })

    for r in bottom:
        confidence = round(min(0.72, 0.55 + abs(r["basis"]) * 2), 2)
        picks.append({
            "symbol": r["symbol"],
            "direction": "SHORT",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "reason": (
                f"Basis carry SHORT: {r['name']} in deep contango "
                f"(basis={r['basis']:+.4f}, price={r['price']:.2f} < "
                f"SMA6m={r['sma_6m']:.2f}). "
                f"Bottom-{BOTTOM_N} carry rank — negative roll yield."
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
                "basis_proxy": round(r["basis"], 6),
                "price": round(r["price"], 4),
                "sma_6m": round(r["sma_6m"], 4),
                "sector": r["sector"],
                "rank": rankings.index(r) + 1,
                "universe_size": len(rankings),
                "rebalance": "monthly",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
            "timestamp": now.isoformat(),
        })

    logger.info(
        "Commodity Basis Carry: %d commodities ranked, %d picks generated "
        "(%d LONG, %d SHORT)",
        len(rankings), len(picks), len(top), len(bottom),
    )
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Running Commodity Basis Carry strategy (standalone)...")
    logger.info(
        "Rebalance window: day <= 3 of month (today: day %d)",
        datetime.now(timezone.utc).day,
    )

    picks = generate_commodity_basis_carry_picks()

    if picks:
        print(json.dumps(picks, indent=2))
    else:
        logger.info("No picks generated (outside rebalance window or data failure)")
        print("[]")
