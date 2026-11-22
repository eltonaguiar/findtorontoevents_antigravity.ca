#!/usr/bin/env python3
"""Harness certification — has any piece of measured evidence silently changed?

WHY THIS EXISTS
---------------
This programme has produced ~8 measurement harnesses whose JSON artifacts are
cited in reports and on the bus. Nothing checked that those numbers still hold.
A number quoted in a doc can drift out of agreement with the artifact that
produced it — because a harness changed, because cached input data refreshed,
because someone "fixed" a cost constant — and every downstream claim then rests
on a figure nobody re-verified.

Certification answers one question per metric: **is the artifact still producing
the number we wrote down?**

DETERMINISTIC vs LIVE — the distinction that makes this useful
  deterministic : reads cached bars/ledgers. Same input => same output. Any drift
                  is a REGRESSION and fails the run.
  live          : reads order books or fetches fresh bars by design. Drift is the
                  POINT of these tools, so it is reported as informational and
                  never fails the run. Treating live drift as failure would train
                  everyone to ignore the certifier.
  external      : depends on a file another agent owns. Reported, never failed —
                  I do not get to declare someone else's artifact broken.

WHY IT DOES NOT RE-RUN HARNESSES BY DEFAULT
  Certification is meant to run after every change, so it must be fast and
  side-effect free. Re-executing the pod backtest takes minutes and would make
  the check something people skip. `--rerun` executes the harness commands first
  when you actually want fresh numbers.

Usage:
  python3 tools/harness_certification.py                  # certify vs baseline
  python3 tools/harness_certification.py --rerun          # re-run harnesses first
  python3 tools/harness_certification.py --rerun --only pod,regime
  python3 tools/harness_certification.py --accept         # promote current -> baseline
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "reports" / "harness_certification"
BASELINE = OUTDIR / "baseline.json"
LATEST = OUTDIR / "latest.json"

# Relative tolerance for "unchanged". Float artifacts round differently between
# runs; anything beyond 0.5% on a headline metric is a real change, not noise.
TOL = 0.005


# --------------------------------------------------------------------------- #
# extractors: artifact JSON -> {metric_name: float|int}                      #
# --------------------------------------------------------------------------- #
def ex_cost_horizon(d: dict) -> dict:
    """Median gross edge per horizon — ALL cells, never a filtered subset.

    REGRESSION GUARD. The first version of this ladder (PART15, 2026-11-22) was
    published as "median gross edge per trade across all positive cells", with n
    = 5/7/8/12 of 12. That is a median taken AFTER dropping every negative
    observation - selection on the dependent variable. It guarantees a positive
    number by construction and overstated the ladder roughly 2x:

        horizon   published (positive-only)   all cells (honest)
        15m              +2.48 bp                 -0.566 bp
        1h               +7.49 bp                 +3.847 bp
        4h              +21.16 bp                 +8.640 bp
        1D              +24.21 bp                +24.206 bp

    1D happened to agree because all 12 of its cells were positive, which is
    exactly why the error survived a spot check: the one horizon anyone would
    sanity-check matched.

    This extractor therefore reports the ALL-CELL median only, plus the counts so
    a reader can see what was included. There is deliberately no
    `median_gross_bp_positive_cells` metric here - a certified metric that can
    only be computed by discarding bad observations is a metric that will be
    misquoted.
    """
    by_h: dict[str, list[float]] = {}
    for r in d.get("rows", []):
        if r.get("status") != "OK" or r.get("gross_bp") is None:
            continue
        by_h.setdefault(r["horizon"], []).append(float(r["gross_bp"]))
    out: dict = {}
    order = ["15m", "1h", "4h", "1D"]
    meds = []
    for h in order:
        v = by_h.get(h) or []
        if not v:
            continue
        out[f"median_gross_bp_{h}"] = statistics.median(v)
        out[f"n_all_cells_{h}"] = len(v)
        out[f"n_positive_cells_{h}"] = sum(1 for x in v if x > 0)
        meds.append(statistics.median(v))
    out["n_ok_rows"] = sum(len(v) for v in by_h.values())
    # The claim that matters is a statement about SHAPE, not about a lucky cell,
    # so certify the shape directly rather than leaving it to a reader's eye.
    out["monotone_increasing_all_cells"] = int(
        all(b >= a for a, b in zip(meds, meds[1:])) and len(meds) == len(order)
    )
    return out


def ex_pod(d: dict) -> dict:
    """POD-EQUITY-BREAKOUT, ALL-history window: the refuted claim's numbers."""
    ws = d.get("windows") or []
    if not isinstance(ws, list) or not ws:
        return {}
    w = next((x for x in ws if "ALL" in str(x.get("label", "")).upper()), ws[0])
    return {
        "n": w.get("n"), "net_pct": w.get("net_pct"),
        "gross_pct": w.get("gross_pct"), "pf": w.get("pf"),
        "wr_pct": w.get("wr_pct"), "t": w.get("t"),
    }


def ex_regime(d: dict) -> dict:
    """Breakout regime test: pre/post-2010 split on the calendar."""
    out = {}
    pre_pos = 0
    for m in d.get("markets", []):
        sym = m.get("symbol")
        pre, post = m.get("pre_2010") or {}, m.get("post_2010") or {}
        if sym == "^GSPC":
            out["spy_pre_mean_bp"] = pre.get("mean_bp")
            out["spy_pre_t"] = pre.get("t")
            out["spy_post_mean_bp"] = post.get("mean_bp")
            out["spy_post_t"] = post.get("t")
        if (pre.get("mean_bp") or 0) > 0:
            pre_pos += 1
    out["markets_pre2010_positive"] = pre_pos
    out["markets_total"] = len(d.get("markets", []))
    return out


def ex_funding(d: dict) -> dict:
    """Funding carry: the reproducible H-228 measurement."""
    return {
        "gross_mean_bp_day": d.get("gross_mean_bp_day"),
        "gross_ann_pct": d.get("gross_ann_pct"),
        "carry_sharpe": d.get("carry_sharpe"),
        "pct_days_negative_funding": d.get("pct_days_negative_funding"),
        "max_dd_bp": d.get("max_dd_bp"),
    }


def ex_h119(d: dict) -> dict:
    """H-119 ledger audit: both price conventions, so neither is cherry-picked."""
    out = {}
    clean = d.get("acceptance_clean_rows") or {}
    for key, tag in (("clean_resolver_exit_px", "resolver"),
                     ("clean_exit_px", "exit")):
        e = clean.get(key) or {}
        if e:
            out[f"n_{tag}"] = e.get("n")
            out[f"net_pf_{tag}"] = e.get("net_pf")
            out[f"ci_lb_{tag}"] = e.get("ci_lb")
    prov = d.get("provenance") or {}
    out["rows_created_after_close"] = prov.get("rows_created_after_close")
    out["n_rows"] = d.get("n_rows")
    return out


def ex_carry_cost(d: dict) -> dict:
    return {
        "median_round_trip_bp": d.get("median_round_trip_bp"),
        "worst_round_trip_bp": d.get("worst_round_trip_bp"),
        "fee_component_bp": d.get("fee_component_bp"),
    }


# name, artifact, extractor, class, rerun command
MANIFEST = [
    ("cost_horizon", "reports/cost_horizon/cost_horizon_ladder.json",
     ex_cost_horizon, "deterministic", ["tools/cost_horizon_ladder.py"]),
    ("pod", "reports/pod_equity_breakout/pod_equity_breakout_backtest.json",
     ex_pod, "deterministic", ["tools/pod_equity_breakout_backtest.py"]),
    ("regime", "reports/breakout_regime/breakout_regime_test.json",
     ex_regime, "deterministic", ["tools/breakout_regime_test.py", "--cost", "4"]),
    ("funding", "reports/funding_carry/funding_carry_measure.json",
     ex_funding, "deterministic", ["tools/funding_carry_measure.py"]),
    ("h119", "reports/h119_ledger_audit/h119_ledger_audit.json",
     ex_h119, "deterministic", ["tools/h119_ledger_audit.py"]),
    ("carry_cost", "reports/carry_execution/carry_execution_cost.json",
     ex_carry_cost, "live", ["tools/carry_execution_cost.py"]),
]


def collect() -> dict:
    out: dict = {}
    for name, rel, fn, cls, _cmd in MANIFEST:
        path = ROOT / rel
        if not path.exists():
            out[name] = {"_class": cls, "_error": f"artifact missing: {rel}"}
            continue
        try:
            data = json.loads(path.read_text())
            metrics = fn(data)
            metrics["_class"] = cls
            metrics["_artifact"] = rel
            out[name] = metrics
        except Exception as exc:  # noqa: BLE001 - a broken artifact is a finding
            out[name] = {"_class": cls, "_error": f"{type(exc).__name__}: {exc}"}
    return out


def close(a, b) -> bool:
    if a is None or b is None:
        return a is b
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if fa == fb:
        return True
    scale = max(abs(fa), abs(fb), 1e-12)
    return abs(fa - fb) / scale <= TOL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated harness names")
    ap.add_argument("--accept", action="store_true")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    if args.rerun:
        for name, _rel, _fn, _cls, cmd in MANIFEST:
            if only and name not in only:
                continue
            print(f"[RERUN] {name}: {' '.join(cmd)}")
            try:
                r = subprocess.run([sys.executable] + cmd, cwd=ROOT,
                                   capture_output=True, text=True, timeout=1800)
                if r.returncode != 0:
                    print(f"  exit {r.returncode} — artifact may be stale")
                    tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
                    for ln in tail:
                        print(f"  | {ln}")
            except subprocess.TimeoutExpired:
                print("  TIMEOUT — leaving existing artifact in place")

    cur = collect()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LATEST.write_text(json.dumps({"certified_utc": stamp, "harnesses": cur},
                                 indent=2, sort_keys=True))

    if args.accept or not BASELINE.exists():
        BASELINE.write_text(json.dumps({"certified_utc": stamp, "harnesses": cur},
                                       indent=2, sort_keys=True))
        print(f"{'ACCEPTED' if args.accept else 'BASELINE CREATED'}: "
              f"{BASELINE.relative_to(ROOT)} ({stamp})")
        if not args.accept:
            print("  Nothing to compare against yet — next run will diff.")
            return 0

    base = json.loads(BASELINE.read_text())["harnesses"]
    print(f"\n=== HARNESS CERTIFICATION — current vs baseline ===")
    print(f"  baseline {json.loads(BASELINE.read_text())['certified_utc']}")
    print(f"  current  {stamp}\n")

    failures, live_drift, unchanged = [], [], 0
    for name, _rel, _fn, cls, _cmd in MANIFEST:
        b, c = base.get(name, {}), cur.get(name, {})
        print(f"  [{name}]  ({cls})")
        if "_error" in c:
            print(f"    ERROR: {c['_error']}")
            failures.append(f"{name}: {c['_error']}")
            continue
        if not b:
            print("    no baseline entry — recording only")
            continue
        keys = sorted(k for k in c if not k.startswith("_"))
        if not keys:
            print("    (no metrics extracted)")
            continue
        for k in keys:
            bv, cv = b.get(k), c.get(k)
            if close(bv, cv):
                unchanged += 1
                print(f"    {k:28s} {bv} == {cv}")
            else:
                msg = f"{name}.{k}: {bv} -> {cv}"
                if cls == "deterministic":
                    print(f"    {k:28s} {bv} -> {cv}   *** CHANGED ***")
                    failures.append(msg)
                else:
                    print(f"    {k:28s} {bv} -> {cv}   (live, informational)")
                    live_drift.append(msg)

    print(f"\n=== VERDICT ===")
    print(f"  metrics unchanged        : {unchanged}")
    print(f"  deterministic CHANGES    : {len(failures)}")
    print(f"  live drifts (expected)   : {len(live_drift)}")
    if failures:
        print("\n  CERTIFICATION FAILED — deterministic evidence moved without a")
        print("  matching change to the docs that cite it:")
        for f in failures:
            print(f"    - {f}")
        print("\n  Either the harness changed, or the doc citing it is now wrong.")
        print("  Fix whichever is true before quoting the number again.")
        return 1
    print("\n  CERTIFICATION PASSED — every deterministic metric still reproduces.")
    if live_drift:
        print("  Live-measured metrics moved, which is what they are for.")
    print("\n  Note: a PASS means the numbers still reconcile with their artifacts.")
    print("  It does NOT mean any of them is a profitable edge. Every deterministic")
    print("  metric here currently reads negative or breakeven after cost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
