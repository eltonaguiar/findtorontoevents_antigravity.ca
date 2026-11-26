#!/usr/bin/env python3
"""
Audit Impact Tracker — Measures before/after performance of the 7 fixes applied 2026-03-13.

Reads live data from:
  - alpha_engine/data/strategy_performance.json
  - alpha_engine/data/closed_picks.json
  - KIMI_RISEOFTHECLAW/data/signal_tracking.json
  - KIMI_RISEOFTHECLAW/data/ml_training_stats.json
  - cross_aggregation/data/consensus_outcomes.json
  - battleground/data/ (incubator picks)

Outputs:
  - battleground/data/audit_baseline_20260313.json  (snapshot)
  - battleground/data/audit_impact_results.json     (comparison)
"""

import json
import os
import math
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AUDIT_CUTOFF = datetime(2026, 3, 13, 11, 30, 0, tzinfo=timezone.utc)
AUDIT_CUTOFF_ISO = AUDIT_CUTOFF.isoformat()

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "battleground" / "data"

DATA_PATHS = {
    "alpha_strategy_perf": ROOT / "alpha_engine" / "data" / "strategy_performance.json",
    "alpha_closed_picks":  ROOT / "alpha_engine" / "data" / "closed_picks.json",
    "kimi_signal_tracking": ROOT / "KIMI_RISEOFTHECLAW" / "data" / "signal_tracking.json",
    "kimi_ml_stats":       ROOT / "KIMI_RISEOFTHECLAW" / "data" / "ml_training_stats.json",
    "consensus_outcomes":  ROOT / "cross_aggregation" / "data" / "consensus_outcomes.json",
    "incubator_picks":     ROOT / "battleground" / "data" / "active_picks.json",
    "incubator_closed":    ROOT / "battleground" / "data" / "closed_picks.json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path):
    """Load JSON file, return None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [WARN] Could not load {path.name}: {exc}")
        return None


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [OK] Saved {path}")


def parse_ts(raw) -> datetime | None:
    """Best-effort ISO timestamp parse."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def safe_div(a, b, default=0.0):
    return a / b if b else default


def compute_sharpe(pnl_list: list[float], risk_free=0.0) -> float:
    """Annualized Sharpe from a list of per-trade PnL percentages."""
    if len(pnl_list) < 2:
        return 0.0
    mean_r = sum(pnl_list) / len(pnl_list) - risk_free
    var = sum((r - mean_r - risk_free) ** 2 for r in pnl_list) / (len(pnl_list) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    # Annualise assuming ~365 trades/year (daily-ish cadence)
    return (mean_r / std) * math.sqrt(365)


def split_picks(picks: list[dict], ts_field: str = "timestamp"):
    """Split a list of picks into before/after audit cutoff."""
    before, after = [], []
    for p in picks:
        ts = parse_ts(p.get(ts_field) or p.get("created_at") or p.get("entry_time") or p.get("tracked_at"))
        if ts is None or ts < AUDIT_CUTOFF:
            before.append(p)
        else:
            after.append(p)
    return before, after


def pick_stats(picks: list[dict], pnl_field="pnl_pct", status_field="status"):
    """Compute WR, avg PnL, total PnL, Sharpe from a list of closed picks."""
    closed = [p for p in picks if p.get(status_field, "").upper() in ("WON", "LOST", "TP_HIT", "SL_HIT")]
    if not closed:
        return {
            "total_closed": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "avg_pnl_pct": 0.0, "total_pnl_pct": 0.0, "sharpe": 0.0,
            "sl_hit_count": 0, "sl_hit_rate": 0.0,
        }
    wins = sum(1 for p in closed if p.get(status_field, "").upper() in ("WON", "TP_HIT"))
    losses = len(closed) - wins
    pnl_list = [float(p.get(pnl_field, 0) or 0) for p in closed]
    sl_hits = sum(1 for p in closed if str(p.get("exit_reason", "")).upper() == "SL_HIT")
    return {
        "total_closed": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(safe_div(wins, len(closed)) * 100, 2),
        "avg_pnl_pct": round(safe_div(sum(pnl_list), len(pnl_list)), 4),
        "total_pnl_pct": round(sum(pnl_list), 4),
        "sharpe": round(compute_sharpe(pnl_list), 3),
        "sl_hit_count": sl_hits,
        "sl_hit_rate": round(safe_div(sl_hits, len(closed)) * 100, 2),
    }


# ---------------------------------------------------------------------------
# Per-system metric extraction
# ---------------------------------------------------------------------------
def extract_alpha_engine_metrics():
    """Alpha Engine: per-strategy perf + closed picks split by audit cutoff."""
    print("[1/5] Alpha Engine ...")
    strat_perf = load_json(DATA_PATHS["alpha_strategy_perf"]) or {}
    closed_picks = load_json(DATA_PATHS["alpha_closed_picks"]) or []

    # Aggregate strategy-level stats
    total_closed = sum(s.get("closed_picks", 0) for s in strat_perf.values())
    total_wins = sum(s.get("wins", 0) for s in strat_perf.values())
    total_sl = sum(s.get("exit_reasons", {}).get("SL_HIT", 0) for s in strat_perf.values())

    # Split closed picks
    before, after = split_picks(closed_picks)
    before_stats = pick_stats(before)
    after_stats = pick_stats(after)

    return {
        "system": "alpha_engine",
        "aggregate": {
            "total_strategies": len(strat_perf),
            "total_closed": total_closed,
            "total_wins": total_wins,
            "overall_wr": round(safe_div(total_wins, total_closed) * 100, 2),
            "total_sl_hits": total_sl,
            "sl_hit_rate": round(safe_div(total_sl, total_closed) * 100, 2),
        },
        "before_audit": before_stats,
        "after_audit": after_stats,
    }


def extract_kimi_metrics():
    """KIMI: signal tracking summary + ML AUC."""
    print("[2/5] KIMI Scanner ...")
    tracking = load_json(DATA_PATHS["kimi_signal_tracking"]) or {}
    ml_stats = load_json(DATA_PATHS["kimi_ml_stats"]) or {}

    summary = tracking.get("summary", {})
    signals = tracking.get("signals", [])

    # Split signals into before/after
    before, after = split_picks(signals, ts_field="entry_time")
    before_closed = [s for s in before if s.get("status", "").upper() in ("WON", "LOST", "TP_HIT", "SL_HIT")]
    after_closed = [s for s in after if s.get("status", "").upper() in ("WON", "LOST", "TP_HIT", "SL_HIT")]

    def signal_stats(sigs):
        if not sigs:
            return {"total": 0, "wins": 0, "losses": 0, "wr": 0.0, "avg_pnl": 0.0}
        wins = sum(1 for s in sigs if s.get("status", "").upper() in ("WON", "TP_HIT"))
        pnls = [float(s.get("pnl_pct", 0) or 0) for s in sigs]
        return {
            "total": len(sigs),
            "wins": wins,
            "losses": len(sigs) - wins,
            "wr": round(safe_div(wins, len(sigs)) * 100, 2),
            "avg_pnl": round(safe_div(sum(pnls), len(pnls)), 4),
        }

    return {
        "system": "kimi_scanner",
        "aggregate": {
            "total_signals": summary.get("total_signals", 0),
            "wins": summary.get("wins", 0),
            "losses": summary.get("losses", 0),
            "open": summary.get("open", 0),
            "win_rate": summary.get("win_rate", 0.0),
            "avg_pnl": summary.get("avg_pnl", 0.0),
            "total_pnl": summary.get("total_pnl", 0.0),
        },
        "ml": {
            "cv_auc_mean": ml_stats.get("cv_auc_mean", 0.0),
            "cv_auc_std": ml_stats.get("cv_auc_std", 0.0),
            "n_samples": ml_stats.get("n_samples", 0),
            "mode": ml_stats.get("mode", "unknown"),
            "trained_at": ml_stats.get("trained_at", ""),
        },
        "before_audit": signal_stats(before_closed),
        "after_audit": signal_stats(after_closed),
    }


def extract_consensus_metrics():
    """Cross-aggregator consensus outcomes."""
    print("[3/5] Cross Aggregator ...")
    data = load_json(DATA_PATHS["consensus_outcomes"]) or {}
    active = data.get("active", [])
    closed = data.get("closed", [])

    before_closed, after_closed = split_picks(closed, ts_field="closed_at")

    def consensus_stats(picks):
        if not picks:
            return {"total": 0, "wins": 0, "losses": 0, "wr": 0.0, "avg_pnl": 0.0}
        wins = sum(1 for p in picks if p.get("status", "").upper() == "WON")
        pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
        return {
            "total": len(picks),
            "wins": wins,
            "losses": len(picks) - wins,
            "wr": round(safe_div(wins, len(picks)) * 100, 2),
            "avg_pnl": round(safe_div(sum(pnls), len(pnls)), 4),
        }

    return {
        "system": "cross_aggregator",
        "aggregate": {
            "active_count": len(active),
            "closed_count": len(closed),
            **consensus_stats(closed),
        },
        "before_audit": consensus_stats(before_closed),
        "after_audit": consensus_stats(after_closed),
    }


def extract_incubator_metrics():
    """Incubator: promoted strategies count, pick performance."""
    print("[4/5] Incubator ...")
    active = load_json(DATA_PATHS["incubator_picks"]) or []
    closed = load_json(DATA_PATHS["incubator_closed"]) or []

    # closed may be a list or a dict with a "picks" key
    if isinstance(closed, dict):
        closed = closed.get("picks", closed.get("closed", []))
    if isinstance(active, dict):
        active = active.get("picks", active.get("active", []))

    before, after = split_picks(closed)

    return {
        "system": "incubator",
        "aggregate": {
            "active_strategies": len(active) if isinstance(active, list) else 0,
            "closed_count": len(closed) if isinstance(closed, list) else 0,
        },
        "before_audit": pick_stats(before) if isinstance(before, list) else {},
        "after_audit": pick_stats(after) if isinstance(after, list) else {},
    }


def extract_strategy_performance_detail():
    """Per-strategy exit-reason breakdown from alpha strategy_performance.json."""
    print("[5/5] Strategy exit-reason breakdown ...")
    strat_perf = load_json(DATA_PATHS["alpha_strategy_perf"]) or {}
    breakdown = {}
    for name, stats in strat_perf.items():
        exits = stats.get("exit_reasons", {})
        total = stats.get("closed_picks", 0)
        sl = exits.get("SL_HIT", 0)
        breakdown[name] = {
            "closed": total,
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "wr": stats.get("win_rate", 0.0),
            "sl_hits": sl,
            "sl_hit_rate": round(safe_div(sl, total) * 100, 2),
            "exit_reasons": exits,
            "kelly": stats.get("kelly_fraction", 0.0),
            "sharpe": stats.get("sharpe", 0.0),
        }
    return breakdown


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------
def create_baseline_snapshot() -> dict:
    """Build and save the baseline snapshot."""
    print("=" * 60)
    print("AUDIT IMPACT TRACKER — Creating baseline snapshot")
    print(f"  Audit cutoff: {AUDIT_CUTOFF_ISO}")
    print("=" * 60)

    alpha = extract_alpha_engine_metrics()
    kimi = extract_kimi_metrics()
    consensus = extract_consensus_metrics()
    incubator = extract_incubator_metrics()
    strat_detail = extract_strategy_performance_detail()

    snapshot = {
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_cutoff": AUDIT_CUTOFF_ISO,
        "description": "Baseline snapshot for 7 critical fixes applied 2026-03-13",
        "fixes_applied": [
            "1. SL placement fix (ATR-based instead of fixed %)",
            "2. ML AUC threshold gate (>0.55 required)",
            "3. Forward-validation minimum trades increased (15 -> 30)",
            "4. DSR gate for incubator promotion (Sharpe >= 1.0)",
            "5. Consensus minimum agreement count raised (2 -> 3)",
            "6. Exit-reason tracking added to all systems",
            "7. Walk-forward confirmation required before production",
        ],
        "systems": {
            "alpha_engine": alpha,
            "kimi_scanner": kimi,
            "cross_aggregator": consensus,
            "incubator": incubator,
        },
        "strategy_detail": strat_detail,
    }

    save_json(OUTPUT_DIR / "audit_baseline_20260313.json", snapshot)
    return snapshot


def compare_before_after(baseline: dict | None = None) -> dict:
    """
    Compare before-audit vs after-audit metrics.
    If no baseline passed, loads from disk.
    """
    if baseline is None:
        bp = OUTPUT_DIR / "audit_baseline_20260313.json"
        baseline = load_json(bp)
        if baseline is None:
            print("[ERROR] No baseline found. Run create_baseline_snapshot() first.")
            return {}

    # Re-extract current data (after-audit may have grown since snapshot)
    alpha = extract_alpha_engine_metrics()
    kimi = extract_kimi_metrics()
    consensus = extract_consensus_metrics()
    incubator = extract_incubator_metrics()

    def pct_change(before_val, after_val):
        """Percentage change, positive = improvement direction depends on metric."""
        if before_val == 0:
            return None
        return round(((after_val - before_val) / abs(before_val)) * 100, 2)

    def compare_system(name, current):
        b = current.get("before_audit", {})
        a = current.get("after_audit", {})
        comparisons = {}

        # Win rate
        b_wr = b.get("win_rate", b.get("wr", 0.0))
        a_wr = a.get("win_rate", a.get("wr", 0.0))
        wr_delta = pct_change(b_wr, a_wr)
        comparisons["win_rate"] = {
            "before": b_wr, "after": a_wr,
            "change_pct": wr_delta,
            "improved": (a_wr > b_wr) if a.get("total", a.get("total_closed", 0)) > 0 else None,
        }

        # Avg PnL
        b_pnl = b.get("avg_pnl_pct", b.get("avg_pnl", 0.0))
        a_pnl = a.get("avg_pnl_pct", a.get("avg_pnl", 0.0))
        pnl_delta = pct_change(b_pnl, a_pnl) if b_pnl != 0 else None
        comparisons["avg_pnl"] = {
            "before": b_pnl, "after": a_pnl,
            "change_pct": pnl_delta,
            "improved": (a_pnl > b_pnl) if a.get("total", a.get("total_closed", 0)) > 0 else None,
        }

        # SL hit rate (alpha-specific, lower is better)
        if "sl_hit_rate" in b:
            b_sl = b.get("sl_hit_rate", 0.0)
            a_sl = a.get("sl_hit_rate", 0.0)
            comparisons["sl_hit_rate"] = {
                "before": b_sl, "after": a_sl,
                "change_pct": pct_change(b_sl, a_sl),
                "improved": (a_sl < b_sl) if a.get("total_closed", 0) > 0 else None,
                "note": "Lower is better",
            }

        # Sharpe (alpha-specific)
        if "sharpe" in b:
            b_sh = b.get("sharpe", 0.0)
            a_sh = a.get("sharpe", 0.0)
            comparisons["sharpe"] = {
                "before": b_sh, "after": a_sh,
                "change_pct": pct_change(b_sh, a_sh) if b_sh != 0 else None,
                "improved": (a_sh > b_sh) if a.get("total_closed", 0) > 0 else None,
            }

        # Trade counts
        comparisons["trade_count"] = {
            "before": b.get("total_closed", b.get("total", 0)),
            "after": a.get("total_closed", a.get("total", 0)),
        }

        return comparisons

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_cutoff": AUDIT_CUTOFF_ISO,
        "baseline_timestamp": baseline.get("snapshot_timestamp", ""),
        "systems": {},
        "summary_table": [],
    }

    systems_current = {
        "alpha_engine": alpha,
        "kimi_scanner": kimi,
        "cross_aggregator": consensus,
        "incubator": incubator,
    }

    for sys_name, current in systems_current.items():
        comp = compare_system(sys_name, current)
        results["systems"][sys_name] = comp

        # Build human-readable summary row
        wr = comp.get("win_rate", {})
        pnl = comp.get("avg_pnl", {})
        sl = comp.get("sl_hit_rate", {})
        trades_before = comp.get("trade_count", {}).get("before", 0)
        trades_after = comp.get("trade_count", {}).get("after", 0)

        row = {
            "system": sys_name,
            "trades_before": trades_before,
            "trades_after": trades_after,
            "wr_before": wr.get("before", 0),
            "wr_after": wr.get("after", 0),
            "wr_change": wr.get("change_pct"),
            "wr_improved": wr.get("improved"),
            "pnl_before": pnl.get("before", 0),
            "pnl_after": pnl.get("after", 0),
        }
        if sl:
            row["sl_before"] = sl.get("before", 0)
            row["sl_after"] = sl.get("after", 0)
            row["sl_improved"] = sl.get("improved")
        results["summary_table"].append(row)

    # ML AUC tracking for KIMI
    baseline_ml = baseline.get("systems", {}).get("kimi_scanner", {}).get("ml", {})
    current_ml = kimi.get("ml", {})
    results["kimi_ml_comparison"] = {
        "auc_at_baseline": baseline_ml.get("cv_auc_mean", 0.0),
        "auc_current": current_ml.get("cv_auc_mean", 0.0),
        "auc_change": pct_change(
            baseline_ml.get("cv_auc_mean", 0.0),
            current_ml.get("cv_auc_mean", 0.0),
        ),
        "samples_at_baseline": baseline_ml.get("n_samples", 0),
        "samples_current": current_ml.get("n_samples", 0),
    }

    save_json(OUTPUT_DIR / "audit_impact_results.json", results)
    print_comparison_table(results)
    return results


def print_comparison_table(results: dict):
    """Pretty-print the before/after comparison to stdout."""
    print()
    print("=" * 72)
    print("  AUDIT IMPACT COMPARISON  —  Before vs After 2026-03-13 11:30 UTC")
    print("=" * 72)

    header = f"{'System':<20} {'Trades B/A':>10} {'WR Before':>10} {'WR After':>10} {'WR Chg':>8} {'Status':>8}"
    print(header)
    print("-" * 72)

    for row in results.get("summary_table", []):
        trades = f"{row['trades_before']}/{row['trades_after']}"
        wr_b = f"{row['wr_before']:.1f}%"
        wr_a = f"{row['wr_after']:.1f}%"
        chg = f"{row['wr_change']:.1f}%" if row.get("wr_change") is not None else "N/A"

        improved = row.get("wr_improved")
        if improved is True:
            status = "UP"
        elif improved is False:
            status = "DOWN"
        else:
            status = "WAIT"

        print(f"{row['system']:<20} {trades:>10} {wr_b:>10} {wr_a:>10} {chg:>8} {status:>8}")

    # SL hit rate detail for alpha
    for row in results.get("summary_table", []):
        if "sl_before" in row and row["system"] == "alpha_engine":
            print()
            print(f"  Alpha SL Hit Rate:  {row['sl_before']:.1f}% -> {row['sl_after']:.1f}%  ", end="")
            if row.get("sl_improved") is True:
                print("(IMPROVED - fewer stop-losses hit)")
            elif row.get("sl_improved") is False:
                print("(WORSE - more stop-losses hit)")
            else:
                print("(waiting for post-audit trades)")

    # ML AUC
    ml = results.get("kimi_ml_comparison", {})
    if ml.get("auc_at_baseline"):
        print(f"  KIMI ML AUC:        {ml['auc_at_baseline']:.4f} -> {ml['auc_current']:.4f}  ", end="")
        chg = ml.get("auc_change")
        if chg is not None and chg > 0:
            print(f"(+{chg:.1f}% IMPROVED)")
        elif chg is not None:
            print(f"({chg:.1f}%)")
        else:
            print()

    print()
    print("=" * 72)
    print(f"  Results saved to: battleground/data/audit_impact_results.json")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = create_baseline_snapshot()
    compare_before_after(baseline)
