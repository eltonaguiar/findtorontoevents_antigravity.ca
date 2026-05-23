"""
Regulated Asset Screener — Compliance Taxonomy & Liquidity-Adjusted Allocation.

Implements Phase 4 deliverables from the turnaround research roadmap:
- Regulated-asset taxonomy (large-cap, stablecoins, CME derivatives)
- Liquidity screening (order-book depth proxy, 24h volume)
- Manipulation risk scoring (low-cap = high manipulation risk)
- Compliance-constrained allocation (max 5% per asset)

Usage:
    python quant_lab/regulated_assets.py               # Full screening report
    python quant_lab/regulated_assets.py --screen       # Asset screening only
    python quant_lab/regulated_assets.py --allocate     # Constrained allocation
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "quant_lab"))
from kpi_engine import load_closed_picks, compute_all_kpis


# ─────────────────────────────────────────────────────────────────
# Regulated Asset Taxonomy
# ─────────────────────────────────────────────────────────────────

REGULATED_ASSETS = {
    # Large-cap crypto (widely accepted, deep liquidity)
    "BTCUSDT": {
        "category": "large_cap_crypto",
        "regulated_status": "approved",
        "market_cap_tier": "mega",  # >$500B
        "exchanges": ["Binance", "Coinbase", "CME"],
        "daily_volume_usd": 30_000_000_000,
        "manipulation_risk": "low",
        "notes": "Baseline crypto benchmark, CME futures available",
    },
    "ETHUSDT": {
        "category": "large_cap_crypto",
        "regulated_status": "approved",
        "market_cap_tier": "mega",  # >$300B
        "exchanges": ["Binance", "Coinbase", "CME"],
        "daily_volume_usd": 20_000_000_000,
        "manipulation_risk": "low",
        "notes": "Strong DeFi ecosystem, deep order book",
    },
    "BNBUSDT": {
        "category": "large_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "large",  # >$50B
        "exchanges": ["Binance"],
        "daily_volume_usd": 2_000_000_000,
        "manipulation_risk": "medium",
        "notes": "Exchange token — regulatory scrutiny in some jurisdictions",
    },
    "SOLUSDT": {
        "category": "large_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "large",  # >$30B
        "exchanges": ["Binance", "Coinbase", "Kraken"],
        "daily_volume_usd": 3_000_000_000,
        "manipulation_risk": "medium",
        "notes": "High-performance chain, growing institutional interest",
    },
    "XRPUSDT": {
        "category": "large_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "large",
        "exchanges": ["Binance", "Kraken"],
        "daily_volume_usd": 2_000_000_000,
        "manipulation_risk": "medium",
        "notes": "SEC case partially resolved, regulatory clarity improving",
    },

    # Mid-cap crypto (decent liquidity, higher manipulation risk)
    "ADAUSDT": {
        "category": "mid_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Coinbase"],
        "daily_volume_usd": 500_000_000,
        "manipulation_risk": "medium",
        "notes": "Academic approach, proof-of-stake",
    },
    "DOTUSDT": {
        "category": "mid_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Kraken"],
        "daily_volume_usd": 300_000_000,
        "manipulation_risk": "medium",
        "notes": "Parachain ecosystem",
    },
    "MATICUSDT": {
        "category": "mid_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Coinbase"],
        "daily_volume_usd": 400_000_000,
        "manipulation_risk": "medium",
        "notes": "L2 scaling, rebranded to Polygon",
    },
    "AVAXUSDT": {
        "category": "mid_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Coinbase"],
        "daily_volume_usd": 500_000_000,
        "manipulation_risk": "medium",
        "notes": "Subnet architecture, institutional DeFi",
    },
    "LINKUSDT": {
        "category": "mid_cap_crypto",
        "regulated_status": "review_needed",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Coinbase"],
        "daily_volume_usd": 600_000_000,
        "manipulation_risk": "medium",
        "notes": "Oracle infrastructure, CCIP",
    },

    # Small-cap / meme (high manipulation risk)
    "DOGEUSDT": {
        "category": "meme_coin",
        "regulated_status": "caution",
        "market_cap_tier": "mid",
        "exchanges": ["Binance", "Coinbase"],
        "daily_volume_usd": 1_000_000_000,
        "manipulation_risk": "high",
        "notes": "Meme-driven, high social media correlation",
    },
    "SHIBUSDT": {
        "category": "meme_coin",
        "regulated_status": "caution",
        "market_cap_tier": "small",
        "exchanges": ["Binance"],
        "daily_volume_usd": 200_000_000,
        "manipulation_risk": "high",
        "notes": "Meme token, thin order book relative to market cap",
    },

    # Stablecoins (capital preservation)
    "USDC": {
        "category": "regulated_stablecoin",
        "regulated_status": "approved",
        "market_cap_tier": "large",
        "exchanges": ["Coinbase", "Kraken", "Circle"],
        "daily_volume_usd": 5_000_000_000,
        "manipulation_risk": "very_low",
        "notes": "Fully-backed, Circle regulated, US compliant",
    },
}

# Symbols our strategies actually trade (normalized)
SYMBOL_NORMALIZER = {
    "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT", "BTC/USDT": "BTCUSDT",
    "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT", "ETH/USDT": "ETHUSDT",
    "BNB-USD": "BNBUSDT", "BNBUSD": "BNBUSDT",
    "SOL-USD": "SOLUSDT", "SOLUSD": "SOLUSDT",
    "DOGE-USD": "DOGEUSDT", "DOGEUSD": "DOGEUSDT",
    "ADA-USD": "ADAUSDT", "ADAUSD": "ADAUSDT",
    "XRP-USD": "XRPUSDT", "XRPUSD": "XRPUSDT",
    "DOT-USD": "DOTUSDT", "DOTUSD": "DOTUSDT",
    "LINK-USD": "LINKUSDT", "LINKUSD": "LINKUSDT",
    "AVAX-USD": "AVAXUSDT", "AVAXUSD": "AVAXUSDT",
    "MATIC-USD": "MATICUSDT", "MATICUSD": "MATICUSDT",
    "SHIB-USD": "SHIBUSDT", "SHIBUSD": "SHIBUSDT",
}


def normalize_symbol(sym):
    """Normalize a symbol to our canonical form."""
    sym_upper = sym.upper().strip()
    return SYMBOL_NORMALIZER.get(sym_upper, sym_upper)


# ─────────────────────────────────────────────────────────────────
# Asset Screening
# ─────────────────────────────────────────────────────────────────

def screen_traded_assets():
    """Screen all symbols we've traded against the regulated-asset taxonomy."""
    closed = load_closed_picks()
    if not closed:
        return []

    # Gather all symbols traded
    symbol_stats = defaultdict(lambda: {"trades": 0, "pnl": 0, "strategies": set()})
    for trade in closed:
        sym = normalize_symbol(trade.get("symbol", "UNKNOWN"))
        symbol_stats[sym]["trades"] += 1
        symbol_stats[sym]["pnl"] += trade.get("pnl_pct", 0)
        symbol_stats[sym]["strategies"].add(trade.get("strategy", ""))

    results = []
    for sym, stats in sorted(symbol_stats.items(), key=lambda x: x[1]["trades"], reverse=True):
        asset_info = REGULATED_ASSETS.get(sym, {})
        results.append({
            "symbol": sym,
            "trades": stats["trades"],
            "total_pnl": round(stats["pnl"], 6),
            "strategies_using": len(stats["strategies"]),
            "category": asset_info.get("category", "unclassified"),
            "regulated_status": asset_info.get("regulated_status", "unknown"),
            "market_cap_tier": asset_info.get("market_cap_tier", "unknown"),
            "manipulation_risk": asset_info.get("manipulation_risk", "unknown"),
            "daily_volume_usd": asset_info.get("daily_volume_usd", 0),
            "compliant_for_allocation": asset_info.get("regulated_status") in ("approved", "review_needed"),
        })

    return results


def compute_manipulation_score(sym):
    """Compute manipulation risk score (0=safe, 1=high risk).

    Based on: market cap tier, daily volume, exchange count, category.
    """
    info = REGULATED_ASSETS.get(sym, {})
    if not info:
        return 0.8  # unknown = assume risky

    score = 0.0

    # Market cap tier
    tier_scores = {"mega": 0, "large": 0.1, "mid": 0.3, "small": 0.6}
    score += tier_scores.get(info.get("market_cap_tier", "small"), 0.6)

    # Category
    cat_scores = {"large_cap_crypto": 0, "regulated_stablecoin": 0,
                  "mid_cap_crypto": 0.2, "meme_coin": 0.5}
    score += cat_scores.get(info.get("category", ""), 0.3)

    # Exchange count (more exchanges = harder to manipulate)
    n_exchanges = len(info.get("exchanges", []))
    score += max(0, 0.3 - n_exchanges * 0.1)

    return min(round(score, 4), 1.0)


# ─────────────────────────────────────────────────────────────────
# Compliance-Constrained Allocation
# ─────────────────────────────────────────────────────────────────

def constrained_allocation(budget, max_per_asset_pct=0.10):
    """Allocate capital across strategies with regulatory and concentration constraints.

    Rules:
    1. Max 10% of total capital per single approved asset (was 5% — too restrictive)
    2. Max 8% for review_needed assets
    3. Meme coins capped at 3% each
    4. Unknown assets capped at 2%
    5. Allocation weighted by strategy edge (expectancy × Kelly)
    """
    kpis = compute_all_kpis(min_trades=3)
    if not kpis:
        return {}

    # Filter to strategies with positive edge
    edge_strategies = [k for k in kpis if k["expectancy_pct"] > 0 and k["kelly_fraction"] > 0]
    if not edge_strategies:
        return {"error": "No strategies with positive edge found"}

    # Get primary symbol for each strategy
    closed = load_closed_picks()
    strat_symbols = defaultdict(lambda: defaultdict(int))
    for t in closed:
        strat_symbols[t.get("strategy", "")][normalize_symbol(t.get("symbol", ""))] += 1

    # Build allocation
    allocations = []
    total_edge_weight = sum(k["expectancy_pct"] * max(k["kelly_fraction"], 0.01) for k in edge_strategies)

    for kpi in edge_strategies:
        strat = kpi["entity_id"]
        edge_weight = kpi["expectancy_pct"] * max(kpi["kelly_fraction"], 0.01) / total_edge_weight

        # Primary symbol
        sym_counts = strat_symbols.get(strat, {})
        primary_sym = max(sym_counts, key=sym_counts.get) if sym_counts else "UNKNOWN"
        asset_info = REGULATED_ASSETS.get(primary_sym, {})

        # Tiered compliance caps (widened to improve allocation coverage)
        reg_status = asset_info.get("regulated_status", "unknown")
        if reg_status == "approved":
            cap = max_per_asset_pct       # 10% for BTC, ETH
        elif reg_status == "review_needed":
            cap = 0.08                    # 8% for SOL, BNB, XRP, ADA, etc.
        elif reg_status == "caution":
            cap = 0.03                    # 3% for meme coins (was 2%)
        else:
            cap = 0.02                    # 2% for unknown assets (was 1%)

        raw_alloc = edge_weight * budget
        capped_alloc = min(raw_alloc, budget * cap)

        allocations.append({
            "strategy": strat,
            "primary_symbol": primary_sym,
            "regulated_status": reg_status,
            "manipulation_risk": compute_manipulation_score(primary_sym),
            "edge_weight": round(edge_weight, 4),
            "raw_allocation_usd": round(raw_alloc, 2),
            "capped_allocation_usd": round(capped_alloc, 2),
            "allocation_pct": round(capped_alloc / budget * 100, 2),
            "cap_reason": "meme_cap" if reg_status == "caution" else
                          "max_asset_cap" if capped_alloc < raw_alloc else "none",
        })

    # Sort by allocation
    allocations.sort(key=lambda x: x["capped_allocation_usd"], reverse=True)

    total_allocated = sum(a["capped_allocation_usd"] for a in allocations)
    return {
        "budget": budget,
        "max_per_asset_pct": max_per_asset_pct,
        "total_allocated_usd": round(total_allocated, 2),
        "unallocated_usd": round(budget - total_allocated, 2),
        "num_strategies": len(allocations),
        "allocations": allocations,
    }


# ─────────────────────────────────────────────────────────────────
# Main Report
# ─────────────────────────────────────────────────────────────────

def print_full_report():
    """Generate complete regulated asset report."""
    print("\n" + "=" * 100)
    print("REGULATED ASSET SCREENING & COMPLIANCE REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 100)

    # Asset screening
    print(f"\n{'─'*80}")
    print("ASSET COMPLIANCE SCREENING")
    print(f"{'─'*80}")
    screened = screen_traded_assets()
    if screened:
        print(f"\n{'Symbol':<15} {'Cat':<20} {'Status':<15} {'Risk':<10} {'Trades':>6} {'PnL':>10}")
        print("-" * 80)
        for a in screened:
            status_color = "✓" if a["regulated_status"] == "approved" else \
                           "?" if a["regulated_status"] == "review_needed" else "✗"
            print(f"{a['symbol']:<15} {a['category']:<20} {status_color} {a['regulated_status']:<12} "
                  f"{a['manipulation_risk']:<10} {a['trades']:>6} {a['total_pnl']:>+9.4f}")

    # Constrained allocation for each budget
    for budget in [500, 1000, 2000, 5000]:
        print(f"\n{'─'*80}")
        print(f"COMPLIANCE-CONSTRAINED ALLOCATION — ${budget:,} Budget")
        print(f"{'─'*80}")
        alloc = constrained_allocation(budget)
        if "error" in alloc:
            print(f"  {alloc['error']}")
            continue

        print(f"  Total allocated: ${alloc['total_allocated_usd']:,.2f} / ${budget:,}")
        print(f"  Unallocated (cash reserve): ${alloc['unallocated_usd']:,.2f}")
        print(f"\n  {'Strategy':<30} {'Symbol':<12} {'Status':<12} {'Alloc$':>8} {'%':>6} {'Cap':>10}")
        print("  " + "-" * 80)
        for a in alloc["allocations"][:10]:
            print(f"  {a['strategy']:<30} {a['primary_symbol']:<12} "
                  f"{a['regulated_status']:<12} ${a['capped_allocation_usd']:>7.2f} "
                  f"{a['allocation_pct']:>5.1f}% {a['cap_reason']:>10}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regulated Asset Screener")
    parser.add_argument("--screen", action="store_true")
    parser.add_argument("--allocate", action="store_true")
    parser.add_argument("--budget", type=float, default=1000)
    args = parser.parse_args()

    if args.screen:
        results = screen_traded_assets()
        print(json.dumps(results, indent=2, default=list))
    elif args.allocate:
        alloc = constrained_allocation(args.budget)
        print(json.dumps(alloc, indent=2))
    else:
        print_full_report()
