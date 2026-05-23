#!/usr/bin/env python3
"""
DEX On-Chain Trader Scraper & Pick Generator
=============================================
Tracks top traders on decentralized perpetual exchanges via public APIs
and subgraphs. No API key needed for most sources.

Sources:
  1. Copin.io -- Aggregated DEX copy-trading (dYdX, GMX, Kwenta, etc.)
  2. dYdX v4 -- Cosmos-based, indexer API
  3. GMX -- Arbitrum, via TheGraph subgraph

Rate limit: 500ms between calls.
"""

import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ═══════════════════════════════════════════════════════════════
# COPIN.IO -- Aggregated DEX Trader Intelligence
# ═══════════════════════════════════════════════════════════════

COPIN_API = "https://api.copin.io"
COPIN_MIRRORS = [
    "https://api.copin.io",
]

# Supported protocols on Copin
COPIN_PROTOCOLS = [
    "GMX_V2",
    "KWENTA",
    "POLYNOMIAL",
    "DYDX",
    "HYPERLIQUID",
    "GNS_POLY",
    "MUX",
    "LEVEL_ARB",
]


def copin_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """GET request to Copin.io API."""
    for mirror in COPIN_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    break
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def copin_post(path: str, body: dict = None, retries: int = 3) -> dict:
    """POST request to Copin.io API."""
    for mirror in COPIN_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.post(url, json=body or {}, headers={
                    **HEADERS,
                    "Content-Type": "application/json",
                }, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    break
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def fetch_copin_leaderboard(protocol: str = "GMX_V2", limit: int = 20) -> list:
    """Fetch top traders from Copin.io for a given protocol."""
    # Try the top traders endpoint
    data = copin_get(f"/public/traders/top", params={
        "protocol": protocol,
        "limit": str(limit),
        "sortBy": "pnl",
        "timeRange": "D90",
    })

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("traders", []))

    # Fallback: try explorer endpoint
    data = copin_post("/public/traders/filter", body={
        "protocol": protocol,
        "sortBy": "pnl",
        "sortOrder": "desc",
        "limit": limit,
        "offset": 0,
        "ranges": {
            "minPnl": 1000,
            "minWinRate": 50,
            "minTrades": 20,
        },
    })

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("traders", []))
    return []


def fetch_copin_positions(account: str, protocol: str = "GMX_V2") -> list:
    """Fetch open positions for a trader on Copin."""
    data = copin_get(f"/public/position/open", params={
        "account": account,
        "protocol": protocol,
    })
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("positions", []))
    return []


def scan_copin_traders(max_per_protocol: int = 10) -> tuple:
    """Scan Copin.io across multiple DEX protocols."""
    print("\n--- COPIN.IO DEX AGGREGATOR ---")

    all_profiles = []
    all_picks = []

    for protocol in COPIN_PROTOCOLS:
        print(f"  Protocol: {protocol}")
        traders = fetch_copin_leaderboard(protocol, limit=max_per_protocol)
        time.sleep(RATE_LIMIT_SEC)

        if not traders:
            print(f"    No traders found")
            continue

        print(f"    Found {len(traders)} traders")

        for trader in traders[:max_per_protocol]:
            account = trader.get("account", trader.get("address", ""))
            if not account:
                continue

            try:
                pnl = float(trader.get("pnl", trader.get("totalPnl", 0)))
                win_rate = float(trader.get("winRate", trader.get("winRatio", 0)))
                if win_rate > 1:
                    win_rate = win_rate / 100.0
                total_trades = int(trader.get("totalTrade", trader.get("totalOrders", 0)))
            except (ValueError, TypeError):
                continue

            # Filter: must have edge
            if total_trades < 10 or win_rate < 0.50 or pnl < 500:
                continue

            profile = {
                "account": account,
                "protocol": protocol,
                "pnl": round(pnl, 2),
                "win_rate": round(win_rate, 4),
                "total_trades": total_trades,
                "analysis_time": datetime.now(timezone.utc).isoformat(),
            }
            all_profiles.append(profile)

            # Get positions
            positions = fetch_copin_positions(account, protocol)
            time.sleep(RATE_LIMIT_SEC)

            if not positions:
                continue

            for pos in positions:
                pick = copin_position_to_pick(pos, trader, protocol)
                if pick:
                    all_picks.append(pick)

        print(f"    Qualified: {len([p for p in all_profiles if p['protocol'] == protocol])}")

    return all_profiles, all_picks


def copin_position_to_pick(position: dict, trader: dict, protocol: str) -> dict:
    """Convert a Copin position to pick format."""
    symbol = position.get("indexToken", position.get("pair", position.get("symbol", "")))
    if not symbol:
        return None

    # Normalize symbol
    symbol = symbol.upper().replace("-", "").replace("_", "")
    if not symbol.endswith("USDT") and not symbol.endswith("USD"):
        symbol = symbol + "USDT"

    is_long = position.get("isLong", position.get("side", "").lower() == "long")
    direction = "LONG" if is_long else "SHORT"

    try:
        entry_price = float(position.get("averagePrice", position.get("entryPrice", 0)))
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    try:
        leverage = float(position.get("leverage", 1))
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 50)

    try:
        win_rate = float(trader.get("winRate", trader.get("winRatio", 0)))
        if win_rate > 1:
            win_rate = win_rate / 100.0
    except (ValueError, TypeError):
        win_rate = 0

    try:
        pnl = float(trader.get("pnl", 0))
    except (ValueError, TypeError):
        pnl = 0

    account = trader.get("account", trader.get("address", ""))[:10]
    confidence = round(min(0.95, 0.60 + win_rate * 0.25), 3)

    if direction == "LONG":
        tp_price = round(entry_price * 1.04, 8)
        sl_price = round(entry_price * 0.975, 8)
    else:
        tp_price = round(entry_price * 0.96, 8)
        sl_price = round(entry_price * 1.025, 8)

    try:
        upl = float(position.get("unrealisedPnl", position.get("pnl", 0)))
    except (ValueError, TypeError):
        upl = 0

    now = datetime.now(timezone.utc)
    pick_id = f"dex_{protocol}_{account}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"dex_{protocol.lower()}_{account}",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": entry_price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 150.0,
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.025,
        "max_safe_leverage": leverage,
        "forward_trades": int(trader.get("totalTrade", 0)),
        "forward_wr": win_rate,
        "forward_validated": win_rate >= 0.50,
        "elite_score": min(100, int(win_rate * 50 + min(pnl / 1000, 30))),
        "elite_grade": "A" if win_rate >= 0.60 else "B" if win_rate >= 0.50 else "C",
        "reason": (f"DEX {protocol} trader {account}... | "
                   f"WR:{win_rate*100:.0f}% PnL:${pnl:,.0f}"),
        "source_system": f"copy_trader_dex_{protocol.lower()}",
        "trader_address": trader.get("account", ""),
        "protocol": protocol,
        "unrealized_pnl": round(upl, 2),
        "timestamp": now.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# dYdX v4 -- Direct Indexer API
# ═══════════════════════════════════════════════════════════════

DYDX_INDEXER = "https://indexer.dydx.trade/v4"


def fetch_dydx_leaderboard(limit: int = 20) -> list:
    """Fetch dYdX v4 leaderboard via indexer."""
    print("\n--- dYdX v4 LEADERBOARD ---")
    try:
        resp = requests.get(f"{DYDX_INDEXER}/leaderboard/pnl", params={
            "period": "NINETY_DAYS",
            "limit": str(limit),
        }, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            traders = data if isinstance(data, list) else data.get("users", data.get("results", []))
            print(f"  Found {len(traders)} dYdX traders")
            return traders
    except Exception as e:
        print(f"  [WARN] dYdX indexer failed: {e}")
    return []


def fetch_dydx_positions(address: str) -> list:
    """Fetch open positions for a dYdX address."""
    try:
        resp = requests.get(f"{DYDX_INDEXER}/addresses/{address}/perpetualPositions",
                           params={"status": "OPEN"}, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("positions", data if isinstance(data, list) else [])
    except Exception as e:
        print(f"  [WARN] dYdX positions failed: {e}")
    return []


def scan_dydx_traders(max_traders: int = 15) -> tuple:
    """Scan dYdX v4 top traders."""
    traders = fetch_dydx_leaderboard(limit=30)
    all_profiles = []
    all_picks = []

    for i, trader in enumerate(traders[:max_traders]):
        address = trader.get("address", trader.get("subaccountId", ""))
        if not address:
            continue

        # Extract subaccount address (may include subaccount number)
        base_addr = address.split("/")[0] if "/" in address else address

        try:
            pnl = float(trader.get("pnl", trader.get("totalPnl", 0)))
        except (ValueError, TypeError):
            pnl = 0

        print(f"  [{i+1}] {base_addr[:12]}... PnL:${pnl:,.0f} ", end="", flush=True)

        positions = fetch_dydx_positions(base_addr)
        time.sleep(RATE_LIMIT_SEC)

        profile = {
            "address": base_addr,
            "pnl": round(pnl, 2),
            "protocol": "DYDX_V4",
            "open_positions": len(positions),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if not positions:
            print("no positions")
            continue

        for pos in positions:
            symbol = pos.get("market", pos.get("ticker", ""))
            if not symbol:
                continue

            # Convert dYdX market format (BTC-USD -> BTCUSDT)
            symbol = symbol.replace("-USD", "USDT").replace("-", "")

            try:
                entry_price = float(pos.get("entryPrice", 0))
                size = float(pos.get("size", 0))
            except (ValueError, TypeError):
                continue
            if entry_price <= 0:
                continue

            direction = "LONG" if size > 0 else "SHORT"
            now = datetime.now(timezone.utc)

            confidence = round(min(0.90, 0.55 + min(pnl / 100000, 0.20)), 3)
            if direction == "LONG":
                tp = round(entry_price * 1.04, 8)
                sl = round(entry_price * 0.975, 8)
            else:
                tp = round(entry_price * 0.96, 8)
                sl = round(entry_price * 1.025, 8)

            try:
                upl = float(pos.get("unrealizedPnl", 0))
            except (ValueError, TypeError):
                upl = 0

            pick_id = f"dydx_{base_addr[:8]}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"
            all_picks.append({
                "id": pick_id,
                "strategy": f"dex_dydx_{base_addr[:8]}",
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
                "allocation": 150.0,
                "position_sizing": "copy_trader",
                "risk_per_trade_pct": 0.025,
                "max_safe_leverage": 1.0,
                "forward_trades": 0,
                "forward_wr": 0,
                "forward_validated": False,
                "elite_score": min(100, int(min(pnl / 500, 50) + 20)),
                "elite_grade": "B",
                "reason": f"dYdX v4 top PnL trader {base_addr[:12]}... | PnL:${pnl:,.0f}",
                "source_system": "copy_trader_dex_dydx",
                "trader_address": base_addr,
                "protocol": "DYDX_V4",
                "unrealized_pnl": round(upl, 2),
                "timestamp": now.isoformat(),
            })

        print(f"{len(positions)} positions")

    return all_profiles, all_picks


# ═══════════════════════════════════════════════════════════════
# GMX v2 -- TheGraph Subgraph
# ═══════════════════════════════════════════════════════════════

GMX_SUBGRAPH = "https://subgraph.satsuma-prod.com/3b2ced13c8d9/gmx/synthetics-arbitrum-stats/api"
GMX_SUBGRAPH_FALLBACK = "https://api.thegraph.com/subgraphs/name/gmx-io/gmx-stats"


def fetch_gmx_top_traders(limit: int = 20) -> list:
    """Query GMX subgraph for top PnL traders."""
    print("\n--- GMX v2 (Arbitrum) ---")

    query = """
    {
      tradingStats(
        first: %d,
        orderBy: realizedPnl,
        orderDirection: desc,
        where: { period: "total", realizedPnl_gt: "0" }
      ) {
        account
        realizedPnl
        volume
        closedCount
        losses
        wins
      }
    }
    """ % limit

    for url in [GMX_SUBGRAPH, GMX_SUBGRAPH_FALLBACK]:
        try:
            resp = requests.post(url, json={"query": query}, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                traders = data.get("data", {}).get("tradingStats", [])
                if traders:
                    print(f"  Found {len(traders)} GMX traders")
                    return traders
        except Exception as e:
            print(f"  [WARN] GMX subgraph failed ({url[:30]}...): {e}")
            continue

    print("  [WARN] GMX subgraph unavailable")
    return []


def scan_gmx_traders(max_traders: int = 15) -> tuple:
    """Scan GMX top traders via subgraph."""
    traders = fetch_gmx_top_traders(limit=30)
    all_profiles = []
    all_picks = []

    for i, trader in enumerate(traders[:max_traders]):
        account = trader.get("account", "")
        if not account:
            continue

        try:
            pnl_raw = float(trader.get("realizedPnl", 0))
            pnl = pnl_raw / 1e30 if pnl_raw > 1e20 else pnl_raw  # GMX uses 30-decimal precision
            wins = int(trader.get("wins", 0))
            losses = int(trader.get("losses", 0))
            closed = int(trader.get("closedCount", wins + losses))
        except (ValueError, TypeError):
            continue

        total = wins + losses if (wins + losses) > 0 else max(closed, 1)
        win_rate = wins / total if total > 0 else 0

        if total < 10 or win_rate < 0.45:
            continue

        profile = {
            "account": account,
            "pnl": round(pnl, 2),
            "win_rate": round(win_rate, 4),
            "wins": wins,
            "losses": losses,
            "total_trades": total,
            "protocol": "GMX_V2",
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)
        # Note: GMX subgraph doesn't expose open positions directly
        # We track these traders for consensus with other sources

    print(f"  GMX qualified traders: {len(all_profiles)}")
    return all_profiles, all_picks


# ═══════════════════════════════════════════════════════════════
# MAIN SCAN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

def scan_all_dex(max_per_source: int = 10) -> tuple:
    """Run all DEX scrapers and consolidate results.

    Uses dedicated scraper modules when available (copin_scraper, dydx_scraper,
    gmx_scraper, gains_scraper) with fallback to inline implementations above.
    """
    print("=" * 70)
    print("  DEX ON-CHAIN TRADER INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Sources: Copin.io | dYdX v4 | GMX v2 | Gains Network")
    print("=" * 70)

    all_profiles = []
    all_picks = []

    # 1. Copin.io (aggregated DEX data) -- try dedicated scraper first
    try:
        from copin_scraper import scan_copin, save_copin_results
        copin_profiles, copin_picks = scan_copin(max_per_protocol=max_per_source)
        save_copin_results(copin_profiles, copin_picks)
        all_profiles.extend(copin_profiles)
        all_picks.extend(copin_picks)
        print(f"  Copin.io: {len(copin_profiles)} traders, {len(copin_picks)} picks")
    except ImportError:
        # Fallback to inline implementation
        try:
            copin_profiles, copin_picks = scan_copin_traders(max_per_protocol=max_per_source)
            all_profiles.extend(copin_profiles)
            all_picks.extend(copin_picks)
        except Exception as e:
            print(f"  [ERROR] Copin scan failed: {e}")
    except Exception as e:
        print(f"  [ERROR] Copin scan failed: {e}")

    # 2. dYdX v4 -- try dedicated scraper first
    try:
        from dydx_scraper import scan_dydx, save_dydx_results
        dydx_profiles, dydx_picks = scan_dydx(max_traders=max_per_source)
        save_dydx_results(dydx_profiles, dydx_picks)
        all_profiles.extend(dydx_profiles)
        all_picks.extend(dydx_picks)
        print(f"  dYdX v4: {len(dydx_profiles)} traders, {len(dydx_picks)} picks")
    except ImportError:
        try:
            dydx_profiles, dydx_picks = scan_dydx_traders(max_traders=max_per_source)
            all_profiles.extend(dydx_profiles)
            all_picks.extend(dydx_picks)
        except Exception as e:
            print(f"  [ERROR] dYdX scan failed: {e}")
    except Exception as e:
        print(f"  [ERROR] dYdX scan failed: {e}")

    # 3. GMX v2 -- try dedicated scraper first
    try:
        from gmx_scraper import scan_gmx, save_gmx_results
        gmx_profiles, gmx_picks = scan_gmx(max_per_chain=max_per_source)
        save_gmx_results(gmx_profiles, gmx_picks)
        all_profiles.extend(gmx_profiles)
        all_picks.extend(gmx_picks)
        print(f"  GMX v2: {len(gmx_profiles)} traders, {len(gmx_picks)} picks")
    except ImportError:
        try:
            gmx_profiles, gmx_picks = scan_gmx_traders(max_traders=max_per_source)
            all_profiles.extend(gmx_profiles)
            all_picks.extend(gmx_picks)
        except Exception as e:
            print(f"  [ERROR] GMX scan failed: {e}")
    except Exception as e:
        print(f"  [ERROR] GMX scan failed: {e}")

    # 4. Gains Network (gTrade) -- NEW
    try:
        from gains_scraper import scan_gains, save_gains_results
        gains_profiles, gains_picks = scan_gains(max_traders_per_network=max_per_source)
        save_gains_results(gains_profiles, gains_picks)
        all_profiles.extend(gains_profiles)
        all_picks.extend(gains_picks)
        print(f"  Gains Network: {len(gains_profiles)} traders, {len(gains_picks)} picks")
    except ImportError:
        print("  [WARN] gains_scraper.py not found -- skipping Gains Network")
    except Exception as e:
        print(f"  [ERROR] Gains Network scan failed: {e}")

    # Save consolidated results
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "dex_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "dex_on_chain",
            "total_profiles": len(all_profiles),
            "total_picks": len(all_picks),
            "protocols": list(set(
                p.get("protocol", p.get("chain", p.get("network", "unknown")))
                for p in all_profiles
            )),
            "profiles": all_profiles,
        }, f, indent=2, default=str)

    picks_path = DATA_DIR / "dex_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(all_picks, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  DEX SCAN COMPLETE")
    print(f"  Profiles: {len(all_profiles)} | Picks: {len(all_picks)}")
    print(f"{'='*70}\n")

    return all_profiles, all_picks


if __name__ == "__main__":
    scan_all_dex(max_per_source=10)
