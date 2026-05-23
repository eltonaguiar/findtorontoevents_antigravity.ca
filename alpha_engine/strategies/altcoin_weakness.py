"""
Altcoin Weakness Scanner
========================
Detects structural altcoin weakness relative to BTC to generate SHORT signals.

Edge:
  - BTC dominance rising = altcoins losing BTC value (structural outflow)
  - Altcoins below 200-day MA with RSI(14) > 60 = dead-cat bounce SHORT
  - Short alts that are underperforming BTC by >15% over 14 days

Rules (BTC dominance mode):
  SHORT when:
    1. Altcoin 14-day return < BTC 14-day return - 15%  (underperforming BTC)
    AND
    2. Price < 200-day MA  (downtrend)
    AND
    3. RSI(14) in 55-70 (short the bounce)
  TP = entry - 2.5x ATR(14)
  SL = entry + 1.5x ATR(14)

Academic basis: Altcoin beta > 1 to BTC (Borri 2019). When BTC dominance rises,
altcoins fall faster than BTC making them ideal SHORT candidates.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_FILE = DATA_DIR / "altcoin_weakness_picks.json"

# High-liquidity altcoins with historically high BTC beta
TARGET_ALTS = [
    "SOLUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "MATICUSDT",
    "LINKUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT", "UNIUSDT",
    "NEARUSDT", "FETUSDT", "SUIUSDT", "APTUSDT", "INJUSDT",
    "ARBUSDT", "OPUSDT", "SANDUSDT", "MANAUSDT", "GALAUSDT",
]

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

MA_PERIOD = 200
ATR_PERIOD = 14
RSI_PERIOD = 14
LOOKBACK_DAYS = 14
UNDERPERF_THRESHOLD = -0.15   # alt must underperform BTC by 15%+ over 14 days
RSI_SHORT_MIN = 55.0           # require a bounce to short into
RSI_SHORT_MAX = 72.0
TP_ATR_MULT = 2.5
SL_ATR_MULT = 1.5
MIN_PRICE = 0.001              # avoid dust / delisted tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _fetch_binance_ohlcv(symbol: str, interval: str = "1d", limit: int = 250) -> pd.DataFrame:
    """Fetch OHLCV from Binance with multi-mirror failover."""
    import urllib.request
    _HDR = {"User-Agent": "AltcoinWeakness/1.0"}

    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers=_HDR)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_vol", "trades", "taker_buy_vol",
                "taker_buy_quote_vol", "ignore",
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            df["date"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("date", inplace=True)
            return df
        except Exception:
            continue
    return pd.DataFrame()


def _compute_relative_return(alt_close: pd.Series, btc_close: pd.Series, days: int) -> float:
    """Return alt 14d return minus BTC 14d return (negative = underperforming)."""
    if len(alt_close) < days + 1 or len(btc_close) < days + 1:
        return 0.0
    alt_ret = (alt_close.iloc[-1] / alt_close.iloc[-days]) - 1.0
    btc_ret = (btc_close.iloc[-1] / btc_close.iloc[-days]) - 1.0
    return float(alt_ret - btc_ret)


def _evaluate_symbol(
    symbol: str,
    df: pd.DataFrame,
    btc_close: pd.Series,
) -> list:
    """Apply altcoin weakness rules. Returns list of pick dicts."""
    if df is None or df.empty or len(df) < MA_PERIOD + LOOKBACK_DAYS + 5:
        return []

    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi14 = _rsi(close, RSI_PERIOD)
    ma200 = close.rolling(MA_PERIOD).mean()
    atr14 = _atr(high, low, close, ATR_PERIOD)

    price = float(close.iloc[-1])
    rsi_val = float(rsi14.iloc[-1])
    ma_val = float(ma200.iloc[-1])
    atr_val = float(atr14.iloc[-1])

    if (
        pd.isna(rsi_val) or pd.isna(ma_val) or pd.isna(atr_val)
        or atr_val <= 0 or price < MIN_PRICE
    ):
        return []

    # Relative performance vs BTC over LOOKBACK_DAYS
    rel_ret = _compute_relative_return(close, btc_close, LOOKBACK_DAYS)

    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    picks = []

    # SHORT signal: alt underperforms BTC by >15%, below 200 MA, RSI bounce
    is_below_ma = price < ma_val
    is_underperforming = rel_ret < UNDERPERF_THRESHOLD
    is_bounce = RSI_SHORT_MIN <= rsi_val <= RSI_SHORT_MAX

    if is_below_ma and is_underperforming and is_bounce:
        # Confidence scales with how much the alt is underperforming BTC
        severity = min(abs(rel_ret) / 0.30, 1.0)  # 0.30 = max expected underperformance
        confidence = round(0.55 + severity * 0.30, 3)  # range 0.55 – 0.85

        tp = round(price - TP_ATR_MULT * atr_val, 8)
        sl = round(price + SL_ATR_MULT * atr_val, 8)
        if tp <= 0 or sl <= price:
            return []

        pick_id = f"altcoin_weakness::{symbol}::{today_str}_SHORT"
        picks.append({
            "id": pick_id,
            "strategy": "altcoin_weakness",
            "symbol": symbol,
            "direction": "SHORT",
            "signal_type": "SHORT",
            "entry_price": price,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "asset_class": "CRYPTO",
            "category": "crypto",
            "source_system": "altcoin_weakness",
            "timeframe": "1d",
            "timestamp": now_iso,
            "created_at": now_iso,
            "entry_date": today_str,
            "status": "ACTIVE",
            "rsi_14": round(rsi_val, 2),
            "rel_return_14d_vs_btc": round(rel_ret * 100, 2),
            "ma200": round(ma_val, 6),
            "reasoning": [
                f"Alt underperforms BTC by {rel_ret*100:.1f}% over {LOOKBACK_DAYS}d (threshold {UNDERPERF_THRESHOLD*100:.0f}%)",
                f"RSI(14)={rsi_val:.1f} (dead-cat bounce into downtrend)",
                f"Price ${price:.4f} below 200-day MA ${ma_val:.4f}",
                "Altcoin Weakness: beta>1 to BTC — structural outflow SHORT",
            ],
            "risk_reward": round(TP_ATR_MULT / SL_ATR_MULT, 2),
        })

    return picks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> list:
    """Scan all alt targets, write picks to JSON, return list."""
    print("[ALT_WEAK] Altcoin Weakness scanner starting...")

    # Fetch BTC as benchmark first
    btc_df = _fetch_binance_ohlcv("BTCUSDT", interval="1d", limit=250)
    if btc_df.empty:
        print("[ALT_WEAK] Could not fetch BTC data — aborting")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text("[]")
        return []

    btc_close = btc_df["close"]
    btc_ret_14d = float(btc_close.iloc[-1] / btc_close.iloc[-LOOKBACK_DAYS]) - 1.0
    print(f"[ALT_WEAK] BTC 14d return: {btc_ret_14d*100:.1f}%")

    all_picks = []
    for sym in TARGET_ALTS:
        try:
            df = _fetch_binance_ohlcv(sym, interval="1d", limit=250)
            if df.empty:
                continue
            picks = _evaluate_symbol(sym, df, btc_close)
            all_picks.extend(picks)
            rel = _compute_relative_return(df["close"], btc_close, LOOKBACK_DAYS)
            print(f"[ALT_WEAK] {sym}: rel_vs_btc={rel*100:.1f}% signals={len(picks)}")
        except Exception as exc:
            print(f"[ALT_WEAK] {sym} failed: {exc}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(all_picks, indent=2))
    print(f"[ALT_WEAK] Wrote {len(all_picks)} picks to {OUTPUT_FILE}")
    return all_picks


if __name__ == "__main__":
    try:
        picks = run()
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text("[]")
        sys.exit(0)
