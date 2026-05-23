#!/usr/bin/env python3
"""
Multi-Asset Scorer & Leaderboard
==================================
Scoring and ranking engine for multi-asset forward-testing performance.

Scores each portfolio variant and strategy based on:
  - Win Rate: 30% weight
  - Profit Factor: 25% weight
  - Sharpe Ratio: 25% weight
  - Max Drawdown (inverse): 20% weight

Output: leaderboard.json — ranked variants with composite scores + grades.

Run: python copy_trader_intel/multi_asset_scorer.py
"""

import json
import sys
import os
import math
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
CONFIG_PATH = Path(__file__).parent / "multi_asset_config.json"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def calculate_sharpe(pnl_list, risk_free_rate=0.0):
    """Calculate Sharpe ratio from a list of trade PnL percentages."""
    if len(pnl_list) < 2:
        return 0.0
    mean = sum(pnl_list) / len(pnl_list)
    variance = sum((p - mean) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    trades_per_year = 252 / max(1, 5)
    return (mean - risk_free_rate) / std * math.sqrt(trades_per_year)


def calculate_max_drawdown(pnl_list):
    """Calculate max drawdown from cumulative PnL."""
    if not pnl_list:
        return 0.0
    equity = [0]
    for pnl in pnl_list:
        equity.append(equity[-1] + pnl)
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        dd = peak - e
        max_dd = max(max_dd, dd)
    return max_dd


def calculate_profit_factor(pnl_list):
    """Calculate profit factor."""
    gross_profit = sum(p for p in pnl_list if p > 0)
    gross_loss = abs(sum(p for p in pnl_list if p < 0))
    if gross_loss == 0:
        return 99.99 if gross_profit > 0 else 0
    return gross_profit / gross_loss


def score_portfolio_variant(variant_name, trades, config=None):
    """Score a portfolio variant based on forward-testing or backtest results."""
    if not config:
        config = load_config()

    weights = config.get("scoring", {}).get("weights", {
        "win_rate": 0.30, "profit_factor": 0.25,
        "sharpe_ratio": 0.25, "max_drawdown_inverse": 0.20,
    })
    min_trades = config.get("scoring", {}).get("min_trades_for_ranking", 15)
    grade_thresholds = config.get("scoring", {}).get("grade_thresholds", {
        "A": 80, "B": 60, "C": 40, "D": 20, "F": 0,
    })

    total = len(trades)
    if total == 0:
        return _empty_score(variant_name)

    pnl_list = []
    for t in trades:
        pnl = t.get("pnl_pct", t.get("unrealized_pnl_pct", 0))
        if pnl is not None:
            pnl_list.append(float(pnl))

    wins = sum(1 for p in pnl_list if p > 0)
    losses = sum(1 for p in pnl_list if p < 0)
    win_rate = wins / total if total > 0 else 0
    total_pnl = sum(pnl_list)
    avg_pnl = total_pnl / total if total > 0 else 0
    profit_factor = calculate_profit_factor(pnl_list)
    sharpe = calculate_sharpe(pnl_list)
    max_dd = calculate_max_drawdown(pnl_list)

    wr_score = min(100, win_rate * 100)
    pf_score = min(100, max(0, profit_factor * 33.33))
    sharpe_score = min(100, max(0, (sharpe + 2) * 25))
    mdd_score = max(0, 100 - max_dd * 5)

    composite = (
        wr_score * weights.get("win_rate", 0.30) +
        pf_score * weights.get("profit_factor", 0.25) +
        sharpe_score * weights.get("sharpe_ratio", 0.25) +
        mdd_score * weights.get("max_drawdown_inverse", 0.20)
    )

    if total < min_trades:
        composite *= (total / min_trades)

    composite = round(min(100, max(0, composite)), 1)

    grade = "F"
    for g, threshold in sorted(grade_thresholds.items(), key=lambda x: x[1], reverse=True):
        if composite >= threshold:
            grade = g
            break

    by_asset = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
    for t in trades:
        ac = t.get("asset_class", t.get("category", "UNKNOWN")).upper()
        pnl = t.get("pnl_pct", 0) or 0
        by_asset[ac]["trades"] += 1
        by_asset[ac]["wins"] += 1 if pnl > 0 else 0
        by_asset[ac]["pnl"] += float(pnl)

    by_asset_summary = {}
    for ac, stats in by_asset.items():
        by_asset_summary[ac] = {
            "trades": stats["trades"],
            "wins": stats["wins"],
            "win_rate": round(stats["wins"] / stats["trades"] * 100, 1) if stats["trades"] > 0 else 0,
            "total_pnl": round(stats["pnl"], 4),
        }

    return {
        "variant_name": variant_name,
        "composite_score": composite,
        "grade": grade,
        "total_trades": total,
        "sufficient_data": total >= min_trades,
        "metrics": {
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_pnl_pct": round(total_pnl, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
            "wins": wins,
            "losses": losses,
        },
        "component_scores": {
            "win_rate_score": round(wr_score, 1),
            "profit_factor_score": round(pf_score, 1),
            "sharpe_score": round(sharpe_score, 1),
            "max_dd_score": round(mdd_score, 1),
        },
        "by_asset_class": by_asset_summary,
    }


def _empty_score(variant_name):
    return {
        "variant_name": variant_name, "composite_score": 0, "grade": "F",
        "total_trades": 0, "sufficient_data": False,
        "metrics": {"win_rate": 0, "profit_factor": 0, "sharpe_ratio": 0,
                    "max_drawdown_pct": 0, "total_pnl_pct": 0, "avg_pnl_pct": 0,
                    "wins": 0, "losses": 0},
        "component_scores": {"win_rate_score": 0, "profit_factor_score": 0,
                             "sharpe_score": 0, "max_dd_score": 0},
        "by_asset_class": {},
    }


def build_leaderboard():
    """Build scored leaderboard from backtest results and variation portfolios."""
    print("=" * 70)
    print("  MULTI-ASSET SCORER & LEADERBOARD")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    config = load_config()
    all_scores = []

    # Score backtest results — handle BOTH nested and flat formats
    bt_path = DATA_DIR / "backtest_results.json"
    bt_path_alt = DATA_DIR / "multi_asset_backtest_results.json"

    if bt_path.exists():
        print("\n  [1] Scoring walk-forward backtest results...")
        with open(bt_path) as f:
            bt_data = json.load(f)

        bt_count = 0
        results_dict = bt_data.get("results", {})
        if isinstance(results_dict, dict):
            # Nested format: results.{asset_class}.{strategy}.walk_forward
            for asset_class, strategies in results_dict.items():
                if not isinstance(strategies, dict):
                    continue
                for strat_name, strat_data in strategies.items():
                    wf = strat_data.get("walk_forward", {})
                    oos = wf.get("out_of_sample", {})
                    if not oos or oos.get("trade_count", 0) == 0:
                        continue

                    # Score using OOS metrics directly
                    name = f"bt_{strat_name}::{asset_class}"
                    wr = oos.get("win_rate", 0)
                    pf = oos.get("profit_factor", 0)
                    sr = oos.get("sharpe_ratio", 0)
                    mdd = oos.get("max_drawdown", 0) * 100  # Convert to pct
                    tc = oos.get("trade_count", 0)
                    robust = wf.get("robust", False)

                    # Create synthetic trades for scoring
                    synth_trades = []
                    total_pnl = oos.get("total_pnl_pct", 0)
                    wins = int(wr * tc)
                    for i in range(wins):
                        synth_trades.append({"pnl_pct": abs(total_pnl / tc) * 1.5 if tc > 0 else 1, "asset_class": asset_class.upper()})
                    for i in range(tc - wins):
                        synth_trades.append({"pnl_pct": -abs(total_pnl / tc) * 0.8 if tc > 0 else -1, "asset_class": asset_class.upper()})

                    score = score_portfolio_variant(name, synth_trades, config)
                    score["source"] = "backtest_walk_forward"
                    score["strategy"] = strat_name
                    score["asset_class"] = asset_class.upper()
                    score["robust"] = robust
                    score["oos_win_rate"] = round(wr * 100, 1)
                    score["oos_profit_factor"] = round(pf, 2)
                    score["oos_sharpe"] = round(sr, 2)
                    score["oos_trades"] = tc
                    all_scores.append(score)
                    bt_count += 1

                    # Also score the top grid search result
                    grid_top5 = strat_data.get("grid_top5", [])
                    if grid_top5:
                        best_grid = grid_top5[0]
                        g_name = f"grid_{strat_name}::{asset_class}::tp{best_grid.get('tp_mult', '?')}sl{best_grid.get('sl_mult', '?')}"
                        g_wr = best_grid.get("win_rate", 0)
                        g_tc = best_grid.get("trade_count", 0)
                        g_pnl = best_grid.get("total_pnl_pct", 0)
                        g_wins = int(g_wr * g_tc)
                        g_trades = []
                        for i in range(g_wins):
                            g_trades.append({"pnl_pct": abs(g_pnl / g_tc) * 1.5 if g_tc > 0 else 1, "asset_class": asset_class.upper()})
                        for i in range(g_tc - g_wins):
                            g_trades.append({"pnl_pct": -abs(g_pnl / g_tc) * 0.8 if g_tc > 0 else -1, "asset_class": asset_class.upper()})

                        g_score = score_portfolio_variant(g_name, g_trades, config)
                        g_score["source"] = "backtest_grid_search"
                        g_score["strategy"] = strat_name
                        g_score["asset_class"] = asset_class.upper()
                        g_score["tp_mult"] = best_grid.get("tp_mult")
                        g_score["sl_mult"] = best_grid.get("sl_mult")
                        all_scores.append(g_score)
                        bt_count += 1

        print(f"    Scored {bt_count} backtest combos")

    elif bt_path_alt.exists():
        print("\n  [1] Scoring flat backtest results...")
        with open(bt_path_alt) as f:
            bt_data = json.load(f)
        for result in bt_data.get("results", []):
            trades = result.get("trades", [])
            scored_trades = [{"pnl_pct": t.get("pnl_pct", 0),
                              "asset_class": result.get("asset_class", "UNKNOWN")}
                             for t in trades]
            name = f"bt_{result['strategy']}::{result['symbol']}"
            score = score_portfolio_variant(name, scored_trades, config)
            score["source"] = "backtest"
            score["strategy"] = result.get("strategy", "")
            score["asset_class"] = result.get("asset_class", "")
            all_scores.append(score)
        print(f"    Scored {len(bt_data.get('results', []))} backtest combos")

    # Score variation portfolios
    var_path = DATA_DIR / "variation_portfolios.json"
    if var_path.exists():
        print("\n  [2] Scoring variation portfolios...")
        with open(var_path) as f:
            var_data = json.load(f)
        for variant_name, variant_info in var_data.get("variants", {}).items():
            picks = variant_info.get("picks", [])
            scored_trades = [{"pnl_pct": float(p.get("pnl_pct", 0) or 0),
                              "asset_class": p.get("asset_class", "UNKNOWN").upper()}
                             for p in picks]
            name = f"variant_{variant_name}"
            score = score_portfolio_variant(name, scored_trades, config)
            score["source"] = "variation_portfolio"
            all_scores.append(score)
        print(f"    Scored {len(var_data.get('variants', {}))} variants")

    # Score crypto copytrader
    ct_path = Path(__file__).parent.parent / "alpha_engine" / "data" / "portfolio_copytrader.json"
    if ct_path.exists():
        print("\n  [3] Scoring crypto copytrader...")
        try:
            with open(ct_path) as f:
                ct_data = json.load(f)
            ct_closed = ct_data.get("closed_positions", [])
            scored_trades = [{"pnl_pct": cp.get("pnl_pct", 0), "asset_class": "CRYPTO"}
                             for cp in ct_closed]
            score = score_portfolio_variant("crypto_copytrader", scored_trades, config)
            score["source"] = "live_forward_test"
            all_scores.append(score)
            print(f"    Scored crypto copytrader ({len(ct_closed)} closed)")
        except Exception as e:
            print(f"    [WARN] Could not score: {e}")

    all_scores.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, s in enumerate(all_scores):
        s["rank"] = i + 1

    now_iso = datetime.now(timezone.utc).isoformat()
    output = {
        "generated_at": now_iso,
        "total_scored": len(all_scores),
        "scoring_weights": config.get("scoring", {}).get("weights", {}),
        "leaderboard": all_scores,
        "top_10": all_scores[:10],
    }

    path = DATA_DIR / "leaderboard.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  [OK] Saved leaderboard ({len(all_scores)} entries) -> {path}")

    # Audit-compatible output
    audit_scores = [{"variant": s["variant_name"], "score": s["composite_score"],
                     "grade": s["grade"], "wr": s["metrics"]["win_rate"],
                     "pf": s["metrics"]["profit_factor"],
                     "sharpe": s["metrics"]["sharpe_ratio"],
                     "trades": s["total_trades"], "rank": s["rank"]}
                    for s in all_scores[:50]]
    audit_path = DATA_DIR / "multi_asset_audit_scores.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": now_iso, "scores": audit_scores}, f, indent=2)
    print(f"  [OK] Audit scores -> {audit_path}")

    # Print leaderboard
    print("\n" + "=" * 70)
    print("  LEADERBOARD (Top 15)")
    print("=" * 70)
    print(f"  {'#':>3s} {'G':>2s} {'Score':>5s} {'Name':30s} {'WR%':>5s} {'PF':>5s} {'PnL%':>7s}")
    print("  " + "-" * 60)
    for s in all_scores[:15]:
        n = s["variant_name"][:30]
        print(f"  {s['rank']:3d} {s['grade']:>2s} {s['composite_score']:5.1f} {n:30s} "
              f"{s['metrics']['win_rate']:4.1f}% {s['metrics']['profit_factor']:4.2f} "
              f"{s['metrics']['total_pnl_pct']:+6.2f}%")
    print("=" * 70)
    return all_scores


if __name__ == "__main__":
    build_leaderboard()
