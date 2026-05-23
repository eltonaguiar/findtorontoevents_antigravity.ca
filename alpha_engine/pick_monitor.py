#!/usr/bin/env python3
"""
Pick Monitor -- Cross-system position tracker
Loads active picks from alpha_engine, battleground, and KIMI,
fetches current prices from Binance, and generates a P&L report.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCES = [
    ("alpha_engine", os.path.join(BASE_DIR, "alpha_engine", "data", "active_picks.json")),
    ("battleground", os.path.join(BASE_DIR, "battleground", "data", "active_picks.json")),
    ("kimi", os.path.join(BASE_DIR, "KIMI_RISEOFTHECLAW", "data", "active_picks.json")),
]

_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _BINANCE_SPOT_BASES = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ] + [u for u in _BINANCE_SPOT_BASES if u not in (
        "https://data-api.binance.vision", "https://api.binance.us",
    )]
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price?symbol={}"

# Map Yahoo-style symbols to Binance symbols
CRYPTO_BINANCE_MAP = {}  # built dynamically


def load_picks():
    """Load and normalize picks from all sources into a unified format."""
    all_picks = []

    for source_name, path in SOURCES:
        if not os.path.exists(path):
            print(f"[WARN] Missing file: {path}")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Failed to load {path}: {e}")
            continue

        # KIMI wraps picks in {"activePicks": [...]}
        if isinstance(raw, dict):
            entries = raw.get("activePicks", [])
        elif isinstance(raw, list):
            entries = raw
        else:
            continue

        for p in entries:
            pick = normalize_pick(p, source_name)
            if pick:
                all_picks.append(pick)

    return all_picks


def normalize_pick(p, source_name):
    """Normalize a pick from any source into a common schema."""
    # Determine symbol
    symbol = p.get("symbol", "")
    if not symbol:
        return None

    # Determine direction
    direction = (
        p.get("direction", "") or p.get("signal", "")
    ).upper()
    if direction in ("BUY", "LONG"):
        direction = "LONG"
    elif direction in ("SELL", "SHORT"):
        direction = "SHORT"
    else:
        direction = "LONG"  # default

    # Entry price
    entry_price = p.get("entry_price") or p.get("entryPrice")
    if entry_price is None:
        return None
    entry_price = float(entry_price)
    if entry_price <= 0:
        return None

    # Strategy
    strategy = p.get("strategy") or p.get("algorithm") or p.get("algorithmName") or "unknown"

    # Asset class
    category = (
        p.get("category", "") or p.get("symbolCategory", "")
    ).lower()
    asset_class = classify_asset(symbol, category)

    # Take-profit / stop-loss
    tp = p.get("take_profit") or p.get("targetPrice") or p.get("grossTargetPrice")
    sl = p.get("stop_loss") or p.get("stopPrice")

    # Confidence
    confidence = p.get("confidence") or p.get("signalProbability")
    if confidence and float(confidence) > 1:
        confidence = float(confidence) / 100.0
    elif confidence:
        confidence = float(confidence)

    # Entry date
    entry_date = p.get("entry_date") or p.get("entryDate") or p.get("timestamp", "")

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": float(tp) if tp else None,
        "stop_loss": float(sl) if sl else None,
        "strategy": strategy,
        "asset_class": asset_class,
        "source": source_name,
        "confidence": confidence,
        "entry_date": str(entry_date)[:10] if entry_date else "",
    }


def classify_asset(symbol, category_hint):
    """Classify a symbol into crypto/forex/equity."""
    if category_hint in ("crypto", "meme", "penny"):
        return "crypto"
    if category_hint == "forex":
        return "forex"
    if category_hint in ("stock", "stocks", "etf"):
        return "equity"
    if category_hint == "futures":
        return "equity"

    # Heuristic fallback
    sym = symbol.upper()
    if sym.endswith("USDT") or sym.endswith("-USD"):
        return "crypto"
    if sym.endswith("=X"):
        return "forex"
    if sym.endswith("=F"):
        return "equity"
    return "equity"


def symbol_to_binance(symbol):
    """Convert Yahoo-style crypto symbol to Binance format.
    BTC-USD -> BTCUSDT, BTCUSDT -> BTCUSDT, SHIB-USD -> SHIBUSDT
    """
    sym = symbol.upper().strip()
    if sym.endswith("USDT"):
        return sym
    if sym.endswith("-USD"):
        base = sym.replace("-USD", "")
        return base + "USDT"
    if sym.endswith("USD") and not sym.endswith("USDT"):
        return sym + "T"
    return sym + "USDT"


def fetch_binance_price(binance_symbol):
    """Fetch current price from Binance with endpoint failover. Returns float or None."""
    for base in _BINANCE_SPOT_BASES:
        try:
            url = f"{base}/api/v3/ticker/price?symbol={binance_symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "PickMonitor/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return float(data["price"])
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next
            return None
        except (urllib.error.URLError, KeyError, ValueError, OSError):
            continue
    return None


def fetch_all_crypto_prices(symbols):
    """Fetch prices for a set of Binance symbols. Returns dict {binance_symbol: price}."""
    prices = {}
    for sym in symbols:
        price = fetch_binance_price(sym)
        if price is not None:
            prices[sym] = price
    return prices


def calc_pnl_pct(entry_price, current_price, direction):
    """Calculate unrealized P&L percentage."""
    if entry_price == 0:
        return 0.0
    if direction == "LONG":
        return ((current_price - entry_price) / entry_price) * 100.0
    else:  # SHORT
        return ((entry_price - current_price) / entry_price) * 100.0


def run_monitor():
    """Main monitor logic."""
    now = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"  PICK MONITOR -- Cross-System Position Tracker")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # Load all picks
    picks = load_picks()
    if not picks:
        print("\n[ERROR] No picks loaded from any source.")
        return

    print(f"\nLoaded {len(picks)} active picks from {len(SOURCES)} sources\n")

    # Identify crypto symbols that need Binance prices
    crypto_picks = [p for p in picks if str(p.get("asset_class", "")).upper() == "CRYPTO"]
    forex_picks = [p for p in picks if str(p.get("asset_class", "")).upper() == "FOREX"]
    equity_picks = [p for p in picks if str(p.get("asset_class", "")).upper() == "EQUITY"]

    # Build Binance symbol map
    binance_symbols = set()
    pick_to_binance = {}
    for p in crypto_picks:
        bsym = symbol_to_binance(p["symbol"])
        binance_symbols.add(bsym)
        pick_to_binance[id(p)] = bsym

    # Fetch crypto prices
    print(f"Fetching prices for {len(binance_symbols)} crypto symbols from Binance...")
    crypto_prices = fetch_all_crypto_prices(binance_symbols)
    print(f"  Got {len(crypto_prices)}/{len(binance_symbols)} prices\n")

    # Calculate P&L for each pick
    results = []
    for p in picks:
        current_price = None
        price_status = "ok"

        if str(p.get("asset_class", "")).upper() == "CRYPTO":
            bsym = pick_to_binance.get(id(p))
            if bsym and bsym in crypto_prices:
                current_price = crypto_prices[bsym]
            else:
                price_status = "price_unavailable"
        elif str(p.get("asset_class", "")).upper() in ("FOREX", "EQUITY"):
            price_status = "market_hours_only"

        pnl_pct = None
        if current_price is not None:
            pnl_pct = calc_pnl_pct(p["entry_price"], current_price, p["direction"])

        results.append({
            **p,
            "current_price": current_price,
            "pnl_pct": round(pnl_pct, 4) if pnl_pct is not None else None,
            "price_status": price_status,
        })

    # --- Summary Statistics ---
    priced = [r for r in results if r["pnl_pct"] is not None]
    unpriced = [r for r in results if r["pnl_pct"] is None]

    # Filter out extreme outliers (>1000% P&L) from summary stats -- likely bad entry data
    outliers = [r for r in priced if abs(r["pnl_pct"]) > 1000]
    priced_clean = [r for r in priced if abs(r["pnl_pct"]) <= 1000]
    if outliers:
        print(f"[NOTE] Excluded {len(outliers)} outlier(s) with >1000% P&L from summary stats:")
        for o in outliers:
            print(f"  {o['symbol']} {o['pnl_pct']:+.1f}% (entry={o['entry_price']}, current={o['current_price']}) -- likely bad entry data")
        print()

    wins = [r for r in priced_clean if r["pnl_pct"] > 0.05]
    losses = [r for r in priced_clean if r["pnl_pct"] < -0.05]
    flat = [r for r in priced_clean if -0.05 <= r["pnl_pct"] <= 0.05]

    # Counts by asset class
    class_counts = defaultdict(int)
    for r in results:
        class_counts[r["asset_class"]] += 1

    # Overall P&L (using clean set without outliers)
    total_pnl = sum(r["pnl_pct"] for r in priced_clean) if priced_clean else 0
    avg_pnl = total_pnl / len(priced_clean) if priced_clean else 0

    # Quality score
    quality_score = (len(wins) / len(priced_clean) * 100) if priced_clean else 0

    # Top/bottom performers (use clean set)
    sorted_by_pnl = sorted(priced_clean, key=lambda x: x["pnl_pct"], reverse=True)
    top5 = sorted_by_pnl[:5]
    bottom5 = sorted_by_pnl[-5:]

    # Per-strategy win rate (clean set)
    strat_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "flat": 0, "total": 0, "pnl_sum": 0})
    for r in priced_clean:
        s = strat_stats[r["strategy"]]
        s["total"] += 1
        s["pnl_sum"] += r["pnl_pct"]
        if r["pnl_pct"] > 0.05:
            s["wins"] += 1
        elif r["pnl_pct"] < -0.05:
            s["losses"] += 1
        else:
            s["flat"] += 1

    strategy_wr = {}
    for strat, s in strat_stats.items():
        wr = (s["wins"] / s["total"] * 100) if s["total"] > 0 else 0
        strategy_wr[strat] = {
            "win_rate": round(wr, 1),
            "wins": s["wins"],
            "losses": s["losses"],
            "flat": s["flat"],
            "total": s["total"],
            "avg_pnl": round(s["pnl_sum"] / s["total"], 2) if s["total"] else 0,
        }

    # --- Print Report ---
    print("-" * 70)
    print("  ASSET CLASS BREAKDOWN")
    print("-" * 70)
    for cls in ["crypto", "forex", "equity"]:
        print(f"  {cls.upper():>8}: {class_counts.get(cls, 0)} picks")
    print(f"  {'TOTAL':>8}: {len(results)} picks")

    print(f"\n{'-' * 70}")
    print("  WIN / LOSS / FLAT  (crypto only -- live prices)")
    print("-" * 70)
    print(f"  Priced picks: {len(priced_clean)} ({len(outliers)} outlier(s) excluded)")
    print(f"  Wins:         {len(wins)}  (>{'+'}0.05%)")
    print(f"  Losses:       {len(losses)} (<-0.05%)")
    print(f"  Flat:         {len(flat)}  (within +/-0.05%)")
    print(f"  Quality:      {quality_score:.1f}% profitable")
    print(f"  Avg P&L:      {avg_pnl:+.2f}%")

    print(f"\n{'-' * 70}")
    print("  TOP 5 BEST PERFORMERS")
    print("-" * 70)
    for r in top5:
        dir_icon = "L" if r["direction"] == "LONG" else "S"
        print(f"  {r['pnl_pct']:+8.2f}%  {dir_icon} {r['symbol']:<14} @ {r['entry_price']:<12.6g} -> {r['current_price']:<12.6g}  [{r['strategy']}] ({r['source']})")

    print(f"\n{'-' * 70}")
    print("  TOP 5 WORST PERFORMERS")
    print("-" * 70)
    for r in bottom5:
        dir_icon = "L" if r["direction"] == "LONG" else "S"
        print(f"  {r['pnl_pct']:+8.2f}%  {dir_icon} {r['symbol']:<14} @ {r['entry_price']:<12.6g} -> {r['current_price']:<12.6g}  [{r['strategy']}] ({r['source']})")

    # Forex/equity note
    if forex_picks or equity_picks:
        print(f"\n{'-' * 70}")
        print(f"  NON-CRYPTO PICKS (market hours only -- no live price)")
        print("-" * 70)
        for r in results:
            if r["price_status"] == "market_hours_only":
                dir_icon = "L" if r["direction"] == "LONG" else "S"
                sym_display = r["symbol"].replace("=X", "").replace("=F", "")
                print(f"  {dir_icon} {sym_display:<14} @ {r['entry_price']:<12.6g}  [{r['strategy']}] ({r['source']}) -- market closed")

    # Per-strategy summary (top 10 by count)
    print(f"\n{'-' * 70}")
    print("  PER-STRATEGY WIN RATE (priced picks)")
    print("-" * 70)
    sorted_strats = sorted(strategy_wr.items(), key=lambda x: x[1]["total"], reverse=True)
    for strat, s in sorted_strats[:20]:
        bar = "#" * s["wins"] + "." * s["losses"] + "-" * s["flat"]
        print(f"  {s['win_rate']:5.1f}% WR  ({s['wins']}W/{s['losses']}L/{s['flat']}F)  avg {s['avg_pnl']:+.2f}%  {strat}")

    print(f"\n{'=' * 70}")
    print(f"  OVERALL: {len(priced_clean)} priced | {len(wins)}W {len(losses)}L {len(flat)}F | "
          f"Avg P&L {avg_pnl:+.2f}% | Quality {quality_score:.1f}%")
    print(f"  Unpriced (forex/equity/missing): {len(unpriced)} | Outliers excluded: {len(outliers)}")
    print("=" * 70)

    # --- Build JSON report ---
    report = {
        "generated_at": now.isoformat(),
        "summary": {
            "total_picks": len(results),
            "priced_picks": len(priced_clean),
            "outliers_excluded": len(outliers),
            "unpriced_picks": len(unpriced),
            "by_asset_class": dict(class_counts),
            "wins": len(wins),
            "losses": len(losses),
            "flat": len(flat),
            "quality_score_pct": round(quality_score, 2),
            "avg_pnl_pct": round(avg_pnl, 4),
            "total_pnl_sum_pct": round(total_pnl, 4),
        },
        "top5_best": [
            {
                "symbol": r["symbol"],
                "direction": r["direction"],
                "pnl_pct": r["pnl_pct"],
                "entry_price": r["entry_price"],
                "current_price": r["current_price"],
                "strategy": r["strategy"],
                "source": r["source"],
            }
            for r in top5
        ],
        "top5_worst": [
            {
                "symbol": r["symbol"],
                "direction": r["direction"],
                "pnl_pct": r["pnl_pct"],
                "entry_price": r["entry_price"],
                "current_price": r["current_price"],
                "strategy": r["strategy"],
                "source": r["source"],
            }
            for r in bottom5
        ],
        "strategy_win_rates": strategy_wr,
        "all_picks": [
            {
                "symbol": r["symbol"],
                "direction": r["direction"],
                "asset_class": r["asset_class"],
                "entry_price": r["entry_price"],
                "current_price": r["current_price"],
                "pnl_pct": r["pnl_pct"],
                "price_status": r["price_status"],
                "strategy": r["strategy"],
                "source": r["source"],
                "entry_date": r["entry_date"],
                "confidence": r["confidence"],
                "take_profit": r["take_profit"],
                "stop_loss": r["stop_loss"],
            }
            for r in results
        ],
    }

    # Write report
    report_path = os.path.join(BASE_DIR, "alpha_engine", "data", "pick_monitor_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport written to: {report_path}")
    return report


if __name__ == "__main__":
    run_monitor()
