#!/usr/bin/env python3
"""Anti-overfit audit with walk-forward second-gate (P2-15).

Builds on `tools/anti_overfit_audit_sidecar.py` by adding a walk-forward
validation step for every strategy that the DSR layer labels
`EDGE_LIKELY_REAL`. If walk-forward REFUTES (FAIL or INSUFF_N), the strategy
is demoted to `REFUTED_BY_WF` with the per-window metrics attached.

Why this exists
---------------
The 2026-06-13 walk-forward sweep on the 4 EDGE_LIKELY_REAL strategies
(prediction_market_consensus, cta_golden_cross_200, ml_enhanced_INJUSDT_1d_B_lightgbm,
ml_enhanced_RENDERUSDT_1h_D_ensemble_stack) found 4/4 FAIL — a 100% false-positive
rate for the DSR-only view. The DSR (Lopez de Prado AFML 14.5) answers
"is this strategy's Sharpe statistically distinguishable from 0?" but does NOT
test "does it survive rolling out-of-sample evaluation?"

Walk-forward (rolling 14d IS / 5d OOS / 3d step) is the honest forward-deployment
test. Combining DSR AND walk-forward as two independent gates eliminates
single-cohort DSR inflation.

What it does
------------
1. Run `tools/anti_overfit_audit_sidecar.py` to get DSR verdicts
2. For every EDGE_LIKELY_REAL strategy with n >= 20, call
   `tools/walk_forward_per_strategy.py --min-n 20` to get OOS metrics
3. Demote any strategy where walk-forward says FAIL or INSUFF_N to
   `REFUTED_BY_WF` (preserving DSR verdict in the row for traceability)
4. Add `wf_*` fields to every EDGE_LIKELY_REAL row: n_windows, survival_rate,
   mean_oos_pf, mean_oos_wr, verdict, reasons, report path
5. Add summary fields:
   - `wf_gates_run`: count of walk-forward checks invoked
   - `wf_false_positive_rate`: ratio of DSR-EDGE_LIKELY_REAL that WF REFUTED
   - `verdict_counts` updated to include REFUTED_BY_WF
6. Write to `audit_dashboard/data/anti_overfit_audit.json` (same path as sidecar)
   OR `--out` if you want a different file

Usage::

    # Default: regenerate anti_overfit_audit.json with WF second-gate
    python tools/anti_overfit_audit_with_wf.py --min-n 10

    # Dry-run (don't write; print verdict diff)
    python tools/anti_overfit_audit_with_wf.py --min-n 10 --dry-run

    # Tune WF parameters (defaults: 14d IS / 5d OOS / 3d step, n_windows>=3)
    python tools/anti_overfit_audit_with_wf.py --min-n 10 \
        --wf-in-window 14 --wf-out-window 5 --wf-step 3 --wf-min-n 20

    # Skip walk-forward entirely (revert to sidecar behaviour)
    python tools/anti_overfit_audit_with_wf.py --no-walk-forward

Output JSON shape (additions only; backward-compatible with sidecar)
-------------------------------------------------------------------
{
  ...sidecar fields...,
  "wf_gates_run": 4,                      # NEW: number of WF checks invoked
  "wf_false_positive_rate": 1.0,          # NEW: ratio of EDGE_LIKELY_REAL that WF REFUTED
  "verdict_counts": {                     # UPDATED: includes REFUTED_BY_WF
    "EDGE_LIKELY_REAL": 0,
    "UNDETERMINED": 3,
    "OVERFIT_LIKELY": 40,
    "REFUTED_BY_WF": 4,                   # NEW
    ...
  },
  "wf_report_default": "reports/walk_forward_<strategy>_latest.md",  # NEW
  "strategies": [                          # Same array, but each EDGE_LIKELY_REAL row gets:
    {
      ...,
      "wf_verdict": "FAIL",                # NEW
      "wf_reasons": ["survival_rate=..."],  # NEW
      "wf_n_windows": 4,                   # NEW
      "wf_survival_rate": 0.5,             # NEW
      "wf_mean_oos_pf": 1.6033,            # NEW
      "wf_mean_oos_wr": 0.8,               # NEW
      "wf_report": "reports/walk_forward_<strategy>_latest.md"  # NEW
    }
  ]
}

Operator notes
--------------
- This is a one-call wrapper. The DSR layer is unchanged.
- The walk-forward tool already enforces n>=min-n per cell, so candidates with
  n<20 will get a soft "skipped" entry (not REFUTED_BY_WF).
- The script is read-only against the live MySQL DB (trading_picks). It does
  NOT mutate trading_picks; it only writes to anti_overfit_audit.json.
- For the 2026-06-13 cohort, 4/4 EDGE_LIKELY_REAL were REFUTED. Going forward,
  expect wf_false_positive_rate to stabilize at ~50-90% (i.e., DSR-only
  EDGE_LIKELY_REAL is high-precision noise).

CLAUDE.md Wire-Up Rule: this tool is the second gate in the audit pipeline.
The next step (operator approval required per CLAUDE.md) is to:
  1. Add a CI cron that runs this tool daily
  2. Surface the wf_false_positive_rate + per-strategy wf_verdict on /audit
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
SIDECAR = REPO_ROOT / "tools" / "anti_overfit_audit_sidecar.py"
WF_TOOL = REPO_ROOT / "tools" / "walk_forward_per_strategy.py"
DEFAULT_OUT = REPO_ROOT / "audit_dashboard" / "data" / "anti_overfit_audit.json"


def _run_sidecar(min_n: int, out_path: Path) -> dict:
    """Run the existing sidecar and return the parsed JSON payload."""
    cmd = [
        sys.executable, str(SIDECAR),
        "--min-n", str(min_n),
        "--out", str(out_path.relative_to(REPO_ROOT)),
    ]
    result = subprocess.run(
        cmd, cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print(f"Sidecar failed (rc={result.returncode}):", file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        raise SystemExit(1)
    return json.loads(out_path.read_text(encoding="utf-8"))


def _run_walk_forward(strategy: str,
                      in_window: int, out_window: int, step: int, min_n: int,
                      wf_json_path: Path) -> dict:
    """Run the walk-forward tool for one strategy; return the parsed cell dict.

    Returns a normalized dict with keys:
      verdict, reasons, n_windows, survival_rate, mean_oos_pf, mean_oos_wr,
      report_path
    """
    cmd = [
        sys.executable, str(WF_TOOL),
        "--strategy", strategy,
        "--in-window", str(in_window),
        "--out-window", str(out_window),
        "--step", str(step),
        "--min-n", str(min_n),
    ]
    # Forward DB credentials via the canonical resolver.
    # See tools/db_env.py: never inline a literal password here.
    try:
        from tools.db_env import get_stocks_creds  # type: ignore
        creds = get_stocks_creds()
    except Exception:
        creds = {}
    env = os.environ.copy()
    if creds:
        env.setdefault("DB_STOCKS_HOST", str(creds.get("host", "")))
        env.setdefault("DB_STOCKS_USER", str(creds.get("user", "")))
        env.setdefault("DB_STOCKS_PASSWORD", str(creds.get("password", "")))
        env.setdefault("DB_STOCKS_NAME", str(creds.get("database", "")))
    else:
        # Best-effort: let the child inherit only non-secret defaults.
        for k, default in (
            ("DB_STOCKS_HOST", "mysql.50webs.com"),
            ("DB_STOCKS_USER", "ejaguiar1_stocks"),
            ("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        ):
            env.setdefault(k, default)
        # Password stays unset — child must resolve via its own db_env.get_stocks_creds().
    result = subprocess.run(
        cmd, cwd=REPO_ROOT,
        env=env, capture_output=True, text=True, timeout=120,
    )
    # Parse the latest JSON the tool wrote
    if not wf_json_path.exists():
        return {
            "verdict": "WF_TOOL_FAIL",
            "reasons": [f"walk_forward_per_strategy_latest.json not written; rc={result.returncode}"],
            "n_windows": 0, "survival_rate": 0.0,
            "mean_oos_pf": None, "mean_oos_wr": None,
        }
    payload = json.loads(wf_json_path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    if not cells:
        return {
            "verdict": "NO_CELL",
            "reasons": ["no eligible cell (n<wf-min-n or no closed trades)"],
            "n_windows": 0, "survival_rate": 0.0,
            "mean_oos_pf": None, "mean_oos_wr": None,
        }
    # Strategy filter means at most 1 cell
    cell = cells[0]
    return {
        "verdict": cell.get("verdict", "UNKNOWN"),
        "reasons": cell.get("reasons", []),
        "n_windows": cell.get("n_windows", 0),
        "survival_rate": cell.get("survival_rate", 0.0),
        "mean_oos_pf": cell.get("mean_oos_pf"),
        "mean_oos_wr": cell.get("mean_oos_wr"),
        "n_total": cell.get("n_total", 0),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--min-n", type=int, default=10,
                   help="Minimum closed picks per strategy (passed to sidecar; default 10)")
    p.add_argument("--wf-in-window", type=int, default=14,
                   help="Walk-forward IS window in days (default 14)")
    p.add_argument("--wf-out-window", type=int, default=5,
                   help="Walk-forward OOS window in days (default 5)")
    p.add_argument("--wf-step", type=int, default=3,
                   help="Walk-forward step in days (default 3)")
    p.add_argument("--wf-min-n", type=int, default=20,
                   help="Walk-forward min-n per cell (default 20; below 20 → INSUFF_N)")
    p.add_argument("--no-walk-forward", action="store_true",
                   help="Skip walk-forward entirely; emit sidecar output unchanged")
    p.add_argument("--out", default=str(DEFAULT_OUT.relative_to(REPO_ROOT)),
                   help="Output JSON path (default: audit_dashboard/data/anti_overfit_audit.json)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the verdict diff (DSR-EDGE -> WF-REFUTE count) and don't write")
    args = p.parse_args()

    out_path = REPO_ROOT / args.out
    wf_json_path = REPO_ROOT / "audit_dashboard" / "data" / "walk_forward_per_strategy_latest.json"

    # Step 1: run the sidecar to get DSR verdicts
    print(f"[1/3] Running DSR sidecar (min_n={args.min_n}) ...", file=sys.stderr)
    payload = _run_sidecar(args.min_n, out_path)
    n_strategies = len(payload.get("strategies", []))
    dsr_edges = [s for s in payload.get("strategies", []) if s.get("verdict") == "EDGE_LIKELY_REAL"]
    print(f"      DSR verdicts: {payload.get('verdict_counts', {})}", file=sys.stderr)
    print(f"      EDGE_LIKELY_REAL candidates: {len(dsr_edges)}", file=sys.stderr)

    if args.no_walk_forward or not dsr_edges:
        if args.no_walk_forward:
            print(f"[2/3] --no-walk-forward set; skipping second-gate", file=sys.stderr)
        else:
            print(f"[2/3] No EDGE_LIKELY_REAL candidates; skipping second-gate", file=sys.stderr)
        payload["wf_gates_run"] = 0
        payload["wf_false_positive_rate"] = 0.0
        if args.dry_run:
            print(f"[3/3] dry-run: not writing {out_path}", file=sys.stderr)
            return
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[3/3] wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)
        return

    # Step 2: run walk-forward on each EDGE_LIKELY_REAL candidate
    print(f"[2/3] Running walk-forward on {len(dsr_edges)} EDGE_LIKELY_REAL candidates ...", file=sys.stderr)
    refuted = 0
    for i, strat in enumerate(dsr_edges, 1):
        name = strat["strategy"]
        n = strat.get("n", 0)
        print(f"      [{i}/{len(dsr_edges)}] {name}  (n={n}) ...", file=sys.stderr)
        if n < args.wf_min_n:
            strat["wf_verdict"] = "SKIPPED_LOW_N"
            strat["wf_reasons"] = [f"n={n} < wf_min_n={args.wf_min_n}"]
            strat["wf_n_windows"] = 0
            print(f"              SKIPPED_LOW_N (n={n} < {args.wf_min_n})", file=sys.stderr)
            continue
        wf = _run_walk_forward(name,
                               args.wf_in_window, args.wf_out_window, args.wf_step, args.wf_min_n,
                               wf_json_path)
        # Persist per-strategy JSON snapshot for the report trail
        snap_path = REPO_ROOT / "audit_dashboard" / "data" / f"walk_forward_{name}_with_wf.json"
        snap_path.write_text(json.dumps(wf, indent=2), encoding="utf-8")
        # Attach to the strategy row
        strat["wf_verdict"] = wf["verdict"]
        strat["wf_reasons"] = wf["reasons"]
        strat["wf_n_windows"] = wf["n_windows"]
        strat["wf_survival_rate"] = wf["survival_rate"]
        strat["wf_mean_oos_pf"] = wf["mean_oos_pf"]
        strat["wf_mean_oos_wr"] = wf["mean_oos_wr"]
        strat["wf_report"] = f"reports/walk_forward_{name}_latest.md"
        # Demote
        if wf["verdict"] in ("FAIL", "INSUFF_N", "WF_TOOL_FAIL"):
            old_verdict = strat["verdict"]
            strat["verdict"] = "REFUTED_BY_WF"
            strat["previous_verdict"] = old_verdict
            refuted += 1
            print(f"              REFUTED_BY_WF ({wf['verdict']}: {wf['reasons']})", file=sys.stderr)
        else:
            print(f"              PASS ({wf['verdict']})", file=sys.stderr)

    # Step 3: aggregate counts + write
    payload["wf_gates_run"] = len(dsr_edges)
    payload["wf_false_positive_rate"] = round(refuted / max(1, len(dsr_edges)), 4)
    # Re-tally verdict_counts
    new_counts: dict[str, int] = {}
    for s in payload.get("strategies", []):
        v = s.get("verdict", "UNKNOWN")
        new_counts[v] = new_counts.get(v, 0) + 1
    payload["verdict_counts"] = new_counts
    # Annotate validator field
    payload["validator"] = (
        "alpha_engine.anti_overfit_validator (DSR Lopez de Prado AFML 14.5; PBO "
        "Bailey-Borwein-Lopez de Prado-Zhu 2017; Reality Check White 2000) + "
        "tools/walk_forward_per_strategy.py (rolling 14d IS / 5d OOS / 3d step)"
    )
    payload["wf_method"] = {
        "in_window_days": args.wf_in_window,
        "out_window_days": args.wf_out_window,
        "step_days": args.wf_step,
        "min_n_per_cell": args.wf_min_n,
        "gates_required": [
            "survival_rate >= 0.60",
            "mean_oos_wr >= 0.50",
            "n_windows >= 3",
        ],
        "false_positive_history": {
            "2026-06-13": "4/4 DSR-EDGE-LIKELY-REAL REFUTED by walk-forward",
        },
    }

    print(f"[3/3] Verdict diff: DSR-EDGE={len(dsr_edges)} -> REFUTED_BY_WF={refuted} "
          f"(false_positive_rate={payload['wf_false_positive_rate']})", file=sys.stderr)
    if args.dry_run:
        print(f"      dry-run: not writing {out_path}", file=sys.stderr)
        return
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"      wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
