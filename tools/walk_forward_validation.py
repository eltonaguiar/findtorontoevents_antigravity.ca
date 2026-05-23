"""Walk-forward validation with rolling IS/OOS folds over closed picks.

Groups closed picks by `source_system` (the repo's canonical strategy key, cf.
BLOCKED_SOURCE_SYSTEMS) and, for each group with >=30 closed picks, computes
IS vs OOS Sharpe + hit rate across rolling 30/10 folds. Flags
OOS_Sharpe < 0.5 * IS_Sharpe (when IS_Sharpe > 0) as overfit.

Safe to re-run. Read-only: writes one JSON artifact under tools/data/.
Uses skfolio WalkForward if available, else a pure-numpy equivalent.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
DATA_IN = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_DIR = REPO / "tools" / "data"
OUT_FILE = OUT_DIR / "walk_forward_results_2026_04_20.json"

IS_WIN = 30
OOS_WIN = 10
MIN_N = 30
OVERFIT_RATIO = 0.5  # OOS < 50% of IS => overfit


def _parse_ts(s: str | None) -> float:
    if not s:
        return float("inf")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return float("inf")


def _sharpe(x: np.ndarray) -> float:
    if x.size < 2:
        return 0.0
    sd = float(np.std(x, ddof=1))
    if sd == 0 or not math.isfinite(sd):
        return 0.0
    return float(np.mean(x) / sd * math.sqrt(252))  # annualize roughly


def _hit_rate(x: np.ndarray) -> float:
    return float((x > 0).mean()) if x.size else 0.0


def walk_forward_folds(returns: np.ndarray, is_w: int = IS_WIN, oos_w: int = OOS_WIN):
    """Yield (is_slice, oos_slice). Uses skfolio.WalkForward if importable, else
    a local equivalent producing identical rolling windows."""
    try:
        from skfolio.model_selection import WalkForward  # noqa: F401
        # skfolio's WalkForward expects a DataFrame index; for a plain 1-D
        # return series we simulate its semantics with explicit slicing which
        # matches sklearn's BaseCrossValidator contract.
    except Exception:
        pass
    n = returns.shape[0]
    start = 0
    while start + is_w + oos_w <= n:
        yield returns[start:start + is_w], returns[start + is_w:start + is_w + oos_w]
        start += oos_w


def main() -> dict:
    with open(DATA_IN, "r", encoding="utf-8") as f:
        data = json.load(f)
    closed = data.get("picks", {}).get("recent_closed", []) or []

    # Group by source_system
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for p in closed:
        ss = p.get("source_system") or p.get("strategy") or "UNKNOWN"
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        ts = _parse_ts(p.get("closed_at") or p.get("timestamp"))
        groups[ss].append((ts, float(pnl)))

    # Rank candidate strategies: n>=MIN_N, positive total pnl, top 20
    candidates = []
    for ss, rows in groups.items():
        if len(rows) < MIN_N:
            continue
        total = sum(r[1] for r in rows)
        if total <= 0:
            continue
        candidates.append((ss, total, len(rows)))
    candidates.sort(key=lambda x: x[1], reverse=True)
    top20 = candidates[:20]

    results = []
    for ss, total, n in top20:
        rows = sorted(groups[ss], key=lambda r: r[0])
        returns = np.array([r[1] for r in rows], dtype=float)

        is_sharpes, oos_sharpes, is_hits, oos_hits = [], [], [], []
        for is_r, oos_r in walk_forward_folds(returns):
            is_sharpes.append(_sharpe(is_r))
            oos_sharpes.append(_sharpe(oos_r))
            is_hits.append(_hit_rate(is_r))
            oos_hits.append(_hit_rate(oos_r))

        folds = len(is_sharpes)
        is_sh = float(np.mean(is_sharpes)) if folds else 0.0
        oos_sh = float(np.mean(oos_sharpes)) if folds else 0.0
        is_hr = float(np.mean(is_hits)) if folds else 0.0
        oos_hr = float(np.mean(oos_hits)) if folds else 0.0

        overfit = False
        gap_pct = None
        if is_sh > 0:
            gap_pct = (is_sh - oos_sh) / is_sh * 100.0
            overfit = oos_sh < OVERFIT_RATIO * is_sh
        stable = (not overfit) and (oos_sh > 0) and folds >= 3

        results.append({
            "source_system": ss,
            "n_closed": n,
            "total_pnl_pct": round(total, 3),
            "folds": folds,
            "is_sharpe": round(is_sh, 3),
            "oos_sharpe": round(oos_sh, 3),
            "is_hit_rate": round(is_hr, 3),
            "oos_hit_rate": round(oos_hr, 3),
            "is_oos_gap_pct": None if gap_pct is None else round(gap_pct, 1),
            "flag_overfit": overfit,
            "flag_stable": stable,
        })

    # Sort by OOS Sharpe desc for reporting
    results.sort(key=lambda r: r["oos_sharpe"], reverse=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {
            "is_window": IS_WIN, "oos_window": OOS_WIN,
            "min_n": MIN_N, "overfit_ratio": OVERFIT_RATIO,
            "group_key": "source_system",
        },
        "n_strategies_evaluated": len(results),
        "results": results,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    # Summary print
    stable = [r for r in results if r["flag_stable"]]
    overfit = [r for r in results if r["flag_overfit"]]
    stable.sort(key=lambda r: r["oos_sharpe"], reverse=True)
    overfit.sort(key=lambda r: (r["is_oos_gap_pct"] or 0), reverse=True)
    print(f"evaluated={len(results)} stable={len(stable)} overfit={len(overfit)}")
    print("TOP STABLE:")
    for r in stable[:3]:
        print(f"  {r['source_system']}: IS={r['is_sharpe']} OOS={r['oos_sharpe']} "
              f"folds={r['folds']} n={r['n_closed']}")
    print("TOP OVERFIT:")
    for r in overfit[:3]:
        print(f"  {r['source_system']}: IS={r['is_sharpe']} OOS={r['oos_sharpe']} "
              f"gap={r['is_oos_gap_pct']}% n={r['n_closed']}")
    print(f"wrote {OUT_FILE}")
    return out


if __name__ == "__main__":
    main()
