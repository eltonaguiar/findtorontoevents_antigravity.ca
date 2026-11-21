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
    align_returns_by_period,
    cpcv_pbo,
    deflated_sharpe,
    reality_check_pvalue,
)
from alpha_engine.pf_basis import format_pf as _pf_label  # noqa: E402

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


def fetch_strategy_series(cur, min_n: int) -> dict:
    """Return {strategy: [(closed_at, pnl_pct), ...]} for n>=min_n strategies.

    ``closed_at`` is the EXIT timestamp and it is the only honest key for putting
    two strategies on the same clock: the old PBO path stacked each strategy's
    trailing picks and compared different calendar windows (2026-11-20).
    """
    cur.execute(f"""
        SELECT strategy, pnl_pct, closed_at
        FROM trading_picks
        WHERE status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL
          AND strategy <> ''
        ORDER BY strategy, closed_at
    """)
    by_strat: dict[str, list[tuple[object, float]]] = {}
    for row in cur.fetchall():
        s = row["strategy"]
        try:
            pnl = float(row["pnl_pct"])
        except (TypeError, ValueError):
            continue
        by_strat.setdefault(s, []).append((row.get("closed_at"), pnl))
    # Filter to min_n
    return {s: r for s, r in by_strat.items() if len(r) >= min_n}


def fetch_strategy_returns(cur, min_n: int) -> dict:
    """Return {strategy: [pnl_pct, ...]} for strategies with n>=min_n closed picks.

    Kept for callers that only want the return column; timestamps live in
    :func:`fetch_strategy_series` and are required for any aligned PBO.
    """
    return {s: [v for _, v in rows]
            for s, rows in fetch_strategy_series(cur, min_n).items()}


def publication_label(dsr, threshold: float = 0.95) -> tuple[str, str]:
    """(label, reason) for one DSR. A label, never a filter.

    74 of 80 strategies sit below 0.95, and hiding them would make the gate's own
    output unauditable. Demotion is a publication label: the row stays, with its n
    (2026-11-20).
    """
    if dsr is None:
        return "UNRATED", "DSR unavailable"
    try:
        value = float(dsr)
    except (TypeError, ValueError):
        return "UNRATED", "DSR not numeric"
    if value >= threshold:
        return "PUBLISHABLE", "DSR %.4f >= %.2f" % (value, threshold)
    return "PROBATION", "DSR %.4f < %.2f" % (value, threshold)


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
        # A per-strategy PF is compared across strategies, so it carries its own n.
        "pf_n": n,
        "pf_basis": "gross",
        "pf_label": _pf_label(pf, n, basis="gross"),
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

    # Publication label, computed here so a regeneration never loses the demotion.
    label, reason = publication_label(out.get("dsr"))
    out["publication_label"] = label
    out["publication_reason"] = reason

    return out


def gate_failures(payload: dict, dsr_threshold: float = 0.95,
                  min_n: int = 0) -> list[str]:
    """Strategies in a written audit payload whose DSR fails the threshold.

    Pure function so CI logic is testable without a database: the gate reads the
    artifact the sidecar just wrote and judges it.
    """
    bad: list[str] = []
    for row in payload.get("strategies") or []:
        if min_n and int(row.get("n") or 0) < min_n:
            continue
        name = row.get("strategy", "?")
        dsr = row.get("dsr")
        if dsr is None:
            bad.append(f"{name}: DSR unavailable ({row.get('dsr_error') or 'nan'})")
        elif float(dsr) < dsr_threshold:
            bad.append(f"{name}: DSR {float(dsr):.4f} < {dsr_threshold:.2f}")
    return bad


def absolute_state(payload: dict, dsr_threshold: float = 0.95) -> str:
    """The standing count, printed on every run whatever the verdict is.

    The gate below judges *change*, so the reader still needs the absolute
    number to know what the change was measured from.
    """
    rows = payload.get("strategies") or []
    pass_count = payload.get("dsr_pass_count")
    scored = payload.get("dsr_scored_count")
    if not isinstance(pass_count, int) or not isinstance(scored, int) or scored <= 0:
        return (f"no pass counts in the payload ({len(rows)} strategy rows), so the "
                f"share clearing DSR {dsr_threshold:.2f} is unknown")
    below = max(scored - pass_count, 0)
    return (f"{pass_count}/{scored} strategies clear DSR {dsr_threshold:.2f} "
            f"({100.0 * pass_count / scored:.1f}%), {below} below the floor")


def read_previous_audit(path: Path) -> dict:
    """The baseline, taken from the payload this run is about to overwrite.

    In CI that file is the last committed audit (the checkout is shallow, so git
    history is not available). Missing or unreadable means "no baseline", which
    passes: a first run has nothing to regress from.
    """
    try:
        old = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(old.get("dsr_pass_count"), int):
        return {}
    return {
        "generated_at": old.get("generated_at"),
        "pass_count": old.get("dsr_pass_count"),
        "scored_count": old.get("dsr_scored_count"),
        "pass_rate": old.get("dsr_pass_rate"),
    }


def regression_reasons(payload: dict, tolerance_pp: float = 1.0,
                       coverage_tolerance: float = 0.25) -> tuple[list[str], str]:
    """Why this audit is worse than the previous one, plus what it was compared with.

    The absolute state is deliberately NOT a failure. 6 of 80 strategies clearing
    0.95 is the long-standing reality of this book; a gate that fails on it fails
    every hour, which is indistinguishable from a gate that is broken. What this
    returns non-empty for is what a gate is for: the number got worse.
    """
    prev = payload.get("dsr_prev_audit") or {}
    pass_count = payload.get("dsr_pass_count")
    scored = payload.get("dsr_scored_count")
    if not isinstance(pass_count, int) or not isinstance(scored, int) or scored <= 0:
        return (["this audit has no usable pass counts (dsr_pass_count / "
                 "dsr_scored_count), so there is nothing to judge"], "no baseline")
    prev_count = prev.get("pass_count")
    prev_scored = prev.get("scored_count")
    if not isinstance(prev_count, int) or not isinstance(prev_scored, int) or prev_scored <= 0:
        return ([], "no previous audit recorded in this payload (first run), so nothing to regress from")
    rate = 100.0 * pass_count / scored
    prev_rate = 100.0 * prev_count / prev_scored
    drop = prev_rate - rate
    reasons: list[str] = []
    if drop > tolerance_pp:
        reasons.append(
            f"pass rate fell {prev_rate:.1f}% ({prev_count}/{prev_scored}) -> "
            f"{rate:.1f}% ({pass_count}/{scored}), -{drop:.1f}pp "
            f"(tolerance {tolerance_pp:.1f}pp)")
    if scored < prev_scored * (1.0 - coverage_tolerance):
        reasons.append(
            f"scored population shrank {prev_scored} -> {scored} "
            f"(tolerance {coverage_tolerance:.0%})")
    note = "" if reasons else f"previous audit {prev_count}/{prev_scored} ({prev_rate:.1f}%)"
    return reasons, note


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-n", type=int, default=10,
                   help="Minimum closed picks per strategy (default 10)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print results, don't write JSON")
    p.add_argument("--out", default="audit_dashboard/data/anti_overfit_audit.json",
                   help="Output JSON path (relative to repo root)")
    p.add_argument("--check-only", action="store_true",
                   help="do not touch the DB; judge the existing payload and exit 2 on failure")
    p.add_argument("--in", dest="in_path", default=None,
                   help="payload to read with --check-only (defaults to --out)")
    p.add_argument("--gate", action="store_true",
                   help="exit 2 when any strategy's DSR is below --dsr-threshold")
    p.add_argument("--dsr-threshold", type=float, default=0.95,
                   help="DSR floor for --gate (default 0.95)")
    p.add_argument("--regression-tolerance", type=float, default=1.0,
                   help="percentage points the pass rate may fall before --gate "
                        "fails (default 1.0)")
    p.add_argument("--coverage-tolerance", type=float, default=0.25,
                   help="fraction the scored population may shrink before --gate "
                        "fails (default 0.25)")
    args = p.parse_args()

    if args.check_only:
        src = Path(args.in_path) if args.in_path else ROOT / args.out
        if not src.exists():
            print(f"GATE ERROR: payload not found at {src}", file=sys.stderr)
            return 3
        payload = json.loads(src.read_text(encoding="utf-8"))
        state = absolute_state(payload, args.dsr_threshold)
        reasons, note = regression_reasons(payload, args.regression_tolerance,
                                           args.coverage_tolerance)
        if not args.gate:
            if reasons:
                print(f"# {state}; REGRESSION vs the previous audit: {reasons[0]} "
                      f"(advisory: pass --gate to fail)", file=sys.stderr)
            else:
                print(f"# {state}; {note} (advisory: pass --gate to fail)", file=sys.stderr)
            return 0
        if reasons:
            print("ANTI-OVERFIT GATE: FAIL -- regression vs the previous audit",
                  file=sys.stderr)
            print(f"  now: {state}", file=sys.stderr)
            for reason in reasons:
                print(f"  - {reason}", file=sys.stderr)
            return 2
        print(f"ANTI-OVERFIT GATE: PASS -- {state}; {note}", file=sys.stderr)
        return 0
    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    print(f"# Anti-overfit sidecar audit — n>={args.min_n}", file=sys.stderr)

    strat_series = fetch_strategy_series(cur, args.min_n)
    strat_returns = {s: [v for _, v in rows] for s, rows in strat_series.items()}
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
    M = None
    periods: list = []
    align_info: dict = {}
    if len(audited_strats) >= 2:
        # Row-align by EXIT TIMESTAMP (2026-11-20). The old code stacked each
        # strategy's trailing min_len picks onto the same rows, so columns
        # compared different calendar windows and the PBO logit measured the
        # calendar rather than the selection process.
        M, periods, align_info = align_returns_by_period(
            strat_series, min_obs=min(8, args.min_n), min_rows=16
        )
        portfolio_diagnostics["alignment"] = align_info
    if M is not None:
        names = align_info.get("strategies") or audited_strats
        n_folds = min(10, max(2, M.shape[0] // 4))
        try:
            pbo = cpcv_pbo(M, n_folds=n_folds, n_test_groups=2,
                           period_index=periods)
            portfolio_diagnostics["pbo"] = {
                "value": round(float(pbo), 4),
                "n_candidates": int(M.shape[1]),
                "n_observations": int(M.shape[0]),
                "n_folds": n_folds,
                "period": align_info.get("period"),
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
                "best_strategy": names[best_idx],
                "B_bootstraps": 1000,
                "block_size": 10,
                "interpretation": "H0: best-strategy mean return <= 0. p<0.05 rejects H0.",
            }
        except Exception as e:
            portfolio_diagnostics["reality_check"] = {"error": str(e)[:200]}
    else:
        portfolio_diagnostics.setdefault(
            "note",
            "PBO/RC skipped: " + str(
                align_info.get("note")
                or "fewer than 2 strategies with timestamped closed picks"
            ),
        )

    dsr_vals = [float(r["dsr"]) for r in rows if r.get("dsr") is not None]
    pass_count = sum(1 for v in dsr_vals if v >= 0.95)
    label_counts: dict[str, int] = {}
    for r in rows:
        lab = r.get("publication_label", "UNRATED")
        label_counts[lab] = label_counts.get(lab, 0) + 1
    # Label the rows HERE, once, after every row source has run. A label added
    # only at construction is lost the moment anything appends a row by another
    # path -- measured 2026-11-20, when a refresh left 4 of 81 rows unlabelled
    # while the payload still claimed 74 PROBATION.
    pub_counts: dict[str, int] = {}
    for _row in rows:
        _label, _reason = publication_label(_row.get("dsr"))
        _row["publication_label"] = _label
        _row["publication_reason"] = _reason
        _row["publication_dsr_threshold"] = 0.95
        pub_counts[_label] = pub_counts.get(_label, 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_strategies_audited": n_trials,
        "min_n_threshold": args.min_n,
        "verdict_counts": by_verdict,
        "dsr_threshold_real_edge": 0.95,
        "dsr_threshold_undetermined": 0.50,
        # A pass count without a denominator is not a measurement (2026-11-20).
        "dsr_pass_count": pass_count,
        "dsr_scored_count": len(dsr_vals),
        "dsr_pass_rate": round(pass_count / len(dsr_vals), 4) if dsr_vals else None,
        "publication_label_counts": label_counts,
        "publication_label_rule": (
            "label only -- a PROBATION strategy keeps its row and its n in this "
            "payload; nothing is deleted or filtered, so the demotion stays auditable"
        ),
        "source": "ejaguiar1_stocks::trading_picks closed picks",
        "validator": "alpha_engine.anti_overfit_validator (DSR Lopez de Prado AFML 14.5; PBO Bailey-Borwein-Lopez de Prado-Zhu 2017; Reality Check White 2000)",
        "portfolio_diagnostics": portfolio_diagnostics,
        "strategies": rows,
        "publication_label_counts": pub_counts,
        "publication_label_rule": (
            "label only -- a PROBATION strategy keeps its row and its n in this "
            "payload; nothing is deleted or filtered, so the demotion stays "
            "auditable"
        ),
        "publication_labelled_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
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
        return 0

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Read the baseline BEFORE overwriting: this file is the previous audit.
    payload["dsr_prev_audit"] = read_previous_audit(out_path)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)

    if args.gate:
        state = absolute_state(payload, args.dsr_threshold)
        reasons, note = regression_reasons(payload, args.regression_tolerance,
                                           args.coverage_tolerance)
        if reasons:
            print("ANTI-OVERFIT GATE: FAIL -- regression vs the previous audit",
                  file=sys.stderr)
            print(f"  now: {state}", file=sys.stderr)
            for reason in reasons:
                print(f"  - {reason}", file=sys.stderr)
            return 2
        print(f"ANTI-OVERFIT GATE: PASS -- {state}; {note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
