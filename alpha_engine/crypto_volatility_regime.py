"""
Crypto Volatility Regime Momentum Strategy
============================================
Academic basis: Moskowitz, Ooi & Pedersen (JFE 2012) "Time Series Momentum"
adapted for crypto with volatility-regime scaling.

Logic:
  - Compute 60-day time-series momentum (tsmom = sign of 60d return)
  - Compute 20-day realized volatility = std(daily returns) * sqrt(365)
  - Compute 80th percentile of trailing 1-year realized vol
  - LONG signal when: tsmom > 0 AND realized_vol < 80th pct of 1y vol
    (momentum is positive AND we are NOT in a vol spike — ride the trend
     during calm regimes, avoid chasing during blow-off tops)

Data source: yfinance (free, no API key)
Universe: top 10 liquid crypto USD pairs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_volatility_regime"
ACADEMIC_CITATION = "Moskowitz-Ooi-Pedersen (JFE 2012)"

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

TSLOOKBACK = 60
VOL_WINDOW = 20
VOL_PCTILE_WINDOW = 365
VOL_PCTILE_THRESHOLD = 80
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
        if hist.empty or len(hist) < VOL_PCTILE_WINDOW:
            logger.warning(
                "Insufficient data for %s (%d rows, need %d)",
                symbol, len(hist), VOL_PCTILE_WINDOW,
            )
            return None
        closes = hist["Close"].dropna().values.astype(float)
        return closes
    except Exception as e:
        logger.error("Data fetch failed for %s: %s", symbol, e)
        return None


def _compute_realized_vol(daily_returns: "np.ndarray", window: int = VOL_WINDOW) -> "np.ndarray":
    """Annualized realized vol from daily returns (crypto: sqrt(365))."""
    out = np.full(len(daily_returns), np.nan)
    for i in range(window, len(daily_returns)):
        out[i] = np.std(daily_returns[i - window:i]) * np.sqrt(365)
    return out


def generate_volatility_regime_picks() -> list[dict[str, Any]]:
    """Generate volatility-regime momentum picks for crypto universe.

    Returns LONG picks for assets with positive 60d momentum whose current
    realized vol is below the 80th percentile of the trailing 1-year vol.
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in CRYPTO_UNIVERSE:
        closes = _fetch_daily_closes(symbol)
        if closes is None or len(closes) < VOL_PCTILE_WINDOW + TSLOOKBACK:
            continue

        daily_returns = np.diff(closes) / closes[:-1]

        if len(daily_returns) < VOL_PCTILE_WINDOW:
            continue

        tsmom_60d = closes[-1] / closes[-TSLOOKBACK - 1] - 1.0

        realized_vol = _compute_realized_vol(daily_returns, VOL_WINDOW)
        current_rvol = realized_vol[-1]
        if np.isnan(current_rvol):
            logger.warning("Current realized vol is NaN for %s — skipping", symbol)
            continue

        trailing_1y_vol = realized_vol[-VOL_PCTILE_WINDOW:]
        trailing_1y_vol = trailing_1y_vol[~np.isnan(trailing_1y_vol)]
        if len(trailing_1y_vol) < 60:
            logger.warning("Not enough vol history for %s — skipping", symbol)
            continue

        vol_80th_pct = float(np.percentile(trailing_1y_vol, VOL_PCTILE_THRESHOLD))

        logger.info(
            "%s: tsmom_60d=%+.4f  rvol=%.4f  vol_80th=%.4f  signal=%s",
            symbol, tsmom_60d, current_rvol, vol_80th_pct,
            "LONG" if (tsmom_60d > 0 and current_rvol < vol_80th_pct) else "NONE",
        )

        if tsmom_60d > 0 and current_rvol < vol_80th_pct:
            confidence = round(
                min(0.82, 0.55 + abs(tsmom_60d) * 0.5 + (1 - current_rvol / vol_80th_pct) * 0.15),
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
                    f"Volatility Regime Momentum LONG: 60d return={tsmom_60d:+.2%} "
                    f"(positive momentum). Realized vol={current_rvol:.2%} < "
                    f"80th pct 1y vol={vol_80th_pct:.2%} (calm regime). "
                    f"Riding trend in low-vol window — Moskowitz-Ooi-Pedersen TSMOM."
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
                    "tsmom_60d": round(tsmom_60d, 6),
                    "realized_vol_20d": round(float(current_rvol), 6),
                    "vol_80th_pct_1y": round(vol_80th_pct, 6),
                    "vol_ratio": round(current_rvol / vol_80th_pct, 4) if vol_80th_pct > 0 else 0,
                    "tslookback": TSLOOKBACK,
                    "vol_window": VOL_WINDOW,
                    "tp_pct": TP_PCT,
                    "sl_pct": SL_PCT,
                },
                "timestamp": now.isoformat(),
            })

    logger.info(
        "Volatility Regime Momentum: scanned %d symbols, %d picks",
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
    _picks = generate_volatility_regime_picks()

    if _picks:
        print(_json.dumps(_picks, indent=2))
    else:
        logger.info("No picks generated")
        print("[]")
