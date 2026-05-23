#!/usr/bin/env python3
"""
1x (No Leverage) Portfolio Tracker
Forward-tests ALL quality picks (score >= 50) at spot to validate scoring accuracy.
Tracks whether score correlates with actual P&L without leverage distortion.

Run every 30 min alongside the 20x tracker to build comparative data.
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
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_1x.json")
ACTIVE_PICKS_FILE = os.path.join(DATA_DIR, "active_picks.json")

LEVERAGE = 1
BASE_POSITION_SIZE = 200  # $200 per position, $10K portfolio
MIN_SCORE_1X = 50  # Grade C+ -- raised from 50 after 0/9 WR disaster
MAX_TOTAL_POSITIONS = 10  # Raised: ML retrained, SHORT bug fixed, gainer tracker active -- need more data
MAX_PER_CORRELATION_GROUP = 2  # Raised from 1: allow 2 per group for diversified testing

# EMERGENCY FIXES (2026-03-18): 0 wins / 9 losses -- all SL hits
# Root causes: (1) re-entry loops on losing symbols, (2) no cooldown after losses,
# (3) no SL grace period (shakeout protection), (4) entering at market price during downtrend
SL_GRACE_PERIOD_HOURS = 4        # Don't close on SL within first 4 hours (shakeout protection)
SL_WIDEN_PERIOD_HOURS = 2        # Widen SL by 50% for first 2 hours (breathing room)
SL_WIDEN_FACTOR = 1.5            # SL distance multiplied by this during grace period
LIMIT_ORDER_DIP_PCT = 0.001      # Enter 0.1% below current (was 0.5% -- too strict, missed rising entries)
CONSECUTIVE_LOSS_PAUSE_HOURS = 1 # After 2 consecutive losses, pause for 1 hour
CONSECUTIVE_LOSS_PAUSE_COUNT = 2 # Number of consecutive losses before pausing

# Time-based exit parameters (mimicking top Bybit/Bitget copy traders' 4-12h hold patterns)
# Hold times extended based on XGBoost directional accuracy research:
# 1D: 50.8% (coin flip) → 3D: 55.3% (+5.3% edge) → 7D: 56.4% (+6.4% edge)
# Longer holds capture more of the predictive edge.
# Source: yingjeanne.pythonanywhere.com/results (5-year BTC backtest)
OPTIMAL_HOLD_HOURS = 72          # 3 days — where directional edge starts (55.3%)
MAX_HOLD_HOURS_CRYPTO = 168      # 7 days — peak directional accuracy (56.4%)
MAX_HOLD_HOURS_FOREX = 48        # 48h — forex moves 0.3-0.8%/day; if TP not hit by then, edge is gone

# Trailing stop parameters (spot-appropriate)
TRAILING_STOP_ACTIVATION = 0.02  # Activate at +2% spot
TRAILING_STOP_DISTANCE = 0.015   # Trail by 1.5%
MAX_STOP_DISTANCE_PCT = 0.05     # 5% max stop -- wider for 1x
MIN_STOP_DISTANCE_PCT = 0.02     # 2% minimum stop -- crypto noise is 1-2%/hour

# R:R backtest result (2026-03-21, 545 closed picks):
# Current 2:1 R:R is optimal (PF=1.45, +0.34% expectancy, +532% total PnL).
# Wider ratios (3:1, 3.5:1, 4:1 Qwen3-style) destroy WR faster than they grow avg win.
# MFE data shows most winners barely reach current TP — widening causes net losses.
# Factor of 1.0 = keep TP as-is. Increase only if MFE distribution shifts.
TP_WIDEN_FACTOR = 1.0  # Multiply original TP distance by this (1.0 = no change, 1.5 = widen 50%)

# Anti-Martingale position sizing (Category O18, +15-25% CAGR improvement)
# Scale UP after wins, DOWN after losses (opposite of Martingale).
# After a win streak, the edge is likely real -- press it.
# After a loss streak, protect capital until edge returns.
USE_ANTI_MARTINGALE = True
ANTI_MARTINGALE_WIN_BOOST = 1.25   # +25% size after each consecutive win (compounds)
ANTI_MARTINGALE_LOSS_SHRINK = 0.75  # -25% size after each consecutive loss
ANTI_MARTINGALE_MAX_MULT = 2.0     # Cap at 2x base size (no reckless scaling)
ANTI_MARTINGALE_MIN_MULT = 0.5     # Floor at 0.5x base size (always trade something)
ANTI_MARTINGALE_RESET_AFTER = 5    # Reset multiplier after 5 consecutive same-direction

# Score-tiered position sizing
# Purpose: test whether higher scores justify larger allocations
SCORE_TIERS = [
    (80, 200),  # Score >= 80 → $200
    (70, 150),  # Score >= 70 → $150
    (60, 100),  # Score >= 60 → $100
    (50, 75),   # Score >= 50 → $75
]

# Correlation groups -- max 3 per group at 1x
CORRELATION_GROUPS = {
    "large_cap": ["BTC-USD", "BTCUSDT", "ETH-USD", "ETHUSDT"],
    "alt_l1": ["SOL-USD", "SOLUSDT", "AVAX-USD", "AVAXUSDT", "NEAR-USD", "NEARUSDT", "DOT-USD", "DOTUSDT"],
    "defi": ["LINK-USD", "LINKUSDT", "UNI-USD", "UNIUSDT", "AAVE-USD", "AAVEUSDT"],
    "meme": ["DOGE-USD", "DOGEUSDT", "SHIB-USD", "SHIBUSDT"],
    "exchange": ["BNB-USD", "BNBUSDT"],
    "infra": ["RENDER-USD", "RENDERUSDT", "FIL-USD", "FILUSDT", "FET-USD", "FETUSDT"],
}


def fetch_btc_4h_regime():
    """Fetch BTC price change over last 4 hours to determine market regime.

    Uses Binance klines with api1/api2/api3 failover chain.
    Returns tuple: (regime_str, btc_change_pct)
      - "bearish" if BTC 4h change < -1%
      - "bullish" if BTC 4h change > +1%
      - "neutral" otherwise
    """
    binance_urls = [
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api.binance.com",
        "https://data-api.binance.vision",
    ]
    for base in binance_urls:
        try:
            url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=5"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            klines = json.loads(resp.read())
            if klines and len(klines) >= 4:
                open_4h_ago = float(klines[0][1])
                close_now = float(klines[-1][4])
                if open_4h_ago > 0:
                    change_pct = (close_now - open_4h_ago) / open_4h_ago * 100
                    if change_pct < -1.0:
                        regime = "bearish"
                    elif change_pct > 1.0:
                        regime = "bullish"
                    else:
                        regime = "neutral"
                    return regime, round(change_pct, 2)
        except Exception:
            continue

    # Fallback: CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        change_24h = data.get("bitcoin", {}).get("usd_24h_change", 0)
        approx_4h = change_24h / 6.0
        if approx_4h < -1.0:
            return "bearish", round(approx_4h, 2)
        elif approx_4h > 1.0:
            return "bullish", round(approx_4h, 2)
        return "neutral", round(approx_4h, 2)
    except Exception:
        pass

    return "neutral", 0.0


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
    """Anti-Martingale: scale up after wins, down after losses.

    Counts consecutive wins/losses from the most recent closed trades.
    Returns a multiplier (0.5x to 2.0x) for position sizing.
    """
    if not USE_ANTI_MARTINGALE or not closed_positions:
        return 1.0

    # Count consecutive wins or losses from most recent
    streak = 0
    streak_type = None  # 'win' or 'loss'

    for pos in reversed(closed_positions[-20:]):  # check last 20
        pnl = pos.get("pnl_pct", pos.get("pnl_usdt", 0)) or 0
        is_win = pnl > 0

        if streak_type is None:
            streak_type = "win" if is_win else "loss"
            streak = 1
        elif (streak_type == "win" and is_win) or (streak_type == "loss" and not is_win):
            streak += 1
            if streak >= ANTI_MARTINGALE_RESET_AFTER:
                break  # cap streak count
        else:
            break  # streak broken

    if streak_type == "win":
        mult = ANTI_MARTINGALE_WIN_BOOST ** streak
    elif streak_type == "loss":
        mult = ANTI_MARTINGALE_LOSS_SHRINK ** streak
    else:
        mult = 1.0

    # Clamp to bounds
    mult = max(ANTI_MARTINGALE_MIN_MULT, min(ANTI_MARTINGALE_MAX_MULT, mult))
    return round(mult, 2)


def load_portfolio():
    """Load existing portfolio state."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            portfolio = json.load(f)
        # Ensure all required stats keys exist (handles v2.0 reset format)
        _defaults = {"tp_hits": 0, "sl_hits": 0, "trailing_stops": 0,
                     "best_trade_pnl": 0, "worst_trade_pnl": 0,
                     "total_pnl_usdt": 0, "wins": 0, "losses": 0, "total_trades": 0}
        for k, v in _defaults.items():
            portfolio.setdefault("stats", {}).setdefault(k, v)
        if "tier_stats" not in portfolio.get("stats", {}):
            portfolio["stats"]["tier_stats"] = {
                "80+": {"trades": 0, "wins": 0, "pnl": 0},
                "70-79": {"trades": 0, "wins": 0, "pnl": 0},
                "60-69": {"trades": 0, "wins": 0, "pnl": 0},
                "50-59": {"trades": 0, "wins": 0, "pnl": 0},
            }
        return portfolio
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "starting_balance": 10000,
        "current_balance": 10000,
        "leverage": LEVERAGE,
        "tracker_type": "1x_spot_forward_test",
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
            "total_pnl_usdt": 0,
            "best_trade_pnl": 0,
            "worst_trade_pnl": 0,
            # Score-tier breakdown for validation
            "tier_stats": {
                "80+": {"trades": 0, "wins": 0, "pnl": 0},
                "70-79": {"trades": 0, "wins": 0, "pnl": 0},
                "60-69": {"trades": 0, "wins": 0, "pnl": 0},
                "50-59": {"trades": 0, "wins": 0, "pnl": 0},
            },
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


def get_score_tier(score):
    """Return tier label for a score."""
    if score >= 80:
        return "80+"
    elif score >= 70:
        return "70-79"
    elif score >= 60:
        return "60-69"
    else:
        return "50-59"


def get_position_size(score):
    """Score-tiered position sizing."""
    for min_score, size in SCORE_TIERS:
        if score >= min_score:
            return size
    return SCORE_TIERS[-1][1]  # Fallback to smallest tier


def run_check():
    """Main portfolio check -- call every 30 min."""
    portfolio = load_portfolio()
    prices = fetch_prices()

    # Initialize conformal prediction sizer (calibrates from closed trade residuals)
    conformal = ConformalSizer(coverage=0.90) if ConformalSizer else None

    if not prices:
        print("[1x TRACKER] Failed to fetch prices from all APIs")
        return portfolio

    # Ensure tier_stats exists (backwards compat for existing portfolio files)
    if "tier_stats" not in portfolio["stats"]:
        portfolio["stats"]["tier_stats"] = {
            "80+": {"trades": 0, "wins": 0, "pnl": 0},
            "70-79": {"trades": 0, "wins": 0, "pnl": 0},
            "60-69": {"trades": 0, "wins": 0, "pnl": 0},
            "50-59": {"trades": 0, "wins": 0, "pnl": 0},
        }
    if "trailing_stops" not in portfolio["stats"]:
        portfolio["stats"]["trailing_stops"] = 0

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

        # Calculate spot PnL (1x -- no leverage multiplier)
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

        # Check TP hit (with optional TP_WIDEN_FACTOR from R:R backtest)
        tp = pos.get("take_profit", 0)
        if tp > 0 and TP_WIDEN_FACTOR != 1.0 and entry > 0:
            # Widen TP for better R:R (backtest-driven, see rr_backtest_results.json)
            original_tp_dist = abs(tp - entry)
            widened_dist = original_tp_dist * TP_WIDEN_FACTOR
            if direction in ("LONG", "BUY"):
                tp = entry + widened_dist
            else:
                tp = entry - widened_dist
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
                positions_to_close.append(pos_id)
                portfolio["stats"]["tp_hits"] += 1
                portfolio["stats"]["wins"] += 1
                print(f"  TP HIT: {pos['symbol']} {direction} entry={entry:.6f} tp={tp:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT")
                continue

        # Check SL hit (with grace period and widening for shakeout protection)
        sl = pos.get("stop_loss", 0)
        if sl > 0:
            # Calculate how long position has been open
            try:
                opened_at = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
                hours_open = (now - opened_at).total_seconds() / 3600
            except Exception:
                hours_open = 999  # Assume old position if parsing fails

            # EMERGENCY FIX: 4-hour SL grace period -- don't close on SL within first 4 hours
            # This prevents shakeouts where price dips then recovers
            if hours_open < SL_GRACE_PERIOD_HOURS:
                # During grace period, only close if price drops below WIDENED SL
                # (catastrophic protection only, not normal SL)
                if hours_open < SL_WIDEN_PERIOD_HOURS:
                    # First 2 hours: widen SL by 50% (give maximum breathing room)
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
                    # Hours 2-4: use normal SL but still in grace period (log only)
                    effective_sl = sl

                sl_hit_grace = False
                if direction in ("LONG", "BUY") and current <= effective_sl:
                    sl_hit_grace = True
                elif direction in ("SHORT", "SELL") and current >= effective_sl:
                    sl_hit_grace = True

                if not sl_hit_grace:
                    # Within grace period and price hasn't breached widened SL -- SKIP
                    if direction in ("LONG", "BUY") and current <= sl:
                        print(f"  [SL GRACE] {pos['symbol']}: SL breached but within {hours_open:.1f}h grace period (widened SL={effective_sl:.6f}) -- holding")
                    # Don't check normal SL during grace period
                    sl = 0  # Temporarily disable normal SL check below

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
                positions_to_close.append(pos_id)
                portfolio["stats"]["sl_hits"] += 1
                portfolio["stats"]["losses"] += 1
                print(f"  SL HIT: {pos['symbol']} {direction} entry={entry:.6f} sl={sl:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT")
                continue

        # === Trailing Stop Logic ===
        if direction in ("LONG", "BUY"):
            if "hwm_price" not in pos or current > pos.get("hwm_price", 0):
                pos["hwm_price"] = current
        else:
            if "hwm_price" not in pos or current < pos.get("hwm_price", float("inf")):
                pos["hwm_price"] = current

        # Activate trailing stop once we reach activation threshold
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

        # Check trailing stop hit
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
                positions_to_close.append(pos_id)
                portfolio["stats"]["trailing_stops"] += 1
                if trail_pnl > 0:
                    portfolio["stats"]["wins"] += 1
                else:
                    portfolio["stats"]["losses"] += 1
                print(f"  TRAILING STOP: {pos['symbol']} {direction} entry={entry:.6f} trail={trail:.6f} now={current:.6f} pnl=${pos['pnl_usdt']:+.2f}")
                continue

        # === Time-Based Exit Logic ===
        # Top copy traders on Bybit/Bitget use 4-12h optimal hold with strict time exits
        try:
            opened_at_te = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
            hours_open_te = (now - opened_at_te).total_seconds() / 3600
        except Exception:
            hours_open_te = 0

        # Determine max hold hours based on asset type (forex symbols contain "=")
        is_forex = "=" in pos.get("symbol", "") or pos.get("symbol", "").startswith("EUR") or pos.get("symbol", "").startswith("GBP") or pos.get("symbol", "").startswith("USD") or pos.get("symbol", "").startswith("JPY") or pos.get("symbol", "").startswith("AUD")
        max_hold = MAX_HOLD_HOURS_FOREX if is_forex else MAX_HOLD_HOURS_CRYPTO

        time_exit = False
        time_exit_reason = ""

        # Rule 1: If profitable after OPTIMAL_HOLD_HOURS, close to lock in gains
        if hours_open_te > OPTIMAL_HOLD_HOURS and pnl_pct > 0:
            time_exit = True
            time_exit_reason = "TIME_EXIT_PROFIT"
            print(f"  TIME EXIT (PROFIT): {pos['symbol']} {direction} open {hours_open_te:.1f}h > {OPTIMAL_HOLD_HOURS}h, pnl={pnl_pct*100:+.2f}% -- locking profits")

        # Rule 2: Hard max hold -- close regardless (losers that didn't recover)
        elif hours_open_te > max_hold:
            time_exit = True
            time_exit_reason = "TIME_EXIT_MAX_HOLD"
            print(f"  TIME EXIT (MAX HOLD): {pos['symbol']} {direction} open {hours_open_te:.1f}h > {max_hold}h max -- force closing, pnl={pnl_pct*100:+.2f}%")

        if time_exit:
            pos["close_reason"] = time_exit_reason
            pos["close_price"] = current
            pos["close_time"] = now.isoformat()
            pos["pnl_pct"] = pnl_pct * 100
            pos["pnl_usdt"] = pnl_usdt
            pos["hours_held"] = round(hours_open_te, 1)
            positions_to_close.append(pos_id)
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

    # Close positions and update tier stats
    for pos_id in positions_to_close:
        pos = portfolio["positions"].pop(pos_id)
        portfolio["closed_positions"].append(pos)
        portfolio["stats"]["total_pnl_usdt"] += pos["pnl_usdt"]
        portfolio["current_balance"] += pos["pnl_usdt"]
        if pos["pnl_usdt"] > portfolio["stats"]["best_trade_pnl"]:
            portfolio["stats"]["best_trade_pnl"] = pos["pnl_usdt"]
        if pos["pnl_usdt"] < portfolio["stats"]["worst_trade_pnl"]:
            portfolio["stats"]["worst_trade_pnl"] = pos["pnl_usdt"]

        # Track per-tier performance
        tier = get_score_tier(pos.get("score", 0))
        tier_stats = portfolio["stats"]["tier_stats"].get(tier, {"trades": 0, "wins": 0, "pnl": 0})
        tier_stats["trades"] += 1
        if pos["pnl_usdt"] > 0:
            tier_stats["wins"] += 1
        tier_stats["pnl"] = round(tier_stats["pnl"] + pos["pnl_usdt"], 2)
        portfolio["stats"]["tier_stats"][tier] = tier_stats

        # Update conformal prediction calibration set
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

    # === EMERGENCY: Consecutive loss cooldown ===
    # After 2 consecutive losses, pause new entries for 1 hour
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

    # === REGIME GATE (SOFT): Tighten score thresholds against BTC 4h trend ===
    # At 1x, we don't hard-block -- instead raise the score bar.
    # Bearish: LONGs need score >= 60 (instead of 50)
    # Bullish: SHORTs need score >= 60 (instead of 50)
    btc_regime, btc_4h_change = fetch_btc_4h_regime()
    regime_min_score = MIN_SCORE_1X  # default
    if btc_regime != "neutral":
        print(f"  [REGIME] BTC 4h regime: {btc_regime} ({btc_4h_change:+.2f}%)")

    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        # EMERGENCY: Cooldown after consecutive losses
        if cooldown_active:
            print(f"  [COOLDOWN] Skipping all new entries -- loss cooldown active")
            break

        # Max total positions cap (EMERGENCY: reduced to 3)
        if len(portfolio["positions"]) >= MAX_TOTAL_POSITIONS:
            break

        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        score = float(pick.get("elite_score", pick.get("score", pick.get("confidence", 0))) or 0)

        # REGIME HARD-BLOCK (backtested: PF 1.43 -> 2.45, drawdown -7.7x)
        # Block LONGs when 3+ bearish signals present (RSI>70, below EMA, MACD bearish, F&G<25)
        # Backtest showed 23/24 blocked picks at 3/6 threshold were losers (4.2% WR)
        direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
        bearish_count = 0
        _rsi = float(pick.get("rsi_at_entry", pick.get("rsi", 50)) or 50)
        _fg = float(pick.get("fear_greed_index", 50) or 50)
        _regime = str(pick.get("regime_at_entry", "") or "").lower()
        if _rsi > 70: bearish_count += 1
        if _fg < 25: bearish_count += 1
        if _regime in ("bear", "bearish", "crash", "choppy"): bearish_count += 1
        # Check if price below key EMAs (from pick metadata if available)
        if pick.get("below_ema21", False) or pick.get("below_ema50", False): bearish_count += 1
        if direction in ("LONG", "BUY") and bearish_count >= 3:
            # BYPASS: A/S tier (score >= 75) or proven copy trader consensus
            _strat_lower = strategy.lower()
            _is_bypass = (
                score >= 75  # A/S tier: 100% WR on 3 trades
                or "binance_smart_money" in _strat_lower  # 100% WR in bearish
                or ("copy_" in _strat_lower and float(pick.get("confidence", 0) or 0) >= 0.85)  # High-conf copy trader
                or ("ct_consensus" in _strat_lower)  # Cross-trader consensus
            )
            if _is_bypass:
                print(f"  [REGIME BYPASS] {sym} LONG allowed despite {bearish_count} bearish signals: score={score:.0f} strat={strategy[:30]} (SIZE HALVED)")
                pick["_regime_bypass"] = True
                pick["_regime_size_mult"] = 0.5  # Enter at half size in bearish
            else:
                print(f"  [REGIME BLOCK] {sym} LONG blocked: {bearish_count} bearish signals (RSI={_rsi:.0f}, F&G={_fg:.0f}, regime={_regime})")
                continue
        if direction in ("SHORT", "SELL") and bearish_count == 0 and _rsi < 30:
            print(f"  [REGIME BLOCK] {sym} SHORT blocked: 0 bearish signals + RSI oversold")
            continue

        # No blackout hours at 1x -- trade all hours
        # No symbol blacklist at 1x -- test everything to gather data

        # Quality filter: score >= 50 for 1x (EMERGENCY: enforced strictly)
        if score < MIN_SCORE_1X:
            continue

        # Correlation group limit: max 3 per group at 1x
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

        # CONSECUTIVE LOSS GUARD: skip if this symbol lost 3+ times in a row recently
        recent_closed = portfolio.get("closed_positions", [])
        sym_losses = 0
        for cp in reversed(recent_closed[-10:]):
            if cp.get("symbol") == sym:
                if (cp.get("pnl_pct", 0) or 0) < 0:
                    sym_losses += 1
                else:
                    break  # streak broken
            # Also count if same normalized symbol
            elif normalize_symbol(cp.get("symbol", "")) == normalize_symbol(sym):
                if (cp.get("pnl_pct", 0) or 0) < 0:
                    sym_losses += 1
                else:
                    break
        if sym_losses >= 2:  # Tightened from 3 to 2
            print(f"  [LOSS GUARD] Skipping {sym}: {sym_losses} consecutive losses -- cooling off")
            continue

        # TIME COOLDOWN: Don't re-enter a symbol within 4 hours of its last SL hit
        SL_COOLDOWN_HOURS = 4
        last_sl_time = None
        for cp in reversed(recent_closed[-20:]):
            cp_sym = normalize_symbol(cp.get("symbol", ""))
            if cp_sym == normalize_symbol(sym) and cp.get("close_reason", "") == "SL_HIT":
                try:
                    last_sl_time = datetime.fromisoformat(cp.get("close_time", ""))
                except Exception:
                    pass
                break
        if last_sl_time:
            hours_since_sl = (now - last_sl_time).total_seconds() / 3600
            if hours_since_sl < SL_COOLDOWN_HOURS:
                print(f"  [SL COOLDOWN] Skipping {sym}: SL hit {hours_since_sl:.1f}h ago, need {SL_COOLDOWN_HOURS}h cooldown")
                continue

        # ANTI-CHASE: Don't re-enter at a WORSE price than the stopped-out entry
        # (Codex lesson: FET stopped at $0.214, re-entered at $0.2236 = +4.5% higher = chasing)
        for cp in reversed(recent_closed[-20:]):
            cp_sym = normalize_symbol(cp.get("symbol", ""))
            if cp_sym == normalize_symbol(sym) and cp.get("close_reason", "") == "SL_HIT":
                old_entry = float(cp.get("entry_price", 0) or 0)
                new_entry = float(pick.get("entry_price", 0) or 0)
                cp_dir = str(cp.get("direction", "LONG")).upper()
                if old_entry > 0 and new_entry > 0:
                    if cp_dir in ("LONG", "BUY") and new_entry > old_entry * 1.01:
                        print(f"  [ANTI-CHASE] Skipping {sym}: new entry ${new_entry:.4f} > old ${old_entry:.4f} (+{(new_entry/old_entry-1)*100:.1f}%) -- don't chase after SL")
                        break
                    elif cp_dir in ("SHORT", "SELL") and new_entry < old_entry * 0.99:
                        print(f"  [ANTI-CHASE] Skipping {sym}: new entry ${new_entry:.4f} < old ${old_entry:.4f} -- don't chase short after SL")
                        break
        else:
            pass  # No chase detected, continue
        if cp_sym == normalize_symbol(sym) and cp.get("close_reason", "") == "SL_HIT":
            old_entry = float(cp.get("entry_price", 0) or 0)
            new_entry = float(pick.get("entry_price", 0) or 0)
            cp_dir = str(cp.get("direction", "LONG")).upper()
            if old_entry > 0 and new_entry > 0:
                if (cp_dir in ("LONG", "BUY") and new_entry > old_entry * 1.01) or \
                   (cp_dir in ("SHORT", "SELL") and new_entry < old_entry * 0.99):
                    continue

        # Only 1 position per normalized symbol (prevent duplicates like BTC-USD + BTCUSDT)
        norm_base = normalize_symbol(sym)
        existing_syms = {normalize_symbol(p["symbol"]) for p in portfolio["positions"].values()}
        if norm_base in existing_syms:
            continue

        entry = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()

        # REGIME-AWARE DIRECTION FILTER (replaces LONG_ONLY_MODE)
        # xBrat data: crypto SHORTs 71% WR vs LONGs 64% in bearish regime
        # Our data: LONGs 69.4% WR overall, but SHORTs work in bearish conditions
        # Rule: Allow direction that matches the regime
        _regime_dir = str(pick.get("regime_at_entry", "") or "").lower()
        _fg_val = float(pick.get("fear_greed_index", 50) or 50)

        # Determine market bias
        if _regime_dir in ("bear", "bearish", "crash") or _fg_val < 25:
            _market_bias = "BEARISH"
        elif _regime_dir in ("bull", "bullish", "trending") or _fg_val > 60:
            _market_bias = "BULLISH"
        else:
            _market_bias = "NEUTRAL"

        # Direction filter based on regime
        if _market_bias == "BEARISH" and direction in ("LONG", "BUY"):
            # Allow LONGs only if score >= 75 (A/S tier proven winners)
            if score < 75:
                continue  # Block weak LONGs in bearish regime
        elif _market_bias == "BULLISH" and direction in ("SHORT", "SELL"):
            # Allow SHORTs only if score >= 75 (proven short strategies)
            if score < 75:
                continue  # Block weak SHORTs in bullish regime
        # NEUTRAL: allow both directions at any score

        # STALE ENTRY GUARD: if last closed trade on this symbol had same entry price
        # and was a loss, skip -- the pick hasn't refreshed from the scanner
        for cp in reversed(portfolio.get("closed_positions", [])[-5:]):
            cp_sym = cp.get("symbol", "")
            cp_entry = cp.get("entry_price", 0) or 0
            cp_pnl = cp.get("pnl_pct", 0) or 0
            if (normalize_symbol(cp_sym) == normalize_symbol(sym)
                    and abs(cp_entry - entry) < entry * 0.001  # same price within 0.1%
                    and cp_pnl < 0):
                print(f"  [STALE GUARD] Skipping {sym}: same entry ${entry:.2f} as last SL hit -- pick not refreshed")
                entry = 0  # force skip below
                break

        if entry <= 0:
            continue

        # Verify current price is close to entry (don't enter stale picks)
        norm_sym = normalize_symbol(sym)
        current = prices.get(norm_sym, 0)
        if current > 0:
            gap = abs(current - entry) / entry
            if gap > 0.05:  # 5% staleness tolerance (wider than 20x)
                continue

            # EMERGENCY FIX: "Wait for dip" entry -- don't enter at market price
            # Enter at current market price (dip wait disabled -- need trade data)
            entry = current

        # Enforce min/max stop distance -- crypto noise is 1-2%/hour
        if sl > 0 and entry > 0:
            stop_dist = abs(entry - sl) / entry
            # WIDEN stops that are too tight (main cause of 0/9 WR)
            if stop_dist < MIN_STOP_DISTANCE_PCT:
                if direction in ("LONG", "BUY"):
                    sl = entry * (1 - MIN_STOP_DISTANCE_PCT)
                else:
                    sl = entry * (1 + MIN_STOP_DISTANCE_PCT)
                stop_dist = MIN_STOP_DISTANCE_PCT
            # CAP stops that are too wide
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

        # SANITY CHECK 2: Entry price must be within 10% of live market price
        live_price = prices.get(norm_sym, 0)
        if live_price > 0 and entry > 0:
            entry_gap = abs(entry - live_price) / live_price
            if entry_gap > 0.10:  # >10% stale
                print(f"  [SANITY] STALE entry for {sym}: entry=${entry:.4f} vs live=${live_price:.4f} ({entry_gap*100:.0f}% gap)")
                continue

        # STRICT CONFLUENCE MODE (xBrat approach: ALL lights must be green)
        # Instead of composite scoring, require independent pass on each dimension
        STRICT_CONFLUENCE = True
        if STRICT_CONFLUENCE:
            confluence_checks = {
                "score_pass": score >= MIN_SCORE_1X,
                "direction_match": True,  # Already filtered above by regime
                "not_stale": True,  # Already filtered by staleness check
                "rr_acceptable": float(pick.get("risk_reward", 0) or 0) >= 1.0,
                "confidence_min": float(pick.get("confidence", 0) or 0) >= 0.55,
                "not_meme_in_bear": not (
                    sym.upper().replace("USDT","") in {"DOGE","SHIB","PEPE","BONK","FLOKI","WIF","FARTCOIN"}
                    and _market_bias == "BEARISH"
                    and direction in ("LONG", "BUY")
                ),
            }
            failed = [k for k, v in confluence_checks.items() if not v]
            if failed:
                # Log first failure only to reduce noise
                print(f"  [CONFLUENCE] {sym} blocked: {failed[0]} failed ({len(failed)} total)")
                continue

        # Score-tiered position sizing
        position_size = get_position_size(score)

        # Apply conformal prediction sizing multiplier
        conformal_mult = 1.0
        if conformal is not None:
            ml_prob = score / 100.0  # normalize score to 0-1 for conformal
            conformal_mult = conformal.size_multiplier(ml_prob)
            position_size = round(position_size * conformal_mult, 2)

        # Apply anti-martingale sizing (scale up after wins, down after losses)
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

        portfolio["positions"][pos_key] = {
            "symbol": sym,
            "strategy": strategy,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "score": score,
            "score_tier": get_score_tier(score),
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
        }
        portfolio["stats"]["total_trades"] += 1
        print(f"  NEW POSITION: {sym} {direction} entry={entry:.6f} tp={tp:.6f} sl={sl:.6f} score={score:.0f} size=${position_size}")

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
    print(f"1x SPOT PORTFOLIO TRACKER -- {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"Balance: ${portfolio['current_balance']:,.2f} (started $10,000)")
    print(f"Unrealized: ${unrealized_pnl:+,.2f}")
    print(f"Equity: ${portfolio['current_balance'] + unrealized_pnl:,.2f}")
    print(f"Open positions: {len(portfolio['positions'])} / {MAX_TOTAL_POSITIONS}")
    print(f"Closed trades: {total} ({stats['wins']}W-{stats['losses']}L = {wr:.0f}% WR)")
    time_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason", "").startswith("TIME_EXIT"))
    time_profit_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason") == "TIME_EXIT_PROFIT")
    time_max_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason") == "TIME_EXIT_MAX_HOLD")
    print(f"TP Hits: {stats['tp_hits']} | SL Hits: {stats['sl_hits']} | Trail Stops: {stats['trailing_stops']} | Time Exits: {time_exits} (profit={time_profit_exits}, max={time_max_exits})")
    print(f"Total realized P&L: ${stats['total_pnl_usdt']:+,.2f}")
    print(f"Best trade: ${stats['best_trade_pnl']:+,.2f} | Worst: ${stats['worst_trade_pnl']:+,.2f}")

    # Score tier breakdown
    print(f"\n{'='*60}")
    print("SCORE TIER PERFORMANCE (1x Forward Test):")
    for tier_name in ["80+", "70-79", "60-69", "50-59"]:
        ts = stats.get("tier_stats", {}).get(tier_name, {"trades": 0, "wins": 0, "pnl": 0})
        tier_wr = ts["wins"] / ts["trades"] * 100 if ts["trades"] > 0 else 0
        print(f"  {tier_name:>5s}: {ts['trades']:>3d} trades | {ts['wins']:>3d} wins ({tier_wr:>5.1f}% WR) | PnL: ${ts['pnl']:>+8.2f}")
    print(f"{'='*60}")

    if open_positions:
        print(f"\nOpen Positions:")
        for pos in sorted(open_positions, key=lambda x: x.get("current_pnl_pct", 0)):
            pnl = pos.get("current_pnl_pct", 0)
            pnl_usdt = pos.get("current_pnl_usdt", 0)
            print(f"  {pos['symbol']:12s} {pos['direction']:5s} score={pos.get('score',0):>3.0f} size=${pos.get('position_size',0):>3.0f} pnl={pnl:>+6.2f}% (${pnl_usdt:>+7.2f})")

    return portfolio


if __name__ == "__main__":
    run_check()
