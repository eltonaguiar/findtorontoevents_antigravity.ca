#!/usr/bin/env python3
"""
Pick Quality Monitor — Hourly snapshot of active picks by quality tier.
Tracks how low-conf vs high-conf picks perform over time to inform
whether to clean up or keep them.

Run hourly via CLI or workflow. Appends to data/pick_quality_snapshots.json.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOTS_FILE = DATA_DIR / "pick_quality_snapshots.json"
ACTIVE_FILE = DATA_DIR / "active_picks.json"

STABLECOIN_SYMBOLS = {"STABLEUSDT", "USD1USDT", "UUSDT", "USDEUSDT", "FDUSDUSDT",
                      "USDCUSDT", "DAIUSDT", "TUSDUSDT", "BUSDUSDT", "XUSDUSDT"}

BAD_PREFIXES = ("0G", "2Z", "k")  # non-Binance symbols


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def classify_pick(p):
    """Classify a pick into quality tiers."""
    conf = p.get("confidence") or 0
    sym = p.get("symbol", "")
    cat = (p.get("category", "") or "").lower()
    strat = p.get("strategy", "")

    if sym in STABLECOIN_SYMBOLS:
        return "STABLECOIN"
    if any(sym.startswith(pfx) for pfx in BAD_PREFIXES):
        return "BAD_SYMBOL"
    if "forex" in cat:
        return "FOREX"
    if conf >= 0.80:
        return "HIGH_CONF"
    if conf >= 0.70:
        return "MED_CONF"
    return "LOW_CONF"


def compute_pnl(p):
    """Compute unrealized PnL % from entry vs current price."""
    entry = p.get("entry_price", 0)
    current = p.get("current_price") or p.get("price") or 0
    if not entry or not current or entry <= 0:
        return None
    direction = (p.get("signal_type", "") or p.get("direction", "")).upper()
    if direction in ("SELL", "SHORT"):
        return round((entry - current) / entry * 100, 4)
    return round((current - entry) / entry * 100, 4)


def take_snapshot():
    picks = load_json(ACTIVE_FILE)
    now = datetime.now(timezone.utc).isoformat()

    tiers = {}
    for p in picks:
        tier = classify_pick(p)
        if tier not in tiers:
            tiers[tier] = {"count": 0, "pnls": [], "symbols": set(), "strategies": set()}
        tiers[tier]["count"] += 1
        pnl = compute_pnl(p)
        if pnl is not None:
            tiers[tier]["pnls"].append(pnl)
        tiers[tier]["symbols"].add(p.get("symbol", ""))
        tiers[tier]["strategies"].add(p.get("strategy", ""))

    snapshot = {
        "timestamp": now,
        "total_picks": len(picks),
        "tiers": {}
    }

    for tier, data in sorted(tiers.items()):
        pnls = data["pnls"]
        avg_pnl = sum(pnls) / len(pnls) if pnls else None
        winners = sum(1 for x in pnls if x > 0)
        losers = sum(1 for x in pnls if x < 0)
        wr = round(winners / (winners + losers) * 100, 1) if (winners + losers) > 0 else None

        snapshot["tiers"][tier] = {
            "count": data["count"],
            "with_price": len(pnls),
            "avg_pnl_pct": round(avg_pnl, 4) if avg_pnl is not None else None,
            "win_rate": wr,
            "winners": winners,
            "losers": losers,
            "best_pnl": round(max(pnls), 2) if pnls else None,
            "worst_pnl": round(min(pnls), 2) if pnls else None,
            "unique_symbols": len(data["symbols"]),
            "unique_strategies": len(data["strategies"]),
        }

    # Print summary
    print(f"\n=== PICK QUALITY SNAPSHOT — {now[:19]} UTC ===")
    print(f"Total active picks: {len(picks)}\n")
    print(f"{'Tier':<15} {'Count':>5} {'w/Price':>7} {'Avg PnL':>8} {'WR%':>6} {'W':>3} {'L':>3} {'Best':>7} {'Worst':>7}")
    print("-" * 75)
    for tier in ["HIGH_CONF", "MED_CONF", "LOW_CONF", "FOREX", "STABLECOIN", "BAD_SYMBOL"]:
        t = snapshot["tiers"].get(tier)
        if not t:
            continue
        avg = f"{t['avg_pnl_pct']:+.2f}%" if t['avg_pnl_pct'] is not None else "N/A"
        wr = f"{t['win_rate']:.0f}%" if t['win_rate'] is not None else "N/A"
        best = f"{t['best_pnl']:+.1f}%" if t['best_pnl'] is not None else "N/A"
        worst = f"{t['worst_pnl']:+.1f}%" if t['worst_pnl'] is not None else "N/A"
        print(f"{tier:<15} {t['count']:>5} {t['with_price']:>7} {avg:>8} {wr:>6} {t['winners']:>3} {t['losers']:>3} {best:>7} {worst:>7}")

    # Append to history
    history = load_json(SNAPSHOTS_FILE)
    if not isinstance(history, list):
        history = []
    history.append(snapshot)
    # Keep last 168 snapshots (7 days hourly)
    history = history[-168:]
    with open(SNAPSHOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)

    print(f"\nSaved to {SNAPSHOTS_FILE.name} ({len(history)} snapshots)")

    # Trend analysis if we have 3+ snapshots
    if len(history) >= 3:
        print("\n--- TREND (last 3 snapshots) ---")
        for tier in ["HIGH_CONF", "MED_CONF", "LOW_CONF"]:
            vals = []
            for s in history[-3:]:
                t = s.get("tiers", {}).get(tier, {})
                if t.get("avg_pnl_pct") is not None:
                    vals.append(t["avg_pnl_pct"])
            if len(vals) >= 2:
                trend = "IMPROVING" if vals[-1] > vals[0] else "DECLINING" if vals[-1] < vals[0] else "FLAT"
                print(f"  {tier}: {' -> '.join(f'{v:+.2f}%' for v in vals)} [{trend}]")

    return snapshot


if __name__ == "__main__":
    take_snapshot()
