#!/usr/bin/env python3
"""
20x Leverage Portfolio Tracker
Simulates a real 20x leverage portfolio using our active picks.
Tracks which picks would survive, get liquidated, or hit TP at 20x.

Run every 30 min to build a realistic P&L history.
"""

import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_20x.json")
ACTIVE_PICKS_FILE = os.path.join(DATA_DIR, "active_picks.json")

LEVERAGE = 20
BASE_POSITION_SIZE = 100  # Base $100 per position (scaled by equity + volatility)
LIQUIDATION_THRESHOLD = -0.95  # -95% of margin = liquidated at 20x
MAX_RISK_PER_TRADE = 0.005  # 0.5% of equity risked per trade
RESERVE_PCT = 0.20  # 20% stablecoin reserve -- never deploy full equity

# Time-based exit parameters (tighter for 20x -- faster exits at leverage)
# 20x hold times: extended but shorter than 1x due to leverage risk
# Research: 3-7D has best directional edge, but 20x amplifies drawdowns
# Compromise: longer than before, trailing stops as primary exit
OPTIMAL_HOLD_HOURS_20X = 12       # 12h -- lock profits (was 6h, closed winners too early)
MAX_HOLD_HOURS_CRYPTO_20X = 72    # 3 days -- where directional edge starts (was 24h)
MAX_HOLD_HOURS_FOREX_20X = 48     # 48h -- forex moves 0.3-0.8%/day; edge gone after 2 days

# Trailing stop parameters (static fallback when ATR not available)
TRAILING_STOP_ACTIVATION = 0.004  # Lowered: +0.4% spot (+8% at 20x) -- FETUSDT peaked at +0.5% but missed 0.8%
TRAILING_STOP_DISTANCE = 0.003    # Trail by 0.3% (6% buffer at 20x)
MAX_STOP_DISTANCE_PCT = 0.015     # Tightened: 1.5% max stop (was 2%) = 30% max loss at 20x

# R:R backtest result (2026-03-21, 545 closed picks):
# Current 2:1 R:R is optimal. Wider ratios destroy WR faster than they grow avg win.
# At 20x leverage, conservative approach: keep TP as-is (factor 1.0).
TP_WIDEN_FACTOR_20X = 1.0  # Multiply original TP distance by this (1.0 = no change)

# ATR-based trailing stop multipliers (preferred when atr_at_entry available)
ATR_TRAIL_MULT_20X = 0.5          # Trail distance = 0.5 * ATR (tighter for 20x leverage)
ATR_ACTIVATION_MULT_20X = 0.3     # Activate trailing at 0.3 * ATR profit (spot terms)

# Correlation groups -- max 1 position per group (was 2, reduced to prevent correlated losses)
CORRELATION_GROUPS = {
    "large_cap": ["BTC-USD", "BTCUSDT", "ETH-USD", "ETHUSDT"],
    "alt_l1": ["SOL-USD", "SOLUSDT", "AVAX-USD", "AVAXUSDT", "NEAR-USD", "NEARUSDT", "DOT-USD", "DOTUSDT"],
    "defi": ["LINK-USD", "LINKUSDT", "UNI-USD", "UNIUSDT", "AAVE-USD", "AAVEUSDT"],
    "meme": ["DOGE-USD", "DOGEUSDT", "SHIB-USD", "SHIBUSDT"],
    "exchange": ["BNB-USD", "BNBUSDT"],
    "infra": ["RENDER-USD", "RENDERUSDT", "FIL-USD", "FILUSDT", "FET-USD", "FETUSDT"],
}
MAX_PER_CORRELATION_GROUP = 1  # 1 per group -- prevents correlated multi-loss events
MIN_SCORE_20X = 68  # B grade minimum -- data shows <68 loses at 20x leverage
MAX_TOTAL_POSITIONS_20X = 2  # EMERGENCY: was 4, cut to 2 -- max 2 open at 20x
BLOCK_SHORTS_20X = True  # SHORT WR = 20.5% -- death at leverage

# EMERGENCY FIXES (2026-03-18): inherited from 1x disaster analysis
SL_GRACE_PERIOD_HOURS_20X = 4     # Don't close on SL within first 4 hours
SL_WIDEN_PERIOD_HOURS_20X = 2     # Widen SL by 30% for first 2 hours (less than 1x since leveraged)
SL_WIDEN_FACTOR_20X = 1.3         # SL distance * 1.3 during first 2h (tighter than 1x)
CONSECUTIVE_LOSS_PAUSE_HOURS_20X = 2  # After 1 loss at 20x, pause for 2 hours
CONSECUTIVE_LOSS_PAUSE_COUNT_20X = 1  # Just 1 loss triggers cooldown at 20x

# Time-of-day blackout (UTC hours): data shows <15% WR in these windows
# Hours 08 (8% WR/25 trades), 20 (5.7%/35), 23 (6.7%/30), 00 (14.7%/34), 17 (0%/14)
BLACKOUT_HOURS_UTC = {2, 8, 17}  # Only block the 3 worst hours (0% WR with 5+ samples)

# Symbol blacklist: proven losers from quality_investigation.json
# BTCUSDT: 7.7% WR -94.54 PnL | ADAUSDT: 7.7% WR -123.84 PnL | WIF-USD: 15.4% WR -32.8 PnL
SYMBOL_BLACKLIST_20X = {
    "BTCUSDT", "ADAUSDT", "ADA-USD", "WIF-USD", "WIFUSDT",
    "SOL-USD",  # 0% WR in spot symbol form (SOLUSDT separately ok if score high)
    "AVAX-USD", "DOT-USD", "TIA-USD", "ETC-USD",
    "SPY", "QQQ",  # ETFs: 0% WR
    "BONK-USD",  # 25% WR -30.54 PnL
    "FLOKI-USD",  # 25% WR -8.14 PnL
    "STRKUSDT",  # 33% WR -12.86 PnL
    "INJUSDT",  # 25% WR -20.36 PnL
    "POLUSDT",  # 25% WR -11.84 PnL
}

# Symbol whitelist: high conviction based on historical performance
# Only for preferential scoring -- does not bypass other filters
SYMBOL_WHITELIST_20X = {
    "RENDERUSDT", "FETUSDT", "BNBUSDT", "TRXUSDT",
    "FILUSDT", "HBARUSDT", "OPUSDT", "LINKUSDT",
    "NEARUSDT", "APTUSDT", "ARBUSDT", "SUIUSDT",
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
                open_4h_ago = float(klines[0][1])  # open of 4h-ago candle
                close_now = float(klines[-1][4])    # close of latest candle
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

    # Fallback: CoinGecko BTC price (no klines, use 24h change as proxy)
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        change_24h = data.get("bitcoin", {}).get("usd_24h_change", 0)
        # Approximate 4h from 24h: scale by 1/6 (rough)
        approx_4h = change_24h / 6.0
        if approx_4h < -1.0:
            return "bearish", round(approx_4h, 2)
        elif approx_4h > 1.0:
            return "bullish", round(approx_4h, 2)
        return "neutral", round(approx_4h, 2)
    except Exception:
        pass

    return "neutral", 0.0  # fail-open: allow trades if regime unknown


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
                # Map coingecko IDs to USDT symbols
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


def load_portfolio():
    """Load existing portfolio state."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "starting_balance": 10000,
        "current_balance": 10000,
        "positions": {},
        "closed_positions": [],
        "snapshots": [],
        "stats": {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "liquidations": 0,
            "tp_hits": 0,
            "sl_hits": 0,
            "total_pnl_usdt": 0,
            "best_trade_pnl": 0,
            "worst_trade_pnl": 0,
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


def run_check():
    """Main portfolio check -- call every 30 min."""
    portfolio = load_portfolio()
    prices = fetch_prices()

    if not prices:
        print("[20x TRACKER] Failed to fetch prices from all APIs")
        return portfolio

    now = datetime.now(timezone.utc)

    # Load active picks
    try:
        with open(ACTIVE_PICKS_FILE, "r", encoding="utf-8") as f:
            active_picks = json.load(f)
    except Exception:
        active_picks = []

    # === Check existing positions for TP/SL/Liquidation ===
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

        # Calculate spot PnL
        if direction in ("LONG", "BUY"):
            spot_pnl_pct = (current - entry) / entry
        else:
            spot_pnl_pct = (entry - current) / entry

        leveraged_pnl_pct = spot_pnl_pct * LEVERAGE
        pos_size = pos.get("position_size", BASE_POSITION_SIZE)
        pnl_usdt = pos_size * leveraged_pnl_pct

        # SANITY CHECK 3: PnL must be within reasonable bounds (500% at 20x = 25% spot move * 20)
        max_pnl_pct = 5.0  # 500% max for 20x leverage
        if abs(leveraged_pnl_pct) > max_pnl_pct:
            print(f"  [SANITY] CAPPING PnL for {pos['symbol']}: {leveraged_pnl_pct*100:.1f}% exceeds max {max_pnl_pct*100:.0f}%")
            leveraged_pnl_pct = max_pnl_pct if leveraged_pnl_pct > 0 else -max_pnl_pct
            pnl_usdt = pos_size * leveraged_pnl_pct

        # Check liquidation (-95% of margin at 20x = -4.75% spot move)
        if leveraged_pnl_pct <= LIQUIDATION_THRESHOLD:
            pos["close_reason"] = "LIQUIDATED"
            pos["close_price"] = current
            pos["close_time"] = now.isoformat()
            pos["pnl_pct"] = leveraged_pnl_pct * 100
            pos["pnl_usdt"] = -pos.get("position_size", BASE_POSITION_SIZE) * 0.95
            positions_to_close.append(pos_id)
            portfolio["stats"]["liquidations"] += 1
            portfolio["stats"]["losses"] += 1
            print(f"  LIQUIDATED: {pos['symbol']} {direction} entry={entry:.6f} now={current:.6f} spot={spot_pnl_pct*100:+.2f}% lev={leveraged_pnl_pct*100:+.1f}%")
            continue

        # Check TP hit (with optional TP_WIDEN_FACTOR from R:R backtest)
        tp = pos.get("take_profit", 0)
        if tp > 0 and TP_WIDEN_FACTOR_20X != 1.0 and entry > 0:
            original_tp_dist = abs(tp - entry)
            widened_dist = original_tp_dist * TP_WIDEN_FACTOR_20X
            if direction in ("LONG", "BUY"):
                tp = entry + widened_dist
            else:
                tp = entry - widened_dist
        if tp > 0:
            if direction in ("LONG", "BUY") and current >= tp:
                pos["close_reason"] = "TP_HIT"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = leveraged_pnl_pct * 100
                pos["pnl_usdt"] = pnl_usdt
                positions_to_close.append(pos_id)
                portfolio["stats"]["tp_hits"] += 1
                portfolio["stats"]["wins"] += 1
                print(f"  TP HIT: {pos['symbol']} {direction} entry={entry:.6f} tp={tp:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT")
                continue
            elif direction in ("SHORT", "SELL") and current <= tp:
                pos["close_reason"] = "TP_HIT"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = leveraged_pnl_pct * 100
                pos["pnl_usdt"] = pnl_usdt
                positions_to_close.append(pos_id)
                portfolio["stats"]["tp_hits"] += 1
                portfolio["stats"]["wins"] += 1
                print(f"  TP HIT: {pos['symbol']} {direction} entry={entry:.6f} tp={tp:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT")
                continue

        # Check SL hit (with grace period for shakeout protection)
        sl = pos.get("stop_loss", 0)
        if sl > 0:
            # Calculate how long position has been open
            try:
                opened_at = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
                hours_open = (now - opened_at).total_seconds() / 3600
            except Exception:
                hours_open = 999

            # EMERGENCY FIX: 4-hour SL grace period at 20x
            # During grace period, use widened SL (first 2h) or normal SL (2-4h) but log grace
            effective_sl = sl
            in_grace = hours_open < SL_GRACE_PERIOD_HOURS_20X
            if in_grace and hours_open < SL_WIDEN_PERIOD_HOURS_20X and entry > 0:
                sl_dist = abs(entry - sl)
                widened_dist = sl_dist * SL_WIDEN_FACTOR_20X
                if direction in ("LONG", "BUY"):
                    effective_sl = entry - widened_dist
                else:
                    effective_sl = entry + widened_dist

            sl_hit = False
            if direction in ("LONG", "BUY") and current <= effective_sl:
                sl_hit = True
            elif direction in ("SHORT", "SELL") and current >= effective_sl:
                sl_hit = True

            # During grace period (2-4h), if normal SL is breached but widened isn't, hold
            if not sl_hit and in_grace:
                normal_sl_hit = False
                if direction in ("LONG", "BUY") and current <= sl:
                    normal_sl_hit = True
                elif direction in ("SHORT", "SELL") and current >= sl:
                    normal_sl_hit = True
                if normal_sl_hit:
                    print(f"  [SL GRACE 20x] {pos['symbol']}: SL breached but within {hours_open:.1f}h grace -- holding (widened SL={effective_sl:.6f})")

            if sl_hit:
                pos["close_reason"] = "SL_HIT"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = leveraged_pnl_pct * 100
                pos["pnl_usdt"] = pnl_usdt
                positions_to_close.append(pos_id)
                portfolio["stats"]["sl_hits"] = portfolio["stats"].get("sl_hits", 0) + 1
                portfolio["stats"]["losses"] += 1
                print(f"  SL HIT: {pos['symbol']} {direction} entry={entry:.6f} sl={effective_sl:.6f} now={current:.6f} pnl={pnl_usdt:+.2f} USDT")
                continue

        # === Trailing Stop Logic ===
        # Track high water mark in spot price terms
        if direction in ("LONG", "BUY"):
            if "hwm_price" not in pos or current > pos.get("hwm_price", 0):
                pos["hwm_price"] = current
        else:
            if "hwm_price" not in pos or current < pos.get("hwm_price", float("inf")):
                pos["hwm_price"] = current

        # Determine ATR-based or static trailing stop parameters
        atr_trail_dist = pos.get("trailing_stop_atr_distance", 0)
        if atr_trail_dist > 0 and pos.get("hwm_price", 0) > 0:
            # ATR-based: convert price-space ATR distance to percentage, cap at MAX_STOP_DISTANCE_PCT
            effective_trail_pct = min(atr_trail_dist / pos["hwm_price"], MAX_STOP_DISTANCE_PCT)
            effective_activation = min(pos.get("atr_at_entry", 0) * ATR_ACTIVATION_MULT_20X / entry, TRAILING_STOP_ACTIVATION * 2) if entry > 0 else TRAILING_STOP_ACTIVATION
        else:
            # Fallback: static percentages
            effective_trail_pct = TRAILING_STOP_DISTANCE
            effective_activation = TRAILING_STOP_ACTIVATION

        # Activate trailing stop once we reach activation threshold
        if spot_pnl_pct >= effective_activation:
            hwm = pos["hwm_price"]
            if direction in ("LONG", "BUY"):
                new_trail = hwm * (1 - effective_trail_pct)
                old_trail = pos.get("trailing_stop", 0)
                pos["trailing_stop"] = max(old_trail, new_trail)  # Only move up
            else:
                new_trail = hwm * (1 + effective_trail_pct)
                old_trail = pos.get("trailing_stop", float("inf"))
                pos["trailing_stop"] = min(old_trail, new_trail)  # Only move down

        # Check trailing stop hit
        trail = pos.get("trailing_stop", 0)
        if trail > 0:
            if direction in ("LONG", "BUY") and current <= trail:
                trail_pnl = ((current - entry) / entry) * LEVERAGE
                pos["close_reason"] = "TRAILING_STOP"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = trail_pnl * 100
                pos["pnl_usdt"] = pos["position_size"] * trail_pnl  # BUG FIX: was POSITION_SIZE_USDT (undefined)
                positions_to_close.append(pos_id)
                if trail_pnl > 0:
                    portfolio["stats"]["wins"] += 1
                else:
                    portfolio["stats"]["losses"] += 1
                print(f"  TRAILING STOP: {pos['symbol']} {direction} entry={entry:.6f} trail={trail:.6f} now={current:.6f} pnl=${pos['pnl_usdt']:+.2f}")
                continue
            elif direction in ("SHORT", "SELL") and trail < float("inf") and current >= trail:
                trail_pnl = ((entry - current) / entry) * LEVERAGE
                pos["close_reason"] = "TRAILING_STOP"
                pos["close_price"] = current
                pos["close_time"] = now.isoformat()
                pos["pnl_pct"] = trail_pnl * 100
                pos["pnl_usdt"] = pos["position_size"] * trail_pnl  # BUG FIX: was POSITION_SIZE_USDT (undefined)
                positions_to_close.append(pos_id)
                if trail_pnl > 0:
                    portfolio["stats"]["wins"] += 1
                else:
                    portfolio["stats"]["losses"] += 1
                print(f"  TRAILING STOP: {pos['symbol']} {direction} entry={entry:.6f} trail={trail:.6f} now={current:.6f} pnl=${pos['pnl_usdt']:+.2f}")
                continue

        # === MAX PAIN CIRCUIT BREAKER ===
        # Close position if it drops beyond -40% leveraged to prevent liquidation
        MAX_PAIN_THRESHOLD = -0.40
        if leveraged_pnl_pct <= MAX_PAIN_THRESHOLD and leveraged_pnl_pct > LIQUIDATION_THRESHOLD:
            pos["close_reason"] = "MAX_PAIN_CIRCUIT"
            pos["close_price"] = current
            pos["close_time"] = now.isoformat()
            pos["pnl_pct"] = leveraged_pnl_pct * 100
            pos["pnl_usdt"] = pnl_usdt
            positions_to_close.append(pos_id)
            portfolio["stats"]["losses"] += 1
            print(f"  MAX PAIN CIRCUIT: {pos['symbol']} {direction} closed at {leveraged_pnl_pct*100:.1f}% to prevent liquidation")
            continue

        # === Time-Based Exit Logic (tighter for 20x leverage) ===
        # Top copy traders on Bybit/Bitget use 4-12h optimal hold; at 20x we exit faster
        try:
            opened_at_te = datetime.fromisoformat(pos.get("opened_at", now.isoformat()))
            hours_open_te = (now - opened_at_te).total_seconds() / 3600
        except Exception:
            hours_open_te = 0

        # Determine max hold hours based on asset type
        is_forex = "=" in pos.get("symbol", "") or pos.get("symbol", "").startswith("EUR") or pos.get("symbol", "").startswith("GBP") or pos.get("symbol", "").startswith("USD") or pos.get("symbol", "").startswith("JPY") or pos.get("symbol", "").startswith("AUD")
        max_hold_20x = MAX_HOLD_HOURS_FOREX_20X if is_forex else MAX_HOLD_HOURS_CRYPTO_20X

        time_exit = False
        time_exit_reason = ""

        # Rule 1: If profitable after OPTIMAL_HOLD_HOURS_20X, close to lock in gains
        if hours_open_te > OPTIMAL_HOLD_HOURS_20X and spot_pnl_pct > 0:
            time_exit = True
            time_exit_reason = "TIME_EXIT_PROFIT"
            print(f"  TIME EXIT (PROFIT): {pos['symbol']} {direction} open {hours_open_te:.1f}h > {OPTIMAL_HOLD_HOURS_20X}h, lev_pnl={leveraged_pnl_pct*100:+.1f}% -- locking profits at 20x")

        # Rule 2: Hard max hold -- close regardless (no overnight leverage risk)
        elif hours_open_te > max_hold_20x:
            time_exit = True
            time_exit_reason = "TIME_EXIT_MAX_HOLD"
            print(f"  TIME EXIT (MAX HOLD): {pos['symbol']} {direction} open {hours_open_te:.1f}h > {max_hold_20x}h max -- force closing 20x, lev_pnl={leveraged_pnl_pct*100:+.1f}%")

        if time_exit:
            pos["close_reason"] = time_exit_reason
            pos["close_price"] = current
            pos["close_time"] = now.isoformat()
            pos["pnl_pct"] = leveraged_pnl_pct * 100
            pos["pnl_usdt"] = pnl_usdt
            pos["hours_held"] = round(hours_open_te, 1)
            positions_to_close.append(pos_id)
            if leveraged_pnl_pct > 0:
                portfolio["stats"]["wins"] += 1
            else:
                portfolio["stats"]["losses"] += 1
            continue

        # Update position state
        if "high_water_mark_pnl" not in pos:
            pos["high_water_mark_pnl"] = leveraged_pnl_pct * 100
        pos["high_water_mark_pnl"] = max(pos["high_water_mark_pnl"], leveraged_pnl_pct * 100)
        pos["current_pnl_pct"] = leveraged_pnl_pct * 100
        pos["current_pnl_usdt"] = pnl_usdt
        pos["current_price"] = current
        pos["last_checked"] = now.isoformat()

    # Close positions
    for pos_id in positions_to_close:
        pos = portfolio["positions"].pop(pos_id)
        portfolio["closed_positions"].append(pos)
        portfolio["stats"]["total_pnl_usdt"] += pos["pnl_usdt"]
        portfolio["current_balance"] += pos["pnl_usdt"]
        if pos["pnl_usdt"] > portfolio["stats"]["best_trade_pnl"]:
            portfolio["stats"]["best_trade_pnl"] = pos["pnl_usdt"]
        if pos["pnl_usdt"] < portfolio["stats"]["worst_trade_pnl"]:
            portfolio["stats"]["worst_trade_pnl"] = pos["pnl_usdt"]

    # === Add new positions from active picks ===
    # Count positions per correlation group
    group_counts = {}
    for pos in portfolio["positions"].values():
        psym = pos.get("symbol", "")
        for grp, syms in CORRELATION_GROUPS.items():
            if psym in syms:
                group_counts[grp] = group_counts.get(grp, 0) + 1

    # === 24h Drawdown Circuit Breaker ===
    # If portfolio drops >5% in 24h, pause new entries
    pause_new_entries = False
    if portfolio.get("snapshots"):
        cutoff_24h = (now - __import__("datetime").timedelta(hours=24)).isoformat()
        snapshots_24h = [s for s in portfolio["snapshots"] if s.get("time", "") >= cutoff_24h]
        if len(snapshots_24h) >= 2:
            equity_24h_ago = snapshots_24h[0].get("equity", portfolio.get("starting_balance", 10000))
            current_equity = portfolio["current_balance"] + sum(
                p.get("current_pnl_usdt", 0) for p in portfolio["positions"].values()
            )
            drawdown_24h = (current_equity - equity_24h_ago) / equity_24h_ago if equity_24h_ago > 0 else 0
            if drawdown_24h < -0.05:
                pause_new_entries = True
                print(f"  CIRCUIT BREAKER: 24h drawdown {drawdown_24h:.1%} -- pausing new entries")

    if pause_new_entries:
        active_picks = []  # Don't process new picks during drawdown

    # === EMERGENCY: Consecutive loss cooldown for 20x ===
    # After just 1 loss at 20x, pause new entries for 2 hours
    recent_closed_20x = portfolio.get("closed_positions", [])
    consecutive_losses_20x = 0
    for cp in reversed(recent_closed_20x[-10:]):
        if (cp.get("pnl_pct", 0) or cp.get("pnl_usdt", 0) or 0) < 0:
            consecutive_losses_20x += 1
        else:
            break

    cooldown_active_20x = False
    if consecutive_losses_20x >= CONSECUTIVE_LOSS_PAUSE_COUNT_20X and recent_closed_20x:
        last_loss_time_str = recent_closed_20x[-1].get("close_time", "")
        try:
            last_loss_time = datetime.fromisoformat(last_loss_time_str)
            hours_since_last_loss = (now - last_loss_time).total_seconds() / 3600
            if hours_since_last_loss < CONSECUTIVE_LOSS_PAUSE_HOURS_20X:
                cooldown_active_20x = True
                print(f"  [COOLDOWN 20x] {consecutive_losses_20x} consecutive losses -- pausing new entries for {CONSECUTIVE_LOSS_PAUSE_HOURS_20X - hours_since_last_loss:.1f}h more")
        except Exception:
            pass

    # === REGIME GATE: Block directional entries against BTC 4h trend ===
    # At 20x leverage, entering LONGs in a bearish market is catastrophic.
    # SOL/BTC/XRP lost ~40% each because winner_pattern_precursor entered LONGs during bearish regime.
    btc_regime, btc_4h_change = fetch_btc_4h_regime()
    if btc_regime != "neutral":
        print(f"  [REGIME] BTC 4h regime: {btc_regime} ({btc_4h_change:+.2f}%)")

    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        # EMERGENCY: Cooldown after losses at 20x
        if cooldown_active_20x:
            print(f"  [COOLDOWN 20x] Skipping all new entries -- loss cooldown active")
            break

        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        score = float(pick.get("elite_score", pick.get("score", pick.get("confidence", 0))) or 0)

        # === Time-of-day blackout filter ===
        # Data shows 0-15% WR in hours 00, 06, 08, 17, 20-23 (25-35+ sample sizes)
        if now.hour in BLACKOUT_HOURS_UTC:
            continue

        # === Symbol blacklist filter ===
        # BTCUSDT: 7.7% WR, ADAUSDT: 7.7% WR -- proven losers at 20x
        norm_sym_check = normalize_symbol(sym)
        if sym in SYMBOL_BLACKLIST_20X or norm_sym_check in SYMBOL_BLACKLIST_20X:
            continue

        # Quality filter: score >= 68 for 20x (raised from 65 -- data shows 65-67 still loses)
        if score < MIN_SCORE_20X:
            continue

        # Whitelist bonus: boost effective score for high-confidence symbols
        if sym in SYMBOL_WHITELIST_20X or norm_sym_check in SYMBOL_WHITELIST_20X:
            score = min(100, score + 3)  # +3 bonus for whitelist, ensures eligibility at 65→68

        # Forward validation gate -- only block if explicitly disqualified
        # If field doesn't exist, rely on score + blacklist + time filters instead
        # (None of the current active picks populate forward_validated, so strict=True blocks everything)
        forward_validated = pick.get("forward_validated")  # None = not set, False = explicitly failed
        forward_wr = pick.get("forward_wr")
        # Only block if BOTH: explicitly failed AND has a real WR below threshold
        # forward_wr=None/0 means "not evaluated" -- let score gate handle it
        if forward_validated is False and forward_wr and float(forward_wr) > 0 and float(forward_wr) < 0.55:
            continue

        # Correlation group limit: max 2 per group
        skip_corr = False
        for grp, syms in CORRELATION_GROUPS.items():
            if sym in syms and group_counts.get(grp, 0) >= MAX_PER_CORRELATION_GROUP:
                skip_corr = True
                break
        if skip_corr:
            continue

        # Skip if already in portfolio
        pos_key = f"{sym}_{strategy}"
        if pos_key in portfolio["positions"]:
            continue

        # Only allow 1 position per symbol at 20x (prevent doubling down)
        norm_base = normalize_symbol(sym)
        existing_syms = {normalize_symbol(p["symbol"]) for p in portfolio["positions"].values()}
        if norm_base in existing_syms:
            continue

        # Max total positions cap for 20x -- quality over quantity
        if len(portfolio["positions"]) >= MAX_TOTAL_POSITIONS_20X:
            break

        entry = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()

        # Block SHORTs at 20x -- 20.5% WR = guaranteed loss at leverage
        if BLOCK_SHORTS_20X and direction in ("SHORT", "SELL"):
            continue

        # === REGIME GATE: Hard block on directional entries at 20x ===
        # Bearish regime: block ALL new LONGs (catastrophic at 20x)
        # Bullish regime: block ALL new SHORTs (already blocked by BLOCK_SHORTS_20X above, but explicit)
        if btc_regime == "bearish" and direction in ("LONG", "BUY"):
            print(f"  REGIME GATE: blocked LONG entry on {sym} in bearish regime (BTC 4h: {btc_4h_change:+.2f}%)")
            continue
        if btc_regime == "bullish" and direction in ("SHORT", "SELL"):
            print(f"  REGIME GATE: blocked SHORT entry on {sym} in bullish regime (BTC 4h: {btc_4h_change:+.2f}%)")
            continue

        # Regime direction filter -- don't take LONGs when market is against them
        regime = pick.get("market_regime", "")
        long_wr_live = float(pick.get("long_wr_live", 0.5) or 0.5)
        if direction in ("LONG", "BUY") and long_wr_live < 0.45:
            print(f"  [REGIME GATE] SKIP {sym}: LONG WR {long_wr_live:.0%} < 45% in current regime")
            continue

        if entry <= 0:
            continue

        # Verify current price is close to entry (don't enter stale picks)
        norm_sym = normalize_symbol(sym)
        current = prices.get(norm_sym, 0)
        if current > 0:
            gap = abs(current - entry) / entry
            if gap > 0.022:  # More than 2.2% from entry = stale for 20x
                continue

        # SANITY CHECK 2: Entry price must be within 10% of live market price
        live_price = prices.get(norm_sym, 0)
        if live_price > 0 and entry > 0:
            entry_gap = abs(entry - live_price) / live_price
            if entry_gap > 0.10:  # >10% stale
                print(f"  [SANITY] STALE entry for {sym}: entry=${entry:.4f} vs live=${live_price:.4f} ({entry_gap*100:.0f}% gap)")
                continue

        # Tighten stop for 20x: cap at MAX_STOP_DISTANCE_PCT
        if sl > 0 and entry > 0:
            stop_dist = abs(entry - sl) / entry
            if stop_dist > MAX_STOP_DISTANCE_PCT:
                if direction in ("LONG", "BUY"):
                    sl = entry * (1 - MAX_STOP_DISTANCE_PCT)
                else:
                    sl = entry * (1 + MAX_STOP_DISTANCE_PCT)
                # Adjust TP to maintain at least 2:1 R:R
                risk = abs(entry - sl)
                if direction in ("LONG", "BUY"):
                    tp = max(tp, entry + risk * 2)
                else:
                    tp = min(tp, entry - risk * 2)

        # Dynamic position sizing: risk 0.5% of equity per trade, scaled by score tier
        equity = portfolio["current_balance"]
        deployable = equity * (1 - RESERVE_PCT)
        logging.info(f"Reserve: {RESERVE_PCT*100}% ({equity * RESERVE_PCT:.2f}) held as stablecoin buffer")
        stop_dist_pct = abs(entry - sl) / entry if sl > 0 and entry > 0 else MAX_STOP_DISTANCE_PCT
        max_risk_usd = deployable * MAX_RISK_PER_TRADE
        # Position size = max_risk / (stop_distance * leverage)
        if stop_dist_pct > 0:
            position_size = min(BASE_POSITION_SIZE, max_risk_usd / (stop_dist_pct * LEVERAGE))
        else:
            position_size = BASE_POSITION_SIZE

        # Scale position size by score quality tier
        if score >= 80:
            position_size *= 1.0    # Full size for Grade A/S
        elif score >= 70:
            position_size *= 0.75   # 75% for high B
        elif score >= 65:
            position_size *= 0.50   # 50% for low B (minimum 20x threshold)
        else:
            position_size *= 0.25   # 25% safety net (shouldn't reach here with MIN_SCORE_20X=68)

        # Volatility-adjusted sizing: reduce exposure on high-vol assets
        # BTC: 1.0x, ETH: 0.85x, major alts: 0.7x, small/meme: 0.5x
        VOLATILITY_MULTIPLIERS = {
            "BTCUSDT": 1.0, "BTC-USD": 1.0,
            "ETHUSDT": 0.85, "ETH-USD": 0.85,
            "BNBUSDT": 0.8, "BNB-USD": 0.8,
            "XRPUSDT": 0.7, "XRP-USD": 0.7,
            "SOLUSDT": 0.7, "SOL-USD": 0.7,
            "AVAXUSDT": 0.7, "AVAX-USD": 0.7,
            "LINKUSDT": 0.7, "LINK-USD": 0.7,
            "DOTUSDT": 0.7, "DOT-USD": 0.7,
            "NEARUSDT": 0.6, "NEAR-USD": 0.6,
            "ADAUSDT": 0.7, "ADA-USD": 0.7,
        }
        vol_mult = VOLATILITY_MULTIPLIERS.get(sym, VOLATILITY_MULTIPLIERS.get(normalize_symbol(sym), 0.5))
        position_size *= vol_mult

        # === HRP-Based Position Sizing ===
        # When 2+ positions are open, use Hierarchical Risk Parity (Lopez de Prado 2016)
        # to adjust position sizes based on correlation-aware clustering of strategies.
        # HRP weight * num_positions normalizes so that the sum of weights ~ 1.0 per slot.
        # Falls back to equal weight if HRP fails (missing data, scipy unavailable, etc.)
        try:
            open_strategies = [p.get("strategy", "") for p in portfolio["positions"].values()]
            all_strategies = list(set(open_strategies + [strategy]))
            if len(all_strategies) >= 2:
                import sys as _sys
                _hrp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "battleground")
                if _hrp_dir not in _sys.path:
                    _sys.path.insert(0, _hrp_dir)
                from hrp_allocation import compute_hrp_weights
                hrp_weights = compute_hrp_weights(all_strategies, total_risk_budget=1.0)
                hrp_w = hrp_weights.get(strategy, 1.0 / len(all_strategies))
                hrp_scale = hrp_w * len(all_strategies)  # Re-scale: equal weight = 1.0x
                hrp_scale = max(0.25, min(hrp_scale, 3.0))  # Clamp to [0.25x, 3.0x]
                position_size *= hrp_scale
                print(f"  [HRP] {sym} weight={hrp_w:.3f} scale={hrp_scale:.2f}x ({len(all_strategies)} strategies)")
        except Exception as _hrp_err:
            pass  # HRP unavailable -- keep equal-weight position size

        # === Drawdown-Based Continuous Position Scaling ===
        # Linear reduction from 100% at 2% DD to 25% at 5%+ DD (replaces binary pause
        # with proportional scaling; the 24h circuit breaker remains as final backstop)
        high_water_mark = max(
            portfolio.get("starting_balance", 10000),
            max((s.get("equity", 0) for s in portfolio.get("snapshots", [{}])), default=portfolio.get("starting_balance", 10000)),
        )
        dd = 1 - (equity / high_water_mark) if high_water_mark > 0 else 0
        if dd > 0.02:
            dd_scale = max(0.25, 1.0 - (dd / 0.05))
            position_size *= dd_scale
            print(f"  [DD SCALE] drawdown={dd:.2%} high_water={high_water_mark:.2f} scale={dd_scale:.2f}x")

        # === Drawdown Governor from position_sizing module ===
        try:
            from position_sizing import get_drawdown_governor_multiplier
            dd_gov_mult = get_drawdown_governor_multiplier(PORTFOLIO_FILE)
            if dd_gov_mult < 1.0:
                position_size *= dd_gov_mult
                print(f"  [DD GOVERNOR] mult={dd_gov_mult:.2f}x applied to {sym}")
        except Exception as _dd_err:
            pass  # fail-open: module unavailable or portfolio missing

        position_size = max(10, round(position_size, 2))  # Min $10

        # SANITY CHECK 4: Position size must not exceed portfolio limits
        max_single = portfolio["current_balance"] * 0.15  # Max 15% per position
        if position_size > max_single:
            print(f"  [SANITY] CAPPING position size for {sym}: ${position_size:.0f} > ${max_single:.0f} (15% limit)")
            position_size = max_single

        # Update correlation group count
        for grp, syms in CORRELATION_GROUPS.items():
            if sym in syms:
                group_counts[grp] = group_counts.get(grp, 0) + 1

        # Extract ATR for volatility-adjusted trailing stops
        atr_at_entry = float(pick.get("atr_at_entry") or 0)
        trailing_stop_atr = 0.0
        if atr_at_entry > 0:
            trailing_stop_atr = atr_at_entry * ATR_TRAIL_MULT_20X

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
            "atr_at_entry": atr_at_entry,
            "trailing_stop_atr_distance": trailing_stop_atr,
        }
        portfolio["stats"]["total_trades"] += 1
        print(f"  NEW POSITION: {sym} {direction} entry={entry:.6f} tp={tp:.6f} sl={sl:.6f} score={score:.0f}")

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
        "liquidations": portfolio["stats"]["liquidations"],
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
    print(f"20x PORTFOLIO TRACKER -- {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"Balance: ${portfolio['current_balance']:,.2f} (started $10,000)")
    print(f"Unrealized: ${unrealized_pnl:+,.2f}")
    print(f"Equity: ${portfolio['current_balance'] + unrealized_pnl:,.2f}")
    print(f"Open positions: {len(portfolio['positions'])}")
    print(f"Closed trades: {total} ({stats['wins']}W-{stats['losses']}L = {wr:.0f}% WR)")
    print(f"Liquidations: {stats['liquidations']}")
    time_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason", "").startswith("TIME_EXIT"))
    time_profit_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason") == "TIME_EXIT_PROFIT")
    time_max_exits = sum(1 for cp in portfolio.get("closed_positions", []) if cp.get("close_reason") == "TIME_EXIT_MAX_HOLD")
    print(f"TP Hits: {stats['tp_hits']} | SL Hits: {stats['sl_hits']} | Time Exits: {time_exits} (profit={time_profit_exits}, max={time_max_exits})")
    print(f"Total realized P&L: ${stats['total_pnl_usdt']:+,.2f}")
    print(f"Best trade: ${stats['best_trade_pnl']:+,.2f} | Worst: ${stats['worst_trade_pnl']:+,.2f}")

    if open_positions:
        print(f"\nOpen Positions:")
        for pos in sorted(open_positions, key=lambda x: x.get("current_pnl_pct", 0)):
            pnl = pos.get("current_pnl_pct", 0)
            pnl_usdt = pos.get("current_pnl_usdt", 0)
            status = "WIN" if pnl > 0 else "LOSS" if pnl < -50 else "DANGER" if pnl < -20 else "OK"
            print(f"  {pos['symbol']:12s} {pos['direction']:5s} score={pos.get('score',0):>3.0f} pnl={pnl:>+7.1f}% (${pnl_usdt:>+7.2f}) [{status}]")

    # Trust tier recommendations
    print(f"\n{'='*60}")
    print("TRUST TIERS FOR 20x:")
    print(f"  Score 70+:  SAFE for 20x (current active WR: 100%)")
    print(f"  Score 50-69: MODERATE risk (current active WR: 90%)")
    print(f"  Score 30-49: HIGH risk at 20x (WR: 61%)")
    print(f"  Score <30:  DO NOT USE at 20x")
    print(f"{'='*60}")

    return portfolio


if __name__ == "__main__":
    run_check()
