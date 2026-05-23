"""
funding_rate_scanner.py -- Alpha Engine: Binance Funding Rate Scanner
=====================================================================
Scans real-time funding rates across major USDM perpetual futures pairs.
Detects high-confidence BUY signals (negative funding = shorts paying longs).

Signal Logic:
  EXTREME NEGATIVE (< -0.05%/8h) → BUY, 85% confidence
  NEGATIVE         (< -0.01%/8h) → BUY, 65% confidence
  NEUTRAL          (-0.01% to +0.05%) → NEUTRAL
  EXTREME POSITIVE (> +0.05%/8h) → CAUTION (overheated longs)

Run: python funding_rate_scanner.py
"""

import os
import json
import math
import time
import statistics
from datetime import datetime, timezone, timedelta

import requests

# Shared multi-source failover (Binance fapi -> Bybit -> OKX -> Coinglass).
# REQUIRED by project rule (CLAUDE.md / feedback_api_failover): never single
# Binance endpoint.
# Uses centralized failover_imports.py to avoid triple duplicate import blocks.
try:
    from alpha_engine.failover_imports import (
        fetch_funding_entry as _shared_fetch_funding_entry,
        HAS_SHARED_FAILOVER as _HAS_SHARED_FAILOVER,
    )
except ImportError:
    _HAS_SHARED_FAILOVER = False
    _shared_fetch_funding_entry = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# 2026-05-14: Expanded 10→30 symbols (swarm Round A P1, CoinGlass/Binance failover)
# Prioritized by market cap + signal quality (top CRYPTO performers in dashboard)
SYMBOLS = [
    # Majors
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    # Layer 1 high-cap
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "NEARUSDT", "ATOMUSDT",
    "TONUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "HYPEUSDT",
    # DeFi (top performers: DYDX PF 58, BNB PF 56 in dashboard)
    "DYDXUSDT", "AAVEUSDT", "UNIUSDT", "LINKUSDT", "LDOUSDT",
    # High-momentum / trending
    "RENDERUSDT", "TAOUSDT", "FETUSDT", "ARBUSDT", "OPUSDT",
    # Meme / high-vol (useful for funding rate extremes)
    "DOGEUSDT", "PEPEUSDT", "WIFUSDT",
    # Payments
    "XLMUSDT", "LTCUSDT",
]

FAPI_BASES = [
    "https://fapi.binance.com", "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
SPOT_BASES = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://data-api.binance.vision", "https://api.binance.us",
]
# Legacy single-URL references (backward compat)
FAPI_BASE = FAPI_BASES[0]
SPOT_BASE = SPOT_BASES[0]

# Thresholds (expressed as decimal, not percent)
EXTREME_NEG_THRESHOLD = -0.0005   # -0.05%/8h
MODERATE_NEG_THRESHOLD = -0.0001  # -0.01%/8h
EXTREME_POS_THRESHOLD  =  0.0005  # +0.05%/8h

# TP/SL configuration
TP_EXTREME_PCT  = 0.02   # +2% TP for extreme negative
TP_MODERATE_PCT = 0.015  # +1.5% TP for moderate negative
SL_PCT          = 0.01   # -1% SL for both

# Output path
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE  = os.path.join(DATA_DIR, "funding_rate_signals.json")

REQUEST_TIMEOUT = 10   # seconds
EST_OFFSET      = timedelta(hours=-5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _est_now() -> str:
    """Return current time as EST ISO string."""
    utc_now = datetime.now(timezone.utc)
    est_now = utc_now + EST_OFFSET
    return est_now.strftime("%Y-%m-%d %H:%M:%S EST")


def _annualized_rate(funding_rate: float) -> float:
    """Convert 8-hour funding rate to annualized percentage.

    There are 3 funding intervals per day × 365 days.
    """
    return funding_rate * 3 * 365 * 100  # result is a percent


def _get_spot_price(symbol: str, session: requests.Session) -> float | None:
    """Fetch current spot price from Binance public API (with failover)."""
    for base in SPOT_BASES:
        try:
            url = f"{base}/api/v3/ticker/price"
            resp = session.get(url, params={"symbol": symbol}, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception:
            continue
    print(f"  [WARN] Could not fetch spot price for {symbol}: all endpoints failed")
    return None


def _get_latest_funding_rate(symbol: str, session: requests.Session) -> dict | None:
    """Fetch the most recent funding rate entry for a symbol.

    Failover chain (per project rule -- never single Binance):
      1. Binance fapi mirrors (api / api1 / api2 / api3-equiv via fapi/fapi1/fapi2)
      2. Shared multi-source: Bybit -> OKX -> Coinglass (if API key)
    Returns the entry in Binance shape ``{"fundingRate": "<decimal>", "fundingTime": <ms>}``.
    """
    # 1. Binance fapi mirrors
    for base in FAPI_BASES:
        try:
            url = f"{base}/fapi/v1/fundingRate"
            resp = session.get(
                url,
                params={"symbol": symbol, "limit": 10},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            return data[-1]
        except Exception:
            continue

    # 2. Shared multi-source failover (Bybit -> OKX -> Coinglass)
    #    Uses fetch_funding_entry which returns the actual 8h-aligned
    #    funding settlement time instead of int(time.time()*1000).
    if _HAS_SHARED_FAILOVER:
        try:
            entry = _shared_fetch_funding_entry(symbol)
            if entry is not None:
                # Synthesize a Binance-shaped record so downstream code is unchanged.
                # fundingTime is now the actual 8h-aligned settlement time,
                # not a wall-clock approximation.
                return {
                    "symbol": symbol,
                    "fundingRate": str(float(entry["fundingRate"])),
                    "fundingTime": int(entry["fundingTime"]),
                    "_source": entry.get("source", "shared_failover"),
                }
        except Exception:
            pass

    print(f"  [WARN] Could not fetch funding rate for {symbol}: all endpoints failed")
    return None


def _classify_signal(funding_rate: float) -> tuple[str, float, str, float, float]:
    """Return (signal_type, confidence, reason, tp_pct, sl_pct)."""
    if funding_rate < EXTREME_NEG_THRESHOLD:
        return (
            "BUY",
            0.85,
            f"Extreme negative funding ({funding_rate*100:.4f}%/8h): shorts heavily paying longs -- strong mean-reversion setup",
            TP_EXTREME_PCT,
            SL_PCT,
        )
    elif funding_rate < MODERATE_NEG_THRESHOLD:
        return (
            "BUY",
            0.65,
            f"Negative funding ({funding_rate*100:.4f}%/8h): shorts paying longs -- bullish funding pressure",
            TP_MODERATE_PCT,
            SL_PCT,
        )
    elif funding_rate > EXTREME_POS_THRESHOLD:
        return (
            "CAUTION",
            0.70,
            f"Extreme positive funding ({funding_rate*100:.4f}%/8h): longs overextended -- risk of long squeeze",
            0.0,
            0.0,
        )
    else:
        return (
            "NEUTRAL",
            0.50,
            f"Funding rate within normal range ({funding_rate*100:.4f}%/8h)",
            0.0,
            0.0,
        )


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------
def run_scan(verbose: bool = True) -> list[dict]:
    """
    Scan all configured symbols, classify funding rate signals, persist to JSON.

    Returns a list of signal dicts (all symbols, including NEUTRAL).
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if verbose:
        print("=" * 70)
        print("  ALPHA ENGINE -- Funding Rate Scanner")
        print(f"  Scan time: {_est_now()}")
        print("=" * 70)

    session = requests.Session()
    session.headers.update({"User-Agent": "AlphaEngine/1.0"})

    signals: list[dict] = []

    for symbol in SYMBOLS:
        if verbose:
            print(f"  Scanning {symbol}...", end="", flush=True)

        fr_entry = _get_latest_funding_rate(symbol, session)
        if fr_entry is None:
            if verbose:
                print(" [SKIP -- no data]")
            continue

        funding_rate = float(fr_entry["fundingRate"])
        funding_time_ms = int(fr_entry["fundingTime"])
        funding_time_dt = datetime.fromtimestamp(
            funding_time_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        spot_price = _get_spot_price(symbol, session)
        ann_rate   = _annualized_rate(funding_rate)

        signal_type, confidence, reason, tp_pct, sl_pct = _classify_signal(funding_rate)

        entry_price = spot_price
        tp_price    = round(entry_price * (1 + tp_pct), 6) if (entry_price and tp_pct) else None
        sl_price    = round(entry_price * (1 - sl_pct), 6) if (entry_price and sl_pct) else None

        record = {
            "symbol":          symbol,
            "funding_rate_pct": round(funding_rate * 100, 6),
            "ann_rate_pct":    round(ann_rate, 2),
            "funding_time":    funding_time_dt,
            "signal":          signal_type,
            "confidence":      confidence,
            "reason":          reason,
            "entry_price":     entry_price,
            "take_profit":     tp_price,
            "stop_loss":       sl_price,
            "tp_pct":          round(tp_pct * 100, 2),
            "sl_pct":          round(sl_pct * 100, 2),
            "scanned_at":      _est_now(),
        }

        signals.append(record)

        if verbose:
            marker = {
                "BUY":     " [BUY]",
                "CAUTION": " [CAUTION]",
                "NEUTRAL": " [neutral]",
            }.get(signal_type, "")
            print(marker)

        # Be polite to the public API
        time.sleep(0.15)

    # Persist to disk
    payload = {
        "scanned_at": _est_now(),
        "symbol_count": len(SYMBOLS),
        "signal_count": len(signals),
        "buy_signals":  sum(1 for s in signals if s["signal"] == "BUY"),
        "signals":      signals,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    if verbose:
        _print_table(signals)
        print(f"\n  Saved {len(signals)} signals -> {OUTPUT_FILE}")

    return signals


# ---------------------------------------------------------------------------
# Pretty table
# ---------------------------------------------------------------------------
def _print_table(signals: list[dict]) -> None:
    """Print a formatted table of all signals."""
    header = (
        f"\n{'Symbol':<12} {'Funding%':>10} {'Ann%':>8} {'Signal':>8} "
        f"{'Entry':>12} {'TP':>12} {'SL':>12} {'Conf':>6}"
    )
    sep = "-" * 84
    print(sep)
    print(header)
    print(sep)

    # Sort: BUY first (by most negative funding), then CAUTION, then NEUTRAL
    order = {"BUY": 0, "CAUTION": 1, "NEUTRAL": 2}
    sorted_signals = sorted(
        signals,
        key=lambda s: (order.get(s["signal"], 3), s["funding_rate_pct"]),
    )

    for s in sorted_signals:
        entry_str = f"{s['entry_price']:>12.4f}" if s["entry_price"] else f"{'N/A':>12}"
        tp_str    = f"{s['take_profit']:>12.4f}" if s["take_profit"] else f"{'---':>12}"
        sl_str    = f"{s['stop_loss']:>12.4f}"   if s["stop_loss"]   else f"{'---':>12}"
        conf_str  = f"{s['confidence']*100:.0f}%"

        signal_display = s["signal"]

        print(
            f"{s['symbol']:<12} {s['funding_rate_pct']:>+10.4f} {s['ann_rate_pct']:>+8.1f} "
            f"{signal_display:>8} {entry_str} {tp_str} {sl_str} {conf_str:>6}"
        )

    print(sep)

    buy_count     = sum(1 for s in signals if s["signal"] == "BUY")
    caution_count = sum(1 for s in signals if s["signal"] == "CAUTION")
    print(f"  BUY: {buy_count}  |  CAUTION: {caution_count}  |  NEUTRAL: {len(signals) - buy_count - caution_count}")


# ---------------------------------------------------------------------------
# Backtester
# ---------------------------------------------------------------------------
def backtest_funding_rates(
    symbol: str = "BTCUSDT",
    days: int = 90,
    funding_threshold: float = MODERATE_NEG_THRESHOLD,
    hold_periods: int = 1,
    verbose: bool = True,
) -> dict:
    """
    Backtest a simple strategy: buy when funding_rate < threshold, hold for
    `hold_periods` × 8h intervals, then exit at the opening of the next funding
    interval (approximated with Binance kline data).

    Parameters
    ----------
    symbol            : Perpetual futures symbol (default BTCUSDT).
    days              : Number of calendar days of history to download (max ~90
                        from the 1000-row endpoint; use multiple calls for more).
    funding_threshold : Entry trigger (default -0.01%/8h = -0.0001).
    hold_periods      : Number of 8h periods to hold after entry (default 1).
    verbose           : Print progress and results.

    Returns
    -------
    dict with keys: win_rate, avg_pnl_pct, sharpe, num_trades, trades
    """
    if verbose:
        print("=" * 70)
        print(f"  BACKTEST -- {symbol} | last {days}d | threshold {funding_threshold*100:.4f}%")
        print("=" * 70)

    session = requests.Session()
    session.headers.update({"User-Agent": "AlphaEngine/1.0"})

    # 1. Download historical funding rates (limit=1000 gives ~333 days of 8h data)
    url = f"{FAPI_BASE}/fapi/v1/fundingRate"
    try:
        resp = session.get(
            url,
            params={"symbol": symbol, "limit": 1000},
            timeout=30,
        )
        resp.raise_for_status()
        all_rates = resp.json()
    except Exception as exc:
        print(f"  [ERROR] Could not download funding history: {exc}")
        return {}

    if not all_rates:
        print("  [ERROR] No funding rate data returned.")
        return {}

    # Filter to the last `days` days
    cutoff_ms = (time.time() - days * 86400) * 1000
    rates = [r for r in all_rates if int(r["fundingTime"]) >= cutoff_ms]

    if verbose:
        print(f"  Fetched {len(all_rates)} total records; {len(rates)} within last {days}d")

    if len(rates) < 2:
        print("  [ERROR] Not enough data for backtest.")
        return {}

    # 2. Download 8h OHLCV klines for the same period to get entry/exit prices.
    #    We use the perpetual futures kline endpoint so price references match.
    kline_url    = f"{FAPI_BASE}/fapi/v1/klines"
    start_time   = int(rates[0]["fundingTime"])
    end_time_ms  = int(rates[-1]["fundingTime"]) + 8 * 3600 * 1000 * (hold_periods + 1)

    klines_raw: list = []
    batch_start = start_time
    if verbose:
        print("  Downloading 8h klines...", end="", flush=True)

    while batch_start < end_time_ms:
        try:
            r = session.get(
                kline_url,
                params={
                    "symbol":    symbol,
                    "interval":  "8h",
                    "startTime": batch_start,
                    "endTime":   end_time_ms,
                    "limit":     1000,
                },
                timeout=30,
            )
            r.raise_for_status()
            batch = r.json()
        except Exception as exc:
            print(f"\n  [WARN] Kline fetch failed: {exc}")
            break

        if not batch:
            break
        klines_raw.extend(batch)
        batch_start = int(batch[-1][0]) + 1  # next open time
        if len(batch) < 1000:
            break
        time.sleep(0.2)

    if verbose:
        print(f" {len(klines_raw)} candles")

    # Build a lookup: open_time_ms → open_price, close_price
    kline_map: dict[int, dict] = {}
    for k in klines_raw:
        open_ms   = int(k[0])
        kline_map[open_ms] = {
            "open":  float(k[1]),
            "high":  float(k[2]),
            "low":   float(k[3]),
            "close": float(k[4]),
        }

    kline_times_sorted = sorted(kline_map.keys())

    def _find_kline_open_after(ts_ms: int) -> int | None:
        """Return the first kline open time >= ts_ms."""
        for kt in kline_times_sorted:
            if kt >= ts_ms:
                return kt
        return None

    def _find_kline_n_later(start_kt: int, n: int) -> int | None:
        """Return the kline open time that is n steps after start_kt."""
        try:
            idx = kline_times_sorted.index(start_kt)
            target = idx + n
            if target < len(kline_times_sorted):
                return kline_times_sorted[target]
        except ValueError:
            pass
        return None

    # 3. Simulate trades
    trades: list[dict] = []

    for i, rate_entry in enumerate(rates):
        fr = float(rate_entry["fundingRate"])
        if fr >= funding_threshold:
            continue  # No signal

        funding_time_ms = int(rate_entry["fundingTime"])

        # Entry: open of the 8h candle that starts at or after funding event
        entry_kt = _find_kline_open_after(funding_time_ms)
        if entry_kt is None:
            continue
        if entry_kt not in kline_map:
            continue

        entry_price = kline_map[entry_kt]["open"]

        # Exit: open of the candle `hold_periods` bars later
        exit_kt = _find_kline_n_later(entry_kt, hold_periods)
        if exit_kt is None or exit_kt not in kline_map:
            continue

        exit_price = kline_map[exit_kt]["open"]

        pnl_pct = (exit_price - entry_price) / entry_price * 100

        trades.append({
            "funding_time": datetime.fromtimestamp(
                funding_time_ms / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC"),
            "funding_rate_pct": round(fr * 100, 6),
            "entry_price":      entry_price,
            "exit_price":       exit_price,
            "pnl_pct":          round(pnl_pct, 4),
            "win":              pnl_pct > 0,
        })

    # 4. Statistics
    if not trades:
        if verbose:
            print("  No trades triggered with current threshold.")
        return {
            "symbol":    symbol,
            "days":      days,
            "threshold": funding_threshold,
            "num_trades": 0,
            "win_rate":   None,
            "avg_pnl_pct": None,
            "sharpe":     None,
            "trades":     [],
        }

    num_trades  = len(trades)
    wins        = sum(1 for t in trades if t["win"])
    win_rate    = wins / num_trades
    pnl_series  = [t["pnl_pct"] for t in trades]
    avg_pnl     = statistics.mean(pnl_series)

    # Sharpe: (mean / stdev) × sqrt(annualised intervals)
    # 8h intervals: 3/day × 365 = 1095/year
    if len(pnl_series) > 1:
        stdev = statistics.stdev(pnl_series)
        sharpe = (avg_pnl / stdev * math.sqrt(1095)) if stdev > 0 else 0.0
    else:
        sharpe = 0.0

    result = {
        "symbol":       symbol,
        "days":         days,
        "threshold_pct": round(funding_threshold * 100, 4),
        "hold_periods": hold_periods,
        "num_trades":   num_trades,
        "win_rate":     round(win_rate * 100, 2),
        "avg_pnl_pct":  round(avg_pnl, 4),
        "sharpe":       round(sharpe, 4),
        "total_pnl_pct": round(sum(pnl_series), 4),
        "best_trade":   round(max(pnl_series), 4),
        "worst_trade":  round(min(pnl_series), 4),
        "trades":       trades,
    }

    if verbose:
        _print_backtest_results(result)

    return result


def _print_backtest_results(result: dict) -> None:
    """Pretty-print backtest summary."""
    print("\n" + "=" * 50)
    print(f"  BACKTEST RESULTS -- {result['symbol']}")
    print("=" * 50)
    print(f"  Period:         Last {result['days']} days")
    print(f"  Threshold:      {result['threshold_pct']:+.4f}%/8h")
    print(f"  Hold periods:   {result['hold_periods']} × 8h")
    print(f"  Num trades:     {result['num_trades']}")
    print(f"  Win rate:       {result['win_rate']:.1f}%")
    print(f"  Avg P&L/trade:  {result['avg_pnl_pct']:+.4f}%")
    print(f"  Total P&L:      {result['total_pnl_pct']:+.4f}%")
    print(f"  Best trade:     {result['best_trade']:+.4f}%")
    print(f"  Worst trade:    {result['worst_trade']:+.4f}%")
    print(f"  Sharpe ratio:   {result['sharpe']:.4f}")
    print("=" * 50)

    # Print last 5 trades
    recent = result["trades"][-5:]
    if recent:
        print(f"\n  Last {len(recent)} trades:")
        for t in recent:
            win_label = "WIN " if t["win"] else "LOSS"
            print(
                f"    [{win_label}] {t['funding_time']}  FR:{t['funding_rate_pct']:+.4f}%"
                f"  Entry:{t['entry_price']:.2f}  Exit:{t['exit_price']:.2f}"
                f"  PnL:{t['pnl_pct']:+.4f}%"
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Alpha Engine -- Funding Rate Scanner & Backtester"
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest on BTCUSDT (past 90 days)",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Symbol to backtest (default: BTCUSDT)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Lookback days for backtest (default: 90)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=-0.0001,
        help="Funding rate entry threshold for backtest (default: -0.0001 = -0.01%%)",
    )
    parser.add_argument(
        "--hold",
        type=int,
        default=1,
        help="Number of 8h periods to hold in backtest (default: 1)",
    )
    args = parser.parse_args()

    # Always run the live scan
    signals = run_scan(verbose=True)

    # Optionally also run the backtest
    if args.backtest:
        print()
        backtest_funding_rates(
            symbol=args.symbol,
            days=args.days,
            funding_threshold=args.threshold,
            hold_periods=args.hold,
            verbose=True,
        )
