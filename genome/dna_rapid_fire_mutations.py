#!/usr/bin/env python3
"""
DNA Rapid Fire Mutations — Quality-Filtered Variants of Rapid Fire System
==========================================================================

Parent System: rapid_fire (currently in PROBATION tier, 0.15 weight)
  - Problem: High-frequency noise, no proven edge
  - Generates many picks but most are losers
  - Needs heavy filtering to extract any signal from the noise

Mutations (all focused on noise reduction):
  f. rapid_trend_only_mut       — Only fire in direction of 200-EMA trend
  g. rapid_momentum_filter_mut  — Require MACD histogram confirmation
  h. rapid_volume_gate_mut      — Only fire when volume > 1.3x average
  i. rapid_top10_only_mut       — Restrict to top-10 crypto by market cap
  j. rapid_rsi_filter_mut       — RSI(14) < 60 for LONG, > 40 for SHORT

All mutations are SANDBOX tier (0.30 weight) until proven via forward testing.
TP = 2x ATR, SL = 1.5x ATR (standard genome format).

Data Sources: Binance API (klines)
Output: Standard pick format consumed by forward_validator / battleground pipeline
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Try importing indicators from ml_battleground shared
try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
    # Inline fallback indicators
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50.0)

    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


# ── Helpers ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 parent_system: str, mutation_type: str, **extra) -> dict:
    """Create standardized signal dict with mutation metadata."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "direction": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "source_system": "genome",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "parent_system": parent_system,
        "mutation_type": mutation_type,
    }
    sig.update(extra)
    return sig


# ── Data Fetching (Binance klines) ────────────────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Full symbol universe for rapid fire
RAPID_FIRE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
    "LTCUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "SEIUSDT",
    "ATOMUSDT", "MATICUSDT", "TRXUSDT", "OPUSDT", "ARBUSDT",
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT", "FLOKIUSDT", "WIFUSDT",
]

# Top-10 market cap symbols only (for top10 mutation)
TOP10_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
]


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DNARapidFire/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    return pd.DataFrame()


# ── Rapid Fire Base Signal Detection ──────────────────────────────────────
# The original rapid_fire generates signals on almost any price movement.
# These helpers detect the base "rapid fire" trigger that each mutation
# then filters down.

def _detect_rapid_signal(df: pd.DataFrame) -> Optional[str]:
    """
    Detect rapid fire base signal: short-term momentum shift.
    Returns 'BUY' or 'SELL' or None.

    Uses EMA(5) vs EMA(13) crossover on latest bar — fast momentum detection.
    """
    if len(df) < 15:
        return None

    close = df["Close"]
    ema_5 = ema(close, 5)
    ema_13 = ema(close, 13)

    e5_now = float(ema_5.iloc[-1])
    e5_prev = float(ema_5.iloc[-2])
    e13_now = float(ema_13.iloc[-1])
    e13_prev = float(ema_13.iloc[-2])

    if pd.isna(e5_now) or pd.isna(e13_now) or pd.isna(e5_prev) or pd.isna(e13_prev):
        return None

    # Bullish crossover
    if e5_prev <= e13_prev and e5_now > e13_now:
        return "BUY"
    # Bearish crossover
    if e5_prev >= e13_prev and e5_now < e13_now:
        return "SELL"

    return None


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION F: rapid_trend_only_mut
# Only fire in direction of 200-EMA trend. No counter-trend trades.
# ═══════════════════════════════════════════════════════════════════════════

def rapid_trend_only_mut(data: dict) -> list[dict]:
    """
    Rapid Fire + 200-EMA trend filter.

    Problem: Original rapid fire fires in both directions regardless of trend,
    leading to many counter-trend losers. This mutation only allows:
    - BUY signals when price > 200-EMA (uptrend)
    - SELL signals when price < 200-EMA (downtrend)

    Expected: Cuts noise by ~50%, should improve WR from ~35% to ~50-55%
    """
    signals = []

    for symbol in RAPID_FIRE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Detect base rapid fire signal
        direction = _detect_rapid_signal(df)
        if direction is None:
            continue

        # 200-EMA TREND GATE
        ema_200 = float(ema(close, 200).iloc[-1])
        if pd.isna(ema_200):
            continue

        # Only trade WITH the trend
        if direction == "BUY" and current <= ema_200:
            continue  # No counter-trend longs
        if direction == "SELL" and current >= ema_200:
            continue  # No counter-trend shorts

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        trend_dist = abs(current - ema_200) / ema_200

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        conf = min(0.80, 0.42 + trend_dist * 2.0)

        signals.append(_base_signal(
            "rapid_trend_only_mut", symbol, direction, current, tp, sl, conf,
            f"RapidFire trend-only: {direction} with 200-EMA trend, "
            f"price {'above' if direction == 'BUY' else 'below'} EMA200=${ema_200:.4f} "
            f"({trend_dist:.2%} distance) — no counter-trend trades",
            parent_system="rapid_fire",
            mutation_type="trend_filter",
            ema_200=_smart_round(ema_200),
            trend_distance=round(trend_dist, 4),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION G: rapid_momentum_filter_mut
# Require MACD histogram positive for LONG, negative for SHORT
# ═══════════════════════════════════════════════════════════════════════════

def rapid_momentum_filter_mut(data: dict) -> list[dict]:
    """
    Rapid Fire + MACD momentum confirmation.

    Problem: Rapid fire signals lack momentum confirmation. Many signals fire
    during choppy/ranging markets. Adding MACD histogram confirmation ensures
    underlying momentum supports the signal direction.

    BUY requires: MACD histogram > 0 (bullish momentum)
    SELL requires: MACD histogram < 0 (bearish momentum)

    Expected: Filters ~40% of noise — WR ~48-55%
    """
    signals = []

    for symbol in RAPID_FIRE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        direction = _detect_rapid_signal(df)
        if direction is None:
            continue

        # MACD HISTOGRAM GATE
        ema_12 = ema(close, 12)
        ema_26 = ema(close, 26)
        macd_line = ema_12 - ema_26
        signal_line = ema(macd_line, 9)
        histogram = macd_line - signal_line

        hist_val = float(histogram.iloc[-1])
        if pd.isna(hist_val):
            continue

        # Direction must match histogram
        if direction == "BUY" and hist_val <= 0:
            continue  # No bullish signal without bullish momentum
        if direction == "SELL" and hist_val >= 0:
            continue  # No bearish signal without bearish momentum

        # Bonus: histogram accelerating
        hist_prev = float(histogram.iloc[-2]) if len(histogram) > 1 else 0
        accelerating = (direction == "BUY" and hist_val > hist_prev) or \
                       (direction == "SELL" and hist_val < hist_prev)

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        conf = min(0.80, 0.44 + abs(hist_val) / current * 500 + (0.05 if accelerating else 0))

        signals.append(_base_signal(
            "rapid_momentum_filter_mut", symbol, direction, current, tp, sl, conf,
            f"RapidFire MACD-confirmed: {direction}, histogram={hist_val:.6f} "
            f"({'accelerating' if accelerating else 'steady'}) — momentum confirmed",
            parent_system="rapid_fire",
            mutation_type="momentum_filter",
            macd_histogram=round(hist_val, 8),
            histogram_accelerating=accelerating,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION H: rapid_volume_gate_mut
# Only fire when volume > 1.3x average (confirms move has participation)
# ═══════════════════════════════════════════════════════════════════════════

def rapid_volume_gate_mut(data: dict) -> list[dict]:
    """
    Rapid Fire + volume participation gate.

    Problem: Many rapid fire signals fire on thin volume — price moves that
    have no real institutional participation and quickly reverse. This mutation
    requires volume > 1.3x 20-bar average to confirm the move is real.

    Entry: rapid fire signal + volume > 1.3x avg
    Expected: Removes ~50% of low-volume fakeouts — WR ~50-58%
    """
    signals = []

    for symbol in RAPID_FIRE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        direction = _detect_rapid_signal(df)
        if direction is None:
            continue

        # VOLUME GATE: must have participation
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 1.3:
            continue  # Low volume = no conviction, skip

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        conf = min(0.80, 0.44 + (vol_ratio - 1.3) * 0.10)

        signals.append(_base_signal(
            "rapid_volume_gate_mut", symbol, direction, current, tp, sl, conf,
            f"RapidFire volume-confirmed: {direction}, vol={vol_ratio:.1f}x avg "
            f"(>{1.3}x threshold) — move has real participation",
            parent_system="rapid_fire",
            mutation_type="volume_gate",
            volume_ratio=round(vol_ratio, 2),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION I: rapid_top10_only_mut
# Restrict to top-10 crypto by market cap
# ═══════════════════════════════════════════════════════════════════════════

def rapid_top10_only_mut(data: dict) -> list[dict]:
    """
    Rapid Fire restricted to top-10 market cap coins.

    Problem: Rapid fire on small/mid caps generates tons of noise because
    these coins have lower liquidity and wider bid-ask spreads. Top-10 coins
    have the deepest order books and most predictable price action.

    Universe: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, LINK, DOGE
    Entry: rapid fire signal on top-10 coin + basic RSI sanity check
    Expected: Cleaner signals on liquid assets — WR ~48-55%
    """
    signals = []

    for symbol in TOP10_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        direction = _detect_rapid_signal(df)
        if direction is None:
            continue

        # Basic RSI sanity: not at extremes
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue
        # Don't BUY when RSI > 75 (overbought), don't SELL when RSI < 25 (oversold)
        if direction == "BUY" and rsi_14 > 75:
            continue
        if direction == "SELL" and rsi_14 < 25:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        conf = min(0.80, 0.46 + abs(50 - rsi_14) / 200)

        signals.append(_base_signal(
            "rapid_top10_only_mut", symbol, direction, current, tp, sl, conf,
            f"RapidFire top-10: {direction} on {symbol} (top-10 mktcap), "
            f"RSI={rsi_14:.1f} — liquid large-cap only",
            parent_system="rapid_fire",
            mutation_type="top10_filter",
            rsi_14=round(rsi_14, 1),
            is_top10=True,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION J: rapid_rsi_filter_mut
# RSI(14) must be < 60 for LONG (not overbought), > 40 for SHORT
# ═══════════════════════════════════════════════════════════════════════════

def rapid_rsi_filter_mut(data: dict) -> list[dict]:
    """
    Rapid Fire + RSI overbought/oversold filter.

    Problem: Rapid fire often BUYs near tops (RSI > 70) and SELLs near
    bottoms (RSI < 30), resulting in immediate reversals. This mutation
    requires RSI to be in a favorable zone:
    - LONG: RSI < 60 (not overbought, room to run)
    - SHORT: RSI > 40 (not oversold, room to fall)

    Expected: Removes top/bottom chasing — WR ~50-58%
    """
    signals = []

    for symbol in RAPID_FIRE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        direction = _detect_rapid_signal(df)
        if direction is None:
            continue

        # RSI FILTER
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue

        if direction == "BUY" and rsi_14 >= 60:
            continue  # Too overbought for a long entry
        if direction == "SELL" and rsi_14 <= 40:
            continue  # Too oversold for a short entry

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
            # Lower RSI = more room to run = higher confidence
            rsi_bonus = (60 - rsi_14) / 150
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val
            rsi_bonus = (rsi_14 - 40) / 150

        conf = min(0.80, 0.44 + rsi_bonus)

        signals.append(_base_signal(
            "rapid_rsi_filter_mut", symbol, direction, current, tp, sl, conf,
            f"RapidFire RSI-filtered: {direction}, RSI={rsi_14:.1f} "
            f"({'<60 room to run' if direction == 'BUY' else '>40 room to fall'}) "
            f"— not chasing extremes",
            parent_system="rapid_fire",
            mutation_type="rsi_filter",
            rsi_14=round(rsi_14, 1),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY — All Rapid Fire Mutations
# ═══════════════════════════════════════════════════════════════════════════

DNA_RAPID_FIRE_MUTATIONS = {
    "rapid_trend_only_mut": {
        "fn": rapid_trend_only_mut,
        "parent": "rapid_fire",
        "mutation": "trend_filter",
        "trust_weight": 0.3,
        "description": "Only fire in direction of 200-EMA trend — no counter-trend",
    },
    "rapid_momentum_filter_mut": {
        "fn": rapid_momentum_filter_mut,
        "parent": "rapid_fire",
        "mutation": "momentum_filter",
        "trust_weight": 0.3,
        "description": "Require MACD histogram direction match — momentum confirmed",
    },
    "rapid_volume_gate_mut": {
        "fn": rapid_volume_gate_mut,
        "parent": "rapid_fire",
        "mutation": "volume_gate",
        "trust_weight": 0.3,
        "description": "Volume > 1.3x avg — confirms move has real participation",
    },
    "rapid_top10_only_mut": {
        "fn": rapid_top10_only_mut,
        "parent": "rapid_fire",
        "mutation": "top10_filter",
        "trust_weight": 0.3,
        "description": "Top-10 market cap only — liquid large-cap signals",
    },
    "rapid_rsi_filter_mut": {
        "fn": rapid_rsi_filter_mut,
        "parent": "rapid_fire",
        "mutation": "rsi_filter",
        "trust_weight": 0.3,
        "description": "RSI < 60 for LONG, > 40 for SHORT — no extreme chasing",
    },
}

# Total: 5 mutations of rapid_fire (noise reduction focused)


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER — Fetch data & execute all mutations
# ═══════════════════════════════════════════════════════════════════════════

ALL_SCAN_SYMBOLS = sorted(set(RAPID_FIRE_SYMBOLS))


def run_all_mutations(interval: str = "1h", limit: int = 300) -> dict:
    """
    Fetch market data and run all 5 Rapid Fire DNA mutations.

    Returns:
        {
            "metadata": {...},
            "picks": [...],
            "mutations_triggered": [...],
            "mutations_silent": [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"DNA RAPID FIRE MUTATIONS — {len(DNA_RAPID_FIRE_MUTATIONS)} strategies")
    print(f"Focus: Noise reduction from PROBATION-tier rapid_fire system")
    print(f"Scanning {len(ALL_SCAN_SYMBOLS)} symbols on {interval}")
    print(f"{'='*70}\n")

    # Fetch data for all symbols
    data = {}
    for symbol in ALL_SCAN_SYMBOLS:
        df = fetch_binance_klines(symbol, interval=interval, limit=limit)
        if not df.empty and len(df) > 20:
            data[symbol] = df
            print(f"  [OK] {symbol}: {len(df)} bars")
        else:
            print(f"  [--] {symbol}: no data")

    print(f"\nFetched data for {len(data)}/{len(ALL_SCAN_SYMBOLS)} symbols\n")

    # Run all mutations
    all_picks = []
    triggered = []
    silent = []

    for name, info in DNA_RAPID_FIRE_MUTATIONS.items():
        try:
            picks = info["fn"](data)

            if picks:
                for p in picks:
                    p["timeframe"] = p.get("timeframe", interval)
                all_picks.extend(picks)
                triggered.append({
                    "strategy": name,
                    "parent": info["parent"],
                    "mutation": info["mutation"],
                    "picks": len(picks),
                })
                print(f"  [SIGNAL] {name}: {len(picks)} picks")
            else:
                silent.append(name)
                print(f"  [quiet] {name}: 0 picks")
        except Exception as e:
            silent.append(name)
            print(f"  [ERROR] {name}: {e}")

    # Sort by confidence
    all_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    result = {
        "metadata": {
            "timestamp": _now_iso(),
            "total_mutations": len(DNA_RAPID_FIRE_MUTATIONS),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "mutations_silent": len(silent),
            "symbols_scanned": len(data),
            "interval": interval,
            "system": "dna_rapid_fire_mutations",
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
        "mutations_silent": silent,
    }

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_picks)} picks from {len(triggered)}/{len(DNA_RAPID_FIRE_MUTATIONS)} mutations")
    print(f"{'='*70}\n")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Rapid Fire Mutations Scanner (Noise Reduction)")
    parser.add_argument("--interval", default="1h", choices=["1h", "4h", "1d"],
                        help="Kline interval (default: 1h)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Number of bars to fetch (default: 300)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: genome/data/rapid_fire_mutation_picks.json)")
    args = parser.parse_args()

    output_path = args.output or str(ROOT / "genome" / "data" / "rapid_fire_mutation_picks.json")

    result = run_all_mutations(interval=args.interval, limit=args.limit)

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Saved {result['metadata']['total_picks']} picks to {output_path}")

    # Summary
    if result["picks"]:
        print("\nTop 5 picks by confidence:")
        for i, p in enumerate(result["picks"][:5], 1):
            print(f"  {i}. {p['symbol']} {p['signal_type']} | "
                  f"conf={p['confidence']:.2f} | "
                  f"R:R={p['risk_reward']:.1f} | "
                  f"{p['strategy']} ({p['mutation_type']})")
