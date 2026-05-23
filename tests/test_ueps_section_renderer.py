"""Tests for audit_dashboard.ueps_section_renderer.

Project context: updates/long_term_value_project_2026-04-27/PROJECT.md
                Phases 10-11 — dashboard surface for long-term value + swing.

These tests verify:
  * Empty-state placeholder when no picks supplied.
  * Long-term value pick renders all 10 spec elements.
  * Swing pick renders TP/SL/R:R; no thesis-break section.
  * Mandatory ``n=`` display on every aggregate stat.
  * Tier-badge classification per SYNTHESIS § 7 thresholds.
  * LTCG tax-warning banner around 365-day boundary.
  * No XSS — every user-controlled string is escaped.
  * Inline SVG sparkline emission for dividend history.
"""
from __future__ import annotations

import logging

import pytest

from audit_dashboard.ueps_section_renderer import (
    classify_tier,
    render_aggregate_stat_block,
    render_empty_state,
    render_pick_card,
    render_ueps_section,
    render_markdown_inline,
)


# ── Sample fixtures ──────────────────────────────────────────────────────────


def _sample_long_term_pick() -> dict:
    return {
        "symbol": "AAPL",
        "direction": "LONG",
        "entry_price": 150.0,
        "current_price": 165.0,
        "intrinsic_value": 200.0,
        "asset_class": "EQUITY",
        "source_system": "value_screener",
        "strategy": "magic_formula",
        "status": "ACTIVE",
        "pick_type": "long_term_value",
        "holding_horizon": "3y+",
        "exit_mode": "thesis",
        "days_held": 200,
        "thesis": (
            "**Strong free-cash-flow** generator with durable ROIC.\n"
            "- Magic Formula rank top-decile\n"
            "- Piotroski 8/9\n"
            "- Acquirer's Multiple 6.4 (cheap)"
        ),
        "thesis_break_rules": [
            {"metric": "ROIC", "op": "<", "threshold": 0.10, "source": "edgartools"},
            {"metric": "DebtToEquity", "op": ">", "threshold": 1.0, "source": "edgartools"},
            {"metric": "AltmanZDoublePrime", "op": "<", "threshold": 1.10, "source": "edgartools"},
        ],
        "fundamental_snapshot": {
            "pe": 14.0,
            "pb": 1.4,
            "roic": 0.22,
            "fcf_yield": 0.082,
            "debt_to_equity": 0.45,
            "piotroski_f": 8,
            "magic_formula_rank": 17,
            "acquirers_multiple": 6.4,
            "altman_z_double_prime": 3.2,
            "beneish_m": -2.45,
        },
        "earnings_history": [
            {"date": "2025-Q4", "eps_actual": 2.10, "eps_estimate": 2.05, "surprise_pct": 2.4},
            {"date": "2025-Q3", "eps_actual": 1.95, "eps_estimate": 1.90, "surprise_pct": 2.6},
            {"date": "2025-Q2", "eps_actual": 1.65, "eps_estimate": 1.70, "surprise_pct": -2.9},
        ],
        "next_earnings_date": "2026-05-30",
        "dividend_record": {
            "annual_yield": 0.024,
            "payout_ratio": 0.35,
            "consecutive_growth_years": 12,
            "next_ex_div_date": "2026-05-15",
            "history_5y": [
                {"ex_date": "2022-05-15", "amount": 0.23},
                {"ex_date": "2023-05-15", "amount": 0.27},
                {"ex_date": "2024-05-15", "amount": 0.32},
                {"ex_date": "2025-05-15", "amount": 0.38},
                {"ex_date": "2026-05-15", "amount": 0.42},
            ],
        },
        "extra": {
            "current_metrics": {
                "ROIC": 0.21,
                "DebtToEquity": 0.45,
                "AltmanZDoublePrime": 3.2,
            },
            "target_position_pct": 0.05,
            "current_position_pct": 0.04,
            "technical_state": {
                "price": 165.0,
                "ema_50": 158.0,
                "rsi": 56.0,
                "support": 150.0,
                "resistance": 175.0,
            },
        },
    }


def _sample_swing_pick() -> dict:
    return {
        "symbol": "NVDA",
        "direction": "LONG",
        "entry_price": 400.0,
        "take_profit": 428.0,  # +7%
        "stop_loss": 394.0,    # -1.5%
        "asset_class": "EQUITY",
        "source_system": "swing_screener",
        "strategy": "trend_momentum_earnings_catalyst",
        "status": "ACTIVE",
        "pick_type": "swing",
        "holding_horizon": "1m",
        "exit_mode": "tp_sl",
        "days_held": 3,
        "next_earnings_date": "2026-05-15",
        "extra": {
            "swing_score_breakdown": {
                "total_score": 0.81,
                "trend_score": 0.85,
                "momentum_score": 0.80,
                "volume_score": 0.70,
                "catalyst_score": 0.95,
                "signal_quality": "strong",
            },
        },
    }


# ── Tests ────────────────────────────────────────────────────────────────────


def test_renders_empty_state_with_no_picks():
    html = render_ueps_section(picks=[])
    assert "ueps-section" in html
    # All three tabs should still render
    assert "Long-Term Value Holds" in html
    assert "Swing Plays" in html
    assert "Closed Holds" in html
    # Empty-state placeholder appears for each tab
    assert html.count("Building track record") >= 1
    assert "ueps-empty-state" in html


def test_renders_long_term_value_pick_with_all_required_elements():
    pick = _sample_long_term_pick()
    html = render_pick_card(pick)
    # Header pieces
    assert "AAPL" in html
    assert "EQUITY" in html
    assert "long_term_value" in html
    assert "3y+" in html
    assert "day 200" in html
    # Thesis text rendered (markdown converted)
    assert "<strong>Strong free-cash-flow</strong>" in html
    assert "Magic Formula rank top-decile" in html  # list item content
    # Fundamentals
    assert "F-Score" in html
    assert "8/9" in html
    assert "Altman Z" in html
    assert "3.20" in html  # Altman Z'' value
    assert "Magic Formula Rank" in html
    assert "#17" in html
    # IV progress bar present (entry/current/target labels)
    assert "ueps-iv-progress" in html
    assert "Entry: 150.00" in html
    assert "Current: 165.00" in html
    assert "IV Target: 200.00" in html


def test_renders_swing_pick_with_tp_sl_visible():
    pick = _sample_swing_pick()
    html = render_pick_card(pick)
    assert "NVDA" in html
    # TP/SL values
    assert "428.00" in html  # TP
    assert "394.00" in html  # SL
    # R:R = (428-400) / (400-394) = 28/6 = 4.67
    assert "4.67:1" in html
    # No thesis-break section for a swing pick
    assert "ueps-thesis-break" not in html
    # No IV progress bar for swing
    assert "ueps-iv-progress" not in html


def test_renders_n_count_for_strategy_aggregate():
    stats = {
        "strategy": "magic_formula",
        "wr": 0.52,
        "pf": 1.7,
        "n": 250,
    }
    html = render_aggregate_stat_block(stats)
    assert "n=250" in html
    # WR/PF rendered with values
    assert "WR 52.0%" in html
    assert "PF 1.70" in html
    # n label appears next to each stat
    assert html.count("n=250") >= 2


def test_renderer_warns_on_aggregate_stats_without_n(caplog):
    stats = {"strategy": "magic_formula", "wr": 0.52, "pf": 1.7}
    with caplog.at_level(logging.WARNING, logger="audit_dashboard.ueps_section_renderer"):
        html = render_aggregate_stat_block(stats)
    assert "n=?" in html
    assert any(
        "missing n=" in rec.message for rec in caplog.records
    ), f"expected warning about missing n=; got {[r.message for r in caplog.records]}"


def test_renders_tier_badge_correct_for_above_floor():
    # WR=55%, PF=2.1, MDD=8%, n=200 -> Tier 1
    tier = classify_tier(wr=0.55, pf=2.1, mdd=0.08, n=200)
    assert tier == "Tier 1"
    stats = {"strategy": "magic_formula", "wr": 0.55, "pf": 2.1, "mdd": 0.08, "n": 200}
    html = render_aggregate_stat_block(stats)
    assert "Tier 1" in html
    assert "tier1" in html


def test_renders_tier_badge_pre_tier_for_low_n():
    tier = classify_tier(wr=0.6, pf=2.5, mdd=0.05, n=20)
    assert tier == "Building (n=20/100)"
    stats = {"strategy": "magic_formula", "wr": 0.6, "pf": 2.5, "mdd": 0.05, "n": 20}
    html = render_aggregate_stat_block(stats)
    assert "Building (n=20/100)" in html
    assert "building" in html


def test_renders_tier_2_for_meets_t2_but_not_t1():
    tier = classify_tier(wr=0.51, pf=1.6, mdd=0.15, n=150)
    assert tier == "Tier 2"


def test_renders_tax_warning_banner_when_approaching_ltcg():
    pick = _sample_long_term_pick()
    pick["days_held"] = 350
    html = render_pick_card(pick)
    assert "LTCG" in html
    assert "ueps-tax-banner" in html
    assert "ueps-tax-warn" in html  # not yet hit, so warn (not ok)
    # Days-to-LTCG: 365 - 350 = 15
    assert "15 day" in html


def test_renders_tax_warning_NOT_when_well_within_ltcg():
    pick = _sample_long_term_pick()
    pick["days_held"] = 200
    html = render_pick_card(pick)
    assert "LTCG" not in html
    assert "ueps-tax-banner" not in html


def test_renders_tax_ok_banner_after_ltcg_threshold():
    """Past the 365-day mark, banner switches from warn -> ok."""
    pick = _sample_long_term_pick()
    pick["days_held"] = 380
    html = render_pick_card(pick)
    assert "LTCG" in html
    assert "ueps-tax-ok" in html
    assert "qualifies for long-term capital gains" in html


def test_renders_thesis_break_status_per_rule():
    pick = _sample_long_term_pick()
    # 3 rules + corresponding current_metrics already in fixture
    html = render_pick_card(pick)
    assert "ueps-thesis-break" in html
    # Each rule should appear in the table
    assert html.count("ueps-rule-state") == 3
    # All rules currently PASS (none triggered) given fixture metrics
    assert html.count(">PASS<") == 3
    assert ">FAIL<" not in html

    # Now flip one current-metric so the ROIC<0.10 rule triggers.
    pick["extra"]["current_metrics"]["ROIC"] = 0.05
    html2 = render_pick_card(pick)
    assert ">FAIL<" in html2
    assert html2.count(">PASS<") == 2
    assert html2.count(">FAIL<") == 1


def test_html_output_is_valid_no_unescaped_user_content():
    pick = _sample_long_term_pick()
    pick["thesis"] = "<script>alert(1)</script> evil & dangerous"
    pick["symbol"] = '<img src=x onerror=alert(1)>'
    pick["dividend_record"]["next_ex_div_date"] = '"><svg/onload=alert(1)>'
    html_out = render_pick_card(pick)
    # The literal *tag* MUST NOT appear unescaped (no executable HTML).
    assert "<script>" not in html_out
    assert "<img src=x" not in html_out
    assert "<svg/onload=" not in html_out
    # No raw quote-break-out from attribute context: every user-controlled
    # attribute must keep the wrapping quote intact. We verify by checking
    # that the dangerous payload appears in escaped form only.
    assert '"><svg/onload=alert(1)>' not in html_out
    assert "&quot;&gt;&lt;svg/onload=alert(1)&gt;" in html_out
    # Escaped forms SHOULD appear so the operator can see what was filtered.
    assert "&lt;script&gt;" in html_out
    assert "&amp;" in html_out  # `& dangerous` becomes &amp;
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_out


def test_renders_dividend_sparkline_svg():
    pick = _sample_long_term_pick()
    html = render_pick_card(pick)
    assert "<svg" in html
    assert "ueps-div-sparkline" in html
    # 5-point polyline emitted
    assert "<polyline" in html
    # All 5 entries should map to (x,y) pairs (count commas in `points=`)
    poly_start = html.find("points=\"")
    assert poly_start != -1, "polyline points attribute missing"
    poly_end = html.find("\"", poly_start + len("points=\""))
    points_attr = html[poly_start + len("points=\""):poly_end]
    # Each point separated by space, 5 points => 4 spaces.
    assert points_attr.count(" ") == 4


def test_renders_full_ueps_section_with_mixed_pick_types():
    """End-to-end: mixed picks bucket into the right tabs."""
    picks = [
        _sample_long_term_pick(),
        _sample_swing_pick(),
        {**_sample_long_term_pick(), "symbol": "MSFT", "status": "CLOSED"},
    ]
    html = render_ueps_section(picks=picks)
    assert "AAPL" in html
    assert "NVDA" in html
    assert "MSFT" in html
    # Tab structure
    assert 'data-panel="long-term"' in html
    assert 'data-panel="swing"' in html
    assert 'data-panel="closed"' in html


def test_markdown_subset_renders_safely():
    md = "**bold** and *italic* and `code` and <evil>"
    out = render_markdown_inline(md)
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out
    # The evil tag was escaped before any markdown processing.
    assert "<evil>" not in out
    assert "&lt;evil&gt;" in out


def test_aggregate_stats_passed_through_to_card():
    """When aggregate_stats_by_strategy is supplied to render_ueps_section,
    each pick card should display its strategy's tier badge."""
    pick = _sample_long_term_pick()  # strategy=magic_formula
    stats_map = {
        "magic_formula": {
            "strategy": "magic_formula",
            "wr": 0.55,
            "pf": 2.1,
            "mdd": 0.08,
            "n": 200,
        }
    }
    html = render_ueps_section(
        picks=[pick],
        aggregate_stats_by_strategy=stats_map,
    )
    assert "Tier 1" in html
    # n=200 must appear next to WR/PF/MDD (mandatory display).
    assert html.count("n=200") >= 3


def test_empty_state_renders_tab_label():
    html = render_empty_state("Long-Term Value Holds")
    assert "Long-Term Value Holds" in html
    assert "Building track record" in html


def test_dividend_sparkline_handles_single_point_history():
    pick = _sample_long_term_pick()
    pick["dividend_record"]["history_5y"] = [
        {"ex_date": "2026-05-15", "amount": 0.42}
    ]
    html = render_pick_card(pick)
    # Single point still produces a valid <svg> element
    assert "<svg" in html
    assert "ueps-div-sparkline" in html
