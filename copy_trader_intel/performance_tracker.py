#!/usr/bin/env python3
"""
Copy Trader Performance Tracker
================================
Forward-test performance tracker for copy trader picks.
Fetches current prices, resolves TP/SL hits, tracks per-trader stats,
and computes trust scores.

Usage:
    python copy_trader_intel/performance_tracker.py

Data flow:
    1. Load active_picks.json (open picks from scrapers)
    2. Load closed_trades.json (previously resolved)
    3. Fetch current prices from Binance (3+ API failover)
    4. Resolve picks: TP hit -> WON, SL hit -> LOST, >48h -> EXPIRED
    5. Update active_picks.json (remove resolved)
    6. Update closed_trades.json (append resolved)
    7. Compute per-trader stats -> trader_performance.json
    8. Compute trust scores -> trader_trust.json
    9. Print leaderboard
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("[FATAL] requests library required: pip install requests")
    sys.exit(1)

# -- Paths --
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
CLOSED_TRADES_FILE = DATA_DIR / "closed_trades.json"
TRADER_PERFORMANCE_FILE = DATA_DIR / "trader_performance.json"
TRADER_TRUST_FILE = DATA_DIR / "trader_trust.json"
HIGH_WATER_FILE = DATA_DIR / "high_water_marks.json"

# -- Binance API Mirrors (3+ failover per project rules) --
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Fallback price APIs (CoinGecko, KuCoin)
FALLBACK_APIS = [
    {
        "name": "CoinGecko",
        "url": "https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
        "parse": lambda data, cg_id: data.get(cg_id, {}).get("usd"),
    },
    {
        "name": "KuCoin",
        "url": "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_sym}",
        "parse": lambda data, _: float(data.get("data", {}).get("price", 0)) or None,
    },
]

# Rate limiting
RATE_LIMIT_MS = 200
_last_request_time = 0.0

# Pick expiry (hours)
PICK_EXPIRY_HOURS = 48

# -- Symbol mapping helpers --
# Map USDT pairs to CoinGecko IDs for fallback
_CG_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "XRPUSDT": "ripple", "ADAUSDT": "cardano", "DOGEUSDT": "dogecoin",
    "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot", "LINKUSDT": "chainlink",
    "MATICUSDT": "matic-network", "ATOMUSDT": "cosmos", "LTCUSDT": "litecoin",
    "UNIUSDT": "uniswap", "APTUSDT": "aptos", "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism", "NEARUSDT": "near", "SUIUSDT": "sui",
    "SEIUSDT": "sei-network", "TIAUSDT": "celestia",
}


def _rate_limit():
    """Enforce minimum delay between API requests."""
    global _last_request_time
    now = time.time()
    elapsed_ms = (now - _last_request_time) * 1000
    if elapsed_ms < RATE_LIMIT_MS:
        time.sleep((RATE_LIMIT_MS - elapsed_ms) / 1000)
    _last_request_time = time.time()


def fetch_price_binance(symbol: str) -> float | None:
    """Fetch current price from Binance with mirror failover."""
    for mirror in BINANCE_MIRRORS:
        _rate_limit()
        try:
            url = f"{mirror}/api/v3/ticker/price?symbol={symbol}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get("price", 0))
                if price > 0:
                    return price
        except Exception:
            continue
    return None


def fetch_price_fallback(symbol: str) -> float | None:
    """Try CoinGecko and KuCoin as fallbacks."""
    # CoinGecko
    cg_id = _CG_MAP.get(symbol)
    if cg_id:
        _rate_limit()
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                price = resp.json().get(cg_id, {}).get("usd")
                if price and float(price) > 0:
                    return float(price)
        except Exception:
            pass

    # KuCoin (symbol format: BTC-USDT)
    kucoin_sym = symbol.replace("USDT", "-USDT")
    _rate_limit()
    try:
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_sym}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            price_str = (data.get("data") or {}).get("price")
            if price_str:
                price = float(price_str)
                if price > 0:
                    return price
    except Exception:
        pass

    return None


def fetch_current_price(symbol: str) -> float | None:
    """Fetch price with full failover chain: Binance mirrors -> CoinGecko -> KuCoin."""
    price = fetch_price_binance(symbol)
    if price:
        return price
    return fetch_price_fallback(symbol)


def batch_fetch_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetch prices for multiple symbols efficiently.
    Uses Binance batch ticker endpoint first, then fills gaps with individual calls.
    """
    prices = {}

    # Try Binance batch endpoint first (all symbols at once)
    for mirror in BINANCE_MIRRORS:
        _rate_limit()
        try:
            url = f"{mirror}/api/v3/ticker/price"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                all_tickers = resp.json()
                ticker_map = {t["symbol"]: float(t["price"]) for t in all_tickers if float(t.get("price", 0)) > 0}
                for sym in symbols:
                    if sym in ticker_map:
                        prices[sym] = ticker_map[sym]
                break
        except Exception:
            continue

    # Fill gaps with individual calls + fallback
    missing = [s for s in symbols if s not in prices]
    if missing:
        print(f"  Fetching {len(missing)} missing prices individually...")
        for sym in missing:
            price = fetch_current_price(sym)
            if price:
                prices[sym] = price

    return prices


# -- File I/O --

def load_json(path: Path) -> list | dict:
    """Load JSON file, return empty list if missing or invalid."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_json(path: Path, data):
    """Save data to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# -- Pick Resolution --

def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Handle various formats
        ts_str = str(ts_str).strip()
        if "T" in ts_str:
            # ISO format with or without timezone
            if "+" in ts_str or ts_str.endswith("Z"):
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        # Date only (e.g., "2026-03-19")
        return datetime.strptime(ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def resolve_picks(active_picks: list, prices: dict, high_water: dict) -> tuple[list, list]:
    """
    Resolve picks based on current prices.

    For each open pick:
    - Check if TP was hit (price moved favorably past take_profit)
    - Check if SL was hit (price moved unfavorably past stop_loss)
    - Track high-water mark (best price seen)
    - Expire picks older than 48 hours

    Returns: (still_open, newly_closed)
    """
    now = datetime.now(timezone.utc)
    still_open = []
    newly_closed = []

    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        symbol = pick.get("symbol", "")
        current_price = prices.get(symbol)

        if current_price is None:
            # Can't resolve without price, keep open
            still_open.append(pick)
            continue

        pick_id = pick.get("id", "")
        direction = pick.get("direction", pick.get("signal_type", "BUY")).upper()
        entry_price = pick.get("entry_price", 0)
        tp_price = pick.get("take_profit", 0)
        sl_price = pick.get("stop_loss", 0)

        if not entry_price or entry_price <= 0:
            still_open.append(pick)
            continue

        # Update high-water mark
        hwm_key = pick_id or f"{symbol}_{entry_price}"
        prev_hwm = high_water.get(hwm_key, entry_price)

        if direction in ("LONG", "BUY"):
            high_water[hwm_key] = max(prev_hwm, current_price)
        else:
            # For shorts, "high water" = lowest price seen (best for short)
            high_water[hwm_key] = min(prev_hwm, current_price)

        # Check TP/SL hit
        resolved = False
        exit_reason = None
        pnl_pct = 0.0

        if direction in ("LONG", "BUY"):
            # Long: TP hit when price >= tp_price, SL hit when price <= sl_price
            if tp_price and current_price >= tp_price:
                exit_reason = "TP_HIT"
                pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                resolved = True
            elif sl_price and current_price <= sl_price:
                exit_reason = "SL_HIT"
                pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                resolved = True
        else:
            # Short: TP hit when price <= tp_price, SL hit when price >= sl_price
            if tp_price and current_price <= tp_price:
                exit_reason = "TP_HIT"
                pnl_pct = ((entry_price - tp_price) / entry_price) * 100
                resolved = True
            elif sl_price and current_price >= sl_price:
                exit_reason = "SL_HIT"
                pnl_pct = ((entry_price - sl_price) / entry_price) * 100
                resolved = True

        # Check expiry (48 hours)
        if not resolved:
            entry_time = parse_timestamp(pick.get("timestamp") or pick.get("entry_date"))
            if entry_time:
                age_hours = (now - entry_time).total_seconds() / 3600
                if age_hours > PICK_EXPIRY_HOURS:
                    exit_reason = "EXPIRED"
                    # PnL at expiry based on current price
                    if direction in ("LONG", "BUY"):
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    resolved = True

        if resolved:
            # Mark as closed
            pick["status"] = "CLOSED"
            pick["exit_price"] = current_price
            pick["exit_date"] = now.isoformat()
            pick["exit_reason"] = exit_reason
            pick["pnl_pct"] = round(pnl_pct, 4)
            allocation = pick.get("allocation", 200.0)
            pick["pnl_dollar"] = round(allocation * (pnl_pct / 100), 2)

            # Compute hold time
            entry_time = parse_timestamp(pick.get("timestamp") or pick.get("entry_date"))
            if entry_time:
                hold_hours = (now - entry_time).total_seconds() / 3600
                pick["hold_days"] = round(hold_hours / 24, 2)
            else:
                pick["hold_days"] = None

            pick["high_water_mark"] = high_water.get(hwm_key, entry_price)
            newly_closed.append(pick)

            # Remove from high water tracking
            high_water.pop(hwm_key, None)
        else:
            still_open.append(pick)

    return still_open, newly_closed


# -- Trader Stats --

def extract_trader_name(pick: dict) -> str:
    """Extract trader name from strategy field."""
    strategy = pick.get("strategy", "")
    # Remove common prefixes
    for prefix in ("copy_hl_lb_", "copy_hl_", "copy_okx_"):
        if strategy.startswith(prefix):
            return strategy[len(prefix):]
    return strategy or "Unknown"


def extract_source(pick: dict) -> str:
    """Extract source platform from pick."""
    strategy = pick.get("strategy", "")
    source = pick.get("source_system", "")
    if "okx" in strategy.lower() or "okx" in source.lower():
        return "okx"
    if "hl" in strategy.lower() or "hyperliquid" in source.lower():
        return "hyperliquid"
    return source or "unknown"


def compute_trader_stats(active_picks: list, closed_trades: list) -> dict:
    """
    Compute per-trader performance stats.

    Returns dict keyed by trader_name with stats.
    """
    if not active_picks and not closed_trades:
        return {}

    # Guard against None/non-dict items in lists
    active_picks = [p for p in (active_picks or []) if isinstance(p, dict)]
    closed_trades = [t for t in (closed_trades or []) if isinstance(t, dict)]

    # Group all picks by trader
    trader_picks = {}

    for pick in active_picks:
        name = extract_trader_name(pick)
        if name not in trader_picks:
            trader_picks[name] = {"open": [], "closed": [], "source": extract_source(pick)}
        trader_picks[name]["open"].append(pick)

    for trade in closed_trades:
        name = extract_trader_name(trade)
        if name not in trader_picks:
            trader_picks[name] = {"open": [], "closed": [], "source": extract_source(trade)}
        trader_picks[name]["closed"].append(trade)

    # Compute stats per trader
    stats = {}
    for name, data in trader_picks.items():
        open_picks = data["open"]
        closed = data["closed"]
        source = data["source"]

        wins = [t for t in closed if t.get("exit_reason") == "TP_HIT"]
        losses = [t for t in closed if t.get("exit_reason") == "SL_HIT"]
        expired = [t for t in closed if t.get("exit_reason") == "EXPIRED"]

        total = len(open_picks) + len(closed)
        closed_count = len(closed)

        # Win rate (only from resolved, not expired)
        decided = len(wins) + len(losses)
        win_rate = (len(wins) / decided * 100) if decided > 0 else 0.0

        # Profit factor = gross_wins / gross_losses
        gross_win = sum(abs(t.get("pnl_pct", 0)) for t in wins)
        gross_loss = sum(abs(t.get("pnl_pct", 0)) for t in losses)
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (
            99.0 if gross_win > 0 else 0.0
        )

        # Average PnL
        all_pnl = [t.get("pnl_pct", 0) for t in closed if t.get("pnl_pct") is not None]
        avg_pnl = (sum(all_pnl) / len(all_pnl)) if all_pnl else 0.0

        # Average hold time
        hold_times = [t.get("hold_days", 0) for t in closed if t.get("hold_days") is not None]
        avg_hold = (sum(hold_times) / len(hold_times)) if hold_times else 0.0

        # Best and worst trade (coerce None → 0 to avoid TypeError)
        best_trade = max(closed, key=lambda t: t.get("pnl_pct") or 0, default=None)
        worst_trade = min(closed, key=lambda t: t.get("pnl_pct") or 0, default=None)

        stats[name] = {
            "trader_name": name,
            "source": source,
            "total_picks": total,
            "open": len(open_picks),
            "closed": closed_count,
            "wins": len(wins),
            "losses": len(losses),
            "expired": len(expired),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_pnl_pct": round(avg_pnl, 4),
            "avg_hold_days": round(avg_hold, 2),
            "total_pnl_pct": round(sum(all_pnl), 4),
            "best_trade": {
                "symbol": best_trade.get("symbol", ""),
                "pnl_pct": best_trade.get("pnl_pct", 0),
                "direction": best_trade.get("direction", ""),
            } if best_trade else None,
            "worst_trade": {
                "symbol": worst_trade.get("symbol", ""),
                "pnl_pct": worst_trade.get("pnl_pct", 0),
                "direction": worst_trade.get("direction", ""),
            } if worst_trade else None,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    return stats


# -- Trust Scoring --

def compute_trust_scores(trader_stats: dict, existing_trust: dict) -> dict:
    """
    Compute trust scores per trader.

    Rules:
    - Start at 50 (or use existing score)
    - +5 per winning trade (cumulative from total wins)
    - -8 per losing trade (cumulative from total losses)
    - +10 bonus if WR > 60% after 10+ decided trades
    - -15 penalty if WR < 40% after 10+ decided trades
    - Clamp to [0, 100]
    - Flag for removal if below 20
    """
    trust = {}

    for name, stats in trader_stats.items():
        # Start from existing score or base of 50
        prev = existing_trust.get(name, {})
        prev_wins_counted = prev.get("wins_counted", 0)
        prev_losses_counted = prev.get("losses_counted", 0)
        base_score = prev.get("trust_score", 50)

        current_wins = stats.get("wins", 0)
        current_losses = stats.get("losses", 0)

        # Only apply delta (new wins/losses since last run)
        new_wins = max(0, current_wins - prev_wins_counted)
        new_losses = max(0, current_losses - prev_losses_counted)

        score = base_score + (new_wins * 5) - (new_losses * 8)

        # Bonus/penalty based on WR after 10+ decided trades
        decided = current_wins + current_losses
        wr = stats.get("win_rate", 0)

        wr_bonus_applied = prev.get("wr_bonus_applied", False)
        wr_penalty_applied = prev.get("wr_penalty_applied", False)

        if decided >= 10:
            if wr > 60 and not wr_bonus_applied:
                score += 10
                wr_bonus_applied = True
            elif wr < 40 and not wr_penalty_applied:
                score -= 15
                wr_penalty_applied = True

            # Reset flags if WR changes zone
            if wr <= 60:
                wr_bonus_applied = False
            if wr >= 40:
                wr_penalty_applied = False

        # Clamp
        score = max(0, min(100, score))

        trust[name] = {
            "trader_name": name,
            "source": stats.get("source", "unknown"),
            "trust_score": round(score, 1),
            "wins_counted": current_wins,
            "losses_counted": current_losses,
            "total_decided": decided,
            "win_rate": wr,
            "wr_bonus_applied": wr_bonus_applied,
            "wr_penalty_applied": wr_penalty_applied,
            "flagged_for_removal": score < 20,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    return trust


# -- Leaderboard --

def print_leaderboard(trader_stats: dict, trust_scores: dict):
    """Print a formatted leaderboard sorted by profit factor."""
    if not trader_stats:
        print("\n  No trader stats available yet.")
        return

    # Sort by profit factor descending
    sorted_traders = sorted(
        trader_stats.values(),
        key=lambda t: t.get("profit_factor", 0),
        reverse=True,
    )

    print("\n" + "=" * 100)
    print("  COPY TRADER LEADERBOARD -- Sorted by Profit Factor")
    print("=" * 100)
    print(f"  {'Rank':<5} {'Trader':<30} {'Source':<12} {'Picks':<7} "
          f"{'Open':<6} {'W/L/E':<10} {'WR%':<8} {'PF':<8} "
          f"{'Avg PnL':<10} {'Trust':<7} {'Flag':<5}")
    print("-" * 100)

    for i, t in enumerate(sorted_traders, 1):
        name = t["trader_name"][:28]
        ts = trust_scores.get(t["trader_name"], {})
        trust = ts.get("trust_score", 50)
        flagged = "!!!" if ts.get("flagged_for_removal") else ""

        wle = f"{t['wins']}/{t['losses']}/{t['expired']}"
        print(f"  {i:<5} {name:<30} {t['source']:<12} {t['total_picks']:<7} "
              f"{t['open']:<6} {wle:<10} {t['win_rate']:<8.1f} {t['profit_factor']:<8.2f} "
              f"{t['avg_pnl_pct']:<10.2f} {trust:<7.0f} {flagged:<5}")

    print("-" * 100)
    total_open = sum(t["open"] for t in sorted_traders)
    total_closed = sum(t["closed"] for t in sorted_traders)
    total_picks = sum(t["total_picks"] for t in sorted_traders)
    print(f"  TOTAL: {total_picks} picks ({total_open} open, {total_closed} closed)")
    flagged_count = sum(1 for ts in trust_scores.values() if ts.get("flagged_for_removal"))
    if flagged_count:
        print(f"  WARNING: {flagged_count} trader(s) flagged for removal (trust < 20)")
    print("=" * 100 + "\n")


# -- Main --

def main():
    """Run the full performance tracking pipeline."""
    print("=" * 70)
    print("  COPY TRADER PERFORMANCE TRACKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. Load data
    print("\n[1/6] Loading data...")
    active_picks = load_json(ACTIVE_PICKS_FILE)
    closed_trades = load_json(CLOSED_TRADES_FILE)
    high_water = load_json(HIGH_WATER_FILE)
    if isinstance(high_water, list):
        high_water = {}
    existing_trust = load_json(TRADER_TRUST_FILE)
    if isinstance(existing_trust, list):
        existing_trust = {}

    open_picks = [p for p in active_picks if isinstance(p, dict) and p.get("status", "OPEN") == "OPEN"]
    print(f"  Active picks: {len(open_picks)}")
    print(f"  Previously closed: {len(closed_trades)}")

    if not open_picks and not closed_trades:
        print("  No picks to track. Exiting.")
        return

    # 2. Fetch current prices
    symbols = sorted(set(p.get("symbol", "") for p in open_picks if p.get("symbol")))
    print(f"\n[2/6] Fetching prices for {len(symbols)} symbols...")
    prices = batch_fetch_prices(symbols)
    print(f"  Got prices for {len(prices)}/{len(symbols)} symbols")

    missing_prices = [s for s in symbols if s not in prices]
    if missing_prices:
        print(f"  Missing prices for: {', '.join(missing_prices[:10])}"
              f"{'...' if len(missing_prices) > 10 else ''}")

    # 3. Resolve picks
    print(f"\n[3/6] Resolving picks...")
    still_open, newly_closed = resolve_picks(open_picks, prices, high_water)
    print(f"  Still open: {len(still_open)}")
    print(f"  Newly closed: {len(newly_closed)}")
    if newly_closed:
        tp_hits = sum(1 for t in newly_closed if t.get("exit_reason") == "TP_HIT")
        sl_hits = sum(1 for t in newly_closed if t.get("exit_reason") == "SL_HIT")
        expired = sum(1 for t in newly_closed if t.get("exit_reason") == "EXPIRED")
        print(f"    TP hits: {tp_hits}, SL hits: {sl_hits}, Expired: {expired}")

    # 4. Update files
    print(f"\n[4/6] Saving updated data...")
    # Merge newly closed into closed trades (avoid duplicates by ID)
    existing_ids = set()
    for t in closed_trades:
        tid = t.get("id", "")
        if tid:
            existing_ids.add(tid)

    for t in newly_closed:
        tid = t.get("id", "")
        if tid and tid not in existing_ids:
            closed_trades.append(t)
            existing_ids.add(tid)
        elif not tid:
            closed_trades.append(t)

    save_json(ACTIVE_PICKS_FILE, still_open)
    save_json(CLOSED_TRADES_FILE, closed_trades)
    save_json(HIGH_WATER_FILE, high_water)
    print(f"  active_picks.json: {len(still_open)} picks")
    print(f"  closed_trades.json: {len(closed_trades)} trades")

    # 5. Compute trader stats
    print(f"\n[5/6] Computing trader stats...")
    trader_stats = compute_trader_stats(still_open or [], closed_trades or [])
    save_json(TRADER_PERFORMANCE_FILE, trader_stats)
    print(f"  {len(trader_stats)} traders tracked")

    # 6. Compute trust scores
    print(f"\n[6/6] Computing trust scores...")
    trust_scores = compute_trust_scores(trader_stats, existing_trust)
    save_json(TRADER_TRUST_FILE, trust_scores)

    flagged = [n for n, t in trust_scores.items() if t.get("flagged_for_removal")]
    if flagged:
        print(f"  FLAGGED for removal: {', '.join(flagged)}")

    # Print leaderboard
    print_leaderboard(trader_stats, trust_scores)

    print("Performance tracking complete.")


if __name__ == "__main__":
    main()
