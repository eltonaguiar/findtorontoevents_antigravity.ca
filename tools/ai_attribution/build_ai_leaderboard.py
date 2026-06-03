#!/usr/bin/env python3
"""Build the per-AI pick-attribution leaderboard.

Reads the swarm pick book (``audit_dashboard/data/swarm_picks.json``), fans
each pick out per consulted AI engine (``models_consulted[].underlying_model``),
joins the resolved ``outcome``, and writes a leaderboard JSON the
``ai_leaderboard.html`` dashboard page renders.

Answers: which AI engine is best per asset class / horizon — by realized
win-rate, profit-factor and a small-n-safe rank score.

Phase 1 (this file): per-engine + per-asset-class roll-up.
Design: reports/design_per_ai_pick_attribution_2026-05-15.md

Read-only consumer of swarm_picks.json — never mutates the pick book.

Usage:
    python -m tools.ai_attribution.build_ai_leaderboard
    python tools/ai_attribution/build_ai_leaderboard.py --picks <path> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"
DEFAULT_OUT = REPO_ROOT / "audit_dashboard" / "data" / "ai_leaderboard"
DEFAULT_RESEARCH = REPO_ROOT / "research" / "asset_class"

SCHEMA_VERSION = "v1"
# A cell is rank-eligible only at n >= this (Tier-2 charter floor is 100;
# 20 is the Phase-1 "developing" visibility floor — below it a cell renders
# greyed and rank-ineligible).
MIN_N_RANKED = 20
# Shrinkage strength for the rank score — pulls a thin engine's WR toward the
# asset-class pooled prior so 3 lucky picks cannot top the board.
SHRINKAGE_ALPHA = 50.0

# Intended-hold horizon buckets, derived from the pick timeframe.
_HORIZON_BY_TF = {
    "1m": "short", "3m": "short", "5m": "short", "15m": "short",
    "30m": "short", "1h": "short",
    "2h": "medium", "4h": "medium", "6h": "medium", "12h": "medium",
    "1d": "medium",
    "3d": "long", "1w": "long", "1m+": "long", "1mo": "long", "1y": "long",
}


def horizon_for(timeframe: Any) -> str:
    """Map a pick timeframe to short / medium / long. Unknown -> medium."""
    return _HORIZON_BY_TF.get(str(timeframe or "").strip().lower(), "medium")


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI for a proportion, returned as percent (lo, hi)."""
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(max(0.0, centre - half) * 100, 1),
            round(min(1.0, centre + half) * 100, 1))


def _is_resolved(outcome: dict | None) -> bool:
    return bool(outcome) and outcome.get("pnl_pct") is not None


def _blank_cell() -> dict[str, Any]:
    return {"picks": [], "wins": 0, "losses": 0,
            "win_pnl": 0.0, "loss_pnl": 0.0}


def _accumulate(cell: dict[str, Any], pnl: float) -> None:
    if pnl > 0:
        cell["wins"] += 1
        cell["win_pnl"] += pnl
    else:
        cell["losses"] += 1
        cell["loss_pnl"] += abs(pnl)


def _metrics(cell: dict[str, Any]) -> dict[str, Any]:
    """Turn an accumulator cell into reported metrics."""
    n = cell["wins"] + cell["losses"]
    wr = round(100.0 * cell["wins"] / n, 1) if n else 0.0
    pf = (round(cell["win_pnl"] / cell["loss_pnl"], 2)
          if cell["loss_pnl"] > 0
          else (round(cell["win_pnl"], 2) if cell["win_pnl"] > 0 else 0.0))
    net = cell["win_pnl"] - cell["loss_pnl"]
    expectancy = round(net / n, 3) if n else 0.0
    ci_lo, ci_hi = wilson_ci(cell["wins"], n)
    return {
        "n": n, "wins": cell["wins"], "losses": cell["losses"],
        "wr": wr, "pf": pf, "expectancy": expectancy,
        "wilson_ci": [ci_lo, ci_hi], "wr_lower_bound": ci_lo,
        "rank_eligible": n >= MIN_N_RANKED,
        "classification": "classified" if n >= MIN_N_RANKED else "building",
    }


def _rank_score(m: dict[str, Any], pooled_wr: float) -> float:
    """Small-n-safe composite score. Shrinks WR toward the pooled prior,
    rewards PF, penalises a wide Wilson interval."""
    n = m["n"]
    if n <= 0:
        return 0.0
    wr_shrunk = (m["wins"] + SHRINKAGE_ALPHA * pooled_wr) / (n + SHRINKAGE_ALPHA)
    ci_halfwidth = (m["wilson_ci"][1] - m["wilson_ci"][0]) / 2.0
    pf = max(m["pf"], 0.1)
    return round(wr_shrunk * 100 + 12 * math.log(pf) - 0.15 * ci_halfwidth, 2)


def mine_research_proposers(research_dir: Path) -> dict[str, Any]:
    """Count research candidates proposed per engine.

    Mines ``research/asset_class/<cls>/run_*/p2_candidates.json`` —
    each candidate carries ``proposed_by_engine``. These are strategy
    *specs* with no realized outcome, so they are reported as a separate
    "contribution roster" — never folded into the realized-performance
    leaderboard (which needs resolved picks).
    """
    proposers: dict[str, dict[str, Any]] = {}
    total = 0
    if not research_dir.exists():
        return {"engines": {}, "total_candidates": 0}
    for p2 in sorted(research_dir.glob("*/run_*/p2_candidates.json")):
        try:
            items = json.loads(p2.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            eng = str(it.get("proposed_by_engine") or "unknown")
            cls = str(it.get("asset_class") or "UNKNOWN").upper()
            e = proposers.setdefault(eng, {"total": 0, "by_asset_class": {}})
            e["total"] += 1
            e["by_asset_class"][cls] = e["by_asset_class"].get(cls, 0) + 1
            total += 1
    return {"engines": proposers, "total_candidates": total}


def build(picks_path: Path,
          research_dir: Path | None = None) -> dict[str, Any]:
    """Build the leaderboard payload from the swarm pick book."""
    raw = json.loads(picks_path.read_text(encoding="utf-8"))
    picks = raw if isinstance(raw, list) else raw.get("picks", [])

    # engine -> {"overall": cell, "by_class": {cls: cell}, "by_horizon": {...}}
    engines: dict[str, dict[str, Any]] = {}
    # asset-class pooled accumulator for the shrinkage prior
    class_pool: dict[str, dict[str, Any]] = {}
    total_resolved = 0
    total_picks = len(picks)

    for p in picks:
        outcome = p.get("outcome") or {}
        resolved = _is_resolved(outcome)
        asset_class = str(p.get("asset_class") or "UNKNOWN").upper()
        horizon = horizon_for(p.get("timeframe"))
        pnl = float(outcome.get("pnl_pct") or 0.0) if resolved else None

        seen_engines: set[tuple[str, str]] = set()
        for mc in p.get("models_consulted", []):
            engine = str(mc.get("underlying_model") or "unknown")
            pid = str(p.get("pick_id", ""))
            dedup_key = (pid, engine)
            if dedup_key in seen_engines:
                continue
            seen_engines.add(dedup_key)
            e = engines.setdefault(engine, {
                "overall": _blank_cell(),
                "by_class": {},
                "by_horizon": {},
            })
            e["overall"]["picks"].append(p.get("pick_id"))
            cls_cell = e["by_class"].setdefault(asset_class, _blank_cell())
            hz_cell = e["by_horizon"].setdefault(horizon, _blank_cell())
            cls_cell["picks"].append(p.get("pick_id"))
            hz_cell["picks"].append(p.get("pick_id"))
            if resolved:
                _accumulate(e["overall"], pnl)
                _accumulate(cls_cell, pnl)
                _accumulate(hz_cell, pnl)
                cp = class_pool.setdefault(asset_class, _blank_cell())
                _accumulate(cp, pnl)

        if resolved:
            total_resolved += 1

    # pooled WR per class for shrinkage
    pooled: dict[str, float] = {}
    for cls, cell in class_pool.items():
        n = cell["wins"] + cell["losses"]
        pooled[cls] = (cell["wins"] / n) if n else 0.5
    global_pool_wr = (
        sum(c["wins"] for c in class_pool.values())
        / max(1, sum(c["wins"] + c["losses"] for c in class_pool.values()))
    ) if class_pool else 0.5

    if total_resolved == 0:
        import logging as _lg
        _lg.getLogger(__name__).warning(
            "ai-leaderboard: no resolved picks found — leaderboard will be empty. "
            "Check that swarm_picks.json contains resolved outcomes and that "
            "models_consulted[].underlying_model field is present."
        )

    out_engines: list[dict[str, Any]] = []
    for engine, e in sorted(engines.items()):
        overall_m = _metrics(e["overall"])
        overall_m["rank_score"] = _rank_score(overall_m, global_pool_wr)
        overall_m["total_picks"] = len(e["overall"]["picks"])
        by_class = {}
        for cls, cell in sorted(e["by_class"].items()):
            cm = _metrics(cell)
            cm["rank_score"] = _rank_score(cm, pooled.get(cls, 0.5))
            cm["total_picks"] = len(cell["picks"])
            by_class[cls] = cm
        by_horizon = {}
        for hz, cell in sorted(e["by_horizon"].items()):
            hm = _metrics(cell)
            hm["rank_score"] = _rank_score(hm, global_pool_wr)
            hm["total_picks"] = len(cell["picks"])
            by_horizon[hz] = hm
        # best asset class = highest rank_score among rank-eligible cells
        eligible = {c: m for c, m in by_class.items() if m["rank_eligible"]}
        best_class = (max(eligible, key=lambda c: eligible[c]["rank_score"])
                      if eligible else None)
        out_engines.append({
            "engine": engine,
            "overall": overall_m,
            "by_asset_class": by_class,
            "by_horizon": by_horizon,
            "best_asset_class": best_class,
        })

    # board sort: rank-eligible engines first (by rank_score), then building
    out_engines.sort(
        key=lambda e: (e["overall"]["rank_eligible"],
                       e["overall"]["rank_score"]),
        reverse=True,
    )

    research = mine_research_proposers(research_dir or DEFAULT_RESEARCH)

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "min_n_ranked": MIN_N_RANKED,
        "shrinkage_alpha": SHRINKAGE_ALPHA,
        "totals": {
            "picks": total_picks,
            "resolved": total_resolved,
            "engines": len(out_engines),
            "research_candidates": research["total_candidates"],
        },
        "engines": out_engines,
        "research_proposers": research["engines"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the per-AI leaderboard.")
    ap.add_argument("--picks", type=Path, default=DEFAULT_PICKS,
                    help="Path to swarm_picks.json.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="Output directory for the leaderboard JSON.")
    args = ap.parse_args(argv)

    if not args.picks.exists():
        print(f"[ai-leaderboard] no pick book at {args.picks} — nothing to do.")
        return 0

    payload = build(args.picks)
    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / "ai_leaderboard_index.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    t = payload["totals"]
    print(f"[ai-leaderboard] {t['engines']} engine(s), "
          f"{t['resolved']}/{t['picks']} resolved picks -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
