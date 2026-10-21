import json
import os
from pathlib import Path

import pytest

from audit_trail.quality_gates import passes_smart_gate


def test_smart_picks_are_gate_validated():
    """Every pick surfaced as a Smart Pick must pass passes_smart_gate."""
    candidates = [
        Path("audit_dashboard/data/dashboard_data.json"),
        Path("audit_dashboard/data/dashboard_payload.json"),
    ]
    payload_path = next((p for p in candidates if p.exists()), None)
    if payload_path is None:
        pytest.skip("no dashboard payload available")
    data = json.loads(payload_path.read_text(encoding="utf-8"))
    picks = (data.get("picks") or {}).get("smart_picks") or []
    for p in picks:
        assert passes_smart_gate(dict(p)), f"non-gate-validated pick in smart_picks: {p.get('symbol')}"


def test_curated_feed_is_separate_and_labeled():
    candidates = [
        Path("audit_dashboard/data/dashboard_data.json"),
        Path("audit_dashboard/data/dashboard_payload.json"),
    ]
    payload_path = next((p for p in candidates if p.exists()), None)
    if payload_path is None:
        pytest.skip("no dashboard payload available")
    data = json.loads(payload_path.read_text(encoding="utf-8"))
    picks = data.get("picks") or {}
    curated = picks.get("curated_feed") or []
    for p in curated:
        assert p.get("validation_status") == "Curated – not gate-validated"
    # curated picks must not be duplicated into smart_picks
    smart_syms = {(p.get("symbol"), p.get("direction")) for p in (picks.get("smart_picks") or [])}
    for p in curated:
        assert (p.get("symbol"), p.get("direction")) not in smart_syms
