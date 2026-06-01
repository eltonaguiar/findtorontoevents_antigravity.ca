"""Bond Credit Spread Mean Reversion — HYG-TLT spread z-score trading.

Academic basis: Bessembinder, Kahle, Maxwell & Xu (JFE 2009) "Measuring
abnormal bond performance".
Logic: HYG/TLT ratio as credit risk proxy. When the ratio z-score exceeds
+2σ above its 60-day mean, credit is overextended → expect compression →
LONG HYG. When z-score < -2, credit is oversold → LONG TLT (flight to
quality). Exit when z-score reverts to 0 or max hold 720h.

Universe: HYG (high-yield corp), TLT (20+ year Treasury).

forced_resolution: max_hold_hours=720, tp_pct=2.0, sl_pct=1.0,
time_exit_at_market=True
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_credit_spread"
UNIVERSE: tuple[str, ...] = ("HYG", "TLT")
LOOKBACK = 60
ZSCORE_ENTRY = 2.0
ZSCORE_EXIT = 0.0
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


def generate_bond_credit_spread_picks() -> list[dict[str, Any]]:
    """Generate bond picks from HYG/TLT ratio z-score.

    When z-score > +2: credit overextended → LONG HYG (spread compression).
    When z-score < -2: credit oversold → LONG TLT (flight to quality).
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    hyg_hist = _fetch_history("HYG", period="1y")
    tlt_hist = _fetch_history("TLT", period="1y")
    if hyg_hist is None or tlt_hist is None:
        logger.warning("Could not fetch HYG or TLT data")
        return picks

    hyg_close = _close_series(hyg_hist)
    tlt_close = _close_series(tlt_hist)

    if len(hyg_close) < LOOKBACK + 5 or len(tlt_close) < LOOKBACK + 5:
        logger.warning("Insufficient data: HYG=%d, TLT=%d bars", len(hyg_close), len(tlt_close))
        return picks

    # Align on common index
    common_idx = hyg_close.index.intersection(tlt_close.index)
    if len(common_idx) < LOOKBACK + 5:
        logger.warning("Insufficient overlapping bars: %d", len(common_idx))
        return picks
    hyg_aligned = hyg_close.reindex(common_idx)
    tlt_aligned = tlt_close.reindex(common_idx)

    ratio = hyg_aligned / tlt_aligned
    ratio = ratio.dropna()
    if len(ratio) < LOOKBACK + 1:
        logger.warning("Insufficient ratio data: %d bars", len(ratio))
        return picks

    ratio_mean = ratio.rolling(LOOKBACK).mean()
    ratio_std = ratio.rolling(LOOKBACK).std()

    z_now = float((ratio.iloc[-1] - ratio_mean.iloc[-1]) / ratio_std.iloc[-1]) if ratio_std.iloc[-1] > 0 else 0.0
    logger.info("HYG/TLT ratio z-score (60d): %.3f", z_now)

    direction: Optional[str] = None
    symbol: Optional[str] = None
    reason: str = ""

    if z_now > ZSCORE_ENTRY:
        direction = "LONG"
        symbol = "HYG"
        reason = (
            f"HYG/TLT ratio z-score={z_now:.2f} (>+{ZSCORE_ENTRY}) — credit overextended, "
            f"expect spread compression. Bessembinder et al. (JFE 2009)"
        )
    elif z_now < -ZSCORE_ENTRY:
        direction = "LONG"
        symbol = "TLT"
        reason = (
            f"HYG/TLT ratio z-score={z_now:.2f} (<-{ZSCORE_ENTRY}) — credit oversold, "
            f"flight to quality. Bessembinder et al. (JFE 2009)"
        )

    if direction is None:
        logger.info("Z-score %.3f within ±%.1f band — no signal", z_now, ZSCORE_ENTRY)
        return picks

    hist_target = hyg_hist if symbol == "HYG" else tlt_hist
    price = float(_close_series(hist_target).iloc[-1])
    confidence = round(min(0.75, 0.55 + min(abs(z_now) - ZSCORE_ENTRY, 2.0) * 0.10), 2)

    picks.append({
        "symbol": symbol,
        "direction": direction,
        "strategy": STRATEGY_NAME,
        "asset_class": "BOND",
        "category": "bond",
        "entry_price": round(price, 4),
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
        "academic_citation": "Bessembinder, Kahle, Maxwell & Xu (JFE 2009)",
        "extra": {
            "hyg_tlt_zscore": round(z_now, 4),
            "hyg_tlt_ratio": round(float(ratio.iloc[-1]), 6),
            "ratio_mean_60d": round(float(ratio_mean.iloc[-1]), 6),
            "ratio_std_60d": round(float(ratio_std.iloc[-1]), 6),
            "entry_price": round(price, 4),
            "lookback": LOOKBACK,
            "zscore_entry_threshold": ZSCORE_ENTRY,
            "exit_rule": f"z-score reverts to {ZSCORE_EXIT} or max_hold 720h",
        },
    })

    logger.info(
        "%s %s: z=%.3f, price=%.4f, confidence=%.2f",
        direction, symbol, z_now, price, confidence,
    )
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_bond_credit_spread_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
