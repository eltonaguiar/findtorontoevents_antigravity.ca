"""Meme Stock Momentum Squeeze — prototype for MEME asset class.

Targets: highly shorted small-cap names with abnormal social-volume spikes
and gamma-exposure clustering (proxy: price-volume breakouts on no news).

Paper-pilot only until n≥500 clean resolved + institutional backtest pass.
Academic basis: Boehmer et al. (JFE 2021) on short squeeze predictability;
Lakonishok et al. (JF 1992) on institutional herding.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Proxy universe — highly retail-traded names (expandable)
_MEME_UNIVERSE = [
    "GME", "AMC", "BBBY", "BB", "PLTR", "RIVN", "LCID", "NKLA",
    "MULN", "HLBZ", "TTOO", "GOEV", "DNA", "SOFI", "HOOD",
]


def _fetch_snapshot(tickers: list[str]) -> pd.DataFrame:
    """Fetch last-5d OHLCV for meme universe via yfinance."""
    rows = []
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d", interval="1d")
            if len(hist) >= 2:
                prev = hist.iloc[-2]
                last = hist.iloc[-1]
                rows.append({
                    "symbol": t,
                    "close": float(last["Close"]),
                    "prev_close": float(prev["Close"]),
                    "volume": float(last["Volume"]),
                    "vol_avg_5d": float(hist["Volume"].mean()),
                    "high_5d": float(hist["High"].max()),
                    "low_5d": float(hist["Low"].min()),
                })
        except Exception as e:
            logger.debug("%s fetch failed: %s", t, e)
    return pd.DataFrame(rows)


def generate_meme_momentum_squeeze_picks(
    min_volume_surge: float = 2.0,
    min_price_change: float = 0.05,
    max_market_cap_proxy: float = 50.0,  # proxy: skip if price > $50 (not micro/small)
) -> list[dict[str, Any]]:
    """Generate LONG picks for meme names showing squeeze precursors."""
    df = _fetch_snapshot(_MEME_UNIVERSE)
    if df.empty:
        return []

    df["vol_surge"] = df["volume"] / df["vol_avg_5d"]
    df["price_chg"] = (df["close"] - df["prev_close"]) / df["prev_close"]
    df["range_position"] = (df["close"] - df["low_5d"]) / (df["high_5d"] - df["low_5d"]).replace(0, float("nan"))

    picks: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        # Squeeze precursor: volume surge + price jump + near 5d high
        if row["vol_surge"] < min_volume_surge:
            continue
        if row["price_chg"] < min_price_change:
            continue
        if row["close"] > max_market_cap_proxy:
            continue
        if pd.isna(row["range_position"]) or row["range_position"] < 0.70:
            continue

        conf = min(0.85, 0.55 + (row["vol_surge"] - 2.0) * 0.08 + row["price_chg"] * 2.0)
        picks.append({
            "symbol": row["symbol"],
            "direction": "LONG",
            "entry_price": float(row["close"]),
            "confidence": round(conf, 4),
            "trust": 5 if conf >= 0.70 else 4,
            "score": int(conf * 100),
            "strategy": "meme_momentum_squeeze",
            "asset_class": "MEME",
            "extra": {
                "vol_surge": round(float(row["vol_surge"]), 2),
                "price_chg": round(float(row["price_chg"]), 4),
                "range_pos": round(float(row["range_position"]), 2),
                "source": "yfinance_snapshot",
            },
            "forced_resolution": {"tp_pct": 8.0, "sl_pct": 4.0, "max_hold_hours": 72},
        })

    logger.info("meme_momentum_squeeze: %d picks from %d scanned", len(picks), len(df))
    return picks


def generate_picks() -> list[dict[str, Any]]:
    """Alias for emitter compatibility."""
    return generate_meme_momentum_squeeze_picks()


if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.INFO)
    picks = generate_meme_momentum_squeeze_picks()
    print(json.dumps({"n": len(picks), "picks": picks}, indent=2, default=str))
    sys.exit(0 if picks else 1)
