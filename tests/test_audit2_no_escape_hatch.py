"""Guards against the /audit2 "NO EDGE = SURFACE BROKEN" escape hatch being
re-installed by a future optimist.

The 2026-11-20 consolidation review found /audit2 rendering a banner whose
subtext was, in effect, "if we report no edge it must be a bug, not a finding".
That framing converts a *negative result* into an *excuse*, and it is exactly
the failure mode that kept the dashboard from ever reporting the truth.

These tests pin the honest contract:
  1. A zero-money-ready ledger must be representable and renderable.
  2. The surface may label a null result as "no edge found" but must NOT
     auto-label it "broken".
  3. Verdict vocabulary stays closed (so a new verdict cannot slip past the
     downstream gates silently).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
VERDICT_JSON = REPO / "audit_dashboard" / "data" / "money_ready_verdict.json"
TEMPLATE = REPO / "audit_dashboard" / "template.html"
AUDIT2_HTML = REPO / "audit_dashboard" / "audit2.html"
AUDIT2_JS = REPO / "audit_dashboard" / "audit2.js"

# The only verdicts downstream code is allowed to branch on.
CLOSED_VOCAB = {"MONEY_READY", "WATCH", "NOT_READY", "INSUFFICIENT_DATA"}


def test_zero_money_ready_is_a_valid_ledger_shape():
    """An empty money_ready list is a legitimate result, not a corrupt file."""
    if not VERDICT_JSON.exists():
        pytest.skip(f"{VERDICT_JSON.name} not present in this checkout")
    data = json.loads(VERDICT_JSON.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    assert "money_ready" in summary, "summary must always carry a money_ready key"
    assert isinstance(summary["money_ready"], list)
    # The whole point: zero is allowed.
    assert summary.get("n_classes", 0) >= 0


def test_verdict_vocabulary_is_closed():
    """Every emitted verdict must be one of the four the gates understand."""
    if not VERDICT_JSON.exists():
        pytest.skip(f"{VERDICT_JSON.name} not present in this checkout")
    data = json.loads(VERDICT_JSON.read_text(encoding="utf-8"))
    classes = data.get("classes") or data.get("by_asset_class") or {}
    if isinstance(classes, list):  # tolerate list-of-dicts shape
        classes = {c.get("asset_class", str(i)): c for i, c in enumerate(classes)}
    seen = {str(v.get("verdict")).upper() for v in classes.values() if isinstance(v, dict)}
    unknown = seen - CLOSED_VOCAB
    assert not unknown, f"verdicts outside the closed vocabulary: {sorted(unknown)}"


def test_no_surface_claims_absence_of_edge_means_broken_surface():
    """The escape-hatch phrasing must not come back.

    We allow "no edge" and "insufficient data" wording. We forbid phrasing that
    asserts a null result *implies* the pipeline is broken, because that invites
    a future agent to "fix" a real negative finding.
    """
    for path in (TEMPLATE, AUDIT2_HTML):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        banned = [
            r"no\s+edge\s+means\s+(the\s+)?(surface|pipeline|dashboard)\s+is\s+broken",
            r"if\s+we\s+see\s+no\s+edge[\s\S]{0,40}broken",
            r"0\s+money[\s-]?ready[\s\S]{0,30}(is|means)\s+(a\s+)?bug",
        ]
        for pat in banned:
            assert not re.search(pat, text, re.IGNORECASE), (
                f"{path.name}: banned escape-hatch phrasing /{pat}/ — a null "
                "result is a finding, not a bug"
            )


def test_audit2_static_pod_registry_declares_its_own_staleness():
    """`audit2.js` ships a HARDCODED pod registry (reports/ is not web-served).

    That is a reasonable trade-off, but it creates a real failure mode: a reader
    or an agent treats the static snapshot as live. Nothing in the payload
    distinguishes it from numbers fetched at page load, and no process fails when
    the snapshot drifts from the JSON beside it.

    So the file must at minimum *say* it is a static snapshot and *date* it, and
    that date must be in the future-proof ISO form a diff can catch. If this test
    fails, someone stripped the provenance marker — restore it.
    """
    if not AUDIT2_JS.exists():
        pytest.skip(f"{AUDIT2_JS.name} not present in this checkout")
    js = AUDIT2_JS.read_text(encoding="utf-8", errors="replace")
    assert re.search(r"static\s+snapshot|hardcoded", js, re.IGNORECASE), (
        f"{AUDIT2_JS.name}: the pod registry is hardcoded but no longer says so — "
        "a reader will mistake it for live data"
    )
    assert re.search(r"generated\s+20\d\d-\d\d-\d\d", js, re.IGNORECASE), (
        f"{AUDIT2_JS.name}: no 'Generated YYYY-MM-DD' marker — staleness of the "
        "static pod registry becomes undetectable"
    )


def test_audit2_live_numbers_come_from_the_ledger_not_the_snapshot():
    """Live metrics must be fetched, not baked into the static registry.

    Guards the specific confusion the review flagged: the file mixes a static pod
    list with live ledger numbers, so a stale pod entry looks as fresh as a
    freshly-fetched PF.
    """
    if not AUDIT2_JS.exists():
        pytest.skip(f"{AUDIT2_JS.name} not present in this checkout")
    js = AUDIT2_JS.read_text(encoding="utf-8", errors="replace")
    assert "audit3_ledger.json" in js, (
        f"{AUDIT2_JS.name}: no reference to audit3_ledger.json — the surface is "
        "not reading the ledger it claims to render"
    )
