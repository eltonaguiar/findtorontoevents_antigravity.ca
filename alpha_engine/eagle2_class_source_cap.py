"""EAGLE2 Phase 0 — per-class single-source concentration cap for Smart Picks intake.

No single source_system may exceed ``max_share`` of an asset class within the
active pick list. Trims lowest-scored picks from the dominant source first.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Iterable

log = logging.getLogger("eagle2_class_source_cap")

DEFAULT_MAX_SINGLE_SOURCE_SHARE = 0.60


def _norm_source(p: dict) -> str:
    return str(p.get("source_system") or p.get("system") or "unknown").strip().lower()


def _norm_class(p: dict) -> str:
    return str(p.get("asset_class") or "UNKNOWN").strip().upper()


def _score_key(p: dict) -> tuple[float, float]:
    return (
        float(p.get("ml_composite") or 0.0),
        float(p.get("smart_score") or 0.0),
    )


def enforce_class_single_source_cap(
    picks: Iterable[dict],
    max_share: float = DEFAULT_MAX_SINGLE_SOURCE_SHARE,
) -> tuple[list[dict], dict]:
    """Trim picks so no (source, asset_class) cohort exceeds ``max_share`` of class total."""
    picks_list = list(picks or [])
    stats = {
        "input": len(picks_list),
        "trimmed": 0,
        "max_share": max_share,
        "classes_affected": [],
    }
    if not picks_list or max_share >= 1.0:
        return picks_list, stats

    by_class: dict[str, list[dict]] = {}
    for p in picks_list:
        by_class.setdefault(_norm_class(p), []).append(p)

    to_drop: set[int] = set()
    for ac, members in by_class.items():
        if len(members) < 2:
            continue
        counts = Counter(_norm_source(p) for p in members)
        top_src, top_n = counts.most_common(1)[0]
        share = top_n / len(members)
        if share <= max_share:
            continue
        # Keep at most floor(max_share * n) from dominant source; trim rest.
        max_allowed = max(1, int(max_share * len(members)))
        if top_n <= max_allowed:
            continue
        dominant = [p for p in members if _norm_source(p) == top_src]
        dominant_sorted = sorted(dominant, key=_score_key)
        excess = top_n - max_allowed
        for m in dominant_sorted[:excess]:
            to_drop.add(id(m))
        stats["classes_affected"].append(
            {
                "asset_class": ac,
                "source": top_src,
                "share_before": round(share, 3),
                "trimmed": excess,
            }
        )
        log.info(
            "[eagle2_class_source_cap] %s/%s share %.1f%% > %.0f%% — trimmed %d",
            top_src,
            ac,
            share * 100.0,
            max_share * 100.0,
            excess,
        )

    if not to_drop:
        return picks_list, stats
    out = [p for p in picks_list if id(p) not in to_drop]
    stats["trimmed"] = len(picks_list) - len(out)
    stats["output"] = len(out)
    return out, stats
