#!/usr/bin/env python3
"""
Order-Book Imbalance POC for Battleground Crypto Trading System
===============================================================
Fetches Binance public order book data for BTC, ETH, SOL, XRP and calculates
microstructure signals: imbalance ratios, spread, wall detection, and
confluence scoring with existing Keltner signals.

This is a SNAPSHOT-based POC. For production use, migrate to Binance WebSocket
streams (wss://stream.binance.com:9443/ws/<symbol>@depth20@100ms) to get
continuous updates instead of polling every 15-30 min.

Usage:
    python orderbook_imbalance_poc.py [--keltner-file PATH]
"""

import json
import os
import sys
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "NEARUSDT"]
_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"
DEPTH_LIMIT = 20
WALL_MULTIPLIER = 5.0  # a level > 5x median = wall

# Signal thresholds
STRONG_BUY_IMB5 = 0.30
STRONG_BUY_IMB10 = 0.20
BUY_IMB5 = 0.15
BUY_IMB10 = 0.10

STRONG_SELL_IMB5 = -0.30
STRONG_SELL_IMB10 = -0.20
SELL_IMB5 = -0.15
SELL_IMB10 = -0.10

# Confluence adjustments
CONFLUENCE_AGREE_BOOST = 0.15
CONFLUENCE_DISAGREE_PENALTY = 0.10

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "orderbook_snapshot.json"


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def fetch_orderbook(symbol: str, limit: int = DEPTH_LIMIT) -> dict:
    """Fetch order book from Binance public API with endpoint failover."""
    for base in _BINANCE_SPOT_BASES:
        try:
            resp = requests.get(
                f"{base}/api/v3/depth",
                params={"symbol": symbol, "limit": limit},
                timeout=10,
            )
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            continue
    raise RuntimeError(f"All Binance endpoints failed for {symbol} orderbook")


def calc_imbalance(bids: list[list[str]], asks: list[list[str]], depth: int) -> float:
    """
    imbalance = (sum_bid_vol - sum_ask_vol) / (sum_bid_vol + sum_ask_vol)
    Range: -1.0 (all asks) to +1.0 (all bids)
    """
    bid_vol = sum(float(b[1]) for b in bids[:depth])
    ask_vol = sum(float(a[1]) for a in asks[:depth])
    total = bid_vol + ask_vol
    if total == 0:
        return 0.0
    return (bid_vol - ask_vol) / total


def detect_wall(levels: list[list[str]], multiplier: float = WALL_MULTIPLIER) -> bool:
    """True if any single level has volume > multiplier * median volume."""
    if len(levels) < 3:
        return False
    volumes = [float(lv[1]) for lv in levels]
    med = statistics.median(volumes)
    if med == 0:
        return False
    return any(v > multiplier * med for v in volumes)


def calc_spread_bps(best_bid: float, best_ask: float) -> float:
    """Spread in basis points."""
    mid = (best_bid + best_ask) / 2.0
    if mid == 0:
        return 0.0
    return (best_ask - best_bid) / mid * 10_000


def classify_signal(
    imb5: float, imb10: float, bid_wall: bool, ask_wall: bool
) -> tuple[str, float]:
    """
    Returns (signal_label, signal_strength).
    Strength is 0-1 based on how far beyond thresholds the imbalance sits.
    """
    if imb5 > STRONG_BUY_IMB5 and imb10 > STRONG_BUY_IMB10 and not ask_wall:
        strength = min(1.0, 0.7 + (imb5 - STRONG_BUY_IMB5))
        return "STRONG_BUY", round(strength, 3)

    if imb5 > BUY_IMB5 and imb10 > BUY_IMB10:
        strength = min(1.0, 0.4 + (imb5 - BUY_IMB5) * 2)
        return "BUY", round(strength, 3)

    if imb5 < STRONG_SELL_IMB5 and imb10 < STRONG_SELL_IMB10 and not bid_wall:
        strength = min(1.0, 0.7 + abs(imb5 - STRONG_SELL_IMB5))
        return "STRONG_SELL", round(strength, 3)

    if imb5 < SELL_IMB5 and imb10 < SELL_IMB10:
        strength = min(1.0, 0.4 + abs(imb5 - SELL_IMB5) * 2)
        return "SELL", round(strength, 3)

    # Neutral — strength reflects how close to zero the imbalance is
    strength = round(max(0.0, 0.3 - abs(imb5)), 3)
    return "NEUTRAL", strength


def apply_confluence(
    ob_signal: str,
    ob_strength: float,
    keltner_signal: Optional[str],
) -> tuple[float, str]:
    """
    Adjust confidence based on Keltner signal agreement.
    Returns (adjusted_strength, confluence_note).
    """
    if keltner_signal is None:
        return ob_strength, "no_keltner_data"

    bullish_ob = ob_signal in ("STRONG_BUY", "BUY")
    bearish_ob = ob_signal in ("STRONG_SELL", "SELL")
    bullish_k = keltner_signal.upper() in ("BUY", "STRONG_BUY", "LONG")
    bearish_k = keltner_signal.upper() in ("SELL", "STRONG_SELL", "SHORT")

    if ob_signal == "NEUTRAL":
        return ob_strength, "ob_neutral"

    if (bullish_ob and bullish_k) or (bearish_ob and bearish_k):
        adj = min(1.0, ob_strength + CONFLUENCE_AGREE_BOOST)
        return round(adj, 3), "agrees_+15%"

    if (bullish_ob and bearish_k) or (bearish_ob and bullish_k):
        adj = max(0.0, ob_strength - CONFLUENCE_DISAGREE_PENALTY)
        return round(adj, 3), "disagrees_-10%"

    return ob_strength, "keltner_neutral"


def load_keltner_signals(path: Optional[str] = None) -> dict:
    """
    Try to load Keltner signals from active_picks.json or a supplied path.
    Returns {symbol: signal_direction} or empty dict.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.append(DATA_DIR / "active_picks.json")

    for p in candidates:
        if p.exists():
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                signals = {}
                picks = data if isinstance(data, list) else data.get("picks", [])
                for pick in picks:
                    sym = pick.get("symbol", "")
                    direction = pick.get("signal", pick.get("direction", ""))
                    if sym and direction:
                        signals[sym] = direction
                return signals
            except (json.JSONDecodeError, KeyError):
                continue
    return {}


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_all(keltner_path: Optional[str] = None) -> dict:
    """Fetch order books for all symbols and compute metrics."""
    keltner = load_keltner_signals(keltner_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    results = {"timestamp": timestamp, "symbols": {}}

    for symbol in SYMBOLS:
        try:
            book = fetch_orderbook(symbol)
            bids = book["bids"]  # [[price, qty], ...]
            asks = book["asks"]

            imb5 = round(calc_imbalance(bids, asks, 5), 4)
            imb10 = round(calc_imbalance(bids, asks, 10), 4)
            imb20 = round(calc_imbalance(bids, asks, 20), 4)

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = round(calc_spread_bps(best_bid, best_ask), 2)

            bwall = detect_wall(bids)
            awall = detect_wall(asks)

            signal, strength = classify_signal(imb5, imb10, bwall, awall)

            # Confluence with Keltner
            k_sig = keltner.get(symbol)
            adj_strength, conf_note = apply_confluence(signal, strength, k_sig)

            results["symbols"][symbol] = {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "imbalance_5": imb5,
                "imbalance_10": imb10,
                "imbalance_20": imb20,
                "spread_bps": spread,
                "bid_wall": bwall,
                "ask_wall": awall,
                "signal": signal,
                "signal_strength": round(adj_strength, 3),
                "confluence": conf_note,
            }

        except requests.RequestException as e:
            results["symbols"][symbol] = {"error": str(e)}
        except Exception as e:
            results["symbols"][symbol] = {"error": f"unexpected: {e}"}

        # Polite rate limiting — Binance public API allows 1200 req/min
        time.sleep(0.1)

    return results


def print_table(results: dict) -> None:
    """Print a human-readable summary table."""
    ts = results["timestamp"]
    print(f"\n{'='*82}")
    print(f"  ORDER-BOOK IMBALANCE SNAPSHOT  |  {ts}")
    print(f"{'='*82}")
    header = (
        f"{'Symbol':<10} {'Imb5':>7} {'Imb10':>7} {'Imb20':>7} "
        f"{'Spread':>7} {'BidW':>5} {'AskW':>5} {'Signal':>12} {'Str':>5} {'Conf':>16}"
    )
    print(header)
    print("-" * 82)

    for sym, d in results["symbols"].items():
        if "error" in d:
            print(f"{sym:<10} ERROR: {d['error']}")
            continue
        bw = "YES" if d["bid_wall"] else "-"
        aw = "YES" if d["ask_wall"] else "-"
        print(
            f"{sym:<10} {d['imbalance_5']:>+7.4f} {d['imbalance_10']:>+7.4f} "
            f"{d['imbalance_20']:>+7.4f} {d['spread_bps']:>6.1f}bp "
            f"{bw:>5} {aw:>5} {d['signal']:>12} {d['signal_strength']:>5.3f} "
            f"{d.get('confluence', ''):>16}"
        )

    print("-" * 82)
    print("  Imbalance: +1.0 = all bids (bullish), -1.0 = all asks (bearish)")
    print("  Wall: bid/ask level with volume > 5x median")
    print("  Confluence: agreement/disagreement with Keltner channel signal")
    print()
    print("  LIMITATIONS (POC):")
    print("  - This is a single snapshot, NOT a continuous stream.")
    print("  - Order book can change drastically in milliseconds (spoofing, iceberg orders).")
    print("  - For production: use Binance WebSocket depth stream for real-time updates.")
    print("  - Imbalance signals are most reliable when confirmed by price action over 2-3 scans.")
    print(f"{'='*82}\n")


def save_snapshot(results: dict) -> Path:
    """Save results to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Order-Book Imbalance POC")
    parser.add_argument(
        "--keltner-file",
        type=str,
        default=None,
        help="Path to JSON with Keltner/active picks for confluence scoring",
    )
    args = parser.parse_args()

    print("Fetching Binance order books for BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT...")
    results = analyze_all(keltner_path=args.keltner_file)

    print_table(results)

    out = save_snapshot(results)
    print(f"Snapshot saved to: {out}")


if __name__ == "__main__":
    main()
