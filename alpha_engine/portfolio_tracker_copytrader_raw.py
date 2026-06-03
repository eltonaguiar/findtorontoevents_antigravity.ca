#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

RAW Copy Trader Portfolio Tracker (UNGATED)
============================================
Forward-tests ALL copy trader signals with ZERO safety gates.
Purpose: compare "pure copy trader signals" vs the gated version
(portfolio_tracker_copytrader.py) to measure whether our gates help or hurt.

Differences from the gated version:
  - MIN_SCORE = 0 (accept everything)
  - NO blackout hours (same as gated, but explicit)
  - NO symbol blacklist
  - NO correlation group limits
  - NO consecutive loss cooldown
  - NO consecutive loss guard per symbol
  - NO LONG-only mode restriction (accepts SHORTs too)
  - NO stale entry guard
  - NO strategy keyword filter (accepts ALL strategies, not just scalp/breakout)

Still tracks: equity, W/L, PnL, trailing stops, hold duration metrics.
Still uses: trailing stops, TP/SL, time-based exits, anti-martingale sizing.

Portfolio file: data/portfolio_copytrader_raw.json
Run every 30 min alongside other trackers for comparative data.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
try:
    from conformal_sizing import ConformalSizer
except ImportError:
    ConformalSizer = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_copytrader_raw.json")
ACTIVE_PICKS_FILE = os.path.join(DATA_DIR, "active_picks.json")

LEVERAGE = 1
BASE_POSITION_SIZE = 150
MIN_SCORE = 0  # *** UNGATED: accept ALL scores ***
MAX_TOTAL_POSITIONS = 10

# Copy trader consensus sizing (same as gated)
CONSENSUS_SIZE_1 = 100
CONSENSUS_SIZE_2 = 150
CONSENSUS_SIZE_3_PLUS = 200

# Time exits (same discipline)
OPTIMAL_HOLD_HOURS = 8
MAX_HOLD_HOURS = 24

# Trailing stop (same parameters)
TRAILING_STOP_ACTIVATION = 0.015
TRAILING_STOP_DISTANCE = 0.008
MAX_STOP_DISTANCE_PCT = 0.03
MIN_STOP_DISTANCE_PCT = 0.01

# SL grace period (same)
SL_GRACE_PERIOD_HOURS = 2
SL_WIDEN_PERIOD_HOURS = 1
SL_WIDEN_FACTOR = 1.3

# Anti-Martingale (same)
USE_ANTI_MARTINGALE = True
ANTI_MARTINGALE_WIN_BOOST = 1.20
ANTI_MARTINGALE_LOSS_SHRINK = 0.80
ANTI_MARTINGALE_MAX_MULT = 1.8
ANTI_MARTINGALE_MIN_MULT = 0.5
ANTI_MARTINGALE_RESET_AFTER = 5

# *** UNGATED: Accept ALL strategies, not just copy trader pattern ones ***
# No ACCEPTED_STRATEGIES filter, no STRATEGY_KEYWORDS filter

# *** UNGATED: No correlation group limits ***
# Correlation groups kept only for metrics tracking, not for blocking
CORRELATION_GROUPS = {
    "large_cap": ["BTC-USD", "BTCUSDT", "ETH-USD", "ETHUSDT"],
    "alt_l1": ["SOL-USD", "SOLUSDT", "AVAX-USD", "AVAXUSDT", "NEAR-USD", "NEARUSDT", "DOT-USD", "DOTUSDT"],
    "defi": ["LINK-USD", "LINKUSDT", "UNI-USD", "UNIUSDT", "AAVE-USD", "AAVEUSDT"],
    "meme": ["DOGE-USD", "DOGEUSDT", "SHIB-USD", "SHIBUSDT"],
    "exchange": ["BNB-USD", "BNBUSDT"],
    "infra": ["RENDER-USD", "RENDERUSDT", "FIL-USD", "FILUSDT", "FET-USD", "FETUSDT"],
}

HOLD_DURATION_BUCKETS = ["0-4h", "4-12h", "12-24h", "24h+"]


def fetch_prices():
    """Fetch live prices with 3-API fallback chain."""
    apis = [
        ("https://api.binance.com/api/v3/ticker/price", "binance"),
        ("https://api1.binance.com/api/v3/ticker/price", "binance_mirror"),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,bnb,fetch-ai,render-token,tia-token,atom,ondo,cake,zec&vs_currencies=usd", "coingecko"),
    ]

    for url, source in apis:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())

            if source.startswith("binance"):
                return {t["symbol"]: float(t["price"]) for t in data}
            elif source == "coingecko":
                mapping = {
                    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                    "dogecoin": "DOGEUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
                    "avalanche-2": "AVAXUSDT", "chainlink": "LINKUSDT", "polkadot": "DOTUSDT",
                    "near": "NEARUSDT", "shiba-inu": "SHIBUSDT", "filecoin": "FILUSDT",
                    "bnb": "BNBUSDT", "fetch-ai": "FETUSDT", "render-token": "RENDERUSDT",
                    "atom": "ATOMUSDT", "cake": "CAKEUSDT",
                }
                prices = {}
                for cg_id, sym in mapping.items():
                    if cg_id in data and "usd" in data[cg_id]:
                        prices[sym] = float(data[cg_id]["usd"])
                return prices
        except Exception:
            continue
    return {}


def get_anti_martingale_multiplier(closed_positions):
    """Anti-Martingale: scale up after wins, down after losses."""
    if not USE_ANTI_MARTINGALE or not closed_positions:
        return 1.0

    streak = 0
    streak_type = None

    for pos in reversed(closed_positions[-20:]):
        pnl = pos.get("pnl_pct", pos.get("pnl_usdt", 0)) or 0
        is_win = pnl > 0

        if streak_type is None:
            streak_type = "win" if is_win else "loss"
            streak = 1
        elif (streak_type == "win" and is_win) or (streak_type == "loss" and not is_win):
            streak += 1
            if streak >= ANTI_MARTINGALE_RESET_AFTER:
                break
        else:
            break

    if streak_type == "win":
        mult = ANTI_MARTINGALE_WIN_BOOST ** streak
    elif streak_type == "loss":
        mult = ANTI_MARTINGALE_LOSS_SHRINK ** streak
    else:
        mult = 1.0

    mult = max(ANTI_MARTINGALE_MIN_MULT, min(ANTI_MARTINGALE_MAX_MULT, mult))
    return round(mult, 2)


def get_hold_duration_bucket(hours):
    if hours < 4:
        return "0-4h"
    elif hours < 12:
        return "4-12h"
    elif hours < 24:
        return "12-24h"
    else:
        return "24h+"


def get_consensus_position_size(pick):
    consensus = int(pick.get("consensus_count", pick.get("copy_trader_count", 1)) or 1)
    if consensus >= 3:
        return CONSENSUS_SIZE_3_PLUS
    elif consensus >= 2:
        return CONSENSUS_SIZE_2
    else:
        return CONSENSUS_SIZE_1


def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                portfolio = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[WARN] Corrupted portfolio JSON, resetting: {e}")
            return _new_portfolio()
        _defaults = {
            "tp_hits": 0, "sl_hits": 0, "trailing_stops": 0,
            "best_trade_pnl": 0, "worst_trade_pnl": 0,
            "total_pnl_usdt": 0, "wins": 0, "losses": 0, "total_trades": 0,
            "time_exits": 0,
        }
        for k, v in _defaults.items():
            portfolio.setdefault("stats", {}).setdefault(k, v)
        portfolio["stats"].setdefault("copytrader_metrics", _default_copytrader_metrics())
        return portfolio
    return _new_portfolio()


def _default_copytrader_metrics():
    return {
        "avg_hold_hours": 0,
        "total_hold_hours": 0,
        "hold_duration_buckets": {
            "0-4h": {"trades": 0, "wins": 0, "pnl": 0},
            "4-12h": {"trades": 0, "wins": 0, "pnl": 0},
            "12-24h": {"trades": 0, "wins": 0, "pnl": 0},
            "24h+": {"trades": 0, "wins": 0, "pnl": 0},
        },
        "entry_hour_performance": {},
    }


def _new_portfolio():
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "starting_balance": 10000,
        "current_balance": 10000,
        "leverage": LEVERAGE,
        "tracker_type": "copytrader_raw_ungated",
        "description": (
            "UNGATED copy trader forward-test. Accepts ALL picks with NO safety gates "
            "(no min score, no blacklist, no correlation limits, no LONG-only, no cooldowns). "
            "Purpose: compare pure signals vs gated version to see if gates add value."
        ),
        "positions": {},
        "closed_positions": [],
        "snapshots": [],
        "stats": {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "tp_hits": 0,
            "sl_hits": 0,
            "trailing_stops": 0,
            "time_exits": 0,
            "total_pnl_usdt": 0,
            "best_trade_pnl": 0,
            "worst_trade_pnl": 0,
            "copytrader_metrics": _default_copytrader_metrics(),
        },
    }


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, default=str)


def normalize_symbol(sym):
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


def update_copytrader_metrics(portfolio, pos):
    metrics = portfolio["stats"].setdefault("copytrader_metrics", _default_copytrader_metrics())

    hours_held = pos.get("hours_held", 0)
    pnl_usdt = pos.get("pnl_usdt", 0)
    is_win = pnl_usdt > 0

    total_closed = portfolio["stats"]["wins"] + portfolio["stats"]["losses"]
    if total_closed > 0:
        metrics["total_hold_hours"] = metrics.get("total_hold_hours", 0) + hours_held
        metrics["avg_hold_hours"] = round(metrics["total_hold_hours"] / total_closed, 2)

    bucket = get_hold_duration_bucket(hours_held)
    bucket_stats = metrics.setdefault("hold_duration_buckets", {}).setdefault(
        bucket, {"trades": 0, "wins": 0, "pnl": 0}
    )
    bucket_stats["trades"] += 1
    if is_win:
        bucket_stats["wins"] += 1
    bucket_stats["pnl"] = round(bucket_stats["pnl"] + pnl_usdt, 2)

    try:
        opened_at = datetime.fromisoformat(pos.get("opened_at", ""))
        entry_hour = str(opened_at.hour)
        hour_stats = metrics.setdefault("entry_hour_performance", {}).setdefault(
            entry_hour, {"trades": 0, "wins": 0, "pnl": 0}
        )
        hour_stats["trades"] += 1
        if is_win:
            hour_stats["wins"] += 1
        hour_stats["pnl"] = round(hour_stats["pnl"] + pnl_usdt, 2)
    except Exception:
        pass


def run_check():
    """Main portfolio check -- call every 30 min. UNGATED version."""
    portfolio = load_portfolio()
    prices = fetch_prices()

    conformal = ConformalSizer(coverage=0.90) if ConformalSizer else None

    if not prices:
        print("[RAW COPYTRADER TRACKER] Failed to fetch prices from all APIs")
        return portfolio

    if "copytrader_metrics" not in portfolio["stats"]:
        portfolio["stats"]["copytrader_metrics"] = _default_copytrader_metrics()
    if "trailing_stops" not in portfolio["stats"]:
        portfolio["stats"]["trailing_stops"] = 0
    if "time_exits" not in portfolio["stats"]:
        portfolio["stats"]["time_exits"] = 0

    now = datetime.now(timezone.utc)

    # Load active picks
    try:
        with open(ACTIVE_PICKS_FILE, "r", encoding="utf-8") as f:
            active_picks = json.load(f)
    except Exception:
        active_picks = []

    # === Check existing positions for TP/SL ===
    positions_to_close = []
    for pos_id, pos in list(portfolio["positions"].items()):
        sym = normalize_symbol(pos["symbol"])
        current = prices.get(sym, 0)
        if current <= 0:
            continue

        entry = pos["entry_price"]
        direction = pos["direction"]

        # SANITY CHECK 1: Exit price must be within 50% of entry (catches data errors like TAO $272 -> $0.058)
        if entry > 0 and current > 0:
            price_change = abs(current - entry) / entry
            if price_change > 0.50:  # >50% move is suspicious
                print(f"  [SANITY] SUSPICIOUS exit for {pos['symbol']}: entry=${entry:.4f} exit=${current:.4f} ({price_change*100:.0f}% change)")
                print(f"  [SANITY] Capping exit at entry +/- 20% to prevent phantom PnL")
                if current > entry:
                    current = entry * 1.20  # Cap at +20%
                else:
                    current = entry * 0.80  # Cap at -20%

        if direction in ("LONG", "BUY"):
            pnl_pct = (current - entry) / entry
        else:
            pnl_pct = (entry - current) / entry

        pos_size = pos.get("position_size", BASE_POSITION_SIZE)
        pnl_usdt = pos_size * pnl_pct

        # SANITY CHECK 3: PnL must be within reasonable bounds
        max_pnl_pct = 0.50  # 50% max for 1x spot
        if abs(pnl_pct) > max_pnl_pct:
            print(f"  [SANITY] CAPPING PnL for {pos['symbol']}: {pnl_pct*100:.1f}% exceeds max {max_pnl_pct*100:.0f}%")
            pnl_pct = max_pnl_pct if pnl_pct > 0 else -max_pnl_pct
            pnl_usdt = pos_size * pnl_pct

        try:
            opened_at = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
            hours_open = (now - opened_at).total_seconds() / 3600
        except Exception:
            hours_open = 999

        # Check TP hit
        tp = pos.get("take_profit", 0)
        if tp > 0:
            tp_hit = False
            if direction in ("LONG", "BUY") and current >= tp:
                tp_hit = True
            elif direction in ("SHORT", "SELL") and current <= tp:
                tp_hit = True

            if tp_hit:
                pos["close_reason"] = "TP_HIT"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = pnl_pct * 100
                pos["pnl_usdt"] = pnl_usdt
                pos["hours_held"] = round(hours_open, 1)
                positions_to_close.append(pos_id)
                portfolio["stats"]["tp_hits"] += 1
                portfolio["stats"]["wins"] += 1
                print(f"  TP HIT: {pos['symbol']} {direction} entry={entry:.6f} tp={tp:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT ({hours_open:.1f}h)")
                continue

        # Check SL hit (with grace period)
        sl = pos.get("stop_loss", 0)
        if sl > 0:
            if hours_open < SL_GRACE_PERIOD_HOURS:
                if hours_open < SL_WIDEN_PERIOD_HOURS:
                    if entry > 0:
                        sl_dist = abs(entry - sl)
                        widened_dist = sl_dist * SL_WIDEN_FACTOR
                        if direction in ("LONG", "BUY"):
                            effective_sl = entry - widened_dist
                        else:
                            effective_sl = entry + widened_dist
                    else:
                        effective_sl = sl
                else:
                    effective_sl = sl

                sl_hit_grace = False
                if direction in ("LONG", "BUY") and current <= effective_sl:
                    sl_hit_grace = True
                elif direction in ("SHORT", "SELL") and current >= effective_sl:
                    sl_hit_grace = True

                if not sl_hit_grace:
                    if direction in ("LONG", "BUY") and current <= sl:
                        print(f"  [SL GRACE] {pos['symbol']}: SL breached but within {hours_open:.1f}h grace period -- holding")
                    sl = 0

            sl_hit = False
            if sl > 0:
                if direction in ("LONG", "BUY") and current <= sl:
                    sl_hit = True
                elif direction in ("SHORT", "SELL") and current >= sl:
                    sl_hit = True

            if sl_hit:
                pos["close_reason"] = "SL_HIT"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = pnl_pct * 100
                pos["pnl_usdt"] = pnl_usdt
                pos["hours_held"] = round(hours_open, 1)
                positions_to_close.append(pos_id)
                portfolio["stats"]["sl_hits"] += 1
                portfolio["stats"]["losses"] += 1
                print(f"  SL HIT: {pos['symbol']} {direction} entry={entry:.6f} sl={pos.get('stop_loss', 0):.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT ({hours_open:.1f}h)")
                continue

        # === Trailing Stop ===
        if direction in ("LONG", "BUY"):
            if "hwm_price" not in pos or current > pos.get("hwm_price", 0):
                pos["hwm_price"] = current
        else:
            if "hwm_price" not in pos or current < pos.get("hwm_price", float("inf")):
                pos["hwm_price"] = current

        if pnl_pct >= TRAILING_STOP_ACTIVATION:
            hwm = pos["hwm_price"]
            if direction in ("LONG", "BUY"):
                new_trail = hwm * (1 - TRAILING_STOP_DISTANCE)
                old_trail = pos.get("trailing_stop", 0)
                pos["trailing_stop"] = max(old_trail, new_trail)
            else:
                new_trail = hwm * (1 + TRAILING_STOP_DISTANCE)
                old_trail = pos.get("trailing_stop", float("inf"))
                pos["trailing_stop"] = min(old_trail, new_trail)

        trail = pos.get("trailing_stop", 0)
        if trail > 0:
            trail_hit = False
            if direction in ("LONG", "BUY") and current <= trail:
                trail_hit = True
            elif direction in ("SHORT", "SELL") and trail < float("inf") and current >= trail:
                trail_hit = True

            if trail_hit:
                if direction in ("LONG", "BUY"):
                    trail_pnl = (current - entry) / entry
                else:
                    trail_pnl = (entry - current) / entry
                pos["close_reason"] = "TRAILING_STOP"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = trail_pnl * 100
                pos["pnl_usdt"] = pos["position_size"] * trail_pnl
                pos["hours_held"] = round(hours_open, 1)
                positions_to_close.append(pos_id)
                portfolio["stats"]["trailing_stops"] += 1
                if trail_pnl > 0:
                    portfolio["stats"]["wins"] += 1
                else:
                    portfolio["stats"]["losses"] += 1
                print(f"  TRAILING STOP: {pos['symbol']} {direction} entry={entry:.6f} trail={trail:.6f} now={current:.6f} pnl=${pos['pnl_usdt']:+.2f} ({hours_open:.1f}h)")
                continue

        # === Time-Based Exit ===
        time_exit = False
        time_exit_reason = ""

        if hours_open > OPTIMAL_HOLD_HOURS and pnl_pct > 0:
            time_exit = True
            time_exit_reason = "TIME_EXIT_PROFIT"
            print(f"  TIME EXIT (PROFIT): {pos['symbol']} {direction} open {hours_open:.1f}h > {OPTIMAL_HOLD_HOURS}h, pnl={pnl_pct*100:+.2f}% -- locking profits")
        elif hours_open > MAX_HOLD_HOURS:
            time_exit = True
            time_exit_reason = "TIME_EXIT_MAX_HOLD"
            print(f"  TIME EXIT (MAX HOLD): {pos['symbol']} {direction} open {hours_open:.1f}h > {MAX_HOLD_HOURS}h max -- force closing, pnl={pnl_pct*100:+.2f}%")

        if time_exit:
            pos["close_reason"] = time_exit_reason
            pos["close_price"] = current
            pos["close_time"] = now.isoformat()
            pos["pnl_pct"] = pnl_pct * 100
            pos["pnl_usdt"] = pnl_usdt
            pos["hours_held"] = round(hours_open, 1)
            positions_to_close.append(pos_id)
            portfolio["stats"]["time_exits"] = portfolio["stats"].get("time_exits", 0) + 1
            if pnl_pct > 0:
                portfolio["stats"]["wins"] += 1
            else:
                portfolio["stats"]["losses"] += 1
            continue

        # Update position state
        if "high_water_mark_pnl" not in pos:
            pos["high_water_mark_pnl"] = pnl_pct * 100
        pos["high_water_mark_pnl"] = max(pos["high_water_mark_pnl"], pnl_pct * 100)
        pos["current_pnl_pct"] = pnl_pct * 100
        pos["current_pnl_usdt"] = pnl_usdt
        pos["current_price"] = current
        pos["last_checked"] = now.isoformat()

    # Close positions and update metrics
    for pos_id in positions_to_close:
        pos = portfolio["positions"].pop(pos_id)
        portfolio["closed_positions"].append(pos)
        portfolio["stats"]["total_pnl_usdt"] += pos["pnl_usdt"]
        portfolio["current_balance"] += pos["pnl_usdt"]
        if pos["pnl_usdt"] > portfolio["stats"]["best_trade_pnl"]:
            portfolio["stats"]["best_trade_pnl"] = pos["pnl_usdt"]
        if pos["pnl_usdt"] < portfolio["stats"]["worst_trade_pnl"]:
            portfolio["stats"]["worst_trade_pnl"] = pos["pnl_usdt"]

        update_copytrader_metrics(portfolio, pos)

        if conformal is not None:
            ml_at_entry = pos.get("ml_score_at_entry", pos.get("score", 50) / 100.0)
            win = 1.0 if pos["pnl_usdt"] > 0 else 0.0
            conformal.update(ml_at_entry, win)

    # === Add new positions from active picks (UNGATED) ===
    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        # *** UNGATED: NO cooldown check ***
        # *** UNGATED: NO strategy filter ***
        # *** UNGATED: NO correlation group limit ***

        # Max total positions cap (still needed to prevent infinite positions)
        if len(portfolio["positions"]) >= MAX_TOTAL_POSITIONS:
            break

        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        score = float(pick.get("elite_score", pick.get("score", pick.get("confidence", 0))) or 0)

        # *** UNGATED: MIN_SCORE = 0, accept all ***
        # (no score filter at all)

        # *** UNGATED: NO blackout hours ***
        # *** UNGATED: NO symbol blacklist ***
        # *** UNGATED: NO correlation group check ***
        # *** UNGATED: NO consecutive loss guard per symbol ***

        # Skip if already in portfolio (same symbol + strategy) -- basic dedup only
        pos_key = f"{sym}_{strategy}"
        if pos_key in portfolio["positions"]:
            continue

        # Only 1 position per normalized symbol (basic dedup)
        norm_base = normalize_symbol(sym)
        existing_syms = {normalize_symbol(p["symbol"]) for p in portfolio["positions"].values()}
        if norm_base in existing_syms:
            continue

        entry = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()

        # *** UNGATED: NO LONG-only restriction -- accept SHORTs too ***
        # *** UNGATED: NO stale entry guard ***

        if entry <= 0:
            continue

        # Verify current price is close to entry
        norm_sym = normalize_symbol(sym)
        current = prices.get(norm_sym, 0)
        if current > 0:
            gap = abs(current - entry) / entry
            if gap > 0.05:
                continue
            entry = current

        # SANITY CHECK 2: Entry price must be within 10% of live market price
        live_price = prices.get(norm_sym, 0)
        if live_price > 0 and entry > 0:
            entry_gap = abs(entry - live_price) / live_price
            if entry_gap > 0.10:  # >10% stale
                print(f"  [SANITY] STALE entry for {sym}: entry=${entry:.4f} vs live=${live_price:.4f} ({entry_gap*100:.0f}% gap)")
                continue

        # Enforce min/max stop distance
        if sl > 0 and entry > 0:
            stop_dist = abs(entry - sl) / entry
            if stop_dist < MIN_STOP_DISTANCE_PCT:
                if direction in ("LONG", "BUY"):
                    sl = entry * (1 - MIN_STOP_DISTANCE_PCT)
                else:
                    sl = entry * (1 + MIN_STOP_DISTANCE_PCT)
                stop_dist = MIN_STOP_DISTANCE_PCT
            if stop_dist > MAX_STOP_DISTANCE_PCT:
                if direction in ("LONG", "BUY"):
                    sl = entry * (1 - MAX_STOP_DISTANCE_PCT)
                else:
                    sl = entry * (1 + MAX_STOP_DISTANCE_PCT)
                risk = abs(entry - sl)
                if direction in ("LONG", "BUY"):
                    tp = max(tp, entry + risk * 2)
                else:
                    tp = min(tp, entry - risk * 2)

        # Position sizing
        position_size = get_consensus_position_size(pick)

        conformal_mult = 1.0
        if conformal is not None:
            ml_prob = score / 100.0
            conformal_mult = conformal.size_multiplier(ml_prob)
            position_size = round(position_size * conformal_mult, 2)

        am_mult = get_anti_martingale_multiplier(portfolio.get("closed_positions", []))
        if am_mult != 1.0:
            position_size = round(position_size * am_mult, 2)
            print(f"    [ANTI-MARTINGALE] {am_mult:.2f}x multiplier applied (size=${position_size})")

        # SANITY CHECK 4: Position size must not exceed portfolio limits
        max_single = portfolio["current_balance"] * 0.15  # Max 15% per position
        if position_size > max_single:
            print(f"  [SANITY] CAPPING position size for {sym}: ${position_size:.0f} > ${max_single:.0f} (15% limit)")
            position_size = max_single

        consensus_count = int(pick.get("consensus_count", pick.get("copy_trader_count", 1)) or 1)

        portfolio["positions"][pos_key] = {
            "symbol": sym,
            "strategy": strategy,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "score": score,
            "position_size": position_size,
            "leverage": LEVERAGE,
            "opened_at": now.isoformat(),
            "current_pnl_pct": 0,
            "current_pnl_usdt": 0,
            "hwm_price": entry,
            "trailing_stop": 0,
            "high_water_mark_pnl": 0,
            "ml_score_at_entry": score / 100.0 if score > 0 else 0,
            "conformal_multiplier": conformal_mult,
            "consensus_count": consensus_count,
            "ungated": True,  # Flag for identification
        }
        portfolio["stats"]["total_trades"] += 1
        print(f"  NEW POSITION (RAW): {sym} {direction} entry={entry:.6f} tp={tp:.6f} sl={sl:.6f} score={score:.0f} size=${position_size} consensus={consensus_count}")

    # === Calculate unrealized P&L ===
    unrealized_pnl = 0
    open_positions = []
    for pos_id, pos in portfolio["positions"].items():
        unrealized_pnl += pos.get("current_pnl_usdt", 0)
        open_positions.append(pos)

    # === Take snapshot ===
    snapshot = {
        "time": now.isoformat(),
        "balance": portfolio["current_balance"],
        "unrealized_pnl": unrealized_pnl,
        "equity": portfolio["current_balance"] + unrealized_pnl,
        "open_positions": len(portfolio["positions"]),
        "total_trades": portfolio["stats"]["total_trades"],
        "wins": portfolio["stats"]["wins"],
        "losses": portfolio["stats"]["losses"],
    }
    portfolio["snapshots"].append(snapshot)

    if len(portfolio["snapshots"]) > 500:
        portfolio["snapshots"] = portfolio["snapshots"][-500:]

    # SANITY CHECK 5: Balance should never go below 0 or above 3x starting
    starting_balance = portfolio.get("starting_balance", 10000)
    if portfolio["current_balance"] < 0:
        print(f"  [SANITY] NEGATIVE BALANCE detected: ${portfolio['current_balance']:.2f} -- resetting to $0")
        portfolio["current_balance"] = 0
    if portfolio["current_balance"] > starting_balance * 3:
        print(f"  [SANITY] SUSPICIOUS BALANCE: ${portfolio['current_balance']:.2f} > 3x starting -- possible data error")

    save_portfolio(portfolio)

    # === Print Summary ===
    stats = portfolio["stats"]
    total = stats["wins"] + stats["losses"]
    wr = stats["wins"] / total * 100 if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"RAW (UNGATED) COPY TRADER TRACKER -- {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"Balance: ${portfolio['current_balance']:,.2f} (started $10,000)")
    print(f"Unrealized: ${unrealized_pnl:+,.2f}")
    print(f"Equity: ${portfolio['current_balance'] + unrealized_pnl:,.2f}")
    print(f"Open positions: {len(portfolio['positions'])} / {MAX_TOTAL_POSITIONS}")
    print(f"Closed trades: {total} ({stats['wins']}W-{stats['losses']}L = {wr:.0f}% WR)")
    print(f"TP Hits: {stats['tp_hits']} | SL Hits: {stats['sl_hits']} | Trail Stops: {stats['trailing_stops']} | Time Exits: {stats.get('time_exits', 0)}")
    print(f"Total realized P&L: ${stats['total_pnl_usdt']:+,.2f}")
    print(f"Best trade: ${stats['best_trade_pnl']:+,.2f} | Worst: ${stats['worst_trade_pnl']:+,.2f}")

    ct_metrics = stats.get("copytrader_metrics", {})
    print(f"\n{'='*60}")
    print("UNGATED COPY TRADER METRICS:")
    print(f"  Avg hold time: {ct_metrics.get('avg_hold_hours', 0):.1f}h")

    print(f"\n  Win Rate by Hold Duration:")
    for bucket_name in HOLD_DURATION_BUCKETS:
        bucket = ct_metrics.get("hold_duration_buckets", {}).get(bucket_name, {"trades": 0, "wins": 0, "pnl": 0})
        bucket_wr = bucket["wins"] / bucket["trades"] * 100 if bucket["trades"] > 0 else 0
        print(f"    {bucket_name:>6s}: {bucket['trades']:>3d} trades | {bucket['wins']:>3d} wins ({bucket_wr:>5.1f}% WR) | PnL: ${bucket['pnl']:>+8.2f}")

    hour_perf = ct_metrics.get("entry_hour_performance", {})
    if hour_perf:
        print(f"\n  Best Entry Hours (UTC):")
        sorted_hours = sorted(hour_perf.items(), key=lambda x: x[1].get("pnl", 0), reverse=True)
        for hour, hstats in sorted_hours[:5]:
            h_wr = hstats["wins"] / hstats["trades"] * 100 if hstats["trades"] > 0 else 0
            print(f"    {int(hour):02d}:00 UTC: {hstats['trades']:>3d} trades | {h_wr:>5.1f}% WR | PnL: ${hstats['pnl']:>+8.2f}")

    print(f"{'='*60}")
    print(f"\n*** This is the UNGATED tracker. Compare with portfolio_copytrader.json (GATED) ***")
    print(f"*** If this outperforms: gates are blocking good signals ***")
    print(f"*** If gated outperforms: gates add value ***")

    if open_positions:
        print(f"\nOpen Positions:")
        for pos in sorted(open_positions, key=lambda x: x.get("current_pnl_pct", 0)):
            pnl = pos.get("current_pnl_pct", 0)
            pnl_usdt = pos.get("current_pnl_usdt", 0)
            consensus = pos.get("consensus_count", 1)
            print(f"  {pos['symbol']:12s} {pos['direction']:5s} score={pos.get('score',0):>3.0f} size=${pos.get('position_size',0):>3.0f} consensus={consensus} pnl={pnl:>+6.2f}% (${pnl_usdt:>+7.2f})")

    return portfolio


if __name__ == "__main__":
    run_check()
