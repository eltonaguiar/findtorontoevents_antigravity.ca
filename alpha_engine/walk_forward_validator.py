#!/usr/bin/env python3
"""
Walk-Forward Validator — Tests whether strategies have REAL edge or are overfitting.

Loads closed picks from audit_trail/data/dashboard_payload.json, splits each strategy's
trades into chronological windows, and checks consistency of edge across time.

Stdlib only. Windows UTF-8 safe.
"""

import json
import os
import sys
import math
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

try:
    from alpha_engine.statistical_tests import run_all_tests as run_statistical_tests
    HAS_STAT_TESTS = True
except ImportError:
    try:
        from statistical_tests import run_all_tests as run_statistical_tests
        HAS_STAT_TESTS = True
    except ImportError:
        HAS_STAT_TESTS = False

# Windows UTF-8 fix
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "alpha_engine" / "data"
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = DATA_DIR / "walk_forward_validation.json"

MIN_TRADES = 20
NUM_WINDOWS = 5


def load_closed_picks():
    """Load all closed picks from dashboard payload."""
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    picks = []
    # recent_closed
    for p in data.get("picks", {}).get("recent_closed", []):
        picks.append(p)
    # universal_resolved_picks (if present)
    for p in data.get("universal_resolved_picks", []):
        picks.append(p)

    # Also gather leaderboard for supplementary stats
    leaderboard = {x["strategy"]: x for x in data.get("leaderboard", []) if x.get("strategy")}

    return picks, leaderboard


def parse_ts(ts_str):
    """Parse various timestamp formats to epoch seconds."""
    if not ts_str:
        return None
    ts_str = str(ts_str).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def compute_window_metrics(trades):
    """Compute WR, PF, avg PnL, Sharpe estimate for a set of trades."""
    if not trades:
        return {"wr": 0, "pf": 0, "avg_pnl": 0, "sharpe": 0, "n": 0,
                "wins": 0, "losses": 0, "gross_win": 0, "gross_loss": 0,
                "total_pnl": 0}

    pnls = [t["pnl_pct"] for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    losses = n - wins
    wr = (wins / n) * 100 if n else 0

    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0)

    avg_pnl = sum(pnls) / n if n else 0

    # Sharpe estimate (per-trade)
    if n >= 2:
        mean = avg_pnl
        variance = sum((p - mean) ** 2 for p in pnls) / (n - 1)
        std = math.sqrt(variance) if variance > 0 else 0.001
        sharpe = mean / std if std > 0 else 0
    else:
        sharpe = 0

    return {
        "wr": round(wr, 1),
        "pf": round(pf, 2),
        "avg_pnl": round(avg_pnl, 3),
        "sharpe": round(sharpe, 3),
        "n": n,
        "wins": wins,
        "losses": losses,
        "gross_win": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "total_pnl": round(sum(pnls), 2),
    }


def compute_consistency_score(windows):
    """
    Consistency Score (0-100):
    - All 5 windows positive PnL: +40 pts
    - WR > 45% in 4/5 windows: +25 pts
    - PF > 1.0 in 4/5 windows: +20 pts
    - No single window with WR < 30%: +15 pts
    """
    score = 0
    n_win = len(windows)
    if n_win == 0:
        return 0, {}

    positive_pnl_count = sum(1 for w in windows if w["total_pnl"] > 0)
    wr_above_45_count = sum(1 for w in windows if w["wr"] > 45)
    pf_above_1_count = sum(1 for w in windows if w["pf"] > 1.0)
    min_wr = min(w["wr"] for w in windows)

    # All windows positive PnL
    if positive_pnl_count == n_win:
        score += 40
    elif positive_pnl_count >= n_win - 1:
        score += 20

    # WR > 45% in 4/5 windows
    if wr_above_45_count >= n_win - 1:
        score += 25
    elif wr_above_45_count >= n_win - 2:
        score += 10

    # PF > 1.0 in 4/5 windows
    if pf_above_1_count >= n_win - 1:
        score += 20
    elif pf_above_1_count >= n_win - 2:
        score += 8

    # No window with WR < 30%
    if min_wr >= 30:
        score += 15

    return score, {
        "positive_pnl_windows": positive_pnl_count,
        "wr_above_45_windows": wr_above_45_count,
        "pf_above_1_windows": pf_above_1_count,
        "min_window_wr": round(min_wr, 1),
    }


def detect_edge_decay(windows):
    """
    Compare first half vs second half performance.
    Flag as DECAYING if second half degrades significantly.
    """
    if len(windows) < 4:
        return {"decaying": False, "reason": "insufficient_windows"}

    mid = len(windows) // 2
    first_half = windows[:mid]
    second_half = windows[mid:]

    def agg(ws):
        total_wins = sum(w["wins"] for w in ws)
        total_n = sum(w["n"] for w in ws)
        wr = (total_wins / total_n * 100) if total_n else 0
        gross_win = sum(w["gross_win"] for w in ws)
        gross_loss = sum(w["gross_loss"] for w in ws)
        pf = (gross_win / gross_loss) if gross_loss > 0 else (999 if gross_win > 0 else 0)
        avg_pnl = sum(w["total_pnl"] for w in ws) / total_n if total_n else 0
        return {"wr": wr, "pf": pf, "avg_pnl": avg_pnl, "n": total_n}

    first = agg(first_half)
    second = agg(second_half)

    reasons = []
    decaying = False

    # WR decay: second half < first half - 10pp
    wr_drop = first["wr"] - second["wr"]
    if wr_drop > 10:
        reasons.append(f"WR dropped {wr_drop:.1f}pp ({first['wr']:.1f}% -> {second['wr']:.1f}%)")
        decaying = True

    # PF decay: second half < first half * 0.5
    if first["pf"] > 0 and second["pf"] < first["pf"] * 0.5:
        reasons.append(f"PF halved ({first['pf']:.2f} -> {second['pf']:.2f})")
        decaying = True

    # Avg PnL sign flip
    if first["avg_pnl"] > 0 and second["avg_pnl"] < 0:
        reasons.append(f"Avg PnL flipped negative ({first['avg_pnl']:.3f} -> {second['avg_pnl']:.3f})")
        decaying = True

    return {
        "decaying": decaying,
        "reasons": reasons,
        "first_half": {k: round(v, 3) if isinstance(v, float) else v for k, v in first.items()},
        "second_half": {k: round(v, 3) if isinstance(v, float) else v for k, v in second.items()},
    }


def assess_regime_robustness(trades):
    """
    Split trades by direction (LONG vs SHORT) as regime proxy.
    Flag strategies that only profit in one direction.
    """
    long_trades = [t for t in trades if t.get("direction", "").upper() == "LONG"]
    short_trades = [t for t in trades if t.get("direction", "").upper() == "SHORT"]

    result = {
        "multi_direction": len(long_trades) > 0 and len(short_trades) > 0,
        "long_count": len(long_trades),
        "short_count": len(short_trades),
    }

    if long_trades:
        long_pnls = [t["pnl_pct"] for t in long_trades]
        result["long_wr"] = round(sum(1 for p in long_pnls if p > 0) / len(long_pnls) * 100, 1)
        result["long_avg_pnl"] = round(sum(long_pnls) / len(long_pnls), 3)

    if short_trades:
        short_pnls = [t["pnl_pct"] for t in short_trades]
        result["short_wr"] = round(sum(1 for p in short_pnls if p > 0) / len(short_pnls) * 100, 1)
        result["short_avg_pnl"] = round(sum(short_pnls) / len(short_pnls), 3)

    # Single-regime flag: only profitable in one direction with 10+ trades each
    single_regime = False
    if len(long_trades) >= 10 and len(short_trades) >= 10:
        long_profitable = result.get("long_avg_pnl", 0) > 0
        short_profitable = result.get("short_avg_pnl", 0) > 0
        if long_profitable != short_profitable:
            single_regime = True
    elif not result["multi_direction"]:
        single_regime = None  # Unknown — only one direction

    result["single_regime_only"] = single_regime
    return result


def determine_verdict(consistency_score, decay_info, regime_info, n_trades):
    """
    ROBUST: Consistency >= 70, no decay, multi-regime
    MODERATE: Consistency 40-69, minor decay acceptable
    FRAGILE: Consistency < 40 OR significant decay OR single-regime-only
    INSUFFICIENT: < 20 trades
    """
    if n_trades < MIN_TRADES:
        return "INSUFFICIENT"

    is_decaying = decay_info.get("decaying", False)
    single_regime = regime_info.get("single_regime_only", None)

    if consistency_score >= 70 and not is_decaying and single_regime is not True:
        return "ROBUST"
    elif consistency_score < 40 or is_decaying or single_regime is True:
        return "FRAGILE"
    else:
        return "MODERATE"


def run():
    """Main entry point."""
    print("=" * 80)
    print("WALK-FORWARD VALIDATOR -- Real Edge or Overfitting?")
    print("=" * 80)
    print()

    picks, leaderboard = load_closed_picks()
    print(f"Loaded {len(picks)} closed picks, {len(leaderboard)} leaderboard strategies")

    # Group picks by strategy
    by_strategy = defaultdict(list)
    skipped_no_pnl = 0
    skipped_no_ts = 0
    for p in picks:
        strategy = p.get("strategy", "").strip()
        if not strategy:
            continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            skipped_no_pnl += 1
            continue  # breakeven (pnl==0) is a valid data point
        ts = parse_ts(p.get("closed_at") or p.get("timestamp"))
        if ts is None:
            skipped_no_ts += 1
            continue
        by_strategy[strategy].append({
            "pnl_pct": float(pnl),
            "ts": ts,
            "direction": p.get("direction", ""),
            "symbol": p.get("symbol", ""),
            "status": p.get("status", ""),
            "source_system": p.get("source_system", ""),
        })

    print(f"Skipped: {skipped_no_pnl} zero/null PnL, {skipped_no_ts} no timestamp")
    print(f"Strategies with trade data: {len(by_strategy)}")

    # Sort each strategy's trades chronologically
    for strat in by_strategy:
        by_strategy[strat].sort(key=lambda x: x["ts"])

    # Validate each strategy
    results = []
    for strategy, trades in by_strategy.items():
        n = len(trades)
        lb_entry = leaderboard.get(strategy, {})
        lb_trades = lb_entry.get("fwd_trades", 0) or 0

        entry = {
            "strategy": strategy,
            "trades_in_data": n,
            "trades_in_leaderboard": lb_trades,
            "source_systems": list(set(t["source_system"] for t in trades)),
        }

        if n < MIN_TRADES:
            entry["verdict"] = "INSUFFICIENT"
            entry["consistency_score"] = None
            entry["reason"] = f"Only {n} trades in data (need {MIN_TRADES}+)"
            results.append(entry)
            continue

        # Split into NUM_WINDOWS chronological windows
        window_size = n // NUM_WINDOWS
        remainder = n % NUM_WINDOWS
        windows = []
        window_pnl_arrays = []
        idx = 0
        for w in range(NUM_WINDOWS):
            sz = window_size + (1 if w < remainder else 0)
            if sz == 0:
                continue
            window_trades = trades[idx:idx + sz]
            metrics = compute_window_metrics(window_trades)
            metrics["window_idx"] = w
            metrics["from_ts"] = datetime.fromtimestamp(
                window_trades[0]["ts"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            metrics["to_ts"] = datetime.fromtimestamp(
                window_trades[-1]["ts"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            windows.append(metrics)
            window_pnl_arrays.append([t["pnl_pct"] for t in window_trades])
            idx += sz

        # Consistency score
        consistency, consistency_detail = compute_consistency_score(windows)

        # Edge decay
        decay = detect_edge_decay(windows)

        # Regime robustness
        regime = assess_regime_robustness(trades)

        # Overall metrics
        overall = compute_window_metrics(trades)

        # Statistical validation tests
        stat_tests = None
        if HAS_STAT_TESTS and len(window_pnl_arrays) >= 2:
            all_pnls = [t["pnl_pct"] for t in trades]
            try:
                stat_tests = run_statistical_tests(all_pnls, window_pnl_arrays)
            except Exception:
                stat_tests = None

        # Verdict
        verdict = determine_verdict(consistency, decay, regime, n)

        entry.update({
            "verdict": verdict,
            "consistency_score": consistency,
            "consistency_detail": consistency_detail,
            "overall_metrics": overall,
            "windows": windows,
            "edge_decay": decay,
            "regime_robustness": regime,
            "statistical_tests": stat_tests,
            "leaderboard_wr": lb_entry.get("fwd_wr"),
            "leaderboard_pf": lb_entry.get("fwd_pf"),
            "leaderboard_health": lb_entry.get("health"),
        })
        results.append(entry)

    # Sort: ROBUST first, then MODERATE, FRAGILE, INSUFFICIENT
    verdict_order = {"ROBUST": 0, "MODERATE": 1, "FRAGILE": 2, "INSUFFICIENT": 3}
    results.sort(key=lambda x: (
        verdict_order.get(x["verdict"], 9),
        -(x.get("consistency_score") or -1),
    ))

    # Print ranked table
    print()
    print("=" * 110)
    print(f"{'STRATEGY':<50} {'VERDICT':<13} {'SCORE':>5} {'TRADES':>6} "
          f"{'WR%':>6} {'PF':>6} {'DECAY':>8} {'REGIME':>10}")
    print("-" * 110)

    counts = defaultdict(int)
    for r in results:
        v = r["verdict"]
        counts[v] += 1
        score = r.get("consistency_score")
        score_str = f"{score:>5}" if score is not None else "  N/A"
        n_trades = r["trades_in_data"]

        if v == "INSUFFICIENT":
            print(f"{r['strategy']:<50} {v:<13} {score_str} {n_trades:>6}")
            continue

        om = r.get("overall_metrics", {})
        wr = om.get("wr", 0)
        pf = om.get("pf", 0)
        decay_flag = "YES" if r.get("edge_decay", {}).get("decaying") else "no"
        regime_flag = "SINGLE" if r.get("regime_robustness", {}).get(
            "single_regime_only") is True else "multi"

        print(f"{r['strategy']:<50} {v:<13} {score_str} {n_trades:>6} "
              f"{wr:>5.1f}% {pf:>5.2f} {decay_flag:>8} {regime_flag:>10}")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print(f"  ROBUST:       {counts.get('ROBUST', 0)}")
    print(f"  MODERATE:     {counts.get('MODERATE', 0)}")
    print(f"  FRAGILE:      {counts.get('FRAGILE', 0)}")
    print(f"  INSUFFICIENT: {counts.get('INSUFFICIENT', 0)}")
    print(f"  Total:        {len(results)}")
    print()

    # Detail on ROBUST strategies
    robust = [r for r in results if r["verdict"] == "ROBUST"]
    if robust:
        print("--- ROBUST Strategies (Real Edge Confirmed) ---")
        for r in robust:
            om = r["overall_metrics"]
            print(f"  {r['strategy']}")
            print(f"    Score={r['consistency_score']}  Trades={r['trades_in_data']}  "
                  f"WR={om['wr']}%  PF={om['pf']}  AvgPnL={om['avg_pnl']}%  "
                  f"Sharpe={om['sharpe']}")
            for w in r.get("windows", []):
                print(f"    Window {w['window_idx']}: n={w['n']:>3}  WR={w['wr']:>5.1f}%  "
                      f"PF={w['pf']:>5.2f}  PnL={w['total_pnl']:>7.2f}%  "
                      f"[{w['from_ts']} -> {w['to_ts']}]")
        print()

    # Detail on DECAYING strategies
    decaying = [r for r in results if r.get("edge_decay", {}).get("decaying")]
    if decaying:
        print("--- DECAYING Strategies (Edge Fading) ---")
        for r in decaying:
            d = r["edge_decay"]
            print(f"  {r['strategy']}: {'; '.join(d.get('reasons', []))}")
            fh = d["first_half"]
            sh = d["second_half"]
            print(f"    1st half: WR={fh['wr']:.1f}%  PF={fh['pf']:.2f}  "
                  f"AvgPnL={fh['avg_pnl']:.3f}%")
            print(f"    2nd half: WR={sh['wr']:.1f}%  PF={sh['pf']:.2f}  "
                  f"AvgPnL={sh['avg_pnl']:.3f}%")
        print()

    # Statistical test results
    stat_tested = [r for r in results if r.get("statistical_tests")]
    if stat_tested:
        print("--- Statistical Validation Tests ---")
        for r in stat_tested:
            st = r["statistical_tests"]
            shapiro_p = st.get("shapiro_wilk", {}).get("p_value", "N/A")
            levene_p = st.get("levenes", {}).get("p_value", "N/A")
            rec_test = st.get("recommended_test", "?")
            rec_pass = st.get("recommended_result")
            overall = st.get("overall_pass")
            status = "PASS" if overall else ("FAIL" if overall is False else "N/A")
            normal_str = "yes" if st.get("shapiro_wilk", {}).get("normal") else "no"
            eqvar_str = "yes" if st.get("levenes", {}).get("equal_variance") else "no"
            print(f"  {r['strategy']:<45} normal={normal_str:>3}  eq_var={eqvar_str:>3}  "
                  f"recommended={rec_test:<15} overall={status}")
        print()

    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies_analyzed": len(results),
        "verdict_counts": dict(counts),
        "min_trades_threshold": MIN_TRADES,
        "num_windows": NUM_WINDOWS,
        "strategies": results,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    run()
