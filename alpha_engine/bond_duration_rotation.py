"""Bond Duration Rotation — duration timing via relative momentum.

Academic basis: Ilmanen (2011) "Expected Returns", Ch. 15 on duration timing.
Logic: When TLT (long duration) 1-month return exceeds SHY (short duration),
the yield curve is steepening / rates falling → increase duration by going
LONG TLT. When SHY outperforms TLT, rates rising / curve flattening →
decrease duration by going LONG SHY. Monthly rebalance cadence.

Universe: TLT (20+ year Treasury), SHY (1-3 year Treasury).

forced_resolution: max_hold_hours=720, tp_pct=2.0, sl_pct=1.0,
time_exit_at_market=True
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_duration_rotation"
UNIVERSE: tuple[str, ...] = ("TLT", "SHY")
RETURN_LOOKBACK = 21  # ~1 month of trading days
ANNUALIZATION_FACTOR = 252


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_history(symbol: str, period: str = "1y") -> Optional[Any]:
    """Return yfinance DataFrame for *symbol* or None on failure."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval="1d")
        if hist is None or hist.empty:
            logger.warning("Empty history for %s", symbol)
            return None
        return hist
    except Exception as e:
        logger.error("yfinance fetch failed for %s: %s", symbol, e)
        return None


def _close_series(hist: Any) -> Any:
    """Extract a single-column Close Series from yfinance DataFrame."""
    close = hist["Close"]
    if hasattr(close, "iloc") and hasattr(close, "shape") and len(getattr(close, "shape", ())) > 1:
        close = close.iloc[:, 0]
    return close.squeeze()


def _compute_return(close: Any, lookback: int) -> Optional[float]:
    """Return lookback-day return (current / close[lookback] - 1)."""
    try:
        if len(close) < lookback + 1:
            return None
        cur = float(close.iloc[-1])
        past = float(close.iloc[-(lookback + 1)])
        if past <= 0:
            return None
        return (cur - past) / past
    except Exception:
        return None


def generate_bond_duration_rotation_picks() -> list[dict[str, Any]]:
    """Generate bond picks from TLT vs SHY 1-month relative momentum.

    TLT 1m return > SHY 1m return → LONG TLT (increase duration).
    SHY 1m return > TLT 1m return → LONG SHY (decrease duration).
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    tlt_hist = _fetch_history("TLT", period="1y")
    shy_hist = _fetch_history("SHY", period="1y")
    if tlt_hist is None or shy_hist is None:
        logger.warning("Could not fetch TLT or SHY data")
        return picks

    tlt_close = _close_series(tlt_hist)
    shy_close = _close_series(shy_hist)

    if len(tlt_close) < RETURN_LOOKBACK + 2 or len(shy_close) < RETURN_LOOKBACK + 2:
        logger.warning("Insufficient data: TLT=%d, SHY=%d bars", len(tlt_close), len(shy_close))
        return picks

    tlt_ret = _compute_return(tlt_close, RETURN_LOOKBACK)
    shy_ret = _compute_return(shy_close, RETURN_LOOKBACK)
    if tlt_ret is None or shy_ret is None:
        logger.warning("Could not compute returns")
        return picks

    logger.info("TLT 1m return: %.3f%%, SHY 1m return: %.3f%%", tlt_ret * 100, shy_ret * 100)

    direction: Optional[str] = None
    symbol: Optional[str] = None
    reason: str = ""
    entry_price: float = 0.0

    if tlt_ret > shy_ret:
        direction = "LONG"
        symbol = "TLT"
        entry_price = float(tlt_close.iloc[-1])
        spread = tlt_ret - shy_ret
        reason = (
            f"TLT 1m return ({tlt_ret:+.2%}) > SHY ({shy_ret:+.2%}), "
            f"spread={spread:+.2%} — duration extension signal (rates falling). "
            f"Ilmanen (2011) Expected Returns"
        )
    else:
        direction = "LONG"
        symbol = "SHY"
        entry_price = float(shy_close.iloc[-1])
        spread = shy_ret - tlt_ret
        reason = (
            f"SHY 1m return ({shy_ret:+.2%}) > TLT ({tlt_ret:+.2%}), "
            f"spread={spread:+.2%} — duration compression signal (rates rising). "
            f"Ilmanen (2011) Expected Returns"
        )

    abs_spread = abs(tlt_ret - shy_ret)
    confidence = round(min(0.75, 0.55 + min(abs_spread, 0.05) * 4.0), 2)

    picks.append({
        "symbol": symbol,
        "direction": direction,
        "strategy": STRATEGY_NAME,
        "asset_class": "BOND",
        "category": "bond",
        "confidence": confidence,
        "generated_at": now.isoformat(),
        "reason": reason,
        "source": "alpha_engine",
        "source_system": STRATEGY_NAME,
        "forced_resolution": {
            "max_hold_hours": 720,
            "tp_pct": 2.0,
            "sl_pct": 1.0,
            "time_exit_at_market": True,
        },
        "paper_pilot": True,
        "academic_citation": "Ilmanen (2011) Expected Returns",
        "extra": {
            "tlt_return_1m": round(tlt_ret, 4),
            "shy_return_1m": round(shy_ret, 4),
            "return_spread": round(tlt_ret - shy_ret, 4),
            "entry_price": round(entry_price, 4),
            "lookback_days": RETURN_LOOKBACK,
            "rebalance_cadence": "monthly",
            "exit_rule": "flip signal or max_hold 720h",
        },
    })

    logger.info(
        "%s %s: TLT_ret=%.3f%%, SHY_ret=%.3f%%, spread=%.3f%%, confidence=%.2f",
        direction, symbol, tlt_ret * 100, shy_ret * 100, abs_spread * 100, confidence,
    )
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_bond_duration_rotation_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
