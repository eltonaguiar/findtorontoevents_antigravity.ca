#!/usr/bin/env python3
"""
Gains Network (gTrade) Top Trader Scraper & Pick Generator
===========================================================
Scrapes Gains Network's gTrade platform for open trades and top traders
across Arbitrum, Base, and Polygon deployments.

NO API KEY NEEDED -- gTrade REST and WebSocket APIs are fully public.

Backend API (DNS pattern: backend-<network>.gains.trade):
  Arbitrum:  https://backend-arbitrum.gains.trade
  Base:      https://backend-base.gains.trade
  Polygon:   https://backend-polygon.gains.trade

Key Endpoints:
  GET /trading-variables       -- Core trading data (pairs, fees, collaterals)
  GET /open-trades             -- All open trades system-wide (DEPRECATED Oct 2025)
  GET /open-trades/<address>   -- Open trades for specific trader
  GET /personal-trading-history-table/<address>  -- Historical trades for trader
  GET /trading-history-24h     -- All trades from last 24 hours

WebSocket (wss://backend-<network>.gains.trade):
  Events: liveEvents, registerTrade, unregisterTrade, updateTrade

gTrade supports 290+ pairs: crypto, forex, commodities, stocks, indices.

Subgraph (stats): https://thegraph.com/hosted-service/subgraph/gainsnetwork-org/gtrade-stats-arbitrum
  (Note: hosted service deprecated -- may need Graph Network API key)
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# -- Configuration --
GAINS_BACKENDS = {
    "arbitrum": "https://backend-arbitrum.gains.trade",
    "base": "https://backend-base.gains.trade",
    "polygon": "https://backend-polygon.gains.trade",
}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.6

# Minimum criteria
MIN_TRADES = 10
MIN_WIN_RATE = 0.50

# Known top gTrade traders (from on-chain API + live open trades data)
# Verified via Gains Network backend-arbitrum.gains.trade/open-trades API (2026-03-19)
# Ranked by number of concurrent open positions (indicates active, serious traders)
SEED_WALLETS = {
    "arbitrum": [
        # --- Top active traders from live /open-trades API (2026-03-19) ---
        ("0x21A85F4097D94FDDD2c899634A0be8347844eb6f", "gtrade_46pos_active"),    # 46 open positions
        ("0x9dD9C763fB332e47D08210F6245847BCd00C546c", "gtrade_39pos_active"),    # 39 open positions
        ("0xA5f6fc9E82d6780D549cD4624971bFb8f3E8917D", "gtrade_37pos_active"),    # 37 open positions
        ("0xF9B0dB290E2bd32792B785Dd63C455F35E91C2f4", "gtrade_24pos_active"),    # 24 open positions
        ("0x9908255F7F2dFfcCaa14448a2356E5A8fD8e8bC1", "gtrade_21pos_whale1"),    # 21 open positions
        ("0xB9eAf02ddF51bAA7be9F1FCeE6C2A1622384a0f4", "gtrade_21pos_whale2"),    # 21 open positions
        ("0xd7189A81961CB3cC0Dd6eC6a1f90Bc5f95DfD7f0", "gtrade_20pos_46k_col"),   # 20 open, 46K collateral
        ("0xA24B7143DcD0A6896F834bb9A02387c335E71247", "gtrade_20pos_active"),    # 20 open positions
        ("0xFa55DDeF91720FaaF5e5615313a4D4bd60dEf821", "gtrade_20pos_whale3"),    # 20 open positions
        ("0xde69ab862A24F2801787545E53b8fC526d739654", "gtrade_18pos_active"),    # 18 open positions
        ("0x2a724bE1b63caEc1c3Ef95834fdD443c3347Ee1D", "gtrade_17pos_347col"),    # 17 open, 347 collateral
        ("0x4CC614ea2E463CAB0b3180F747a3cEef569B2cE5", "gtrade_13pos_active"),    # 13 open positions
        ("0x772bD5185D0bbcaFeb791a31F4Cd9f7AbcfDD961", "gtrade_13pos_whale4"),    # 13 open positions
        ("0x7e0bF7CB9101BF098cDC1211596945218b0303E7", "gtrade_12pos_active"),    # 12 open positions
        ("0x1Cfe4C78c787be6AB0396f303a152a60A462a86A", "gtrade_11pos_active"),    # 11 open positions
        # --- BTC whale with 12x leverage from API sample ---
        ("0x9A4EB6169bb07C51DC3DDCDFA4cF8A5F71616E06", "gtrade_btc_12x_whale"),   # BTC 12x long, 843 collateral
    ],
    "base": [],
    "polygon": [],
}

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/1.0",
}

# gTrade pair index to symbol mapping (common pairs)
# Full list from /trading-variables endpoint
PAIR_INDEX_MAP = {
    0: "BTCUSDT",
    1: "ETHUSDT",
    2: "LINKUSDT",
    3: "DOGEUSDT",
    4: "MATICUSDT",
    5: "ADAUSDT",
    6: "SUSHIUSDT",
    7: "AAVEUSDT",
    8: "ALGOUSDT",
    9: "BATUSDT",
    10: "COMPUSDT",
    11: "DOTUSDT",
    12: "EOSUSDT",
    13: "LTCUSDT",
    14: "MANAUSDT",
    15: "NEOUSDT",
    16: "SOLUSDT",
    17: "UNIUSDT",
    18: "XLMUSDT",
    19: "XRPUSDT",
    20: "YFIUSDT",
    21: "AVAXUSDT",
    # Forex pairs start around index 32
    32: "EURUSD",
    33: "GBPUSD",
    34: "USDJPY",
    35: "USDCHF",
    36: "AUDUSD",
    37: "USDCAD",
    38: "NZDUSD",
    39: "EURGBP",
    40: "EURJPY",
    41: "GBPJPY",
    # Commodities
    46: "XAUUSD",  # Gold
    47: "XAGUSD",  # Silver
    # Stocks start around 60
    60: "AAPL",
    61: "META",
    62: "GOOGL",
    63: "AMZN",
    64: "MSFT",
    65: "TSLA",
    66: "NVDA",
}


def gains_get(network: str, path: str, retries: int = 3) -> any:
    """GET request to Gains Network backend API."""
    base = GAINS_BACKENDS.get(network, GAINS_BACKENDS["arbitrum"])
    url = f"{base}{path}"

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(3)
                continue
            elif resp.status_code == 404:
                return None
            else:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                print(f"  [WARN] gTrade GET {path} returned {resp.status_code}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  [ERROR] gTrade GET {path}: {e}")
    return None


def fetch_trading_variables(network: str) -> dict:
    """
    Fetch core trading variables (pairs, fees, collaterals).
    Used to build pair index -> symbol mapping.
    """
    data = gains_get(network, "/trading-variables")
    return data if isinstance(data, dict) else {}


def fetch_open_trades_for_address(network: str, address: str) -> list:
    """
    Fetch open trades for a specific trader address.
    GET /open-trades/<address>
    """
    data = gains_get(network, f"/open-trades/{address}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("trades", data.get("openTrades", []))
    return []


def fetch_all_open_trades(network: str) -> list:
    """
    Fetch ALL open trades system-wide.
    GET /open-trades
    Note: May be deprecated or return limited data since Oct 2025.
    """
    data = gains_get(network, "/open-trades")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("trades", data.get("openTrades", []))
    return []


def fetch_trading_history(network: str, address: str) -> list:
    """
    Fetch personal trading history for a trader.
    GET /personal-trading-history-table/<address>
    """
    data = gains_get(network, f"/personal-trading-history-table/{address}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("trades", data.get("history", []))
    return []


def fetch_24h_history(network: str) -> list:
    """
    Fetch all trades from last 24 hours.
    GET /trading-history-24h
    Useful for discovering active traders.
    """
    data = gains_get(network, "/trading-history-24h")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("trades", [])
    return []


def build_pair_map(network: str) -> dict:
    """
    Build pair index -> symbol mapping from trading variables.
    Falls back to hardcoded PAIR_INDEX_MAP if API fails.
    """
    tv = fetch_trading_variables(network)
    pair_map = dict(PAIR_INDEX_MAP)  # Start with hardcoded

    if tv:
        pairs = tv.get("pairs", tv.get("pairsData", []))
        if isinstance(pairs, list):
            for i, pair in enumerate(pairs):
                if isinstance(pair, dict):
                    name = pair.get("from", "") + pair.get("to", "")
                    if not name:
                        name = pair.get("name", pair.get("symbol", ""))
                    if name:
                        pair_map[i] = name.upper().replace("/", "").replace("-", "")
        elif isinstance(pairs, dict):
            for idx_str, pair in pairs.items():
                try:
                    idx = int(idx_str)
                except ValueError:
                    continue
                if isinstance(pair, dict):
                    name = pair.get("from", "") + pair.get("to", "")
                    if not name:
                        name = pair.get("name", "")
                    if name:
                        pair_map[idx] = name.upper().replace("/", "").replace("-", "")

    return pair_map


def discover_active_traders(network: str, min_trades: int = 3) -> list:
    """
    Discover active traders from 24h trading history.
    Returns list of (address, trade_count) tuples sorted by activity.
    """
    history = fetch_24h_history(network)
    if not history:
        return []

    # Count trades per address
    trader_counts = {}
    for trade in history:
        addr = trade.get("trader", trade.get("address", trade.get("user", "")))
        if addr:
            trader_counts[addr.lower()] = trader_counts.get(addr.lower(), 0) + 1

    # Filter by minimum activity and sort
    active = [(addr, count) for addr, count in trader_counts.items()
              if count >= min_trades]
    active.sort(key=lambda x: x[1], reverse=True)

    return active


def parse_trade(trade: dict, pair_map: dict) -> dict:
    """Parse a gTrade trade object into a normalized format."""
    # Extract pair index and look up symbol
    try:
        pair_index = int(trade.get("pairIndex", trade.get("pair", -1)))
    except (ValueError, TypeError):
        pair_index = -1

    symbol = pair_map.get(pair_index, f"PAIR_{pair_index}")

    # Direction: buy=True means LONG
    is_long = trade.get("buy", trade.get("long", trade.get("isLong", True)))
    if isinstance(is_long, str):
        is_long = is_long.lower() in ("true", "1", "long")
    direction = "LONG" if is_long else "SHORT"

    # Prices -- gTrade uses 1e10 precision for prices
    try:
        open_price = float(trade.get("openPrice", trade.get("entryPrice", 0)))
        if open_price > 1e8:  # Likely in 1e10 format
            open_price = open_price / 1e10
    except (ValueError, TypeError):
        open_price = 0

    # TP/SL
    try:
        tp_price = float(trade.get("tp", 0))
        if tp_price > 1e8:
            tp_price = tp_price / 1e10
    except (ValueError, TypeError):
        tp_price = 0

    try:
        sl_price = float(trade.get("sl", 0))
        if sl_price > 1e8:
            sl_price = sl_price / 1e10
    except (ValueError, TypeError):
        sl_price = 0

    # Position size (collateral * leverage)
    try:
        collateral = float(trade.get("collateral", trade.get("positionSizeDai", 0)))
        if collateral > 1e15:  # In wei
            collateral = collateral / 1e18
    except (ValueError, TypeError):
        collateral = 0

    try:
        leverage = float(trade.get("leverage", 1))
        if leverage > 1000:  # Likely in 1e3 format
            leverage = leverage / 1000
    except (ValueError, TypeError):
        leverage = 1.0

    # Trade index
    trade_index = trade.get("index", trade.get("tradeIndex", 0))
    trader = trade.get("trader", trade.get("address", trade.get("user", "")))

    return {
        "trader": trader,
        "pair_index": pair_index,
        "symbol": symbol,
        "direction": direction,
        "open_price": open_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "collateral": collateral,
        "leverage": min(leverage, 150),  # gTrade supports up to 150x
        "size_usd": collateral * leverage,
        "trade_index": trade_index,
    }


def analyze_trader_gains(network: str, address: str, label: str = "",
                         pair_map: dict = None) -> dict:
    """Analyze a gTrade trader's performance and open positions."""
    print(f"  [{network}] Analyzing {label or address[:12]}...", end=" ", flush=True)

    pair_map = pair_map or PAIR_INDEX_MAP

    # Get open trades
    time.sleep(RATE_LIMIT_SEC)
    open_trades_raw = fetch_open_trades_for_address(network, address)

    # Get trade history
    time.sleep(RATE_LIMIT_SEC)
    history_raw = fetch_trading_history(network, address)

    # Parse open trades
    open_trades = []
    for t in open_trades_raw:
        parsed = parse_trade(t, pair_map)
        if parsed["open_price"] > 0:
            open_trades.append(parsed)

    # Analyze history for win rate
    wins = 0
    losses = 0
    total_pnl = 0

    for t in history_raw:
        try:
            pnl = float(t.get("pnl", t.get("percentProfit", 0)))
            # If percentProfit, convert to approximate USD
            if "percentProfit" in t and "collateral" in t:
                collateral = float(t.get("collateral", 0))
                if collateral > 1e15:
                    collateral = collateral / 1e18
                pnl = collateral * pnl / 100
        except (ValueError, TypeError):
            continue

        if pnl > 0:
            wins += 1
            total_pnl += pnl
        elif pnl < 0:
            losses += 1
            total_pnl += pnl

    total_closed = wins + losses
    win_rate = wins / total_closed if total_closed > 0 else 0

    # Profit factor
    gross_profit = sum(
        float(t.get("pnl", 0)) for t in history_raw
        if float(t.get("pnl", 0)) > 0
    ) if history_raw else 0
    gross_loss = abs(sum(
        float(t.get("pnl", 0)) for t in history_raw
        if float(t.get("pnl", 0)) < 0
    )) if history_raw else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    # Edge score
    edge = 0
    if win_rate >= 0.60:
        edge += 20
    elif win_rate >= 0.50:
        edge += 10
    if total_closed >= 50:
        edge += 15
    elif total_closed >= 20:
        edge += 8
    if total_pnl > 5000:
        edge += 15
    elif total_pnl > 500:
        edge += 8

    qualified = (
        total_closed >= MIN_TRADES
        and win_rate >= MIN_WIN_RATE
        and len(open_trades) > 0
    )

    icon = "OK" if qualified else "SKIP"
    print(f"[{icon}] WR:{win_rate*100:.0f}% PnL:${total_pnl:,.0f} "
          f"Trades:{total_closed} Open:{len(open_trades)} Edge:{edge}")

    return {
        "address": address,
        "label": label,
        "network": network,
        "win_rate": round(win_rate, 4),
        "total_trades": total_closed,
        "wins": wins,
        "losses": losses,
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "edge_score": min(edge, 100),
        "open_trades": open_trades,
        "history_count": len(history_raw),
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "qualified": qualified,
    }


def generate_picks(profile: dict) -> list:
    """Convert a gTrade trader's open positions into audit-compatible picks."""
    picks = []
    addr = profile["address"]
    label = profile.get("label", addr[:12])
    network = profile.get("network", "arbitrum")
    edge = profile.get("edge_score", 30)
    wr = profile.get("win_rate", 0.5)
    pf = profile.get("profit_factor", 1.0)
    now = datetime.now(timezone.utc)

    for trade in profile.get("open_trades", []):
        symbol = trade.get("symbol", "")
        if not symbol or symbol.startswith("PAIR_"):
            continue

        direction = trade.get("direction", "LONG")
        entry = trade.get("open_price", 0)
        if entry <= 0:
            continue

        leverage = trade.get("leverage", 1)

        # Use trader's TP/SL if set, otherwise default
        tp = trade.get("tp_price", 0)
        sl = trade.get("sl_price", 0)

        if not tp or tp <= 0:
            tp_pct = 0.04
            tp = round(entry * (1 + tp_pct), 8) if direction == "LONG" else round(entry * (1 - tp_pct), 8)
        if not sl or sl <= 0:
            sl_pct = 0.025
            sl = round(entry * (1 - sl_pct), 8) if direction == "LONG" else round(entry * (1 + sl_pct), 8)

        confidence = round(min(0.95, 0.35 + edge / 200 + wr * 0.20), 3)

        # Determine category
        if any(fx in symbol for fx in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]):
            if "XAU" in symbol or "XAG" in symbol:
                category = "commodity"
            elif symbol.endswith("USDT") or symbol.endswith("USD"):
                # Check if it's crypto or forex
                crypto_bases = ["BTC", "ETH", "SOL", "LINK", "DOGE", "ADA", "AVAX",
                                "UNI", "AAVE", "DOT", "LTC", "XRP", "MATIC"]
                if any(symbol.startswith(c) for c in crypto_bases):
                    category = "crypto"
                else:
                    category = "forex"
            else:
                category = "forex"
        else:
            category = "crypto"

        safe_label = label[:16]
        pick_id = f"copy_gtrade_{network}_{safe_label}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"copy_gtrade_{network}_{safe_label}",
            "symbol": symbol,
            "category": category,
            "signal_type": "BUY" if direction == "LONG" else "SELL",
            "direction": direction,
            "entry_price": entry,
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": confidence,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "status": "OPEN",
            "hold_days": None,
            "allocation": 200.0,
            "position_sizing": "copy_trader",
            "risk_per_trade_pct": 0.025,
            "max_safe_leverage": min(leverage, 50),
            "forward_trades": profile.get("total_trades", 0),
            "forward_wr": wr,
            "forward_validated": wr >= MIN_WIN_RATE and profile.get("total_trades", 0) >= MIN_TRADES,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
            "reason": (f"gTrade {network} trader {safe_label} | WR:{wr*100:.0f}% "
                       f"PF:{pf:.1f} PnL:${profile.get('total_pnl',0):,.0f} "
                       f"Lev:{leverage:.0f}x Edge:{edge}"),
            "source_system": f"copy_trader_gtrade_{network}",
            "trader_address": addr,
            "trader_pnl": profile.get("total_pnl", 0),
            "network": network,
            "collateral": trade.get("collateral", 0),
            "leverage": leverage,
            "pair_index": trade.get("pair_index", -1),
            "timestamp": now.isoformat(),
        })

    return picks


def scan_gains(networks: list = None, max_traders_per_network: int = 15) -> tuple:
    """
    Main gTrade scan: discover active traders, analyze, generate picks.
    Returns (profiles, picks).
    """
    networks = networks or ["arbitrum"]

    print("=" * 70)
    print("  GAINS NETWORK (gTrade) COPY TRADER INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Networks: {', '.join(networks)}")
    print("=" * 70)

    all_profiles = []
    all_picks = []

    for network in networks:
        print(f"\n  --- {network.upper()} ---")
        base_url = GAINS_BACKENDS.get(network)
        if not base_url:
            print(f"  Unknown network: {network}")
            continue

        # Build pair map
        print("  Fetching trading variables...")
        pair_map = build_pair_map(network)
        print(f"  Pair map: {len(pair_map)} pairs indexed")

        # Discover active traders from 24h history
        print("  Discovering active traders from 24h history...")
        time.sleep(RATE_LIMIT_SEC)
        active_traders = discover_active_traders(network, min_trades=3)

        # Merge with seed wallets
        addresses = {}
        for addr, count in active_traders[:max_traders_per_network]:
            addresses[addr] = f"gtrade_{addr[:8]}"

        for addr, label in SEED_WALLETS.get(network, []):
            if addr.lower() not in addresses:
                addresses[addr.lower()] = label

        if not addresses:
            print(f"  No active traders found for {network}")
            # Try fetching all open trades as fallback
            print("  Trying /open-trades fallback...")
            time.sleep(RATE_LIMIT_SEC)
            all_open = fetch_all_open_trades(network)
            if all_open:
                trader_set = set()
                for t in all_open:
                    addr = t.get("trader", t.get("address", t.get("user", "")))
                    if addr:
                        trader_set.add(addr.lower())
                for addr in list(trader_set)[:max_traders_per_network]:
                    addresses[addr] = f"gtrade_{addr[:8]}"
                print(f"  Found {len(addresses)} traders with open positions")

        if not addresses:
            continue

        print(f"  Analyzing {len(addresses)} traders...")

        for addr, label in list(addresses.items())[:max_traders_per_network]:
            try:
                profile = analyze_trader_gains(network, addr, label, pair_map=pair_map)
                all_profiles.append(profile)

                if profile.get("qualified"):
                    picks = generate_picks(profile)
                    all_picks.extend(picks)
                    for pk in picks:
                        print(f"    -> {pk['direction']} {pk['symbol']} @ "
                              f"{pk['entry_price']:.4f} {pk['leverage']:.0f}x")

            except Exception as e:
                print(f"  [ERROR] {label}: {e}")

    print(f"\n{'='*70}")
    print(f"  GAINS NETWORK SCAN COMPLETE")
    print(f"  Analyzed: {len(all_profiles)} | Qualified: "
          f"{sum(1 for p in all_profiles if p.get('qualified'))} | Picks: {len(all_picks)}")
    print(f"{'='*70}\n")

    return all_profiles, all_picks


def save_gains_results(profiles: list, picks: list):
    """Save gTrade results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "gains_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "gains_network_gtrade",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "gains_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_gains()
    save_gains_results(profiles, picks)
    print(f"\nDone. {len(picks)} gTrade copy trader picks generated.")
