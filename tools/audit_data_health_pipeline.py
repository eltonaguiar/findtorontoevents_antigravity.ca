#!/usr/bin/env python3
"""
Audit data health pipeline + edge evaluation (plan 2026-04-20).

Reads audit_dashboard/data/dashboard_data.json, runs structural / asset-class /
staleness / tab-mapping checks, high-conviction counterfactuals on recent_closed,
Guide-style filters, optional cross-permutation summary, and writes:
  - audit_dashboard/data/health_report.json
  - audit_dashboard/data/edge_report.md

Also refreshes tools/data/score_pnl_analysis.json via analyze_audit_scores_vs_pnl.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.dashboard_generator import _derive_asset_class  # noqa: E402
from tools.hc_gates_python import filter_high_conviction_ordered, reset_hc_gate_params_cache  # noqa: E402

DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
HEALTH_OUT = REPO / "audit_dashboard" / "data" / "health_report.json"
EDGE_OUT = REPO / "audit_dashboard" / "data" / "edge_report.md"
SCORE_PNL_OUT = REPO / "tools" / "data" / "score_pnl_analysis.json"
ACTIVE_BOOK_OUT = REPO / "tools" / "data" / "audit_active_book_analysis.json"


def _float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _finite(x: Any) -> bool:
    f = _float(x)
    return math.isfinite(f)


def _pick_key(p: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(p.get("symbol") or ""),
            str(p.get("strategy") or ""),
            str(p.get("direction") or ""),
            str(p.get("closed_at") or p.get("timestamp") or ""),
        ]
    )


def _normalize_wr(v: Any) -> float:
    f = _float(v)
    if not math.isfinite(f):
        return float("nan")
    if f > 1.5:
        f /= 100.0
    return f


def _profit_factor(pnls: List[float]) -> float:
    wins = sum(max(p, 0.0) for p in pnls)
    losses = sum(-min(p, 0.0) for p in pnls)
    if losses < 1e-12:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def _summarize_pnls(rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    pn = [_float(r.get("pnl_pct")) for r in rows]
    pn = [p for p in pn if math.isfinite(p)]
    if not pn:
        return {"label": label, "n": 0}
    a = np.array(pn, dtype=np.float64)
    return {
        "label": label,
        "n": len(a),
        "win_rate_pct": round(float(100 * np.mean(a > 0)), 3),
        "mean_pnl_pct": round(float(np.mean(a)), 5),
        "median_pnl_pct": round(float(np.median(a)), 5),
        "profit_factor": round(float(_profit_factor(list(a))), 4),
        "sum_pnl_pct": round(float(np.sum(a)), 4),
    }


def check_structural(rows: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    empty_sym = empty_dir = empty_strat = bad_price = zero_pnl_suspicious = 0
    confidence_scale_mixed = {"over_1": 0, "01_1": 0}
    for p in rows:
        sym = str(p.get("symbol") or "").strip()
        if not sym:
            empty_sym += 1
        if not str(p.get("direction") or "").strip():
            empty_dir += 1
        if not str(p.get("strategy") or "").strip():
            empty_strat += 1
        for fld in ("entry_price", "exit_price", "close_price"):
            if fld in p and p[fld] is not None and not _finite(p.get(fld)):
                bad_price += 1
                break
        ep, xp = _float(p.get("entry_price")), _float(p.get("exit_price"))
        pnl = _float(p.get("pnl_pct"))
        if math.isfinite(ep) and math.isfinite(xp) and abs(ep - xp) > 1e-9 and abs(pnl) < 1e-9:
            zero_pnl_suspicious += 1
        cf = p.get("confidence")
        if cf is not None and _finite(cf):
            c = _float(cf)
            if c > 1.0:
                confidence_scale_mixed["over_1"] += 1
            elif 0 <= c <= 1:
                confidence_scale_mixed["01_1"] += 1
    return {
        "subset": name,
        "counts": {
            "rows": len(rows),
            "empty_symbol": empty_sym,
            "empty_direction": empty_dir,
            "empty_strategy": empty_strat,
            "non_finite_entry_exit": bad_price,
            "flat_pnl_with_price_move": zero_pnl_suspicious,
            "confidence_gt_1": confidence_scale_mixed["over_1"],
            "confidence_0_1": confidence_scale_mixed["01_1"],
        },
        "severity": "warn" if (empty_sym or empty_dir or bad_price) else "ok",
    }


def check_asset_mismatches(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    mismatches: List[Dict[str, Any]] = []
    for p in rows:
        sym = str(p.get("symbol") or "")
        raw = dict(p) if isinstance(p, dict) else {}
        expected = _derive_asset_class(
            sym,
            raw,
            str(p.get("source_system") or ""),
            str(p.get("strategy") or ""),
        )
        reported = str(p.get("asset_class") or p.get("category") or "").upper().strip()
        if reported in ("STOCKS", "EQUITIES"):
            reported = "EQUITY"
        if reported and expected != reported:
            mismatches.append(
                {
                    "symbol": sym,
                    "reported": reported,
                    "derived": expected,
                    "key": _pick_key(p),
                }
            )
    return {
        "n_mismatch": len(mismatches),
        "sample": mismatches[:40],
    }


def check_forward_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    bad: List[str] = []
    for p in rows:
        st = int(p.get("strat_fwd_trades") or 0)
        wr = _normalize_wr(p.get("strat_fwd_wr"))
        if st == 0 and wr > 0.01:
            bad.append(_pick_key(p))
    return {"strat_fwd_wr_positive_but_zero_trades": len(bad), "sample_keys": bad[:20]}


def check_bleed_heuristic(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Same symbol + strategy: divergent forward_wr snapshots (possible merge noise)."""
    by_ss: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in rows:
        sym = str(p.get("symbol") or "").upper()
        strat = str(p.get("strategy") or "")
        if sym and strat:
            by_ss[(sym, strat)].append(p)
    flagged = 0
    examples: List[Dict[str, Any]] = []
    for (sym, strat), group in by_ss.items():
        if len(group) < 2:
            continue
        wrs = [_normalize_wr(x.get("strat_fwd_wr")) for x in group]
        wrs = [w for w in wrs if math.isfinite(w)]
        if len(wrs) < 2:
            continue
        if max(wrs) - min(wrs) > 0.25:
            flagged += 1
            if len(examples) < 15:
                examples.append(
                    {
                        "symbol": sym,
                        "strategy": strat,
                        "strat_fwd_wr_min": round(min(wrs), 4),
                        "strat_fwd_wr_max": round(max(wrs), 4),
                        "n": len(group),
                    }
                )
    return {"n_symbol_strategy_groups_wide_wr_spread": flagged, "examples": examples}


def verify_va_refs(active: List[Dict[str, Any]], va: Dict[str, Any]) -> Dict[str, Any]:
    refs = va.get("active_pick_refs") or []
    if not isinstance(refs, list):
        return {"error": "active_pick_refs not a list"}
    id_set = {str(p.get("id") or "") for p in active}
    keys = set()
    for p in active:
        k = "|".join(
            [
                str(p.get("symbol") or ""),
                str(p.get("strategy") or ""),
                str(p.get("direction") or ""),
            ]
        )
        keys.add(k)
    resolved = 0
    missing: List[Dict[str, Any]] = []
    for r in refs:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "")
        if rid and rid in id_set:
            resolved += 1
            continue
        rk = "|".join(
            [
                str(r.get("symbol") or ""),
                str(r.get("strategy") or ""),
                str(r.get("direction") or ""),
            ]
        )
        if rk in keys:
            resolved += 1
        else:
            missing.append(r)
    return {
        "n_refs": len(refs),
        "resolved_to_active": resolved,
        "unresolved_sample": missing[:15],
    }


def smart_feed_vs_dashboard(data: Dict[str, Any]) -> Dict[str, Any]:
    picks = data.get("picks") or {}
    smart_tab = picks.get("smart_picks") or []
    feed = data.get("smart_picks_feed") or {}
    scalp = feed.get("scalp_picks") if isinstance(feed, dict) else None
    picks_feed = feed.get("picks") if isinstance(feed, dict) else None
    return {
        "picks_smart_picks_len": len(smart_tab) if isinstance(smart_tab, list) else 0,
        "feed_generated_at": feed.get("generated_at") if isinstance(feed, dict) else None,
        "feed_scalp_count": len(scalp) if isinstance(scalp, list) else None,
        "feed_picks_count": len(picks_feed) if isinstance(picks_feed, list) else None,
        "dashboard_generated_at": data.get("generated_at"),
    }


def guide_proven_confidence_band(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Empirical 'Guide' slice: trust_tier PROVEN and confidence in [0.8, 0.9] (unit or percent)."""
    sel: List[Dict[str, Any]] = []
    for p in rows:
        tt = str(p.get("trust_tier") or "").upper()
        cf = _float(p.get("confidence"))
        if not math.isfinite(cf):
            continue
        if cf > 1:
            cf /= 100.0
        if tt == "PROVEN" and 0.8 <= cf <= 0.9:
            sel.append(p)
    return _summarize_pnls(sel, "guide_proven_confidence_0.8_0.9")


def guide_proven_only(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """All PROVEN trust_tier closes (Guide references PROVEN as elite edge)."""
    sel = [p for p in rows if str(p.get("trust_tier") or "").upper() == "PROVEN"]
    return _summarize_pnls(sel, "guide_proven_trust_tier_only")


def run_pipeline(dash_path: Path, skip_score_script: bool) -> int:
    reset_hc_gate_params_cache()
    if not dash_path.is_file():
        print("missing dashboard", dash_path, file=sys.stderr)
        return 1

    raw = dash_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    picks = data.get("picks") or {}
    active = picks.get("active") or []
    active_raw = picks.get("active_raw") or []
    recent_closed = picks.get("recent_closed") or []
    va = data.get("verified_alpha") or {}
    meta = data.get("metadata") or {}

    # --- Sort closed for HC ordered filter (oldest first — same as typical time order) ---
    def _closed_sort_key(p: Dict[str, Any]) -> str:
        return str(p.get("closed_at") or p.get("timestamp") or "")

    closed_sorted = sorted(recent_closed, key=_closed_sort_key)
    hc_pass = filter_high_conviction_ordered([dict(x) for x in closed_sorted])

    structural_active = check_structural(active, "picks.active")
    structural_closed = check_structural(recent_closed, "picks.recent_closed")
    asset_active = check_asset_mismatches(active)
    asset_closed = check_asset_mismatches(recent_closed)
    fwd_closed = check_forward_stats(recent_closed)
    bleed = check_bleed_heuristic(recent_closed)
    va_check = verify_va_refs(active, va)
    smart_info = smart_feed_vs_dashboard(data)

    baseline = _summarize_pnls(recent_closed, "recent_closed_baseline")
    hc_summary = _summarize_pnls(hc_pass, "high_conviction_counterfactual_ordered")
    guide_summary = guide_proven_confidence_band(recent_closed)
    guide_proven_only_summary = guide_proven_only(recent_closed)

    # Active book: HC pass rate
    hc_active = filter_high_conviction_ordered([dict(x) for x in active])
    active_hc_rate = len(hc_active) / len(active) if active else 0.0

    perm_summary = {}
    csp_summary_blob: Dict[str, Any] = {}
    csp = data.get("cross_strategy_permutations")
    if isinstance(csp, dict):
        sm = csp.get("summary") if isinstance(csp.get("summary"), dict) else {}
        csp_summary_blob = dict(sm) if sm else {}
        perm_summary = {
            "has_permutations": bool(csp.get("permutations")),
            "summary_keys": list((csp.get("summary") or {}).keys())[:20]
            if isinstance(csp.get("summary"), dict)
            else [],
            "summary": csp_summary_blob,
        }

    # Staleness block
    df = data.get("data_freshness") or {}
    feed = data.get("smart_picks_feed") or {}
    staleness = {
        "data_freshness": df,
        "smart_feed_generated_at": feed.get("generated_at") if isinstance(feed, dict) else None,
        "dashboard_generated_at": data.get("generated_at"),
        "metadata_payload_lag_seconds": meta.get("payload_lag_seconds"),
    }

    # Tab mapping (documented)
    tab_mapping = {
        "active_vs_active_raw": {
            "active_len": len(active),
            "active_raw_len": len(active_raw) if isinstance(active_raw, list) else 0,
            "note": "Published actives are post-gate; active_raw is larger pool when present.",
        },
        "smart_picks_tab": smart_info,
        "verified_alpha_refs": va_check,
        "track_pct_columns": "UI prefers strat_fwd_wr / strat_fwd_trades; fallback forward_wr / forward_trades",
        "hc_gates_python": "Mirrors audit_dashboard/hc_filter.js via tools/hc_gates_python.py",
    }

    health_report = {
        "dashboard_path": str(dash_path).replace("\\", "/"),
        "snapshot": {
            "generated_at": data.get("generated_at"),
            "metadata": meta,
            "repo_sha": meta.get("repo_sha") or meta.get("last_code_change_sha"),
        },
        "structural": [structural_active, structural_closed],
        "asset_class_mismatches": {
            "active": asset_active,
            "recent_closed": asset_closed,
        },
        "forward_stat_anomalies": fwd_closed,
        "symbol_strategy_wr_spread": bleed,
        "staleness": staleness,
        "tab_and_filters": tab_mapping,
        "cross_strategy_permutations": perm_summary,
        "edge_counterfactuals": {
            "baseline": baseline,
            "high_conviction_ordered": hc_summary,
            "guide_proven_confidence_0.8_0.9": guide_summary,
            "guide_proven_tier_only": guide_proven_only_summary,
        },
        "hc_params_config_path": "config/hc_gate_params.json",
    }

    HEALTH_OUT.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_OUT.write_text(json.dumps(health_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Edge markdown
    lines = [
        "# Audit edge report (automated health pipeline)",
        "",
        f"**Dashboard snapshot:** `{data.get('generated_at')}`  ",
        f"**Source:** `{dash_path}`  ",
        "",
        "## Data health (summary)",
        "",
        f"- Asset class mismatches (active): **{asset_active['n_mismatch']}**",
        f"- Asset class mismatches (closed): **{asset_closed['n_mismatch']}**",
        f"- Forward WR &gt; 0 but strat_fwd_trades = 0: **{fwd_closed['strat_fwd_wr_positive_but_zero_trades']}**",
        f"- Symbol+strategy wide WR spread groups: **{bleed['n_symbol_strategy_groups_wide_wr_spread']}**",
        f"- Verified-alpha refs resolved to active: **{va_check.get('resolved_to_active', 0)}** / **{va_check.get('n_refs', 0)}**",
        "",
        "## Closed-book performance (recent_closed)",
        "",
        "Counterfactual high-conviction uses the same ordered filter as `hc_filter.js` "
        "(correlation-pair registry applied in time order). Status is not forced OPEN for HC "
        "(gates do not check status).",
        "",
        "| Cohort | n | Win% | Mean pnl% | PF |",
        "|--------|---|------|------------|-----|",
        f"| {baseline['label']} | {baseline['n']} | {baseline.get('win_rate_pct', '')} | {baseline.get('mean_pnl_pct', '')} | {baseline.get('profit_factor', '')} |",
        f"| {hc_summary['label']} | {hc_summary['n']} | {hc_summary.get('win_rate_pct', '')} | {hc_summary.get('mean_pnl_pct', '')} | {hc_summary.get('profit_factor', '')} |",
        f"| {guide_summary['label']} | {guide_summary['n']} | {guide_summary.get('win_rate_pct', '')} | {guide_summary.get('mean_pnl_pct', '')} | {guide_summary.get('profit_factor', '')} |",
        f"| {guide_proven_only_summary['label']} | {guide_proven_only_summary['n']} | {guide_proven_only_summary.get('win_rate_pct', '')} | {guide_proven_only_summary.get('mean_pnl_pct', '')} | {guide_proven_only_summary.get('profit_factor', '')} |",
        "",
        f"- **Active picks passing HC gates now:** {len(hc_active)} / {len(active)} ({100*active_hc_rate:.1f}%)",
        "",
        f"- **Guide confidence band 0.8–0.9 on PROVEN:** n={guide_summary['n']} in this `recent_closed` window — "
        "the UI sometimes cites this band; if n=0, that slice cannot be empirically validated on current history.",
        "",
        "## TRUE edge vs marketing",
        "",
        "- **High-conviction filter** is a strict multi-gate rule set (score, trust, forward WR, "
        "per-asset floors, regime blocks, independent consensus, walk-forward). "
        "Empirical closed-book stats above show whether that slice historically outperformed the baseline.",
        "- **Guide slice** (`PROVEN` + confidence 0.8–0.9) is documented in the UI; when n=0 on closes, use **PROVEN-only** row or HC counterfactual instead.",
        "- **Confidence** is weakly correlated with pool-wide PnL in prior quant review—do not equate "
        "confidence with expectancy.",
        "",
        "## Limitations",
        "",
        "- Closed history does not include uniform fees/slippage; sum of pnl% is not portfolio equity.",
        "- Lookahead / stale forward stats on old rows possible.",
        "- Many historical closes may omit fields the UI now shows.",
        "",
        "## Combo / confluence track",
        "",
        "- See `cross_strategy_permutations` in dashboard JSON and `audit_dashboard/data/strategy_expansion_backtests.json` "
        "for research artifacts; production confluence lives under `alpha_engine/` (multi_signal_confluence, confluence_pipeline).",
        f"- **cross_strategy_permutations.summary (snapshot):** `{json.dumps(csp_summary_blob, ensure_ascii=False)[:500]}{'...' if len(json.dumps(csp_summary_blob)) > 500 else ''}`",
        "- Per-strategy stats from closes: `tools/data/audit_combo_strategy_stats.json` (top by closed count).",
        "",
        "## Machine-readable outputs",
        "",
        f"- `{HEALTH_OUT.relative_to(REPO).as_posix()}`",
        f"- `{SCORE_PNL_OUT.relative_to(REPO).as_posix()}` (from analyze_audit_scores_vs_pnl)",
        "",
    ]
    EDGE_OUT.write_text("\n".join(lines), encoding="utf-8")

    if not skip_score_script:
        sp = subprocess.run(
            [sys.executable, str(REPO / "tools" / "analyze_audit_scores_vs_pnl.py"), "--dashboard", str(dash_path)],
            cwd=str(REPO),
        )
        if sp.returncode != 0:
            print("analyze_audit_scores_vs_pnl failed", sp.returncode, file=sys.stderr)
        sp2 = subprocess.run(
            [sys.executable, str(REPO / "tools" / "analyze_audit_active_book.py"), "--dashboard", str(dash_path)],
            cwd=str(REPO),
        )
        if sp2.returncode != 0:
            print("analyze_audit_active_book failed", sp2.returncode, file=sys.stderr)

    # Combo appendix: forward_validator stats on closed (top by n)
    try:
        from alpha_engine.forward_validator import compute_all_strategy_stats  # noqa: WPS433

        perf = compute_all_strategy_stats(recent_closed)
        combo_appendix_path = REPO / "tools" / "data" / "audit_combo_strategy_stats.json"
        if isinstance(perf, dict):
            rows: List[Tuple[int, str, Dict[str, Any]]] = []
            for k, v in perf.items():
                if not isinstance(v, dict):
                    continue
                n = int(v.get("closed_picks") or 0)
                rows.append((n, k, v))
            rows.sort(key=lambda x: -x[0])
            slim2: List[Dict[str, Any]] = []
            for n, k, v in rows[:40]:
                slim2.append(
                    {
                        "strategy": k,
                        "closed_picks": v.get("closed_picks"),
                        "win_rate": v.get("win_rate"),
                        "profit_factor": v.get("profit_factor"),
                        "avg_pnl_pct": v.get("avg_pnl_pct"),
                    }
                )
            combo_appendix_path.write_text(
                json.dumps(
                    {"source": "compute_all_strategy_stats(recent_closed)", "top_by_closed_picks": slim2},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            health_report["combo_strategy_stats_top_path"] = combo_appendix_path.relative_to(REPO).as_posix()
            HEALTH_OUT.write_text(json.dumps(health_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as exc:
        health_report["combo_strategy_stats_error"] = str(exc)
        HEALTH_OUT.write_text(json.dumps(health_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("wrote", HEALTH_OUT)
    print("wrote", EDGE_OUT)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    ap.add_argument("--skip-score-scripts", action="store_true")
    args = ap.parse_args()
    return run_pipeline(Path(args.dashboard), args.skip_score_scripts)


if __name__ == "__main__":
    raise SystemExit(main())
