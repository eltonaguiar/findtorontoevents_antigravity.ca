"""Canonical status vocabulary for the hypothesis registry (read-only view).

`reports/hypothesis_registry.json` is an append-only pre-registration artifact;
its `status` field has drifted into 28 spellings ("PRE-REGISTERED",
"forward-shadow", "REJECTED - only 0 scored windows", ...). Rewriting that file
would destroy the audit trail, so this module normalises on read instead.

Canonical states (7):

    PRE_REGISTERED  declared, no test yet
    UNTESTED        declared and testable but not started
    BLOCKED_DATA    cannot be tested yet (missing feed / failed control)
    FORWARD         in forward observation / shadow / paper pilot
    SUPPORTED       passed its pre-registered test
    WEAK            tested, inconclusive or marginal
    REFUTED         tested and failed, killed, or rejected

Unknown spellings are reported as UNKNOWN rather than guessed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

CANONICAL_STATES = (
    "PRE_REGISTERED", "UNTESTED", "BLOCKED_DATA", "FORWARD",
    "SUPPORTED", "WEAK", "REFUTED",
)
UNKNOWN = "UNKNOWN"

# Exact (case-folded, dashed/underscored) matches first.
_EXACT = {
    "pre_registered": "PRE_REGISTERED",
    "pre-registered": "PRE_REGISTERED",
    "registered-untested": "PRE_REGISTERED",
    "registered_untested": "PRE_REGISTERED",
    "untested": "UNTESTED",
    "untested_data_gap": "BLOCKED_DATA",
    "data_gap": "BLOCKED_DATA",
    "registered_blocked_on_data": "BLOCKED_DATA",
    "control_failed_pending_clean_entry": "BLOCKED_DATA",
    "forward_observation": "FORWARD",
    "forward_shadow": "FORWARD",
    "forward-shadow": "FORWARD",
    "forward_accruing": "FORWARD",
    "paper_pilot": "FORWARD",
    "shadow_implementation": "FORWARD",
    "shadow_live": "FORWARD",
    "tested_pass": "SUPPORTED",
    "tested_pass_backtest_forward_pending": "SUPPORTED",
    "supported": "SUPPORTED",
    "tested_weak": "WEAK",
    "weak": "WEAK",
    "refuted": "REFUTED",
    "killed": "REFUTED",
    "tested_kill": "REFUTED",
    "rejected": "REFUTED",
    "harness_rejected": "REFUTED",
    "failed_archived": "REFUTED",
    "null": "REFUTED",
    "closed": "REFUTED",
}

# Prefix rules catch free-text variants like
# "REJECTED - only 0 scored windows (need 3)".
_PREFIX = (
    ("rejected", "REFUTED"),
    ("refuted", "REFUTED"),
    ("killed", "REFUTED"),
    ("supported", "SUPPORTED"),
    ("tested_pass", "SUPPORTED"),
)


def normalize_status(raw: Any) -> str:
    """Map a registry status spelling to a canonical state (or UNKNOWN)."""
    if raw is None:
        return UNKNOWN
    text = str(raw).strip().casefold()
    if not text:
        return UNKNOWN
    # Normalise separators and whitespace, keeping one canonical form.
    key = text.replace(" ", "_")
    if key in _EXACT:
        return _EXACT[key]
    # A data-gap note anywhere means it cannot be tested yet.
    if "data_gap" in key or "data-gap" in key:
        return "BLOCKED_DATA"
    # Free-text variants ("REJECTED - reason", "refuted due to ...").
    head = key.split("_-_")[0].split("__")[0]
    for prefix, state in _PREFIX:
        if key.startswith(prefix) or head.startswith(prefix):
            return state
    return UNKNOWN


def iter_hypotheses(node: Any) -> Iterable[Mapping[str, Any]]:
    """Yield every dict that looks like a hypothesis record, recursively."""
    if isinstance(node, dict):
        if isinstance(node.get("id"), str) and "status" in node:
            yield node
        for v in node.values():
            yield from iter_hypotheses(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_hypotheses(v)


def summarize(registry: Any) -> dict[str, Any]:
    """Canonical-state counts plus the unmapped spellings (never coerced)."""
    counts: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    total = 0
    for hyp in iter_hypotheses(registry):
        total += 1
        state = normalize_status(hyp.get("status"))
        counts[state] += 1
        if state == UNKNOWN:
            unmapped[str(hyp.get("status"))] += 1
    return {
        "total": total,
        "counts": {s: counts.get(s, 0) for s in CANONICAL_STATES},
        "unknown": counts.get(UNKNOWN, 0),
        "unmapped_spellings": dict(unmapped.most_common()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default="reports/hypothesis_registry.json")
    args = ap.parse_args(argv)
    data = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    out = summarize(data)
    print(json.dumps(out, indent=1))
    return 0 if out["unknown"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
