#!/usr/bin/env python3
"""
Copin.io Aggregated DEX Trader Scraper & Pick Generator
========================================================
Scrapes Copin.io's aggregated trader data across 54+ perpetual DEXs
(GMX, dYdX, Kwenta, GNS, Hyperliquid, etc.), identifies top performers,
and generates picks in the standard active_picks.json format.

REQUIRES API KEY -- Set COPIN_API_KEY env var or in .env file.
Apply at https://docs.copin.io/features/developer

API Base: https://api.copin.io
Docs:     https://api-docs.copin.io/

Supported protocols: GMX, GMX_V2, KWENTA, POLYNOMIAL, DYDX, HYPERLIQUID,
                     GNS, GNS_POLY, LEVEL_ARB, MUX_ARB, HMX_ARB, VELA_ARB,
                     SYNTHETIX_V3, APOLLOX_BNB, and 40+ more.

Endpoints used:
  - GET  /leaderboards/page                         -- Top traders by PnL/volume
  - POST /public/:PROTOCOL/position/statistic/filter -- Trader stats across protocol
  - POST /:PROTOCOL/top-positions/opening            -- Currently open positions
  - POST /:PROTOCOL/position/filter                  -- Position history
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# -- Configuration --
COPIN_API_BASE = "https://api.copin.io"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Rate limit: be conservative
RATE_LIMIT_SEC = 0.6

# Protocols to scan (high-volume perp DEXs)
SCAN_PROTOCOLS = [
    "GMX_V2",
    "DYDX",
    "HYPERLIQUID",
    "GNS",
    "KWENTA",
    "POLYNOMIAL",
    "SYNTHETIX_V3",
    "MUX_ARB",
    "HMX_ARB",
    "LEVEL_ARB",
]

# Minimum criteria
MIN_TRADES = 15
MIN_WIN_RATE = 0.52
MIN_TOTAL_PNL = 200  # USD

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/1.0",
}


def _get_api_key() -> str:
    """Load Copin API key from env or .env file."""
    key = os.environ.get("COPIN_API_KEY", "")
    if key:
        return key
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("COPIN_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def copin_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """GET request to Copin API with auth header."""
    api_key = _get_api_key()
    headers = {**HEADERS}
    if api_key:
        headers["x-api-key"] = api_key
    url = f"{COPIN_API_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(3)
                continue
            elif resp.status_code in (401, 403):
                print(f"  [AUTH] Copin API key required/invalid for {path}")
                return {}
            else:
                print(f"  [WARN] Copin GET {path} returned {resp.status_code}")
                return {}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  [ERROR] Copin GET {path}: {e}")
    return {}


def copin_post(path: str, body: dict = None, retries: int = 3) -> dict:
    """POST request to Copin API with auth header."""
    api_key = _get_api_key()
    headers = {**HEADERS}
    if api_key:
        headers["x-api-key"] = api_key
    url = f"{COPIN_API_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=body or {}, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(3)
                continue
            elif resp.status_code in (401, 403):
                print(f"  [AUTH] Copin API key required/invalid for {path}")
                return {}
            else:
                print(f"  [WARN] Copin POST {path} returned {resp.status_code}")
                return {}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  [ERROR] Copin POST {path}: {e}")
    return {}


def fetch_leaderboard(protocol: str, period: str = "MONTH", limit: int = 20) -> list:
    """
    Fetch trader leaderboard for a given protocol.
    GET /leaderboards/page?protocol=X&statisticType=MONTH&limit=20
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    data = copin_get("/leaderboards/page", params={
        "protocol": protocol,
        "queryDate": now_ms,
        "statisticType": period,
        "limit": limit,
        "offset": 0,
        "sort_by": "totalPnl",
        "sort_type": "desc",
    })
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, list):
        return data
    return []


def fetch_trader_stats(protocol: str, account: str) -> dict:
    """
    Fetch detailed statistics for a trader.
    POST /public/:PROTOCOL/position/statistic/filter
    """
    data = copin_post(f"/public/{protocol}/position/statistic/filter", body={
        "accounts": [account],
    })
    if isinstance(data, dict) and "data" in data:
        traders = data["data"]
        if isinstance(traders, list) and len(traders) > 0:
            return traders[0]
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}


def fetch_open_positions(protocol: str, limit: int = 50) -> list:
    """
    Fetch currently open positions across the protocol.
    POST /:PROTOCOL/top-positions/opening
    """
    data = copin_post(f"/{protocol}/top-positions/opening", body={
        "limit": limit,
        "offset": 0,
        "sortBy": "size",
        "sortType": "desc",
    })
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, list):
        return data
    return []


def fetch_trader_positions(protocol: str, account: str, limit: int = 20) -> list:
    """
    Fetch position history for a trader.
    POST /:PROTOCOL/position/filter
    """
    data = copin_post(f"/{protocol}/position/filter", body={
        "account": account,
        "limit": limit,
        "offset": 0,
        "sortBy": "openBlockTime",
        "sortType": "desc",
    })
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, list):
        return data
    return []


def normalize_symbol(raw: str) -> str:
    """Normalize index token / pair to standard XXXUSDT format."""
    if not raw:
        return ""
    # Remove common suffixes/prefixes
    s = raw.upper().replace("-PERP", "").replace("_PERP", "")
    s = s.replace("-USD", "").replace("/USD", "").replace("_USD", "")
    s = s.replace("-USDT", "").replace("/USDT", "")
    s = s.replace("-", "").replace("/", "").replace(" ", "")
    # Ensure ends with USDT
    if not s.endswith("USDT"):
        s += "USDT"
    return s


def position_to_pick(pos: dict, protocol: str, trader_stats: dict = None) -> dict:
    """Convert a Copin position into an active_picks.json compatible pick."""
    now = datetime.now(timezone.utc)

    # Extract symbol
    raw_symbol = pos.get("indexToken", pos.get("pair", pos.get("market", "")))
    symbol = normalize_symbol(raw_symbol)
    if not symbol:
        return None

    # Direction
    is_long = pos.get("isLong", pos.get("side", "").upper() == "LONG")
    if isinstance(is_long, str):
        is_long = is_long.upper() in ("TRUE", "LONG", "1")
    direction = "LONG" if is_long else "SHORT"

    # Entry price
    try:
        entry_price = float(pos.get("averagePrice", pos.get("entryPrice", pos.get("openPrice", 0))))
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    # Size
    try:
        size_usd = float(pos.get("size", pos.get("collateral", 0)))
    except (ValueError, TypeError):
        size_usd = 0

    # Leverage
    try:
        leverage = float(pos.get("leverage", 1))
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 50)

    # Trader stats
    account = pos.get("account", pos.get("trader", "unknown"))
    wr = 0.5
    total_pnl = 0
    total_trades = 0
    if trader_stats:
        try:
            total_trades = int(trader_stats.get("totalTrade", 0))
            wins = int(trader_stats.get("totalWin", 0))
            wr = wins / total_trades if total_trades > 0 else 0.5
            total_pnl = float(trader_stats.get("totalPnl", trader_stats.get("totalRealisedPnl", 0)))
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # TP/SL: 4% TP, 2.5% SL
    tp_pct = 0.04
    sl_pct = 0.025
    if direction == "LONG":
        tp = round(entry_price * (1 + tp_pct), 8)
        sl = round(entry_price * (1 - sl_pct), 8)
    else:
        tp = round(entry_price * (1 - tp_pct), 8)
        sl = round(entry_price * (1 + sl_pct), 8)

    # Confidence
    confidence = round(min(0.95, 0.40 + wr * 0.30 + min(total_pnl, 50000) / 200000), 3)

    # Edge score
    edge = 0
    if wr >= 0.65:
        edge += 25
    elif wr >= 0.55:
        edge += 15
    elif wr >= 0.52:
        edge += 8
    if total_pnl > 10000:
        edge += 20
    elif total_pnl > 1000:
        edge += 10
    if total_trades >= 100:
        edge += 15
    elif total_trades >= 30:
        edge += 8

    safe_account = str(account)[:16]
    pick_id = f"copin_{protocol.lower()}_{safe_account}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"copin_{protocol.lower()}_{safe_account}",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": entry_price,
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
        "max_safe_leverage": leverage,
        "forward_trades": total_trades,
        "forward_wr": round(wr, 4),
        "forward_validated": wr >= MIN_WIN_RATE and total_trades >= MIN_TRADES,
        "elite_score": min(edge, 100),
        "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
        "reason": (f"Copin {protocol} trader {safe_account} | "
                   f"WR:{wr*100:.0f}% PnL:${total_pnl:,.0f} Trades:{total_trades}"),
        "source_system": "copy_trader_copin",
        "source_protocol": protocol,
        "trader_address": str(account),
        "trader_pnl": round(total_pnl, 2),
        "size_usd": round(size_usd, 2),
        "leverage": leverage,
        "timestamp": now.isoformat(),
    }


def scan_copin(protocols: list = None, max_per_protocol: int = 10) -> tuple:
    """
    Main scan: fetch leaderboards across protocols, get positions, generate picks.
    Returns (all_profiles, all_picks).
    """
    protocols = protocols or SCAN_PROTOCOLS
    print("=" * 70)
    print("  COPIN.IO AGGREGATED DEX TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Protocols: {', '.join(protocols)}")
    print("=" * 70)

    api_key = _get_api_key()
    if not api_key:
        print("  [WARN] No COPIN_API_KEY set. Some endpoints may require auth.")
        print("  Set COPIN_API_KEY env var or add to copy_trader_intel/.env")

    all_profiles = []
    all_picks = []

    for protocol in protocols:
        print(f"\n  --- {protocol} ---")
        time.sleep(RATE_LIMIT_SEC)

        # Step 1: Get leaderboard
        lb = fetch_leaderboard(protocol, limit=max_per_protocol)
        if not lb:
            print(f"  No leaderboard data for {protocol}")
            continue
        print(f"  Leaderboard: {len(lb)} traders")

        # Step 2: For each top trader, get stats and positions
        for i, trader in enumerate(lb[:max_per_protocol]):
            account = trader.get("account", "")
            if not account:
                continue

            total_pnl = float(trader.get("totalPnl", 0))
            total_trades = int(trader.get("totalTrade", 0))
            wins = int(trader.get("totalWin", 0))
            wr = wins / total_trades if total_trades > 0 else 0

            # Filter by minimum criteria
            if total_trades < MIN_TRADES or wr < MIN_WIN_RATE or total_pnl < MIN_TOTAL_PNL:
                continue

            print(f"  [{i+1}] {account[:12]}... WR:{wr*100:.0f}% "
                  f"PnL:${total_pnl:,.0f} Trades:{total_trades}", end=" ")

            profile = {
                "account": account,
                "protocol": protocol,
                "totalPnl": round(total_pnl, 2),
                "totalTrade": total_trades,
                "totalWin": wins,
                "totalLose": int(trader.get("totalLose", 0)),
                "win_rate": round(wr, 4),
                "totalVolume": float(trader.get("totalVolume", 0)),
                "ranking": trader.get("ranking", 0),
                "analysis_time": datetime.now(timezone.utc).isoformat(),
            }
            all_profiles.append(profile)

            # Get this trader's recent positions
            time.sleep(RATE_LIMIT_SEC)
            positions = fetch_trader_positions(protocol, account, limit=10)

            # Filter for open positions only
            open_positions = [p for p in positions
                              if not p.get("closeBlockTime") and not p.get("closedAt")]

            if not open_positions:
                print("-- no open positions")
                continue

            picks_count = 0
            for pos in open_positions:
                pick = position_to_pick(pos, protocol, trader_stats=trader)
                if pick:
                    all_picks.append(pick)
                    picks_count += 1

            print(f"-> {picks_count} picks")

    print(f"\n{'='*70}")
    print(f"  COPIN SCAN COMPLETE")
    print(f"  Protocols scanned: {len(protocols)}")
    print(f"  Qualified traders: {len(all_profiles)}")
    print(f"  Picks generated: {len(all_picks)}")
    print(f"{'='*70}\n")

    return all_profiles, all_picks


def save_copin_results(profiles: list, picks: list):
    """Save Copin results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "copin_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "copin.io",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "copin_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_copin()
    save_copin_results(profiles, picks)
    print(f"\nDone. {len(picks)} Copin copy trader picks generated.")
