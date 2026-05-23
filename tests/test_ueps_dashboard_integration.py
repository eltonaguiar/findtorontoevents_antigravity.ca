"""UEPS dashboard integration tests.

Verifies that audit_trail/dashboard_generator.py wires
audit_dashboard/ueps_section_renderer.render_ueps_section() into the
`#ueps-section-mount` div of audit_dashboard/template.html.

Wiring contract under test:
  * `_render_ueps_section_html(active, closed)` filters picks by
    pick_type in {long_term_value, swing}; ignores other types.
  * `_build_ueps_aggregate_stats(closed)` returns per-strategy {wr, pf, n}
    where n counts CLOSED picks only (per docs/PERFORMANCE_CHARTER.md
    section 10 "n=value" rule).
  * `build_html(payload, ueps_active_picks=..., ueps_closed_picks=...)`
    replaces the `<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->` marker in
    template.html with the rendered HTML.

Reference docs:
  * updates/long_term_value_project_2026-04-27/PROJECT.md
  * audit_dashboard/ueps_section_renderer.py (render_ueps_section)
  * alpha_engine/long_term_pick_contract.py (is_long_term_value, is_swing)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from audit_trail import dashboard_generator as dg
from audit_dashboard.ueps_section_renderer import render_ueps_section


ROOT = Path(__file__).resolve().parent.parent


# Fixtures


def _make_long_term_value_pick(symbol="AAPL", **overrides):
    pick = {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": 150.0,
        "asset_class": "EQUITY",
        "source_system": "value_screener",
        "strategy": "magic_formula_x_piotroski",
        "status": "ACTIVE",
        "pick_type": "long_term_value",
        "holding_horizon": "3y+",
        "exit_mode": "thesis",
        "thesis": "Quality compounder at attractive multiple.",
        "thesis_break_rules": [{"metric": "roic", "op": "<", "threshold": 0.10}],
        "intrinsic_value": 200.0,
        "fundamental_snapshot": {"piotroski_f": 8, "roic": 0.22},
        "earnings_history": [],
        "next_earnings_date": None,
        "dividend_record": {},
        "catalyst_dates": [],
        "universe_gate_passed": True,
        "safety_gate_passed": True,
    }
    pick.update(overrides)
    return pick


def _make_swing_pick(symbol="MSFT", **overrides):
    pick = {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": 400.0,
        "take_profit": 420.0,
        "stop_loss": 388.0,
        "asset_class": "EQUITY",
        "source_system": "swing_screener",
        "strategy": "trend_momentum_earnings_catalyst",
        "status": "ACTIVE",
        "pick_type": "swing",
        "holding_horizon": "1m",
        "exit_mode": "tp_sl",
    }
    pick.update(overrides)
    return pick


def _make_crypto_pick(symbol="BTCUSDT"):
    """A non-UEPS pick that should be filtered out by the wiring."""
    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": 50000.0,
        "asset_class": "CRYPTO",
        "source_system": "alpha_engine",
        "strategy": "btc_scalp",
        "status": "ACTIVE",
    }


# 1. Empty-picks -> "Building" placeholder


def test_render_with_no_picks_produces_building_placeholder():
    """render_ueps_section([], {}) emits valid HTML containing 'Building'."""
    out = render_ueps_section(picks=[], aggregate_stats_by_strategy={})
    assert isinstance(out, str)
    assert len(out) > 0
    assert "Building" in out
    assert "class=\"ueps-section\"" in out
    assert out.count("ueps-empty-state") >= 3


def test_helper_renders_building_state_for_non_ueps_picks():
    """Helper with only non-UEPS picks renders a valid section showing
    "Building" empty-state in each sub-tab; non-UEPS pick must NOT leak in."""
    crypto = _make_crypto_pick()
    out = dg._render_ueps_section_html([crypto], [])
    assert out
    assert "Building" in out
    assert "BTCUSDT" not in out


# 2. Pick with ticker reaches the rendered HTML


def test_render_with_long_term_value_pick_includes_ticker():
    pick = _make_long_term_value_pick(symbol="GOOGL")
    out = render_ueps_section(
        picks=[pick],
        aggregate_stats_by_strategy={},
    )
    assert "GOOGL" in out
    assert "data-pick-type=\"long_term_value\"" in out
    assert "Quality compounder" in out


# 3. Filter by pick_type


def test_render_filters_picks_by_type():
    ltv = _make_long_term_value_pick(symbol="AAPL")
    swing = _make_swing_pick(symbol="MSFT")
    crypto = _make_crypto_pick(symbol="BTCUSDT")

    out = dg._render_ueps_section_html([ltv, swing, crypto], [])
    assert out
    assert "AAPL" in out
    assert "MSFT" in out
    assert "BTCUSDT" not in out


def test_helper_skips_picks_without_pick_type_field():
    """Picks missing pick_type (legacy crypto/forex picks) must be dropped."""
    legacy = {
        "symbol": "EURUSD=X",
        "direction": "LONG",
        "asset_class": "FOREX",
        "strategy": "forex_carry_momentum",
        "status": "ACTIVE",
    }
    out = dg._render_ueps_section_html([legacy], [])
    assert "EURUSD" not in out
    assert "Building" in out


# 4. n in aggregate_stats == count of closed picks (CHARTER section 10)


def test_n_value_in_aggregate_stats_matches_closed_pick_count():
    """5 closed long_term_value picks -> aggregate_stats[n] == 5."""
    strategy = "magic_formula_x_piotroski"
    closed = [
        _make_long_term_value_pick(
            symbol="CLO" + str(i), strategy=strategy, status="CLOSED",
            pnl_pct=2.0 if i < 3 else -1.0,
        )
        for i in range(5)
    ]
    aggs = dg._build_ueps_aggregate_stats(closed)
    assert strategy in aggs
    assert aggs[strategy]["n"] == 5


def test_aggregate_wr_pf_computed_from_closed_pnl():
    """3 wins + 2 losses -> WR=0.6; gross_profit=12, gross_loss=3 -> PF=4.0."""
    strategy = "swing_strat_a"
    closed = [
        _make_swing_pick(strategy=strategy, status="CLOSED", pnl_pct=5.0),
        _make_swing_pick(strategy=strategy, status="CLOSED", pnl_pct=4.0),
        _make_swing_pick(strategy=strategy, status="CLOSED", pnl_pct=3.0),
        _make_swing_pick(strategy=strategy, status="CLOSED", pnl_pct=-2.0),
        _make_swing_pick(strategy=strategy, status="CLOSED", pnl_pct=-1.0),
    ]
    aggs = dg._build_ueps_aggregate_stats(closed)
    assert aggs[strategy]["n"] == 5
    assert aggs[strategy]["wr"] == pytest.approx(0.6, abs=0.001)
    assert aggs[strategy]["pf"] == pytest.approx(4.0, abs=0.01)


def test_aggregate_stats_only_count_closed_long_term_or_swing():
    """A closed CRYPTO pick must NOT contribute to UEPS aggregates."""
    closed = [
        _make_long_term_value_pick(
            symbol="LTV1", strategy="ueps_strat", status="CLOSED", pnl_pct=3.0
        ),
        # Closed crypto pick — must be excluded
        {
            "symbol": "BTC",
            "strategy": "ueps_strat",
            "status": "CLOSED",
            "pick_type": "scalp",
            "pnl_pct": 999.0,  # would dominate if leaked
        },
    ]
    aggs = dg._build_ueps_aggregate_stats(closed)
    assert aggs["ueps_strat"]["n"] == 1
    assert aggs["ueps_strat"]["wr"] == pytest.approx(1.0, abs=0.001)


# 5. Template substitution


def test_template_has_ueps_marker_and_mount():
    template = (ROOT / "audit_dashboard" / "template.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->" in template
    assert "id=\"ueps-section-mount\"" in template
    assert "id=\"tab-ueps\"" in template


def test_template_substitution_lands_in_mount_point(tmp_path, monkeypatch):
    """build_html() with one LTV pick: rendered ticker shows up inside
    the #ueps-section-mount div in the output index.html."""
    template_src = ROOT / "audit_dashboard" / "template.html"
    template_text = template_src.read_text(encoding="utf-8", errors="replace")

    fake_root = tmp_path
    (fake_root / "audit_dashboard").mkdir()
    (fake_root / "audit_dashboard" / "data").mkdir()
    (fake_root / "audit_dashboard" / "template.html").write_text(
        template_text, encoding="utf-8"
    )
    monkeypatch.setattr(dg, "ROOT", fake_root)

    payload = {"meta": {"generated_at": "2026-04-28T00:00:00Z"}}
    pick = _make_long_term_value_pick(symbol="NVDA")

    dg.build_html(payload, ueps_active_picks=[pick], ueps_closed_picks=[])

    out_html = (fake_root / "audit_dashboard" / "index.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->" not in out_html
    assert "NVDA" in out_html
    # The rendered NVDA ticker appears inside the mount div.
    mount_idx = out_html.index("id=\"ueps-section-mount\"")
    nvda_idx = out_html.index("NVDA")
    assert nvda_idx > mount_idx


def test_template_substitution_with_empty_picks_renders_section_frame(
    tmp_path, monkeypatch
):
    """Empty pick lists: marker is replaced by the renderer's own
    section frame, which contains a "Building" empty-state in each sub-tab."""
    template_src = ROOT / "audit_dashboard" / "template.html"
    template_text = template_src.read_text(encoding="utf-8", errors="replace")

    fake_root = tmp_path
    (fake_root / "audit_dashboard").mkdir()
    (fake_root / "audit_dashboard" / "data").mkdir()
    (fake_root / "audit_dashboard" / "template.html").write_text(
        template_text, encoding="utf-8"
    )
    monkeypatch.setattr(dg, "ROOT", fake_root)

    payload = {"meta": {"generated_at": "2026-04-28T00:00:00Z"}}
    dg.build_html(payload, ueps_active_picks=[], ueps_closed_picks=[])

    out_html = (fake_root / "audit_dashboard" / "index.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "Building" in out_html


def test_disk_load_fallback_when_picks_not_passed(tmp_path, monkeypatch):
    """build_html() without explicit picks loads from disk; missing
    closed_picks.json doesn't crash the build."""
    template_src = ROOT / "audit_dashboard" / "template.html"
    template_text = template_src.read_text(encoding="utf-8", errors="replace")

    fake_root = tmp_path
    (fake_root / "audit_dashboard").mkdir()
    (fake_root / "audit_dashboard" / "data").mkdir()
    (fake_root / "alpha_engine").mkdir()
    (fake_root / "alpha_engine" / "data").mkdir()
    (fake_root / "audit_dashboard" / "template.html").write_text(
        template_text, encoding="utf-8"
    )
    (fake_root / "alpha_engine" / "data" / "active_picks.json").write_text(
        "[]", encoding="utf-8"
    )
    monkeypatch.setattr(dg, "ROOT", fake_root)

    payload = {"meta": {"generated_at": "2026-04-28T00:00:00Z"}}
    dg.build_html(payload)

    out_html = (fake_root / "audit_dashboard" / "index.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "Building" in out_html


# 6. Closed long_term_value picks reach the renderer's "Closed Holds" tab


def test_closed_long_term_value_picks_route_to_closed_subtab():
    """Closed LTV picks land in the renderer's data-panel="closed" section."""
    closed = _make_long_term_value_pick(symbol="IBM", status="CLOSED")
    out = dg._render_ueps_section_html([], [closed])
    assert "IBM" in out
    closed_panel_idx = out.index("data-panel=\"closed\"")
    ibm_idx = out.index("IBM")
    long_term_panel_idx = out.index("data-panel=\"long-term\"")
    assert ibm_idx > closed_panel_idx
    long_term_slice = out[long_term_panel_idx:closed_panel_idx]
    assert "IBM" not in long_term_slice
