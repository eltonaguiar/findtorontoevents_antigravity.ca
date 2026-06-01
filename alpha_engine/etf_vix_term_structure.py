"""ETF VIX Term Structure Signal — Ang et al. (JF 2006).

Academic basis:
  Ang et al. (2006) "The Cross-Section of Volatility and Expected Returns"
  (Journal of Finance). VIX level and term structure predict equity returns:
  high VIX (>25) signals fear regime → defensive rotation into GLD/TLT;
  low VIX (<15) signals complacency → increase equity exposure (SPY/QQQ).

Logic:
  - Fetch VIX (^VIX) and compute 20-day SMA
  - VIX > 25 AND VIX > 20d SMA → fear regime → LONG GLD + TLT (defensive)
  - VIX < 15 → complacency regime → LONG SPY + QQQ (offensive)
  - Neutral band (15 <= VIX <= 25): no signal
  - Exit: VIX crosses back through threshold OR max hold 720h (30 days)

Forced resolution: max_hold_hours=720, tp_pct=5.0, sl_pct=3.0,
time_exit_at_market=True (ETF class default).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "etf_vix_term_structure"
VIX_FEAR_THRESHOLD = 25.0
VIX_COMPLACENCY_THRESHOLD = 15.0
VIX_SMA_PERIOD = 20
DEFENSIVE_UNIVERSE: tuple[str, ...] = ("GLD", "TLT")
OFFENSIVE_UNIVERSE: tuple[str, ...] = ("SPY", "QQQ")
ALL_SYMBOLS: tuple[str, ...] = DEFENSIVE_UNIVERSE + OFFENSIVE_UNIVERSE
CONFIDENCE_BASE_FEAR = 0.65
CONFIDENCE_BASE_CALM = 0.62
CONFIDENCE_CEIL = 0.76


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_vix_data() -> Optional[Any]:
    """Fetch VIX daily closes for the last 3 months."""
    import yfinance as yf
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="3mo")
        if hist.empty or len(hist) < VIX_SMA_PERIOD + 2:
            logger.warning("Insufficient VIX data (%d rows)", len(hist) if hist is not None else 0)
            return None
        return hist
    except Exception as e:
        logger.error("VIX fetch failed: %s", e)
        return None


def _fetch_price_data(symbols: tuple[str, ...]) -> dict[str, Any]:
    """Fetch 3-month OHLCV for given symbols via yfinance."""
    import yfinance as yf

    data: dict[str, Any] = {}
    try:
        raw = yf.download(
            list(symbols), period="3mo", group_by="ticker",
            progress=False, threads=False,
        )
        if raw is None or raw.empty:
            logger.warning("yfinance returned empty data for VIX strategy symbols")
            return data
    except Exception as e:
        logger.error("yfinance download failed: %s", e)
        return data

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
            if df is not None and not df.empty and len(df) >= 20:
                data[symbol] = df.dropna(subset=["Close"])
        except Exception as e:
            logger.warning("Data parse error for %s: %s", symbol, e)

    logger.info("Fetched data for %d/%d VIX strategy symbols", len(data), len(symbols))
    return data


def _analyse_vix(vix_hist) -> dict[str, Any]:
    """Analyse VIX level vs SMA and determine regime.

    Returns dict with vix_close, vix_sma20, regime (FEAR/CALM/NEUTRAL).
    """
    close = vix_hist["Close"]
    vix_close = float(close.iloc[-1])
    vix_sma20 = float(close.iloc[-VIX_SMA_PERIOD:].mean())

    if vix_close > VIX_FEAR_THRESHOLD and vix_close > vix_sma20:
        regime = "FEAR"
    elif vix_close < VIX_COMPLACENCY_THRESHOLD:
        regime = "CALM"
    else:
        regime = "NEUTRAL"

    return {
        "vix_close": vix_close,
        "vix_sma20": vix_sma20,
        "vix_vs_sma": vix_close - vix_sma20,
        "regime": regime,
    }


def generate_vix_term_structure_picks() -> list[dict[str, Any]]:
    """Generate VIX term-structure signal picks.

    When VIX > 25 and rising: LONG GLD + TLT (defensive).
    When VIX < 15: LONG SPY + QQQ (offensive).
    Returns [] in the neutral band or when data is insufficient.
    """
    vix_hist = _fetch_vix_data()
    if vix_hist is None:
        return []

    vix_info = _analyse_vix(vix_hist)
    regime = vix_info["regime"]

    if regime == "NEUTRAL":
        logger.info(
            "VIX=%.1f (SMA20=%.1f) in neutral band [%.0f, %.0f] — no picks",
            vix_info["vix_close"], vix_info["vix_sma20"],
            VIX_COMPLACENCY_THRESHOLD, VIX_FEAR_THRESHOLD,
        )
        return []

    target_symbols = DEFENSIVE_UNIVERSE if regime == "FEAR" else OFFENSIVE_UNIVERSE
    price_data = _fetch_price_data(target_symbols)

    if len(price_data) < len(target_symbols):
        logger.warning(
            "Only %d/%d target symbols available for %s regime",
            len(price_data), len(target_symbols), regime,
        )

    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for symbol in target_symbols:
        df = price_data.get(symbol)
        if df is None or df.empty:
            logger.warning("No price data for %s — skipping", symbol)
            continue

        close = df["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            continue

        if regime == "FEAR":
            vix_excess = vix_info["vix_close"] - VIX_FEAR_THRESHOLD
            confidence = round(
                min(CONFIDENCE_CEIL, CONFIDENCE_BASE_FEAR + min(0.10, vix_excess * 0.01)),
                2,
            )
            direction = "LONG"
            reason = (
                f"VIX Fear Regime: VIX={vix_info['vix_close']:.1f} > {VIX_FEAR_THRESHOLD:.0f} "
                f"AND > SMA20={vix_info['vix_sma20']:.1f} — rotating to defensive "
                f"({symbol}), flight to safety"
            )
        else:
            vix_margin = VIX_COMPLACENCY_THRESHOLD - vix_info["vix_close"]
            confidence = round(
                min(CONFIDENCE_CEIL, CONFIDENCE_BASE_CALM + min(0.12, vix_margin * 0.02)),
                2,
            )
            direction = "LONG"
            reason = (
                f"VIX Complacency Regime: VIX={vix_info['vix_close']:.1f} < {VIX_COMPLACENCY_THRESHOLD:.0f} "
                f"— increasing equity exposure ({symbol}), risk-on"
            )

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "strategy": STRATEGY_NAME,
            "asset_class": "ETF",
            "category": "etf",
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
            "academic_citation": "Ang et al. (JF 2006)",
            "extra": {
                "vix_close": round(vix_info["vix_close"], 2),
                "vix_sma20": round(vix_info["vix_sma20"], 2),
                "vix_vs_sma": round(vix_info["vix_vs_sma"], 2),
                "regime": regime,
                "entry_price": round(price, 4),
                "fear_threshold": VIX_FEAR_THRESHOLD,
                "complacency_threshold": VIX_COMPLACENCY_THRESHOLD,
                "exit_rule": "vix_crosses_back_through_threshold_or_max_hold_720h",
            },
        })

    logger.info(
        "Generated %d VIX picks (VIX=%.1f, regime=%s, symbols=%s)",
        len(picks), vix_info["vix_close"], regime,
        [p["symbol"] for p in picks],
    )
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_vix_term_structure_picks()
    print(json.dumps({"strategy": STRATEGY_NAME, "n_picks": len(picks), "picks": picks}, indent=2, default=str))
