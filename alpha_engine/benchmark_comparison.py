#!/usr/bin/env python3
"""
Benchmark Comparison Module for Alpha Engine
==============================================
Compares our system's closed-pick performance against simple baseline
strategies (BTC buy-and-hold, EMA crossover) to quantify alpha.

Uses stdlib only (urllib.request, json, math, statistics, datetime).
Binance 5-mirror failover per project rules.

Exports:
    compute_btc_buy_hold(start_date, end_date) -> dict
    compute_ma_crossover_baseline(start_date, end_date) -> dict
    compute_our_performance(closed_picks_path, start_date, end_date) -> dict
    generate_comparison_report(closed_picks_path) -> dict
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

_log = logging.getLogger("alpha_engine.benchmark_comparison")

# ---------------------------------------------------------------------------
# Windows UTF-8 fix (consistent with other alpha_engine modules)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Binance API mirrors — 5-mirror failover (data-api first for CI)
# Plus CoinGecko / KuCoin / CryptoCompare fallback per CLAUDE.md
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# In CI, data-api.binance.vision is already first; keep order as-is
if os.environ.get("GITHUB_ACTIONS"):
    # Ensure non-geo-blocked endpoint is first
    _preferred = "https://data-api.binance.vision"
    if BINANCE_MIRRORS[0] != _preferred:
        BINANCE_MIRRORS.remove(_preferred)
        BINANCE_MIRRORS.insert(0, _preferred)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
_TIMEOUT = 15
_USER_AGENT = "AlphaEngine-Benchmark/1.0"


def _http_get_json(url: str, timeout: int = _TIMEOUT):
    """GET JSON from url, return parsed dict/list or None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError, Exception) as exc:
        _log.debug("HTTP fail %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Kline fetching with failover
# ---------------------------------------------------------------------------

def _date_to_ms(dt_str: str) -> int:
    """Convert YYYY-MM-DD to epoch milliseconds UTC."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _fetch_binance_klines(symbol: str, interval: str,
                          start_ms: int, end_ms: int,
                          limit: int = 1000) -> list | None:
    """Fetch klines from Binance with 5-mirror failover.

    Returns list of [open_time, open, high, low, close, volume, ...] or None.
    Handles pagination for large date ranges.
    """
    all_klines = []
    cursor_ms = start_ms

    while cursor_ms < end_ms:
        fetched = False
        for base in BINANCE_MIRRORS:
            url = (
                f"{base}/api/v3/klines"
                f"?symbol={symbol}&interval={interval}"
                f"&startTime={cursor_ms}&endTime={end_ms}&limit={limit}"
            )
            data = _http_get_json(url)
            if data and isinstance(data, list) and len(data) > 0:
                all_klines.extend(data)
                # Advance cursor past last candle
                last_open_time = data[-1][0]
                cursor_ms = last_open_time + 1
                fetched = True
                break
            time.sleep(0.2)

        if not fetched:
            # All Binance mirrors failed for this chunk
            _log.warning("All Binance mirrors failed at cursor %d", cursor_ms)
            break

    return all_klines if all_klines else None


def _fetch_klines_with_full_failover(symbol: str, interval: str,
                                     start_date: str, end_date: str) -> list | None:
    """Fetch klines with Binance 5-mirror -> CoinGecko -> CryptoCompare failover.

    Returns list of dicts: [{"t": epoch_s, "o": float, "h": float, "l": float, "c": float}, ...]
    """
    start_ms = _date_to_ms(start_date)
    end_ms = _date_to_ms(end_date)

    # --- Attempt 1: Binance mirrors ---
    raw = _fetch_binance_klines(symbol, interval, start_ms, end_ms)
    if raw:
        return [
            {
                "t": int(k[0]) // 1000,
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
            }
            for k in raw
        ]

    _log.info("Binance failed, trying CoinGecko for %s", symbol)

    # --- Attempt 2: CoinGecko OHLC ---
    # CoinGecko accepts days parameter; max 90 days per call for free tier
    coin_id = "bitcoin" if "BTC" in symbol else symbol.replace("USDT", "").lower()
    days = max(1, (end_ms - start_ms) // (86400 * 1000))
    cg_url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
    cg_data = _http_get_json(cg_url)
    if cg_data and isinstance(cg_data, list) and len(cg_data) > 0:
        return [
            {"t": int(k[0]) // 1000, "o": k[1], "h": k[2], "l": k[3], "c": k[4]}
            for k in cg_data
            if start_ms <= k[0] <= end_ms
        ]

    _log.info("CoinGecko failed, trying CryptoCompare for %s", symbol)

    # --- Attempt 3: CryptoCompare ---
    # Map interval to CC endpoint
    fsym = "BTC" if "BTC" in symbol else symbol.replace("USDT", "")
    if interval in ("1d", "1D"):
        cc_endpoint = "histoday"
    elif interval in ("4h", "4H"):
        cc_endpoint = "histohour"
    else:
        cc_endpoint = "histohour"

    cc_limit = min(2000, days * (24 if cc_endpoint == "histohour" else 1))
    cc_url = (
        f"{CRYPTOCOMPARE_BASE}/{cc_endpoint}"
        f"?fsym={fsym}&tsym=USD&limit={cc_limit}"
        f"&toTs={end_ms // 1000}"
    )
    cc_data = _http_get_json(cc_url)
    if cc_data and isinstance(cc_data, dict) and cc_data.get("Data"):
        entries = cc_data["Data"]
        if isinstance(entries, dict) and "Data" in entries:
            entries = entries["Data"]
        start_s = start_ms // 1000
        end_s = end_ms // 1000
        return [
            {"t": e["time"], "o": e["open"], "h": e["high"],
             "l": e["low"], "c": e["close"]}
            for e in entries
            if start_s <= e.get("time", 0) <= end_s and e.get("close", 0) > 0
        ]

    _log.error("All data sources failed for %s %s", symbol, interval)
    return None


# ---------------------------------------------------------------------------
# Math / statistics helpers
# ---------------------------------------------------------------------------

def _compute_returns(prices: list[float]) -> list[float]:
    """Compute period-over-period returns from a price series."""
    if len(prices) < 2:
        return []
    return [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]


def _max_drawdown(prices: list[float]) -> float:
    """Compute maximum drawdown from a price series. Returns negative pct."""
    if len(prices) < 2:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (p - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd * 100, 4)  # as percentage


def _sharpe_ratio(returns: list[float], periods_per_year: float = 365.0,
                  risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio from a list of periodic returns."""
    if len(returns) < 2:
        return 0.0
    mean_r = statistics.mean(returns)
    std_r = statistics.stdev(returns)
    if std_r == 0:
        return 0.0
    excess = mean_r - (risk_free_rate / periods_per_year)
    return round((excess / std_r) * math.sqrt(periods_per_year), 4)


def _trade_date_sort_key(x: dict) -> str:
    d = x.get("exit_date") or x.get("entry_date") or ""
    return d if isinstance(d, str) else ""


def _equity_curve_from_trades(trades: list[dict]) -> list[float]:
    """Build equity curve from a list of trades with pnl_pct.

    Starts at 1.0 (normalized). Each trade compounds.
    """
    equity = [1.0]
    for t in sorted(trades, key=_trade_date_sort_key):
        pnl = t.get("pnl_pct", 0.0)
        if pnl is None:
            pnl = 0.0
        equity.append(equity[-1] * (1.0 + pnl))
    return equity


# ---------------------------------------------------------------------------
# Benchmark 1: BTC Buy & Hold
# ---------------------------------------------------------------------------

def compute_btc_buy_hold(start_date: str, end_date: str) -> dict:
    """Compute BTC buy-and-hold performance for the given period.

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Returns:
        {"pnl_pct": float, "max_dd": float, "sharpe": float}
    """
    klines = _fetch_klines_with_full_failover("BTCUSDT", "1d", start_date, end_date)

    if not klines or len(klines) < 2:
        _log.warning("Insufficient BTC data for buy-hold benchmark")
        return {"pnl_pct": 0.0, "max_dd": 0.0, "sharpe": 0.0, "error": "insufficient_data"}

    closes = [k["c"] for k in klines]
    total_return = ((closes[-1] / closes[0]) - 1.0) * 100
    max_dd = _max_drawdown(closes)
    daily_returns = _compute_returns(closes)
    sharpe = _sharpe_ratio(daily_returns, periods_per_year=365.0)

    return {
        "pnl_pct": round(total_return, 4),
        "max_dd": max_dd,
        "sharpe": sharpe,
    }


# ---------------------------------------------------------------------------
# Benchmark 2: EMA(9)/EMA(21) Crossover on BTC 4H
# ---------------------------------------------------------------------------

def _ema(values: list[float], period: int) -> list[float]:
    """Compute EMA for a list of values. Returns list of same length (NaN-padded)."""
    if len(values) < period:
        return [float("nan")] * len(values)

    multiplier = 2.0 / (period + 1)
    ema_vals = [float("nan")] * (period - 1)
    # Seed with SMA of first `period` values
    sma = sum(values[:period]) / period
    ema_vals.append(sma)

    for i in range(period, len(values)):
        val = (values[i] - ema_vals[-1]) * multiplier + ema_vals[-1]
        ema_vals.append(val)

    return ema_vals


def compute_ma_crossover_baseline(start_date: str, end_date: str) -> dict:
    """EMA(9)/EMA(21) crossover strategy on BTC 4H candles.

    Buy when EMA9 > EMA21, sell when EMA9 < EMA21.

    Returns:
        {"pnl_pct": float, "wr": float, "trades": int,
         "max_dd": float, "sharpe": float}
    """
    klines = _fetch_klines_with_full_failover("BTCUSDT", "4h", start_date, end_date)

    if not klines or len(klines) < 25:
        _log.warning("Insufficient BTC 4H data for MA crossover benchmark")
        return {"pnl_pct": 0.0, "wr": 0.0, "trades": 0,
                "max_dd": 0.0, "sharpe": 0.0, "error": "insufficient_data"}

    closes = [k["c"] for k in klines]
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)

    # Simulate trades
    trades = []
    in_position = False
    entry_price = 0.0
    equity = [1.0]
    current_equity = 1.0

    for i in range(21, len(closes)):
        e9 = ema9[i]
        e21 = ema21[i]
        prev_e9 = ema9[i - 1]
        prev_e21 = ema21[i - 1]

        if math.isnan(e9) or math.isnan(e21) or math.isnan(prev_e9) or math.isnan(prev_e21):
            continue

        # Buy signal: EMA9 crosses above EMA21
        if not in_position and prev_e9 <= prev_e21 and e9 > e21:
            entry_price = closes[i]
            in_position = True

        # Sell signal: EMA9 crosses below EMA21
        elif in_position and prev_e9 >= prev_e21 and e9 < e21:
            exit_price = closes[i]
            pnl = (exit_price / entry_price) - 1.0
            trades.append({"pnl": pnl})
            current_equity *= (1.0 + pnl)
            equity.append(current_equity)
            in_position = False

    # Close any open position at end
    if in_position and len(closes) > 0:
        exit_price = closes[-1]
        pnl = (exit_price / entry_price) - 1.0
        trades.append({"pnl": pnl})
        current_equity *= (1.0 + pnl)
        equity.append(current_equity)

    total_return = (current_equity - 1.0) * 100
    wins = sum(1 for t in trades if t["pnl"] > 0)
    wr = (wins / len(trades) * 100) if trades else 0.0
    max_dd = _max_drawdown(equity)

    # Sharpe from 4h returns
    period_returns = _compute_returns(equity) if len(equity) > 1 else []
    # ~6 candles/day * 365 = 2190 periods/year for 4h
    sharpe = _sharpe_ratio(period_returns, periods_per_year=2190.0) if period_returns else 0.0

    return {
        "pnl_pct": round(total_return, 4),
        "wr": round(wr, 2),
        "trades": len(trades),
        "max_dd": max_dd,
        "sharpe": sharpe,
    }


# ---------------------------------------------------------------------------
# Our System Performance
# ---------------------------------------------------------------------------

def compute_our_performance(closed_picks_path: str,
                            start_date: str | None = None,
                            end_date: str | None = None) -> dict:
    """Compute performance metrics from our closed picks.

    Args:
        closed_picks_path: Path to closed_picks.json
        start_date: Optional YYYY-MM-DD filter (inclusive)
        end_date: Optional YYYY-MM-DD filter (inclusive)

    Returns:
        {"pnl_pct": float, "wr": float, "trades": int, "avg_win": float,
         "avg_loss": float, "pf": float, "max_dd": float, "sharpe": float}
    """
    try:
        with open(closed_picks_path, "r", encoding="utf-8") as f:
            picks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _log.error("Cannot read closed picks: %s", exc)
        return {
            "pnl_pct": 0.0, "wr": 0.0, "trades": 0, "avg_win": 0.0,
            "avg_loss": 0.0, "pf": 0.0, "max_dd": 0.0, "sharpe": 0.0,
            "error": str(exc),
        }

    if not isinstance(picks, list):
        picks = []

    # Filter by date range
    filtered = []
    for p in picks:
        exit_dt = p.get("exit_date") or p.get("entry_date") or ""
        if start_date and exit_dt < start_date:
            continue
        if end_date and exit_dt > end_date:
            continue
        filtered.append(p)

    if not filtered:
        _log.warning("No closed picks in date range %s to %s", start_date, end_date)
        return {
            "pnl_pct": 0.0, "wr": 0.0, "trades": 0, "avg_win": 0.0,
            "avg_loss": 0.0, "pf": 0.0, "max_dd": 0.0, "sharpe": 0.0,
        }

    # Extract PnL values
    pnls = []
    for p in filtered:
        pnl = p.get("pnl_pct")
        if pnl is not None:
            pnls.append(float(pnl))

    if not pnls:
        return {
            "pnl_pct": 0.0, "wr": 0.0, "trades": 0, "avg_win": 0.0,
            "avg_loss": 0.0, "pf": 0.0, "max_dd": 0.0, "sharpe": 0.0,
        }

    # Win rate
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    wr = (len(wins) / len(pnls)) * 100 if pnls else 0.0

    # Average win / loss
    avg_win = statistics.mean(wins) * 100 if wins else 0.0
    avg_loss = statistics.mean(losses) * 100 if losses else 0.0

    # Profit factor = gross wins / abs(gross losses)
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    pf = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    # Total compounded PnL
    equity_curve = _equity_curve_from_trades(filtered)
    total_pnl = (equity_curve[-1] - 1.0) * 100

    # Max drawdown
    max_dd = _max_drawdown(equity_curve)

    # Sharpe from trade-level returns (approximate: treat each trade as a period)
    sharpe = _sharpe_ratio(pnls, periods_per_year=365.0) if len(pnls) >= 2 else 0.0

    return {
        "pnl_pct": round(total_pnl, 4),
        "wr": round(wr, 2),
        "trades": len(pnls),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "pf": round(pf, 4) if pf != float("inf") else 999.99,
        "max_dd": max_dd,
        "sharpe": sharpe,
    }


# ---------------------------------------------------------------------------
# Main Report Generator
# ---------------------------------------------------------------------------

def generate_comparison_report(
    closed_picks_path: str = "data/closed_picks.json",
) -> dict:
    """Generate full benchmark comparison report.

    Determines date range from closed picks, runs all three benchmarks,
    computes alpha differentials, and saves to data/benchmark_comparison.json.

    Returns the report dict.
    """
    # Resolve path relative to this file's directory
    base_dir = Path(__file__).resolve().parent
    picks_path = base_dir / closed_picks_path
    output_path = base_dir / "data" / "benchmark_comparison.json"

    # Read picks to determine date range
    start_date = None
    end_date = None
    try:
        with open(picks_path, "r", encoding="utf-8") as f:
            picks = json.load(f)
        if isinstance(picks, list) and picks:
            dates = []
            for p in picks:
                for key in ("entry_date", "exit_date"):
                    d = p.get(key)
                    if d and isinstance(d, str) and len(d) >= 10:
                        dates.append(d[:10])
            if dates:
                start_date = min(dates)
                end_date = max(dates)
    except Exception as exc:
        _log.error("Cannot determine date range: %s", exc)

    if not start_date or not end_date:
        now = datetime.now(timezone.utc)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        _log.info("Using default 30-day window: %s to %s", start_date, end_date)

    _log.info("Benchmark period: %s to %s", start_date, end_date)

    # Run benchmarks
    _log.info("Computing our system performance...")
    our = compute_our_performance(str(picks_path), start_date, end_date)

    _log.info("Computing BTC buy-and-hold benchmark...")
    hodl = compute_btc_buy_hold(start_date, end_date)

    _log.info("Computing EMA crossover baseline...")
    ma = compute_ma_crossover_baseline(start_date, end_date)

    # Alpha differentials
    alpha_vs_hodl = round(our.get("pnl_pct", 0.0) - hodl.get("pnl_pct", 0.0), 4)
    alpha_vs_ma = round(our.get("pnl_pct", 0.0) - ma.get("pnl_pct", 0.0), 4)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period": {"start": start_date, "end": end_date},
        "our_system": {
            "pnl_pct": our.get("pnl_pct", 0.0),
            "wr": our.get("wr", 0.0),
            "trades": our.get("trades", 0),
            "sharpe": our.get("sharpe", 0.0),
            "max_dd": our.get("max_dd", 0.0),
            "pf": our.get("pf", 0.0),
        },
        "btc_buy_hold": {
            "pnl_pct": hodl.get("pnl_pct", 0.0),
            "sharpe": hodl.get("sharpe", 0.0),
            "max_dd": hodl.get("max_dd", 0.0),
        },
        "ma_crossover": {
            "pnl_pct": ma.get("pnl_pct", 0.0),
            "wr": ma.get("wr", 0.0),
            "trades": ma.get("trades", 0),
            "sharpe": ma.get("sharpe", 0.0),
            "max_dd": ma.get("max_dd", 0.0),
        },
        "alpha_vs_hodl": alpha_vs_hodl,
        "alpha_vs_ma": alpha_vs_ma,
    }

    # Save report
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    _log.info("Benchmark report saved to %s", output_path)

    # Print summary table to stdout
    print("\n" + "=" * 60)
    print("  BENCHMARK COMPARISON REPORT")
    print("=" * 60)
    print(f"  Period: {start_date} to {end_date}")
    print("-" * 60)
    print(f"  {'Metric':<20} {'Our System':>12} {'BTC HODL':>12} {'EMA Cross':>12}")
    print("-" * 60)
    print(f"  {'PnL %':<20} {our.get('pnl_pct', 0):>11.2f}% {hodl.get('pnl_pct', 0):>11.2f}% {ma.get('pnl_pct', 0):>11.2f}%")
    print(f"  {'Win Rate %':<20} {our.get('wr', 0):>11.2f}% {'N/A':>12} {ma.get('wr', 0):>11.2f}%")
    print(f"  {'Trades':<20} {our.get('trades', 0):>12} {'1':>12} {ma.get('trades', 0):>12}")
    print(f"  {'Sharpe':<20} {our.get('sharpe', 0):>12.4f} {hodl.get('sharpe', 0):>12.4f} {ma.get('sharpe', 0):>12.4f}")
    print(f"  {'Max Drawdown %':<20} {our.get('max_dd', 0):>11.2f}% {hodl.get('max_dd', 0):>11.2f}% {ma.get('max_dd', 0):>11.2f}%")
    print("-" * 60)
    print(f"  Alpha vs HODL:      {alpha_vs_hodl:>+.2f}%")
    print(f"  Alpha vs EMA Cross: {alpha_vs_ma:>+.2f}%")
    print("=" * 60 + "\n")

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    generate_comparison_report()
