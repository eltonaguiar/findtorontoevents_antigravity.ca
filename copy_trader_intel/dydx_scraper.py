#!/usr/bin/env python3
"""
dYdX v4 (Cosmos) Top Trader Scraper & Pick Generator
=====================================================
Tracks top traders on dYdX v4 via the public Indexer REST API.
dYdX v4 runs on a Cosmos app-chain; the Indexer provides a REST API
that mirrors on-chain state without needing an API key.

NO API KEY NEEDED -- dYdX Indexer API is fully public and free.

Indexer Base URL: https://indexer.dydx.trade/v4
Docs:            https://docs.dydx.exchange/api_integration-indexer/indexer_api

Key Endpoints:
  - GET /v4/addresses/{address}                                    -- Subaccounts for address
  - GET /v4/addresses/{address}/subaccountNumber/{n}               -- Subaccount details
  - GET /v4/perpetualPositions?address=X&subaccountNumber=0        -- Open perp positions
  - GET /v4/fills?address=X&subaccountNumber=0                     -- Trade fills/history
  - GET /v4/historical-pnl?address=X&subaccountNumber=0            -- PnL ticks
  - GET /v4/perpetualMarkets                                       -- All available markets

Note: dYdX v4 does NOT have a built-in leaderboard API. We use known
top-performing addresses from on-chain analysis and Copin.io rankings.
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# -- Configuration --
DYDX_INDEXER_BASE = "https://indexer.dydx.trade/v4"

# Fallback indexer endpoints
DYDX_INDEXER_MIRRORS = [
    "https://indexer.dydx.trade/v4",
    "https://dydx-mainnet-indexer.allthatnode.com/v4",
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.4

# Minimum criteria for qualification
MIN_TRADES = 15
MIN_WIN_RATE = 0.50
MIN_TOTAL_PNL = 100  # USD

# Known top dYdX v4 traders (from Copin.io leaderboards, on-chain analysis,
# and live block data extraction via Polkachu RPC)
# Format: (dydx1... address, label)
# Addresses verified on dydx-mainnet-1 chain (2026-03-19)
SEED_WALLETS = [
    # --- Original seed wallets (Copin.io leaderboard) ---
    ("dydx1sxdvx2kzgdykutxfv06ka9gt0klu8wctfwskhg", "dydx_whale_1"),
    ("dydx1v0hzqsleyjdfzy9lkuv5nrqyucgvj7t5yuzqaw", "dydx_whale_2"),
    ("dydx14t9etqf5selxfmrfu0t5ep20rghjnrm4gfvvat", "dydx_whale_3"),
    ("dydx1gf4xyat0cgfn04qf53r8hhrrc9ahv55ep82fv2", "dydx_whale_4"),
    ("dydx18p7nz5rqezkyscdz9pv9rchnsesjyjjyfe92t3", "dydx_whale_5"),
    # --- Active traders extracted from dydx-mainnet-1 blocks (2026-03-19) ---
    # These addresses were submitting MsgPlaceOrder txs in recent blocks
    ("dydx12zrde8fgwn88vuehnm9prfdgtcdlm8fqc2kqzf", "dydx_active_trader_1"),
    ("dydx14dltc2w6y3dhf0naz8luglsvjt0vhvswm2j6d0", "dydx_active_trader_2"),
    ("dydx15ztc7xy42tn2ukkc0qjthkucw9ac63pgp70urn", "dydx_active_trader_3"),
    ("dydx16wrau2x4tsg033xfrrdpae6kxfn9kyuerr5jjp", "dydx_active_trader_4"),
    ("dydx17xpfvakm2amg962yls6f84z3kell8c5leqdyt2", "dydx_active_trader_5"),
    ("dydx1c8fd59zw0e79m7p5skne5xvcna9cs59mxmprnr", "dydx_active_trader_6"),
    ("dydx1d06lgyy03spureacp933g3qc3wwuszaxjurk5w", "dydx_active_trader_7"),
    ("dydx1ensqm4lyl5vg6mrj7uwpvrggjmw2wd8rnwu40c", "dydx_active_trader_8"),
    ("dydx1jv65s3grqf6v6jl3dp4t6c9t9rk99cd8wx2cfg", "dydx_active_trader_9"),
    ("dydx1ltyc6y4skclzafvpznpt2qjwmfwgsndp458rmp", "dydx_active_trader_10"),
    ("dydx1ph7ek4yk82gdaw0r4yzluuchxwe96yrjdjq9wr", "dydx_active_trader_11"),
    ("dydx1wxje320an3karyc6mjw4zghs300dmrjkwn7xtk", "dydx_active_trader_12"),
    ("dydx1ycklg0q3cxvt2khh675mefxxx3x53mufuhakxe", "dydx_active_trader_13"),
]

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CopyTraderIntel/1.0",
}


def dydx_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """GET request to dYdX Indexer API with mirror failover."""
    for base_url in DYDX_INDEXER_MIRRORS:
        url = f"{base_url}{path}" if path.startswith("/") else f"{base_url}/{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                elif resp.status_code == 404:
                    return {}
                else:
                    break  # try next mirror
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    print(f"  [WARN] All dYdX indexer mirrors failed for {path}")
    return {}


def get_subaccounts(address: str) -> list:
    """Get all subaccounts for a dYdX address."""
    data = dydx_get(f"/addresses/{address}")
    if isinstance(data, dict):
        return data.get("subaccounts", [])
    return []


def get_subaccount_detail(address: str, subaccount_number: int = 0) -> dict:
    """Get detailed subaccount info including equity."""
    return dydx_get(f"/addresses/{address}/subaccountNumber/{subaccount_number}")


def get_perpetual_positions(address: str, subaccount_number: int = 0,
                            status: str = "OPEN") -> list:
    """
    Get perpetual positions for a subaccount.
    Status: OPEN, CLOSED, LIQUIDATED
    """
    data = dydx_get("/perpetualPositions", params={
        "address": address,
        "subaccountNumber": subaccount_number,
        "status": status,
        "limit": 50,
    })
    if isinstance(data, dict):
        return data.get("positions", [])
    return []


def get_fills(address: str, subaccount_number: int = 0, limit: int = 100) -> list:
    """Get trade fills (execution history) for a subaccount."""
    data = dydx_get("/fills", params={
        "address": address,
        "subaccountNumber": subaccount_number,
        "limit": limit,
    })
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("fills", [])
    return []


def get_historical_pnl(address: str, subaccount_number: int = 0, limit: int = 90) -> list:
    """Get historical PnL ticks for performance analysis."""
    data = dydx_get("/historical-pnl", params={
        "address": address,
        "subaccountNumber": subaccount_number,
        "limit": limit,
    })
    if isinstance(data, dict):
        return data.get("historicalPnl", [])
    return []


def get_markets() -> dict:
    """Get all perpetual markets on dYdX."""
    data = dydx_get("/perpetualMarkets")
    if isinstance(data, dict):
        return data.get("markets", {})
    return {}


def normalize_market(market: str) -> str:
    """Convert dYdX market ID to standard symbol. BTC-USD -> BTCUSDT"""
    if not market:
        return ""
    s = market.upper().replace("-USD", "USDT").replace("-USDT", "USDT")
    if not s.endswith("USDT"):
        s += "USDT"
    return s


def analyze_trader(address: str, label: str = "") -> dict:
    """Full analysis of a dYdX v4 trader."""
    print(f"  Analyzing {label or address[:16]}...", end=" ", flush=True)

    # Get subaccount info
    subaccount = get_subaccount_detail(address, 0)
    if not subaccount:
        print("no subaccount")
        return {"address": address, "label": label, "error": "no_subaccount"}

    # Account equity
    try:
        equity = float(subaccount.get("equity", 0))
    except (ValueError, TypeError):
        equity = 0

    # Get open positions
    time.sleep(RATE_LIMIT_SEC)
    open_positions = get_perpetual_positions(address, 0, status="OPEN")

    # Get closed positions for win rate
    time.sleep(RATE_LIMIT_SEC)
    closed_positions = get_perpetual_positions(address, 0, status="CLOSED")

    # Get fills for detailed analysis
    time.sleep(RATE_LIMIT_SEC)
    fills = get_fills(address, 0, limit=200)

    # Get historical PnL
    time.sleep(RATE_LIMIT_SEC)
    pnl_history = get_historical_pnl(address, 0, limit=90)

    # Calculate stats from closed positions
    wins = 0
    losses = 0
    total_pnl = 0
    pnl_values = []

    for pos in closed_positions:
        try:
            realized = float(pos.get("realizedPnl", 0))
        except (ValueError, TypeError):
            continue
        if realized > 0:
            wins += 1
        elif realized < 0:
            losses += 1
        total_pnl += realized
        pnl_values.append(realized)

    # Also check PnL history for total
    if pnl_history:
        try:
            latest_pnl = float(pnl_history[0].get("totalPnl", 0))
            if abs(latest_pnl) > abs(total_pnl):
                total_pnl = latest_pnl
        except (ValueError, TypeError, IndexError):
            pass

    total_closed = wins + losses
    win_rate = wins / total_closed if total_closed > 0 else 0

    # Profit factor
    gross_profit = sum(p for p in pnl_values if p > 0)
    gross_loss = abs(sum(p for p in pnl_values if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    # Max drawdown from PnL history
    max_dd = 0
    cum = 0
    peak = 0
    for pnl in pnl_values:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = (max_dd / max(equity, 1)) * 100 if equity > 0 else 0

    # Edge score
    edge = 0
    if win_rate >= 0.65:
        edge += 25
    elif win_rate >= 0.55:
        edge += 15
    elif win_rate >= 0.50:
        edge += 8
    if profit_factor >= 2.0:
        edge += 20
    elif profit_factor >= 1.5:
        edge += 12
    if total_closed >= 100:
        edge += 15
    elif total_closed >= 30:
        edge += 8
    if total_pnl > 10000:
        edge += 20
    elif total_pnl > 1000:
        edge += 12
    elif total_pnl > 100:
        edge += 5

    qualified = (
        total_closed >= MIN_TRADES
        and win_rate >= MIN_WIN_RATE
        and total_pnl >= MIN_TOTAL_PNL
        and len(open_positions) > 0
    )

    icon = "OK" if qualified else "SKIP"
    print(f"[{icon}] WR:{win_rate*100:.0f}% PnL:${total_pnl:,.0f} "
          f"PF:{profit_factor:.1f} Trades:{total_closed} Positions:{len(open_positions)}")

    # Parse open positions
    parsed_positions = []
    for pos in open_positions:
        try:
            size = float(pos.get("size", 0))
            entry = float(pos.get("entryPrice", 0))
            unrealized = float(pos.get("unrealizedPnl", 0))
        except (ValueError, TypeError):
            continue
        if entry <= 0:
            continue

        parsed_positions.append({
            "market": pos.get("market", ""),
            "symbol": normalize_market(pos.get("market", "")),
            "side": pos.get("side", "LONG"),
            "size": size,
            "entry_price": entry,
            "unrealized_pnl": unrealized,
            "status": pos.get("status", "OPEN"),
        })

    return {
        "address": address,
        "label": label,
        "equity": round(equity, 2),
        "total_realized_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 4),
        "total_trades": total_closed,
        "wins": wins,
        "losses": losses,
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "edge_score": min(edge, 100),
        "open_positions": parsed_positions,
        "fill_count": len(fills),
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "qualified": qualified,
    }


def generate_picks(profile: dict) -> list:
    """Convert a dYdX trader's open positions into audit-compatible picks."""
    picks = []
    addr = profile["address"]
    label = profile.get("label", addr[:12])
    edge = profile.get("edge_score", 30)
    wr = profile.get("win_rate", 0.5)
    pf = profile.get("profit_factor", 1.0)
    now = datetime.now(timezone.utc)

    for pos in profile.get("open_positions", []):
        symbol = pos.get("symbol", "")
        if not symbol:
            continue

        direction = pos.get("side", "LONG").upper()
        entry = pos.get("entry_price", 0)
        if entry <= 0:
            continue

        # TP/SL: 3.5% TP, 2% SL
        tp_pct = 0.035
        sl_pct = 0.02
        if direction == "LONG":
            tp = round(entry * (1 + tp_pct), 8)
            sl = round(entry * (1 - sl_pct), 8)
        else:
            tp = round(entry * (1 - tp_pct), 8)
            sl = round(entry * (1 + sl_pct), 8)

        confidence = round(min(0.95, 0.35 + edge / 200 + wr * 0.25), 3)
        pick_id = f"copy_dydx_{label}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"copy_dydx_{label}",
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
            "risk_per_trade_pct": 0.02,
            "max_safe_leverage": 1,  # dYdX positions don't expose leverage directly
            "forward_trades": profile.get("total_trades", 0),
            "forward_wr": wr,
            "forward_validated": wr >= MIN_WIN_RATE and profile.get("total_trades", 0) >= MIN_TRADES,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 50 else "B" if edge >= 30 else "C",
            "reason": (f"dYdX v4 trader {label} | WR:{wr*100:.0f}% PF:{pf:.1f} "
                       f"PnL:${profile.get('total_realized_pnl',0):,.0f} Edge:{edge}"),
            "source_system": "copy_trader_dydx",
            "trader_address": addr,
            "trader_pnl": profile.get("total_realized_pnl", 0),
            "trader_equity": profile.get("equity", 0),
            "unrealized_pnl": pos.get("unrealized_pnl", 0),
            "dydx_market": pos.get("market", ""),
            "timestamp": now.isoformat(),
        })

    return picks


def scan_dydx(max_traders: int = 20) -> tuple:
    """
    Main dYdX scan: analyze seed wallets, generate picks.
    Returns (profiles, picks).
    """
    print("=" * 70)
    print("  dYdX v4 COPY TRADER INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Indexer: {DYDX_INDEXER_BASE}")
    print("=" * 70)

    # Verify API connectivity
    print("\n  Testing indexer connectivity...")
    markets = get_markets()
    if markets:
        print(f"  Connected! {len(markets)} perpetual markets available")
    else:
        print("  [WARN] Could not fetch markets -- indexer may be down")

    all_profiles = []
    all_picks = []

    print(f"\n  Analyzing {len(SEED_WALLETS)} seed wallets...")

    for addr, label in SEED_WALLETS[:max_traders]:
        try:
            profile = analyze_trader(addr, label)
            all_profiles.append(profile)

            if profile.get("qualified"):
                picks = generate_picks(profile)
                all_picks.extend(picks)
                for pk in picks:
                    print(f"    -> {pk['direction']} {pk['symbol']} @ {pk['entry_price']:.4f}")

            time.sleep(RATE_LIMIT_SEC)
        except Exception as e:
            print(f"  [ERROR] {label}: {e}")

    print(f"\n{'='*70}")
    print(f"  dYdX SCAN COMPLETE")
    print(f"  Analyzed: {len(all_profiles)} | Qualified: "
          f"{sum(1 for p in all_profiles if p.get('qualified'))} | Picks: {len(all_picks)}")
    print(f"{'='*70}\n")

    return all_profiles, all_picks


def save_dydx_results(profiles: list, picks: list):
    """Save dYdX results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "dydx_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "dydx_v4_indexer",
            "indexer_url": DYDX_INDEXER_BASE,
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "dydx_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_dydx()
    save_dydx_results(profiles, picks)
    print(f"\nDone. {len(picks)} dYdX v4 copy trader picks generated.")
