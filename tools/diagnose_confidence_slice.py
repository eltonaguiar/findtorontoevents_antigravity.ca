#!/usr/bin/env python3
"""Diagnose the confidence feature's -0.087 correlation with WIN outcomes.

Cerebras consultation ruled out an explicit sign-flip (grep for `confidence = 1 -`
patterns returned nothing). So the negative correlation is structural, not a bug.

This script slices the closed-picks ledger by source_system, asset_class,
signal_type, and confidence bucket to find where the negative correlation
concentrates. If `confidence` is actively misleading in a specific regime
or source, we can either gate against that slice or rebuild the feature
on triple-barrier labels.

Writes reports/CONFIDENCE_SLICE_DIAGNOSIS_2026_04_22.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CLOSED_PICKS = REPO / "alpha_engine" / "data" / "closed_picks.json"
REPORT = REPO / "reports" / "CONFIDENCE_SLICE_DIAGNOSIS_2026_04_22.md"


def _wr(s: pd.Series) -> float:
    return float((s > 0).mean()) if len(s) else 0.0


def _pf(s: pd.Series) -> Any:
    gp = s[s > 0].sum()
    gl = -s[s < 0].sum()
    return float(gp / gl) if gl > 0 else None


def conditional_corr(df: pd.DataFrame, by: str, min_n: int = 80) -> pd.DataFrame:
    df = df.copy()
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df = df.dropna(subset=["confidence", "pnl_pct"])
    df["win"] = (df["pnl_pct"] > 0).astype(int)
    rows = []
    for key, sub in df.groupby(by):
        n = len(sub)
        if n < min_n:
            continue
        r_conf_win = sub["confidence"].corr(sub["win"])
        r_conf_pnl = sub["confidence"].corr(sub["pnl_pct"])
        rows.append({
            by: key,
            "n": n,
            "wr": round(_wr(sub["pnl_pct"]), 4),
            "pf": _pf(sub["pnl_pct"]),
            "r(conf,win)": round(float(r_conf_win), 4) if not np.isnan(r_conf_win) else None,
            "r(conf,pnl)": round(float(r_conf_pnl), 4) if not np.isnan(r_conf_pnl) else None,
            "mean_conf": round(float(sub["confidence"].mean()), 4),
        })
    if not rows:
        return pd.DataFrame(columns=[by, "n", "wr", "pf", "r(conf,win)", "r(conf,pnl)", "mean_conf"])
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def confidence_bucket_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df = df.dropna(subset=["confidence", "pnl_pct"])
    bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    labels = ["<0.50", "0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80-0.90", "0.90-1.00"]
    df["bucket"] = pd.cut(df["confidence"], bins=bins, labels=labels, include_lowest=True)
    rows = []
    for b, sub in df.groupby("bucket", observed=True):
        n = len(sub)
        if n < 10:
            rows.append({"bucket": b, "n": n, "wr": None, "pf": None, "mean_pnl_pct": None})
            continue
        rows.append({
            "bucket": str(b),
            "n": n,
            "wr": round(_wr(sub["pnl_pct"]), 4),
            "pf": _pf(sub["pnl_pct"]),
            "mean_pnl_pct": round(float(sub["pnl_pct"].mean()), 4),
        })
    return pd.DataFrame(rows)


def write_report(sections: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# `confidence` Feature — Sliced Diagnosis\n"]
    lines.append("**Hypothesis:** the -0.087 global correlation between `confidence` and WIN is not a")
    lines.append("code bug (no `confidence = 1 - X` patterns exist in `alpha_engine/`). It's structural.")
    lines.append("Question: does the sign FLIP in specific slices (source_system, asset_class, direction)?\n")
    for title, body in sections.items():
        lines.append(f"\n## {title}\n")
        if isinstance(body, pd.DataFrame):
            try:
                lines.append(body.to_markdown(index=False))
            except ImportError:
                lines.append("```\n" + body.to_string(index=False) + "\n```")
        else:
            lines.append(str(body))
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    raw = json.loads(CLOSED_PICKS.read_text())
    df = pd.DataFrame(raw)
    df = df[df["status"] == "CLOSED"].copy()
    df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce")
    df = df.dropna(subset=["pnl_pct"])

    print(f"Loaded {len(df):,} closed picks")

    global_r = pd.to_numeric(df["confidence"], errors="coerce").corr((df["pnl_pct"] > 0).astype(int))
    print(f"Global r(confidence, win) = {global_r:+.4f}")

    print("\nBy source_system (min_n=80)...")
    by_source = conditional_corr(df, "source_system", min_n=80)
    print(by_source.to_string(index=False))

    print("\nBy asset_class (min_n=80)...")
    by_ac = conditional_corr(df, "asset_class", min_n=80) if "asset_class" in df.columns else conditional_corr(df, "category", min_n=80)

    print("\nBy signal_type (direction bias)...")
    by_dir = conditional_corr(df, "signal_type", min_n=80)
    print(by_dir.to_string(index=False))

    print("\nBy strategy (top-12, min_n=40)...")
    by_strat = conditional_corr(df, "strategy", min_n=40).head(12)
    print(by_strat.to_string(index=False))

    print("\nConfidence bucket vs outcome (tail risk check)...")
    bucket = confidence_bucket_table(df)
    print(bucket.to_string(index=False))

    write_report({
        f"Global correlation (baseline)": f"r(confidence, win) = **{global_r:+.4f}** across {len(df):,} closed picks.",
        "By source_system (n >= 80)": by_source,
        "By asset_class (n >= 80)": by_ac,
        "By signal_type direction (n >= 80)": by_dir,
        "By strategy (top 12 by n, min_n=40)": by_strat,
        "Confidence bucket vs outcome": bucket,
    })
    print(f"\nReport -> {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
