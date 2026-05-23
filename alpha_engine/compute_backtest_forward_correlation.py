#!/usr/bin/env python3
"""
Backtest-to-Forward Performance Correlation Analysis
=====================================================
Computes the Pearson correlation between backtest (in-sample) win rates
and forward (out-of-sample) win rates across all strategies that have both.

Data sources:
  1. battleground/data/walk_forward_results.json -- train vs test WR
  2. alpha_engine/data/strategy_isolation_config.json -- backtest_wr vs fwd_wr
  3. alpha_engine/data/strategy_audit_report.json -- actual forward WR (vs claimed)

Output: alpha_engine/data/backtest_forward_correlation.json
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
ALPHA_DATA = Path(__file__).resolve().parent / "data"
BG_DATA = ROOT / "battleground" / "data"


def pearson(x_vals, y_vals):
    """Compute Pearson correlation coefficient between two lists."""
    n = len(x_vals)
    if n < 3:
        return None  # Need at least 3 points for meaningful correlation
    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
    var_x = sum((x - mean_x) ** 2 for x in x_vals)
    var_y = sum((y - mean_y) ** 2 for y in y_vals)
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return 0.0
    return cov / denom


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def main():
    pairs = []  # list of {"name", "backtest_wr", "forward_wr", "source"}

    # -- Source 1: Walk-forward results (train = backtest, test = forward) --
    wf = load_json(BG_DATA / "walk_forward_results.json")
    if wf and "strategies" in wf:
        for name, data in wf["strategies"].items():
            train = data.get("train", {})
            test = data.get("test", {})
            train_wr = train.get("win_rate_pct")
            test_wr = test.get("win_rate_pct")
            if train_wr is not None and test_wr is not None:
                pairs.append({
                    "name": name,
                    "backtest_wr": round(train_wr, 1),
                    "forward_wr": round(test_wr, 1),
                    "drop_pp": round(train_wr - test_wr, 1),
                    "source": "walk_forward_split",
                    "train_trades": train.get("num_trades", 0),
                    "test_trades": test.get("num_trades", 0),
                    "verdict": data.get("verdict", "")
                })

    # -- Source 2: Strategy isolation config (backtest_wr vs fwd_wr) --
    iso = load_json(ALPHA_DATA / "strategy_isolation_config.json")
    if iso and "strategy_isolations" in iso:
        # Avoid duplicates with walk-forward data
        wf_names = {p["name"] for p in pairs}
        for s in iso["strategy_isolations"]:
            name = s.get("strategy", "")
            bt_wr = s.get("backtest_wr")
            fw_wr = s.get("fwd_wr")
            if bt_wr is not None and fw_wr is not None and name not in wf_names:
                pairs.append({
                    "name": name,
                    "backtest_wr": round(bt_wr, 1),
                    "forward_wr": round(fw_wr, 1),
                    "drop_pp": round(bt_wr - fw_wr, 1),
                    "source": "isolation_tracking",
                    "train_trades": 0,
                    "test_trades": s.get("fwd_trades", 0),
                    "verdict": s.get("walk_forward", "")
                })

    # -- Source 3: Audit report -- documented WR vs actual forward WR --
    # The master_dashboard.py has documented_wr for 8 strategies.
    # The audit report has actual forward WR. We can match them.
    documented_wr_claims = {
        "forex_usd_momentum": 70.0,
        "connors_rsi2": 73.0,
        "vix_spike_reversal": 78.0,
        "funding_rate_carry": 71.0,
        "next_gen": 65.0,
        "triple_rsi": 90.0,
        "orb": 74.56,
        "altcoin_season": 68.0,
    }
    # Map audit report strategy names to our claims (fuzzy match)
    audit = load_json(ALPHA_DATA / "strategy_audit_report.json")
    if audit and "all_strategies_ranked" in audit:
        existing_names = {p["name"] for p in pairs}
        for s in audit["all_strategies_ranked"]:
            name = s.get("strategy", "")
            actual_wr = s.get("win_rate_pct")
            total_trades = s.get("total_trades", 0)
            if actual_wr is None or total_trades < 5:
                continue
            # Check if we have a documented WR claim for this strategy
            for claim_name, claim_wr in documented_wr_claims.items():
                if claim_name in name or name in claim_name:
                    if name not in existing_names:
                        pairs.append({
                            "name": name,
                            "backtest_wr": claim_wr,
                            "forward_wr": round(actual_wr, 1),
                            "drop_pp": round(claim_wr - actual_wr, 1),
                            "source": "documented_vs_actual",
                            "train_trades": 0,
                            "test_trades": total_trades,
                            "verdict": ""
                        })
                        existing_names.add(name)
                    break

    if not pairs:
        print("ERROR: No strategy pairs found with both backtest and forward WR")
        sys.exit(1)

    # -- Compute statistics --
    backtest_wrs = [p["backtest_wr"] for p in pairs]
    forward_wrs = [p["forward_wr"] for p in pairs]

    correlation = pearson(backtest_wrs, forward_wrs)
    r_squared = correlation ** 2 if correlation is not None else None

    avg_drop = sum(p["drop_pp"] for p in pairs) / len(pairs)
    degraded_count = sum(1 for p in pairs if p["drop_pp"] > 10)
    improved_count = sum(1 for p in pairs if p["drop_pp"] < -5)

    # Sort by degradation (worst first)
    pairs.sort(key=lambda p: -p["drop_pp"])

    # Build warning message
    if r_squared is not None:
        pct_explained = round(r_squared * 100, 1)
        if correlation is not None and correlation < 0:
            warning = (
                f"INVERSE correlation detected (r={correlation:.2f}): "
                f"higher backtest WR actually predicts WORSE forward performance. "
                f"Strategies with modest backtest WR ({avg_drop:+.0f}pp avg drop across {len(pairs)} strategies) "
                f"tend to hold up better out-of-sample."
            )
        elif r_squared < 0.25:
            warning = f"Backtest results predict only {pct_explained}% of forward performance"
        else:
            warning = f"Backtest WR explains {pct_explained}% of forward variance (r={correlation:.2f})"
    else:
        pct_explained = None
        warning = "Insufficient data for correlation (need 3+ strategy pairs)"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "correlation": round(correlation, 4) if correlation is not None else None,
        "r_squared": round(r_squared, 4) if r_squared is not None else None,
        "r_squared_pct": pct_explained,
        "strategies_compared": len(pairs),
        "avg_wr_drop_pp": round(avg_drop, 1),
        "median_wr_drop_pp": round(sorted(p["drop_pp"] for p in pairs)[len(pairs) // 2], 1),
        "degraded_count": degraded_count,
        "degraded_pct": round(degraded_count / len(pairs) * 100, 1),
        "improved_count": improved_count,
        "warning": warning,
        "kimi_claw_comparison": {
            "kimi_r": 0.34,
            "kimi_r_squared": 0.12,
            "our_r": round(correlation, 4) if correlation is not None else None,
            "our_r_squared": round(r_squared, 4) if r_squared is not None else None,
            "note": "KIMI Claw found r=0.34 (r^2=0.12). Values <0.5 mean backtest is a poor predictor."
        },
        "strategies": pairs
    }

    out_path = ALPHA_DATA / "backtest_forward_correlation.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"\n{'='*70}")
    print(f"  BACKTEST-TO-FORWARD CORRELATION ANALYSIS")
    print(f"{'='*70}")
    print(f"  Strategies compared: {len(pairs)}")
    print(f"  Pearson r:           {correlation:.4f}" if correlation else "  Pearson r:           N/A")
    print(f"  R-squared:           {r_squared:.4f} ({pct_explained}% explained)" if r_squared else "  R-squared:           N/A")
    print(f"  Avg WR drop:         {avg_drop:+.1f} pp")
    print(f"  Degraded >10pp:      {degraded_count}/{len(pairs)} ({degraded_count/len(pairs)*100:.0f}%)")
    print(f"  KIMI Claw r=0.34:    {'CONFIRMED' if correlation and abs(correlation - 0.34) < 0.15 else 'DIFFERS'}")
    print(f"{'='*70}")
    print(f"\n  WARNING: {warning}")
    print(f"\n  Strategy Details (sorted by degradation):")
    for p in pairs:
        marker = "!!!" if p["drop_pp"] > 30 else "!!" if p["drop_pp"] > 10 else "  "
        print(f"  {marker} {p['name']:50s}  BT={p['backtest_wr']:5.1f}%  FWD={p['forward_wr']:5.1f}%  drop={p['drop_pp']:+6.1f}pp  [{p['source']}]")

    print(f"\n  Saved -> {out_path}\n")
    return result


if __name__ == "__main__":
    main()
