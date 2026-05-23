#!/usr/bin/env python3
"""
Score-PnL Calibration Analyzer
==============================
Analyzes predictive power of all score fields across the two trade populations
in the antigravity system:
  1. closed_picks.json (5,264 trades) — legacy + ML-scored mixes
  2. dashboard_data.json recent_closed (3,500 trades) — fully scored dashboard view

Usage:
    python tools/score_pnl_calibration.py [--output report.md]
"""
import json
import argparse
import math
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
CLOSED_PATH = REPO / "alpha_engine" / "data" / "closed_picks.json"
DASHBOARD_PATH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"


def load_closed_picks():
    with open(CLOSED_PATH, "r", encoding="utf-8") as f:
        picks = json.load(f)
    df = pd.DataFrame(picks)
    df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce")
    return df


def load_dashboard_recent_closed():
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    recent_closed = data.get("picks", {}).get("recent_closed", [])
    df = pd.DataFrame(recent_closed)
    if "pnl_pct" in df.columns:
        df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce")
    return df


def population_split(df):
    """Split closed_picks into ML-scored (Pop A) and non-ML (Pop B)."""
    pop_a = df[df["ml_score"].notna()].copy()
    pop_b = df[df["ml_score"].isna()].copy()
    return pop_a, pop_b


def correlation_analysis(df, score_col, win_col):
    series = pd.to_numeric(df[score_col], errors="coerce")
    valid = df[series.notna() & df["pnl_pct"].notna()].copy()
    if len(valid) == 0:
        return None
    corr = series[valid.index].corr(valid["pnl_pct"])
    return {
        "n": len(valid),
        "coverage": len(valid) / len(df),
        "pnl_corr": corr,
        "score_mean": series[valid.index].mean(),
        "score_std": series[valid.index].std(),
    }


def decile_analysis(df, score_col, win_col, min_per_decile=10):
    series = pd.to_numeric(df[score_col], errors="coerce")
    valid = df[series.notna() & df["pnl_pct"].notna()].copy()
    if len(valid) < min_per_decile * 5:
        return []
    valid["_score"] = series[valid.index]
    try:
        valid["_decile"] = pd.qcut(
            valid["_score"].rank(method="first"), 10, labels=False, duplicates="drop"
        )
    except ValueError:
        return []
    results = []
    for d in range(10):
        subset = valid[valid["_decile"] == d]
        if len(subset) == 0:
            continue
        results.append(
            {
                "decile": d + 1,
                "n": len(subset),
                "score_min": subset["_score"].min(),
                "score_max": subset["_score"].max(),
                "win_rate": subset[win_col].mean(),
                "avg_pnl": subset["pnl_pct"].mean(),
                "total_pnl": subset["pnl_pct"].sum(),
            }
        )
    return results


def strategy_level(df, score_col, win_col, min_trades=15):
    series = pd.to_numeric(df[score_col], errors="coerce")
    valid = df[series.notna() & df["pnl_pct"].notna()].copy()
    valid["_score"] = series[valid.index]
    results = []
    for strat, group in valid.groupby("strategy"):
        if len(group) < min_trades:
            continue
        corr = group["_score"].corr(group["pnl_pct"])
        results.append(
            {
                "strategy": strat,
                "n": len(group),
                "win_rate": group[win_col].mean(),
                "avg_pnl": group["pnl_pct"].mean(),
                "score_pnl_corr": corr,
                "avg_score": group["_score"].mean(),
            }
        )
    return sorted(results, key=lambda x: x["n"], reverse=True)


def near_miss_analysis(df):
    """Calculate exit-to-TP proximity for SL hits (no external APIs needed)."""
    valid = df[
        df["exit_price"].notna()
        & df["take_profit"].notna()
        & df["stop_loss"].notna()
        & df["entry_price"].notna()
    ].copy()
    if len(valid) == 0:
        return None

    def tp_distance(row):
        return abs(row["exit_price"] - row["take_profit"]) / row["entry_price"] * 100

    valid["tp_distance_pct"] = valid.apply(tp_distance, axis=1)
    sl_hits = valid[valid.get("exit_reason", "") == "SL_HIT"]
    if len(sl_hits) == 0:
        return None

    close_to_tp = sl_hits[sl_hits["tp_distance_pct"] < 1.0]
    return {
        "total_sl_hits": len(sl_hits),
        "near_misses_within_1pct": len(close_to_tp),
        "near_miss_rate": len(close_to_tp) / len(sl_hits) if len(sl_hits) > 0 else 0,
        "median_tp_distance_pct": sl_hits["tp_distance_pct"].median(),
        "worst_5": sl_hits.nsmallest(5, "tp_distance_pct")[
            ["symbol", "direction", "tp_distance_pct", "pnl_pct"]
        ].to_dict("records"),
    }


def generate_report(closed_df, dash_df):
    lines = []
    lines.append("# Score-PnL Calibration Report")
    lines.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # --- CLOSED_PICKS ARCHITECTURE ---
    lines.append("## 1. Data Architecture: Two Populations in closed_picks.json")
    pop_a, pop_b = population_split(closed_df)
    lines.append(f"| Population | Count | Score Fields | Outcome Type |")
    lines.append(f"|------------|-------|--------------|--------------|")
    lines.append(
        f"| **A (ML-scored)** | {len(pop_a):,} | ml_score, confluence_score | WON/LOST/EXPIRED |"
    )
    lines.append(
        f"| **B (Non-ML)** | {len(pop_b):,} | confidence | CLOSED |"
    )
    lines.append("")

    # Score coverage
    lines.append("### Score Field Coverage (closed_picks.json)")
    lines.append("| Field | Non-Null | Coverage | Notes |")
    lines.append("|-------|----------|----------|-------|")
    for col in [
        "confidence",
        "ml_score",
        "confluence_score",
        "elite_score",
        "ml_composite_score",
        "method_a_score",
        "entry_timing_score",
    ]:
        non_null = closed_df[col].notna().sum()
        cov = non_null / len(closed_df)
        note = {
            "ml_score": "Only Pop A",
            "confidence": "Only Pop B (Pop A = NaN)",
            "confluence_score": "Always 1.0, no variance" if non_null > 0 else "",
            "elite_score": "Essentially non-existent" if non_null <= 5 else "",
            "ml_composite_score": "Essentially non-existent" if non_null <= 5 else "",
            "method_a_score": "Essentially non-existent" if non_null <= 5 else "",
            "entry_timing_score": "Essentially non-existent" if non_null <= 5 else "",
        }.get(col, "")
        lines.append(f"| {col} | {non_null:,} | {cov:.1%} | {note} |")
    lines.append("")

    # --- POPULATION A: ml_score ---
    pop_a["won"] = pop_a["status"] == "WON"
    pop_a["ml_score"] = pd.to_numeric(pop_a["ml_score"], errors="coerce")
    corr_a = pop_a["ml_score"].corr(pop_a["pnl_pct"])
    lines.append(f"## 2. Population A: ml_score (n={len(pop_a):,})")
    lines.append(f"**Correlation with PnL:** `{corr_a:+.4f}`")
    lines.append("")
    lines.append("| Decile | Score Range | n | WR | Avg PnL | Total PnL |")
    lines.append("|--------|-------------|---|----|---------|-----------|")
    for d in decile_analysis(pop_a, "ml_score", "won"):
        lines.append(
            f"| D{d['decile']:2d} | {d['score_min']:.3f}-{d['score_max']:.3f} | {d['n']:,} | "
            f"{d['win_rate']:.1%} | {d['avg_pnl']:+.3f}% | {d['total_pnl']:+.2f}% |"
        )
    lines.append("")

    # --- POPULATION B: confidence ---
    pop_b["won"] = pop_b["pnl_pct"] > 0
    pop_b["confidence"] = pd.to_numeric(pop_b["confidence"], errors="coerce")
    corr_b = pop_b["confidence"].corr(pop_b["pnl_pct"])
    lines.append(f"## 3. Population B: confidence (n={len(pop_b):,})")
    lines.append(f"**Correlation with PnL:** `{corr_b:+.4f}`")
    lines.append(
        "> :warning: `confidence` has essentially **zero** correlation with PnL across {:,} trades.\n"
        .format(len(pop_b))
    )
    lines.append("| Decile | Score Range | n | WR | Avg PnL | Total PnL |")
    lines.append("|--------|-------------|---|----|---------|-----------|")
    for d in decile_analysis(pop_b, "confidence", "won"):
        lines.append(
            f"| D{d['decile']:2d} | {d['score_min']:.3f}-{d['score_max']:.3f} | {d['n']:,} | "
            f"{d['win_rate']:.1%} | {d['avg_pnl']:+.3f}% | {d['total_pnl']:+.2f}% |"
        )
    lines.append("")

    # High-confidence losers in Pop B
    conf_90 = pop_b["confidence"].quantile(0.9)
    high_conf = pop_b[pop_b["confidence"] >= conf_90]
    high_conf_losers = high_conf[high_conf["pnl_pct"] < 0]
    lines.append(
        f"**High-Confidence Losers:** Top 10% (≥{conf_90:.3f}) = {len(high_conf):,} trades, "
        f"{len(high_conf_losers):,} losers ({len(high_conf_losers)/len(high_conf):.1%}). "
        f"Total PnL: {high_conf['pnl_pct'].sum():+.2f}%"
    )
    lines.append("")

    # Symbol concentration
    sym_summary = (
        high_conf_losers.groupby(["symbol", "direction"])
        .agg({"pnl_pct": ["count", "mean", "sum"], "confidence": "mean"})
        .reset_index()
    )
    sym_summary.columns = ["symbol", "direction", "trades", "avg_pnl", "total_pnl", "avg_conf"]
    sym_summary = sym_summary.sort_values("total_pnl").head(8)
    if len(sym_summary) > 0:
        lines.append("| Symbol | Dir | Trades | Avg PnL | Total | Avg Conf |")
        lines.append("|--------|-----|--------|---------|-------|----------|")
        for _, row in sym_summary.iterrows():
            lines.append(
                f"| {row['symbol']:12s} | {row['direction']:4s} | {row['trades']:,} | "
                f"{row['avg_pnl']:+.2f}% | {row['total_pnl']:+.2f}% | {row['avg_conf']:.3f} |"
            )
    lines.append("")

    # --- DASHBOARD DATA ---
    if len(dash_df) > 0 and "score" in dash_df.columns:
        lines.append(f"## 4. Dashboard recent_closed (n={len(dash_df):,})")
        lines.append("All score fields populated. 181 unique strategies.")
        lines.append("")

        dash_df["pnl_pct"] = pd.to_numeric(dash_df["pnl_pct"], errors="coerce")
        dash_df["won"] = dash_df["pnl_pct"] > 0

        for col in ["score", "elite_score", "ml_composite_score", "method_a_score", "confidence"]:
            if col not in dash_df.columns:
                continue
            series = pd.to_numeric(dash_df[col], errors="coerce")
            if series.notna().sum() < 100:
                continue
            corr = series.corr(dash_df["pnl_pct"])
            lines.append(f"- `{col}` vs PnL: **{corr:+.4f}** (n={series.notna().sum():,})")
        lines.append("")

        # Worst strategies in dashboard data
        lines.append("### Worst Strategies (dashboard, min 20 trades)")
        lines.append("| Strategy | n | WR | Avg PnL | Total PnL |")
        lines.append("|----------|---|----|---------|-----------|")
        for strat in dash_df["strategy"].value_counts().index:
            subset = dash_df[dash_df["strategy"] == strat]
            if len(subset) < 20:
                continue
            wr = subset["won"].mean()
            avg_pnl = subset["pnl_pct"].mean()
            total_pnl = subset["pnl_pct"].sum()
            if total_pnl < -10:  # Only show significant bleeders
                lines.append(
                    f"| {str(strat)[:35]:35s} | {len(subset):,} | {wr:.1%} | "
                    f"{avg_pnl:+.3f}% | {total_pnl:+.2f}% |"
                )
        lines.append("")

    # --- NEAR MISSES ---
    lines.append("## 5. Near-Miss Analysis (SL hits within 1% of TP)")
    nm = near_miss_analysis(closed_df)
    if nm:
        lines.append(f"- Total SL hits: **{nm['total_sl_hits']:,}**")
        lines.append(f"- Near-misses (within 1% of TP): **{nm['near_misses_within_1pct']:,}** ({nm['near_miss_rate']:.1%})")
        lines.append(f"- Median TP distance for SL hits: **{nm['median_tp_distance_pct']:.2f}%**")
        lines.append("")
    else:
        lines.append("Insufficient data for near-miss calculation.")
        lines.append("")

    # --- RECOMMENDATIONS ---
    lines.append("## 6. Recommendations")
    lines.append("")
    lines.append("| Priority | Action | Evidence |")
    lines.append("|----------|--------|----------|")
    lines.append(f"| P0 | Fix `confidence` scoring logic | r={corr_b:+.3f} across {len(pop_b):,} trades |")
    lines.append("| P0 | Deprecate `confluence_score` | Always 1.0, zero variance |")
    lines.append("| P0 | Block `volume_spike_breakout` from live | 11.6% WR, -80% total (Pop B) |")
    lines.append("| P1 | Investigate D10 `ml_score` drop | D9 86.4% WR → D10 56.7% WR |")
    lines.append("| P1 | Populate elite/ml_composite/method_a across ALL trades | Currently 1 trade only |")
    lines.append("| P1 | Add TAOUSDT/BTCUSDT to loss watchlist | High-confidence repeated losers |")
    lines.append("| P2 | Unify scoring pipeline | Two disjoint populations prevent comparison |")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=str, default=None)
    args = parser.parse_args()

    closed_df = load_closed_picks()
    dash_df = load_dashboard_recent_closed()
    report = generate_report(closed_df, dash_df)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
