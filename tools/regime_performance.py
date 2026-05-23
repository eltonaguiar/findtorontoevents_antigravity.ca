#!/usr/bin/env python3
"""Regime-segmented performance reporting with Sharpe/Sortino/Calmar per regime.

Kilocode #6: Answers "Where does our alpha come from? Which strategies work
in which market conditions?"

Since regime fields are unpopulated in pick data, we infer BTC regime from
the distribution of BTCUSDT closed picks in rolling weekly windows:
  - BULL:  weekly avg PnL of BTC picks > +1%
  - BEAR:  weekly avg PnL of BTC picks < -1%
  - CHOP:  in between, volatility (std) > 3%
  - CRISIS: BTC picks losing > 3% avg in the window
  - UNKNOWN: no BTC data for that week
"""

import json, math, sys, os
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts_str):
    if not ts_str:
        return None
    for fmt in (None, "%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S EST", "%Y-%m-%d %H:%M:%S"):
        try:
            if fmt is None:
                dt = datetime.fromisoformat(ts_str)
            else:
                dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _week_key(dt):
    """ISO year-week string."""
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _safe_div(a, b, default=0.0):
    return a / b if b else default


# ---------------------------------------------------------------------------
# Regime inference from BTC pick PnL
# ---------------------------------------------------------------------------

def infer_weekly_regimes(picks):
    """Build a dict mapping week-key -> regime from BTCUSDT pick performance."""
    btc_weeks = defaultdict(list)
    for p in picks:
        sym = (p.get("symbol") or "").upper()
        if "BTC" not in sym:
            continue
        ts = _parse_ts(p.get("timestamp"))
        if ts is None:
            continue
        pnl = float(p.get("pnl_pct", 0) or 0)
        btc_weeks[_week_key(ts)].append(pnl)

    regimes = {}
    for wk, pnls in btc_weeks.items():
        avg = sum(pnls) / len(pnls)
        std = math.sqrt(sum((x - avg) ** 2 for x in pnls) / len(pnls)) if len(pnls) > 1 else 0
        if avg < -3:
            regimes[wk] = "CRISIS"
        elif avg < -1:
            regimes[wk] = "BEAR"
        elif avg > 1:
            regimes[wk] = "BULL"
        elif std > 3:
            regimes[wk] = "CHOP"
        else:
            regimes[wk] = "CHOP"  # low-vol sideways still CHOP
    return regimes


def assign_regime(pick, weekly_regimes):
    """Return regime label for a single pick."""
    # Prefer explicit fields if ever populated
    for field in ("regime", "btc_regime", "regime_at_entry", "fgi_regime"):
        val = (pick.get(field) or "").upper().strip()
        if val in ("BULL", "BEAR", "CHOP", "RANGING", "CRISIS"):
            return val if val != "RANGING" else "CHOP"
    ts = _parse_ts(pick.get("timestamp"))
    if ts is None:
        return "UNKNOWN"
    return weekly_regimes.get(_week_key(ts), "UNKNOWN")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(pnls):
    """Compute performance metrics from a list of PnL percentages."""
    n = len(pnls)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for x in pnls if x > 0)
    losses = [x for x in pnls if x < 0]
    gross_win = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(losses))
    avg_pnl = sum(pnls) / n
    cum_pnl = sum(pnls)
    std = math.sqrt(sum((x - avg_pnl) ** 2 for x in pnls) / n) if n > 1 else 0

    # Sharpe (annualized, assume ~250 trades/year equiv)
    sharpe = _safe_div(avg_pnl, std) * math.sqrt(min(n, 250)) if std > 0 else 0

    # Sortino (downside deviation)
    down_dev = math.sqrt(sum(min(x, 0) ** 2 for x in pnls) / n) if n > 0 else 0
    sortino = _safe_div(avg_pnl, down_dev) * math.sqrt(min(n, 250)) if down_dev > 0 else 0

    # Max drawdown (cumulative equity curve)
    equity = 0
    peak = 0
    max_dd = 0
    for x in pnls:
        equity += x
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    calmar = _safe_div(cum_pnl, max_dd) if max_dd > 0 else (cum_pnl if cum_pnl > 0 else 0)

    return {
        "n": n,
        "wr_pct": round(100 * wins / n, 1),
        "pf": round(_safe_div(gross_win, gross_loss), 2),
        "avg_pnl": round(avg_pnl, 3),
        "cum_pnl": round(cum_pnl, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_dd": round(max_dd, 2),
        "calmar": round(calmar, 2),
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run(data_path=None, output_path=None):
    repo = Path(__file__).resolve().parent.parent
    if data_path is None:
        data_path = repo / "audit_dashboard" / "data" / "dashboard_data.json"
    if output_path is None:
        output_path = repo / "tools" / "regime_performance_results.json"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks")

    # 1. Infer regimes
    weekly_regimes = infer_weekly_regimes(picks)
    print(f"Inferred regimes for {len(weekly_regimes)} weeks: "
          + str({r: sum(1 for v in weekly_regimes.values() if v == r)
                 for r in sorted(set(weekly_regimes.values()))}))

    # 2. Classify each pick
    regime_picks = defaultdict(list)       # regime -> [pnl]
    regime_dir = defaultdict(list)         # (regime, direction) -> [pnl]
    source_regime = defaultdict(list)      # (source, regime) -> [pnl]
    source_counts = defaultdict(int)

    for p in picks:
        reg = assign_regime(p, weekly_regimes)
        pnl = float(p.get("pnl_pct", 0) or 0)
        direction = (p.get("direction") or "LONG").upper()
        source = p.get("source_system") or "unknown"
        regime_picks[reg].append(pnl)
        regime_dir[(reg, direction)].append(pnl)
        source_regime[(source, reg)].append(pnl)
        source_counts[source] += 1

    # 3. Per-regime metrics
    regimes_order = ["BULL", "BEAR", "CHOP", "CRISIS", "UNKNOWN"]
    regime_results = {}
    print("\n" + "=" * 80)
    print(f"{'REGIME':<10} {'N':>6} {'WR%':>6} {'PF':>6} {'AvgPnL':>8} {'CumPnL':>9} "
          f"{'Sharpe':>7} {'Sortino':>8} {'MaxDD':>7} {'Calmar':>7}")
    print("-" * 80)
    for reg in regimes_order:
        pnls = regime_picks.get(reg, [])
        m = compute_metrics(pnls)
        regime_results[reg] = m
        if m["n"] > 0:
            print(f"{reg:<10} {m['n']:>6} {m['wr_pct']:>5.1f}% {m['pf']:>6.2f} "
                  f"{m['avg_pnl']:>+8.3f} {m['cum_pnl']:>+9.2f} "
                  f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} {m['max_dd']:>7.2f} {m['calmar']:>7.2f}")

    # 4. Direction breakdown per regime
    print("\n" + "=" * 80)
    print("DIRECTION BREAKDOWN PER REGIME")
    print(f"{'REGIME':<10} {'DIR':<6} {'N':>6} {'WR%':>6} {'PF':>6} {'AvgPnL':>8} {'Sharpe':>7}")
    print("-" * 80)
    dir_results = {}
    for reg in regimes_order:
        for d in ["LONG", "SHORT"]:
            pnls = regime_dir.get((reg, d), [])
            m = compute_metrics(pnls)
            dir_results[f"{reg}_{d}"] = m
            if m["n"] > 0:
                print(f"{reg:<10} {d:<6} {m['n']:>6} {m['wr_pct']:>5.1f}% {m['pf']:>6.2f} "
                      f"{m['avg_pnl']:>+8.3f} {m['sharpe']:>7.2f}")

    # 5. Top 10 sources x regime heat-map
    top_sources = sorted(source_counts, key=source_counts.get, reverse=True)[:10]
    source_regime_results = {}
    print("\n" + "=" * 80)
    print("SOURCE x REGIME HEAT-MAP (avg PnL %)")
    print(f"{'SOURCE':<25}", end="")
    for reg in regimes_order:
        print(f" {reg:>10}", end="")
    print(f" {'TOTAL':>10}")
    print("-" * (25 + 11 * (len(regimes_order) + 1)))

    for src in top_sources:
        src_data = {}
        print(f"{src[:24]:<25}", end="")
        all_pnls = []
        for reg in regimes_order:
            pnls = source_regime.get((src, reg), [])
            m = compute_metrics(pnls)
            src_data[reg] = m
            all_pnls.extend(pnls)
            if m["n"] >= 5:
                # Heat indicator
                avg = m["avg_pnl"]
                marker = "+" if avg > 0.5 else ("-" if avg < -0.5 else "~")
                print(f" {marker}{avg:>+8.2f}%", end="")
            elif m["n"] > 0:
                print(f"  ({m['n']:>3}trds)", end="")
            else:
                print(f" {'---':>10}", end="")
        total_m = compute_metrics(all_pnls)
        src_data["TOTAL"] = total_m
        marker = "+" if total_m["avg_pnl"] > 0.5 else ("-" if total_m["avg_pnl"] < -0.5 else "~")
        print(f" {marker}{total_m['avg_pnl']:>+8.2f}%")
        source_regime_results[src] = src_data

    # 6. Best/worst combos
    print("\n" + "=" * 80)
    print("BEST SOURCE x REGIME COMBOS (n >= 10):")
    combos = []
    for (src, reg), pnls in source_regime.items():
        if len(pnls) >= 10:
            m = compute_metrics(pnls)
            combos.append((src, reg, m))
    combos.sort(key=lambda x: x[2]["sharpe"], reverse=True)
    for src, reg, m in combos[:10]:
        print(f"  {src:<25} {reg:<8} n={m['n']:>4} WR={m['wr_pct']:>5.1f}% "
              f"Sharpe={m['sharpe']:>6.2f} PF={m['pf']:>5.2f} AvgPnL={m['avg_pnl']:>+.3f}%")

    print("\nWORST SOURCE x REGIME COMBOS (n >= 10):")
    for src, reg, m in combos[-10:]:
        print(f"  {src:<25} {reg:<8} n={m['n']:>4} WR={m['wr_pct']:>5.1f}% "
              f"Sharpe={m['sharpe']:>6.2f} PF={m['pf']:>5.2f} AvgPnL={m['avg_pnl']:>+.3f}%")

    # 7. Write results JSON
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "weekly_regimes": weekly_regimes,
        "regime_summary": regime_results,
        "direction_by_regime": dir_results,
        "source_regime_heatmap": source_regime_results,
        "best_combos": [{"source": s, "regime": r, **m} for s, r, m in combos[:10]],
        "worst_combos": [{"source": s, "regime": r, **m} for s, r, m in combos[-10:]],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults written to {output_path}")
    return results


if __name__ == "__main__":
    run()
