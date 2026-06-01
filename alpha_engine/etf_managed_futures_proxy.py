"""ETF Managed Futures Proxy — liquid-ETF replication of CTA trend-following.

Academic basis: Mulvey & Nadbielny (JPM 2024) — managed futures replication via liquid ETFs.
Logic: Long DBMF, KMLM when 3-month momentum > 0 AND VIX < 25. Rebalance weekly.
Flat (no picks) when VIX >= 25 or momentum <= 0.

Symbols:
  DBMF — iMGP DBi Managed Futures Fund (replicates SG CTA Index)
  KMLM — KFA Mount Lucas Managed Futures Index Strategy ETF

Both are liquid ETFs that track managed-futures / CTA trend-following
indices, providing retail access to the managed-futures asset class
without direct futures account requirements.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "etf_managed_futures_proxy"
SYMBOLS: tuple[str, ...] = ("DBMF", "KMLM")
MOMENTUM_LOOKBACK_DAYS = 63
VIX_FLAT_THRESHOLD = 25.0
CONFIDENCE_BASE = 0.62
CONFIDENCE_STRONG_MOM = 0.70
STRONG_MOM_THRESHOLD = 0.05


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_vix() -> Optional[float]:
    """Fetch latest VIX close via yfinance."""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error("VIX fetch failed: %s", e)
        return None


def _fetch_3m_momentum(symbol: str) -> Optional[float]:
    """Return 3-month (63 trading days) return for *symbol* via yfinance.

    Returns None if data is insufficient or fetch fails.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo")
        if hist.empty or len(hist) < MOMENTUM_LOOKBACK_DAYS + 1:
            logger.warning("Insufficient data for %s (%d rows)", symbol, len(hist))
            return None
        close_now = float(hist["Close"].iloc[-1])
        close_ago = float(hist["Close"].iloc[-(MOMENTUM_LOOKBACK_DAYS + 1)])
        if close_ago <= 0:
            return None
        return (close_now - close_ago) / close_ago
    except Exception as e:
        logger.error("Momentum fetch failed for %s: %s", symbol, e)
        return None


def _fetch_latest_price(symbol: str) -> Optional[float]:
    """Fetch latest close price for *symbol*."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error("Price fetch failed for %s: %s", symbol, e)
        return None


def generate_etf_managed_futures_picks() -> list[dict[str, Any]]:
    """Generate managed-futures proxy picks.

    Returns LONG picks for DBMF / KMLM when:
      - 3-month momentum > 0
      - VIX < 25

    Returns ``[]`` (flat) otherwise.
    """
    vix = _fetch_vix()
    if vix is None:
        logger.warning("Cannot fetch VIX — returning no picks")
        return []

    if vix >= VIX_FLAT_THRESHOLD:
        logger.info("VIX=%.1f >= %.0f: FLAT — no managed-futures picks", vix, VIX_FLAT_THRESHOLD)
        return []

    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in SYMBOLS:
        mom = _fetch_3m_momentum(symbol)
        if mom is None:
            logger.warning("No momentum data for %s — skipping", symbol)
            continue

        if mom <= 0:
            logger.info("%s 3m momentum=%.2f%% <= 0 — skipping", symbol, mom * 100)
            continue

        price = _fetch_latest_price(symbol)
        if price is None:
            logger.warning("No price for %s — skipping", symbol)
            continue

        confidence = CONFIDENCE_STRONG_MOM if mom >= STRONG_MOM_THRESHOLD else CONFIDENCE_BASE

        vix_regime = "LOW" if vix < 15 else "NORMAL" if vix < 20 else "ELEVATED"
        reason = (
            f"3m momentum={mom:+.2%} (>0), VIX={vix:.1f} "
            f"(regime: {vix_regime}), equal-weight allocation"
        )

        picks.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "ETF",
            "category": "managed_futures",
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "reason": reason,
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 720,
                "tp_pct": 5.0,
                "sl_pct": 3.0,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Mulvey & Nadbielny (JPM 2024)",
            "extra": {
                "momentum_3m": round(mom, 4),
                "momentum_3m_pct": round(mom * 100, 2),
                "vix": round(vix, 2),
                "vix_regime": vix_regime,
                "entry_price": round(price, 4),
                "rebalance": "weekly",
                "allocation": "equal_weight",
            },
        })

    logger.info("Generated %d managed-futures picks (VIX=%.1f)", len(picks), vix)
    return picks


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_etf_managed_futures_picks()
    print(json.dumps({"n_picks": len(picks), "picks": picks}, indent=2, default=str))
