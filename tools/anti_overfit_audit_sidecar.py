#!/usr/bin/env python3
"""Anti-overfit audit sidecar — per-strategy DSR/Sharpe writer.

Wires `alpha_engine/anti_overfit_validator.py` (orphan since 2026-05-02 per
Kimi audit) into a production-callable sidecar that:

  1. Pulls per-strategy closed-pick returns from ejaguiar1_stocks.trading_picks
  2. Computes Sharpe + Deflated Sharpe Ratio per strategy with n >= MIN_N
  3. Writes audit_dashboard/data/anti_overfit_audit.json with DSR + verdict

CLAUDE.md Wire-Up Rule: this is the "opt-in sidecar with explicit Wiring
Plan" path. The follow-up PR consumes anti_overfit_audit.json in
audit_trail/dashboard_generator.py to surface DSR alongside each strategy
card on /audit. No production picks are gated on this output yet — sidecar
emits ADVISORY tags only.

Lopez de Prado AFML thresholds (per Kimi industry_standards_research.md):
  DSR >= 0.95  -> headline Sharpe survives multiple-testing correction
  DSR <  0.95  -> probably noise; demote or quarantine
  DSR <  0.50  -> reject; almost certainly overfit

Usage:
    python tools/anti_overfit_audit_sidecar.py            # full audit
    python tools/anti_overfit_audit_sidecar.py --min-n 20 # raise n floor
    python tools/anti_overfit_audit_sidecar.py --dry-run  # don't write

Env: DB_STOCKS_HOST / DB_STOCKS_USER / DB_STOCKS_PASSWORD / DB_STOCKS_NAME
     (default mysql.50webs.com / ejaguiar1_stocks / stocks / ejaguiar1_stocks)

SUPREME EDGE P1 wire-up — 2026-05-11.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy not installed", file=sys.stderr)
    sys.exit(2)

# Validator under audit
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from alpha_engine.anti_overfit_validator import (  # noqa: E402
    cpcv_pbo,
    deflated_sharpe,
    reality_check_pvalue,
)

# Effective-N reporter (master-plan Action #2 — autocorrelation correction)
try:
    sys.path.insert(0, str(ROOT / "tools"))
    from effective_n_reporter import compute_n_eff as _compute_n_eff  # noqa: E402
    _N_EFF_AVAILABLE = True
except Exception:
    _compute_n_eff = None  # type: ignore
    _N_EFF_AVAILABLE = False


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=120,
    )


def fetch_strategy_returns(cur, min_n: int) -> dict:
    """Return {strategy: [pnl_pct, ...]} for strategies with n>=min_n closed picks."""
    cur.execute(f"""
        SELECT strategy, pnl_pct
        FROM trading_picks
        WHERE status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL
          AND strategy <> ''
        ORDER BY strategy
    """)
    by_strat: dict[str, list[float]] = {}
    for row in cur.fetchall():
        s = row["strategy"]
        try:
            pnl = float(row["pnl_pct"])
        except (TypeError, ValueError):
            continue
        by_strat.setdefault(s, []).append(pnl)
    # Filter to min_n
    return {s: r for s, r in by_strat.items() if len(r) >= min_n}


def audit_strategy(name: str, returns: list[float], n_trials: int) -> dict:
    arr = np.asarray(returns, dtype=np.float64)
    n = arr.size
    mu = float(arr.mean())
    sd = float(arr.std(ddof=1)) if n > 1 else 0.0
    sharpe = (mu / sd) if sd > 1e-12 else 0.0
    wins = int((arr > 0).sum())
    wr = wins * 100.0 / n if n else 0.0
    pf = (arr[arr > 0].sum() / abs(arr[arr < 0].sum())) if (arr < 0).sum() > 0 and arr[arr < 0].sum() != 0 else None

    out = {
        "strategy": name,
        "n": n,
        "wr_pct": round(wr, 2),
        "pf": round(float(pf), 3) if pf is not None else None,
        "avg_pnl_pct": round(mu, 4),
        "std_pnl_pct": round(sd, 4),
        "sharpe": round(sharpe, 4),
    }

    if _N_EFF_AVAILABLE and n >= 2:
        try:
            n_eff_result = _compute_n_eff(list(returns))
            out["n_eff"] = n_eff_result["n_eff"]
            out["deflation_pct"] = n_eff_result["deflation_pct"]
            if n_eff_result["deflation_pct"] > 30:
                out["autocorr_flag"] = "HIGH_AUTOCORR"
            elif n_eff_result["deflation_pct"] > 15:
                out["autocorr_flag"] = "MODERATE_AUTOCORR"
            else:
                out["autocorr_flag"] = "OK"
        except Exception as exc:
            out["n_eff"] = None
            out["autocorr_flag"] = f"N_EFF_ERR:{str(exc)[:60]}"

    try:
        dsr = deflated_sharpe(sharpe, n_trials=n_trials, returns_array=arr)
        out["dsr"] = round(dsr, 4)
        if dsr >= 0.95:
            verdict = "EDGE_LIKELY_REAL"
        elif dsr >= 0.50:
            verdict = "UNDETERMINED"
        else:
            verdict = "OVERFIT_LIKELY"
        out["verdict"] = verdict
    except Exception as exc:
        out["dsr"] = None
        out["verdict"] = "DSR_ERR"
        out["dsr_error"] = str(exc)[:120]

    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-n", type=int, default=10,
                   help="Minimum closed picks per strategy (default 10)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/anti_overfit_audit.json",
                   help="Output JSON path (relative to repo root)")
    args = p.parse_args()

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    print(f"# Anti-overfit sidecar audit — n>={args.min_n}", file=sys.stderr)

    strat_returns = fetch_strategy_returns(cur, args.min_n)
    cur.close()
    conn.close()

    n_trials = len(strat_returns)
    print(f"# {n_trials} strategies meet n>={args.min_n} closed picks", file=sys.stderr)

    rows = []
    for name in sorted(strat_returns.keys()):
        try:
            r = audit_strategy(name, strat_returns[name], n_trials)
            rows.append(r)
        except Exception as e:
            print(f"  audit {name}: {e}", file=sys.stderr)

    # Sort: real-edge first, then undetermined, then overfit
    verdict_rank = {"EDGE_LIKELY_REAL": 0, "UNDETERMINED": 1,
                    "OVERFIT_LIKELY": 2, "DSR_ERR": 3}
    rows.sort(key=lambda r: (verdict_rank.get(r.get("verdict", "DSR_ERR"), 4),
                              -(r.get("dsr") or 0)))

    by_verdict: dict[str, int] = {}
    for r in rows:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1

    # Portfolio-level PBO + Reality Check (selection-process diagnostics —
    # one number for the whole strategy universe, NOT per-strategy).
    portfolio_diagnostics: dict = {}
    audited_strats = sorted(strat_returns.keys())
    if len(audited_strats) >= 2:
        # Align returns: pad each strategy's series to common length M (the
        # min across all strategies). PBO requires equal-length columns.
        min_len = min(len(strat_returns[s]) for s in audited_strats)
        if min_len >= 8:
            # Use trailing min_len entries per strategy. This is a coarse
            # alignment — chronological ordering is best-effort given that
            # closed_picks rows lack a guaranteed per-strategy index.
            cols = []
            for s in audited_strats:
                cols.append(np.asarray(strat_returns[s][-min_len:],
                                       dtype=np.float64))
            M = np.column_stack(cols)
            n_folds = min(10, max(2, min_len // 4))
            try:
                pbo = cpcv_pbo(M, n_folds=n_folds, n_test_groups=2)
                portfolio_diagnostics["pbo"] = {
                    "value": round(float(pbo), 4),
                    "n_candidates": int(M.shape[1]),
                    "n_observations": int(M.shape[0]),
                    "n_folds": n_folds,
                    "threshold_overfit": 0.5,
                    "verdict": "OVERFIT_LIKELY" if pbo >= 0.5 else "SELECTION_EDGE_SURVIVES",
                    "interpretation": (
                        "Probability the IS-best strategy underperforms OOS median. "
                        ">= 0.5 means selection is indistinguishable from chance."
                    ),
                }
            except Exception as e:
                portfolio_diagnostics["pbo"] = {"error": str(e)[:200]}
            # White's Reality Check on the IS-best strategy: H0 = no
            # outperformance vs zero-return benchmark.
            try:
                best_idx = int(np.argmax(M.mean(axis=0) / np.where(M.std(axis=0, ddof=1) < 1e-12, 1e-12, M.std(axis=0, ddof=1))))
                rc_p = reality_check_pvalue(M[:, best_idx], benchmark=0.0,
                                             B=1000, block_size=10)
                portfolio_diagnostics["reality_check"] = {
                    "p_value": round(float(rc_p), 4),
                    "best_strategy": audited_strats[best_idx],
                    "B_bootstraps": 1000,
                    "block_size": 10,
                    "interpretation": "H0: best-strategy mean return <= 0. p<0.05 rejects H0.",
                }
            except Exception as e:
                portfolio_diagnostics["reality_check"] = {"error": str(e)[:200]}
        else:
            portfolio_diagnostics["note"] = (
                f"min_strategy_n={min_len} below floor 8; PBO/RC skipped"
            )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_strategies_audited": n_trials,
        "min_n_threshold": args.min_n,
        "verdict_counts": by_verdict,
        "dsr_threshold_real_edge": 0.95,
        "dsr_threshold_undetermined": 0.50,
        "source": "ejaguiar1_stocks::trading_picks closed picks",
        "validator": "alpha_engine.anti_overfit_validator (DSR Lopez de Prado AFML 14.5; PBO Bailey-Borwein-Lopez de Prado-Zhu 2017; Reality Check White 2000)",
        "portfolio_diagnostics": portfolio_diagnostics,
        "strategies": rows,
    }

    summary_lines = []
    summary_lines.append(f"# Anti-overfit audit summary @ {payload['generated_at']}")
    summary_lines.append(f"# n_trials = {n_trials} strategies (n>={args.min_n} closed picks each)")
    for v, c in sorted(by_verdict.items()):
        summary_lines.append(f"#   {v:18} {c}")
    if "pbo" in portfolio_diagnostics and "value" in portfolio_diagnostics["pbo"]:
        summary_lines.append(
            f"# PBO = {portfolio_diagnostics['pbo']['value']:.4f}  "
            f"({portfolio_diagnostics['pbo']['verdict']})"
        )
    if "reality_check" in portfolio_diagnostics and "p_value" in portfolio_diagnostics["reality_check"]:
        rc = portfolio_diagnostics["reality_check"]
        summary_lines.append(
            f"# Reality Check p={rc['p_value']:.4f}  best={rc['best_strategy'][:30]}"
        )
    print("\n".join(summary_lines), file=sys.stderr)

    # Top-5 real-edge candidates
    real_edges = [r for r in rows if r.get("verdict") == "EDGE_LIKELY_REAL"]
    if real_edges:
        print("\n# Top-5 EDGE_LIKELY_REAL:", file=sys.stderr)
        for r in real_edges[:5]:
            print(f"  {r['strategy'][:40]:40} n={r['n']:5}  WR={r['wr_pct']:5.1f}%  "
                  f"Sharpe={r['sharpe']:+.3f}  DSR={r['dsr']:.4f}", file=sys.stderr)
    overfit = [r for r in rows if r.get("verdict") == "OVERFIT_LIKELY"]
    if overfit:
        print(f"\n# Top-5 OVERFIT_LIKELY (n={len(overfit)} total):", file=sys.stderr)
        for r in overfit[:5]:
            print(f"  {r['strategy'][:40]:40} n={r['n']:5}  WR={r['wr_pct']:5.1f}%  "
                  f"Sharpe={r['sharpe']:+.3f}  DSR={r['dsr']:.4f}", file=sys.stderr)

    if args.dry_run:
        print("\n# dry-run: not writing JSON", file=sys.stderr)
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
