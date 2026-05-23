# -*- coding: utf-8 -*-
"""Mercury 2 — post-scan quality metrics (IC, hit-rate@K, economic WR).

Writes `data/metrics_report.json` for CI dashboards and drift tracking.
Run: python -m mercury2.metrics_report
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, VERSION, SYSTEM_NAME
from .scanner import pick_is_economic_win

CLOSED_PATH = DATA_DIR / "closed_picks.json"
SCAN_SUMMARY_PATH = DATA_DIR / "scan_summary.json"
OUT_PATH = DATA_DIR / "metrics_report.json"


def _pnl_series(df: pd.DataFrame) -> pd.Series:
    if "pnl_pct" in df.columns:
        return pd.to_numeric(df["pnl_pct"], errors="coerce")
    return pd.to_numeric(df.get("realized_pnl_pct"), errors="coerce")


def build_report() -> dict:
    if not CLOSED_PATH.exists():
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "error": "closed_picks.json missing",
        }

    closed = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    if not isinstance(closed, list) or not closed:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "closed_trades": 0,
            "note": "no closed trades",
        }

    df = pd.DataFrame(closed)
    df["confidence"] = pd.to_numeric(df.get("confidence"), errors="coerce")
    pnl = _pnl_series(df)
    df["_pnl"] = pnl
    df = df.dropna(subset=["confidence", "_pnl"])

    n = len(df)
    wins_ec = sum(pick_is_economic_win(p) for p in closed if isinstance(p, dict))
    total = len(closed)
    wr_ec = round(100.0 * wins_ec / total, 2) if total else 0.0

    pearson_ic = None
    spearman_ic = None
    if n >= 8:
        pearson_ic = round(float(df["confidence"].corr(df["_pnl"])), 4)
        spearman_ic = round(
            float(df[["confidence", "_pnl"]].corr(method="spearman").iloc[0, 1]),
            4,
        )

    hit_at_k = {}
    for k in (3, 5, 10):
        if n >= k:
            top = df.nlargest(k, "confidence")
            hit_at_k[f"hit_rate_at_top_{k}"] = round(
                float((top["_pnl"] > 0).mean() * 100),
                2,
            )

    scan_meta = {}
    if SCAN_SUMMARY_PATH.exists():
        try:
            scan_meta = json.loads(SCAN_SUMMARY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    quality_flags = []
    if pearson_ic is not None and abs(pearson_ic) < 0.08:
        quality_flags.append("low_linear_ic")
    if spearman_ic is not None and abs(spearman_ic) < 0.08:
        quality_flags.append("low_rank_ic")
    if hit_at_k.get("hit_rate_at_top_5") is not None and hit_at_k["hit_rate_at_top_5"] < 45:
        quality_flags.append("weak_top5_hit_rate")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": SYSTEM_NAME,
        "version": VERSION,
        "closed_trades": total,
        "rows_with_confidence_and_pnl": n,
        "win_rate_economic_pct": wr_ec,
        "pearson_ic_confidence_vs_pnl": pearson_ic,
        "spearman_ic_confidence_vs_pnl": spearman_ic,
        **hit_at_k,
        "scan_summary_win_rate": scan_meta.get("win_rate"),
        "scan_summary_timestamp": scan_meta.get("timestamp"),
        "quality_flags": quality_flags,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
