#!/usr/bin/env python3
"""Dynamic Kelly Position Sizing with CVaR Constraint.

Mercury formula: w = Kelly * (target_CVaR / current_CVaR)
Determines optimal bet size per strategy based on edge + risk.

Usage:
    python tools/dynamic_kelly_sizer.py
    python tools/dynamic_kelly_sizer.py --balance 100000
"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TARGET_CVAR = -5.0          # Target CVaR95 (configurable, %)
TARGET_VOL = 15.0           # Target annualised volatility (%)
MIN_TRADES = 20             # Minimum closed trades to compute Kelly
KELLY_FRACTION = 0.25       # Quarter-Kelly (institutional standard)
MIN_POSITION_PCT = 0.5      # Floor: never size below 0.5%
MAX_POSITION_PCT = 15.0     # Ceiling: never size above 15%
DEFAULT_BALANCE = 100_000   # Default portfolio balance for $ output

# Flat sizing baselines (current system) for comparison
FLAT_SIZING = {
    "SCALPER":          4.0,
    "TRUSTOURSCORE":    7.5,
    "TESTER":           5.0,
    "zerounderscore":   5.0,
    "DEFAULT":          5.0,
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DATA = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
RISK_DATA = os.path.join(REPO, "tools", "portfolio_risk_results.json")
OUTPUT_PATH = os.path.join(REPO, "tools", "kelly_sizing_results.json")


def load_data():
    """Load closed picks and per-source risk metrics."""
    with open(DASHBOARD_DATA, "r", encoding="utf-8") as f:
        dash = json.load(f)
    closed = dash["picks"]["recent_closed"]

    with open(RISK_DATA, "r", encoding="utf-8") as f:
        risk = json.load(f)
    return closed, risk


def compute_kelly(wins, losses):
    """Compute raw Kelly fraction: f* = (p*b - q) / b.

    p = win probability, q = 1-p, b = avg_win / avg_loss.
    Returns 0 if edge is non-positive.
    """
    if not wins or not losses:
        return 0.0
    p = len(wins) / (len(wins) + len(losses))
    q = 1.0 - p
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))
    if avg_loss == 0:
        return 0.0
    b = avg_win / avg_loss
    f_star = (p * b - q) / b
    return max(f_star, 0.0)


def annualised_vol(pnl_pcts, trades_per_day=2.0):
    """Estimate annualised volatility from per-trade PnL %."""
    if len(pnl_pcts) < 2:
        return TARGET_VOL  # fallback
    mean = sum(pnl_pcts) / len(pnl_pcts)
    var = sum((x - mean) ** 2 for x in pnl_pcts) / (len(pnl_pcts) - 1)
    per_trade_vol = math.sqrt(var)
    # Annualise: vol_annual = vol_trade * sqrt(trades_per_day * 252)
    annual_factor = math.sqrt(trades_per_day * 252)
    return per_trade_vol * annual_factor


def compute_strategy_cvar95(pnl_pcts):
    """Compute empirical CVaR95 (Expected Shortfall) from PnL list."""
    if len(pnl_pcts) < 20:
        return TARGET_CVAR
    sorted_pnl = sorted(pnl_pcts)
    cutoff = max(1, int(len(sorted_pnl) * 0.05))
    tail = sorted_pnl[:cutoff]
    return sum(tail) / len(tail)


def size_strategies(closed, risk, balance=DEFAULT_BALANCE):
    """Compute Kelly-CVaR position sizes for all qualifying strategies."""
    # Group closed picks by source_system
    by_source = defaultdict(list)
    for pick in closed:
        src = pick.get("source_system", "unknown")
        pnl = pick.get("pnl_pct")
        if pnl is not None:
            by_source[src].append(pnl)

    risk_per_source = risk.get("per_source_system", {})
    results = {}

    for source, pnls in sorted(by_source.items()):
        n = len(pnls)
        if n < MIN_TRADES:
            continue

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        # --- Step 1: Raw Kelly ---
        f_star = compute_kelly(wins, losses)
        if f_star <= 0:
            results[source] = _zero_result(source, n, pnls, balance)
            continue

        # --- Step 2: Quarter-Kelly ---
        f_quarter = f_star * KELLY_FRACTION

        # --- Step 3: CVaR constraint ---
        src_risk = risk_per_source.get(source, {})
        strategy_cvar = src_risk.get("CVaR_95") or compute_strategy_cvar95(pnls)
        # Both target and strategy CVaR are negative; use abs ratio
        cvar_ratio = min(1.0, abs(TARGET_CVAR) / abs(strategy_cvar)) if strategy_cvar != 0 else 1.0
        f_cvar = f_quarter * cvar_ratio

        # --- Step 4: Volatility scaling ---
        real_vol = annualised_vol(pnls)
        vol_scale = min(2.0, TARGET_VOL / real_vol) if real_vol > 0 else 1.0
        f_final = f_cvar * vol_scale

        # --- Step 5: Clamp ---
        f_pct = max(MIN_POSITION_PCT, min(MAX_POSITION_PCT, f_final * 100))

        win_rate = len(wins) / n * 100
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0

        results[source] = {
            "source_system": source,
            "n_trades": n,
            "win_rate_pct": round(win_rate, 2),
            "avg_win_pct": round(avg_win, 3),
            "avg_loss_pct": round(avg_loss, 3),
            "raw_kelly_pct": round(f_star * 100, 3),
            "quarter_kelly_pct": round(f_quarter * 100, 3),
            "strategy_CVaR95": round(strategy_cvar, 3),
            "cvar_ratio": round(cvar_ratio, 4),
            "realised_vol_annual_pct": round(real_vol, 2),
            "vol_scale": round(vol_scale, 4),
            "recommended_pct": round(f_pct, 2),
            "recommended_dollars": round(balance * f_pct / 100, 2),
            "flat_baseline_pct": FLAT_SIZING["DEFAULT"],
            "vs_flat_delta_pct": round(f_pct - FLAT_SIZING["DEFAULT"], 2),
        }

    return results


def _zero_result(source, n, pnls, balance):
    """Result for strategies with no positive edge."""
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    wr = len(wins) / n * 100 if n else 0
    return {
        "source_system": source,
        "n_trades": n,
        "win_rate_pct": round(wr, 2),
        "avg_win_pct": round(sum(wins) / len(wins), 3) if wins else 0,
        "avg_loss_pct": round(abs(sum(losses) / len(losses)), 3) if losses else 0,
        "raw_kelly_pct": 0.0,
        "quarter_kelly_pct": 0.0,
        "strategy_CVaR95": 0.0,
        "cvar_ratio": 0.0,
        "realised_vol_annual_pct": round(annualised_vol(pnls), 2),
        "vol_scale": 0.0,
        "recommended_pct": MIN_POSITION_PCT,
        "recommended_dollars": round(balance * MIN_POSITION_PCT / 100, 2),
        "flat_baseline_pct": FLAT_SIZING["DEFAULT"],
        "vs_flat_delta_pct": round(MIN_POSITION_PCT - FLAT_SIZING["DEFAULT"], 2),
        "edge": "NEGATIVE — Kelly recommends 0% allocation",
    }


def get_recommended_size(strategy_name, portfolio_balance=DEFAULT_BALANCE):
    """Lookup function: returns recommended dollar amount for a strategy.

    Loads precomputed results from kelly_sizing_results.json.
    Falls back to minimum position size if strategy not found.
    """
    if not os.path.exists(OUTPUT_PATH):
        raise FileNotFoundError(
            f"{OUTPUT_PATH} not found. Run `python tools/dynamic_kelly_sizer.py` first."
        )
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    strats = data.get("strategies", {})
    entry = strats.get(strategy_name)
    if entry is None:
        # Try fuzzy match
        for key in strats:
            if strategy_name.lower() in key.lower():
                entry = strats[key]
                break

    if entry is None:
        pct = MIN_POSITION_PCT
    else:
        pct = entry["recommended_pct"]

    dollars = round(portfolio_balance * pct / 100, 2)
    return {
        "strategy": strategy_name,
        "position_pct": pct,
        "position_dollars": dollars,
        "portfolio_balance": portfolio_balance,
    }


def main():
    balance = DEFAULT_BALANCE
    if "--balance" in sys.argv:
        idx = sys.argv.index("--balance")
        if idx + 1 < len(sys.argv):
            balance = float(sys.argv[idx + 1])

    closed, risk = load_data()
    results = size_strategies(closed, risk, balance)

    # Sort by recommended_pct descending
    ranked = dict(sorted(results.items(), key=lambda x: -x[1]["recommended_pct"]))

    output = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "target_CVaR95_pct": TARGET_CVAR,
            "target_vol_annual_pct": TARGET_VOL,
            "kelly_fraction": KELLY_FRACTION,
            "min_trades": MIN_TRADES,
            "min_position_pct": MIN_POSITION_PCT,
            "max_position_pct": MAX_POSITION_PCT,
            "portfolio_balance": balance,
        },
        "strategies": ranked,
        "summary": {
            "total_strategies_sized": len(ranked),
            "positive_edge_count": sum(1 for r in ranked.values() if r["raw_kelly_pct"] > 0),
            "negative_edge_count": sum(1 for r in ranked.values() if r["raw_kelly_pct"] == 0),
            "avg_recommended_pct": round(
                sum(r["recommended_pct"] for r in ranked.values()) / max(len(ranked), 1), 2
            ),
            "avg_flat_baseline_pct": FLAT_SIZING["DEFAULT"],
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # --- Console report ---
    print("=" * 80)
    print("  DYNAMIC KELLY POSITION SIZING WITH CVaR CONSTRAINT")
    print(f"  Portfolio: ${balance:,.0f} | Target CVaR95: {TARGET_CVAR}%"
          f" | Target Vol: {TARGET_VOL}% | Kelly Frac: {KELLY_FRACTION}")
    print("=" * 80)
    print(f"{'Source System':<30} {'Trades':>6} {'WR%':>6} {'Kelly%':>7}"
          f" {'CVaR95':>7} {'Rec%':>6} {'$':>10} {'vs Flat':>8}")
    print("-" * 80)
    for name, r in ranked.items():
        edge_flag = " *" if r["raw_kelly_pct"] == 0 else ""
        print(f"{name:<30} {r['n_trades']:>6} {r['win_rate_pct']:>5.1f}%"
              f" {r['raw_kelly_pct']:>6.2f}% {r['strategy_CVaR95']:>6.2f}%"
              f" {r['recommended_pct']:>5.2f}% {r['recommended_dollars']:>10,.0f}"
              f" {r['vs_flat_delta_pct']:>+7.2f}%{edge_flag}")
    print("-" * 80)
    pos_edge = sum(1 for r in ranked.values() if r["raw_kelly_pct"] > 0)
    neg_edge = len(ranked) - pos_edge
    print(f"  {len(ranked)} strategies sized | {pos_edge} positive edge | {neg_edge} negative edge (*)")
    avg_rec = sum(r["recommended_pct"] for r in ranked.values()) / max(len(ranked), 1)
    print(f"  Avg recommended: {avg_rec:.2f}% vs flat {FLAT_SIZING['DEFAULT']:.1f}%")
    print(f"  Results written to: {OUTPUT_PATH}")
    print()

    return output


if __name__ == "__main__":
    main()
