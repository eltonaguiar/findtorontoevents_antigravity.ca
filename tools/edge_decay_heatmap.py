"""Edge-decay heatmap data builder for the /audit dashboard.

Rolling 30d Profit Factor + Win Rate per strategy. Flags strategies as:

  - ``dead``       — PF < 0.8 over the trailing 30d window
  - ``decaying``   — PF is monotonically falling across 7d / 30d / 90d windows
  - ``improving``  — PF is monotonically rising across 7d / 30d / 90d
  - ``stable``     — none of the above

Output: ``audit_dashboard/data/edge_decay_heatmap.json`` consumed by a
future ``audit_dashboard/edge_stability.html`` widget.

Sidecar status (swarm 4/4 round 2026-05-13: TRULY_SIDECAR — dashboard-only,
no scoring or gate caller needed).

Wiring Plan (per CLAUDE.md Wire-Up Rule):
    Target caller: ``audit_trail/dashboard_generator.py`` OR
    ``.github/workflows/audit-dashboard.yml`` as a post-step. Both wire
    by invoking ``python -m tools.edge_decay_heatmap`` and reading the
    JSON in the renderer. Expected wire-up PR opens after #961 (COT
    dedup) lands so the inputs (`closed_picks.json`) reflect post-dedup
    reality. Until then, this tool is run manually and the JSON sits
    next to other sidecar artefacts.

Usage:
  python -m tools.edge_decay_heatmap
  python -m tools.edge_decay_heatmap --min-n 30

NFA. Read-only. Hindsight metrics.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSED_PICKS = ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUT_PATH = ROOT / "audit_dashboard" / "data" / "edge_decay_heatmap.json"

WINDOWS_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": 36500}
WINDOWS_ORDER = ["7d", "30d", "90d", "all"]
DEAD_PF_THRESHOLD = 0.8


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _load_closed_picks() -> list[dict]:
    if not CLOSED_PICKS.exists():
        return []
    try:
        d = json.loads(CLOSED_PICKS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("picks") or []
    return []


def _is_matic_ghost(p: dict) -> bool:
    src = (p.get("source_system") or "").lower()
    sym = (p.get("symbol") or "").upper()
    return src == "quan_engine" and sym.startswith("MATIC")


def _metrics(picks: list[dict]) -> dict:
    n = len(picks)
    if n == 0:
        return {"n": 0, "wr": None, "pf": None}
    wins = 0
    win_pnl = 0.0
    loss_pnl = 0.0
    for p in picks:
        try:
            v = float(p.get("pnl_pct"))
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        if v > 0:
            wins += 1
            win_pnl += v
        elif v < 0:
            loss_pnl += abs(v)
    wr = 100.0 * wins / n
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else (999.0 if win_pnl > 0 else 0.0)
    return {"n": n, "wr": round(wr, 2), "pf": round(pf, 3)}


def _classify(by_window: dict[str, dict]) -> str:
    pfs = [by_window.get(w, {}).get("pf") for w in ("90d", "30d", "7d")]
    pfs = [p for p in pfs if p is not None]
    if len(pfs) < 2:
        return "insufficient"
    pf_30 = by_window.get("30d", {}).get("pf")
    if pf_30 is not None and pf_30 < DEAD_PF_THRESHOLD:
        return "dead"
    # Strict monotone falling: 90d > 30d > 7d
    if all(pfs[i] > pfs[i + 1] for i in range(len(pfs) - 1)):
        return "decaying"
    if all(pfs[i] < pfs[i + 1] for i in range(len(pfs) - 1)):
        return "improving"
    return "stable"


def build(min_n: int = 30, ghost_filter: bool = True,
          out_path: Path | None = None) -> dict:
    picks_raw = _load_closed_picks()
    if ghost_filter:
        picks_raw = [p for p in picks_raw if not _is_matic_ghost(p)]
    now = datetime.now(timezone.utc)
    by_strat: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in picks_raw:
        strat = p.get("strategy") or ""
        src = p.get("source_system") or ""
        ts = _parse_ts(p.get("closed_at") or p.get("exit_time") or "")
        if not strat or ts is None:
            continue
        p2 = dict(p)
        p2["_exit_dt"] = ts
        by_strat[(strat, src)].append(p2)
    rows = []
    for (strat, src), picks in by_strat.items():
        by_window = {}
        for w, days in WINDOWS_DAYS.items():
            cutoff = now - timedelta(days=days)
            subset = [p for p in picks if p["_exit_dt"] >= cutoff]
            by_window[w] = _metrics(subset)
        total_n = by_window["all"]["n"]
        if total_n < min_n:
            continue
        verdict = _classify(by_window)
        rows.append({
            "strategy": strat,
            "source_system": src,
            "n_total": total_n,
            "per_window": by_window,
            "verdict": verdict,
        })
    rows.sort(key=lambda r: (
        {"dead": 0, "decaying": 1, "stable": 2, "improving": 3,
         "insufficient": 4}.get(r["verdict"], 9),
        -r["n_total"],
    ))
    payload = {
        "generated_at": now.isoformat(),
        "schema_version": "v1",
        "min_n": min_n,
        "ghost_filter_applied": ghost_filter,
        "windows": WINDOWS_ORDER,
        "dead_pf_threshold": DEAD_PF_THRESHOLD,
        "n_strategies": len(rows),
        "rows": rows,
        "summary_counts": {
            v: sum(1 for r in rows if r["verdict"] == v)
            for v in ("dead", "decaying", "stable", "improving", "insufficient")
        },
        "notes": [
            "PF<0.8 over trailing 30d → 'dead'.",
            "Monotone PF drop 90d→30d→7d → 'decaying'.",
            "Monotone PF rise 90d→30d→7d → 'improving'.",
            "Ghost filter drops (source_system=quan_engine, symbol MATIC*).",
        ],
    }
    target = out_path or OUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# edge_decay_heatmap: wrote {target.relative_to(ROOT)}",
          file=sys.stderr)
    print(f"# n_strategies={len(rows)} verdict_counts={payload['summary_counts']}",
          file=sys.stderr)
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-n", type=int, default=30)
    ap.add_argument("--no-ghost-filter", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    build(min_n=args.min_n, ghost_filter=(not args.no_ghost_filter),
          out_path=args.out)


if __name__ == "__main__":
    main()
