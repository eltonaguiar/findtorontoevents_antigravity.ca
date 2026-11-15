"""wired_in_childlike must be on both the dashboard and the resolver."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ACTIVE = "audit_dashboard/data/wired_in_childlike_active_picks.json"


def test_dashboard_and_resolver_register_same_file() -> None:
    dash = (REPO / "audit_trail/dashboard_generator.py").read_text(encoding="utf-8")
    resolver = (REPO / "audit_trail/universal_pick_resolver.py").read_text(encoding="utf-8")
    assert "wired_in_childlike" in dash
    assert ACTIVE in dash
    assert "wired_in_childlike" in resolver
    assert ACTIVE in resolver
    assert '"wired_in_childlike"' in dash.split("_PAPER_ONLY_SYSTEMS")[1].split("_HIDDEN_SYSTEMS")[0]


def test_active_file_is_monitorable() -> None:
    payload = json.loads((REPO / ACTIVE).read_text(encoding="utf-8"))
    picks = payload["picks"]
    assert len(picks) == 3
    classes = {p["asset_class"] for p in picks}
    assert classes == {"ETF", "EQUITY", "BOND"}
    for p in picks:
        assert p["status"] == "OPEN"
        assert p["entry_price"] > 0
        assert p["take_profit"] > p["entry_price"] > p["stop_loss"]
        assert "current_price" not in p
        assert p["sizing_allowed"] is False
