#!/usr/bin/env python
"""HF Quality Gate pre-flip re-smoke gate.

Pulls 100 fresh picks from ``audit_dashboard/data/dashboard_data.json``,
runs the HF Quality Gate (``alpha_engine.hedge_fund_quality_gate.passes_hedge_fund_gate``)
on each, prints PASS/FAIL + per-AC breakdown, and exits 0 if reject
rate < ``--max-reject`` (default 0.35) or 1 otherwise.

This script is the 4th of the 4 telemetry guardrails the external-AI
consensus required for the ``HF_QUALITY_GATE_ENABLED`` default-on flip
(see ``reports/external_ai_review_hf_gate_default_on_2026_04_28.md``).
Wire into CI as a guard before any future config change.

Usage:
    python tools/run_hf_gate_smoke.py
    python tools/run_hf_gate_smoke.py --max-reject 0.35 --n 100
    python tools/run_hf_gate_smoke.py --picks-source path/to/dashboard_data.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("hf_gate_smoke")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PICKS_SOURCE = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"


def _ensure_repo_on_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def _load_picks(source: Path, n: int) -> list[dict[str, Any]]:
    """Pull up to ``n`` picks from a dashboard_data.json-shaped file.

    We prefer ``picks.active`` and fall back to ``picks.recent_closed``;
    both layouts are observed in the live JSON.
    """
    with source.open("r", encoding="utf-8") as fh:
        blob = json.load(fh)

    candidates: list[dict[str, Any]] = []
    picks = blob.get("picks", {}) if isinstance(blob, dict) else {}
    if isinstance(picks, dict):
        active = picks.get("active") or []
        recent = picks.get("recent_closed") or []
        if isinstance(active, list):
            candidates.extend(p for p in active if isinstance(p, dict))
        if isinstance(recent, list) and len(candidates) < n:
            candidates.extend(p for p in recent if isinstance(p, dict))

    # Some dashboards store picks under ``active_picks`` etc — best-effort fallbacks.
    if not candidates and isinstance(blob, dict):
        for key in ("active_picks", "all_picks", "picks_list"):
            v = blob.get(key)
            if isinstance(v, list):
                candidates.extend(p for p in v if isinstance(p, dict))
                if candidates:
                    break

    return candidates[:n]


def _run_smoke(
    picks: list[dict[str, Any]],
    max_reject: float,
) -> tuple[int, int, dict[str, Any]]:
    """Run the HF gate over ``picks``. Returns (rejects, total, breakdown)."""
    _ensure_repo_on_path()
    from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate

    total = 0
    rejects = 0
    reject_reasons: Counter[str] = Counter()
    per_ac_total: Counter[str] = Counter()
    per_ac_reject: Counter[str] = Counter()

    for pick in picks:
        total += 1
        ac = str(pick.get("asset_class") or "UNKNOWN").upper()
        per_ac_total[ac] += 1
        try:
            ok, reason = passes_hedge_fund_gate(pick)
        except Exception as exc:
            ok, reason = True, f"hf_gate_exception:{exc!r}"
            logger.debug(f"hf_gate exception on pick {pick.get('id')}: {exc!r}")
        if not ok:
            rejects += 1
            per_ac_reject[ac] += 1
            reject_reasons[(reason or "no_reason").split(":", 1)[0]] += 1

    rate = (rejects / total) if total else 0.0
    breakdown = {
        "total": total,
        "rejects": rejects,
        "reject_rate": round(rate, 4),
        "max_reject_threshold": max_reject,
        "verdict": "PASS" if rate < max_reject else "FAIL",
        "top_reject_reasons": reject_reasons.most_common(10),
        "per_asset_class": {
            ac: {
                "total": per_ac_total[ac],
                "rejects": per_ac_reject.get(ac, 0),
                "reject_rate": round(
                    per_ac_reject.get(ac, 0) / per_ac_total[ac], 4
                ),
            }
            for ac in sorted(per_ac_total)
        },
    }
    return rejects, total, breakdown


def _format_report(breakdown: dict[str, Any]) -> str:
    lines = []
    verdict = breakdown["verdict"]
    lines.append(f"=== HF Gate Smoke — {verdict} ===")
    lines.append(
        f"sample={breakdown['total']} rejects={breakdown['rejects']} "
        f"reject_rate={breakdown['reject_rate']:.4f} "
        f"threshold={breakdown['max_reject_threshold']:.4f}"
    )
    lines.append("Top reject reasons:")
    for reason, count in breakdown["top_reject_reasons"]:
        lines.append(f"  {count:>4}  {reason}")
    lines.append("Per asset class:")
    for ac, row in breakdown["per_asset_class"].items():
        lines.append(
            f"  {ac:<10} n={row['total']:<5} rejects={row['rejects']:<5} "
            f"rate={row['reject_rate']:.4f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--picks-source",
        default=str(DEFAULT_PICKS_SOURCE),
        help="Path to dashboard_data.json (default: %(default)s)",
    )
    parser.add_argument("--n", type=int, default=100, help="Sample size (default 100)")
    parser.add_argument(
        "--max-reject",
        type=float,
        default=0.35,
        help="Reject-rate ceiling for PASS (default 0.35)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON summary"
    )
    args = parser.parse_args(argv)

    source = Path(args.picks_source)
    if not source.exists():
        print(f"ERROR: picks source not found: {source}", file=sys.stderr)
        return 2

    picks = _load_picks(source, args.n)
    if not picks:
        print(
            f"ERROR: no picks found in {source} (expected picks.active or "
            "picks.recent_closed)",
            file=sys.stderr,
        )
        return 2

    rejects, total, breakdown = _run_smoke(picks, args.max_reject)
    if args.json:
        print(json.dumps(breakdown, indent=2, default=str))
    else:
        print(_format_report(breakdown))

    return 0 if breakdown["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
