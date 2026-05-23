#!/usr/bin/env python3
"""
Antigravity V2 Restricted — Category-Locked Production Variants
================================================================

Created: 2026-03-14 by Antigravity AI
Based on: V2 backtest results showing category-specific edges

These are the PRODUCTION variants of V2 mutations, restricted to ONLY
the asset categories where they showed a proven edge:

  ag_momentum_cascade_meme   — MEME coins ONLY (57.1% WR, +14.59% PnL, 1.79 PF)
  ag_gravity_well_majors     — Tier 1 Majors ONLY (45.2% WR, +15.20% PnL, 1.42 PF)

Also includes a live pick generator that fetches current Binance data
and outputs forward-test picks with full documentation.
"""

from __future__ import annotations

import json
import sys
import time
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from genome.mutation_lab.antigravity_mutations_v2 import (
    _ema, _atr, _bb_width, _base_signal, _smart_round,
    momentum_cascade, gravity_well,
    FAST_BARS, MEDIUM_BARS, SLOW_BARS, MIN_MOMENTUM_PCT,
    BB_COMPRESSION_LOOKBACK, VOLUME_IGNITION_MULT,
)

# ═══════════════════════════════════════════════════════════════════════
# Category-Restricted Symbol Lists (PROVEN edges only)
# ═══════════════════════════════════════════════════════════════════════

MEME_ONLY = [
    "DOGEUSDT", "SHIBUSDT", "WLDUSDT", "WIFUSDT",
    "1000PEPEUSDT", "1000BONKUSDT", "1000FLOKIUSDT",
]

MAJORS_ONLY = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
]

# Also include JUP since it was our best symbol across all mutations
JUPUSDT_SPECIAL = ["JUPUSDT"]

# Full universe for unrestricted scans (just picks, no trading)
FULL_SCAN = MEME_ONLY + MAJORS_ONLY + JUPUSDT_SPECIAL


# ═══════════════════════════════════════════════════════════════════════
# Data Fetcher
# ═══════════════════════════════════════════════════════════════════════

def fetch_live_klines(symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Fetch live klines from Binance."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            "OpenTime", "Open", "High", "Low", "Close", "Volume",
            "CloseTime", "QuoteVolume", "Trades", "TakerBuyBase",
            "TakerBuyQuote", "Ignore"
        ])
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit="ms")
        return df
    except Exception as e:
        print(f"  ERROR fetching {symbol}: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════
# AG_MOMENTUM_CASCADE_MEME — Restricted to MEME coins only
# ═══════════════════════════════════════════════════════════════════════

def momentum_cascade_meme(data: dict) -> list[dict]:
    """
    Production variant: Momentum Cascade restricted to MEME coins.
    Backtest: 57.1% WR, +14.59% PnL, 1.79 PF on 56 trades.
    """
    signals = []
    for symbol in MEME_ONLY:
        df = data.get(symbol)
        if df is None or len(df) < SLOW_BARS + 5:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        ret_fast = (current - float(close.iloc[-FAST_BARS - 1])) / float(close.iloc[-FAST_BARS - 1])
        ret_medium = (current - float(close.iloc[-MEDIUM_BARS - 1])) / float(close.iloc[-MEDIUM_BARS - 1])
        ret_slow = (current - float(close.iloc[-SLOW_BARS - 1])) / float(close.iloc[-SLOW_BARS - 1])

        all_bullish = (ret_fast > MIN_MOMENTUM_PCT and ret_medium > MIN_MOMENTUM_PCT and ret_slow > MIN_MOMENTUM_PCT)
        all_bearish = (ret_fast < -MIN_MOMENTUM_PCT and ret_medium < -MIN_MOMENTUM_PCT and ret_slow < -MIN_MOMENTUM_PCT)

        if not all_bullish and not all_bearish:
            continue

        direction = "BUY" if all_bullish else "SELL"
        atr_val = float(_atr(high, low, close, 14).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        total_momentum = abs(ret_fast) + abs(ret_medium) + abs(ret_slow)
        is_accelerating = (ret_fast > ret_medium > ret_slow) if direction == "BUY" else (ret_fast < ret_medium < ret_slow)

        if direction == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val

        conf = min(0.82, 0.55 + total_momentum * 3 + (0.08 if is_accelerating else 0))
        accel_tag = "ACCELERATING" if is_accelerating else "aligned"

        signals.append(_base_signal(
            "ag_momentum_cascade_meme", symbol, direction, current, tp, sl, conf,
            f"Momentum Cascade MEME: fast={ret_fast:+.2%} med={ret_medium:+.2%} "
            f"slow={ret_slow:+.2%} -- {accel_tag} triple-speed {direction}",
            parent_system="battleground",
            mutation_type="momentum_cascade_meme_restricted",
            ret_fast_pct=round(ret_fast * 100, 3),
            ret_medium_pct=round(ret_medium * 100, 3),
            ret_slow_pct=round(ret_slow * 100, 3),
            total_momentum_pct=round(total_momentum * 100, 3),
            is_accelerating=is_accelerating,
            timeframe="1h",
            category_restriction="MEME_COINS_ONLY",
            backtest_wr="57.1%",
            backtest_pf="1.79",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════
# AG_GRAVITY_WELL_MAJORS — Restricted to Tier 1 Majors only
# ═══════════════════════════════════════════════════════════════════════

def gravity_well_majors(data: dict) -> list[dict]:
    """
    Production variant: Gravity Well restricted to Tier 1 Majors.
    Backtest: 45.2% WR, +15.20% PnL, 1.42 PF on 42 trades.
    """
    signals = []
    for symbol in MAJORS_ONLY:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        bb_w = _bb_width(close, 20)
        if bb_w.isna().iloc[-1]:
            continue

        current_bw = float(bb_w.iloc[-1])
        recent_bw = bb_w.iloc[-BB_COMPRESSION_LOOKBACK:]
        min_bw = float(recent_bw.min())

        if min_bw <= 0:
            continue
        if current_bw > min_bw * 1.10:
            continue

        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        if vol_avg <= 0:
            continue
        vol_ratio = float(volume.iloc[-1]) / vol_avg

        if vol_ratio < VOLUME_IGNITION_MULT:
            continue

        sma_20 = float(close.rolling(20).mean().iloc[-1])
        if pd.isna(sma_20) or sma_20 <= 0:
            continue

        if current > sma_20:
            direction = "BUY"
        elif current < sma_20:
            direction = "SELL"
        else:
            continue

        atr_val = float(_atr(high, low, close, 14).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        bb_avg_50 = bb_w.rolling(50).mean().iloc[-1]
        compression_ratio = min_bw / float(bb_avg_50) if not pd.isna(bb_avg_50) and float(bb_avg_50) > 0 else 1.0

        if direction == "BUY":
            tp = current + 2.5 * atr_val
            sl = current - 1.0 * atr_val
        else:
            tp = current - 2.5 * atr_val
            sl = current + 1.0 * atr_val

        conf = min(0.83, 0.60 + (vol_ratio - 1.0) * 0.08 +
                   max(0, (1.0 - compression_ratio) * 0.3))

        signals.append(_base_signal(
            "ag_gravity_well_majors", symbol, direction, current, tp, sl, conf,
            f"Gravity Well MAJORS: BB width={current_bw:.3f}% "
            f"(20-bar min={min_bw:.3f}%), vol={vol_ratio:.1f}x avg, "
            f"compression releasing {direction}",
            parent_system="battleground",
            mutation_type="compression_breakout_majors_restricted",
            bb_width_pct=round(current_bw, 4),
            bb_width_min=round(min_bw, 4),
            vol_ratio=round(vol_ratio, 2),
            compression_ratio=round(compression_ratio, 3),
            timeframe="1h",
            category_restriction="TIER_1_MAJORS_ONLY",
            backtest_wr="45.2%",
            backtest_pf="1.42",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════
# JUPUSDT Special Scanner — Our best symbol across ALL mutations
# ═══════════════════════════════════════════════════════════════════════

def jupusdt_scanner(data: dict) -> list[dict]:
    """
    Special scanner for JUPUSDT — runs ALL edges we have against it.
    Backtest: 65.7% WR, +22.64% PnL, 1.65 PF across 35 trades.
    """
    signals = []
    jup_data = {"JUPUSDT": data.get("JUPUSDT")} if "JUPUSDT" in data else {}
    btc_data = {"BTCUSDT": data.get("BTCUSDT")} if "BTCUSDT" in data else {}

    if not jup_data.get("JUPUSDT") is None:
        # Run momentum cascade on JUP
        mc_sigs = momentum_cascade({**jup_data, **btc_data})
        for s in mc_sigs:
            if s["symbol"] == "JUPUSDT":
                s["strategy"] = "ag_jupusdt_momentum"
                s["mutation_type"] = "jupusdt_special_momentum"
                signals.append(s)

        # Run gravity well on JUP
        gw_sigs = gravity_well({**jup_data, **btc_data})
        for s in gw_sigs:
            if s["symbol"] == "JUPUSDT":
                s["strategy"] = "ag_jupusdt_gravity"
                s["mutation_type"] = "jupusdt_special_gravity"
                signals.append(s)

    return signals


# ═══════════════════════════════════════════════════════════════════════
# Production Registry
# ═══════════════════════════════════════════════════════════════════════

RESTRICTED_MUTATIONS = {
    "ag_momentum_cascade_meme": momentum_cascade_meme,
    "ag_gravity_well_majors": gravity_well_majors,
    "ag_jupusdt_scanner": jupusdt_scanner,
}


# ═══════════════════════════════════════════════════════════════════════
# Live Pick Generator
# ═══════════════════════════════════════════════════════════════════════

def generate_live_picks() -> list[dict]:
    """
    Fetch current Binance data and generate forward-test picks.
    Returns all signals from restricted mutations.
    """
    print("=" * 70)
    print("  ANTIGRAVITY V2 RESTRICTED -- Live Forward-Test Pick Generator")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    est_time = datetime.now(timezone.utc) - timedelta(hours=4)
    print(f"  {est_time.strftime('%Y-%m-%d %H:%M:%S EST')}")
    print("=" * 70)

    # Fetch data for all symbols we need
    all_symbols = list(set(MEME_ONLY + MAJORS_ONLY + JUPUSDT_SPECIAL))
    data = {}

    print(f"\n  Fetching {len(all_symbols)} symbols from Binance...")
    for sym in all_symbols:
        df = fetch_live_klines(sym, "1h", 100)
        if not df.empty and len(df) >= 30:
            data[sym] = df
            print(f"    + {sym}: {len(df)} bars, latest close=${float(df['Close'].iloc[-1]):.4f}")
        else:
            print(f"    - {sym}: no data")
        time.sleep(0.1)

    print(f"\n  Data fetched: {len(data)}/{len(all_symbols)} symbols")

    # Run all restricted mutations
    all_picks = []
    print(f"\n  Running {len(RESTRICTED_MUTATIONS)} restricted mutations...\n")

    for mut_name, mut_func in RESTRICTED_MUTATIONS.items():
        try:
            picks = mut_func(data)
            all_picks.extend(picks)
            if picks:
                print(f"  {mut_name}: {len(picks)} picks generated")
                for p in picks:
                    direction_emoji = "LONG" if p["signal_type"] == "BUY" else "SHORT"
                    print(f"    {direction_emoji} {p['symbol']} @ ${p['entry_price']}")
                    print(f"      TP: ${p['take_profit']} | SL: ${p['stop_loss']} | "
                          f"RR: {p['risk_reward']:.1f} | Conf: {p['confidence']:.0%}")
                    print(f"      Reason: {p['reason']}")
            else:
                print(f"  {mut_name}: No signals (conditions not met)")
        except Exception as e:
            print(f"  {mut_name}: ERROR -- {e}")

    print(f"\n  Total live picks: {len(all_picks)}")
    return all_picks, data


def format_picks_for_chatwithit(picks: list[dict]) -> str:
    """Format picks into markdown table for CHATWITHIT.md."""
    if not picks:
        return "No picks generated at this time — market conditions don't match any restricted mutation criteria.\n"

    est_now = datetime.now(timezone.utc) - timedelta(hours=4)
    lines = []
    lines.append(f"| # | Symbol | Direction | Entry Price | TP | SL | RR | Strategy | Reason |")
    lines.append(f"|---|--------|-----------|-------------|-----|-----|-----|----------|--------|")

    for i, p in enumerate(picks, 1):
        sym = p["symbol"].replace("USDT", "")
        direction = p["signal_type"]
        entry = p["entry_price"]
        tp = p["take_profit"]
        sl = p["stop_loss"]
        rr = p["risk_reward"]
        strat = p["strategy"].replace("ag_", "").replace("_mut", "")
        reason = p["reason"][:80] + "..." if len(p["reason"]) > 80 else p["reason"]
        lines.append(f"| {i} | {sym} | {direction} | ${entry} | ${tp} | ${sl} | {rr:.1f} | {strat} | {reason} |")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    picks, data = generate_live_picks()

    if picks:
        # Save picks to JSON
        output_dir = PROJECT_ROOT / "genome" / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        picks_path = output_dir / "ag_v2_restricted_live_picks.json"
        with open(picks_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "generated_est": (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S EST"),
                "mutations_run": list(RESTRICTED_MUTATIONS.keys()),
                "symbols_scanned": list(data.keys()),
                "total_picks": len(picks),
                "picks": picks,
            }, f, indent=2, default=str)
        print(f"\n  Picks saved to: {picks_path}")

        # Print CHATWITHIT format
        print("\n" + "=" * 70)
        print("  CHATWITHIT.md FORMAT:")
        print("=" * 70)
        print(format_picks_for_chatwithit(picks))
    else:
        print("\n  No picks generated. Market conditions don't match criteria.")
        print("  This is EXPECTED for selective strategies — they wait for the right moment.")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)
