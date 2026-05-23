"""Per-asset-class edge-stability analysis.

Produces `audit_dashboard/data/edge_stability/edge_stability_<CLASS>.json`
per asset class. Stdlib only. Reuses metric helpers from the existing
walk-forward harness + edge decay monitor.

Usage:
  python -m tools.edge.edge_stability --all
  python -m tools.edge.edge_stability --class BOND --out path/to/json

Schema (SCHEMA_VERSION=v1, must stay stable for /audit consumer):
  {
    "schema_version": "v1",
    "asset_class": "BOND",
    "as_of": "<UTC ISO>",
    "n_total": int,
    "tier_floor": {pf, wr, mdd, n},
    "windows": ["7d","30d","90d","all"],
    "per_window_aggregate": {<window>: {n, wr, pf, avg_pnl, sharpe, wilson_ci}},
    "per_strategy": [
      {strategy, source_system, n, per_window, stability_score, verdict,
       is_recent_decay, is_recent_lift}
    ],
    "latest_picks": [<10 most-recent closed picks per class>],
    "concentration": {top3_strategy_pnl_share, top3_symbol_pnl_share, pareto_flag},
    "consistency_verdict": "STABLE_EDGE|RECENT_LIFT|DECAYING_EDGE|NO_EDGE|INSUFFICIENT_DATA",
    "consistency_rationale": "..."
  }
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Reuse existing helpers — no duplicate math
from alpha_engine.walk_forward_validator import (
    compute_window_metrics,
    parse_ts,
)

SCHEMA_VERSION = "v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_PATH = REPO_ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUT_DIR = REPO_ROOT / "audit_dashboard" / "data" / "edge_stability"

WINDOWS_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": None}
WINDOWS_ORDER = ["7d", "30d", "90d", "all"]
# "INDEX" stock-index class renamed to "INDEX_STOCK" to avoid filename collision
# with aggregate edge_stability_index.json output. Per code review HIGH bug #1.
ASSET_CLASSES = ["CRYPTO", "FOREX", "COMMODITY", "BOND", "EQUITY", "ETF", "FUTURES", "INDEX_STOCK"]
TIER2_FLOOR = {"pf": 1.5, "wr": 50.0, "mdd": 20.0, "n": 100}

# Known data-quality artifacts to strip (see memory feedback files)
GHOST_SYMBOL_STATS = {
    # (symbol, source_system) → reason for stripping
    ("MATICUSDT", "quan_engine"): "100%-WR-2.5%-TP artifact (project_quan_engine_matic_positive_artifact)",
}


# ─── helpers ──────────────────────────────────────────────────────────────


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (round(max(0.0, center - half) * 100, 1), round(min(1.0, center + half) * 100, 1))


def _pnl_pct(p: dict) -> float | None:
    v = p.get("pnl_pct")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_won(p: dict) -> bool:
    """Match outcome_resolver convention. WIN = positive pnl_pct OR status in WIN-set."""
    s = str(p.get("status") or "").upper()
    if s in ("WON", "WIN", "CLOSED_TP", "TP_HIT"):
        return True
    if s in ("LOST", "LOSS", "CLOSED_SL", "SL_HIT"):
        return False
    pnl = _pnl_pct(p) or 0.0
    return pnl > 0


def _exit_dt(p: dict) -> datetime | None:
    for k in ("closed_at", "exit_time", "timestamp"):
        ts = p.get(k)
        if ts:
            epoch = parse_ts(ts)
            if epoch is not None:
                return datetime.fromtimestamp(epoch, tz=timezone.utc)
    return None


def _normalize(p: dict) -> dict | None:
    """Return a flat dict with only the fields edge_stability cares about,
    or None if the pick is unusable (no asset_class, no exit_time, no pnl).
    Safe to call with None / non-dict — returns None.
    """
    if not isinstance(p, dict):
        return None
    ac = (p.get("asset_class") or "").upper().strip()
    if not ac:
        return None
    pnl = _pnl_pct(p)
    if pnl is None:
        return None
    dt = _exit_dt(p)
    if dt is None:
        return None
    strat = (p.get("strategy") or "").strip() or "(unknown)"
    src = (p.get("source_system") or "").strip() or "(unknown)"
    sym = (p.get("symbol") or "").strip().upper()
    # Strip known ghosts
    if (sym, src) in GHOST_SYMBOL_STATS:
        return None
    return {
        "asset_class": ac,
        "strategy": strat,
        "source_system": src,
        "symbol": sym,
        "pnl_pct": pnl,
        "won": _is_won(p),
        "exit_dt": dt,
        "id": p.get("id"),
        "direction": p.get("direction"),
    }


def _load_all_picks() -> list[dict]:
    if not PAYLOAD_PATH.exists():
        print(f"::error::missing payload: {PAYLOAD_PATH}", file=sys.stderr)
        return []
    raw = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    picks = list(raw.get("picks", {}).get("recent_closed", []) or [])
    picks.extend(raw.get("universal_resolved_picks", []) or [])
    out = []
    for p in picks:
        n = _normalize(p)
        if n:
            out.append(n)
    return out


def _slice_window(picks: list[dict], now: datetime, days: int | None) -> list[dict]:
    if days is None:
        return picks
    cutoff = now - timedelta(days=days)
    return [p for p in picks if p["exit_dt"] >= cutoff]


def _metrics(window_picks: list[dict]) -> dict:
    """Map normalized picks → walk_forward_validator.compute_window_metrics shape."""
    trades = [{"pnl_pct": p["pnl_pct"]} for p in window_picks]
    m = compute_window_metrics(trades)
    wins = sum(1 for p in window_picks if p["won"])
    n = len(window_picks)
    ci_lo, ci_hi = wilson_ci(wins, n)
    m["wilson_ci"] = [ci_lo, ci_hi]
    m["n_wins"] = wins
    return m


def _stability_score(per_window: dict[str, dict]) -> int:
    """0-100 score: PF>1 each window (40), WR>=tier in 80% windows (25),
    rolling WR slope not negative (20), n>=30 each window (15).

    Simplified for v1 — slope not yet computed (needs intra-window time
    series); credit full 20 if 7d WR >= 30d WR else 0.
    """
    score = 0
    pos_pf = sum(1 for w in per_window.values() if (w.get("pf") or 0) > 1)
    if pos_pf >= len(per_window):
        score += 40
    elif pos_pf >= len(per_window) - 1:
        score += 25
    wr_floor_hits = sum(1 for w in per_window.values() if (w.get("wr") or 0) >= TIER2_FLOOR["wr"])
    if wr_floor_hits / max(1, len(per_window)) >= 0.8:
        score += 25
    wr_7d = (per_window.get("7d") or {}).get("wr", 0)
    wr_30d = (per_window.get("30d") or {}).get("wr", 0)
    if wr_7d >= wr_30d:
        score += 20
    n_hits = sum(1 for w in per_window.values() if (w.get("n") or 0) >= 30)
    if n_hits >= len(per_window):
        score += 15
    elif n_hits >= len(per_window) - 1:
        score += 10
    return min(100, score)


def _decay_or_lift(per_window: dict[str, dict]) -> tuple[bool, bool]:
    """Compare 7d vs 90d WR. ≥+10pp = lift; ≤-10pp = decay."""
    wr_7d = (per_window.get("7d") or {}).get("wr", 0)
    wr_90d = (per_window.get("90d") or {}).get("wr", 0)
    delta = wr_7d - wr_90d
    return (delta <= -10, delta >= 10)


def _per_strategy(class_picks: list[dict], now: datetime) -> list[dict]:
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in class_picks:
        by[(p["strategy"], p["source_system"])].append(p)
    out: list[dict] = []
    for (strat, src), picks in by.items():
        per_window = {w: _metrics(_slice_window(picks, now, WINDOWS_DAYS[w])) for w in WINDOWS_ORDER}
        score = _stability_score(per_window)
        decay, lift = _decay_or_lift(per_window)
        all_n = per_window["all"]["n"]
        all_pf = per_window["all"]["pf"]
        all_wr = per_window["all"]["wr"]
        if all_n < 30:
            verdict = "INSUFFICIENT_DATA"
        elif score >= 75:
            verdict = "STABLE_EDGE"
        elif lift:
            verdict = "RECENT_LIFT"
        elif decay:
            verdict = "DECAYING_EDGE"
        elif all_pf < 1.0 and all_wr < TIER2_FLOOR["wr"]:
            verdict = "NO_EDGE"
        else:
            verdict = "MIXED"
        out.append({
            "strategy": strat,
            "source_system": src,
            "n_total": all_n,
            "per_window": per_window,
            "stability_score": score,
            "verdict": verdict,
            "is_recent_decay": decay,
            "is_recent_lift": lift,
        })
    out.sort(key=lambda r: (-r["stability_score"], -r["n_total"]))
    return out


def _concentration(class_picks: list[dict]) -> dict:
    strat_pnl: dict[str, float] = defaultdict(float)
    sym_pnl: dict[str, float] = defaultdict(float)
    for p in class_picks:
        strat_pnl[p["strategy"]] += p["pnl_pct"]
        sym_pnl[p["symbol"]] += p["pnl_pct"]
    total = sum(abs(v) for v in strat_pnl.values()) or 1.0
    top3_strat = sorted(strat_pnl.values(), key=lambda v: -abs(v))[:3]
    top3_sym = sorted(sym_pnl.values(), key=lambda v: -abs(v))[:3]
    s_share = sum(abs(v) for v in top3_strat) / total
    sym_share = sum(abs(v) for v in top3_sym) / total
    flag = []
    if s_share > 0.7:
        flag.append("STRATEGY_CONCENTRATED")
    if sym_share > 0.7:
        flag.append("SYMBOL_CONCENTRATED")
    return {
        "top3_strategy_pnl_share": round(s_share, 3),
        "top3_symbol_pnl_share": round(sym_share, 3),
        "pareto_flag": "+".join(flag) or "DISTRIBUTED",
    }


def _class_verdict(per_window: dict[str, dict], per_strat: list[dict]) -> tuple[str, str]:
    n_all = per_window["all"]["n"]
    pf_all = per_window["all"]["pf"]
    wr_all = per_window["all"]["wr"]
    if n_all < TIER2_FLOOR["n"]:
        return (
            "INSUFFICIENT_DATA",
            f"n={n_all} below Tier-2 floor n>={TIER2_FLOOR['n']}; per-class verdict deferred.",
        )
    stable_count = sum(1 for s in per_strat if s["verdict"] == "STABLE_EDGE")
    decay_count = sum(1 for s in per_strat if s["verdict"] == "DECAYING_EDGE")
    lift_count = sum(1 for s in per_strat if s["verdict"] == "RECENT_LIFT")
    if pf_all >= TIER2_FLOOR["pf"] and wr_all >= TIER2_FLOOR["wr"]:
        v = "STABLE_EDGE"
    elif lift_count > decay_count and lift_count >= 2:
        v = "RECENT_LIFT"
    elif decay_count > lift_count and decay_count >= 2:
        v = "DECAYING_EDGE"
    elif pf_all < 1.0:
        v = "NO_EDGE"
    else:
        v = "MIXED"
    rationale = (
        f"all-time PF={pf_all} WR={wr_all}% n={n_all}; "
        f"stable={stable_count}, lifting={lift_count}, decaying={decay_count}."
    )
    return v, rationale


def compute_class(asset_class: str, all_picks: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(tz=timezone.utc)
    class_picks = [p for p in all_picks if p["asset_class"] == asset_class.upper()]
    per_window = {w: _metrics(_slice_window(class_picks, now, WINDOWS_DAYS[w])) for w in WINDOWS_ORDER}
    per_strat = _per_strategy(class_picks, now)
    concentration = _concentration(class_picks) if class_picks else {}
    latest = sorted(class_picks, key=lambda p: p["exit_dt"], reverse=True)[:10]
    latest_serialized = [{
        "id": p["id"],
        "strategy": p["strategy"],
        "source_system": p["source_system"],
        "symbol": p["symbol"],
        "direction": p["direction"],
        "closed_at": p["exit_dt"].isoformat(),
        "pnl_pct": round(p["pnl_pct"], 3),
        "won": p["won"],
    } for p in latest]
    verdict, rationale = _class_verdict(per_window, per_strat)
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_class": asset_class.upper(),
        "as_of": now.isoformat(),
        "n_total": len(class_picks),
        "tier_floor": TIER2_FLOOR,
        "windows": WINDOWS_ORDER,
        "per_window_aggregate": per_window,
        "per_strategy": per_strat,
        "latest_picks": latest_serialized,
        "concentration": concentration,
        "consistency_verdict": verdict,
        "consistency_rationale": rationale,
    }


def write_class(asset_class: str, data: dict, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"edge_stability_{asset_class.upper()}.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path


def write_index(out_dir: Path | None = None) -> Path:
    """Aggregate per-class summaries into one index file."""
    out_dir = out_dir or OUT_DIR
    idx: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": datetime.now(tz=timezone.utc).isoformat(),
        "classes": {},
    }
    for path in sorted(out_dir.glob("edge_stability_*.json")):
        # Skip both lowercase aggregate AND any future uppercase reintroduction
        if path.name.lower() in ("edge_stability_index.json",):
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cls = d.get("asset_class")
        if not cls:
            continue
        # Defense-in-depth: never self-include an aggregate file as a class
        if cls.upper() == "INDEX":
            continue
        idx["classes"][cls] = {
            "consistency_verdict": d.get("consistency_verdict"),
            "consistency_rationale": d.get("consistency_rationale"),
            "n_total": d.get("n_total"),
            "all_time_pf": (d.get("per_window_aggregate", {}).get("all") or {}).get("pf"),
            "all_time_wr": (d.get("per_window_aggregate", {}).get("all") or {}).get("wr"),
            "all_time_sharpe": (d.get("per_window_aggregate", {}).get("all") or {}).get("sharpe"),
            "wr_7d": (d.get("per_window_aggregate", {}).get("7d") or {}).get("wr"),
            "wr_30d": (d.get("per_window_aggregate", {}).get("30d") or {}).get("wr"),
            "wr_90d": (d.get("per_window_aggregate", {}).get("90d") or {}).get("wr"),
            "pareto_flag": (d.get("concentration") or {}).get("pareto_flag"),
        }
    idx_path = out_dir / "edge_stability_index.json"
    idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    return idx_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="asset_class", default=None,
                    help="Single class to compute. Default: --all.")
    ap.add_argument("--all", action="store_true", help="Compute every asset class.")
    ap.add_argument("--out", type=Path, default=OUT_DIR,
                    help="Output dir (default audit_dashboard/data/edge_stability/).")
    args = ap.parse_args()

    if not args.asset_class and not args.all:
        ap.error("pass --class <NAME> or --all")

    print("Loading dashboard_payload.json...")
    all_picks = _load_all_picks()
    print(f"Loaded {len(all_picks)} usable closed picks.")

    classes = ASSET_CLASSES if args.all else [args.asset_class.upper()]
    for cls in classes:
        data = compute_class(cls, all_picks)
        path = write_class(cls, data, args.out)
        v = data["consistency_verdict"]
        n = data["n_total"]
        agg = data["per_window_aggregate"]["all"]
        print(f"  {cls:10s} verdict={v:20s} n={n:6d} PF={agg['pf']:5.2f} WR={agg['wr']:5.1f}% Sharpe={agg['sharpe']:5.2f}  -> {path.name}")
    write_index(args.out)
    print(f"\nIndex: {args.out / 'edge_stability_index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
