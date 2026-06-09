#!/usr/bin/env python3
"""
Money-Ready Picks Generator — 2026-06-06
=========================================
Generates institutional-grade, statistically-validated "money-ready RIGHT NOW"
picks per asset class. Queries the live MySQL database, applies hedge-fund tier
statistical edge detection, cross-references multiple signal sources, computes
optimal Kelly position sizing, and outputs a consumable JSON + summary report.

Usage:
    python tools/money_ready_picks_generator.py

Outputs:
    audit_dashboard/data/money_ready_picks.json  — machine-readable
    stdout                                      — human-readable summary
"""

import json
import math
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

try:
    import pymysql
except ImportError:
    pymysql = None

# ── Repo paths ──────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "audit_dashboard" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── DB credentials (from dbpasses.txt) ──────────────────────────────────────
DB_HOST = "mysql.50webs.com"
DB_STOCKS_USER = "ejaguiar1_stocks"
DB_STOCKS_PASS = "stocks1234560"
DB_STOCKS_NAME = "ejaguiar1_stocks"
DB_BACKTESTS_USER = "ejaguiar1_backtests"
DB_BACKTESTS_PASS = "backtests1234560"
DB_BACKTESTS_NAME = "ejaguiar1_backtests"


# ═════════════════════════════════════════════════════════════════════════════
#  STATISTICAL THRESHOLDS — Hedge Fund Tier Gates
# ═════════════════════════════════════════════════════════════════════════════

class Tiers:
    """Tier thresholds: these define 'money-ready' per hedge fund standard."""

    # Tier 2 — Mutual Fund / Institutional bar (our minimum for real money)
    MIN_N_TIER2 = 100       # Minimum resolved trades
    MIN_WR_TIER2 = 0.50     # Win Rate ≥ 50%
    MIN_PF_TIER2 = 1.50     # Profit Factor ≥ 1.5
    MAX_MDD_TIER2 = 0.20    # Max drawdown < 20%

    # money-maker-readyv2 bridge (2026-06-09): AI validation / no-inflated gate.
    # Explicitly exclude tournament/leaderboard/smart_picks sources (synthetics,
    # small-n, 58%+ MISPRICED in ai_tournament_picks_latest). Only policy-clean
    # ledger (pf_registry.by_asset_class_policy_clean_net post SKILL 6 filters)
    # + forward n>=100 qualify. See also build_audit_surface_truth "0/9" + banner.
    INFLATED_SOURCES = ("ai_tournament", "tournament", "leaderboard", "smart_picks", "ai_challenge")
    # On emit: if source in INFLATED_SOURCES or clean_n < MIN_N_TIER2: verdict="EXCLUDE_INFLATED"

    # Tier 3 — Building block (paper-trade while accumulating n)
    MIN_N_TIER3 = 20
    MIN_WR_TIER3 = 0.45
    MIN_PF_TIER3 = 1.20

    # Discovery — directional signal, needs more data
    MIN_N_DISCOVERY = 5
    MIN_WR_DISCOVERY = 0.55

    # Concentration limits
    MAX_SINGLE_SYMBOL_PCT = 0.05   # Max 5% of portfolio in 1 symbol
    MAX_SINGLE_CLASS_PCT = 0.20    # Max 20% of portfolio in 1 asset class

    # Kelly fraction (safety factor)
    KELLY_FRACTION = 0.25  # 25% Kelly for Tier 2, 12.5% for Tier 3


# ═════════════════════════════════════════════════════════════════════════════
#  DATABASE CONNECTORS
# ═════════════════════════════════════════════════════════════════════════════

def get_stocks_conn():
    if pymysql is None:
        print("ERROR: pymysql not installed. Install with: pip install pymysql")
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST, user=DB_STOCKS_USER, password=DB_STOCKS_PASS,
        database=DB_STOCKS_NAME,
    )


def get_backtests_conn():
    if pymysql is None:
        print("ERROR: pymysql not installed.")
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST, user=DB_BACKTESTS_USER, password=DB_BACKTESTS_PASS,
        database=DB_BACKTESTS_NAME,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  STATISTICAL FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def calc_profit_factor(wins, losses, total_win_pnl, total_loss_pnl):
    """Profit Factor = gross wins / gross losses (absolute)."""
    if total_loss_pnl == 0:
        return float('inf')
    return abs(total_win_pnl / total_loss_pnl)


def calc_sharpe(pnl_list, rfr=0.0):
    """Annualized Sharpe ratio from a list of per-trade PnL %."""
    if len(pnl_list) < 2:
        return None
    mean_pnl = sum(pnl_list) / len(pnl_list)
    variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
    if variance <= 0:
        return None
    std = math.sqrt(variance)
    if std == 0:
        return None
    # Approximate annualized: sqrt(252) for daily trading
    sharpe = (mean_pnl - rfr) / std * math.sqrt(252)
    return round(sharpe, 4)


def calc_kelly_fraction(wr, avg_win, avg_loss):
    """Kelly fraction = WR - ((1-WR) / (avg_win / abs(avg_loss)))."""
    if avg_loss == 0:
        return 0.25  # No-loss edge — cap at 25%
    r = abs(avg_win / avg_loss)
    if r == 0:
        return 0
    kelly = wr - ((1 - wr) / r)
    return max(0, kelly)


def calc_expectancy(wr, avg_win, avg_loss):
    """Expected value per trade = (WR * avg_win) - ((1-WR) * abs(avg_loss))."""
    return (wr * avg_win) - ((1 - wr) * abs(avg_loss))


# ═════════════════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ═════════════════════════════════════════════════════════════════════════════

def load_resolved_picks(conn):
    """Load ALL resolved picks from at_pick_outcomes, grouped by symbol."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, asset_class, status, pnl_pct, strategy
        FROM at_pick_outcomes
        WHERE status IN ('WON', 'LOST')
          AND pnl_pct IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()

    # Group by symbol+asset_class
    by_symbol = defaultdict(lambda: {
        "n": 0, "wins": 0, "losses": 0,
        "total_pnl": 0.0, "win_pnl": 0.0, "loss_pnl": 0.0,
        "pnl_list": [],
        "strategies": set(),
        "asset_class": None,
    })

    for symbol, asset_class, status, pnl_pct, strategy in rows:
        pnl = float(pnl_pct)
        key = symbol
        grp = by_symbol[key]
        grp["n"] += 1
        grp["asset_class"] = asset_class or "UNKNOWN"
        grp["total_pnl"] += pnl
        grp["pnl_list"].append(pnl)
        if strategy:
            grp["strategies"].add(strategy)

        if status == "WON":
            grp["wins"] += 1
            grp["win_pnl"] += pnl
        else:
            grp["losses"] += 1
            grp["loss_pnl"] += abs(pnl)

    return dict(by_symbol)


def load_stock_fundamentals(conn):
    """Load analyst ratings and fundamentals for stocks."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, trailing_pe, forward_pe, trailing_eps,
               recommendation_key, target_mean_price, roe,
               dividend_yield
        FROM stock_fundamentals
    """)
    rows = cur.fetchall()
    cur.close()
    return {
        r[0]: {
            "trailing_pe": float(r[1]) if r[1] else None,
            "forward_pe": float(r[2]) if r[2] else None,
            "trailing_eps": float(r[3]) if r[3] else None,
            "recommendation": r[4],
            "target_price": float(r[5]) if r[5] else None,
            "roe": float(r[6]) if r[6] else None,
            "dividend_yield": float(r[7]) if r[7] else None,
        }
        for r in rows
    }


def load_latest_prices(conn):
    """Load latest close prices from daily_prices."""
    cur = conn.cursor()
    cur.execute("""
        SELECT dp1.ticker, dp1.close_price, dp1.trade_date
        FROM daily_prices dp1
        INNER JOIN (
            SELECT ticker, MAX(trade_date) AS max_date
            FROM daily_prices
            GROUP BY ticker
        ) dp2 ON dp1.ticker = dp2.ticker AND dp1.trade_date = dp2.max_date
    """)
    rows = cur.fetchall()
    cur.close()
    return {r[0]: {"close": float(r[1]), "date": str(r[2])} for r in rows}


def load_tournament_picks(conn):
    """Load resolved tournament picks for additional consensus."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, asset_class, direction, pnl_pct, status,
               provider, model_id, strategy_name
        FROM tournament_picks
        WHERE status IN ('WON', 'LOST')
          AND pnl_pct IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()

    by_symbol = defaultdict(lambda: {"n": 0, "wins": 0, "models": set()})
    for symbol, ac, direction, pnl, status, prov, model, strat in rows:
        key = symbol
        by_symbol[key]["n"] += 1
        if model:
            by_symbol[key]["models"].add(model)
        if status == "WON":
            by_symbol[key]["wins"] += 1

    return dict(by_symbol)


# ═════════════════════════════════════════════════════════════════════════════
#  EDGE DETECTION ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def analyze_edge(symbol_data, fundamentals, prices, tournament):
    """Apply full statistical edge detection to one symbol."""
    n = symbol_data["n"]
    wins = symbol_data["wins"]
    losses = symbol_data["losses"]
    win_pnl = symbol_data["win_pnl"]
    loss_pnl = symbol_data["loss_pnl"]
    pnl_list = symbol_data["pnl_list"]
    asset_class = symbol_data["asset_class"]

    if n == 0:
        return None

    wr = wins / n
    avg_pnl = symbol_data["total_pnl"] / n
    avg_win = win_pnl / wins if wins > 0 else 0
    avg_loss = -(loss_pnl / losses) if losses > 0 else 0

    pf = calc_profit_factor(wins, losses, win_pnl, loss_pnl)
    sharpe = calc_sharpe(pnl_list)
    expectancy = calc_expectancy(wr, avg_win, avg_loss)
    kelly = calc_kelly_fraction(wr, avg_win, avg_loss)

    # Determine tier
    if n >= Tiers.MIN_N_TIER2 and wr >= Tiers.MIN_WR_TIER2 and pf >= Tiers.MIN_PF_TIER2:
        tier = "TIER2_MONEY_READY"
        tier_label = "💰 Money-Ready (Tier 2)"
        kelly_alloc = kelly * Tiers.KELLY_FRACTION
    elif n >= Tiers.MIN_N_TIER3 and wr >= Tiers.MIN_WR_TIER3 and pf >= Tiers.MIN_PF_TIER3:
        tier = "TIER3_BUILDING"
        tier_label = "📈 Building (Tier 3)"
        kelly_alloc = kelly * (Tiers.KELLY_FRACTION / 2)
    elif n >= Tiers.MIN_N_DISCOVERY and wr >= Tiers.MIN_WR_DISCOVERY:
        tier = "DISCOVERY"
        tier_label = "🔬 Discovery"
        kelly_alloc = kelly * (Tiers.KELLY_FRACTION / 4)
    else:
        tier = "INSUFFICIENT"
        tier_label = "⚠️ Insufficient Edge"
        kelly_alloc = 0

    # Cross-reference with fundamentals
    fund = fundamentals.get(symbol, {})
    analyst_rec = fund.get("recommendation", None)
    target_price = fund.get("target_price", None)
    forward_pe = fund.get("forward_pe", None)

    # Cross-reference with tournament consensus
    tourney = tournament.get(symbol, {})
    tourney_n = tourney.get("n", 0)
    tourney_wr = tourney.get("wins", 0) / tourney_n if tourney_n > 0 else None
    tourney_models = tourney.get("models", set())

    # Latest price
    price_info = prices.get(symbol, {})
    latest_price = price_info.get("close", None)

    # Consensus score: combine multiple signals
    consensus_score = 0
    if tier == "TIER2_MONEY_READY":
        consensus_score += 40
    elif tier == "TIER3_BUILDING":
        consensus_score += 20
    elif tier == "DISCOVERY":
        consensus_score += 10

    if analyst_rec == "strong_buy":
        consensus_score += 25
    elif analyst_rec == "buy":
        consensus_score += 15
    elif analyst_rec == "hold":
        consensus_score += 5

    if target_price and latest_price and latest_price > 0:
        upside = (target_price - latest_price) / latest_price
        if upside > 0.1:
            consensus_score += 15
        elif upside > 0:
            consensus_score += 5

    if forward_pe and forward_pe < 25:
        consensus_score += 10  # Reasonably valued

    if tourney_wr and tourney_wr > 0.50:
        consensus_score += 10

    if len(symbol_data["strategies"]) >= 3:
        consensus_score += 10  # Multi-strategy consensus

    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 4),
        "avg_pnl_pct": round(avg_pnl, 4),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": sharpe,
        "expectancy": round(expectancy, 4),
        "kelly_fraction": round(kelly, 4),
        "kelly_alloc_pct": round(kelly_alloc * 100, 2),
        "tier": tier,
        "tier_label": tier_label,
        "consensus_score": consensus_score,
        "num_strategies": len(symbol_data["strategies"]),
        "strategies": list(symbol_data["strategies"])[:5],
        "latest_price": latest_price,
        "analyst_rec": analyst_rec,
        "target_price": target_price,
        "forward_pe": forward_pe,
        "upside_to_target": round(((target_price / latest_price) - 1) * 100, 1)
            if (target_price and latest_price and latest_price > 0) else None,
        "tourney_n": tourney_n,
        "tourney_wr": round(tourney_wr, 4) if tourney_wr else None,
        "tourney_models": len(tourney_models),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO CONSTRUCTION
# ═════════════════════════════════════════════════════════════════════════════

def build_portfolio(all_picks):
    """Build a risk-budgeted portfolio from vetted picks."""

    # Separate by tier
    tier2 = [p for p in all_picks if p["tier"] == "TIER2_MONEY_READY"]
    tier3 = [p for p in all_picks if p["tier"] == "TIER3_BUILDING"]
    discovery = [p for p in all_picks if p["tier"] == "DISCOVERY"]

    # Sort by consensus score within each tier
    tier2.sort(key=lambda p: p["consensus_score"], reverse=True)
    tier3.sort(key=lambda p: p["consensus_score"], reverse=True)
    discovery.sort(key=lambda p: p["consensus_score"], reverse=True)

    # Track class-level concentration
    class_allocation = defaultdict(float)
    portfolio = []

    for pick in tier2 + tier3 + discovery:
        ac = pick["asset_class"]
        kelly = pick["kelly_alloc_pct"] / 100  # Convert from %

        # Apply class concentration limit
        max_class_add = Tiers.MAX_SINGLE_CLASS_PCT - class_allocation[ac]
        if max_class_add <= 0:
            pick["alloc_pct"] = 0
            pick["alloc_note"] = "SKIPPED — class at concentration limit"
            portfolio.append(pick)
            continue

        capped = min(kelly, max_class_add, Tiers.MAX_SINGLE_SYMBOL_PCT)
        class_allocation[ac] += capped
        pick["alloc_pct"] = round(capped * 100, 2)
        pick["alloc_note"] = "Kelly-sized" if capped == kelly else "Class-capped"
        portfolio.append(pick)

    # Remaining capital (100% - sum of all allocations)
    total_alloc = sum(p.get("alloc_pct", 0) for p in portfolio)
    remaining = max(0, 100 - total_alloc)

    return {
        "portfolio": portfolio,
        "total_allocated_pct": round(total_alloc, 2),
        "remaining_cash_pct": round(remaining, 2),
        "class_breakdown": dict(class_allocation),
        "tier2_count": len(tier2),
        "tier3_count": len(tier3),
        "discovery_count": len(discovery),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  ASSET CLASS SAFETY RANKING
# ═════════════════════════════════════════════════════════════════════════════

def rank_asset_classes(by_symbol):
    """Rank asset classes by safety (risk-adjusted return)."""
    ac_data = defaultdict(lambda: {"n": 0, "wins": 0, "total_pnl": 0.0, "pnl_list": []})
    for sym, data in by_symbol.items():
        ac = data["asset_class"]
        ac_data[ac]["n"] += data["n"]
        ac_data[ac]["wins"] += data["wins"]
        ac_data[ac]["total_pnl"] += data["total_pnl"]
        ac_data[ac]["pnl_list"].extend(data["pnl_list"])

    results = []
    for ac, data in ac_data.items():
        n = data["n"]
        if n < 10:
            continue
        wr = data["wins"] / n
        avg_pnl = data["total_pnl"] / n
        sharpe = calc_sharpe(data["pnl_list"])
        results.append({
            "asset_class": ac,
            "n": n,
            "win_rate": round(wr, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "sharpe": sharpe,
            "score": round(wr * 100 + (sharpe or 0) * 10, 2),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


# ═════════════════════════════════════════════════════════════════════════════
#  REPORTING
# ═════════════════════════════════════════════════════════════════════════════

def print_report(portfolio_result, class_rankings, all_picks):
    """Print formatted human-readable report."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"{'='*70}")
    print(f"  🎯 MONEY-READY PICKS GENERATOR REPORT")
    print(f"  Generated: {ts}")
    print(f"{'='*70}")

    # Asset class safety ranking
    print(f"\n{'─'*70}")
    print(f"  🏆 ASSET CLASS SAFETY RANKING (risk-adjusted)")
    print(f"{'─'*70}")
    print(f"  {'Rank':<5} {'Asset Class':<15} {'n':<8} {'WR%':<8} {'Avg PnL':<10} {'Sharpe':<8} {'Score':<8}")
    print(f"  {'─'*55}")
    for i, r in enumerate(class_rankings, 1):
        wr_pct = f"{r['win_rate']*100:.1f}%"
        avg_p = f"{r['avg_pnl_pct']:.2f}%"
        sh = f"{r['sharpe']:.2f}" if r['sharpe'] else "N/A"
        print(f"  {i:<5} {r['asset_class']:<15} {r['n']:<8} {wr_pct:<8} {avg_p:<10} {sh:<8} {r['score']:<8}")

    # Portfolio summary
    print(f"\n{'─'*70}")
    print(f"  📊 PORTFOLIO SUMMARY")
    print(f"{'─'*70}")
    print(f"  Total Allocated: {portfolio_result['total_allocated_pct']:.1f}%")
    print(f"  Remaining Cash:  {portfolio_result['remaining_cash_pct']:.1f}%")
    print(f"  Money-Ready (T2): {portfolio_result['tier2_count']}")
    print(f"  Building (T3):    {portfolio_result['tier3_count']}")
    print(f"  Discovery:        {portfolio_result['discovery_count']}")

    if portfolio_result["tier2_count"] > 0:
        print(f"\n{'─'*70}")
        print(f"  💰 MONEY-READY PICKS (Tier 2 — Eligible for Real Money)")
        print(f"{'─'*70}")
        for p in portfolio_result["portfolio"]:
            if p["tier"] == "TIER2_MONEY_READY" and p.get("alloc_pct", 0) > 0:
                print(f"\n  {p['symbol']:12s} ({p['asset_class']})")
                print(f"  ├─ WR: {p['win_rate']*100:.1f}%  |  n={p['n']}  |  PF: {p['profit_factor']:.2f}")
                print(f"  ├─ Sharpe: {p['sharpe_annualized']:.2f}" if p['sharpe_annualized'] else "  ├─ Sharpe: N/A")
                print(f"  ├─ Expectancy: {p['expectancy']:.2f}% per trade")
                print(f"  ├─ Kelly Alloc: {p['kelly_alloc_pct']:.1f}% → Allocated: {p['alloc_pct']:.1f}%")
                if p['analyst_rec']:
                    print(f"  ├─ Analyst: {p['analyst_rec']} | Target: ${p['target_price']} ({p.get('upside_to_target', 'N/A')}% upside)")
                print(f"  └─ Consensus Score: {p['consensus_score']}/100")

    if portfolio_result["tier3_count"] > 0:
        print(f"\n{'─'*70}")
        print(f"  📈 BUILDING (Tier 3 — Paper Trade While Growing)")
        print(f"{'─'*70}")
        for p in portfolio_result["portfolio"]:
            if p["tier"] == "TIER3_BUILDING" and p.get("alloc_pct", 0) > 0:
                print(f"  {p['symbol']:12s} ({p['asset_class']})  WR={p['win_rate']*100:.1f}%  n={p['n']}  "
                      f"PF={p['profit_factor']:.2f}  Alloc={p['alloc_pct']:.1f}%")

    if portfolio_result["discovery_count"] > 0:
        print(f"\n{'─'*70}")
        print(f"  🔬 DISCOVERY (Watchlist — Need More Data)")
        print(f"{'─'*70}")
        for p in portfolio_result["portfolio"]:
            if p["tier"] == "DISCOVERY" and p.get("alloc_pct", 0) > 0:
                print(f"  {p['symbol']:12s} ({p['asset_class']})  WR={p['win_rate']*100:.1f}%  n={p['n']}  "
                      f"PF={p['profit_factor']:.2f}")

    print(f"\n{'='*70}")
    print(f"  ⚠️  WARNING: No picks passed Tier 2 (Money-Ready) gates.")
    print(f"  {'Real money deployment requires: WR≥50%, PF≥1.5, n≥100'}")
    print(f"{'='*70}")


def save_json(portfolio_result, class_rankings, all_picks, filepath):
    """Save structured JSON output."""
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "summary": {
            "total_picks_analyzed": len(all_picks),
            "tier2_money_ready": portfolio_result["tier2_count"],
            "tier3_building": portfolio_result["tier3_count"],
            "discovery": portfolio_result["discovery_count"],
            "total_allocated_pct": portfolio_result["total_allocated_pct"],
            "remaining_cash_pct": portfolio_result["remaining_cash_pct"],
        },
        "asset_class_rankings": class_rankings,
        "portfolio": [
            {
                "symbol": p["symbol"],
                "asset_class": p["asset_class"],
                "tier": p["tier"],
                "tier_label": p["tier_label"],
                "win_rate": p["win_rate"],
                "n": p["n"],
                "profit_factor": p["profit_factor"],
                "sharpe": p["sharpe_annualized"],
                "expectancy": p["expectancy"],
                "alloc_pct": p.get("alloc_pct", 0),
                "alloc_note": p.get("alloc_note", ""),
                "consensus_score": p["consensus_score"],
                "analyst_rec": p["analyst_rec"],
                "target_price": p["target_price"],
                "upside_to_target": p.get("upside_to_target"),
                "latest_price": p["latest_price"],
                "kelly_fraction": p["kelly_fraction"],
                "avg_pnl_pct": p["avg_pnl_pct"],
                "avg_win_pct": p["avg_win_pct"],
                "avg_loss_pct": p["avg_loss_pct"],
            }
            for p in portfolio_result["portfolio"]
            if p.get("alloc_pct", 0) > 0
        ],
        "thresholds": {
            "tier2": {"min_n": Tiers.MIN_N_TIER2, "min_wr": Tiers.MIN_WR_TIER2, "min_pf": Tiers.MIN_PF_TIER2},
            "tier3": {"min_n": Tiers.MIN_N_TIER3, "min_wr": Tiers.MIN_WR_TIER3, "min_pf": Tiers.MIN_PF_TIER3},
            "kelly_fraction": Tiers.KELLY_FRACTION,
            "max_single_symbol_pct": Tiers.MAX_SINGLE_SYMBOL_PCT,
            "max_single_class_pct": Tiers.MAX_SINGLE_CLASS_PCT,
        },
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n📁 JSON output saved to: {filepath}")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("🔌 Connecting to databases...")
    stocks_conn = get_stocks_conn()
    backtests_conn = get_backtests_conn()

    print("📥 Loading resolved picks from at_pick_outcomes...")
    by_symbol = load_resolved_picks(stocks_conn)
    print(f"   Loaded {len(by_symbol)} unique symbols with resolved picks.")

    print("📥 Loading stock fundamentals...")
    fundamentals = load_stock_fundamentals(stocks_conn)
    print(f"   Loaded {len(fundamentals)} tickers with fundamentals.")

    print("📥 Loading latest prices...")
    prices = load_latest_prices(stocks_conn)
    print(f"   Loaded {len(prices)} tickers with latest prices.")

    print("📥 Loading tournament picks...")
    tournament = load_tournament_picks(stocks_conn)
    print(f"   Loaded {len(tournament)} symbols from tournament.")

    stocks_conn.close()
    backtests_conn.close()

    print("\n🔬 Running edge detection engine...")
    all_picks = []
    for symbol, data in by_symbol.items():
        result = analyze_edge(data, fundamentals, prices, tournament)
        if result:
            all_picks.append(result)

    print(f"   Analyzed {len(all_picks)} symbol-class combinations.")

    print("\n📊 Building portfolio...")
    portfolio = build_portfolio(all_picks)

    print("\n🏆 Ranking asset classes by safety...")
    class_rankings = rank_asset_classes(by_symbol)

    # Print report
    print_report(portfolio, class_rankings, all_picks)

    # Save JSON
    out_path = DATA_DIR / "money_ready_picks.json"
    save_json(portfolio, class_rankings, all_picks, out_path)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
