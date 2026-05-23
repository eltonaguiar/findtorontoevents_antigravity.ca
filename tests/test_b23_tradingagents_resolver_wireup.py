"""B23 regression test (2026-05-01): tradingagents must be registered in
universal_pick_resolver.SYSTEM_SOURCES so its picks have outcomes resolved.

Background: PR #544 added the TradingAgents emitter; PR #582 registered
`ueps_picks.json` in dashboard's JSON_PICK_SOURCES. Cursor's audit
flagged that `tradingagents_picks.json` was never registered in the
RESOLVER's SYSTEM_SOURCES — so the picks would render on /audit but
never have TP/SL/TIME_EXIT tracked. They'd stay permanently OPEN.

This test pins the registration so a future refactor can't silently
drop it.
"""
from __future__ import annotations

from audit_trail import universal_pick_resolver


def test_tradingagents_registered_in_system_sources():
    """tradingagents must be in SYSTEM_SOURCES with the canonical pick file path."""
    sources = dict(universal_pick_resolver.SYSTEM_SOURCES)
    assert "tradingagents" in sources, (
        "tradingagents missing from universal_pick_resolver.SYSTEM_SOURCES — "
        "picks emitted by alpha_engine/tradingagents_emitter.py would never "
        "have outcomes resolved (permanently OPEN). Add the entry "
        '("tradingagents", "alpha_engine/data/tradingagents_picks.json").'
    )
    assert sources["tradingagents"] == "alpha_engine/data/tradingagents_picks.json", (
        "tradingagents path in SYSTEM_SOURCES does not match the emitter's "
        "output file. The emitter writes to alpha_engine/data/tradingagents_picks.json "
        "(see alpha_engine/tradingagents_emitter.py DEFAULT_OUTPUT)."
    )


def test_tradingagents_path_matches_dashboard_json_pick_sources():
    """Cross-check: the resolver's SYSTEM_SOURCES path for tradingagents
    must match what JSON_PICK_SOURCES uses in dashboard_generator.
    A drift between the two = tradingagents picks visible on /audit
    but never resolved → permanent-OPEN bug class."""
    from audit_trail import dashboard_generator

    resolver_sources = dict(universal_pick_resolver.SYSTEM_SOURCES)
    # JSON_PICK_SOURCES is a list of (system_name, active_path, closed_path)
    dashboard_sources = {
        entry[0]: entry[1] for entry in dashboard_generator.JSON_PICK_SOURCES
    }

    assert "tradingagents" in dashboard_sources, "tradingagents missing from dashboard JSON_PICK_SOURCES"
    assert "tradingagents" in resolver_sources, "tradingagents missing from resolver SYSTEM_SOURCES"
    assert resolver_sources["tradingagents"] == dashboard_sources["tradingagents"], (
        f"Path drift: resolver={resolver_sources['tradingagents']!r} vs "
        f"dashboard={dashboard_sources['tradingagents']!r}. Both must point to the same file."
    )
