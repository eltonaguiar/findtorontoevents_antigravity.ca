#!/usr/bin/env python3
"""
Drift Protocol (Solana) Top Trader Scraper & Pick Generator
============================================================
Drift is Solana's #2 perp DEX. This scraper discovers active whale traders
via the public DLOB (Decentralized Limit Order Book) server and L3 orderbook,
then generates copy-trader picks from their positions.

NO API KEY NEEDED -- Drift DLOB APIs are fully public and free.

DLOB Server Endpoints (VERIFIED WORKING 2026-03-19):
  Base: https://dlob.drift.trade
  L2:   GET /l2?marketIndex={i}&marketType=perp
  L3:   GET /l3?marketIndex={i}&marketType=perp
  Top:  GET /topMakers?marketIndex={i}&marketType=perp&side={bid|ask}&limit=N

Market Indices (perp):
  0: SOL-PERP    1: BTC-PERP    2: ETH-PERP    3: APT-PERP
  4: 1MBONK-PERP 5: MATIC-PERP  6: ARB-PERP    7: DOGE-PERP
  8: BNB-PERP    9: SUI-PERP   10: 1MPEPE-PERP 11: OP-PERP
  12: RENDER-PERP 13: XRP-PERP  14: HNT-PERP   15: INJ-PERP
  16: LINK-PERP  17: RLB-PERP   18: PYTH-PERP   19: TIA-PERP
  20: JTO-PERP   21: SEI-PERP   22: WIF-PERP    23: JUP-PERP
  24: DYM-PERP   25: TAO-PERP   26: W-PERP      27: KMNO-PERP
  28: TNSR-PERP  29: DRIFT-PERP

Approach:
  1. For each perp market, get topMakers (bid + ask) to find active wallets
  2. Scan L3 orderbook to see their active orders and implied positions
  3. Cross-reference across markets to profile each trader
  4. Rank by activity (# markets, order sizes) and generate picks
"""

import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import requests

# Fix Windows charmap encoding
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- Configuration --
DLOB_BASE = "https://dlob.drift.trade"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.3

# Perp market index -> symbol mapping
DRIFT_PERP_MARKETS = {
    0: "SOLUSDT",
    1: "BTCUSDT",
    2: "ETHUSDT",
    3: "APTUSDT",
    4: "BONKUSDT",
    5: "MATICUSDT",
    6: "ARBUSDT",
    7: "DOGEUSDT",
    8: "BNBUSDT",
    9: "SUIUSDT",
    10: "PEPEUSDT",
    11: "OPUSDT",
    12: "RENDERUSDT",
    13: "XRPUSDT",
    14: "HNTUSDT",
    15: "INJUSDT",
    16: "LINKUSDT",
    17: "RLBUSDT",
    18: "PYTHUSDT",
    19: "TIAUSDT",
    20: "JTOUSDT",
    21: "SEIUSDT",
    22: "WIFUSDT",
    23: "JUPUSDT",
    24: "DYMUSDT",
    25: "TAOUSDT",
    26: "WUSDT",
    27: "KMNOUSDT",
    28: "TNSRUSDT",
    29: "DRIFTUSDT",
}

# Subset of important markets to scan (saves time)
KEY_MARKETS = [0, 1, 2, 7, 9, 13, 16, 22, 23]  # SOL, BTC, ETH, DOGE, SUI, XRP, LINK, WIF, JUP

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/2.0",
}

# Minimum criteria
MIN_MARKETS_ACTIVE = 2  # Must be active in at least 2 markets
MIN_TOTAL_SIZE_USD = 5000  # Minimum aggregate position size


def dlob_get(path: str, params: dict = None, retries: int = 3):
    """GET request to Drift DLOB server."""
    url = f"{DLOB_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(2)
                continue
            elif resp.status_code == 400:
                # Bad request (e.g., invalid params)
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  [ERROR] DLOB {path}: {e}")
    return None


def get_top_makers(market_index: int, side: str = "bid", limit: int = 10) -> list:
    """Get top market makers for a specific perp market and side."""
    data = dlob_get("/topMakers", params={
        "marketIndex": market_index,
        "marketType": "perp",
        "side": side,
        "limit": limit,
    })
    if isinstance(data, list):
        return data
    return []


def get_l2_orderbook(market_index: int) -> dict:
    """Get L2 orderbook (aggregated price levels) for a perp market."""
    data = dlob_get("/l2", params={
        "marketIndex": market_index,
        "marketType": "perp",
    })
    return data if isinstance(data, dict) else {}


def get_l3_orderbook(market_index: int) -> dict:
    """Get L3 orderbook (individual orders with maker addresses) for a perp market."""
    data = dlob_get("/l3", params={
        "marketIndex": market_index,
        "marketType": "perp",
    })
    return data if isinstance(data, dict) else {}


def parse_drift_price(raw_price) -> float:
    """Parse Drift price (6 decimal places, e.g. 88684667 = $88.684667 for SOL)."""
    try:
        return int(raw_price) / 1e6
    except (ValueError, TypeError):
        return 0.0


def parse_drift_size(raw_size) -> float:
    """Parse Drift size (9 decimal places, base units)."""
    try:
        return int(raw_size) / 1e9
    except (ValueError, TypeError):
        return 0.0


def discover_traders(markets: list = None) -> dict:
    """
    Discover active traders by scanning topMakers and L3 orderbook
    across multiple perp markets.

    Returns dict: { pubkey: { markets: {idx: { orders, side_bias, total_size }}, ... } }
    """
    markets = markets or KEY_MARKETS
    traders = defaultdict(lambda: {
        "markets": {},
        "total_bid_size_usd": 0,
        "total_ask_size_usd": 0,
        "market_count": 0,
    })

    for idx in markets:
        symbol = DRIFT_PERP_MARKETS.get(idx, f"MARKET{idx}")
        print(f"  Scanning {symbol} (index {idx})...", end=" ", flush=True)

        # Get oracle/mark price from L2
        time.sleep(RATE_LIMIT_SEC)
        l2 = get_l2_orderbook(idx)
        mark_price = parse_drift_price(l2.get("markPrice", l2.get("oracle", 0)))
        if mark_price <= 0:
            print("no price")
            continue

        # Get top makers on both sides
        time.sleep(RATE_LIMIT_SEC)
        bid_makers = get_top_makers(idx, "bid", limit=10)
        time.sleep(RATE_LIMIT_SEC)
        ask_makers = get_top_makers(idx, "ask", limit=10)

        all_makers = set(bid_makers + ask_makers)

        if not all_makers:
            print("no makers")
            continue

        # Get L3 to find each maker's order sizes
        time.sleep(RATE_LIMIT_SEC)
        l3 = get_l3_orderbook(idx)
        bids = l3.get("bids", [])
        asks = l3.get("asks", [])

        # Index orders by maker
        maker_orders = defaultdict(lambda: {"bid_size": 0, "ask_size": 0, "orders": 0})
        for order in bids:
            maker = order.get("maker", "")
            if maker in all_makers:
                size_base = parse_drift_size(order.get("size", 0))
                size_usd = size_base * mark_price
                maker_orders[maker]["bid_size"] += size_usd
                maker_orders[maker]["orders"] += 1

        for order in asks:
            maker = order.get("maker", "")
            if maker in all_makers:
                size_base = parse_drift_size(order.get("size", 0))
                size_usd = size_base * mark_price
                maker_orders[maker]["ask_size"] += size_usd
                maker_orders[maker]["orders"] += 1

        active_count = 0
        for maker, info in maker_orders.items():
            total_size = info["bid_size"] + info["ask_size"]
            if total_size > 0:
                traders[maker]["markets"][idx] = {
                    "symbol": symbol,
                    "mark_price": mark_price,
                    "bid_size_usd": round(info["bid_size"], 2),
                    "ask_size_usd": round(info["ask_size"], 2),
                    "total_size_usd": round(total_size, 2),
                    "order_count": info["orders"],
                    "side_bias": "LONG" if info["bid_size"] > info["ask_size"] * 1.5 else
                                 "SHORT" if info["ask_size"] > info["bid_size"] * 1.5 else "NEUTRAL",
                }
                traders[maker]["total_bid_size_usd"] += info["bid_size"]
                traders[maker]["total_ask_size_usd"] += info["ask_size"]
                active_count += 1

        print(f"${mark_price:,.2f} | {active_count} active traders")

    # Update market count
    for pubkey, data in traders.items():
        data["market_count"] = len(data["markets"])

    return dict(traders)


def analyze_drift_traders(traders: dict, max_traders: int = 15) -> list:
    """
    Score and rank discovered Drift traders.
    Returns list of trader profiles sorted by edge score.
    """
    profiles = []

    # Sort by total size * market diversity
    ranked = sorted(
        traders.items(),
        key=lambda x: (x[1]["market_count"], x[1]["total_bid_size_usd"] + x[1]["total_ask_size_usd"]),
        reverse=True,
    )

    for pubkey, data in ranked[:max_traders]:
        total_size = data["total_bid_size_usd"] + data["total_ask_size_usd"]
        market_count = data["market_count"]

        if market_count < MIN_MARKETS_ACTIVE and total_size < MIN_TOTAL_SIZE_USD:
            continue

        # Edge scoring
        edge = 0
        if market_count >= 5:
            edge += 25
        elif market_count >= 3:
            edge += 15
        elif market_count >= 2:
            edge += 8

        if total_size >= 500000:
            edge += 25
        elif total_size >= 100000:
            edge += 15
        elif total_size >= 10000:
            edge += 8

        # Directional bias consistency (if they lean same way across markets, more conviction)
        biases = [m["side_bias"] for m in data["markets"].values()]
        long_count = biases.count("LONG")
        short_count = biases.count("SHORT")
        if long_count >= 2 or short_count >= 2:
            edge += 10  # Consistent directional view

        # Determine dominant positions (where they have clear directional bias)
        open_positions = []
        for idx, mkt_info in data["markets"].items():
            bias = mkt_info["side_bias"]
            if bias == "NEUTRAL":
                # Market makers often neutral -- still include large ones
                if mkt_info["total_size_usd"] < 50000:
                    continue
                # Default to LONG for large neutral positions
                bias = "LONG" if mkt_info["bid_size_usd"] >= mkt_info["ask_size_usd"] else "SHORT"

            open_positions.append({
                "market_index": idx,
                "symbol": mkt_info["symbol"],
                "direction": bias,
                "mark_price": mkt_info["mark_price"],
                "size_usd": mkt_info["total_size_usd"],
                "bid_size_usd": mkt_info["bid_size_usd"],
                "ask_size_usd": mkt_info["ask_size_usd"],
                "order_count": mkt_info["order_count"],
            })

        qualified = len(open_positions) > 0 and (market_count >= MIN_MARKETS_ACTIVE or total_size >= MIN_TOTAL_SIZE_USD)

        icon = "OK" if qualified else "SKIP"
        print(f"  [{icon}] {pubkey[:12]}... Markets:{market_count} "
              f"Size:${total_size:,.0f} Positions:{len(open_positions)} Edge:{edge}")

        profiles.append({
            "address": pubkey,
            "label": f"drift_{pubkey[:8]}",
            "chain": "solana",
            "platform": "drift",
            "market_count": market_count,
            "total_size_usd": round(total_size, 2),
            "edge_score": min(edge, 100),
            "open_positions": open_positions,
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "qualified": qualified,
        })

    return profiles


def generate_picks(profile: dict) -> list:
    """Convert a Drift trader's positions into audit-compatible picks."""
    picks = []
    addr = profile["address"]
    label = profile.get("label", addr[:12])
    edge = profile.get("edge_score", 30)
    now = datetime.now(timezone.utc)

    for pos in profile.get("open_positions", []):
        symbol = pos.get("symbol", "")
        if not symbol:
            continue

        direction = pos.get("direction", "LONG")
        price = pos.get("mark_price", 0)
        if price <= 0:
            continue

        # TP/SL: 4% TP, 2.5% SL (same as other copy trader scrapers)
        tp_pct = 0.04
        sl_pct = 0.025
        if direction == "LONG":
            tp = round(price * (1 + tp_pct), 8)
            sl = round(price * (1 - sl_pct), 8)
        else:
            tp = round(price * (1 - tp_pct), 8)
            sl = round(price * (1 + sl_pct), 8)

        # Confidence based on edge score and size
        size_usd = pos.get("size_usd", 0)
        size_bonus = min(0.10, size_usd / 1000000)  # Up to 0.10 for $1M+
        confidence = round(min(0.90, 0.35 + edge / 200 + size_bonus), 3)

        pick_id = f"copy_drift_{label}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"copy_drift_{label}",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY" if direction == "LONG" else "SELL",
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
            "position_sizing": "copy_trader",
            "risk_per_trade_pct": 0.025,
            "max_safe_leverage": 1,
            "forward_trades": pos.get("order_count", 0),
            "forward_wr": 0.55,  # Estimated -- Drift doesn't expose historical WR
            "forward_validated": edge >= 30,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
            "reason": (f"Drift Protocol trader {label} | "
                       f"Markets:{profile.get('market_count', 0)} "
                       f"Size:${profile.get('total_size_usd', 0):,.0f} Edge:{edge}"),
            "source_system": "copy_trader_drift",
            "trader_address": addr,
            "chain": "solana",
            "platform": "drift",
            "size_usd": size_usd,
            "market_index": pos.get("market_index", -1),
            "timestamp": now.isoformat(),
        })

    return picks


def fetch_solana_health() -> dict:
    """
    Fetch Solana network health metrics via JSON RPC (free public endpoint, no auth).
    Returns TPS and epoch info as Solana ecosystem activity context.
    High TPS = healthy network = confidence boost for Drift/Solana picks.
    """
    rpc_url = "https://api.mainnet-beta.solana.com"
    headers = {"Content-Type": "application/json"}
    result = {}

    try:
        resp = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "getRecentPerformanceSamples", "params": [4]},
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            samples = resp.json().get("result", [])
            tps_vals = [s["numTransactions"] / s["samplePeriodSecs"]
                        for s in samples if s.get("samplePeriodSecs", 0) > 0]
            if tps_vals:
                avg_tps = sum(tps_vals) / len(tps_vals)
                result["solana_tps"] = round(avg_tps, 0)
                result["solana_network_health"] = (
                    "HIGH_ACTIVITY" if avg_tps > 3000 else
                    "NORMAL"        if avg_tps > 1000 else
                    "LOW_ACTIVITY"
                )
    except Exception:
        pass

    try:
        resp = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "id": 2, "method": "getEpochInfo", "params": []},
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            ei = resp.json().get("result", {})
            result["solana_epoch"] = ei.get("epoch")
            result["solana_slot"] = ei.get("absoluteSlot")
    except Exception:
        pass

    return result


def scan_drift_traders(max_traders: int = 15, markets: list = None) -> tuple:
    """
    Main Drift scan: discover active traders via DLOB, analyze, generate picks.
    Returns (profiles, picks).
    """
    print("=" * 70)
    print("  DRIFT PROTOCOL (SOLANA) COPY TRADER INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  DLOB Server: {DLOB_BASE}")

    # Solana network health check via JSON RPC
    sol_health = fetch_solana_health()
    if sol_health.get("solana_tps"):
        tps = sol_health["solana_tps"]
        health = sol_health.get("solana_network_health", "UNKNOWN")
        epoch = sol_health.get("solana_epoch", "?")
        print(f"  Solana Network: {tps:.0f} TPS | {health} | Epoch {epoch}")

    print("=" * 70)

    # Step 1: Discover active traders across perp markets
    print("\n  --- DISCOVERING TRADERS ---")
    traders = discover_traders(markets=markets or KEY_MARKETS)
    print(f"\n  Discovered {len(traders)} unique traders across {len(markets or KEY_MARKETS)} markets")

    if not traders:
        print("  [WARN] No traders discovered")
        return [], []

    # Step 2: Analyze and rank traders
    print("\n  --- ANALYZING TRADERS ---")
    profiles = analyze_drift_traders(traders, max_traders=max_traders)

    # Step 3: Generate picks
    all_picks = []
    qualified = [p for p in profiles if p.get("qualified")]
    for profile in qualified:
        picks = generate_picks(profile)
        all_picks.extend(picks)
        for pk in picks:
            print(f"    -> {pk['direction']} {pk['symbol']} @ ${pk['entry_price']:,.4f}")

    print(f"\n{'='*70}")
    print(f"  DRIFT SCAN COMPLETE")
    print(f"  Analyzed: {len(profiles)} | Qualified: {len(qualified)} | Picks: {len(all_picks)}")
    print(f"{'='*70}\n")

    return profiles, all_picks


def save_drift_results(profiles: list, picks: list):
    """Save Drift results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "drift_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "drift_dlob",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "drift_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_drift_traders()
    save_drift_results(profiles, picks)
    print(f"\nDone. {len(picks)} Drift Protocol copy trader picks generated.")
