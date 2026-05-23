#!/usr/bin/env python3
"""Diagnostic: SL hit rate per asset class on closed trade data.

Computes the stop-loss hit rate per asset class (CRYPTO / FOREX / EQUITY /
COMMODITY / FUTURES / ETF / UNKNOWN) on the ghost-cleaned closed_picks.json
and the universal_resolved_picks.json audit-trail feed. This is the
calibration diagnostic for the per-category SL-distance floors defined in
``non_crypto_agent/main.sl_distance_floor_gate`` — run it to empirically
re-tune the floors after enough forward-test data accumulates.

Usage:
    python tools/calibration/sl_hit_rate_by_class.py

Notes:
    * Asset class is inferred via audit_trail.asset_classification.classify_symbol
      since closed_picks.json / universal_resolved_picks.json do not store a
      category field on the trade record.
    * An exit_reason that starts with "sl" (e.g. ``sl``, ``sl_hit``,
      ``sl_hit_resolved``) is counted as a stop-loss hit. Anything else (tp,
      tp_hit, time_exit, expired, price_resolved, ...) is counted as not-SL.
    * Also reports the SL-distance distribution (median / p25 / p75) per class
      where entry_price + stop_loss are both present, so tight-stop patterns
      correlated with SL hits are visible at a glance.

Cited by DEEPSEEK_APR122026.MD §6B (75.5% SL hit on universal_resolved_picks)
and the main-thread re-measurement (59.1% on ghost-cleaned closed_picks).
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from audit_trail.asset_classification import classify_symbol
except Exception as e:  # pragma: no cover - diagnostic only
    print(f"WARN: could not import classify_symbol ({e}); falling back to UNKNOWN")
    classify_symbol = None  # type: ignore


DEFAULT_SOURCES: list[Path] = [
    ROOT / "alpha_engine" / "data" / "closed_picks.json",
    ROOT / "audit_trail" / "data" / "universal_resolved_picks.json",
]


def _asset_class(symbol: str) -> str:
    if not symbol or classify_symbol is None:
        return "UNKNOWN"
    try:
        result = classify_symbol(symbol)
        cls = getattr(result, "asset_class", None) or "UNKNOWN"
        return str(cls).upper()
    except Exception:
        return "UNKNOWN"


def _is_sl_hit(exit_reason: Any) -> bool:
    reason = str(exit_reason or "").strip().lower()
    return reason.startswith("sl")


def _sl_distance(pick: dict) -> float | None:
    try:
        entry = float(pick.get("entry_price"))  # type: ignore[arg-type]
        sl = float(pick.get("stop_loss"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(entry) or not math.isfinite(sl) or entry == 0:
        return None
    return abs(entry - sl) / abs(entry)


def _load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  SKIP (missing): {path}")
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # tolerate dict-wrapped shapes
        for key in ("picks", "closed_picks", "trades", "resolved"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def _report(label: str, picks: list[dict]) -> None:
    per_class: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "sl_hits": 0, "distances": []}
    )
    skipped_status = 0
    for pick in picks:
        # Only count closed/resolved trades with an exit_reason — open picks
        # and status-less entries would skew the denominator.
        exit_reason = pick.get("exit_reason")
        if not exit_reason:
            skipped_status += 1
            continue
        cls = _asset_class(str(pick.get("symbol", "")))
        bucket = per_class[cls]
        bucket["total"] += 1
        if _is_sl_hit(exit_reason):
            bucket["sl_hits"] += 1
        dist = _sl_distance(pick)
        if dist is not None:
            bucket["distances"].append(dist)

    print(f"\n=== {label} ===")
    total_all = sum(b["total"] for b in per_class.values())
    sl_all = sum(b["sl_hits"] for b in per_class.values())
    if total_all == 0:
        print("  (no closed picks with exit_reason)")
        return

    overall = sl_all / total_all * 100 if total_all else 0.0
    print(f"  overall: {sl_all}/{total_all} = {overall:5.1f}% SL hit "
          f"(skipped {skipped_status} with no exit_reason)")

    print(f"  {'class':<12} {'total':>7} {'sl_hit':>7} {'rate':>7}   "
          f"{'median_sl_dist':>14} {'p25':>7} {'p75':>7}")
    for cls in sorted(per_class, key=lambda c: -per_class[c]["total"]):
        b = per_class[cls]
        rate = b["sl_hits"] / b["total"] * 100 if b["total"] else 0.0
        dists = sorted(b["distances"])
        if dists:
            median = statistics.median(dists) * 100
            p25 = dists[len(dists) // 4] * 100
            p75 = dists[(3 * len(dists)) // 4] * 100
            median_s = f"{median:6.2f}%"
            p25_s = f"{p25:6.2f}%"
            p75_s = f"{p75:6.2f}%"
        else:
            median_s = p25_s = p75_s = "   n/a"
        print(f"  {cls:<12} {b['total']:>7d} {b['sl_hits']:>7d} "
              f"{rate:>6.1f}%   {median_s:>14} {p25_s:>7} {p75_s:>7}")


def main(argv: list[str] | None = None) -> int:
    sources = [Path(p) for p in (argv or [])] or DEFAULT_SOURCES
    print("SL hit rate per asset class")
    print("Sources:")
    for p in sources:
        print(f"  - {p}")
    for src in sources:
        picks = _load(src)
        _report(src.name, picks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
