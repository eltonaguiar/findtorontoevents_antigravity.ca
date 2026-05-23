#!/usr/bin/env python3
"""
Whale & Smart Money Tracker
============================
Tracks large-wallet on-chain activity across multiple data sources to
derive trading signals from whale movements.

Sources:
  1. Etherscan/BscScan whale alerts (large token transfers)
  2. Whale Alert API (free tier -- large transfers)
  3. Arkham Intelligence labels (public address labels)
  4. CryptoQuant exchange flow data

No API keys required for basic functionality.
Optional keys: WHALE_ALERT_API_KEY, ETHERSCAN_API_KEY
"""

import json
import time
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Known exchange hot wallet addresses (for flow analysis)
EXCHANGE_WALLETS = {
    # Binance
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot 1",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Hot 2",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance Hot 3",
    # Coinbase
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase Hot 1",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase Hot 2",
    # Kraken
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken Hot",
    # OKX
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX Hot 1",
    # Bybit
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit Hot 1",
}

# Known whale wallets to track (high-conviction traders)
TRACKED_WHALES = [
    ("0x8894e0a0c962cb723c1ef8a1b4e0ce8b5cde29a9", "James Fickel (ETH whale)"),
    ("0x176f3dab24a159341c0509bb36b833e7fdd0a132", "Justin Sun"),
    ("0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503", "Binance Deployer"),
    ("0x07a98c27c53ed9016e5bd0ce980c8f3a73fdf330", "Jump Trading"),
    ("0xbdfa4f4492dd7b7cf211209c4791af8d52bf5c50", "Wintermute"),
    ("0x0d0707963952f2fba59dd06f2b425ace40b492fe", "Gate.io Hot"),
    ("0x1db92e2eebc8e0c075a02bea49a2935bcd2dfcf4", "Alameda remnant"),
]


def fetch_whale_alert_transfers(min_value_usd: int = 1000000) -> list:
    """
    Fetch recent large transfers from Whale Alert API (free tier).
    Returns transfers > $1M in the last hour.
    """
    api_key = os.getenv("WHALE_ALERT_API_KEY", "")
    if not api_key:
        # Try free public endpoint
        try:
            resp = requests.get("https://api.whale-alert.io/v1/transactions", params={
                "min_value": str(min_value_usd),
                "start": str(int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())),
                "cursor": "",
            }, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("transactions", [])
        except Exception as e:
            print(f"  [WARN] Whale Alert (no key): {e}")
        return []

    try:
        resp = requests.get("https://api.whale-alert.io/v1/transactions", params={
            "api_key": api_key,
            "min_value": str(min_value_usd),
            "start": str(int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())),
        }, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("transactions", [])
    except Exception as e:
        print(f"  [WARN] Whale Alert: {e}")
    return []


def fetch_etherscan_whale_txs(address: str, label: str = "") -> list:
    """Fetch recent large transactions for a tracked whale from Etherscan."""
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    if not api_key:
        return []

    try:
        resp = requests.get("https://api.etherscan.io/api", params={
            "module": "account",
            "action": "tokentx",
            "address": address,
            "page": "1",
            "offset": "20",
            "sort": "desc",
            "apikey": api_key,
        }, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                return data.get("result", [])
    except Exception as e:
        print(f"  [WARN] Etherscan ({label}): {e}")
    return []


def analyze_exchange_flows(transfers: list) -> dict:
    """
    Analyze whale transfers to/from exchanges.
    Returns flow analysis: net inflow = bearish, net outflow = bullish.
    """
    exchange_addrs = set(EXCHANGE_WALLETS.keys())

    flows = {}  # symbol -> {"inflow_usd": 0, "outflow_usd": 0}

    for tx in transfers:
        symbol = tx.get("symbol", tx.get("blockchain", "")).upper()
        value_usd = float(tx.get("amount_usd", tx.get("value_usd", 0)))
        from_addr = tx.get("from", {}).get("address", "").lower()
        to_addr = tx.get("to", {}).get("address", "").lower()

        if symbol not in flows:
            flows[symbol] = {"inflow_usd": 0, "outflow_usd": 0, "transfers": 0}

        if to_addr in exchange_addrs and from_addr not in exchange_addrs:
            flows[symbol]["inflow_usd"] += value_usd  # Deposit to exchange = potential sell
        elif from_addr in exchange_addrs and to_addr not in exchange_addrs:
            flows[symbol]["outflow_usd"] += value_usd  # Withdrawal from exchange = holding

        flows[symbol]["transfers"] += 1

    return flows


def generate_whale_picks(flows: dict) -> list:
    """Generate picks based on whale flow analysis."""
    picks = []
    now = datetime.now(timezone.utc)

    for symbol, flow in flows.items():
        if flow["transfers"] < 2:
            continue

        inflow = flow["inflow_usd"]
        outflow = flow["outflow_usd"]
        total = inflow + outflow

        if total < 1_000_000:
            continue

        net_ratio = (outflow - inflow) / total if total > 0 else 0

        # Strong outflow (bullish): net_ratio > 0.3
        # Strong inflow (bearish): net_ratio < -0.3
        if abs(net_ratio) < 0.3:
            continue  # Not strong enough signal

        direction = "LONG" if net_ratio > 0 else "SHORT"
        confidence = round(min(0.85, 0.50 + abs(net_ratio) * 0.5), 3)

        # Normalize symbol
        std_symbol = symbol.replace("-", "").replace("_", "")
        if std_symbol in ("BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA",
                           "AVAX", "DOT", "MATIC", "LINK", "UNI", "AAVE"):
            std_symbol = std_symbol + "USDT"
        else:
            continue  # Skip unknown tokens

        pick_id = f"whale_flow_{std_symbol}::{direction}::{now.strftime('%Y-%m-%d_%H%M')}"

        flow_label = "OUTFLOW" if net_ratio > 0 else "INFLOW"
        picks.append({
            "id": pick_id,
            "strategy": "whale_exchange_flow",
            "symbol": std_symbol,
            "category": "crypto",
            "signal_type": "BUY" if direction == "LONG" else "SELL",
            "direction": direction,
            "entry_price": 0,  # Needs live price fill
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
            "status": "OPEN",
            "hold_days": None,
            "allocation": 150.0,
            "position_sizing": "whale_flow",
            "risk_per_trade_pct": 0.02,
            "max_safe_leverage": 1.0,
            "forward_trades": 0,
            "forward_wr": 0,
            "forward_validated": False,
            "elite_score": min(100, int(abs(net_ratio) * 80 + min(total / 10_000_000, 20))),
            "elite_grade": "B",
            "reason": (f"Whale {flow_label} | Net: ${abs(outflow-inflow):,.0f} "
                       f"({abs(net_ratio)*100:.0f}% ratio) | "
                       f"In:${inflow:,.0f} Out:${outflow:,.0f}"),
            "source_system": "whale_exchange_flow",
            "whale_inflow_usd": round(inflow, 2),
            "whale_outflow_usd": round(outflow, 2),
            "whale_net_ratio": round(net_ratio, 4),
            "timestamp": now.isoformat(),
        })

    return picks


def scan_whale_activity() -> tuple:
    """Main whale tracking scan."""
    print("=" * 70)
    print("  WHALE & SMART MONEY TRACKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    all_transfers = []
    all_picks = []

    # 1. Whale Alert transfers
    print("\n  Fetching Whale Alert transfers...")
    transfers = fetch_whale_alert_transfers(min_value_usd=1_000_000)
    all_transfers.extend(transfers)
    print(f"  Whale Alert: {len(transfers)} large transfers")

    # 2. Analyze exchange flows
    if all_transfers:
        print("\n  Analyzing exchange flows...")
        flows = analyze_exchange_flows(all_transfers)
        flow_picks = generate_whale_picks(flows)
        all_picks.extend(flow_picks)
        print(f"  Flow signals: {len(flow_picks)} picks from {len(flows)} symbols")

        for sym, flow in sorted(flows.items(), key=lambda x: x[1]["inflow_usd"] + x[1]["outflow_usd"], reverse=True)[:5]:
            net = flow["outflow_usd"] - flow["inflow_usd"]
            direction = "OUTFLOW" if net > 0 else "INFLOW"
            print(f"    {sym}: {direction} ${abs(net):,.0f} ({flow['transfers']} txs)")

    # 3. Track specific whales (if Etherscan key available)
    if os.getenv("ETHERSCAN_API_KEY"):
        print("\n  Tracking known whales...")
        for addr, label in TRACKED_WHALES[:5]:
            txs = fetch_etherscan_whale_txs(addr, label)
            if txs:
                print(f"    {label}: {len(txs)} recent txs")
            time.sleep(RATE_LIMIT_SEC)
    else:
        print("\n  [INFO] Set ETHERSCAN_API_KEY for whale wallet tracking")

    # Save results
    now_iso = datetime.now(timezone.utc).isoformat()

    with open(DATA_DIR / "whale_transfers.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "transfer_count": len(all_transfers),
            "picks_generated": len(all_picks),
        }, f, indent=2, default=str)

    with open(DATA_DIR / "whale_picks.json", "w", encoding="utf-8") as f:
        json.dump(all_picks, f, indent=2, default=str)

    print(f"\n  Whale scan complete: {len(all_transfers)} transfers, {len(all_picks)} picks")
    return all_transfers, all_picks


if __name__ == "__main__":
    scan_whale_activity()
