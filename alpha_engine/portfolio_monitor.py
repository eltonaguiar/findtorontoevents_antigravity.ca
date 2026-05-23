#!/usr/bin/env python3
"""
Portfolio Insight Monitor
=========================
Compares performance across all portfolio trackers, detects anomalies,
identifies winning/losing patterns, and flags sandbox vs production
discrepancies.

Usage:
    python alpha_engine/portfolio_monitor.py        # standalone from repo root
    python -m alpha_engine.portfolio_monitor        # as module

Runs every 15-20 min via GitHub Actions (alpha-engine-live.yml).
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ─────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"

# Thresholds
CONSECUTIVE_SL_WARNING = 3
SCORE_INVERSION_THRESHOLD = 40  # If picks <40 score win more, flag it
OUTPERFORMANCE_THRESHOLD = 2.0  # % difference to flag
SANDBOX_VS_PROD_WR_GAP = 15    # % WR gap to flag


def _safe_json_load(path: Path) -> dict | list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _sanitize(obj):
    """Replace NaN/Inf with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def _pnl_normalize(pnl: float) -> float:
    """Normalize PnL to percentage. If stored as fraction, convert."""
    if pnl is None:
        return 0.0
    if abs(pnl) < 5:  # Likely fractional (0.03 = 3%)
        return pnl * 100
    return pnl  # Already in percentage


# ─── Portfolio Loading ───────────────────────────────────────────────────

def load_portfolio(name: str) -> dict:
    """Load a portfolio JSON and extract key metrics."""
    filename_map = {
        "1x": "portfolio_1x.json",
        "20x": "portfolio_20x.json",
        "copytrader": "portfolio_copytrader.json",
    }
    path = DATA_DIR / filename_map.get(name, f"portfolio_{name}.json")
    data = _safe_json_load(path)
    if not isinstance(data, dict) or not data:
        return {"name": name, "loaded": False}

    positions = data.get("positions", {})
    closed = data.get("closed_positions", [])
    stats = data.get("stats", {})

    starting = data.get("starting_balance", 10000)
    current = data.get("current_balance", starting)
    total_return = ((current - starting) / starting) * 100 if starting > 0 else 0

    # Compute from closed positions
    wins = sum(1 for c in closed if _is_win(c))
    losses = len(closed) - wins
    wr = (wins / len(closed) * 100) if closed else 0
    total_pnl = sum(c.get("pnl_pct", 0) for c in closed)

    # Unrealized PnL from open positions
    unrealized = sum(
        p.get("current_pnl_pct", 0) for p in positions.values()
    ) if isinstance(positions, dict) else 0

    return {
        "name": name,
        "loaded": True,
        "starting_balance": starting,
        "current_balance": current,
        "total_return_pct": round(total_return, 2),
        "open_positions": len(positions),
        "closed_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 1),
        "realized_pnl_pct": round(_pnl_normalize(total_pnl), 2),
        "unrealized_pnl_pct": round(_pnl_normalize(unrealized), 2),
        "leverage": data.get("leverage", 1),
        "closed_positions": closed,
        "positions": positions,
        "stats": stats,
    }


def _is_win(trade: dict) -> bool:
    reason = (trade.get("close_reason") or trade.get("status") or "").upper()
    if "TP" in reason or "WIN" in reason or "WON" in reason or "PROFIT" in reason:
        return True
    if "SL" in reason or "LOSS" in reason or "LOST" in reason:
        return False
    pnl = trade.get("pnl_pct", 0)
    return pnl > 0


# ─── Insight Generation ─────────────────────────────────────────────────

def compare_portfolios(portfolios: dict[str, dict]) -> list[dict]:
    """Compare portfolios and generate insights."""
    insights = []
    loaded = {k: v for k, v in portfolios.items() if v.get("loaded")}

    if len(loaded) < 2:
        return insights

    # Compare each pair
    names = list(loaded.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = loaded[names[i]], loaded[names[j]]

            ret_diff = a["total_return_pct"] - b["total_return_pct"]
            if abs(ret_diff) > OUTPERFORMANCE_THRESHOLD:
                better = a if ret_diff > 0 else b
                worse = a if ret_diff <= 0 else b
                insights.append({
                    "type": "portfolio_comparison",
                    "severity": "HIGH" if abs(ret_diff) > 5 else "MEDIUM",
                    "message": (
                        f"{better['name']} portfolio is outperforming {worse['name']} "
                        f"by {abs(ret_diff):.1f}% -- consider adjusting allocation"
                    ),
                    "details": {
                        "better": better["name"],
                        "better_return": better["total_return_pct"],
                        "worse": worse["name"],
                        "worse_return": worse["total_return_pct"],
                    },
                })

            wr_diff = a["win_rate"] - b["win_rate"]
            if abs(wr_diff) > 10 and a["closed_trades"] >= 5 and b["closed_trades"] >= 5:
                better = a if wr_diff > 0 else b
                worse = a if wr_diff <= 0 else b
                insights.append({
                    "type": "win_rate_gap",
                    "severity": "HIGH" if abs(wr_diff) > 20 else "MEDIUM",
                    "message": (
                        f"{better['name']} WR ({better['win_rate']:.0f}%) is significantly "
                        f"higher than {worse['name']} ({worse['win_rate']:.0f}%) -- "
                        f"investigate strategy selection"
                    ),
                    "details": {
                        "better": better["name"],
                        "better_wr": better["win_rate"],
                        "worse": worse["name"],
                        "worse_wr": worse["win_rate"],
                    },
                })

    return insights


def detect_consecutive_sl(portfolio: dict) -> list[dict]:
    """Detect consecutive SL hits (signals trouble)."""
    insights = []
    closed = portfolio.get("closed_positions", [])
    if len(closed) < CONSECUTIVE_SL_WARNING:
        return insights

    # Check last N trades
    recent = closed[-CONSECUTIVE_SL_WARNING:]
    consecutive_sl = all(
        "SL" in (c.get("close_reason") or c.get("status") or "").upper()
        for c in recent
    )

    if consecutive_sl:
        lev = portfolio.get("leverage", 1)
        msg = (
            f"{portfolio['name']} portfolio had {CONSECUTIVE_SL_WARNING} consecutive SL hits"
        )
        if lev > 1:
            msg += f" at {lev}x leverage -- consider reducing leverage"
        else:
            msg += " -- review strategy selection"

        insights.append({
            "type": "consecutive_sl",
            "severity": "CRITICAL" if lev > 5 else "HIGH",
            "message": msg,
            "details": {
                "portfolio": portfolio["name"],
                "leverage": lev,
                "recent_trades": [
                    {"symbol": c.get("symbol"), "pnl_pct": c.get("pnl_pct"),
                     "reason": c.get("close_reason")}
                    for c in recent
                ],
            },
        })

    return insights


def detect_score_calibration_issues(portfolios: dict[str, dict]) -> list[dict]:
    """Check if low-score picks are beating high-score picks."""
    insights = []

    all_closed = []
    for p in portfolios.values():
        if not p.get("loaded"):
            continue
        for c in p.get("closed_positions", []):
            score = c.get("score") or c.get("dashboard_score")
            if score is not None:
                all_closed.append({
                    "score": float(score),
                    "win": _is_win(c),
                    "pnl_pct": c.get("pnl_pct", 0),
                    "strategy": c.get("strategy", "?"),
                })

    # Also include closed_picks.json
    closed_picks = _safe_json_load(DATA_DIR / "closed_picks.json")
    if isinstance(closed_picks, list):
        for c in closed_picks:
            score = c.get("score") or c.get("confidence")
            if score is not None:
                s = float(score)
                if 0 < s <= 1:
                    s *= 100
                all_closed.append({
                    "score": s,
                    "win": (c.get("status") or "").upper() in ("WON", "WIN"),
                    "pnl_pct": c.get("pnl_pct", 0),
                    "strategy": c.get("strategy", "?"),
                })

    if len(all_closed) < 10:
        return insights

    # Split into low-score and high-score
    low = [t for t in all_closed if t["score"] < SCORE_INVERSION_THRESHOLD]
    high = [t for t in all_closed if t["score"] >= 60]

    if len(low) >= 5 and len(high) >= 5:
        low_wr = sum(1 for t in low if t["win"]) / len(low) * 100
        high_wr = sum(1 for t in high if t["win"]) / len(high) * 100

        if low_wr > high_wr:
            insights.append({
                "type": "score_inversion",
                "severity": "CRITICAL",
                "message": (
                    f"Low-score picks (<{SCORE_INVERSION_THRESHOLD}) are winning "
                    f"{low_wr:.0f}% vs high-score (60+) at {high_wr:.0f}% -- "
                    f"score calibration needed!"
                ),
                "details": {
                    "low_score_wr": round(low_wr, 1),
                    "high_score_wr": round(high_wr, 1),
                    "low_count": len(low),
                    "high_count": len(high),
                },
            })
        elif low_wr > 50:
            insights.append({
                "type": "low_score_opportunity",
                "severity": "MEDIUM",
                "message": (
                    f"Low-score picks (<{SCORE_INVERSION_THRESHOLD}) are winning "
                    f"{low_wr:.0f}% -- hidden opportunity in low-confidence signals"
                ),
                "details": {
                    "low_score_wr": round(low_wr, 1),
                    "low_count": len(low),
                },
            })

    return insights


def detect_strategy_sandbox_vs_prod(portfolios: dict[str, dict]) -> list[dict]:
    """
    Compare sandbox (untraded/backfill) picks vs production (actually traded).
    If sandbox picks are winning more, flag it.
    """
    insights = []

    # Sandbox = closed_picks.json (mostly backfill/forward validation)
    closed_picks = _safe_json_load(DATA_DIR / "closed_picks.json")
    if not isinstance(closed_picks, list) or len(closed_picks) < 10:
        return insights

    sandbox_wins = sum(1 for c in closed_picks if (c.get("status") or "").upper() in ("WON", "WIN"))
    sandbox_total = len(closed_picks)
    sandbox_wr = sandbox_wins / sandbox_total * 100

    # Production = portfolio closed_positions
    prod_closed = []
    for p in portfolios.values():
        if p.get("loaded"):
            prod_closed.extend(p.get("closed_positions", []))

    if len(prod_closed) < 5:
        return insights

    prod_wins = sum(1 for c in prod_closed if _is_win(c))
    prod_wr = prod_wins / len(prod_closed) * 100

    gap = sandbox_wr - prod_wr
    if gap > SANDBOX_VS_PROD_WR_GAP:
        insights.append({
            "type": "sandbox_vs_production",
            "severity": "HIGH",
            "message": (
                f"Sandbox WR ({sandbox_wr:.0f}%, n={sandbox_total}) is beating "
                f"production WR ({prod_wr:.0f}%, n={len(prod_closed)}) by {gap:.0f}% -- "
                f"investigate execution or entry timing"
            ),
            "details": {
                "sandbox_wr": round(sandbox_wr, 1),
                "sandbox_trades": sandbox_total,
                "production_wr": round(prod_wr, 1),
                "production_trades": len(prod_closed),
                "gap_pct": round(gap, 1),
            },
        })
    elif gap < -SANDBOX_VS_PROD_WR_GAP:
        insights.append({
            "type": "production_outperformance",
            "severity": "MEDIUM",
            "message": (
                f"Production WR ({prod_wr:.0f}%) is beating sandbox ({sandbox_wr:.0f}%) -- "
                f"live filtering/sizing is adding value"
            ),
            "details": {
                "sandbox_wr": round(sandbox_wr, 1),
                "production_wr": round(prod_wr, 1),
            },
        })

    return insights


def detect_strategy_discrepancies(portfolios: dict[str, dict]) -> list[dict]:
    """Find strategies that perform differently across portfolios."""
    insights = []

    # Gather per-strategy stats from each portfolio
    strat_by_portfolio = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "trades": 0}))

    for pname, p in portfolios.items():
        if not p.get("loaded"):
            continue
        for c in p.get("closed_positions", []):
            strat = c.get("strategy", "?")
            strat_by_portfolio[strat][pname]["trades"] += 1
            if _is_win(c):
                strat_by_portfolio[strat][pname]["wins"] += 1

    # Also include sandbox
    closed_picks = _safe_json_load(DATA_DIR / "closed_picks.json")
    if isinstance(closed_picks, list):
        for c in closed_picks:
            strat = c.get("strategy", "?")
            strat_by_portfolio[strat]["sandbox"]["trades"] += 1
            if (c.get("status") or "").upper() in ("WON", "WIN"):
                strat_by_portfolio[strat]["sandbox"]["wins"] += 1

    for strat, port_stats in strat_by_portfolio.items():
        if len(port_stats) < 2:
            continue

        wrs = {}
        for pname, info in port_stats.items():
            if info["trades"] >= 3:
                wrs[pname] = info["wins"] / info["trades"] * 100

        if len(wrs) < 2:
            continue

        max_wr = max(wrs.values())
        min_wr = min(wrs.values())
        if max_wr - min_wr > 30:
            best = max(wrs, key=wrs.get)
            worst = min(wrs, key=wrs.get)
            insights.append({
                "type": "strategy_discrepancy",
                "severity": "HIGH",
                "message": (
                    f"Strategy '{strat[:35]}' has {max_wr:.0f}% WR in {best} "
                    f"but {min_wr:.0f}% in {worst} -- investigate"
                ),
                "details": {
                    "strategy": strat,
                    "win_rates": {k: round(v, 1) for k, v in wrs.items()},
                },
            })

    return insights


# ─── Save & Report ───────────────────────────────────────────────────────

def save_insights(result: dict):
    """Save insights to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "portfolio_insights.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(_sanitize(result), f, indent=2)
    print(f"  Saved insights to {path}")


def print_report(result: dict):
    """Print a clear human-readable report."""
    print()
    print("=" * 70)
    print("  PORTFOLIO INSIGHT MONITOR")
    print(f"  {result.get('generated_at', '?')}")
    print("=" * 70)

    # Portfolio summary table
    summaries = result.get("portfolio_summaries", {})
    if summaries:
        print(f"\n  {'Portfolio':<14} {'Balance':>10} {'Return':>8} {'Open':>5} "
              f"{'Closed':>7} {'WR':>6} {'PnL':>8}")
        print(f"  {'-'*14} {'-'*10} {'-'*8} {'-'*5} {'-'*7} {'-'*6} {'-'*8}")
        for name, s in summaries.items():
            if not s.get("loaded"):
                print(f"  {name:<14} {'NOT LOADED':>10}")
                continue
            print(f"  {name:<14} ${s['current_balance']:>9,.0f} "
                  f"{s['total_return_pct']:>+7.2f}% {s['open_positions']:>5} "
                  f"{s['closed_trades']:>7} {s['win_rate']:>5.1f}% "
                  f"{s['realized_pnl_pct']:>+7.2f}%")

    # Insights
    all_insights = result.get("insights", [])
    if all_insights:
        print(f"\n  INSIGHTS ({len(all_insights)}):")
        for idx, ins in enumerate(all_insights, 1):
            severity = ins.get("severity", "INFO")
            marker = {"CRITICAL": "[!!!]", "HIGH": "[!!]",
                      "MEDIUM": "[!]", "LOW": "[.]"}.get(severity, "[?]")
            print(f"\n    {idx}. {marker} {ins['message']}")
    else:
        print("\n  No actionable insights detected.")

    print()
    print("=" * 70)


# ─── Main ─────────────────────────────────────────────────────────────────

def run_portfolio_monitor() -> dict:
    """Run the full portfolio monitoring pipeline. Returns result dict."""
    print("\n[PORTFOLIO MONITOR] Comparing portfolio performance...")

    # Load all portfolios
    portfolios = {}
    for name in ("1x", "20x", "copytrader"):
        portfolios[name] = load_portfolio(name)
        status = "loaded" if portfolios[name].get("loaded") else "not found"
        print(f"  {name}: {status}")

    # Generate all insights
    all_insights = []

    all_insights.extend(compare_portfolios(portfolios))

    for p in portfolios.values():
        if p.get("loaded"):
            all_insights.extend(detect_consecutive_sl(p))

    all_insights.extend(detect_score_calibration_issues(portfolios))
    all_insights.extend(detect_strategy_sandbox_vs_prod(portfolios))
    all_insights.extend(detect_strategy_discrepancies(portfolios))

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_insights.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

    # Build summaries (strip closed_positions/positions to keep output clean)
    summaries = {}
    for name, p in portfolios.items():
        summary = {k: v for k, v in p.items()
                   if k not in ("closed_positions", "positions")}
        summaries[name] = summary

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_summaries": summaries,
        "insights": all_insights,
        "insight_count": len(all_insights),
        "critical_count": sum(1 for i in all_insights if i.get("severity") == "CRITICAL"),
    }

    save_insights(result)
    print_report(result)

    return result


if __name__ == "__main__":
    run_portfolio_monitor()
