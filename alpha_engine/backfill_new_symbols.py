#!/usr/bin/env python3
"""
Backfill closed picks for new symbols that have zero training data.

Fetches 30 days of 1h klines from Binance (with mirror fallbacks),
runs 3 simple strategy backtests (RSI bounce, EMA crossover, Volume spike),
and appends simulated closed picks to closed_picks.json.

Uses only stdlib. No pandas/numpy.
"""

import json
import math
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NEW_SYMBOLS = [
    "ETHFIUSDT", "XMRUSDT", "QNTUSDT", "DEXEUSDT", "LITUSDT",
    "TOMOUSDT", "BAKEUSDT", "HIFIUSDT", "ENJUSDT", "THEUSDT",
    "PIXELUSDT", "SAHARAUSDT", "ANKRUSDT", "HOTUSDT",
]

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")

# ---------------------------------------------------------------------------
# SSL context (skip verification for Binance API)
# ---------------------------------------------------------------------------

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Binance kline fetcher with mirror fallback
# ---------------------------------------------------------------------------

def fetch_klines(symbol, interval="1h", limit=720):
    """Fetch klines from Binance with 3+ mirror fallback."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - 30 * 24 * 60 * 60 * 1000  # 30 days ago

    all_klines = []
    current_start = start_ms

    while current_start < now_ms:
        params = (
            f"symbol={symbol}&interval={interval}"
            f"&startTime={current_start}&limit=1000"
        )
        data = None
        last_err = None
        for mirror in BINANCE_MIRRORS:
            url = f"{mirror}/api/v3/klines?{params}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=_ssl_ctx, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                last_err = e
                continue

        if data is None:
            print(f"  [WARN] All mirrors failed for {symbol}: {last_err}")
            break

        if not data:
            break

        all_klines.extend(data)
        # Move start to after the last candle
        current_start = int(data[-1][0]) + 1

        if len(data) < 1000:
            break

        time.sleep(0.2)  # rate limit courtesy

    return all_klines


def parse_klines(raw):
    """Convert raw Binance klines to list of dicts."""
    candles = []
    for k in raw:
        candles.append({
            "open_time": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": int(k[6]),
        })
    return candles


# ---------------------------------------------------------------------------
# Indicator helpers (pure stdlib)
# ---------------------------------------------------------------------------

def calc_ema(values, period):
    """Exponential moving average."""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    # Seed with SMA
    sma = sum(values[:period]) / period
    result.append(sma)
    mult = 2.0 / (period + 1)
    for i in range(period, len(values)):
        ema_val = (values[i] - result[-1]) * mult + result[-1]
        result.append(ema_val)
    return result


def calc_sma(values, period):
    """Simple moving average."""
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1: i + 1]) / period)
    return result


def calc_rsi(closes, period=14):
    """RSI using Wilder's smoothing."""
    if len(closes) < period + 1:
        return [None] * len(closes)

    result = [None] * period
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1.0 + rs))

    return result


def calc_atr(candles, period=14):
    """Average True Range."""
    if len(candles) < period + 1:
        return [None] * len(candles)

    trs = [None]
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    result = [None] * period
    first_atr = sum(t for t in trs[1:period + 1]) / period
    result.append(first_atr)
    for i in range(period + 1, len(trs)):
        atr_val = (result[-1] * (period - 1) + trs[i]) / period
        result.append(atr_val)

    return result


# ---------------------------------------------------------------------------
# Strategy backtests
# ---------------------------------------------------------------------------

def _make_pick(strategy, symbol, entry_price, exit_price, pnl_pct, status,
               direction, confidence, rsi_at_entry, volume_ratio, atr_at_entry,
               entry_time_ms, exit_time_ms, timeframe="1h", category="crypto"):
    """Create a closed pick dict matching the schema."""
    entry_dt = datetime.fromtimestamp(entry_time_ms / 1000, tz=timezone.utc)
    exit_dt = datetime.fromtimestamp(exit_time_ms / 1000, tz=timezone.utc)
    entry_date = entry_dt.strftime("%Y-%m-%d")
    exit_date = exit_dt.strftime("%Y-%m-%d")
    hold_days = max(0, (exit_dt - entry_dt).days)

    pick_id = f"{strategy}::{symbol}::{entry_date}::{entry_time_ms}"

    if status == "WON":
        exit_reason = "TP_HIT"
    else:
        exit_reason = "SL_HIT"

    tp_pct = abs(pnl_pct) if status == "WON" else 0.03
    sl_pct = abs(pnl_pct) if status == "LOST" else 0.02

    if direction == "LONG":
        take_profit = round(entry_price * (1 + tp_pct), 8)
        stop_loss = round(entry_price * (1 - sl_pct), 8)
    else:
        take_profit = round(entry_price * (1 - tp_pct), 8)
        stop_loss = round(entry_price * (1 + sl_pct), 8)

    extra = {
        "backfill": True,
        "backfill_strategy": strategy,
        "timeframe": timeframe,
        "generated_at": entry_dt.isoformat(),
        "closed_at": exit_dt.isoformat(),
        "transaction_cost_pct": 0.001,
        "gross_pnl_pct": round(pnl_pct + 0.001, 6),
        "net_pnl_pct": round(pnl_pct, 6),
    }

    return {
        "id": pick_id,
        "strategy": strategy,
        "symbol": symbol,
        "category": category,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "entry_price": round(entry_price, 8),
        "entry_date": entry_date,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": round(confidence, 4),
        "ml_score": 0.5,
        "exit_price": round(exit_price, 8),
        "exit_date": exit_date,
        "exit_reason": exit_reason,
        "pnl_pct": round(pnl_pct, 6),
        "pnl_dollar": 0.0,
        "high_water_mark": round(entry_price, 8),
        "status": status,
        "regime_at_entry": "backfill",
        "atr_at_entry": round(atr_at_entry, 8) if atr_at_entry else None,
        "rsi_at_entry": round(rsi_at_entry, 2) if rsi_at_entry else None,
        "volume_ratio": round(volume_ratio, 4) if volume_ratio else None,
        "hold_days": hold_days,
        "extra_json": json.dumps(extra),
    }


def backtest_rsi_bounce(candles, symbol):
    """RSI bounce: Buy when RSI(14) < 30, sell when RSI > 70. TP +3%, SL -2%."""
    closes = [c["close"] for c in candles]
    rsi = calc_rsi(closes, 14)
    atr = calc_atr(candles, 14)
    volumes = [c["volume"] for c in candles]
    vol_sma20 = calc_sma(volumes, 20)

    picks = []
    in_trade = False
    entry_price = 0
    entry_idx = 0
    tp_pct = 0.03
    sl_pct = 0.02

    for i in range(20, len(candles)):
        if rsi[i] is None:
            continue

        if not in_trade and rsi[i] < 30:
            in_trade = True
            entry_price = candles[i]["close"]
            entry_idx = i
        elif in_trade:
            high = candles[i]["high"]
            low = candles[i]["low"]
            current_close = candles[i]["close"]

            # Check SL first (conservative)
            if low <= entry_price * (1 - sl_pct):
                exit_price = entry_price * (1 - sl_pct)
                pnl = -sl_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] else 1.0
                picks.append(_make_pick(
                    "rsi_bounce_backfill", symbol, entry_price, exit_price,
                    pnl, "LOST", "LONG", 0.65,
                    rsi[entry_idx], vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False
            elif high >= entry_price * (1 + tp_pct):
                exit_price = entry_price * (1 + tp_pct)
                pnl = tp_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] else 1.0
                picks.append(_make_pick(
                    "rsi_bounce_backfill", symbol, entry_price, exit_price,
                    pnl, "WON", "LONG", 0.7,
                    rsi[entry_idx], vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False
            elif rsi[i] > 70:
                # RSI exit signal
                pnl_raw = (current_close - entry_price) / entry_price - 0.001
                status = "WON" if pnl_raw > 0 else "LOST"
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] else 1.0
                picks.append(_make_pick(
                    "rsi_bounce_backfill", symbol, entry_price, current_close,
                    pnl_raw, status, "LONG", 0.65,
                    rsi[entry_idx], vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False

    return picks


def backtest_ema_crossover(candles, symbol):
    """EMA crossover: Buy when EMA(9) crosses above EMA(21). TP +4%, SL -2.5%."""
    closes = [c["close"] for c in candles]
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    rsi = calc_rsi(closes, 14)
    atr = calc_atr(candles, 14)
    volumes = [c["volume"] for c in candles]
    vol_sma20 = calc_sma(volumes, 20)

    picks = []
    in_trade = False
    entry_price = 0
    entry_idx = 0
    tp_pct = 0.04
    sl_pct = 0.025

    for i in range(22, len(candles)):
        if ema9[i] is None or ema21[i] is None or ema9[i - 1] is None or ema21[i - 1] is None:
            continue

        cross_up = ema9[i - 1] <= ema21[i - 1] and ema9[i] > ema21[i]

        if not in_trade and cross_up:
            in_trade = True
            entry_price = candles[i]["close"]
            entry_idx = i
        elif in_trade:
            high = candles[i]["high"]
            low = candles[i]["low"]

            if low <= entry_price * (1 - sl_pct):
                exit_price = entry_price * (1 - sl_pct)
                pnl = -sl_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] and vol_sma20[entry_idx] > 0 else 1.0
                picks.append(_make_pick(
                    "ema_crossover_backfill", symbol, entry_price, exit_price,
                    pnl, "LOST", "LONG", 0.6,
                    rsi[entry_idx] if rsi[entry_idx] else 50.0,
                    vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False
            elif high >= entry_price * (1 + tp_pct):
                exit_price = entry_price * (1 + tp_pct)
                pnl = tp_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] and vol_sma20[entry_idx] > 0 else 1.0
                picks.append(_make_pick(
                    "ema_crossover_backfill", symbol, entry_price, exit_price,
                    pnl, "WON", "LONG", 0.7,
                    rsi[entry_idx] if rsi[entry_idx] else 50.0,
                    vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False

    return picks


def backtest_volume_spike(candles, symbol):
    """Volume spike: Buy when vol > 2x 20-period avg and close > open. TP +3%, SL -1.5%."""
    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]
    vol_sma20 = calc_sma(volumes, 20)
    rsi = calc_rsi(closes, 14)
    atr = calc_atr(candles, 14)

    picks = []
    in_trade = False
    entry_price = 0
    entry_idx = 0
    tp_pct = 0.03
    sl_pct = 0.015

    for i in range(20, len(candles)):
        if vol_sma20[i] is None or vol_sma20[i] == 0:
            continue

        vol_ratio = volumes[i] / vol_sma20[i]
        bullish = candles[i]["close"] > candles[i]["open"]

        if not in_trade and vol_ratio > 2.0 and bullish:
            in_trade = True
            entry_price = candles[i]["close"]
            entry_idx = i
        elif in_trade:
            high = candles[i]["high"]
            low = candles[i]["low"]

            if low <= entry_price * (1 - sl_pct):
                exit_price = entry_price * (1 - sl_pct)
                pnl = -sl_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] else 1.0
                picks.append(_make_pick(
                    "volume_spike_backfill", symbol, entry_price, exit_price,
                    pnl, "LOST", "LONG", 0.75,
                    rsi[entry_idx] if rsi[entry_idx] else 50.0,
                    vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False
            elif high >= entry_price * (1 + tp_pct):
                exit_price = entry_price * (1 + tp_pct)
                pnl = tp_pct - 0.001
                vol_r = volumes[entry_idx] / vol_sma20[entry_idx] if vol_sma20[entry_idx] else 1.0
                picks.append(_make_pick(
                    "volume_spike_backfill", symbol, entry_price, exit_price,
                    pnl, "WON", "LONG", 0.80,
                    rsi[entry_idx] if rsi[entry_idx] else 50.0,
                    vol_r, atr[entry_idx],
                    candles[entry_idx]["open_time"], candles[i]["close_time"],
                ))
                in_trade = False

    return picks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Backfill New Symbols -- Closed Picks Generator")
    print("=" * 60)
    print(f"  Symbols: {len(NEW_SYMBOLS)}")
    print(f"  Strategies: rsi_bounce, ema_crossover, volume_spike")
    print(f"  Output: {CLOSED_PICKS_PATH}")
    print("=" * 60)

    all_new_picks = []
    summary = {}

    for sym in NEW_SYMBOLS:
        print(f"\n[{sym}] Fetching 30d 1h klines...")
        raw = fetch_klines(sym, "1h")
        if not raw:
            print(f"  [SKIP] No data returned for {sym}")
            summary[sym] = {"count": 0, "wins": 0, "losses": 0, "avg_pnl": 0.0}
            continue

        candles = parse_klines(raw)
        print(f"  Got {len(candles)} candles")

        if len(candles) < 30:
            print(f"  [SKIP] Not enough candles for {sym}")
            summary[sym] = {"count": 0, "wins": 0, "losses": 0, "avg_pnl": 0.0}
            continue

        picks_rsi = backtest_rsi_bounce(candles, sym)
        picks_ema = backtest_ema_crossover(candles, sym)
        picks_vol = backtest_volume_spike(candles, sym)

        sym_picks = picks_rsi + picks_ema + picks_vol
        all_new_picks.extend(sym_picks)

        wins = sum(1 for p in sym_picks if p["status"] == "WON")
        losses = sum(1 for p in sym_picks if p["status"] == "LOST")
        avg_pnl = sum(p["pnl_pct"] for p in sym_picks) / len(sym_picks) if sym_picks else 0.0

        summary[sym] = {
            "count": len(sym_picks),
            "wins": wins,
            "losses": losses,
            "avg_pnl": avg_pnl,
            "rsi": len(picks_rsi),
            "ema": len(picks_ema),
            "vol": len(picks_vol),
        }

        wr = (wins / len(sym_picks) * 100) if sym_picks else 0
        print(f"  Picks: {len(sym_picks)} (RSI:{len(picks_rsi)} EMA:{len(picks_ema)} VOL:{len(picks_vol)}) | WR: {wr:.1f}% | Avg PnL: {avg_pnl*100:.2f}%")

        time.sleep(0.3)  # rate limit between symbols

    # Load existing closed picks and append
    print(f"\n{'=' * 60}")
    print(f"  Loading existing closed picks...")

    existing = []
    if os.path.exists(CLOSED_PICKS_PATH):
        with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"  Existing picks: {len(existing)}")

    # De-duplicate by id
    existing_ids = {p["id"] for p in existing}
    new_unique = [p for p in all_new_picks if p["id"] not in existing_ids]

    if not new_unique:
        print("  No new picks to add (all duplicates).")
    else:
        combined = existing + new_unique
        with open(CLOSED_PICKS_PATH, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        print(f"  Added {len(new_unique)} new picks (total: {len(combined)})")

    # Final summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  {'Symbol':<14} {'Picks':>6} {'Wins':>6} {'Lost':>6} {'WR%':>7} {'AvgPnL':>9}")
    print(f"  {'-'*14} {'-'*6} {'-'*6} {'-'*6} {'-'*7} {'-'*9}")

    total_picks = 0
    total_wins = 0
    total_losses = 0
    total_pnl_sum = 0.0

    for sym in NEW_SYMBOLS:
        s = summary.get(sym, {})
        cnt = s.get("count", 0)
        w = s.get("wins", 0)
        l = s.get("losses", 0)
        ap = s.get("avg_pnl", 0.0)
        wr = (w / cnt * 100) if cnt > 0 else 0
        total_picks += cnt
        total_wins += w
        total_losses += l
        total_pnl_sum += ap * cnt
        print(f"  {sym:<14} {cnt:>6} {w:>6} {l:>6} {wr:>6.1f}% {ap*100:>8.2f}%")

    overall_wr = (total_wins / total_picks * 100) if total_picks > 0 else 0
    overall_pnl = (total_pnl_sum / total_picks) if total_picks > 0 else 0
    print(f"  {'-'*14} {'-'*6} {'-'*6} {'-'*6} {'-'*7} {'-'*9}")
    print(f"  {'TOTAL':<14} {total_picks:>6} {total_wins:>6} {total_losses:>6} {overall_wr:>6.1f}% {overall_pnl*100:>8.2f}%")
    print(f"\n  Done! {len(new_unique)} backfill picks appended to closed_picks.json")


if __name__ == "__main__":
    main()
