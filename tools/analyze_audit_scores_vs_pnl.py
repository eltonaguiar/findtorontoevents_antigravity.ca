#!/usr/bin/env python3
"""Quant-style audit: correlate dashboard scores with realized pnl_pct (closed picks).

Reads ``audit_dashboard/data/dashboard_data.json``. Recomputes ``smart_score`` via
``audit_trail.quality_gates.calculate_smart_score`` when missing (JSON often omits it
on ``recent_closed``).

Outputs:
  - ``tools/data/score_pnl_analysis.json`` — machine-readable metrics
  - stdout summary for piping

No scipy (import can stall on some Windows hosts): Pearson + tie-aware Spearman via numpy.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import logging
import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

for _lg in ("audit_trail.quality_gates", "audit_trail.forward_degradation_tracker"):
    logging.getLogger(_lg).setLevel(logging.CRITICAL)

from audit_trail.quality_gates import calculate_smart_score, classify_pick_quality  # noqa: E402

DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "score_pnl_analysis.json"


def _float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 15:
        return float("nan")
    a, b = x[m], y[m]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def avg_ranks(arr: np.ndarray) -> np.ndarray:
    """1-based average ranks for ties."""
    n = len(arr)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        v = arr[order[i]]
        while j < n and arr[order[j]] == v:
            j += 1
        avg = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 15:
        return float("nan")
    a, b = x[m], y[m]
    return pearson(avg_ranks(a), avg_ranks(b))


def quintile_lift(scores: np.ndarray, pnls: np.ndarray) -> Dict[str, Any]:
    m = np.isfinite(scores) & np.isfinite(pnls)
    s, p = scores[m], pnls[m]
    n = len(s)
    if n < 50:
        return {}
    # Equal-frequency quintiles on score (rank sort → chunk)
    order = np.argsort(s, kind="mergesort")
    out = []
    for q in range(5):
        lo_i = (q * n) // 5
        hi_i = ((q + 1) * n) // 5 if q < 4 else n
        idx = order[lo_i:hi_i]
        sub = p[idx]
        out.append(
            {
                "quintile": q + 1,
                "n": int(len(sub)),
                "mean_pnl_pct": round(float(np.mean(sub)), 4),
                "win_rate_pct": round(float(100.0 * np.mean(sub > 0)), 2),
                "bucket_var_min": round(float(np.min(s[idx])), 4),
                "bucket_var_max": round(float(np.max(s[idx])), 4),
            }
        )
    top = out[-1]["mean_pnl_pct"]
    bot = out[0]["mean_pnl_pct"]
    return {"by_quintile": out, "top_minus_bottom_mean_pnl_pp": round(top - bot, 4)}


def verified_ref_set(va: Dict[str, Any]) -> set:
    refs = va.get("active_pick_refs") or []
    keys = set()
    for r in refs:
        if not isinstance(r, dict):
            continue
        pid = r.get("id")
        if pid:
            keys.add(str(pid))
        sym = str(r.get("symbol") or "").upper()
        strat = str(r.get("strategy") or "")
        d = str(r.get("direction") or "").upper()
        keys.add("%s|%s|%s" % (sym, strat, d))
    return keys


def pick_verified_key(p: Dict[str, Any]) -> Tuple[str, str]:
    pid = str(p.get("id") or "")
    sym = str(p.get("symbol") or "").upper()
    strat = str(p.get("strategy") or "")
    d = str(p.get("direction") or "").upper()
    return pid, "%s|%s|%s" % (sym, strat, d)


def slice_rows(
    rows: List[Dict[str, Any]],
    *,
    asset_filter: Optional[str] = None,
    verified_keys: Optional[set] = None,
    verified_only: bool = False,
) -> List[Dict[str, Any]]:
    out = []
    for p in rows:
        ac = str(p.get("asset_class") or "").upper()
        if asset_filter == "CRYPTO" and ac != "CRYPTO":
            continue
        if asset_filter == "NON_CRYPTO" and ac == "CRYPTO":
            continue
        if verified_only and verified_keys:
            pid, ck = pick_verified_key(p)
            if pid not in verified_keys and ck not in verified_keys:
                continue
        out.append(p)
    return out


def _tier_if_still_active(p: Dict[str, Any]) -> str:
    """Counterfactual SMART vs ACTIVE: gates reject CLOSED status; simulate OPEN."""
    p2 = dict(p)
    p2["status"] = "OPEN"
    try:
        return classify_pick_quality(p2)
    except Exception:
        return "?"


def enrich_row(p: Dict[str, Any]) -> Dict[str, Any]:
    ss = p.get("smart_score")
    if ss is None:
        ss = calculate_smart_score(p)
    tier = _tier_if_still_active(p)
    return {
        "pnl_pct": _float(p.get("pnl_pct")),
        "score": _float(p.get("score")),
        "smart_score": float(ss) if ss is not None else calculate_smart_score(p),
        "ml_composite_score": _float(p.get("ml_composite_score")),
        "elite_score": _float(p.get("elite_score")),
        "confidence": _float(p.get("confidence")),
        "trust_tier": str(p.get("trust_tier") or ""),
        "asset_class": str(p.get("asset_class") or ""),
        "quality_tier": tier,
        "strategy": str(p.get("strategy") or ""),
        "source_system": str(p.get("source_system") or ""),
    }


def analyze_slice(name: str, enriched: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(enriched) < 30:
        return {"name": name, "n": len(enriched), "note": "insufficient_n"}

    def col(k: str) -> np.ndarray:
        return np.array([_float(r.get(k)) for r in enriched], dtype=np.float64)

    pnl = col("pnl_pct")
    metrics = ("score", "smart_score", "ml_composite_score", "elite_score", "confidence")
    cor = {}
    for m in metrics:
        x = col(m)
        cor[m] = {
            "pearson_pnl": round(pearson(x, pnl), 5) if len(enriched) else None,
            "spearman_pnl": round(spearman(x, pnl), 5) if len(enriched) else None,
        }

    # Win rate: top 25% score vs bottom 25%
    sc = col("score")
    if np.isfinite(sc).sum() >= 40:
        hi = np.percentile(sc[np.isfinite(sc)], 75)
        lo = np.percentile(sc[np.isfinite(sc)], 25)
        hi_m = pnl[sc >= hi]
        lo_m = pnl[sc <= lo]
        wr_hi = float(np.mean(hi_m > 0)) if len(hi_m) else float("nan")
        wr_lo = float(np.mean(lo_m > 0)) if len(lo_m) else float("nan")
        cor["score_quartiles"] = {
            "win_rate_top_quartile_pct": round(100 * wr_hi, 2),
            "win_rate_bottom_quartile_pct": round(100 * wr_lo, 2),
            "spread_pp": round(100 * (wr_hi - wr_lo), 2),
        }

    q_smart = quintile_lift(col("smart_score"), pnl)
    q_score = quintile_lift(col("score"), pnl)

    # Trust tier breakdown
    by_trust: Dict[str, List[float]] = defaultdict(list)
    for r in enriched:
        by_trust[str(r.get("trust_tier") or "UNKNOWN")].append(_float(r.get("pnl_pct")))

    trust_summary = {}
    for t, vals in by_trust.items():
        if len(vals) < 8:
            continue
        a = np.array(vals, dtype=np.float64)
        trust_summary[t] = {
            "n": len(vals),
            "mean_pnl_pct": round(float(np.mean(a)), 4),
            "win_rate_pct": round(float(100 * np.mean(a > 0)), 2),
        }

    # SMART vs ACTIVE (at signal time classification)
    sm = defaultdict(list)
    for r in enriched:
        sm[str(r.get("quality_tier") or "?")].append(_float(r.get("pnl_pct")))
    tier_cmp = {}
    for t, vals in sm.items():
        if len(vals) < 5:
            continue
        a = np.array(vals, dtype=np.float64)
        tier_cmp[t] = {
            "n": len(vals),
            "mean_pnl_pct": round(float(np.mean(a)), 4),
            "win_rate_pct": round(float(100 * np.mean(a > 0)), 2),
        }

    return {
        "name": name,
        "n": len(enriched),
        "correlations_vs_pnl_pct": cor,
        "quintile_smart_score": q_smart,
        "quintile_score": q_score,
        "by_trust_tier": trust_summary,
        "by_quality_tier_signal_time": tier_cmp,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("missing %s" % path, file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    picks = data.get("picks") or {}
    recent_closed = picks.get("recent_closed") or []
    active = picks.get("active") or []
    va = data.get("verified_alpha") or {}
    vkeys = verified_ref_set(va)

    enriched_closed = [enrich_row(p) for p in recent_closed]
    enriched_active = [enrich_row(p) for p in active]

    slices = {
        "recent_closed_all": analyze_slice("recent_closed_all", enriched_closed),
        "recent_closed_crypto": analyze_slice(
            "recent_closed_crypto",
            [enrich_row(p) for p in slice_rows(recent_closed, asset_filter="CRYPTO")],
        ),
        "recent_closed_non_crypto": analyze_slice(
            "recent_closed_non_crypto",
            [enrich_row(p) for p in slice_rows(recent_closed, asset_filter="NON_CRYPTO")],
        ),
        "active_all": analyze_slice("active_all", enriched_active),
    }
    if vkeys:
        vclosed = [enrich_row(p) for p in slice_rows(recent_closed, verified_only=True, verified_keys=vkeys)]
        slices["recent_closed_verified_alpha_pool_overlap"] = analyze_slice(
            "recent_closed_verified_alpha_pool_overlap", vclosed
        )

    # Top source_systems by count (closed)
    src_counts: Dict[str, int] = defaultdict(int)
    for p in recent_closed:
        src_counts[str(p.get("source_system") or "unknown")] += 1
    top_src = sorted(src_counts.keys(), key=lambda k: -src_counts[k])[:12]
    for src in top_src:
        rows = [p for p in recent_closed if str(p.get("source_system") or "") == src]
        if src_counts[src] < 80:
            continue
        slices["closed_source_%s" % src[:40]] = analyze_slice(
            "closed_source:%s" % src, [enrich_row(p) for p in rows]
        )

    report = {
        "dashboard_path": str(path).replace("\\", "/"),
        "n_recent_closed": len(recent_closed),
        "n_active": len(active),
        "verified_alpha_summary": {
            "active_count": va.get("active_count"),
            "smart_count": va.get("smart_count"),
            "active_share_pct": va.get("active_share_pct"),
            "smart_share_pct": va.get("smart_share_pct"),
            "realized": va.get("realized"),
            "audited": va.get("audited"),
            "status_note": va.get("status_note"),
            "n_active_pick_refs": len(vkeys),
        },
        "picks_smart_picks_feed_len": len(picks.get("smart_picks") or []) if picks.get("smart_picks") is not None else 0,
        "slices": slices,
        "best_ic_hint": _best_ic_hint(slices),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps(report["best_ic_hint"], indent=2))
    print("wrote", out_path)
    return 0


def _best_ic_hint(slices: Dict[str, Any]) -> Dict[str, Any]:
    """Which scalar had highest |spearman| to pnl in main slices."""
    best = []
    for sk in ("recent_closed_all", "recent_closed_crypto", "recent_closed_non_crypto"):
        block = slices.get(sk) or {}
        cor = block.get("correlations_vs_pnl_pct") or {}
        for metric, d in cor.items():
            if not isinstance(d, dict):
                continue
            sp = d.get("spearman_pnl")
            if sp is None or (isinstance(sp, float) and math.isnan(sp)):
                continue
            best.append((abs(sp), sp, metric, sk))
    best.sort(reverse=True)
    return {"ranked_abs_spearman": [{"metric": x[2], "slice": x[3], "spearman": x[1]} for x in best[:8]]}


if __name__ == "__main__":
    sys.exit(main())
