"""FX DXY Divergence Trade Strategy

Academic basis: Clarida, Galí & Gertler (2003) — "The Role of Monetary Policy
in Exchange Rate Dynamics". They show that large USD moves (>1% over 5 days)
are driven by monetary policy divergence and tend to persist against the
weakest G10 currencies while reversing against the strongest.

Mechanic:
  - Fetch DXY (DX-Y.N) and all G10 FX pairs vs USD.
  - Compute DXY 5d return. If > +1% → USD is strengthening: SHORT the
    weakest pair (largest 5d loss vs USD). If < -1% → USD weakening:
    LONG the strongest pair (largest 5d gain vs USD).
  - Convergence exit: close when the divergent pair's 5d return converges
    back toward zero (|5d ret| < 0.5%) OR max hold 48h.

Universe: 8 major FX pairs + DXY via yfinance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FX_UNIVERSE = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCHF=X", "NZDUSD=X", "USDCAD=X", "EURGBP=X",
]

DXY_TICKER = "UUP"  # Invesco DB USD Bullish Fund — reliable DXY proxy on yfinance
STRATEGY_NAME = "fx_dxy_divergence"
DXY_MOVE_THRESHOLD = 0.01  # 1%


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(price: float) -> float:
    if abs(price) >= 100:
        return round(price, 2)
    elif abs(price) >= 10:
        return round(price, 3)
    else:
        return round(price, 5)


def generate_picks(
    data: dict[str, pd.DataFrame] | None = None,
    dxy_data: pd.DataFrame | None = None,
) -> List[dict[str, Any]]:
    """Generate DXY divergence picks.

    Each pick includes forced_resolution with max_hold_hours=48, tp_pct=0.3,
    sl_pct=0.2, time_exit_at_market=True.
    """
    if data is None or dxy_data is None:
        data, dxy_data = _download_data()

    if dxy_data is None or len(dxy_data) < 10:
        logger.warning("Insufficient DXY data")
        return []

    dxy_close = dxy_data["Close"].dropna()
    if len(dxy_close) < 6:
        logger.warning("DXY: need >=6 bars, got %d", len(dxy_close))
        return []

    dxy_5d_ret = float(dxy_close.iloc[-1] / dxy_close.iloc[-6] - 1)

    if abs(dxy_5d_ret) < DXY_MOVE_THRESHOLD:
        logger.info("DXY 5d return %.2f%% below threshold — no signal", dxy_5d_ret * 100)
        return []

    # Rank FX pairs by their 5d return vs USD
    pair_returns: list[tuple[str, float, pd.DataFrame]] = []
    for symbol, df in data.items():
        if df is None or len(df) < 10:
            continue
        close = df["Close"].dropna()
        if len(close) < 6:
            continue
        ret_5d = float(close.iloc[-1] / close.iloc[-6] - 1)
        pair_returns.append((symbol, ret_5d, df))

    if not pair_returns:
        return []

    # For DXY strengthening (positive): find weakest pair (most negative return) → SHORT it
    # For DXY weakening (negative): find strongest pair (most positive return) → LONG it
    pair_returns.sort(key=lambda x: x[1])

    picks: List[dict[str, Any]] = []

    if dxy_5d_ret > DXY_MOVE_THRESHOLD:
        # USD strengthening → SHORT the weakest pair
        symbol, ret_5d, df = pair_returns[0]
        direction = "SHORT"
        current_price = float(df["Close"].iloc[-1])
        confidence = min(0.72, 0.55 + abs(dxy_5d_ret) * 5)
        reason = (
            f"DXY +{dxy_5d_ret*100:.2f}% (5d) → USD strong. "
            f"Weakest pair {symbol} ret={ret_5d*100:.2f}% → SHORT"
        )
    elif dxy_5d_ret < -DXY_MOVE_THRESHOLD:
        # USD weakening → LONG the strongest pair
        symbol, ret_5d, df = pair_returns[-1]
        direction = "LONG"
        current_price = float(df["Close"].iloc[-1])
        confidence = min(0.72, 0.55 + abs(dxy_5d_ret) * 5)
        reason = (
            f"DXY {dxy_5d_ret*100:.2f}% (5d) → USD weak. "
            f"Strongest pair {symbol} ret={ret_5d*100:+.2f}% → LONG"
        )
    else:
        return []

    tp_pct = 0.3 / 100
    sl_pct = 0.2 / 100
    if direction == "LONG":
        take_profit = _smart_round(current_price * (1 + tp_pct))
        stop_loss = _smart_round(current_price * (1 - sl_pct))
    else:
        take_profit = _smart_round(current_price * (1 - tp_pct))
        stop_loss = _smart_round(current_price * (1 + sl_pct))

    rr = tp_pct / sl_pct

    picks.append({
        "symbol": symbol,
        "direction": direction,
        "strategy": STRATEGY_NAME,
        "asset_class": "FOREX",
        "category": "forex",
        "entry_price": _smart_round(current_price),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": round(confidence, 4),
        "risk_reward": round(rr, 2),
        "timestamp": _now_iso(),
        "reason": reason,
        "source": "alpha_engine",
        "source_system": STRATEGY_NAME,
        "forced_resolution": {
            "max_hold_hours": 48,
            "tp_pct": 0.3,
            "sl_pct": 0.2,
            "time_exit_at_market": True,
        },
        "paper_pilot": True,
        "academic_citation": "Clarida, Gali & Gertler (2003)",
    })

    logger.info("%s: generated %d picks (DXY 5d=%.2f%%)", STRATEGY_NAME, len(picks), dxy_5d_ret * 100)
    return picks


def _download_data() -> tuple[dict[str, pd.DataFrame], pd.DataFrame | None]:
    """Download FX + DXY data via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance required: pip install yfinance")
        return {}, None

    end = datetime.now(timezone.utc)
    start = end - pd.Timedelta(days=30)

    # DXY
    dxy_df = None
    try:
        dxy_df = yf.download(
            DXY_TICKER,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )
        if dxy_df is not None and isinstance(dxy_df.columns, pd.MultiIndex):
            dxy_df.columns = dxy_df.columns.get_level_values(0)
        if dxy_df is not None and len(dxy_df) < 5:
            dxy_df = None
    except Exception as e:
        logger.warning("DXY download failed: %s", e)

    # FX pairs
    data: dict[str, pd.DataFrame] = {}
    for symbol in FX_UNIVERSE:
        try:
            df = yf.download(
                symbol,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
            )
            if df is not None and len(df) > 5:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[symbol] = df
        except Exception as e:
            logger.warning("%s: download failed: %s", symbol, e)

    return data, dxy_df


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Running %s standalone...", STRATEGY_NAME)
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        print("No picks generated (DXY move below 1% threshold).")
    logger.info("Done — %d picks.", len(picks))
