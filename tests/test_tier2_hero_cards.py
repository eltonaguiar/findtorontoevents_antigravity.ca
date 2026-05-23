"""Tier-2 hero cards regression tests.

Verifies that audit_trail/dashboard_generator.py promotes the 4 buried
Tier-2 candidate strategies (signal_validation, mega_mutation, rl_agent,
claude_gainer) from the alphabetical systems[] grid into hero-card data,
AND that audit_dashboard/template.html renders them with honest CHARTER s2
tier badges (no fake-promotion of strategies that fall below the n>=100
floor).

Wiring contract under test:
  * `_compute_tier2_proven_strategies(systems, closed_picks)` returns
    a dict with `cards` (4 entries) and `flagged_dropouts` (any strategy
    that has dropped out of strict Tier-2 since 2026-04-27 research).
  * `_classify_tier(wr, pf, mdd, n)` correctly bucketises per CHARTER s2.
  * Each card carries WR / PF / MaxDD / n fields for the renderer.
  * Strategy names are NEVER truncated.
  * Dashboard payload includes a top-level `tier2_proven_strategies` key.

Reference docs:
  * docs/PERFORMANCE_CHARTER.md s2 (tier definitions, n>=100 floor)
  * updates/long_term_value_project_2026-04-27/research/13_goldmine_audit.md
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from audit_trail import dashboard_generator as dg


ROOT = Path(__file__).resolve().parent.parent
TARGET_NAMES = ("signal_validation", "mega_mutation", "rl_agent", "claude_gainer")


def _make_system(
    name,
    n_closed=120,
    n_resolved=120,
    wins=70,
    losses=30,
    win_rate=70.0,
    pf=2.5,
    mdd=12.0,
    asset_classes=("CRYPTO",),
    last_signal_at="2026-04-25T00:00:00Z",
    status="active",
):
    return {
        "name": name,
        "active_picks": 0,
        "closed_picks": n_closed,
        "resolved_picks": n_resolved,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": pf,
        "max_drawdown": mdd,
        "expectancy": 1.5,
        "total_pnl_pct": 50.0,
        "asset_classes": list(asset_classes),
        "last_signal_at": last_signal_at,
        "status": status,
    }


def _fixture_systems():
    """Synthetic systems list mirroring real production shape (Apr 28 recompute)."""
    return [
        _make_system(
            "signal_validation",
            n_closed=338,
            n_resolved=159,
            wins=95,
            losses=64,
            win_rate=59.7,
            pf=2.25,
            mdd=12.05,
            asset_classes=("CRYPTO", "FOREX"),
        ),
        _make_system(
            "mega_mutation",
            n_closed=96,
            n_resolved=58,
            wins=37,
            losses=21,
            win_rate=63.8,
            pf=2.70,
            mdd=35.96,
        ),
        _make_system(
            "rl_agent",
            n_closed=10,
            n_resolved=5,
            wins=3,
            losses=2,
            win_rate=60.0,
            pf=2.54,
            mdd=2.14,
        ),
        _make_system(
            "claude_gainer",
            n_closed=933,
            n_resolved=32,
            wins=18,
            losses=14,
            win_rate=56.2,
            pf=2.23,
            mdd=33.48,
        ),
        # Distractor — not in promotion set
        _make_system("luxalgo", n_resolved=200, win_rate=48.0, pf=1.1, mdd=18.0),
    ]


def _fixture_closed_picks():
    """Minimal closed-pick fixtures so recent_picks/sparkline have inputs."""
    out = []
    for sys_name in TARGET_NAMES:
        for i in range(5):
            out.append({
                "symbol": f"BTC{i}",
                "direction": "LONG",
                "source_system": sys_name,
                "status": "win" if i % 2 == 0 else "loss",
                "pnl_pct": 2.0 if i % 2 == 0 else -1.5,
                "closed_at": f"2026-04-{20 + i:02d}T12:00:00Z",
                "timestamp": f"2026-04-{20 + i:02d}T12:00:00Z",
            })
    return out


# ── Tier classification unit tests ─────────────────────────────────────────────


def test_classify_tier_strict_tier2_qualifies():
    """signal_validation production shape clears Tier 2."""
    tier, _reason = dg._classify_tier(wr_pct=59.7, pf=2.25, max_dd_pct=12.05, n=159)
    assert tier == "Tier 2"


def test_classify_tier_n_below_100_returns_building():
    """Strategies below the n>=100 floor must be marked 'Building' regardless of
    headline metrics — protects against fake promotion (CHARTER s10)."""
    tier, reason = dg._classify_tier(wr_pct=63.8, pf=2.70, max_dd_pct=35.96, n=58)
    assert tier == "Building"
    assert "100" in reason


def test_classify_tier_below_tier3_when_mdd_blown():
    tier, reason = dg._classify_tier(wr_pct=63.8, pf=2.70, max_dd_pct=36.0, n=140)
    assert tier == "Below Tier 3"
    assert "MDD" in reason


# ── Hero-card payload tests ───────────────────────────────────────────────────


def test_tier2_payload_returns_four_cards():
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    assert isinstance(result, dict)
    assert "cards" in result
    cards = result["cards"]
    assert len(cards) == 4
    names = [c["name"] for c in cards]
    for target in TARGET_NAMES:
        assert target in names, f"target {target} missing from hero-card list"


def test_tier2_payload_includes_required_fields():
    """Every card must expose WR / PF / MaxDD / n for the renderer."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    required = {"name", "tier", "wr_pct", "profit_factor", "max_drawdown", "n", "recent_picks", "pnl_sparkline_90d"}
    for card in result["cards"]:
        missing = required - set(card.keys())
        assert not missing, f"card {card.get('name')} missing fields: {missing}"


def test_tier2_payload_strategy_names_not_truncated():
    """No '...'-style truncation in any strategy name (full name visible)."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    for card in result["cards"]:
        assert "..." not in card["name"], f"name truncated: {card['name']!r}"
        assert card["name"] in TARGET_NAMES, f"unexpected card name: {card['name']!r}"


def test_tier2_payload_signal_validation_strict_tier2():
    """signal_validation MUST stamp as strict Tier-2 (only one that qualifies as
    of 2026-04-28 recompute — see updates/.../research/13_goldmine_audit.md)."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    sv = next(c for c in result["cards"] if c["name"] == "signal_validation")
    assert sv["tier"] == "Tier 2"
    assert sv["is_strict_tier2"] is True


def test_tier2_payload_flags_dropouts():
    """Strategies that fall below n>=100 floor at recompute time MUST end up in
    flagged_dropouts so the dashboard banner is honest."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    flagged_names = {f["name"] for f in result["flagged_dropouts"]}
    # mega_mutation, rl_agent, claude_gainer all fall below n>=100 OR exceed MDD
    assert "mega_mutation" in flagged_names
    assert "rl_agent" in flagged_names
    assert "claude_gainer" in flagged_names
    # signal_validation must NOT be flagged
    assert "signal_validation" not in flagged_names


def test_tier2_payload_thin_sample_badge_when_n_lt_200():
    """Per CHARTER s10, thin-sample badge fires for n<200."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    sv = next(c for c in result["cards"] if c["name"] == "signal_validation")
    # n=159 < 200, must be thin
    assert sv["thin_sample"] is True


def test_tier2_payload_recent_picks_has_outcome():
    """Recent picks list must include outcome / symbol for renderer."""
    result = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    sv = next(c for c in result["cards"] if c["name"] == "signal_validation")
    assert isinstance(sv["recent_picks"], list)
    if sv["recent_picks"]:
        rp = sv["recent_picks"][0]
        assert "symbol" in rp
        assert "outcome" in rp
        assert rp["outcome"] in {"WIN", "LOSS", "FLAT"}


def test_tier2_payload_staleness_detection():
    """Systems with last_signal_at > 30d ago (or missing) must be marked stale."""
    # Active system: last_signal 10 days ago
    active = dg._compute_tier2_proven_strategies(_fixture_systems(), _fixture_closed_picks())
    sv = next(c for c in active["cards"] if c["name"] == "signal_validation")
    # fixture last_signal_at = 2026-04-25, ~18 days ago → not stale
    assert sv["is_stale"] is False, f"Expected not stale, got is_stale={sv['is_stale']} stale_days={sv['stale_days']}"
    assert sv["stale_days"] is not None
    assert sv["stale_days"] < 30

    # Build a system list where signal_validation has a stale last_signal_at
    old_systems = _fixture_systems()
    for s in old_systems:
        if s["name"] == "signal_validation":
            s = dict(s)  # copy so we don't mutate the module-level fixture
            s["last_signal_at"] = "2025-01-15T00:00:00Z"  # ~480 days ago
            break
    # Replace in list
    old_systems_fixed = []
    for s in old_systems:
        if s["name"] == "signal_validation":
            old_systems_fixed.append({
                **s,
                "last_signal_at": "2025-01-15T00:00:00Z",
            })
        else:
            old_systems_fixed.append(s)

    stale_result = dg._compute_tier2_proven_strategies(old_systems_fixed, _fixture_closed_picks())
    sv_stale = next(c for c in stale_result["cards"] if c["name"] == "signal_validation")
    assert sv_stale["is_stale"] is True
    assert sv_stale["stale_days"] > 30

    # Missing last_signal_at should also be stale
    no_signal_systems = _fixture_systems()
    no_signal_fixed = []
    for s in no_signal_systems:
        s_copy = dict(s)
        if s_copy["name"] == "signal_validation":
            del s_copy["last_signal_at"]
        no_signal_fixed.append(s_copy)
    missing_result = dg._compute_tier2_proven_strategies(no_signal_fixed, _fixture_closed_picks())
    sv_missing = next(c for c in missing_result["cards"] if c["name"] == "signal_validation")
    assert sv_missing["is_stale"] is True
    assert sv_missing["stale_days"] is None  # unknown


# ── Template integration test ─────────────────────────────────────────────────


def test_template_html_includes_tier2_hero_section():
    """Template must contain the tier2-hero-section mount and renderer hook."""
    template = (ROOT / "audit_dashboard" / "template.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert 'id="tier2-hero-section"' in template, "tier2 hero section mount missing"
    assert 'renderTier2Heroes' in template, "renderTier2Heroes JS function missing"
    assert 'tier2-hero-cards-grid' in template, "tier2 cards grid mount missing"


def test_template_html_renders_full_strategy_names_no_truncation():
    """Hero card strategy names must use full names, not CSS-truncated."""
    template = (ROOT / "audit_dashboard" / "template.html").read_text(
        encoding="utf-8", errors="replace"
    )
    # Find the renderTier2Heroes function block
    m = re.search(r"function renderTier2Heroes\(.*?^\}", template, re.DOTALL | re.MULTILINE)
    assert m is not None, "renderTier2Heroes function not found"
    block = m.group(0)
    # Strategy name is rendered with word-break, NOT text-overflow:ellipsis
    assert "text-overflow:ellipsis" not in block, "name field uses ellipsis truncation"


# ── Optional live data integration test ───────────────────────────────────────


def test_live_dashboard_payload_includes_tier2_field():
    """If the production dashboard_data.json exists, it must carry the new field."""
    payload_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
    if not payload_path.exists():
        pytest.skip("dashboard_data.json not present in checkout")
    import json
    data = json.loads(payload_path.read_text(encoding="utf-8", errors="replace"))
    # The field is OPTIONAL on existing snapshots (added 2026-04-28); we accept
    # absence here, but if present it must be well-formed.
    if "tier2_proven_strategies" in data:
        t2 = data["tier2_proven_strategies"]
        assert isinstance(t2, dict)
        assert "cards" in t2
        assert "flagged_dropouts" in t2
