#!/usr/bin/env python3
"""
Consensus Backtester - Historical Consensus vs Individual Performance
=====================================================================
Mercury Recommendation #3: Backtest whether consensus signals (2+ traders
holding the same symbol in the same direction) outperform individual picks.

Loads all per-exchange pick files and qualified_traders.json, identifies
consensus events, computes aggregate metrics, and builds a trader pair matrix.

Usage:
    python copy_trader_intel/consensus_backtester.py
"""

import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from itertools import combinations

# Fix Windows charmap encoding - force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"

# All per-exchange pick files to scan
PICK_FILES = [
    "active_picks.json",
    "okx_picks.json",
    "bybit_picks.json",
    "bitget_picks.json",
    "bingx_picks.json",
    "gate_picks.json",
    "copin_picks.json",
    "dydx_picks.json",
    "gmx_picks.json",
    "gains_picks.json",
    "dex_picks.json",
    "dex_whale_picks.json",
]

# Binance price API with failover chain
PRICE_APIS = [
    "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api2.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
    "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}",
]


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to consistent format (e.g., BTCUSDT)."""
    s = symbol.upper().strip()
    # Remove common suffixes/prefixes
    for suffix in ["-SWAP", "-PERP", "_PERP", ".P"]:
        s = s.replace(suffix, "")
    # Normalize separators
    s = s.replace("-", "").replace("/", "").replace("_", "")
    # Ensure USDT suffix for common pairs
    if s in ("BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK",
             "DOT", "MATIC", "UNI", "AAVE", "NEAR", "ARB", "OP", "SUI",
             "APT", "SEI", "TIA", "INJ", "HYPE", "WIF", "JUP", "PEPE"):
        s += "USDT"
    return s


def extract_trader_id(pick: dict) -> str:
    """Extract a unique trader identifier from a pick."""
    # Try trader_name first (CEX), then strategy, then trader_address (on-chain)
    if pick.get("trader_name"):
        source = pick.get("source_system", "unknown")
        return f"{source}:{pick['trader_name']}"
    if pick.get("trader_address"):
        return f"hl:{pick['trader_address'][:10]}"
    if pick.get("strategy"):
        return pick["strategy"]
    return f"unknown:{pick.get('id', 'no_id')}"


def get_current_price(symbol: str) -> float:
    """Fetch current price with failover chain."""
    try:
        import requests
    except ImportError:
        return 0.0

    norm = normalize_symbol(symbol)

    # Try Binance mirrors first
    for url_template in PRICE_APIS[:3]:
        try:
            url = url_template.format(symbol=norm)
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("price", 0))
        except Exception:
            continue

    # CoinGecko fallback
    cg_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
              "XRP": "ripple", "DOGE": "dogecoin", "AVAX": "avalanche-2"}
    base = norm.replace("USDT", "").replace("USD", "")
    cg_id = cg_map.get(base)
    if cg_id:
        try:
            url = PRICE_APIS[3].format(cg_id=cg_id)
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get(cg_id, {}).get("usd", 0))
        except Exception:
            pass

    # KuCoin fallback
    try:
        kucoin_sym = f"{base}-USDT"
        url = PRICE_APIS[4].format(kucoin_symbol=kucoin_sym)
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("data", {}).get("price", 0))
    except Exception:
        pass

    return 0.0


def load_all_picks() -> list:
    """Load picks from all exchange files, deduplicating by id."""
    all_picks = []
    seen_ids = set()

    for filename in PICK_FILES:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict) and "picks" in data:
                picks = data["picks"]
            else:
                continue

            for pick in picks:
                pick_id = pick.get("id", "")
                # Deduplicate across files (active_picks.json aggregates others)
                if pick_id and pick_id in seen_ids:
                    continue
                if pick_id:
                    seen_ids.add(pick_id)
                # Tag which file it came from
                if "source_file" not in pick:
                    pick["source_file"] = filename
                all_picks.append(pick)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  [WARN] Failed to load {filename}: {e}")

    return all_picks


def load_qualified_traders() -> dict:
    """Load qualified traders data, keyed by address/label."""
    filepath = DATA_DIR / "qualified_traders.json"
    if not filepath.exists():
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        traders = data.get("traders", []) if isinstance(data, dict) else data
        result = {}
        for t in traders:
            key = t.get("label") or t.get("address", "unknown")
            result[key] = t
        return result
    except (json.JSONDecodeError, IOError):
        return {}


def estimate_pick_outcome(pick: dict, current_prices: dict) -> dict:
    """
    Estimate whether a pick hit TP, SL, or is still open.
    Returns dict with: resolved (bool), won (bool), pnl_pct (float).
    """
    status = pick.get("status", "OPEN").upper()
    symbol = normalize_symbol(pick.get("symbol", ""))
    direction = pick.get("direction", "LONG").upper()
    entry_price = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)

    # Already resolved
    if pick.get("exit_price") is not None and pick.get("pnl_pct") is not None:
        pnl = pick["pnl_pct"]
        return {"resolved": True, "won": pnl > 0, "pnl_pct": pnl}

    if status in ("CLOSED", "HIT_TP", "HIT_SL", "STOPPED"):
        pnl = pick.get("pnl_pct", 0) or 0
        won = status == "HIT_TP" or pnl > 0
        return {"resolved": True, "won": won, "pnl_pct": pnl}

    # For open picks, estimate using current price
    if not entry_price or entry_price == 0:
        return {"resolved": False, "won": False, "pnl_pct": 0}

    current = current_prices.get(symbol, 0)
    if current == 0:
        # Use unrealized PnL if available
        unrealized = pick.get("unrealized_pnl", 0)
        if unrealized and unrealized != 0:
            # Approximate PnL % from unrealized dollar amount
            alloc = pick.get("allocation", 200.0)
            pnl_pct = (unrealized / alloc * 100) if alloc > 0 else 0
            return {"resolved": False, "won": unrealized > 0, "pnl_pct": pnl_pct}
        return {"resolved": False, "won": False, "pnl_pct": 0}

    # Calculate unrealized PnL
    if direction == "LONG":
        pnl_pct = ((current - entry_price) / entry_price) * 100
        # Check if TP or SL would have been hit
        if tp and current >= tp:
            pnl_pct = ((tp - entry_price) / entry_price) * 100
            return {"resolved": True, "won": True, "pnl_pct": pnl_pct}
        if sl and current <= sl:
            pnl_pct = ((sl - entry_price) / entry_price) * 100
            return {"resolved": True, "won": False, "pnl_pct": pnl_pct}
    else:  # SHORT
        pnl_pct = ((entry_price - current) / entry_price) * 100
        if tp and current <= tp:
            pnl_pct = ((entry_price - tp) / entry_price) * 100
            return {"resolved": True, "won": True, "pnl_pct": pnl_pct}
        if sl and current >= sl:
            pnl_pct = ((entry_price - sl) / entry_price) * 100
            return {"resolved": True, "won": False, "pnl_pct": pnl_pct}

    return {"resolved": False, "won": pnl_pct > 0, "pnl_pct": pnl_pct}


def identify_consensus_groups(picks: list) -> tuple:
    """
    Group picks by (symbol, direction) to find consensus events.
    Returns (consensus_picks, individual_picks) where consensus = 2+ traders
    on the same symbol+direction.
    """
    # Group by (normalized_symbol, direction)
    groups = defaultdict(list)
    for pick in picks:
        symbol = normalize_symbol(pick.get("symbol", ""))
        direction = pick.get("direction", "LONG").upper()
        if not symbol:
            continue
        key = (symbol, direction)
        groups[key].append(pick)

    consensus_picks = []
    individual_picks = []

    for (symbol, direction), group in groups.items():
        # Deduplicate by trader within each group
        trader_picks = {}
        for pick in group:
            trader_id = extract_trader_id(pick)
            # Keep the pick with highest confidence per trader
            if trader_id not in trader_picks:
                trader_picks[trader_id] = pick
            else:
                existing_conf = trader_picks[trader_id].get("confidence", 0)
                new_conf = pick.get("confidence", 0)
                if new_conf > existing_conf:
                    trader_picks[trader_id] = pick

        unique_traders = list(trader_picks.keys())
        unique_picks = list(trader_picks.values())

        if len(unique_traders) >= 2:
            # Mark as consensus with metadata
            for pick in unique_picks:
                pick["_consensus"] = True
                pick["_consensus_count"] = len(unique_traders)
                pick["_consensus_traders"] = unique_traders
                pick["_norm_symbol"] = symbol
            consensus_picks.extend(unique_picks)
        else:
            for pick in unique_picks:
                pick["_consensus"] = False
                pick["_consensus_count"] = 1
                pick["_norm_symbol"] = symbol
            individual_picks.extend(unique_picks)

    return consensus_picks, individual_picks


def compute_metrics(picks: list, outcomes: dict) -> dict:
    """Compute aggregate metrics for a set of picks."""
    total = 0
    wins = 0
    losses = 0
    total_pnl = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    pnl_list = []
    resolved_count = 0

    for pick in picks:
        pick_id = id(pick)  # Use object id since dict IDs can duplicate
        outcome = outcomes.get(pick_id, {})
        pnl_pct = outcome.get("pnl_pct", 0)
        total += 1
        total_pnl += pnl_pct
        pnl_list.append(pnl_pct)

        if outcome.get("resolved"):
            resolved_count += 1

        if outcome.get("won"):
            wins += 1
            gross_profit += abs(pnl_pct)
        elif pnl_pct < 0:
            losses += 1
            gross_loss += abs(pnl_pct)

    win_rate = (wins / total * 100) if total > 0 else 0
    avg_pnl = (total_pnl / total) if total > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
        99.99 if gross_profit > 0 else 0
    )
    avg_win = (gross_profit / wins) if wins > 0 else 0
    avg_loss = (gross_loss / losses) if losses > 0 else 0

    return {
        "total_picks": total,
        "resolved_picks": resolved_count,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "avg_pnl_pct": round(avg_pnl, 4),
        "total_pnl_pct": round(total_pnl, 4),
        "profit_factor": round(profit_factor, 2),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "best_pnl_pct": round(max(pnl_list), 4) if pnl_list else 0,
        "worst_pnl_pct": round(min(pnl_list), 4) if pnl_list else 0,
    }


def build_trader_pair_matrix(picks: list, outcomes: dict) -> dict:
    """
    For all trader pairs, compute agreement frequency and performance.
    Returns dict with pair stats.
    """
    # Map each trader to their picks by (symbol, direction)
    trader_positions = defaultdict(dict)  # trader_id -> {(sym, dir): pick}
    for pick in picks:
        trader_id = extract_trader_id(pick)
        symbol = normalize_symbol(pick.get("symbol", ""))
        direction = pick.get("direction", "LONG").upper()
        if not symbol:
            continue
        key = (symbol, direction)
        # Keep highest confidence pick per position
        if key not in trader_positions[trader_id]:
            trader_positions[trader_id][key] = pick
        else:
            if pick.get("confidence", 0) > trader_positions[trader_id][key].get("confidence", 0):
                trader_positions[trader_id][key] = pick

    all_traders = list(trader_positions.keys())
    if len(all_traders) < 2:
        return {"pairs": [], "best_pairs": []}

    pair_stats = []

    for t1, t2 in combinations(all_traders, 2):
        positions_t1 = set(trader_positions[t1].keys())
        positions_t2 = set(trader_positions[t2].keys())

        agreements = positions_t1 & positions_t2
        if not agreements:
            continue

        # Compute metrics when they agree
        agree_wins = 0
        agree_total = 0
        agree_pnl = 0.0

        for pos_key in agreements:
            pick1 = trader_positions[t1][pos_key]
            pick2 = trader_positions[t2][pos_key]
            out1 = outcomes.get(id(pick1), {})
            out2 = outcomes.get(id(pick2), {})

            # Average outcome of the pair
            avg_pnl = (out1.get("pnl_pct", 0) + out2.get("pnl_pct", 0)) / 2
            either_won = out1.get("won", False) or out2.get("won", False)
            both_won = out1.get("won", False) and out2.get("won", False)

            agree_total += 1
            agree_pnl += avg_pnl
            if both_won:
                agree_wins += 1

        # Compute solo metrics (positions where only one trader is in)
        solo_t1 = positions_t1 - positions_t2
        solo_t2 = positions_t2 - positions_t1
        solo_wins = 0
        solo_total = 0
        solo_pnl = 0.0

        for pos_key in solo_t1:
            pick = trader_positions[t1][pos_key]
            out = outcomes.get(id(pick), {})
            solo_total += 1
            solo_pnl += out.get("pnl_pct", 0)
            if out.get("won", False):
                solo_wins += 1

        for pos_key in solo_t2:
            pick = trader_positions[t2][pos_key]
            out = outcomes.get(id(pick), {})
            solo_total += 1
            solo_pnl += out.get("pnl_pct", 0)
            if out.get("won", False):
                solo_wins += 1

        agree_wr = (agree_wins / agree_total * 100) if agree_total > 0 else 0
        solo_wr = (solo_wins / solo_total * 100) if solo_total > 0 else 0
        wr_boost = agree_wr - solo_wr

        pair_stats.append({
            "trader_1": t1,
            "trader_2": t2,
            "agreement_count": agree_total,
            "agreement_symbols": [f"{s} {d}" for s, d in agreements],
            "agree_win_rate_pct": round(agree_wr, 2),
            "agree_avg_pnl_pct": round(agree_pnl / agree_total, 4) if agree_total > 0 else 0,
            "solo_win_rate_pct": round(solo_wr, 2),
            "solo_avg_pnl_pct": round(solo_pnl / solo_total, 4) if solo_total > 0 else 0,
            "wr_boost_pct": round(wr_boost, 2),
        })

    # Sort by agreement win rate, then by agreement count
    pair_stats.sort(key=lambda x: (x["agree_win_rate_pct"], x["agreement_count"]), reverse=True)

    # Top 5 best pairs
    best_pairs = pair_stats[:5]

    return {
        "pairs": pair_stats,
        "best_pairs": best_pairs,
    }


def fetch_prices_batch(symbols: list) -> dict:
    """Fetch current prices for all unique symbols."""
    prices = {}

    # Skip fetching if --no-fetch mode
    if os.environ.get("CONSENSUS_NO_FETCH"):
        print("\n  [--no-fetch] Skipping price fetching, using unrealized PnL only")
        return prices

    unique_symbols = list(set(symbols))

    print(f"\n  Fetching prices for {len(unique_symbols)} symbols...")
    for i, sym in enumerate(unique_symbols):
        if i > 0 and i % 5 == 0:
            time.sleep(0.3)  # Rate limit
        try:
            price = get_current_price(sym)
            if price > 0:
                prices[sym] = price
        except Exception:
            continue

    print(f"  Got prices for {len(prices)}/{len(unique_symbols)} symbols")
    return prices


def run_backtest():
    """Main backtest entry point."""
    print("=" * 65)
    print("  CONSENSUS BACKTESTER - Historical Consensus vs Individual")
    print("=" * 65)

    # 1. Load all data
    print("\n[1/5] Loading pick data...")
    all_picks = load_all_picks()
    qualified = load_qualified_traders()
    print(f"  Loaded {len(all_picks)} total picks from {len(PICK_FILES)} files")
    print(f"  Loaded {len(qualified)} qualified traders")

    if not all_picks:
        print("\n  [ERROR] No picks found. Run the copy trader scanner first.")
        return

    # 2. Fetch current prices for open positions
    print("\n[2/5] Fetching current prices for outcome estimation...")
    symbols = [normalize_symbol(p.get("symbol", "")) for p in all_picks if p.get("symbol")]
    current_prices = fetch_prices_batch(symbols)

    # 3. Estimate outcomes for all picks
    print("\n[3/5] Estimating pick outcomes...")
    outcomes = {}
    for pick in all_picks:
        outcome = estimate_pick_outcome(pick, current_prices)
        outcomes[id(pick)] = outcome

    resolved = sum(1 for o in outcomes.values() if o.get("resolved"))
    winning = sum(1 for o in outcomes.values() if o.get("won"))
    print(f"  Resolved: {resolved}/{len(all_picks)} | Winning: {winning}/{len(all_picks)}")

    # 4. Identify consensus vs individual
    print("\n[4/5] Identifying consensus groups...")
    consensus_picks, individual_picks = identify_consensus_groups(all_picks)
    print(f"  Consensus picks (2+ traders agree): {len(consensus_picks)}")
    print(f"  Individual picks (solo trader):     {len(individual_picks)}")

    # Compute metrics
    consensus_metrics = compute_metrics(consensus_picks, outcomes)
    individual_metrics = compute_metrics(individual_picks, outcomes)

    # Consensus boost
    wr_boost = consensus_metrics["win_rate_pct"] - individual_metrics["win_rate_pct"]
    pnl_boost = consensus_metrics["avg_pnl_pct"] - individual_metrics["avg_pnl_pct"]
    pf_boost = consensus_metrics["profit_factor"] - individual_metrics["profit_factor"]

    # 5. Build trader pair matrix
    print("\n[5/5] Building trader pair matrix...")
    pair_matrix = build_trader_pair_matrix(all_picks, outcomes)
    print(f"  Found {len(pair_matrix['pairs'])} trader pairs with agreements")

    # Build consensus signal details
    consensus_signals = defaultdict(list)
    for pick in consensus_picks:
        sym = pick.get("_norm_symbol", "")
        direction = pick.get("direction", "")
        key = f"{sym} {direction}"
        trader_id = extract_trader_id(pick)
        consensus_signals[key].append({
            "trader": trader_id,
            "entry_price": pick.get("entry_price", 0),
            "confidence": pick.get("confidence", 0),
        })

    # Compile results
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks_analyzed": len(all_picks),
        "consensus_vs_individual": {
            "consensus": {
                **consensus_metrics,
                "description": "Picks where 2+ traders held the same symbol in the same direction",
            },
            "individual": {
                **individual_metrics,
                "description": "Picks where only 1 trader held the position (no agreement)",
            },
            "comparison": {
                "win_rate_boost_pct": round(wr_boost, 2),
                "avg_pnl_boost_pct": round(pnl_boost, 4),
                "profit_factor_boost": round(pf_boost, 2),
                "consensus_is_better": wr_boost > 0 or pnl_boost > 0,
            },
        },
        "consensus_signals": {k: v for k, v in consensus_signals.items()},
        "trader_pairs": pair_matrix["pairs"],
        "best_pairs": pair_matrix["best_pairs"],
        "consensus_win_rate_boost": round(wr_boost, 2),
    }

    # Save results
    output_path = DATA_DIR / "consensus_backtest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  [OK] Results saved to {output_path}")

    # Print summary table
    print_summary(results)

    return results


def print_summary(results: dict):
    """Print formatted summary table to CLI."""
    cvi = results["consensus_vs_individual"]
    cons = cvi["consensus"]
    indiv = cvi["individual"]
    comp = cvi["comparison"]

    print("\n" + "=" * 65)
    print("  BACKTEST RESULTS SUMMARY")
    print("=" * 65)

    # Consensus vs Individual comparison table
    header = f"  {'Metric':<25} {'Consensus':>15} {'Individual':>15}"
    print(header)
    print("  " + "-" * 55)

    rows = [
        ("Total Picks", cons["total_picks"], indiv["total_picks"]),
        ("Win Rate %", f"{cons['win_rate_pct']:.1f}%", f"{indiv['win_rate_pct']:.1f}%"),
        ("Avg PnL %", f"{cons['avg_pnl_pct']:.2f}%", f"{indiv['avg_pnl_pct']:.2f}%"),
        ("Profit Factor", f"{cons['profit_factor']:.2f}", f"{indiv['profit_factor']:.2f}"),
        ("Best Trade %", f"{cons['best_pnl_pct']:.2f}%", f"{indiv['best_pnl_pct']:.2f}%"),
        ("Worst Trade %", f"{cons['worst_pnl_pct']:.2f}%", f"{indiv['worst_pnl_pct']:.2f}%"),
    ]

    for label, c_val, i_val in rows:
        print(f"  {label:<25} {str(c_val):>15} {str(i_val):>15}")

    # Boost summary
    print("\n  " + "-" * 55)
    verdict = "[OK] CONSENSUS OUTPERFORMS" if comp["consensus_is_better"] else "[WARN] INDIVIDUAL OUTPERFORMS"
    print(f"  {verdict}")
    print(f"  Win Rate Boost:    {comp['win_rate_boost_pct']:+.2f} pp")
    print(f"  Avg PnL Boost:     {comp['avg_pnl_boost_pct']:+.4f}%")
    print(f"  Profit Factor +/-: {comp['profit_factor_boost']:+.2f}")

    # Top trader pairs
    best = results.get("best_pairs", [])
    if best:
        print("\n" + "=" * 65)
        print("  TOP 5 TRADER PAIRS (by agreement win rate)")
        print("=" * 65)
        print(f"  {'Pair':<40} {'Agree':>5} {'WR%':>7} {'Boost':>7}")
        print("  " + "-" * 60)

        for pair in best[:5]:
            t1_short = pair["trader_1"][-20:] if len(pair["trader_1"]) > 20 else pair["trader_1"]
            t2_short = pair["trader_2"][-20:] if len(pair["trader_2"]) > 20 else pair["trader_2"]
            pair_label = f"{t1_short} + {t2_short}"
            if len(pair_label) > 39:
                pair_label = pair_label[:36] + "..."
            print(f"  {pair_label:<40} {pair['agreement_count']:>5} "
                  f"{pair['agree_win_rate_pct']:>6.1f}% {pair['wr_boost_pct']:>+6.1f}%")

        # Show what symbols the best pair agrees on
        if best:
            top_pair = best[0]
            syms = ", ".join(top_pair.get("agreement_symbols", [])[:5])
            print(f"\n  Best pair agrees on: {syms}")

    print("\n" + "=" * 65)
    print(f"  Total picks analyzed: {results['total_picks_analyzed']}")
    print(f"  Total trader pairs:   {len(results.get('trader_pairs', []))}")
    print(f"  Consensus WR boost:   {results['consensus_win_rate_boost']:+.2f} pp")
    print("=" * 65)


if __name__ == "__main__":
    # Support --no-fetch flag to skip price fetching (uses unrealized PnL only)
    if "--no-fetch" in sys.argv:
        os.environ["CONSENSUS_NO_FETCH"] = "1"
    run_backtest()
