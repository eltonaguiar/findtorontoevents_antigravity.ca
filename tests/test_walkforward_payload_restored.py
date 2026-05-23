"""Regression test for issue #696 — walkforward payload restoration.

PR #665 (merged 2026-05-02 23:08Z) silently removed the walkforward
payload assignment from audit_trail/dashboard_generator.py. Live
consumer audit_dashboard/template.html:834-864 (MAJOR GOAL banner)
became permanently empty.

This test reads the actual source file and asserts the wiring is
present. If it ever fails, the payload-key wiring has been removed
again.

Existing tests/test_dashboard_generator_walkforward_byclass.py
constructs its own fake payload and gives false-green — does NOT
exercise the source file.
"""
from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "audit_trail" / "dashboard_generator.py"


def _src() -> str:
    return SRC.read_text(encoding="utf-8")


def test_wf_by_class_local_initialized():
    s = _src()
    assert "_wf_by_class: dict = {}" in s, \
        "_wf_by_class local must be initialized before the try block"
    assert "_wf_results_generated_at = None" in s


def test_wf_by_class_read_from_json():
    s = _src()
    assert '_wf_data.get("by_class")' in s, \
        "by_class key must be pulled from walkforward_results.json"
    assert '_wf_data.get("generated_at")' in s


def test_walkforward_payload_key_assigned():
    s = _src()
    assert '"walkforward":' in s, "walkforward payload key missing"
    assert '"by_class": _wf_by_class' in s, \
        "walkforward.by_class must reference _wf_by_class local"
    assert '"generated_at": _wf_results_generated_at' in s


def test_template_consumer_still_present():
    """If the template stops consuming walkforward, can drop the
    payload — but until then the wiring must stay."""
    tpl = (REPO / "audit_dashboard" / "template.html").read_text(encoding="utf-8")
    assert "walkforward-by-class-card" in tpl, \
        "template no longer references the walkforward card; consider removing payload"
