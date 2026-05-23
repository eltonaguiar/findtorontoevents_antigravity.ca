"""Smoke test that verifies catalyst_filter is importable from alpha_engine and
that production_scanner.py contains the wire-up call site for it.

This is a static / import-only test — it does NOT invoke any network calls,
does NOT run the full scanner, and does NOT depend on yfinance/openbb data.
The wire-up's value is "the call site exists and is importable"; the data
provider quality is a follow-up concern.
"""
from __future__ import annotations

import importlib
from pathlib import Path


def test_catalyst_filter_importable():
    """Module must import and expose the public API the wire-up uses."""
    mod = importlib.import_module("alpha_engine.catalyst_filter")
    assert hasattr(mod, "hours_to_earnings"), "missing public hours_to_earnings()"
    assert hasattr(mod, "get_next_earnings_dt"), "missing get_next_earnings_dt()"
    assert hasattr(mod, "filter_imminent_earnings"), "missing filter_imminent_earnings()"


def test_catalyst_filter_no_op_on_empty_symbol():
    """Defensive: empty/None symbol must not raise."""
    from alpha_engine.catalyst_filter import hours_to_earnings, get_next_earnings_dt
    assert get_next_earnings_dt("") is None
    assert get_next_earnings_dt(None) is None  # type: ignore[arg-type]
    # hours_to_earnings should also tolerate junk and return None
    assert hours_to_earnings("") is None


def test_production_scanner_has_catalyst_wire_up():
    """The pre-filter call site must be present in production_scanner.py."""
    p = Path(__file__).resolve().parent.parent / "alpha_engine" / "production_scanner.py"
    src = p.read_text(encoding="utf-8")
    assert "from alpha_engine.catalyst_filter import hours_to_earnings" in src, \
        "catalyst_filter import not found in production_scanner.py"
    assert "[CATALYST FILTER]" in src, \
        "catalyst filter log marker not found in production_scanner.py"
    assert "_catalyst_block" in src, \
        "_catalyst_block flag not set on any pick — wire-up incomplete"
