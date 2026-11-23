#!/usr/bin/env python3
"""verify_forward_benchmark.py — P1-5 credential-free verifier for benchmark_coverage.

Reads the published forward ledger (audit2_forward.json or forward_clock.json) and
reports the current benchmark_coverage for each hypothesis. Fails if any hypothesis
that should be eligible has coverage < 0.90.

This is the offline check that can run in CI without DB creds. The actual fix
(benchmark_leg price joins for the missing ~87 rows) still requires the live DB.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forward", default="audit_dashboard/data/audit2_forward.json",
                    help="Path to the forward clock JSON")
    ap.add_argument("--min-coverage", type=float, default=0.90)
    args = ap.parse_args()

    p = Path(args.forward)
    if not p.exists():
        print(f"SKIP: {p} not found (no forward data in this workspace)", file=sys.stderr)
        return 0

    data = json.loads(p.read_text())
    # Support both "by_hypothesis" shape (audit2_forward.json) and flat list
    if isinstance(data, dict) and "by_hypothesis" in data:
        rows = []
        for hyp, v in data["by_hypothesis"].items():
            n = int(v.get("n") or 0)
            bench = int(v.get("benchmark_leg") or 0)
            cov = bench / n if n else 0.0
            rows.append({"hypothesis": hyp, "benchmark_coverage": cov, "n": n, "benchmark_leg": bench})
    else:
        rows = data if isinstance(data, list) else data.get("rows") or data.get("hypotheses") or []
    if not rows:
        print("SKIP: forward file has no rows/hypotheses", file=sys.stderr)
        return 0

    bad = []
    for r in rows:
        cov = r.get("benchmark_coverage") or r.get("benchmark_cov") or 0.0
        hyp = r.get("hypothesis") or r.get("id") or r.get("pod")
        if cov < args.min_coverage:
            bad.append((hyp, cov))

    if bad:
        print("FAIL: benchmark_coverage below threshold", file=sys.stderr)
        for h, c in bad:
            print(f"  {h}: {c:.3f} < {args.min_coverage}", file=sys.stderr)
        return 1

    print(f"OK: all {len(rows)} hypotheses meet benchmark_coverage >= {args.min_coverage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
