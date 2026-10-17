"""Pick-rationale passthrough for the ``*_audit_push.py`` emitters.

Why this exists
---------------
Each emitter normalizes its source pick down to the handful of columns
``at_raw_picks`` needs (symbol / direction / entry / tp / sl / confidence /
strategy / timestamp). That ``normalize()`` step rebuilt the dict from scratch
and therefore **dropped the human-readable ``reason``**.

``audit_trail.recorder.record_raw_pick`` persists exactly the dict it is handed
into ``at_raw_picks.raw_payload``, so the rationale never reached MySQL. The
``/audit`` row tooltip renders a "Why now:" block from ``p.reason``
(``audit_dashboard/template.html``), so it came up empty for every pick emitted
through those systems — the pick was present, the justification was not.

The rationale *does* exist upstream: ``alpha_engine/data/active_picks.json``
carries ~200 fields per pick including ``reason``, e.g.

    "Residual momentum #2: beta=1.28, residual_7d=-2.3%, residual_14d=27.9%,
     RSI=64. Blitz et al. (2011 JFE): pure alpha after beta removal."

It was simply discarded at the last hop.

What this does
--------------
``with_pick_reason()`` copies the rationale plus the structural evidence the
/audit tooltip reads onto the normalized payload, so it survives into MySQL and
can be retrieved and shown. Only fields that are actually present are added, so
payloads stay small (both the JSON column and the dashboard payload are
size-sensitive) and sources that never had a reason are unaffected.

Design rules:
  * fail-open — this must never be able to break an emitter's audit push
  * additive only — an existing non-empty value on ``normalized`` wins
  * bounded — the reason is truncated so a runaway emitter cannot bloat
    ``raw_payload`` (the sibling ``sync_all_picks_to_mysql`` path truncates to
    4000 chars, so stay well inside that)
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

__all__ = [
    "REASON_KEYS",
    "REASON_NESTED",
    "EVIDENCE_KEYS",
    "DEFAULT_MAX_LEN",
    "extract_reason",
    "with_pick_reason",
]

#: Ordered by preference. ``audit_trail/dashboard_generator.py`` resolves the
#: same chain when it builds the dashboard payload, so both ends agree on what
#: "the" reason is.
#:
#: NOTE: ``antigravity_tooltip`` is deliberately NOT here. It is a safety /
#: protocol note (e.g. "Safe Trading Protocol: Under Threshold (REJECTED for
#: Real Money)"), not an entry rationale, and the /audit insight tooltip renders
#: it in its own "Antigravity safety" row. It is passed through as evidence
#: instead — see :data:`EVIDENCE_KEYS`.
REASON_KEYS: Sequence[str] = (
    "reason",
    "signal_reason",
    "entry_reason",
    "raw_reason",
    "reasoning",
    "confluence_reason",
    "notes",
)

#: Some emitters wrap their payload; look one level in for a reason.
REASON_NESTED: Sequence[str] = ("extra", "audit", "signal", "metadata")

#: Structural evidence the /audit insight tooltip renders under
#: "Fundamental / structural basis" (confluence / agreeing systems / concept),
#: plus ``antigravity_tooltip`` which feeds the "Antigravity safety" row.
EVIDENCE_KEYS: Sequence[str] = (
    "confluence_strategies",
    "source_strategies",
    "concept_family",
    "antigravity_tooltip",
)

#: Keep --in raw_payload-- comfortably bounded.
DEFAULT_MAX_LEN = 600


def _as_text(val: Any, max_len: int) -> str:
    """Coerce a scalar to trimmed text; anything structured/non-scalar -> ''."""
    if val is None or isinstance(val, (dict, list, tuple, set, bool)):
        return ""
    text = str(val).strip()
    if not text:
        return ""
    if max_len and max_len > 0:
        return text[:max_len]
    return text


def extract_reason(pick: Dict[str, Any], max_len: int = DEFAULT_MAX_LEN) -> str:
    """Return the best available human-readable rationale for ``pick``.

    Checks :data:`REASON_KEYS` in order, then one level into each of
    :data:`REASON_NESTED`. Returns ``""`` when nothing usable is found —
    callers must treat that as "no rationale available", not as an error.
    """
    if not isinstance(pick, dict):
        return ""
    for key in REASON_KEYS:
        text = _as_text(pick.get(key), max_len)
        if text:
            return text
    for parent in REASON_NESTED:
        nested = pick.get(parent)
        if isinstance(nested, dict):
            for key in REASON_KEYS:
                text = _as_text(nested.get(key), max_len)
                if text:
                    return text
    return ""


def with_pick_reason(normalized: Dict[str, Any], pick: Dict[str, Any],
                     max_len: int = DEFAULT_MAX_LEN) -> Dict[str, Any]:
    """Attach ``pick``'s rationale + tooltip evidence onto ``normalized``.

    Mutates and returns ``normalized``. Never raises: a rationale helper must
    not be able to break an emitter's audit push.
    """
    if not isinstance(normalized, dict):
        return normalized
    if not isinstance(pick, dict):
        return normalized

    try:
        reason = extract_reason(pick, max_len=max_len)
        if reason and not _as_text(normalized.get("reason"), 0):
            normalized["reason"] = reason

        # Preserve the structural evidence the tooltip renders. Additive only.
        for key in EVIDENCE_KEYS:
            if _as_text(normalized.get(key), 0):
                continue
            val = pick.get(key)
            if val:
                normalized[key] = val

        # Confluence note is a separate tooltip line; keep it if present.
        note: Optional[str] = _as_text(pick.get("confluence_reason"), max_len)
        if note and not _as_text(normalized.get("confluence_reason"), 0):
            normalized["confluence_reason"] = note
    except Exception:  # pragma: no cover - defensive: never break the push
        pass

    return normalized
