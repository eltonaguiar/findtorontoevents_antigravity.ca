"""Per-source volume share cap (PR-H, 2026-05-12; updated 2026-05-16).

Caps the CRYPTO active-pick volume share of low-PF source systems that
dilute the CRYPTO aggregate. Trim excess by lowest ``smart_score`` /
``ml_composite``.

Caps (verdict-grade live numbers, `asset_class_health` / `systems`):
  - ``quan_engine``         -> 5%  (legacy drag; fully blocked elsewhere too)
  - ``luxalgo_filters``     -> 10% (PF 1.12, ~17.5% of CRYPTO n; 2026-05-15)
  - ``battleground``        -> 2%  (2026-05-16: PF 0.65, sub-floor drag)
  - ``copy_trader_highscore``-> 2% (2026-05-16: PF 0.80 WR 30.3% n=99)
  - ``regime_terminal``     -> 2%  (2026-05-16: PF 0.95 WR 32.3% n=65)
  - ``rapid_fire``          -> 5%  (2026-05-16: PF 0.81 WR 37.1% n=570 CRYPTO+FOREX)
  - ``super_signals``       -> 5%  (2026-05-16: PF 0.86 WR 36.8% CRYPTO; WR 36.8% EQUITY)
  - ``regime_terminal``     -> 2%/5% CRYPTO/EQUITY+FOREX (2026-05-16: WR 34.3% drag)

This is an INTAKE cap only — it does not change scoring or sizing. It
filters the active pick list AFTER scoring + tier selection but BEFORE
persistence.

Wire-up: ``alpha_engine/smart_picks_engine.py`` (final ``top`` list) AND
``alpha_engine/production_scanner.py`` (before ``save_active_picks``) — the
scanner caller was added 2026-05-15 to close the production_scanner bypass.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

log = logging.getLogger("per_source_volume_cap")

# {source_system: {asset_class: max_share_fraction}}
PER_SOURCE_VOLUME_CAP: dict[str, dict[str, float]] = {
    "quan_engine":          {"CRYPTO": 0.05},
    "luxalgo_filters":      {"CRYPTO": 0.10},
    # 2026-05-16 CRYPTO autopsy: these sources have sub-floor PF and drag class WR below 50%.
    # Soft caps (2%) reduce dilution without hard-blocking — user approval needed for full block.
    "battleground":         {"CRYPTO": 0.02},   # PF 0.65, severe drag
    "copy_trader_highscore":{"CRYPTO": 0.02},   # PF 0.80, WR 30.3%, n=99
    # EAGLE2 Phase 0 (2026-06-02): hard zero — policy-clean EQUITY PF 0.33, 40% concentration.
    "regime_terminal":      {"CRYPTO": 0.0, "EQUITY": 0.0, "FOREX": 0.0},
    # EAGLE2 Phase 0 (2026-06-05): multi_asset_cot COMMODITY WR=17% (n=223 closed)
    # + 91 OPEN losing positions. Hard zero on COMMODITY intake.
    "multi_asset_cot":      {"COMMODITY": 0.0},
    # EAGLE2 Phase 0: 14d CRYPTO 66% single-source concentration via incubator_gainer.
    "incubator_gainer":     {"CRYPTO": 0.0},
    # Unverified mercury2 path — lab/tournament only until M-108 forward proof.
    "mercury2_fast":        {"CRYPTO": 0.0},
    # 2026-05-16 CRYPTO+FOREX autopsy: rapid_fire filtered by score>=10 but still PF<1.
    # super_signals bypasses smart_picks_engine (see quality_gates.py:3795) — cap on intake.
    "rapid_fire":           {"CRYPTO": 0.0, "FOREX": 0.0},  # 2026-05-28: KILLED — PF 0.77, -70% PnL. BLACKLISTED.
    "super_signals":        {"CRYPTO": 0.05, "EQUITY": 0.05},  # PF 0.86 WR 36.8%; EQUITY WR 36.8%
}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _norm_class(s: Any) -> str:
    return str(s or "").strip().upper()


def _pick_source(p: dict) -> str:
    return _norm(p.get("source_system") or p.get("system") or p.get("source"))


def _pick_class(p: dict) -> str:
    return _norm_class(p.get("asset_class"))


def _score_key(p: dict) -> tuple[float, float]:
    # Sort ascending — lowest score trimmed first.
    return (
        float(p.get("ml_composite") or 0.0),
        float(p.get("smart_score") or 0.0),
    )


def enforce_cap(
    picks: Iterable[dict],
    caps: dict[str, dict[str, float]] | None = None,
) -> list[dict]:
    """Return filtered list with per-(source, class) volume share <= cap.

    Trim lowest-scored picks from offending (source, class) cohorts.
    Non-matching picks pass through untouched.
    """
    picks_list = list(picks or [])
    cap_table = caps if caps is not None else PER_SOURCE_VOLUME_CAP
    if not picks_list or not cap_table:
        return picks_list

    # Tally per-class totals + per-(source, class) members.
    class_totals: dict[str, int] = {}
    cohorts: dict[tuple[str, str], list[dict]] = {}
    for p in picks_list:
        ac = _pick_class(p)
        src = _pick_source(p)
        class_totals[ac] = class_totals.get(ac, 0) + 1
        cohorts.setdefault((src, ac), []).append(p)

    to_drop: set[int] = set()
    for src, class_caps in cap_table.items():
        src_n = _norm(src)
        for ac, frac in (class_caps or {}).items():
            ac_n = _norm_class(ac)
            members = cohorts.get((src_n, ac_n)) or []
            total = class_totals.get(ac_n, 0)
            if not members or total <= 0:
                continue
            # Solve for max_allowed s.t. max_allowed / (total - excess) <= frac
            # where excess = members - max_allowed (picks dropped shrink denom).
            # => max_allowed <= frac * (total - members) / (1 - frac)
            f = float(frac)
            if f >= 1.0:
                continue  # cap >= 100% never trims
            others = total - len(members)
            max_allowed = int((f * others) / (1.0 - f))
            # At least 1 if cap > 0 and any candidate exists.
            if max_allowed < 1 and f > 0:
                max_allowed = 1
            if len(members) <= max_allowed:
                continue
            members_sorted = sorted(members, key=_score_key)
            excess = len(members) - max_allowed
            for m in members_sorted[:excess]:
                to_drop.add(id(m))
            log.info(
                "[per_source_volume_cap] %s/%s trimmed %d picks "
                "(had %d / %d total, cap %.0f%% -> %d)",
                src_n, ac_n, excess, len(members), total,
                frac * 100.0, max_allowed,
            )

    if not to_drop:
        return picks_list
    return [p for p in picks_list if id(p) not in to_drop]


# Per-symbol concentration caps within a given asset class.
# Prevents a single symbol from dominating a class's active pick list.
# Discovered 2026-05-16: quan_engine CRYPTO was 60% ONDOUSDT; removing it collapses
# quan_engine CRYPTO PF from 1.30 → 0.92 — the edge is symbol-specific, not systematic.
PER_SYMBOL_CLASS_CAP: dict[str, dict[str, float]] = {
    "ONDOUSDT": {"CRYPTO": 0.10},  # cap at 10% of CRYPTO picks (was 60% via quan_engine)
}


def enforce_symbol_cap(
    picks: Iterable[dict],
    symbol_caps: dict[str, dict[str, float]] | None = None,
) -> list[dict]:
    """Cap any single symbol's share of a class's active picks.

    Trims lowest-scored picks of the over-represented symbol until the
    symbol's share of the class is at or below the cap fraction.
    """
    picks_list = list(picks or [])
    cap_table = symbol_caps if symbol_caps is not None else PER_SYMBOL_CLASS_CAP
    if not picks_list or not cap_table:
        return picks_list

    class_totals: dict[str, int] = {}
    sym_cohorts: dict[tuple[str, str], list[dict]] = {}
    for p in picks_list:
        ac = _pick_class(p)
        sym = str(p.get("symbol") or "").strip().upper()
        class_totals[ac] = class_totals.get(ac, 0) + 1
        sym_cohorts.setdefault((sym, ac), []).append(p)

    to_drop: set[int] = set()
    for symbol, class_caps in cap_table.items():
        sym_n = symbol.strip().upper()
        for ac, frac in (class_caps or {}).items():
            ac_n = _norm_class(ac)
            members = sym_cohorts.get((sym_n, ac_n)) or []
            total = class_totals.get(ac_n, 0)
            if not members or total <= 0:
                continue
            f = float(frac)
            if f >= 1.0:
                continue
            others = total - len(members)
            max_allowed = int((f * others) / (1.0 - f))
            if max_allowed < 1 and f > 0:
                max_allowed = 1
            if len(members) <= max_allowed:
                continue
            members_sorted = sorted(members, key=_score_key)
            excess = len(members) - max_allowed
            for m in members_sorted[:excess]:
                to_drop.add(id(m))
            log.info(
                "[per_source_volume_cap] symbol %s/%s trimmed %d picks "
                "(had %d / %d total, cap %.0f%% -> %d)",
                sym_n, ac_n, excess, len(members), total,
                frac * 100.0, max_allowed,
            )

    if not to_drop:
        return picks_list
    return [p for p in picks_list if id(p) not in to_drop]
