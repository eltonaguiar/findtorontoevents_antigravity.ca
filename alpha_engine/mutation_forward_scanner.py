#!/usr/bin/env python3
"""
Mutation Forward-Test Scanner
=============================
Live scanner for the 9 Keltner compression-expansion mutation survivors.
Reads genomes from data/massive_mutation_results.json, fetches 4h Binance candles,
and generates picks when entry conditions are met NOW.

Output: data/mutation_forward_picks.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(BASE_DIR, "data", "massive_mutation_results.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "mutation_forward_picks.json")

SYMBOLS = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT", "AVAXUSDT"]
INTERVAL = "4h"
LIMIT = 200  # candles to fetch

_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = INTERVAL, limit: int = LIMIT) -> list[dict]:
    """Fetch OHLCV candles from Binance with endpoint failover."""
    for base in _BINANCE_KLINE_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MutationScanner/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
            candles = []
            for k in raw:
                candles.append({
                    "ts": int(k[0]),
                    "o": float(k[1]),
                    "h": float(k[2]),
                    "l": float(k[3]),
                    "c": float(k[4]),
                    "v": float(k[5]),
                })
            return candles
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next
            print(f"  [WARN] {symbol} fetch from {base} failed: HTTP {e.code}")
        except (urllib.error.URLError, OSError) as e:
            print(f"  [WARN] {symbol} fetch from {base} failed: {e}")
            continue
    print(f"  [ERROR] Could not fetch {symbol} from any Binance endpoint")
    return []


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average. Returns list same length as input (NaN-padded)."""
    out = [float("nan")] * len(values)
    if len(values) < period or period < 1:
        return out
    # Seed with SMA
    sma = sum(values[:period]) / period
    out[period - 1] = sma
    k = 2.0 / (period + 1)
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def atr(candles: list[dict], period: int) -> list[float]:
    """Average True Range. Returns list same length as candles."""
    out = [float("nan")] * len(candles)
    if len(candles) < 2 or period < 1:
        return out
    trs = []
    for i in range(len(candles)):
        h, l, c_prev = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"] if i > 0 else candles[i]["o"]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    # EMA-smoothed ATR
    return ema(trs, period)


def hma(values: list[float], period: int) -> list[float]:
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    n = max(period, 2)
    half = max(n // 2, 1)
    sqrt_n = max(int(n ** 0.5), 1)

    wma_half = wma(values, half)
    wma_full = wma(values, n)

    # 2*WMA(half) - WMA(full)
    diff = []
    for i in range(len(values)):
        if _isnan(wma_half[i]) or _isnan(wma_full[i]):
            diff.append(float("nan"))
        else:
            diff.append(2.0 * wma_half[i] - wma_full[i])

    return wma(diff, sqrt_n)


def wma(values: list[float], period: int) -> list[float]:
    """Weighted Moving Average."""
    out = [float("nan")] * len(values)
    if period < 1 or len(values) < period:
        return out
    denom = period * (period + 1) / 2.0
    for i in range(period - 1, len(values)):
        if any(_isnan(values[i - period + 1 + j]) for j in range(period)):
            continue
        s = sum(values[i - period + 1 + j] * (j + 1) for j in range(period))
        out[i] = s / denom
    return out


def sma(values: list[float], period: int) -> list[float]:
    """Simple Moving Average."""
    out = [float("nan")] * len(values)
    if period < 1 or len(values) < period:
        return out
    running = sum(values[:period])
    out[period - 1] = running / period
    for i in range(period, len(values)):
        running += values[i] - values[i - period]
        out[i] = running / period
    return out


def _isnan(v):
    return v != v  # NaN != NaN


# ---------------------------------------------------------------------------
# Keltner compression-expansion strategy
# ---------------------------------------------------------------------------
def evaluate_genome(genome: dict, candles: list[dict], symbol: str) -> dict | None:
    """
    Evaluate a single genome against current candle data for one symbol.
    Returns a pick dict if entry conditions are met NOW, else None.
    """
    genes = genome["genes"]
    ema_p = int(genes["ema_period"])
    atr_p = int(genes["atr_period"])
    ch_mult = float(genes["channel_mult"])
    comp_window = int(genes["comp_window"])
    min_edge = float(genes["min_edge"])
    vol_confirm = float(genes["volume_confirm"])
    hma_p = int(genes["hma_period"])
    tp_mult = float(genes["tp_atr_mult"])
    sl_mult = float(genes["sl_atr_mult"])
    trend_str_min = float(genes["trend_strength_min"])

    if len(candles) < max(ema_p, atr_p, comp_window, hma_p) + 10:
        return None

    closes = [c["c"] for c in candles]
    volumes = [c["v"] for c in candles]

    ema_vals = ema(closes, ema_p)
    atr_vals = atr(candles, atr_p)
    hma_vals = hma(closes, hma_p)
    vol_sma = sma(volumes, 20)

    # We need the last 2 bars to detect state transition
    idx = len(candles) - 1  # current (latest) bar
    idx_prev = idx - 1

    if any(_isnan(v) for v in [ema_vals[idx], atr_vals[idx], hma_vals[idx],
                                 ema_vals[idx_prev], atr_vals[idx_prev]]):
        return None
    if _isnan(vol_sma[idx]):
        return None

    # Channel bounds
    def channel(i):
        e, a = ema_vals[i], atr_vals[i]
        if _isnan(e) or _isnan(a) or e == 0:
            return None, None, None
        upper = e + ch_mult * a
        lower = e - ch_mult * a
        width = (upper - lower) / e
        return upper, lower, width

    # Check compression over the comp_window: count bars where width < min_edge
    compression_count = 0
    lookback_start = max(0, idx - comp_window)
    for i in range(lookback_start, idx):
        u, l, w = channel(i)
        if w is not None and w < min_edge:
            compression_count += 1

    # Require at least 30% of the window to have been compressed
    compression_ratio = compression_count / max(comp_window, 1)
    is_recently_compressed = compression_ratio >= 0.3

    # Current bar channel
    upper_now, lower_now, width_now = channel(idx)
    upper_prev, lower_prev, width_prev = channel(idx_prev)
    if upper_now is None or upper_prev is None:
        return None

    # Expansion: current width exceeds min_edge while recently compressed
    is_expanding = width_now >= min_edge and is_recently_compressed

    # Check if price is breaking out of channel
    close_now = closes[idx]
    close_prev = closes[idx_prev]

    breakout_long = close_now > upper_now and close_prev <= upper_prev
    breakout_short = close_now < lower_now and close_prev >= lower_prev

    if not is_expanding and not breakout_long and not breakout_short:
        # Also check: price already above channel (continuation)
        if close_now > upper_now and is_recently_compressed:
            breakout_long = True
        elif close_now < lower_now and is_recently_compressed:
            breakout_short = True

    if not breakout_long and not breakout_short:
        return None

    # HMA trend filter
    if not _isnan(hma_vals[idx]) and not _isnan(hma_vals[idx_prev]):
        hma_rising = hma_vals[idx] > hma_vals[idx_prev]
        hma_falling = hma_vals[idx] < hma_vals[idx_prev]
        if breakout_long and not hma_rising:
            return None
        if breakout_short and not hma_falling:
            return None

    # Trend strength filter
    if trend_str_min > 0 and ema_vals[idx] != 0:
        ema_slope = abs(ema_vals[idx] - ema_vals[idx_prev]) / ema_vals[idx]
        if ema_slope < trend_str_min:
            return None

    # Volume confirmation
    if vol_confirm > 0 and not _isnan(vol_sma[idx]):
        vol_ratio = volumes[idx] / vol_sma[idx] if vol_sma[idx] > 0 else 0
        if vol_ratio < vol_confirm:
            return None

    # Build pick
    signal = "BUY" if breakout_long else "SELL"
    current_atr = atr_vals[idx]
    entry = close_now

    if signal == "BUY":
        tp = entry + tp_mult * current_atr
        sl = entry - sl_mult * current_atr
    else:
        tp = entry - tp_mult * current_atr
        sl = entry + sl_mult * current_atr

    # Confidence from genome fitness + backtest win rate
    bt_wr = genome["details"].get("win_rate", 0.5)
    fitness = genome.get("fitness", 0.3)
    sym_sharpe = genome["details"].get("symbol_sharpes", {}).get(symbol, 0)
    confidence = round(min(0.95, bt_wr * 0.4 + fitness * 0.3 + min(sym_sharpe, 1.0) * 0.3), 4)

    return {
        "symbol": symbol,
        "signal": signal,
        "entry_price": round(entry, 8),
        "take_profit": round(tp, 8),
        "stop_loss": round(sl, 8),
        "genome_id": genome["genome_id"],
        "confidence": confidence,
        "strategy": "mutation_keltner",
        "backtest_win_rate": bt_wr,
        "backtest_profit_factor": genome["details"].get("profit_factor", 0),
        "backtest_trades": genome["details"].get("trade_count", 0),
        "genome_fitness": fitness,
        "compression_ratio": round(compression_ratio, 4),
        "channel_width": round(width_now, 6) if width_now else None,
        "atr_value": round(current_atr, 8),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("MUTATION FORWARD-TEST SCANNER")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Load genomes
    if not os.path.exists(RESULTS_PATH):
        print(f"[ERROR] Results file not found: {RESULTS_PATH}")
        sys.exit(1)

    with open(RESULTS_PATH, "r") as f:
        data = json.load(f)

    genomes = data.get("top_genomes", [])
    print(f"Loaded {len(genomes)} mutation survivors")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Interval: {INTERVAL} | Candles: {LIMIT}")
    print("-" * 60)

    # Fetch candle data for all symbols (cache to avoid re-fetching)
    candle_cache: dict[str, list[dict]] = {}
    for sym in SYMBOLS:
        print(f"Fetching {sym} {INTERVAL} candles...", end=" ")
        candles = fetch_klines(sym)
        candle_cache[sym] = candles
        print(f"got {len(candles)} candles")
        time.sleep(0.2)  # rate limit courtesy

    print("-" * 60)

    # Evaluate all genome x symbol combinations
    picks = []
    for genome in genomes:
        gid = genome["genome_id"]
        for sym in SYMBOLS:
            candles = candle_cache.get(sym, [])
            if not candles:
                continue
            pick = evaluate_genome(genome, candles, sym)
            if pick:
                picks.append(pick)
                direction = "LONG" if pick["signal"] == "BUY" else "SHORT"
                print(f"  PICK: {gid} | {sym} {direction} @ {pick['entry_price']:.4f} "
                      f"| TP {pick['take_profit']:.4f} | SL {pick['stop_loss']:.4f} "
                      f"| conf={pick['confidence']:.3f}")

    print("-" * 60)
    print(f"Total picks generated: {len(picks)}")

    # Sort by confidence descending
    picks.sort(key=lambda x: x["confidence"], reverse=True)

    # Consensus: count how many genomes agree on each symbol+direction
    consensus = {}
    for p in picks:
        key = f"{p['symbol']}_{p['signal']}"
        consensus.setdefault(key, []).append(p["genome_id"])

    if consensus:
        print("\nConsensus signals:")
        for key, gids in sorted(consensus.items(), key=lambda x: -len(x[1])):
            sym, sig = key.rsplit("_", 1)
            print(f"  {sym} {sig}: {len(gids)} genomes agree ({', '.join(gids)})")

    # Build output
    output = {
        "metadata": {
            "scanner": "mutation_forward_scanner",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "genomes_evaluated": len(genomes),
            "symbols_scanned": SYMBOLS,
            "interval": INTERVAL,
            "total_picks": len(picks),
            "consensus": {k: len(v) for k, v in consensus.items()},
        },
        "picks": picks,
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput saved to: {OUTPUT_PATH}")
    print("=" * 60)
    return picks


if __name__ == "__main__":
    main()
