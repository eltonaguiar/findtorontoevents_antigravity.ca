"""Render-surface tests for loop3 49759d10 summary keys.

Verifies that the four NEW summary payload keys added in commit 49759d109b5
are wired both into the dashboard generator output and the /audit page
template.html. Also guards the existing F8 / F2 / BT-FWD correlation cards
against accidental deletion when peers refactor the summary card grid.

Per CLAUDE.md the dashboard generator is NEVER executed in tests — these
are static source-text checks only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "audit_dashboard" / "template.html"
GENERATOR = REPO_ROOT / "audit_trail" / "dashboard_generator.py"

NEW_PAYLOAD_KEYS = (
    "total_pnl_pct_compounded_rolling_100",
    "total_pnl_pct_geomean_annualized",
    "net_sharpe_per_trade",
    "net_sharpe_per_trade_annual",
)


@pytest.fixture(scope="module")
def template_text() -> str:
    if not TEMPLATE.exists():
        pytest.skip(f"template not present: {TEMPLATE}")
    return TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def generator_text() -> str:
    if not GENERATOR.exists():
        pytest.skip(f"generator not present: {GENERATOR}")
    return GENERATOR.read_text(encoding="utf-8")


# ── Template references the 4 new payload keys ────────────────────────────
@pytest.mark.parametrize("key", NEW_PAYLOAD_KEYS)
def test_template_references_new_summary_key(template_text: str, key: str) -> None:
    assert key in template_text, (
        f"audit_dashboard/template.html does not reference summary.{key} — "
        f"the loop3 49759d10 metric is collected in the payload but not rendered."
    )


# ── Generator emits the 4 new payload keys ────────────────────────────────
@pytest.mark.parametrize("key", NEW_PAYLOAD_KEYS)
def test_generator_emits_new_summary_key(generator_text: str, key: str) -> None:
    quoted = f'"{key}"'
    assert quoted in generator_text, (
        f"audit_trail/dashboard_generator.py does not emit {quoted} into the "
        f"summary block — payload schema is missing the loop3 49759d10 metric."
    )


# ── Tooltips for the new tiles are present (so users see context) ─────────
def test_template_has_rolling100_tooltip(template_text: str) -> None:
    assert "Last 100 closed trades compounded" in template_text


def test_template_has_geomean_tooltip(template_text: str) -> None:
    assert "Daily mean return" in template_text and "252" in template_text


def test_template_has_per_trade_sharpe_tooltip(template_text: str) -> None:
    assert "Strategy-quality Sharpe" in template_text


def test_template_has_per_trade_sharpe_annual_tooltip(template_text: str) -> None:
    assert "sqrt(trades_per_year)" in template_text


# ── New tile labels render on the page ────────────────────────────────────
@pytest.mark.parametrize(
    "label",
    [
        "Rolling 100",
        "Annualized geomean",
        "Sharpe (per-trade) *",
        "Sharpe (per-trade, ann.)",
    ],
)
def test_template_has_new_card_label(template_text: str, label: str) -> None:
    assert label in template_text, f"new summary card label not rendered: {label}"


# ── Em-dash null safety: the new tiles must not render '0' on null ────────
def test_template_uses_em_dash_for_null_values(template_text: str) -> None:
    # The two compound tiles + two sharpe tiles all share the pattern
    # `has ? fmt...(...) : '—'`. Confirm at least 4 such guards live in the
    # newly inserted block (search the literal em-dash, U+2014).
    em = "'—'"
    occurrences = template_text.count(em)
    assert occurrences >= 4, (
        f"expected at least 4 em-dash null guards (one per new tile), "
        f"found {occurrences}. The new tiles may render '0' on null payloads."
    )


# ── Regression guards: existing cards still wired ─────────────────────────
def test_f8_divergence_card_still_present(template_text: str) -> None:
    assert "F8 FWD-vs-BT Divergence" in template_text, (
        "F8 divergence card was removed — likely accidental during the loop3 "
        "summary-tile addition. Restore it."
    )


def test_f2_per_asset_class_leaderboard_still_present(template_text: str) -> None:
    assert "Per-asset-class leaderboard" in template_text, (
        "F2 per-asset-class leaderboard reference removed — restore it."
    )


def test_bt_fwd_correlation_card_still_present(template_text: str) -> None:
    assert "BT/FWD Corr" in template_text, (
        "BT/FWD correlation card was removed — likely accidental during the "
        "loop3 summary-tile addition. Restore it."
    )


def test_existing_total_pnl_card_still_present(template_text: str) -> None:
    # The Total PnL card lives next to the new tiles; if our edit accidentally
    # collapsed it, this catches it.
    assert "'Total PnL'" in template_text or '"Total PnL"' in template_text


def test_existing_net_sharpe_card_still_present(template_text: str) -> None:
    assert "'Net Sharpe'" in template_text or '"Net Sharpe"' in template_text
