#!/usr/bin/env python3
"""Variant certification — stamp every emitted pick with HOW it was computed.

WHY THIS EXISTS (item 6)
------------------------
The scanner enriches picks through a chain of optional modules, each wrapped in
`except ImportError: pass`:

    model_calibration.apply_calibration_to_picks()   -> adds calibrated_probability
                                                        + prediction_uncertainty
    elite_scorer.enrich_picks_with_elite_score()     -> adds elite_score
    ...

When one of those modules is missing, the scan keeps going and emits picks that
look completely normal. They are not comparable to a fully-enriched pick, and the
consequence is worse than lost enrichment:

    # production_scanner.py, ensemble agreement gate
    _unc = _p.get("prediction_uncertainty", None)
    if _unc is None:
        _p["ensemble_agreement"] = "UNKNOWN"
        surviving.append(_p)          # <-- PASSES THE HARD BLOCK GATE
        continue
    if _unc > 0.30:
        ...block the pick...

`prediction_uncertainty` exists only if calibration ran. So a missing optional
module does not merely reduce a pick's information — it silently DISABLES a gate
that was built to block low-agreement picks. Every pick then passes with
`ensemble_agreement: "UNKNOWN"`, which reads like a neutral data state rather than
"the filter never ran".

BEFORE THIS MODULE: two populations of picks were mixed in one file with nothing
distinguishing them — `full` (all enrichment ran, gates enforced) and `core_only`
(degraded, one or more gates silently skipped). Any downstream win-rate computed
across the mixed population is measuring neither one.

AFTER: every pick carries

    strategy_variant      "full" | "core_only"
    variant_missing       [module names that were unavailable]
    variant_gates_skipped [gates that therefore did not run]
    variant_certified_utc timestamp

so a consumer can filter to a single population before computing anything.

DESIGN NOTES
  - Stdlib only, zero imports from the scanner, so it can never itself be the
    reason a scan fails. A certification module that can crash the thing it is
    certifying is worse than none.
  - `probe()` tests importability ONCE and caches. Repeated import attempts inside
    a hot loop are slow and can emit duplicate warnings.
  - Degradation is recorded at the point of failure (`note_degraded`), not inferred
    afterwards from a missing key. Inferring would confuse "module absent" with
    "module present but returned nothing" — different bugs.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timezone

# label -> (module, attribute that must exist, gates this module enables)
OPTIONAL_FEATURES: dict[str, tuple[str, str, list[str]]] = {
    "model_calibration": (
        "model_calibration",
        "apply_calibration_to_picks",
        ["ensemble_agreement_gate"],
    ),
    "elite_scorer": (
        "elite_scorer",
        "enrich_picks_with_elite_score",
        ["elite_score_ranking"],
    ),
}

VARIANT_FULL = "full"
VARIANT_CORE = "core_only"

_probe_cache: dict[str, dict] | None = None
_degraded: dict[str, str] = {}   # label -> reason recorded at the failure site


def probe(force: bool = False) -> dict[str, dict]:
    """Is each optional feature importable? Cached; `force=True` re-tests."""
    global _probe_cache
    if _probe_cache is not None and not force:
        return _probe_cache
    out: dict[str, dict] = {}
    for label, (mod_name, attr, gates) in OPTIONAL_FEATURES.items():
        entry = {"available": False, "error": None, "gates": gates}
        try:
            mod = importlib.import_module(mod_name)
            if attr and not hasattr(mod, attr):
                entry["error"] = f"{mod_name} imported but has no {attr}"
            else:
                entry["available"] = True
        except Exception as exc:  # noqa: BLE001 - reporting is the whole point
            entry["error"] = f"{type(exc).__name__}: {exc}"
        out[label] = entry
    _probe_cache = out
    return out


def note_degraded(label: str, reason: str) -> None:
    """Record that a feature failed AT RUNTIME, even if it probed as available.

    A module can import fine and still raise when called. Only this path catches
    that, which is why degradation is recorded here rather than inferred from the
    probe result.
    """
    _degraded[label] = reason


def reset() -> None:
    """Clear runtime degradation. Call at the start of each scan."""
    _degraded.clear()


def stamp() -> dict:
    """The variant block to merge into a pick."""
    p = probe()
    missing = sorted(
        {label for label, e in p.items() if not e["available"]} | set(_degraded)
    )
    gates_skipped: list[str] = []
    for label in missing:
        gates_skipped.extend(p.get(label, {}).get("gates", []))
    variant = VARIANT_FULL if not missing else VARIANT_CORE
    block = {
        "strategy_variant": variant,
        "variant_missing": missing,
        "variant_gates_skipped": sorted(set(gates_skipped)),
        "variant_certified_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    if missing:
        reasons = {lbl: _degraded.get(lbl) or p.get(lbl, {}).get("error")
                   for lbl in missing}
        block["variant_reasons"] = reasons
    return block


def annotate_picks(picks: list[dict]) -> dict:
    """Stamp every pick in place. Returns the variant block for logging.

    In place, because the scanner passes `active` around by reference and callers
    would otherwise keep using the unstamped list.
    """
    block = stamp()
    for p in picks:
        if isinstance(p, dict):
            p.update(block)
    return block


def summary_line(block: dict) -> str:
    if block["strategy_variant"] == VARIANT_FULL:
        return "[VARIANT] full — all enrichment ran, all gates enforced"
    return (
        f"[VARIANT] core_only — MISSING {block['variant_missing']}; "
        f"GATES NOT ENFORCED: {block['variant_gates_skipped']}. "
        f"These picks are not comparable to full-variant picks."
    )


if __name__ == "__main__":
    b = stamp()
    print(summary_line(b))
    print()
    for label, e in probe().items():
        state = "OK" if e["available"] else f"ABSENT ({e['error']})"
        print(f"  {label:22s} {state}")
        print(f"  {'':22s} gates: {e['gates']}")
