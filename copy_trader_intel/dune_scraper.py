#!/usr/bin/env python3
"""
Dune Analytics On-Chain Trader Intelligence Scraper
====================================================
Reads results from public Dune Analytics queries to extract trader
leaderboards, whale wallets, DEX market data, and smart money flows.

IMPORTANT: Free-tier Dune API can ONLY read results from existing
public queries (cannot create/execute custom SQL). We rely on popular
community queries that have recent cached execution results.

API Endpoint:
  GET https://api.dune.com/api/v1/query/{QUERY_ID}/results
  Headers: X-Dune-API-Key: <key>

Verified Working Queries (as of 2026-03-19):
  6233831 -- Top 50 Profitable Traders (wallet, PnL, ROI, trade_count)
  3141002 -- GMX V2 Overall Traders PnL (daily aggregate)
  1518036 -- GMX V2 Overall Traders PnL (90-day window)
  6288825 -- Hyperliquid market data (coin, price, volume, OI, funding)
  6602796 -- Hyperliquid HIP-3 / trade.xyz market data
  5717014 -- DEX traders per chain (daily active traders)
  6457591 -- Polymarket whale dominance distribution

Additional Query IDs to Probe (may return data if recently executed):
  1168810 -- Top Traders on GMX Ranked By PnL
  1227065 -- Top Weekly Traders on GMX by PnL
  1323032 -- Top Traders on GMX PnL (Avalanche)
  1655426 -- GMX Traders PnL (draft)
  1486328 -- TOP traders crypto sorted by PnL
  1414018 -- PnL 1 month top performers
  276845  -- Top 50 whales collection
  419620  -- Wallet Tracker

Rate Limit: Free tier = ~6 req/min. Sleep 10s between calls.

Requires: DUNE_API_KEY environment variable (Windows env var, powershell fallback).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DUNE_API_BASE = "https://api.dune.com/api/v1"

RATE_LIMIT_SEC = 10  # Free tier is strict: ~6 req/min

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/2.0 DuneScraper",
}

# ======================================================================
# Known Public Query IDs (verified or probed)
# ======================================================================

# Category: Trader Leaderboards (wallet-level PnL data)
TRADER_LEADERBOARD_QUERIES = {
    6233831: {
        "name": "Top 50 Profitable Traders",
        "description": "Polymarket/DEX top 50 traders ranked by realized PnL",
        "columns": ["wallet", "realized_pnl", "roi_percent", "trade_count",
                     "active_days", "trades_per_day", "capital_deployed",
                     "days_active", "last_trade"],
        "verified": True,
    },
    1486328: {
        "name": "TOP traders crypto sorted by PnL",
        "description": "Gains Network / perpetual protocol top traders",
        "columns": ["account", "pnl", "volume", "trades"],
        "verified": False,
    },
    1414018: {
        "name": "PnL general 1 month top performers",
        "description": "Monthly top performing wallets",
        "columns": ["account", "pnl", "roi"],
        "verified": False,
    },
    1168810: {
        "name": "Top Traders on GMX Ranked By PnL",
        "description": "GMX v1 trader leaderboard by PnL (Arbitrum)",
        "columns": ["account", "realisedPnl", "volume", "trades"],
        "verified": False,
    },
    1227065: {
        "name": "Top Weekly Traders on GMX by PnL",
        "description": "GMX weekly top traders",
        "columns": ["account", "pnl", "volume"],
        "verified": False,
    },
    1323032: {
        "name": "Top Traders on GMX PnL (Avalanche)",
        "description": "GMX Avalanche trader leaderboard",
        "columns": ["account", "pnl"],
        "verified": False,
    },
    1655426: {
        "name": "GMX Traders PnL (draft)",
        "description": "GMX trader PnL draft version",
        "columns": ["account", "pnl"],
        "verified": False,
    },
}

# Category: Protocol-level market data (aggregate, useful for context)
MARKET_DATA_QUERIES = {
    6288825: {
        "name": "Hyperliquid Market Data",
        "description": "Hyperliquid perps: coin, price, volume, OI, funding, leverage",
        "columns": ["dex_type", "coin", "mark_price", "volume_24h",
                     "oi_usd_notional", "max_leverage", "funding_rate_pct",
                     "open_interest"],
        "verified": True,
    },
    6602796: {
        "name": "Hyperliquid HIP-3 / trade.xyz Market Data",
        "description": "Hyperliquid ecosystem perps including trade.xyz",
        "columns": ["dex_type", "market", "coin", "pair", "oi_usd_notional",
                     "volume_24h", "max_leverage"],
        "verified": True,
    },
    3141002: {
        "name": "GMX V2 Overall Traders PnL",
        "description": "GMX V2 daily aggregate PnL (profit/loss over time)",
        "columns": ["time", "profit_pnl", "loss_pnl", "total_pnl",
                     "daily_pnl_format", "weekly_pnl_format"],
        "verified": True,
    },
    1518036: {
        "name": "GMX V2 Traders PnL (90-day)",
        "description": "GMX V2 aggregate PnL with 90-day window",
        "columns": ["time", "profit_pnl", "loss_pnl", "total_pnl",
                     "daily_pnl_format"],
        "verified": True,
    },
    5717014: {
        "name": "DEX Traders per Chain",
        "description": "Daily active DEX traders by chain (Ethereum, Arbitrum, etc.)",
        "columns": ["chain", "date", "transactions"],
        "verified": True,
    },
}

# Category: Whale/Smart Money
WHALE_QUERIES = {
    6457591: {
        "name": "Polymarket Whale Dominance Distribution",
        "description": "Whale dominance distribution across Polymarket markets",
        "columns": ["dominance_bucket", "market_count", "bucket_sort_key"],
        "verified": True,
    },
    276845: {
        "name": "Top 50 Whales Collection",
        "description": "Top 50 ETH whale wallets",
        "columns": ["wallet", "eth_balance"],
        "verified": False,
    },
    419620: {
        "name": "Wallet Tracker",
        "description": "General wallet activity tracker",
        "columns": ["address", "transactions"],
        "verified": False,
    },
}

# All queries combined, ordered by priority (trader leaderboards first)
ALL_QUERIES = {}
ALL_QUERIES.update(TRADER_LEADERBOARD_QUERIES)
ALL_QUERIES.update(MARKET_DATA_QUERIES)
ALL_QUERIES.update(WHALE_QUERIES)


# ======================================================================
# API Key Loading
# ======================================================================

def _get_dune_api_key() -> str:
    """
    Load DUNE_API_KEY from environment.
    Falls back to Windows User-level env var via powershell.
    """
    key = os.environ.get("DUNE_API_KEY", "")
    if key:
        return key.strip()

    # Windows powershell fallback
    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('DUNE_API_KEY', 'User')"],
                capture_output=True, text=True, timeout=5
            )
            key = result.stdout.strip()
            if key:
                return key
        except Exception:
            pass

    return ""


# ======================================================================
# API Request Helper
# ======================================================================

def dune_get_results(query_id: int, limit: int = 100, offset: int = 0,
                     retries: int = 2) -> dict:
    """
    Fetch results from a Dune Analytics public query.

    GET https://api.dune.com/api/v1/query/{QUERY_ID}/results
    Headers: X-Dune-API-Key: <key>

    Returns the full response dict, or {} on failure.
    Possible states: QUERY_STATE_COMPLETED, QUERY_STATE_FAILED,
                     QUERY_STATE_EXECUTING, QUERY_STATE_PENDING
    """
    api_key = _get_dune_api_key()
    if not api_key:
        print("  [ERROR] DUNE_API_KEY not set. Cannot query Dune Analytics.")
        return {}

    url = f"{DUNE_API_BASE}/query/{query_id}/results"
    params = {"limit": limit}
    if offset > 0:
        params["offset"] = offset

    headers = {
        **HEADERS,
        "X-Dune-API-Key": api_key,
    }

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "")

                if state == "QUERY_STATE_COMPLETED":
                    return data
                elif state == "QUERY_STATE_FAILED":
                    err = data.get("error", {})
                    msg = err.get("message", "unknown error") if isinstance(err, dict) else str(err)
                    print(f"    [WARN] Query {query_id} execution failed: {msg[:80]}")
                    return {}
                else:
                    print(f"    [INFO] Query {query_id} state: {state}")
                    return {}

            elif resp.status_code == 429:
                print(f"    [RATE] Query {query_id}: rate limited, waiting 30s...")
                time.sleep(30)
                continue
            elif resp.status_code == 404:
                # "Query not found or private" or "No execution found"
                return {}
            elif resp.status_code == 402:
                print(f"    [WARN] Query {query_id}: paid plan required")
                return {}
            elif resp.status_code == 412:
                # "Result already expired"
                return {}
            else:
                print(f"    [WARN] Query {query_id}: HTTP {resp.status_code}")
                if attempt < retries - 1:
                    time.sleep(5)
                continue

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                print(f"    [ERROR] Query {query_id}: {e}")

    return {}


def extract_rows(response: dict) -> list:
    """Extract rows from a Dune API response."""
    return response.get("result", {}).get("rows", [])


def extract_columns(response: dict) -> list:
    """Extract column names from a Dune API response."""
    return response.get("result", {}).get("metadata", {}).get("column_names", [])


def extract_row_count(response: dict) -> int:
    """Extract total row count from a Dune API response."""
    return response.get("result", {}).get("metadata", {}).get("total_row_count", 0)


# ======================================================================
# Data Parsers for Each Query Type
# ======================================================================

def parse_trader_leaderboard(rows: list, query_id: int) -> list:
    """
    Parse trader leaderboard rows into standardized trader profiles.
    Handles different column naming conventions across queries.
    """
    profiles = []

    for row in rows:
        # Wallet/account address
        wallet = (row.get("wallet") or row.get("account") or
                  row.get("address") or row.get("trader") or "")
        if not wallet:
            continue

        # PnL
        pnl = 0.0
        for field in ["realized_pnl", "realisedPnl", "pnl", "net_pnl",
                       "profit", "total_pnl", "realised_pnl"]:
            val = row.get(field)
            if val is not None:
                try:
                    pnl = float(val)
                    break
                except (ValueError, TypeError):
                    continue

        # ROI
        roi = 0.0
        for field in ["roi_percent", "roi", "return_pct", "roi_pct"]:
            val = row.get(field)
            if val is not None:
                try:
                    roi = float(val)
                    break
                except (ValueError, TypeError):
                    continue
        # Normalize: if roi is given as percentage (e.g. 718.1), convert to decimal
        if abs(roi) > 10:
            roi_decimal = roi / 100.0
        else:
            roi_decimal = roi

        # Trade count
        trade_count = 0
        for field in ["trade_count", "trades", "totalTrades", "num_trades"]:
            val = row.get(field)
            if val is not None:
                try:
                    trade_count = int(val)
                    break
                except (ValueError, TypeError):
                    continue

        # Capital deployed
        capital = 0.0
        for field in ["capital_deployed", "volume", "total_volume"]:
            val = row.get(field)
            if val is not None:
                try:
                    capital = float(val)
                    break
                except (ValueError, TypeError):
                    continue

        # Active days
        active_days = 0
        for field in ["active_days", "days_active"]:
            val = row.get(field)
            if val is not None:
                try:
                    active_days = int(val)
                    break
                except (ValueError, TypeError):
                    continue

        # Win rate (some queries include it)
        win_rate = 0.0
        for field in ["win_rate", "winRate", "win_ratio"]:
            val = row.get(field)
            if val is not None:
                try:
                    win_rate = float(val)
                    if win_rate > 1:
                        win_rate /= 100.0
                    break
                except (ValueError, TypeError):
                    continue

        # Last trade timestamp
        last_trade = row.get("last_trade", row.get("last_trade_time", ""))

        # Edge score: heuristic based on PnL, ROI, trades, active days
        edge = 0
        if pnl > 1_000_000:
            edge += 30
        elif pnl > 100_000:
            edge += 20
        elif pnl > 10_000:
            edge += 10
        elif pnl > 1_000:
            edge += 5

        if abs(roi_decimal) > 5:
            edge += 20
        elif abs(roi_decimal) > 1:
            edge += 10
        elif abs(roi_decimal) > 0.5:
            edge += 5

        if trade_count > 10000:
            edge += 15
        elif trade_count > 1000:
            edge += 10
        elif trade_count > 100:
            edge += 5

        if active_days > 300:
            edge += 10
        elif active_days > 100:
            edge += 5

        edge = min(edge, 100)

        profiles.append({
            "wallet": wallet,
            "realized_pnl": round(pnl, 2),
            "roi_percent": round(roi, 2),
            "roi_decimal": round(roi_decimal, 4),
            "trade_count": trade_count,
            "capital_deployed": round(capital, 2),
            "active_days": active_days,
            "win_rate": round(win_rate, 4),
            "last_trade": str(last_trade),
            "edge_score": edge,
            "source_query_id": query_id,
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        })

    return profiles


def parse_market_data(rows: list, query_id: int) -> list:
    """
    Parse Hyperliquid/GMX market data rows into standardized format.
    Used for market context enrichment (funding rates, OI, volume).
    """
    markets = []

    for row in rows:
        coin = row.get("coin", row.get("symbol", ""))
        if not coin:
            continue

        # Clean HTML from market field if present
        market = row.get("market", row.get("pair", ""))
        if "<a " in str(market):
            # Extract text from HTML link
            import re
            text_match = re.search(r">([^<]+)<", str(market))
            market = text_match.group(1) if text_match else market

        dex_type = row.get("dex_type", "unknown")

        mark_price = 0.0
        try:
            mark_price = float(row.get("mark_price", 0))
        except (ValueError, TypeError):
            pass

        volume_24h = 0.0
        try:
            volume_24h = float(row.get("volume_24h", 0))
        except (ValueError, TypeError):
            pass

        oi = 0.0
        try:
            oi = float(row.get("oi_usd_notional", row.get("open_interest", 0)))
        except (ValueError, TypeError):
            pass

        funding = 0.0
        try:
            funding = float(row.get("funding_rate_pct", 0))
        except (ValueError, TypeError):
            pass

        max_leverage = 0
        try:
            max_leverage = int(row.get("max_leverage", 0))
        except (ValueError, TypeError):
            pass

        markets.append({
            "coin": coin.upper(),
            "symbol": f"{coin.upper()}USDT" if "USD" not in coin.upper() else coin.upper(),
            "dex_type": dex_type,
            "market": market,
            "mark_price": mark_price,
            "volume_24h": round(volume_24h, 2),
            "open_interest_usd": round(oi, 2),
            "funding_rate_pct": round(funding, 8),
            "max_leverage": max_leverage,
            "source_query_id": query_id,
        })

    return markets


def parse_gmx_aggregate_pnl(rows: list, query_id: int) -> dict:
    """
    Parse GMX V2 aggregate PnL data.
    Returns a summary with recent trends.
    """
    if not rows:
        return {}

    # Sort by time descending (most recent first)
    rows_sorted = sorted(rows, key=lambda r: r.get("time", ""), reverse=True)
    latest = rows_sorted[0] if rows_sorted else {}

    daily_pnl = 0.0
    try:
        daily_pnl = float(latest.get("daily_pnl_format", 0))
    except (ValueError, TypeError):
        pass

    weekly_pnl = 0.0
    try:
        weekly_pnl = float(latest.get("weekly_pnl_format", 0))
    except (ValueError, TypeError):
        pass

    total_profit = 0.0
    try:
        total_profit = float(latest.get("total_profit_pnl", 0))
    except (ValueError, TypeError):
        pass

    total_loss = 0.0
    try:
        total_loss = float(latest.get("total_loss_pnl", 0))
    except (ValueError, TypeError):
        pass

    # Calculate recent trend (last 7 entries)
    recent_daily = []
    for r in rows_sorted[:7]:
        try:
            d = float(r.get("daily_pnl_format", 0))
            recent_daily.append(d)
        except (ValueError, TypeError):
            continue

    trend = "neutral"
    if recent_daily:
        positive_days = sum(1 for d in recent_daily if d > 0)
        if positive_days >= 5:
            trend = "bullish"
        elif positive_days <= 2:
            trend = "bearish"

    return {
        "latest_date": latest.get("time", ""),
        "daily_pnl_usd": round(daily_pnl, 2),
        "weekly_pnl_usd": round(weekly_pnl, 2),
        "total_trader_profit_usd": round(total_profit, 2),
        "total_trader_loss_usd": round(total_loss, 2),
        "recent_trend": trend,
        "data_points": len(rows),
        "source_query_id": query_id,
    }


# ======================================================================
# Pick Generation
# ======================================================================

def generate_picks_from_market_data(markets: list, gmx_context: dict = None) -> list:
    """
    Generate trading picks from Hyperliquid market data.

    Strategy: identify coins with high volume, high OI, and positive funding
    (indicating bullish momentum). Negative funding -> short opportunity.
    """
    picks = []
    now = datetime.now(timezone.utc)

    # Filter to significant markets
    significant = [m for m in markets
                   if m.get("volume_24h", 0) > 1_000_000
                   and m.get("open_interest_usd", 0) > 500_000
                   and m.get("mark_price", 0) > 0]

    # Sort by volume descending
    significant.sort(key=lambda m: m.get("volume_24h", 0), reverse=True)

    for market in significant[:20]:
        coin = market["coin"]
        symbol = market["symbol"]
        price = market["mark_price"]
        funding = market.get("funding_rate_pct", 0)
        volume = market.get("volume_24h", 0)
        oi = market.get("open_interest_usd", 0)
        dex_type = market.get("dex_type", "unknown")

        # Determine direction from funding rate
        # Positive funding = longs paying shorts (market bullish) -> go LONG
        # Negative funding = shorts paying longs (market bearish) -> go SHORT
        # Very high positive funding = overleveraged longs -> potential SHORT
        if funding > 0.01:
            # Extremely positive funding -> contrarian SHORT (funding rate carry)
            direction = "SHORT"
            signal = "SELL"
            reason_detail = f"extreme funding {funding*100:.4f}% (contrarian SHORT)"
            confidence_base = 0.55
        elif funding > 0:
            direction = "LONG"
            signal = "BUY"
            reason_detail = f"positive funding {funding*100:.4f}% (bullish momentum)"
            confidence_base = 0.60
        elif funding < -0.005:
            # Very negative funding -> contrarian LONG
            direction = "LONG"
            signal = "BUY"
            reason_detail = f"extreme neg funding {funding*100:.4f}% (contrarian LONG)"
            confidence_base = 0.55
        else:
            direction = "SHORT"
            signal = "SELL"
            reason_detail = f"negative funding {funding*100:.4f}% (bearish)"
            confidence_base = 0.58

        # Adjust confidence by volume/OI ratio
        vol_oi_ratio = volume / oi if oi > 0 else 0
        if vol_oi_ratio > 3:
            confidence_base += 0.05  # High turnover = active trading
        elif vol_oi_ratio < 0.5:
            confidence_base -= 0.05  # Low turnover = stale positions

        confidence = round(min(0.90, max(0.40, confidence_base)), 3)

        # TP/SL
        tp_pct = 0.04
        sl_pct = 0.025
        if direction == "LONG":
            tp = round(price * (1 + tp_pct), 8)
            sl = round(price * (1 - sl_pct), 8)
        else:
            tp = round(price * (1 - tp_pct), 8)
            sl = round(price * (1 + sl_pct), 8)

        safe_coin = coin.replace("/", "_").replace(" ", "_")[:12]
        pick_id = (f"dune_{dex_type.lower().replace('.','_')}_{safe_coin}::"
                   f"{symbol}::{now.strftime('%Y-%m-%d_%H%M')}")

        picks.append({
            "id": pick_id,
            "strategy": f"dune_{dex_type.lower().replace('.','_')}_{safe_coin}_funding",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal,
            "direction": direction,
            "entry_price": price,
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
            "position_sizing": "dune_analytics",
            "risk_per_trade_pct": 0.025,
            "max_safe_leverage": min(market.get("max_leverage", 10), 20),
            "forward_trades": 0,
            "forward_wr": 0,
            "forward_validated": False,
            "elite_score": int(confidence * 80),
            "elite_grade": "B" if confidence >= 0.60 else "C",
            "reason": (f"Dune {dex_type} | {coin} | {reason_detail} | "
                       f"Vol:${volume:,.0f} OI:${oi:,.0f}"),
            "source_system": "copy_trader_dune",
            "dex_type": dex_type,
            "funding_rate_pct": funding,
            "volume_24h": volume,
            "open_interest_usd": oi,
            "timestamp": now.isoformat(),
        })

    return picks


def generate_picks_from_traders(profiles: list) -> list:
    """
    Generate picks from trader leaderboard data.
    Since we only have wallet addresses and PnL (no open positions),
    we create "smart money tracker" signals noting these wallets are active.
    """
    picks = []
    now = datetime.now(timezone.utc)

    # Filter to recently active, profitable traders
    qualified = [p for p in profiles
                 if p.get("realized_pnl", 0) > 1000
                 and p.get("trade_count", 0) >= 10]

    # Sort by PnL descending
    qualified.sort(key=lambda p: p.get("realized_pnl", 0), reverse=True)

    for trader in qualified[:10]:
        wallet = trader["wallet"]
        pnl = trader["realized_pnl"]
        roi = trader.get("roi_decimal", 0)
        trades = trader.get("trade_count", 0)
        edge = trader.get("edge_score", 30)

        # We don't know their exact positions, so create a "follow this wallet" signal
        # The wallet address itself is the valuable intelligence
        confidence = round(min(0.85, 0.50 + edge / 200), 3)

        short_wallet = f"{wallet[:6]}...{wallet[-4:]}" if len(wallet) > 12 else wallet
        pick_id = f"dune_smart_money_{short_wallet}::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"dune_smart_money_{short_wallet}",
            "symbol": "WALLET_TRACKER",
            "category": "crypto",
            "signal_type": "WATCH",
            "direction": "LONG",
            "entry_price": 0,
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": 0,
            "stop_loss": 0,
            "confidence": confidence,
            "ml_score": confidence,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "status": "WATCHING",
            "hold_days": None,
            "allocation": 0,
            "position_sizing": "wallet_tracker",
            "risk_per_trade_pct": 0,
            "max_safe_leverage": 1,
            "forward_trades": trades,
            "forward_wr": trader.get("win_rate", 0),
            "forward_validated": trades >= 100 and pnl > 10000,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
            "reason": (f"Dune Smart Money | {short_wallet} | "
                       f"PnL:${pnl:,.0f} ROI:{roi*100:.0f}% "
                       f"Trades:{trades:,}"),
            "source_system": "copy_trader_dune",
            "trader_wallet": wallet,
            "trader_pnl": pnl,
            "trader_roi": roi,
            "trader_trades": trades,
            "trader_active_days": trader.get("active_days", 0),
            "last_trade": trader.get("last_trade", ""),
            "timestamp": now.isoformat(),
        })

    return picks


# ======================================================================
# Main Scanner
# ======================================================================

def scan_dune(max_market_picks: int = 15, include_unverified: bool = True) -> tuple:
    """
    Main Dune Analytics scan.

    Probes all known query IDs, extracts data from those with cached results,
    and generates trading picks.

    Returns (profiles_and_data, picks).

    Strategy:
    1. Try trader leaderboard queries -> wallet-level PnL data
    2. Try Hyperliquid market data -> funding rate signals
    3. Try GMX aggregate data -> market context
    4. Try whale/smart money queries -> wallet tracking
    """
    api_key = _get_dune_api_key()
    if not api_key:
        print("  [ERROR] DUNE_API_KEY not found. Set it as a Windows env var.")
        print("         Get a free API key at https://dune.com/settings/api")
        return {}, []

    print("=" * 70)
    print("  DUNE ANALYTICS ON-CHAIN INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Rate limit: {RATE_LIMIT_SEC}s between calls (free tier)")
    print("=" * 70)

    all_trader_profiles = []
    all_market_data = []
    gmx_context = {}
    all_picks = []
    queries_attempted = 0
    queries_succeeded = 0

    # -- Phase 1: Trader Leaderboard Queries --
    print("\n  --- Phase 1: Trader Leaderboards ---")
    for qid, info in TRADER_LEADERBOARD_QUERIES.items():
        if not include_unverified and not info.get("verified"):
            continue

        queries_attempted += 1
        print(f"  [{queries_attempted}] Query {qid}: {info['name']}...", end=" ", flush=True)

        resp = dune_get_results(qid, limit=50)
        rows = extract_rows(resp)

        if rows:
            queries_succeeded += 1
            profiles = parse_trader_leaderboard(rows, qid)
            all_trader_profiles.extend(profiles)
            print(f"OK ({len(rows)} rows, {len(profiles)} traders)")
        else:
            print("no data")

        time.sleep(RATE_LIMIT_SEC)

    # -- Phase 2: Market Data (Hyperliquid, etc.) --
    print("\n  --- Phase 2: Market Data (Hyperliquid/GMX) ---")
    for qid, info in MARKET_DATA_QUERIES.items():
        if not include_unverified and not info.get("verified"):
            continue

        queries_attempted += 1
        print(f"  [{queries_attempted}] Query {qid}: {info['name']}...", end=" ", flush=True)

        resp = dune_get_results(qid, limit=100)
        rows = extract_rows(resp)

        if rows:
            queries_succeeded += 1

            if "market_data" in info.get("description", "").lower() or \
               "hyperliquid" in info.get("name", "").lower():
                markets = parse_market_data(rows, qid)
                all_market_data.extend(markets)
                print(f"OK ({len(rows)} rows, {len(markets)} markets)")
            elif "gmx" in info.get("name", "").lower() and "aggregate" in info.get("description", "").lower():
                gmx_context = parse_gmx_aggregate_pnl(rows, qid)
                print(f"OK ({len(rows)} data points, trend:{gmx_context.get('recent_trend','?')})")
            elif "traders per chain" in info.get("name", "").lower():
                print(f"OK ({len(rows)} rows, chain activity data)")
            else:
                markets = parse_market_data(rows, qid)
                if markets:
                    all_market_data.extend(markets)
                print(f"OK ({len(rows)} rows)")
        else:
            print("no data")

        time.sleep(RATE_LIMIT_SEC)

    # -- Phase 3: Whale/Smart Money Queries --
    print("\n  --- Phase 3: Whale & Smart Money ---")
    for qid, info in WHALE_QUERIES.items():
        if not include_unverified and not info.get("verified"):
            continue

        queries_attempted += 1
        print(f"  [{queries_attempted}] Query {qid}: {info['name']}...", end=" ", flush=True)

        resp = dune_get_results(qid, limit=50)
        rows = extract_rows(resp)

        if rows:
            queries_succeeded += 1
            print(f"OK ({len(rows)} rows)")
        else:
            print("no data")

        time.sleep(RATE_LIMIT_SEC)

    # -- Phase 4: Generate Picks --
    print("\n  --- Phase 4: Generate Picks ---")

    # Picks from market data (funding rate signals)
    if all_market_data:
        # Deduplicate markets by coin+dex_type
        seen = set()
        unique_markets = []
        for m in all_market_data:
            key = f"{m['coin']}_{m['dex_type']}"
            if key not in seen:
                seen.add(key)
                unique_markets.append(m)

        market_picks = generate_picks_from_market_data(unique_markets, gmx_context)
        all_picks.extend(market_picks)
        print(f"  Market data picks: {len(market_picks)}")

    # Picks from trader leaderboard (wallet tracker signals)
    if all_trader_profiles:
        trader_picks = generate_picks_from_traders(all_trader_profiles)
        all_picks.extend(trader_picks)
        print(f"  Smart money tracker picks: {len(trader_picks)}")

    # -- Summary --
    print(f"\n{'=' * 70}")
    print(f"  DUNE ANALYTICS SCAN COMPLETE")
    print(f"  Queries attempted: {queries_attempted}")
    print(f"  Queries with data: {queries_succeeded}")
    print(f"  Trader profiles:   {len(all_trader_profiles)}")
    print(f"  Market data points:{len(all_market_data)}")
    print(f"  Total picks:       {len(all_picks)}")
    if gmx_context:
        print(f"  GMX V2 trend:      {gmx_context.get('recent_trend', 'unknown')}")
        print(f"    Daily PnL:       ${gmx_context.get('daily_pnl_usd', 0):,.0f}")
        print(f"    Weekly PnL:      ${gmx_context.get('weekly_pnl_usd', 0):,.0f}")
    print(f"{'=' * 70}\n")

    # Combine all data for profiles output
    all_data = {
        "trader_profiles": all_trader_profiles,
        "market_data": all_market_data,
        "gmx_context": gmx_context,
        "queries_attempted": queries_attempted,
        "queries_succeeded": queries_succeeded,
    }

    return all_data, all_picks


def save_dune_results(data, picks: list):
    """Save Dune results to data files.

    ``data`` is normally a dict from ``scan_dune`` but may be an empty list
    when the scan short-circuits (e.g. missing API key).  Normalise to dict
    before accessing any keys so callers never hit ``AttributeError``.
    """
    if not isinstance(data, dict):
        data = {}

    now_iso = datetime.now(timezone.utc).isoformat()

    # Save profiles/data
    profiles_path = DATA_DIR / "dune_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "dune_analytics",
            "trader_count": len(data.get("trader_profiles", [])),
            "market_data_count": len(data.get("market_data", [])),
            "queries_attempted": data.get("queries_attempted", 0),
            "queries_succeeded": data.get("queries_succeeded", 0),
            "trader_profiles": data.get("trader_profiles", []),
            "market_data": data.get("market_data", []),
            "gmx_context": data.get("gmx_context", {}),
        }, f, indent=2, default=str)
    print(f"  Saved data to {profiles_path}")

    # Save picks
    picks_path = DATA_DIR / "dune_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    data, picks = scan_dune()
    save_dune_results(data, picks)
    print(f"\nDone. {len(picks)} Dune Analytics picks generated.")
