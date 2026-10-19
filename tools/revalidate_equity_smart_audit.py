#!/usr/bin/env python3
"""
revalidate_equity_smart_audit.py
==================================

Re-audit helper for the EQUITY 7x SMART-gate disparity finding from
PHASE 1C.d (audit doc: updates/2026-06-23-equity-smart-gate-7x-disparity-audit.md).

When #28051310550 commits + fresh data lands in pick_funnel_90d.json, run this
script and it will:
  1) Read pick_funnel_90d.json (90-day PickFlow funnel snapshot)
  2) Extract per-class scanned / passed_smart / passed_verified_alpha /
     passed_high_conviction / passed_proven / WR%
  3) Compute (CRYPTO_smart_pct / EQUITY_smart_pct) ratio
  4) Classify against 5x / 7x / 10x thresholds:
     - <5.0x  -> EQUITY out-performs -> floor TOO STRICT, apply remediation R1/R2/R3
     - 5-10x  -> structural finding ROBUST (matching PHASE 1C.d's 7x)
     - >10.0x -> severe drift -> IMMEDIATE R1 soft-penalty + R3 macro-stress action
  5) Print verdict + freshness caveat showing the JSON mtime epoch

Re-runnable: zero side effects, reads-only, prints verdict to stdout.
AGENTS.md doc discipline: see updates/2026-06-23-...md companion.

Usage:
  python3 tools/revalidate_equity_smart_audit.py
  python3 tools/revalidate_equity_smart_audit.py --threshold-soft 5.0 --threshold-robust 10.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


SNAPSHOT_PATH = Path("audit_dashboard/data/pick_funnel_90d.json")
DEFAULT_THRESHOLD_SOFT = 5.0       # below this: floor may be too strict
DEFAULT_THRESHOLD_ROBUST = 10.0    # above this: severe drift; remediation urgent


def _read_snapshot(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"snapshot not found: {path}")
    with path.open("rb") as f:
        return json.load(f)


def _per_class_block(funnel_by_class, cls: str) -> Optional[dict]:
    """PickFlow store funnel_by_class as DICT (keyed by class name) — but the schema
    has been seen to drift to LIST-of-dicts in legacy runs; handle both so the
    helper stays robust regardless of cron-version drift.
    """
    if isinstance(funnel_by_class, dict):
        return funnel_by_class.get(cls)
    if isinstance(funnel_by_class, list):
        for entry in funnel_by_class:
            if isinstance(entry, dict) and entry.get("class", entry.get("asset_class", "")).upper() == cls:
                return entry
    return None


def _stats(block: Optional[dict]) -> dict:
    if not block:
        return {"present": False}
    scanned = block.get("scanned", block.get("n_scanned", 0))
    smart = block.get("passed_smart", block.get("smart_pass", 0))
    va = block.get("passed_verified_alpha", block.get("verified_alpha_pass", 0))
    hc = block.get("passed_high_conviction", block.get("high_conviction_pass", 0))
    proven = block.get("passed_proven", block.get("proven_pass", 0))
    n_out = block.get("n_outcomes", block.get("outcomes", 0))
    wr_pct = block.get("wr_pct", block.get("win_rate", None))
    smart_pct = (smart / scanned * 100.0) if scanned else 0.0
    return {
        "present": True,
        "scanned": scanned,
        "passed_smart": smart,
        "smart_pct": round(smart_pct, 4),
        "passed_verified_alpha": va,
        "passed_high_conviction": hc,
        "passed_proven": proven,
        "n_outcomes": n_out,
        "wr_pct": wr_pct,
    }


def _verdict(ratio: Optional[float], t_soft: float, t_robust: float) -> str:
    """Classify ratio against soft+robust thresholds.

    Boundary semantics: ratio in [t_soft, t_robust] (both inclusive) is ROBUST;
    ratio strictly below t_soft is SOFT_DRIFT; ratio strictly above t_robust
    is SEVERE_DRIFT. Returned tuple-format is split below for testability.
    """
    if ratio is None:
        return "INSUFFICIENT_DATA"
    if ratio < t_soft:
        return (
            f"SOFT_DRIFT ratio={ratio:.2f}x (<{t_soft}x) — EQUITY may be over-suppressed; "
            f"consider remediation R1 (hard floor -> soft penalty) and R2 (n-sample dynamic flooring)"
        )
    if ratio <= t_robust:
        return (
            f"ROBUST ratio={ratio:.2f}x ∈ [{t_soft}x, {t_robust}x] — PHASE 1C.d structural finding holds; "
            f"the elite_score>=55 floor (quality_gates.py:7938) calibration is empirically sound"
        )
    return (
        f"SEVERE_DRIFT ratio={ratio:.2f}x (>{t_robust}x) — floor is starving EQUITY throughput; "
        f"remediation R1 (convert to soft penalty) and R3 (macro-stress linkage) URGENT"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-audit the EQUITY 7x SMART-gate disparity on the latest pick_funnel_90d.json snapshot."
    )
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH, help="path to pick_funnel_90d.json")
    parser.add_argument("--threshold-soft", type=float, default=DEFAULT_THRESHOLD_SOFT,
                        help="ratio below this triggers soft-drift verdict (default 5.0x)")
    parser.add_argument("--threshold-robust", type=float, default=DEFAULT_THRESHOLD_ROBUST,
                        help="ratio above this triggers severe-drift verdict (default 10.0x)")
    args = parser.parse_args()

    try:
        snapshot = _read_snapshot(args.snapshot)
    except FileNotFoundError as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return 2

    mtime_epoch = int(args.snapshot.stat().st_mtime)
    window_days = snapshot.get("window_days", "?")
    funnel_by_class = snapshot.get("funnel_by_class", {})

    crypto = _stats(_per_class_block(funnel_by_class, "CRYPTO"))
    equity = _stats(_per_class_block(funnel_by_class, "EQUITY"))

    print("=== revalidate_equity_smart_audit.py ===")
    print(f"  snapshot:               {args.snapshot}")
    print(f"  snapshot_mtime_epoch:   {mtime_epoch}")
    print(f"  snapshot_window_days:   {window_days}")
    print()

    if not crypto["present"] or not equity["present"]:
        print(f"  CRYPTO block present: {crypto['present']}")
        print(f"  EQUITY block present: {equity['present']}")
        print("  ERROR: cannot compute ratio — missing CRYPTO or EQUITY in funnel_by_class",
              file=sys.stderr)
        return 3

    print(f"  CRYPTO: scanned={crypto['scanned']:>6} smart_pass={crypto['passed_smart']:>5} "
          f"({crypto['smart_pct']:.2f}%) va={crypto['passed_verified_alpha']} "
          f"hc={crypto['passed_high_conviction']} proven={crypto['passed_proven']} "
          f"| WR={crypto['wr_pct']}% n={crypto['n_outcomes']}")
    print(f"  EQUITY: scanned={equity['scanned']:>6} smart_pass={equity['passed_smart']:>5} "
          f"({equity['smart_pct']:.2f}%) va={equity['passed_verified_alpha']} "
          f"hc={equity['passed_high_conviction']} proven={equity['passed_proven']} "
          f"| WR={equity['wr_pct']}% n={equity['n_outcomes']}")
    print()

    ratio = (crypto["smart_pct"] / equity["smart_pct"]) if equity["smart_pct"] > 0 else None
    if ratio is None:
        print("  ratio: undefined (EQUITY smart_pct = 0 — confirms EQUITY starvation under current floor)")
    else:
        # Round trip precision: with CRYPTO scanned=15139 + smart=1478 the ratio is exact
        # but with smaller denominators (e.g. ETF=92) rounding could shift the verdict at
        # boundary ratios. Print 3 decimal places to surface any near-threshold drift.
        print(f"  ratio CRYPTO_smart_pct / EQUITY_smart_pct = {crypto['smart_pct']:.3f}% / "
              f"{equity['smart_pct']:.3f}% = **{ratio:.3f}x**")

    print()
    print(f"  verdict: {_verdict(ratio, args.threshold_soft, args.threshold_robust)}")
    print()
    print(f"  freshness: snapshot last modified {mtime_epoch} (epoch); "
          f"CRYPTO/EQUITY ratios are robust to drift but decimals will refresh once "
          f"#28051310550 auto-commits land.")
    print()
    if crypto["scanned"] + equity["scanned"] < 1000:
        print("  NOTE: combined scan volume <1000 picks — ratios carry high variance; "
              "consider widening threshold band by 2-3x before drawing conclusions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
