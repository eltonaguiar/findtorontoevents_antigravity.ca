"""Bond TLT Trend Vol Scaled — time-series momentum on TLT with inverse-vol sizing.

Academic basis: Asness, Moskowitz & Pedersen (JF 2013) "Value & Momentum Everywhere".
Logic: 60-day tsmom × 1/realized_vol scaling on TLT (and fallbacks IEF, AGG).
Long when 60-day return > 0; position weight inversely proportional to 20-day
realized volatility (annualized).  If TLT momentum ≤ 0, scan IEF then AGG.

Symbols:
  TLT — iShares 20+ Year Treasury Bond ETF  (primary, long-duration)
  IEF — iShares 7-10 Year Treasury Bond ETF  (intermediate-duration fallback)
  AGG — iShares Core US Aggregate Bond ETF   (broad-aggregate fallback)

forced_resolution: max_hold_hours=720 (30 days), tp_pct=3.0, sl_pct=2.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_tlt_trend_vol_scaled"
UNIVERSE: tuple[str, ...] = ("TLT", "IEF", "AGG")
MOMENTUM_LOOKBACK = 60
VOL_WINDOW = 20
ANNUALIZATION_FACTOR = 252
CONFIDENCE_BASE = 0.60
CONFIDENCE_STRONG_MOM = 0.70
STRONG_MOM_THRESHOLD = 0.03


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


def _compute_momentum(close: Any, lookback: int = MOMENTUM_LOOKBACK) -> Optional[float]:
    """Return *lookback*-day return (current / close[lookback] - 1)."""
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


def _compute_realized_vol(daily_returns: Any, window: int = VOL_WINDOW) -> Optional[float]:
    """Return annualized realized volatility (std of last *window* daily returns × √252)."""
    try:
        if len(daily_returns) < window:
            return None
        recent = daily_returns.iloc[-window:]
        std = float(recent.std())
        return std * (ANNUALIZATION_FACTOR ** 0.5)
    except Exception:
        return None


def generate_bond_tlt_trend_vol_picks() -> list[dict[str, Any]]:
    """Generate bond trend-following picks with inverse-vol position sizing.

    Scans TLT → IEF → AGG in order.  First symbol with 60-day momentum > 0
    becomes the pick.  Position weight = 1 / realized_vol (capped).

    Returns ``[]`` if no bond ETF has positive momentum.
    """
    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in UNIVERSE:
        hist = _fetch_history(symbol, period="1y")
        if hist is None:
            continue

        close = hist["Close"]
        if isinstance(close, type(hist)):
            close = close.iloc[:, 0]
        close = close.squeeze()

        mom = _compute_momentum(close, MOMENTUM_LOOKBACK)
        if mom is None:
            logger.warning("Insufficient data for %s momentum", symbol)
            continue

        daily_ret = close.pct_change().dropna()
        vol = _compute_realized_vol(daily_ret, VOL_WINDOW)
        if vol is None or vol <= 0:
            logger.warning("Insufficient data for %s vol", symbol)
            continue

        inv_vol_weight = 1.0 / vol
        inv_vol_weight = min(max(inv_vol_weight, 0.2), 5.0)

        if mom <= 0:
            logger.info("%s 60d momentum=%.2f%% <= 0 — skipping", symbol, mom * 100)
            continue

        price = float(close.iloc[-1])
        confidence = CONFIDENCE_STRONG_MOM if mom >= STRONG_MOM_THRESHOLD else CONFIDENCE_BASE

        reason = (
            f"60d tsmom={mom:+.2%} (>0), 20d real_vol={vol:.2%}, "
            f"inv_vol_weight={inv_vol_weight:.2f}x, academic: "
            f"Asness-Moskowitz-Pedersen (JF 2013)"
        )

        picks.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "ETF",
            "category": "bond",
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "reason": reason,
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 720,
                "tp_pct": 3.0,
                "sl_pct": 2.0,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Asness-Moskowitz-Pedersen (JF 2013)",
            "extra": {
                "momentum_60d": round(mom, 4),
                "momentum_60d_pct": round(mom * 100, 2),
                "realized_vol_20d": round(vol, 4),
                "realized_vol_20d_pct": round(vol * 100, 2),
                "inv_vol_weight": round(inv_vol_weight, 4),
                "entry_price": round(price, 4),
                "momentum_lookback": MOMENTUM_LOOKBACK,
                "vol_window": VOL_WINDOW,
            },
        })

        logger.info(
            "LONG %s: 60d mom=%.2f%%, vol=%.2f%%, weight=%.2fx",
            symbol, mom * 100, vol * 100, inv_vol_weight,
        )
        break

    if not picks:
        logger.info("No bond ETF with positive 60d momentum — FLAT")

    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_bond_tlt_trend_vol_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
