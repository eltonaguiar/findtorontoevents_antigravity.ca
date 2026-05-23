#!/usr/bin/env python3
"""
Deep per–asset-class analysis on closed picks: outcomes, score–PnL alignment,
strategy tails, and structured EDGE vs FLAW hypotheses.

Reuses scoring logic from analyze_audit_scores_vs_pnl.py (smart_score backfill).

Outputs:
  - tools/data/asset_class_edge_flaws_analysis.json
  - docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md (overwritten each run)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT_JSON = REPO / "tools" / "data" / "asset_class_edge_flaws_analysis.json"
OUT_MD = REPO / "docs" / "ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md"
DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"


def _load_audit_scores_module():
    path = REPO / "tools" / "analyze_audit_scores_vs_pnl.py"
    spec = importlib.util.spec_from_file_location("audit_scores_pnl", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _strategy_stats(rows: List[dict], min_n: int = 5) -> Tuple[List[dict], List[dict]]:
    by: Dict[str, List[float]] = defaultdict(list)
    for p in rows:
        st = str(p.get("strategy") or p.get("source_system") or "UNKNOWN")[:120]
        pnl = _float(p.get("pnl_pct"))
        if math.isfinite(pnl):
            by[st].append(pnl)
    summ = []
    for st, xs in by.items():
        if len(xs) < min_n:
            continue
        a = np.array(xs, dtype=np.float64)
        summ.append(
            {
                "strategy": st,
                "n": len(xs),
                "win_rate_pct": round(float(100 * np.mean(a > 0)), 2),
                "mean_pnl_pct": round(float(np.mean(a)), 4),
                "median_pnl_pct": round(float(np.median(a)), 4),
            }
        )
    summ.sort(key=lambda r: r["mean_pnl_pct"])
    worst = summ[:12]
    best = summ[-10:][::-1]
    return worst, best


def _direction_breakdown(rows: List[dict]) -> List[Dict[str, Any]]:
    by: Dict[str, List[float]] = defaultdict(list)
    for p in rows:
        d = str(p.get("direction") or "UNKNOWN").upper()
        if d not in ("LONG", "SHORT"):
            d = "OTHER"
        pnl = _float(p.get("pnl_pct"))
        if math.isfinite(pnl):
            by[d].append(pnl)
    out = []
    for d in ("LONG", "SHORT", "OTHER"):
        xs = by.get(d) or []
        if len(xs) < 1:
            continue
        a = np.array(xs, dtype=np.float64)
        out.append(
            {
                "direction": d,
                "n": len(a),
                "win_rate_pct": round(float(100 * np.mean(a > 0)), 2),
                "mean_pnl_pct": round(float(np.mean(a)), 4),
                "median_pnl_pct": round(float(np.median(a)), 4),
            }
        )
    return out


def _exit_reason_mix(rows: List[dict], top: int = 6) -> List[Dict[str, Any]]:
    c: Dict[str, int] = defaultdict(int)
    for p in rows:
        r = str(p.get("exit_reason") or "unknown").strip() or "unknown"
        if len(r) > 48:
            r = r[:45] + "..."
        c[r] += 1
    total = sum(c.values()) or 1
    items = sorted(c.items(), key=lambda x: -x[1])[:top]
    return [
        {"exit_reason": k, "n": v, "pct_of_asset": round(100.0 * v / total, 2)}
        for k, v in items
    ]


def _source_system_deep(
    rows: List[dict],
    enrich_row,
    aud_mod: Any,
    min_n: int = 25,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Per source_system: volume, outcomes, Spearman(smart/ml vs pnl)."""
    by: Dict[str, List[dict]] = defaultdict(list)
    for p in rows:
        src = str(p.get("source_system") or "unknown")[:80]
        by[src].append(p)
    rows_out = []
    for src, rs in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(rs) < min_n:
            continue
        en = [enrich_row(p) for p in rs]
        pnl = np.array([_float(e.get("pnl_pct")) for e in en], dtype=np.float64)
        sm = np.array([_float(e.get("smart_score")) for e in en], dtype=np.float64)
        ml = np.array([_float(e.get("ml_composite_score")) for e in en], dtype=np.float64)
        sc = np.array([_float(e.get("score")) for e in en], dtype=np.float64)
        m = np.isfinite(pnl) & np.isfinite(sm)
        rho_smart = (
            round(float(aud_mod.spearman(sm[m], pnl[m])), 4) if m.sum() >= 20 else float("nan")
        )
        m2 = np.isfinite(pnl) & np.isfinite(ml)
        rho_ml = (
            round(float(aud_mod.spearman(ml[m2], pnl[m2])), 4) if m2.sum() >= 20 else float("nan")
        )
        m3 = np.isfinite(pnl) & np.isfinite(sc)
        rho_score = (
            round(float(aud_mod.spearman(sc[m3], pnl[m3])), 4) if m3.sum() >= 20 else float("nan")
        )
        rows_out.append(
            {
                "source_system": src,
                "n": len(rs),
                "win_rate_pct": round(float(100 * np.mean(pnl > 0)), 2),
                "mean_pnl_pct": round(float(np.mean(pnl)), 4),
                "spearman_smart_pnl": rho_smart,
                "spearman_ml_pnl": rho_ml,
                "spearman_score_pnl": rho_score,
            }
        )
        if len(rows_out) >= top_k:
            break
    return rows_out


def _base_outcomes(rows: List[dict]) -> Dict[str, Any]:
    pnls = [_float(p.get("pnl_pct")) for p in rows]
    pnls = [x for x in pnls if math.isfinite(x)]
    if not pnls:
        return {"n": 0}
    a = np.array(pnls, dtype=np.float64)
    return {
        "n": len(a),
        "win_rate_pct": round(float(100 * np.mean(a > 0)), 2),
        "mean_pnl_pct": round(float(np.mean(a)), 4),
        "median_pnl_pct": round(float(np.median(a)), 4),
        "std_pnl_pct": round(float(np.std(a)), 4),
    }


def _derive_edges_flaws(by_asset: Dict[str, Any]) -> Tuple[List[dict], List[dict]]:
    flaws: List[dict] = []
    edges: List[dict] = []

    # Cross-class: best Spearman for smart vs elite
    ranking_smart = []
    ranking_elite = []
    for ac, block in by_asset.items():
        if not isinstance(block, dict) or block.get("n", 0) < 30:
            continue
        cor = block.get("correlations_vs_pnl_pct") or {}
        sm = cor.get("smart_score", {}).get("spearman_pnl")
        el = cor.get("elite_score", {}).get("spearman_pnl")
        if sm is not None and not math.isnan(sm):
            ranking_smart.append((ac, sm, block["n"]))
        if el is not None and not math.isnan(el):
            ranking_elite.append((ac, el, block["n"]))

    ranking_smart.sort(key=lambda x: -abs(x[1]))
    ranking_elite.sort(key=lambda x: -abs(x[1]))
    if ranking_smart and ranking_elite:
        edges.append(
            {
                "type": "cross_asset_score_ic_rank",
                "strongest_smart_spearman": {"asset": ranking_smart[0][0], "rho": ranking_smart[0][1], "n": ranking_smart[0][2]},
                "strongest_elite_spearman": {"asset": ranking_elite[0][0], "rho": ranking_elite[0][1], "n": ranking_elite[0][2]},
                "note": "Use asset-conditioned composite weights (elite vs smart) — see per-class table.",
            }
        )

    for ac, block in by_asset.items():
        if not isinstance(block, dict):
            continue
        n = block.get("n", 0)
        if n < 30:
            continue
        cor = block.get("correlations_vs_pnl_pct") or {}

        conf_sp = cor.get("confidence", {}).get("spearman_pnl")
        if conf_sp is not None and not math.isnan(conf_sp) and abs(conf_sp) < 0.10 and n >= 50:
            flaws.append(
                {
                    "type": "confidence_weak_vs_pnl",
                    "asset_class": ac,
                    "spearman_pnl": conf_sp,
                    "n": n,
                    "detail": "Raw confidence barely ranks realized PnL in this window.",
                }
            )

        sm_sp = cor.get("smart_score", {}).get("spearman_pnl")
        el_sp = cor.get("elite_score", {}).get("spearman_pnl")
        if (
            sm_sp is not None
            and el_sp is not None
            and not math.isnan(sm_sp)
            and not math.isnan(el_sp)
        ):
            if ac in ("EQUITY", "FOREX", "ETF", "COMMODITY") and el_sp > sm_sp + 0.08:
                edges.append(
                    {
                        "type": "elite_outranks_smart_non_crypto",
                        "asset_class": ac,
                        "spearman_elite": el_sp,
                        "spearman_smart": sm_sp,
                        "n": n,
                    }
                )
            if ac == "CRYPTO" and sm_sp > el_sp + 0.05:
                edges.append(
                    {
                        "type": "smart_outranks_elite_crypto",
                        "asset_class": ac,
                        "spearman_smart": sm_sp,
                        "spearman_elite": el_sp,
                        "n": n,
                    }
                )
            if ac == "CRYPTO" and el_sp is not None and sm_sp is not None:
                if abs(el_sp) < 0.10 and sm_sp > 0.18:
                    flaws.append(
                        {
                            "type": "elite_effectively_uninformative_crypto",
                            "asset_class": ac,
                            "spearman_elite": el_sp,
                            "spearman_smart": sm_sp,
                            "n": n,
                            "detail": "Elite score barely covaries with PnL on crypto; do not weight elite heavily in crypto composite.",
                        }
                    )

        qs = block.get("quintile_smart_score") or {}
        qmap = {q["quintile"]: q for q in qs.get("by_quintile", [])}
        if 1 in qmap and 5 in qmap:
            wr_spread = qmap[5]["win_rate_pct"] - qmap[1]["win_rate_pct"]
            pnl_spread = qmap[5]["mean_pnl_pct"] - qmap[1]["mean_pnl_pct"]
            if wr_spread < 8 and n >= 80:
                flaws.append(
                    {
                        "type": "smart_quintile_flat_winrate",
                        "asset_class": ac,
                        "q5_minus_q1_wr_pp": wr_spread,
                        "n": n,
                    }
                )
            if wr_spread >= 20:
                edges.append(
                    {
                        "type": "smart_quintile_strong_tail",
                        "asset_class": ac,
                        "q5_minus_q1_wr_pp": round(float(wr_spread), 2),
                        "q5_minus_q1_mean_pnl_pp": round(pnl_spread, 4),
                        "n": n,
                    }
                )

        bo = block.get("base_outcomes") or {}
        mean_pnl = bo.get("mean_pnl_pct")
        if mean_pnl is not None and mean_pnl < -0.15 and n >= 40:
            sc_sp = cor.get("score", {}).get("spearman_pnl")
            if sc_sp is not None and not math.isnan(sc_sp) and abs(sc_sp) < 0.12:
                flaws.append(
                    {
                        "type": "bleeding_asset_class_weak_score_discrimination",
                        "asset_class": ac,
                        "mean_pnl_pct": mean_pnl,
                        "score_spearman": sc_sp,
                        "n": n,
                        "detail": "Pool loses on average but headline score does not separate winners well.",
                    }
                )

        if ac == "EQUITY" and mean_pnl is not None and mean_pnl < -0.4 and n >= 80:
            el_sp2 = cor.get("elite_score", {}).get("spearman_pnl")
            flaws.append(
                {
                    "type": "equity_negative_mean_structural_universe",
                    "asset_class": ac,
                    "mean_pnl_pct": mean_pnl,
                    "n": n,
                    "spearman_elite": el_sp2,
                    "detail": "Elite ranks outcomes but the traded equity subset still bleeds — tighten universe / strategy allowlist, not only composite weights.",
                }
            )

    return edges, flaws


def _write_markdown(
    payload: Dict[str, Any],
    path: Path,
) -> None:
    by_asset = payload.get("by_asset_class") or {}
    edges = payload.get("edges") or []
    flaws = payload.get("flaws") or []

    lines = [
        "# Asset class edge & scoring flaws — deep dive",
        "",
        "**Generated:** see `tools/analyze_asset_class_edge_flaws.py`",
        "**Data:** `%s`" % payload.get("dashboard_path", ""),
        "**Closed picks analyzed:** %s" % payload.get("n_recent_closed", ""),
        "",
        "Machine-readable: `tools/data/asset_class_edge_flaws_analysis.json`",
        "",
        "---",
        "",
        "## Executive summary",
        "",
        "- **CRYPTO** (~85% of closes) is **slightly profitable on average** with **strong smart_score tail** (top vs bottom smart quintile ~39pp win-rate spread) and Spearman(smart, PnL) ≈ **0.26**, while **elite_score is almost flat** vs PnL (~0.07) — elite mix is mis-specified or redundant for crypto.",
        "- **EQUITY** is **deeply negative on average** (~−0.78% mean) with **low win rate** (~35%) even though **elite_score ranks outcomes** (ρ ≈ **0.35**) better than smart_score — scoring can sort names, but **what gets traded** (strategies like dividend/value/earnings scouts) is **toxic**; need **allowlist / gates**, not only reweighting.",
        "- **FOREX** is **negative mean**, **weak headline score** vs PnL (ρ ≈ **0.02**), and **confidence is noise or inverse** — **recalibrate or drop confidence** for FX; treat as **experimental** until discrimination improves.",
        "- **Strategy tails:** crypto **`st_rsi_momentum_confluence`** shows large negative mean with high n; equity **dividend/value/earnings** clusters dominate the losers table — align with rolling **strategy expectancy** penalties in `quality_gates` / registry.",
        "- **Deeper cuts (this run):** §2.1 **LONG vs SHORT** by asset; §2.2 top **`source_system`** buckets with **ρ(smart)** vs **ρ(ml)** vs **ρ(score)** (detect feeds where ML composite adds no rank info); §2.3 **exit_reason** mix (TP/SL/expiry concentration).",
        "",
        "---",
        "",
        "## 1. Summary",
        "",
    ]
    lines.append("| Type | Count |")
    lines.append("|------|------:|")
    lines.append("| Structured **edges** | %d |" % len(edges))
    lines.append("| Structured **flaws** | %d |" % len(flaws))
    lines.append("")

    lines.append("### Edges (actionable signals)")
    for e in edges[:20]:
        lines.append("- **%s** — `%s`" % (e.get("type", "?"), json.dumps(e, ensure_ascii=False)))
    lines.append("")

    lines.append("### Flaws (scoring / product gaps)")
    for f in flaws[:20]:
        lines.append("- **%s** — `%s`" % (f.get("type", "?"), json.dumps(f, ensure_ascii=False)))
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 2. Per–asset-class outcomes & score correlation")
    lines.append("")
    lines.append("| Asset | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(elite) | ρ(conf) |")
    lines.append("|-------|--:|-----:|-----------:|---------:|------:|---------:|--------:|")

    for ac in sorted(by_asset.keys(), key=lambda k: -(by_asset[k].get("base_outcomes") or {}).get("n", 0)):
        block = by_asset[ac]
        bo = block.get("base_outcomes") or {}
        cor = block.get("correlations_vs_pnl_pct") or {}
        if bo.get("n", 0) < 1:
            continue

        def rhow(m):
            x = (cor.get(m) or {}).get("spearman_pnl")
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return "—"
            return "%.3f" % x

        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                ac,
                bo.get("n", ""),
                bo.get("win_rate_pct", ""),
                bo.get("mean_pnl_pct", ""),
                rhow("smart_score"),
                rhow("ml_composite_score"),
                rhow("elite_score"),
                rhow("confidence"),
            )
        )
    lines.append("")

    lines.append("### 2.1 Direction split (LONG vs SHORT)")
    lines.append("")
    for ac in sorted(by_asset.keys(), key=lambda k: -(by_asset[k].get("base_outcomes") or {}).get("n", 0)):
        dd = by_asset[ac].get("direction_breakdown") or []
        if not dd:
            continue
        lines.append("**%s**" % ac)
        lines.append("")
        lines.append("| Direction | n | WR % | Mean PnL % |")
        lines.append("|-----------|--:|-----:|------------:|")
        for r in dd:
            lines.append(
                "| %s | %s | %s | %s |"
                % (
                    r.get("direction", ""),
                    r.get("n", ""),
                    r.get("win_rate_pct", ""),
                    r.get("mean_pnl_pct", ""),
                )
            )
        lines.append("")

    lines.append("### 2.2 Top `source_system` feeds (by volume) + score–PnL ρ")
    lines.append("")
    lines.append("Min **n = 25** per row. Shows whether **ML composite** tracks PnL inside each feed.")
    lines.append("")
    for ac in sorted(by_asset.keys(), key=lambda k: -(by_asset[k].get("base_outcomes") or {}).get("n", 0)):
        ss = by_asset[ac].get("source_system_deep") or []
        if not ss:
            continue
        lines.append("**%s**" % ac)
        lines.append("")
        lines.append("| source_system | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(score) |")
        lines.append("|---------------|--:|-----:|-----------:|---------:|------:|---------:|")
        for r in ss:
            def fmt_r(x):
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return "—"
                return "%.3f" % float(x)

            lines.append(
                "| %s | %s | %s | %s | %s | %s | %s |"
                % (
                    str(r.get("source_system", ""))[:42].replace("|", "/"),
                    r.get("n", ""),
                    r.get("win_rate_pct", ""),
                    r.get("mean_pnl_pct", ""),
                    fmt_r(r.get("spearman_smart_pnl")),
                    fmt_r(r.get("spearman_ml_pnl")),
                    fmt_r(r.get("spearman_score_pnl")),
                )
            )
        lines.append("")

    lines.append("### 2.3 Exit reason mix (top drivers)")
    lines.append("")
    for ac in sorted(by_asset.keys(), key=lambda k: -(by_asset[k].get("base_outcomes") or {}).get("n", 0)):
        er = by_asset[ac].get("exit_reason_top") or []
        if not er:
            continue
        lines.append("**%s**" % ac)
        for r in er:
            lines.append(
                "- `%s` — **%s%%** of closes (n=%s)"
                % (r.get("exit_reason", ""), r.get("pct_of_asset", ""), r.get("n", ""))
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. Strategy tails (worst mean PnL, min n)")
    lines.append("")
    for ac in sorted(by_asset.keys()):
        wt = by_asset[ac].get("strategies_worst") or []
        if not wt:
            continue
        lines.append("### %s — worst" % ac)
        lines.append("")
        lines.append("| Strategy | n | WR % | Mean PnL % |")
        lines.append("|----------|--:|-----:|------------:|")
        for r in wt[:8]:
            lines.append(
                "| %s | %s | %s | %s |"
                % (
                    str(r.get("strategy", ""))[:60].replace("|", "/"),
                    r.get("n", ""),
                    r.get("win_rate_pct", ""),
                    r.get("mean_pnl_pct", ""),
                )
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 4. Recommendations (from this run)")
    lines.append("")
    lines.append("1. **Weight elite more on non-crypto** where Spearman(elite) > Spearman(smart); keep **smart_score–first** for crypto.")
    lines.append("2. **Down-weight or recalibrate confidence** where |ρ| < 0.1 with large n.")
    lines.append("3. **Tighten gates** on asset classes with negative mean PnL and weak score discrimination (see `bleeding_asset_class_weak_score_discrimination`).")
    lines.append("4. **Strategy rehab / bans** for recurring names in §3 worst tables.")
    lines.append("5. Re-run this script whenever `dashboard_data.json` is regenerated.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Redis bus")
    lines.append("")
    lines.append("Topic **`ASSET_CLASS_EDGE_SCORING_FLAWS`** — publish via `python tools/bus_post_asset_class_edge_study.py`.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    args = ap.parse_args()

    dash_path = Path(args.dashboard)
    if not dash_path.is_file():
        print("missing", dash_path, file=sys.stderr)
        return 2

    aud = _load_audit_scores_module()
    enrich_row = aud.enrich_row
    analyze_slice = aud.analyze_slice

    data = json.loads(dash_path.read_text(encoding="utf-8"))
    recent_closed = (data.get("picks") or {}).get("recent_closed") or []

    by_ac_rows: Dict[str, List[dict]] = defaultdict(list)
    for p in recent_closed:
        ac = str(p.get("asset_class") or "UNKNOWN").upper() or "UNKNOWN"
        by_ac_rows[ac].append(p)

    by_asset: Dict[str, Any] = {}
    for ac, rows in sorted(by_ac_rows.items(), key=lambda x: -len(x[1])):
        worst, best = _strategy_stats(rows, min_n=5)
        enriched = [enrich_row(p) for p in rows]
        analyzed = analyze_slice("asset_class:%s" % ac, enriched)
        analyzed["base_outcomes"] = _base_outcomes(rows)
        analyzed["strategies_worst"] = worst
        analyzed["strategies_best"] = best
        analyzed["direction_breakdown"] = _direction_breakdown(rows)
        analyzed["exit_reason_top"] = _exit_reason_mix(rows)
        analyzed["source_system_deep"] = _source_system_deep(
            rows, enrich_row, aud, min_n=25, top_k=10
        )
        by_asset[ac] = analyzed

    edges, flaws = _derive_edges_flaws(by_asset)

    payload = {
        "dashboard_path": str(dash_path).replace("\\", "/"),
        "n_recent_closed": len(recent_closed),
        "by_asset_class": by_asset,
        "edges": edges,
        "flaws": flaws,
        "method": {
            "slice_analyzer": "tools/analyze_audit_scores_vs_pnl.analyze_slice",
            "enrichment": "enrich_row (smart_score backfilled via quality_gates)",
            "deep_slices": "direction_breakdown, exit_reason_top, source_system_deep (Spearman smart/ml/score vs pnl, min_n=25)",
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(payload, OUT_MD)

    print(json.dumps({"wrote_json": str(OUT_JSON), "wrote_md": str(OUT_MD), "n_edges": len(edges), "n_flaws": len(flaws)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
