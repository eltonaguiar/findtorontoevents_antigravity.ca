#!/usr/bin/env python3
"""
Strategy Killer — Identify and eliminate underperforming strategies.

Aggregates data from ALL sources:
  - alpha_engine/data/strategy_performance.json
  - alpha_engine/data/track_record.json
  - alpha_engine/data/closed_picks.json
  - audit_trail/data/dashboard_payload.json (per-system per-strategy stats)
  - audit_trail/data/universal_resolved_picks.json

Computes per-strategy metrics, applies KILL / PROBATION / PROVEN tiers,
and outputs kill lists + tier assignments.

Stdlib only. Windows UTF-8 safe.
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

STRATEGY_PERF_PATH = os.path.join(DATA, "strategy_performance.json")
TRACK_RECORD_PATH = os.path.join(DATA, "track_record.json")
CLOSED_PICKS_PATH = os.path.join(DATA, "closed_picks.json")
DASHBOARD_PAYLOAD_PATH = os.path.join(BASE, "..", "audit_trail", "data", "dashboard_payload.json")
UNIVERSAL_RESOLVED_PATH = os.path.join(BASE, "..", "audit_trail", "data", "universal_resolved_picks.json")
CORE_WHITELIST_PATH = os.path.join(DATA, "core_whitelist.json")

# Output paths
KILL_LIST_PATH = os.path.join(DATA, "strategy_kill_list.json")
TIERS_PATH = os.path.join(DATA, "strategy_tiers.json")

# ---------------------------------------------------------------------------
# KILL / PROBATION / PROVEN thresholds
# ---------------------------------------------------------------------------
KILL_CRITERIA = {
    "wr_zero_min_trades": 3,         # WR = 0% with 3+ trades
    "wr_low_threshold": 0.25,        # WR < 25% with 5+ trades
    "wr_low_min_trades": 5,
    "pf_low_threshold": 0.5,         # Profit factor < 0.5 with 5+ trades
    "pf_low_min_trades": 5,
    "pnl_dollar_floor": -500,        # Total PnL < -$500
    "max_consec_losses": 5,          # Max consecutive losses >= 5
    "avg_rr_floor": 0.5,             # Average R:R < 0.5
}

PROBATION_CRITERIA = {
    "wr_range": (0.25, 0.40),        # WR 25-40% with 5+ trades
    "wr_min_trades": 5,
    "pf_range": (0.5, 0.8),          # Profit factor 0.5-0.8
}

PROVEN_CRITERIA = {
    "wr_threshold": 0.55,            # WR >= 55% with 10+ trades
    "wr_min_trades": 10,
    "pf_threshold": 1.5,             # Profit factor >= 1.5
}

# Score adjustments
PROBATION_PENALTY = -25
PROVEN_BONUS = +15

# Assumed position size for dollar PnL when not available
DEFAULT_POSITION_SIZE = 2000.0


def _load_json(path):
    """Load JSON file, return None if missing."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None


def _save_json(path, data):
    """Save JSON with pretty formatting."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Data aggregation: build per-strategy trade lists from ALL sources
# ---------------------------------------------------------------------------
class StrategyAggregator:
    """Collects trades per strategy from every data source."""

    def __init__(self):
        # strategy_name -> list of trade dicts with at minimum:
        #   pnl_pct (float), won (bool), pnl_dollar (float or None)
        self.trades = defaultdict(list)
        # Pre-computed stats from sources that only give aggregates
        self.precomputed = {}

    # -- Source 1: closed_picks.json (individual trades) -------------------
    def ingest_closed_picks(self, path):
        data = _load_json(path)
        if not data:
            print("  [SKIP] closed_picks.json not found")
            return 0
        count = 0
        for pick in data:
            strat = pick.get("strategy", "unknown")
            pnl_pct = pick.get("pnl_pct", 0.0) or 0.0
            pnl_dollar = pick.get("pnl_dollar", None)
            won = pnl_pct > 0
            self.trades[strat].append({
                "pnl_pct": pnl_pct,
                "won": won,
                "pnl_dollar": pnl_dollar if pnl_dollar else pnl_pct * DEFAULT_POSITION_SIZE,
                "source": "closed_picks",
            })
            count += 1
        print(f"  [OK] closed_picks.json: {count} trades, {len(set(p.get('strategy') for p in data))} strategies")
        return count

    # -- Source 2: universal_resolved_picks.json (individual trades) -------
    def ingest_universal_resolved(self, path):
        data = _load_json(path)
        if not data:
            print("  [SKIP] universal_resolved_picks.json not found")
            return 0
        count = 0
        for pick in data:
            strat = pick.get("strategy", "unknown")
            pnl_pct = pick.get("pnl_pct", 0.0) or 0.0
            won = pnl_pct > 0
            self.trades[strat].append({
                "pnl_pct": pnl_pct,
                "won": won,
                "pnl_dollar": pnl_pct * DEFAULT_POSITION_SIZE,
                "source": "universal_resolved",
            })
            count += 1
        print(f"  [OK] universal_resolved_picks.json: {count} trades, {len(set(p.get('strategy') for p in data))} strategies")
        return count

    # -- Source 3: track_record.json (pre-aggregated per strategy) ---------
    def ingest_track_record(self, path):
        data = _load_json(path)
        if not data:
            print("  [SKIP] track_record.json not found")
            return 0
        strategies = data.get("strategies", [])
        for s in strategies:
            name = s.get("strategy", "unknown")
            self.precomputed[name] = {
                "trades": s.get("trades", 0),
                "win_rate": s.get("win_rate", 0.0),
                "pnl_dollar": s.get("pnl_dollar", 0.0),
                "sharpe": s.get("sharpe", 0.0),
                "source": "track_record",
            }
        print(f"  [OK] track_record.json: {len(strategies)} strategies")
        return len(strategies)

    # -- Source 4: strategy_performance.json (pre-aggregated) --------------
    def ingest_strategy_performance(self, path):
        data = _load_json(path)
        if not data:
            print("  [SKIP] strategy_performance.json not found")
            return 0
        for name, stats in data.items():
            # Only store if we don't already have individual trades
            if name not in self.precomputed:
                self.precomputed[name] = {
                    "trades": stats.get("closed_picks", 0),
                    "win_rate": stats.get("win_rate", 0.0),
                    "avg_pnl": stats.get("avg_pnl", 0.0),
                    "profit_factor": stats.get("profit_factor", 0.0),
                    "source": "strategy_performance",
                }
        print(f"  [OK] strategy_performance.json: {len(data)} strategies")
        return len(data)

    # -- Source 5: dashboard_payload.json (per-system per-strategy) --------
    def ingest_dashboard_payload(self, path):
        data = _load_json(path)
        if not data:
            print("  [SKIP] dashboard_payload.json not found")
            return 0
        systems = data.get("systems", [])
        count = 0
        for system in systems:
            sys_name = system.get("name", "")
            for strat in system.get("strategies", []):
                name = strat.get("name", "unknown")
                resolved = strat.get("resolved", 0)
                if resolved < 1:
                    continue
                wins = strat.get("wins", 0)
                losses = strat.get("losses", 0)
                total_pnl = strat.get("total_pnl", 0.0)
                avg_pnl = strat.get("avg_pnl", 0.0)
                wr = strat.get("win_rate", 0.0)
                # Normalize win_rate: some are 0-100, some 0-1
                if wr > 1.0:
                    wr = wr / 100.0

                key = f"{sys_name}::{name}"
                self.precomputed[key] = {
                    "trades": resolved,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": wr,
                    "total_pnl_pct": total_pnl,
                    "avg_pnl_pct": avg_pnl,
                    "pnl_dollar": total_pnl * DEFAULT_POSITION_SIZE / 100.0,
                    "source": f"dashboard:{sys_name}",
                }
                count += 1
        print(f"  [OK] dashboard_payload.json: {count} strategy entries across {len(systems)} systems")
        return count


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------
def compute_metrics(trades_list):
    """Compute full metrics from a list of trade dicts."""
    if not trades_list:
        return None

    n = len(trades_list)
    wins = [t for t in trades_list if t["won"]]
    losses = [t for t in trades_list if not t["won"]]

    win_pnls = [t["pnl_pct"] for t in wins]
    loss_pnls = [t["pnl_pct"] for t in losses]
    all_pnls = [t["pnl_pct"] for t in trades_list]
    dollar_pnls = [t.get("pnl_dollar", 0) or 0 for t in trades_list]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / n if n > 0 else 0.0
    total_pnl_pct = sum(all_pnls)
    total_pnl_dollar = sum(dollar_pnls)

    gross_wins = sum(p for p in all_pnls if p > 0)
    gross_losses = abs(sum(p for p in all_pnls if p < 0))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (10.0 if gross_wins > 0 else 0.0)

    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0
    avg_rr = (avg_win / avg_loss) if avg_loss > 0 else (10.0 if avg_win > 0 else 0.0)

    # Max consecutive losses
    max_consec_losses = 0
    current_streak = 0
    for t in trades_list:
        if not t["won"]:
            current_streak += 1
            max_consec_losses = max(max_consec_losses, current_streak)
        else:
            current_streak = 0

    # Sharpe ratio (per-trade)
    sharpe = 0.0
    if n >= 2:
        mean_pnl = sum(all_pnls) / n
        variance = sum((p - mean_pnl) ** 2 for p in all_pnls) / (n - 1)
        std = math.sqrt(variance) if variance > 0 else 0
        sharpe = (mean_pnl / std) if std > 0 else 0.0

    return {
        "trades": n,
        "wins": win_count,
        "losses": loss_count,
        "win_rate": round(win_rate, 4),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "total_pnl_dollar": round(total_pnl_dollar, 2),
        "profit_factor": round(profit_factor, 4),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "avg_rr": round(avg_rr, 4),
        "max_consec_losses": max_consec_losses,
        "sharpe": round(sharpe, 4),
        "gross_wins_pct": round(gross_wins, 4),
        "gross_losses_pct": round(gross_losses, 4),
    }


def compute_metrics_from_precomputed(pre):
    """Build metrics dict from pre-aggregated stats."""
    trades = pre.get("trades", 0)
    wins = pre.get("wins", 0)
    losses = pre.get("losses", 0)
    wr = pre.get("win_rate", 0.0)
    pf = pre.get("profit_factor", None)
    pnl_dollar = pre.get("pnl_dollar", 0.0)
    total_pnl_pct = pre.get("total_pnl_pct", 0.0)
    avg_pnl = pre.get("avg_pnl", pre.get("avg_pnl_pct", 0.0))
    sharpe = pre.get("sharpe", 0.0)

    # Reconstruct wins/losses if not given
    if wins == 0 and losses == 0 and trades > 0:
        wins = int(round(wr * trades))
        losses = trades - wins

    # Estimate profit factor if not given
    if pf is None:
        # Cannot compute precisely, use what we have
        pf = 0.0

    # Estimate avg_rr from avg_pnl if we have wr
    avg_rr = 0.0
    # We can't compute this without individual trade data; mark as unknown

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 4),
        "total_pnl_pct": round(total_pnl_pct, 4) if total_pnl_pct else round(avg_pnl * trades, 4),
        "total_pnl_dollar": round(pnl_dollar, 2) if pnl_dollar else 0.0,
        "profit_factor": round(pf, 4) if pf else 0.0,
        "avg_win_pct": 0.0,
        "avg_loss_pct": 0.0,
        "avg_rr": avg_rr,
        "max_consec_losses": 0,  # Unknown from aggregates
        "sharpe": round(sharpe, 4) if sharpe else 0.0,
        "gross_wins_pct": 0.0,
        "gross_losses_pct": 0.0,
        "precomputed_only": True,
    }


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------
def classify_strategy(name, metrics):
    """Return (tier, reasons) for a strategy."""
    n = metrics["trades"]
    wr = metrics["win_rate"]
    pf = metrics["profit_factor"]
    pnl_d = metrics["total_pnl_dollar"]
    mcl = metrics["max_consec_losses"]
    avg_rr = metrics["avg_rr"]
    precomp = metrics.get("precomputed_only", False)

    kill_reasons = []
    probation_reasons = []
    proven_reasons = []

    # ---- KILL checks ----
    if wr == 0.0 and n >= KILL_CRITERIA["wr_zero_min_trades"]:
        kill_reasons.append(f"0% WR with {n} trades")

    if wr < KILL_CRITERIA["wr_low_threshold"] and n >= KILL_CRITERIA["wr_low_min_trades"]:
        kill_reasons.append(f"WR {wr*100:.1f}% < 25% with {n} trades")

    if pf < KILL_CRITERIA["pf_low_threshold"] and pf > 0 and n >= KILL_CRITERIA["pf_low_min_trades"]:
        kill_reasons.append(f"PF {pf:.2f} < 0.50 with {n} trades")
    elif pf == 0.0 and n >= KILL_CRITERIA["pf_low_min_trades"]:
        kill_reasons.append(f"PF 0.00 (zero wins) with {n} trades")

    if pnl_d < KILL_CRITERIA["pnl_dollar_floor"]:
        kill_reasons.append(f"PnL ${pnl_d:,.2f} < ${KILL_CRITERIA['pnl_dollar_floor']:,}")

    if mcl >= KILL_CRITERIA["max_consec_losses"] and not precomp:
        kill_reasons.append(f"{mcl} consecutive losses (>= {KILL_CRITERIA['max_consec_losses']})")

    if avg_rr > 0 and avg_rr < KILL_CRITERIA["avg_rr_floor"] and n >= 5 and not precomp:
        kill_reasons.append(f"Avg R:R {avg_rr:.2f} < {KILL_CRITERIA['avg_rr_floor']}")

    if kill_reasons:
        return "KILL", kill_reasons

    # ---- PROVEN checks ----
    if (wr >= PROVEN_CRITERIA["wr_threshold"]
            and n >= PROVEN_CRITERIA["wr_min_trades"]
            and pf >= PROVEN_CRITERIA["pf_threshold"]):
        proven_reasons.append(
            f"WR {wr*100:.1f}% >= 55%, PF {pf:.2f} >= 1.5, {n} trades >= 10"
        )
        return "PROVEN", proven_reasons

    # ---- PROBATION checks ----
    lo, hi = PROBATION_CRITERIA["wr_range"]
    if lo <= wr < hi and n >= PROBATION_CRITERIA["wr_min_trades"]:
        probation_reasons.append(f"WR {wr*100:.1f}% in 25-40% range with {n} trades")

    pf_lo, pf_hi = PROBATION_CRITERIA["pf_range"]
    if pf_lo <= pf < pf_hi and n >= 5:
        probation_reasons.append(f"PF {pf:.2f} in 0.50-0.80 range")

    if probation_reasons:
        return "PROBATION", probation_reasons

    # ---- ACTIVE (neutral) ----
    return "ACTIVE", ["Does not trigger kill, probation, or proven criteria"]


# ---------------------------------------------------------------------------
# Main run()
# ---------------------------------------------------------------------------
def run():
    print("=" * 72)
    print("  STRATEGY KILLER — Underperformer Analysis")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 72)
    print()

    # 1. Aggregate data from all sources
    print("[1/5] Loading data sources...")
    agg = StrategyAggregator()
    agg.ingest_closed_picks(CLOSED_PICKS_PATH)
    agg.ingest_universal_resolved(UNIVERSAL_RESOLVED_PATH)
    agg.ingest_track_record(TRACK_RECORD_PATH)
    agg.ingest_strategy_performance(STRATEGY_PERF_PATH)
    agg.ingest_dashboard_payload(DASHBOARD_PAYLOAD_PATH)
    print()

    # 2. Compute per-strategy metrics
    print("[2/5] Computing per-strategy metrics...")
    all_metrics = {}

    # From individual trade data (highest quality)
    for strat, trades_list in agg.trades.items():
        if len(trades_list) >= 1:
            m = compute_metrics(trades_list)
            if m:
                all_metrics[strat] = m

    # From precomputed (fill in strategies we don't have trades for)
    for strat, pre in agg.precomputed.items():
        if strat not in all_metrics and pre.get("trades", 0) >= 1:
            m = compute_metrics_from_precomputed(pre)
            if m:
                all_metrics[strat] = m

    print(f"  Total strategies with metrics: {len(all_metrics)}")
    print()

    # 3. Classify into tiers
    print("[3/5] Classifying strategies into tiers...")
    tiers = {"KILL": [], "PROBATION": [], "PROVEN": [], "ACTIVE": []}

    for strat, metrics in sorted(all_metrics.items(), key=lambda x: x[1]["total_pnl_dollar"]):
        tier, reasons = classify_strategy(strat, metrics)
        entry = {
            "strategy": strat,
            "tier": tier,
            "reasons": reasons,
            "metrics": metrics,
        }
        tiers[tier].append(entry)

    # Sort each tier
    tiers["KILL"].sort(key=lambda x: x["metrics"]["total_pnl_dollar"])
    tiers["PROBATION"].sort(key=lambda x: x["metrics"]["total_pnl_dollar"])
    tiers["PROVEN"].sort(key=lambda x: x["metrics"]["total_pnl_dollar"], reverse=True)
    tiers["ACTIVE"].sort(key=lambda x: x["metrics"]["total_pnl_dollar"], reverse=True)

    # 4. Calculate savings
    kill_pnl = sum(e["metrics"]["total_pnl_dollar"] for e in tiers["KILL"])
    probation_pnl = sum(e["metrics"]["total_pnl_dollar"] for e in tiers["PROBATION"])
    proven_pnl = sum(e["metrics"]["total_pnl_dollar"] for e in tiers["PROVEN"])
    active_pnl = sum(e["metrics"]["total_pnl_dollar"] for e in tiers["ACTIVE"])

    # 5. Print summary
    print()
    print("=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)
    print()
    print(f"  PROVEN   : {len(tiers['PROVEN']):>4} strategies  |  PnL: ${proven_pnl:>+12,.2f}")
    print(f"  ACTIVE   : {len(tiers['ACTIVE']):>4} strategies  |  PnL: ${active_pnl:>+12,.2f}")
    print(f"  PROBATION: {len(tiers['PROBATION']):>4} strategies  |  PnL: ${probation_pnl:>+12,.2f}")
    print(f"  KILL     : {len(tiers['KILL']):>4} strategies  |  PnL: ${kill_pnl:>+12,.2f}")
    print(f"  {'─' * 50}")
    print(f"  TOTAL    : {sum(len(v) for v in tiers.values()):>4} strategies")
    print()

    if kill_pnl < 0:
        print(f"  >>> KILLING {len(tiers['KILL'])} strategies saves ${abs(kill_pnl):,.2f} in losses <<<")
    print()

    # Print top 15 PROVEN
    if tiers["PROVEN"]:
        print("─" * 72)
        print("  TOP PROVEN STRATEGIES (keep these, they make money)")
        print("─" * 72)
        for i, e in enumerate(tiers["PROVEN"][:15], 1):
            m = e["metrics"]
            print(f"  {i:>2}. {e['strategy'][:45]:<45} "
                  f"WR={m['win_rate']*100:5.1f}%  PF={m['profit_factor']:6.2f}  "
                  f"PnL=${m['total_pnl_dollar']:>+10,.2f}  ({m['trades']} trades)")
        print()

    # Print worst KILL strategies
    if tiers["KILL"]:
        print("─" * 72)
        print("  WORST KILL STRATEGIES (these are destroying capital)")
        print("─" * 72)
        for i, e in enumerate(tiers["KILL"][:30], 1):
            m = e["metrics"]
            reasons_str = "; ".join(e["reasons"][:2])
            print(f"  {i:>2}. {e['strategy'][:42]:<42} "
                  f"WR={m['win_rate']*100:5.1f}%  PF={m['profit_factor']:6.2f}  "
                  f"PnL=${m['total_pnl_dollar']:>+10,.2f}  ({m['trades']} trades)")
            print(f"      Reason: {reasons_str}")
        if len(tiers["KILL"]) > 30:
            print(f"  ... and {len(tiers['KILL']) - 30} more")
        print()

    # Print PROBATION
    if tiers["PROBATION"]:
        print("─" * 72)
        print(f"  PROBATION STRATEGIES ({len(tiers['PROBATION'])} — score penalty {PROBATION_PENALTY})")
        print("─" * 72)
        for i, e in enumerate(tiers["PROBATION"][:15], 1):
            m = e["metrics"]
            print(f"  {i:>2}. {e['strategy'][:45]:<45} "
                  f"WR={m['win_rate']*100:5.1f}%  PF={m['profit_factor']:6.2f}  "
                  f"PnL=${m['total_pnl_dollar']:>+10,.2f}  ({m['trades']} trades)")
        if len(tiers["PROBATION"]) > 15:
            print(f"  ... and {len(tiers['PROBATION']) - 15} more")
        print()

    # 6. Build kill list
    kill_names = [e["strategy"] for e in tiers["KILL"]]
    kill_list_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_killed": len(kill_names),
        "total_capital_saved": round(abs(kill_pnl), 2) if kill_pnl < 0 else 0,
        "kill_criteria": KILL_CRITERIA,
        "strategies": []
    }
    for e in tiers["KILL"]:
        kill_list_output["strategies"].append({
            "strategy": e["strategy"],
            "reasons": e["reasons"],
            "trades": e["metrics"]["trades"],
            "win_rate": e["metrics"]["win_rate"],
            "profit_factor": e["metrics"]["profit_factor"],
            "total_pnl_dollar": e["metrics"]["total_pnl_dollar"],
            "total_pnl_pct": e["metrics"]["total_pnl_pct"],
            "sharpe": e["metrics"]["sharpe"],
        })

    # 7. Build tiers output
    tiers_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "proven": len(tiers["PROVEN"]),
            "active": len(tiers["ACTIVE"]),
            "probation": len(tiers["PROBATION"]),
            "kill": len(tiers["KILL"]),
            "total": sum(len(v) for v in tiers.values()),
            "proven_pnl_dollar": round(proven_pnl, 2),
            "active_pnl_dollar": round(active_pnl, 2),
            "probation_pnl_dollar": round(probation_pnl, 2),
            "kill_pnl_dollar": round(kill_pnl, 2),
            "capital_saved_by_killing": round(abs(kill_pnl), 2) if kill_pnl < 0 else 0,
        },
        "score_adjustments": {
            "probation_penalty": PROBATION_PENALTY,
            "proven_bonus": PROVEN_BONUS,
        },
        "tiers": {}
    }
    for tier_name in ["PROVEN", "ACTIVE", "PROBATION", "KILL"]:
        tiers_output["tiers"][tier_name] = []
        for e in tiers[tier_name]:
            tiers_output["tiers"][tier_name].append({
                "strategy": e["strategy"],
                "reasons": e["reasons"],
                "metrics": e["metrics"],
            })

    # 8. Save outputs
    print("[4/5] Saving outputs...")
    _save_json(KILL_LIST_PATH, kill_list_output)
    print(f"  [SAVED] {KILL_LIST_PATH}")
    _save_json(TIERS_PATH, tiers_output)
    print(f"  [SAVED] {TIERS_PATH}")

    # 9. Update core_whitelist.json with killed strategies
    print()
    print("[5/5] Updating core_whitelist.json...")
    whitelist = _load_json(CORE_WHITELIST_PATH) or {
        "core_strategies": [],
        "incubator_strategies": [],
        "kill_list": [],
        "kill_patterns": [],
        "kill_categories": [],
        "metadata": {},
    }

    existing_kills = set(whitelist.get("kill_list", []))

    # PROTECTED STRATEGIES: never allow protected/core/incubator to be killed
    protected = set(whitelist.get("protected_strategies", []))
    protected.update(whitelist.get("core_strategies", []))
    protected.update(whitelist.get("incubator_strategies", []))
    protected_lower = {p.lower() for p in protected if isinstance(p, str)}
    safe_kill_names = []
    for kn in kill_names:
        kn_base = kn.split("::", 1)[1] if "::" in kn else kn
        if kn_base.lower() in protected_lower or kn.lower() in protected_lower:
            print(f"  [PROTECTED] Refusing to kill {kn} (in protected_strategies)")
            continue
        safe_kill_names.append(kn)

    new_kills = set(safe_kill_names) - existing_kills
    whitelist["kill_list"] = sorted(set(whitelist.get("kill_list", [])) | set(safe_kill_names))

    # Add proven strategies to core if not already there
    proven_names = [e["strategy"] for e in tiers["PROVEN"]]
    existing_core = set(whitelist.get("core_strategies", []))
    # Only promote strategies that are simple names (not system::strategy composites)
    promotable = [n for n in proven_names if "::" not in n and n not in existing_core]
    whitelist["core_strategies"] = sorted(set(whitelist.get("core_strategies", [])) | set(promotable))

    whitelist["metadata"]["last_kill_run"] = datetime.now(timezone.utc).isoformat()
    whitelist["metadata"]["kill_run_stats"] = {
        "total_killed": len(kill_names),
        "new_kills_added": len(new_kills),
        "capital_saved": round(abs(kill_pnl), 2) if kill_pnl < 0 else 0,
        "proven_promoted": len(promotable),
    }

    _save_json(CORE_WHITELIST_PATH, whitelist)
    print(f"  [SAVED] {CORE_WHITELIST_PATH}")
    print(f"  New kills added: {len(new_kills)}")
    print(f"  Proven promoted to core: {len(promotable)}")
    print()

    # Final summary
    print("=" * 72)
    surviving = len(tiers["PROVEN"]) + len(tiers["ACTIVE"])
    print(f"  FINAL: {surviving} strategies survive out of {sum(len(v) for v in tiers.values())}")
    print(f"  PROVEN: {len(tiers['PROVEN'])} | ACTIVE: {len(tiers['ACTIVE'])} | PROBATION: {len(tiers['PROBATION'])} | KILLED: {len(tiers['KILL'])}")
    if kill_pnl < 0:
        print(f"  CAPITAL SAVED: ${abs(kill_pnl):,.2f}")
    print("=" * 72)

    return tiers_output


if __name__ == "__main__":
    run()
