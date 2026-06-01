"""
Crypto Whale Accumulation Signal Strategy
==========================================
Academic basis: Makarov & Schoar (RFS 2020) on crypto market microstructure.

Logic:
  - Use volume spike (>2x 20d avg volume) as proxy for whale activity
  - Use price near 20d low (<20th percentile of 20d range) as proxy for
    accumulation zone (whales buy dips, not breakouts)
  - Entry LONG: volume_ratio > 2.0 AND price_pctile_20d < 20
  - Exit: price > 50th percentile of 20d range OR max hold 72h

Data source: yfinance (free, no API key)
Universe: top 10 liquid crypto USD pairs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_whale_accumulation"
ACADEMIC_CITATION = "Makarov-Schoar (RFS 2020)"

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

VOL_WINDOW = 20
VOL_RATIO_THRESHOLD = 2.0
PRICE_PCTILE_THRESHOLD = 20
PRICE_EXIT_PCTILE = 50
FETCH_PERIOD = "3mo"

TP_PCT = 5.0
SL_PCT = 3.0
MAX_HOLD_HOURS = 72


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_daily_ohlcv(symbol: str) -> "tuple[np.ndarray, np.ndarray, np.ndarray] | None":
    """Fetch daily close, high, low, volume via yfinance.

    Returns (close_arr, high_arr, low_arr, volume_arr) or None.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=FETCH_PERIOD)
        if hist.empty or len(hist) < VOL_WINDOW + 5:
            logger.warning(
                "Insufficient data for %s (%d rows, need %d)",
                symbol, len(hist), VOL_WINDOW + 5,
            )
            return None
        close = hist["Close"].dropna().values.astype(float)
        high = hist["High"].dropna().values.astype(float)
        low = hist["Low"].dropna().values.astype(float)
        volume = hist["Volume"].dropna().values.astype(float)
        n = min(len(close), len(high), len(low), len(volume))
        return close[-n:], high[-n:], low[-n:], volume[-n:]
    except Exception as e:
        logger.error("Data fetch failed for %s: %s", symbol, e)
        return None


def _volume_ratio(volume: "np.ndarray", window: int = VOL_WINDOW) -> float:
    """Current volume / SMA(volume, window)."""
    if len(volume) < window + 1:
        return 0.0
    avg_vol = float(np.mean(volume[-(window + 1):-1]))
    if avg_vol < 1e-15:
        return 0.0
    return float(volume[-1]) / avg_vol


def _price_percentile_20d(close: "np.ndarray", high: "np.ndarray", low: "np.ndarray") -> float:
    """Current price's percentile position within the 20d high-low range.

    Returns 0-100. 0 = at 20d low, 100 = at 20d high.
    """
    if len(close) < VOL_WINDOW:
        return 50.0
    range_high = float(np.max(high[-VOL_WINDOW:]))
    range_low = float(np.min(low[-VOL_WINDOW:]))
    span = range_high - range_low
    if span < 1e-15:
        return 50.0
    return (float(close[-1]) - range_low) / span * 100.0


def generate_whale_accumulation_picks() -> list[dict[str, Any]]:
    """Generate whale accumulation picks for crypto universe.

    Returns LONG picks for assets showing volume spikes near 20d lows
    (proxy for institutional/whale accumulation).
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in CRYPTO_UNIVERSE:
        result = _fetch_daily_ohlcv(symbol)
        if result is None:
            continue

        close, high, low, volume = result
        price = float(close[-1])
        vol_ratio = _volume_ratio(volume)
        pctile = _price_percentile_20d(close, high, low)

        range_high = float(np.max(high[-VOL_WINDOW:]))
        range_low = float(np.min(low[-VOL_WINDOW:]))

        logger.info(
            "%s: price=%.2f  vol_ratio=%.2f  pctile_20d=%.1f  signal=%s",
            symbol, price, vol_ratio, pctile,
            "LONG" if (vol_ratio > VOL_RATIO_THRESHOLD and pctile < PRICE_PCTILE_THRESHOLD) else "NONE",
        )

        if vol_ratio > VOL_RATIO_THRESHOLD and pctile < PRICE_PCTILE_THRESHOLD:
            confidence = round(
                min(0.80, 0.50 + vol_ratio * 0.05 + (PRICE_PCTILE_THRESHOLD - pctile) * 0.005),
                2,
            )
            picks.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": STRATEGY_NAME,
                "asset_class": "CRYPTO",
                "category": "crypto",
                "confidence": confidence,
                "generated_at": now.isoformat(),
                "reason": (
                    f"Whale Accumulation LONG: volume_ratio={vol_ratio:.1f}x "
                    f"(>{VOL_RATIO_THRESHOLD}x threshold — spike detected). "
                    f"Price at {pctile:.0f}th pctile of 20d range "
                    f"({price:.2f} in [{range_low:.2f}, {range_high:.2f}]). "
                    f"Whale proxy: heavy volume near lows — Makarov-Schoar microstructure."
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
                    "volume_ratio": round(vol_ratio, 4),
                    "price_pctile_20d": round(pctile, 2),
                    "price": round(price, 4),
                    "range_20d_low": round(range_low, 4),
                    "range_20d_high": round(range_high, 4),
                    "exit_pctile": PRICE_EXIT_PCTILE,
                    "tp_pct": TP_PCT,
                    "sl_pct": SL_PCT,
                },
                "timestamp": now.isoformat(),
            })

    logger.info(
        "Whale Accumulation: scanned %d symbols, %d picks",
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
    _picks = generate_whale_accumulation_picks()

    if _picks:
        print(_json.dumps(_picks, indent=2))
    else:
        logger.info("No picks generated")
        print("[]")
