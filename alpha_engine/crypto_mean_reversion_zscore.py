"""
Crypto Mean Reversion Z-Score Strategy
=======================================
Academic basis: Poterba & Summers (1988) + Liu (2022) crypto-specific.

Logic:
  - Compute Z-score of price vs 20-day SMA
  - Compute 200-day SMA as trend filter (only trade in direction of trend)
  - Entry LONG: Z < -2.0 AND price > 200d SMA (oversold in uptrend)
  - Entry SHORT: Z > 2.0 AND price < 200d SMA (overbought in downtrend)
  - Exit: Z crosses back to 0 OR max hold 72h

Data source: yfinance (free, no API key)
Universe: top 10 liquid crypto USD pairs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_mean_reversion_zscore"
ACADEMIC_CITATION = "Poterba-Summers (1988); Liu (2022)"

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

SMA_SHORT = 20
SMA_LONG = 200
Z_ENTRY = 2.0
Z_EXIT = 0.0
FETCH_PERIOD = "2y"

TP_PCT = 5.0
SL_PCT = 3.0
MAX_HOLD_HOURS = 72


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_daily_closes(symbol: str) -> "np.ndarray | None":
    """Fetch daily close prices via yfinance. Returns numpy array or None."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=FETCH_PERIOD)
        if hist.empty or len(hist) < SMA_LONG + SMA_SHORT:
            logger.warning(
                "Insufficient data for %s (%d rows, need %d)",
                symbol, len(hist), SMA_LONG + SMA_SHORT,
            )
            return None
        closes = hist["Close"].dropna().values.astype(float)
        return closes
    except Exception as e:
        logger.error("Data fetch failed for %s: %s", symbol, e)
        return None


def _sma(arr: "np.ndarray", window: int) -> float:
    """Simple moving average of last `window` values."""
    if len(arr) < window:
        return float("nan")
    return float(np.mean(arr[-window:]))


def _zscore(price: float, sma_val: float, window_arr: "np.ndarray") -> float:
    """Z-score = (price - SMA) / std(window)."""
    std_val = float(np.std(window_arr[-SMA_SHORT:]))
    if std_val < 1e-15:
        return 0.0
    return (price - sma_val) / std_val


def generate_mean_reversion_zscore_picks() -> list[dict[str, Any]]:
    """Generate mean-reversion Z-score picks for crypto universe.

    Returns LONG picks for oversold-in-uptrend and SHORT picks for
    overbought-in-downtrend, filtered by 200d SMA trend.
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in CRYPTO_UNIVERSE:
        closes = _fetch_daily_closes(symbol)
        if closes is None:
            continue

        price = float(closes[-1])
        sma_20 = _sma(closes, SMA_SHORT)
        sma_200 = _sma(closes, SMA_LONG)

        if np.isnan(sma_20) or np.isnan(sma_200) or sma_200 <= 0:
            logger.warning("Invalid SMAs for %s — skipping", symbol)
            continue

        z = _zscore(price, sma_20, closes)

        uptrend = price > sma_200
        downtrend = price < sma_200

        logger.info(
            "%s: price=%.2f  sma20=%.2f  sma200=%.2f  z=%.2f  trend=%s",
            symbol, price, sma_20, sma_200, z,
            "UP" if uptrend else "DOWN",
        )

        direction = None
        if z < -Z_ENTRY and uptrend:
            direction = "LONG"
        elif z > Z_ENTRY and downtrend:
            direction = "SHORT"

        if direction is not None:
            confidence = round(
                min(0.80, 0.55 + abs(z) * 0.05),
                2,
            )
            trend_label = "uptrend" if direction == "LONG" else "downtrend"
            picks.append({
                "symbol": symbol,
                "direction": direction,
                "strategy": STRATEGY_NAME,
                "asset_class": "CRYPTO",
                "category": "crypto",
                "confidence": confidence,
                "generated_at": now.isoformat(),
                "reason": (
                    f"Mean Reversion Z-Score {direction}: Z={z:+.2f} "
                    f"(price={price:.2f} vs SMA20={sma_20:.2f}). "
                    f"Trend filter: price {'>' if uptrend else '<'} "
                    f"SMA200={sma_200:.2f} ({trend_label}). "
                    f"Oversold bounce in {trend_label} — Poterba-Summers mean reversion."
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
                    "zscore": round(z, 4),
                    "price": round(price, 4),
                    "sma_20": round(sma_20, 4),
                    "sma_200": round(sma_200, 4),
                    "z_entry": Z_ENTRY,
                    "z_exit": Z_EXIT,
                    "tp_pct": TP_PCT,
                    "sl_pct": SL_PCT,
                },
                "timestamp": now.isoformat(),
            })

    logger.info(
        "Mean Reversion Z-Score: scanned %d symbols, %d picks",
        len(CRYPTO_UNIVERSE), len(picks),
    )
    return picks


if __name__ == "__main__":
    import json as _json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Running %s (standalone)...", STRATEGY_NAME)
    _picks = generate_mean_reversion_zscore_picks()

    if _picks:
        print(_json.dumps(_picks, indent=2))
    else:
        logger.info("No picks generated")
        print("[]")
