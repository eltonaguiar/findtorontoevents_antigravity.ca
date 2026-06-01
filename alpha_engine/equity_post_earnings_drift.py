"""
Equity Post-Earnings Announcement Drift (PEAD) Proxy Strategy
=============================================================
Academic basis: Bernard & Thomas (1989), Chan, Jegadeesh & Lakonishok (1996).
Edge: Stocks with positive earnings surprises systematically drift upward
for 20-60 trading days as the market underreacts to the information.

Since yfinance earnings estimates are unreliable, we use a price-volume
proxy: a single-day rally >3% on volume >2x the 20-day average signals
a "positive surprise" event. Entry at T+1 close, hold 60 days.

Data source: yfinance (free, no API key).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _HAS_YFINANCE = False

# ---------------------------------------------------------------------------
# Universe & Parameters
# ---------------------------------------------------------------------------
PEAD_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "UNH", "JNJ", "PG", "MA", "HD", "CRM", "KO", "PEP",
    "AVGO", "LLY", "COST",
]

MIN_DAILY_RETURN = 0.03   # +3% single-day rally
MIN_VOLUME_RATIO = 2.0    # volume >= 2x 20-day avg
HOLD_DAYS = 60            # PEAD drift window
TP_PCT = 0.03             # 3% take-profit
SL_PCT = 0.02             # 2% stop-loss
MAX_HOLD_HOURS = 168      # paper pilot cap (7 days)
LOOKBACK_DAYS = 90        # how far back to look for the surprise event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_ohlcv(symbol: str, period: str = "6mo") -> Any:
    """Fetch OHLCV data via yfinance. Returns DataFrame or None."""
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed")
        return None
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, auto_adjust=True)
        if hist is None or hist.empty or len(hist) < 25:
            logger.debug("%s: insufficient history (%s rows)", symbol,
                         len(hist) if hist is not None else 0)
            return None
        return hist
    except Exception as exc:
        logger.debug("%s: yfinance fetch error: %s", symbol, exc)
        return None


def _find_surprise_day(hist: Any) -> dict | None:
    """Find the most recent 'surprise' day in the lookback window.

    A surprise day is defined as:
      - 1-day return > +3%
      - Volume >= 2x 20-day average volume

    Returns dict with surprise details, or None if no surprise found.
    """
    close = hist["Close"]
    volume = hist["Volume"]

    # Compute daily returns and rolling volume average
    returns = close.pct_change()
    vol_avg_20d = volume.rolling(window=20).mean()

    # Only look at recent data (within LOOKBACK_DAYS trading days)
    lookback = min(LOOKBACK_DAYS, len(close) - 21)

    for i in range(-1, -lookback - 1, -1):
        try:
            daily_ret = float(returns.iloc[i])
            vol_ratio = float(volume.iloc[i] / vol_avg_20d.iloc[i]) if vol_avg_20d.iloc[i] > 0 else 0
        except (IndexError, ValueError):
            continue

        if daily_ret > MIN_DAILY_RETURN and vol_ratio > MIN_VOLUME_RATIO:
            days_ago = abs(i) - 1  # 0-indexed from most recent
            surprise_date = close.index[i]
            return {
                "days_ago": days_ago,
                "surprise_date": str(surprise_date.date()) if hasattr(surprise_date, "date") else str(surprise_date),
                "daily_return": round(daily_ret * 100, 2),
                "volume_ratio": round(vol_ratio, 2),
                "close_on_surprise": float(close.iloc[i]),
            }

    return None


# ---------------------------------------------------------------------------
# Core strategy
# ---------------------------------------------------------------------------
def equity_post_earnings_drift_signals(
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate PEAD proxy LONG signals.

    Entry: stock rallied >3% on volume >2x 20d avg within last 60 days.
    Exit: after 60 days or max hold 168h (paper pilot).

    Returns:
        List of pick dicts with all standard Alpha Engine fields.
    """
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed — cannot run equity_post_earnings_drift")
        return []

    universe = symbols or PEAD_UNIVERSE
    signals: list[dict[str, Any]] = []

    logger.info("PEAD Proxy: scanning %d symbols for surprise-day signals", len(universe))

    for symbol in universe:
        try:
            hist = _fetch_ohlcv(symbol, period="6mo")
            if hist is None:
                continue

            surprise = _find_surprise_day(hist)
            if surprise is None:
                logger.debug("%s: no surprise day found", symbol)
                continue

            # Only enter within 1 day of the surprise (T+1 entry)
            if surprise["days_ago"] > 1:
                logger.debug("%s: surprise was %d days ago, too late for T+1 entry",
                             symbol, surprise["days_ago"])
                continue

            current_price = float(hist["Close"].iloc[-1])
            if current_price <= 0:
                continue

            # Confidence scales with surprise magnitude
            # Base 0.60, +0.01 per 1% above 3% threshold, capped at 0.78
            excess_ret = surprise["daily_return"] - (MIN_DAILY_RETURN * 100)
            vol_bonus = min((surprise["volume_ratio"] - MIN_VOLUME_RATIO) * 0.02, 0.10)
            confidence = min(0.78, 0.60 + excess_ret * 0.01 + vol_bonus)

            tp = round(current_price * (1 + TP_PCT), 4)
            sl = round(current_price * (1 - SL_PCT), 4)

            signals.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": "equity_post_earnings_drift",
                "asset_class": "EQUITY",
                "category": "equity",
                "signal_type": "BUY",
                "entry_price": round(current_price, 2),
                "take_profit": tp,
                "stop_loss": sl,
                "tp": tp,
                "sl": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(TP_PCT / SL_PCT, 2),
                "generated_at": _now_iso(),
                "reason": (
                    f"PEAD proxy: {surprise['daily_return']:+.1f}% rally on "
                    f"{surprise['volume_ratio']:.1f}x volume "
                    f"(surprise date {surprise['surprise_date']}). "
                    f"T+1 entry, {HOLD_DAYS}d drift window."
                ),
                "source": "alpha_engine",
                "source_system": "equity_post_earnings_drift",
                "forced_resolution": {
                    "max_hold_hours": MAX_HOLD_HOURS,
                    "tp_pct": TP_PCT * 100,
                    "sl_pct": SL_PCT * 100,
                    "time_exit_at_market": True,
                },
                "paper_pilot": True,
                "academic_citation": "Bernard & Thomas (1989); Chan, Jegadeesh & Lakonishok (1996)",
                "extra": {
                    "surprise_date": surprise["surprise_date"],
                    "surprise_daily_return_pct": surprise["daily_return"],
                    "surprise_volume_ratio": surprise["volume_ratio"],
                    "hold_days": HOLD_DAYS,
                    "days_since_surprise": surprise["days_ago"],
                },
                "timestamp": _now_iso(),
            })

            logger.info(
                "%s: PEAD signal — surprise %.1f%% on %.1fx vol, conf=%.3f",
                symbol, surprise["daily_return"], surprise["volume_ratio"], confidence,
            )

        except Exception as exc:
            logger.debug("PEAD error for %s: %s", symbol, exc)
            continue

    logger.info("PEAD Proxy: %d signals from %d symbols", len(signals), len(universe))
    return signals


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    print("=" * 60)
    print("Equity Post-Earnings Announcement Drift (PEAD) Proxy")
    print("Bernard & Thomas (1989); Chan, Jegadeesh & Lakonishok (1996)")
    print("=" * 60)

    picks = equity_post_earnings_drift_signals()

    print(f"\nTotal signals: {len(picks)}")
    if picks:
        print(f"{'Symbol':<8} {'Direction':<7} {'Conf':<6} {'Ret%':>7} {'VolX':>6} {'Price':>10}")
        print("-" * 50)
        for p in picks:
            ex = p.get("extra", {})
            print(
                f"{p['symbol']:<8} {p['direction']:<7} {p['confidence']:<6.2f} "
                f"{ex.get('surprise_daily_return_pct', 0):>+7.1f} "
                f"{ex.get('surprise_volume_ratio', 0):>6.1f} "
                f"${p['entry_price']:>9.2f}"
            )
    else:
        print("No PEAD signals today (no qualifying surprise days found).")
