"""Generate `audit_dashboard/data/research_manifest.json` — the compact data
backing the /audit/research.html UI (2026-10-18).

Walks `research/asset_class/<class>/run_*` and, per run, reads:
  - `_summary.json`  (verdict, funnel counts, citations, cost, wall time)
  - `p3_backtest.json` (per-strategy pf / wr / sharpe / mdd / n_trades +
    walk-forward folds — trimmed to keep the manifest small)

Ranks every backtested strategy across ALL runs into a global "top strategies"
list (default 100) so the page can show the 100 best research strategies with
their proof at a glance.

Run: python -m tools.research.build_research_manifest
Output: audit_dashboard/data/research_manifest.json (committed + FTP-deployed
with the rest of audit_dashboard/data by the hourly audit-dashboard workflow).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = REPO_ROOT / "research" / "asset_class"
OUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "research_manifest.json"
TOP_N = 100


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _slim_strategy(row: dict) -> dict:
    folds = row.get("walk_forward_folds") or []
    return {
        "spec_id": row.get("spec_id"),
        "pf": row.get("pf"),
        "wr": row.get("wr"),
        "sharpe": row.get("sharpe"),
        "mdd": row.get("mdd"),
        "n": row.get("n_trades"),
        "folds": [
            {"pf": f.get("pf"), "wr": f.get("wr"), "sharpe": f.get("sharpe"), "n": f.get("n_trades")}
            for f in folds
        ],
    }


def _proof_score(s: dict) -> float:
    """Rank score: punish tiny samples hard, reward PF + Sharpe, cap MDD drag."""
    try:
        n = float(s.get("n") or 0)
        pf = float(s.get("pf") or 0)
        sharpe = float(s.get("sharpe") or 0)
        mdd = float(s.get("mdd") or 0)
    except (TypeError, ValueError):
        return -1.0
    if n < 10:
        return -1.0  # untradable sample — keep visible but unranked
    return round(pf + 0.5 * sharpe - 0.01 * max(0.0, mdd - 20.0) + min(n, 200) / 200.0, 4)


def main() -> int:
    if not RESEARCH_ROOT.is_dir():
        print(f"missing {RESEARCH_ROOT}", file=sys.stderr)
        return 1

    classes = {}
    top = []
    for class_dir in sorted(RESEARCH_ROOT.iterdir()):
        if not class_dir.is_dir():
            continue
        runs = []
        for run_dir in sorted(class_dir.glob("run_*")):
            summary = _read_json(run_dir / "_summary.json") or {}
            p3 = _read_json(run_dir / "p3_backtest.json")
            strategies = []
            if isinstance(p3, list):
                for row in p3:
                    if isinstance(row, dict):
                        strategies.append(_slim_strategy(row))
            elif isinstance(p3, dict):
                for row in (p3.get("strategies") or p3.get("results") or []):
                    if isinstance(row, dict):
                        strategies.append(_slim_strategy(row))
            rel = f"research/asset_class/{class_dir.name}/{run_dir.name}"
            for s in strategies:
                s["class"] = class_dir.name
                s["run_ts"] = summary.get("run_ts_utc") or run_dir.name.replace("run_", "")
                s["run"] = rel
                s["score"] = _proof_score(s)
                top.append(s)
            runs.append({
                "run": run_dir.name,
                "path": rel,
                "ts": summary.get("run_ts_utc") or run_dir.name.replace("run_", ""),
                "verdict": summary.get("verdict"),
                "aborted": bool(summary.get("aborted")),
                "funnel": {
                    "candidates": summary.get("n_candidates"),
                    "backtested": summary.get("n_backtested"),
                    "independent": summary.get("n_independent_after_cross_test"),
                    "validated": summary.get("n_v3b_validated"),
                    "rejected": summary.get("n_v3b_rejected"),
                },
                "citations": {
                    "verified": summary.get("n_citations_verified"),
                    "hallucinated": summary.get("n_citations_hallucinated"),
                },
                "cost_usd": summary.get("cost_usd"),
                "wall_time_sec": summary.get("wall_time_sec"),
                "n_strategies": len(strategies),
            })
        classes[class_dir.name] = {
            "n_runs": len(runs),
            "latest_verdict": runs[-1]["verdict"] if runs else None,
            "latest_ts": runs[-1]["ts"] if runs else None,
            "runs": runs,
        }

    top.sort(key=lambda s: s["score"], reverse=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "tools/research/build_research_manifest.py",
        "top_n": TOP_N,
        "n_strategies_total": len(top),
        "classes": classes,
        "top_strategies": top[:TOP_N],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(
        f"wrote {OUT_PATH} — {sum(c['n_runs'] for c in classes.values())} runs, "
        f"{len(top)} strategies ({len(manifest['top_strategies'])} ranked)"
    )
    return 0


if __name__ == "__main__":
    # Direct-script invocation safety (AGENTS.md import gotcha):
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
