"""
Equity Short Squeeze Signal Strategy
=====================================
Academic basis: Boehmer, Jones & Zhang (JFE 2021).
Edge: Stocks with extreme short interest experience violent short-covering
rallies when momentum triggers. We proxy this with a triple filter:
sharp price increase + volume explosion + RSI > 70 (momentum confirmation).

This is a MOMENTUM RIDING strategy — not value. High risk, high reward.
The RSI < 50 exit is aggressive: we bail as soon as momentum fades.

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
SQUEEZE_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "UNH", "JNJ", "PG", "MA", "HD", "CRM", "KO", "PEP",
    "AVGO", "LLY", "COST",
]

MIN_RETURN_3D = 0.08       # +8% over 3 days
MIN_VOLUME_RATIO = 3.0     # volume >= 3x 20-day avg
RSI_PERIOD = 14
RSI_MIN = 70               # RSI > 70 = overbought momentum
RSI_EXIT = 50              # exit when RSI drops below 50
TP_PCT = 0.03              # 3% take-profit
SL_PCT = 0.02              # 2% stop-loss
MAX_HOLD_HOURS = 72        # short hold — momentum rides are fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_rsi(close: Any, period: int = 14) -> Any:
    """Compute RSI using pandas. Returns Series."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _fetch_ohlcv(symbol: str, period: str = "3mo") -> Any:
    """Fetch OHLCV via yfinance. Returns DataFrame or None."""
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
def equity_short_squeeze_signals(
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate short squeeze momentum LONG signals.

    Entry conditions (all must be true):
      1. 3-day return > +8%
      2. Current volume >= 3x 20-day average
      3. RSI(14) > 70 (momentum confirmation)

    Exit: RSI < 50 OR max hold 72h.

    Returns:
        List of pick dicts with all standard Alpha Engine fields.
    """
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed — cannot run equity_short_squeeze")
        return []

    universe = symbols or SQUEEZE_UNIVERSE
    signals: list[dict[str, Any]] = []

    logger.info("Short Squeeze: scanning %d symbols for squeeze signals", len(universe))

    for symbol in universe:
        try:
            hist = _fetch_ohlcv(symbol, period="3mo")
            if hist is None:
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            if len(close) < 21 or len(volume) < 21:
                continue

            current_price = float(close.iloc[-1])
            if current_price <= 0:
                continue

            # Condition 1: 3-day return > 8%
            ret_3d = float(close.iloc[-1] / close.iloc[-4] - 1)
            if ret_3d < MIN_RETURN_3D:
                logger.debug("%s: 3d return %.2f%% < %.2f%%",
                             symbol, ret_3d * 100, MIN_RETURN_3D * 100)
                continue

            # Condition 2: volume >= 3x 20-day average
            vol_today = float(volume.iloc[-1])
            vol_20d_avg = float(volume.iloc[-20:].mean())
            if vol_20d_avg <= 0:
                continue
            vol_ratio = vol_today / vol_20d_avg

            if vol_ratio < MIN_VOLUME_RATIO:
                logger.debug("%s: vol_ratio %.2f < %.2f",
                             symbol, vol_ratio, MIN_VOLUME_RATIO)
                continue

            # Condition 3: RSI(14) > 70
            rsi_series = _compute_rsi(close, RSI_PERIOD)
            rsi_val = float(rsi_series.iloc[-1])
            if np.isnan(rsi_val) or rsi_val < RSI_MIN:
                logger.debug("%s: RSI %.1f < %d", symbol, rsi_val, RSI_MIN)
                continue

            # All conditions met — squeeze signal
            # Confidence scales with return magnitude and volume explosion
            ret_bonus = min((ret_3d - MIN_RETURN_3D) * 1.5, 0.12)
            vol_bonus = min((vol_ratio - MIN_VOLUME_RATIO) * 0.02, 0.08)
            rsi_bonus = min((rsi_val - RSI_MIN) / 100.0, 0.04)
            confidence = min(0.82, 0.55 + ret_bonus + vol_bonus + rsi_bonus)

            tp = round(current_price * (1 + TP_PCT), 4)
            sl = round(current_price * (1 - SL_PCT), 4)

            signals.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": "equity_short_squeeze",
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
                    f"Short squeeze proxy: 3d return {ret_3d * 100:+.1f}% (>8%), "
                    f"volume {vol_ratio:.1f}x 20d avg (>3x), "
                    f"RSI(14)={rsi_val:.0f} (>70). "
                    f"Momentum riding — high risk/high reward."
                ),
                "source": "alpha_engine",
                "source_system": "equity_short_squeeze",
                "forced_resolution": {
                    "max_hold_hours": MAX_HOLD_HOURS,
                    "tp_pct": TP_PCT * 100,
                    "sl_pct": SL_PCT * 100,
                    "time_exit_at_market": True,
                },
                "paper_pilot": True,
                "academic_citation": "Boehmer, Jones & Zhang (JFE 2021)",
                "extra": {
                    "return_3d_pct": round(ret_3d * 100, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "rsi_14": round(rsi_val, 1),
                    "rsi_exit_threshold": RSI_EXIT,
                    "hold_days": MAX_HOLD_HOURS // 24,
                },
                "timestamp": _now_iso(),
            })

            logger.info(
                "%s: SQUEEZE — 3d %.1f%%, vol %.1fx, RSI %.0f, conf=%.3f",
                symbol, ret_3d * 100, vol_ratio, rsi_val, confidence,
            )

        except Exception as exc:
            logger.debug("Short squeeze error for %s: %s", symbol, exc)
            continue

    logger.info("Short Squeeze: %d signals from %d symbols", len(signals), len(universe))
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
    print("Equity Short Squeeze Signal Strategy")
    print("Boehmer, Jones & Zhang (JFE 2021)")
    print("=" * 60)

    picks = equity_short_squeeze_signals()

    print(f"\nTotal signals: {len(picks)}")
    if picks:
        print(f"{'Symbol':<8} {'Direction':<7} {'Conf':<6} {'3dRet%':>7} {'VolX':>6} {'RSI':>5} {'Price':>10}")
        print("-" * 55)
        for p in picks:
            ex = p.get("extra", {})
            print(
                f"{p['symbol']:<8} {p['direction']:<7} {p['confidence']:<6.2f} "
                f"{ex.get('return_3d_pct', 0):>+7.1f} "
                f"{ex.get('volume_ratio', 0):>6.1f} "
                f"{ex.get('rsi_14', 0):>5.0f} "
                f"${p['entry_price']:>9.2f}"
            )
    else:
        print("No short squeeze signals today (no triple-filter matches).")
