"""Bond Yield Curve Slope Carry — duration positioning via curve slope momentum.

Academic basis: Cochrane & Piazzesi (AER 2005) "Bond Risk Premia".
Logic: Use TLT/SHY relative strength as a proxy for yield curve slope.
When the 60-day momentum of the TLT/SHY ratio is positive, the curve is
steepening (long end outperforming) → LONG TLT. When negative, the curve
is flattening/inverting → LONG SHY.

Universe: TLT (20+ year Treasury), SHY (1-3 year Treasury).

forced_resolution: max_hold_hours=720, tp_pct=2.0, sl_pct=1.0,
time_exit_at_market=True
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_yield_curve_slope"
UNIVERSE: tuple[str, ...] = ("TLT", "SHY")
MOMENTUM_LOOKBACK = 60
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


def generate_bond_yield_curve_slope_picks() -> list[dict[str, Any]]:
    """Generate bond picks from TLT/SHY ratio 60-day momentum.

    Positive momentum → curve steepening → LONG TLT (increase duration).
    Negative momentum → curve flattening → LONG SHY (decrease duration).
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

    if len(tlt_close) < MOMENTUM_LOOKBACK + 5 or len(shy_close) < MOMENTUM_LOOKBACK + 5:
        logger.warning("Insufficient data: TLT=%d, SHY=%d bars", len(tlt_close), len(shy_close))
        return picks

    # Align on common index
    common_idx = tlt_close.index.intersection(shy_close.index)
    if len(common_idx) < MOMENTUM_LOOKBACK + 5:
        logger.warning("Insufficient overlapping bars: %d", len(common_idx))
        return picks
    tlt_aligned = tlt_close.reindex(common_idx).dropna()
    shy_aligned = shy_close.reindex(common_idx).dropna()

    # Re-align after dropna
    common_idx2 = tlt_aligned.index.intersection(shy_aligned.index)
    if len(common_idx2) < MOMENTUM_LOOKBACK + 5:
        logger.warning("Insufficient clean overlapping bars: %d", len(common_idx2))
        return picks
    tlt_aligned = tlt_aligned.reindex(common_idx2)
    shy_aligned = shy_aligned.reindex(common_idx2)

    ratio = tlt_aligned / shy_aligned
    ratio = ratio.dropna()
    if len(ratio) < MOMENTUM_LOOKBACK + 1:
        logger.warning("Insufficient ratio data: %d bars", len(ratio))
        return picks

    # 60-day momentum of the ratio
    current_ratio = float(ratio.iloc[-1])
    past_ratio = float(ratio.iloc[-(MOMENTUM_LOOKBACK + 1)])
    if past_ratio <= 0:
        logger.warning("Past ratio <= 0, cannot compute momentum")
        return picks

    ratio_momentum = (current_ratio - past_ratio) / past_ratio
    logger.info("TLT/SHY ratio 60d momentum: %.4f%%", ratio_momentum * 100)

    direction: Optional[str] = None
    symbol: Optional[str] = None
    reason: str = ""

    if ratio_momentum > 0:
        direction = "LONG"
        symbol = "TLT"
        reason = (
            f"TLT/SHY ratio 60d momentum={ratio_momentum:+.2%} (>0) — curve steepening, "
            f"long duration. Cochrane & Piazzesi (AER 2005)"
        )
    else:
        direction = "LONG"
        symbol = "SHY"
        reason = (
            f"TLT/SHY ratio 60d momentum={ratio_momentum:+.2%} (<0) — curve flattening, "
            f"short duration. Cochrane & Piazzesi (AER 2005)"
        )

    hist_target = tlt_hist if symbol == "TLT" else shy_hist
    price = float(_close_series(hist_target).iloc[-1])
    confidence = round(min(0.75, 0.55 + min(abs(ratio_momentum), 0.10) * 2.0), 2)

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
        "academic_citation": "Cochrane & Piazzesi (AER 2005)",
        "extra": {
            "tlt_shy_ratio": round(current_ratio, 6),
            "tlt_shy_ratio_60d_ago": round(past_ratio, 6),
            "ratio_momentum_60d": round(ratio_momentum, 4),
            "ratio_momentum_60d_pct": round(ratio_momentum * 100, 2),
            "entry_price": round(price, 4),
            "momentum_lookback": MOMENTUM_LOOKBACK,
            "exit_rule": "momentum flip or max_hold 720h",
        },
    })

    logger.info(
        "%s %s: ratio_mom=%.3f%%, price=%.4f, confidence=%.2f",
        direction, symbol, ratio_momentum * 100, price, confidence,
    )
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_bond_yield_curve_slope_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
