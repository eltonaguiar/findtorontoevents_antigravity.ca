#!/usr/bin/env python3
"""Audit /audit picks edge review: asset classes, IC by class, filter counterfactuals.

Reads dashboard JSON (e.g. tools/data/audit_edge_review_live.json).
Uses Python gates: _is_verified_alpha_pick, passes_smart_gate (OPEN counterfactual),
_is_valid_resolved_pick. High conviction: node tools/hc_batch_eval.js.

Outputs: tools/data/audit_edge_review_report.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.dashboard_generator import (  # noqa: E402
    _is_valid_resolved_pick,
    _is_verified_alpha_pick,
)
from audit_trail.quality_gates import passes_smart_gate  # noqa: E402

_aas_path = REPO / "tools" / "analyze_audit_scores_vs_pnl.py"
_spec = importlib.util.spec_from_file_location("analyze_audit_scores_vs_pnl", _aas_path)
_aas = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_aas)
enrich_row = _aas.enrich_row
pearson = _aas.pearson
spearman = _aas.spearman


def _float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def wilson_ci_pct(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Approx 95% Wilson score interval for win rate (0–100 scale)."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = wins / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, (centre - half) * 100), min(100.0, (centre + half) * 100))


def normalize_sym(s: str) -> str:
    t = (s or "").upper().replace("BINANCE:", "").replace("BYBIT:", "").strip()
    t = t.replace("-USD", "USDT")
    return "".join(c for c in t if c.isalnum() or c in "=_-")


def pick_key_triple(p: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        normalize_sym(str(p.get("symbol") or "")),
        str(p.get("strategy") or ""),
        str(p.get("direction") or p.get("signal_type") or "").upper(),
    )


def pick_key_loose(p: Dict[str, Any]) -> Tuple[str, str]:
    return (
        normalize_sym(str(p.get("symbol") or "")),
        str(p.get("direction") or p.get("signal_type") or "").upper(),
    )


def build_smart_feed_index(feed: Any) -> Tuple[set, set]:
    """Exact triple keys and loose (sym, dir) from smart_picks_feed.picks."""
    if not isinstance(feed, dict):
        return set(), set()
    picks = feed.get("picks") or []
    exact: set = set()
    loose: set = set()
    for p in picks:
        if not isinstance(p, dict):
            continue
        exact.add(pick_key_triple(p))
        loose.add(pick_key_loose(p))
    return exact, loose


def as_open(p: Dict[str, Any]) -> Dict[str, Any]:
    q = dict(p)
    q["status"] = "OPEN"
    return q


def cohort_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "wins": 0,
            "losses": 0,
            "flat": 0,
            "win_rate_pct": None,
            "mean_pnl_pct": None,
            "median_pnl_pct": None,
            "wilson_wr_low_pct": None,
            "wilson_wr_high_pct": None,
        }
    pnls = np.array([_float(r.get("pnl_pct")) for r in rows], dtype=np.float64)
    wins = int(np.sum(pnls > 0))
    losses = int(np.sum(pnls < 0))
    flat = int(np.sum(pnls == 0))
    n = len(rows)
    resolved = wins + losses + flat
    wr = 100.0 * wins / n if n else None
    lo, hi = wilson_ci_pct(wins, n)
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "win_rate_pct": round(wr, 2) if wr is not None else None,
        "mean_pnl_pct": round(float(np.mean(pnls)), 4),
        "median_pnl_pct": round(float(np.median(pnls)), 4),
        "wilson_wr_low_pct": round(lo, 2),
        "wilson_wr_high_pct": round(hi, 2),
    }


def analyze_ic_by_asset_class(
    closed: List[Dict[str, Any]], min_n: int = 30
) -> Dict[str, Any]:
    by_ac: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in closed:
        ac = str(p.get("asset_class") or "UNKNOWN").upper() or "UNKNOWN"
        by_ac[ac].append(p)

    out: Dict[str, Any] = {}
    for ac, rows in sorted(by_ac.items(), key=lambda x: -len(x[1])):
        enriched = [enrich_row(p) for p in rows]
        if len(enriched) < min_n:
            out[ac] = {"n": len(enriched), "note": "insufficient_n_for_ic"}
            continue
        pnl = np.array([_float(r.get("pnl_pct")) for r in enriched], dtype=np.float64)
        metrics = ("score", "smart_score", "elite_score", "confidence")
        cor: Dict[str, Any] = {}
        for m in metrics:
            x = np.array([_float(r.get(m)) for r in enriched], dtype=np.float64)
            cor[m] = {
                "pearson_pnl": round(pearson(x, pnl), 5),
                "spearman_pnl": round(spearman(x, pnl), 5),
            }
        out[ac] = {"n": len(enriched), "correlations_vs_pnl_pct": cor}
    return out


def run_hc_node(picks: List[Dict[str, Any]], repo: Path) -> List[bool]:
    script = repo / "tools" / "hc_batch_eval.js"
    proc = subprocess.run(
        ["node", str(script)],
        input=json.dumps(picks),
        capture_output=True,
        text=True,
        cwd=str(repo),
    )
    if proc.returncode != 0:
        raise RuntimeError("hc_batch_eval failed: " + (proc.stderr or proc.stdout))
    return json.loads(proc.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        default=str(REPO / "tools" / "data" / "audit_edge_review_live.json"),
        help="Path to dashboard_data.json",
    )
    ap.add_argument(
        "--out",
        default=str(REPO / "tools" / "data" / "audit_edge_review_report.json"),
    )
    args = ap.parse_args()
    path = Path(args.dashboard)
    if not path.is_file():
        print("missing", path, file=sys.stderr)
        return 1

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    generated_at = data.get("generated_at")
    picks_block = data.get("picks") or {}
    recent_closed = picks_block.get("recent_closed") or []
    active = picks_block.get("active") or []
    smart_picks_tier = picks_block.get("smart_picks") or []
    perf_ac = (data.get("performance") or {}).get("by_asset_class") or {}
    smart_feed = data.get("smart_picks_feed") or {}
    feed_exact, feed_loose = build_smart_feed_index(smart_feed)

    validated = [p for p in recent_closed if _is_valid_resolved_pick(p)]

    # Symbol / strategy breadth (active + validated closed)
    breadth: Dict[str, Any] = {"by_asset_class": {}}

    def add_breadth(rows: List[Dict[str, Any]], label: str) -> None:
        for p in rows:
            ac = str(p.get("asset_class") or "UNKNOWN").upper() or "UNKNOWN"
            if ac not in breadth["by_asset_class"]:
                breadth["by_asset_class"][ac] = {
                    "symbols_active": set(),
                    "symbols_closed": set(),
                    "strategies_active": set(),
                    "strategies_closed": set(),
                }
            b = breadth["by_asset_class"][ac]
            sym = str(p.get("symbol") or "")
            strat = str(p.get("strategy") or "")
            src = str(p.get("source_system") or "")
            if "active" in label:
                b["symbols_active"].add(sym)
                b["strategies_active"].add((src, strat))
            else:
                b["symbols_closed"].add(sym)
                b["strategies_closed"].add((src, strat))

    add_breadth(active, "active")
    add_breadth(validated, "closed")

    for ac, b in breadth["by_asset_class"].items():
        b["unique_symbols_active"] = len(b.pop("symbols_active"))
        b["unique_symbols_closed"] = len(b.pop("symbols_closed"))
        b["unique_strategy_keys_active"] = len(b.pop("strategies_active"))
        b["unique_strategy_keys_closed"] = len(b.pop("strategies_closed"))

    # Counterfactual flags
    smart_gate_pass: List[Dict[str, Any]] = []
    va_pass: List[Dict[str, Any]] = []
    feed_overlap: List[Dict[str, Any]] = []

    for p in validated:
        if passes_smart_gate(as_open(p)):
            smart_gate_pass.append(p)
        if _is_verified_alpha_pick(p):
            va_pass.append(p)
        k3 = pick_key_triple(p)
        kl = pick_key_loose(p)
        if k3 in feed_exact or kl in feed_loose:
            feed_overlap.append(p)

    seen_k3: set = set()
    feed_dedup: List[Dict[str, Any]] = []
    for p in feed_overlap:
        k3 = pick_key_triple(p)
        if k3 in seen_k3:
            continue
        seen_k3.add(k3)
        feed_dedup.append(p)

    baseline = cohort_metrics(validated)

    # Node HC batch (validated picks only)
    try:
        hc_flags = run_hc_node(validated, REPO)
    except Exception as e:
        hc_flags = None
        hc_error = str(e)
    else:
        hc_error = None

    hc_pass: List[Dict[str, Any]] = []
    if hc_flags is not None:
        if len(hc_flags) != len(validated):
            hc_error = "hc length mismatch %s vs %s" % (len(hc_flags), len(validated))
            hc_pass = []
        else:
            for p, ok in zip(validated, hc_flags):
                if ok:
                    hc_pass.append(p)

    filters_summary = {
        "baseline_validated_closed": baseline,
        "passes_smart_gate_counterfactual_OPEN": cohort_metrics(smart_gate_pass),
        "python_verified_alpha": cohort_metrics(va_pass),
        "smart_picks_feed_overlap_exact_or_loose": cohort_metrics(feed_dedup),
        "picks_smart_picks_tier_active_count": len(smart_picks_tier),
        "high_conviction_js_passesHighConvictionPick": cohort_metrics(hc_pass)
        if not hc_error
        else None,
    }
    if hc_error:
        filters_summary["high_conviction_error"] = hc_error

    # Per asset class: baseline vs smart gate vs VA
    by_ac_filters: Dict[str, Any] = {}
    for ac in sorted({str(p.get("asset_class") or "UNKNOWN").upper() for p in validated}):
        sub = [p for p in validated if str(p.get("asset_class") or "").upper() == ac]
        sub_smart = [p for p in sub if passes_smart_gate(as_open(p))]
        sub_va = [p for p in sub if _is_verified_alpha_pick(p)]
        by_ac_filters[ac] = {
            "baseline": cohort_metrics(sub),
            "smart_gate": cohort_metrics(sub_smart),
            "verified_alpha": cohort_metrics(sub_va),
        }

    ic_by_asset = analyze_ic_by_asset_class(validated)

    report = {
        "meta": {
            "dashboard_path": str(path).replace("\\", "/"),
            "data_source_url": "https://findtorontoevents.ca/audit/data/dashboard_data.json",
            "fetched_at_utc": fetched_at,
            "payload_generated_at": generated_at,
            "note": "Use SITE JSON in browser when available; embedded HTML may be older.",
        },
        "counts": {
            "recent_closed_raw": len(recent_closed),
            "validated_closed_for_metrics": len(validated),
            "active": len(active),
            "smart_picks_tier_in_payload": len(smart_picks_tier),
            "smart_picks_feed_picks_count": len((smart_feed.get("picks") or [])),
        },
        "performance_by_asset_class_from_payload": perf_ac,
        "symbol_strategy_breadth": breadth,
        "ic_by_asset_class_validated_closed": ic_by_asset,
        "filter_counterfactuals_validated_closed": filters_summary,
        "per_asset_class_filters": by_ac_filters,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
