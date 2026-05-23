#!/usr/bin/env python3
"""
Strategy Learning Engine v2.0
==============================
Analyzes top traders' historical fills to reverse-engineer their actual
entry conditions, timing patterns, sizing behavior, and psychological
tendencies (post-win/loss behavior).

v2.0 enhancements:
- Per-coin strategy profiles (direction bias, TP/SL, hold time, entry hours per coin)
- EST timezone conversion for entry/exit times
- Leverage extraction from clearinghouse state
- TP/SL inference from PnL distribution (median win% = TP, median loss% = SL)
- Profit factor and avg PnL per trade per coin
- Best session per coin

Builds on strategy_reverse_engineer.py but goes deeper:
- Entry timing patterns (session, hour, day-of-week)
- Directional bias with context awareness
- Coin specialization scoring
- Position sizing pattern detection (fixed vs variable, scale-in/out)
- Hold time classification with percentile breakdown
- Win rate segmented by direction, coin, time
- Entry price pattern detection (dip buyer vs breakout chaser)
- Consecutive trade psychology (tilt detection, post-win sizing)
- Leverage usage patterns
- Day-of-week performance analysis

Output: copy_trader_intel/data/learned_strategies.json
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

try:
    import requests
except ImportError:
    print("[ERROR] requests module required: pip install requests")
    sys.exit(1)

HL_API = "https://api.hyperliquid.xyz/info"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Rate limit between HL API calls
HL_RATE_LIMIT_S = 0.8
MAX_TRADERS = 15
MIN_EDGE_SCORE = 60
MAX_FILLS_PER_TRADER = 100

# EST offset: UTC-5 (standard Eastern Time)
EST_OFFSET = timedelta(hours=-5)
TZ_EST = timezone(EST_OFFSET)


# ─── Trading Session Definitions (UTC) ───────────────────────────────────────

SESSIONS = {
    "ASIA_SESSION":   (0, 8),    # 00:00-08:00 UTC (Tokyo/Shanghai open)
    "LONDON_SESSION": (8, 14),   # 08:00-14:00 UTC (London open, pre-NY)
    "US_SESSION":     (14, 21),  # 14:00-21:00 UTC (NY open through close)
    "LATE_US":        (21, 24),  # 21:00-00:00 UTC (after-hours / low liquidity)
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ─── Hyperliquid API ──────────────────────────────────────────────────────────

def hl_post(payload, retries=3):
    """POST to Hyperliquid API with retry logic."""
    for attempt in range(retries):
        try:
            r = requests.post(HL_API, json=payload, timeout=15,
                              headers={"Content-Type": "application/json"})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5)
            else:
                print(f"    [WARN] HL API failed after {retries} attempts: {e}")
                return [] if isinstance(payload.get("type", ""), str) else {}


def fetch_fills(address, max_fills=MAX_FILLS_PER_TRADER):
    """Fetch recent fills for a trader from Hyperliquid.

    Uses userFills with a 90-day lookback. Returns up to max_fills.
    """
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp() * 1000)
    payload = {"type": "userFills", "user": address}
    result = hl_post(payload)

    if not isinstance(result, list):
        return []

    # Filter to last 90 days and cap
    fills = [f for f in result if f.get("time", 0) >= start_ms]
    fills.sort(key=lambda x: x.get("time", 0))
    return fills[-max_fills:]


def fetch_user_state(address):
    """Fetch clearinghouse state for leverage extraction.

    Returns dict with per-coin leverage from open positions.
    """
    payload = {"type": "clearinghouseState", "user": address}
    result = hl_post(payload)
    if not isinstance(result, dict):
        return {}
    return result


def extract_leverage_per_coin(user_state):
    """Extract per-coin leverage from clearinghouse state positions.

    Returns dict: coin -> leverage value (float).
    """
    leverage_map = {}
    positions = user_state.get("assetPositions", [])
    for pos in positions:
        p = pos.get("position", pos)
        coin = p.get("coin", "")
        if not coin:
            continue
        lev = p.get("leverage", {})
        if isinstance(lev, dict):
            lev_val = float(lev.get("value", 1))
        else:
            lev_val = float(lev) if lev else 1.0
        leverage_map[coin] = lev_val
    return leverage_map


def utc_hour_to_est(hour_utc):
    """Convert a UTC hour (0-23) to EST hour (0-23)."""
    return (hour_utc - 5) % 24


# ─── Trade Reconstruction ─────────────────────────────────────────────────────

def reconstruct_trades(fills):
    """Match open/close fills into complete trades.

    Returns list of closed trade dicts with entry/exit info including EST times.
    """
    by_coin = defaultdict(list)
    for fill in fills:
        coin = fill.get("coin", "")
        if not coin:
            continue
        by_coin[coin].append(fill)

    closed_trades = []

    for coin, coin_fills in by_coin.items():
        coin_fills.sort(key=lambda x: x.get("time", 0))

        open_fills = []  # stack for scale-in tracking
        for f in coin_fills:
            d = f.get("dir", "")
            px = float(f.get("px", 0))
            sz = float(f.get("sz", 0))
            t = f.get("time", 0)
            cpnl = float(f.get("closedPnl", 0))
            fee = float(f.get("fee", 0))
            is_liq = f.get("liquidation", False)

            if "Open" in d:
                open_fills.append({
                    "price": px, "size": sz, "time": t,
                    "direction": "LONG" if "Long" in d else "SHORT",
                    "fee": fee,
                })
            elif "Close" in d and open_fills:
                entry = open_fills.pop(0)  # FIFO matching
                hold_ms = t - entry["time"]
                hold_hours = hold_ms / (1000 * 3600) if hold_ms > 0 else 0

                if entry["direction"] == "LONG":
                    pnl_pct = (px - entry["price"]) / entry["price"] * 100 if entry["price"] > 0 else 0
                else:
                    pnl_pct = (entry["price"] - px) / entry["price"] * 100 if entry["price"] > 0 else 0

                entry_dt = datetime.fromtimestamp(entry["time"] / 1000, tz=timezone.utc)
                exit_dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)

                # EST conversions
                entry_dt_est = entry_dt.astimezone(TZ_EST)
                exit_dt_est = exit_dt.astimezone(TZ_EST)

                closed_trades.append({
                    "coin": coin,
                    "direction": entry["direction"],
                    "entry_price": entry["price"],
                    "exit_price": px,
                    "entry_time_ms": entry["time"],
                    "exit_time_ms": t,
                    "hold_hours": round(hold_hours, 3),
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_dollar": cpnl,
                    "entry_size": entry["size"],
                    "exit_size": sz,
                    "entry_fee": entry["fee"],
                    "exit_fee": fee,
                    "is_win": cpnl > 0 if cpnl != 0 else pnl_pct > 0,  # Use closedPnl (ground truth) over FIFO calc
                    "entry_hour_utc": entry_dt.hour,
                    "exit_hour_utc": exit_dt.hour,
                    "entry_hour_est": entry_dt_est.hour,
                    "exit_hour_est": exit_dt_est.hour,
                    "entry_time_est": entry_dt_est.strftime("%Y-%m-%d %H:%M EST"),
                    "exit_time_est": exit_dt_est.strftime("%Y-%m-%d %H:%M EST"),
                    "entry_day": DAY_NAMES[entry_dt.weekday()],
                    "exit_day": DAY_NAMES[exit_dt.weekday()],
                    "was_liquidated": is_liq,
                    "notional_usd": round(entry["price"] * entry["size"], 2),
                })

    closed_trades.sort(key=lambda x: x.get("entry_time_ms", 0))

    # FALLBACK: If FIFO produced too few trades but we have close fills with closedPnl,
    # use close fills directly. This handles traders with overlapping/partial fills
    # where opens < closes (common on Hyperliquid).
    if len(closed_trades) < 5:
        close_fills = [f for f in fills if "Close" in f.get("dir", "") and float(f.get("closedPnl", 0)) != 0]
        if len(close_fills) >= 5:
            closed_trades = []
            for f in close_fills:
                coin = f.get("coin", "")
                d = f.get("dir", "")
                px = float(f.get("px", 0))
                sz = float(f.get("sz", 0))
                t = f.get("time", 0)
                cpnl = float(f.get("closedPnl", 0))
                fee = float(f.get("fee", 0))
                is_liq = f.get("liquidation", False)
                direction = "LONG" if "Long" in d else "SHORT"

                dt_utc = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
                dt_est = dt_utc.astimezone(TZ_EST)

                closed_trades.append({
                    "coin": coin,
                    "direction": direction,
                    "entry_price": px,  # approximate (close price as proxy)
                    "exit_price": px,
                    "entry_time_ms": t,
                    "exit_time_ms": t,
                    "hold_hours": 0,  # unknown from close fills alone
                    "pnl_pct": round(cpnl / (px * sz) * 100, 4) if px * sz > 0 else 0,
                    "pnl_dollar": cpnl,
                    "entry_size": sz,
                    "exit_size": sz,
                    "entry_fee": 0,
                    "exit_fee": fee,
                    "is_win": cpnl > 0,
                    "entry_hour_utc": dt_utc.hour,
                    "exit_hour_utc": dt_utc.hour,
                    "entry_hour_est": dt_est.hour,
                    "exit_hour_est": dt_est.hour,
                    "entry_time_est": dt_est.strftime("%Y-%m-%d %H:%M EST"),
                    "exit_time_est": dt_est.strftime("%Y-%m-%d %H:%M EST"),
                    "entry_day": DAY_NAMES[dt_utc.weekday()],
                    "exit_day": DAY_NAMES[dt_utc.weekday()],
                    "was_liquidated": is_liq,
                    "notional_usd": round(px * sz, 2),
                    "_from_close_fill": True,
                })
            closed_trades.sort(key=lambda x: x.get("entry_time_ms", 0))

    return closed_trades


# ─── Per-Coin Strategy Builder ───────────────────────────────────────────────

def build_coin_strategies(trades, leverage_map=None):
    """Build a per-coin strategy profile from closed trades.

    For each coin the trader has traded, computes:
    - Direction bias (L/S ratio)
    - TP/SL from PnL% distribution (median win = TP, median loss = SL)
    - Hold time breakdown (wins vs losses)
    - Preferred entry hours (UTC + EST)
    - Win rate overall and by direction
    - Profit factor, avg PnL per trade
    - Best trading session
    - Position sizing
    - Leverage from clearinghouse state

    Args:
        trades: list of reconstructed trade dicts
        leverage_map: dict of coin -> leverage from clearinghouse (optional)

    Returns:
        dict: coin -> coin_profile dict
    """
    if leverage_map is None:
        leverage_map = {}

    coin_trades = defaultdict(list)
    for t in trades:
        coin_trades[t["coin"]].append(t)

    coin_strategies = {}

    for coin, ctrades in coin_trades.items():
        if len(ctrades) < 2:
            continue  # need at least 2 trades for meaningful stats

        # --- Direction breakdown ---
        longs = [t for t in ctrades if t["direction"] == "LONG"]
        shorts = [t for t in ctrades if t["direction"] == "SHORT"]
        total = len(ctrades)
        long_pct = len(longs) / total * 100 if total > 0 else 50

        if long_pct > 75:
            direction_bias = "LONG_ONLY"
        elif long_pct > 60:
            direction_bias = "LONG_BIASED"
        elif long_pct < 25:
            direction_bias = "SHORT_ONLY"
        elif long_pct < 40:
            direction_bias = "SHORT_BIASED"
        else:
            direction_bias = "BALANCED"

        # --- Win rates ---
        wins = [t for t in ctrades if t["is_win"]]
        losses = [t for t in ctrades if not t["is_win"]]
        win_rate = len(wins) / total if total > 0 else 0
        long_wins = sum(1 for t in longs if t["is_win"])
        short_wins = sum(1 for t in shorts if t["is_win"])
        long_wr = long_wins / max(len(longs), 1)
        short_wr = short_wins / max(len(shorts), 1)

        # --- TP/SL from PnL% distribution ---
        win_pnl_pcts = [t["pnl_pct"] for t in wins if t["pnl_pct"] > 0]
        loss_pnl_pcts = [abs(t["pnl_pct"]) for t in losses if t["pnl_pct"] < 0]

        median_tp_pct = round(statistics.median(win_pnl_pcts), 4) if win_pnl_pcts else 0
        median_sl_pct = round(statistics.median(loss_pnl_pcts), 4) if loss_pnl_pcts else 0
        avg_tp_pct = round(statistics.mean(win_pnl_pcts), 4) if win_pnl_pcts else 0
        avg_sl_pct = round(statistics.mean(loss_pnl_pcts), 4) if loss_pnl_pcts else 0
        max_win_pct = round(max(win_pnl_pcts), 4) if win_pnl_pcts else 0
        max_loss_pct = round(max(loss_pnl_pcts), 4) if loss_pnl_pcts else 0

        # --- Hold time ---
        all_holds = [t["hold_hours"] for t in ctrades if t["hold_hours"] >= 0]
        win_holds = [t["hold_hours"] for t in wins if t["hold_hours"] >= 0]
        loss_holds = [t["hold_hours"] for t in losses if t["hold_hours"] >= 0]

        median_hold = round(statistics.median(all_holds), 3) if all_holds else 0
        avg_hold_wins = round(statistics.mean(win_holds), 3) if win_holds else 0
        avg_hold_losses = round(statistics.mean(loss_holds), 3) if loss_holds else 0

        # --- Entry hour preferences (UTC + EST) ---
        hour_counts_utc = defaultdict(int)
        hour_counts_est = defaultdict(int)
        for t in ctrades:
            hour_counts_utc[t["entry_hour_utc"]] += 1
            hour_counts_est[t["entry_hour_est"]] += 1

        sorted_hours_utc = sorted(hour_counts_utc.items(), key=lambda x: x[1], reverse=True)
        sorted_hours_est = sorted(hour_counts_est.items(), key=lambda x: x[1], reverse=True)
        preferred_hours_utc = [h for h, _ in sorted_hours_utc[:3]]
        preferred_hours_est = [h for h, _ in sorted_hours_est[:3]]

        # --- Best session ---
        session_counts = defaultdict(int)
        session_wins = defaultdict(int)
        for t in ctrades:
            s = classify_session(t["entry_hour_utc"])
            session_counts[s] += 1
            if t["is_win"]:
                session_wins[s] += 1

        best_session = "UNKNOWN"
        best_session_wr = 0
        for s, count in session_counts.items():
            if count >= 2:
                wr = session_wins.get(s, 0) / count
                if wr > best_session_wr:
                    best_session_wr = wr
                    best_session = s

        # --- Profit factor ---
        gross_profit = sum(t["pnl_dollar"] for t in ctrades if t["pnl_dollar"] > 0)
        gross_loss = abs(sum(t["pnl_dollar"] for t in ctrades if t["pnl_dollar"] < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

        # --- Avg PnL per trade ---
        total_pnl = sum(t["pnl_dollar"] for t in ctrades)
        avg_pnl_per_trade = round(total_pnl / total, 2) if total > 0 else 0

        # --- Position sizing ---
        notionals = [t["notional_usd"] for t in ctrades if t["notional_usd"] > 0]
        avg_position_usd = round(statistics.mean(notionals), 2) if notionals else 0

        # --- Leverage from clearinghouse ---
        leverage = leverage_map.get(coin, None)

        coin_profile = {
            "coin": coin,
            "direction_bias": direction_bias,
            "leverage": leverage,
            "median_tp_pct": median_tp_pct,
            "median_sl_pct": median_sl_pct,
            "avg_tp_pct": avg_tp_pct,
            "avg_sl_pct": avg_sl_pct,
            "max_win_pct": max_win_pct,
            "max_loss_pct": max_loss_pct,
            "median_hold_hours": median_hold,
            "avg_hold_hours_wins": avg_hold_wins,
            "avg_hold_hours_losses": avg_hold_losses,
            "preferred_entry_hours_est": preferred_hours_est,
            "preferred_entry_hours_utc": preferred_hours_utc,
            "win_rate": round(win_rate, 4),
            "long_wr": round(long_wr, 4),
            "short_wr": round(short_wr, 4),
            "sample_size": total,
            "long_count": len(longs),
            "short_count": len(shorts),
            "avg_position_usd": avg_position_usd,
            "profit_factor": profit_factor,
            "avg_pnl_per_trade": avg_pnl_per_trade,
            "total_pnl": round(total_pnl, 2),
            "best_session": best_session,
        }

        coin_strategies[coin] = coin_profile

    return coin_strategies


# ─── Pattern Analyzers ─────────────────────────────────────────────────────────

def classify_session(hour_utc):
    """Map an hour (0-23) to a trading session name."""
    for name, (start, end) in SESSIONS.items():
        if start <= hour_utc < end:
            return name
    return "ASIA_SESSION"  # wrap-around


def analyze_entry_timing(trades):
    """Analyze when the trader enters positions.

    Returns session preference, peak hours, and per-hour distribution.
    """
    if not trades:
        return {}

    hour_counts = defaultdict(int)
    session_counts = defaultdict(int)
    session_wins = defaultdict(int)

    for t in trades:
        h = t["entry_hour_utc"]
        hour_counts[h] += 1
        s = classify_session(h)
        session_counts[s] += 1
        if t["is_win"]:
            session_wins[s] += 1

    # Top 4 entry hours
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    peak_hours = [h for h, _ in sorted_hours[:4]]

    # EST peak hours
    peak_hours_est = [utc_hour_to_est(h) for h in peak_hours]

    # Preferred session (most trades)
    preferred = max(session_counts, key=session_counts.get) if session_counts else "UNKNOWN"

    # Session win rates
    session_wr = {}
    for s, count in session_counts.items():
        wr = session_wins.get(s, 0) / count if count > 0 else 0
        session_wr[s] = {"trades": count, "win_rate": round(wr, 3)}

    # Best session by win rate (min 5 trades)
    best_session = preferred
    best_wr = 0
    for s, info in session_wr.items():
        if info["trades"] >= 5 and info["win_rate"] > best_wr:
            best_wr = info["win_rate"]
            best_session = s

    return {
        "preferred_session": preferred,
        "best_session_by_wr": best_session,
        "entry_hours_utc": peak_hours,
        "entry_hours_est": peak_hours_est,
        "session_breakdown": session_wr,
        "hour_distribution": dict(sorted(hour_counts.items())),
    }


def analyze_direction_bias(trades):
    """Analyze long vs short tendencies and performance by direction."""
    if not trades:
        return {}

    longs = [t for t in trades if t["direction"] == "LONG"]
    shorts = [t for t in trades if t["direction"] == "SHORT"]
    total = len(trades)
    long_pct = len(longs) / total * 100 if total > 0 else 50

    if long_pct > 75:
        bias = "LONG_ONLY"
    elif long_pct > 60:
        bias = "LONG_BIASED"
    elif long_pct < 25:
        bias = "SHORT_ONLY"
    elif long_pct < 40:
        bias = "SHORT_BIASED"
    else:
        bias = "BALANCED"

    long_wr = sum(1 for t in longs if t["is_win"]) / max(len(longs), 1)
    short_wr = sum(1 for t in shorts if t["is_win"]) / max(len(shorts), 1)

    long_pnl = sum(t["pnl_dollar"] for t in longs)
    short_pnl = sum(t["pnl_dollar"] for t in shorts)

    return {
        "direction_bias": bias,
        "long_count": len(longs),
        "short_count": len(shorts),
        "long_pct": round(long_pct, 1),
        "long_win_rate": round(long_wr, 4),
        "short_win_rate": round(short_wr, 4),
        "long_total_pnl": round(long_pnl, 2),
        "short_total_pnl": round(short_pnl, 2),
        "better_direction": "LONG" if long_wr > short_wr + 0.03 else ("SHORT" if short_wr > long_wr + 0.03 else "EQUAL"),
    }


def analyze_coin_preferences(trades):
    """Analyze which coins the trader specializes in."""
    if not trades:
        return {}

    coin_data = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0, "hold_hours": []})

    for t in trades:
        c = t["coin"]
        coin_data[c]["trades"] += 1
        if t["is_win"]:
            coin_data[c]["wins"] += 1
        coin_data[c]["pnl"] += t["pnl_dollar"]
        coin_data[c]["hold_hours"].append(t["hold_hours"])

    best_coins = []
    for coin, data in sorted(coin_data.items(), key=lambda x: x[1]["trades"], reverse=True):
        wr = data["wins"] / data["trades"] if data["trades"] > 0 else 0
        avg_hold = statistics.mean(data["hold_hours"]) if data["hold_hours"] else 0
        best_coins.append({
            "coin": coin,
            "trades": data["trades"],
            "wr": round(wr, 3),
            "avg_pnl": round(data["pnl"] / data["trades"], 2) if data["trades"] > 0 else 0,
            "total_pnl": round(data["pnl"], 2),
            "avg_hold_h": round(avg_hold, 2),
        })

    # Specialization: does the trader focus on few coins?
    total = len(trades)
    top_coin_pct = best_coins[0]["trades"] / total * 100 if best_coins else 0
    if len(best_coins) <= 2 and top_coin_pct > 60:
        specialization = "SPECIALIST"
    elif len(best_coins) <= 5:
        specialization = "FOCUSED"
    else:
        specialization = "DIVERSIFIED"

    return {
        "best_coins": best_coins[:10],
        "specialization": specialization,
        "unique_coins": len(coin_data),
        "top_coin_share_pct": round(top_coin_pct, 1),
    }


def analyze_sizing_patterns(trades):
    """Detect if the trader uses fixed or variable position sizing, and scale-in/out."""
    if len(trades) < 3:
        return {"sizing_pattern": "INSUFFICIENT_DATA"}

    notionals = [t["notional_usd"] for t in trades if t["notional_usd"] > 0]
    if not notionals:
        return {"sizing_pattern": "UNKNOWN"}

    mean_size = statistics.mean(notionals)
    if len(notionals) >= 2:
        stdev_size = statistics.stdev(notionals)
    else:
        stdev_size = 0
    cv = stdev_size / mean_size if mean_size > 0 else 0  # coefficient of variation

    if cv < 0.15:
        pattern = "FIXED"
    elif cv < 0.4:
        pattern = "SEMI_FIXED"
    elif cv < 0.8:
        pattern = "VARIABLE"
    else:
        pattern = "HIGHLY_VARIABLE"

    # Scale-in detection: multiple opens on same coin before a close
    # (already partially captured in trade reconstruction, but check entry_size vs exit_size)
    size_changes = sum(1 for t in trades if abs(t["exit_size"] - t["entry_size"]) / max(t["entry_size"], 0.001) > 0.1)
    scale_ratio = size_changes / len(trades) if trades else 0

    return {
        "sizing_pattern": pattern,
        "avg_position_usd": round(mean_size, 2),
        "median_position_usd": round(statistics.median(notionals), 2),
        "size_stdev": round(stdev_size, 2),
        "coefficient_of_variation": round(cv, 3),
        "scale_in_out_ratio": round(scale_ratio, 3),
        "uses_scaling": scale_ratio > 0.2,
    }


def analyze_hold_time(trades):
    """Classify the trader's hold time style with percentile breakdown."""
    if not trades:
        return {}

    holds = [t["hold_hours"] for t in trades if t["hold_hours"] >= 0]
    if not holds:
        return {}

    sorted_holds = sorted(holds)
    n = len(sorted_holds)
    median_h = statistics.median(sorted_holds)
    mean_h = statistics.mean(sorted_holds)
    p10 = sorted_holds[int(n * 0.1)] if n > 10 else sorted_holds[0]
    p25 = sorted_holds[int(n * 0.25)] if n > 4 else sorted_holds[0]
    p75 = sorted_holds[int(n * 0.75)] if n > 4 else sorted_holds[-1]
    p90 = sorted_holds[int(n * 0.9)] if n > 10 else sorted_holds[-1]

    # Classify
    if median_h < 0.25:
        style = "SCALPER"
    elif median_h < 1:
        style = "MICRO_SCALPER"
    elif median_h < 8:
        style = "DAY_TRADER"
    elif median_h < 48:
        style = "SWING"
    elif median_h < 168:
        style = "POSITION"
    else:
        style = "LONG_TERM"

    return {
        "hold_style": style,
        "avg_hold_hours": round(mean_h, 2),
        "median_hold_hours": round(median_h, 3),
        "p10_hours": round(p10, 3),
        "p25_hours": round(p25, 3),
        "p75_hours": round(p75, 3),
        "p90_hours": round(p90, 3),
        "min_hold_hours": round(sorted_holds[0], 3),
        "max_hold_hours": round(sorted_holds[-1], 2),
    }


def analyze_entry_price_pattern(trades):
    """Detect if the trader buys dips or chases breakouts.

    Compares entry price to recent price movement (using preceding trades
    on the same coin as a proxy when we don't have candle data).
    """
    if len(trades) < 5:
        return {"entry_pattern": "INSUFFICIENT_DATA"}

    # Group by coin, compare entry price to prior entries on same coin
    coin_entries = defaultdict(list)
    for t in trades:
        coin_entries[t["coin"]].append(t)

    dip_count = 0
    breakout_count = 0
    neutral_count = 0
    total_compared = 0

    for coin, entries in coin_entries.items():
        if len(entries) < 2:
            continue
        for i in range(1, len(entries)):
            prev = entries[i - 1]
            curr = entries[i]

            if curr["direction"] == "LONG":
                if curr["entry_price"] < prev["entry_price"] * 0.995:
                    dip_count += 1
                elif curr["entry_price"] > prev["entry_price"] * 1.005:
                    breakout_count += 1
                else:
                    neutral_count += 1
            else:  # SHORT
                if curr["entry_price"] > prev["entry_price"] * 1.005:
                    dip_count += 1  # shorting a pump = "dip" equivalent
                elif curr["entry_price"] < prev["entry_price"] * 0.995:
                    breakout_count += 1  # shorting a drop = breakout short
                else:
                    neutral_count += 1
            total_compared += 1

    if total_compared == 0:
        return {"entry_pattern": "UNKNOWN"}

    dip_pct = dip_count / total_compared
    breakout_pct = breakout_count / total_compared

    if dip_pct > 0.5:
        pattern = "DIP_BUYER"
    elif breakout_pct > 0.5:
        pattern = "BREAKOUT_CHASER"
    elif abs(dip_pct - breakout_pct) < 0.1:
        pattern = "MIXED"
    elif dip_pct > breakout_pct:
        pattern = "LEAN_DIP"
    else:
        pattern = "LEAN_BREAKOUT"

    return {
        "entry_pattern": pattern,
        "dip_entries_pct": round(dip_pct * 100, 1),
        "breakout_entries_pct": round(breakout_pct * 100, 1),
        "neutral_entries_pct": round(neutral_count / max(total_compared, 1) * 100, 1),
        "entries_compared": total_compared,
    }


def analyze_consecutive_patterns(trades):
    """Detect post-win and post-loss behavior.

    After a win: do they increase size? Take another trade quickly?
    After a loss: do they pause? Reduce size? Tilt (trade more aggressively)?
    """
    if len(trades) < 5:
        return {"post_win_behavior": "INSUFFICIENT_DATA", "post_loss_behavior": "INSUFFICIENT_DATA"}

    post_win_sizes = []
    post_loss_sizes = []
    pre_win_sizes = []
    pre_loss_sizes = []

    post_win_gaps_h = []
    post_loss_gaps_h = []

    for i in range(1, len(trades)):
        prev = trades[i - 1]
        curr = trades[i]

        gap_h = (curr["entry_time_ms"] - prev["exit_time_ms"]) / (1000 * 3600)
        gap_h = max(0, gap_h)

        if prev["is_win"]:
            post_win_sizes.append(curr["notional_usd"])
            pre_win_sizes.append(prev["notional_usd"])
            post_win_gaps_h.append(gap_h)
        else:
            post_loss_sizes.append(curr["notional_usd"])
            pre_loss_sizes.append(prev["notional_usd"])
            post_loss_gaps_h.append(gap_h)

    # Post-win behavior
    if post_win_sizes and pre_win_sizes:
        avg_pre_win = statistics.mean(pre_win_sizes) if pre_win_sizes else 1
        avg_post_win = statistics.mean(post_win_sizes) if post_win_sizes else 1
        win_size_ratio = avg_post_win / avg_pre_win if avg_pre_win > 0 else 1
        avg_post_win_gap = statistics.mean(post_win_gaps_h) if post_win_gaps_h else 0

        if win_size_ratio > 1.2:
            post_win = "SIZE_UP"
        elif win_size_ratio < 0.8:
            post_win = "SIZE_DOWN"
        else:
            post_win = "STEADY"
    else:
        post_win = "UNKNOWN"
        avg_post_win_gap = 0
        win_size_ratio = 1.0

    # Post-loss behavior
    if post_loss_sizes and pre_loss_sizes:
        avg_pre_loss = statistics.mean(pre_loss_sizes) if pre_loss_sizes else 1
        avg_post_loss = statistics.mean(post_loss_sizes) if post_loss_sizes else 1
        loss_size_ratio = avg_post_loss / avg_pre_loss if avg_pre_loss > 0 else 1
        avg_post_loss_gap = statistics.mean(post_loss_gaps_h) if post_loss_gaps_h else 0

        if avg_post_loss_gap > 4:
            post_loss = f"PAUSE_{int(avg_post_loss_gap)}H"
        elif loss_size_ratio > 1.3:
            post_loss = "REVENGE_TRADE"
        elif loss_size_ratio < 0.7:
            post_loss = "REDUCE_SIZE"
        else:
            post_loss = "STEADY"
    else:
        post_loss = "UNKNOWN"
        avg_post_loss_gap = 0
        loss_size_ratio = 1.0

    return {
        "post_win_behavior": post_win,
        "post_win_size_ratio": round(win_size_ratio, 3),
        "avg_gap_after_win_h": round(avg_post_win_gap, 2),
        "post_loss_behavior": post_loss,
        "post_loss_size_ratio": round(loss_size_ratio, 3),
        "avg_gap_after_loss_h": round(avg_post_loss_gap, 2),
        "win_streak_data": _streak_analysis(trades),
    }


def _streak_analysis(trades):
    """Calculate max win/loss streaks."""
    max_w = max_l = curr_w = curr_l = 0
    for t in trades:
        if t["is_win"]:
            curr_w += 1
            curr_l = 0
            max_w = max(max_w, curr_w)
        else:
            curr_l += 1
            curr_w = 0
            max_l = max(max_l, curr_l)
    return {"max_win_streak": max_w, "max_loss_streak": max_l}


def analyze_day_of_week(trades):
    """Find best and worst trading days."""
    if not trades:
        return {}

    day_data = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0})
    for t in trades:
        d = t["entry_day"]
        day_data[d]["trades"] += 1
        if t["is_win"]:
            day_data[d]["wins"] += 1
        day_data[d]["pnl"] += t["pnl_dollar"]

    day_stats = {}
    best_day = worst_day = None
    best_wr = -1
    worst_wr = 2

    for day in DAY_NAMES:
        info = day_data.get(day, {"trades": 0, "wins": 0, "pnl": 0})
        wr = info["wins"] / info["trades"] if info["trades"] > 0 else 0
        day_stats[day] = {
            "trades": info["trades"],
            "win_rate": round(wr, 3),
            "pnl": round(info["pnl"], 2),
        }
        if info["trades"] >= 3:
            if wr > best_wr:
                best_wr = wr
                best_day = day
            if wr < worst_wr:
                worst_wr = wr
                worst_day = day

    return {
        "day_stats": day_stats,
        "best_day_of_week": best_day or "N/A",
        "worst_day_of_week": worst_day or "N/A",
    }


def analyze_leverage(trades):
    """Estimate leverage usage from position sizes vs account equity.

    Since HL fills don't directly report leverage, we estimate from
    notional/size patterns. This is approximate.
    """
    if not trades:
        return {}

    # HL fills include "startPosition" in some cases; we use notional as proxy
    notionals = [t["notional_usd"] for t in trades if t["notional_usd"] > 0]
    if not notionals:
        return {"avg_leverage": 0, "max_leverage_used": 0}

    # We can't determine exact leverage without account equity at trade time,
    # but we can report notional ranges
    return {
        "avg_notional_usd": round(statistics.mean(notionals), 2),
        "median_notional_usd": round(statistics.median(notionals), 2),
        "max_notional_usd": round(max(notionals), 2),
        "min_notional_usd": round(min(notionals), 2),
    }


def compute_trades_per_day(trades):
    """Calculate average trades per day over the analysis window."""
    if len(trades) < 2:
        return 0
    first_ms = trades[0]["entry_time_ms"]
    last_ms = trades[-1]["entry_time_ms"]
    span_days = (last_ms - first_ms) / (1000 * 86400)
    if span_days < 1:
        span_days = 1
    return round(len(trades) / span_days, 1)


# ─── Actionable Rule Generator ────────────────────────────────────────────────

def generate_actionable_rules(trader_label, direction_info, timing_info, coin_info,
                              hold_info, entry_info, consec_info, sizing_info,
                              day_info, trades, coin_strategies=None):
    """Generate human-readable actionable trading rules from learned patterns.

    v2.0: Now includes per-coin specific rules when coin_strategies is provided.
    """
    rules = []

    # Direction rule
    bias = direction_info.get("direction_bias", "BALANCED")
    better = direction_info.get("better_direction", "EQUAL")
    if better != "EQUAL":
        long_wr = direction_info.get("long_win_rate", 0)
        short_wr = direction_info.get("short_win_rate", 0)
        best_wr = max(long_wr, short_wr)
        rules.append(f"{better} preferred (WR: {best_wr*100:.0f}%)")

    # Session rule
    pref_session = timing_info.get("preferred_session", "")
    best_session = timing_info.get("best_session_by_wr", "")
    if pref_session:
        hours_utc = timing_info.get("entry_hours_utc", [])
        hours_est = timing_info.get("entry_hours_est", [])
        hours_utc_str = ",".join(str(h) for h in hours_utc[:3])
        hours_est_str = ",".join(str(h) for h in hours_est[:3])
        rules.append(f"Prefer {pref_session.replace('_', ' ')} entries (UTC: {hours_utc_str} / EST: {hours_est_str})")

    # Coin rule
    best_coins = coin_info.get("best_coins", [])
    winning_coins = [c for c in best_coins if c["wr"] >= 0.6 and c["trades"] >= 3]
    if winning_coins:
        coins_str = ", ".join(c["coin"] for c in winning_coins[:3])
        rules.append(f"Best coins: {coins_str}")

    # Per-coin TP/SL rules (v2.0)
    if coin_strategies:
        for coin, cs in sorted(coin_strategies.items(), key=lambda x: x[1].get("sample_size", 0), reverse=True):
            if cs.get("sample_size", 0) < 3:
                continue
            tp = cs.get("median_tp_pct", 0)
            sl = cs.get("median_sl_pct", 0)
            wr = cs.get("win_rate", 0)
            lev = cs.get("leverage")
            bias = cs.get("direction_bias", "BALANCED")

            parts = [f"{coin}: {bias}"]
            if tp > 0 and sl > 0:
                parts.append(f"TP:{tp:.1f}%/SL:{sl:.1f}%")
            if wr > 0:
                parts.append(f"WR:{wr*100:.0f}%")
            if lev is not None:
                parts.append(f"{lev:.0f}x lev")
            if cs.get("median_hold_hours", 0) > 0:
                mh = cs["median_hold_hours"]
                if mh < 1:
                    parts.append(f"hold:{mh*60:.0f}m")
                else:
                    parts.append(f"hold:{mh:.1f}h")

            rules.append(" | ".join(parts))

            # Only show top 5 coin-specific rules
            if len([r for r in rules if r.startswith(coin + ":")]) >= 5:
                break

    # Hold time rule
    style = hold_info.get("hold_style", "")
    med = hold_info.get("median_hold_hours", 0)
    if style and med > 0:
        if med < 1:
            rules.append(f"Scalp style: hold {med*60:.0f} min median")
        else:
            rules.append(f"{style} style: hold {med:.1f}h median")

    # Entry pattern rule
    ep = entry_info.get("entry_pattern", "")
    if ep == "DIP_BUYER":
        rules.append("Entry: buy dips (price below recent avg)")
    elif ep == "BREAKOUT_CHASER":
        rules.append("Entry: chase breakouts (price above recent range)")
    elif ep == "LEAN_DIP":
        rules.append("Entry: lean toward dip buying")
    elif ep == "LEAN_BREAKOUT":
        rules.append("Entry: lean toward breakout entries")

    # Post-win/loss behavior
    pw = consec_info.get("post_win_behavior", "")
    pl = consec_info.get("post_loss_behavior", "")
    if pw == "SIZE_UP":
        ratio = consec_info.get("post_win_size_ratio", 1)
        rules.append(f"After win: increases size {ratio:.1f}x")
    if "PAUSE" in pl:
        rules.append(f"After loss: {pl.replace('_', ' ').lower()}")
    elif pl == "REVENGE_TRADE":
        rules.append("WARNING: revenge trades after losses (increases size)")
    elif pl == "REDUCE_SIZE":
        rules.append("After loss: reduces position size (disciplined)")

    # Day of week
    best_d = day_info.get("best_day_of_week", "N/A")
    worst_d = day_info.get("worst_day_of_week", "N/A")
    if best_d != "N/A" and worst_d != "N/A" and best_d != worst_d:
        rules.append(f"Best day: {best_d}, avoid: {worst_d}")

    # Position sizing
    sp = sizing_info.get("sizing_pattern", "")
    avg_sz = sizing_info.get("avg_position_usd", 0)
    if sp and avg_sz > 0:
        if avg_sz >= 1_000_000:
            sz_str = f"${avg_sz/1e6:.1f}M"
        elif avg_sz >= 1000:
            sz_str = f"${avg_sz/1e3:.0f}K"
        else:
            sz_str = f"${avg_sz:.0f}"
        rules.append(f"Position size: {sz_str} avg ({sp.lower().replace('_', ' ')})")

    return rules


# ─── Main Analysis Pipeline ───────────────────────────────────────────────────

def analyze_trader(address, label, trader_stats):
    """Full pattern analysis for one trader.

    Returns a learned strategy dict or None if insufficient data.
    """
    print(f"\n  Analyzing: {label} ({address[:10]}...)")

    fills = fetch_fills(address, max_fills=MAX_FILLS_PER_TRADER)
    time.sleep(HL_RATE_LIMIT_S)

    if not fills:
        print(f"    No fills returned")
        return None

    print(f"    Fills fetched: {len(fills)}")

    trades = reconstruct_trades(fills)
    if len(trades) < 5:
        print(f"    Only {len(trades)} closed trades, need at least 5")
        return None

    print(f"    Closed trades reconstructed: {len(trades)}")

    # Fetch clearinghouse state for leverage extraction
    user_state = fetch_user_state(address)
    leverage_map = extract_leverage_per_coin(user_state) if user_state else {}
    time.sleep(HL_RATE_LIMIT_S)

    if leverage_map:
        print(f"    Leverage data: {len(leverage_map)} coins ({', '.join(f'{c}:{v:.0f}x' for c, v in list(leverage_map.items())[:5])})")

    # Build per-coin strategy profiles (v2.0)
    coin_strategies = build_coin_strategies(trades, leverage_map)
    print(f"    Per-coin profiles built: {len(coin_strategies)} coins")

    # Run all analyzers
    timing = analyze_entry_timing(trades)
    direction = analyze_direction_bias(trades)
    coins = analyze_coin_preferences(trades)
    sizing = analyze_sizing_patterns(trades)
    hold = analyze_hold_time(trades)
    entry = analyze_entry_price_pattern(trades)
    consec = analyze_consecutive_patterns(trades)
    days = analyze_day_of_week(trades)
    leverage = analyze_leverage(trades)
    tpd = compute_trades_per_day(trades)

    # Overall win rate
    total_wr = sum(1 for t in trades if t["is_win"]) / len(trades)
    total_pnl = sum(t["pnl_dollar"] for t in trades)

    # Detect "never closes losers" pattern (survivorship bias warning)
    # If WR > 95% AND trader has open positions with unrealized losses
    never_closes_losers = False
    unrealized_losses_usd = 0
    if total_wr > 0.95 and user_state:
        positions = user_state.get("assetPositions", [])
        for pos in positions:
            p = pos.get("position", pos)
            upl = float(p.get("unrealizedPnl", 0))
            if upl < 0:
                unrealized_losses_usd += abs(upl)
        if unrealized_losses_usd > total_pnl * 0.5:  # unrealized losses > 50% of realized gains
            never_closes_losers = True
            print(f"    [WARN] SURVIVORSHIP BIAS: WR={total_wr*100:.0f}% but ${unrealized_losses_usd:,.0f} in unrealized losses (only closes winners)")

    # Profit factor
    gross_profit = sum(t["pnl_dollar"] for t in trades if t["pnl_dollar"] > 0)
    gross_loss = abs(sum(t["pnl_dollar"] for t in trades if t["pnl_dollar"] < 0))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

    # Generate rules (v2.0: pass coin_strategies for per-coin rules)
    rules = generate_actionable_rules(
        label, direction, timing, coins, hold, entry, consec, sizing, days, trades,
        coin_strategies=coin_strategies
    )

    # Confidence: based on sample size and consistency
    n = len(trades)
    consistency_bonus = 0.1 if sizing.get("coefficient_of_variation", 1) < 0.3 else 0
    sample_factor = min(n / 50, 1.0)  # max confidence at 50+ trades
    wr_factor = total_wr * 0.4
    confidence = round(min(0.95, sample_factor * 0.5 + wr_factor + consistency_bonus), 2)

    result = {
        "trader_label": label,
        "trader_address": address,
        "trader_stats": {
            "win_rate": trader_stats.get("win_rate", total_wr),
            "pnl": trader_stats.get("total_realized_pnl", total_pnl),
            "edge_score": trader_stats.get("edge_score", 0),
        },
        "fills_analyzed": len(fills),
        "trades_reconstructed": len(trades),
        "survivorship_bias_warning": never_closes_losers,
        "unrealized_losses_usd": round(unrealized_losses_usd, 2) if never_closes_losers else 0,
        "coin_strategies": coin_strategies,
        "learned_patterns": {
            "trading_style": hold.get("hold_style", "UNKNOWN"),
            "preferred_session": timing.get("preferred_session", "UNKNOWN"),
            "best_session_by_wr": timing.get("best_session_by_wr", "UNKNOWN"),
            "entry_hours_utc": timing.get("entry_hours_utc", []),
            "entry_hours_est": timing.get("entry_hours_est", []),
            "session_breakdown": timing.get("session_breakdown", {}),
            "best_coins": coins.get("best_coins", [])[:5],
            "coin_specialization": coins.get("specialization", "UNKNOWN"),
            "direction_bias": direction.get("direction_bias", "BALANCED"),
            "long_win_rate": direction.get("long_win_rate", 0),
            "short_win_rate": direction.get("short_win_rate", 0),
            "better_direction": direction.get("better_direction", "EQUAL"),
            "avg_hold_hours": hold.get("avg_hold_hours", 0),
            "median_hold_hours": hold.get("median_hold_hours", 0),
            "hold_style": hold.get("hold_style", "UNKNOWN"),
            "hold_percentiles": {
                "p10": hold.get("p10_hours", 0),
                "p25": hold.get("p25_hours", 0),
                "p75": hold.get("p75_hours", 0),
                "p90": hold.get("p90_hours", 0),
            },
            "sizing_pattern": sizing.get("sizing_pattern", "UNKNOWN"),
            "avg_position_usd": sizing.get("avg_position_usd", 0),
            "uses_scaling": sizing.get("uses_scaling", False),
            "entry_pattern": entry.get("entry_pattern", "UNKNOWN"),
            "dip_entries_pct": entry.get("dip_entries_pct", 0),
            "breakout_entries_pct": entry.get("breakout_entries_pct", 0),
            "post_win_behavior": consec.get("post_win_behavior", "UNKNOWN"),
            "post_win_size_ratio": consec.get("post_win_size_ratio", 1.0),
            "post_loss_behavior": consec.get("post_loss_behavior", "UNKNOWN"),
            "post_loss_size_ratio": consec.get("post_loss_size_ratio", 1.0),
            "avg_gap_after_loss_h": consec.get("avg_gap_after_loss_h", 0),
            "max_win_streak": consec.get("win_streak_data", {}).get("max_win_streak", 0),
            "max_loss_streak": consec.get("win_streak_data", {}).get("max_loss_streak", 0),
            "leverage_info": leverage,
            "leverage_per_coin": leverage_map,
            "trades_per_day": tpd,
            "best_day_of_week": days.get("best_day_of_week", "N/A"),
            "worst_day_of_week": days.get("worst_day_of_week", "N/A"),
            "day_breakdown": days.get("day_stats", {}),
        },
        "overall_metrics": {
            "win_rate": round(total_wr, 4),
            "profit_factor": pf,
            "total_pnl": round(total_pnl, 2),
            "total_trades": len(trades),
        },
        "actionable_rules": rules,
        "confidence": confidence,
    }

    # Print summary
    print(f"    Style: {hold.get('hold_style', '?')} | Bias: {direction.get('direction_bias', '?')}")
    print(f"    Session: {timing.get('preferred_session', '?')} | Entry: {entry.get('entry_pattern', '?')}")
    print(f"    WR: {total_wr*100:.1f}% (L:{direction.get('long_win_rate',0)*100:.0f}% S:{direction.get('short_win_rate',0)*100:.0f}%)")
    print(f"    Hold: {hold.get('median_hold_hours', 0):.2f}h median | Coins: {coins.get('specialization', '?')}")
    print(f"    Post-win: {consec.get('post_win_behavior', '?')} | Post-loss: {consec.get('post_loss_behavior', '?')}")

    # Per-coin summary (v2.0)
    if coin_strategies:
        top_coins = sorted(coin_strategies.items(), key=lambda x: x[1].get("sample_size", 0), reverse=True)[:3]
        for coin, cs in top_coins:
            lev_str = f" {cs['leverage']:.0f}x" if cs.get("leverage") else ""
            print(f"    {coin}: {cs['direction_bias']} WR:{cs['win_rate']*100:.0f}% "
                  f"TP:{cs['median_tp_pct']:.1f}%/SL:{cs['median_sl_pct']:.1f}% "
                  f"hold:{cs['median_hold_hours']:.1f}h{lev_str} n={cs['sample_size']}")

    print(f"    Rules: {len(rules)} generated | Confidence: {confidence}")

    return result


def load_qualified_traders():
    """Load qualified traders from data files, filtered by edge_score."""
    qt_path = DATA_DIR / "qualified_traders.json"
    if not qt_path.exists():
        print("  [ERROR] qualified_traders.json not found. Run hyperliquid_scraper.py first.")
        return []

    with open(qt_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    traders = data.get("traders", [])

    # Filter by edge score and qualified status
    qualified = [
        t for t in traders
        if t.get("qualified", False) and t.get("edge_score", 0) >= MIN_EDGE_SCORE
    ]

    # Sort by edge score descending, cap at MAX_TRADERS
    qualified.sort(key=lambda x: x.get("edge_score", 0), reverse=True)
    return qualified[:MAX_TRADERS]


def run():
    """Main entry point: analyze all qualified traders and save learned strategies."""
    print("=" * 70)
    print("  STRATEGY LEARNING ENGINE v2.0")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Max traders: {MAX_TRADERS} | Min edge score: {MIN_EDGE_SCORE}")
    print(f"  Max fills per trader: {MAX_FILLS_PER_TRADER} | Rate limit: {HL_RATE_LIMIT_S}s")
    print(f"  Features: per-coin profiles, EST times, leverage, TP/SL inference")
    print("=" * 70)

    traders = load_qualified_traders()
    if not traders:
        print("  No qualified traders found with edge_score >= {MIN_EDGE_SCORE}")
        return []

    print(f"  Qualified traders to analyze: {len(traders)}")

    strategies = []
    errors = 0

    for i, trader in enumerate(traders, 1):
        addr = trader["address"]
        label = trader.get("label", addr[:12])
        print(f"\n--- [{i}/{len(traders)}] {label} (edge: {trader.get('edge_score', 0)}) ---")

        try:
            result = analyze_trader(addr, label, trader)
            if result:
                strategies.append(result)
                n_coins = len(result.get("coin_strategies", {}))
                print(f"    [OK] Learned {len(result['actionable_rules'])} rules, {n_coins} coin profiles")
            else:
                print(f"    [SKIP] Insufficient data")
        except Exception as e:
            errors += 1
            print(f"    [ERROR] {e}")
            import traceback
            traceback.print_exc()

    # Save results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "2.0",
        "traders_analyzed": len(strategies),
        "traders_skipped": len(traders) - len(strategies) - errors,
        "traders_errored": errors,
        "min_edge_score": MIN_EDGE_SCORE,
        "strategies": strategies,
    }

    out_path = DATA_DIR / "learned_strategies.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"  STRATEGY LEARNING COMPLETE v2.0")
    print(f"  Analyzed: {len(strategies)} traders | Errors: {errors}")
    print(f"  Output: {out_path}")

    # Summary table
    if strategies:
        print(f"\n  {'Trader':<28s} {'Style':<15s} {'Bias':<14s} {'WR':>6s} {'Coins':>5s} {'Rules':>5s}")
        print(f"  {'-'*28} {'-'*15} {'-'*14} {'-'*6} {'-'*5} {'-'*5}")
        for s in strategies:
            lp = s["learned_patterns"]
            wr = s["overall_metrics"]["win_rate"] * 100
            n_coins = len(s.get("coin_strategies", {}))
            print(f"  {s['trader_label']:<28s} "
                  f"{lp['hold_style']:<15s} "
                  f"{lp['direction_bias']:<14s} "
                  f"{wr:5.1f}% "
                  f"{n_coins:>5d} "
                  f"{len(s['actionable_rules']):>5d}")

    print(f"{'=' * 70}\n")
    return strategies


if __name__ == "__main__":
    run()
