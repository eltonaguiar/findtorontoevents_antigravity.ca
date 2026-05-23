#!/usr/bin/env python3
"""
GMX v2 (Arbitrum/Avalanche) Top Trader Scraper & Pick Generator
================================================================
Tracks top traders on GMX v2 Synthetics via their Subsquid GraphQL API
and REST endpoints.

NO API KEY NEEDED -- GMX APIs are fully public and free.

Subsquid GraphQL Endpoints (VERIFIED WORKING 2026-03-19):
  Arbitrum: https://gmx.squids.live/gmx-synthetics-arbitrum:prod/api/graphql
  Avalanche: https://gmx.squids.live/gmx-synthetics-avalanche:prod/api/graphql

REST API:
  Arbitrum: https://arbitrum-api.gmxinfra.io
  Avalanche: https://avalanche-api.gmxinfra.io

Schema notes (Subsquid, NOT TheGraph):
  - AccountStat: id (=account address), wins, losses, realizedPnl, volume, closedCount
  - Position: account, market, isLong, sizeInUsd, entryPrice, leverage, openedAt, isSnapshot
  - TradeAction: account, eventName, marketAddress, sizeDeltaUsd, isLong, executionPrice, timestamp
  - Market: id (=market token address), indexToken, longToken, shortToken
  - Use orderBy: fieldName_DESC/ASC (Subsquid syntax), NOT orderBy/orderDirection

Approach:
  1. Query AccountStat for top PnL accounts
  2. Query Position (isSnapshot=false, sizeInUsd>0) for each account's open positions
  3. Use REST /markets for address-to-symbol mapping
  4. Generate picks from open positions of qualified traders
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# Fix Windows charmap encoding
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- Configuration --
GMX_SUBSQUID = {
    "arbitrum": "https://gmx.squids.live/gmx-synthetics-arbitrum:prod/api/graphql",
    "avalanche": "https://gmx.squids.live/gmx-synthetics-avalanche:prod/api/graphql",
}

GMX_REST = {
    "arbitrum": "https://arbitrum-api.gmxinfra.io",
    "avalanche": "https://avalanche-api.gmxinfra.io",
}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.5

# Minimum criteria
MIN_TRADES = 10
MIN_WIN_RATE = 0.50
MIN_TOTAL_PNL = 100  # USD

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/2.0",
}

# Known top GMX traders (from on-chain analysis, Copin leaderboards, Subsquid API)
# Verified via GMX Subsquid GraphQL API query (2026-03-19) + Copin/Bitcoinist articles
# PnL figures are lifetime realized PnL from AccountStat entity
SEED_WALLETS = {
    "arbitrum": [
        # --- Top PnL traders from Subsquid API (verified 2026-03-19) ---
        ("0x92812499fF2c040f93121Aab684680a6e603C4A7", "gmx_top1_10M_pnl"),      # WR:71% W:24 L:10 PnL:$10.4M
        ("0x08c788aFdACF6cf81180D2bBBE42A7434D0C7A92", "gmx_copin_11M_pnl"),      # WR:65% W:70 L:37 PnL:$7.5M (Copin top August)
        ("0x5C83942B7919db30634f9Bc9e0e72aD778852FC8", "gmx_top3_6M_pnl"),        # WR:64% W:43 L:24 PnL:$6.6M
        ("0x7Ab8C59Db7b959Bb8C3481d5b9836dfbc939AF21", "gmx_top4_6M_pnl"),        # WR:65% W:17 L:9 PnL:$6.6M
        ("0xbB3406CD37b3D4c1F0e35c948051060D23d7DED4", "gmx_90pct_wr_5M"),        # WR:90% W:268 L:29 PnL:$5.3M
        ("0xe4d31c2541A9cE596419879B1A46Ffc7cD202c62", "gmx_top6_4M_pnl"),        # WR:63% W:47 L:28 PnL:$4.9M
        ("0xE8d8bB57eDf69e4daf806Ba60BF2658C81eb91db", "gmx_high_vol_4M"),        # WR:56% W:181 L:140 PnL:$4.9M 321 trades
        ("0x4210Ebe4d47F7a183a8FeF5A7aa64f8eD918Df83", "gmx_87pct_wr_4M"),        # WR:88% W:7 L:1 PnL:$4.5M
        ("0x7B7b908c076B9784487180dE92E7161c2982734E", "gmx_80pct_wr_3M"),        # WR:80% W:4 L:1 PnL:$3.9M
        ("0xB6860393Ade5CD3766E47e0B031A0F4C33FD48a4", "gmx_100pct_wr_3M"),       # WR:100% W:42 L:0 PnL:$3.2M
        ("0x1ee7a73cb5B0B6b056d8138085b2009E6a6bEDF5", "gmx_70pct_230t_2M"),      # WR:70% W:160 L:70 PnL:$2.8M 230 trades
        ("0xF005093464E14cbacF0f9B9A371269FC118776DD", "gmx_81pct_wr_2M"),        # WR:81% W:13 L:3 PnL:$2.7M
        ("0x565729a615E191756b7b61E97D8E83238dd44925", "gmx_mega_vol_1019t"),     # WR:74% W:757 L:262 PnL:$2.0M 1019 trades
        ("0xAb3067C58811aDE7aA17B58808Db3b4c2E86f603", "gmx_top15_1M_pnl"),       # WR:62% W:15 L:9 PnL:$1.9M
        # --- Verified from Bitcoinist article (80% WR whale, ~$1.2M profit) ---
        ("0x324e265aee8575660094222ea2330234053487f7", "gmx_80pct_btcist_whale"),  # WR:80% 10 trades, $992K single ETH short
        # --- Verified from Copin blog Week 43 analysis ($1.1M PnL in 60d) ---
        ("0x160A8D28D63961297e51E4f1a0401bf4D27f5162", "gmx_copin_wk43_top1"),    # WR:70% PnL:$1.1M in 60d, max ROI 197%
        # --- Original seed wallets ---
        ("0x0e3167e5559e76993155b6b6896d5e39d3e57350", "gmx_arb_whale1"),
        ("0x5a504a024ab71a6e0f3b74f19290ee0e69049499", "gmx_arb_whale2"),
        ("0x8f42adbba1b16eaae3bb5754915e0d06059add75", "gmx_arb_whale3"),
    ],
    "avalanche": [],
}


def graphql_query(chain: str, query: str, variables: dict = None, retries: int = 3) -> dict:
    """Execute a GraphQL query against GMX Subsquid endpoint."""
    url = GMX_SUBSQUID.get(chain, GMX_SUBSQUID["arbitrum"])
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    err_msg = data['errors'][0].get('message', 'unknown')
                    print(f"  [GQL ERROR] {err_msg}")
                    return {}
                return data.get("data", {})
            elif resp.status_code == 429:
                time.sleep(3)
                continue
            else:
                print(f"  [WARN] GMX GraphQL returned {resp.status_code}")
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return {}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  [ERROR] GMX GraphQL: {e}")
    return {}


def gmx_rest_get(chain: str, path: str, retries: int = 3) -> dict:
    """GET request to GMX REST API."""
    base = GMX_REST.get(chain, GMX_REST["arbitrum"])
    url = f"{base}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(2)
                continue
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def fetch_top_accounts_by_pnl(chain: str, limit: int = 20) -> list:
    """
    Query AccountStat for top PnL accounts.
    Subsquid schema: AccountStat.id IS the account address.
    Fields: id, wins, losses, realizedPnl, volume, closedCount
    """
    query = """
    query TopAccounts($limit: Int!) {
        accountStats(
            orderBy: realizedPnl_DESC,
            limit: $limit
        ) {
            id
            wins
            losses
            realizedPnl
            volume
            closedCount
        }
    }
    """

    data = graphql_query(chain, query, variables={"limit": limit})
    return data.get("accountStats", [])


def fetch_open_positions(chain: str, account: str, limit: int = 20) -> list:
    """
    Fetch open positions for a specific account from the Position entity.
    isSnapshot=false filters out daily snapshots, sizeInUsd>0 = currently open.
    """
    query = """
    query OpenPositions($account: String!, $limit: Int!) {
        positions(
            limit: $limit,
            orderBy: sizeInUsd_DESC,
            where: {
                account_eq: $account,
                sizeInUsd_gt: "0",
                isSnapshot_eq: false
            }
        ) {
            id
            account
            market
            isLong
            sizeInUsd
            entryPrice
            collateralAmount
            leverage
            openedAt
            realizedPnl
            unrealizedPnl
        }
    }
    """

    data = graphql_query(chain, query, variables={
        "account": account,
        "limit": limit,
    })

    return data.get("positions", [])


def fetch_largest_open_positions(chain: str, limit: int = 50) -> list:
    """
    Fetch the largest open positions across all accounts.
    Used to discover active whale traders.
    """
    query = """
    query LargestPositions($limit: Int!) {
        positions(
            limit: $limit,
            orderBy: sizeInUsd_DESC,
            where: {
                sizeInUsd_gt: "0",
                isSnapshot_eq: false
            }
        ) {
            account
            market
            isLong
            sizeInUsd
            entryPrice
            leverage
            openedAt
        }
    }
    """

    data = graphql_query(chain, query, variables={"limit": limit})
    return data.get("positions", [])


def fetch_trade_actions(chain: str, account: str, limit: int = 50) -> list:
    """
    Fetch recent TradeActions for a specific account.
    TradeAction records open/close/liquidation events.
    """
    query = """
    query TradeActions($account: String!, $limit: Int!) {
        tradeActions(
            orderBy: timestamp_DESC,
            limit: $limit,
            where: { account_eq: $account }
        ) {
            id
            eventName
            account
            marketAddress
            timestamp
            transactionHash
            sizeDeltaUsd
            isLong
            executionPrice
            pnlUsd
        }
    }
    """

    data = graphql_query(chain, query, variables={
        "account": account,
        "limit": limit,
    })

    return data.get("tradeActions", [])


def build_market_map_rest(chain: str) -> dict:
    """
    Build mapping from market token address -> symbol using REST /markets.
    REST returns: name (e.g. "BTC/USD [WBTC.b-USDC]"), marketToken, indexToken, etc.
    """
    data = gmx_rest_get(chain, "/markets")
    mapping = {}

    markets = data if isinstance(data, list) else data.get("markets", [])
    for m in markets:
        market_token = m.get("marketToken", "")
        name = m.get("name", "")
        if market_token and name:
            # Extract base symbol from name like "BTC/USD [WBTC.b-USDC]"
            base = name.split("/")[0].strip() if "/" in name else name.split(" ")[0]
            if base and base != "SWAP-ONLY":
                mapping[market_token.lower()] = f"{base}USDT"

    return mapping


def build_market_map_gql(chain: str) -> dict:
    """
    Build market mapping from GraphQL Market entity.
    Market fields: id, indexToken, longToken, shortToken
    Maps market id -> indexToken address (need REST for symbol name).
    """
    query = """
    query Markets {
        markets(limit: 200) {
            id
            indexToken
            longToken
            shortToken
        }
    }
    """
    data = graphql_query(chain, query)
    markets = data.get("markets", [])
    # Returns address-to-address mapping; REST is better for symbol names
    return {m["id"].lower(): m.get("indexToken", "") for m in markets if m.get("id")}


def build_market_map(chain: str) -> dict:
    """Build market address -> symbol mapping. Prefers REST API."""
    print("  Fetching market info from REST API...")
    mapping = build_market_map_rest(chain)
    if mapping:
        print(f"  Market map: {len(mapping)} markets indexed")
        return mapping

    print("  REST failed, trying GraphQL markets...")
    gql_map = build_market_map_gql(chain)
    if gql_map:
        print(f"  GQL market map: {len(gql_map)} markets (address-only)")
    return gql_map


def parse_gmx_decimal(value, decimals: int = 30) -> float:
    """Parse GMX BigInt values (30 decimal places for USD, varies for prices)."""
    try:
        v = int(value) if isinstance(value, str) else value
        return v / (10 ** decimals)
    except (ValueError, TypeError):
        return 0.0


def analyze_trader(chain: str, address: str, label: str = "",
                   market_map: dict = None, preloaded_positions: list = None) -> dict:
    """Analyze a GMX trader's performance using AccountStat + Position queries."""
    print(f"  [{chain}] Analyzing {label or address[:12]}...", end=" ", flush=True)

    # Get account stats
    time.sleep(RATE_LIMIT_SEC)

    # Query account stat by ID (id = account address)
    query = """
    query AccountStatById($id: String!) {
        accountStatById(id: $id) {
            id
            wins
            losses
            realizedPnl
            volume
            closedCount
        }
    }
    """
    stat_data = graphql_query(chain, query, variables={"id": address})
    stat = stat_data.get("accountStatById")

    wins = 0
    losses = 0
    total_closed = 0
    realized_pnl = 0.0

    if stat:
        wins = stat.get("wins", 0)
        losses = stat.get("losses", 0)
        total_closed = stat.get("closedCount", wins + losses)
        realized_pnl = parse_gmx_decimal(stat.get("realizedPnl", 0))
    else:
        # Fallback: estimate from trade actions
        time.sleep(RATE_LIMIT_SEC)
        trades = fetch_trade_actions(chain, address, limit=100)
        for t in trades:
            event = t.get("eventName", "")
            if "Decrease" in event or "Close" in event:
                total_closed += 1
                pnl = parse_gmx_decimal(t.get("pnlUsd", 0))
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                realized_pnl += pnl

    if total_closed == 0:
        print("no trades")
        return {"address": address, "label": label, "chain": chain, "error": "no_trades"}

    win_rate = wins / total_closed if total_closed > 0 else 0.5

    # Get open positions
    if preloaded_positions is not None:
        raw_positions = preloaded_positions
    else:
        time.sleep(RATE_LIMIT_SEC)
        raw_positions = fetch_open_positions(chain, address, limit=20)

    open_positions = []
    for pos in raw_positions:
        market = pos.get("market", "")
        is_long = pos.get("isLong", True)

        size_usd = parse_gmx_decimal(pos.get("sizeInUsd", 0))
        if size_usd <= 0:
            continue

        # Entry price decimals vary by asset. GMX uses different precision.
        # For most assets, prices are stored with ~12-24 decimal shift
        raw_entry = pos.get("entryPrice", 0)
        entry = parse_gmx_decimal(raw_entry, 30)
        # Heuristic: if entry is unreasonably small, try fewer decimals
        if entry < 0.000001 and raw_entry:
            entry = parse_gmx_decimal(raw_entry, 24)
        if entry < 0.000001 and raw_entry:
            entry = parse_gmx_decimal(raw_entry, 18)
        if entry < 0.000001 and raw_entry:
            entry = parse_gmx_decimal(raw_entry, 12)

        symbol = ""
        if market_map:
            symbol = market_map.get(market.lower(), "")
        if not symbol:
            symbol = market_map.get(market, "") if market_map else ""

        leverage = pos.get("leverage", 0)
        if isinstance(leverage, str):
            try:
                leverage = int(leverage)
            except ValueError:
                leverage = 0
        # GMX leverage is in basis points (10000 = 1x)
        leverage_x = leverage / 10000 if leverage > 100 else leverage

        open_positions.append({
            "market_address": market,
            "symbol": symbol,
            "direction": "LONG" if is_long else "SHORT",
            "entry_price": entry,
            "size_usd": size_usd,
            "leverage": round(leverage_x, 2),
            "opened_at": pos.get("openedAt", 0),
        })

    # Edge score
    edge = 0
    if win_rate >= 0.65:
        edge += 25
    elif win_rate >= 0.55:
        edge += 15
    elif win_rate >= 0.50:
        edge += 10
    if total_closed >= 50:
        edge += 15
    elif total_closed >= 20:
        edge += 10
    elif total_closed >= 10:
        edge += 5
    if realized_pnl > 100000:
        edge += 20
    elif realized_pnl > 10000:
        edge += 10
    elif realized_pnl > 1000:
        edge += 5
    if len(open_positions) > 0:
        edge += 5

    qualified = (
        total_closed >= MIN_TRADES
        and win_rate >= MIN_WIN_RATE
        and len(open_positions) > 0
    )

    icon = "OK" if qualified else "SKIP"
    print(f"[{icon}] WR:{win_rate*100:.0f}% W:{wins} L:{losses} "
          f"PnL:${realized_pnl:,.0f} Open:{len(open_positions)} Edge:{edge}")

    return {
        "address": address,
        "label": label,
        "chain": chain,
        "win_rate": round(win_rate, 4),
        "total_trades": total_closed,
        "wins": wins,
        "losses": losses,
        "realized_pnl_usd": round(realized_pnl, 2),
        "edge_score": min(edge, 100),
        "open_positions": open_positions,
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "qualified": qualified,
    }


def generate_picks(profile: dict) -> list:
    """Convert a GMX trader's open positions into audit-compatible picks."""
    picks = []
    addr = profile["address"]
    label = profile.get("label", addr[:12])
    chain = profile.get("chain", "arbitrum")
    edge = profile.get("edge_score", 30)
    wr = profile.get("win_rate", 0.5)
    now = datetime.now(timezone.utc)

    for pos in profile.get("open_positions", []):
        symbol = pos.get("symbol", "")
        if not symbol:
            continue

        direction = pos.get("direction", "LONG")
        entry = pos.get("entry_price", 0)
        if entry <= 0:
            continue

        # TP/SL: 4% TP, 2.5% SL
        tp_pct = 0.04
        sl_pct = 0.025
        if direction == "LONG":
            tp = round(entry * (1 + tp_pct), 8)
            sl = round(entry * (1 - sl_pct), 8)
        else:
            tp = round(entry * (1 - tp_pct), 8)
            sl = round(entry * (1 + sl_pct), 8)

        confidence = round(min(0.95, 0.35 + edge / 200 + wr * 0.20), 3)
        pick_id = f"copy_gmx_{chain}_{label}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"copy_gmx_{chain}_{label}",
            "symbol": symbol,
            "category": "crypto",
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
            "max_safe_leverage": pos.get("leverage", 1),
            "forward_trades": profile.get("total_trades", 0),
            "forward_wr": wr,
            "forward_validated": wr >= MIN_WIN_RATE and profile.get("total_trades", 0) >= MIN_TRADES,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
            "reason": (f"GMX {chain} trader {label} | WR:{wr*100:.0f}% "
                       f"Trades:{profile.get('total_trades',0)} "
                       f"PnL:${profile.get('realized_pnl_usd', 0):,.0f} Edge:{edge}"),
            "source_system": f"copy_trader_gmx_{chain}",
            "trader_address": addr,
            "chain": chain,
            "size_usd": pos.get("size_usd", 0),
            "market_address": pos.get("market_address", ""),
            "timestamp": now.isoformat(),
        })

    return picks


def scan_gmx(chains: list = None, max_per_chain: int = 15) -> tuple:
    """
    Main GMX scan: query top accounts + discover whales, analyze, generate picks.
    Returns (profiles, picks).
    """
    chains = chains or ["arbitrum"]

    print("=" * 70)
    print("  GMX v2 COPY TRADER INTELLIGENCE SCANNER (Subsquid)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Chains: {', '.join(chains)}")
    print("=" * 70)

    all_profiles = []
    all_picks = []

    for chain in chains:
        print(f"\n  --- {chain.upper()} ---")

        # Build market address -> symbol mapping
        market_map = build_market_map(chain)

        # Strategy 1: Top accounts by realized PnL
        print("  Querying top accounts by PnL...")
        time.sleep(RATE_LIMIT_SEC)
        top_accounts = fetch_top_accounts_by_pnl(chain, limit=max_per_chain)

        # Build address set: top accounts + seed wallets
        addresses = {}
        for acct in top_accounts:
            addr = acct.get("id", "")  # id IS the account address in Subsquid
            if addr:
                pnl = parse_gmx_decimal(acct.get("realizedPnl", 0))
                addresses[addr] = {
                    "label": f"gmx_top_{addr[:8]}",
                    "stats": acct,
                }

        # Strategy 2: Discover whales from largest open positions
        print("  Discovering whale positions...")
        time.sleep(RATE_LIMIT_SEC)
        whale_positions = fetch_largest_open_positions(chain, limit=30)
        whale_accounts = {}
        for pos in whale_positions:
            acct = pos.get("account", "")
            if acct and acct not in addresses:
                if acct not in whale_accounts:
                    whale_accounts[acct] = []
                whale_accounts[acct].append(pos)

        for addr, positions in list(whale_accounts.items())[:5]:
            addresses[addr] = {
                "label": f"gmx_whale_{addr[:8]}",
                "preloaded_positions": positions,
            }

        # Add seed wallets
        for addr, label in SEED_WALLETS.get(chain, []):
            if addr not in addresses:
                addresses[addr] = {"label": label}

        if not addresses:
            print(f"  No addresses found for {chain}")
            continue

        print(f"  Analyzing {len(addresses)} traders...")

        for addr, info in list(addresses.items())[:max_per_chain]:
            try:
                profile = analyze_trader(
                    chain, addr,
                    label=info.get("label", ""),
                    market_map=market_map,
                    preloaded_positions=info.get("preloaded_positions"),
                )
                all_profiles.append(profile)

                if profile.get("qualified"):
                    picks = generate_picks(profile)
                    all_picks.extend(picks)
                    for pk in picks:
                        print(f"    -> {pk['direction']} {pk['symbol']} @ "
                              f"{pk['entry_price']:.4f}")

                time.sleep(RATE_LIMIT_SEC)
            except Exception as e:
                print(f"  [ERROR] {info.get('label', addr[:12])}: {e}")

    print(f"\n{'='*70}")
    print(f"  GMX SCAN COMPLETE")
    print(f"  Analyzed: {len(all_profiles)} | Qualified: "
          f"{sum(1 for p in all_profiles if p.get('qualified'))} | Picks: {len(all_picks)}")
    print(f"{'='*70}\n")

    return all_profiles, all_picks


def save_gmx_results(profiles: list, picks: list):
    """Save GMX results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "gmx_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "gmx_v2_subsquid",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "gmx_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_gmx()
    save_gmx_results(profiles, picks)
    print(f"\nDone. {len(picks)} GMX v2 copy trader picks generated.")
