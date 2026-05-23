#!/usr/bin/env python3
"""
Copy Trader Pattern Portfolio Tracker
Forward-tests strategies derived from PROVEN copy trader patterns (400-1200% ROI).
These are pre-validated by real trader performance.
Data-driven quality filters from 884 closed trade analysis:
MIN_SCORE=80 (65.9% WR), short filter (13.8% WR), bad hours 08-13 UTC blocked,
RSI>70 LONG blocked (7.9% WR), volume spike >5x blocked (11% WR).

Strict exits mimic copy trader discipline: 8h optimal hold, 24h hard max,
early trailing stop activation at +1.5%.

Run every 30 min alongside other trackers for comparative data.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

# Allow imports from alpha_engine directory when run standalone
sys.path.insert(0, os.path.dirname(__file__))
try:
    from conformal_sizing import ConformalSizer
except ImportError:
    ConformalSizer = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_copytrader.json")
ACTIVE_PICKS_FILE = os.path.join(DATA_DIR, "active_picks.json")
COPY_TRADER_PICKS_FILE = os.path.join(os.path.dirname(__file__), "..", "copy_trader_intel", "data", "active_picks.json")

LEVERAGE = 5  # 5x leverage — moderate risk, matches successful copy traders
BASE_POSITION_SIZE = 500  # $500 base per position (5% of $10K portfolio)
MIN_SCORE = 80  # Data-driven: scores below 80 have ~33% WR regardless. Only 80+ has 65.9% WR.
MAX_TOTAL_POSITIONS = 10
MAX_PER_CORRELATION_GROUP = 3

# Copy trader-specific position sizing by consensus count
CONSENSUS_SIZE_1 = 500   # 1 trader pattern match = $500 (5% of portfolio)
CONSENSUS_SIZE_2 = 750   # 2 trader pattern matches = $750 (7.5%)
CONSENSUS_SIZE_3_PLUS = 1000  # 3+ trader pattern matches = $1000 (10%)

# Strict copy trader exits (mimicking their discipline)
MIN_HOLD_HOURS = 4       # Data-driven: exits before 1h have 13.3% WR. Hold at least 4h.
# Extended holds: directional edge peaks at 3-7 days per research
# But copy traders typically hold shorter -- compromise at 2-3 days
OPTIMAL_HOLD_HOURS = 24  # 1 day -- lock profits (was 8h, too aggressive)
MAX_HOLD_HOURS = 72      # 3 days -- capture directional edge (was 24h)

# Trailing stop parameters (tighter than 1x -- scalper-style)
TRAILING_STOP_ACTIVATION = 0.015  # Activate at +1.5% (lock profits early)
TRAILING_STOP_DISTANCE = 0.008    # Trail by 0.8%
MAX_STOP_DISTANCE_PCT = 0.03      # 3% max stop distance
MIN_STOP_DISTANCE_PCT = 0.01      # 1% minimum stop distance

# R:R backtest result (2026-03-21, 545 closed picks):
# Current 2:1 R:R is optimal. Wider ratios destroy WR faster than they grow avg win.
# Copy trader patterns confirm: tight TP + high WR > wide TP + low WR.
TP_WIDEN_FACTOR = 1.0  # Multiply original TP distance by this (1.0 = no change)

# SL grace period (shakeout protection)
SL_GRACE_PERIOD_HOURS = 2        # Shorter grace for faster-paced strategies
SL_WIDEN_PERIOD_HOURS = 1
SL_WIDEN_FACTOR = 1.3

# Consecutive loss cooldown
CONSECUTIVE_LOSS_PAUSE_HOURS = 1
CONSECUTIVE_LOSS_PAUSE_COUNT = 3  # More lenient -- 3 losses before pause

# Anti-Martingale position sizing
USE_ANTI_MARTINGALE = True
ANTI_MARTINGALE_WIN_BOOST = 1.20
ANTI_MARTINGALE_LOSS_SHRINK = 0.80
ANTI_MARTINGALE_MAX_MULT = 1.8
ANTI_MARTINGALE_MIN_MULT = 0.5
ANTI_MARTINGALE_RESET_AFTER = 5

# Accepted strategies -- only copy trader pattern strategies
ACCEPTED_STRATEGIES = {
    "donchian_breakout_scalp",
    "funding_rate_scalp",
    "funding_rate_carry",
    "keltner_compression_btc",
    "keltner_compression_sol",
    "dynamic_gainer_momentum",
}
# Also accept any strategy with these keywords in the name
STRATEGY_KEYWORDS = ["scalp", "breakout", "copy_trader", "copy_hl", "copy_okx", "okx_copy", "copy_bybit", "bybit_copy", "copy_bitget", "copy_bingx", "copy_gate", "copy_dex", "consensus", "reverse_engineered_", "copy_"]

# Correlation groups
CORRELATION_GROUPS = {
    "large_cap": ["BTC-USD", "BTCUSDT", "ETH-USD", "ETHUSDT"],
    "alt_l1": ["SOL-USD", "SOLUSDT", "AVAX-USD", "AVAXUSDT", "NEAR-USD", "NEARUSDT", "DOT-USD", "DOTUSDT"],
    "defi": ["LINK-USD", "LINKUSDT", "UNI-USD", "UNIUSDT", "AAVE-USD", "AAVEUSDT"],
    "meme": ["DOGE-USD", "DOGEUSDT", "SHIB-USD", "SHIBUSDT"],
    "exchange": ["BNB-USD", "BNBUSDT"],
    "infra": ["RENDER-USD", "RENDERUSDT", "FIL-USD", "FILUSDT", "FET-USD", "FETUSDT"],
}

# Hold duration buckets for metrics tracking
HOLD_DURATION_BUCKETS = ["0-4h", "4-12h", "12-24h", "24h+"]


def fetch_prices():
    """Fetch live prices with 3-API fallback chain."""
    apis = [
        ("https://api.binance.com/api/v3/ticker/price", "binance"),
        ("https://api1.binance.com/api/v3/ticker/price", "binance_mirror"),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,bnb,fetch-ai,render-token,tia-token,atom,ondo,cake,zec,fartcoin,axie-infinity,tao-network,the-open-network,sui,aave,pump-fun&vs_currencies=usd", "coingecko"),
    ]

    for url, source in apis:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())

            if source.startswith("binance"):
                prices = {t["symbol"]: float(t["price"]) for t in data}
                # Backfill missing tokens from Hyperliquid
                try:
                    hl_req = urllib.request.Request("https://api.hyperliquid.xyz/info",
                        data=json.dumps({"type": "allMids"}).encode(),
                        headers={"Content-Type": "application/json"}, method="POST")
                    hl_resp = urllib.request.urlopen(hl_req, timeout=5)
                    hl_mids = json.loads(hl_resp.read())
                    for coin, mid in hl_mids.items():
                        sym = coin + "USDT"
                        if sym not in prices and float(mid) > 0:
                            prices[sym] = float(mid)
                except Exception:
                    pass
                return prices
            elif source == "coingecko":
                mapping = {
                    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                    "dogecoin": "DOGEUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
                    "avalanche-2": "AVAXUSDT", "chainlink": "LINKUSDT", "polkadot": "DOTUSDT",
                    "near": "NEARUSDT", "shiba-inu": "SHIBUSDT", "filecoin": "FILUSDT",
                    "bnb": "BNBUSDT", "fetch-ai": "FETUSDT", "render-token": "RENDERUSDT",
                    "atom": "ATOMUSDT", "cake": "CAKEUSDT",
                    "fartcoin": "FARTCOINUSDT", "axie-infinity": "AXSUSDT",
                    "tao-network": "TAOUSDT", "the-open-network": "TONUSDT",
                    "sui": "SUIUSDT", "aave": "AAVEUSDT", "pump-fun": "PUMPUSDT",
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


def is_accepted_strategy(strategy):
    """Check if a strategy is in the accepted copy trader pattern list."""
    if not strategy:
        return False
    strategy_lower = strategy.lower()
    if strategy_lower in ACCEPTED_STRATEGIES:
        return True
    for keyword in STRATEGY_KEYWORDS:
        if keyword in strategy_lower:
            return True
    return False


def get_hold_duration_bucket(hours):
    """Return the hold duration bucket label for a given number of hours."""
    if hours < 4:
        return "0-4h"
    elif hours < 12:
        return "4-12h"
    elif hours < 24:
        return "12-24h"
    else:
        return "24h+"


def get_consensus_position_size(pick):
    """Position size scaled by copy trader consensus count."""
    consensus = int(pick.get("consensus_count", pick.get("copy_trader_count", 1)) or 1)
    if consensus >= 3:
        return CONSENSUS_SIZE_3_PLUS
    elif consensus >= 2:
        return CONSENSUS_SIZE_2
    else:
        return CONSENSUS_SIZE_1


def load_portfolio():
    """Load existing portfolio state."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            portfolio = json.load(f)
        # Ensure all required stats keys exist
        _defaults = {
            "tp_hits": 0, "sl_hits": 0, "trailing_stops": 0,
            "best_trade_pnl": 0, "worst_trade_pnl": 0,
            "total_pnl_usdt": 0, "wins": 0, "losses": 0, "total_trades": 0,
            "time_exits": 0,
        }
        for k, v in _defaults.items():
            portfolio.setdefault("stats", {}).setdefault(k, v)
        # Ensure copy trader metrics exist
        portfolio["stats"].setdefault("copytrader_metrics", _default_copytrader_metrics())
        return portfolio
    return _new_portfolio()


def _default_copytrader_metrics():
    """Default copy trader-specific metrics structure."""
    return {
        "avg_hold_hours": 0,
        "total_hold_hours": 0,
        "hold_duration_buckets": {
            "0-4h": {"trades": 0, "wins": 0, "pnl": 0},
            "4-12h": {"trades": 0, "wins": 0, "pnl": 0},
            "12-24h": {"trades": 0, "wins": 0, "pnl": 0},
            "24h+": {"trades": 0, "wins": 0, "pnl": 0},
        },
        "entry_hour_performance": {},  # hour (0-23) -> {trades, wins, pnl}
    }


def _new_portfolio():
    """Create a fresh portfolio."""
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "starting_balance": 10000,
        "current_balance": 10000,
        "leverage": LEVERAGE,
        "tracker_type": "copytrader_forward_test",
        "description": "Forward-tests PROVEN copy trader pattern strategies (400-1200% ROI). Looser entry gates, strict scalper-style exits.",
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
    """Save portfolio state."""
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, default=str)


def normalize_symbol(sym):
    """Normalize symbol to Binance format."""
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


def update_copytrader_metrics(portfolio, pos):
    """Update copy trader-specific metrics when closing a position."""
    metrics = portfolio["stats"].setdefault("copytrader_metrics", _default_copytrader_metrics())

    hours_held = pos.get("hours_held", 0)
    pnl_usdt = pos.get("pnl_usdt", 0)
    is_win = pnl_usdt > 0

    # Update average hold time
    total_closed = portfolio["stats"]["wins"] + portfolio["stats"]["losses"]
    if total_closed > 0:
        metrics["total_hold_hours"] = metrics.get("total_hold_hours", 0) + hours_held
        metrics["avg_hold_hours"] = round(metrics["total_hold_hours"] / total_closed, 2)

    # Update hold duration bucket stats
    bucket = get_hold_duration_bucket(hours_held)
    bucket_stats = metrics.setdefault("hold_duration_buckets", {}).setdefault(
        bucket, {"trades": 0, "wins": 0, "pnl": 0}
    )
    bucket_stats["trades"] += 1
    if is_win:
        bucket_stats["wins"] += 1
    bucket_stats["pnl"] = round(bucket_stats["pnl"] + pnl_usdt, 2)

    # Update entry hour performance
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
    """Main portfolio check -- call every 30 min."""
    portfolio = load_portfolio()
    prices = fetch_prices()

    conformal = ConformalSizer(coverage=0.90) if ConformalSizer else None

    if not prices:
        print("[COPYTRADER TRACKER] Failed to fetch prices from all APIs")
        return portfolio

    # Ensure copytrader_metrics exists (backwards compat)
    if "copytrader_metrics" not in portfolio["stats"]:
        portfolio["stats"]["copytrader_metrics"] = _default_copytrader_metrics()
    if "trailing_stops" not in portfolio["stats"]:
        portfolio["stats"]["trailing_stops"] = 0
    if "time_exits" not in portfolio["stats"]:
        portfolio["stats"]["time_exits"] = 0

    now = datetime.now(timezone.utc)

    # Load active picks from both alpha engine and copy trader intel
    active_picks = []
    for picks_file in [ACTIVE_PICKS_FILE, COPY_TRADER_PICKS_FILE]:
        try:
            with open(picks_file, "r", encoding="utf-8") as f:
                file_picks = json.load(f)
                if isinstance(file_picks, list):
                    active_picks.extend(file_picks)
        except Exception:
            pass

    # === Check existing positions for TP/SL ===
    positions_to_close = []
    for pos_id, pos in list(portfolio.get("positions", {}).items()):
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

        # Calculate spot PnL (1x -- no leverage)
        if direction in ("LONG", "BUY"):
            pnl_pct = (current - entry) / entry
        else:
            pnl_pct = (entry - current) / entry

        pos_size = pos.get("position_size", BASE_POSITION_SIZE)
        pnl_usdt = pos_size * pnl_pct

        # SANITY CHECK 3: PnL must be within reasonable bounds
        max_pnl_pct = 2.50  # 250% max for 5x leverage (50% spot * 5)
        if abs(pnl_pct) > max_pnl_pct:
            print(f"  [SANITY] CAPPING PnL for {pos['symbol']}: {pnl_pct*100:.1f}% exceeds max {max_pnl_pct*100:.0f}%")
            pnl_pct = max_pnl_pct if pnl_pct > 0 else -max_pnl_pct
            pnl_usdt = pos_size * pnl_pct

        # Calculate hours open
        try:
            opened_at = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
            hours_open = (now - opened_at).total_seconds() / 3600
        except Exception:
            hours_open = 999

        # DATA-DRIVEN: Minimum hold time guard (exits < 4h have poor WR)
        # SL hits still allowed through (capital protection), but TP/trailing/time exits delayed
        min_hold_met = hours_open >= MIN_HOLD_HOURS

        # Check TP hit (only if minimum hold time met, with optional R:R widen)
        tp = pos.get("take_profit", 0)
        if tp > 0 and TP_WIDEN_FACTOR != 1.0 and entry > 0:
            original_tp_dist = abs(tp - entry)
            widened_dist = original_tp_dist * TP_WIDEN_FACTOR
            if direction in ("LONG", "BUY"):
                tp = entry + widened_dist
            else:
                tp = entry - widened_dist
        if tp > 0 and min_hold_met:
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

        # Check SL hit (with grace period for shakeout protection)
        sl = pos.get("stop_loss", 0)
        if sl > 0:
            # SL grace period -- shortened for copy trader speed
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
                    sl = 0  # Temporarily disable normal SL check

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

        # === Trailing Stop Logic (tighter -- scalper-style) ===
        if direction in ("LONG", "BUY"):
            if "hwm_price" not in pos or current > pos.get("hwm_price", 0):
                pos["hwm_price"] = current
        else:
            if "hwm_price" not in pos or current < pos.get("hwm_price", float("inf")):
                pos["hwm_price"] = current

        # Activate trailing stop at +1.5% (early profit locking)
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

        # Check trailing stop hit (only if minimum hold time met)
        trail = pos.get("trailing_stop", 0)
        if trail > 0 and min_hold_met:
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

        # === Time-Based Exit Logic (strict copy trader discipline) ===
        time_exit = False
        time_exit_reason = ""

        # Rule 1: If profitable after 8h optimal hold, close to lock in gains (min hold already met)
        if hours_open > OPTIMAL_HOLD_HOURS and pnl_pct > 0:
            time_exit = True
            time_exit_reason = "TIME_EXIT_PROFIT"
            print(f"  TIME EXIT (PROFIT): {pos['symbol']} {direction} open {hours_open:.1f}h > {OPTIMAL_HOLD_HOURS}h, pnl={pnl_pct*100:+.2f}% -- locking profits")

        # Rule 2: Hard 24h max -- close regardless (no multi-day holds)
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

        # Update copy trader-specific metrics
        update_copytrader_metrics(portfolio, pos)

        # Update conformal prediction calibration
        if conformal is not None:
            ml_at_entry = pos.get("ml_score_at_entry", pos.get("score", 50) / 100.0)
            win = 1.0 if pos["pnl_usdt"] > 0 else 0.0
            conformal.update(ml_at_entry, win)

    # === Add new positions from active picks ===
    # Count positions per correlation group
    group_counts = {}
    for pos in portfolio["positions"].values():
        psym = pos.get("symbol", "")
        for grp, syms in CORRELATION_GROUPS.items():
            if psym in syms:
                group_counts[grp] = group_counts.get(grp, 0) + 1

    # === Consecutive loss cooldown ===
    recent_closed = portfolio.get("closed_positions", [])
    consecutive_losses = 0
    for cp in reversed(recent_closed[-10:]):
        if (cp.get("pnl_pct", 0) or cp.get("pnl_usdt", 0) or 0) < 0:
            consecutive_losses += 1
        else:
            break

    cooldown_active = False
    if consecutive_losses >= CONSECUTIVE_LOSS_PAUSE_COUNT and recent_closed:
        last_loss_time_str = recent_closed[-1].get("close_time", "")
        try:
            last_loss_time = datetime.fromisoformat(last_loss_time_str)
            hours_since_last_loss = (now - last_loss_time).total_seconds() / 3600
            if hours_since_last_loss < CONSECUTIVE_LOSS_PAUSE_HOURS:
                cooldown_active = True
                print(f"  [COOLDOWN] {consecutive_losses} consecutive losses -- pausing new entries for {CONSECUTIVE_LOSS_PAUSE_HOURS - hours_since_last_loss:.1f}h more")
        except Exception:
            pass

    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        status_value = str(pick.get("status", "") or "").strip().upper()
        open_like_statuses = {"", "OPEN", "ACTIVE", "PENDING", "LIVE", "RUNNING"}
        if status_value not in open_like_statuses:
            continue

        # Cooldown after consecutive losses
        if cooldown_active:
            print(f"  [COOLDOWN] Skipping all new entries -- loss cooldown active")
            break

        # Max total positions cap
        if len(portfolio["positions"]) >= MAX_TOTAL_POSITIONS:
            break

        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        score = float(pick.get("elite_score", pick.get("score", pick.get("confidence", 0))) or 0)

        # === STRATEGY FILTER: Only accept copy trader pattern strategies ===
        if not is_accepted_strategy(strategy):
            continue

        # Quality filter: score >= 80 (data-driven: below 80 = ~33% WR)
        if score < MIN_SCORE:
            continue

        # DATA-DRIVEN FILTER: Short direction — shorts have 13.8% WR, -9.19% avg PnL
        direction_raw = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
        if direction_raw in ("SHORT", "SELL") and score < 90:
            print(f"  [QUALITY] Skipping {sym} SHORT: score {score:.0f} < 90 (shorts need exceptional scores, 13.8% WR overall)")
            continue

        # DATA-DRIVEN FILTER: Bad hours — 08:00-13:00 UTC has 9-19% WR
        current_hour = now.hour
        BAD_HOURS = {8, 9, 10, 11, 12, 13}
        GOOD_HOURS = {23, 7}  # 60-74% WR
        if current_hour in BAD_HOURS:
            print(f"  [QUALITY] Skipping {sym}: current hour {current_hour:02d}:00 UTC is in bad hours (9-19% WR)")
            continue

        # DATA-DRIVEN FILTER: RSI > 70 for LONG entries — 7.9% WR
        enrichment = pick.get("enrichment", {})
        rsi_data = enrichment.get("rsi", {})
        rsi = rsi_data.get("rsi_14_1h", None)
        if rsi is not None and direction_raw in ("LONG", "BUY") and rsi > 70:
            print(f"  [QUALITY] Skipping {sym} LONG: RSI {rsi:.1f} > 70 (7.9% WR for overbought entries)")
            continue

        # DATA-DRIVEN FILTER: Volume spike > 5x — extreme spikes predict losses (11% WR)
        vol_ratio = enrichment.get("volume_ratio", enrichment.get("vol_ratio", None))
        if vol_ratio is not None and float(vol_ratio) > 5.0:
            print(f"  [QUALITY] Skipping {sym}: volume spike {float(vol_ratio):.1f}x > 5x (11% WR for extreme spikes)")
            continue

        # Pump guard — block pumped tokens
        try:
            from alpha_engine.pump_guard import calculate_pump_risk
            pump_risk = calculate_pump_risk(sym, 0, 1.0)  # basic check
            if pump_risk > 0.7:
                print(f"  [PUMP GUARD] Blocking {sym} — pump risk {pump_risk:.2f}")
                continue
            elif pump_risk > 0.5:
                print(f"  [PUMP GUARD] Warning on {sym} — pump risk {pump_risk:.2f}, reducing size")
                _pump_size_penalty = 0.5  # applied later at position sizing
            else:
                _pump_size_penalty = 1.0
        except Exception:
            _pump_size_penalty = 1.0

        # Strategy-pair affinity check
        try:
            from alpha_engine.strategy_pair_affinity import get_affinity
            affinity = get_affinity(strategy, sym)
            if affinity is not None and affinity < 0.2:
                print(f"  [AFFINITY] Skipping {sym} — affinity {affinity:.2f} too low for {strategy}")
                continue
            if affinity and affinity > 0.7:
                print(f"  [AFFINITY] HIGH affinity {affinity:.2f} for {sym} + {strategy}")
        except Exception:
            pass

        # Boost logging for good hours
        if current_hour in GOOD_HOURS:
            print(f"  [QUALITY] Good entry hour {current_hour:02d}:00 UTC (60-74% WR) for {sym}")

        # Correlation group limit: max 3 per group
        skip_corr = False
        for grp, syms in CORRELATION_GROUPS.items():
            if sym in syms and group_counts.get(grp, 0) >= MAX_PER_CORRELATION_GROUP:
                skip_corr = True
                break
        if skip_corr:
            continue

        # Skip if already in portfolio (same symbol + strategy)
        pos_key = f"{sym}_{strategy}"
        if pos_key in portfolio["positions"]:
            continue

        # Consecutive loss guard per symbol
        sym_losses = 0
        for cp in reversed(recent_closed[-10:]):
            cp_sym = cp.get("symbol", "")
            if cp_sym == sym or normalize_symbol(cp_sym) == normalize_symbol(sym):
                if (cp.get("pnl_pct", 0) or 0) < 0:
                    sym_losses += 1
                else:
                    break
        if sym_losses >= 3:
            print(f"  [LOSS GUARD] Skipping {sym}: {sym_losses} consecutive losses -- cooling off")
            continue

        # Only 1 position per normalized symbol
        norm_base = normalize_symbol(sym)
        existing_syms = {normalize_symbol(p["symbol"]) for p in portfolio["positions"].values()}
        if norm_base in existing_syms:
            continue

        entry = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()

        # Copy traders trade both long and short -- allow both directions
        LONG_ONLY_MODE = False
        if LONG_ONLY_MODE and direction in ("SHORT", "SELL"):
            continue

        # Stale entry guard
        for cp in reversed(portfolio.get("closed_positions", [])[-5:]):
            cp_sym = cp.get("symbol", "")
            cp_entry = cp.get("entry_price", 0) or 0
            cp_pnl = cp.get("pnl_pct", 0) or 0
            if (normalize_symbol(cp_sym) == normalize_symbol(sym)
                    and abs(cp_entry - entry) < entry * 0.001
                    and cp_pnl < 0):
                print(f"  [STALE GUARD] Skipping {sym}: same entry ${entry:.2f} as last SL hit -- pick not refreshed")
                entry = 0
                break

        if entry <= 0:
            continue

        # Verify current price is close to entry
        norm_sym = normalize_symbol(sym)
        current = prices.get(norm_sym, 0)
        if current > 0:
            gap = abs(current - entry) / entry
            if gap > 0.05:
                continue
            # Enter at current market price
            entry = current

        # SANITY CHECK 2: Entry price must be within 10% of live market price
        live_price = prices.get(norm_sym, 0)
        if live_price > 0 and entry > 0:
            entry_gap = abs(entry - live_price) / live_price
            if entry_gap > 0.10:  # >10% stale
                print(f"  [SANITY] STALE entry for {sym}: entry=${entry:.4f} vs live=${live_price:.4f} ({entry_gap*100:.0f}% gap)")
                continue

        # Enforce min/max stop distance (3% max for copy trader)
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
                # Maintain at least 2:1 R:R
                risk = abs(entry - sl)
                if direction in ("LONG", "BUY"):
                    tp = max(tp, entry + risk * 2)
                else:
                    tp = min(tp, entry - risk * 2)

        # Copy trader consensus-based position sizing
        position_size = get_consensus_position_size(pick)

        # Apply conformal prediction sizing multiplier
        conformal_mult = 1.0
        if conformal is not None:
            ml_prob = score / 100.0
            conformal_mult = conformal.size_multiplier(ml_prob)
            position_size = round(position_size * conformal_mult, 2)

        # Apply pump guard size penalty
        if _pump_size_penalty < 1.0:
            position_size = round(position_size * _pump_size_penalty, 2)
            print(f"    [PUMP GUARD] Reduced size to ${position_size} (penalty {_pump_size_penalty:.2f}x)")

        # Dynamic sizing from price regression ML
        try:
            from alpha_engine.price_regression import predict_pnl
            prediction = predict_pnl(pick)
            if prediction:
                pred_mult = prediction.get('position_size_multiplier', 1.0)
                position_size = round(position_size * pred_mult, 2)
                # Also use recommended TP/SL if available
                rec_tp = prediction.get('recommended_tp_pct')
                rec_sl = prediction.get('recommended_sl_pct')
                if rec_tp and rec_tp > 0:
                    if direction in ("LONG", "BUY"):
                        tp = round(entry * (1 + rec_tp/100), 8)
                    else:
                        tp = round(entry * (1 - rec_tp/100), 8)
                if rec_sl and rec_sl > 0:
                    if direction in ("LONG", "BUY"):
                        sl = round(entry * (1 - rec_sl/100), 8)
                    else:
                        sl = round(entry * (1 + rec_sl/100), 8)
                print(f"    [ML-SIZING] pred_pnl={prediction.get('predicted_pnl_pct',0):+.2f}% mult={pred_mult:.2f}x tp={rec_tp}% sl={rec_sl}%")
        except Exception:
            pass  # Non-fatal

        # Apply anti-martingale sizing
        am_mult = get_anti_martingale_multiplier(portfolio.get("closed_positions", []))
        if am_mult != 1.0:
            position_size = round(position_size * am_mult, 2)
            print(f"    [ANTI-MARTINGALE] {am_mult:.2f}x multiplier applied (size=${position_size})")

        # SANITY CHECK 4: Position size must not exceed portfolio limits
        max_single = portfolio["current_balance"] * 0.15  # Max 15% per position
        if position_size > max_single:
            print(f"  [SANITY] CAPPING position size for {sym}: ${position_size:.0f} > ${max_single:.0f} (15% limit)")
            position_size = max_single

        # Update correlation group count
        for grp, syms in CORRELATION_GROUPS.items():
            if sym in syms:
                group_counts[grp] = group_counts.get(grp, 0) + 1

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
            "ml_score_at_entry": score / 100.0,
            "conformal_multiplier": conformal_mult,
            "consensus_count": consensus_count,
        }
        portfolio["stats"]["total_trades"] += 1
        print(f"  NEW POSITION: {sym} {direction} entry={entry:.6f} tp={tp:.6f} sl={sl:.6f} score={score:.0f} size=${position_size} consensus={consensus_count}")

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

    # Keep last 500 snapshots
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
    print(f"COPY TRADER PORTFOLIO TRACKER -- {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"Balance: ${portfolio['current_balance']:,.2f} (started $10,000)")
    print(f"Unrealized: ${unrealized_pnl:+,.2f}")
    print(f"Equity: ${portfolio['current_balance'] + unrealized_pnl:,.2f}")
    print(f"Open positions: {len(portfolio['positions'])} / {MAX_TOTAL_POSITIONS}")
    print(f"Closed trades: {total} ({stats['wins']}W-{stats['losses']}L = {wr:.0f}% WR)")
    print(f"TP Hits: {stats['tp_hits']} | SL Hits: {stats['sl_hits']} | Trail Stops: {stats['trailing_stops']} | Time Exits: {stats.get('time_exits', 0)}")
    print(f"Total realized P&L: ${stats['total_pnl_usdt']:+,.2f}")
    print(f"Best trade: ${stats['best_trade_pnl']:+,.2f} | Worst: ${stats['worst_trade_pnl']:+,.2f}")

    # Copy trader metrics breakdown
    ct_metrics = stats.get("copytrader_metrics", {})
    print(f"\n{'='*60}")
    print("COPY TRADER METRICS:")
    print(f"  Avg hold time: {ct_metrics.get('avg_hold_hours', 0):.1f}h")

    print(f"\n  Win Rate by Hold Duration:")
    for bucket_name in HOLD_DURATION_BUCKETS:
        bucket = ct_metrics.get("hold_duration_buckets", {}).get(bucket_name, {"trades": 0, "wins": 0, "pnl": 0})
        bucket_wr = bucket["wins"] / bucket["trades"] * 100 if bucket["trades"] > 0 else 0
        print(f"    {bucket_name:>6s}: {bucket['trades']:>3d} trades | {bucket['wins']:>3d} wins ({bucket_wr:>5.1f}% WR) | PnL: ${bucket['pnl']:>+8.2f}")

    # Best entry hours
    hour_perf = ct_metrics.get("entry_hour_performance", {})
    if hour_perf:
        print(f"\n  Best Entry Hours (UTC):")
        sorted_hours = sorted(hour_perf.items(), key=lambda x: x[1].get("pnl", 0), reverse=True)
        for hour, hstats in sorted_hours[:5]:
            h_wr = hstats["wins"] / hstats["trades"] * 100 if hstats["trades"] > 0 else 0
            print(f"    {int(hour):02d}:00 UTC: {hstats['trades']:>3d} trades | {h_wr:>5.1f}% WR | PnL: ${hstats['pnl']:>+8.2f}")

    print(f"{'='*60}")

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
