#!/usr/bin/env python3
"""
Strategy Reverse Engineer
=========================
Analyzes fill history from qualified Hyperliquid traders to extract their
actual trading patterns and build reproducible strategy profiles.

For each trader, we extract:
- Preferred coins and their frequency
- Direction bias (long-heavy, short-heavy, balanced)
- Typical leverage range
- Average hold time (entry to exit)
- Entry timing patterns (time of day, day of week)
- Position sizing behavior
- Win rate by coin, by direction, by time
- Entry criteria heuristics (breakout, mean-reversion, momentum)
- Entry pattern classification (breakout, mean-reversion, momentum, dip-buyer)

Output: strategy_profiles.json -- one profile per qualified trader
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import time
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
import requests

HL_API = "https://api.hyperliquid.xyz/info"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def hl_post(payload, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post(HL_API, json=payload, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return {} if isinstance(payload, dict) else []


def get_fills(address, start_time=None):
    payload = {"type": "userFills", "user": address}
    if start_time:
        payload["startTime"] = start_time
    result = hl_post(payload)
    return result if isinstance(result, list) else []


# Binance API failover chain for candle data
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
]


def normalize_symbol_for_binance(coin):
    """Convert HL coin name to Binance ticker."""
    s = coin.upper().replace("-", "").replace("/", "")
    # Skip non-crypto assets (equities, commodities, perps with special prefixes)
    if s.startswith("XYZ:") or s.startswith("KM:") or s.startswith("@") or s.startswith("HYNA:"):
        return None
    if s.endswith("USDT"):
        return s
    if s.endswith("USD"):
        return s + "T"
    return s + "USDT"


def fetch_klines(coin, entry_time_ms, interval="1h", limit=24):
    """Fetch candle data around an entry timestamp from Binance with failover.

    Returns list of [open_time, open, high, low, close, volume, ...] or [].
    We request candles ending at entry_time so we get the price action leading up to entry.
    """
    symbol = normalize_symbol_for_binance(coin)
    if not symbol:
        return []

    # Start time: go back `limit` candles from entry
    interval_ms = {"1h": 3600000, "4h": 14400000, "15m": 900000}.get(interval, 3600000)
    start_ms = entry_time_ms - (limit * interval_ms)

    for endpoint in BINANCE_ENDPOINTS:
        try:
            url = (f"{endpoint}/api/v3/klines?symbol={symbol}"
                   f"&interval={interval}&startTime={start_ms}"
                   f"&endTime={entry_time_ms}&limit={limit}")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return []


def classify_entry_pattern(coin, entry_price, direction, entry_time_ms):
    """Classify a single trade entry into one of:
    - breakout: entry near recent high (long) or low (short)
    - mean_reversion: bounce from support/resistance
    - momentum: following a large candle in the same direction
    - dip_buyer: entry on a red candle during an uptrend (or green candle short in downtrend)
    - unknown: insufficient data

    Uses 1h candles for the 24 hours preceding entry.
    """
    klines = fetch_klines(coin, entry_time_ms, interval="1h", limit=24)
    if len(klines) < 6:
        return "unknown", 0.0

    # Parse candle data
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    opens = [float(k[1]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    recent_high = max(highs[-12:])  # 12h high
    recent_low = min(lows[-12:])    # 12h low
    price_range = recent_high - recent_low if recent_high > recent_low else 1e-8
    avg_volume = statistics.mean(volumes) if volumes else 1

    # Last candle before entry
    last_close = closes[-1]
    last_open = opens[-1]
    last_candle_pct = (last_close - last_open) / last_open * 100 if last_open > 0 else 0

    # Average candle body size
    candle_bodies = [abs(c - o) / o * 100 for c, o in zip(closes, opens) if o > 0]
    avg_body = statistics.mean(candle_bodies) if candle_bodies else 0.5

    # Trend: compare first half average to second half
    first_half_avg = statistics.mean(closes[:len(closes)//2]) if closes[:len(closes)//2] else entry_price
    second_half_avg = statistics.mean(closes[len(closes)//2:]) if closes[len(closes)//2:] else entry_price
    is_uptrend = second_half_avg > first_half_avg * 1.002
    is_downtrend = second_half_avg < first_half_avg * 0.998

    # Proximity to recent high/low (0 = at low, 1 = at high)
    position_in_range = (entry_price - recent_low) / price_range if price_range > 0 else 0.5

    # -- Pattern Classification --
    confidence = 0.0

    # BREAKOUT: entry near extreme of recent range
    if direction == "LONG" and position_in_range > 0.85:
        confidence = min(position_in_range, 1.0)
        return "breakout", round(confidence, 3)
    if direction == "SHORT" and position_in_range < 0.15:
        confidence = min(1 - position_in_range, 1.0)
        return "breakout", round(confidence, 3)

    # MOMENTUM: last candle was large and in the same direction as the trade
    if abs(last_candle_pct) > avg_body * 1.5:
        if (direction == "LONG" and last_candle_pct > 0) or (direction == "SHORT" and last_candle_pct < 0):
            confidence = min(abs(last_candle_pct) / (avg_body * 3), 1.0)
            return "momentum", round(confidence, 3)

    # DIP_BUYER: red candle in an uptrend (long), or green candle in downtrend (short)
    if direction == "LONG" and is_uptrend and last_candle_pct < -0.1:
        confidence = min(abs(last_candle_pct) / (avg_body * 2), 1.0)
        return "dip_buyer", round(confidence, 3)
    if direction == "SHORT" and is_downtrend and last_candle_pct > 0.1:
        confidence = min(abs(last_candle_pct) / (avg_body * 2), 1.0)
        return "dip_buyer", round(confidence, 3)

    # MEAN_REVERSION: entry near support (long) or resistance (short) in range-bound market
    if direction == "LONG" and position_in_range < 0.3 and not is_downtrend:
        confidence = min(1 - position_in_range, 1.0)
        return "mean_reversion", round(confidence, 3)
    if direction == "SHORT" and position_in_range > 0.7 and not is_uptrend:
        confidence = min(position_in_range, 1.0)
        return "mean_reversion", round(confidence, 3)

    # Fallback: if nothing clearly matches, use best guess from position
    if direction == "LONG":
        if position_in_range < 0.4:
            return "mean_reversion", round(0.3, 3)
        else:
            return "momentum", round(0.3, 3)
    else:
        if position_in_range > 0.6:
            return "mean_reversion", round(0.3, 3)
        else:
            return "momentum", round(0.3, 3)


def classify_entries_for_trades(closed_trades, max_lookups=30):
    """Classify entry patterns for a list of closed trades.

    Limits API calls to max_lookups to avoid rate limiting.
    Returns a dict with pattern counts and per-trade classifications.
    """
    pattern_counts = defaultdict(int)
    pattern_details = []
    classified = 0

    for trade in closed_trades:
        if classified >= max_lookups:
            break

        coin = trade.get("coin", "")
        entry_price = trade.get("entry_price", 0)
        direction = trade.get("direction", "LONG")
        entry_time = trade.get("entry_time", 0)

        if not coin or entry_price <= 0 or entry_time <= 0:
            continue

        pattern, confidence = classify_entry_pattern(coin, entry_price, direction, entry_time)
        pattern_counts[pattern] += 1
        classified += 1

        pattern_details.append({
            "coin": coin,
            "direction": direction,
            "entry_price": entry_price,
            "pattern": pattern,
            "confidence": confidence,
        })

        time.sleep(0.15)  # rate limit

    # Determine dominant pattern
    total_classified = sum(v for k, v in pattern_counts.items() if k != "unknown")
    dominant_pattern = "unknown"
    dominant_pct = 0
    if total_classified > 0:
        for pattern, count in pattern_counts.items():
            if pattern == "unknown":
                continue
            pct = count / total_classified
            if pct > dominant_pct:
                dominant_pct = pct
                dominant_pattern = pattern

    return {
        "total_classified": classified,
        "pattern_counts": dict(pattern_counts),
        "dominant_pattern": dominant_pattern,
        "dominant_pattern_pct": round(dominant_pct * 100, 1),
        "details": pattern_details[-10:],  # Keep last 10 for reference
    }


def reverse_engineer_trader(address, label=""):
    """Deep analysis of a trader's fill history to extract strategy DNA."""
    print(f"\n{'='*60}")
    print(f"  REVERSE ENGINEERING: {label or address[:12]}")
    print(f"{'='*60}")

    # Get 90 days of fills
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp() * 1000)
    fills = get_fills(address, start_time=start_ms)

    if not fills:
        print("  No fills found")
        return None

    print(f"  Total fills: {len(fills)}")

    # -- Parse fills into structured trades --
    # Group consecutive fills on same coin+direction into "trades"
    trades = []
    by_coin_dir = defaultdict(list)

    for fill in fills:
        coin = fill.get("coin", "")
        side = fill.get("side", "")  # "B" or "A" (buy/sell)
        px = float(fill.get("px", 0))
        sz = float(fill.get("sz", 0))
        t = fill.get("time", 0)
        cpnl = float(fill.get("closedPnl", 0))
        direction = fill.get("dir", "")  # "Open Long", "Close Long", "Open Short", "Close Short"
        fee = float(fill.get("fee", 0))
        is_liq = fill.get("liquidation", False)

        by_coin_dir[coin].append({
            "side": side,
            "price": px,
            "size": sz,
            "time": t,
            "closed_pnl": cpnl,
            "direction": direction,
            "fee": fee,
            "is_liquidation": is_liq,
        })

    # -- Reconstruct trade sequences per coin --
    all_closed_trades = []

    for coin, coin_fills in by_coin_dir.items():
        coin_fills.sort(key=lambda x: x["time"])

        # Track open/close pairs
        open_fill = None
        for f in coin_fills:
            d = f["direction"]
            if "Open" in d:
                open_fill = f
            elif "Close" in d and open_fill:
                hold_ms = f["time"] - open_fill["time"]
                hold_hours = hold_ms / (1000 * 3600) if hold_ms > 0 else 0
                trade_dir = "LONG" if "Long" in open_fill["direction"] else "SHORT"

                if trade_dir == "LONG":
                    pnl_pct = (f["price"] - open_fill["price"]) / open_fill["price"] * 100
                else:
                    pnl_pct = (open_fill["price"] - f["price"]) / open_fill["price"] * 100

                entry_dt = datetime.fromtimestamp(open_fill["time"] / 1000, tz=timezone.utc)

                all_closed_trades.append({
                    "coin": coin,
                    "direction": trade_dir,
                    "entry_price": open_fill["price"],
                    "exit_price": f["price"],
                    "entry_time": open_fill["time"],
                    "exit_time": f["time"],
                    "hold_hours": round(hold_hours, 2),
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_dollar": f["closed_pnl"],
                    "size": open_fill["size"],
                    "fee": open_fill["fee"] + f["fee"],
                    "is_win": pnl_pct > 0,
                    "entry_hour_utc": entry_dt.hour,
                    "entry_day_of_week": entry_dt.strftime("%A"),
                    "was_liquidated": f.get("is_liquidation", False),
                })
                open_fill = None

    if not all_closed_trades:
        print("  Could not reconstruct any closed trades")
        return None

    print(f"  Reconstructed trades: {len(all_closed_trades)}")

    # -- STRATEGY DNA EXTRACTION --

    # 1. Direction Bias
    longs = [t for t in all_closed_trades if t["direction"] == "LONG"]
    shorts = [t for t in all_closed_trades if t["direction"] == "SHORT"]
    long_pct = len(longs) / len(all_closed_trades) * 100
    if long_pct > 65:
        direction_bias = "LONG_HEAVY"
    elif long_pct < 35:
        direction_bias = "SHORT_HEAVY"
    else:
        direction_bias = "BALANCED"

    # 2. Win rates by direction
    long_wr = sum(1 for t in longs if t["is_win"]) / max(len(longs), 1)
    short_wr = sum(1 for t in shorts if t["is_win"]) / max(len(shorts), 1)

    # 3. Hold time analysis
    hold_times = [t["hold_hours"] for t in all_closed_trades if t["hold_hours"] > 0]
    if hold_times:
        median_hold = statistics.median(hold_times)
        mean_hold = statistics.mean(hold_times)
        p25_hold = sorted(hold_times)[len(hold_times) // 4]
        p75_hold = sorted(hold_times)[3 * len(hold_times) // 4]
    else:
        median_hold = mean_hold = p25_hold = p75_hold = 0

    # Classify trading style
    if median_hold < 1:
        trading_style = "SCALPER"
    elif median_hold < 8:
        trading_style = "DAY_TRADER"
    elif median_hold < 72:
        trading_style = "SWING_TRADER"
    else:
        trading_style = "POSITION_TRADER"

    # 4. Coin preferences
    coin_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0, "avg_hold": []})
    for t in all_closed_trades:
        c = t["coin"]
        coin_stats[c]["trades"] += 1
        coin_stats[c]["wins"] += 1 if t["is_win"] else 0
        coin_stats[c]["pnl"] += t["pnl_dollar"]
        coin_stats[c]["avg_hold"].append(t["hold_hours"])

    top_coins = sorted(coin_stats.items(), key=lambda x: x[1]["trades"], reverse=True)
    coin_breakdown = []
    for coin, stats in top_coins[:10]:
        wr = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0
        avg_h = statistics.mean(stats["avg_hold"]) if stats["avg_hold"] else 0
        coin_breakdown.append({
            "coin": coin,
            "trades": stats["trades"],
            "win_rate": round(wr, 3),
            "total_pnl": round(stats["pnl"], 2),
            "avg_hold_hours": round(avg_h, 1),
        })

    # 5. Time-of-day patterns
    hour_dist = defaultdict(int)
    for t in all_closed_trades:
        hour_dist[t["entry_hour_utc"]] += 1
    peak_hours = sorted(hour_dist.items(), key=lambda x: x[1], reverse=True)[:5]

    # 6. Day-of-week patterns
    day_dist = defaultdict(lambda: {"trades": 0, "wins": 0})
    for t in all_closed_trades:
        d = t["entry_day_of_week"]
        day_dist[d]["trades"] += 1
        day_dist[d]["wins"] += 1 if t["is_win"] else 0

    # 7. PnL distribution
    pnl_pcts = [t["pnl_pct"] for t in all_closed_trades]
    wins_pnl = [p for p in pnl_pcts if p > 0]
    losses_pnl = [p for p in pnl_pcts if p < 0]
    avg_win_pct = statistics.mean(wins_pnl) if wins_pnl else 0
    avg_loss_pct = statistics.mean(losses_pnl) if losses_pnl else 0

    # 8. Streak analysis
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    curr_w = 0
    curr_l = 0
    for t in all_closed_trades:
        if t["is_win"]:
            curr_w += 1
            curr_l = 0
            max_win_streak = max(max_win_streak, curr_w)
        else:
            curr_l += 1
            curr_w = 0
            max_loss_streak = max(max_loss_streak, curr_l)

    # 9. Entry pattern classification
    # Look at PnL distribution to infer style
    big_wins = sum(1 for p in pnl_pcts if p > 5)
    small_wins = sum(1 for p in pnl_pcts if 0 < p <= 2)
    tight_losses = sum(1 for p in pnl_pcts if -2 <= p < 0)

    if big_wins > len(all_closed_trades) * 0.15 and avg_win_pct > abs(avg_loss_pct) * 2:
        entry_style = "BREAKOUT_MOMENTUM"
        entry_description = "Catches large moves, likely enters on breakouts. Wide TP, tight SL."
    elif small_wins > len(all_closed_trades) * 0.4 and tight_losses > len(all_closed_trades) * 0.2:
        entry_style = "MEAN_REVERSION"
        entry_description = "High-frequency small wins. Likely buys dips / sells rips with tight targets."
    elif abs(avg_win_pct) > 3 and abs(avg_loss_pct) > 3:
        entry_style = "SWING_CONVICTION"
        entry_description = "Takes larger positions with wider stops. Holds through volatility."
    else:
        entry_style = "MIXED_ADAPTIVE"
        entry_description = "Adapts strategy based on market conditions. No single dominant pattern."

    # 9b. Price-action-based entry pattern classification
    #     Correlate entry timestamps with candle data from Binance
    print(f"  Classifying entry patterns from price action...")
    entry_classification = classify_entries_for_trades(all_closed_trades, max_lookups=20)
    if entry_classification["total_classified"] > 0:
        print(f"     Classified {entry_classification['total_classified']} entries: "
              f"dominant={entry_classification['dominant_pattern']} "
              f"({entry_classification['dominant_pattern_pct']:.0f}%)")
        for pat, cnt in entry_classification["pattern_counts"].items():
            print(f"       {pat}: {cnt}")

    # 10. Liquidation rate
    liq_count = sum(1 for t in all_closed_trades if t.get("was_liquidated"))
    liq_rate = liq_count / len(all_closed_trades)

    # 11. Overall win rate
    total_wr = sum(1 for t in all_closed_trades if t["is_win"]) / len(all_closed_trades)

    # 12. Profit factor
    gp = sum(t["pnl_dollar"] for t in all_closed_trades if t["pnl_dollar"] > 0)
    gl = abs(sum(t["pnl_dollar"] for t in all_closed_trades if t["pnl_dollar"] < 0))
    pf = round(gp / gl, 2) if gl > 0 else 99.99

    # -- Build Strategy Profile --
    profile = {
        "address": address,
        "label": label,
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "total_fills": len(fills),
        "reconstructed_trades": len(all_closed_trades),

        # Strategy DNA
        "strategy_dna": {
            "trading_style": trading_style,
            "direction_bias": direction_bias,
            "entry_style": entry_style,
            "entry_description": entry_description,
            "median_hold_hours": round(median_hold, 1),
            "mean_hold_hours": round(mean_hold, 1),
            "hold_p25_hours": round(p25_hold, 1),
            "hold_p75_hours": round(p75_hold, 1),
            "entry_pattern_classification": {
                "dominant_pattern": entry_classification.get("dominant_pattern", "unknown"),
                "dominant_pattern_pct": entry_classification.get("dominant_pattern_pct", 0),
                "pattern_counts": entry_classification.get("pattern_counts", {}),
                "classified_count": entry_classification.get("total_classified", 0),
                "sample_entries": entry_classification.get("details", []),
            },
        },

        # Performance metrics
        "performance": {
            "win_rate": round(total_wr, 4),
            "long_win_rate": round(long_wr, 4),
            "short_win_rate": round(short_wr, 4),
            "profit_factor": pf,
            "avg_win_pct": round(avg_win_pct, 3),
            "avg_loss_pct": round(avg_loss_pct, 3),
            "risk_reward_ratio": round(abs(avg_win_pct / avg_loss_pct), 2) if avg_loss_pct != 0 else 99.99,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "liquidation_rate": round(liq_rate, 4),
            "total_pnl_dollar": round(sum(t["pnl_dollar"] for t in all_closed_trades), 2),
        },

        # Coin preferences
        "coin_breakdown": coin_breakdown,
        "primary_coins": [c["coin"] for c in coin_breakdown[:3]],

        # Timing
        "timing": {
            "peak_entry_hours_utc": [h for h, _ in peak_hours],
            "day_of_week_stats": {d: {"trades": s["trades"], "win_rate": round(s["wins"]/max(s["trades"],1), 3)}
                                  for d, s in day_dist.items()},
        },

        # Direction split
        "direction_split": {
            "long_count": len(longs),
            "short_count": len(shorts),
            "long_pct": round(long_pct, 1),
        },

        # Recommended parameters for our copy strategy
        "recommended_params": {
            "tp_pct": round(abs(avg_win_pct) * 0.8, 2),  # 80% of their avg win as TP
            "sl_pct": round(abs(avg_loss_pct) * 1.2, 2),  # 120% of their avg loss as SL
            "preferred_direction": "LONG" if long_wr > short_wr + 0.05 else "SHORT" if short_wr > long_wr + 0.05 else "BOTH",
            "max_leverage": 5 if liq_rate > 0.02 else 10,
            "trade_frequency": f"{len(all_closed_trades) / 90:.1f} trades/day",
            "best_coins": [c["coin"] for c in coin_breakdown[:5] if c["win_rate"] > 0.5],
            "avoid_coins": [c["coin"] for c in coin_breakdown if c["win_rate"] < 0.4 and c["trades"] >= 5],
        },

        # Safety gate assessment
        "safety_gate_impact": {
            "needs_high_leverage": any(t.get("was_liquidated") for t in all_closed_trades),
            "needs_short_selling": len(shorts) > len(all_closed_trades) * 0.2,
            "uses_tight_stops": abs(avg_loss_pct) < 1.5,
            "uses_wide_stops": abs(avg_loss_pct) > 5,
            "high_frequency": len(all_closed_trades) / 90 > 5,
            "recommendation": (
                "EXEMPT_FROM_SAFETY_GATES" if total_wr > 0.65 and pf > 2.0
                else "REDUCED_SAFETY_GATES" if total_wr > 0.55 and pf > 1.5
                else "STANDARD_SAFETY_GATES"
            ),
        },
    }

    # Print summary
    print(f"\n  [PICK] STRATEGY DNA:")
    print(f"     Style: {trading_style} | Entry: {entry_style}")
    print(f"     Direction: {direction_bias} (L:{len(longs)} S:{len(shorts)})")
    print(f"     Hold: {median_hold:.1f}h median ({p25_hold:.1f}-{p75_hold:.1f}h range)")
    print(f"     WR: {total_wr*100:.1f}% | PF: {pf} | R:R: {profile['performance']['risk_reward_ratio']}")
    print(f"     Avg Win: +{avg_win_pct:.2f}% | Avg Loss: {avg_loss_pct:.2f}%")
    print(f"     Top coins: {', '.join(profile['primary_coins'])}")
    print(f"     Best hours (UTC): {profile['timing']['peak_entry_hours_utc'][:3]}")
    print(f"     Safety: {profile['safety_gate_impact']['recommendation']}")
    print(f"     Recommended TP: {profile['recommended_params']['tp_pct']:.2f}% | SL: {profile['recommended_params']['sl_pct']:.2f}%")

    return profile


def run_reverse_engineering():
    """Load qualified traders and reverse-engineer each one's strategy."""
    print("=" * 70)
    print("  STRATEGY REVERSE ENGINEERING ENGINE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load qualified traders
    qt_path = DATA_DIR / "qualified_traders.json"
    if not qt_path.exists():
        print("  ERROR: No qualified_traders.json found. Run hyperliquid_scraper.py first.")
        return

    with open(qt_path) as f:
        data = json.load(f)

    traders = data.get("traders", [])
    print(f"  Qualified traders to analyze: {len(traders)}")

    all_profiles = []
    for trader in traders:
        addr = trader["address"]
        label = trader.get("label", addr[:10])
        try:
            profile = reverse_engineer_trader(addr, label)
            if profile:
                all_profiles.append(profile)
            time.sleep(0.5)
        except Exception as e:
            print(f"  [ERROR] {label}: {e}")

    # Save strategy profiles (merge with existing, don't overwrite)
    out_path = DATA_DIR / "strategy_profiles.json"
    existing_profiles = {}
    if out_path.exists():
        try:
            with open(out_path) as f:
                existing_data = json.load(f)
            for ep in existing_data.get("profiles", []):
                existing_profiles[ep.get("address", "")] = ep
        except (json.JSONDecodeError, IOError):
            pass

    # Merge: new profiles overwrite existing ones by address, keep others
    for p in all_profiles:
        existing_profiles[p["address"]] = p

    merged_profiles = list(existing_profiles.values())

    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profiles": merged_profiles,
        }, f, indent=2, default=str)
    print(f"\n  [OK] Saved {len(merged_profiles)} strategy profiles to {out_path}")

    # Generate "our version" of their strategies as reproducible rules
    strategies_path = DATA_DIR / "extracted_strategies.json"
    extracted = []
    for p in all_profiles:
        dna = p.get("strategy_dna", {})
        perf = p.get("performance", {})
        params = p.get("recommended_params", {})
        safety = p.get("safety_gate_impact", {})

        # Build per-coin performance map for filtering
        coin_perf = {}
        for cb in p.get("coin_breakdown", []):
            coin_perf[cb["coin"]] = {
                "trades": cb.get("trades", 0),
                "win_rate": cb.get("win_rate", 0),
                "total_pnl": cb.get("total_pnl", 0),
                "avg_hold_hours": cb.get("avg_hold_hours", 0),
            }

        strategy = {
            "strategy_id": f"hl_copy_{p['label']}",
            "source_trader": p["address"],
            "source_label": p["label"],
            "description": f"{dna['trading_style']} {dna['entry_style']} on {', '.join(p.get('primary_coins', ['ETH']))}",
            "rules": {
                "coins": params.get("best_coins", []),
                "all_traded_coins": [c["coin"] for c in p.get("coin_breakdown", [])],
                "avoid_coins": params.get("avoid_coins", []),
                "direction": params.get("preferred_direction", "BOTH"),
                "tp_pct": params.get("tp_pct", 3.0),
                "sl_pct": params.get("sl_pct", 2.0),
                "max_leverage": params.get("max_leverage", 5),
                "entry_hours_utc": p.get("timing", {}).get("peak_entry_hours_utc", [])[:5],
                "min_hold_hours": dna.get("hold_p25_hours", 0.5),
                "typical_hold_hours": dna.get("median_hold_hours", 4),
            },
            "coin_performance": coin_perf,
            "expected_performance": {
                "win_rate": perf.get("win_rate", 0),
                "profit_factor": perf.get("profit_factor", 1),
                "avg_win_pct": perf.get("avg_win_pct", 0),
                "avg_loss_pct": perf.get("avg_loss_pct", 0),
                "trades_per_day": params.get("trade_frequency", "unknown"),
            },
            "safety_gate_mode": safety.get("recommendation", "STANDARD_SAFETY_GATES"),
            "run_dual_mode": True,  # Run with AND without safety gates
        }
        extracted.append(strategy)

    with open(strategies_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "strategies": extracted,
            "note": "Each strategy runs in dual mode: with safety gates AND without, to measure impact",
        }, f, indent=2, default=str)
    print(f"  [OK] Saved {len(extracted)} extracted strategies to {strategies_path}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"  Analyzed: {len(all_profiles)} traders")
    for p in all_profiles:
        dna = p["strategy_dna"]
        perf = p["performance"]
        safety = p["safety_gate_impact"]
        print(f"    {p['label']:25s} | {dna['trading_style']:16s} | {dna['entry_style']:20s} | "
              f"WR:{perf['win_rate']*100:5.1f}% | Safety: {safety['recommendation']}")
    print(f"{'='*70}\n")

    return all_profiles


if __name__ == "__main__":
    run_reverse_engineering()
