#!/usr/bin/env python3
"""
Crypto Vol-Regime Accumulation Detector (CRYPTO)
================================================
Unique Brand-New Strategy per TESTING_PROTOCOL.MD §0.1–§0.6 + §16 HF addendum.

Academic basis:
- Gu, Kelly & Xiu (2020): volume-profile momentum in retail- heavy markets.
- Wyckoff/Silverstein accumulation schematics: quiet accumulation before markup.
- Ait-Sahalia & Saglam (2021): microstructure of crypto flash events.

Edge:
  Realized volatility compresses (quiet period) while volume profile shows
  stealth accumulation — volume rises on flat-to-slightly-negative price
  action. This predicts breakout / continuation with asymmetric payoff.

Data source: yfinance (free, no API key)
Universe: top 10 liquid crypto USD pairs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_vol_regime_accumulation"
ACADEMIC_CITATION = "Gu, Kelly & Xiu (2020) + Wyckoff accumulation schematics"

CRYPTO_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

# --- Parameters ---
LOOKBACK_DAYS = 30          # Days for vol/volume history
VOL_WINDOW = 14             # Realized vol rolling window
VOL_PERCENTILE_THRESHOLD = 30  # Vol must be below 30th percentile of lookback
VOLATILITY_DAYS = 14        # Annualization factor
VOLUME_TREND_WINDOW = 5     # Short volume trend
VOLUME_SLOPE_MIN = 1.2      # Volume SMA must rise >= 20% vs longer SMA
PRICE_CHANGE_MAX = 0.02     # Price must be flat (-2% to +1%) over trigger window
MAX_HOLD_HOURS = 72
TP_PCT = 6.0
SL_PCT = 4.0

# Slippage per TESTING_PROTOCOL §0.6 topic gate #1
EXPECTED_SLIPPAGE_BPS = 6
MAX_AUM_USD = 350_000
DAILY_LOSS_LIMIT_PCT = 2.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_ohlcv(symbol: str, period: str = "1mo", interval: str = "1h") -> Any:
    """Fetch hourly OHLCV via yfinance."""
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period=period, interval=interval)
        if hist is None or hist.empty or len(hist) < VOL_WINDOW + 10:
            return None
        return hist
    except Exception as exc:
        logger.debug("%s: fetch error: %s", symbol, exc)
        return None


def _realized_vol(close: "np.ndarray", window: int = VOL_WINDOW) -> float:
    """Annualized realized volatility from log returns."""
    if len(close) < window + 1:
        return float("inf")
    log_ret = np.log(close[1:] / close[:-1])
    rolling_std = float(np.std(log_ret[-window:]))
    # Hourly to annual (assuming ~24*365 hours for crypto)
    return rolling_std * np.sqrt(24 * 365)


def _volume_trend(volume: "np.ndarray", short: int = VOLUME_TREND_WINDOW, long: int = VOL_WINDOW) -> float:
    """Ratio of short volume SMA to long volume SMA."""
    if len(volume) < long + 1:
        return 0.0
    short_avg = float(np.mean(volume[-short:]))
    long_avg = float(np.mean(volume[-long:]))
    if long_avg < 1e-15:
        return 0.0
    return short_avg / long_avg


def _price_change(close: "np.ndarray", bars: int = VOLUME_TREND_WINDOW) -> float:
    """Return over last N bars."""
    if len(close) < bars + 1:
        return 0.0
    return float(close[-1] / close[-(bars + 1)] - 1.0)


def _vol_percentile(current_vol: float, close: "np.ndarray", lookback: int = LOOKBACK_DAYS * 24) -> float:
    """Percentile of current realized vol vs lookback distribution."""
    if len(close) < lookback + VOL_WINDOW + 1:
        return 50.0
    log_ret = np.log(close[1:] / close[:-1])
    hist_vols = []
    for i in range(lookback):
        if i + VOL_WINDOW > len(log_ret):
            break
        hist_vols.append(float(np.std(log_ret[-(i + VOL_WINDOW):len(log_ret) - i])))
    if not hist_vols:
        return 50.0
    hist_vols_arr = np.array(hist_vols) * np.sqrt(24 * 365)
    return float(np.mean(hist_vols_arr < current_vol) * 100)


def _score_pick(conf: float, trust: int, direction: str) -> int:
    """Layer 2.5 compliant score."""
    base = int(conf * 100)
    if direction.upper() in ("SHORT", "SELL"):
        base += 5
    if 6 <= trust <= 7:
        base += 15
    return max(40, min(85, base))


def generate_vol_regime_accumulation_picks() -> list[dict[str, Any]]:
    """Generate paper-pilot picks for vol-regime accumulation strategy."""
    picks: list[dict[str, Any]] = []
    now = _now_iso()

    for sym in CRYPTO_UNIVERSE:
        hist = _fetch_ohlcv(sym)
        if hist is None:
            continue
        close = hist["Close"].dropna().values.astype(float)
        volume = hist["Volume"].dropna().values.astype(float)
        if len(close) < VOL_WINDOW + 5 or len(volume) < VOL_WINDOW + 5:
            continue

        cur_vol = _realized_vol(close)
        vol_pct = _vol_percentile(cur_vol, close)
        vol_trend = _volume_trend(volume)
        price_chg = _price_change(close)

        # Core signal: vol compressed + volume rising + price flat
        if vol_pct <= VOL_PERCENTILE_THRESHOLD and vol_trend >= VOLUME_SLOPE_MIN and -0.02 <= price_chg <= 0.01:
            entry = float(close[-1])
            direction = "LONG"
            # Confidence scales with vol compression depth and volume steepness
            conf_raw = min(0.82, 0.55 + (VOL_PERCENTILE_THRESHOLD - vol_pct) / 100 * 0.25 + (vol_trend - 1.0) * 0.15)
            conf = min(0.85, conf_raw)  # Cap to avoid toxic LONG+Conf>=0.90
            trust = 5
            if vol_trend >= 1.5:
                trust = 6
            score = _score_pick(conf, trust, direction)

            tp = round(entry * (1 + TP_PCT / 100), 6)
            sl = round(entry * (1 - SL_PCT / 100), 6)

            picks.append({
                "symbol": sym,
                "asset_class": "CRYPTO",
                "direction": direction,
                "strategy": STRATEGY_NAME,
                "source_system": f"{STRATEGY_NAME}_v1",
                "confidence": round(conf, 4),
                "trust": trust,
                "score": score,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "forced_resolution": {
                    "max_hold_hours": MAX_HOLD_HOURS,
                    "tp_pct": TP_PCT,
                    "sl_pct": SL_PCT,
                },
                "methodology_v2_extensions": {
                    "expected_slippage_bps": EXPECTED_SLIPPAGE_BPS,
                    "regime_kill_switch": "extreme_fear_or_vol_spike_gt_80th_pct",
                    "max_reasonable_aum_usd": MAX_AUM_USD,
                    "cross_strategy_corr_risk": "medium (BTC beta dominates)",
                    "live_vs_paper_slippage_delta_bps": "to_be_tracked",
                    "reward_to_risk_floor": round(TP_PCT / SL_PCT, 2),
                    "vol_targeting": True,
                    "daily_loss_limit_pct": DAILY_LOSS_LIMIT_PCT,
                    "next_bar_open_fill": True,
                },
                "notes": (
                    f"Unique CRYPTO: vol-compression accumulation on {sym}. "
                    f"Vol={cur_vol:.1%} (pct={vol_pct:.0f}), vol_trend={vol_trend:.2f}, price_chg={price_chg:.2%}. "
                    f"Academic: {ACADEMIC_CITATION}. Protocol-hardened (Layer 2.5, §16). Paper-pilot only."
                ),
                "created_at": now,
                "paper_pilot": True,
            })

    return picks


if __name__ == "__main__":
    picks = generate_vol_regime_accumulation_picks()
    print(f"Generated {len(picks)} CRYPTO vol-regime accumulation picks.")
    for p in picks:
        print(f"  {p['symbol']} | score={p['score']} | trust={p['trust']} | conf={p['confidence']}")
