"""
Crypto Liquidation Cascade Fade Strategy
=========================================
Academic basis: Ait-Sahalia et al. (2021) on flash crashes and liquidation
cascades in crypto markets.

Logic:
  - Use 4h candles from yfinance to detect sharp drops
  - Entry LONG: 4h return < -5% AND volume_ratio > 3.0x → fade the panic
    (liquidation cascades overshoot; price mean-reverts 65-72% per Ait-Sahalia)
  - Exit: price recovers to pre-crash level OR max hold 48h

Data source: yfinance (free, no API key)
Universe: top 10 liquid crypto USD pairs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_liquidation_fade"
ACADEMIC_CITATION = "Ait-Sahalia et al. (2021)"

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

DROP_THRESHOLD = -0.05
VOL_RATIO_THRESHOLD = 3.0
VOL_WINDOW = 20
FETCH_INTERVAL = "1h"
FETCH_PERIOD = "5d"

TP_PCT = 5.0
SL_PCT = 3.0
MAX_HOLD_HOURS = 48


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_hourly_ohlcv(symbol: str) -> "tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None":
    """Fetch hourly OHLCV via yfinance.

    Returns (close, high, low, volume) arrays or None.
    yfinance supports '1h' interval with max 730 days.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(interval=FETCH_INTERVAL, period=FETCH_PERIOD)
        if hist.empty or len(hist) < VOL_WINDOW + 10:
            logger.warning(
                "Insufficient hourly data for %s (%d rows, need %d)",
                symbol, len(hist), VOL_WINDOW + 10,
            )
            return None
        close = hist["Close"].dropna().values.astype(float)
        high = hist["High"].dropna().values.astype(float)
        low = hist["Low"].dropna().values.astype(float)
        volume = hist["Volume"].dropna().values.astype(float)
        n = min(len(close), len(high), len(low), len(volume))
        return close[-n:], high[-n:], low[-n:], volume[-n:]
    except Exception as e:
        logger.error("Hourly data fetch failed for %s: %s", symbol, e)
        return None


def _4h_return_from_hourly(close: "np.ndarray") -> float:
    """Compute return over last 4 hourly bars.

    Uses 4-bar window from hourly data to approximate 4h return.
    """
    if len(close) < 5:
        return 0.0
    return float(close[-1] / close[-5] - 1.0)


def _volume_ratio_hourly(volume: "np.ndarray", window: int = VOL_WINDOW) -> float:
    """Current hourly volume / SMA(volume, window)."""
    if len(volume) < window + 1:
        return 0.0
    avg_vol = float(np.mean(volume[-(window + 1):-1]))
    if avg_vol < 1e-15:
        return 0.0
    return float(volume[-1]) / avg_vol


def _pre_crash_price(close: "np.ndarray") -> float:
    """Price 5 bars ago (start of the 4h drop window)."""
    if len(close) < 5:
        return float(close[-1])
    return float(close[-5])


def generate_liquidation_fade_picks() -> list[dict[str, Any]]:
    """Generate liquidation cascade fade picks for crypto universe.

    Returns LONG picks for assets that experienced a sharp 4h drop (>5%)
    with elevated volume (>3x avg), fading the panic sell-off.
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in CRYPTO_UNIVERSE:
        result = _fetch_hourly_ohlcv(symbol)
        if result is None:
            continue

        close, high, low, volume = result
        price = float(close[-1])
        ret_4h = _4h_return_from_hourly(close)
        vol_ratio = _volume_ratio_hourly(volume)
        pre_crash = _pre_crash_price(close)

        logger.info(
            "%s: price=%.2f  4h_return=%+.2f%%  vol_ratio=%.2f  signal=%s",
            symbol, price, ret_4h * 100, vol_ratio,
            "LONG" if (ret_4h < DROP_THRESHOLD and vol_ratio > VOL_RATIO_THRESHOLD) else "NONE",
        )

        if ret_4h < DROP_THRESHOLD and vol_ratio > VOL_RATIO_THRESHOLD:
            confidence = round(
                min(0.78, 0.50 + abs(ret_4h) * 3 + vol_ratio * 0.02),
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
                    f"Liquidation Cascade Fade LONG: 4h return={ret_4h:+.2%} "
                    f"(>{abs(DROP_THRESHOLD):.0%} drop). "
                    f"Volume ratio={vol_ratio:.1f}x (>{VOL_RATIO_THRESHOLD}x — "
                    f"elevated liquidation activity). "
                    f"Pre-crash level={pre_crash:.2f}. "
                    f"Fading panic — Ait-Sahalia cascade recovery."
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
                    "return_4h": round(ret_4h, 6),
                    "volume_ratio": round(vol_ratio, 4),
                    "price": round(price, 4),
                    "pre_crash_price": round(pre_crash, 4),
                    "drop_threshold": DROP_THRESHOLD,
                    "vol_threshold": VOL_RATIO_THRESHOLD,
                    "max_hold_hours": MAX_HOLD_HOURS,
                    "tp_pct": TP_PCT,
                    "sl_pct": SL_PCT,
                },
                "timestamp": now.isoformat(),
            })

    logger.info(
        "Liquidation Cascade Fade: scanned %d symbols, %d picks",
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
    _picks = generate_liquidation_fade_picks()

    if _picks:
        print(_json.dumps(_picks, indent=2))
    else:
        logger.info("No picks generated")
        print("[]")
