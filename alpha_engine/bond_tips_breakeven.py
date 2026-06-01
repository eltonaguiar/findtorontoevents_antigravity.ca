"""Bond TIPS Breakeven Timing — inflation expectations via TIP vs TLT relative strength.

Academic basis: Gürkaynak, Sack & Wright (JBF 2010) "The TIPS Yield Curve
and Inflation Compensation".
Logic: When TIP (TIPS ETF) 3-month return exceeds TLT (nominal Treasury),
inflation expectations are rising → overweight TIP. When TLT outperforms
TIP, deflation fears / falling breakevens → overweight TLT.

Universe: TIP (iShares TIPS Bond ETF), TLT (20+ year Treasury).

forced_resolution: max_hold_hours=720, tp_pct=2.0, sl_pct=1.0,
time_exit_at_market=True
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_tips_breakeven"
UNIVERSE: tuple[str, ...] = ("TIP", "TLT")
RETURN_LOOKBACK = 63  # ~3 months of trading days
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


def generate_bond_tips_breakeven_picks() -> list[dict[str, Any]]:
    """Generate bond picks from TIP vs TLT 3-month relative strength.

    TIP 3m return > TLT 3m return → LONG TIP (inflation expectations rising).
    TLT 3m return > TIP 3m return → LONG TLT (deflation fears / falling breakevens).
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    tip_hist = _fetch_history("TIP", period="1y")
    tlt_hist = _fetch_history("TLT", period="1y")
    if tip_hist is None or tlt_hist is None:
        logger.warning("Could not fetch TIP or TLT data")
        return picks

    tip_close = _close_series(tip_hist)
    tlt_close = _close_series(tlt_hist)

    if len(tip_close) < RETURN_LOOKBACK + 2 or len(tlt_close) < RETURN_LOOKBACK + 2:
        logger.warning("Insufficient data: TIP=%d, TLT=%d bars", len(tip_close), len(tlt_close))
        return picks

    tip_ret = _compute_return(tip_close, RETURN_LOOKBACK)
    tlt_ret = _compute_return(tlt_close, RETURN_LOOKBACK)
    if tip_ret is None or tlt_ret is None:
        logger.warning("Could not compute returns")
        return picks

    logger.info("TIP 3m return: %.3f%%, TLT 3m return: %.3f%%", tip_ret * 100, tlt_ret * 100)

    direction: Optional[str] = None
    symbol: Optional[str] = None
    reason: str = ""
    entry_price: float = 0.0

    if tip_ret > tlt_ret:
        direction = "LONG"
        symbol = "TIP"
        entry_price = float(tip_close.iloc[-1])
        spread = tip_ret - tlt_ret
        reason = (
            f"TIP 3m return ({tip_ret:+.2%}) > TLT ({tlt_ret:+.2%}), "
            f"spread={spread:+.2%} — inflation expectations rising, overweight TIPS. "
            f"Gürkaynak, Sack & Wright (JBF 2010)"
        )
    else:
        direction = "LONG"
        symbol = "TLT"
        entry_price = float(tlt_close.iloc[-1])
        spread = tlt_ret - tip_ret
        reason = (
            f"TLT 3m return ({tlt_ret:+.2%}) > TIP ({tip_ret:+.2%}), "
            f"spread={spread:+.2%} — deflation fears / falling breakevens, overweight nominals. "
            f"Gürkaynak, Sack & Wright (JBF 2010)"
        )

    abs_spread = abs(tip_ret - tlt_ret)
    confidence = round(min(0.75, 0.55 + min(abs_spread, 0.06) * 3.33), 2)

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
        "academic_citation": "Gürkaynak, Sack & Wright (JBF 2010)",
        "extra": {
            "tip_return_3m": round(tip_ret, 4),
            "tlt_return_3m": round(tlt_ret, 4),
            "return_spread": round(tip_ret - tlt_ret, 4),
            "entry_price": round(entry_price, 4),
            "lookback_days": RETURN_LOOKBACK,
            "exit_rule": "relative strength flip or max_hold 720h",
        },
    })

    logger.info(
        "%s %s: TIP_ret=%.3f%%, TLT_ret=%.3f%%, spread=%.3f%%, confidence=%.2f",
        direction, symbol, tip_ret * 100, tlt_ret * 100, abs_spread * 100, confidence,
    )
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_bond_tips_breakeven_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
