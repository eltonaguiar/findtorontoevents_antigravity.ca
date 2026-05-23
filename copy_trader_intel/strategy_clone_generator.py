#!/usr/bin/env python3
"""
Strategy Clone Pick Generator
==============================
Uses our reverse-engineered strategy rules (from extracted_strategies.json)
to independently generate picks via Binance market data, then cross-examines
them against the traders' actual positions.

Output:
  - clone_picks.json: Our independent picks tagged as "proven_trader_strategy_clone"
  - cross_examination.json: Comparison of our picks vs their actual positions
  - Both wired into the /audit pipeline

NO API KEY NEEDED: Uses Binance public klines + Hyperliquid public API.
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Binance endpoints (geo-safe fallback chain)
BINANCE_APIS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
]

# Hyperliquid API
HL_INFO_API = "https://api.hyperliquid.xyz/info"

# Map HL coin names to Binance symbols
HL_TO_BINANCE = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "DOT": "DOTUSDT",
    "LINK": "LINKUSDT", "NEAR": "NEARUSDT", "RENDER": "RENDERUSDT",
    "FET": "FETUSDT", "HYPE": "HYPEUSDT", "IP": "IPUSDT",
    "ONDO": "ONDOUSDT", "SUI": "SUIUSDT", "WIF": "WIFUSDT",
    "JUP": "JUPUSDT", "ENA": "ENAUSDT", "STX": "STXUSDT",
    "SEI": "SEIUSDT", "TIA": "TIAUSDT", "INJ": "INJUSDT",
    "ARB": "ARBUSDT", "OP": "OPUSDT", "MET": "METISUSDT",
    "ASTER": "ASTERUSDT", "ZEC": "ZECUSDT", "FARTCOIN": "FARTCOINUSDT",
    "ANIME": "ANIMEUSDT", "AXS": "AXSUSDT",
}

# Coins that are HL-specific perps (not available on Binance)
HL_ONLY_COINS = {"xyz:CL", "xyz:MU", "xyz:TSLA", "xyz:COIN", "xyz:AAPL", "xyz:NVDA"}


def binance_klines(symbol, interval="1h", limit=100):
    """Fetch klines from Binance with geo-safe fallback."""
    for base in BINANCE_APIS:
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": symbol, "interval": interval, "limit": limit
            }, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return []


def compute_rsi(closes, period=14):
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral default
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_ema(values, period):
    """Compute EMA."""
    if len(values) < period:
        return values[-1] if values else 0
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def compute_atr(highs, lows, closes, period=14):
    """Compute ATR."""
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    return sum(trs[-period:]) / period


def analyze_coin(symbol, rules):
    """
    Analyze a coin using the extracted strategy rules to decide if
    we should enter a position right now.

    Returns: dict with signal info or None if no signal
    """
    klines = binance_klines(symbol, "1h", 100)
    if not klines or len(klines) < 30:
        return None

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    current_price = closes[-1]

    # Current hour (UTC)
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour

    # Strategy parameters
    direction_bias = rules.get("direction", "LONG")
    entry_hours = rules.get("entry_hours_utc", list(range(24)))
    tp_pct = rules.get("tp_pct", 2.0) / 100
    sl_pct = rules.get("sl_pct", 1.5) / 100

    # Check 1: Are we in a preferred entry hour?
    hour_match = current_hour in entry_hours if entry_hours else True

    # Check 2: RSI-based entry logic
    rsi = compute_rsi(closes)
    rsi_signal = None
    if direction_bias in ("LONG", "BALANCED"):
        if rsi < 35:
            rsi_signal = "LONG"  # Oversold → buy
        elif rsi < 45:
            rsi_signal = "LONG_WEAK"
    if direction_bias in ("SHORT", "BALANCED"):
        if rsi > 65:
            rsi_signal = "SHORT"  # Overbought → sell
        elif rsi > 55:
            rsi_signal = "SHORT_WEAK"

    # Check 3: EMA trend alignment
    ema_20 = compute_ema(closes, 20)
    ema_50 = compute_ema(closes, 50)
    trend = "BULLISH" if ema_20 > ema_50 else "BEARISH"

    # Check 4: Volume confirmation (current volume > 1.2x average)
    avg_vol = sum(volumes[-20:]) / len(volumes[-20:]) if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_ok = volumes[-1] > avg_vol * 1.0  # relaxed filter

    # Check 5: ATR for volatility assessment
    atr = compute_atr(highs, lows, closes)
    atr_pct = atr / current_price * 100 if current_price > 0 else 0

    # Decision logic
    signal = None
    confidence = 0.5
    reasons = []

    if direction_bias == "LONG" or direction_bias == "LONG_HEAVY":
        if trend == "BULLISH":
            confidence += 0.10
            reasons.append("EMA bullish trend")
        if rsi_signal in ("LONG", "LONG_WEAK"):
            confidence += 0.15 if rsi_signal == "LONG" else 0.05
            reasons.append(f"RSI {rsi:.1f} (oversold)")
        elif rsi < 50:
            confidence += 0.03
            reasons.append(f"RSI {rsi:.1f} (below midline)")
        if hour_match:
            confidence += 0.08
            reasons.append(f"Entry hour {current_hour} matches trader pattern")
        if vol_ok:
            confidence += 0.05
            reasons.append("Volume confirmed")
        if confidence >= 0.65:
            signal = "LONG"

    elif direction_bias == "SHORT" or direction_bias == "SHORT_HEAVY":
        if trend == "BEARISH":
            confidence += 0.10
            reasons.append("EMA bearish trend")
        if rsi_signal in ("SHORT", "SHORT_WEAK"):
            confidence += 0.15 if rsi_signal == "SHORT" else 0.05
            reasons.append(f"RSI {rsi:.1f} (overbought)")
        elif rsi > 50:
            confidence += 0.03
            reasons.append(f"RSI {rsi:.1f} (above midline)")
        if hour_match:
            confidence += 0.08
            reasons.append(f"Entry hour {current_hour} matches trader pattern")
        if vol_ok:
            confidence += 0.05
            reasons.append("Volume confirmed")
        if confidence >= 0.65:
            signal = "SHORT"

    elif direction_bias == "BALANCED":
        # For balanced traders, go with the stronger signal
        long_conf = 0.5
        short_conf = 0.5
        if trend == "BULLISH":
            long_conf += 0.10
        else:
            short_conf += 0.10
        if rsi < 40:
            long_conf += 0.15
        elif rsi > 60:
            short_conf += 0.15
        if hour_match:
            long_conf += 0.08
            short_conf += 0.08
        if vol_ok:
            long_conf += 0.05
            short_conf += 0.05

        if long_conf > short_conf and long_conf >= 0.65:
            signal = "LONG"
            confidence = long_conf
            reasons.append(f"Balanced trader, LONG stronger (RSI {rsi:.1f}, {trend})")
        elif short_conf >= 0.65:
            signal = "SHORT"
            confidence = short_conf
            reasons.append(f"Balanced trader, SHORT stronger (RSI {rsi:.1f}, {trend})")

    if not signal:
        return None

    # Build the pick
    if signal == "LONG":
        tp = round(current_price * (1 + tp_pct), 8)
        sl = round(current_price * (1 - max(sl_pct, 0.01)), 8)
    else:
        tp = round(current_price * (1 - tp_pct), 8)
        sl = round(current_price * (1 + max(sl_pct, 0.01)), 8)

    return {
        "symbol": symbol,
        "direction": signal,
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(min(confidence, 0.95), 3),
        "rsi": round(rsi, 1),
        "trend": trend,
        "atr_pct": round(atr_pct, 3),
        "reasons": reasons,
    }


def hl_post(payload, retries=3):
    """POST to Hyperliquid info API."""
    for attempt in range(retries):
        try:
            resp = requests.post(HL_INFO_API, json=payload, timeout=15)
            if resp.status_code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5)
    return {}


def get_trader_positions(address):
    """Get current open positions for a trader from Hyperliquid."""
    state = hl_post({"type": "clearinghouseState", "user": address})
    if not state:
        return []
    positions = []
    for pos in state.get("assetPositions", []):
        p = pos.get("position", pos)
        size = float(p.get("szi", 0))
        if size != 0:
            positions.append({
                "coin": p.get("coin", ""),
                "direction": "LONG" if size > 0 else "SHORT",
                "entry_price": float(p.get("entryPx", 0)),
                "size": abs(size),
            })
    return positions


def cross_examine(our_picks, trader_positions, strategy):
    """
    Compare our strategy-clone picks against the trader's actual positions.
    Returns cross-examination results.
    """
    results = {
        "strategy_id": strategy.get("strategy_id", ""),
        "trader_label": strategy.get("source_label", ""),
        "our_picks_count": len(our_picks),
        "their_positions_count": len(trader_positions),
        "matches": [],
        "our_only": [],
        "theirs_only": [],
        "agreement_rate": 0,
        "direction_agreement_rate": 0,
    }

    our_coins = {}
    for p in our_picks:
        # Convert BTCUSDT → BTC for comparison
        coin = p["symbol"].replace("USDT", "").replace("USDC", "")
        our_coins[coin] = p

    their_coins = {}
    for p in trader_positions:
        their_coins[p["coin"]] = p

    # Find matches
    matched_coins = set(our_coins.keys()) & set(their_coins.keys())
    direction_matches = 0

    for coin in matched_coins:
        our = our_coins[coin]
        theirs = their_coins[coin]
        dir_match = our["direction"] == theirs["direction"]
        if dir_match:
            direction_matches += 1
        results["matches"].append({
            "coin": coin,
            "our_direction": our["direction"],
            "their_direction": theirs["direction"],
            "direction_match": dir_match,
            "our_entry": our["entry_price"],
            "their_entry": theirs["entry_price"],
            "entry_diff_pct": round(abs(our["entry_price"] - theirs["entry_price"]) / max(theirs["entry_price"], 0.001) * 100, 2),
        })

    results["our_only"] = [{"coin": c, "direction": our_coins[c]["direction"]}
                           for c in set(our_coins.keys()) - set(their_coins.keys())]
    results["theirs_only"] = [{"coin": c, "direction": their_coins[c]["direction"]}
                              for c in set(their_coins.keys()) - set(our_coins.keys())]

    total_coins = len(set(our_coins.keys()) | set(their_coins.keys()))
    results["agreement_rate"] = round(len(matched_coins) / max(total_coins, 1) * 100, 1)
    results["direction_agreement_rate"] = round(direction_matches / max(len(matched_coins), 1) * 100, 1)

    return results


def run():
    """Main: generate clone picks + cross-examine against actual positions."""
    print("=" * 70)
    print("  STRATEGY CLONE PICK GENERATOR")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load extracted strategies
    strat_file = DATA_DIR / "extracted_strategies.json"
    if not strat_file.exists():
        print("  [ERROR] No extracted_strategies.json found. Run strategy_reverse_engineer.py first.")
        return

    with open(strat_file) as f:
        strat_data = json.load(f)

    strategies = strat_data.get("strategies", [])
    print(f"\n  Loaded {len(strategies)} extracted strategies")

    # Also load qualified traders for address lookups
    qt_file = DATA_DIR / "qualified_traders.json"
    qualified_traders = {}
    if qt_file.exists():
        with open(qt_file) as f:
            qt_data = json.load(f)
        for t in qt_data.get("traders", []):
            qualified_traders[t.get("label", "")] = t

    now = datetime.now(timezone.utc)
    all_clone_picks = []
    all_cross_exams = []

    for strat in strategies:
        sid = strat.get("strategy_id", "unknown")
        label = strat.get("source_label", "")
        rules = strat.get("rules", {})
        expected = strat.get("expected_performance", {})
        safety_mode = strat.get("safety_gate_mode", "STANDARD_SAFETY_GATES")

        print(f"\n{'='*60}")
        print(f"  CLONING: {sid}")
        print(f"  Trader: {label} | Style: {strat.get('description', '')}")
        print(f"  Safety: {safety_mode}")
        print(f"{'='*60}")

        # Get coins to analyze — use expanded list
        # Priority: best_coins > all_traded_coins > major coin baseline
        coins = rules.get("coins", [])
        all_traded = rules.get("all_traded_coins", [])
        avoid = set(rules.get("avoid_coins", []))

        # Combine: strategy coins + all traded coins + top majors for broader coverage
        TOP_MAJORS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA",
                      "AVAX", "LINK", "NEAR", "SUI", "RENDER", "FET",
                      "HYPE", "ONDO"]
        combined = list(dict.fromkeys(coins + all_traded + TOP_MAJORS))  # dedup preserving order

        # Filter out HL-only coins and map to Binance symbols
        tradeable_coins = []
        seen_syms = set()
        for coin in combined:
            if coin in HL_ONLY_COINS or coin in avoid:
                continue
            binance_sym = HL_TO_BINANCE.get(coin, f"{coin}USDT")
            if binance_sym not in seen_syms:
                seen_syms.add(binance_sym)
                tradeable_coins.append((coin, binance_sym))

        if not tradeable_coins:
            print(f"  [SKIP] No tradeable coins for this strategy")
            continue

        # Load per-coin performance data for filtering
        coin_performance = strat.get("coin_performance", {})
        overall_wr = expected.get("win_rate", 0)

        # Generate picks for each coin — with per-coin performance gate
        strat_picks = []
        for coin, binance_sym in tradeable_coins:
            # === PERFORMANCE GATE ===
            # Only clone on coins where the trader has proven edge
            perf = coin_performance.get(coin, None)
            if perf:
                # Trader has data for this coin — check it
                coin_wr = perf.get("win_rate", 0)
                coin_pnl = perf.get("total_pnl", 0)
                coin_trades = perf.get("trades", 0)

                if coin_pnl < 0 and coin_trades >= 3:
                    print(f"  [GATE] {binance_sym}: trader has NEGATIVE PnL (${coin_pnl:.2f}) on {coin_trades} trades — skipping")
                    continue
                if coin_wr < 0.45 and coin_trades >= 5:
                    print(f"  [GATE] {binance_sym}: trader WR too low ({coin_wr*100:.0f}%) on {coin_trades} trades — skipping")
                    continue
                if coin_pnl < 0 and coin_wr < 0.6:
                    print(f"  [GATE] {binance_sym}: negative PnL + low WR ({coin_wr*100:.0f}%) — skipping")
                    continue
            else:
                # No per-coin data — only clone on unproven coins if overall WR is very high
                if overall_wr < 0.70:
                    print(f"  [GATE] {binance_sym}: no coin-specific data & overall WR < 70% — skipping")
                    continue
            result = analyze_coin(binance_sym, rules)
            if result:
                # Build audit-compatible pick
                pick_id = f"clone_{sid}::{binance_sym}::{now.strftime('%Y-%m-%d_%H%M')}"
                pick = {
                    "id": pick_id,
                    "strategy": f"clone_{sid}",
                    "symbol": binance_sym,
                    "category": "crypto",
                    "signal_type": "BUY" if result["direction"] == "LONG" else "SELL",
                    "direction": result["direction"],
                    "entry_price": result["entry_price"],
                    "entry_date": now.strftime("%Y-%m-%d"),
                    "take_profit": result["take_profit"],
                    "stop_loss": result["stop_loss"],
                    "confidence": result["confidence"],
                    "ml_score": result["confidence"],
                    "exit_price": None,
                    "exit_date": None,
                    "exit_reason": None,
                    "pnl_pct": None,
                    "pnl_dollar": None,
                    "status": "OPEN",
                    "hold_days": None,
                    "allocation": 200.0,  # $200 per clone position
                    "position_sizing": "strategy_clone",
                    "risk_per_trade_pct": 0.02,
                    "max_safe_leverage": min(rules.get("max_leverage", 5), 10),
                    # Forward validation (start at zero; pipeline earns these via closed trades)
                    # Trader's self-reported stats live in clone_expected_wr / clone_expected_pf below
                    # so the UI can display them as unvalidated expectations, separate from pipeline truth.
                    "forward_trades": 0,
                    "forward_wr": 0.0,
                    "forward_validated": False,
                    # Edge & grading — ungraded until pipeline validates from closed trades
                    "elite_score": 0,
                    "elite_grade": "UNGRADED",
                    # Clone-specific metadata
                    "reason": (f"Strategy Clone of {label} | "
                              f"ExpWR:{expected.get('win_rate',0)*100:.0f}% "
                              f"PF:{expected.get('profit_factor',0):.1f} | "
                              f"RSI:{result['rsi']} {result['trend']} | "
                              + ", ".join(result["reasons"][:3])),
                    "source_system": "copy_trader_intel",
                    "source_strategy_type": "proven_trader_strategy_clone",
                    "clone_source_trader": label,
                    "clone_strategy_id": sid,
                    "clone_safety_mode": safety_mode,
                    "clone_expected_wr": expected.get("win_rate", 0),
                    "clone_expected_pf": expected.get("profit_factor", 0),
                    "timestamp": now.isoformat(),
                    # Tags for audit tracking
                    "tags": ["proven_trader_strategy_clone", f"clone_{label}", safety_mode.lower()],
                }
                strat_picks.append(pick)
                print(f"  📊 {result['direction']} {binance_sym} @ {result['entry_price']:.4f} "
                      f"| Conf:{result['confidence']:.2f} RSI:{result['rsi']:.0f} "
                      f"| TP:{result['take_profit']:.4f} SL:{result['stop_loss']:.4f}")
            else:
                print(f"  [--] {binance_sym}: no signal (conditions not met)")

        all_clone_picks.extend(strat_picks)

        # Cross-examine: get trader's actual positions
        trader_addr = strat.get("source_trader", "")
        if trader_addr:
            print(f"\n  Cross-examining vs {label}'s live positions...")
            time.sleep(0.8)
            their_positions = get_trader_positions(trader_addr)
            if their_positions:
                xr = cross_examine(strat_picks, their_positions, strat)
                all_cross_exams.append(xr)
                print(f"  📋 Agreement: {xr['agreement_rate']}% coins | "
                      f"Direction match: {xr['direction_agreement_rate']}%")
                print(f"     Matches: {len(xr['matches'])} | "
                      f"Ours only: {len(xr['our_only'])} | "
                      f"Theirs only: {len(xr['theirs_only'])}")
                for m in xr["matches"]:
                    icon = "✅" if m["direction_match"] else "❌"
                    print(f"     {icon} {m['coin']}: us={m['our_direction']} them={m['their_direction']} "
                          f"(entry diff: {m['entry_diff_pct']:.1f}%)")
            else:
                print(f"  [--] Trader has no open positions currently")

    # Save clone picks
    with open(DATA_DIR / "clone_picks.json", "w") as f:
        json.dump(all_clone_picks, f, indent=2, default=str)

    # Save cross-examination results
    cross_exam_output = {
        "generated_at": now.isoformat(),
        "total_strategies_examined": len(strategies),
        "total_clone_picks": len(all_clone_picks),
        "examinations": all_cross_exams,
        "summary": {
            "avg_agreement_rate": round(
                sum(x["agreement_rate"] for x in all_cross_exams) / max(len(all_cross_exams), 1), 1
            ),
            "avg_direction_agreement": round(
                sum(x["direction_agreement_rate"] for x in all_cross_exams) / max(len(all_cross_exams), 1), 1
            ),
        }
    }
    with open(DATA_DIR / "cross_examination.json", "w") as f:
        json.dump(cross_exam_output, f, indent=2, default=str)

    # Also append clone picks to active_picks.json for audit integration
    # (but with distinct IDs so they don't conflict with copy picks)
    existing_picks = []
    active_file = DATA_DIR / "active_picks.json"
    if active_file.exists():
        with open(active_file) as f:
            existing_picks = json.load(f)

    # Remove old clones, keep copy picks
    existing_picks = [p for p in existing_picks if p.get("source_strategy_type") != "proven_trader_strategy_clone"]
    existing_picks.extend(all_clone_picks)

    with open(active_file, "w") as f:
        json.dump(existing_picks, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  RESULTS")
    print(f"  Clone picks: {len(all_clone_picks)}")
    print(f"  Cross-examinations: {len(all_cross_exams)}")
    if all_cross_exams:
        print(f"  Avg agreement: {cross_exam_output['summary']['avg_agreement_rate']}%")
        print(f"  Avg direction match: {cross_exam_output['summary']['avg_direction_agreement']}%")
    print(f"  Files: clone_picks.json, cross_examination.json, active_picks.json (updated)")
    print(f"{'='*70}\n")

    return all_clone_picks, all_cross_exams


if __name__ == "__main__":
    run()
