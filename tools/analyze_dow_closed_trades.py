#!/usr/bin/env python3
"""
Day-of-week (UTC) analysis for closed picks in audit dashboard JSON.

Tests:
  - Pearson chi-square independence: weekday × win/loss (pnl_pct > 0 vs not)
  - Kruskal-Wallis H: pnl_pct distributions across weekdays (nonparametric one-way)

Outputs:
  - tools/data/dow_closed_trades_analysis.json
  - stdout summary

Weekday: Python datetime.weekday() — Monday=0, Sunday=6. All times UTC from closed_at.

Requires: numpy, scipy (not in root requirements.txt — install scipy in the venv used for analysis).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "dow_closed_trades_analysis.json"

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _parse_closed_at(s: Any) -> Optional[datetime]:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        for suf in (" EST", " EDT", " UTC", " GMT"):
            t = t.replace(suf, "")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _float_pnl(x: Any) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _collect(
    rows: List[dict], asset_filter: Optional[str] = None
) -> Tuple[List[int], List[float], List[str]]:
    """Return parallel lists: weekday 0-6, pnl_pct, asset_class."""
    wds: List[int] = []
    pnls: List[float] = []
    acs: List[str] = []
    for r in rows:
        if asset_filter:
            ac = (r.get("asset_class") or "").upper()
            if ac != asset_filter.upper():
                continue
        dt = _parse_closed_at(r.get("closed_at"))
        pnl = _float_pnl(r.get("pnl_pct"))
        if dt is None or pnl is None:
            continue
        wds.append(dt.weekday())
        pnls.append(pnl)
        acs.append(str(r.get("asset_class") or "UNKNOWN"))
    return wds, pnls, acs


def _stats_for_slice(
    label: str, wds: List[int], pnls: List[float]
) -> Dict[str, Any]:
    from scipy.stats import chi2_contingency, kruskal

    n = len(pnls)
    if n < 21:
        return {"slice": label, "n": n, "error": "insufficient_n"}

    wins = np.array([1 if p > 0 else 0 for p in pnls])
    # 7 × 2 contingency: rows = weekday, cols = [loss, win]
    table = np.zeros((7, 2), dtype=float)
    for wd, w in zip(wds, wins):
        table[wd, int(w)] += 1

    chi2, p_chi2, dof, expected = chi2_contingency(table)
    # Cramer's V (2 columns)
    cramers_v = float(np.sqrt(chi2 / (n * min(7 - 1, 2 - 1)))) if n > 0 else 0.0

    # Kruskal-Wallis: one list per weekday with n>=1
    groups = [[] for _ in range(7)]
    for wd, p in zip(wds, pnls):
        groups[wd].append(p)
    nonempty = [np.array(g, dtype=float) for g in groups if len(g) > 0]
    if len(nonempty) >= 2:
        h_stat, p_kw = kruskal(*nonempty)
    else:
        h_stat, p_kw = float("nan"), float("nan")

    by_dow = []
    for d in range(7):
        idx = [i for i, w in enumerate(wds) if w == d]
        xs = [pnls[i] for i in idx]
        nw = sum(1 for x in xs if x > 0)
        nn = len(xs)
        by_dow.append(
            {
                "weekday": d,
                "weekday_name": WEEKDAY_NAMES[d],
                "n": nn,
                "win_rate_pct": round(100.0 * nw / nn, 2) if nn else 0.0,
                "mean_pnl_pct": round(float(np.mean(xs)), 4) if nn else 0.0,
                "median_pnl_pct": round(float(np.median(xs)), 4) if nn else 0.0,
            }
        )

    # Best / worst mean pnl (min n >= 30 for stability note)
    eligible = [b for b in by_dow if b["n"] >= 10]
    if eligible:
        best = max(eligible, key=lambda b: b["mean_pnl_pct"])
        worst = min(eligible, key=lambda b: b["mean_pnl_pct"])
    else:
        best = worst = None

    return {
        "slice": label,
        "n": n,
        "timezone_note": "UTC; weekday from closed_at",
        "chi2_independence_win_vs_day": {
            "chi2": round(float(chi2), 4),
            "df": int(dof),
            "p_value": float(p_chi2),
            "cramers_v": round(cramers_v, 4),
            "interpretation": (
                "H0: win/loss independent of weekday. "
                "Low p suggests day-specific win rates differ beyond chance."
            ),
        },
        "kruskal_wallis_pnl_by_day": {
            "H": round(float(h_stat), 4) if np.isfinite(h_stat) else None,
            "p_value": float(p_kw) if np.isfinite(p_kw) else None,
            "interpretation": (
                "H0: pnl_pct distributions identical across weekdays. "
                "Sensitive to heavy tails; use with chi-square and descriptives."
            ),
        },
        "by_weekday": by_dow,
        "best_mean_pnl_weekday": best,
        "worst_mean_pnl_weekday": worst,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("missing", path, file=sys.stderr)
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    closed = data.get("picks", {}).get("recent_closed") or []

    w_all, p_all, _ = _collect(closed, None)
    w_cr, p_cr, _ = _collect(closed, "CRYPTO")

    payload = {
        "dashboard_path": str(path),
        "n_recent_closed_total": len(closed),
        "slices": {
            "all": _stats_for_slice("all_closed", w_all, p_all),
            "crypto": _stats_for_slice("crypto_only", w_cr, p_cr),
        },
        "methods": {
            "chi2": "scipy.stats.chi2_contingency on 7×2 (weekday × win/loss)",
            "kruskal": "scipy.stats.kruskal on seven pnl_pct samples",
            "references": [
                "Lakonishok & Maberly (1990) — day-of-week equity patterns (context only)",
                "Reporting follows common practice: test + effect size (Cramer's V) + descriptives",
            ],
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "chi2_p_all": payload["slices"]["all"].get("chi2_independence_win_vs_day", {}).get("p_value")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
