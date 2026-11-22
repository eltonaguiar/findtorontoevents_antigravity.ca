"""The (population, cost_model, win_definition) triple is declared and honest."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import (  # noqa: E402
    COST_MODEL,
    FLAT_EPSILON_PCT,
    POPULATION,
    WIN_DEFINITION,
    build_view,
    canonical_row,
    provenance,
)

PICK = {
    "id": "p1", "symbol": "AAA", "asset_class": "EQUITY", "direction": "LONG",
    "entry_price": 100.0, "pnl_pct": 2.0, "closed_at": "2026-11-19", "strategy": "s1",
}


def test_provenance_names_all_three_parts():
    prov = provenance()
    assert prov["population"] == POPULATION == "resolved_closed_picks_net"
    assert prov["cost_model"] == COST_MODEL
    assert prov["win_definition"] == WIN_DEFINITION
    assert prov["schema"] == "audit.canonical.v1"


def test_build_view_carries_the_triple():
    view = build_view([PICK], generated_at="2026-11-20T00:00:00Z")
    assert view["provenance"]["population"] == POPULATION
    assert view["provenance"]["cost_model"] == COST_MODEL
    assert view["provenance"]["win_definition"] == WIN_DEFINITION


def test_declared_win_definition_matches_the_code():
    """The string must describe what canonical_row actually computes.

    `won` is gross-based by design, so a pick that clears the epsilon gross but
    not after cost is a WIN and a net loss at the same time. That is exactly the
    trap the declaration exists to expose — assert it rather than hope.
    """
    row = canonical_row({**PICK, "pnl_pct": FLAT_EPSILON_PCT + 0.001})
    assert row is not None
    assert row["won"] is True
    assert row["pnl_net_pct"] < 0, "cost exceeds the gross gain — win, but net-negative"
    assert "gross" in WIN_DEFINITION and "net" not in WIN_DEFINITION


def test_flat_is_neither_a_win_nor_a_loss():
    row = canonical_row({**PICK, "pnl_pct": 0.0})
    assert row is not None
    assert row["won"] is False and row["lost"] is False
    assert row["status"] == "FLAT"
