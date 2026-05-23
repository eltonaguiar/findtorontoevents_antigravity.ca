#!/usr/bin/env python3
"""
Backfill OHLCV-derived features for closed picks that have missing indicators.

The ML ranker trains on closed_picks.json but 83-94% of features (RSI, ATR,
volume_ratio) are imputed constants because they weren't captured at entry time.
This script fetches real 1h candles from Binance and computes the actual values.

Features computed:
  - rsi_at_entry: 14-period Wilder RSI
  - atr_at_entry: 14-period ATR (absolute, not percentage)
  - volume_ratio: current volume / 20-bar average volume
  - macd_hist: MACD histogram (12/26/9)
  - bb_width: Bollinger Band width (20,2) as fraction of middle band
  - obv_trend: OBV slope direction over 14 bars (+1, 0, -1)

Usage:
  python -m alpha_engine.backfill_ohlcv_features
  python -m alpha_engine.backfill_ohlcv_features --dry-run
  python -m alpha_engine.backfill_ohlcv_features --limit 10
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Binance API helpers (3-mirror failover per MEMORY.md API Failover Rule)
# ---------------------------------------------------------------------------

BINANCE_MIRRORS = [
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

RATE_LIMIT_SECONDS = 0.2  # 200ms between API calls


def _fetch_klines(symbol: str, interval: str, end_ms: int, limit: int = 50) -> list:
    """Fetch klines from Binance with 3-mirror failover.

    Returns list of [open_time, open, high, low, close, volume, ...] or empty list.
    """
    params = (
        f"symbol={symbol}&interval={interval}&endTime={end_ms}&limit={limit}"
    )
    last_err = None
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list) and len(data) > 0:
                    return data
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                OSError, TimeoutError) as exc:
            last_err = exc
            continue
    # All mirrors failed
    if last_err:
        print(f"  [WARN] All Binance mirrors failed for {symbol}: {last_err}")
    return []


# ---------------------------------------------------------------------------
# Symbol normalization
# ---------------------------------------------------------------------------

# Categories / symbol patterns that cannot be fetched from Binance
_SKIP_CATEGORIES = {"forex", "stock", "etf", "futures"}

# Symbols with '=' are forex (e.g., AUDUSD=X, USDCAD=X)
# Symbols without USDT suffix and not in dash format are likely equities (SPY, QQQ, NVDA)


def _to_binance_symbol(symbol: str, category: str) -> str | None:
    """Convert a pick symbol to Binance trading pair, or None if not convertible."""
    if category in _SKIP_CATEGORIES:
        return None
    if "=" in symbol:
        # Forex pair like AUDUSD=X
        return None
    if symbol.endswith("USDT"):
        return symbol
    if "-USD" in symbol:
        # CoinGecko-style: BTC-USD -> BTCUSDT, SOL-USD -> SOLUSDT
        base = symbol.split("-")[0]
        return f"{base}USDT"
    # Pure ticker without USDT and no dash -- likely equity/ETF even if category says crypto
    # Check if it looks like a crypto ticker (all uppercase, short)
    # We'll attempt it and let the API tell us if it fails
    if symbol.isalpha() and len(symbol) <= 5 and symbol.isupper():
        # Likely equity ticker (SPY, QQQ, NVDA, GLD, etc.)
        return None
    return None


def _entry_timestamp_ms(pick: dict) -> int | None:
    """Extract entry timestamp in milliseconds from pick.

    Tries (in order):
      1. Timestamp embedded in the pick ID (last :: segment)
      2. entry_date string parsed as date -> midnight UTC
    """
    pick_id = str(pick.get("id", ""))
    parts = pick_id.split("::")
    if len(parts) >= 4:
        try:
            ts = int(parts[-1])
            if ts > 1_000_000_000_000:  # milliseconds
                return ts
            if ts > 1_000_000_000:  # seconds
                return ts * 1000
        except (ValueError, TypeError):
            pass

    entry_date = pick.get("entry_date")
    if entry_date:
        try:
            dt = datetime.strptime(entry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            pass

    return None


# ---------------------------------------------------------------------------
# Pure-Python indicator calculations (no numpy required)
# ---------------------------------------------------------------------------

def _wilder_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute Wilder's RSI using the smoothed moving average method."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    if len(gains) < period:
        return None

    # Initial SMA for first `period` values
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder smoothing for remaining values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(highs: list[float], lows: list[float], closes: list[float],
         period: int = 14) -> float | None:
    """Compute Average True Range (Wilder smoothing)."""
    if len(closes) < period + 1:
        return None
    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    atr_val = sum(true_ranges[:period]) / period
    for i in range(period, len(true_ranges)):
        atr_val = (atr_val * (period - 1) + true_ranges[i]) / period
    return atr_val


def _volume_ratio(volumes: list[float], lookback: int = 20) -> float | None:
    """Current volume / average of prior `lookback` bars."""
    if len(volumes) < lookback + 1:
        return None
    avg = sum(volumes[-(lookback + 1):-1]) / lookback
    if avg == 0:
        return None
    return volumes[-1] / avg


def _ema(values: list[float], period: int) -> list[float]:
    """Compute EMA series. Returns list same length as input (first period-1 are SMA-seeded)."""
    if len(values) < period:
        return values[:]
    k = 2.0 / (period + 1)
    result = []
    # Seed with SMA
    sma = sum(values[:period]) / period
    for i in range(period):
        result.append(sma)  # placeholder for pre-seed values
    result[-1] = sma  # last of the seed block is the actual SMA
    for i in range(period, len(values)):
        val = values[i] * k + result[-1] * (1 - k)
        result.append(val)
    return result


def _macd_histogram(closes: list[float]) -> float | None:
    """MACD histogram (12, 26, 9). Returns last value."""
    if len(closes) < 35:  # need 26 + 9 for signal line
        return None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema(macd_line[25:], 9)  # start from where ema26 is valid
    if not signal:
        return None
    return macd_line[-1] - signal[-1]


def _bb_width(closes: list[float], period: int = 20, num_std: float = 2.0) -> float | None:
    """Bollinger Band width as (upper - lower) / middle."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    sma = sum(window) / period
    if sma == 0:
        return None
    variance = sum((x - sma) ** 2 for x in window) / period
    std = variance ** 0.5
    upper = sma + num_std * std
    lower = sma - num_std * std
    return (upper - lower) / sma


def _obv_trend(closes: list[float], volumes: list[float],
               period: int = 14) -> int | None:
    """OBV trend direction over last `period` bars. Returns +1, 0, or -1."""
    if len(closes) < period + 1 or len(volumes) < period + 1:
        return None
    # Compute OBV for last period+1 bars
    start = len(closes) - period - 1
    obv = 0.0
    obv_values = [0.0]
    for i in range(start + 1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        obv_values.append(obv)

    # Simple linear regression slope sign
    n = len(obv_values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(obv_values) / n
    numerator = sum((i - x_mean) * (obv_values[i] - y_mean) for i in range(n))
    if numerator > 0:
        return 1
    elif numerator < 0:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Main backfill logic
# ---------------------------------------------------------------------------

def compute_features_from_klines(klines: list) -> dict:
    """Extract OHLCV arrays from Binance klines and compute all features."""
    opens = [float(k[1]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    features = {}

    rsi = _wilder_rsi(closes)
    if rsi is not None:
        features["rsi_at_entry"] = round(rsi, 2)

    atr_val = _atr(highs, lows, closes)
    if atr_val is not None:
        features["atr_at_entry"] = round(atr_val, 8)

    vr = _volume_ratio(volumes)
    if vr is not None:
        features["volume_ratio"] = round(vr, 4)

    macd_h = _macd_histogram(closes)
    if macd_h is not None:
        features["macd_hist"] = round(macd_h, 8)

    bb_w = _bb_width(closes)
    if bb_w is not None:
        features["bb_width"] = round(bb_w, 6)

    obv_t = _obv_trend(closes, volumes)
    if obv_t is not None:
        features["obv_trend"] = obv_t

    return features


def needs_backfill(pick: dict) -> bool:
    """Check if a pick is missing any of the core features."""
    return (
        pick.get("rsi_at_entry") is None
        or pick.get("atr_at_entry") is None
        or pick.get("volume_ratio") is None
        or pick.get("macd_hist") is None
        or pick.get("bb_width") is None
        or pick.get("obv_trend") is None
    )


def backfill_picks(picks: list[dict], dry_run: bool = False,
                   limit: int | None = None) -> tuple[int, int]:
    """Backfill missing OHLCV features for closed picks.

    Returns (picks_processed, features_populated).
    """
    candidates = [p for p in picks if needs_backfill(p)]
    if limit is not None:
        candidates = candidates[:limit]

    total_processed = 0
    total_features = 0
    skipped_non_crypto = 0
    skipped_no_timestamp = 0
    skipped_api_fail = 0

    for i, pick in enumerate(candidates):
        symbol = pick.get("symbol", "")
        category = pick.get("category", "crypto")

        binance_symbol = _to_binance_symbol(symbol, category)
        if binance_symbol is None:
            skipped_non_crypto += 1
            if dry_run:
                print(f"  [SKIP] {symbol} (category={category}, not on Binance)")
            continue

        ts_ms = _entry_timestamp_ms(pick)
        if ts_ms is None:
            skipped_no_timestamp += 1
            if dry_run:
                print(f"  [SKIP] {symbol} (no valid timestamp)")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would backfill {symbol} ({binance_symbol}) "
                  f"@ {pick.get('entry_date', '?')}")
            total_processed += 1
            continue

        # Fetch 50 bars of 1h klines ending at entry time
        klines = _fetch_klines(binance_symbol, "1h", end_ms=ts_ms, limit=50)

        if not klines or len(klines) < 20:
            skipped_api_fail += 1
            print(f"  [WARN] Insufficient kline data for {binance_symbol} "
                  f"({len(klines)} bars) @ {pick.get('entry_date', '?')}")
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        features = compute_features_from_klines(klines)

        # Only overwrite features that are currently missing
        updated_count = 0
        for key, value in features.items():
            if pick.get(key) is None:
                pick[key] = value
                updated_count += 1

        total_features += updated_count
        total_processed += 1

        if updated_count > 0:
            print(f"  [{i + 1}/{len(candidates)}] {symbol}: "
                  f"+{updated_count} features (RSI={features.get('rsi_at_entry', '?')}, "
                  f"ATR={features.get('atr_at_entry', '?')}, "
                  f"VR={features.get('volume_ratio', '?')})")

        # Rate limit between API calls
        time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n--- Backfill Summary ---")
    print(f"Candidates: {len(candidates)}")
    print(f"Processed:  {total_processed}")
    print(f"Features populated: {total_features}")
    print(f"Skipped (non-Binance): {skipped_non_crypto}")
    print(f"Skipped (no timestamp): {skipped_no_timestamp}")
    print(f"Skipped (API fail/insufficient data): {skipped_api_fail}")

    return total_processed, total_features


def main():
    parser = argparse.ArgumentParser(
        description="Backfill OHLCV-derived features for closed picks"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be backfilled without saving",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process N picks (for testing)",
    )
    args = parser.parse_args()

    # Resolve path relative to this file's directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    picks_path = os.path.join(data_dir, "closed_picks.json")

    if not os.path.exists(picks_path):
        print(f"ERROR: {picks_path} not found")
        sys.exit(1)

    with open(picks_path, "r", encoding="utf-8") as f:
        picks = json.load(f)

    print(f"Loaded {len(picks)} closed picks from {picks_path}")

    n_processed, n_features = backfill_picks(
        picks, dry_run=args.dry_run, limit=args.limit
    )

    if not args.dry_run and n_features > 0:
        with open(picks_path, "w", encoding="utf-8") as f:
            json.dump(picks, f, indent=2, ensure_ascii=False)
        print(f"\nSaved updated picks to {picks_path}")

    print(f"\nBackfilled {n_processed} picks, {n_features} features populated")


if __name__ == "__main__":
    main()
