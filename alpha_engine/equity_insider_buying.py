"""
Equity Insider Buying Cluster Proxy Strategy
=============================================
Academic basis: Lakonishok & Lee (JF 2001) "Are Insider Trades Informative?"
Edge: Stocks with insider buying clusters (multiple insiders buying within
a short window) outperform by 5-8% over the following 6 months. Insiders
buy when they believe the stock is undervalued — their trades are the
strongest signal of future outperformance.

Proxy: Stock outperforms SPY by >2% over 5 days while volume increases
(5d avg > 1.5x 20d avg). This captures institutional/insider accumulation
without requiring SEC EDGAR scraping.

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
INSIDER_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "UNH", "JNJ", "PG", "MA", "HD", "CRM", "KO", "PEP",
    "AVGO", "LLY", "COST",
]

BENCHMARK = "SPY"
EXCESS_RETURN_THRESHOLD = 0.02   # +2% excess return vs SPY over 5d
VOLUME_RATIO_5D_VS_20D = 1.5    # 5d avg volume >= 1.5x 20d avg
HOLD_DAYS = 30
TP_PCT = 0.03                    # 3% take-profit
SL_PCT = 0.02                    # 2% stop-loss
MAX_HOLD_HOURS = 168             # paper pilot cap (7 days)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_close_volume(symbol: str, period: str = "3mo") -> Any:
    """Fetch OHLCV data via yfinance. Returns DataFrame or None (fail-open)."""
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed")
        return None
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, auto_adjust=True)
        if hist is None or hist.empty or len(hist) < 25:
            logger.debug("%s: insufficient data (%s rows)", symbol,
                         len(hist) if hist is not None else 0)
            return None
        return hist
    except Exception as exc:
        logger.debug("%s: yfinance error: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Core strategy
# ---------------------------------------------------------------------------
def equity_insider_buying_signals(
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate insider-buying proxy LONG signals.

    Entry conditions (all must be true):
      1. 5-day excess return vs SPY > +2%
      2. 5-day average volume > 1.5x 20-day average volume

    Returns:
        List of pick dicts with all standard Alpha Engine fields.
    """
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed — cannot run equity_insider_buying")
        return []

    universe = symbols or INSIDER_UNIVERSE

    # Fetch SPY benchmark data once
    spy_hist = _fetch_close_volume(BENCHMARK, period="3mo")
    if spy_hist is None:
        logger.error("Failed to fetch SPY benchmark data")
        return []

    spy_close = spy_hist["Close"]
    spy_ret_5d = float(spy_close.iloc[-1] / spy_close.iloc[-6] - 1) if len(spy_close) >= 6 else 0.0

    signals: list[dict[str, Any]] = []

    logger.info("Insider Buying Proxy: scanning %d symbols", len(universe))

    for symbol in universe:
        try:
            hist = _fetch_close_volume(symbol, period="3mo")
            if hist is None:
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            if len(close) < 21 or len(volume) < 21:
                continue

            current_price = float(close.iloc[-1])
            if current_price <= 0:
                continue

            # Condition 1: 5-day excess return vs SPY > 2%
            stock_ret_5d = float(close.iloc[-1] / close.iloc[-6] - 1)
            excess_return = stock_ret_5d - spy_ret_5d

            if excess_return < EXCESS_RETURN_THRESHOLD:
                logger.debug("%s: excess return %.2f%% < %.2f%%",
                             symbol, excess_return * 100, EXCESS_RETURN_THRESHOLD * 100)
                continue

            # Condition 2: 5d avg volume > 1.5x 20d avg volume
            vol_5d_avg = float(volume.iloc[-5:].mean())
            vol_20d_avg = float(volume.iloc[-20:].mean())

            if vol_20d_avg <= 0:
                continue

            vol_ratio = vol_5d_avg / vol_20d_avg

            if vol_ratio < VOLUME_RATIO_5D_VS_20D:
                logger.debug("%s: vol_ratio %.2f < %.2f",
                             symbol, vol_ratio, VOLUME_RATIO_5D_VS_20D)
                continue

            # Both conditions met — generate signal
            # Confidence scales with excess return magnitude and volume surge
            ret_bonus = min((excess_return - EXCESS_RETURN_THRESHOLD) * 2.0, 0.12)
            vol_bonus = min((vol_ratio - VOLUME_RATIO_5D_VS_20D) * 0.03, 0.06)
            confidence = min(0.78, 0.58 + ret_bonus + vol_bonus)

            tp = round(current_price * (1 + TP_PCT), 4)
            sl = round(current_price * (1 - SL_PCT), 4)

            signals.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": "equity_insider_buying",
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
                    f"Insider buying proxy: 5d excess return vs SPY "
                    f"{excess_return * 100:+.1f}% (>2%), "
                    f"5d/20d vol ratio {vol_ratio:.2f}x (>1.5x). "
                    f"Accumulation pattern detected."
                ),
                "source": "alpha_engine",
                "source_system": "equity_insider_buying",
                "forced_resolution": {
                    "max_hold_hours": MAX_HOLD_HOURS,
                    "tp_pct": TP_PCT * 100,
                    "sl_pct": SL_PCT * 100,
                    "time_exit_at_market": True,
                },
                "paper_pilot": True,
                "academic_citation": "Lakonishok & Lee (JF 2001) 'Are Insider Trades Informative?'",
                "extra": {
                    "excess_return_5d_pct": round(excess_return * 100, 2),
                    "stock_return_5d_pct": round(stock_ret_5d * 100, 2),
                    "spy_return_5d_pct": round(spy_ret_5d * 100, 2),
                    "volume_ratio_5d_vs_20d": round(vol_ratio, 2),
                    "vol_5d_avg": round(vol_5d_avg, 0),
                    "vol_20d_avg": round(vol_20d_avg, 0),
                    "hold_days": HOLD_DAYS,
                },
                "timestamp": _now_iso(),
            })

            logger.info(
                "%s: Insider proxy — excess %.1f%%, vol_ratio %.2fx, conf=%.3f",
                symbol, excess_return * 100, vol_ratio, confidence,
            )

        except Exception as exc:
            logger.debug("Insider buying error for %s: %s", symbol, exc)
            continue

    logger.info("Insider Buying Proxy: %d signals from %d symbols",
                len(signals), len(universe))
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
    print("Equity Insider Buying Cluster Proxy Strategy")
    print("Lakonishok & Lee (JF 2001)")
    print("=" * 60)

    picks = equity_insider_buying_signals()

    print(f"\nTotal signals: {len(picks)}")
    if picks:
        print(f"{'Symbol':<8} {'Direction':<7} {'Conf':<6} {'ExRet%':>7} {'VolR':>6} {'Price':>10}")
        print("-" * 50)
        for p in picks:
            ex = p.get("extra", {})
            print(
                f"{p['symbol']:<8} {p['direction']:<7} {p['confidence']:<6.2f} "
                f"{ex.get('excess_return_5d_pct', 0):>+7.1f} "
                f"{ex.get('volume_ratio_5d_vs_20d', 0):>6.2f} "
                f"${p['entry_price']:>9.2f}"
            )
    else:
        print("No insider buying proxy signals today.")
